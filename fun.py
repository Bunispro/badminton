import sqlite3
from tabulate import tabulate  # pip install tabulate (optional but nice)

# --- CHOOSE YOUR DATABASE ---
# Use 'bwf_data_2008-now__v1.sqlite' to query raw match and tournament data.
# Use 'testing_bwf.sqlite' to query Elo ratings, predictions, and run results.
DB_PATH = "testing_bwf.sqlite"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row  # so columns have names

def q(sql):
    cur = conn.execute(sql)
    rows = cur.fetchall()
    if not rows:
        print("✓ No rows returned")
        return
    print(tabulate([tuple(r) for r in rows], headers=rows[0].keys()))


# ==============================================================================
# EXAMPLES FOR 'testing_bwf.sqlite' (Elo Ratings & Results)
# ==============================================================================


# --- Get Top 20 MS Players from the latest run ---
# This is great for seeing the final rankings.
# You can change 'MS' to 'WS', 'MD', 'WD', or 'XD'.
q("""
    SELECT
        p.name_display,
        r.final_rating,
        u.final_uncertainty,
        r.match_count,
        r.peak_rating,
        r.final_rating_date
    FROM final_player_ratings r
    JOIN final_player_uncertainty u ON r.run_id = u.run_id AND r.event = u.event AND r.player_id = u.player_id
    JOIN 'bwf_data_2008-now__v1.sqlite'.players p ON r.player_id = p.player_id
    WHERE r.run_id = (SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1)
      AND r.event = 'MS'
    ORDER BY r.final_rating DESC
    LIMIT 20;
""")

# --- Compare the performance of all your model runs ---
# This helps you find which parameters (K, beta, etc.) worked best.
# Lower log_loss and brier scores are better.
# q("""
#     SELECT
#         run_id,
#         K,
#         beta,
#         cap_K_mult,
#         log_loss,
#         brier,
#         ece,
#         accuracy,
#         n_matches
#     FROM run_metadata
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


# ==============================================================================
# EXAMPLES FOR 'bwf_data_2008-now__v1.sqlite' (Raw Match Data)
# ==============================================================================

# --- Find a specific player by name ---
# q("""
#     SELECT * FROM players WHERE name_display LIKE '%Ginting%';
# """)

# --- Check the ingestion report for a specific tournament ---
# This helps you see if there were any issues when you imported the data.
# NOTE: To run this query, set DB_PATH to "bwf_data_2008-now__v1.sqlite"
# q("""
#     SELECT
#         r.*
#     FROM ingestion_report r
#     JOIN matches m ON r.match_id = m.match_id
#     WHERE m.tournament_id = '4709' -- PERODUA Malaysia Masters 2023
#       AND (r.unresolved_players = 1 OR r.invalid_scores = 1 OR r.winner_mismatch = 1);
# """)

# --- Count how many valid matches were ingested per year ---
# q("""
#     SELECT strftime('%Y', match_date) as year, COUNT(*) as num_matches
#     FROM matches
#     WHERE is_valid_for_rating = 1
#     GROUP BY year
#     ORDER BY year ASC;
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
#         SUM(invalid_scores) as invalid_score_errors,
#         SUM(winner_mismatch) as winner_mismatch_errors,
#         SUM(invalid_participants) as invalid_participant_errors,
#         SUM(retired_or_walkover) as retired_or_walkovers,
#         COUNT(*) as total_matches_logged
#     FROM ingestion_report;
# """)

# --- Find all matches with any critical error, most recent first ---
# This helps you find specific matches to investigate.
# q("""
#     SELECT
#         r.match_id,
#         m.tournament_id,
#         t.name as tournament_name,
#         m.match_date,
#         r.unresolved_players,
#         r.invalid_scores,
#         r.winner_mismatch,
#         r.invalid_participants
#     FROM ingestion_report r
#     JOIN matches m ON r.match_id = m.match_id
#     JOIN tournaments t ON m.tournament_id = t.tournament_id
#     WHERE r.unresolved_players = 1
#        OR r.invalid_scores = 1
#        OR r.winner_mismatch = 1
#        OR r.invalid_participants = 1
#     ORDER BY m.match_date DESC
#     LIMIT 50;
# """)
