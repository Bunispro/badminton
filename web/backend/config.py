import os
import json
from dotenv import load_dotenv

load_dotenv()

COUNTRY_CODES_PATH = "d:/badminton/web/frontend_new/lib/countryCodes.json"
REVERSE_COUNTRY_MAPPING = {}
if os.path.exists(COUNTRY_CODES_PATH):
    with open(COUNTRY_CODES_PATH, 'r', encoding='utf-8') as f:
        country_codes = json.load(f)
        for name, code in country_codes.items():
            REVERSE_COUNTRY_MAPPING.setdefault(code.lower(), []).append(name)
else:
    print(f"Warning: {COUNTRY_CODES_PATH} not found")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
CORE_DB_PATH = os.getenv("CORE_DB", "bwf_data_2008-now__v1.sqlite")
RATINGS_DB_PATH = os.getenv("RATINGS_DB", "elo_ratings.sqlite")
