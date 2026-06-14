import os
import sys
import re
import json
import argparse
import urllib.request
import urllib.parse
import time
import sqlite3
from datetime import datetime, date
from bs4 import BeautifulSoup

# Try to import scraper and parser utilities
try:
    from scraper import BwfScraper
except ImportError:
    print("[Warning] Could not import BwfScraper from scraper.py. Tournament scraper won't work.")

try:
    from parse_historical_rankings import parse_xlsx, parse_pdf, parse_date_week_from_filename
except ImportError:
    print("[Warning] Could not import ranking parsers from parse_historical_rankings.py. Rankings parsing won't work.")

# Configuration Constants
FAILED_FILE = "data-non-wt/failed_tournaments.json"
INDEX_FILE = "index/all_tournaments_2008_2026.json"
DEFAULT_CHROME_PROFILE = r"D:\chrome-scrap"
RANKINGS_OUTPUT_DIR = "data_rankings"
DB_PATH = "elo_ratings.sqlite"
BASE_URL = "https://corporate.bwfbadminton.com/players/historical-rankings/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

def run_match_scraper(start_date_str, headless, chrome_profile):
    """
    Scrapes tournaments starting on or after the specified date.
    Equivalent to Run_scraper.py
    """
    print(f"\n--- Starting Tournament Match Scraper (Date Filter: {start_date_str}) ---")
    if not os.path.exists(INDEX_FILE):
        print(f"[Error] Index file not found: {INDEX_FILE}")
        return False
        
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        all_tournaments = json.load(f)
        
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    tournaments_to_scrape = []
    
    for t in all_tournaments:
        s_date_str = t.get("start_date")
        if s_date_str:
            try:
                # Accept formats "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
                if " " in s_date_str:
                    t_date = datetime.strptime(s_date_str, "%Y-%m-%d %H:%M:%S").date()
                else:
                    t_date = datetime.strptime(s_date_str, "%Y-%m-%d").date()
                    
                if t_date >= start_date:
                    tournaments_to_scrape.append(t)
            except Exception as e:
                print(f"[Warning] Failed parsing tournament date '{s_date_str}': {e}")

    print(f"Found {len(all_tournaments)} total tournaments in the index.")
    print(f"Filtered to {len(tournaments_to_scrape)} tournaments starting on or after {start_date_str}.")
    
    if not tournaments_to_scrape:
        print("No tournaments to scrape based on the current filter.")
        return True
        
    print(f"Initializing Selenium BwfScraper (headless={headless}, profile={chrome_profile})...")
    scraper_inst = BwfScraper(chrome_profile, headless=headless)
    scraper_inst.start()
    
    success = False
    try:
        scraper_inst.scrape_many(tournaments_to_scrape)
        success = True
    except Exception as e:
        print(f"[Error] Scraper execution failed: {e}")
    finally:
        scraper_inst.stop()
        print("BwfScraper stopped.")
        
    return success

def run_failed_scraper(headless, chrome_profile):
    """
    Retries scraping failed tournaments listed in failed_tournaments.json.
    Equivalent to Run_failed_scraper.py
    """
    print("\n--- Starting Failed Scraper Retry ---")
    if not os.path.exists(FAILED_FILE):
        print(f"[Info] No failed tournaments log found at: {FAILED_FILE}")
        return True
        
    if not os.path.exists(INDEX_FILE):
        print(f"[Error] Index file not found: {INDEX_FILE}")
        return False
        
    with open(FAILED_FILE, "r", encoding="utf-8") as f:
        failed_list = json.load(f)
        
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        all_tournaments = json.load(f)
        
    index_map = {t["url"]: t for t in all_tournaments if "url" in t}
    seen_urls = set()
    unique_failed = []
    
    for f_item in failed_list:
        url = f_item["url"]
        if url not in seen_urls:
            unique_failed.append(f_item)
            seen_urls.add(url)
            
    current_date = datetime.now().date()
    tournaments_to_retry = []
    skipped_future = 0
    
    for f_item in unique_failed:
        url = f_item["url"]
        meta = index_map.get(url)
        
        if not meta:
            # Fallback checks if not in index
            year_match = re.search(r"202[6-9]", url)
            if year_match and int(year_match.group(0)) > current_date.year:
                skipped_future += 1
                continue
                
            tournaments_to_retry.append({
                "url": url,
                "category": f_item.get("tier", "Unknown"),
                "name": url.split("/")[-1].replace("-", " ").title()
            })
            continue
            
        start_date_str = meta.get("start_date")
        if start_date_str:
            try:
                if " " in start_date_str:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S").date()
                else:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    
                if start_date > current_date:
                    skipped_future += 1
                    continue
            except Exception as e:
                print(f"[Warning] Error parsing date for {url}: {e}")
                
        tournaments_to_retry.append({
            "url": url,
            "category": meta.get("category") or f_item.get("tier") or "Unknown",
            "name": meta.get("name") or "Unknown Tournament"
        })
        
    print(f"Total failed entries listed: {len(failed_list)}")
    print(f"Unique failed URLs: {len(unique_failed)}")
    print(f"Skipped (future/unreleased): {skipped_future}")
    print(f"Tournaments to retry: {len(tournaments_to_retry)}")
    
    if not tournaments_to_retry:
        print("Nothing to retry.")
        return True
        
    print(f"Initializing Selenium BwfScraper for Retries (headless={headless}, profile={chrome_profile})...")
    scraper_inst = BwfScraper(chrome_profile, headless=headless)
    scraper_inst.start()
    
    success = False
    try:
        scraper_inst.scrape_many(tournaments_to_retry)
        success = True
    except Exception as e:
        print(f"[Error] Failed scraper execution failed: {e}")
    finally:
        scraper_inst.stop()
        print("BwfScraper stopped.")
        
    return success

