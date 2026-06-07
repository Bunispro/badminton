import math
from db_ratings import init_rating_table
from datetime import datetime


COVID_START = datetime(2020, 3, 1)
COVID_END = datetime(2021, 6, 1)

def get_mov_multiplier(score_str, event_canon, mov_base_mult=1.0, mov_growth_rate=1.0):
    if event_canon not in ['MS', 'MD', 'XD'] or mov_base_mult == 1.0:
        return 1.0
    if not score_str or '-' not in score_str or 'Retired' in score_str or 'Walkover' in score_str:
        return 1.0
    
    sets = score_str.strip().split(' ')
    p1_total = 0
    p2_total = 0
    for s in sets:
        parts = s.split('-')
        if len(parts) == 2:
            try:
                p1_total += int(parts[0])
                p2_total += int(parts[1])
            except ValueError:
                pass
                
    if p1_total == 0 and p2_total == 0:
        return 1.0
        
    point_gap = abs(p1_total - p2_total)
    
    if point_gap <= 5:
        return mov_base_mult
    else:
        # Exponential curve starting from 6 point gap
        return min(1.35, mov_base_mult * (mov_growth_rate ** (point_gap - 5)))

def snapshot_ratings(test_cursor, run_id, ratings_by_event, date, updated_keys=None):
    history_data = []
    if updated_keys is not None:
        for event, pid in updated_keys:
            rating = ratings_by_event.get(event, {}).get(pid)
            if rating is not None:
                history_data.append((run_id, pid, event, date, rating))
    else:
        for event, ratings in ratings_by_event.items():
            for pid, rating in ratings.items():
                history_data.append((run_id, pid, event, date, rating))
    if history_data:
        test_cursor.executemany("""
            INSERT OR REPLACE INTO rating_history
            (run_id, player_id, event, rating_date, rating)
            VALUES (?, ?, ?, ?, ?)
        """, history_data)
def effective_inactive_days(last_date, current_date):
    total_days = (current_date - last_date).days

    # calculate overlap with COVID window
    overlap_start = max(last_date, COVID_START)
    overlap_end = min(current_date, COVID_END)

    if overlap_start < overlap_end:
        covid_days = (overlap_end - overlap_start).days
    else:
        covid_days = 0

    return total_days - covid_days

def update_uncertainty_after_match(u_old, uncertainty_decay, u_min=0.05, u_max=1.0):
    # multiplicative shrink each match
    u_new = u_old * uncertainty_decay
    # clamp
    return max(u_min, min(u_max, u_new))

def grow_uncertainty_inactivity(u_old, days_inactive, u_growth,
                               u_min=0.05, u_max=1.0,
                                max_inc_per_month=0.15, grace_days=60,):
    if days_inactive <= grace_days:
        return max(u_min, min(u_max, u_old))

    months = (days_inactive - grace_days) / 30.0
    inc = months * u_growth
    inc = min(inc, max_inc_per_month)

    u_new = u_old + inc
    return max(u_min, min(u_max, u_new))

def prepare_player_state(pid, ratings, last_played, uncertainty_dict,
                         current_date, base_rating, u_growth,
                         u_min, u_max, max_inc_per_month,
                         rating_decay_per_year, decay_grace_days):

    old_rating = ratings.get(pid, base_rating)
    last_date = last_played.get(pid)
    u_old = uncertainty_dict.get(pid, 1.0)
    if last_date:
        days_inactive = effective_inactive_days(last_date, current_date)

        u_old = grow_uncertainty_inactivity(
            u_old,
            days_inactive,
            u_growth,
            u_min,
            u_max,
            max_inc_per_month,
            grace_days=60)

        # --- NEW: Rating Decay for Inactivity ---
        if days_inactive > decay_grace_days and rating_decay_per_year > 0:
            decay_factor = (days_inactive - decay_grace_days) / 365.25
            total_decay_multiplier = rating_decay_per_year * decay_factor
            # Cap the total decay to 50% of the rating above base
            total_decay_multiplier = min(total_decay_multiplier, 0.5)

            excess_rating = old_rating - base_rating
            decay_amount = excess_rating * total_decay_multiplier
            old_rating -= decay_amount

    # persist updated values
    ratings[pid] = old_rating
    uncertainty_dict[pid] = u_old

    return old_rating, u_old

