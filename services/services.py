import logging
import os
import time
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
                
from utils.mongodb_utils import GetMongoClient

load_dotenv()

def getTaskList()-> dict:
    client = GetMongoClient("submit")
    submit = client.find()
    
    results = []
    for doc in submit:
        item = {k:v for k,v in doc.items() if k != "_id"}
        results.append(item)
    return results
        

def getTaskDetail(task_id: str)-> dict:
    client = GetMongoClient("task_detail")
    task_detail = client.find_one({"submit_id": task_id})
    # 不存在任务，创建默认任务参数
    if task_detail is None:
        createDefaultTask(task_id)
        task_detail = client.find_one({"submit_id": task_id})
    # 从mongodb中查到详情，取消_id后返回任务详情
    
    if task_detail is None:
        logging.error(f"任务详情{task_id}不存在")
        return None
    
    result = {k:v for k,v in task_detail.items() if k != "_id"}
    return result
   

def createDefaultTask(task_id: str)-> dict:
    # 先查询submit表，查询基础数据
    client = GetMongoClient("submit")
    submit_data = client.find_one({"id": int(task_id)})
    if submit_data is None:
        logging.error(f"任务{task_id}不存在")
        return None
    
    task_detail = {
        "submit_id": task_id,
        "reference_content": "",
        "created_at": int(time.time()),
        "model": "moonshot-v1-8k",
        "language": "chinese",
        "keyword": "",
        "keyword_density": 0.05,
        "targe_url": submit_data["url"],
        "name": submit_data["name"],
        "email": submit_data["email"],
    }
    client = GetMongoClient("task_detail")
    print("111")
    client.insert_one(task_detail)
    print("222")
    return task_detail