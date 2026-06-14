from fastapi import APIRouter, Depends, Query, HTTPException, Request
from typing import Optional
import sqlite3
import pandas as pd
import numpy as np
import xgboost as xgb
import shap
from datetime import datetime, date, timedelta

from database import get_core_db, get_ratings_db
from services.player_service import get_latest_rating
from config import RATINGS_DB_PATH

router = APIRouter()

# Load XGBoost model and explainer globally from SQLite
xgb_model = None
shap_explainer = None

XGB_TIERS = ['T0', 'T1', 'T2', 'T3', 'T4', 'T5', 'T6']
XGB_ROUNDS = ['', '3/4', '5/6', 'Cons. QF', 'Cons. R16', 'Cons. SF', 'Cons. final', 'Final', 'QF', 'Qual. F', 'Qual. QF', 'Qual. R128', 'Qual. R16', 'Qual. R32', 'Qual. R64', 'Qual. SF', 'R1', 'R128', 'R16', 'R2', 'R256', 'R3', 'R32', 'R4', 'R5', 'R6', 'R64', 'R7', 'SF']
XGB_EVENTS = ['MD', 'MS', 'WD', 'WS', 'XD']

def scale_shap_contributions(shap_raw: dict, predicted_prob: float):
    """
    Scales raw log-odds SHAP values to represent exact probability shifts
    summing up to predicted_prob - base_prob using a mathematically consistent
    local baseline probability.
    """
    total_logit_shift = sum(shap_raw.values())
    
    # Clip predicted_prob to prevent division by zero in logit
    prob_clipped = np.clip(predicted_prob, 1e-15, 1.0 - 1e-15)
    logit_prob = np.log(prob_clipped / (1.0 - prob_clipped))
    
    # Define a consistent base probability for this specific prediction
    true_base_logit = logit_prob - total_logit_shift
    true_base_prob = 1.0 / (1.0 + np.exp(-true_base_logit))
    total_prob_shift = predicted_prob - true_base_prob
    
    if abs(total_logit_shift) > 1e-5:
        k = total_prob_shift / total_logit_shift
    else:
        k = prob_clipped * (1.0 - prob_clipped)
        
    scaled = {key: round(float(val * k), 4) for key, val in shap_raw.items()}
    return scaled

try:
    import pickle
    # Connect directly to ratings DB to fetch the model
    conn = sqlite3.connect(RATINGS_DB_PATH)
    cursor = conn.cursor()
    # Check if table exists first
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ml_models'")
    if cursor.fetchone():
        cursor.execute("SELECT model_bytes FROM ml_models WHERE model_name = ?", ("xgboost_expectation",))
        row = cursor.fetchone()
        if row:
            xgb_model = pickle.loads(row[0])
            shap_explainer = shap.TreeExplainer(xgb_model)
            print("Backend: Successfully loaded XGBoost expectation model from database.")
        else:
            print("Backend Warning: Model 'xgboost_expectation' not found in database.")
    else:
        print("Backend Warning: 'ml_models' table does not exist yet.")
    conn.close()
except Exception as e:
    print(f"Backend Warning: Could not load XGBoost model from database: {e}")

def get_player_rest(cursor_core, player_id, ref_date_str=None):
    """Computes rest days relative to ref_date_str clamped to 90"""
    if ref_date_str is None:
        ref_date_str = datetime.now().strftime("%Y-%m-%d")
        ref_date = datetime.now().date()
    else:
        ref_date = datetime.strptime(ref_date_str, "%Y-%m-%d").date()
    
    # Rest days
    cursor_core.execute("""
        SELECT MAX(match_date) 
        FROM matches m
        JOIN match_participants mp ON m.match_id = mp.match_id
        WHERE mp.player_id = ? AND m.is_valid_for_rating = 1 AND m.match_date <= ?
    """, (player_id, ref_date_str))
    
    last_date_row = cursor_core.fetchone()
    last_date_str = last_date_row[0] if last_date_row else None
    if last_date_str:
        rest_days = (ref_date - datetime.strptime(last_date_str, "%Y-%m-%d").date()).days
        rest_days = min(90, rest_days)
    else:
        rest_days = 90
        
    return rest_days

