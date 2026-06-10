import sqlite3
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import log_loss, brier_score_loss, accuracy_score
import json

DB_PATH = "elo_ratings.sqlite"

def evaluate(name, preds, actuals):
    # Clip to prevent log loss domain errors
    preds = np.clip(preds, 1e-15, 1 - 1e-15)
    ll = log_loss(actuals, preds)
    brier = brier_score_loss(actuals, preds)
    acc = accuracy_score(actuals, preds > 0.5)
    print(f"  {name:15} | Log Loss: {ll:.4f} | Brier: {brier:.4f} | Accuracy: {acc:.2%}")

def test_split_date(df, split_date, features):
    print(f"\n==================================================")
    print(f" Chronological Split Date: {split_date}")
    print(f"==================================================")
    
    train_df = df[df['match_date'] < split_date].copy()
    test_df = df[df['match_date'] >= split_date].copy()
    
    print(f"  Train matches: {len(train_df)}")
    print(f"  Test matches:  {len(test_df)}")
    
    X_train = train_df[features]
    y_train = train_df['winner_side_1']
    X_test = test_df[features]
    y_test = test_df['winner_side_1']
    
    model = xgb.XGBClassifier(
        objective='binary:logistic',
        eval_metric='logloss',
        max_depth=5,
        learning_rate=0.08,
        n_estimators=150,
        subsample=0.8,
        colsample_bytree=0.8,
        enable_categorical=True,
        random_state=42
    )
    
    model.fit(X_train, y_train, verbose=False)
    
    # Predict
    test_df['xgb_prob'] = model.predict_proba(X_test)[:, 1]
    test_df['elo_prob'] = 1 / (1 + 10 ** (-test_df['elo_diff'] / 400.0))
    test_df['whr_prob'] = 1 / (1 + 10 ** (-test_df['whr_diff'] / 400.0))
    
    evaluate("Baseline Elo", test_df['elo_prob'], y_test)
    evaluate("Baseline WHR", test_df['whr_prob'], y_test)
    evaluate("XGBoost Expect", test_df['xgb_prob'], y_test)

def main():
    conn = sqlite3.connect(DB_PATH)
    print("Loading ML features from database...")
    df = pd.read_sql_query("SELECT * FROM ml_match_features", conn)
    conn.close()
    
    print(f"Loaded {len(df)} matches.")
    
    # 1. Convert categorical features to category dtype
    df['tier'] = df['tier'].astype('category')
    df['round'] = df['round'].astype('category')
    df['event'] = df['event'].astype('category')
    
    # Ensure all numeric columns are float
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
    
    # Test multiple split dates to ensure robustness and no leak/drift
    test_split_date(df, '2023-01-01', features)
    test_split_date(df, '2024-01-01', features)
    test_split_date(df, '2025-01-01', features)
    
    # 7. Train final model on entire dataset and save
    print("\nTraining final model on full dataset...")
    X_full = df[features]
    y_full = df['winner_side_1']
    
    final_model = xgb.XGBClassifier(
        objective='binary:logistic',
        eval_metric='logloss',
        max_depth=5,
        learning_rate=0.08,
        n_estimators=150,
        subsample=0.8,
        colsample_bytree=0.8,
        enable_categorical=True,
        random_state=42
    )
    final_model.fit(X_full, y_full, verbose=False)
    
    # Try SHAP analysis on full dataset sample
    try:
        import shap
        print("\nCalculating SHAP values for full dataset sample...")
        explainer = shap.TreeExplainer(final_model)
        sample_X = X_full.sample(n=10000, random_state=42)
        shap_values = explainer(sample_X)
        
        # Print top feature contributions
        vals = np.abs(shap_values.values).mean(0)
        feature_importance = pd.DataFrame(list(zip(X_full.columns, vals)), columns=['feature', 'importance_value'])
        feature_importance.sort_values(by=['importance_value'], ascending=False, inplace=True)
        print("Top 8 Feature Contributions (SHAP):")
        print(feature_importance.head(8).to_string(index=False))
    except Exception as e:
        print(f"SHAP calculations skipped: {e}")
        
    # Serialize model and save as BLOB in SQLite
    import pickle
    print("\nSerializing and saving final expectation model to database...")
    model_bytes = pickle.dumps(final_model)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS ml_models (model_name TEXT PRIMARY KEY, model_bytes BLOB)")
    cursor.execute("INSERT OR REPLACE INTO ml_models (model_name, model_bytes) VALUES (?, ?)", ("xgboost_expectation", model_bytes))
    conn.commit()
    conn.close()
    print("Saved final expectation model directly in 'elo_ratings.sqlite' (table: ml_models).")

if __name__ == "__main__":
    main()
