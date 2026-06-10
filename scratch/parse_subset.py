import sqlite3
import os
import sys

# Add root folder to sys.path so we can import parse_historical_rankings
sys.path.append("d:/badminton")
import parse_historical_rankings

parse_historical_rankings.DB_PATH = "elo_ratings.sqlite"
parse_historical_rankings.INPUT_DIR = "data_rankings"

def main():
    conn = sqlite3.connect("elo_ratings.sqlite")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bwf_historical_rankings (
            rank_date TEXT NOT NULL,
            week INTEGER NOT NULL,
            event TEXT NOT NULL,
            rank INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            player_name TEXT,
            country TEXT,
            points INTEGER,
            PRIMARY KEY (rank_date, event, rank, player_id)
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bwf_hist_player ON bwf_historical_rankings(player_id, rank_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bwf_hist_date ON bwf_historical_rankings(rank_date, event)")
    conn.commit()

    cursor.execute("SELECT DISTINCT rank_date FROM bwf_historical_rankings")
    parsed_dates = {row[0] for row in cursor.fetchall()}

    files = [f for f in os.listdir("data_rankings") if f.startswith("WR_") and f.lower().endswith(".xlsx")]
    print(f"Found {len(files)} Excel files in data_rankings.")

    parsed_count = 0
    for filename in sorted(files):
        rank_date, week = parse_historical_rankings.parse_date_week_from_filename(filename)
        if not rank_date or week is None:
            continue
        if rank_date in parsed_dates:
            continue
            
        file_path = os.path.join("data_rankings", filename)
        if os.path.getsize(file_path) == 0:
            continue
            
        rows = parse_historical_rankings.parse_xlsx(file_path, rank_date, week)
        if rows:
            cursor.executemany("""
                INSERT OR REPLACE INTO bwf_historical_rankings 
                (rank_date, week, event, rank, player_id, player_name, country, points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            conn.commit()
            print(f"  [SUCCESS] Ingested {len(rows)} entries for {rank_date} (Week {week})")
            parsed_count += 1
            if parsed_count >= 25: # Parse 25 files
                print("Reached target of 25 files. Stopping.")
                break

    conn.close()

if __name__ == "__main__":
    main()
