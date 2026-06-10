import sqlite3
import numpy as np
import math
from scipy.optimize import minimize
import os

CORE_DB = "d:/badminton/bwf_data_2008-now__v1.sqlite"
RATINGS_DB = "d:/badminton/elo_ratings.sqlite"

def load_data():
    print("Connecting to databases...")
    conn_core = sqlite3.connect(CORE_DB)
    conn_core.row_factory = sqlite3.Row
    cursor_core = conn_core.cursor()

    conn_ratings = sqlite3.connect(RATINGS_DB)
    conn_ratings.row_factory = sqlite3.Row
    cursor_ratings = conn_ratings.cursor()

    print("Fetching valid singles matches (MS & WS) and participants via JOIN...")
    # Fetch singles matches with valid flags and their participants in a single query
    cursor_core.execute("""
        SELECT m.match_id, m.match_date, m.event_canon, m.winner_side, mp.player_id, mp.side
        FROM matches m
        JOIN match_participants mp ON m.match_id = mp.match_id
        WHERE m.event_canon IN ('MS', 'WS') AND m.is_valid_for_rating = 1
        ORDER BY m.match_date DESC
        LIMIT 100000
    """)
    rows = cursor_core.fetchall()
    print(f"Loaded {len(rows)} database rows.")

    # Group participants by match
    matches = {}
    for r in rows:
        mid = r['match_id']
        if mid not in matches:
            matches[mid] = {
                "match_id": mid,
                "date": r['match_date'],
                "event": r['event_canon'],
                "winner": r['winner_side'],
                "parts": {}
            }
        matches[mid]["parts"][r['side']] = r['player_id']

    # Keep matches with both sides present
    valid_matches = [m for m in matches.values() if 1 in m["parts"] and 2 in m["parts"]]
    print(f"Found {len(valid_matches)} matches with both sides present.")

    # We will process a subset of 10000 matches to make it fast
    valid_matches = valid_matches[:10000]

    dataset = []
    print("Resolving BWF points and ELO ratings on match dates...")
    count = 0
    total = len(valid_matches)
    for m in valid_matches:
        count += 1
        if count % 5000 == 0:
            print(f"  Processed {count}/{total} matches...")
            
        mid = m['match_id']
        date = m['date']
        event = m['event']
        winner = m['winner']

        p1_id = m["parts"][1]
        p2_id = m["parts"][2]

        # Get BWF points for Side 1
        cursor_ratings.execute("""
            SELECT points FROM bwf_historical_rankings
            WHERE player_id = ? AND event = ? AND rank_date <= ?
            ORDER BY rank_date DESC LIMIT 1
        """, (p1_id, event, date))
        row1 = cursor_ratings.fetchone()
        pts1 = row1['points'] if row1 else None

        # Get BWF points for Side 2
        cursor_ratings.execute("""
            SELECT points FROM bwf_historical_rankings
            WHERE player_id = ? AND event = ? AND rank_date <= ?
            ORDER BY rank_date DESC LIMIT 1
        """, (p2_id, event, date))
        row2 = cursor_ratings.fetchone()
        pts2 = row2['points'] if row2 else None

        # Get ELO ratings on match date (for comparison)
        cursor_ratings.execute("""
            SELECT rating FROM rating_history
            WHERE run_id LIKE '%final%' AND player_id = ? AND event = ? AND rating_date < ?
            ORDER BY rating_date DESC LIMIT 1
        """, (p1_id, event, date))
        erow1 = cursor_ratings.fetchone()
        elo1 = erow1['rating'] if erow1 else 1000.0

        cursor_ratings.execute("""
            SELECT rating FROM rating_history
            WHERE run_id LIKE '%final%' AND player_id = ? AND event = ? AND rating_date < ?
            ORDER BY rating_date DESC LIMIT 1
        """, (p2_id, event, date))
        erow2 = cursor_ratings.fetchone()
        elo2 = erow2['rating'] if erow2 else 1000.0

        if pts1 is not None and pts2 is not None and pts1 > 0 and pts2 > 0:
            actual = 1 if winner == 1 else 0
            dataset.append({
                "match_id": mid,
                "date": date,
                "event": event,
                "pts1": pts1,
                "pts2": pts2,
                "elo1": elo1,
                "elo2": elo2,
                "actual": actual
            })

    conn_core.close()
    conn_ratings.close()
    print(f"Constructed dataset with {len(dataset)} matches having BWF points for both sides.")
    return dataset