def run_rankings_downloader(years):
    """
    Downloads BWF ranking files for specified years.
    Equivalent to scrape_historical_rankings.py
    """
    print(f"\n--- Starting BWF Rankings Downloader (Years: {years}) ---")
    os.makedirs(RANKINGS_OUTPUT_DIR, exist_ok=True)
    
    def fetch_page(year):
        url = f"{BASE_URL}?ryear={year}"
        print(f"Fetching listings for year: {year}...")
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.read()
        except Exception as e:
            print(f"[Error] Fetching page for year {year}: {e}")
            return None
            
    def download_file(file_url, dest_path):
        if os.path.exists(dest_path) and os.stat(dest_path).st_size > 0:
            return True
            
        parsed = urllib.parse.urlparse(file_url)
        encoded_path = urllib.parse.quote(parsed.path)
        url_to_fetch = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, encoded_path, parsed.params, parsed.query, parsed.fragment))
        
        print(f"Downloading: {file_url} -> {dest_path}")
        req = urllib.request.Request(url_to_fetch, headers=HEADERS)
        
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as response, open(dest_path, "wb") as f:
                    f.write(response.read())
                print(f"  [OK] Downloaded successfully.")
                time.sleep(1) # Rate limiting
                return True
            except Exception as e:
                print(f"  [ERROR] Attempt {attempt + 1} failed: {e}")
                if os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except:
                        pass
                time.sleep(2)
        return False

    def parse_filename_meta(filename):
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
        week_match = re.search(r"[Ww]eek\s*[-_]?\s*(\d+)", filename)
        date_str = date_match.group(1) if date_match else None
        week_num = int(week_match.group(1)) if week_match else None
        return date_str, week_num

    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    for year in years:
        html_content = fetch_page(year)
        if not html_content:
            continue
            
        soup = BeautifulSoup(html_content, "html.parser")
        links = soup.find_all("a", href=True)
        found_links = 0
        
        for link in links:
            href = link["href"].strip()
            if "extranet.bwf.sport" in href and ("/document-system/" in href or "/docs/" in href):
                found_links += 1
                raw_filename = os.path.basename(urllib.parse.unquote(href))
                date_str, week_num = parse_filename_meta(raw_filename)
                
                if not date_str or week_num is None:
                    link_text = link.get_text() or link.get("title") or ""
                    date_str, week_num = parse_filename_meta(link_text)
                    
                if date_str and week_num is not None:
                    ext = os.path.splitext(raw_filename)[1].lower() or ".pdf"
                    dest_filename = f"WR_{date_str}_Week_{week_num}{ext}"
                    dest_path = os.path.join(RANKINGS_OUTPUT_DIR, dest_filename)
                    
                    if os.path.exists(dest_path) and os.stat(dest_path).st_size > 0:
                        skipped_count += 1
                        continue
                        
                    if download_file(href, dest_path):
                        success_count += 1
                    else:
                        fail_count += 1
                else:
                    print(f"[Warning] Could not parse metadata from URL or link text: {href}")
                    
        print(f"Year {year}: Found {found_links} BWF ranking documents.")
        
    print("\n--- BWF Downloader Run Summary ---")
    print(f"Successfully Downloaded : {success_count} files")
    print(f"Failed Downloads        : {fail_count} files")
    print(f"Already Existed         : {skipped_count} files")
    print("---------------------------------")
    return fail_count == 0

