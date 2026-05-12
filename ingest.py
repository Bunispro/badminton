import os
import re
import json
from db_ingest import init_db
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
    reports_batch,
    match_id,
    unresolved_flag,
    has_player_conflict, # New parameter
    invalid_scores,
    date_fallback,
    winner_mismatch,
    retired_or_walkover,
    invalid_participants,
    is_team_match
):
    report_tuple = (
        match_id,
        int(unresolved_flag),
        int(has_player_conflict), # New value in tuple
        int(invalid_scores),
        int(date_fallback),
        int(winner_mismatch),
        int(retired_or_walkover),
        int(invalid_participants),
        int(is_team_match),
        datetime.now(timezone.utc).isoformat()
    )
    reports_batch.append(report_tuple)

def load_player_id_mappings(cursor, mapping_file_path="player_id_map.json"):
    """Reads a JSON map and populates the player_id_mapping table."""
    if not os.path.exists(mapping_file_path):
        # This is not an error, just informational if the file doesn't exist.
        return

    with open(mapping_file_path, "r", encoding="utf-8") as f:
        id_map = json.load(f)

    mappings = list(id_map.items())
    if not mappings:
        return

    # First, ensure all canonical_ids exist in the players table
    canonical_ids_to_ensure = list(set(id_map.values()))
    
    # Filter out canonical_ids that already exist in players
    existing_players = set()
    if canonical_ids_to_ensure:
        placeholders = ','.join('?' for _ in canonical_ids_to_ensure)
        cursor.execute(f"SELECT player_id FROM players WHERE player_id IN ({placeholders})", canonical_ids_to_ensure)
        existing_players = {row[0] for row in cursor.fetchall()}

    players_to_insert = []
    for pid in canonical_ids_to_ensure:
        if pid not in existing_players:
            # Insert a placeholder player. Details will be filled in later by ensure_player
            # if a match involving this player is processed.
            players_to_insert.append((pid, None, None, None)) # name_display, name_normalized, country_code can be null initially

    if players_to_insert:
        cursor.executemany("""
            INSERT OR IGNORE INTO players (player_id, name_display, name_normalized, country_code)
            VALUES (?, ?, ?, ?)
        """, players_to_insert)
        print(f"Ensured {len(players_to_insert)} canonical players exist in 'players' table.")

    cursor.executemany("""
        INSERT INTO player_id_mapping (old_id, canonical_id)
        VALUES (?, ?)
        ON CONFLICT(old_id) DO UPDATE SET
            canonical_id=excluded.canonical_id
    """, mappings)
    print(f"Loaded/updated {len(mappings)} player ID mappings.")

def ensure_player(cursor, player_json, tournament_id, current_match_id, id_conflicts, unresolved_log_batch, id_mapping_cache, alias_cache, empty_names_log, alias_ambiguities) -> tuple[str | None, bool]:
    pid = player_json.get("id")
    name = player_json["nameDisplay"]
    norm = normalize_name(name)
    
    if pid is not None:
        pid = str(pid)
        if not norm:
            empty_names_log[pid] = name
        is_conflict = False

        # Check if this ID has been mapped to a canonical one
        if pid in id_mapping_cache:
            pid = id_mapping_cache[pid]

        # --- NEW CONFLICT DETECTION LOGIC ---
        # If we haven't already flagged a conflict for this name during this run...
        if norm not in id_conflicts:
            # ...check if another player ID is already using this normalized name.
            existing_pids = alias_cache.get(norm, set())
            other_pids = existing_pids - {pid}
            if other_pids:
                # Conflict detected!
                is_conflict = True
                all_conflicting_ids = other_pids.union({pid})
                id_conflicts[norm] = all_conflicting_ids

        country = player_json.get("countryName")

        cursor.execute("""
            INSERT INTO players (player_id, name_display, name_normalized, country_code)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                name_display=COALESCE(players.name_display, excluded.name_display),
                country_code=COALESCE(players.country_code, excluded.country_code),
                name_normalized=COALESCE(players.name_normalized, excluded.name_normalized)
        """, (pid, name, norm, country))

        # insert alias
        cursor.execute("""
            INSERT OR IGNORE INTO player_aliases (player_id, alias_normalized)
            VALUES (?, ?)
        """, (pid, norm))
        
        # Update cache
        if norm not in alias_cache:
            alias_cache[norm] = set()
        alias_cache[norm].add(pid)

        return pid, is_conflict

    # 2. Fallback to searching the aliases table if no explicit name mapping exists
    existing_pids = alias_cache.get(norm, set())
    if existing_pids:
        if len(existing_pids) > 1:
            alias_ambiguities[norm] = list(existing_pids)
        return list(existing_pids)[0], False

    # 3. If still not found, log as unresolved so it can be mapped later
    unresolved_log_batch.append((
        tournament_id,
        current_match_id,
        norm,
        datetime.now(timezone.utc).isoformat()
    ))

    return None, False

