import sqlite3
# pyrefly: ignore [missing-import]
import numpy as np
import sys

TEST_DB_PATH = "elo_ratings.sqlite"
CORE_DB_PATH = "bwf_data_2008-now__v1.sqlite"

def calculate_metrics(predictions, actuals):
    """Calculates log_loss, brier score, and accuracy."""
    if len(predictions) == 0:
        return None, None, None
    log_loss = -np.mean(actuals * np.log(predictions + 1e-12) + (1 - actuals) * np.log(1 - predictions + 1e-12))
    brier = np.mean((predictions - actuals) ** 2)
    accuracy = np.mean((predictions > 0.5) == actuals)
    return log_loss, brier, accuracy

def analyze_calibration(cursor, run_id):
    print("\n--- Calibration (Reliability) ---")
    cursor.execute("""
        SELECT predicted_prob, actual
        FROM prediction_log
        WHERE run_id = ?
    """, (run_id,))
    rows = cursor.fetchall()
    
    if not rows:
        return
        
    preds = np.array([r[0] for r in rows])
    actuals = np.array([r[1] for r in rows])
    
    bins = np.linspace(0, 1, 21) # 5% bins
    for i in range(len(bins)-1):
        lower = bins[i]
        upper = bins[i+1]
        mask = (preds >= lower) & (preds < upper)
        if i == len(bins) - 2: # inclusive for last bin
            mask = (preds >= lower) & (preds <= upper)
            
        if np.sum(mask) > 0:
            avg_pred = np.mean(preds[mask])
            win_rate = np.mean(actuals[mask])
            count = np.sum(mask)
            # We want win_rate to be close to avg_pred
            print(f"Prob [{lower:.2f} - {upper:.2f}]: Avg Pred = {avg_pred:.3f}, Actual Win = {win_rate:.3f} (N={count})")

def analyze_temporal(cursor, run_id):
    print("\n--- Temporal Degradation ---")
    cursor.execute("""
        SELECT strftime('%Y', m.match_date) as year, p.predicted_prob, p.actual
        FROM prediction_log p
        JOIN core.matches m ON p.match_id = m.match_id
        WHERE p.run_id = ?
    """, (run_id,))
    rows = cursor.fetchall()
    
    data_by_year = {}
    for year, pred, actual in rows:
        if year not in data_by_year:
            data_by_year[year] = {'preds': [], 'actuals': []}
        data_by_year[year]['preds'].append(pred)
        data_by_year[year]['actuals'].append(actual)
        
    for year in sorted(data_by_year.keys()):
        preds = np.array(data_by_year[year]['preds'])
        actuals = np.array(data_by_year[year]['actuals'])
        ll, brier, acc = calculate_metrics(preds, actuals)
        print(f"Year {year}: Log Loss = {ll:.4f}, Brier = {brier:.4f}, Acc = {acc:.4f} (N={len(preds)})")

def analyze_uncertainty(cursor, run_id):
    print("\n--- High Uncertainty (Inactivity/Comeback) Test ---")
    # We test the top 10% highest uncertainty matches and bottom 10%
    cursor.execute("""
        SELECT uncertainty_mean, predicted_prob, actual
        FROM prediction_log
        WHERE run_id = ?
    """, (run_id,))
    rows = cursor.fetchall()
    
    if not rows:
        return
        
    uncertainties = np.array([r[0] for r in rows])
    preds = np.array([r[1] for r in rows])
    actuals = np.array([r[2] for r in rows])
    
    p90 = np.percentile(uncertainties, 90)
    p10 = np.percentile(uncertainties, 10)
    
    # High Uncertainty
    high_mask = uncertainties >= p90
    ll_h, br_h, acc_h = calculate_metrics(preds[high_mask], actuals[high_mask])
    
    # Low Uncertainty
    low_mask = uncertainties <= p10
    ll_l, br_l, acc_l = calculate_metrics(preds[low_mask], actuals[low_mask])
    
    # Mid Uncertainty
    mid_mask = (uncertainties > p10) & (uncertainties < p90)
    ll_m, br_m, acc_m = calculate_metrics(preds[mid_mask], actuals[mid_mask])
    
    print(f"High Uncertainty (>= {p90:.2f}): Log Loss = {ll_h:.4f}, Acc = {acc_h:.4f} (N={np.sum(high_mask)})")
    print(f"Mid  Uncertainty (<  {p90:.2f}): Log Loss = {ll_m:.4f}, Acc = {acc_m:.4f} (N={np.sum(mid_mask)})")
    print(f"Low  Uncertainty (<= {p10:.2f}): Log Loss = {ll_l:.4f}, Acc = {acc_l:.4f} (N={np.sum(low_mask)})")


