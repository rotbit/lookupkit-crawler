import asyncio
import time
import logging
import os
from dotenv import load_dotenv
from multiprocessing import Process
from pymongo import MongoClient
from supabase import create_client, Client

# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载.env
load_dotenv()

class DataLoader:
    def __init__(self):
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        supabase: Client = create_client(url, key)
        self.supabase = supabase
        
        mongo_db_url: str = os.environ.get("MONGO_DB_URL")
        self.mongo_client = MongoClient(mongo_db_url)
        self.mongo_db = self.mongo_client["lookupkit"]
            
    def category_data_sync(self):
        logger.info("开始加载navigation_category")
        categoryTable = self.supabase.table('navigation_category').select('*').execute()
        print(categoryTable)
        self.write_to_mongo(categoryTable.data, "navigation_category")
    
    def submit_data_sync(self):
        logger.info("开始加载submitTable")
        submitTable = self.supabase.table('submit').select('*').execute()
        print(submitTable)
        self.write_to_mongo(submitTable.data, "submit")

    def web_navigation_data_sync(self):
        logger.info("开始加载web_navigation")
        webNavigationTable = self.supabase.table('web_navigation').select('*').execute()
        self.write_to_mongo(webNavigationTable.data, "web_navigation")
 
    def write_to_mongo(self, data, collection):
        if not data:
            logger.info(f"没有数据写入{collection}表")
            return
        
        client = self.mongo_db[collection]
        for item in data:
            try:
                client.insert_one(item)
                logger.info(f"成功写入{collection}表")
            except Exception as e:
                logger.error(f"写入{collection}表失败: {e}")


def start_sync_scheduler():    
    while True:    
        data_loader = DataLoader()
        data_loader.submit_data_sync()
        data_loader.category_data_sync()
        time.sleep(60 * 60 * 12) # 每12小时同步一次数据

def start_sync_scheduler_once():
    data_loader = DataLoader()
    data_loader.submit_data_sync()
    data_loader.category_data_sync()
    
# 异步执行翻译
def run_async_data_schedule(web_nav: dict, model_name:str, language:str):
    # 启动翻译进程
    asyncio.run(start_sync_scheduler())
