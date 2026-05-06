import sqlite3

def init_whr_tables(conn):
    """
    Initializes tables specifically for storing Whole-History Rating results.
    """
    cursor = conn.cursor()

    # Table to store the daily ratings for each player or pair (entity).
    # This is the main output of the WHR model.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whr_rating_history (
            run_id TEXT,
            entity_id TEXT, -- Can be a player_id (e.g., '52786') or a pair_id (e.g., '123+456')
            event TEXT,
            rating_date TEXT,
            rating REAL,
            PRIMARY KEY (run_id, entity_id, event, rating_date)
        );
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_whr_history_run_event_date
        ON whr_rating_history(run_id, event, rating_date);
    """)

    # A simplified metadata table for WHR runs. We can add evaluation
    # metrics here later, similar to the Elo run_metadata table.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whr_run_metadata (
            run_id TEXT PRIMARY KEY,
            w2 REAL,
            iterations INTEGER,
            notes TEXT,
            created_at TEXT
        );
    """)

    print("WHR-specific tables initialized successfully.")
    conn.commit()