def analyze_low_uncertainty_anomalies(cursor, run_id):
    print("\n--- Low Uncertainty Anomalies (The 'Veteran' Check) ---")
    # Get 10th percentile of uncertainty
    cursor.execute("""
        SELECT uncertainty_mean
        FROM prediction_log
        WHERE run_id = ?
    """, (run_id,))
    rows = cursor.fetchall()
    if not rows: return
    
    uncertainties = np.array([r[0] for r in rows])
    p10 = np.percentile(uncertainties, 10)
    
    # Get worst predictions where uncertainty is low
    cursor.execute(f"""
        SELECT m.match_date, m.event_canon, p.predicted_prob, p.actual, p.uncertainty_mean, m.match_id, m.score, t.name,
            (SELECT GROUP_CONCAT(pl.name_display, ' / ') FROM core.match_participants mp JOIN core.players pl ON mp.player_id = pl.player_id WHERE mp.match_id = m.match_id AND mp.side = 1) as side1,
            (SELECT GROUP_CONCAT(pl.name_display, ' / ') FROM core.match_participants mp JOIN core.players pl ON mp.player_id = pl.player_id WHERE mp.match_id = m.match_id AND mp.side = 2) as side2
        FROM prediction_log p
        JOIN core.matches m ON p.match_id = m.match_id
        LEFT JOIN core.tournaments t ON m.tournament_id = t.tournament_id
        WHERE p.run_id = ? AND p.uncertainty_mean <= ?
    """, (run_id, p10))
    low_unc_rows = cursor.fetchall()
    
    preds = np.array([r[2] for r in low_unc_rows])
    actuals = np.array([r[3] for r in low_unc_rows])
    
    # Let's find the biggest misses (where pred > 0.5 but actual is 0, or pred < 0.5 but actual is 1)
    # log loss for each:
    log_losses = - (actuals * np.log(preds + 1e-12) + (1 - actuals) * np.log(1 - preds + 1e-12))
    
    # Combine with details and sort
    misses = []
    for i, r in enumerate(low_unc_rows):
        misses.append({'date': r[0], 'event': r[1], 'pred': r[2], 'actual': r[3], 'll': log_losses[i], 'match_id': r[5], 'score': r[6], 'tournament': r[7], 'side1': r[8], 'side2': r[9]})
        
    misses.sort(key=lambda x: x['ll'], reverse=True)
    
    print(f"Top 10 Biggest Upsets in Low Uncertainty Matches (<= {p10:.2f}):")
    for m in misses[:10]:
        print(f"  {m['date']} [{m['event']}] - {m['tournament']} ({m['match_id']})")
        print(f"    {m['side1']} vs {m['side2']}")
        print(f"    Score: {m['score']}")
        print(f"    Pred Win: {m['pred']:.4f}, Actual: {m['actual']} (Log Loss: {m['ll']:.4f})\n")

def analyze_2026_anomalies(cursor, run_id):
    print("\n--- 2026 Performance Drop Investigation ---")
    
    # 1. Per-event breakdown for 2026
    cursor.execute("""
        SELECT m.event_canon, p.predicted_prob, p.actual
        FROM prediction_log p
        JOIN core.matches m ON p.match_id = m.match_id
        WHERE p.run_id = ? AND strftime('%Y', m.match_date) = '2026'
    """, (run_id,))
    rows = cursor.fetchall()
    
    if not rows:
        print("No 2026 data found.")
        return
        
    event_data = {}
    for ev, pred, actual in rows:
        if ev not in event_data:
            event_data[ev] = {'preds': [], 'actuals': []}
        event_data[ev]['preds'].append(pred)
        event_data[ev]['actuals'].append(actual)
        
    print("2026 Metrics by Event:")
    for ev in sorted(event_data.keys()):
        preds = np.array(event_data[ev]['preds'])
        actuals = np.array(event_data[ev]['actuals'])
        ll, brier, acc = calculate_metrics(preds, actuals)
        print(f"  {ev}: Log Loss = {ll:.4f}, Acc = {acc:.4f} (N={len(preds)})")

    # 2. Top 15 biggest misses in 2026
    cursor.execute("""
        SELECT m.match_date, m.event_canon, p.predicted_prob, p.actual, p.uncertainty_mean, m.match_id, m.score, t.name,
            (SELECT GROUP_CONCAT(pl.name_display, ' / ') FROM core.match_participants mp JOIN core.players pl ON mp.player_id = pl.player_id WHERE mp.match_id = m.match_id AND mp.side = 1) as side1,
            (SELECT GROUP_CONCAT(pl.name_display, ' / ') FROM core.match_participants mp JOIN core.players pl ON mp.player_id = pl.player_id WHERE mp.match_id = m.match_id AND mp.side = 2) as side2
        FROM prediction_log p
        JOIN core.matches m ON p.match_id = m.match_id
        LEFT JOIN core.tournaments t ON m.tournament_id = t.tournament_id
        WHERE p.run_id = ? AND strftime('%Y', m.match_date) = '2026'
    """, (run_id,))
    rows2026 = cursor.fetchall()
    
    misses = []
    for r in rows2026:
        date, ev, pred, actual, unc, match_id, score, tournament, side1, side2 = r
        ll = - (actual * np.log(pred + 1e-12) + (1 - actual) * np.log(1 - pred + 1e-12))
        misses.append({'date': date, 'event': ev, 'pred': pred, 'actual': actual, 'll': ll, 'unc': unc, 'match_id': match_id, 'score': score, 'tournament': tournament, 'side1': side1, 'side2': side2})
        
    misses.sort(key=lambda x: x['ll'], reverse=True)
    
    print("\nTop 15 Biggest Upsets in 2026:")
    for m in misses[:15]:
        print(f"  {m['date']} [{m['event']}] - {m['tournament']} ({m['match_id']})")
        print(f"    {m['side1']} vs {m['side2']}")
        print(f"    Score: {m['score']}")
        print(f"    Pred Win: {m['pred']:.4f}, Actual: {m['actual']} (Uncertainty: {m['unc']:.3f})\n")

def main(run_id=None):
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(f"ATTACH DATABASE '{CORE_DB_PATH}' AS core")
    
    if run_id is None:
        cursor.execute("SELECT run_id FROM run_metadata ORDER BY created_at DESC LIMIT 1")
        last_run = cursor.fetchone()
        if last_run:
            run_id = last_run[0]
            print(f"Analyzing most recent run: {run_id}")
        else:
            print("No runs found.")
            return

    analyze_calibration(cursor, run_id)
    analyze_temporal(cursor, run_id)
    analyze_uncertainty(cursor, run_id)
    
    analyze_low_uncertainty_anomalies(cursor, run_id)
    analyze_2026_anomalies(cursor, run_id)
    
    conn.close()

if __name__ == "__main__":
    run_id_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(run_id_arg)
