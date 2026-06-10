from fastapi import APIRouter, Depends, Query, Path, HTTPException, Request
from typing import Optional
import sqlite3
import os
from datetime import datetime, timedelta

from database import get_core_db, get_ratings_db
from config import RATINGS_DB_PATH, CORE_DB_PATH

def safe_float(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, bytes):
        import struct
        if len(val) == 8:
            return struct.unpack('d', val)[0]
        elif len(val) == 4:
            return struct.unpack('f', val)[0]
        else:
            try:
                return float(val.decode('utf-8'))
            except:
                return None
    try:
        return float(val)
    except:
        return None

THRESHOLD_CACHE = {}
router = APIRouter()

@router.get("/api/players/search")
def search_players(request: Request, q: str = Query(..., min_length=2), db: sqlite3.Connection = Depends(get_core_db)):
    cursor = db.cursor()
    cursor.execute("""
        SELECT player_id, name_display, name_normalized, country_code
        FROM players
        WHERE name_display LIKE ? OR name_normalized LIKE ? 
        LIMIT 1000
    """, (f"%{q}%", f"%{q}%"))
    rows = cursor.fetchall()
    
    pids = [r['player_id'] for r in rows]
    ratings_map = {}
    if pids:
        placeholders = ",".join(["?"] * len(pids))
        try:
            with sqlite3.connect(RATINGS_DB_PATH) as conn_ratings:
                conn_ratings.row_factory = sqlite3.Row
                cursor_ratings = conn_ratings.cursor()
                cursor_ratings.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='player_stats'")
                if cursor_ratings.fetchone()[0] > 0:
                    cursor_ratings.execute(f"""
                        SELECT player_id, rating 
                        FROM player_stats 
                        WHERE player_id IN ({placeholders}) AND mode = 'current' AND model = 'elo' AND event = 'MS'
                    """, pids)
                    rating_rows = cursor_ratings.fetchall()
                    ratings_map = {r['player_id']: r['rating'] for r in rating_rows}
        except Exception as e:
            print(f"Error fetching ratings for search: {e}")
                
    return [{
        "id": r['player_id'], 
        "player_id": r['player_id'], 
        "name": r['name_display'] or r['name_normalized'],
        "country": r['country_code'],
        "rating": ratings_map.get(r['player_id'], None)
    } for r in rows]


@router.get("/api/player/{id}")
def get_player_details(id: str = Path(..., max_length=10), db_core: sqlite3.Connection = Depends(get_core_db)):
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

