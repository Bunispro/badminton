import sqlite3
import numpy as np
import sys
from datetime import date

CORE_DB_PATH = "bwf_data_2008-now__v1.sqlite"
TEST_DB_PATH = "elo_ratings.sqlite"

def analyze_whr(run_id_prefix):
    conn_test = sqlite3.connect(TEST_DB_PATH)
    cursor_test = conn_test.cursor()
    
    conn_core = sqlite3.connect(CORE_DB_PATH)
    cursor_core = conn_core.cursor()
    
    # 1. Get all events for this run
    cursor_test.execute("SELECT DISTINCT event FROM whr_rating_history WHERE run_id LIKE ?", (run_id_prefix + "%",))
    events = [r[0] for r in cursor_test.fetchall()]
    
    if not events:
        print(f"No events found for run ID prefix: {run_id_prefix}")
        return
        
    print(f"Analyzing WHR run: {run_id_prefix}")
    
    overall_preds = []
    overall_actuals = []
    
    for event in events:
        print(f"\nProcessing {event}...")
        
        # Load ratings into memory for fast lookup: ratings[player_id][date_str] = rating
        cursor_test.execute("""
            SELECT entity_id, rating_date, rating 
            FROM whr_rating_history 
            WHERE run_id LIKE ? AND event = ?
        """, (run_id_prefix + "%", event))
        
        ratings_lookup = {}
        for pid, dt, r in cursor_test.fetchall():
            if pid not in ratings_lookup:
                ratings_lookup[pid] = {}
            ratings_lookup[pid][dt] = r
            
        # Fetch matches for this event
        is_doubles = event in ["MD", "WD", "XD"]
        query = """
            SELECT
                m.match_id,
                m.match_date,
                m.winner_side,
                GROUP_CONCAT(CASE WHEN mp.side = 1 THEN mp.player_id END) AS p1_ids,
                GROUP_CONCAT(CASE WHEN mp.side = 2 THEN mp.player_id END) AS p2_ids
            FROM matches m
            JOIN match_participants mp ON mp.match_id = m.match_id
            WHERE m.event_canon = ? AND m.is_valid_for_rating = 1
            GROUP BY m.match_id, m.match_date, m.winner_side
            HAVING COUNT(CASE WHEN mp.side = 1 THEN 1 END) > 0
               AND COUNT(CASE WHEN mp.side = 2 THEN 1 END) > 0
        """
        cursor_core.execute(query, (event,))
        matches = cursor_core.fetchall()
        
        preds = []
        actuals = []
        
        for mid, dt, winner, p1_ids_str, p2_ids_str in matches:
            if is_doubles:
                p1_ids = p1_ids_str.split(',')
                p2_ids = p2_ids_str.split(',')
            else:
                p1_ids = [p1_ids_str]
                p2_ids = [p2_ids_str]
                
            # Get ratings for side A
            rA = 0
            valid = True
            for pid in p1_ids:
                r = ratings_lookup.get(pid, {}).get(dt)
                if r is not None:
                    rA += r
                else:
                    valid = False
                    break
                    
            # Get ratings for side B
            rB = 0
            for pid in p2_ids:
                r = ratings_lookup.get(pid, {}).get(dt)
                if r is not None:
                    rB += r
                else:
                    valid = False
                    break
                    
            if not valid:
                continue # Skip if ratings not found (should be rare)
                
            # Calculate probability
            # Elo formula: P = 1 / (1 + 10^((rB - rA)/400))
            prob = 1.0 / (1.0 + 10.0 ** ((rB - rA) / 400.0))
            
            preds.append(prob)
            actuals.append(1 if winner == 1 else 0)
            
        preds = np.array(preds)
        actuals = np.array(actuals)
        
        if len(preds) == 0:
            print(f"No valid matches with ratings found for {event}.")
            continue
            
        log_loss = -np.mean(actuals * np.log(preds + 1e-15) + (1 - actuals) * np.log(1 - preds + 1e-15))
        accuracy = np.mean((preds > 0.5) == actuals)
        
        print(f"  Matches: {len(preds)}")
        print(f"  Log Loss: {log_loss:.5f}")
        print(f"  Accuracy: {accuracy:.4f}")
        
        overall_preds.extend(preds)
        overall_actuals.extend(actuals)
        
    overall_preds = np.array(overall_preds)
    overall_actuals = np.array(overall_actuals)
    
    if len(overall_preds) > 0:
        log_loss = -np.mean(overall_actuals * np.log(overall_preds + 1e-15) + (1 - overall_actuals) * np.log(1 - overall_preds + 1e-15))
        accuracy = np.mean((overall_preds > 0.5) == overall_actuals)
        
        print(f"\n--- Overall Results ---")
        print(f"Total Matches: {len(overall_preds)}")
        print(f"Log Loss: {log_loss:.5f}")
        print(f"Accuracy: {accuracy:.4f}")
        
    conn_test.close()
    conn_core.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python whr_analysis.py <run_id_prefix>")
        sys.exit(1)
    run_id_prefix = sys.argv[1]
    analyze_whr(run_id_prefix)
