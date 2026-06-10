import sqlite3
import traceback
from config import CORE_DB_PATH, RATINGS_DB_PATH

def get_ratings_db():
    """Dependency to get connection to the ratings database."""
    conn = sqlite3.connect(RATINGS_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_core_db():
    """Dependency to get connection to the core database."""
    conn = sqlite3.connect(CORE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db_indices():
    """Initialize necessary tables and indices for performance."""
    print("Checking database indices...")
    try:
        with sqlite3.connect(RATINGS_DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS whr_ranking_history(
                    run_id TEXT,
                    event TEXT,
                    rating_date TEXT,
                    player_id TEXT,
                    rank INTEGER
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_whr_ranking_lookup ON whr_ranking_history (run_id, event, player_id, rating_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_whr_player_date ON whr_rating_history (run_id, event, player_id, rating_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_elo_player_date ON rating_history (run_id, event, player_id, rating_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_elo_run_event_date ON rating_history (run_id, event, rating_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_whr_run_event_date ON whr_rating_history (run_id, event, rating_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_whr_player_rating ON whr_rating_history (run_id, event, player_id, rating DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_elo_player_rating ON rating_history (run_id, event, player_id, rating DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_whr_rating_rank ON whr_rating_history (run_id, event, rating_date, rating DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_elo_rating_rank ON rating_history (run_id, event, rating_date, rating DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_synergy_player1 ON pair_synergy_current (player1_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_synergy_player2 ON pair_synergy_current (player2_id)")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS player_views(
                    player_id TEXT PRIMARY KEY,
                    view_count INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_cache(
                    cache_key TEXT PRIMARY KEY,
                    cache_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS bwf_prediction_log (
                    match_id TEXT PRIMARY KEY,
                    points_p1 INTEGER,
                    points_p2 INTEGER,
                    predicted_prob_ratio REAL,
                    predicted_prob_diff REAL,
                    actual INTEGER
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_bwf_pred_match ON bwf_prediction_log(match_id)")

        with sqlite3.connect(CORE_DB_PATH) as conn:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_match_participants_player_id ON match_participants(player_id)")
        print("Indices verified.")

    except Exception as e:
        traceback.print_exc()
        print(f"Error during lifespan startup: {e}")
