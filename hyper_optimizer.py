import subprocess
import sys
import json
import random
import os

# --- 1. Define the Search Space for Hyperparameters ---
# For each parameter, define a range (for floats) or a list of values (for discrete choices).
SEARCH_SPACE = {
    "K": [50, 60, 65, 70, 80],
    "Ks": [15, 20, 25, 30],
    "beta": (1.0, 1.5),
    "uncertainty_decay": (0.92, 0.98),
    "u_growth": (0.03, 0.07),
    "Ks_beta": (0.5, 1.2),
    "su_decay": (0.95, 0.99),
    "su_growth": (0.02, 0.06),
    "cap_K_mult": [2.0, 2.5, 3.0, 3.5],
}

# --- 2. Define Fixed Parameters ---
FIXED_CONFIG = {
    "split_date": "2018-01-01",
    "D_map": {
        "MS": 450, "WS": 400, "MD": 420, "WD": 380, "XD": 410
    }
}

# --- 3. Define Optimization Settings ---
NUM_TRIALS = 50  # How many different combinations to test

def run_command(command):
    """Runs a command and prints its output in real-time."""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1)
    for line in iter(process.stdout.readline, ''):
        print(line, end='')
    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, command)

def sample_parameters():
    """Randomly samples a configuration from the SEARCH_SPACE."""
    config = {}
    for key, value in SEARCH_SPACE.items():
        if isinstance(value, list):
            config[key] = random.choice(value)
        elif isinstance(value, tuple):
            config[key] = random.uniform(value[0], value[1])
    
    config.update(FIXED_CONFIG)
    return config

def main():
    print(f"--- Starting Hyperparameter Optimization for {NUM_TRIALS} trials ---")

    for i in range(NUM_TRIALS):
        print(f"\n{'='*60}")
        print(f"--- Trial {i + 1}/{NUM_TRIALS} ---")
        print(f"{'='*60}")

        config = sample_parameters()
        print("Testing config:")
        for key, val in sorted(config.items()):
            if isinstance(val, float):
                print(f"  {key:<20}: {val:.4f}")
            else:
                print(f"  {key:<20}: {val}")

        temp_config_path = "temp_elo_config.json"
        with open(temp_config_path, 'w') as f:
            json.dump(config, f)

        try:
            print("\n--- Running Elo Engine ---")
            run_command([sys.executable, "Run_elo_from_config.py", temp_config_path])

            print("\n--- Running Analysis ---")
            run_command([sys.executable, "run_analysis.py"])

        except subprocess.CalledProcessError as e:
            print(f"\n[!] ERROR during trial {i + 1}. Skipping to next trial.")
            print(f"  Command '{' '.join(e.cmd)}' failed with exit code {e.returncode}.")
            continue
        
        print(f"\n[✓] Trial {i + 1} completed successfully.")

    os.remove(temp_config_path) # Clean up the temp file
    print(f"\n{'='*60}\n--- Optimization Finished ---")
    print("Query the 'run_metadata' table in 'testing_bwf.sqlite' to see results.")
    print("Example query: SELECT run_id, log_loss, K, beta, cap_K_mult FROM run_metadata ORDER BY log_loss ASC LIMIT 10;")

if __name__ == "__main__":
    main()