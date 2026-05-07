import sqlite3
from tabulate import tabulate  # pip install tabulate (optional but nice)

# --- CHOOSE YOUR DATABASE ---
# Use 'bwf_data_2008-now__v1.sqlite' to query raw match and tournament data.
# Use 'elo_ratings.sqlite' to query Elo ratings, predictions, and run results.
DB_PATH = "elo_ratings.sqlite"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row  # so columns have names

def q(sql):
    cur = conn.execute(sql)
    rows = cur.fetchall()
    if not rows:
        print("✓ No rows returned")
        return
    print(tabulate([tuple(r) for r in rows], headers=rows[0].keys()))


# q("""
#     SELECT
#         match_id,
#         event,
#         predicted_prob,
#         actual,
#         pre_rating_p1,
#         pre_rating_p2
#     FROM prediction_log
#     WHERE run_id = (SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1)
#     ORDER BY match_id ASC
#     LIMIT 10;
# """)


# q("""
#     ATTACH DATABASE 'bwf_data_2008-now__v1.sqlite' AS core;

#     SELECT
#         p.name_display,
#         r.final_rating,
#         u.final_uncertainty,
#         r.match_count,
#         r.peak_rating,
#         r.final_rating_date
#     FROM final_player_ratings r
#     JOIN final_player_uncertainty u ON r.run_id = u.run_id AND r.event = u.event AND r.player_id = u.player_id
#     JOIN core.players p ON r.player_id = p.player_id
#     WHERE r.run_id = (SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1)
#       AND r.event = 'MS' -- Change event as needed (WS, MD, WD, XD)
#     ORDER BY r.final_rating DESC
#     LIMIT 20;
# """)

# q("""
#     ATTACH DATABASE 'bwf_data_2008-now__v1.sqlite' AS core;

#     SELECT
#         p.name_display,
#         h.rating_date,
#         h.rating
#     FROM rating_history h
#     JOIN core.players p ON h.player_id = p.player_id
#     WHERE h.run_id = (SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1)
#       AND h.event = 'MS'
#       AND p.name_display LIKE '%AXELSEN%' -- Look for a specific player
#     ORDER BY h.rating_date DESC
#     LIMIT 10;
# """)

# q("""
#     ATTACH DATABASE 'bwf_data_2008-now__v1.sqlite' AS core;

#     SELECT
#         p1.name_display || ' + ' || p2.name_display AS pair_name,
#         psc.synergy,
#         psc.synergy_uncertainty,
#         psc.last_updated
#     FROM pair_synergy_current psc
#     JOIN core.players p1 ON psc.player1_id = p1.player_id
#     JOIN core.players p2 ON psc.player2_id = p2.player_id
#     WHERE psc.run_id = (SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1)
#       AND psc.event = 'MD' -- Or WD, XD
#     ORDER BY psc.synergy DESC
#     LIMIT 10;
# """)


# --- Compare the performance of all your model runs ---
# This helps you find which parameters (K, beta, etc.) worked best.
# Lower log_loss and brier scores are better.
# q("""
#     SELECT
#         run_id,
#         K,
#         beta,
#         cap_K_mult,
#         u_growth,
#         log_loss,
#         brier,
#         ece,
#         accuracy,
#         empirical_entropy_log_loss,
#         favorite_gap,
#         mean_prediction,
#         empirical_rate,
#         prediction_bias,
#         mean_uncertainty,
#         median_uncertainty,
#         std_uncertainty,
#         pct_u_max,
#         pct_u_min,
#         n_matches
#     FROM run_metadata
#     WHERE log_loss IS NOT NULL
#     ORDER BY log_loss ASC;
# """)

# --- Get the rating history for a specific player ---
# Useful for seeing how a player's rating has evolved over time.
# q("""
#     SELECT
#         rating_date,
#         rating
#     FROM rating_history
#     WHERE player_id = '52786' -- Viktor AXELSEN
#       AND event = 'MS'
#       AND run_id = (SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1)
#     ORDER BY rating_date ASC;
# """)

# --- Get Best Run_ID for Each Event ---
# This query identifies the run_id that achieved the lowest log_loss
# for each individual event (MS, WS, MD, WD, XD).
q("""
    SELECT
        event,
        run_id,
        log_loss,
        brier,
        ece,
        n_matches
    FROM run_event_metrics
    WHERE (event, log_loss) IN (
        SELECT
            event,
            MIN(log_loss)
        FROM run_event_metrics
        WHERE log_loss IS NOT NULL
        GROUP BY event
    )
    ORDER BY event;
""")


# ==============================================================================
# EXAMPLES FOR 'bwf_data_2008-now__v1.sqlite' (Raw Match Data)
# ==============================================================================

# --- Find a specific player by name ---
# q("""
#     SELECT * FROM players WHERE name_display LIKE '%Ginting%';
# """)

# ==============================================================================
# EXAMPLES FOR CHECKING INGESTION HEALTH (in 'bwf_data_2008-now__v1.sqlite')
# ==============================================================================
# To run these, make sure DB_PATH is set to your main data database.

# --- Get a high-level summary of all ingestion errors ---
# This is the best first step to see the overall health of your data.
# q("""
#     SELECT
#         SUM(unresolved_players) as unresolved_player_errors,
#        SUM(has_player_conflict) as player_id_conflict_errors,
#         SUM(invalid_scores) as invalid_score_errors,
#         SUM(winner_mismatch) as winner_mismatch_errors,
#         SUM(invalid_participants) as invalid_participant_errors,
#         SUM(retired_or_walkover) as retired_or_walkovers,
#         COUNT(*) as total_matches_logged
#     FROM ingestion_report;
# """)
