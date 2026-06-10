import sqlite3
from typing import Optional

def get_latest_rating(cursor: sqlite3.Cursor, player_id: str, event: str, model: str) -> Optional[float]:
    """
    Fetch the latest rating for a given player, event, and model.
    Returns the rating value as a float, or None if not found.
    """
    if model == "whr":
        cursor.execute("SELECT run_id FROM whr_run_metadata WHERE run_id LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%_{event}",))
        row = cursor.fetchone()
        if not row:
            return None
        run_id = row['run_id']
        
        cursor.execute("""
            SELECT rating
            FROM whr_rating_history
            WHERE run_id = ? AND event = ? AND player_id = ?
            ORDER BY rating_date DESC
            LIMIT 1
        """, (run_id, event, player_id))
        
    elif model == "elo":
        cursor.execute("SELECT run_id FROM run_metadata WHERE run_id LIKE '%final%' ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return None
        run_id = row['run_id']
        
        cursor.execute("""
            SELECT rating
            FROM rating_history
            WHERE run_id = ? AND event = ? AND player_id = ?
            ORDER BY rating_date DESC
            LIMIT 1
        """, (run_id, event, player_id))
    elif model == "bwf":
        cursor.execute("""
            SELECT points as rating
            FROM bwf_historical_rankings
            WHERE event = ? AND player_id = ?
            ORDER BY rank_date DESC
            LIMIT 1
        """, (event, player_id))
    else:
        return None
        
    row = cursor.fetchone()
    return row['rating'] if row else None
