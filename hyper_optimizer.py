import subprocess
import sys
import json
import random
import os

# --- 1. Define the Search Space for Hyperparameters ---
# For each parameter, define a range (for floats) or a list of values (for discrete choices).
SEARCH_SPACE = {
    # Core Elo params
    "K": (60, 90),
    "beta": (1.45, 1.65),
    "u_growth": (0.04, 0.08),
    "D_base": (350, 480),
    "rating_decay_per_year": (0.01, 0.09),
    "decay_grace_days": (110, 180),
    "split_date": ["2018-01-01"], 
    "cap_K_mult": (2.5, 4.0),
    
    # MoV params
    "mov_base_mult": (0.70, 0.95),
    "mov_growth_rate": (1.01, 1.15),
    
    # Synergy params
    "Ks": (15, 40),
    "Ks_beta": (0.5, 1.5),
    "su_growth": (0.02, 0.08),
    "su_decay": (0.92, 0.99),
}

# --- 2. Define Fixed Parameters ---
# Some parameters are less sensitive or have been established in previous runs.
FIXED_CONFIG = {
    "uncertainty_decay": 0.95, # A stable value
}

# --- 3. Define Optimization Settings ---
NUM_TRIALS = 150  # How many different combinations to test

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

        temp_config_path = f"temp_elo_config_{i}.json"
        captured_run_id = None
        try:
            with open(temp_config_path, 'w') as f:
                json.dump(config, f)

            print("\n--- Running Elo Engine ---")
            # Capture stdout to extract the run_id
            elo_output = subprocess.run([sys.executable, "Run_elo_mov_config.py", temp_config_path], capture_output=True, text=True, encoding='utf-8', check=True)
            print(elo_output.stdout, end='') # Print the captured output

            for line in elo_output.stdout.splitlines():
                if line.startswith("RUN_ID_FOR_ANALYSIS:"):
                    captured_run_id = line.split(":", 1)[1].strip()
                    break

            if not captured_run_id:
                raise ValueError("Could not capture run_id from Elo engine output.")

            print("\n--- Running Analysis ---")
            run_command([sys.executable, "run_analysis.py", captured_run_id])

            print(f"\n[✓] Trial {i + 1} completed successfully.")

        except subprocess.CalledProcessError as e:
            print(f"\n[!] ERROR during trial {i + 1}. Skipping to next trial.")
            print(f"  Command '{' '.join(e.cmd)}' failed with exit code {e.returncode}.")
            print("\n--- Subprocess Output ---")
            # Print stdout and stderr from the failed process for debugging
            if e.stdout:
                print("--- STDOUT ---")
                print(e.stdout)
            if e.stderr:
                print("--- STDERR ---")
                print(e.stderr)
            print("-------------------------\n")
            continue
        except ValueError as e:
            print(f"\n[!] ERROR during trial {i + 1}: {e}. Skipping to next trial.")
            continue
        finally:
            # Ensure the temp file is always removed, even if the trial fails
            if os.path.exists(temp_config_path):
                os.remove(temp_config_path)

    print(f"\n{'='*60}\n--- Optimization Finished ---")
    print("Query the 'run_metadata' table in 'elo_ratings.sqlite' to see results.")
    print("Example query: SELECT run_id, log_loss, K, beta, cap_K_mult FROM run_metadata ORDER BY log_loss ASC LIMIT 10;")

if __name__ == "__main__":
    main()