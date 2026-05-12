from fastapi import FastAPI, HTTPException, Request, Query, Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
import os
from typing import Optional, Literal
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

CORE_DB = os.getenv("CORE_DB", "bwf_data_2008-now__v1.sqlite")
RATINGS_DB = os.getenv("RATINGS_DB", "elo_ratings.sqlite")

# Ensure indices exist on startup
with sqlite3.connect(RATINGS_DB) as conn:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_whr_player_date ON whr_rating_history (run_id, event, player_id, rating_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_elo_player_date ON rating_history (run_id, event, player_id, rating_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_whr_player_rating ON whr_rating_history (run_id, event, player_id, rating DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_elo_player_rating ON rating_history (run_id, event, player_id, rating DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_whr_rating_rank ON whr_rating_history (run_id, event, rating_date, rating DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_elo_rating_rank ON rating_history (run_id, event, rating_date, rating DESC)")

from fastapi import Depends

def get_ratings_db():
    conn = sqlite3.connect(RATINGS_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_core_db():
    conn = sqlite3.connect(CORE_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@app.get("/")
def read_root():
    return {"status": "API is running", "version": "1.0.0"}

@app.get("/api/events")
def get_events():
    return ["MS", "WS", "MD", "WD", "XD"]

@app.get("/api/leaderboard")
@limiter.limit("100/minute")
def get_leaderboard(request: Request, 
                    event: Literal["MS", "WS", "MD", "WD", "XD"] = "MS", 
                    model: Literal["whr", "elo"] = "whr", 
                    mode: Literal["current", "peak"] = "current",
                    limit: int = Query(50, ge=1, le=200),
                    offset: int = Query(0, ge=0),
                    period: str = Query("1m", description="Period for rating changes (7d, 1m, 3m, 6m, 1y, 2y, 3y)"),
                    db_ratings: sqlite3.Connection = Depends(get_ratings_db),
                    db_core: sqlite3.Connection = Depends(get_core_db)):
    
    cursor = db_ratings.cursor()

    
    try:
        if model == "whr":
            # Get latest run ID for WHR for this event
            cursor.execute("SELECT run_id FROM whr_run_metadata WHERE run_id LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%_{event}",))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="No WHR runs found")
            run_id = row['run_id']
            
            cursor.execute("SELECT MAX(rating_date) FROM whr_rating_history WHERE run_id = ?", (run_id,))
            latest_date = cursor.fetchone()[0]
            
            # Query leaderboard (latest or peak rating per player)
            if mode == "peak":
                query = """
                    SELECT player_id, MAX(rating) as rating, rating_date, uncertainty
                    FROM whr_rating_history
                    WHERE run_id = ? AND event = ?
                    GROUP BY player_id
                    ORDER BY rating DESC
                    LIMIT ? OFFSET ?
                """
                cursor.execute(query, (run_id, event, limit, offset))
            else:
                two_years_ago = (datetime.strptime(latest_date, "%Y-%m-%d") - timedelta(days=547)).strftime("%Y-%m-%d")
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
                    LIMIT ? OFFSET ?
                """
                cursor.execute(query, (run_id, event, two_years_ago, limit, offset))
                
        elif model == "elo":
            cursor.execute("SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="No Elo runs found")
            run_id = row['run_id']
            
            cursor.execute("SELECT MAX(rating_date) FROM rating_history WHERE run_id = ?", (run_id,))
            latest_date = cursor.fetchone()[0]
            
            if mode == "peak":
                query = """
                    SELECT player_id, MAX(rating) as rating, rating_date, rd
                    FROM rating_history
                    WHERE run_id = ? AND event = ?
                    GROUP BY player_id
                    ORDER BY rating DESC
                    LIMIT ? OFFSET ?
                """
                cursor.execute(query, (run_id, event, limit, offset))
            else:
                two_years_ago = (datetime.strptime(latest_date, "%Y-%m-%d") - timedelta(days=547)).strftime("%Y-%m-%d")
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
                    LIMIT ? OFFSET ?
                """
                cursor.execute(query, (run_id, event, two_years_ago, limit, offset))
                
        else:
            raise HTTPException(status_code=400, detail="Invalid model")

        rows = cursor.fetchall()
        
        if not rows:
            return []

        # Calculate past date
        latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")
        if period == "7d":
            past_dt = latest_dt - timedelta(days=7)
        elif period == "1m":
            past_dt = latest_dt - timedelta(days=30)
        elif period == "3m":
            past_dt = latest_dt - timedelta(days=90)
        elif period == "6m":
            past_dt = latest_dt - timedelta(days=180)
        elif period == "1y":
            past_dt = latest_dt - timedelta(days=365)
        elif period == "2y":
            past_dt = latest_dt - timedelta(days=730)
        elif period == "3y":
            past_dt = latest_dt - timedelta(days=1095)
        else:
            past_dt = latest_dt - timedelta(days=30)
            
        past_date = past_dt.strftime("%Y-%m-%d")

        # Map to dict and get names in ONE query (Fix N+1 problem)
        pids = [r['player_id'] for r in rows]
        placeholders = ",".join(["?"] * len(pids))
        
        cursor_core = db_core.cursor()
        cursor_core.execute(f"SELECT player_id, name_normalized, name_display, country_code FROM players WHERE player_id IN ({placeholders})", pids)
        name_rows = cursor_core.fetchall()
        
        # Build a lookup dict
        player_info = {}
        for nr in name_rows:
            player_info[nr['player_id']] = {
                "name": nr['name_display'] or nr['name_normalized'] or nr['player_id'],
                "country": nr['country_code']
            }
            
        # Fetch rating at past_date
        table_name = "whr_rating_history" if model == "whr" else "rating_history"
        cursor.execute(f"""
            WITH ranked AS (
                SELECT player_id, rating, rating_date,
                       ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY ABS(julianday(rating_date) - julianday(?))) as rn
                FROM {table_name}
                WHERE run_id = ? AND event = ? AND player_id IN ({placeholders})
            )
            SELECT player_id, rating, rating_date
            FROM ranked
            WHERE rn = 1
        """, [past_date, run_id, event] + pids)
        past_rows = cursor.fetchall()
        
        past_rating_map = {r['player_id']: r['rating'] for r in past_rows}
            
        # Fetch top 10 matches for each player in ONE query
        cursor_core.execute(f"""
            WITH ranked_matches AS (
                SELECT 
                    mp.player_id,
                    m.match_id,
                    ROW_NUMBER() OVER(PARTITION BY mp.player_id ORDER BY m.match_date DESC) as rn
                FROM match_participants mp
                JOIN matches m ON mp.match_id = m.match_id
                WHERE mp.player_id IN ({placeholders}) AND m.is_valid_for_rating = 1
            )
            SELECT player_id, match_id FROM ranked_matches WHERE rn <= 10
        """, pids)
        match_id_rows = cursor_core.fetchall()
        
        # Group match IDs by player
        player_matches_map = {}
        all_match_ids = set()
        for mr in match_id_rows:
            pid = mr['player_id']
            mid = mr['match_id']
            if pid not in player_matches_map:
                player_matches_map[pid] = []
            player_matches_map[pid].append(mid)
            all_match_ids.add(mid)
            
        matches_data = {}
        if all_match_ids:
            match_placeholders = ",".join(["?"] * len(all_match_ids))
            cursor_core.execute(f"""
                SELECT 
                    m.match_id,
                    m.match_date,
                    m.score,
                    m.winner_side,
                    m.event_canon,
                    m.round,
                    t.name as tournament_name,
                    mp.side,
                    mp.player_id,
                    p.name_display,
                    p.country_code
                FROM match_participants mp
                JOIN matches m ON mp.match_id = m.match_id
                LEFT JOIN tournaments t ON m.tournament_id = t.tournament_id
                LEFT JOIN players p ON mp.player_id = p.player_id
                WHERE m.match_id IN ({match_placeholders})
                ORDER BY m.match_date DESC
            """, list(all_match_ids))
            full_match_rows = cursor_core.fetchall()
            
            for r in full_match_rows:
                mid = r['match_id']
                if mid not in matches_data:
                    matches_data[mid] = {
                        "match_id": mid,
                        "date": r['match_date'],
                        "score": r['score'],
                        "winner_side": r['winner_side'],
                        "tournament": r['tournament_name'],
                        "event": r['event_canon'],
                        "round": r['round'],
                        "side1": [],
                        "side2": []
                    }
                
                participant = {
                    "id": r['player_id'],
                    "name": r['name_display'],
                    "country": r['country_code']
                }
                
                if r['side'] == 1:
                    matches_data[mid]["side1"].append(participant)
                else:
                    matches_data[mid]["side2"].append(participant)
            
        results = []
        for r in rows:
            pid = r['player_id']
            info = player_info.get(pid, {"name": pid, "country": None})
            
            current_rating = r['rating']
            past_rating = past_rating_map.get(pid, current_rating)
            change = round(current_rating - past_rating, 1)
            
            results.append({
                "player_id": pid,
                "name": info["name"],
                "country": info["country"],
                "rating": round(current_rating + 1000, 1) if model == "whr" else round(current_rating, 1),
                "uncertainty": round((r['uncertainty' if model == "whr" else 'rd'] or 0.0), 1),
                "date": r['rating_date'],
                "change": change,
                "recent_matches": [matches_data[mid] for mid in player_matches_map.get(pid, []) if mid in matches_data]
            })
            
        return results
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_leaderboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/players/search")
@limiter.limit("30/minute")
def search_players(request: Request, q: str = Query(..., min_length=2), db: sqlite3.Connection = Depends(get_core_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT player_id, name_display, name_normalized 
        FROM players 
        WHERE name_display LIKE ? OR name_normalized LIKE ? 
        LIMIT 10
    """, (f"%{q}%", f"%{q}%"))
    rows = cursor.fetchall()
    return [{"id": r['player_id'], "name": r['name_display'] or r['name_normalized']} for r in rows]

@app.get("/api/player/{id}")
def get_player_details(id: str = Path(..., max_length=10), db_core: sqlite3.Connection = Depends(get_core_db), db_ratings: sqlite3.Connection = Depends(get_ratings_db)):
    cursor_core = db_core.cursor()
    cursor_core.execute("SELECT name_display, name_normalized, country_code FROM players WHERE player_id = ?", (id,))
    row = cursor_core.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Player not found")
        
    cursor_core.execute("""
        SELECT DISTINCT event_canon 
        FROM matches m
        JOIN match_participants mp ON m.match_id = mp.match_id
        WHERE mp.player_id = ? AND m.is_valid_for_rating = 1
    """, (id,))
    events = [r['event_canon'] for r in cursor_core.fetchall() if r['event_canon']]
    
    return {"id": id, "name": row['name_display'] or row['name_normalized'], "country": row['country_code'], "disciplines": events}

@app.get("/api/player/{id}/history")
def get_player_history(id: str = Path(..., max_length=10), event: str = "MS", model: str = "elo", db: sqlite3.Connection = Depends(get_ratings_db)):
        
    cursor = db.cursor()
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
    
    # Find peak point
    peak_date = None
    if rows:
        peak_row = max(rows, key=lambda x: x['rating'] or 0)
        peak_date = peak_row['rating_date']
        
    # Find partner for peak point if doubles
    peak_partner = None
    if peak_date and event in ['MD', 'WD', 'XD']:
        from datetime import datetime, timedelta
        try:
            p_date = datetime.strptime(peak_date, "%Y-%m-%d")
            start_date = (p_date - timedelta(days=90)).strftime("%Y-%m-%d")
            
            core_conn = sqlite3.connect(CORE_DB)
            core_conn.row_factory = sqlite3.Row
            core_cursor = core_conn.cursor()
            
            core_cursor.execute("""
                SELECT p.name_display, count(*) as count
                FROM matches m
                JOIN match_participants mp1 ON m.match_id = mp1.match_id AND mp1.player_id = ?
                JOIN match_participants mp2 ON m.match_id = mp2.match_id AND mp2.player_id != ? AND mp1.side = mp2.side
                JOIN players p ON mp2.player_id = p.player_id
                WHERE m.event_canon = ? AND m.match_date BETWEEN ? AND ? AND m.is_valid_for_rating = 1
                GROUP BY mp2.player_id
                ORDER BY count DESC
                LIMIT 1
            """, (id, id, event, start_date, peak_date))
            
            partner_row = core_cursor.fetchone()
            if partner_row:
                peak_partner = partner_row['name_display']
                
            core_conn.close()
        except Exception as e:
            print(f"Error finding partner: {e}")
            
    result = []
    for r in rows:
        rating_date = r['rating_date']
        rating = r['rating']
        
        # Query rank
        if model == "whr":
            cursor.execute("""
                SELECT count(*) + 1 as rank 
                FROM whr_rating_history 
                WHERE run_id = ? AND event = ? AND rating_date = ? AND rating > ?
            """, (run_id, event, rating_date, rating))
        else:
            cursor.execute("""
                SELECT rank 
                FROM ranking_history 
                WHERE run_id = ? AND event = ? AND player_id = ? AND rating_date = ?
            """, (run_id, event, id, rating_date))
            
        rank_row = cursor.fetchone()
        rank = rank_row['rank'] if rank_row else None
        
        item = {
            "date": rating_date, 
            "rating": round((rating or 0.0) + 1000, 1) if model == "whr" else round((rating or 0.0), 1),
            "uncertainty": round((r['uncertainty'] or 0.0), 2) if model == "whr" else round((r['rd'] or 0.0), 2),
            "rank": rank
        }
        
        if rating_date == peak_date and peak_partner:
            item["partner"] = peak_partner
            
        result.append(item)
        
    return result

@app.get("/api/player/{id}/matches")
def get_player_matches(id: str = Path(...), 
                       event: str = Query(None), 
                       limit: int = Query(20, ge=1, le=100),
                       offset: int = Query(0, ge=0),
                       db: sqlite3.Connection = Depends(get_core_db)):
        
    cursor = db.cursor()
    
    if event:
        cursor.execute("""
            SELECT m.match_id 
            FROM matches m
            JOIN match_participants mp ON m.match_id = mp.match_id
            WHERE mp.player_id = ? AND m.event_canon = ? AND m.is_valid_for_rating = 1
            ORDER BY m.match_date DESC
            LIMIT ? OFFSET ?
        """, (id, event, limit, offset))
    else:
        cursor.execute("""
            SELECT m.match_id 
            FROM matches m
            JOIN match_participants mp ON m.match_id = mp.match_id
            WHERE mp.player_id = ? AND m.is_valid_for_rating = 1
            ORDER BY m.match_date DESC
            LIMIT ? OFFSET ?
        """, (id, limit, offset))
        
    match_ids = [r['match_id'] for r in cursor.fetchall()]
    
    if not match_ids:
        return []
        
    placeholders = ",".join(["?"] * len(match_ids))
    
    query = f"""
        SELECT 
            m.match_id,
            m.match_date,
            m.score,
            m.winner_side,
            m.event_canon,
            m.round,
            t.name as tournament_name,
            mp.side,
            mp.player_id,
            p.name_display,
            p.country_code
        FROM match_participants mp
        JOIN matches m ON mp.match_id = m.match_id
        LEFT JOIN tournaments t ON m.tournament_id = t.tournament_id
        LEFT JOIN players p ON mp.player_id = p.player_id
        WHERE m.match_id IN ({placeholders})
        ORDER BY m.match_date DESC
    """
    
    cursor.execute(query, match_ids)
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
                "side1": [],
                "side2": []
            }
        
        participant = {
            "id": r['player_id'],
            "name": r['name_display'],
            "country": r['country_code']
        }
        
        if r['side'] == 1:
            matches[mid]["side1"].append(participant)
        else:
            matches[mid]["side2"].append(participant)
            
    return list(matches.values())

@app.get("/api/predict")
@limiter.limit("10/minute")
def predict_match(request: Request, 
                  p1: str = Query(..., max_length=10), 
                  p2: str = Query(..., max_length=10), 
                  event: str = "MS", 
                  model: str = "whr",
                  db: sqlite3.Connection = Depends(get_ratings_db)):
        
    cursor = db.cursor()
    
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

@app.get("/api/player/{id}/synergy")
def get_player_synergy(id: str = Path(..., max_length=10), 
                       event: str = Query(..., pattern="^(MD|WD|XD)$"),
                       db: sqlite3.Connection = Depends(get_ratings_db)):
    
    cursor = db.cursor()
    
    # Get latest run_id for event
    cursor.execute("SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1")
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No Elo runs found")
    run_id = row['run_id']
    
    # Query synergy
    cursor.execute("""
        SELECT 
            CASE WHEN player1_id = ? THEN player2_id ELSE player1_id END as partner_id,
            synergy
        FROM pair_synergy_current
        WHERE run_id = ? AND event = ? AND (player1_id = ? OR player2_id = ?)
        ORDER BY synergy DESC
    """, (id, run_id, event, id, id))
    
    rows = cursor.fetchall()
    
    if not rows:
        return []
        
    # Fetch partner names from core DB
    partner_ids = [r['partner_id'] for r in rows]
    placeholders = ",".join(["?"] * len(partner_ids))
    
    import os
    CORE_DB = os.getenv("CORE_DB", "bwf_data_2008-now__v1.sqlite")
    
    core_conn = sqlite3.connect(CORE_DB)
    core_conn.row_factory = sqlite3.Row
    core_cursor = core_conn.cursor()
    
    core_cursor.execute(f"""
        SELECT player_id, name_display
        FROM players
        WHERE player_id IN ({placeholders})
    """, partner_ids)
    
    name_rows = core_cursor.fetchall()
    name_map = {r['player_id']: r['name_display'] for r in name_rows}
    core_conn.close()
    
    result = []
    for r in rows:
        pid = r['partner_id']
        result.append({
            "partner_id": pid,
            "partner_name": name_map.get(pid, f"Player {pid}"),
            "synergy": round(r['synergy'], 3)
        })
        
    return result

@app.get("/api/player/{id}/stats")
def get_player_stats(id: str = Path(...), 
                     event: str = Query(...),
                     period: str = Query("all"),
                     db_core: sqlite3.Connection = Depends(get_core_db),
                     db_ratings: sqlite3.Connection = Depends(get_ratings_db)):
    
    from datetime import datetime, timedelta
    now = datetime.now()
    start_date = "2000-01-01" 
    if period == "1m":
        start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    elif period == "3m":
        start_date = (now - timedelta(days=90)).strftime("%Y-%m-%d")
    elif period == "6m":
        start_date = (now - timedelta(days=180)).strftime("%Y-%m-%d")
        
    cursor_core = db_core.cursor()
    
    cursor_core.execute("""
        SELECT 
            count(m.match_id) as total,
            sum(case when m.winner_side = mp.side then 1 else 0 end) as wins
        FROM matches m
        JOIN match_participants mp ON m.match_id = mp.match_id AND mp.player_id = ?
        WHERE m.event_canon = ? AND m.match_date >= ? AND m.is_valid_for_rating = 1
    """, (id, event, start_date))
    
    stats_row = cursor_core.fetchone()
    total_matches = stats_row['total'] if stats_row else 0
    wins = stats_row['wins'] if stats_row and stats_row['wins'] else 0
    win_rate = round((wins / total_matches * 100), 1) if total_matches > 0 else 0.0
    
    synergy_list = []
    opponents_list = []
    if event in ['MD', 'WD', 'XD']:
        cursor_ratings = db_ratings.cursor()
        cursor_ratings.execute("SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1")
        run_row = cursor_ratings.fetchone()
        if run_row:
            run_id = run_row['run_id']
            
            cursor_ratings.execute("""
                SELECT 
                    CASE WHEN player1_id = ? THEN player2_id ELSE player1_id END as partner_id,
                    synergy
                FROM pair_synergy_current
                WHERE run_id = ? AND event = ? AND (player1_id = ? OR player2_id = ?)
                ORDER BY synergy DESC
            """, (id, run_id, event, id, id))
            
            syn_rows = cursor_ratings.fetchall()
            
            if syn_rows:
                partner_ids = [r['partner_id'] for r in syn_rows]
                placeholders = ",".join(["?"] * len(partner_ids))
                
                query = f"""
                    SELECT 
                        mp2.player_id as partner_id,
                        count(m.match_id) as total,
                        sum(case when m.winner_side = mp1.side then 1 else 0 end) as wins
                    FROM matches m
                    JOIN match_participants mp1 ON m.match_id = mp1.match_id AND mp1.player_id = ?
                    JOIN match_participants mp2 ON m.match_id = mp2.match_id AND mp2.player_id != ? AND mp1.side = mp2.side
                    WHERE m.event_canon = ? AND m.match_date >= ? AND m.is_valid_for_rating = 1
                      AND mp2.player_id IN ({placeholders})
                    GROUP BY mp2.player_id
                """
                
                cursor_core.execute(query, (id, id, event, start_date, *partner_ids))
                partner_stats = cursor_core.fetchall()
                
                stats_map = {r['partner_id']: {"total": r['total'], "wins": r['wins']} for r in partner_stats}
                
                cursor_core.execute(f"""
                    SELECT player_id, name_display
                    FROM players
                    WHERE player_id IN ({placeholders})
                """, partner_ids)
                
                name_rows = cursor_core.fetchall()
                name_map = {r['player_id']: r['name_display'] for r in name_rows}
                
                for r in syn_rows:
                    pid = r['partner_id']
                    p_stats = stats_map.get(pid, {"total": 0, "wins": 0})
                    p_total = p_stats['total']
                    p_wins = p_stats['wins'] if p_stats['wins'] else 0
                    p_win_rate = round((p_wins / p_total * 100), 1) if p_total > 0 else 0.0
                    
                    synergy_list.append({
                        "partner_id": pid,
                        "partner_name": name_map.get(pid, f"Player {pid}"),
                        "synergy": round(r['synergy'], 3),
                        "win_rate": p_win_rate,
                        "total_matches": p_total
                    })
                    
    if event in ['MS', 'WS']:
        cursor_core.execute("""
            SELECT 
                mp2.player_id as opponent_id,
                count(m.match_id) as total,
                sum(case when m.winner_side = mp1.side then 1 else 0 end) as wins
            FROM matches m
            JOIN match_participants mp1 ON m.match_id = mp1.match_id AND mp1.player_id = ?
            JOIN match_participants mp2 ON m.match_id = mp2.match_id AND mp1.side != mp2.side
            WHERE m.event_canon = ? AND m.match_date >= ? AND m.is_valid_for_rating = 1
            GROUP BY mp2.player_id
            ORDER BY total DESC
            LIMIT 4
        """, (id, event, start_date))
        
        opp_rows = cursor_core.fetchall()
        
        if opp_rows:
            opp_ids = [r['opponent_id'] for r in opp_rows]
            placeholders = ",".join(["?"] * len(opp_ids))
            
            cursor_core.execute(f"""
                SELECT player_id, name_display
                FROM players
                WHERE player_id IN ({placeholders})
            """, opp_ids)
            
            name_rows = cursor_core.fetchall()
            name_map = {r['player_id']: r['name_display'] for r in name_rows}
            
            for r in opp_rows:
                oid = r['opponent_id']
                o_total = r['total']
                o_wins = r['wins'] if r['wins'] else 0
                o_win_rate = round((o_wins / o_total * 100), 1) if o_total > 0 else 0.0
                
                opponents_list.append({
                    "opponent_id": oid,
                    "opponent_name": name_map.get(oid, f"Player {oid}"),
                    "win_rate": o_win_rate,
                    "total_matches": o_total,
                    "wins": o_wins
                })
                
    return {
        "player_id": id,
        "event": event,
        "period": period,
        "total_matches": total_matches,
        "wins": wins,
        "win_rate": win_rate,
        "synergy": synergy_list,
        "opponents": opponents_list
    }

fastest_increase_cache = {}

@app.get("/api/leaderboard/fastest_increase")
def get_fastest_increase(event: str = Query(..., pattern="^(MS|WS|MD|WD|XD)$"),
                         period: str = Query("1m", pattern="^(1m|3m|6m)$"),
                         model: str = Query("elo", pattern="^(elo|whr)$"),
                         db: sqlite3.Connection = Depends(get_ratings_db)):
    
    cursor = db.cursor()
    
    if model == "elo":
        cursor.execute("SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No Elo runs found")
        run_id = row['run_id']
        table_name = "rating_history"
        uncertainty_threshold = 100
    else:
        cursor.execute("SELECT run_id FROM whr_run_metadata ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No WHR runs found")
        run_id = row['run_id']
        table_name = "whr_rating_history"
        uncertainty_threshold = 0.5
        
    cache_key = (run_id, event, period, model)
    if cache_key in fastest_increase_cache:
        return fastest_increase_cache[cache_key]
        
    from datetime import datetime, timedelta
    now = datetime.now()
    if period == "1m":
        days = 30
    elif period == "3m":
        days = 90
    elif period == "6m":
        days = 180
        
    start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    
    cursor.execute(f"""
        SELECT MIN(rating_date) FROM {table_name} WHERE run_id = ? AND rating_date >= ?
    """, (run_id, start_date))
    db_start_date = cursor.fetchone()[0]
    
    cursor.execute(f"""
        SELECT MAX(rating_date) FROM {table_name} WHERE run_id = ?
    """, (run_id,))
    db_end_date = cursor.fetchone()[0]
    
    if not db_start_date or not db_end_date:
        return []
        
    if model == "elo":
        cursor.execute("""
            WITH latest_start_date AS (
                SELECT player_id, MAX(rating_date) as rating_date
                FROM rating_history
                WHERE run_id = ? AND event = ? AND rating_date <= ?
                GROUP BY player_id
            ),
            latest_end_date AS (
                SELECT player_id, MAX(rating_date) as rating_date
                FROM rating_history
                WHERE run_id = ? AND event = ? AND rating_date <= ?
                GROUP BY player_id
            ),
            start_ratings AS (
                SELECT r.player_id, r.rating, r.rd
                FROM rating_history r
                JOIN latest_start_date l ON r.player_id = l.player_id AND r.rating_date = l.rating_date
                WHERE r.run_id = ? AND r.event = ?
            ),
            end_ratings AS (
                SELECT r.player_id, r.rating, r.rd
                FROM rating_history r
                JOIN latest_end_date l ON r.player_id = l.player_id AND r.rating_date = l.rating_date
                WHERE r.run_id = ? AND r.event = ?
            )
            SELECT e.player_id, (e.rating - s.rating) as increase
            FROM end_ratings e
            JOIN start_ratings s ON e.player_id = s.player_id
            WHERE (s.rd IS NULL OR s.rd < ?) AND (e.rd IS NULL OR e.rd < ?)
            ORDER BY increase DESC
            LIMIT 5
        """, (run_id, event, db_start_date, run_id, event, db_end_date, run_id, event, run_id, event, uncertainty_threshold, uncertainty_threshold))
    else:
        cursor.execute("""
            WITH latest_start_date AS (
                SELECT player_id, MAX(rating_date) as rating_date
                FROM whr_rating_history
                WHERE run_id = ? AND event = ? AND rating_date <= ?
                GROUP BY player_id
            ),
            latest_end_date AS (
                SELECT player_id, MAX(rating_date) as rating_date
                FROM whr_rating_history
                WHERE run_id = ? AND event = ? AND rating_date <= ?
                GROUP BY player_id
            ),
            start_ratings AS (
                SELECT r.player_id, r.rating, u.uncertainty
                FROM whr_rating_history r
                JOIN latest_start_date l ON r.player_id = l.player_id AND r.rating_date = l.rating_date
                LEFT JOIN uncertainty_history u ON r.run_id = u.run_id AND r.event = u.event AND r.player_id = u.player_id AND r.rating_date = u.snapshot_date
                WHERE r.run_id = ? AND r.event = ?
            ),
            end_ratings AS (
                SELECT r.player_id, r.rating, u.uncertainty
                FROM whr_rating_history r
                JOIN latest_end_date l ON r.player_id = l.player_id AND r.rating_date = l.rating_date
                LEFT JOIN uncertainty_history u ON r.run_id = u.run_id AND r.event = u.event AND r.player_id = u.player_id AND r.rating_date = u.snapshot_date
                WHERE r.run_id = ? AND r.event = ?
            )
            SELECT e.player_id, (e.rating - s.rating) as increase
            FROM end_ratings e
            JOIN start_ratings s ON e.player_id = s.player_id
            WHERE (s.uncertainty IS NULL OR s.uncertainty < ?) AND (e.uncertainty IS NULL OR e.uncertainty < ?)
            ORDER BY increase DESC
            LIMIT 5
        """, (run_id, event, db_start_date, run_id, event, db_end_date, run_id, event, run_id, event, uncertainty_threshold, uncertainty_threshold))
        
    rows = cursor.fetchall()
    
    player_ids = [r['player_id'] for r in rows]
    if not player_ids:
        return []
        
    placeholders = ",".join(["?"] * len(player_ids))
    
    import os
    CORE_DB = os.getenv("CORE_DB", "bwf_data_2008-now__v1.sqlite")
    core_conn = sqlite3.connect(CORE_DB)
    core_conn.row_factory = sqlite3.Row
    core_cursor = core_conn.cursor()
    
    core_cursor.execute(f"""
        SELECT player_id, name_display
        FROM players
        WHERE player_id IN ({placeholders})
    """, player_ids)
    
    name_rows = core_cursor.fetchall()
    name_map = {r['player_id']: r['name_display'] for r in name_rows}
    core_conn.close()
    
    result = []
    for r in rows:
        pid = r['player_id']
        result.append({
            "player_id": pid,
            "player_name": name_map.get(pid, f"Player {pid}"),
            "increase": round(r['increase'], 1)
        })
        
    fastest_increase_cache[cache_key] = result
    return result

@app.get("/api/headtohead")
def get_head_to_head(p1: str = Query(..., max_length=10), 
                     p2: str = Query(..., max_length=10),
                     db: sqlite3.Connection = Depends(get_core_db)):
        
    cursor_core = db.cursor()
    
    # Query matches where p1 and p2 played against each other
    cursor_core.execute("""
        SELECT m.match_id, m.match_date, m.score, m.winner_side, m.event_canon,
               t.name as tournament_name
        FROM matches m
        JOIN match_participants mp1 ON m.match_id = mp1.match_id AND mp1.player_id = ?
        JOIN match_participants mp2 ON m.match_id = mp2.match_id AND mp2.player_id = ?
        JOIN tournaments t ON m.tournament_id = t.tournament_id
        WHERE mp1.side != mp2.side AND m.is_valid_for_rating = 1
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
def get_player_uncertainty(id: str = Path(..., max_length=10), event: str = "MS", model: str = "elo", db: sqlite3.Connection = Depends(get_ratings_db)):
        
    cursor = db.cursor()
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
def get_countries(db: sqlite3.Connection = Depends(get_core_db)):
    cursor = db.cursor()
    cursor.execute("SELECT DISTINCT country_code FROM players WHERE country_code IS NOT NULL AND country_code != '' ORDER BY country_code")
    rows = cursor.fetchall()
    return [r['country_code'] for r in rows]

@app.get("/api/gainers")
def get_gainers(event: Literal["MS", "WS", "MD", "WD", "XD"] = "MS", 
               model: Literal["whr", "elo"] = "whr", 
               period: Literal["month", "3months", "6months", "year"] = "3months",
               db_ratings: sqlite3.Connection = Depends(get_ratings_db),
               db_core: sqlite3.Connection = Depends(get_core_db)):
    cursor = db_ratings.cursor()
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
    cursor_core = db_core.cursor()
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
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../frontend")), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
