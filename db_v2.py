import sqlite3

db_path = "bwf_data_2008-now.sqlite"
testing_db_path = "testing_bwf.sqlite"


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
            numeric_id TEXT,
            name TEXT NOT NULL,
            year INTEGER ,
            tier TEXT,
            source TEXT,
            start_date TEXT,
            end_date TEXT,
            location TEXT,
            country TEXT,
            url TEXT,
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
            player_name TEXT,
            normalized_name TEXT,
            timestamp TEXT
        );
    """)

    conn.commit()
    return conn

def init_rating_table(conn):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rating_history (
            player_id TEXT,
            event TEXT,
            rating_date TEXT,
            rating REAL,
            rd REAL,
            volatility REAL,
            PRIMARY KEY (player_id, event, rating_date)
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_rating_event_date
        ON rating_history(event, rating_date);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_rating_player_id
        ON rating_history(player_id);
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prediction_log (
            run_id TEXT,
            match_id TEXT,
            event TEXT,
            predicted_prob REAL,
            actual INTEGER,
            pre_rating_p1 REAL,
            pre_rating_p2 REAL,
            uncertainty_mean REAL,
            D_eff REAL,
            K_eff REAL,
            PRIMARY KEY (run_id, match_id)
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_prediction_event
        ON prediction_log(event);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_prediction_run
        ON prediction_log(run_id);
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pair_synergy_current (
            run_id TEXT,
            event TEXT,
            player1_id TEXT,
            player2_id TEXT,
            synergy REAL,
            last_updated TEXT,
            PRIMARY KEY (run_id, event, player1_id, player2_id)
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pair_event
        ON pair_synergy_current(event);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pair_run
        ON pair_synergy_current(run_id);
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pair_synergy_history (
            run_id TEXT,
            event TEXT,
            player1_id TEXT,
            player2_id TEXT,
            snapshot_date TEXT,
            synergy REAL,
            PRIMARY KEY (run_id, event, player1_id, player2_id, snapshot_date)
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idk_pair_history_run
        ON pair_synergy_history(run_id);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idk_pair_history_event
        ON pair_synergy_history(event);
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS final_player_ratings (
            run_id TEXT,
            event TEXT,
            player_id TEXT,
            final_rating REAL,
            final_rating_date TEXT,
            peak_rating REAL,
            peak_rating_date TEXT,
            match_count INTEGER,
            PRIMARY KEY (run_id, event, player_id)
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_final_player_run_event
        ON final_player_ratings(run_id, event);
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS run_metadata (
            run_id TEXT PRIMARY KEY,

            -- model config
            mode TEXT,
            split_date TEXT,
            K REAL,
            D REAL,
            Ks REAL,
            alpha REAL,
            beta REAL,
            decay_rate REAL,
            uncertainty_decay REAL,
            u_growth REAL,

            -- evaluation metrics
            kl_gap REAL,
            log_loss REAL,
            brier REAL,
            ece REAL,
            accuracy REAL,
            favorite_gap REAL,
            mean_prediction REAL,
            empirical_rate REAL,
            prediction_bias REAL,
            mean_uncertainty REAL,
            median_uncertainty REAL,
            std_uncertainty REAL,
            pct_u_max REAL,
            pct_u_min REAL,
            n_matches INTEGER,
            notes TEXT,
            created_at TEXT
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idk_run_metadata_kl_gap
        ON run_metadata(kl_gap);
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS final_player_uncertainty (
            run_id TEXT,
            event TEXT,
            player_id TEXT,
            final_uncertainty REAL,
            final_date TEXT,
            PRIMARY KEY (run_id, event, player_id)
        );
    """)


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uncertainty_history (
            run_id TEXT,
            event TEXT,
            player_id TEXT,
            snapshot_date TEXT,
            uncertainty REAL,
            PRIMARY KEY (run_id, event, player_id, snapshot_date)
        );
    """)
    conn.commit()
