import sqlite3
import json
import os
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
        "MD": {
            "K": 82.6413, "beta": 1.5365, "u_growth": 0.0555, "rating_decay_per_year": 0.0617, "decay_grace_days": 152.1722,
            "cap_K_mult": 3.6331, "Ks": 18.4304, "uncertainty_decay": 0.95, "Ks_beta": 0.813, "su_decay": 0.9344, "su_growth": 0.0462,
            "mov_base_mult": 0.7844, "mov_growth_rate": 1.1089, "D": 392.8
        },
        "MS": {
            "K": 68.2673, "beta": 1.5974, "u_growth": 0.0597, "rating_decay_per_year": 0.0306, "decay_grace_days": 166.1262,
            "cap_K_mult": 3.334, "Ks": 24.7918, "uncertainty_decay": 0.95, "Ks_beta": 1.2068, "su_decay": 0.9642, "su_growth": 0.0465,
            "mov_base_mult": 0.758, "mov_growth_rate": 1.0451, "D": 424.8
        },
        "WD": {
            "K": 85.1701, "beta": 1.6016, "u_growth": 0.0669, "rating_decay_per_year": 0.0592, "decay_grace_days": 157.35,
            "cap_K_mult": 3.4495, "Ks": 17.8065, "uncertainty_decay": 0.95, "Ks_beta": 0.7653, "su_decay": 0.9212, "su_growth": 0.0415,
            "mov_base_mult": 0.8862, "mov_growth_rate": 1.087, "D": 364.4
        },
        "WS": {
            "K": 80.5555, "beta": 1.6354, "u_growth": 0.06, "rating_decay_per_year": 0.0268, "decay_grace_days": 146.7345,
            "cap_K_mult": 3.4607, "Ks": 25.812, "uncertainty_decay": 0.95, "Ks_beta": 0.966, "su_decay": 0.9635, "su_growth": 0.0669,
            "mov_base_mult": 0.7664, "mov_growth_rate": 1.0786, "D": 448.5
        },
        "XD": {
            "K": 81.5302, "beta": 1.5571, "u_growth": 0.0597, "rating_decay_per_year": 0.0451, "decay_grace_days": 152.1458,
            "cap_K_mult": 3.3675, "Ks": 19.357, "uncertainty_decay": 0.95, "Ks_beta": 0.9545, "su_decay": 0.936, "su_growth": 0.05,
            "mov_base_mult": 0.7276, "mov_growth_rate": 1.0884, "D": 425.2
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

# --- Rebuild API Cache ---
if os.environ.get("SKIP_CACHE_REBUILD") != "1":
    try:
        print("\nRebuilding API cache...")
        import sys
        base_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.join(base_dir, "web", "backend")
        sys.path.append(backend_dir)
        from build_cache import build_cache
        build_cache()
        print("API cache rebuilt successfully!")
    except Exception as cache_err:
        print(f"Warning: Failed to rebuild API cache: {cache_err}")
else:
    print("\nSkipping cache rebuild as requested by the pipeline orchestrator.")