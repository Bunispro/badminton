from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
import os
from typing import Optional
from datetime import datetime, timedelta

app = FastAPI()

CORE_DB = "bwf_data_2008-now__v1.sqlite"
RATINGS_DB = "elo_ratings.sqlite"

# Keep connections open globally
conn_core = sqlite3.connect(CORE_DB, check_same_thread=False)
conn_core.row_factory = sqlite3.Row

conn_ratings = sqlite3.connect(RATINGS_DB, check_same_thread=False)
conn_ratings.row_factory = sqlite3.Row

# Add indices for performance optimization
conn_ratings.execute("CREATE INDEX IF NOT EXISTS idx_whr_player_date ON whr_rating_history (run_id, event, player_id, rating_date)")
conn_ratings.execute("CREATE INDEX IF NOT EXISTS idx_elo_player_date ON rating_history (run_id, event, player_id, rating_date)")

@app.get("/")
def read_root():
    return FileResponse("web/frontend/index.html")

@app.get("/api/events")
def get_events():
    return ["MS", "WS", "MD", "WD", "XD"]

@app.get("/api/leaderboard")
def get_leaderboard(event: str = "MS", model: str = "whr", mode: str = "current"):
    two_years_ago = (datetime.now() - timedelta(days=730)).isoformat()[:10]
    if model == "whr":
        # Get latest run ID for WHR for this event
        cursor = conn_ratings.cursor()
        cursor.execute("SELECT run_id FROM whr_run_metadata WHERE run_id LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%_{event}",))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No WHR runs found")
        run_id = row['run_id']
        
        # Query leaderboard (latest or peak rating per player)
        if mode == "peak":
            query = """
                WITH ranked AS (
                    SELECT player_id, rating, rating_date, uncertainty,
                           ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY rating DESC) as rn
                    FROM whr_rating_history
                    WHERE run_id = ? AND event = ?
                )
                SELECT player_id, rating, rating_date, uncertainty
                FROM ranked
                WHERE rn = 1
                ORDER BY rating DESC
                LIMIT 100
            """
            cursor.execute(query, (run_id, event))
        else:
            query = """
                WITH ranked AS (
                    SELECT player_id, rating, rating_date, uncertainty,
                           ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY rating_date DESC) as rn
                    FROM whr_rating_history
                    WHERE run_id = ? AND event = ? AND rating_date >= ?
                )
                SELECT player_id, rating, rating_date, uncertainty
                FROM ranked
                WHERE rn = 1
                ORDER BY rating DESC
                LIMIT 100
            """
            cursor.execute(query, (run_id, event, two_years_ago))
            
        rows = cursor.fetchall()
        
    elif model == "elo":
        # Get latest run ID for Elo
        cursor = conn_ratings.cursor()
        cursor.execute("SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No Elo runs found")
        run_id = row['run_id']
        
        # Query leaderboard
        if mode == "peak":
            query = """
                WITH ranked AS (
                    SELECT player_id, rating, rating_date, rd,
                           ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY rating DESC) as rn
                    FROM rating_history
                    WHERE run_id = ? AND event = ?
                )
                SELECT player_id, rating, rating_date, rd
                FROM ranked
                WHERE rn = 1
                ORDER BY rating DESC
                LIMIT 100
            """
            cursor.execute(query, (run_id, event))
        else:
            query = """
                WITH ranked AS (
                    SELECT player_id, rating, rating_date, rd,
                           ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY rating_date DESC) as rn
                    FROM rating_history
                    WHERE run_id = ? AND event = ? AND rating_date >= ?
                )
                SELECT player_id, rating, rating_date, rd
                FROM ranked
                WHERE rn = 1
                ORDER BY rating DESC
                LIMIT 100
            """
            cursor.execute(query, (run_id, event, two_years_ago))
            
        rows = cursor.fetchall()
    else:
        raise HTTPException(status_code=400, detail="Invalid model")

    if not rows:
        return []

    # Map to dict and get names in ONE query (Fix N+1 problem)
    pids = [r['player_id'] for r in rows]
    placeholders = ",".join(["?"] * len(pids))
    
    cursor_core = conn_core.cursor()
    cursor_core.execute(f"SELECT player_id, name_normalized, name_display FROM players WHERE player_id IN ({placeholders})", pids)
    name_rows = cursor_core.fetchall()
    
    # Build a lookup dict
    name_map = {}
    for nr in name_rows:
        name_map[nr['player_id']] = nr['name_display'] or nr['name_normalized'] or nr['player_id']
        
    results = []
    for r in rows:
        pid = r['player_id']
        name = name_map.get(pid, pid)
        
        results.append({
            "player_id": pid,
            "name": name,
            "rating": round(r['rating'] + 1000, 1) if model == "whr" else round(r['rating'], 1),
            "uncertainty": round((r['uncertainty' if model == "whr" else 'rd'] or 0.0), 1),
            "date": r['rating_date']
        })
        
    return results

