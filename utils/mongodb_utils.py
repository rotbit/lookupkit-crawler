import logging
import os
import time
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def GetMongoClient(collection:str) -> MongoClient:
    # mongodb查询submit表    
    mongo_db_url: str = os.environ.get("MONGO_DB_URL")
    mongo_client = MongoClient(mongo_db_url)
    mongo_db = mongo_client["lookupkit"]
    client = mongo_db[collection]
    return client