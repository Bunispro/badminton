import sqlite3
import numpy as np
import math
import json
from datetime import datetime, date, timedelta
import time
import os
from multiprocessing import Pool
import whr.whole_history_rating as whr

# --- CONFIGURATION ---
CORE_DB_PATH = "bwf_data_2008-now__v1.sqlite"
START_YEAR = 2018
OUTPUT_DIR = "whr_tuning_results"

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
    if diff > 100.0: return 0.0
    if diff < -100.0: return 1.0
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

def run_task(args):
    event, w2 = args
    print(f"Starting task: {event} with w2={w2}")
    
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        results_file = os.path.join(OUTPUT_DIR, f"results_{event}_{w2:.2f}.json")
        error_file = os.path.join(OUTPUT_DIR, f"error_{event}_{w2:.2f}.txt")
        
        # Load data
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

        # Initialize WHR
        whr_system = whr.Base(config={'w2': w2})
        
        # Burn-in
        initial_games = [g for g in games if g['date'].year < START_YEAR]
        for g in initial_games:
            whr_system.create_game(g['p1'], g['p2'], g['winner'], g['day_index'], 0, g['weight'])
        whr_system.iterate(50)

        def get_safe_rating(player):
            hist = whr_system.ratings_for_player(player)
            return hist[-1][1] if hist else 0.0

        all_preds, all_actuals = [], []
        test_games_pool = [g for g in games if g['date'].year >= START_YEAR]
        
        max_day = max(g['day_index'] for g in test_games_pool)
        start_day = min(g['day_index'] for g in test_games_pool)
        
        checkpoints = []
        weeks_processed = 0
        
        for current_day in range(start_day, max_day + 1, 7):
            week_games = [g for g in test_games_pool if current_day <= g['day_index'] < current_day + 7]
            
            if not week_games:
                weeks_processed += 1
                continue

            # Predict
            for g in week_games:
                if is_doubles:
                    rA = sum(get_safe_rating(p) for p in g['p1'])
                    rB = sum(get_safe_rating(p) for p in g['p2'])
                else:
                    rA = get_safe_rating(g['p1'])
                    rB = get_safe_rating(g['p2'])

                prob = safe_prob(rA, rB)
                all_preds.append(prob)
                all_actuals.append(1 if g['winner'] == 'A' else 0)

            # Add and Update
            for g in week_games:
                whr_system.create_game(g['p1'], g['p2'], g['winner'], g['day_index'], 0, g['weight'])
            
            whr_system.auto_iterate(time_limit=10, precision=1e-3, batch_size=5)
            weeks_processed += 1

            # Checkpoint every 10 weeks
            if weeks_processed % 10 == 0:
                current_real_date = start_date + timedelta(days=current_day)
                month_str = current_real_date.strftime('%b %Y')
                
                preds_np = np.array(all_preds)
                actuals_np = np.array(all_actuals)
                
                log_loss = -np.mean(actuals_np * np.log(preds_np + 1e-15) + (1 - actuals_np) * np.log(1 - preds_np + 1e-15))
                accuracy = np.mean((preds_np > 0.5) == actuals_np)
                ece = calculate_ece(preds_np, actuals_np)
                brier = np.mean((preds_np - actuals_np)**2)
                
                checkpoints.append({
                    "month": month_str,
                    "log_loss": round(log_loss, 5),
                    "accuracy": round(accuracy, 4),
                    "ece": round(ece, 5),
                    "brier": round(brier, 5)
                })
                
                # Save checkpoints
                with open(results_file, "w") as f:
                    json.dump(checkpoints, f, indent=4)
                
                print(f"[{event} w2={w2}] Checkpoint at {month_str}")

        # Final save
        current_real_date = start_date + timedelta(days=max_day)
        month_str = current_real_date.strftime('%b %Y')
        preds_np = np.array(all_preds)
        actuals_np = np.array(all_actuals)
        
        log_loss = -np.mean(actuals_np * np.log(preds_np + 1e-15) + (1 - actuals_np) * np.log(1 - preds_np + 1e-15))
        accuracy = np.mean((preds_np > 0.5) == actuals_np)
        ece = calculate_ece(preds_np, actuals_np)
        brier = np.mean((preds_np - actuals_np)**2)
        
        checkpoints.append({
            "month": month_str,
            "log_loss": round(log_loss, 5),
            "accuracy": round(accuracy, 4),
            "ece": round(ece, 5),
            "brier": round(brier, 5),
            "final": True
        })
        
        with open(results_file, "w") as f:
            json.dump(checkpoints, f, indent=4)
            
        print(f"Completed task: {event} with w2={w2}")
        return True
        
    except Exception as e:
        print(f"Error in task {event} with w2={w2}: {e}")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        error_file = os.path.join(OUTPUT_DIR, f"error_{event}_{w2:.2f}.txt")
        with open(error_file, "a") as f:
            f.write(f"{datetime.now().isoformat()}: {str(e)}\n")
        return False

if __name__ == "__main__":
    events = ["MS", "WS", "MD", "WD", "XD"]
    w2_values = [0.01, 0.05, 0.1, 0.3]
    
    tasks = [(e, w) for e in events for w in w2_values]
    print(f"Submitting {len(tasks)} tasks to pool of 4 workers...")
    
    # Use pool of 4 as requested
    with Pool(processes=4) as pool:
        results = pool.map(run_task, tasks)
        
    print("All tasks completed.")
    print(f"Successes: {sum(1 for r in results if r)}")
    print(f"Failures: {sum(1 for r in results if not r)}")
