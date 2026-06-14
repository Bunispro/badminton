import sqlite3
conn = sqlite3.connect(r'd:\badminton\elo_ratings.sqlite')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*), MAX(rank_date) FROM bwf_historical_rankings")
print("BWF stats currently:", dict(cursor.fetchone()))
conn.close()