@app.get("/api/player/{id}/history")
def get_player_history(id: str, event: str = "MS", model: str = "whr"):
    if not id.isdigit() or len(id) > 10:
        raise HTTPException(status_code=400, detail="Invalid player ID")
        
    cursor = conn_ratings.cursor()
    if model == "whr":
        cursor.execute("SELECT run_id FROM whr_run_metadata WHERE run_id LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%_{event}",))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No WHR runs found")
        run_id = row['run_id']
        
        cursor.execute("""
            SELECT rating_date, rating, uncertainty
            FROM whr_rating_history
            WHERE run_id = ? AND event = ? AND player_id = ?
            ORDER BY rating_date ASC
        """, (run_id, event, id))
        
    elif model == "elo":
        cursor.execute("SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No Elo runs found")
        run_id = row['run_id']
        
        cursor.execute("""
            SELECT rating_date, rating, rd
            FROM rating_history
            WHERE run_id = ? AND event = ? AND player_id = ?
            ORDER BY rating_date ASC
        """, (run_id, event, id))
    else:
        raise HTTPException(status_code=400, detail="Invalid model")
        
    rows = cursor.fetchall()
    return [
        {
            "date": r['rating_date'], 
            "rating": round((r['rating'] or 0.0) + 1000, 1) if model == "whr" else round((r['rating'] or 0.0), 1),
            "uncertainty": round((r['uncertainty'] or 0.0), 2) if model == "whr" else round((r['rd'] or 0.0), 2)
        } 
        for r in rows
    ]

@app.get("/api/player/{id}/matches")
def get_player_matches(id: str):
    if not id.isdigit() or len(id) > 10:
        raise HTTPException(status_code=400, detail="Invalid player ID")
        
    cursor = conn_core.cursor()
    
    query = """
        SELECT 
            m.match_id,
            m.match_date,
            m.score,
            m.winner_side,
            m.event_canon,
            m.round,
            t.name as tournament_name,
            mp1.side as player_side,
            mp2.player_id as opponent_id,
            p.name_display as opponent_name
        FROM match_participants mp1
        JOIN matches m ON mp1.match_id = m.match_id
        LEFT JOIN tournaments t ON m.tournament_id = t.tournament_id
        JOIN match_participants mp2 ON m.match_id = mp2.match_id AND mp2.side != mp1.side
        LEFT JOIN players p ON mp2.player_id = p.player_id
        WHERE mp1.player_id = ?
        ORDER BY m.match_date DESC
    """
    
    cursor.execute(query, (id,))
    rows = cursor.fetchall()
    
    matches = {}
    for r in rows:
        mid = r['match_id']
        if mid not in matches:
            matches[mid] = {
                "match_id": mid,
                "date": r['match_date'],
                "score": r['score'],
                "winner_side": r['winner_side'],
                "tournament": r['tournament_name'],
                "event": r['event_canon'],
                "round": r['round'],
                "player_side": r['player_side'],
                "opponents": []
            }
        matches[mid]["opponents"].append({
            "id": r['opponent_id'],
            "name": r['opponent_name']
        })
        
    return list(matches.values())

