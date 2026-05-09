import sqlite3
import math
from datetime import datetime, date, timedelta

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
        # Exponential curve starting from 6 point gap
        return min(1.2, mov_base_mult * (mov_growth_rate ** (point_gap - 5)))

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
    try:
        cursor.execute("ALTER TABLE whr_rating_history ADD COLUMN uncertainty REAL")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whr_run_metadata (
            run_id TEXT PRIMARY KEY,
            w2 REAL,
            iterations INTEGER,
            created_at TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whr_run_event ON whr_rating_history (run_id, event)")
    conn.commit()

def fetch_matches_for_whr(core_conn, event_filter, limit=None):
    """
    Fetches all valid matches from the database and formats them for the WHR library.
    WHR needs a list of games, where each game contains the winner's name,
    the loser's name, and the day number (as an integer from the start of the dataset).
    """
    print(f"Fetching matches for event: {event_filter}...")
    cursor = core_conn.cursor()

    # 1. Find the first date in the entire valid dataset to anchor our timeline
    cursor.execute("SELECT MIN(match_date) FROM matches WHERE is_valid_for_rating = 1")
    min_date_str = cursor.fetchone()[0]
    if not min_date_str:
        return [], set(), None
    start_date = date.fromisoformat(min_date_str)

    # 2. Fetch all matches for the specified event
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
    all_entities = set() # Using a set for efficient addition of unique players/pairs

    is_doubles = event_filter in ["MD", "WD", "XD"]

    for date_str, winner_side, p1_ids_str, p2_ids_str, score in cursor:
        # 3. Calculate day index
        current_date = date.fromisoformat(date_str)
        day_index = (current_date - start_date).days

        # 4. Create canonical keys for players/pairs
        if is_doubles:
            # For doubles, split into lists of strings
            p1_key = p1_ids_str.split(',')
            p2_key = p2_ids_str.split(',')
            for p in p1_key + p2_key:
                all_entities.add(p)
        else:
            # For singles, the key is just the player ID string
            p1_key = p1_ids_str
            p2_key = p2_ids_str
            all_entities.add(p1_key)
            all_entities.add(p2_key)

        # 5. Format for WHR library
        winner = 'A' if winner_side == 1 else 'B'
        weight = get_mov_multiplier(score, event_filter)
        games.append([p1_key, p2_key, winner, day_index, weight])

    print(f"Found {len(games)} games starting from {start_date.isoformat()}.")
    return games, all_entities, start_date


def store_whr_results(test_conn, run_id, event, whr_system, start_date, w2, iterations):
    """
    Takes the converged ratings from the WHR system and saves them to the database.
    """
    print("Storing WHR results in the database...")
    cursor = test_conn.cursor()

    # Clear old results for this run_id and event to ensure a clean slate
    cursor.execute("DELETE FROM whr_rating_history WHERE run_id = ? AND event = ?", (run_id, event))

    history_data = []

    for player_name in whr_system.players.keys():
        ratings = whr_system.ratings_for_player(player_name)
        for rating_info in ratings:
            time_step = rating_info[0]
            elo_rating = rating_info[1]
            uncertainty = rating_info[2]
            
            current_date = start_date + timedelta(days=time_step)
            rating_date_str = current_date.isoformat()
            
            history_data.append((
                run_id,
                player_name,
                event,
                rating_date_str,
                elo_rating,
                uncertainty
            ))

    # Bulk insert periodically to be memory-efficient and fast
    batch_size = 50000
    for i in range(0, len(history_data), batch_size):
        batch = history_data[i:i+batch_size]
        cursor.executemany("""
            INSERT INTO whr_rating_history (run_id, player_id, event, rating_date, rating, uncertainty)
            VALUES (?, ?, ?, ?, ?, ?)
        """, batch)
        print(f"  ...inserted batch of {len(batch)} records")

    # Log the metadata for this run
    cursor.execute("""
        INSERT INTO whr_run_metadata (run_id, w2, iterations, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            w2=excluded.w2,
            iterations=excluded.iterations
    """, (run_id, w2, iterations, datetime.now().isoformat()))

    test_conn.commit()
    print(f"Successfully stored rating history for event {event}.")


def run_whr_for_event(core_conn, test_conn, run_id_prefix, w2, event, limit=None):
    """
    Orchestrates the entire WHR process for a single event (e.g., 'MS').
    """
    run_id = f"{run_id_prefix}_{event}"
    print(f"\n--- Starting WHR run for event: {event} (Run ID: {run_id}) ---")

    # 1. Fetch and format data from the database
    # We expect this to return the games list, a way to map names back to IDs, and the first date.
    games, all_entities, start_date = fetch_matches_for_whr(core_conn, event, limit)
    if not games:
        print(f"No games found for event {event}. Skipping.")
        return

    print(f"Processing {len(games)} games and {len(all_entities)} unique entities.")

    # 2. Initialize and run the WHR model
    print(f"Initializing WHR model with w2 (skill drift) = {w2}...")
    whr_system = whr.Base(config={'w2': w2})
    for g in games:
        whr_system.create_game(side_a=g[0], side_b=g[1], winner=g[2], time_step=g[3], handicap=0.0, weight=g[4])

    print("Running WHR iterations... (this may take a while)")
    iterations = 50
    whr_system.iterate(iterations)
    print("WHR calculation complete.")

    # 3. Store the results back into our ratings database
    store_whr_results(test_conn, run_id, event, whr_system, start_date, w2, iterations)
    print(f"--- Finished WHR run for event: {event} ---")


def main():
    """
    Main entry point to run the WHR analysis for all events.
    """
    # --- Configuration ---
    CORE_DB_PATH = "bwf_data_2008-now__v1.sqlite"
    TEST_DB_PATH = "elo_ratings.sqlite"
    RUN_ID_PREFIX = f"whr_{datetime.now().strftime('%Y%m%d%H%M')}"
    
    # This is the main hyperparameter for WHR, controlling skill drift over time.
    # Locked in after grid search (capped at 2.0 to avoid overfitting)
    W2_PARAM = 1.0

    # --- Database Connections ---
    core_conn = None
    test_conn = None
    try:
        core_conn = sqlite3.connect(CORE_DB_PATH)
        test_conn = sqlite3.connect(TEST_DB_PATH)

        # Ensure the new WHR-specific tables exist
        init_whr_tables(test_conn)

        # WHR is run separately for each event, just like our Elo system.
        events_to_run = ["MS", "WS", "MD", "WD", "XD"]
        for event in events_to_run:
            run_whr_for_event(core_conn, test_conn, RUN_ID_PREFIX, W2_PARAM, event)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if core_conn:
            core_conn.close()
        if test_conn:
            test_conn.close()
        print("\nAll processes finished. Database connections closed.")


if __name__ == "__main__":
    main()