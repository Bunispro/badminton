import os
import sqlite3
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.metrics import log_loss, brier_score_loss, accuracy_score
import bisect

# Try loading from web/backend/.env or current directory
if os.path.exists("web/backend/.env"):
    load_dotenv("web/backend/.env")
else:
    load_dotenv()

CORE_DB_PATH = os.getenv("CORE_DB", "bwf_data_2008-now__v1.sqlite")
RATINGS_DB_PATH = os.getenv("RATINGS_DB", "elo_ratings.sqlite")

def main():
    print("Database paths:")
    print(f"  CORE_DB:    {CORE_DB_PATH}")
    print(f"  RATINGS_DB: {RATINGS_DB_PATH}")
    
    if not os.path.exists(CORE_DB_PATH) or not os.path.exists(RATINGS_DB_PATH):
        print("Error: One or both databases not found.")
        return
        
    print("\nLoading BWF historical rankings into memory...")
    conn_ratings = sqlite3.connect(RATINGS_DB_PATH)
    cursor_ratings = conn_ratings.cursor()
    cursor_ratings.execute("SELECT rank_date, event, player_id, points FROM bwf_historical_rankings ORDER BY rank_date ASC")
    rankings_rows = cursor_ratings.fetchall()
    
    # build dictionary for fast O(log N) bisect lookup
    rankings_dict = {}
    for r_date, event, p_id, pts in rankings_rows:
        p_id = str(p_id)
        key = (p_id, event)
        if key not in rankings_dict:
            rankings_dict[key] = []
        rankings_dict[key].append((r_date, pts))
        
    print(f"Loaded {len(rankings_rows)} rankings for {len(rankings_dict)} player-event combinations.")
    
    print("\nLoading matches and participants from core DB...")
    conn_core = sqlite3.connect(CORE_DB_PATH)
    conn_core.row_factory = sqlite3.Row
    cursor_core = conn_core.cursor()
    
    # Fetch all valid matches in the era covered by the scraped rankings
    cursor_core.execute("""
        SELECT m.match_id, m.match_date, m.event_canon, m.winner_side, mp.player_id, mp.side
        FROM matches m
        JOIN match_participants mp ON m.match_id = mp.match_id
        WHERE m.is_valid_for_rating = 1 AND m.match_date >= '2019-02-19' AND m.match_date <= '2022-12-31'
        ORDER BY m.match_date ASC
    """)
    rows = cursor_core.fetchall()
    print(f"Loaded {len(rows)} participant rows from core DB.")
    
    # Group participants by match_id
    matches = {}
    for row in rows:
        mid = row['match_id']
        if mid not in matches:
            matches[mid] = {
                "match_id": mid,
                "date": row['match_date'],
                "event": row['event_canon'],
                "winner": row['winner_side'],
                "side1": [],
                "side2": []
            }
        if row['side'] == 1:
            matches[mid]["side1"].append(str(row['player_id']))
        else:
            matches[mid]["side2"].append(str(row['player_id']))
            
    print(f"Grouped into {len(matches)} matches.")
    
    # Helper function to find the most recent points relative to a match_date
    def get_points(p_id, ev, match_date):
        lst = rankings_dict.get((p_id, ev))
        if not lst:
            return None
        # Extract dates for bisecting
        dates = [x[0] for x in lst]
        idx = bisect.bisect_right(dates, match_date)
        if idx > 0:
            return lst[idx - 1][1]
        return None
        
    print("\nCalculating BWF predictions...")
    dataset = []
    for mid, m in matches.items():
        event = m["event"]
        date = m["date"]
        winner = m["winner"]
        
        # Side 1 points lookup
        pts_list1 = []
        for p_id in m["side1"]:
            pts = get_points(p_id, event, date)
            if pts is not None:
                pts_list1.append(pts)
                
        # Side 2 points lookup
        pts_list2 = []
        for p_id in m["side2"]:
            pts = get_points(p_id, event, date)
            if pts is not None:
                pts_list2.append(pts)
                
        # We need points for both sides to make a prediction
        if pts_list1 and pts_list2:
            pts1 = sum(pts_list1) / len(pts_list1)
            pts2 = sum(pts_list2) / len(pts_list2)
            
            if pts1 > 0 and pts2 > 0:
                actual = 1 if winner == 1 else 0
                
                # Calibrated Ratio Model: P = 1 / (1 + (P2/P1)^0.1987)
                prob_ratio = 1.0 / (1.0 + (pts2 / pts1) ** 0.1987)
                
                # Calibrated Difference Model: P = 1 / (1 + 10^(-(P1-P2)/95238.1))
                prob_diff = 1.0 / (1.0 + 10.0 ** (-(pts1 - pts2) / 95238.1))
                
                dataset.append({
                    "match_id": mid,
                    "points_p1": int(round(pts1)),
                    "points_p2": int(round(pts2)),
                    "predicted_prob_ratio": prob_ratio,
                    "predicted_prob_diff": prob_diff,
                    "actual": actual
                })
                
    print(f"Calculated predictions for {len(dataset)} matches.")
    
    if dataset:
        df_pred = pd.DataFrame(dataset)
        actuals = df_pred["actual"].values
        
        # Ratio model metrics
        preds_ratio = np.clip(df_pred["predicted_prob_ratio"].values, 1e-15, 1.0 - 1e-15)
        ll_ratio = log_loss(actuals, preds_ratio)
        brier_ratio = brier_score_loss(actuals, preds_ratio)
        acc_ratio = accuracy_score(actuals, preds_ratio > 0.5)
        
        # Difference model metrics
        preds_diff = np.clip(df_pred["predicted_prob_diff"].values, 1e-15, 1.0 - 1e-15)
        ll_diff = log_loss(actuals, preds_diff)
        brier_diff = brier_score_loss(actuals, preds_diff)
        acc_diff = accuracy_score(actuals, preds_diff > 0.5)
        
        print("\n==================================================")
        print(f" BWF Predictor Performance ({len(dataset)} matches)")
        print("==================================================")
        print(" BWF Ratio Model:")
        print(f"  Log Loss:    {ll_ratio:.4f}")
        print(f"  Brier Score: {brier_ratio:.4f}")
        print(f"  Accuracy:    {acc_ratio:.2%}")
        print("--------------------------------------------------")
        print(" BWF Difference Model:")
        print(f"  Log Loss:    {ll_diff:.4f}")
        print(f"  Brier Score: {brier_diff:.4f}")
        print(f"  Accuracy:    {acc_diff:.2%}")
        print("==================================================\n")
        
        print("Storing BWF predictions in table 'bwf_prediction_log'...")
        cursor_ratings.execute("DROP TABLE IF EXISTS bwf_prediction_log")
        cursor_ratings.execute("""
            CREATE TABLE bwf_prediction_log (
                match_id TEXT PRIMARY KEY,
                points_p1 INTEGER,
                points_p2 INTEGER,
                predicted_prob_ratio REAL,
                predicted_prob_diff REAL,
                actual INTEGER
            )
        """)
        
        bwf_log_data = [
            (str(m["match_id"]), int(m["points_p1"]), int(m["points_p2"]), float(m["predicted_prob_ratio"]), float(m["predicted_prob_diff"]), int(m["actual"]))
            for m in dataset
        ]
        
        cursor_ratings.executemany("""
            INSERT INTO bwf_prediction_log (match_id, points_p1, points_p2, predicted_prob_ratio, predicted_prob_diff, actual)
            VALUES (?, ?, ?, ?, ?, ?)
        """, bwf_log_data)
        
        cursor_ratings.execute("CREATE INDEX IF NOT EXISTS idx_bwf_pred_match ON bwf_prediction_log(match_id)")
        conn_ratings.commit()
        print(f"Successfully saved {len(bwf_log_data)} BWF predictions to ratings DB.")
        
    conn_ratings.close()
    conn_core.close()

if __name__ == "__main__":
    main()
