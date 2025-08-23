from pathlib import Path
from pymongo import MongoClient

OCAPS_URL = 'https://ocap.red-bear.ru/api/v1/operations?tag=&name=&newer=2025-01-01&older=2099-12-12'
OCAP_URL = 'https://ocap.red-bear.ru/data/%s'

OCAPS_PATH = Path("ocaps")
TEMP_PATH = Path("temp")
SQUAD_FILE = Path("data/squad.json")

mongo_client = MongoClient("mongodb://localhost:27017")  
db = mongo_client["stat"]      
collection = db["misssion_stat"]

DOWNLOAD_DATE = "2025-08-23"