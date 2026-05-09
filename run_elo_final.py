import sqlite3
import json
from datetime import datetime

from elo_engine_1_0 import run_elo
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
        "MS": {
            "K": 74.18, "beta": 1.50, "u_growth": 0.058, "D": 417,
            "rating_decay_per_year": 0.04, "decay_grace_days": 178,
            "cap_K_mult": 3.99, "Ks": 34, "uncertainty_decay": 0.95, "Ks_beta": 0.86, "su_decay": 0.93, "su_growth": 0.02,
            "mov_base_mult": 0.72, "mov_growth_rate": 1.039
        },
        "WS": {
            "K": 80.89, "beta": 1.62, "u_growth": 0.054, "D": 464,
            "rating_decay_per_year": 0.016, "decay_grace_days": 114,
            "cap_K_mult": 3.96, "Ks": 38, "uncertainty_decay": 0.95, "Ks_beta": 0.83, "su_decay": 0.98, "su_growth": 0.07,
            "mov_base_mult": 1.0, "mov_growth_rate": 1.0
        },
        "MD": {
            "K": 86.68, "beta": 1.57, "u_growth": 0.040, "D": 460,
            "rating_decay_per_year": 0.04, "decay_grace_days": 123,
            "cap_K_mult": 3.23, "Ks": 17, "uncertainty_decay": 0.95, "Ks_beta": 0.85, "su_decay": 0.95, "su_growth": 0.06,
            "mov_base_mult": 0.81, "mov_growth_rate": 1.086
        },
        "WD": {
            "K": 77.83, "beta": 1.57, "u_growth": 0.047, "D": 343,
            "rating_decay_per_year": 0.02, "decay_grace_days": 167,
            "cap_K_mult": 3.55, "Ks": 16, "uncertainty_decay": 0.95, "Ks_beta": 0.60, "su_decay": 0.99, "su_growth": 0.04,
            "mov_base_mult": 1.0, "mov_growth_rate": 1.0
        },
        "XD": {
            "K": 86.68, "beta": 1.57, "u_growth": 0.040, "D": 460,
            "rating_decay_per_year": 0.04, "decay_grace_days": 123,
            "cap_K_mult": 3.23, "Ks": 17, "uncertainty_decay": 0.95, "Ks_beta": 0.85, "su_decay": 0.95, "su_growth": 0.06,
            "mov_base_mult": 0.81, "mov_growth_rate": 1.086
        }
    }
}
# Add a default config for safety, using the doubles params as they are most common
final_config["event_params"]["default"] = final_config["event_params"]["MD"]

# --- 3. Create a unique ID for this run ---
run_id = f"elo_final__{datetime.now().strftime('%Y%m%d%H%M%S')}"
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