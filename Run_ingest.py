from ingest import ingest_folder
from db_ingest import init_db

db_path = "bwf_data_2008-now__v1.sqlite"

conn = None
try:
    conn = init_db(db_path)
    # You can add all the folders you want to process here
    ingest_folder(conn, "data-non-wt")
    ingest_folder(conn, "data_wt")
    # ingest_folder(conn, "data_wt/HSBC_BWF_World_Tour_Super_500") # etc.
    conn.commit()
    print("\nFull ingestion complete and committed!")
finally:
    if conn:
        conn.close()
        print("Database connection closed.")