def is_valid_badminton_score_15(s1, s2):
    winner = max(s1, s2)
    loser = min(s1, s2)
    
    if winner < 15:
        return False
    
    if winner == 15:
        return loser <= 13
    
    if winner > 15 and winner < 21:
        return (winner - loser) == 2
    
    if winner == 21:
        return loser == 19 or loser == 20
        
    return False

def compute_score_winner(score_raw, match_date=None):
    team1_sets = 0
    team2_sets = 0

    use_15_system = False
    if match_date and match_date >= "2027-01-04":
        use_15_system = True

    def is_valid_badminton_score(s1, s2):
        winner = max(s1, s2)
        loser = min(s1, s2)
        
        if winner < 21:
            return False
        
        if winner == 21:
            return loser <= 19
        
        if winner > 21 and winner < 30:
            return (winner - loser) == 2
        
        if winner == 30:
            return loser == 28 or loser == 29
            
        return False

    def is_valid_score(s1, s2):
        if use_15_system:
            return is_valid_badminton_score_15(s1, s2)
        else:
            return is_valid_badminton_score(s1, s2)

    if isinstance(score_raw, list):
        for s in score_raw:
            home = s.get("home")
            away = s.get("away")
            if home is None or away is None:
                continue
            
            # Filter for point anomalies
            if not is_valid_score(home, away):
                return None

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

            # Filter for point anomalies
            if not is_valid_score(home, away):
                return None

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
    # 1. Remove accents and non-ASCII characters
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    
    # Replace hyphens with spaces to treat parts as separate words
    name = name.replace('-', ' ')
    name = re.sub(r"\[.*?\]", "", name).lower()
    # 2. Keep only alphanumeric words
    words = re.findall(r'\w+', name)
    # 3. Sort words alphabetically and join
    return " ".join(sorted(words))


# --- Event Classification Configuration ---
VALID_EVENTS = {"MS", "WS", "MD", "WD", "XD"}

# Patterns for blocking non-rating-eligible events
BLOCK_PREFIXES = {
    "bd", "bs", "gd", "gs",  # junior boys/girls singles/doubles
    "tpa", "tpi", "tapi", "tapa",  # team event buckets
    "bmst", "d ", "s ",  # para/class divisions often start like these
}
BLOCK_REGEX = re.compile(
    r"\b(u\d{2}|u\d{1})\b|wh\s*\d|sh\s*\d|sl\s*\d|su\s*\d|ss\s*\d|exhibition|plate|para",
    re.IGNORECASE
)

# Ordered patterns for canonical event classification
# Prioritize more specific (e.g., women's) over less specific (e.g., men's)
# Use regex for more robust matching
CANON_EVENT_PATTERNS = [
    ("WS", [r"women's singles", r"womens singles", r"women singles", r"\bws\b"]),
    ("WD", [r"women's doubles", r"womens doubles", r"women doubles", r"dobles femeninos", r"\bwd\b"]),
    ("MS", [r"men's singles", r"mens singles", r"men singles", r"\bms\b"]),
    ("MD", [r"men's doubles", r"mens doubles", r"men doubles", r"dobles masculinos", r"\bmd\b"]),
    ("XD", [r"mixed doubles", r"dobles mixtos", r"\bxd\b", r"mxd\b"]),
]

