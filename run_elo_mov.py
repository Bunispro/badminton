import sqlite3
import json
from datetime import datetime

from elo_engine_mov import run_elo
from db_ratings import init_rating_table

# --- 1. Define Database Paths ---
CORE_DB_PATH = "bwf_data_2008-now__v1.sqlite"
TEST_DB_PATH = "elo_ratings.sqlite"

# --- 2. Define the FINAL, per-discipline configuration ---
# This is built from your best results from the optimization phases.
final_config = {
    "split_date": "2018-01-01", # A balanced choice from your results
    "base_rating": 1000,
    "store_history": True,
    "event_params": {
        # From Phase 3: h_opt3__K=65_b=1.59_ug=0.059_D=378_rd=0.02_gd=128...
        "MS": {
            "K": 65, "beta": 1.59, "u_growth": 0.059, "D": 378,
            "rating_decay_per_year": 0.025, "decay_grace_days": 128,
            "cap_K_mult": 3.0, "Ks": 25, "uncertainty_decay": 0.95, "Ks_beta": 0.85, "su_decay": 0.97, "su_growth": 0.04
        },
        "WS": {
            "K": 82, "beta": 1.50, "u_growth": 0.042, "D": 459,
            "rating_decay_per_year": 0.017, "decay_grace_days": 176,
            "cap_K_mult": 3.5, "Ks": 25, "uncertainty_decay": 0.95, "Ks_beta": 0.85, "su_decay": 0.97, "su_growth": 0.04
        },
        "MD": {
            "K": 85, "beta": 1.50, "u_growth": 0.063, "D": 363,
            "rating_decay_per_year": 0.074, "decay_grace_days": 146,
            "cap_K_mult": 3.0, "Ks": 25, "uncertainty_decay": 0.95, "Ks_beta": 0.85, "su_decay": 0.97, "su_growth": 0.04
        },
        "WD": {
            "K": 85, "beta": 1.50, "u_growth": 0.063, "D": 363,
            "rating_decay_per_year": 0.074, "decay_grace_days": 146,
            "cap_K_mult": 3.0, "Ks": 25, "uncertainty_decay": 0.95, "Ks_beta": 0.85, "su_decay": 0.97, "su_growth": 0.04
        },
        "XD": {
            "K": 85, "beta": 1.50, "u_growth": 0.063, "D": 363,
            "rating_decay_per_year": 0.074, "decay_grace_days": 146,
            "cap_K_mult": 3.0, "Ks": 25, "uncertainty_decay": 0.95, "Ks_beta": 0.85, "su_decay": 0.97, "su_growth": 0.04
        }
    }
}
# Add a default config for safety, using the doubles params as they are most common
final_config["event_params"]["default"] = final_config["event_params"]["MD"]

# --- 3. Create a unique ID for this run ---
run_id = f"elo_mov__{datetime.now().strftime('%Y%m%d%H%M%S')}"
print(f"Starting FINAL Elo run with ID: {run_id}")

# --- 4. Set up database connections ---
core_conn = sqlite3.connect(CORE_DB_PATH)
test_conn = sqlite3.connect(TEST_DB_PATH)
test_cursor = test_conn.cursor()

init_rating_table(test_conn)

# --- 5. Log the run's metadata ---
# We store the whole config as a JSON string for perfect reproducibility
test_cursor.execute("""
    INSERT INTO run_metadata (run_id, mode, split_date, notes, created_at)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(run_id) DO NOTHING
""", (
    run_id,
    "elo_v1_final",
    final_config['split_date'],
    json.dumps(final_config["event_params"]), # Store the detailed params
    datetime.now().isoformat()
))
test_conn.commit()

# --- 6. Execute the Elo engine ---
try:
    run_elo(core_conn=core_conn, test_conn=test_conn, run_id=run_id, **final_config)
    print("\nElo run completed successfully!")
    print(f"To analyze, run: python run_analysis.py {run_id}")
except Exception as e:
    print(f"\n--- ELO RUN FAILED ---")
    print(f"Error: {e}")
    test_cursor.execute("UPDATE run_metadata SET notes = ? WHERE run_id = ?", (f"FAILED: {e}", run_id))
    test_conn.commit()
    raise
finally:
    core_conn.close()
    test_conn.close()
    print("Database connections closed.")