def get_h2h_rate(cursor_core, side1_ids, side2_ids, ref_date_str=None):
    """Fetches head-to-head winrate for the matchup, capped at the last 2 years relative to ref_date_str"""
    if ref_date_str is None:
        ref_date = datetime.now()
        ref_date_str = ref_date.strftime("%Y-%m-%d")
    else:
        ref_date = datetime.strptime(ref_date_str, "%Y-%m-%d")
        
    team_a = "+".join(sorted(side1_ids))
    team_b = "+".join(sorted(side2_ids))
    m_key = tuple(sorted([team_a, team_b]))
    
    # Calculate cutoff date for 2 years ago relative to ref_date
    two_years_ago_str = (ref_date - timedelta(days=730)).strftime("%Y-%m-%d")
    
    # Find candidate matches in the last 2 years where at least one of these players played
    all_players = list(set(side1_ids + side2_ids))
    placeholders = ",".join(["?"] * len(all_players))
    
    cursor_core.execute(f"""
        SELECT DISTINCT mp.match_id
        FROM match_participants mp
        JOIN matches m ON mp.match_id = m.match_id
        WHERE mp.player_id IN ({placeholders}) AND m.is_valid_for_rating = 1 AND m.match_date >= ? AND m.match_date <= ?
    """, all_players + [two_years_ago_str, ref_date_str])
    
    candidate_match_ids = [r[0] for r in cursor_core.fetchall()]
    if not candidate_match_ids:
        return 0.5
        
    # Query details of only these candidate matches
    placeholders_matches = ",".join(["?"] * len(candidate_match_ids))
    cursor_core.execute(f"""
        SELECT m.match_id, m.winner_side, mp.side, mp.player_id
        FROM matches m
        JOIN match_participants mp ON m.match_id = mp.match_id
        WHERE m.match_id IN ({placeholders_matches})
    """, candidate_match_ids)
    
    match_details = {}
    for mid, winner_side, side, pid in cursor_core.fetchall():
        if mid not in match_details:
            match_details[mid] = {"winner_side": winner_side, "side1": [], "side2": []}
        if side == 1:
            match_details[mid]["side1"].append(pid)
        else:
            match_details[mid]["side2"].append(pid)
            
    wins = 0
    losses = 0
    for mid, details in match_details.items():
        t1 = "+".join(sorted(details["side1"]))
        t2 = "+".join(sorted(details["side2"]))
        if (t1 == team_a and t2 == team_b) or (t1 == team_b and t2 == team_a):
            winner_a = (details["winner_side"] == 1 if t1 == team_a else details["winner_side"] == 2)
            if winner_a:
                wins += 1
            else:
                losses += 1
                
    total = wins + losses
    h2h_rate = wins / total if total > 0 else 0.5
    # Standardize relative to team A being m_key[0]
    if team_a == m_key[1]:
        h2h_rate = 1.0 - h2h_rate
    return h2h_rate

@router.get("/api/predict")
def predict_match(request: Request, 
                  p1: str = Query(..., max_length=10), 
                  p2: str = Query(..., max_length=10), 
                  event: str = "MS", 
                  model: str = "whr",
                  db: sqlite3.Connection = Depends(get_ratings_db),
                  db_core: sqlite3.Connection = Depends(get_core_db)):
        
    cursor = db.cursor()
    
    if model == "elo":
        res = predict_match_v2(request, side1=p1, side2=p2, event=event, model=model, db_ratings=db, db_core=db_core)
        return {
            "p1": p1,
            "p2": p2,
            "prob_p1": res["prob_side1"],
            "prob_p2": res["prob_side2"],
            "r1": res["r1"],
            "r2": res["r2"],
            "shap_contributions": res.get("shap_contributions")
        }
        
    r1 = get_latest_rating(cursor, p1, event, model)
    r2 = get_latest_rating(cursor, p2, event, model)
    
    if r1 is None or r2 is None:
        raise HTTPException(status_code=404, detail="One or both players not found or have no rating")
        
    if model == "bwf":
        prob = 1.0 / (1.0 + (r2 / r1) ** 0.1987) if r1 > 0 else 0.5
    else:
        prob = 1.0 / (1.0 + 10.0 ** ((r2 - r1) / 400.0))
    
    return {
        "p1": p1,
        "p2": p2,
        "prob_p1": round(prob, 3),
        "prob_p2": round(1 - prob, 3),
        "r1": round(r1, 1),
        "r2": round(r2, 1)
    }

