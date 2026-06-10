import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import bisect
from collections import defaultdict
import os

TEST_DB_PATH = "elo_ratings.sqlite"
CORE_DB_PATH = "bwf_data_2008-now__v1.sqlite"
ML_DB_PATH = "elo_ratings.sqlite" # We store the dataset here

def load_history_lookups(conn):
    print("Loading rating and synergy history for fast lookups...")
    cursor = conn.cursor()
    
    # 1. Elo Ratings
    cursor.execute("SELECT run_id FROM rating_history ORDER BY rating_date DESC LIMIT 1")
    last_elo_run = cursor.fetchone()[0]
    print(f"  Using Elo run: {last_elo_run}")
    
    cursor.execute("""
        SELECT player_id, rating_date, rating 
        FROM rating_history 
        WHERE run_id = ?
        ORDER BY player_id, rating_date ASC
    """, (last_elo_run,))
    
    elo_lookup = defaultdict(list)
    for pid, rdate, rating in cursor.fetchall():
        elo_lookup[pid].append((rdate, rating))
        
    # 2. WHR Ratings
    # Query the most recent run_id for each event in WHR (since they are separate)
    cursor.execute("SELECT DISTINCT run_id FROM whr_rating_history ORDER BY run_id DESC")
    whr_runs = [r[0] for r in cursor.fetchall()[:5]] # Get the latest 5 runs (one per event)
    print(f"  Using WHR runs: {whr_runs}")
    
    whr_lookup = defaultdict(list)
    for run in whr_runs:
        cursor.execute("""
            SELECT player_id, rating_date, rating 
            FROM whr_rating_history 
            WHERE run_id = ?
            ORDER BY player_id, rating_date ASC
        """, (run,))
        for pid, rdate, rating in cursor.fetchall():
            whr_lookup[pid].append((rdate, rating))
            
    # 3. Elo Synergy
    cursor.execute("SELECT run_id FROM pair_synergy_history ORDER BY snapshot_date DESC LIMIT 1")
    last_syn_run = cursor.fetchone()[0]
    print(f"  Using Synergy run: {last_syn_run}")
    
    cursor.execute("""
        SELECT player1_id, player2_id, snapshot_date, synergy 
        FROM pair_synergy_history 
        WHERE run_id = ?
        ORDER BY player1_id, player2_id, snapshot_date ASC
    """, (last_syn_run,))
    
    synergy_lookup = defaultdict(list)
    for p1, p2, sdate, syn in cursor.fetchall():
        pair_key = "+".join(sorted([p1, p2]))
        synergy_lookup[pair_key].append((sdate, syn))
        
    return elo_lookup, whr_lookup, synergy_lookup

def get_historical_val(lookup_dict, key, date_str, default_val=1000.0):
    """Retrieves the value for key strictly BEFORE date_str using binary search"""
    history = lookup_dict.get(key)
    if not history:
        return default_val
    
    # Extract dates for bisect
    dates = [h[0] for h in history]
    # bisect_left finds the index of the first date >= date_str.
    # Therefore, idx - 1 will point to the last date strictly < date_str.
    idx = bisect.bisect_left(dates, date_str)
    if idx == 0:
        return default_val
    return history[idx - 1][1]

