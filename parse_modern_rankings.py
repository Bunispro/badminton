import os
import sqlite3
from parse_historical_rankings import parse_xlsx, parse_pdf, parse_date_week_from_filename

DB_PATH = "elo_ratings.sqlite"
INPUT_DIR = "data_rankings"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get set of already parsed dates
    cursor.execute("SELECT DISTINCT rank_date FROM bwf_historical_rankings")
    parsed_dates = {row[0] for row in cursor.fetchall()}
    print(f"Found {len(parsed_dates)} dates already loaded in database.")
    
    files = [f for f in os.listdir(INPUT_DIR) if f.startswith("WR_") and f.lower().endswith((".xlsx", ".pdf"))]
    # Filter for files containing 2023, 2024, 2025, 2026
    modern_years = ["2023-", "2024-", "2025-", "2026-"]
    files = [f for f in files if any(yr in f for yr in modern_years)]
    print(f"Found {len(files)} modern files to parse in {INPUT_DIR}.")
    
    parsed_count = 0
    # Sort in reverse order so the newest (e.g. 2026) is parsed first!
    for filename in sorted(files, reverse=True):
        rank_date, week = parse_date_week_from_filename(filename)
        if not rank_date or week is None:
            continue
            
        if rank_date in parsed_dates:
            continue
            
        file_path = os.path.join(INPUT_DIR, filename)
        if os.path.getsize(file_path) == 0:
            print(f"Skipping empty file: {filename}")
            continue
            
        print(f"Parsing {filename}...")
        try:
            if filename.lower().endswith(".xlsx"):
                rows = parse_xlsx(file_path, rank_date, week)
            else:
                rows = parse_pdf(file_path, rank_date, week)
                
            if rows:
                cursor.executemany("""
                    INSERT OR REPLACE INTO bwf_historical_rankings 
                    (rank_date, week, event, rank, player_id, player_name, country, points)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, rows)
                conn.commit()
                print(f"  [SUCCESS] Ingested {len(rows)} entries for {rank_date} (Week {week}) into database.")
                parsed_count += 1
        except Exception as e:
            print(f"  [ERROR] Failed to parse {filename}: {e}")
            
    conn.close()
    print(f"Parser complete. Newly ingested weeks: {parsed_count}")

if __name__ == "__main__":
    main()
