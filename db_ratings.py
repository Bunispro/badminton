import sqlite3


def init_rating_table(conn):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rating_history (
            run_id TEXT,
            player_id TEXT,
            event TEXT,
            rating_date TEXT,
            rating REAL,
            rd REAL,
            volatility REAL,
            PRIMARY KEY (run_id, player_id, event, rating_date)
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
            synergy_uncertainty REAL,
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
            synergy_uncertainty REAL,
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
            D_map TEXT,
            Ks REAL,
            beta REAL,            
            uncertainty_decay REAL,
            u_growth REAL,
            Ks_beta REAL,
            cap_K_mult REAL,
            su_decay REAL,
            su_growth REAL,
            rating_decay_per_year REAL,
            decay_grace_days INTEGER,

            -- evaluation metrics
            kl_gap REAL,
            log_loss REAL,
            brier REAL,
            ece REAL,
            accuracy REAL,
            favorite_gap REAL,
            mean_prediction REAL,
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
        CREATE TABLE IF NOT EXISTS run_event_metrics (
            run_id TEXT,
            event TEXT,
            log_loss REAL,
            brier REAL,
            ece REAL,
            n_matches INTEGER,
            PRIMARY KEY (run_id, event),
            FOREIGN KEY (run_id) REFERENCES run_metadata(run_id)
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_run_event_metrics_run_id ON run_event_metrics(run_id);
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