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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whr_rating_history (
            run_id TEXT,
            player_id TEXT,
            event TEXT,
            rating_date TEXT,
            rating REAL,
            uncertainty REAL,
            PRIMARY KEY (run_id, player_id, event, rating_date)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whr_run_metadata (
            run_id TEXT PRIMARY KEY,
            w2 REAL,
            iterations INTEGER,
            notes TEXT,
            created_at TEXT
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ranking_history (
            run_id TEXT,
            event TEXT,
            rating_date TEXT,
            player_id TEXT,
            rank INTEGER,
            PRIMARY KEY (run_id, event, rating_date, player_id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            player_id TEXT,
            event TEXT,
            model TEXT,
            mode TEXT,
            snapshot_date TEXT,
            winrate REAL,
            global_rank INTEGER,
            rating REAL,
            rating_date TEXT,
            rank_at_peak INTEGER,
            last_played_date TEXT,
            total_matches INTEGER,
            country_code TEXT,
            change_1m REAL,
            change_3m REAL,
            change_6m REAL,
            PRIMARY KEY (player_id, event, model, mode, snapshot_date)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_cache (
            cache_key TEXT PRIMARY KEY,
            cache_value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_views (
            player_id TEXT PRIMARY KEY,
            view_count INTEGER DEFAULT 0
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whr_ranking_history (
            run_id TEXT,
            event TEXT,
            rating_date TEXT,
            player_id TEXT,
            rank INTEGER,
            PRIMARY KEY (run_id, event, rating_date, player_id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bwf_historical_rankings (
            rank_date TEXT NOT NULL,
            week INTEGER NOT NULL,
            event TEXT NOT NULL,
            rank INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            player_name TEXT,
            country TEXT,
            points INTEGER,
            PRIMARY KEY (rank_date, event, rank, player_id)
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bwf_hist_player ON bwf_historical_rankings(player_id, rank_date);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bwf_hist_date ON bwf_historical_rankings(rank_date, event);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ranking_history_player ON ranking_history(player_id, event);
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_whr_ranking_history_player ON whr_ranking_history(player_id, event);
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ml_models (
            model_name TEXT PRIMARY KEY,
            model_bytes BLOB
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ml_match_features (
            match_id TEXT PRIMARY KEY,
            match_date TEXT,
            event TEXT,
            winner_side_1 INTEGER,
            duration REAL,
            tier TEXT,
            round TEXT,
            elo_a REAL,
            elo_b REAL,
            elo_diff REAL,
            whr_a REAL,
            whr_b REAL,
            whr_diff REAL,
            synergy_a REAL,
            synergy_b REAL,
            avg_rest_a REAL,
            avg_rest_b REAL,
            rest_diff REAL,
            h2h_rate REAL
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS xgb_prediction_log (
            match_id TEXT PRIMARY KEY,
            predicted_prob REAL,
            actual INTEGER
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bwf_prediction_log (
            match_id TEXT PRIMARY KEY,
            points_p1 INTEGER,
            points_p2 INTEGER,
            predicted_prob_ratio REAL,
            predicted_prob_diff REAL,
            actual INTEGER
        );
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bwf_pred_match ON bwf_prediction_log(match_id);
    """)

    conn.commit()