@router.get("/api/predict_match_v2")
def predict_match_v2(request: Request, 
                      side1: str = Query(..., description="Comma-separated player IDs for side 1"), 
                      side2: str = Query(..., description="Comma-separated player IDs for side 2"), 
                      event: str = "MS", 
                      model: str = "whr",
                      db_ratings: sqlite3.Connection = Depends(get_ratings_db),
                      db_core: sqlite3.Connection = Depends(get_core_db)):
    
    p1_ids = [pid.strip() for pid in side1.split(',')]
    p2_ids = [pid.strip() for pid in side2.split(',')]
    
    cursor_ratings = db_ratings.cursor()
    cursor_core = db_core.cursor()
    
    r1_list = []
    for pid in p1_ids:
        r = get_latest_rating(cursor_ratings, pid, event, model)
        if r is not None:
            r1_list.append(r)
            
    r2_list = []
    for pid in p2_ids:
        r = get_latest_rating(cursor_ratings, pid, event, model)
        if r is not None:
            r2_list.append(r)
            
    if not r1_list or not r2_list:
        raise HTTPException(status_code=404, detail="One or both sides have no valid rated players")
        
    avg_r1 = sum(r1_list) / len(r1_list)
    avg_r2 = sum(r2_list) / len(r2_list)
    
    if model == "bwf":
        prob = 1.0 / (1.0 + (avg_r2 / avg_r1) ** 0.1987) if avg_r1 > 0 else 0.5
    else:
        # Default classical ELO calculation
        prob = 1.0 / (1.0 + 10.0 ** ((avg_r2 - avg_r1) / 400.0))
    shap_contributions = None
    
    # Use XGBoost for Elo model if available
    if model == "elo" and xgb_model is not None:
        try:
            # 1. Fetch synergies
            syn1 = 0.0
            syn2 = 0.0
            if len(p1_ids) == 2:
                cursor_ratings.execute("SELECT synergy FROM pair_synergy_current WHERE (player1_id=? AND player2_id=?) OR (player1_id=? AND player2_id=?)", (p1_ids[0], p1_ids[1], p1_ids[1], p1_ids[0]))
                row = cursor_ratings.fetchone()
                if row: syn1 = row[0]
            if len(p2_ids) == 2:
                cursor_ratings.execute("SELECT synergy FROM pair_synergy_current WHERE (player1_id=? AND player2_id=?) OR (player1_id=? AND player2_id=?)", (p2_ids[0], p2_ids[1], p2_ids[1], p2_ids[0]))
                row = cursor_ratings.fetchone()
                if row: syn2 = row[0]
                
            # 2. Fetch rest days (clamped to 40)
            rest_1_list = [get_player_rest(cursor_core, pid) for pid in p1_ids]
            rest_2_list = [get_player_rest(cursor_core, pid) for pid in p2_ids]
            
            avg_rest_a = np.mean(rest_1_list)
            avg_rest_b = np.mean(rest_2_list)
            
            h2h_rate = get_h2h_rate(cursor_core, p1_ids, p2_ids)
            
            # 3. Construct Match Feature DataFrame (9 features)
            feature_data = {
                'elo_diff': [avg_r1 - avg_r2],
                'synergy_a': [syn1],
                'synergy_b': [syn2],
                'duration': [35.0], # Default imputed median
                'tier': pd.Categorical(['T3'], categories=XGB_TIERS),
                'round': pd.Categorical(['R32'], categories=XGB_ROUNDS),
                'event': pd.Categorical([event], categories=XGB_EVENTS),
                'rest_diff': [avg_rest_a - avg_rest_b],
                'h2h_rate': [h2h_rate]
            }
            X = pd.DataFrame(feature_data)
            
            # Predict win probability using XGBoost
            prob = float(xgb_model.predict_proba(X)[0, 1])
            
            # 4. Extract SHAP contributions if explainer is active
            if shap_explainer is not None:
                shap_res = shap_explainer(X)[0]
                raw_contributions = {
                    "Baseline Skill Gap": float(shap_res.values[0]), # elo_diff
                    "Doubles Chemistry": float(shap_res.values[1] + shap_res.values[2]),  # synergy_a + synergy_b
                    "Fatigue & Rest Gap": float(shap_res.values[7]), # rest_diff
                    "H2H Record": float(shap_res.values[8]), # h2h_rate
                    "Match Context": float(shap_res.values[3] + shap_res.values[4] + shap_res.values[5] + shap_res.values[6]) # duration + tier + round + event
                }
                shap_contributions = scale_shap_contributions(raw_contributions, prob)
        except Exception as ex:
            print(f"Prediction fallback due to error: {ex}")
            # Fallback to classical probability already calculated
            
    return {
        "side1": p1_ids,
        "side2": p2_ids,
        "prob_side1": round(prob, 3),
        "prob_side2": round(1 - prob, 3),
        "r1": round(avg_r1, 1),
        "r2": round(avg_r2, 1),
        "shap_contributions": shap_contributions
    }

