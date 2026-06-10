import json
import os
import re
from datetime import datetime
from scraper import BwfScraper

# Constants
FAILED_FILE = r"d:\badminton\data-non-wt\failed_tournaments.json"
INDEX_FILE = r"d:\badminton\index\all_tournaments_2008_2026.json"
CHROME_PROFILE = r"D:\chrome-scrap"
CURRENT_DATE = datetime.now().date()

def run_failed_scraper():
    if not os.path.exists(FAILED_FILE):
        print(f"Error: {FAILED_FILE} not found.")
        return

    if not os.path.exists(INDEX_FILE):
        print(f"Error: {INDEX_FILE} not found.")
        return

    # Load failed tournaments
    with open(FAILED_FILE, "r", encoding="utf-8") as f:
        failed_list = json.load(f)

    # Load all tournaments for metadata (dates)
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        all_tournaments = json.load(f)

    # Create a lookup for all tournaments by URL
    index_map = {t["url"]: t for t in all_tournaments if "url" in t}

    # Deduplicate failed list by URL
    seen_urls = set()
    unique_failed = []
    for f in failed_list:
        url = f["url"]
        if url not in seen_urls:
            unique_failed.append(f)
            seen_urls.add(url)

    tournaments_to_retry = []
    skipped_future = 0
    skipped_no_meta = 0

    for f in unique_failed:
        url = f["url"]
        meta = index_map.get(url)

        if not meta:
            # If not in index, we can't check date easily. 
            # But most of these are likely past since they were attempted.
            # However, for safety and better data, we'll log it.
            print(f"Warning: No metadata found for {url}")
            # We'll still try to scrape it if it doesn't look like it's from the future
            # But let's be strict and skip for now or try to extract year from URL
            year_match = re.search(r"202[6-9]", url)
            if year_match and int(year_match.group(0)) > CURRENT_DATE.year:
                skipped_future += 1
                continue
            
            # If no meta, we can still provide category from the failure log
            tournaments_to_retry.append({
                "url": url,
                "category": f.get("tier", "Unknown"),
                "name": url.split("/")[-1].replace("-", " ").title()
            })
            continue

        start_date_str = meta.get("start_date")
        if start_date_str:
            try:
                # Format: "2008-01-15 00:00:00"
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S").date()
                if start_date > CURRENT_DATE:
                    skipped_future += 1
                    continue
            except Exception as e:
                print(f"Error parsing date for {url}: {e}")

        # Map metadata fields for scraper
        tournaments_to_retry.append({
            "url": url,
            "category": meta.get("category") or f.get("tier") or "Unknown",
            "name": meta.get("name") or "Unknown Tournament"
        })

    print(f"Total failed entries: {len(failed_list)}")
    print(f"Unique failed URLs: {len(unique_failed)}")
    print(f"Skipped (future): {skipped_future}")
    print(f"Tournaments to retry: {len(tournaments_to_retry)}")

    if not tournaments_to_retry:
        print("Nothing to scrape.")
        return

    # Initialize and run scraper
    # Setting headless=True for background execution.
    scraper = BwfScraper(CHROME_PROFILE, headless=True)
    scraper.start()
    
    try:
        scraper.scrape_many(tournaments_to_retry)
    except Exception as e:
        print(f"Scraper execution failed: {e}")
    finally:
        scraper.stop()

if __name__ == "__main__":
    run_failed_scraper()
