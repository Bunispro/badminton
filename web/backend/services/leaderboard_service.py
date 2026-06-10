import sqlite3
from typing import Optional
from datetime import datetime, timedelta
from fastapi import HTTPException
from config import CORE_DB_PATH, REVERSE_COUNTRY_MAPPING

def fetch_leaderboard_data(db_ratings: sqlite3.Connection, db_core: sqlite3.Connection,
                           event: str, model: str, mode: str, limit: int, offset: int, period: str,
                           country: Optional[str] = None):
    """
    Fetch the leaderboard data with given filters.
    Optimized to minimize N+1 query issues.
    """
    cursor = db_ratings.cursor()
    try:
        if country:
            cursor.execute(f"ATTACH DATABASE '{CORE_DB_PATH}' AS core")
        # Try to use player_stats table first
        cursor.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='player_stats'")
        table_exists = cursor.fetchone()[0] > 0
        
        use_stats_table = False
        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM player_stats WHERE event = ? AND model = ? AND mode = ?", (event, model, mode))
            if cursor.fetchone()[0] > 0:
                use_stats_table = True
                
        # Fetch run_id needed for history queries
        run_id = None
        if model == "whr":
            cursor.execute("SELECT run_id FROM whr_run_metadata WHERE run_id LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%_{event}",))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="No WHR runs found")
            run_id = row['run_id']
        elif model == "elo":
            cursor.execute("SELECT run_id FROM run_metadata WHERE run_id LIKE '%final%' ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="No Elo runs found")
            run_id = row['run_id']
            
        if model == "bwf":
            print("Using BWF rankings for leaderboard")
            cursor.execute("SELECT MAX(rank_date) FROM bwf_historical_rankings WHERE event = ?", (event,))
            latest_date_row = cursor.fetchone()
            if not latest_date_row or not latest_date_row[0]:
                raise HTTPException(status_code=404, detail="No BWF rankings found")
            latest_date = latest_date_row[0]
            
            if country:
                codes = [c.strip().lower() for c in country.split(',')]
                countries = []
                for code in codes:
                    countries.extend(REVERSE_COUNTRY_MAPPING.get(code, [code]))
                placeholders = ",".join(["?"] * len(countries))
                query = f"""
                    SELECT player_id, points as rating, rank_date as rating_date, NULL as winrate, NULL as rank_at_peak, NULL as change
                    FROM bwf_historical_rankings
                    WHERE event = ? AND rank_date = ? AND country IN ({placeholders})
                    ORDER BY rank ASC
                    LIMIT ? OFFSET ?
                """
                cursor.execute(query, [event, latest_date] + countries + [limit, offset])
            else:
                query = """
                    SELECT player_id, points as rating, rank_date as rating_date, NULL as winrate, NULL as rank_at_peak, NULL as change
                    FROM bwf_historical_rankings
                    WHERE event = ? AND rank_date = ?
                    ORDER BY rank ASC
                    LIMIT ? OFFSET ?
                """
                cursor.execute(query, (event, latest_date, limit, offset))
            rows = cursor.fetchall()
            
        elif use_stats_table:
            print("Using player_stats table for leaderboard")
            cursor.execute("SELECT MAX(rating_date) FROM player_stats WHERE event = ? AND model = ? AND mode = ?", (event, model, mode))
            latest_date = cursor.fetchone()[0]
            
            # Map period to change column
            change_col = "change_1m"
            if period == "3m": change_col = "change_3m"
            elif period == "6m": change_col = "change_6m"
            elif period == "1y": change_col = "change_6m" # Fallback for now
 
            if country:
                codes = [c.strip().lower() for c in country.split(',')]
                countries = []
                for code in codes:
                    countries.extend(REVERSE_COUNTRY_MAPPING.get(code, [code]))
                placeholders = ",".join(["?"] * len(countries))
                query = f"""
                    SELECT ps.player_id, ps.rating, 
                           CASE WHEN ps.mode = 'peak' THEN ps.rating_date ELSE ps.last_played_date END as rating_date,
                           ps.winrate, ps.rank_at_peak, ps.{change_col} as change
                    FROM player_stats ps
                    JOIN core.players p ON ps.player_id = p.player_id
                    WHERE ps.event = ? AND ps.model = ? AND ps.mode = ? AND ps.snapshot_date = (SELECT MAX(snapshot_date) FROM player_stats)
                      AND p.country_code IN ({placeholders})
                    ORDER BY ps.global_rank ASC
                    LIMIT ? OFFSET ?
                """
                cursor.execute(query, [event, model, mode] + countries + [limit, offset])
            else:
                cursor.execute(f"""
                    SELECT player_id, rating, 
                           CASE WHEN mode = 'peak' THEN rating_date ELSE last_played_date END as rating_date,
                           winrate, rank_at_peak, {change_col} as change
                    FROM player_stats
                    WHERE event = ? AND model = ? AND mode = ? AND snapshot_date = (SELECT MAX(snapshot_date) FROM player_stats)
                    ORDER BY global_rank ASC
                    LIMIT ? OFFSET ?
                """, (event, model, mode, limit, offset))
            rows = cursor.fetchall()
            
        else:
            print("Fallback to on-the-fly calculation for leaderboard")
            if model == "whr":
                cursor.execute("SELECT MAX(rating_date) FROM whr_rating_history WHERE run_id = ?", (run_id,))
                latest_date = cursor.fetchone()[0]
                
                if country:
                    codes = [c.strip().lower() for c in country.split(',')]
                    countries = []
                    for code in codes:
                        countries.extend(REVERSE_COUNTRY_MAPPING.get(code, [code]))
                    placeholders = ",".join(["?"] * len(countries))
                    if mode == "peak":
                        query = f"""
                            SELECT rh.player_id, MAX(rh.rating) as rating, rh.rating_date
                            FROM whr_rating_history rh
                            JOIN core.players p ON rh.player_id = p.player_id
                            WHERE rh.run_id = ? AND rh.event = ? AND p.country_code IN ({placeholders})
                            GROUP BY rh.player_id
                            ORDER BY rating DESC
                            LIMIT ? OFFSET ?
                        """
                        cursor.execute(query, [run_id, event] + countries + [limit, offset])
                    else:
                        two_years_ago = (datetime.strptime(latest_date, "%Y-%m-%d") - timedelta(days=547)).strftime("%Y-%m-%d")
                        query = f"""
                            WITH ranked AS (
                                SELECT rh.player_id, rh.rating, rh.rating_date,
                                       ROW_NUMBER() OVER(PARTITION BY rh.player_id ORDER BY rh.rating_date DESC) as rn
                                FROM whr_rating_history rh
                                JOIN core.players p ON rh.player_id = p.player_id
                                WHERE rh.run_id = ? AND rh.event = ? AND rh.rating_date >= ? AND p.country_code IN ({placeholders})
                            )
                            SELECT player_id, rating, rating_date
                            FROM ranked
                            WHERE rn = 1
                            ORDER BY rating DESC
                            LIMIT ? OFFSET ?
                        """
                        cursor.execute(query, [run_id, event, two_years_ago] + countries + [limit, offset])
                else:
                    if mode == "peak":
                        query = """
                            SELECT player_id, MAX(rating) as rating, rating_date
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
                                SELECT player_id, rating, rating_date,
                                       ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY rating_date DESC) as rn
                                FROM whr_rating_history
                                WHERE run_id = ? AND event = ? AND rating_date >= ?
                            )
                            SELECT player_id, rating, rating_date
                            FROM ranked
                            WHERE rn = 1
                            ORDER BY rating DESC
                            LIMIT ? OFFSET ?
                        """
                        cursor.execute(query, (run_id, event, two_years_ago, limit, offset))
                    
            elif model == "elo":
                cursor.execute("SELECT MAX(rating_date) FROM rating_history WHERE run_id = ?", (run_id,))
                latest_date = cursor.fetchone()[0]
                
                if country:
                    codes = [c.strip().lower() for c in country.split(',')]
                    countries = []
                    for code in codes:
                        countries.extend(REVERSE_COUNTRY_MAPPING.get(code, [code]))
                    placeholders = ",".join(["?"] * len(countries))
                    if mode == "peak":
                        query = f"""
                            SELECT rh.player_id, MAX(rh.rating) as rating, rh.rating_date
                            FROM rating_history rh
                            JOIN core.players p ON rh.player_id = p.player_id
                            WHERE rh.run_id = ? AND rh.event = ? AND p.country_code IN ({placeholders})
                            GROUP BY rh.player_id
                            ORDER BY rating DESC
                            LIMIT ? OFFSET ?
                        """
                        cursor.execute(query, [run_id, event] + countries + [limit, offset])
                    else:
                        two_years_ago = (datetime.strptime(latest_date, "%Y-%m-%d") - timedelta(days=547)).strftime("%Y-%m-%d")
                        query = f"""
                            WITH ranked AS (
                                SELECT rh.player_id, rh.rating, rh.rating_date,
                                       ROW_NUMBER() OVER(PARTITION BY rh.player_id ORDER BY rh.rating_date DESC) as rn
                                FROM rating_history rh
                                JOIN core.players p ON rh.player_id = p.player_id
                                WHERE rh.run_id = ? AND rh.event = ? AND rh.rating_date >= ? AND p.country_code IN ({placeholders})
                            )
                            SELECT player_id, rating, rating_date
                            FROM ranked
                            WHERE rn = 1
                            ORDER BY rating DESC
                            LIMIT ? OFFSET ?
                        """
                        cursor.execute(query, [run_id, event, two_years_ago] + countries + [limit, offset])
                else:
                    if mode == "peak":
                        query = """
                            SELECT player_id, MAX(rating) as rating, rating_date
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
                                SELECT player_id, rating, rating_date,
                                       ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY rating_date DESC) as rn
                                FROM rating_history
                                WHERE run_id = ? AND event = ? AND rating_date >= ?
                            )
                            SELECT player_id, rating, rating_date
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
        
        three_months_dt = latest_dt - timedelta(days=90)
        three_months_date = three_months_dt.strftime("%Y-%m-%d")

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
        if model == "bwf":
            cursor.execute(f"""
                SELECT player_id, points as rating, rank_date as rating_date
                FROM bwf_historical_rankings
                WHERE event = ? AND rank_date = (
                    SELECT MAX(rank_date) FROM bwf_historical_rankings
                    WHERE event = ? AND rank_date <= ?
                ) AND player_id IN ({placeholders})
            """, [event, event, past_date] + pids)
            past_rows = cursor.fetchall()
        else:
            table_name = "whr_rating_history" if model == "whr" else "rating_history"
            cursor.execute(f"""
                WITH ranked AS (
                    SELECT player_id, rating, rating_date,
                           ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY CASE WHEN rating_date <= ? THEN 0 ELSE 1 END, ABS(julianday(rating_date) - julianday(?))) as rn
                    FROM {table_name}
                    WHERE run_id = ? AND event = ? AND player_id IN ({placeholders})
                )
                SELECT player_id, rating, rating_date
                FROM ranked
                WHERE rn = 1
            """, [past_date, past_date, run_id, event] + pids)
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
                WHERE mp.player_id IN ({placeholders}) AND m.is_valid_for_rating = 1 AND m.event_canon = ?
            )
            SELECT player_id, match_id FROM ranked_matches WHERE rn <= 10
        """, pids + [event])
        match_id_rows = cursor_core.fetchall()
        
        # Fetch winrate for each player in ONE query if calculating on the fly
        winrate_map = {}
        if not use_stats_table and mode == "peak":
            cursor_core.execute(f"""
                SELECT 
                    mp.player_id,
                    COUNT(*) as total_matches,
                    SUM(CASE WHEN mp.side = m.winner_side THEN 1 ELSE 0 END) as wins
                FROM match_participants mp
                JOIN matches m ON mp.match_id = m.match_id
                WHERE mp.player_id IN ({placeholders}) AND m.is_valid_for_rating = 1
                GROUP BY mp.player_id
            """, pids)
            winrate_rows = cursor_core.fetchall()
            winrate_map = {r['player_id']: round((r['wins'] / r['total_matches']) * 100, 1) for r in winrate_rows if r['total_matches'] > 0}

        # Fetch Peak Global Rank (highest global rank of all time) for each player if calculating on the fly
        rank_at_peak_map = {}
        if not use_stats_table:
            if model == "bwf":
                history_table = "bwf_historical_rankings"
            else:
                history_table = "whr_ranking_history" if model == "whr" else "ranking_history"
            
            if pids:
                pids_param = [int(x) if str(x).isdigit() else x for x in pids] if model == "bwf" else pids
                placeholders = ",".join(["?"] * len(pids_param))
                cursor.execute(f"""
                    SELECT player_id, MIN(rank)
                    FROM {history_table}
                    WHERE event = ? AND player_id IN ({placeholders})
                    GROUP BY player_id
                """, [event] + pids_param)
                for row in cursor.fetchall():
                    rank_at_peak_map[str(row[0])] = row[1]

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
                    matches_data[mid]["side1"].append(participant)
                else:
                    matches_data[mid]["side2"].append(participant)
            
        # Fetch rating history for the last 3 months
        if model == "bwf":
            cursor.execute(f"""
                SELECT player_id, points as rating, rank_date as rating_date
                FROM bwf_historical_rankings
                WHERE event = ? AND player_id IN ({placeholders}) AND rank_date >= ?
                ORDER BY rank_date ASC
            """, [event] + pids + [three_months_date])
            history_rows = cursor.fetchall()
        else:
            cursor.execute(f"""
                SELECT player_id, rating, rating_date
                FROM {table_name}
                WHERE run_id = ? AND event = ? AND player_id IN ({placeholders}) AND rating_date >= ?
                ORDER BY rating_date ASC
            """, [run_id, event] + pids + [three_months_date])
            history_rows = cursor.fetchall()
        
        # Group history by player
        player_history_map = {}
        for hr in history_rows:
            pid = hr['player_id']
            if pid not in player_history_map:
                player_history_map[pid] = []
            player_history_map[pid].append({
                "date": hr['rating_date'],
                "rating": round(hr['rating'], 1)
            })
            
        results = []
        for r in rows:
            pid = r['player_id']
            info = player_info.get(pid, {"name": pid, "country": None})
            
            current_rating = r['rating']
            if use_stats_table and r['change'] is not None:
                change = round(r['change'], 1)
            else:
                past_rating = past_rating_map.get(pid, current_rating)
                change = round(current_rating - past_rating, 1)
            
            results.append({
                "player_id": pid,
                "name": info["name"],
                "country": info["country"],
                "rating": round(current_rating, 1),
                "date": r['rating_date'],
                "change": change,
                "recent_matches": [matches_data[mid] for mid in player_matches_map.get(pid, []) if mid in matches_data],
                "history": player_history_map.get(pid, []),
                "winrate": r['winrate'] if use_stats_table else winrate_map.get(pid, None),
                "rank_at_peak": r['rank_at_peak'] if use_stats_table else rank_at_peak_map.get(str(pid), rank_at_peak_map.get(pid, None))
            })
            
        return results
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error in fetch_leaderboard_data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