@router.get("/api/headtohead")
def get_head_to_head(p1: str = Query(..., max_length=10), 
                     p2: str = Query(..., max_length=10),
                     db: sqlite3.Connection = Depends(get_core_db)):
        
    cursor_core = db.cursor()
    
    cursor_core.execute("""
        SELECT m.match_id, m.match_date, m.score, m.winner_side, m.event_canon,
               t.name as tournament_name
        FROM matches m
        JOIN match_participants mp1 ON m.match_id = mp1.match_id AND mp1.player_id = ?
        JOIN match_participants mp2 ON m.match_id = mp2.match_id AND mp2.player_id = ?
        JOIN tournaments t ON m.tournament_id = t.tournament_id
        WHERE mp1.side != mp2.side AND m.is_valid_for_rating = 1
        ORDER BY m.match_date DESC
    """, (p1, p2))
    
    rows = cursor_core.fetchall()
    
    results = []
    for r in rows:
        results.append({
            "match_id": r['match_id'],
            "date": r['match_date'],
            "score": r['score'],
            "winner_side": r['winner_side'],
            "event": r['event_canon'],
            "tournament": r['tournament_name']
        })
        
    return results

@router.get("/api/headtohead_v2")
def get_headtohead_v2(request: Request, 
                      side1: str = Query(..., description="Comma-separated player IDs for side 1"), 
                      side2: str = Query(..., description="Comma-separated player IDs for side 2"), 
                      event: Optional[str] = None,
                      db_core: sqlite3.Connection = Depends(get_core_db)):
    
    p1_ids = sorted([pid.strip() for pid in side1.split(',')])
    p2_ids = sorted([pid.strip() for pid in side2.split(',')])
    
    cursor = db_core.cursor()
    
    cursor.execute("""
        SELECT m.match_id
        FROM match_participants mp
        JOIN matches m ON mp.match_id = m.match_id
        WHERE mp.player_id = ? AND m.is_valid_for_rating = 1
    """, (p1_ids[0],))
    
    possible_match_ids = [r['match_id'] for r in cursor.fetchall()]
    
    if not possible_match_ids:
        return {"summary": {"side1_wins": 0, "side2_wins": 0, "total": 0}, "matches": []}
        
    placeholders = ",".join(["?"] * len(possible_match_ids))
    
    cursor.execute(f"""
        SELECT mp.match_id, mp.side, mp.player_id, m.winner_side, m.match_date, m.score, m.event_canon, m.round, t.name as tournament_name
        FROM match_participants mp
        JOIN matches m ON mp.match_id = m.match_id
        LEFT JOIN tournaments t ON m.tournament_id = t.tournament_id
        WHERE mp.match_id IN ({placeholders})
    """, possible_match_ids)
    
    rows = cursor.fetchall()
    
    match_map = {}
    for r in rows:
        mid = r['match_id']
        if mid not in match_map:
            match_map[mid] = {
                "match_id": mid,
                "side1_players": [],
                "side2_players": [],
                "winner_side": r['winner_side'],
                "date": r['match_date'],
                "score": r['score'],
                "event": r['event_canon'],
                "round": r['round'],
                "tournament": r['tournament_name']
            }
        if r['side'] == 1:
            match_map[mid]["side1_players"].append(r['player_id'])
        else:
            match_map[mid]["side2_players"].append(r['player_id'])
            
    final_matches = []
    side1_wins = 0
    side2_wins = 0
    
    for mid, m in match_map.items():
        s1 = sorted(m["side1_players"])
        s2 = sorted(m["side2_players"])
        
        match_found = False
        winner_side = m["winner_side"]
        
        if s1 == p1_ids and s2 == p2_ids:
            match_found = True
            if winner_side == 1: side1_wins += 1
            elif winner_side == 2: side2_wins += 1
        elif s1 == p2_ids and s2 == p1_ids:
            match_found = True
            if winner_side == 1: side2_wins += 1
            elif winner_side == 2: side1_wins += 1
            
        if match_found:
            final_matches.append(m)
            
    final_matches.sort(key=lambda x: x['date'], reverse=True)
    
    return {
        "summary": {
            "side1_wins": side1_wins,
            "side2_wins": side2_wins,
            "total": len(final_matches)
        },
        "matches": final_matches
    }

