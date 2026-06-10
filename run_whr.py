import sqlite3
import math
import os
from datetime import datetime, date, timedelta
import numpy as np
from sklearn.isotonic import IsotonicRegression

import whr.whole_history_rating as whr

def get_mov_multiplier(score_str, event_canon, mov_base_mult=0.95, mov_growth_rate=1.1):
    if event_canon not in ['MS', 'MD', 'XD'] or mov_base_mult == 1.0:
        return 1.0
    if not score_str or '-' not in score_str or 'Retired' in score_str or 'Walkover' in score_str:
        return 1.0
    
    sets = score_str.strip().split(' ')
    p1_total = 0
    p2_total = 0
    for s in sets:
        parts = s.split('-')
        if len(parts) == 2:
            try:
                p1_total += int(parts[0])
                p2_total += int(parts[1])
            except ValueError:
                pass
                
    if p1_total == 0 and p2_total == 0:
        return 1.0
        
    point_gap = abs(p1_total - p2_total)
    
    if point_gap <= 5:
        return mov_base_mult
    else:
        return min(1.2, mov_base_mult * (mov_growth_rate ** (point_gap - 5)))

def safe_prob(rA, rB):
    """Safely calculates probability using Elo scale (base 10, divisor 400)"""
    diff = (rB - rA) / 400.0
    if diff > 10.0: return 0.0
    if diff < -10.0: return 1.0
    return 1.0 / (1.0 + 10**diff)

