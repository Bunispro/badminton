import sqlite3
import math
from datetime import datetime, date, timedelta

# We will use the 'whr' library. You'll need to install it:
# pip install whr
from whr import WholeHistoryRating

# Import the new schema definition
from db_whr import init_whr_tables

def fetch_matches_for_whr(core_conn, event_filter):
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
            GROUP_CONCAT(CASE WHEN mp.side = 2 THEN mp.player_id END) AS p2_ids
        FROM matches m
        JOIN match_participants mp ON mp.match_id = m.match_id
        WHERE m.event_canon = ? AND m.is_valid_for_rating = 1
        GROUP BY m.match_id, m.match_date, m.winner_side
        HAVING COUNT(CASE WHEN mp.side = 1 THEN 1 END) > 0
           AND COUNT(CASE WHEN mp.side = 2 THEN 1 END) > 0
        ORDER BY m.match_date ASC;
    """
    cursor.execute(query, (event_filter,))

    games = []
    all_entities = set() # Using a set for efficient addition of unique players/pairs

    is_doubles = event_filter in ["MD", "WD", "XD"]

    for date_str, winner_side, p1_ids_str, p2_ids_str in cursor:
        # 3. Calculate day index
        current_date = date.fromisoformat(date_str)
        day_index = (current_date - start_date).days

        # 4. Create canonical keys for players/pairs
        if is_doubles:
            # For doubles, sort player IDs to create a consistent pair key
            p1_key = "+".join(sorted(p1_ids_str.split(',')))
            p2_key = "+".join(sorted(p2_ids_str.split(',')))
        else:
            # For singles, the key is just the player ID
            p1_key = p1_ids_str
            p2_key = p2_ids_str
        
        # Add keys to our set of all entities
        all_entities.add(p1_key)
        all_entities.add(p2_key)

        # 5. Determine winner and loser and format for WHR library
        if winner_side == 1:
            winner_key, loser_key = p1_key, p2_key
        else:
            winner_key, loser_key = p2_key, p1_key

        games.append([winner_key, loser_key, day_index])

    print(f"Found {len(games)} games starting from {start_date.isoformat()}.")
    return games, all_entities, start_date


def store_whr_results(test_conn, run_id, event, whr_system, start_date):
    """
    Takes the converged ratings from the WHR system and saves them to the database.
    WHR provides a rating for every player for every day of the entire history.
    """
    print("Storing WHR results in the database...")
    cursor = test_conn.cursor()

    # Clear old results for this run_id and event to ensure a clean slate
    cursor.execute("DELETE FROM whr_rating_history WHERE run_id = ? AND event = ?", (run_id, event))

    history_data = []
    num_days = whr_system.days[-1] # Get the last day index from the model

    for day_index in range(num_days + 1):
        current_date = start_date + timedelta(days=day_index)
        rating_date_str = current_date.isoformat()
        
        # Get ratings for all players on this specific day
        daily_ratings = whr_system.ratings_for_day(day_index)

        for entity_id, (rating, uncertainty) in daily_ratings.items():
            # Convert raw WHR rating (log-odds) to a more intuitive Elo-like scale.
            elo_like_rating = rating * 400 / math.log(10) + 1500

            history_data.append((
                run_id,
                entity_id,
                event,
                rating_date_str,
                elo_like_rating
            ))

        # Bulk insert periodically to be memory-efficient and fast
        if len(history_data) >= 50000:
            cursor.executemany("""
                INSERT INTO whr_rating_history (run_id, entity_id, event, rating_date, rating)
                VALUES (?, ?, ?, ?, ?)
            """, history_data)
            history_data = []
            print(f"  ...inserted batch up to day {day_index}")

    # Insert any remaining data
    if history_data:
        cursor.executemany("""
            INSERT INTO whr_rating_history (run_id, entity_id, event, rating_date, rating)
            VALUES (?, ?, ?, ?, ?)
        """, history_data)

    # Log the metadata for this run
    cursor.execute("""
        INSERT INTO whr_run_metadata (run_id, w2, iterations, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            w2=excluded.w2,
            iterations=excluded.iterations
    """, (run_id, whr_system.w2, whr_system.iteration_count, datetime.now().isoformat()))

    test_conn.commit()
    print(f"Successfully stored {day_index + 1} days of rating history.")


def run_whr_for_event(core_conn, test_conn, run_id_prefix, w2, event):
    """
    Orchestrates the entire WHR process for a single event (e.g., 'MS').
    """
    run_id = f"{run_id_prefix}_{event}"
    print(f"\n--- Starting WHR run for event: {event} (Run ID: {run_id}) ---")

    # 1. Fetch and format data from the database
    # We expect this to return the games list, a way to map names back to IDs, and the first date.
    games, all_entities, start_date = fetch_matches_for_whr(core_conn, event)
    if not games:
        print(f"No games found for event {event}. Skipping.")
        return

    print(f"Processing {len(games)} games and {len(all_entities)} unique entities.")

    # 2. Initialize and run the WHR model
    print(f"Initializing WHR model with w2 (skill drift) = {w2}...")
    whr_system = WholeHistoryRating(w2=w2)
    whr_system.create_games(games)

    print("Running WHR iterations... (this may take a while)")
    # The library handles the iterative solving of the sparse matrix.
    # We just need to call the iterate method.
    whr_system.iterate(50) # 50 iterations is a reasonable default
    print("WHR calculation complete.")

    # 3. Store the results back into our ratings database
    store_whr_results(test_conn, run_id, event, whr_system, start_date)
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
    W2_PARAM = 0.05 

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