def prepare_synergy_state(pair_key, synergy_dict, su_dict, last_played_dict,
                          current_date, su_growth, su_min, su_max,
                          max_inc_per_month, player_ratings=None):
    
    if pair_key not in synergy_dict:
        if player_ratings is not None and len(player_ratings) == 2:
            gap = abs(player_ratings[0] - player_ratings[1])
            # Cold-start synergy heuristic: large rating gaps result in a negative starting synergy,
            # while well-matched players start with neutral/slight positive synergy.
            synergy = -0.05 * gap if gap > 200 else 10.0
        else:
            synergy = 0.0
        synergy_dict[pair_key] = synergy
    else:
        synergy = synergy_dict[pair_key]
        
    su = su_dict.get(pair_key, 1.0)
    last_date = last_played_dict.get(pair_key)

    if last_date:
        days_inactive = effective_inactive_days(last_date, current_date)
        su = grow_uncertainty_inactivity(
            su, days_inactive, su_growth, su_min, su_max, max_inc_per_month
        )
    
    su_dict[pair_key] = su
    return synergy, su

def update_synergy_state(synergy, su, error, Ks, Ks_beta, su_decay, su_min, su_max):
    su_scaled = (su - su_min) / (su_max - su_min + 1e-12)
    Ks_multi = 1 + Ks_beta * su_scaled
    Ks_eff = Ks * Ks_multi

    delta = Ks_eff * error
    new_synergy = synergy + delta
    new_su = max(su_min, su * su_decay)

    return new_synergy, new_su


def load_synergy(test_cursor, run_id):
    synergy_by_event = {}
    synergy_uncertainty_by_event = {}

    test_cursor.execute("""
        SELECT event, player1_id, player2_id, synergy, synergy_uncertainty
        FROM pair_synergy_current
        WHERE run_id = ?
    """, (run_id,))

    for event, p1, p2, value, su_value in test_cursor:
        if event not in synergy_by_event:
            synergy_by_event[event] = {}
            synergy_uncertainty_by_event[event] = {}

        key = f"{p1}+{p2}"
        synergy_by_event[event][key] = value
        synergy_uncertainty_by_event[event][key] = su_value or 1.0

    return synergy_by_event, synergy_uncertainty_by_event

