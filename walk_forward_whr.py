import sqlite3
import numpy as np
import math
import json
from datetime import datetime, date
import time
from datetime import timedelta
import whr.whole_history_rating as whr

# --- CONFIGURATION ---
CORE_DB_PATH = "bwf_data_2008-now__v1.sqlite"
W2_VALUE = 0.3  # Lowered for better ECE/Calibration as discussed
START_YEAR = 2018

def get_mov_multiplier(score_str, event_canon, mov_base_mult=0.95, mov_growth_rate=1.10):
    if event_canon not in ['MS', 'MD', 'XD'] or mov_base_mult == 1.0:
        return 1.0
    if not score_str or '-' not in score_str or 'Retired' in score_str or 'Walkover' in score_str:
        return 1.0
    
    sets = score_str.strip().split(' ')
    p1_total, p2_total = 0, 0
    for s in sets:
        parts = s.split('-')
        if len(parts) == 2:
            try:
                p1_total += int(parts[0])
                p2_total += int(parts[1])
            except ValueError: pass
                
    if p1_total == 0 and p2_total == 0: return 1.0
        
    point_gap = abs(p1_total - p2_total)
    # Margin of Victory cap at 1.2 to prevent over-fitting
    return min(1.2, mov_base_mult * (mov_growth_rate ** (point_gap - 5))) if point_gap > 5 else mov_base_mult

def safe_prob(rA, rB):
    """Safely calculates probability to prevent math.exp OverflowErrors"""
    diff = rB - rA
    # If the rating gap is astronomical, return definitive 1.0 or 0.0
    if diff > 100.0:
        return 0.0  # B is overwhelmingly favored
    elif diff < -100.0:
        return 1.0  # A is overwhelmingly favored
    
    return 1.0 / (1.0 + math.exp(diff))

def calculate_ece(preds, actuals, n_bins=10):
    confidences = np.maximum(preds, 1 - preds)
    accuracies = (preds > 0.5) == actuals
    bin_boundaries = np.linspace(0.5, 1.0, n_bins + 1)
    ece = 0
    for i in range(n_bins):
        bin_lower, bin_upper = bin_boundaries[i], bin_boundaries[i+1]
        in_bin = (confidences >= bin_lower) & (confidences < bin_upper)
        if np.sum(in_bin) > 0:
            bin_acc = np.mean(accuracies[in_bin])
            bin_conf = np.mean(confidences[in_bin])
            weight = np.sum(in_bin) / len(preds)
            ece += weight * np.abs(bin_acc - bin_conf)
    return ece