@app.get("/api/predict")
def predict_match(p1: str, p2: str, event: str = "MS", model: str = "whr"):
    if not p1.isdigit() or not p2.isdigit() or len(p1) > 10 or len(p2) > 10:
        raise HTTPException(status_code=400, detail="Invalid player IDs")
        
    cursor = conn_ratings.cursor()
    
    # Get ratings for both players
    # For simplicity, we get the latest rating
    
    r1 = get_latest_rating(cursor, p1, event, model)
    r2 = get_latest_rating(cursor, p2, event, model)
    
    if r1 is None or r2 is None:
        raise HTTPException(status_code=404, detail="One or both players not found or have no rating")
        
    # Elo formula
    prob = 1.0 / (1.0 + 10.0 ** ((r2 - r1) / 400.0))
    
    return {
        "p1": p1,
        "p2": p2,
        "prob_p1": round(prob, 3),
        "prob_p2": round(1 - prob, 3),
        "r1": round(r1 + 1000, 1) if model == "whr" else round(r1, 1),
        "r2": round(r2 + 1000, 1) if model == "whr" else round(r2, 1)
    }

@app.get("/api/headtohead")
def get_head_to_head(p1: str, p2: str):
    if not p1.isdigit() or not p2.isdigit() or len(p1) > 10 or len(p2) > 10:
        raise HTTPException(status_code=400, detail="Invalid player IDs")
        
    cursor_core = conn_core.cursor()
    
    # Query matches where p1 and p2 played against each other
    cursor_core.execute("""
        SELECT m.match_id, m.match_date, m.score, m.winner_side, m.event_canon,
               t.name as tournament_name
        FROM matches m
        JOIN match_participants mp1 ON m.match_id = mp1.match_id AND mp1.player_id = ?
        JOIN match_participants mp2 ON m.match_id = mp2.match_id AND mp2.player_id = ?
        JOIN tournaments t ON m.tournament_id = t.tournament_id
        WHERE mp1.side != mp2.side
        ORDER BY m.match_date DESC
    """, (p1, p2))
    
    rows = cursor_core.fetchall()
    
    results = []
    for r in rows:
        results.append({
            "match_id": r['match_id'],
            "date": r['match_date'],
            "score": r['score'],
            "winner_side": r['winner_side'],
            "event": r['event_canon'],
            "tournament": r['tournament_name']
        })
        
    return results

@app.get("/api/player/{id}/uncertainty")
def get_player_uncertainty(id: str, event: str = "MS", model: str = "whr"):
    if not id.isdigit() or len(id) > 10:
        raise HTTPException(status_code=400, detail="Invalid player ID")
        
    cursor = conn_ratings.cursor()
    if model == "whr":
        cursor.execute("SELECT run_id FROM whr_run_metadata ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No WHR runs found")
        run_id = row['run_id']
        
        cursor.execute("""
            SELECT uncertainty
            FROM whr_rating_history
            WHERE run_id = ? AND event = ? AND player_id = ?
            ORDER BY rating_date DESC
            LIMIT 1
        """, (run_id, event, id))
        
    elif model == "elo":
        cursor.execute("SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No Elo runs found")
        run_id = row['run_id']
        
        cursor.execute("""
            SELECT rd
            FROM rating_history
            WHERE run_id = ? AND event = ? AND player_id = ?
            ORDER BY rating_date DESC
            LIMIT 1
        """, (run_id, event, id))
    else:
        raise HTTPException(status_code=400, detail="Invalid model")
        
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Player not found")
        
    return {"uncertainty": round(row['uncertainty' if model == "whr" else 'rd'], 2)}

@app.get("/api/countries")
def get_countries():
    cursor = conn_core.cursor()
    cursor.execute("SELECT DISTINCT country_code FROM players WHERE country_code IS NOT NULL AND country_code != '' ORDER BY country_code")
    rows = cursor.fetchall()
    return [r['country_code'] for r in rows]

