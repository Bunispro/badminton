from elo_engine_v1 import run_elo
from Compute_metric import register_run_config, evaluate_and_log_run
from db_v2 import init_rating_table
import pandas as pd
import sqlite3
from datetime import datetime
from pandasgui import show
db_path = "bwf_data_2008-now__v1.sqlite"
testing_db_path = "testing_bwf.sqlite"

core_conn = sqlite3.connect(db_path)
model_conn = sqlite3.connect(testing_db_path)


def run_experiment(core_conn, model_conn, config):
    init_rating_table(model_conn)
    register_run_config(model_conn, config)


    run_elo(
            core_conn,
            model_conn,
            split_date=config["split_date"],
            K=config["K"],
            D=config["D"],
            Ks=config["Ks"],
            alpha=config["alpha"],
            beta=config["beta"],
            decay_rate=config["decay_rate"],
            uncertainty_decay=config["uncertainty_decay"],
            u_growth=config["u_growth"],
            run_id=config["run_id"],
            store_history=False
        )



#NOTE: name format is elo_v1(version)__mode=vanilla_additional stuff here

for uncertainty_ in [90,100,110,120,130,140]:
    config = {
        "run_id": f"elo_v1__vanilla+synergy__K={K}",
        "mode": "vanilla+synergy",
        "split_date": "2018-01-01",
        "K": K,
        "D": 400,
        "Ks": 23,
        "alpha": 0,
        "beta": 0,
        "decay_rate": 0,
        "uncertainty_decay": 1,
        "u_growth": 0
    }

    run_experiment(core_conn, model_conn, config)

