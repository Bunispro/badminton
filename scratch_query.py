import sqlite3

conn = sqlite3.connect("elo_ratings.sqlite")
c = conn.cursor()
c.execute("SELECT run_id FROM run_metadata WHERE run_id LIKE '%final%' ORDER BY created_at DESC LIMIT 1")
run_id = c.fetchone()[0]

c.execute("""
    SELECT MIN(rating_date), MAX(rating_date), COUNT(*)
    FROM rating_history
    WHERE run_id = ? AND event = 'MS' AND player_id = '25831'
""", (run_id,))
print("Elo history range:", c.fetchone())

c.execute("""
    SELECT MIN(rating_date), MAX(rating_date), COUNT(*)
    FROM whr_rating_history
    WHERE event = 'MS' AND player_id = '25831'
""")
print("WHR history range:", c.fetchone())

conn.close()
