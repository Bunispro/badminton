from ingest import ingest_folder
db_path = "bwf_data_2008-now__v1.sqlite"
ingest_folder(db_path, "data-non-wt")
ingest_folder(db_path, "data_wt")

#DO NOT TOUCH AFTER RUNNING ARGGHHH