import scraper
import json
from scraper import BwfScraper

scraper = BwfScraper(r"C:\chrome-scrap", headless=False)


with open("index/all_tournaments_2008_2026.json", "r", encoding="utf-8") as f:
    tournaments = json.load(f)


scraper.start()
scraper.scrape_many(tournaments[1499:])

scraper.stop()