@router.get("/api/predict/matchup")
def get_matchup_prediction(
    side1_p1: str,
    side2_p1: str,
    date1: str,
    date2: str,
    side1_p2: Optional[str] = None,
    side2_p2: Optional[str] = None,
    event: str = "MS",
    model: str = "whr",
    db_ratings: sqlite3.Connection = Depends(get_ratings_db),
    db_core: sqlite3.Connection = Depends(get_core_db)
):
    cursor_r = db_ratings.cursor()
    
    def get_historical_rating(p_id, target_date, event_type):
        if not p_id: return 0.0
        if model == "whr":
            cursor_r.execute("SELECT run_id FROM whr_run_metadata WHERE run_id LIKE ? ORDER BY created_at DESC LIMIT 1", (f"%_{event_type}",))
            run_row = cursor_r.fetchone()
            if not run_row:
                cursor_r.execute("SELECT run_id FROM whr_run_metadata ORDER BY created_at DESC LIMIT 1")
                run_row = cursor_r.fetchone()
            run_id = run_row['run_id'] if run_row else None
            if not run_id: return 1000.0
            
            cursor_r.execute("""
                SELECT rating FROM whr_rating_history 
                WHERE run_id = ? AND player_id = ? AND event = ? AND rating_date <= ?
                ORDER BY rating_date DESC LIMIT 1
            """, (run_id, p_id, event_type, target_date))
            row = cursor_r.fetchone()
            if row: return row['rating']
            
            cursor_r.execute("""
                SELECT rating FROM whr_rating_history 
                WHERE run_id = ? AND player_id = ? AND event = ? AND rating_date > ?
                ORDER BY rating_date ASC LIMIT 1
            """, (run_id, p_id, event_type, target_date))
            row = cursor_r.fetchone()
            return row['rating'] if row else 1000.0
            
        elif model == "elo":
            cursor_r.execute("SELECT run_id FROM run_metadata WHERE run_id LIKE '%final%' ORDER BY created_at DESC LIMIT 1")
            run_row = cursor_r.fetchone()
            run_id = run_row['run_id'] if run_row else None
            if not run_id: return 1000.0
            
            cursor_r.execute("""
                SELECT rating FROM rating_history 
                WHERE run_id = ? AND player_id = ? AND event = ? AND rating_date <= ?
                ORDER BY rating_date DESC LIMIT 1
            """, (run_id, p_id, event_type, target_date))
            row = cursor_r.fetchone()
            if row: return row['rating']
            
            cursor_r.execute("""
                SELECT rating FROM rating_history 
                WHERE run_id = ? AND player_id = ? AND event = ? AND rating_date > ?
                ORDER BY rating_date ASC LIMIT 1
            """, (run_id, p_id, event_type, target_date))
            row = cursor_r.fetchone()
            return row['rating'] if row else 1000.0
            
        elif model == "bwf":
            cursor_r.execute("""
                SELECT points FROM bwf_historical_rankings 
                WHERE player_id = ? AND event = ? AND rank_date <= ?
                ORDER BY rank_date DESC LIMIT 1
            """, (p_id, event_type, target_date))
            row = cursor_r.fetchone()
            if row: return row['points']
            
            cursor_r.execute("""
                SELECT points FROM bwf_historical_rankings 
                WHERE player_id = ? AND event = ? AND rank_date > ?
                ORDER BY rank_date ASC LIMIT 1
            """, (p_id, event_type, target_date))
            row = cursor_r.fetchone()
            return row['points'] if row else 0.0
        return 1000.0

    r1a = get_historical_rating(side1_p1, date1, event)
    r1b = get_historical_rating(side1_p2, date1, event) if side1_p2 else 0.0
    
    r2a = get_historical_rating(side2_p1, date2, event)
    r2b = get_historical_rating(side2_p2, date2, event) if side2_p2 else 0.0
    
    strength1 = r1a + r1b
    strength2 = r2a + r2b
    
    prob1 = None
    
    # Use XGBoost for Elo model if available
    if model == "elo" and xgb_model is not None:
        try:
            p1_ids = [side1_p1]
            if side1_p2: p1_ids.append(side1_p2)
            p2_ids = [side2_p1]
            if side2_p2: p2_ids.append(side2_p2)
            
            # 1. Fetch synergies
            syn1 = 0.0
            syn2 = 0.0
            cursor_r = db_ratings.cursor()
            if len(p1_ids) == 2:
                cursor_r.execute("SELECT synergy FROM pair_synergy_current WHERE (player1_id=? AND player2_id=?) OR (player1_id=? AND player2_id=?)", (p1_ids[0], p1_ids[1], p1_ids[1], p1_ids[0]))
                row = cursor_r.fetchone()
                if row: syn1 = row[0]
            if len(p2_ids) == 2:
                cursor_r.execute("SELECT synergy FROM pair_synergy_current WHERE (player1_id=? AND player2_id=?) OR (player1_id=? AND player2_id=?)", (p2_ids[0], p2_ids[1], p2_ids[1], p2_ids[0]))
                row = cursor_r.fetchone()
                if row: syn2 = row[0]
                
            # 2. Fetch rest days relative to target dates
            rest_1_list = [get_player_rest(db_core.cursor(), pid, date1) for pid in p1_ids]
            rest_2_list = [get_player_rest(db_core.cursor(), pid, date2) for pid in p2_ids]
            
            avg_rest_a = np.mean(rest_1_list)
            avg_rest_b = np.mean(rest_2_list)
            
            # Use date1 as the matchup target date reference
            h2h_rate = get_h2h_rate(db_core.cursor(), p1_ids, p2_ids, date1)
            
            # 3. Construct Match Feature DataFrame (9 features)
            feature_data = {
                'elo_diff': [strength1 - strength2], # Side 1 - Side 2
                'synergy_a': [syn1],
                'synergy_b': [syn2],
                'duration': [35.0],
                'tier': pd.Categorical(['T3'], categories=XGB_TIERS),
                'round': pd.Categorical(['R32'], categories=XGB_ROUNDS),
                'event': pd.Categorical([event], categories=XGB_EVENTS),
                'rest_diff': [avg_rest_a - avg_rest_b],
                'h2h_rate': [h2h_rate]
            }
            X = pd.DataFrame(feature_data)
            
            # Predict win probability using XGBoost (for Side 1)
            prob1 = float(xgb_model.predict_proba(X)[0, 1])
        except Exception as ex:
            print(f"Matchup prediction fallback due to error: {ex}")
            prob1 = None
            
    if prob1 is None:
        if model == "bwf":
            if strength1 > 0:
                prob1 = 1.0 / (1.0 + (strength2 / strength1) ** 0.1987)
            else:
                prob1 = 0.5
        else:
            diff = (strength2 - strength1) / 400.0
            prob1 = 1.0 / (1.0 + 10**diff)
    
    cursor_c = db_core.cursor()
    def get_player_info(p_id):
        if not p_id: return None
        cursor_c.execute("SELECT name_display, country_code FROM players WHERE player_id = ?", (p_id,))
        row = cursor_c.fetchone()
        return {"name": row['name_display'], "country": row['country_code']} if row else {"name": p_id, "country": "Unknown"}

    p1a_info = get_player_info(side1_p1)
    p1b_info = get_player_info(side1_p2)
    p2a_info = get_player_info(side2_p1)
    p2b_info = get_player_info(side2_p2)

    def get_synergy(p1, p2, event_type):
        if not p1 or not p2: return 0.0
        cursor_r.execute("""
            SELECT synergy FROM pair_synergy_current 
            WHERE player1_id = ? AND player2_id = ? AND event = ?
        """, (p1, p2, event_type))
        row = cursor_r.fetchone()
        if row: return row['synergy']
        
        cursor_r.execute("""
            SELECT synergy FROM pair_synergy_current 
            WHERE player1_id = ? AND player2_id = ? AND event = ?
        """, (p2, p1, event_type))
        row = cursor_r.fetchone()
        return row['synergy'] if row else 0.0

    syn1 = get_synergy(side1_p1, side1_p2, event) if side1_p2 else 0.0
    syn2 = get_synergy(side2_p1, side2_p2, event) if side2_p2 else 0.0

    return {
        "side1": {
            "p1": {**p1a_info, "rating": round(r1a, 1)},
            "p2": {**p1b_info, "rating": round(r1b, 1)} if side1_p2 else None,
            "total_strength": round(strength1, 1),
            "win_prob": round(prob1 * 100, 1),
            "synergy": round(syn1, 1)
        },
        "side2": {
            "p1": {**p2a_info, "rating": round(r2a, 1)},
            "p2": {**p2b_info, "rating": round(r2b, 1)} if side2_p2 else None,
            "total_strength": round(strength2, 1),
            "win_prob": round((1 - prob1) * 100, 1),
            "synergy": round(syn2, 1)
        },
        "event": event,
        "model": model.upper(),
        "meta": {
            "run_id": model.upper(),
            "date1": date1,
            "date2": date2
        }
    }