def main():
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"ATTACH DATABASE '{CORE_DB_PATH}' AS core")
    
    elo_lookup, whr_lookup, synergy_lookup = load_history_lookups(conn)
    
    print("Fetching chronological matches...")
    cursor.execute("""
        SELECT 
            m.match_id,
            m.match_date,
            m.event_canon,
            m.winner_side,
            m.duration,
            t.tier,
            m.round,
            GROUP_CONCAT(CASE WHEN mp.side = 1 THEN mp.player_id END) AS p1_ids,
            GROUP_CONCAT(CASE WHEN mp.side = 2 THEN mp.player_id END) AS p2_ids
        FROM core.matches m
        JOIN core.match_participants mp ON mp.match_id = m.match_id
        LEFT JOIN core.tournaments t ON m.tournament_id = t.tournament_id
        WHERE m.is_valid_for_rating = 1
        GROUP BY m.match_id, m.match_date, m.event_canon, m.winner_side, m.duration, t.tier, m.round
        ORDER BY m.match_date ASC, m.match_id ASC
    """)
    
    matches = cursor.fetchall()
    print(f"Loaded {len(matches)} matches. Engineering features...")
    
    # State dictionaries for tracking fatigue/rest day metrics
    player_last_played = {}
    player_history = defaultdict(list) # List of datetime.date objects for each player
    
    # State dictionary for tracking head-to-head records
    h2h_tracker = defaultdict(list)
    
    ml_features = []
    
    # Load median durations to impute missing values
    durations_by_event = defaultdict(list)
    for m in matches:
        duration = m[4]
        if duration and duration > 0:
            durations_by_event[m[2]].append(duration)
    median_durations = {event: np.median(durs) for event, durs in durations_by_event.items()}
    
    for idx, match in enumerate(matches):
        match_id, date_str, event, winner_side, duration, tier, round_name, p1_ids_str, p2_ids_str = match
        
        match_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        is_doubles = event in ["MD", "WD", "XD"]
        
        team_a = p1_ids_str.split(",")
        team_b = p2_ids_str.split(",")
        
        # 1. Impute Duration
        if not duration or duration <= 0:
            duration = median_durations.get(event, 35.0) # Fallback to 35 mins
            
        # 2. Compute Rest for both teams (clamped to 90 days)
        def compute_player_rest(player_list):
            rest_days_list = []
            for pid in player_list:
                last_played = player_last_played.get(pid)
                if last_played:
                    rest_days = (match_date - last_played).days
                    rest_days = min(90, rest_days) # Clamp to 90 days max
                else:
                    rest_days = 90 # Default for first match
                rest_days_list.append(rest_days)
            return np.mean(rest_days_list)
            
        avg_rest_a = compute_player_rest(team_a)
        avg_rest_b = compute_player_rest(team_b)
        
        # 3. Retrieve Ratings immediately PRIOR to the match (we use date_str)
        # For doubles, team rating is the average of individual ratings
        elo_a = sum(get_historical_val(elo_lookup, p, date_str, 1000.0) for p in team_a) / len(team_a)
        elo_b = sum(get_historical_val(elo_lookup, p, date_str, 1000.0) for p in team_b) / len(team_b)
        
        # WHR default is 1000.0 Elo
        whr_a = sum(get_historical_val(whr_lookup, p, date_str, 1000.0) for p in team_a) / len(team_a)
        whr_b = sum(get_historical_val(whr_lookup, p, date_str, 1000.0) for p in team_b) / len(team_b)
        
        # Retrieve synergies for doubles
        syn_a = 0.0
        syn_b = 0.0
        if is_doubles and len(team_a) == 2:
            key_a = "+".join(sorted(team_a))
            syn_a = get_historical_val(synergy_lookup, key_a, date_str, 0.0)
        if is_doubles and len(team_b) == 2:
            key_b = "+".join(sorted(team_b))
            syn_b = get_historical_val(synergy_lookup, key_b, date_str, 0.0)
            
        # 4. Compute Head-to-Head win rate before the match (capped at 2 years)
        team_key_a = "+".join(sorted(team_a))
        team_key_b = "+".join(sorted(team_b))
        m_key = tuple(sorted([team_key_a, team_key_b]))
        
        # Filter H2H history to keep only matches in the last 2 years (730 days)
        h2h_history = [item for item in h2h_tracker[m_key] if (match_date - item["date"]).days <= 730]
        h2h_tracker[m_key] = h2h_history
        
        # Compute wins relative to team_key_a
        wins_a = sum(1 for item in h2h_history if item["winner"] == team_key_a)
        total_h2h = len(h2h_history)
        h2h_rate = wins_a / total_h2h if total_h2h > 0 else 0.5
            
        # 5. Save player active state updates after computing metrics
        for pid in team_a + team_b:
            player_last_played[pid] = match_date
            player_history[pid].append(match_date)
            
        # Update H2H tracker with current match outcome
        winner_team = team_key_a if winner_side == 1 else team_key_b
        h2h_tracker[m_key].append({"date": match_date, "winner": winner_team})
            
        # 6. Append feature row (without redundant fatigue features)
        ml_features.append((
            match_id,
            date_str,
            event,
            1 if winner_side == 1 else 0, # Target: 1 if Side 1 wins, else 0
            duration,
            tier,
            round_name,
            elo_a,
            elo_b,
            elo_a - elo_b,
            whr_a,
            whr_b,
            whr_a - whr_b,
            syn_a,
            syn_b,
            avg_rest_a,
            avg_rest_b,
            avg_rest_a - avg_rest_b,
            h2h_rate
        ))
        
        if (idx + 1) % 50000 == 0:
            print(f"  Processed {idx + 1} matches...")

    # Write dataset to SQLite
    print("Writing features to database...")
    cursor.execute("DROP TABLE IF EXISTS ml_match_features")
    cursor.execute("""
        CREATE TABLE ml_match_features (
            match_id TEXT PRIMARY KEY,
            match_date TEXT,
            event TEXT,
            winner_side_1 INTEGER,
            duration REAL,
            tier TEXT,
            round TEXT,
            elo_a REAL,
            elo_b REAL,
            elo_diff REAL,
            whr_a REAL,
            whr_b REAL,
            whr_diff REAL,
            synergy_a REAL,
            synergy_b REAL,
            avg_rest_a REAL,
            avg_rest_b REAL,
            rest_diff REAL,
            h2h_rate REAL
        )
    """)
    
    cursor.executemany("""
        INSERT INTO ml_match_features VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, ml_features)
    
    conn.commit()
    conn.close()
    print("Successfully built machine learning training dataset (table: ml_match_features).")

if __name__ == "__main__":
    main()
