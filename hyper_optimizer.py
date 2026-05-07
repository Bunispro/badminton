import subprocess
import sys
import json
import random
import os

# --- 1. Define the Search Space for Hyperparameters ---
# For each parameter, define a range (for floats) or a list of values (for discrete choices).
# We are now only searching over D_base and split_date.
SEARCH_SPACE = {
    "D_base": (300, 600), # Expanded search range for D
    "split_date": ["2016-01-01", "2017-01-01", "2018-01-01", "2019-01-01", "2020-01-01"], # Expanded search range for split_date
}

# --- 2. Define Fixed Parameters ---
# Using the best parameters from your previous run, with sensible defaults for others.
FIXED_CONFIG = {
    "K": 80,
    "Ks": 25, # Midpoint of previous search
    "beta": 1.33818,
    "uncertainty_decay": 0.95, # Midpoint of previous search
    "u_growth": 0.0300221,
    "Ks_beta": 0.85, # Midpoint of previous search
    "su_decay": 0.97, # Midpoint of previous search
    "su_growth": 0.04, # Midpoint of previous search
    "cap_K_mult": 3.0,
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
    
    # Dynamically create D_map based on the sampled D_base
    if "D_base" in config:
        d_base = config["D_base"]
        config["D_map"] = {
            "MS": d_base * 1.05, # Example multipliers, you can refine these
            "WS": d_base * 1.0,
            "MD": d_base * 1.0,
            "WD": d_base * 0.95,
            "XD": d_base * 1.0
        }

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

        temp_config_path = f"temp_elo_config_{i}.json" # Use unique temp file for each trial
        with open(temp_config_path, 'w') as f:
            json.dump(config, f)

        captured_run_id = None
        try:
            print("\n--- Running Elo Engine ---")
            # Capture stdout to extract the run_id
            elo_output = subprocess.run([sys.executable, "Run_elo_from_config.py", temp_config_path], capture_output=True, text=True, encoding='utf-8', check=True)
            print(elo_output.stdout, end='') # Print the captured output
            
            for line in elo_output.stdout.splitlines():
                if line.startswith("RUN_ID_FOR_ANALYSIS:"):
                    captured_run_id = line.split(":", 1)[1].strip()
                    break
            
            if not captured_run_id:
                raise ValueError("Could not capture run_id from Elo engine output.")

            print("\n--- Running Analysis ---")
            run_command([sys.executable, "run_analysis.py", captured_run_id])

        except subprocess.CalledProcessError as e:
            print(f"\n[!] ERROR during trial {i + 1}. Skipping to next trial.")
            print(f"  Command '{' '.join(e.cmd)}' failed with exit code {e.returncode}.")
            continue
        except ValueError as e:
            print(f"\n[!] ERROR during trial {i + 1}: {e}. Skipping to next trial.")
            continue
        
        print(f"\n[✓] Trial {i + 1} completed successfully.")
        os.remove(temp_config_path) # Clean up the temp file after successful trial

    print(f"\n{'='*60}\n--- Optimization Finished ---")
    print("Query the 'run_metadata' table in 'elo_ratings.sqlite' to see results.")
    print("Example query: SELECT run_id, log_loss, K, beta, cap_K_mult FROM run_metadata ORDER BY log_loss ASC LIMIT 10;")

if __name__ == "__main__":
    main()