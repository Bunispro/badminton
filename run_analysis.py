import sqlite3
import numpy as np
import json
import sys
from db_ratings import init_rating_table # Import init_rating_table

TEST_DB_PATH = "elo_ratings.sqlite"

def calculate_metrics(predictions, actuals):
    """Calculates log_loss, brier score, and ECE."""
    if len(predictions) == 0:
        return None, None, None, None

    # Log Loss
    log_loss = -np.mean(actuals * np.log(predictions) + (1 - actuals) * np.log(1 - predictions))

    # Brier Score
    brier = np.mean((predictions - actuals) ** 2)

    # Expected Calibration Error (ECE)
    n_bins = 10
    bin_limits = np.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_limits[:-1]
    bin_uppers = bin_limits[1:]
    
    ece = 0.0
    for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
        in_bin = (predictions > bin_lower) & (predictions <= bin_upper)
        prop_in_bin = np.mean(in_bin)
        
        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(actuals[in_bin])
            avg_confidence_in_bin = np.mean(predictions[in_bin])
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin

    # Accuracy
    accuracy = np.mean((predictions > 0.5) == actuals)

    return log_loss, brier, ece, accuracy

def add_missing_columns(cursor):
    """
    Adds new columns to the run_metadata table if they don't exist.
    This is a simple migration to handle schema updates.
    """
    columns_to_add = [
        ("favorite_gap", "REAL"),
        ("mean_prediction", "REAL"),
        ("prediction_bias", "REAL"),
        ("mean_uncertainty", "REAL"),
        ("median_uncertainty", "REAL"),
        ("std_uncertainty", "REAL"),
        ("pct_u_max", "REAL"),
        ("pct_u_min", "REAL"),
    ]
    
    cursor.execute("PRAGMA table_info(run_metadata)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            cursor.execute(f"ALTER TABLE run_metadata ADD COLUMN {col_name} {col_type}")
            print(f"Added missing column '{col_name}' to 'run_metadata' table.")

def analyze_run(run_id):
    """Analyzes a specific run_id and updates the metadata tables."""
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()

    # Ensure tables exist before querying
    init_rating_table(conn)
    add_missing_columns(cursor) # Add this call to handle schema updates

    print(f"Analyzing run: {run_id}")

    # Fetch all predictions for the run
    cursor.execute("""
        SELECT event, predicted_prob, actual, uncertainty_mean
        FROM prediction_log
        WHERE run_id = ?
    """, (run_id,))
    
    rows = cursor.fetchall()
    if not rows:
        print("No predictions found for this run_id. Aborting.")
        return

    # Organize data by event
    data_by_event = {}
    all_preds = []
    all_actuals = []
    all_uncertainties = []

    for event, pred, actual, uncertainty_mean in rows:
        if event not in data_by_event:
            data_by_event[event] = {'preds': [], 'actuals': []}
        data_by_event[event]['preds'].append(pred)
        data_by_event[event]['actuals'].append(actual)
        all_preds.append(pred)
        all_actuals.append(actual)
        all_uncertainties.append(uncertainty_mean)

    # --- Analyze Overall Performance ---
    all_preds = np.array(all_preds)
    all_actuals = np.array(all_actuals)
    all_uncertainties = np.array(all_uncertainties)
    
    overall_log_loss, overall_brier, overall_ece, overall_accuracy = calculate_metrics(all_preds, all_actuals)
    
    print("\n--- Overall Metrics ---")
    print(f"  Log Loss: {overall_log_loss:.4f}")
    print(f"  Brier Score: {overall_brier:.4f}")
    print(f"  ECE: {overall_ece:.4f}")
    print(f"  Accuracy: {overall_accuracy:.4f}")

    # Calculate additional metrics
    mean_prediction = np.mean(all_preds)
    prediction_bias = np.mean(all_preds) - np.mean(all_actuals)
    
    # Favorite Gap (Win rate of the predicted favorite)
    favorite_wins = np.sum((all_preds > 0.5) & (all_actuals == 1))
    total_favorites = np.sum(all_preds > 0.5)
    favorite_gap = (favorite_wins / total_favorites) if total_favorites > 0 else 0.0

    # Uncertainty metrics
    mean_uncertainty = np.mean(all_uncertainties)
    median_uncertainty = np.median(all_uncertainties)
    std_uncertainty = np.std(all_uncertainties)
    pct_u_max = np.sum(all_uncertainties >= 0.9) / len(all_uncertainties) # % of matches with high uncertainty
    pct_u_min = np.sum(all_uncertainties <= 0.1) / len(all_uncertainties) # % of matches with low uncertainty

    print(f"  Mean Prediction: {mean_prediction:.4f}")
    print(f"  Prediction Bias: {prediction_bias:.4f}")
    print(f"  Favorite Win Rate (Favorite Gap): {favorite_gap:.4f}")
    print(f"  Mean Uncertainty: {mean_uncertainty:.4f}")
    print(f"  Median Uncertainty: {median_uncertainty:.4f}")
    print(f"  Std Uncertainty: {std_uncertainty:.4f}")
    print(f"  % U >= 0.9: {pct_u_max:.4f}")
    print(f"  % U <= 0.1: {pct_u_min:.4f}")
    print(f"  Total Matches: {len(all_preds)}")

    # Update the main metadata table
    cursor.execute("""
        UPDATE run_metadata SET
            log_loss = ?, brier = ?, ece = ?, accuracy = ?, n_matches = ?,
            mean_prediction = ?, prediction_bias = ?, favorite_gap = ?,
            mean_uncertainty = ?, median_uncertainty = ?, std_uncertainty = ?,
            pct_u_max = ?, pct_u_min = ?
        WHERE run_id = ?
    """, (overall_log_loss, overall_brier, overall_ece, overall_accuracy, len(all_preds),
          mean_prediction, prediction_bias, favorite_gap,
          mean_uncertainty, median_uncertainty, std_uncertainty,
          pct_u_max, pct_u_min, run_id))

    # --- Analyze Per-Event Performance ---
    print("\n--- Per-Event Metrics ---")
    for event, data in sorted(data_by_event.items()):
        preds = np.array(data['preds'])
        actuals = np.array(data['actuals'])
        
        log_loss, brier, ece, _ = calculate_metrics(preds, actuals)
        
        print(f"  {event}:")
        print(f"    Log Loss: {log_loss:.4f}, Brier: {brier:.4f}, ECE: {ece:.4f}, N: {len(preds)}")

        # Update the event-specific metrics table
        cursor.execute("""
            INSERT INTO run_event_metrics (run_id, event, log_loss, brier, ece, n_matches)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id, event) DO UPDATE SET
                log_loss = excluded.log_loss,
                brier = excluded.brier,
                ece = excluded.ece,
                n_matches = excluded.n_matches
        """, (run_id, event, log_loss, brier, ece, len(preds)))
    
    conn.commit()
    conn.close()
    print("\nAnalysis complete and metrics saved to the database.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_id_to_analyze = sys.argv[1]
        analyze_run(run_id_to_analyze)
    else:
        # If no run_id is provided, try to find the most recent one
        try:
            conn = sqlite3.connect(TEST_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1")
            last_run = cursor.fetchone()
            conn.close()
            if last_run:
                print("No run_id provided. Analyzing the most recent run.")
                analyze_run(last_run[0])
            else:
                print("Error: No run_id provided and no runs found in the database.")
                print("Usage: python run_analysis.py <run_id>")
        except Exception as e:
            print(f"Error: Could not automatically find the last run. {e}")
            print("Usage: python run_analysis.py <run_id>")
