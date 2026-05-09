import sqlite3
import numpy as np
import sys
from datetime import date

def calculate_ece(preds, actuals, n_bins=10):
    confidences = np.maximum(preds, 1 - preds)
    accuracies = (preds > 0.5) == actuals
    
    bin_boundaries = np.linspace(0.5, 1.0, n_bins + 1)
    ece = 0
    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i+1]
        
        in_bin = (confidences >= bin_lower) & (confidences < bin_upper)
        if np.sum(in_bin) > 0:
            bin_acc = np.mean(accuracies[in_bin])
            bin_conf = np.mean(confidences[in_bin])
            weight = np.sum(in_bin) / len(preds)
            ece += weight * np.abs(bin_acc - bin_conf)
    return ece


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
    overall_preds_early = []
    overall_actuals_early = []
    overall_preds_late = []
    overall_actuals_late = []
    
    for event in events:
        print(f"\nProcessing {event}...")
        
        # Load ratings into memory for fast lookup: ratings[player_id][date_str] = rating
        cursor_test.execute("""
            SELECT player_id, rating_date, rating 
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
        
        # Sort matches by date for chronological split
        matches.sort(key=lambda x: x[1])
        
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
        brier = np.mean((preds - actuals)**2)
        ece = calculate_ece(preds, actuals)
        
        print(f"  Matches: {len(preds)}")
        print(f"  Log Loss: {log_loss:.5f}")
        print(f"  Accuracy: {accuracy:.4f}")
        print(f"  Brier Score: {brier:.5f}")
        print(f"  ECE: {ece:.5f}")
        
        # Chronological Split (Overfitting Test)
        split_idx = int(len(preds) * 0.8)
        if split_idx > 0 and split_idx < len(preds):
            preds_early = preds[:split_idx]
            actuals_early = actuals[:split_idx]
            preds_late = preds[split_idx:]
            actuals_late = actuals[split_idx:]
            
            ll_early = -np.mean(actuals_early * np.log(preds_early + 1e-15) + (1 - actuals_early) * np.log(1 - preds_early + 1e-15))
            acc_early = np.mean((preds_early > 0.5) == actuals_early)
            
            ll_late = -np.mean(actuals_late * np.log(preds_late + 1e-15) + (1 - actuals_late) * np.log(1 - preds_late + 1e-15))
            acc_late = np.mean((preds_late > 0.5) == actuals_late)
            
            print(f"  --- Split Analysis ---")
            print(f"  Early 80% ({len(preds_early)} matches) - Log Loss: {ll_early:.5f}, Acc: {acc_early:.4f}")
            print(f"  Late 20% ({len(preds_late)} matches) - Log Loss: {ll_late:.5f}, Acc: {acc_late:.4f}")
            
            overall_preds_early.extend(preds_early)
            overall_actuals_early.extend(actuals_early)
            overall_preds_late.extend(preds_late)
            overall_actuals_late.extend(actuals_late)
        
        overall_preds.extend(preds)
        overall_actuals.extend(actuals)
        
    overall_preds = np.array(overall_preds)
    overall_actuals = np.array(overall_actuals)
    
    if len(overall_preds) > 0:
        log_loss = -np.mean(overall_actuals * np.log(overall_preds + 1e-15) + (1 - overall_actuals) * np.log(1 - overall_preds + 1e-15))
        accuracy = np.mean((overall_preds > 0.5) == overall_actuals)
        brier = np.mean((overall_preds - overall_actuals)**2)
        ece = calculate_ece(overall_preds, overall_actuals)
        
        print(f"\n--- Overall Results ---")
        print(f"Total Matches: {len(overall_preds)}")
        print(f"Log Loss: {log_loss:.5f}")
        print(f"Accuracy: {accuracy:.4f}")
        print(f"Brier Score: {brier:.5f}")
        print(f"ECE: {ece:.5f}")
        
        if len(overall_preds_early) > 0:
            overall_preds_early = np.array(overall_preds_early)
            overall_actuals_early = np.array(overall_actuals_early)
            overall_preds_late = np.array(overall_preds_late)
            overall_actuals_late = np.array(overall_actuals_late)
            
            ll_early = -np.mean(overall_actuals_early * np.log(overall_preds_early + 1e-15) + (1 - overall_actuals_early) * np.log(1 - overall_preds_early + 1e-15))
            acc_early = np.mean((overall_preds_early > 0.5) == overall_actuals_early)
            
            ll_late = -np.mean(overall_actuals_late * np.log(overall_preds_late + 1e-15) + (1 - overall_actuals_late) * np.log(1 - overall_preds_late + 1e-15))
            acc_late = np.mean((overall_preds_late > 0.5) == overall_actuals_late)
            
            print(f"\n--- Overall Split Analysis ---")
            print(f"Early 80% ({len(overall_preds_early)} matches) - Log Loss: {ll_early:.5f}, Acc: {acc_early:.4f}")
            print(f"Late 20% ({len(overall_preds_late)} matches) - Log Loss: {ll_late:.5f}, Acc: {acc_late:.4f}")
            
    conn_test.close()
    conn_core.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python whr_analysis.py <run_id_prefix>")
        sys.exit(1)
    run_id_prefix = sys.argv[1]
    analyze_whr(run_id_prefix)
