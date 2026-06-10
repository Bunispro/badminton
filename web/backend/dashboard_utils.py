import sqlite3
import os

CORE_DB = "../../bwf_data_2008-now__v1.sqlite"
RATINGS_DB = "../../elo_ratings.sqlite"

def get_db_pulse_history():
    conn = sqlite3.connect(CORE_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Matches per month for the last 6 months
    cursor.execute("""
        SELECT strftime('%Y-%m', match_date) as month, COUNT(*) as count 
        FROM matches 
        WHERE match_date >= date('now', '-6 months') 
        GROUP BY month 
        ORDER BY month
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def check_whr_synergy():
    conn = sqlite3.connect(RATINGS_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%whr%'")
    tables = [r[0] for r in cursor.fetchall()]
    conn.close()
    return tables

if __name__ == "__main__":
    print("DB Pulse:", get_db_pulse_history())
    print("WHR Tables:", check_whr_synergy())
