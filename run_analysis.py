import sqlite3
import numpy as np
import json
import sys

TEST_DB_PATH = "testing_bwf.sqlite"

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

def analyze_run(run_id):
    """Analyzes a specific run_id and updates the metadata tables."""
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()

    print(f"Analyzing run: {run_id}")

    # Fetch all predictions for the run
    cursor.execute("""
        SELECT event, predicted_prob, actual
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

    for event, pred, actual in rows:
        if event not in data_by_event:
            data_by_event[event] = {'preds': [], 'actuals': []}
        data_by_event[event]['preds'].append(pred)
        data_by_event[event]['actuals'].append(actual)
        all_preds.append(pred)
        all_actuals.append(actual)

    # --- Analyze Overall Performance ---
    all_preds = np.array(all_preds)
    all_actuals = np.array(all_actuals)
    
    overall_log_loss, overall_brier, overall_ece, overall_accuracy = calculate_metrics(all_preds, all_actuals)
    
    print("\n--- Overall Metrics ---")
    print(f"  Log Loss: {overall_log_loss:.4f}")
    print(f"  Brier Score: {overall_brier:.4f}")
    print(f"  ECE: {overall_ece:.4f}")
    print(f"  Accuracy: {overall_accuracy:.4f}")
    print(f"  Total Matches: {len(all_preds)}")

    # Update the main metadata table
    cursor.execute("""
        UPDATE run_metadata
        SET log_loss = ?, brier = ?, ece = ?, accuracy = ?, n_matches = ?
        WHERE run_id = ?
    """, (overall_log_loss, overall_brier, overall_ece, overall_accuracy, len(all_preds), run_id))

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

