import sqlite3
import numpy as np
import math
from datetime import date
import whr.whole_history_rating as whr

CORE_DB = "bwf_data_2008-now__v1.sqlite"

def get_mov_multiplier(score_str, event_canon, mov_base_mult, mov_growth_rate):
    if event_canon not in ['MS', 'WS', 'MD', 'WD', 'XD'] or mov_base_mult == 1.0:
        return 1.0
    if not score_str or '-' not in score_str or 'Retired' in score_str or 'Walkover' in score_str:
        return 1.0
    
    sets = score_str.strip().split(' ')
    p1_total = 0
    p2_total = 0
    for s in sets:
        parts = s.split('-')
        if len(parts) == 2:
            try:
                p1_total += int(parts[0])
                p2_total += int(parts[1])
            except ValueError:
                pass
                
    if p1_total == 0 and p2_total == 0:
        return 1.0
        
    point_gap = abs(p1_total - p2_total)
    
    if point_gap <= 5:
        return mov_base_mult
    else:
        return min(1.5, mov_base_mult * (mov_growth_rate ** (point_gap - 5)))

def load_data(event, limit=5000):
    conn = sqlite3.connect(CORE_DB)
    cursor = conn.cursor()
    
    cursor.execute("SELECT MIN(match_date) FROM matches WHERE is_valid_for_rating = 1")
    min_date_str = cursor.fetchone()[0]
    start_date = date.fromisoformat(min_date_str)
    
    query = """
        SELECT
            m.match_date,
            m.winner_side,
            GROUP_CONCAT(CASE WHEN mp.side = 1 THEN mp.player_id END) AS p1_ids,
            GROUP_CONCAT(CASE WHEN mp.side = 2 THEN mp.player_id END) AS p2_ids,
            m.score
        FROM matches m
        JOIN match_participants mp ON mp.match_id = m.match_id
        WHERE m.event_canon = ? AND m.is_valid_for_rating = 1
        GROUP BY m.match_id, m.match_date, m.winner_side, m.score
        HAVING COUNT(CASE WHEN mp.side = 1 THEN 1 END) > 0
           AND COUNT(CASE WHEN mp.side = 2 THEN 1 END) > 0
        ORDER BY m.match_date DESC
        LIMIT ?
    """
    cursor.execute(query, (event, limit))
    rows = cursor.fetchall()
    conn.close()
    
    rows.reverse()
    
    games_data = []
    is_doubles = event in ["MD", "WD", "XD"]
    
    for date_str, winner_side, p1_ids_str, p2_ids_str, score in rows:
        current_date = date.fromisoformat(date_str)
        day_index = (current_date - start_date).days
        
        if is_doubles:
            p1_key = p1_ids_str.split(',')
            p2_key = p2_ids_str.split(',')
        else:
            p1_key = p1_ids_str
            p2_key = p2_ids_str
            
        winner = 'A' if winner_side == 1 else 'B'
        games_data.append((p1_key, p2_key, winner, day_index, score))
        
    return games_data

def evaluate_mov(games_data, w2, mov_base_mult, mov_growth_rate, event):
    whr_system = whr.Base(config={'w2': w2})
    
    for p1_key, p2_key, winner, day_index, score in games_data:
        weight = get_mov_multiplier(score, event, mov_base_mult, mov_growth_rate)
        whr_system.create_game(side_a=p1_key, side_b=p2_key, winner=winner, time_step=day_index, handicap=0.0, weight=weight)
        
    whr_system.iterate(30)
    
    preds = []
    actuals = []
    
    for game in whr_system.games:
        prob = game.side_a_win_probability()
        prob = np.clip(prob, 1e-15, 1 - 1e-15)
        
        preds.append(prob)
        actuals.append(1 if game.winner == 'A' else 0)
        
    preds = np.array(preds)
    actuals = np.array(actuals)
    
    log_loss = -np.mean(actuals * np.log(preds) + (1 - actuals) * np.log(1 - preds))
    return log_loss

if __name__ == "__main__":
    events = ["MS", "WS", "MD", "WD", "XD"]
    w2 = 2.0
    
    # Based on Elo results, searching higher
    base_mult_vals = [0.80, 0.85, 0.90, 0.95]
    growth_rate_vals = [1.09, 1.11, 1.13, 1.15]
    
    for event in events:
        print(f"\n{'='*40}")
        print(f"MoV Grid Search for {event} (w2={w2})")
        print(f"{'='*40}")
        
        try:
            data = load_data(event, limit=5000)
            print(f"Loaded {len(data)} matches.")
            
            results = []
            for b in base_mult_vals:
                for g in growth_rate_vals:
                    print(f"Evaluating base={b}, growth={g}...")
                    try:
                        loss = evaluate_mov(data, w2, b, g, event)
                        print(f"  Log Loss: {loss:.5f}")
                        results.append((b, g, loss))
                    except Exception as e:
                        print(f"  Error with base={b}, growth={g}: {e}")
                        
            print(f"\n--- Results for {event} ---")
            results.sort(key=lambda x: x[2])
            for b, g, loss in results[:5]: # Top 5
                print(f"base={b:.2f}, growth={g:.3f} : Log Loss = {loss:.5f}")
                
        except Exception as e:
            print(f"Error loading data for {event}: {e}")