@router.get("/api/player/{id}/history")
def get_player_history(id: str = Path(..., max_length=10), 
                       event: str = "MS", 
                       model: str = "elo", 
                       start_date: Optional[str] = Query(None),
                       end_date: Optional[str] = Query(None),
                       db: sqlite3.Connection = Depends(get_ratings_db)):
    cursor = db.cursor()
    if model == "whr":
        cursor.execute("SELECT run_id FROM whr_run_metadata WHERE run_id LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%_{event}",))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No WHR runs found")
        run_id = row['run_id']
        
        # Self-healing fallback: check if there are rank records for this run, otherwise find the latest populated run
        cursor.execute("SELECT COUNT(*) FROM whr_ranking_history WHERE run_id = ?", (run_id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT run_id FROM whr_ranking_history WHERE event = ? ORDER BY rating_date DESC LIMIT 1", (event,))
            fallback_row = cursor.fetchone()
            if fallback_row:
                run_id = fallback_row['run_id']
        
        query = """
            SELECT rating_date, rating
            FROM whr_rating_history
            WHERE run_id = ? AND event = ? AND player_id = ?
        """
        params = [run_id, event, id]
        if start_date:
            query += " AND rating_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND rating_date <= ?"
            params.append(end_date)
        query += " ORDER BY rating_date ASC"
        cursor.execute(query, tuple(params))
        
    elif model == "elo":
        cursor.execute("SELECT run_id FROM run_metadata WHERE run_id LIKE '%final%' ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No Elo runs found")
        run_id = row['run_id']
        
        # Self-healing fallback: check if there are rank records for this run, otherwise find the latest populated run
        cursor.execute("SELECT COUNT(*) FROM ranking_history WHERE run_id = ?", (run_id,))
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT run_id FROM ranking_history WHERE event = ? ORDER BY rating_date DESC LIMIT 1", (event,))
            fallback_row = cursor.fetchone()
            if fallback_row:
                run_id = fallback_row['run_id']
        
        query = """
            SELECT rating_date, rating
            FROM rating_history
            WHERE run_id = ? AND event = ? AND player_id = ?
        """
        params = [run_id, event, id]
        if start_date:
            query += " AND rating_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND rating_date <= ?"
            params.append(end_date)
        query += " ORDER BY rating_date ASC"
        cursor.execute(query, tuple(params))
    else:
        raise HTTPException(status_code=400, detail="Invalid model")
        
    rows = cursor.fetchall()
    
    peak_date = None
    if rows:
        peak_row = max(rows, key=lambda x: safe_float(x['rating']) or 0.0)
        peak_date = peak_row['rating_date']
        
    peak_partner = None
    if peak_date and event in ['MD', 'WD', 'XD']:
        try:
            p_date = datetime.strptime(peak_date, "%Y-%m-%d")
            start_date = (p_date - timedelta(days=90)).strftime("%Y-%m-%d")
            
            core_conn = sqlite3.connect(CORE_DB_PATH)
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
        rating = safe_float(r['rating'])
        
        item = {
            "date": rating_date, 
            "rating": round((rating or 0.0), 1),
            "rank": None
        }
        
        if rating_date == peak_date and peak_partner:
            item["partner"] = peak_partner
            
        result.append(item)
        
    return result

@router.get("/api/player/{id}/matches")
def get_player_matches(id: str = Path(...), 
                       event: str = Query(None), 
                       model: str = Query("elo"), 
                       limit: int = Query(20, ge=1, le=10000),
                       offset: int = Query(0, ge=0),
                       start_date: str = Query(None),
                       end_date: str = Query(None),
                       include_ratings: bool = Query(True),
                       db: sqlite3.Connection = Depends(get_core_db)):
    cursor = db.cursor()
    
    query = """
        SELECT m.match_id 
        FROM matches m
        JOIN match_participants mp ON m.match_id = mp.match_id
        WHERE mp.player_id = ? AND m.is_valid_for_rating = 1
    """
    params = [id]
    
    if event:
        query += " AND m.event_canon = ?"
        params.append(event)
        
    if start_date:
        query += " AND m.match_date >= ?"
        params.append(start_date)
        
    if end_date:
        query += " AND m.match_date <= ?"
        params.append(end_date)
        
    query += " ORDER BY m.match_date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    
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
            m.duration,
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
                "duration": r['duration'],
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
            
    if include_ratings:
        with sqlite3.connect(RATINGS_DB_PATH) as conn_ratings:
            conn_ratings.row_factory = sqlite3.Row
            cursor_ratings = conn_ratings.cursor()
            
            if model == "whr":
                cursor_ratings.execute("SELECT run_id FROM whr_run_metadata WHERE run_id LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%_{event}",))
                row = cursor_ratings.fetchone()
                run_id = row['run_id'] if row else "default"
                
                # Self-healing fallback: check if there are rank records for this run, otherwise find the latest populated run
                cursor_ratings.execute("SELECT COUNT(*) FROM whr_ranking_history WHERE run_id = ?", (run_id,))
                if cursor_ratings.fetchone()[0] == 0:
                    cursor_ratings.execute("SELECT run_id FROM whr_ranking_history WHERE event = ? ORDER BY rating_date DESC LIMIT 1", (event or "MS",))
                    fallback_row = cursor_ratings.fetchone()
                    if fallback_row:
                        run_id = fallback_row['run_id']
                table = "whr_rating_history"
            else:
                cursor_ratings.execute("SELECT run_id FROM run_metadata WHERE run_id LIKE '%final%' ORDER BY created_at DESC LIMIT 1")
                row = cursor_ratings.fetchone()
                run_id = row['run_id'] if row else "default"
                
                # Self-healing fallback: check if there are rank records for this run, otherwise find the latest populated run
                cursor_ratings.execute("SELECT COUNT(*) FROM ranking_history WHERE run_id = ?", (run_id,))
                if cursor_ratings.fetchone()[0] == 0:
                    cursor_ratings.execute("SELECT run_id FROM ranking_history WHERE event = ? ORDER BY rating_date DESC LIMIT 1", (event or "MS",))
                    fallback_row = cursor_ratings.fetchone()
                    if fallback_row:
                        run_id = fallback_row['run_id']
                table = "rating_history"
                
            for mid, m in matches.items():
                for side in ["side1", "side2"]:
                    for p in m[side]:
                        cursor_ratings.execute(f"""
                            SELECT rating
                            FROM {table}
                            WHERE run_id = ? AND event = ? AND player_id = ? AND rating_date <= ?
                            ORDER BY rating_date DESC
                            LIMIT 1
                        """, (run_id, m["event"], p["id"], m["date"]))
                        r_row = cursor_ratings.fetchone()
                        
                        cursor_ratings.execute(f"""
                            SELECT rating
                            FROM {table}
                            WHERE run_id = ? AND event = ? AND player_id = ? AND rating_date < ?
                            ORDER BY rating_date DESC
                            LIMIT 1
                        """, (run_id, m["event"], p["id"], m["date"]))
                        prev_row = cursor_ratings.fetchone()
                        
                        if r_row:
                            r_val = safe_float(r_row["rating"])
                            p["rating"] = r_val
                            
                            h_table = "whr_rating_history" if model == "whr" else "rating_history"
                            cursor_ratings.execute(f"""
                                SELECT count(*) + 1 as rank
                                FROM {h_table}
                                WHERE run_id = ? AND event = ? AND rating_date = ? AND rating > ?
                            """, (run_id, m["event"], m["date"], r_val or 0.0))
                            rank_row = cursor_ratings.fetchone()
                            p["rank"] = rank_row["rank"] if rank_row else None
    
                            if prev_row:
                                prev_val = safe_float(prev_row["rating"])
                                p["rating_change"] = (r_val - prev_val) if r_val is not None and prev_val is not None else 0
                            else:
                                p["rating_change"] = 0
                        else:
                            p["rating"] = None
                            p["rank"] = None
                            p["rating_change"] = None
                            
                s1_ratings = [p["rating"] for p in m["side1"] if p["rating"] is not None]
                s2_ratings = [p["rating"] for p in m["side2"] if p["rating"] is not None]
                if s1_ratings and s2_ratings:
                    avg_s1 = sum(s1_ratings) / len(s1_ratings)
                    avg_s2 = sum(s2_ratings) / len(s2_ratings)
                    m["predicted_win_rate"] = 1 / (1 + 10**((avg_s2 - avg_s1) / 400))
                else:
                    m["predicted_win_rate"] = None
    else:
        for mid, m in matches.items():
            for side in ["side1", "side2"]:
                for p in m[side]:
                    p["rating"] = None
                    p["rank"] = None
                    p["rating_change"] = None
            m["predicted_win_rate"] = None
                
    return list(matches.values())

@router.get("/api/player/{id}/synergy")
def get_player_synergy(id: str = Path(..., max_length=10), 
                       event: str = Query(..., pattern="^(MD|WD|XD)$"),
                       db: sqlite3.Connection = Depends(get_ratings_db)):
    cursor = db.cursor()
    cursor.execute("SELECT run_id FROM run_metadata WHERE run_id LIKE '%final%' ORDER BY created_at DESC LIMIT 1")
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No Elo runs found")
    run_id = row['run_id']
    
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
        
    partner_ids = [r['partner_id'] for r in rows]
    placeholders = ",".join(["?"] * len(partner_ids))
    
    core_conn = sqlite3.connect(CORE_DB_PATH)
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

@router.get("/api/player/{id}/statistics")
def get_player_stats(id: str = Path(...), 
                     event: str = Query(...),
                     period: str = Query("all"),
                     model: str = Query("elo"),
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
        cursor_ratings.execute("SELECT run_id FROM run_metadata WHERE run_id LIKE '%final%' ORDER BY created_at DESC LIMIT 1")
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
                
    cursor_ratings = db_ratings.cursor()
    uncertainty = None
    total_players = 0
    threshold_15 = None
    current_rating = None
    current_rank = None
    
    if model == "whr":
        cursor_ratings.execute("SELECT run_id FROM whr_run_metadata WHERE run_id LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%_{event}",))
        row = cursor_ratings.fetchone()
        
        if row:
            cursor_ratings.execute("""
                SELECT uncertainty, rating
                FROM whr_rating_history
                WHERE run_id = ? AND event = ? AND player_id = ?
                ORDER BY rating_date DESC
                LIMIT 1
            """, (row['run_id'], event, id))
        else:
            cursor_ratings.execute("""
                SELECT uncertainty, rating
                FROM whr_rating_history
                WHERE event = ? AND player_id = ?
                ORDER BY rating_date DESC
                LIMIT 1
            """, (event, id))

        u_row = cursor_ratings.fetchone()
        if u_row:
            u_unc = safe_float(u_row['uncertainty'])
            u_rat = safe_float(u_row['rating'])
            uncertainty = round(u_unc, 2) if u_unc is not None else None
            current_rating = round(u_rat, 2) if u_rat is not None else None

        if row:
            cursor_ratings.execute("SELECT count(*) FROM player_stats WHERE event = ? AND model = ? AND mode = 'current'", (event, model))
            total_players = cursor_ratings.fetchone()[0]
            if total_players == 0:
                cursor_ratings.execute("SELECT count(distinct player_id) FROM whr_rating_history WHERE run_id = ? AND event = ?", (row['run_id'], event))
                total_players = cursor_ratings.fetchone()[0]
        
        if total_players == 0:
            cursor_ratings.execute("SELECT count(distinct player_id) FROM whr_rating_history WHERE event = ?", (event,))
            total_players = cursor_ratings.fetchone()[0]
            
        if row:
            cache_key = (row['run_id'], event, "whr")
            if cache_key in THRESHOLD_CACHE:
                threshold_15 = THRESHOLD_CACHE[cache_key]
            else:
                cursor_ratings.execute("""
                    SELECT uncertainty 
                    FROM whr_rating_history 
                    WHERE run_id = ? AND event = ? AND rating_date = (
                        SELECT MAX(rating_date) 
                        FROM whr_rating_history 
                        WHERE run_id = ? AND event = ?
                    )
                """, (row['run_id'], event, row['run_id'], event))
                u_rows = cursor_ratings.fetchall()
                if u_rows:
                    u_vals = [safe_float(r['uncertainty']) for r in u_rows]
                    u_vals = [x for x in u_vals if x is not None]
                    if u_vals:
                        u_vals.sort()
                        idx = int(len(u_vals) * 0.15)
                        threshold_15 = round(u_vals[idx], 2)
                THRESHOLD_CACHE[cache_key] = threshold_15
                    
        cursor_ratings.execute("""
            SELECT global_rank
            FROM player_stats
            WHERE player_id = ? AND event = ? AND model = ? AND mode = 'current'
            ORDER BY snapshot_date DESC
            LIMIT 1
        """, (id, event, model))
        rank_row = cursor_ratings.fetchone()
        if rank_row:
            current_rank = rank_row['global_rank']
    elif model == "bwf":
        cursor_ratings.execute("""
            SELECT rank, points
            FROM bwf_historical_rankings
            WHERE event = ? AND player_id = ?
            ORDER BY rank_date DESC
            LIMIT 1
        """, (event, id))
        bwf_row = cursor_ratings.fetchone()
        if bwf_row:
            current_rating = safe_float(bwf_row['points'])
            current_rank = bwf_row['rank']
            
        cursor_ratings.execute("""
            SELECT count(distinct player_id) 
            FROM bwf_historical_rankings 
            WHERE event = ? AND rank_date = (SELECT MAX(rank_date) FROM bwf_historical_rankings WHERE event = ?)
        """, (event, event))
        total_row = cursor_ratings.fetchone()
        total_players = total_row[0] if total_row else 0
    else:
        cursor_ratings.execute("SELECT run_id FROM run_metadata WHERE run_id LIKE '%final%' ORDER BY created_at DESC LIMIT 1")
        row = cursor_ratings.fetchone()
        if row:
            cursor_ratings.execute("""
                SELECT rd, rating
                FROM rating_history
                WHERE run_id = ? AND event = ? AND player_id = ?
                ORDER BY rating_date DESC
                LIMIT 1
            """, (row['run_id'], event, id))
            u_row = cursor_ratings.fetchone()
            if u_row:
                u_rd = safe_float(u_row['rd'])
                u_rat = safe_float(u_row['rating'])
                uncertainty = round(u_rd, 2) if u_rd is not None else None
                current_rating = round(u_rat, 2) if u_rat is not None else None

            cursor_ratings.execute("SELECT count(*) FROM player_stats WHERE event = ? AND model = ? AND mode = 'current'", (event, model))
            total_players = cursor_ratings.fetchone()[0]
            if total_players == 0:
                cursor_ratings.execute("SELECT count(distinct player_id) FROM rating_history WHERE run_id = ? AND event = ?", (row['run_id'], event))
                total_players = cursor_ratings.fetchone()[0]
            
            cache_key = (row['run_id'], event, "elo")
            if cache_key in THRESHOLD_CACHE:
                threshold_15 = THRESHOLD_CACHE[cache_key]
            else:
                cursor_ratings.execute("""
                    SELECT rd 
                    FROM rating_history 
                    WHERE run_id = ? AND event = ? AND rating_date = (
                        SELECT MAX(rating_date) 
                        FROM rating_history 
                        WHERE run_id = ? AND event = ?
                    )
                """, (row['run_id'], event, row['run_id'], event))
                u_rows = cursor_ratings.fetchall()
                if u_rows:
                    u_vals = [safe_float(r['rd']) for r in u_rows]
                    u_vals = [x for x in u_vals if x is not None]
                    if u_vals:
                        u_vals.sort()
                        idx = int(len(u_vals) * 0.15)
                        threshold_15 = round(u_vals[idx], 2)
                THRESHOLD_CACHE[cache_key] = threshold_15
                    
            cursor_ratings.execute("""
                SELECT global_rank
                FROM player_stats
                WHERE player_id = ? AND event = ? AND model = ? AND mode = 'current'
                ORDER BY snapshot_date DESC
                LIMIT 1
            """, (id, event, model))
            rank_row = cursor_ratings.fetchone()
            if rank_row:
                current_rank = rank_row['global_rank']

    performance_rating = None
    performance_diff = None
    
    cursor_core.execute("""
        SELECT m.match_id, m.winner_side, mp1.side, m.score
        FROM matches m
        JOIN match_participants mp1 ON m.match_id = mp1.match_id AND mp1.player_id = ?
        WHERE m.event_canon = ? AND m.is_valid_for_rating = 1
        ORDER BY m.match_date DESC
        LIMIT 10
    """, (id, event))
    recent_matches = cursor_core.fetchall()
    
    dominance_score = None
    
    if recent_matches:
        total_diff = 0
        total_sets = 0
        
        for m in recent_matches:
            player_side = m['side']
            score_str = m['score']
            
            if score_str:
                sets = score_str.split(' ')
                for s in sets:
                    parts = s.split('-')
                    if len(parts) == 2:
                        try:
                            s1 = int(parts[0])
                            s2 = int(parts[1])
                            if player_side == 1:
                                total_diff += (s1 - s2)
                            else:
                                total_diff += (s2 - s1)
                            total_sets += 1
                        except ValueError:
                            continue
                            
        if total_sets > 0:
            dominance_score = round(total_diff / total_sets, 2)

    decay_grace_days = 180
    try:
        if model == "elo":
            cursor_ratings.execute("SELECT decay_grace_days FROM run_metadata WHERE run_id LIKE '%final%' ORDER BY created_at DESC LIMIT 1")
            meta_row = cursor_ratings.fetchone()
            if meta_row and meta_row['decay_grace_days'] is not None:
                decay_grace_days = int(meta_row['decay_grace_days'])
    except Exception as e:
        print(f"Error getting decay_grace_days: {e}")

    return {
        "player_id": id,
        "event": event,
        "period": period,
        "total_matches": total_matches,
        "wins": wins,
        "win_rate": win_rate,
        "synergy_list": synergy_list,
        "opponents": opponents_list,
        "uncertainty": uncertainty,
        "total_players": total_players,
        "solid_threshold": threshold_15,
        "current_rating": current_rating,
        "current_rank": current_rank,
        "dominance_score": dominance_score,
        "inactivity_threshold": decay_grace_days
    }

@router.get("/api/player/{id}/uncertainty")
def get_player_uncertainty(id: str = Path(..., max_length=10), event: str = "MS", model: str = "elo", db: sqlite3.Connection = Depends(get_ratings_db)):
    cursor = db.cursor()
    if model == "whr":
        cursor.execute("SELECT run_id FROM whr_run_metadata WHERE run_id LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%_{event}",))
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
        cursor.execute("SELECT run_id FROM run_metadata WHERE run_id LIKE '%final%' ORDER BY created_at DESC LIMIT 1")
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


@router.post("/api/player/{id}/view")
def increment_player_view(id: str, db_ratings: sqlite3.Connection = Depends(get_ratings_db)):
    cursor = db_ratings.cursor()
    cursor.execute("""
        INSERT INTO player_views (player_id, view_count) 
        VALUES (?, 1) 
        ON CONFLICT(player_id) DO UPDATE SET view_count = view_count + 1
    """, (id,))
    db_ratings.commit()
    return {"status": "success"}

@router.get("/api/player/{id}/bwf-history")
def get_player_bwf_history(id: str = Path(..., max_length=10),
                           event: Optional[str] = Query(None),
                           db: sqlite3.Connection = Depends(get_ratings_db)):
    cursor = db.cursor()
    query = """
        SELECT rank_date, week, event, rank, points, country
        FROM bwf_historical_rankings
        WHERE player_id = ?
    """
    params = [id]
    if event:
        query += " AND event = ?"
        params.append(event)
    query += " ORDER BY rank_date ASC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    return [{
        "date": r["rank_date"],
        "week": r["week"],
        "event": r["event"],
        "rank": r["rank"],
        "points": r["points"],
        "country": r["country"]
    } for r in rows]

