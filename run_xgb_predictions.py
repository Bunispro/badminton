import sqlite3
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import log_loss, brier_score_loss, accuracy_score
import sys

DB_PATH = "elo_ratings.sqlite"

def calculate_ece(predictions, actuals, n_bins=10):
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
            
    return ece

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Loading ML features and matches...")
    df = pd.read_sql_query("SELECT * FROM ml_match_features ORDER BY match_date ASC", conn)
    
    # 1. Convert categorical variables
    df['tier'] = df['tier'].astype('category')
    df['round'] = df['round'].astype('category')
    df['event'] = df['event'].astype('category')
    
    numeric_cols = [
        'elo_diff', 'synergy_a', 'synergy_b', 'duration',
        'avg_rest_a', 'avg_rest_b', 'rest_diff', 'h2h_rate'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
            
    features = [
        'elo_diff', 
        'synergy_a', 
        'synergy_b', 
        'duration', 
        'tier', 
        'round', 
        'event',
        'rest_diff', 
        'h2h_rate'
    ]
    
    print("Loading trained XGBoost model from database...")
    try:
        cursor.execute("SELECT model_bytes FROM ml_models WHERE model_name = ?", ("xgboost_expectation",))
        row = cursor.fetchone()
        if not row:
            raise ValueError("Model 'xgboost_expectation' not found in ml_models table.")
        import pickle
        model = pickle.loads(row[0])
    except Exception as e:
        print(f"Error loading model: {e}")
        conn.close()
        sys.exit(1)
        
    print("Running XGBoost predictions on all matches...")
    X = df[features]
    df['xgb_prob'] = model.predict_proba(X)[:, 1]
    
    # Clip predictions to prevent infinite log loss
    preds = np.clip(df['xgb_prob'].values, 1e-15, 1.0 - 1e-15)
    actuals = df['winner_side_1'].values
    
    # Calculate overall metrics
    ll = log_loss(actuals, preds)
    brier = brier_score_loss(actuals, preds)
    acc = accuracy_score(actuals, preds > 0.5)
    ece = calculate_ece(preds, actuals)
    
    print("\n==================================================")
    print(" Overall Post-Prediction XGBoost Metrics (All Eras)")
    print("==================================================")
    print(f"  Log Loss:    {ll:.4f}")
    print(f"  Brier Score: {brier:.4f}")
    print(f"  ECE:         {ece:.4f}")
    print(f"  Accuracy:    {acc:.2%}")
    print("==================================================\n")
    
    # Store predictions in a dedicated database table
    print("Storing XGBoost predictions in table 'xgb_prediction_log'...")
    cursor.execute("DROP TABLE IF EXISTS xgb_prediction_log")
    cursor.execute("""
        CREATE TABLE xgb_prediction_log (
            match_id TEXT PRIMARY KEY,
            predicted_prob REAL,
            actual INTEGER
        )
    """)
    
    xgb_log_data = [
        (str(mid), float(prob), int(act))
        for mid, prob, act in zip(df['match_id'].values, df['xgb_prob'].values, df['winner_side_1'].values)
    ]
    
    cursor.executemany("""
        INSERT INTO xgb_prediction_log (match_id, predicted_prob, actual)
        VALUES (?, ?, ?)
    """, xgb_log_data)
    
    conn.commit()
    conn.close()
    print("Successfully completed predictions and saved results.")

if __name__ == "__main__":
    main()
