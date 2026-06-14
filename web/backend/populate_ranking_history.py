import sqlite3
import time

conn = sqlite3.connect(r'd:\badminton\elo_ratings.sqlite')
cursor = conn.cursor()

print("Calculating and populating ranking_history from rating_history...")
start = time.time()
cursor.execute("DELETE FROM ranking_history")
cursor.execute("""
    INSERT INTO ranking_history (run_id, event, rating_date, player_id, rank)
    SELECT run_id, event, rating_date, player_id,
           ROW_NUMBER() OVER(PARTITION BY run_id, event, rating_date ORDER BY rating DESC) as rank
    FROM rating_history
""")
conn.commit()
print(f"ranking_history populated in {time.time() - start:.2f} seconds. Count: {cursor.execute('SELECT COUNT(*) FROM ranking_history').fetchone()[0]}")

print("Calculating and populating whr_ranking_history from whr_rating_history...")
start = time.time()
cursor.execute("DELETE FROM whr_ranking_history")
cursor.execute("""
    INSERT INTO whr_ranking_history (run_id, event, rating_date, player_id, rank)
    SELECT run_id, event, rating_date, player_id,
           ROW_NUMBER() OVER(PARTITION BY run_id, event, rating_date ORDER BY rating DESC) as rank
    FROM whr_rating_history
""")
conn.commit()
print(f"whr_ranking_history populated in {time.time() - start:.2f} seconds. Count: {cursor.execute('SELECT COUNT(*) FROM whr_ranking_history').fetchone()[0]}")

conn.close()
