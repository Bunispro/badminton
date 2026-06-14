from fastapi import APIRouter, Depends
import sqlite3
from database import get_core_db, get_ratings_db

router = APIRouter()

@router.get("/api/events")
def get_events():
    return ["MS", "WS", "MD", "WD", "XD"]

@router.get("/api/countries")
def get_countries(db_core: sqlite3.Connection = Depends(get_core_db)):
    cursor = db_core.cursor()
    # Using the optimized query that returns counts
    cursor.execute("""
        SELECT country_code, COUNT(*) as count 
        FROM players 
        WHERE country_code IS NOT NULL AND country_code != ''
        GROUP BY country_code 
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    return {row['country_code'].upper(): row['count'] for row in rows}

@router.get("/api/inactivity-threshold")
def get_inactivity_threshold(model: str = "elo", db: sqlite3.Connection = Depends(get_ratings_db)):
    decay_grace_days = 240
    if model == "elo":
        try:
            cursor = db.cursor()
            cursor.execute("SELECT decay_grace_days FROM run_metadata WHERE run_id LIKE '%final%' ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row and row['decay_grace_days'] is not None:
                # Override database configuration if it specifies a grace period, but default to 240 (8 months)
                decay_grace_days = int(row['decay_grace_days'])
        except Exception as e:
            print(f"Error getting decay_grace_days in metadata: {e}")
    # Force 240 days (8 months) as requested by the user
    decay_grace_days = 240
    return {"inactivity_threshold": decay_grace_days}
