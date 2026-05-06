import os
import re
import json
from db_v2 import init_db
import unicodedata
import hashlib
from datetime import datetime, timezone

# Global Identity Map
identity_map = {}

def compute_hash(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True).encode("utf-8")
    ).hexdigest()

def log_ingestion_report(
    cursor,
    match_id,
    unresolved_flag,
    invalid_scores,
    date_fallback,
    winner_mismatch,
    retired_or_walkover,
    invalid_participants,
    is_team_match
):
    cursor.execute("""
        INSERT INTO ingestion_report(
            match_id,
            unresolved_players,
            invalid_scores,
            date_fallback,
            winner_mismatch,
            retired_or_walkover,
            invalid_participants,
            is_team_match,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        match_id,
        int(unresolved_flag),
        int(invalid_scores),
        int(date_fallback),
        int(winner_mismatch),
        int(retired_or_walkover),
        int(invalid_participants),
        int(is_team_match),
        datetime.now(timezone.utc).isoformat()
    ))

def ensure_player(cursor, player_json, tournament_id, current_match_id):
    pid = player_json.get("id")
    name = player_json["nameDisplay"]
    norm = normalize_name(name)
    country = player_json.get("countryCode") or ""

    if pid is not None:
        pid = str(pid)

        cursor.execute("""
            INSERT INTO players (player_id, name_display, name_normalized, country_code)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                name_display=excluded.name_display,
                country_code=excluded.country_code
        """, (pid, name, norm, country))

        # insert alias
        cursor.execute("""
            INSERT OR IGNORE INTO player_aliases (player_id, alias_normalized)
            VALUES (?, ?)
        """, (pid, norm))

        return pid

    # Finals fallback
    cursor.execute("""
        SELECT player_id FROM player_aliases
        WHERE alias_normalized = ?
    """, (norm,))
    row = cursor.fetchone()

    if row:
        return row[0]

    cursor.execute("""
        INSERT INTO unresolved_players_log
        VALUES (?, ?, ?, ?, ?)
    """, (
        tournament_id,
        current_match_id,
        name,
        norm,
        datetime.now(timezone.utc).isoformat()
    ))

    return None

def valid_date_string(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except:
        return False

def is_valid_score(score_data, format='3x21'):
    # Logic handles list-style scores and string scores
    games = []
    if isinstance(score_data, list):
        for s in score_data:
            if s.get('home') is not None and s.get('away') is not None:
                games.append((int(s['home']), int(s['away'])))
    elif isinstance(score_data, str):
        parsed = re.findall(r"(\d+)-(\d+)", score_data)
        games = [(int(h), int(a)) for h, a in parsed]

    if not games: return False
    
    # Simple check: Did someone reach at least 21 (or 15 for new format)?
    target = 15 if format == '3x15' else 21
    wins_team1 = 0
    wins_team2 = 0
    
    for h, a in games:
        if max(h, a) < target: return False
        if h > a: wins_team1 += 1
        else: wins_team2 += 1
        
    return max(wins_team1, wins_team2) >= 2

def compute_score_winner(score_raw):
    team1_sets = 0
    team2_sets = 0

    if isinstance(score_raw, list):
        for s in score_raw:
            home = s.get("home")
            away = s.get("away")
            if home is None or away is None:
                continue
            if home > away:
                team1_sets += 1
            elif away > home:
                team2_sets += 1

        if team1_sets > team2_sets:
            return 1
        if team2_sets > team1_sets:
            return 2

        return None
    
    elif isinstance(score_raw, str):
        games = re.findall(r"(\d+)-(\d+)", score_raw)

        if not games:
            return None

        for home, away in games:
            home = int(home)
            away = int(away)

            if home > away:
                team1_sets += 1
            elif away > home:
                team2_sets += 1

        if team1_sets > team2_sets:
            return 1
        elif team2_sets > team1_sets:
            return 2

        return None
    else:
        return None

def normalize_name(name):
    if not name: return ""
    # 1. Remove accents and brackets
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    name = re.sub(r"\[.*?\]", "", name).lower()
    # 2. Keep only alphanumeric words
    words = re.findall(r'\w+', name)
    # 3. Sort words alphabetically and join
    return " ".join(sorted(words))


VALID_EVENTS = {"MS","WS","MD","WD","XD"}

# stuff you explicitly do NOT want
BLOCK_PREFIXES = {
    "bd","bs","gd","gs",   # junior boys/girls singles/doubles
    "tpa","tpi","tapi","tapa",  # your "TP*" bucket
    "bmst","d ", "s ",     # para/class divisions often start like these
}
BLOCK_REGEX = re.compile(
    r"\b(u\d{2}|u\d{1})\b|wh\s*\d|sh\s*\d|sl\s*\d|su\s*\d|ss\s*\d|exhibition|plate|para",
    re.IGNORECASE
)

def canon_event(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip().lower()
    s = re.sub(r"\s+", " ", s)

    # hard block common non-open categories
    if any(s.startswith(p) for p in BLOCK_PREFIXES):
        return None
    if BLOCK_REGEX.search(s):
        return None

    # exact canonical
    if s in {"ms","ws","md","wd","xd"}:
        return s.upper()

    # starts with discipline token (safe-ish)
    m = re.match(r"^(ms|ws|md|wd|xd)\b", s)
    if m:
        return m.group(1).upper()

    # english & spanish-ish labels (optional)
    if "men's singles" in s or "mens singles" in s or "men singles" in s:
        return "MS"
    if "women's singles" in s or "womens singles" in s or "women singles" in s:
        return "WS"
    if "men's doubles" in s or "mens doubles" in s or "men doubles" in s or "dobles masculinos" in s:
        return "MD"
    if "women's doubles" in s or "womens doubles" in s or "women doubles" in s or "dobles femeninos" in s:
        return "WD"
    if "mixed doubles" in s or "dobles mixtos" in s or s == "mxd":
        return "XD"

    return None


def extract_finals_numeric_id(url: str):
    match = re.search(r"/results/(\d+)/", url)
    if match:
        return str(match.group(1))
    return None

def classify_bwf_event(tournament_name):
    if not tournament_name:
        return None

    name = tournament_name.lower()

    if any(k in name for k in ["world championships", "olympic"]):
        return "T0"

    if any(k in name for k in [
        "oceania championships",
        "asia championships",
        "all africa games",
        "asian games"
    ]):
        return None

    return None


def is_continental_tournament(name: str) -> bool:
    if not name:
        return False

    s = name.lower()

    keywords = [
        "asian championships",
        "european championships",
        "oceania championships",
        "pan am championships",
        "pan american championships",
        "african championships",
        "continental",
        "all africa",
        "all asian"
    ]

    return any(k in s for k in keywords)


TIER_MAP = {
    # T0
    "HSBC BWF World Tour Finals": "T0",

    # T1
    "HSBC BWF World Tour Super 1000": "T1",
    "World Superseries Premier": "T1",

    # T2
    "HSBC BWF World Tour Super 750": "T2",
    "World Superseries": "T2",

    # T3
    "HSBC BWF World Tour Super 500": "T3",
    "Grand Prix Gold": "T3",

    # T4
    "HSBC BWF World Tour Super 300": "T4",
    "Grand Prix": "T4",

    # T5
    "BWF Tour Super 100": "T5",
    "International Challenge": "T5",

    # T6
    "International Series": "T6",
    "Future Series": "T6",
}

def load_tournament_index(cursor, index_path):
    with open(index_path, "r", encoding="utf-8") as f:
        tournaments = json.load(f)

    numeric_to_code = {}


    for t in tournaments:
        is_continental = False
        code = t.get("code")
        numeric_id = str(t.get("id")) if t.get("id") else None

        if not code:
            continue

        if numeric_id:
            numeric_to_code[numeric_id] = code

        name = t.get("name") or ""
        start_date = t.get("start_date")
        end_date = t.get("end_date")
        location = t.get("location")
        country = t.get("country")
        prize_money = t.get("prize_money")
        url = t.get("url")
        tier_raw = t.get("category")
        if "bwfworldtour" in url.lower():
            source = "WT"
        else:
            source = "NON-WT"

        if is_continental_tournament(name):
            is_continental = True

        if tier_raw == "BWF Events":
            tier = classify_bwf_event(name)
            if tier == None:
                is_continental = True
        else:
            tier = TIER_MAP.get(tier_raw)
        

        year = int(start_date[:4]) if start_date else None
        cursor.execute("""
            INSERT INTO tournaments (
                tournament_id,
                numeric_id,
                name,
                year,
                start_date,
                end_date,
                location,
                source,
                country,
                prize_money,
                url,
                tier,
                is_continental
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tournament_id) DO UPDATE SET
                numeric_id=excluded.numeric_id,
                name=excluded.name,
                year=excluded.year,
                start_date=excluded.start_date,
                end_date=excluded.end_date,
                location=excluded.location,
                country=excluded.country,
                prize_money=excluded.prize_money,
                url=excluded.url,
                tier=excluded.tier,
                is_continental=excluded.is_continental
        """, (
            code,
            numeric_id,
            name,
            year,
            start_date,
            end_date,
            location,
            source,
            country,
            prize_money,
            url,
            tier,
            int(is_continental)
        ))

    return numeric_to_code

def pre_scan_identities(folder_path):
    print("Step 1: Building Identity Map from all files...")
    for root, _, files in os.walk(folder_path):
        for file in files:
            if not file.endswith(".json"): continue
            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        # Check top-level and nested matches (Team ties)
                        to_scan = item.get('matches', []) if item.get('isTeamMatch') else [item]
                        for m in to_scan:
                            for side in ['team1', 'team2']:
                                for p in m.get(side, {}).get('players', []):
                                    pid = str(p.get('id'))
                                    if pid and pid not in ['None', 'null']:
                                        norm = normalize_name(p['nameDisplay'])
                                        identity_map[norm] = pid
                except Exception: continue
    print(f"Identity Map built: {len(identity_map)} players recognized.")


def ingest_folder(db_path, folder_path):
    conn = init_db(db_path)
    cursor = conn.cursor()
    mapping_failures = {}

    # Load tournament index and build numeric_id → code mapping
    numeric_to_code = load_tournament_index(
        cursor,
        "index/all_tournaments_2008_2026.json"
    )

    for root, dirs, files in os.walk(folder_path):
        files = sorted(files)

        for file in files:
            if not file.endswith(".json"):
                continue

            path = os.path.join(root, file)

            with open(path, "r", encoding="utf-8") as f:
                matches = json.load(f)

            if not matches:
                continue
            
            # Resolve tournament_id
            match_url = None
            tournament_code = matches[0].get("tournamentCode")

            if tournament_code:
                tournament_id = tournament_code
            else:
                match_url = str(matches[0].get("id"))
                numeric_id = extract_finals_numeric_id(match_url)

                cursor.execute("""
                    SELECT tournament_id
                    FROM tournaments
                    WHERE numeric_id = ?
                """, (numeric_id,))

                row = cursor.fetchone()
                tournament_id = row[0] if row else None

            if not tournament_id:
                tournament_name = matches[0].get("tournamentName") or ""
                mapping_failures[root] = {
                    "tournament_path": root,
                    "tournament_name": tournament_name,
                }
                continue


            cursor.execute("""
                SELECT tier
                FROM tournaments
                WHERE tournament_id = ?
            """, (tournament_id,))
            tier_raw = cursor.fetchone()
            tier = tier_raw[0] if tier_raw else None

                           

            for m in matches:
                raw_match_id = m.get("id")
                if isinstance(raw_match_id, int):
                    match_id = str(raw_match_id)
                else:
                    match_id = compute_hash(m)

                if m.get("isTeamMatch") is True:
                    log_ingestion_report(
                        cursor,
                        match_id,
                        unresolved_flag=False,
                        invalid_scores=False,
                        date_fallback=False,
                        winner_mismatch=False,
                        retired_or_walkover=False,
                        invalid_participants=False,
                        is_team_match=True,
                    )
                    continue
                
                score_status = m.get("scoreStatusValue")

                retired_or_walkover = score_status in ["Retired", "Walkover"]
                unresolved_flag = False
                invalid_participants = False
                winner_mismatch = False

                # `.get(key, default)` does not apply when the JSON value is explicitly null.
                # Normalize nulls to strings before inserting into NOT NULL / text columns.

                event_raw = (m.get("eventName") or "").strip()
                event_canon = canon_event(event_raw)
                round_name = (m.get("roundName") or "").strip()
                court = (m.get("courtName") or "").strip()
                if not event_canon:
                    event_canon = "UNKNOWN"
                score_raw = m.get("score")
                invalid_scores = compute_score_winner(score_raw) is None

                # Resolve match date from payload when available; fallback to filename.
                match_time = m.get("matchTime")
                date_fallback = False
                if match_time:
                    try:
                        dt = datetime.strptime(match_time, "%Y-%m-%d %H:%M:%S")
                        match_date = dt.date().isoformat()
                    except ValueError:
                        match_date = file.replace(".json", "")
                        date_fallback = True
                else:
                    match_date = file.replace(".json", "")
                    date_fallback = True

                if isinstance(score_raw, list):
                    score = " ".join(
                        f"{s['home']}-{s['away']}" for s in score_raw
                    )
                elif isinstance(score_raw, str):
                    score = score_raw
                else:
                    score = ""



                winner = m.get("winner")

                if winner != compute_score_winner(score_raw):
                    winner_mismatch = True

                if not m.get("team1") or not m.get("team2"):
                    invalid_participants = True

                elif not isinstance(m["team1"].get("players"), list) \
                    or not isinstance(m["team2"].get("players"), list):
                        invalid_participants = True

                if invalid_participants:
                    log_ingestion_report(
                        cursor,
                        match_id,
                        unresolved_flag,
                        invalid_scores,
                        date_fallback,
                        winner_mismatch,
                        retired_or_walkover,
                        invalid_participants,
                        is_team_match=False
                    )
                    continue

                team1_ids = []
                team2_ids = []

                for p in m["team1"]["players"]:
                    resolved_id = ensure_player(
                        cursor, p, tournament_id, match_id
                    )
                    if resolved_id is None:
                        unresolved_flag = True
                        continue
                    team1_ids.append(resolved_id)

                for p in m["team2"]["players"]:
                    resolved_id = ensure_player(
                        cursor, p, tournament_id, match_id
                    )
                    if resolved_id is None:
                        unresolved_flag = True
                        continue
                    team2_ids.append(resolved_id)

                expected_players = 1 if event_canon in ("MS", "WS") else 2 if event_canon in ("MD", "WD", "XD") else None

                if expected_players:
                    if len(team1_ids) != expected_players or len(team2_ids) != expected_players:
                        invalid_participants = True

                if invalid_participants:
                    log_ingestion_report(
                        cursor,
                        match_id,
                        True,
                        invalid_scores,
                        date_fallback,
                        winner_mismatch,
                        retired_or_walkover,
                        invalid_participants,
                        is_team_match=False
                    )
                    continue
                VALID_TIERS = {"T0","T1","T2","T3","T4","T5","T6"}
                raw_hash = compute_hash(m)
                is_valid_for_rating = (
                    event_canon in VALID_EVENTS
                    and tier in VALID_TIERS
                    and not (
                        unresolved_flag
                        or invalid_scores
                        or winner_mismatch
                        or retired_or_walkover
                        or invalid_participants
                        # or is_continental

                    )
                )

                cursor.execute("""
                    INSERT INTO matches (
                        match_id,
                        tournament_id,
                        event_raw,
                        event_canon,
                        round,
                        court,
                        match_date,
                        score,
                        winner_side,
                        is_valid_for_rating,
                        raw_hash
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(match_id) DO UPDATE SET
                        score=excluded.score,
                        tournament_id=excluded.tournament_id,
                        winner_side=excluded.winner_side,
                        event_raw=excluded.event_raw,
                        event_canon=excluded.event_canon,
                        round=excluded.round,
                        is_valid_for_rating=excluded.is_valid_for_rating,
                        raw_hash=excluded.raw_hash
                """, (
                    match_id,
                    tournament_id,
                    event_raw,
                    event_canon,
                    round_name,
                    court,
                    match_date,
                    score,
                    winner,
                    is_valid_for_rating,
                    raw_hash
                ))

                cursor.execute("""
                    DELETE FROM match_participants
                    WHERE match_id = ?
                """, (match_id,))

                for pid in team1_ids:
                    cursor.execute("""
                        INSERT INTO match_participants (match_id, side, player_id)
                        VALUES (?, 1, ?)
                    """, (match_id, pid))

                for pid in team2_ids:
                    cursor.execute("""
                        INSERT INTO match_participants (match_id, side, player_id)
                        VALUES (?, 2, ?)
                    """, (match_id, pid))

                log_ingestion_report(
                    cursor,
                    match_id,
                    unresolved_flag,
                    invalid_scores,
                    date_fallback,
                    winner_mismatch,
                    retired_or_walkover,
                    invalid_participants,
                    is_team_match=False

                )

    if mapping_failures:
        report_path = "tournament_mapping_failures.json"
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
                if not isinstance(existing, list):
                    existing = []
        except FileNotFoundError:
            existing = []
        except json.JSONDecodeError:
            existing = []

        merged = {
            item.get("tournament_path"): item
            for item in existing
            if isinstance(item, dict) and item.get("tournament_path")
        }
        merged.update(mapping_failures)

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(
                list(merged.values()),
                f,
                ensure_ascii=False,
                indent=2
            )


    print(f"Tournament mapping failure: {len(mapping_failures)}")
    conn.commit()
    conn.close()


# if __name__ == "__main__":
#     ingest_folder("data")