def run_walk_forward_whr(event):
    print(f"\n=== Starting Optimized Walk-Forward: {event} ===")
    core_conn = sqlite3.connect(CORE_DB_PATH)
    cursor = core_conn.cursor()

    cursor.execute("SELECT MIN(match_date) FROM matches WHERE is_valid_for_rating = 1")
    start_date = date.fromisoformat(cursor.fetchone()[0])
    
    query = """
        SELECT m.match_date, m.winner_side, 
               GROUP_CONCAT(CASE WHEN mp.side = 1 THEN mp.player_id END) AS p1_ids,
               GROUP_CONCAT(CASE WHEN mp.side = 2 THEN mp.player_id END) AS p2_ids,
               m.score
        FROM matches m
        JOIN match_participants mp ON mp.match_id = m.match_id
        WHERE m.event_canon = ? AND m.is_valid_for_rating = 1
        GROUP BY m.match_id ORDER BY m.match_date ASC
    """
    cursor.execute(query, (event,))
    raw_matches = cursor.fetchall()
    core_conn.close()
    
    print(f"Total matches found: {len(raw_matches)}")
    is_doubles = event in ["MD", "WD", "XD"]
    games = []
    for date_str, winner_side, p1_ids_str, p2_ids_str, score in raw_matches:
        current_date = date.fromisoformat(date_str)
        day_index = (current_date - start_date).days
        p1_key = p1_ids_str.split(',') if is_doubles else p1_ids_str
        p2_key = p2_ids_str.split(',') if is_doubles else p2_ids_str
        winner = 'A' if winner_side == 1 else 'B'
        weight = get_mov_multiplier(score, event)
        games.append({'date': current_date, 'day_index': day_index, 'p1': p1_key, 'p2': p2_key, 'winner': winner, 'weight': weight})


    # Initialize WHR with your tuned W2
    whr_system = whr.Base(config={'w2': W2_VALUE})
    
    # 1. OPTIMIZATION: DUMP PRE-2018 DATA
    initial_games = [g for g in games if g['date'].year < START_YEAR]
    print(f"Dumping {len(initial_games)} pre-{START_YEAR} games...")
    for g in initial_games:
        whr_system.create_game(g['p1'], g['p2'], g['winner'], g['day_index'], 0, g['weight'])
    
    print("Performing initial 50 iterations (The Burn-in)...")
    whr_system.iterate(50)

    # 2. LEAKAGE-FREE GET_RATING
    # We default to 0.0 because WHR is log-scale centered at 0.
    def get_safe_rating(player):
        # WHR stores a history. We need the MOST RECENT one known to the system.
        hist = whr_system.ratings_for_player(player)
        return hist[-1][1] if hist else 0.0

    all_preds, all_actuals = [], []
    test_games_pool = [g for g in games if g['date'].year >= START_YEAR]
    
    # Group by weeks to save time (7x speedup over daily)
    max_day = max(g['day_index'] for g in test_games_pool)
    start_day = min(g['day_index'] for g in test_games_pool)
    
    print(f"Walking forward through {len(test_games_pool)} matches...")
    
    start_time = time.time()
    total_weeks = (max_day - start_day) // 7 + 1
    weeks_processed = 0
    # The Loop
    for current_day in range(start_day, max_day + 1, 7):
        week_games = [g for g in test_games_pool if current_day <= g['day_index'] < current_day + 7]
        
        if not week_games:
            weeks_processed += 1
            continue

        # PREDICT FIRST (Zero Leakage)
        for g in week_games:
            if is_doubles:
                rA = sum(get_safe_rating(p) for p in g['p1'])
                rB = sum(get_safe_rating(p) for p in g['p2'])
            else:
                rA = get_safe_rating(g['p1'])
                rB = get_safe_rating(g['p2'])

            # Correct WHR Probability Formula
            prob = safe_prob(rA, rB)
            all_preds.append(prob)
            all_actuals.append(1 if g['winner'] == 'A' else 0)

        # ADD AND UPDATE SECOND
        for g in week_games:
            whr_system.create_game(g['p1'], g['p2'], g['winner'], g['day_index'], 0, g['weight'])
        
        # Tells it to stop iterating once the ratings stop changing by more than 0.001
        whr_system.auto_iterate(time_limit=10, precision=1e-3, batch_size=5)

        weeks_processed += 1

        # Print an update every 10 weeks (roughly every 2.5 months of "game time")
        if weeks_processed % 10 == 0 or weeks_processed == total_weeks:
            elapsed_sec = time.time() - start_time
            pct_done = (weeks_processed / total_weeks) * 100
            
            # Math for ETA
            sec_per_week = elapsed_sec / weeks_processed
            eta_sec = sec_per_week * (total_weeks - weeks_processed)
            eta_hrs = eta_sec / 3600
            
            # Convert the day_index back into a real human-readable date
            current_real_date = start_date + timedelta(days=current_day)
            
            print(f"[{pct_done:5.1f}%] Processing {current_real_date.strftime('%b %Y')} | "
                  f"Elapsed: {elapsed_sec/60:.1f}m | ETA: {eta_hrs:.2f} hrs")
            

    # --- METRICS ---
    all_preds, all_actuals = np.array(all_preds), np.array(all_actuals)
    log_loss = -np.mean(all_actuals * np.log(all_preds + 1e-15) + (1 - all_actuals) * np.log(1 - all_preds + 1e-15))
    accuracy = np.mean((all_preds > 0.5) == all_actuals)
    ece = calculate_ece(all_preds, all_actuals)

    print(f"\nRESULTS [{event}]: LL: {log_loss:.5f} | ACC: {accuracy:.4f} | ECE: {ece:.5f}")
    return {"log_loss": log_loss, "accuracy": accuracy, "ece": ece}

if __name__ == "__main__":
    events = ["MS", "WS", "MD", "WD", "XD"]
    results = {e: run_walk_forward_whr(e) for e in events}
    with open("whr_final_results.json", "w") as f:
        json.dump(results, f, indent=4)