def calibrate_difference_model(dataset):
    # P(win) = 1 / (1 + 10^(-gamma * (pts1 - pts2)))
    # We want to find optimal gamma.
    x = np.array([m['pts1'] - m['pts2'] for m in dataset], dtype=float)
    y = np.array([m['actual'] for m in dataset], dtype=float)

    def log_loss(params):
        gamma = params[0]
        p = 1.0 / (1.0 + 10.0 ** (-gamma * x))
        p = np.clip(p, 1e-15, 1.0 - 1e-15)
        loss = -np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))
        return loss

    res = minimize(log_loss, [1e-5], method='Nelder-Mead')
    opt_gamma = res.x[0]
    min_loss = res.fun
    
    # Calculate accuracy
    p = 1.0 / (1.0 + 10.0 ** (-opt_gamma * x))
    preds = (p >= 0.5).astype(int)
    acc = np.mean(preds == y)

    return opt_gamma, min_loss, acc

def calibrate_ratio_model(dataset):
    # P(win) = 1 / (1 + (pts2 / pts1)^beta)
    # This is equivalent to P(win) = 1 / (1 + e^(-beta * ln(pts1/pts2)))
    ratios = np.array([m['pts2'] / m['pts1'] for m in dataset], dtype=float)
    y = np.array([m['actual'] for m in dataset], dtype=float)

    def log_loss(params):
        beta = params[0]
        p = 1.0 / (1.0 + ratios ** beta)
        p = np.clip(p, 1e-15, 1.0 - 1e-15)
        loss = -np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))
        return loss

    res = minimize(log_loss, [1.0], method='Nelder-Mead')
    opt_beta = res.x[0]
    min_loss = res.fun

    p = 1.0 / (1.0 + ratios ** opt_beta)
    preds = (p >= 0.5).astype(int)
    acc = np.mean(preds == y)

    return opt_beta, min_loss, acc

def evaluate_elo_baseline(dataset):
    elo_diff = np.array([m['elo1'] - m['elo2'] for m in dataset], dtype=float)
    y = np.array([m['actual'] for m in dataset], dtype=float)
    
    p = 1.0 / (1.0 + 10.0 ** (-elo_diff / 400.0))
    p = np.clip(p, 1e-15, 1.0 - 1e-15)
    loss = -np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))
    preds = (p >= 0.5).astype(int)
    acc = np.mean(preds == y)
    
    return loss, acc

def main():
    dataset = load_data()
    if not dataset:
        print("No matches to process.")
        return

    print("\n--- Model Calibration Results ---")
    
    # Elo baseline
    elo_loss, elo_acc = evaluate_elo_baseline(dataset)
    print(f"Elo Baseline (for comparison):")
    print(f"  Log Loss: {elo_loss:.4f}")
    print(f"  Accuracy: {elo_acc*100:.2f}%")

    # Difference Model
    gamma, diff_loss, diff_acc = calibrate_difference_model(dataset)
    print(f"\nBWF Difference Model [P = 1 / (1 + 10^(-gamma * (P1 - P2)))]:")
    print(f"  Optimal gamma: {gamma:.7f}")
    print(f"  Scaling Factor (1/gamma equivalent to 400 in Elo): {1.0/gamma:.2f}")
    print(f"  Log Loss: {diff_loss:.4f}")
    print(f"  Accuracy: {diff_acc*100:.2f}%")

    # Ratio Model
    beta, ratio_loss, ratio_acc = calibrate_ratio_model(dataset)
    print(f"\nBWF Ratio Model [P = 1 / (1 + (P2 / P1)^beta)]:")
    print(f"  Optimal beta (power exponent): {beta:.4f}")
    print(f"  Log Loss: {ratio_loss:.4f}")
    print(f"  Accuracy: {ratio_acc*100:.2f}%")
    
    # Derived formulas summary
    print("\n--- Derived Mathematical Formulations ---")
    print("1. BWF Difference Form:")
    print(f"   Win Prob = 1 / (1 + 10^(-({gamma:.6f} * (Pts1 - Pts2))))")
    print(f"   Or in standard Elo terms (equivalent divisor):")
    print(f"   Win Prob = 1 / (1 + 10^(-(Pts1 - Pts2) / {1.0/gamma:.1f}))")
    
    print("\n2. BWF Ratio Form:")
    print(f"   Win Prob = 1 / (1 + (Pts2 / Pts1)^{beta:.3f})")

if __name__ == "__main__":
    main()