@router.get("/api/predictions/match/{match_id}/shap")
def get_match_shap(match_id: str, ratings_db: sqlite3.Connection = Depends(get_ratings_db)):
    if shap_explainer is None:
        raise HTTPException(status_code=503, detail="SHAP explainer is not active or loaded.")
        
    cursor = ratings_db.cursor()
    cursor.execute("""
        SELECT elo_diff, synergy_a, synergy_b, duration, tier, round, event, rest_diff, h2h_rate
        FROM ml_match_features
        WHERE match_id = ?
    """, (match_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Features not found for this match.")
        
    # sqlite3.Row supports sequence unpacking
    elo_diff, synergy_a, synergy_b, duration, tier, match_round, event, rest_diff, h2h_rate = row
    
    try:
        # Construct Match Feature DataFrame (9 features matching training configuration)
        feature_data = {
            'elo_diff': [elo_diff],
            'synergy_a': [synergy_a],
            'synergy_b': [synergy_b],
            'duration': [duration if duration is not None else 35.0],
            'tier': pd.Categorical([tier], categories=XGB_TIERS),
            'round': pd.Categorical([match_round], categories=XGB_ROUNDS),
            'event': pd.Categorical([event], categories=XGB_EVENTS),
            'rest_diff': [rest_diff],
            'h2h_rate': [h2h_rate]
        }
        X = pd.DataFrame(feature_data)
        
        prob = float(xgb_model.predict_proba(X)[0, 1])
        shap_res = shap_explainer(X)[0]
        
        raw_contributions = {
            "Baseline Skill Gap": float(shap_res.values[0]), # elo_diff
            "Doubles Chemistry": float(shap_res.values[1] + shap_res.values[2]),  # synergy_a + synergy_b
            "Fatigue & Rest Gap": float(shap_res.values[7]), # rest_diff
            "H2H Record": float(shap_res.values[8]), # h2h_rate
            "Match Context": float(shap_res.values[3] + shap_res.values[4] + shap_res.values[5] + shap_res.values[6]) # duration + tier + round + event
        }
        
        shap_contributions = scale_shap_contributions(raw_contributions, prob)
        
        return {
            "match_id": match_id,
            "shap_contributions": shap_contributions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate SHAP values: {e}")

