import sys
import os
import sqlite3

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../web/backend"))

from config import CORE_DB_PATH, RATINGS_DB_PATH
from routers.players import get_player_stats

db_core = sqlite3.connect(CORE_DB_PATH)
db_core.row_factory = sqlite3.Row
db_ratings = sqlite3.connect(RATINGS_DB_PATH)
db_ratings.row_factory = sqlite3.Row

# Get some player ids
cursor = db_core.cursor()
cursor.execute("SELECT player_id FROM players LIMIT 5")
player_ids = [r['player_id'] for r in cursor.fetchall()]

# Test elo, whr, bwf models and events
events = ["MS", "MD"]
models = ["elo", "whr", "bwf"]

for pid in player_ids:
    for event in events:
        for model in models:
            print(f"Testing player={pid}, event={event}, model={model}...")
            try:
                res = get_player_stats(
                    id=pid,
                    event=event,
                    period="all",
                    model=model,
                    db_core=db_core,
                    db_ratings=db_ratings
                )
                print("  Success!")
            except Exception as e:
                import traceback
                print(f"  FAILED with {type(e).__name__}: {e}")
                traceback.print_exc()

db_core.close()
db_ratings.close()