def snapshot_synergy(test_cursor, run_id, synergy_by_event, su_by_event, snapshot_date, updated_keys=None):
    synergy_history_data = []
    if updated_keys is not None:
        for event, key in updated_keys:
            value = synergy_by_event.get(event, {}).get(key)
            su = su_by_event.get(event, {}).get(key, 1.0)
            if value is not None:
                p1, p2 = key.split("+")
                synergy_history_data.append((run_id, event, p1, p2, snapshot_date, value, su))
    else:
        for event, synergy_dict in synergy_by_event.items():
            su_dict = su_by_event.get(event, {})
            for key, value in synergy_dict.items():
                p1, p2 = key.split("+")
                su = su_dict.get(key, 1.0)
    
                synergy_history_data.append((
                    run_id,
                    event,
                    p1,
                    p2,
                    snapshot_date,
                    value,
                    su
                ))
    if synergy_history_data:
        test_cursor.executemany("""
            INSERT OR REPLACE INTO pair_synergy_history
            (run_id, event, player1_id, player2_id,
             snapshot_date, synergy, synergy_uncertainty)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, synergy_history_data)

def snapshot_uncertainty(test_cursor, run_id, uncertainty_by_event, snapshot_date, updated_keys=None):
    uncertainty_history_data = []
    if updated_keys is not None:
        for event, pid in updated_keys:
            u = uncertainty_by_event.get(event, {}).get(pid)
            if u is not None:
                uncertainty_history_data.append((run_id, event, pid, snapshot_date, u))
    else:
        for event, u_dict in uncertainty_by_event.items():
            for pid, u in u_dict.items():
                uncertainty_history_data.append((run_id, event, pid, snapshot_date, u))
    if uncertainty_history_data:
        test_cursor.executemany("""
            INSERT OR REPLACE INTO uncertainty_history
            (run_id, event, player_id, snapshot_date, uncertainty)
            VALUES (?, ?, ?, ?, ?)
        """, uncertainty_history_data)

def upsert_final_player_ratings(test_cursor, run_id, ratings_by_event, peak_by_event, peak_date_by_event, last_played_by_event, match_count_by_event):
    for event, ratings in ratings_by_event.items():
        peaks = peak_by_event.get(event, {})
        peak_dates = peak_date_by_event.get(event, {})
        last_played = last_played_by_event.get(event, {})
        match_counts = match_count_by_event.get(event, {})

        for pid, final_rating in ratings.items():
            final_date_obj = last_played.get(pid)
            final_rating_date = final_date_obj.strftime("%Y-%m-%d") if final_date_obj else None
            peak_rating = peaks.get(pid, final_rating)
            peak_rating_date = peak_dates.get(pid, final_rating_date)
            match_count = match_counts.get(pid, 0)

            test_cursor.execute("""
                INSERT INTO final_player_ratings
                (run_id, event, player_id, final_rating, final_rating_date, peak_rating, peak_rating_date, match_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, event, player_id) DO UPDATE SET
                    final_rating=excluded.final_rating,
                    final_rating_date=excluded.final_rating_date,
                    peak_rating=excluded.peak_rating,
                    peak_rating_date=excluded.peak_rating_date,
                    match_count=excluded.match_count
            """, (
                run_id,
                event,
                pid,
                final_rating,
                final_rating_date,
                peak_rating,
                peak_rating_date,
                match_count
            ))

def upsert_final_uncertainty(test_cursor, run_id, uncertainty_by_event, last_played_by_event):
    for event, u_dict in uncertainty_by_event.items():
        last_played = last_played_by_event.get(event, {})
        for pid, u in u_dict.items():
            final_date_obj = last_played.get(pid)
            final_date = final_date_obj.strftime("%Y-%m-%d") if final_date_obj else None

            test_cursor.execute("""
                INSERT INTO final_player_uncertainty
                (run_id, event, player_id, final_uncertainty, final_date)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(run_id, event, player_id) DO UPDATE SET
                    final_uncertainty = excluded.final_uncertainty,
                    final_date = excluded.final_date
            """, (run_id, event, pid, u, final_date))

def upsert_final_synergy(test_cursor, run_id, synergy_by_event, su_by_event, last_played_by_event):
    for event, synergy_dict in synergy_by_event.items():
        su_dict = su_by_event.get(event, {})
        last_played_dict = last_played_by_event.get(event, {})
        for key, synergy_val in synergy_dict.items():
            p1, p2 = key.split("+")
            su_val = su_dict.get(key, 1.0)
            last_date_obj = last_played_dict.get(key)
            last_date = last_date_obj.strftime("%Y-%m-%d") if last_date_obj else None

            test_cursor.execute("""
                INSERT INTO pair_synergy_current
                (run_id, event, player1_id, player2_id, synergy, synergy_uncertainty, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, event, player1_id, player2_id) DO UPDATE SET
                    synergy=excluded.synergy,
                    synergy_uncertainty=excluded.synergy_uncertainty,
                    last_updated=excluded.last_updated
            """, (run_id, event, p1, p2, synergy_val, su_val, last_date))



def run_elo(
        core_conn,
        test_conn,
        run_id,
        split_date,
        event_params,
        store_history=False,
        base_rating=1000,
        event_filter=None,
    ):
    
    core_cursor = core_conn.cursor()
    test_cursor = test_conn.cursor()
    test_cursor.execute("PRAGMA synchronous = OFF;")
    test_cursor.execute("PRAGMA journal_mode = WAL;")

    init_rating_table(test_conn)
    core_cursor.execute("""
        SELECT
            m.match_id,
            m.match_date,
            m.event_canon,
            GROUP_CONCAT(CASE WHEN mp.side = 1 THEN mp.player_id END) AS p1_ids,
            GROUP_CONCAT(CASE WHEN mp.side = 2 THEN mp.player_id END) AS p2_ids,
            m.winner_side,
            m.score
        FROM matches m
        JOIN match_participants mp
            ON mp.match_id = m.match_id
        LEFT JOIN tournaments t
            ON t.tournament_id = m.tournament_id
        WHERE (? IS NULL OR m.event_canon = ?)
        AND m.is_valid_for_rating = 1
        GROUP BY m.match_id, m.match_date, m.event_canon, m.winner_side, m.score
        HAVING COUNT(CASE WHEN mp.side = 1 THEN 1 END) > 0
           AND COUNT(CASE WHEN mp.side = 2 THEN 1 END) > 0
        ORDER BY m.match_date ASC, m.match_id ASC;
    """, (event_filter, event_filter))

    synergy_by_event, synergy_uncertainty_by_event = load_synergy(test_cursor, run_id)
    current_snapshot_date = None
    updated_players_today = set()
    updated_synergy_today = set()
    ratings_by_event = {}
    last_played_by_event = {}
    uncertainty_by_event = {}
    synergy_last_played_by_event = {}
    peak_by_event = {}
    peak_date_by_event = {}
    match_count_by_event = {}
    u_A = 0
    u_B = 0
    match_processed = 0

    for match in core_cursor:
        match_id, date_str, event, p1_ids, p2_ids, winner_side, score = match

        # --- NEW: Get event-specific or default parameters ---
        params = event_params.get(event, event_params.get("default"))
        if not params:
            # If no specific or default params for this event, skip it.
            # This can happen for "UNKNOWN" events.
            continue

        K = params['K']
        beta = params['beta']
        D_eff = params['D']
        Ks = params['Ks']
        uncertainty_decay = params['uncertainty_decay']
        u_growth = params['u_growth']
        Ks_beta = params['Ks_beta']
        su_decay = params['su_decay']
        su_growth = params['su_growth']
        cap_K_mult = params['cap_K_mult']
        mov_base_mult = params.get('mov_base_mult', 1.0)
        mov_growth_rate = params.get('mov_growth_rate', 1.0)
        # Also get the u_... params that were previously defaults in the signature
        rating_decay_per_year = params.get('rating_decay_per_year', 0.0)
        decay_grace_days = params.get('decay_grace_days', 90)
        u_min = params.get('u_min', 0.05)
        u_max = params.get('u_max', 1.0)
        u_max_inc_per_month = params.get('u_max_inc_per_month', 0.15)

        u_A = 0
        u_B = 0
        match_processed += 1

        if event not in ratings_by_event:
            ratings_by_event[event] = {}

        if event not in synergy_by_event:
            synergy_by_event[event] = {}

        if event not in synergy_uncertainty_by_event:
            synergy_uncertainty_by_event[event] = {}

        if event not in last_played_by_event:
            last_played_by_event[event] = {}
        
        if event not in synergy_last_played_by_event:
            synergy_last_played_by_event[event] = {}

        if event not in uncertainty_by_event:
            uncertainty_by_event[event] = {}

        if event not in peak_by_event:
            peak_by_event[event] = {}

        if event not in peak_date_by_event:
            peak_date_by_event[event] = {}

        if event not in match_count_by_event:
            match_count_by_event[event] = {}

        u_event = uncertainty_by_event[event]
        ratings = ratings_by_event[event]
        synergy = synergy_by_event[event]
        synergy_uncertainty = synergy_uncertainty_by_event[event]
        synergy_last_played = synergy_last_played_by_event[event]
        last_played = last_played_by_event[event]
        peaks = peak_by_event[event]
        peak_dates = peak_date_by_event[event]
        match_counts = match_count_by_event[event]

        current_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        if store_history:
            if current_snapshot_date != date_str:
                if current_snapshot_date is not None:
                    snapshot_ratings(test_cursor, run_id, ratings_by_event, current_snapshot_date, updated_players_today)                    
                    snapshot_synergy(test_cursor, run_id, synergy_by_event, synergy_uncertainty_by_event, current_snapshot_date, updated_synergy_today)
                    snapshot_uncertainty(test_cursor, run_id, uncertainty_by_event, current_snapshot_date, updated_players_today)

                current_snapshot_date = date_str
                updated_players_today.clear()
                updated_synergy_today.clear()
                
            if match_processed % 5000 == 0:
                test_conn.commit()

        teamA_players = p1_ids.split(",")
        teamB_players = p2_ids.split(",")

        win = 1 if winner_side == 1 else 0

        rating_teamA = []
        for pid in teamA_players:
            rating, u = prepare_player_state(pid, ratings, last_played, u_event, current_date, base_rating, u_growth, u_min, u_max, u_max_inc_per_month, rating_decay_per_year, decay_grace_days)

            rating_teamA.append(rating)
            u_A += u
                                             
        rating_teamB = []
        for pid in teamB_players:
            rating, u = prepare_player_state(pid, ratings, last_played, u_event, current_date, base_rating, u_growth, u_min, u_max, u_max_inc_per_month, rating_decay_per_year, decay_grace_days)

            rating_teamB.append(rating)
            u_B += u

        rating_a = sum(rating_teamA) / len(teamA_players)
        rating_b = sum(rating_teamB) / len(teamB_players)

        if len(teamA_players) == 2:
            pairA_key = "+".join(sorted(teamA_players))
            pairB_key = "+".join(sorted(teamB_players))

            sa, sua = prepare_synergy_state(pairA_key, synergy, synergy_uncertainty, synergy_last_played, current_date, su_growth, u_min, u_max, u_max_inc_per_month, rating_teamA)
            sb, sub = prepare_synergy_state(pairB_key, synergy, synergy_uncertainty, synergy_last_played, current_date, su_growth, u_min, u_max, u_max_inc_per_month, rating_teamB)

            ra = rating_a + sa
            rb = rating_b + sb
        else:
            ra = rating_a
            rb = rating_b

        ua = u_A/len(teamA_players)
        ub = u_B/len(teamB_players)

        if len(teamA_players) == 2: # It's a doubles match
            # Boost team uncertainty by factoring in the pair's synergy uncertainty.
            # This makes new pairs converge faster.
            ua = (ua + sua) / 2
            ub = (ub + sub) / 2

        mean_u = (ua + ub)/2
        u_scaled = (mean_u - u_min) / (u_max - u_min + 1e-12)

        p = 1 / (1 + 10 ** ((rb - ra) / D_eff))
        p = max(1e-12, min(1 - 1e-12, p))

        K_multi = 1 + beta * u_scaled
        K_multi = min(K_multi, cap_K_mult)
        K_eff = K * K_multi
   
        mov_multiplier = get_mov_multiplier(score, event, mov_base_mult, mov_growth_rate)
        K_eff = K_eff * mov_multiplier

        delta = K_eff * (win - p)

        if date_str >= split_date:
            #prediction block
            test_cursor.execute("""
                INSERT OR REPLACE INTO prediction_log
                (run_id, match_id, event, predicted_prob, actual,
                pre_rating_p1, pre_rating_p2, uncertainty_mean, D_eff , K_eff)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                match_id,
                event,
                p,
                win,
                ra,
                rb,
                mean_u,
                D_eff,
                K_eff
            ))
            
        
        abs_delta = abs(delta)

        # Determine delta allocation for Team A players
        delta_teamA = {}
        if len(teamA_players) == 2:
            p1, p2 = teamA_players
            r1 = ratings.get(p1, base_rating)
            r2 = ratings.get(p2, base_rating)
            
            if r1 >= r2:
                high_id, low_id = p1, p2
                r_high, r_low = r1, r2
            else:
                high_id, low_id = p2, p1
                r_high, r_low = r2, r1
                
            gap = r_high - r_low
            pair_key = "+".join(sorted(teamA_players))
            syn = synergy.get(pair_key, 0.0)
            
            alpha = params.get('convergence_alpha', 0.0005)
            siphon_mult = min(0.4, alpha * gap * max(0.0, syn))
            
            if win == 1:  # Team A wins (gains rating)
                delta_teamA[high_id] = abs_delta * (0.5 - siphon_mult)
                delta_teamA[low_id] = abs_delta * (0.5 + siphon_mult)
            else:  # Team A loses (loses rating)
                delta_teamA[high_id] = -abs_delta * (0.5 + siphon_mult)
                delta_teamA[low_id] = -abs_delta * (0.5 - siphon_mult)
        else:
            sign = 1 if win == 1 else -1
            for pid in teamA_players:
                delta_teamA[pid] = (sign * abs_delta) / len(teamA_players)

        # Determine delta allocation for Team B players
        delta_teamB = {}
        if len(teamB_players) == 2:
            p1, p2 = teamB_players
            r1 = ratings.get(p1, base_rating)
            r2 = ratings.get(p2, base_rating)
            
            if r1 >= r2:
                high_id, low_id = p1, p2
                r_high, r_low = r1, r2
            else:
                high_id, low_id = p2, p1
                r_high, r_low = r2, r1
                
            gap = r_high - r_low
            pair_key = "+".join(sorted(teamB_players))
            syn = synergy.get(pair_key, 0.0)
            
            alpha = params.get('convergence_alpha', 0.0005)
            siphon_mult = min(0.4, alpha * gap * max(0.0, syn))
            
            if win == 0:  # Team B wins (gains rating)
                delta_teamB[high_id] = abs_delta * (0.5 - siphon_mult)
                delta_teamB[low_id] = abs_delta * (0.5 + siphon_mult)
            else:  # Team B loses (loses rating)
                delta_teamB[high_id] = -abs_delta * (0.5 + siphon_mult)
                delta_teamB[low_id] = -abs_delta * (0.5 - siphon_mult)
        else:
            sign = 1 if win == 0 else -1
            for pid in teamB_players:
                delta_teamB[pid] = (sign * abs_delta) / len(teamB_players)

        # Apply updates for Team A
        for pid in teamA_players:
            old = ratings.get(pid, base_rating)
            ratings[pid] = old + delta_teamA[pid]
            last_played[pid] = current_date
            match_counts[pid] = match_counts.get(pid, 0) + 1
            if pid not in peaks or ratings[pid] > peaks[pid]:
                peaks[pid] = ratings[pid]
                peak_dates[pid] = date_str
            u_old = u_event.get(pid, 1.0)
            u_event[pid] = update_uncertainty_after_match(
                u_old,
                uncertainty_decay,
                u_min=u_min,
                u_max=u_max
            )
            if store_history:
                updated_players_today.add((event, pid))

        # Apply updates for Team B
        for pid in teamB_players:
            old = ratings.get(pid, base_rating)
            ratings[pid] = old + delta_teamB[pid]
            last_played[pid] = current_date
            match_counts[pid] = match_counts.get(pid, 0) + 1
            if pid not in peaks or ratings[pid] > peaks[pid]:
                peaks[pid] = ratings[pid]
                peak_dates[pid] = date_str
            u_old = u_event.get(pid, 1.0)
            u_event[pid] = update_uncertainty_after_match(
                u_old,
                uncertainty_decay,
                u_min=u_min,
                u_max=u_max
            )
            if store_history:
                updated_players_today.add((event, pid))

        if len(teamA_players) == 2:
            new_sa, new_sua = update_synergy_state(sa, sua, win - p, Ks, Ks_beta, su_decay, u_min, u_max)
            synergy[pairA_key] = new_sa
            synergy_uncertainty[pairA_key] = new_sua
            synergy_last_played[pairA_key] = current_date
            if store_history:
                updated_synergy_today.add((event, pairA_key))
        
        if len(teamB_players) == 2:
            new_sb, new_sub = update_synergy_state(sb, sub, -(win - p), Ks, Ks_beta, su_decay, u_min, u_max)
            synergy[pairB_key] = new_sb
            synergy_uncertainty[pairB_key] = new_sub
            synergy_last_played[pairB_key] = current_date
            if store_history:
                updated_synergy_today.add((event, pairB_key))

        

    if current_snapshot_date is not None:
        snapshot_ratings(test_cursor, run_id, ratings_by_event, current_snapshot_date, updated_players_today)
        snapshot_synergy(test_cursor, run_id, synergy_by_event, synergy_uncertainty_by_event, current_snapshot_date, updated_synergy_today)
        snapshot_uncertainty(test_cursor, run_id, uncertainty_by_event, current_snapshot_date, updated_players_today)
    upsert_final_player_ratings(
        test_cursor,
        run_id,
        ratings_by_event,
        peak_by_event,
        peak_date_by_event,
        last_played_by_event,
        match_count_by_event,
    )
    upsert_final_uncertainty(test_cursor, run_id, uncertainty_by_event, last_played_by_event)
    upsert_final_synergy(test_cursor, run_id, synergy_by_event, synergy_uncertainty_by_event, synergy_last_played_by_event)
    test_conn.commit()

    