def canon_event(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip().lower()
    s = re.sub(r"\s+", " ", s)

    # 1. Hard block common non-open categories (highest priority)
    if any(s.startswith(p) for p in BLOCK_PREFIXES):
        return None
    if BLOCK_REGEX.search(s):
        return None

    # 2. Exact canonical matches (e.g., "ms", "ws")
    if s in {"ms","ws","md","wd","xd"}:
        return s.upper()

    # 3. Matches starting with discipline token (e.g., "ms open", "wd qualifiers")
    m = re.match(r"^(ms|ws|md|wd|xd)\b", s)
    if m:
        return m.group(1).upper()

    # 4. Keyword/Regex pattern matching (ordered by specificity/priority)
    for canonical_code, patterns in CANON_EVENT_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, s):
                return canonical_code

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

    # Exclude Junior and Senior events first
    if any(k in name for k in ["junior", "senior"]):
        return None

    if any(k in name for k in ["world championships", "olympic"]):
        return "T0"

    if "thomas" in name and "uber" in name and "finals" in name:
        return "T1"

    if "sudirman" in name:
        return "T1"

    if "championship" in name:
        if "european" in name or "asia" in name or "asian" in name:
            return "T2"

    if any(k in name for k in ["pan am", "africa", "oceania", "asian games"]):
        return "T3"

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

