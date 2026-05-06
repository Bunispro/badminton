import sqlite3
import json
from datetime import datetime

from elo_engine_v1 import run_elo
from db_ratings import init_rating_table

# --- 1. Define Database Paths ---
CORE_DB_PATH = "bwf_data_2008-now__v1.sqlite"
TEST_DB_PATH = "testing_bwf.sqlite" # This will store ratings, predictions, etc.

# --- 2. Define Run Parameters ---
# These are the "knobs" you can turn to tune the model
config = {
    "K": 65,
    "Ks": 23,
    "beta": 1.2,
    "uncertainty_decay": 0.95,
    "u_growth": 0.05,
    "Ks_beta": 0.8,
    "su_decay": 0.98,
    "su_growth": 0.04,
    "cap_K_mult": 3.0,
    "split_date": "2018-01-01",
    "D_map": {
        "MS": 450,
        "WS": 400,
        "MD": 420,
        "WD": 380,
        "XD": 410
    }
}

# --- 3. Create a unique ID for this run ---
run_id = f"elo_v1__K={config['K']}__Ks={config['Ks']}__beta={config['beta']}__sdate={config['split_date']}"
print(f"Starting Elo run with ID: {run_id}")

# --- 4. Set up database connections ---
core_conn = sqlite3.connect(CORE_DB_PATH)
test_conn = sqlite3.connect(TEST_DB_PATH)
test_cursor = test_conn.cursor()

# Ensure all necessary tables exist in the test database
init_rating_table(test_conn)

# --- 5. Log the run's metadata BEFORE starting ---
# This ensures the run is recorded even if it fails midway
test_cursor.execute("""
    INSERT INTO run_metadata (
        run_id, mode, split_date, K, D_map, Ks, beta, uncertainty_decay,
        u_growth, Ks_beta, cap_K_mult, su_decay, su_growth, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(run_id) DO NOTHING
""", (
    run_id,
    "elo_v1",
    config['split_date'],
    config['K'],
    json.dumps(config['D_map']), # Store the dict as a JSON string
    config['Ks'],
    config['beta'],
    config['uncertainty_decay'],
    config['u_growth'],
    config['Ks_beta'],
    config['cap_K_mult'],
    config['su_decay'],
    config['su_growth'],
    datetime.now().isoformat()
))
test_conn.commit()

# --- 6. Execute the Elo engine ---
try:
    run_elo(core_conn=core_conn, test_conn=test_conn, run_id=run_id, **config)
    print("\nElo run completed successfully!")

except Exception as e:
    print(f"\n--- ELO RUN FAILED ---")
    print(f"Error: {e}")
    test_cursor.execute("UPDATE run_metadata SET notes = ? WHERE run_id = ?", (f"FAILED: {e}", run_id))
    test_conn.commit()

finally:
    # --- 7. Close connections ---
    core_conn.close()
    test_conn.close()
    print("Database connections closed.")