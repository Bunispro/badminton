import sqlite3
from tabulate import tabulate  # pip install tabulate (optional but nice)

DB_PATH = "testing_bwf.sqlite"
#DB_PATH = "bwf_data_2008-now__v1.sqlite"
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row  # so columns have names

def q(sql):
    cur = conn.execute(sql)
    rows = cur.fetchall()
    if not rows:
        print("✓ No rows returned")
        return
    print(tabulate([tuple(r) for r in rows], headers=rows[0].keys()))


#elo_v1__mode=vanilla__K=65__D=400__sdate=2018-01-01
cursor = conn.cursor()
cursor.execute

