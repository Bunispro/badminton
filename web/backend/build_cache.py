import sqlite3
import json
import os
import sys
from datetime import datetime

# Add the current directory to sys.path so we can import database and config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import CORE_DB_PATH, RATINGS_DB_PATH, init_db_indices
from routers.dashboard import get_dashboard_summary, get_dashboard_pulse, get_leaderboard_preview, get_trending, get_model_stats
from routers.leaderboard import get_leaderboard

def build_cache():
    print(f"[{datetime.now()}] Building API cache...")
    init_db_indices()
    db_ratings = sqlite3.connect(RATINGS_DB_PATH)
    db_ratings.row_factory = sqlite3.Row
    db_core = sqlite3.connect(CORE_DB_PATH)
    db_core.row_factory = sqlite3.Row
    
    cursor = db_ratings.cursor()
    
    # Ensure api_cache table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_cache (
            cache_key TEXT PRIMARY KEY,
            cache_value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db_ratings.commit()
    
    # Clear existing cache to prevent circular caching (router endpoints check cache first)
    print("  Truncating existing cache table to force fresh computations...")
    cursor.execute("DELETE FROM api_cache")
    db_ratings.commit()
    
    # Helper to save to cache
    def save_cache(key, data):
        cursor.execute("""
            INSERT OR REPLACE INTO api_cache (cache_key, cache_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (key, json.dumps(data)))
        db_ratings.commit()

    # 1. Dashboard Summary
    print("  Caching dashboard summary...")
    summary = get_dashboard_summary(db_core, db_ratings)
    save_cache("dashboard_summary", summary)
    
    # 2. Dashboard Pulse
    print("  Caching dashboard pulse...")
    pulse = get_dashboard_pulse(db_core, db_ratings)
    save_cache("dashboard_pulse", pulse)
    
    # 3. Model Stats
    print("  Caching model stats...")
    mstats = get_model_stats(db_ratings, db_core)
    save_cache("model_stats", mstats)
    
    # 4. Leaderboard Preview
    print("  Caching leaderboard preview...")
    for model in ["elo", "whr", "bwf"]:
        preview = get_leaderboard_preview(model, db_ratings, db_core)
        save_cache(f"leaderboard_preview_{model}", preview)
    
    # 5. Trending Players (for each event and period)
    events = ["MS", "WS", "MD", "WD", "XD"]
    periods = ["1m", "3m"]
    for event in events:
        for period in periods:
            print(f"  Caching trending players for {event} ({period})...")
            trending = get_trending(event=event, period=period, db_ratings=db_ratings, db_core=db_core)
            save_cache(f"trending_{event}_{period}", trending)
        
    # 6. Leaderboard (Top 100 for each event/model/mode)
    # We only cache the first page (top 100) as that's what 99% of users see first
    models = ["elo", "whr", "bwf"]
    modes = ["current", "peak"]
    for event in events:
        for model in models:
            for mode in modes:
                print(f"  Caching leaderboard {event} {model} {mode} (top 100)...")
                # We mock the request and other parameters
                lb_data = get_leaderboard(None, event, model, mode, 100, 0, "1m", None, db_ratings, db_core)
                save_cache(f"leaderboard_{event}_{model}_{mode}_100_0", lb_data)

    db_ratings.close()
    db_core.close()
    print(f"[{datetime.now()}] API cache build complete.")

if __name__ == "__main__":
    build_cache()
