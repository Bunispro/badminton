import sqlite3
import json
from datetime import datetime
import sys

from elo_engine_v1 import run_elo
from db_ratings import init_rating_table

def run_from_config(config_path):
    # --- 1. Load config from file ---
    with open(config_path, 'r') as f:
        config = json.load(f)

    # --- 2. Define Database Paths ---
    CORE_DB_PATH = "bwf_data_2008-now__v1.sqlite"
    TEST_DB_PATH = "elo_ratings.sqlite"

    # --- 3. Create a unique ID for this run ---
    # Create a more descriptive run_id for hyperparameter tuning
    run_id_parts = [
        f"K={config['K']:.0f}",
        f"b={config['beta']:.2f}",
        f"cap={config['cap_K_mult']:.1f}",
        f"ug={config['u_growth']:.3f}",
        f"D={config.get('D_base', 400):.0f}", # Add D_base to run_id
        f"sdate={config['split_date'][:4]}" # Add split_date year to run_id
    ]
    run_id = f"h_opt__{'_'.join(run_id_parts)}__{datetime.now().strftime('%Y%m%d%H%M%S')}"
    print(f"Starting Elo run with ID: {run_id}")

    # --- 4. Set up database connections ---
    core_conn = sqlite3.connect(CORE_DB_PATH)
    test_conn = sqlite3.connect(TEST_DB_PATH)
    test_cursor = test_conn.cursor()

    init_rating_table(test_conn)

    # --- 5. Log the run's metadata ---
    test_cursor.execute("""
        INSERT INTO run_metadata (
            run_id, mode, split_date, K, D_map, Ks, beta, uncertainty_decay,
            u_growth, Ks_beta, cap_K_mult, su_decay, su_growth, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO NOTHING
    """, (
        run_id, "elo_v1_hyper", config['split_date'], config['K'], json.dumps(config['D_map']),
        config['Ks'], config['beta'], config['uncertainty_decay'], config['u_growth'],
        config['Ks_beta'], config['cap_K_mult'], config['su_decay'], config['su_growth'],
        datetime.now().isoformat()
    ))
    test_conn.commit()

    # --- 6. Execute the Elo engine ---
    try:
        run_elo(core_conn=core_conn, test_conn=test_conn, run_id=run_id, **config)
        print("\nElo run completed successfully!")
        print(f"RUN_ID_FOR_ANALYSIS:{run_id}") # Print run_id in a parsable format
    except Exception as e:
        print(f"\n--- ELO RUN FAILED ---")
        print(f"Error: {e}")
        test_cursor.execute("UPDATE run_metadata SET notes = ? WHERE run_id = ?", (f"FAILED: {e}", run_id))
        test_conn.commit()
        raise # Re-raise the exception to notify the optimizer script
    finally:
        core_conn.close()
        test_conn.close()
        print("Database connections closed.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python Run_elo_from_config.py <path_to_config.json>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    run_from_config(config_file)