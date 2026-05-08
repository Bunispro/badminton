import sqlite3
import json
from datetime import datetime
import sys

from elo_engine_mov import run_elo
from db_ratings import init_rating_table

def add_missing_columns(cursor):
    """
    Adds missing columns to the run_metadata table if they don't exist.
    """
    cursor.execute("PRAGMA table_info(run_metadata)")
    columns = {row[1] for row in cursor.fetchall()}
    if 'notes' not in columns:
        cursor.execute("ALTER TABLE run_metadata ADD COLUMN notes TEXT")
        print("Added missing column 'notes' to 'run_metadata' table.")
    if 'mov_base_mult' not in columns:
        cursor.execute("ALTER TABLE run_metadata ADD COLUMN mov_base_mult REAL")
        print("Added missing column 'mov_base_mult' to 'run_metadata' table.")
    if 'mov_growth_rate' not in columns:
        cursor.execute("ALTER TABLE run_metadata ADD COLUMN mov_growth_rate REAL")
        print("Added missing column 'mov_growth_rate' to 'run_metadata' table.")

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
        f"ug={config['u_growth']:.3f}",
        f"D={config.get('D_base', 400):.0f}",
        f"rd={config.get('rating_decay_per_year', 0):.2f}", # rating decay
        f"gd={config.get('decay_grace_days', 0):.0f}", # grace days
        f"mb={config.get('mov_base_mult', 1.0):.2f}",
        f"mg={config.get('mov_growth_rate', 1.0):.3f}",
        f"sdate={config['split_date'][:4]}" # Add split_date year to run_id
    ]
    run_id = f"h_opt_mov__{'_'.join(run_id_parts)}__{datetime.now().strftime('%Y%m%d%H%M%S')}"
    print(f"Starting Elo run with ID: {run_id}")

    # --- 4. Set up database connections ---
    core_conn = sqlite3.connect(CORE_DB_PATH)
    test_conn = sqlite3.connect(TEST_DB_PATH)
    test_cursor = test_conn.cursor()

    init_rating_table(test_conn)
    add_missing_columns(test_cursor)

    # --- 5. Log the run's metadata ---
    test_cursor.execute("""
        INSERT INTO run_metadata (
            run_id, mode, split_date, K, D_map, Ks, beta, uncertainty_decay,
            u_growth, Ks_beta, cap_K_mult, su_decay, su_growth, created_at,
            rating_decay_per_year, decay_grace_days, mov_base_mult, mov_growth_rate
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO NOTHING
    """, (
        run_id, "elo_v1_hyper_p3", config['split_date'], config['K'], json.dumps(config['D_map']),
        config['Ks'], config['beta'], config['uncertainty_decay'], config['u_growth'],
        config['Ks_beta'], config['cap_K_mult'], config['su_decay'], config['su_growth'],
        datetime.now().isoformat(), config.get('rating_decay_per_year', 0), config.get('decay_grace_days', 0),
        config.get('mov_base_mult', 1.0), config.get('mov_growth_rate', 1.0)
    ))
    test_conn.commit()

    # --- 6. Execute the Elo engine ---
    try:
        # D_base is used to create D_map in the optimizer, but run_elo doesn't need it.
        # We remove it from the config before passing to run_elo.
        config.pop('D_base', None)
        # --- NEW: Construct the event_params structure required by the modern engine ---
        all_events = ["MS", "WS", "MD", "WD", "XD", "default"]
        event_params = {}
        # For this tuning run, we apply the same sampled params to all events.
        shared_params = {
            "K": config['K'],
            "beta": config['beta'],
            "Ks": config['Ks'],
            "uncertainty_decay": config['uncertainty_decay'],
            "u_growth": config['u_growth'],
            "Ks_beta": config['Ks_beta'],
            "su_decay": config['su_decay'],
            "su_growth": config['su_growth'],
            "cap_K_mult": config['cap_K_mult'],
            "rating_decay_per_year": config.get('rating_decay_per_year', 0.0),
            "decay_grace_days": int(config.get('decay_grace_days', 90)),
            "mov_base_mult": config.get('mov_base_mult', 1.0),
            "mov_growth_rate": config.get('mov_growth_rate', 1.0)
        }
        for event in all_events:
            event_params[event] = shared_params.copy()
            # Add the event-specific D value, falling back to a default if needed
            event_params[event]['D'] = config['D_map'].get(event, config['D_map'].get('MD', 400))
            if event in ['WS', 'WD']:
                event_params[event]['mov_base_mult'] = 1.0
                event_params[event]['mov_growth_rate'] = 1.0

        # Prepare the final config for the run_elo function
        run_config = {
            "split_date": config['split_date'],
            "store_history": config.get('store_history', False), # History not needed for optimization
            "event_params": event_params
        }

        run_elo(core_conn=core_conn, test_conn=test_conn, run_id=run_id, **run_config)
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