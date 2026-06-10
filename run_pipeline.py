import subprocess
import time
import argparse
import sys
import os

def run_step(step_name, command):
    print(f"\n==================================================", flush=True)
    print(f" STARTING: {step_name}", flush=True)
    print(f" Command: {' '.join(command)}", flush=True)
    print(f"==================================================", flush=True)
    start_time = time.time()
    
    # Run the subprocess and stream the output to console
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Read output line by line as it is printed
    for line in process.stdout:
        print(line, end="", flush=True)
        
    process.wait()
    elapsed = time.time() - start_time
    
    if process.returncode != 0:
        print(f"\n[ERROR] {step_name} failed with exit code {process.returncode}", flush=True)
        sys.exit(process.returncode)
        
    print(f"\n[SUCCESS] {step_name} completed in {elapsed:.2f} seconds.", flush=True)
    return elapsed

def main():
    parser = argparse.ArgumentParser(description="Orchestrate the entire Badminton ratings pipeline.")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip the raw JSON data ingestion step.")
    parser.add_argument("--skip-elo", action="store_true", help="Skip the ELO rating engine step.")
    parser.add_argument("--skip-whr", action="store_true", help="Skip the WHR rating engine step (useful for quick runs since WHR is slow).")
    parser.add_argument("--skip-stats", action="store_true", help="Skip populating player stats and trends.")
    parser.add_argument("--skip-ml", action="store_true", help="Skip rebuilding the ML features dataset.")
    parser.add_argument("--skip-train", action="store_true", help="Skip retraining the XGBoost expectation model.")
    parser.add_argument("--skip-predict", action="store_true", help="Skip generating and logging XGBoost predictions.")
    parser.add_argument("--skip-cache", action="store_true", help="Skip rebuilding the API cache.")
    
    args = parser.parse_args()
    
    # Instruct individual rating run scripts to skip cache rebuilds during rating runs
    os.environ["SKIP_CACHE_REBUILD"] = "1"
    
    pipeline_start = time.time()
    times = {}
    
    # Step 1: Ingest Match Data
    if not args.skip_ingest:
        times["Ingestion"] = run_step("Data Ingestion", [sys.executable, "Run_ingest.py"])
        
    # Step 2: Run Elo final model
    if not args.skip_elo:
        times["Elo Calculations"] = run_step("Elo Engine Run", [sys.executable, "run_elo_final.py"])
        
    # Step 3: Run WHR model and doubles factorization
    if not args.skip_whr:
        times["WHR Calculations & Factorization"] = run_step("WHR Engine Run", [sys.executable, "run_whr.py"])
        
    # Step 4: Populate player stats, winrates, trends, and ranks
    if not args.skip_stats:
        times["Player Stats Aggregation"] = run_step("Player Stats & Trends Population", [sys.executable, "populate_player_stats.py"])
        
    # Step 5: Rebuild ML features dataset
    if not args.skip_ml:
        times["ML Feature Engineering"] = run_step("ML Features Rebuild", [sys.executable, "build_ml_dataset.py"])
        
    # Step 6: Retrain XGBoost model
    if not args.skip_train:
        times["XGBoost Model Training"] = run_step("XGBoost Expectation Model Training", [sys.executable, "train_xgboost.py"])
        
    # Step 7: Generate predictions
    if not args.skip_predict:
        times["XGBoost Predictions Log"] = run_step("Logging XGBoost Predictions", [sys.executable, "run_xgb_predictions.py"])
        times["BWF Predictions Log"] = run_step("Logging BWF Point Predictions", [sys.executable, "run_bwf_predictions.py"])
        
    # Step 8: Rebuild FastAPI application cache
    if not args.skip_cache:
        # Resolve build_cache path
        cache_script = os.path.join("web", "backend", "build_cache.py")
        times["Cache Rebuild"] = run_step("API Cache Generation", [sys.executable, cache_script])
        
    total_time = time.time() - pipeline_start
    print(f"\n==================================================", flush=True)
    print(f" *** PIPELINE RUN COMPLETE ***", flush=True)
    print(f" Total Elapsed Time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)", flush=True)
    print(f"--------------------------------------------------", flush=True)
    for step, duration in times.items():
        print(f" - {step:35}: {duration:.2f}s ({duration/60:.2f}m)", flush=True)
    print(f"==================================================", flush=True)

if __name__ == "__main__":
    main()
