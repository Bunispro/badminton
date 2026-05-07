import sqlite3
import json
from collections import defaultdict

CORE_DB_PATH = "bwf_data_2008-now__v1.sqlite"
CONFLICTS_FILE = "player_id_conflicts.json"
OUTPUT_MAP_FILE = "player_id_map.json"

def get_player_stats(conn, player_ids):
    """
    For a list of player IDs, get their match count and last match date.
    """
    stats = {pid: {'match_count': 0, 'last_date': '1900-01-01'} for pid in player_ids}
    
    if not player_ids:
        return stats

    placeholders = ','.join('?' for _ in player_ids)
    
    query = f"""
        SELECT
            mp.player_id,
            COUNT(mp.match_id) as match_count,
            MAX(m.match_date) as last_date
        FROM match_participants mp
        JOIN matches m ON mp.match_id = m.match_id
        WHERE mp.player_id IN ({placeholders})
        GROUP BY mp.player_id;
    """
    
    cursor = conn.cursor()
    cursor.execute(query, player_ids)
    
    for pid, count, last_date in cursor.fetchall():
        if pid in stats:
            stats[pid]['match_count'] = count
            stats[pid]['last_date'] = last_date
            
    return stats

def choose_canonical_id(stats):
    """
    Heuristic to choose the best ID from a set of conflicting IDs.
    Rule: Highest match count wins. Tie-break with most recent activity.
    """
    if not stats:
        return None
        
    # Find the best ID based on the heuristic
    best_id = max(stats.keys(), key=lambda pid: (stats[pid]['match_count'], stats[pid]['last_date']))
                
    return best_id

def main():
    print("--- Starting Player ID Conflict Resolution ---")
    
    try:
        with open(CONFLICTS_FILE, 'r', encoding='utf-8') as f:
            conflicts = json.load(f)
    except FileNotFoundError:
        print(f"[!] Error: '{CONFLICTS_FILE}' not found.")
        print("Please run the ingestion script at least once to generate it.")
        return
        
    print(f"Found {len(conflicts)} players with conflicting IDs.")
    
    with sqlite3.connect(CORE_DB_PATH) as conn:
        try:
            with open(OUTPUT_MAP_FILE, 'r', encoding='utf-8') as f:
                id_map = json.load(f)
            print(f"Loaded {len(id_map)} existing mappings from '{OUTPUT_MAP_FILE}'.")
        except (FileNotFoundError, json.JSONDecodeError):
            id_map = {}
            print(f"No existing map file found. Creating a new one.")
            
        generated_count = 0
        
        for name, conflicting_ids in conflicts.items():
            if len(conflicting_ids) < 2: continue
            
            stats = get_player_stats(conn, conflicting_ids)
            canonical_id = choose_canonical_id(stats)
            if not canonical_id: continue
            
            for pid in conflicting_ids:
                if pid != canonical_id and pid not in id_map:
                    id_map[pid] = canonical_id
                    generated_count += 1
                        
        with open(OUTPUT_MAP_FILE, 'w', encoding='utf-8') as f:
            json.dump(id_map, f, indent=4, sort_keys=True)
            
        print(f"\nGenerated {generated_count} new ID mappings.")
        print(f"Total mappings in '{OUTPUT_MAP_FILE}': {len(id_map)}")
        print("\n[✓] Process complete. You can now re-run the ingestion script.")

if __name__ == "__main__":
    main()