FOLDER_TIER_MAP = {
    "HSBC_BWF_World_Tour_Finals": "T0",
    "HSBC_BWF_World_Tour_Super_1000": "T1",
    "World_Superseries_Premier": "T1",
    "HSBC_BWF_World_Tour_Super_750": "T2",
    "World_Superseries": "T2",
    "HSBC_BWF_World_Tour_Super_500": "T3",
    "Grand_Prix_Gold": "T3",
    "HSBC_BWF_World_Tour_Super_300": "T4",
    "Grand_Prix": "T4",
    "BWF_Tour_Super_100": "T5",
    "International_Challenge": "T5",
    "International_Series": "T6",
    "Future_Series": "T6",
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

        tier = TIER_MAP.get(tier_raw)
        if tier is None:
            tier = classify_bwf_event(name)
            if tier is None and tier_raw == "BWF Events":
                is_continental = True
        

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


def ingest_folder(conn, folder_path, date_filter=None):
    cursor = conn.cursor()
    mapping_failures = {}
    id_conflicts = {}
    empty_names_log = {}
    alias_ambiguities = {}

    # Load player ID mappings from JSON into the database
    load_player_id_mappings(cursor)

    # Load mappings into memory for fast lookup
    cursor.execute("SELECT old_id, canonical_id FROM player_id_mapping")
    id_mapping_cache = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT alias_normalized, player_id FROM player_aliases")
    alias_cache = {}
    for alias, pid in cursor.fetchall():
        if alias not in alias_cache:
            alias_cache[alias] = set()
        alias_cache[alias].add(pid)

    # Load tournament index and build numeric_id → code mapping
    numeric_to_code = load_tournament_index(
        cursor,
        "index/all_tournaments_2008_2026.json"
    )

    for root, dirs, files in os.walk(folder_path):
        if date_filter:
            # In daily mode, only process the file for the specific date
            target_file = f"{date_filter}.json"
            if target_file in files:
                files_to_process = [target_file]
            else:
                continue # Skip this directory if the daily file isn't here
        else:
            # In full mode, process all sorted json files
            files_to_process = sorted([f for f in files if f.endswith(".json")])

        for file in files_to_process:

            # --- BATCHING ---
            matches_batch = []
            participants_batch = []
            reports_batch = []
            unresolved_log_batch = []

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
                # Fallback for Finals: try to get numeric ID from folder name
                folder_name = os.path.basename(root)
                numeric_id_match = re.match(r"^(\d+)_", folder_name)
                if numeric_id_match:
                    numeric_id = numeric_id_match.group(1)
                    cursor.execute("SELECT tournament_id FROM tournaments WHERE numeric_id = ?", (numeric_id,))
                    row = cursor.fetchone()
                    if row:
                        tournament_id = row[0]

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

            if tier is None:
                folder_name = os.path.basename(root)
                tier = FOLDER_TIER_MAP.get(folder_name)
                if tier:
                    cursor.execute("""
                        UPDATE tournaments
                        SET tier = ?
                        WHERE tournament_id = ?
                    """, (tier, tournament_id))
                    print(f"  [Folder Fallback] Set tier {tier} for {tournament_id} from folder: {folder_name}")

                        
            for top_level_item in matches:
                items_to_process = []
                is_team_tie = top_level_item.get("isTeamMatch") is True

                if is_team_tie:
                    # This is a team tie object. Log it and get sub-matches.
                    tie_id = str(top_level_item.get("id")) if top_level_item.get("id") else compute_hash(top_level_item)
                    log_ingestion_report(
                        reports_batch,
                        tie_id,
                        unresolved_flag=False,
                        invalid_scores=False,
                    has_player_conflict=False, # Default to False
                        date_fallback=False,
                        winner_mismatch=False,
                        retired_or_walkover=False,
                        invalid_participants=False,
                        is_team_match=True
                    )
                    if isinstance(top_level_item.get("matches"), list):
                        items_to_process.extend(top_level_item["matches"])
                else:
                    items_to_process.append(top_level_item)

                for m in items_to_process:
                    raw_match_id = m.get("id")
                    if isinstance(raw_match_id, int):
                        match_id = str(raw_match_id)
                    else:
                        match_id = compute_hash(m)
                    
                    score_status = m.get("scoreStatusValue")

                    retired_or_walkover = score_status in ["Retired", "Walkover"]
                    unresolved_flag = False
                    invalid_participants = False
                    player_conflict_flag = False # True if player ID conflict detected
                    winner_mismatch = False

                    # `.get(key, default)` does not apply when the JSON value is explicitly null.
                    # Normalize nulls to strings before inserting into NOT NULL / text columns.

                    event_raw = (m.get("matchTypeValue") or m.get("eventName") or "").strip()
                    event_canon = canon_event(event_raw)
                    round_name = (m.get("roundName") or "").strip()
                    court = (m.get("courtName") or "").strip()
                    if not event_canon:
                        event_canon = "UNKNOWN"
                    score_raw = m.get("score")
                    
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

                    # Add check to match date fallback
                    if date_fallback:
                        if not re.match(r"^\d{4}-\d{2}-\d{2}$", match_date):
                            print(f"Warning: Fallback date '{match_date}' from file '{file}' is not in YYYY-MM-DD format.")

                    # Score check moved here, passing match_date
                    invalid_scores = compute_score_winner(score_raw, match_date) is None

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
                            reports_batch,
                            match_id,
                            unresolved_flag,
                            player_conflict_flag, # Pass new flag
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
                        resolved_id, player_had_conflict = ensure_player(
                            cursor, p, tournament_id, match_id, id_conflicts, unresolved_log_batch, id_mapping_cache, alias_cache, empty_names_log, alias_ambiguities
                        )
                        if player_had_conflict:
                            player_conflict_flag = True # Set conflict flag, but not unresolved_flag
                        if resolved_id is None:
                            unresolved_flag = True # Only set unresolved_flag if ID is truly missing
                            continue
                        team1_ids.append(resolved_id)

                    for p in m["team2"]["players"]:
                        resolved_id, player_had_conflict = ensure_player(
                            cursor, p, tournament_id, match_id, id_conflicts, unresolved_log_batch, id_mapping_cache, alias_cache, empty_names_log, alias_ambiguities
                        )
                        if player_had_conflict:
                            player_conflict_flag = True # Set conflict flag, but not unresolved_flag
                        if resolved_id is None:
                            unresolved_flag = True # Only set unresolved_flag if ID is truly missing
                            continue
                        team2_ids.append(resolved_id)

                    # If any player in the match was truly unresolved, the match is invalid.
                    # If there were only conflicts (player_conflict_flag=True but unresolved_flag=False),
                    # the match can still be valid for rating if the conflict is resolved by mapping.
                    # So, player_conflict_flag does NOT directly invalidate the match for rating.

                    # Deduplicate player IDs to prevent UNIQUE constraint errors from bad data.
                    team1_ids = list(dict.fromkeys(team1_ids))
                    team2_ids = list(dict.fromkeys(team2_ids))

                    expected_players = 1 if event_canon in ("MS", "WS") else 2 if event_canon in ("MD", "WD", "XD") else None

                    if expected_players:
                        if len(team1_ids) != expected_players or len(team2_ids) != expected_players:
                            invalid_participants = True

                    if invalid_participants:
                        log_ingestion_report(
                            reports_batch,
                            match_id,
                            unresolved_flag, # Use the actual unresolved_flag
                            player_conflict_flag, # Pass new flag
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

                    matches_batch.append((
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

                    for pid in team1_ids:
                        participants_batch.append((match_id, 1, pid))

                    for pid in team2_ids:
                        participants_batch.append((match_id, 2, pid))

                    log_ingestion_report(
                        reports_batch,
                        match_id,
                        unresolved_flag, # Use the actual unresolved_flag
                        player_conflict_flag, # Pass new flag
                        invalid_scores,
                        date_fallback,
                        winner_mismatch,
                        retired_or_walkover,
                        invalid_participants,
                        is_team_match=False
                    )

            # --- BATCH EXECUTION (end of file) ---
            if not matches_batch and not reports_batch:
                continue

            print(f"  Committing {len(matches_batch)} matches from file: {file}")

            match_ids_in_batch = list({m[0] for m in matches_batch})

            if match_ids_in_batch:
                placeholders = ','.join('?' for _ in match_ids_in_batch)
                cursor.execute(f"DELETE FROM match_participants WHERE match_id IN ({placeholders})", match_ids_in_batch)
                cursor.execute(f"DELETE FROM matches WHERE match_id IN ({placeholders})", match_ids_in_batch)

            if matches_batch:
                cursor.executemany("""
                    INSERT INTO matches (
                        match_id, tournament_id, event_raw, event_canon, round, court,
                        match_date, score, winner_side, is_valid_for_rating, raw_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, matches_batch)

            if participants_batch:
                cursor.executemany("""
                    INSERT INTO match_participants (match_id, side, player_id)
                    VALUES (?, ?, ?)
                """, participants_batch)

            if reports_batch:
                cursor.executemany("""
                    INSERT INTO ingestion_report(
                        match_id, unresolved_players, has_player_conflict,
                        invalid_scores, date_fallback, winner_mismatch,
                        retired_or_walkover, invalid_participants,
                        is_team_match, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, reports_batch)

            if unresolved_log_batch:
                cursor.executemany("""
                    INSERT INTO unresolved_players_log
                    (tournament_id, match_id, normalized_name, timestamp)
                    VALUES (?, ?, ?, ?)
                """, unresolved_log_batch)

            conn.commit()

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

    if id_conflicts:
        report_path = "player_id_conflicts.json"
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                existing_conflicts = json.load(f)
                if not isinstance(existing_conflicts, dict):
                    existing_conflicts = {}
        except (FileNotFoundError, json.JSONDecodeError):
            existing_conflicts = {}

        # Merge new conflicts into existing ones
        for norm, new_ids_set in id_conflicts.items():
            # Get existing IDs for this name, default to an empty list
            existing_ids_list = existing_conflicts.get(norm, [])
            # Combine and deduplicate
            merged_ids = set(existing_ids_list).union(new_ids_set)
            # Store as a sorted list for consistent output
            existing_conflicts[norm] = sorted(list(merged_ids))

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(existing_conflicts, f, indent=2, sort_keys=True)

        print(f"\nFound and reported {len(id_conflicts)} new potential player ID conflicts.")
        print(f"Please review '{report_path}' and update 'player_id_map.json' if necessary.")

    if empty_names_log:
        report_path = "empty_normalized_names.json"
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
                if not isinstance(existing, dict):
                    existing = {}
        except (FileNotFoundError, json.JSONDecodeError):
            existing = {}
        existing.update(empty_names_log)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, sort_keys=True)
        print(f"Logged {len(empty_names_log)} names that normalized to empty string to {report_path}")

    if alias_ambiguities:
        report_path = "alias_ambiguities.json"
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
                if not isinstance(existing, dict):
                    existing = {}
        except (FileNotFoundError, json.JSONDecodeError):
            existing = {}
        existing.update(alias_ambiguities)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, sort_keys=True)
        print(f"Logged {len(alias_ambiguities)} alias ambiguities to {report_path}")




    print(f"Tournament mapping failure: {len(mapping_failures)}")


# if __name__ == "__main__":
#     ingest_folder("data")
