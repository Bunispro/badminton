import sqlite3
import math

def get_metrics(run_id):
    conn = sqlite3.connect('elo_ratings.sqlite')
    c = conn.cursor()
    c.execute("""
        SELECT event, actual, predicted_prob 
        FROM prediction_log 
        WHERE run_id = ?
    """, (run_id,))
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        print(f"No data for {run_id}")
        return
        
    total_log_loss = 0
    correct = 0
    
    for event, actual, p in rows:
        total_log_loss += - (actual * math.log(p) + (1 - actual) * math.log(1 - p))
        pred_win = 1 if p > 0.5 else 0
        if pred_win == actual:
            correct += 1
            
    print(f"Run: {run_id}")
    print(f"  Log Loss: {total_log_loss / len(rows):.5f}")
    print(f"  Accuracy: {correct / len(rows):.5f}")

get_metrics('elo_final__20260508210837')
get_metrics('elo_mov__20260508212557')
