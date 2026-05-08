import scraper
import json
from datetime import datetime
from scraper import BwfScraper

scraper = BwfScraper(r"D:\chrome-scrap", headless=False)


with open("index/all_tournaments_2008_2026.json", "r", encoding="utf-8") as f:
    all_tournaments = json.load(f)

# --- NEW: Filter tournaments by start date (YYYY-MM-DD) ---
# Only tournaments with a start_date ON or AFTER this date will be scraped.
start_date_filter_str = "2026-03-01" # Example: Scrape tournaments from Jan 1, 2026 onwards
start_date_filter = datetime.strptime(start_date_filter_str, "%Y-%m-%d").date()

tournaments_to_scrape = [
    t for t in all_tournaments
    if t.get("start_date") and datetime.strptime(t["start_date"], "%Y-%m-%d %H:%M:%S").date() >= start_date_filter
]

print(f"Found {len(all_tournaments)} total tournaments in the index.")
print(f"Filtered down to {len(tournaments_to_scrape)} tournaments starting on or after {start_date_filter_str}.")


scraper.start()
scraper.scrape_many(tournaments_to_scrape)

scraper.stop()
