from fastapi import APIRouter, Depends, Query, Request, HTTPException
from typing import Literal, Optional
import sqlite3
from datetime import datetime, timedelta

from database import get_core_db, get_ratings_db
from services.leaderboard_service import fetch_leaderboard_data
from services.player_service import get_latest_rating
from config import REVERSE_COUNTRY_MAPPING

router = APIRouter()

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from typing import Literal, Optional
import sqlite3
from datetime import datetime, timedelta

from database import get_core_db, get_ratings_db
from services.leaderboard_service import fetch_leaderboard_data
from config import REVERSE_COUNTRY_MAPPING

router = APIRouter()

# Simple LRU-style cache for the leaderboard to avoid repeated hits within seconds
# This replaces the complicated 'preload' logic
from functools import lru_cache

@lru_cache(maxsize=32)
def get_cached_leaderboard_data(event, model, mode, limit, offset, period, country):
    # This is just a wrapper for the service call
    # In a real app, you'd use a proper cache like Redis or a database-backed cache
    # But for now, we'll let the database-backed player_stats table do the heavy lifting
    pass

@router.get("/api/leaderboard")
def get_leaderboard(request: Request, 
                    event: Literal["MS", "WS", "MD", "WD", "XD"] = "MS", 
                    model: Literal["whr", "elo", "bwf"] = "whr", 
                    mode: Literal["current", "peak"] = "current",
                    limit: int = Query(50, ge=1, le=1000),
                    offset: int = Query(0, ge=0),
                    period: str = Query("1m", description="Period for rating changes"),
                    country: Optional[str] = Query(None, description="Country code"),
                    db_ratings: sqlite3.Connection = Depends(get_ratings_db),
                    db_core: sqlite3.Connection = Depends(get_core_db)):
    
    # Check api_cache for the first page (top 100) if no country filter
    if not country and offset + limit <= 100:
        cursor = db_ratings.cursor()
        cursor.execute("SELECT cache_value FROM api_cache WHERE cache_key = ?", (f"leaderboard_{event}_{model}_{mode}_100_0",))
        row = cursor.fetchone()
        if row:
            import json
            full_data = json.loads(row['cache_value'])
            return full_data[offset:offset+limit]

    # Fallback to service if not in cache or complex query
    result = fetch_leaderboard_data(db_ratings, db_core, event, model, mode, limit, offset, period, country)
    
    # Add ranks
    for i, p in enumerate(result):
        p['rank'] = i + offset + 1
        if country:
            p['national_rank'] = i + offset + 1
            
    return result

# Removed /api/gainers and /api/leaderboard/fastest_increase as they are redundant
# Trending data is now served through /api/dashboard/trending using the precalculated stats