def run_rankings_parser():
    """
    Parses downloaded modern PDF/XLSX ranking sheets and updates database.
    Equivalent to parse_modern_rankings.py
    """
    print("\n--- Starting BWF Rankings Parser ---")
    if not os.path.exists(DB_PATH):
        print(f"[Error] Database not found: {DB_PATH}")
        return False
        
    if not os.path.exists(RANKINGS_OUTPUT_DIR):
        print(f"[Error] Rankings directory not found: {RANKINGS_OUTPUT_DIR}")
        return False
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if table exists, create if not
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bwf_historical_rankings (
            rank_date TEXT,
            week INTEGER,
            event TEXT,
            rank INTEGER,
            player_id TEXT,
            player_name TEXT,
            country TEXT,
            points INTEGER,
            PRIMARY KEY (rank_date, event, rank, player_id)
        )
    """)
    conn.commit()
    
    cursor.execute("SELECT DISTINCT rank_date FROM bwf_historical_rankings")
    parsed_dates = {row[0] for row in cursor.fetchall()}
    print(f"Found {len(parsed_dates)} dates already parsed in database.")
    
    files = [f for f in os.listdir(RANKINGS_OUTPUT_DIR) if f.startswith("WR_") and f.lower().endswith((".xlsx", ".pdf"))]
    # Filter for years 2023, 2024, 2025, 2026
    modern_years = ["2023-", "2024-", "2025-", "2026-"]
    files = [f for f in files if any(yr in f for yr in modern_years)]
    print(f"Found {len(files)} modern ranking sheets available in {RANKINGS_OUTPUT_DIR}.")
    
    parsed_count = 0
    # Process newest files first
    for filename in sorted(files, reverse=True):
        rank_date, week = parse_date_week_from_filename(filename)
        if not rank_date or week is None:
            continue
            
        if rank_date in parsed_dates:
            continue
            
        file_path = os.path.join(RANKINGS_OUTPUT_DIR, filename)
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
    print(f"BWF Parser complete. Newly ingested weeks: {parsed_count}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Consolidated BWF scraper and parser orchestrator.")
    parser.add_argument(
        "--mode", 
        choices=["matches", "failed", "rankings-download", "rankings-parse", "all"], 
        default="matches", 
        help="Scraper mode to run. 'matches' scrapes tournaments. 'failed' retries failed runs. 'rankings-download' downloads rankings sheets. 'rankings-parse' parses sheet contents."
    )
    parser.add_argument(
        "--start-date", 
        default="2026-01-01", 
        help="Start date filter (YYYY-MM-DD) for 'matches' mode. Only tournaments starting on or after this date will be scraped. (Default: 2026-01-01)"
    )
    parser.add_argument(
        "--headless", 
        action="store_true", 
        default=False, 
        help="Run match scraper in headless mode (default: False for manual execution, True for automated pipelines)"
    )
    parser.add_argument(
        "--chrome-profile", 
        default=DEFAULT_CHROME_PROFILE, 
        help=f"Path to custom Chrome profile folder. (Default: {DEFAULT_CHROME_PROFILE})"
    )
    parser.add_argument(
        "--years", 
        default="2024,2025,2026", 
        help="Comma-separated years for rankings download. (Default: 2024,2025,2026)"
    )

    args = parser.parse_args()
    
    # Parse years string into list of ints
    try:
        years_list = [int(y.strip()) for y in args.years.split(",") if y.strip().isdigit()]
    except Exception as e:
        print(f"[Error] Failed to parse years parameter: {e}")
        sys.exit(1)
        
    start_time = time.time()
    success = False
    
    if args.mode == "matches":
        success = run_match_scraper(args.start_date, args.headless, args.chrome-profile if hasattr(args, "chrome-profile") else args.chrome_profile)
    elif args.mode == "failed":
        success = run_failed_scraper(args.headless, args.chrome_profile)
    elif args.mode == "rankings-download":
        success = run_rankings_downloader(years_list)
    elif args.mode == "rankings-parse":
        success = run_rankings_parser()
    elif args.mode == "all":
        print("=== RUNNING ALL SCRAPING STAGES IN SEQUENCE ===")
        # 1. Download modern rankings
        rd_ok = run_rankings_downloader(years_list)
        # 2. Parse modern rankings
        rp_ok = run_rankings_parser()
        # 3. Scrape match updates
        m_ok = run_match_scraper(args.start_date, args.headless, args.chrome_profile)
        # 4. Retry failed matches
        f_ok = run_failed_scraper(args.headless, args.chrome_profile)
        success = rd_ok and rp_ok and m_ok and f_ok
        
    duration = time.time() - start_time
    status = "SUCCESS" if success else "FAILED"
    print(f"\n==========================================")
    print(f" Orchestrator Completed: {status} in {duration:.2f} seconds.")
    print(f"==========================================")
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