def init_whr_tables(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whr_rating_history (
            run_id TEXT,
            player_id TEXT,
            event TEXT,
            rating_date TEXT,
            rating REAL,
            uncertainty REAL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whr_run_metadata (
            run_id TEXT PRIMARY KEY,
            w2 REAL,
            iterations INTEGER,
            created_at TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whr_run_event ON whr_rating_history (run_id, event)")
    
    # Ensure prediction_log exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_log (
            run_id TEXT,
            event TEXT,
            actual INTEGER,
            predicted_prob REAL
        )
    """)
    conn.commit()

def fetch_matches_for_whr(core_conn, event_filter, limit=None):
    print(f"Fetching matches for event: {event_filter}...")
    cursor = core_conn.cursor()

    cursor.execute("SELECT MIN(match_date) FROM matches WHERE is_valid_for_rating = 1")
    min_date_str = cursor.fetchone()[0]
    if not min_date_str:
        return [], set(), None
    start_date = date.fromisoformat(min_date_str)

    query = """
        SELECT
            m.match_date,
            m.winner_side,
            GROUP_CONCAT(CASE WHEN mp.side = 1 THEN mp.player_id END) AS p1_ids,
            GROUP_CONCAT(CASE WHEN mp.side = 2 THEN mp.player_id END) AS p2_ids,
            m.score
        FROM matches m
        JOIN match_participants mp ON mp.match_id = m.match_id
        WHERE m.event_canon = ? AND m.is_valid_for_rating = 1
        GROUP BY m.match_id, m.match_date, m.winner_side, m.score
        HAVING COUNT(CASE WHEN mp.side = 1 THEN 1 END) > 0
           AND COUNT(CASE WHEN mp.side = 2 THEN 1 END) > 0
        ORDER BY m.match_date ASC
    """
    if limit is not None:
        query += f" LIMIT {limit}"
    cursor.execute(query, (event_filter,))

    games = []
    all_entities = set()

    is_doubles = event_filter in ["MD", "WD", "XD"]

    for date_str, winner_side, p1_ids_str, p2_ids_str, score in cursor:
        current_date = date.fromisoformat(date_str)
        day_index = (current_date - start_date).days

        if is_doubles:
            p1_key = p1_ids_str.split(',')
            p2_key = p2_ids_str.split(',')
            for pid in p1_key:
                all_entities.add(pid)
            for pid in p2_key:
                all_entities.add(pid)
        else:
            p1_key = p1_ids_str
            p2_key = p2_ids_str
            all_entities.add(p1_key)
            all_entities.add(p2_key)

        winner = 'A' if winner_side == 1 else 'B'
        weight = get_mov_multiplier(score, event_filter)
        games.append([p1_key, p2_key, winner, day_index, weight])

    print(f"Found {len(games)} games starting from {start_date.isoformat()}.")
    return games, all_entities, start_date



def store_whr_results(test_conn, run_id, event, individual_ratings, start_date, w2, iterations):
    print("Storing WHR results in the database...")
    cursor = test_conn.cursor()

    cursor.execute("DELETE FROM whr_rating_history WHERE run_id = ? AND event = ?", (run_id, event))

    history_data = []

    for player_id, ratings in individual_ratings.items():
        for rating_info in ratings:
            time_step = rating_info[0]
            elo_rating = rating_info[1]
            uncertainty = rating_info[2]
            
            current_date = start_date + timedelta(days=time_step)
            rating_date_str = current_date.isoformat()
            
            history_data.append((
                run_id,
                player_id,
                event,
                rating_date_str,
                elo_rating,
                uncertainty
            ))

    batch_size = 50000
    for i in range(0, len(history_data), batch_size):
        batch = history_data[i:i+batch_size]
        cursor.executemany("""
            INSERT INTO whr_rating_history (run_id, player_id, event, rating_date, rating, uncertainty)
            VALUES (?, ?, ?, ?, ?, ?)
        """, batch)
        print(f"  ...inserted batch of {len(batch)} records")

    cursor.execute("""
        INSERT INTO whr_run_metadata (run_id, w2, iterations, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            w2=excluded.w2,
            iterations=excluded.iterations
    """, (run_id, w2, iterations, datetime.now().isoformat()))

    test_conn.commit()
    print(f"Successfully stored rating history for event {event}.")

def run_whr_for_event(core_conn, test_conn, run_id_prefix, w2, event, use_calibration=False, limit=None):
    run_id = f"{run_id_prefix}_{event}"
    print(f"\n--- Starting WHR run for event: {event} (Run ID: {run_id}) ---")

    games, all_entities, start_date = fetch_matches_for_whr(core_conn, event, limit)
    if not games:
        print(f"No games found for event {event}. Skipping.")
        return

    print(f"Processing {len(games)} games and {len(all_entities)} unique entities.")

    print(f"Initializing WHR model with w2 (skill drift) = {w2}...")
    l2_reg = 1e-4
    teammate_l2 = 0.015 if event in ["MD", "WD", "XD"] else 0.0
    whr_system = whr.Base(config={'w2': w2, 'whr_l2_reg': l2_reg, 'whr_teammate_l2_reg': teammate_l2})
    for g in games:
        whr_system.create_game(side_a=g[0], side_b=g[1], winner=g[2], time_step=g[3], handicap=0.0, weight=g[4])

    print("Running WHR iterations... (this may take a while)")
    iterations = 50
    whr_system.iterate(iterations)
    print("WHR calculation complete.")

    is_doubles = event in ["MD", "WD", "XD"]
    individual_ratings = {}
    for player_name in whr_system.players.keys():
        hist = whr_system.ratings_for_player(player_name)
        individual_ratings[player_name] = [(h[0], h[1] + 1000.0, h[2]) for h in hist]

    # Calculate predictions and calibrate if needed
    print("Calculating predictions...")
    ratings_lookup = {}
    for player_name in individual_ratings.keys():
        hist = individual_ratings[player_name]
        # Store both rating (h[1]) and uncertainty (h[2])
        ratings_lookup[player_name] = {h[0]: (h[1], h[2]) for h in hist}
        
    def get_rating(player, day):
        # Return rating and uncertainty, with defaults for new players (1000.0 baseline)
        return ratings_lookup.get(player, {}).get(day, (1000.0, 350.0))
        
    raw_preds = []
    actuals = []
    
    for g in games:
        p1, p2, winner, day, weight = g
        if is_doubles:
            rA = sum(get_rating(p, day)[0] for p in p1)
            rB = sum(get_rating(p, day)[0] for p in p2)
        else:
            rA, uA = get_rating(p1, day)
            rB, uB = get_rating(p2, day)
            
        prob = safe_prob(rA, rB)
        raw_preds.append(prob)
        actuals.append(1 if winner == 'A' else 0)
        
    raw_preds = np.array(raw_preds)
    actuals = np.array(actuals)
    
    if use_calibration:
        print("Applying Isotonic Regression calibration...")
        calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds='clip')
        calibrated_preds = calibrator.fit_transform(raw_preds, actuals)
        final_preds = calibrated_preds
    else:
        final_preds = raw_preds
        
    # Store predictions
    print("Storing predictions in prediction_log...")
    cursor = test_conn.cursor()
    cursor.execute("DELETE FROM prediction_log WHERE run_id = ?", (run_id,))
    
    pred_data = []
    for i in range(len(games)):
        pred_data.append((run_id, event, int(actuals[i]), float(final_preds[i])))
        
    cursor.executemany("""
        INSERT INTO prediction_log (run_id, event, actual, predicted_prob)
        VALUES (?, ?, ?, ?)
    """, pred_data)
    test_conn.commit()

    store_whr_results(test_conn, run_id, event, individual_ratings, start_date, w2, iterations)
    print(f"--- Finished WHR run for event: {event} ---")

def main():
    CORE_DB_PATH = "bwf_data_2008-now__v1.sqlite"
    TEST_DB_PATH = "elo_ratings.sqlite"
    RUN_ID_PREFIX = f"whr_calibrated_{datetime.now().strftime('%Y%m%d%H%M')}"
    
    w2_map = {
        "MD": 4.50,
        "MS": 4.50,
        "WD": 5.00,
        "WS": 5.00,
        "XD": 4.50
    }
    
    core_conn = None
    test_conn = None
    try:
        core_conn = sqlite3.connect(CORE_DB_PATH)
        test_conn = sqlite3.connect(TEST_DB_PATH)

        init_whr_tables(test_conn)

        events_to_run = ["MS", "WS", "MD", "WD", "XD"]
        for event in events_to_run:
            w2 = w2_map.get(event, 1.0)
            run_whr_for_event(core_conn, test_conn, RUN_ID_PREFIX, w2, event, use_calibration=True)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if core_conn:
            core_conn.close()
        if test_conn:
            test_conn.close()
        print("\nAll processes finished. Database connections closed.")

    # --- Rebuild API Cache ---
    if os.environ.get("SKIP_CACHE_REBUILD") != "1":
        try:
            print("\nRebuilding API cache...")
            import sys
            base_dir = os.path.dirname(os.path.abspath(__file__))
            backend_dir = os.path.join(base_dir, "web", "backend")
            sys.path.append(backend_dir)
            from build_cache import build_cache
            build_cache()
            print("API cache rebuilt successfully!")
        except Exception as cache_err:
            print(f"Warning: Failed to rebuild API cache: {cache_err}")
    else:
        print("\nSkipping cache rebuild as requested by the pipeline orchestrator.")

if __name__ == "__main__":
    main()