@app.get("/api/gainers")
def get_gainers(event: str = "MS", model: str = "whr", period: str = "3months"):
    cursor = conn_ratings.cursor()
    if model == "whr":
        cursor.execute("SELECT run_id FROM whr_run_metadata WHERE run_id LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%_{event}",))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No WHR runs found")
        run_id = row['run_id']
        
        cursor.execute("SELECT MAX(rating_date) as max_date FROM whr_rating_history WHERE run_id = ?", (run_id,))
        max_date_str = cursor.fetchone()['max_date']
    elif model == "elo":
        cursor.execute("SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No Elo runs found")
        run_id = row['run_id']
        
        cursor.execute("SELECT MAX(rating_date) as max_date FROM rating_history WHERE run_id = ?", (run_id,))
        max_date_str = cursor.fetchone()['max_date']
    else:
        raise HTTPException(status_code=400, detail="Invalid model")
        
    if not max_date_str:
        raise HTTPException(status_code=404, detail="No ratings found")
        
    max_date = datetime.fromisoformat(max_date_str)
    
    if period == "month":
        target_date = max_date - timedelta(days=30)
    elif period == "3months":
        target_date = max_date - timedelta(days=90)
    elif period == "6months":
        target_date = max_date - timedelta(days=180)
    elif period == "year":
        target_date = max_date - timedelta(days=365)
    else:
        raise HTTPException(status_code=400, detail="Invalid period")
        
    target_date_str = target_date.isoformat()[:10] # YYYY-MM-DD
    
    table = "whr_rating_history" if model == "whr" else "rating_history"
    
    query = f"""
        WITH latest_ratings AS (
            SELECT player_id, rating, rating_date,
                   ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY rating_date DESC) as rn
            FROM {table}
            WHERE run_id = ? AND event = ?
        ),
        past_ratings AS (
            SELECT player_id, rating, rating_date,
                   ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY rating_date DESC) as rn
            FROM {table}
            WHERE run_id = ? AND event = ? AND rating_date <= ?
        )
        SELECT l.player_id, l.rating as current_rating, p.rating as past_rating,
               (l.rating - p.rating) as gain
        FROM latest_ratings l
        JOIN past_ratings p ON l.player_id = p.player_id AND p.rn = 1
        WHERE l.rn = 1
        ORDER BY gain DESC
        LIMIT 10
    """
    
    cursor.execute(query, (run_id, event, run_id, event, target_date_str))
    rows = cursor.fetchall()
    
    pids = [r['player_id'] for r in rows]
    if not pids:
        return []
        
    placeholders = ",".join(["?"] * len(pids))
    cursor_core = conn_core.cursor()
    cursor_core.execute(f"SELECT player_id, name_normalized, name_display, country_code FROM players WHERE player_id IN ({placeholders})", pids)
    name_rows = cursor_core.fetchall()
    
    name_map = {}
    country_map = {}
    for nr in name_rows:
        name_map[nr['player_id']] = nr['name_display'] or nr['name_normalized'] or nr['player_id']
        country_map[nr['player_id']] = nr['country_code']
        
    results = []
    for r in rows:
        pid = r['player_id']
        results.append({
            "player_id": pid,
            "name": name_map.get(pid, pid),
            "country": country_map.get(pid, ""),
            "gain": round(r['gain'], 1),
            "current_rating": round(r['current_rating'] + 1000, 1) if model == "whr" else round(r['current_rating'], 1),
            "past_rating": round(r['past_rating'] + 1000, 1) if model == "whr" else round(r['past_rating'], 1)
        })
        
    return results

def get_latest_rating(cursor, player_id, event, model):
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
        cursor.execute("SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1")
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
    else:
        return None
        
    row = cursor.fetchone()
    return row['rating'] if row else None

# Mount static files (must be at the end or carefully ordered)
# We serve the frontend directory
app.mount("/static", StaticFiles(directory="web/frontend"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
