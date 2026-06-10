import sqlite3
from datetime import datetime, timedelta

RATINGS_DB = r"d:\badminton\elo_ratings.sqlite"
CORE_DB = r"d:\badminton\bwf_data_2008-now__v1.sqlite"

def populate():
    print("Populating player_stats table with trends...")
    db_ratings = sqlite3.connect(RATINGS_DB)
    db_ratings.row_factory = sqlite3.Row
    db_core = sqlite3.connect(CORE_DB)
    db_core.row_factory = sqlite3.Row
    
    # Attach ratings DB to core DB for cross-DB queries
    db_core.execute(f"ATTACH DATABASE '{RATINGS_DB}' AS ratings_db")
    
    cursor = db_ratings.cursor()
    cursor_core = db_core.cursor()
    
    # Create table with trend columns
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            player_id TEXT,
            event TEXT,
            model TEXT,
            mode TEXT,
            snapshot_date TEXT,
            winrate REAL,
            global_rank INTEGER,
            rating REAL,
            rating_date TEXT,
            rank_at_peak INTEGER,
            last_played_date TEXT,
            total_matches INTEGER,
            country_code TEXT,
            change_1m REAL,
            change_3m REAL,
            change_6m REAL,
            PRIMARY KEY (player_id, event, model, mode, snapshot_date)
        )
    """)
    
    # Add columns if they don't exist (in case table already existed)
    try:
        cursor.execute("ALTER TABLE player_stats ADD COLUMN change_1m REAL")
        cursor.execute("ALTER TABLE player_stats ADD COLUMN change_3m REAL")
        cursor.execute("ALTER TABLE player_stats ADD COLUMN change_6m REAL")
    except:
        pass # Already exists
    
    events = ["MS", "WS", "MD", "WD", "XD"]
    models = ["whr", "elo"]
    modes = ["current", "peak"]
    today = datetime.now().strftime("%Y-%m-%d")
    
    for event in events:
        for model in models:
            for mode in modes:
                print(f"Processing {event} {model} {mode}...")
                
                run_id = ""
                table_name = "whr_rating_history" if model == "whr" else "rating_history"
                
                if model == "whr":
                    cursor.execute("SELECT run_id FROM whr_run_metadata WHERE run_id LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%_{event}",))
                    row = cursor.fetchone()
                    if not row: continue
                    run_id = row['run_id']
                else:
                    cursor.execute("SELECT run_id FROM run_metadata WHERE run_id LIKE '%final%' ORDER BY created_at DESC LIMIT 1")
                    row = cursor.fetchone()
                    if not row: continue
                    run_id = row['run_id']
                
                # Fetch leaderboard data
                if mode == "peak":
                    query = f"""
                        SELECT player_id, MAX(rating) as rating, rating_date
                        FROM {table_name}
                        WHERE run_id = ? AND event = ?
                        GROUP BY player_id
                        ORDER BY rating DESC
                    """
                    cursor.execute(query, (run_id, event))
                else:
                    cursor.execute(f"SELECT MAX(rating_date) FROM {table_name} WHERE run_id = ?", (run_id,))
                    latest_date_row = cursor.fetchone()
                    if not latest_date_row: continue
                    latest_date = latest_date_row[0]
                    
                    two_years_ago = (datetime.strptime(latest_date, "%Y-%m-%d") - timedelta(days=730)).strftime("%Y-%m-%d")
                    query = f"""
                        WITH ranked AS (
                            SELECT player_id, rating, rating_date,
                                   ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY rating_date DESC) as rn
                            FROM {table_name}
                            WHERE run_id = ? AND event = ? AND rating_date >= ?
                        )
                        SELECT player_id, rating, rating_date
                        FROM ranked
                        WHERE rn = 1
                        ORDER BY rating DESC
                    """
                    cursor.execute(query, (run_id, event, two_years_ago))
                    
                rows = cursor.fetchall()
                if not rows: continue
                print(f"  Found {len(rows)} players.")
                
                # Pre-fetch historical ratings for changes
                def get_past_ratings(days):
                    p_date = (datetime.strptime(latest_date if mode == 'current' else rows[0]['rating_date'], "%Y-%m-%d") - timedelta(days=days)).strftime("%Y-%m-%d")
                    cursor.execute(f"""
                        WITH ranked AS (
                            SELECT player_id, rating,
                                   ROW_NUMBER() OVER(PARTITION BY player_id ORDER BY rating_date DESC) as rn
                            FROM {table_name}
                            WHERE run_id = ? AND event = ? AND rating_date <= ?
                        )
                        SELECT player_id, rating
                        FROM ranked
                        WHERE rn = 1
                    """, (run_id, event, p_date))
                    return {r['player_id']: r['rating'] for r in cursor.fetchall()}

                past_1m = get_past_ratings(30)
                past_3m = get_past_ratings(90)
                past_6m = get_past_ratings(180)

                # Fetch stats using subquery (attaching ratings_db)
                stats_map = {}
                cursor_core.execute(f"""
                    SELECT 
                        mp.player_id,
                        COUNT(*) as total_matches,
                        SUM(CASE WHEN mp.side = m.winner_side THEN 1 ELSE 0 END) as wins,
                        MAX(m.match_date) as last_played_date,
                        p.country_code
                    FROM match_participants mp
                    JOIN matches m ON mp.match_id = m.match_id
                    JOIN players p ON mp.player_id = p.player_id
                    WHERE mp.player_id IN (
                        SELECT player_id FROM ratings_db.{table_name} WHERE run_id = ? AND event = ?
                    ) AND m.is_valid_for_rating = 1
                    GROUP BY mp.player_id
                """, (run_id, event))
                stats_rows = cursor_core.fetchall()
                for sr in stats_rows:
                    stats_map[sr['player_id']] = {
                        "winrate": round((sr['wins'] / sr['total_matches']) * 100, 1) if sr['total_matches'] > 0 else 0.0,
                        "total_matches": sr['total_matches'],
                        "last_played_date": sr['last_played_date'],
                        "country_code": sr['country_code']
                    }
                
                # Fetch Peak Global Rank (highest global rank of all time) for each player in history
                rank_at_peak_map = {}
                history_table = "whr_ranking_history" if model == "whr" else "ranking_history"
                cursor.execute(f"""
                    SELECT player_id, MIN(rank)
                    FROM {history_table}
                    WHERE event = ?
                    GROUP BY player_id
                """, (event,))
                for row_data in cursor.fetchall():
                    rank_at_peak_map[str(row_data[0])] = row_data[1]
                
                # Insert into player_stats
                insert_data = []
                for index, r in enumerate(rows):
                    pid = r['player_id']
                    p_stats = stats_map.get(pid, {})
                    winrate = p_stats.get("winrate", None)
                    total_matches = p_stats.get("total_matches", 0)
                    last_played_date = p_stats.get("last_played_date", None)
                    country_code = p_stats.get("country_code", None)
                    
                    global_rank = index + 1
                    rating = r['rating']
                    rating_date = r['rating_date']
                    rank_at_peak = rank_at_peak_map.get(str(pid), rank_at_peak_map.get(pid, None))
                    
                    c1m = rating - past_1m.get(pid, rating)
                    c3m = rating - past_3m.get(pid, rating)
                    c6m = rating - past_6m.get(pid, rating)
                    
                    insert_data.append((
                        pid, event, model, mode, today,
                        winrate, global_rank, rating, rating_date, rank_at_peak,
                        last_played_date, total_matches, country_code,
                        c1m, c3m, c6m
                    ))
                
                cursor.executemany("""
                    INSERT OR REPLACE INTO player_stats 
                    (player_id, event, model, mode, snapshot_date, winrate, global_rank, rating, rating_date, rank_at_peak, last_played_date, total_matches, country_code, change_1m, change_3m, change_6m)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, insert_data)
                
                db_ratings.commit()
                print(f"  Inserted {len(insert_data)} rows.")
                
    db_ratings.close()
    db_core.close()
    print("Done.")

if __name__ == "__main__":
    populate()
