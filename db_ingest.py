import sqlite3

db_path = "bwf_data_2008-now.sqlite"
testing_db_path = "elo_ratings.sqlite"


def init_db(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    # Matches
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            tournament_id TEXT NOT NULL,
            event_raw TEXT NOT NULL,
            event_canon TEXT NOT NULL,
            round TEXT,
            court TEXT,
            match_date TEXT NOT NULL,
            score TEXT,
            is_valid_for_rating BOOLEAN,
            winner_side INTEGER,
            raw_hash TEXT,
            FOREIGN KEY (tournament_id) REFERENCES tournaments(tournament_id)
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_matches_date 
        ON matches(match_date);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_matches_event_date 
        ON matches(event_canon, match_date);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_matches_tournament_id
        ON matches(tournament_id);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_matches_is_valid_for_rating
        ON matches(is_valid_for_rating);
    """)


    # Players
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id TEXT PRIMARY KEY,
            name_display TEXT,
            name_normalized TEXT,
            country_code TEXT
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_players_normalized
        ON players(name_normalized);
    """)

    # Player Aliases
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_aliases (
            player_id TEXT,
            alias_normalized TEXT,
            PRIMARY KEY (player_id, alias_normalized),
            FOREIGN KEY (player_id) REFERENCES players(player_id)
        );
    """)

    # Player id
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_id_mapping (
            old_id TEXT PRIMARY KEY,
            canonical_id TEXT,
            FOREIGN KEY (canonical_id) REFERENCES players(player_id)
        );
    """)
    
    # Tournaments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            tournament_id TEXT PRIMARY KEY,
            numeric_id TEXT UNIQUE,
            name TEXT NOT NULL,
            year INTEGER ,
            tier TEXT,
            source TEXT,
            start_date TEXT,
            end_date TEXT,
            location TEXT,
            country TEXT,
            url TEXT UNIQUE,
            is_continental BOOLEAN,
            prize_money INTEGER
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_tournament_year
        ON tournaments(year);
    """)

    # Match Participants
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_participants (
            match_id TEXT,
            side INTEGER CHECK (side IN (1, 2)),
            player_id TEXT,
            PRIMARY KEY (match_id, side, player_id),
            FOREIGN KEY (match_id) REFERENCES matches(match_id),
            FOREIGN KEY (player_id) REFERENCES players(player_id)
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_participants_player
        ON match_participants(player_id);
    """)

    # Ingestion Report
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_report (
            match_id TEXT,
            unresolved_players BOOLEAN,
            invalid_scores BOOLEAN,
            date_fallback BOOLEAN,
            winner_mismatch BOOLEAN,
            has_player_conflict BOOLEAN, -- New column to distinguish from unresolved_players
            retired_or_walkover BOOLEAN,
            invalid_participants BOOLEAN,
            is_team_match BOOLEAN,
            timestamp TEXT,
            PRIMARY KEY (match_id, timestamp)
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ingestion_timestamp
        ON ingestion_report(timestamp);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ingestion_match_id
        ON ingestion_report(match_id);
    """)


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS unresolved_players_log (
            tournament_id TEXT,
            match_id TEXT,
            normalized_name TEXT,
            timestamp TEXT
        );
    """)

    conn.commit()
    return conn