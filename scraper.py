from itertools import count
import os
import re
import json
import random
import time
import datetime
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright


class BwfScraper:

    def __init__(self, chrome_profile_path, headless=False):
        self.chrome_profile_path = chrome_profile_path
        self.headless = headless
        self.context = None
        self.page = None

    # -----------------------------
    # Browser setup / teardown
    # -----------------------------
    def start(self):
        self.p = sync_playwright().start()

        self.context = self.p.chromium.launch_persistent_context(
            user_data_dir=self.chrome_profile_path,
            channel="chrome",
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--disable-sync",
                "--no-first-run"
            ]
        )

        self.page = self.context.new_page()

    def stop(self):
        if self.context:
            self.context.close()
        if hasattr(self, "p"):
            self.p.stop()

    # -----------------------------
    # Utility helpers
    # -----------------------------

    def safe_folder_name(self, name):
        name = name.strip()
        name = re.sub(r"[^\w\s-]", "", name)  # remove weird chars
        name = name.replace(" ", "_")
        return name

    #get tournament list from calendar (need manual filter applying)
    def harvest_calendar_manual_filter(self, out_root="index", wait_seconds=15):

        import os
        import json

        os.makedirs(out_root, exist_ok=True)

        print("\n===== MANUAL FILTER MODE =====")

        # 1️⃣ Open calendar
        self.page.goto("https://bwfbadminton.com/calendar/", wait_until="domcontentloaded")
        self.page.wait_for_timeout(3000)

        # 2️⃣ Switch to ALL TOURNAMENTS
        print("Switching to ALL TOURNAMENTS...")
        with self.page.expect_response(
            lambda r: "vue-tournaments-search" in r.url and r.status == 200,
            timeout=30000
        ):
            self.page.locator("text=ALL TOURNAMENTS").click()

        self.page.wait_for_timeout(2000)

        # 3️⃣ Manual filter window
        print(f"\n⏳ You have {wait_seconds} seconds to:")
        print("   - Set From: 01/01/2008")
        print("   - Set To:   31/12/2026")
        print("   - Ensure you're on Page 1\n")

        self.page.wait_for_timeout(wait_seconds * 1000)

        print("Starting automatic pagination...\n")

        all_rows = []
        seen_codes = set()
        page_num = 1

        # ---- Capture first page manually by forcing a fresh API call ----
        next_btn = self.page.locator("a.button:has(i.fa-chevron-right)")

        if next_btn.count() == 0:
            print("❌ Next button not found. Filter likely not applied correctly.")
            return

        # Trigger first response
        with self.page.expect_response(
            lambda r: "vue-tournaments-search" in r.url and r.status == 200,
            timeout=30000
        ) as resp_info:
            next_btn.first.click()

        data = resp_info.value.json()

        # Go back to page 1
        prev_btn = self.page.locator("a.button:has(i.fa-chevron-left)")

        if prev_btn.count() > 0:
            with self.page.expect_response(
                lambda r: "vue-tournaments-search" in r.url and r.status == 200,
                timeout=30000
            ) as resp_info:
                prev_btn.first.click()
            data = resp_info.value.json()

        # ---- Pagination Loop ----
        while True:

            batch = data.get("results", {}).get("data", [])
            print(f"Page {page_num}: {len(batch)} tournaments")

            if not batch:
                break

            for t in batch:
                code = t.get("code")
                if not code or code in seen_codes:
                    continue
                seen_codes.add(code)
                all_rows.append(t)

            # Get next arrow
            next_btn = self.page.locator("a.button:has(i.fa-chevron-right)")

            if next_btn.count() == 0:
                print("No next button found.")
                break

            classes = next_btn.first.get_attribute("class") or ""
            if "disabled" in classes:
                print("Reached last page.")
                break

            page_num += 1

            with self.page.expect_response(
                lambda r: "vue-tournaments-search" in r.url and r.status == 200,
                timeout=30000
            ) as resp_info:
                next_btn.first.click()

            data = resp_info.value.json()
            self.page.wait_for_timeout(1200)

        print("\nTotal tournaments collected:", len(all_rows))

        out_path = os.path.join(out_root, "all_tournaments_2008_2026.json")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_rows, f, ensure_ascii=False, indent=2)

        print("Saved:", out_path)
        print("===== DONE =====\n")


    def make_tournament_folder(self, tournament_url, tier, root="data-non-wt"):

        path_parts = urlparse(tournament_url).path.strip("/").split("/")

        if "tournament" in path_parts:
            i = path_parts.index("tournament")
            tournament_id = path_parts[i + 1]
            slug = path_parts[i + 2]
        elif "results" in path_parts:
            i = path_parts.index("results")
            tournament_id = path_parts[i + 1]
            slug = path_parts[i + 2]
        else:
            raise ValueError(f"Unknown URL structure: {tournament_url}")

        folder_name = f"{tournament_id}_{slug}"

        tier_folder = self.safe_folder_name(tier)

        out_dir = os.path.join(root, tier_folder, folder_name)
        os.makedirs(out_dir, exist_ok=True)

        return out_dir


    def extract_day_urls(self):
        links = self.page.locator("#ajaxTabsResults a")
        urls = []

        for i in range(links.count()):
            href = links.nth(i).get_attribute("href")
            if href and "/results/" in href:
                urls.append(href)

        # dedupe preserve order
        seen = set()
        clean = []
        for u in urls:
            if u not in seen:
                clean.append(u)
                seen.add(u)

        return clean

    def date_from_url(self, url):
        m = re.search(r"/(\d{4}-\d{2}-\d{2})", url)
        return m.group(1) if m else None
    
    def human_pause(self, min_ms=800, max_ms=2000):
        delay = random.randint(min_ms, max_ms)
        self.page.wait_for_timeout(delay)

    def human_mouse_move(self):
        self.page.mouse.move(
            random.randint(100, 800),
            random.randint(100, 600),
            steps=random.randint(5, 20)
        )

    def human_scroll(self):
        self.page.mouse.wheel(0, random.randint(200, 800))

    def log_failed_tournament(self, tournament_url, tier, error_message, root="data-non-wt"):


        fail_path = os.path.join(root, "failed_tournaments.json")

        record = {
            "url": tournament_url,
            "tier": tier,
            "error": str(error_message),
            "timestamp": datetime.datetime.now().isoformat()
        }

        # Load existing failures
        if os.path.exists(fail_path):
            with open(fail_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except:
                    data = []
        else:
            data = []

        data.append(record)

        with open(fail_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print("⚠ Logged failure to file.")


    # -----------------------------
    # Core scraping
    # -----------------------------
    def scrape_one_tournament(self, tournament_url, tier):

        if "bwfworldtourfinals" in tournament_url:
            return self.scrape_finals(tournament_url, tier)
        if "bwfworldtour" in tournament_url:
            return self.scrape_one_tournament_World_Tour(tournament_url, tier)
        else:
            return self.scrape_non_wt_tournament(tournament_url, tier)
        
    def scrape_non_wt_tournament(self, tournament_url, tier):

        print("\n==============================")
        print("Scraping NON-WT:", tournament_url)

        self.page.goto(tournament_url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(3000)

        # Locate day tabs (exclude podium)
        day_tabs = self.page.locator("#ajaxTabsResults li a:not([data-key='podium'])")
        total_days = day_tabs.count()

        print("Day tabs found (excluding podium):", total_days)

        if total_days == 0:
            print("❌ No day tabs found.")
            return

        # -----------------------------
        # 1️⃣ Click FIRST day to detect team tournament
        # -----------------------------
        first_tab = day_tabs.nth(0)
        first_date = first_tab.get_attribute("data-key")
        first_label = first_tab.inner_text().strip()

        print(f"Detecting tournament type via first day: {first_label} ({first_date})")

        self.human_mouse_move()
        self.human_scroll()
        self.human_pause(1000, 3000)

        try:
            with self.page.expect_response(
                lambda r: (
                    "api/tournaments/day-matches?" in r.url
                    and f"date={first_date}" in r.url
                    and "order=" in r.url
                    and "court=" in r.url
                    and "/courts" not in r.url
                    and "/players" not in r.url
                    and r.status == 200
                ),
                timeout=30000
            ) as resp_info:

                first_tab.click()

            first_data = resp_info.value.json()

        except Exception as e:
            print("❌ Failed on first day detection:", e)
            return

        # -----------------------------
        # 2️⃣ Detect team tournament
        # -----------------------------
        is_team = False
        if first_data and isinstance(first_data, list):
            if first_data[0].get("isTeamMatch"):
                is_team = True
                print("⚠ Team tournament detected.")

        if is_team:
            tier = tier + "_TEAM"

        # -----------------------------
        # 3️⃣ Create folder AFTER detection
        # -----------------------------
        out_dir = self.make_tournament_folder(
            tournament_url,
            tier,
            root="data-non-wt"
        )

        # Save first day
        first_out_path = os.path.join(out_dir, f"{first_date}.json")

        if not os.path.exists(first_out_path):
            with open(first_out_path, "w", encoding="utf-8") as f:
                json.dump(first_data, f, ensure_ascii=False, indent=2)

            print("Saved:", first_date, "matches:", len(first_data))
        else:
            print(f"Skipping {first_date} (already saved)")

        self.human_pause(1500, 4000)

        # -----------------------------
        # 4️⃣ Process remaining days
        # -----------------------------
        for i in range(1, total_days):

            day_tabs = self.page.locator("#ajaxTabsResults li a:not([data-key='podium'])")
            tab = day_tabs.nth(i)

            date_key = tab.get_attribute("data-key")
            day_label = tab.inner_text().strip()

            out_path = os.path.join(out_dir, f"{date_key}.json")

            if os.path.exists(out_path):
                print(f"Skipping {date_key} (already saved)")
                continue

            print(f"Clicking day {i+1}/{total_days}: {day_label} ({date_key})")

            self.human_mouse_move()
            self.human_scroll()
            self.human_pause(1000, 3000)

            try:
                with self.page.expect_response(
                    lambda r: (
                        "api/tournaments/day-matches?" in r.url
                        and f"date={date_key}" in r.url
                        and "order=" in r.url
                        and "court=" in r.url
                        and "/courts" not in r.url
                        and "/players" not in r.url
                        and r.status == 200
                    ),
                    timeout=30000
                ) as resp_info:

                    tab.click()

                data = resp_info.value.json()

            except Exception as e:
                print("❌ Failed on day:", date_key, e)
                continue

            if not data:
                print("Empty day data.")
                continue

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print("Saved:", date_key, "matches:", len(data))

            self.human_pause(1500, 4000)

        print("===== COMPLETED NON-WT =====\n")

        
        
    def scrape_one_tournament_World_Tour(self, tournament_url, tier):

        print("\n==============================")
        print("Scraping:", tournament_url)

        out_dir = self.make_tournament_folder(tournament_url, tier, root = "data_wt")
        print("Saving to:", out_dir)
        
        self.page.goto(tournament_url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(random.randint(4000, 8000))

        day_urls = self.extract_day_urls()
        print("Found days:", len(day_urls) - 1)
        time.sleep(random.uniform(10, 25))
        
        for day_url in day_urls:
            day = self.date_from_url(day_url)
            if not day:
                continue

            out_path = os.path.join(out_dir, f"{day}.json")

            if os.path.exists(out_path):
                print("Already have", day, "- skipping")
                continue

            print("Visiting:", day_url)

            try:
                with self.page.expect_response(
                    lambda r: (
                        "api/tournaments/day-matches?" in r.url
                        and "date=" in r.url
                        and "court=" in r.url
                        and r.status == 200
                    ),
                    timeout=20000
                ) as response_info:
                    self.page.goto(day_url, wait_until="domcontentloaded")

                response = response_info.value

                try:
                    data = response.json()
                except Exception:
                    raise ValueError("Failed to parse JSON")

                # JSON conditioning
                if (
                    isinstance(data, list)
                    and data
                    and isinstance(data[0], dict)
                    and "team1" in data[0]
                    and "team2" in data[0]
                ):
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    print("Saved:", day, "matches:", len(data))

                else:
                    raise ValueError("Invalid or empty match data")

                # small buffer after successful capture
                self.page.wait_for_timeout(2000)

            except Exception as e:
                print(f"❌ Tournament failed on {day}: {e}")
                print("Aborting this tournament.")
                return  # stop entire tournament immediately

            # human-ish behavior AFTER successful save
            self.page.mouse.wheel(0, random.randint(200, 800))
            self.page.mouse.move(random.randint(100, 600), random.randint(100, 600))
            self.page.wait_for_timeout(random.randint(6000, 12000))

        print(f"===== COMPLETED TOURNAMENT: {tournament_url} =====\n")

    def scrape_finals(self, tournament_url, tier):

        print("\n==============================")
        print("Scraping FINALS:", tournament_url)

        out_dir = self.make_tournament_folder(tournament_url, tier, root="data_wt")

        self.page.goto(tournament_url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(random.randint(4000, 8000))

        title_locator = self.page.locator(".box-results-tournament h2")

        if title_locator.count() > 0:
            tournament_name = title_locator.first.inner_text().strip()
        else:
            tournament_name = self.slug_to_name(tournament_url)  # fallback

        all_links = self.page.locator("a").all()
        day_urls = []

        for link in all_links:
            href = link.get_attribute("href")
            if href and re.search(r"/\d{4}-\d{2}-\d{2}$", href):
                day_urls.append(href)

        # remove duplicates
        day_urls = list(dict.fromkeys(day_urls))

        for day_url in day_urls:
            print("Processing day:", day_url)
            day = self.date_from_url(day_url)
            if not day:
                continue

            out_path = os.path.join(out_dir, f"{day}.json")
            if os.path.exists(out_path):
                print("Already have", day, "- skipping")
                continue

            self.page.goto(day_url, wait_until="domcontentloaded")
            self.page.wait_for_timeout(random.randint(6000, 10000))

            rows = self.page.locator("li[class*='match-']")
            print("Match rows found:", rows.count())
            matches = []

            for i in range(rows.count()):
                row = rows.nth(i)

                # Extract class to get event
                row_class = row.get_attribute("class") or ""
                event = ""
                for part in row_class.split():
                    if part.startswith("draw-"):
                        event = part.replace("draw-", "")
                        break

                # Team extraction
                team1 = row.locator(".player1, .player2").all_inner_texts()
                team2 = row.locator(".player3, .player4").all_inner_texts()

                team1 = [p.strip() for p in team1 if p.strip()]
                team2 = [p.strip() for p in team2 if p.strip()]

                # Score
                score = row.locator(".score").inner_text().replace(",", "").strip()

                # Winner detection
                team1_winner = (
                    row.locator(".player1.player_winner, .player2.player_winner").count() > 0
                )

                if not team1_winner:
                    team1, team2 = team2, team1

                # Round name
                round_name = row.locator(".round").inner_text().strip()

                # Court info
                court_loc = row.locator(".round-location").inner_text().strip()
                court_no = row.locator(".round-court").inner_text().strip()
                court = f"{court_loc} {court_no}"

                matches.append({
                    "id": f"{tournament_url}_{day}_{i}",
                    "tournamentName": tournament_name,
                    "eventName": event,
                    "roundName": round_name,
                    "courtName": court,
                    "score": score,
                    "winner": 1,
                    "team1": {
                        "players": [{"id": None, "nameDisplay": p} for p in team1],
                        "countryCode": ""
                    },
                    "team2": {
                        "players": [{"id": None, "nameDisplay": p} for p in team2],
                        "countryCode": ""
                    }
                })

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(matches, f, ensure_ascii=False, indent=2)

            print("Saved:", day, "matches:", len(matches))

        print(f"===== COMPLETED FINAL: {tournament_url} =====\n")


    def scrape_many(self, tournament_list, min_sleep=7, max_sleep=12):

        count = 0

        for t in tournament_list:

            url = t["url"]
            tier = t.get("category", "Unknown")
            name = t.get("name", "Unknown Tournament")

            print("\n==============================")
            print(f"Scraping: {name}")
            print(f"Tier: {tier}")
            print("==============================")

            try:
                self.scrape_one_tournament(url, tier)
            except Exception as e:
                print("❌ Tournament crashed:", url)
                self.log_failed_tournament(url, tier, e)

            count += 1

            sleep_time = random.randint(min_sleep, max_sleep)
            print(f"\nSleeping {sleep_time} seconds...")
            time.sleep(sleep_time)

            if random.random() < 0.2:
                self.page.goto("https://www.google.com")
                time.sleep(random.uniform(10, 20))

            if count % 25 == 0:
                long_break = random.uniform(45, 90)
                print(f"\nLong break: {long_break/60:.1f} minutes...")
                time.sleep(long_break)


