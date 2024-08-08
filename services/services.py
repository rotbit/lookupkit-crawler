import logging
import os
import time
import sys
import asyncio
from dotenv import load_dotenv
from multiprocessing import Process


sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
                
from utils.mongodb_utils import GetMongoClient
from utils.website_crawler import WebsiteCrawler
from services.llm import get_llm_model

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
   

def generate_page_content(task_detail: dict):
    # 更新任务详情
    client = GetMongoClient("task_detail")
    task_id = task_detail.get("submit_id")
    client.update_one({"submit_id": task_id}, {"$set": task_detail})
    
    # 开启生成进程
    generate_process = Process(target=run_async_process, args=(task_detail,))
    generate_process.start()
    
    return task_detail

def run_async_process(task_detail: dict):
    # 启动网站数据爬虫
    asyncio.run(generate_start(task_detail))
    
def create_task_progress(task_id: str, status: str):
    # 删除已有的进度，创建新的进度
    client = GetMongoClient("task_progress")
    client.delete_one({"submit_id": task_id})
    
    client.insert_one({"submit_id": task_id, "progress": 0, "status": status})

def get_task_progress(task_id: str):
    client = GetMongoClient("task_progress")
    task_progress = client.find_one({"submit_id": task_id})
    return task_progress

def update_task_progress(task_id: str, progress: int, status: str):
    client = GetMongoClient("task_progress")
    client.update_one({"submit_id": task_id}, {"$set": {"progress": progress, "status": status}})

def get_collect_data(url: str) -> dict:
    client = GetMongoClient("collect_data")
    collect_data = client.find_one({"url": url})
    return collect_data

def get_category_data() -> list:
    client = GetMongoClient("navigation_category")
    category_data = client.find()
    results = []
    for doc in category_data:
        results.append(doc["name"])
    return results

async def generate_start(task_detail: dict):
    collect_data = get_collect_data(task_detail["task_url"])
    update_task_progress(task_detail["task_id"], 10, "collect_data")
    if collect_data is None:
        # 启动网站数据爬虫
        websiteCrawler = WebsiteCrawler()
        await websiteCrawler.collect_website_info(task_detail["task_url"])
        collect_data = get_collect_data(task_detail["task_url"])
        
    # 更新任务进度
    update_task_progress(task_detail["task_id"], 20, "generate_intro")
    # 使用大模型生成内容
    llm_model = get_llm_model(task_detail["model"])
    introduction = llm_model.generate_introduction(collect_data["content"])
    
    update_task_progress(task_detail["task_id"], 20, "generate_feature")
    features = llm_model.generate_features(collect_data["content"])
    
    # 生成分类
    tags = get_category_data()
    prompt =  'tag_list is:' + ','.join(tags) + '. content is: ' + introduction + features
    update_task_progress(task_detail["task_id"], 20, "generate_tags")
    selected_tags = llm_model.process_tags(prompt)
    
    page_detail = {
        "url": task_detail["task_url"],
        "introduction": introduction,
        "features": features,
        "tags": selected_tags,
        "language": task_detail["language"],
    }
    # 保存网页数据到mongodb
    client = GetMongoClient("page_detail")
    client.insert_one(page_detail)
    
    # 更新任务进度
    update_task_progress(task_detail["task_id"], 100, "completed")
    
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
    client.insert_one(task_detail)
    return task_detail

def update_task_detail(task_id: str, task_detail: dict):
    client = GetMongoClient("task_detail")
    result = client.update_one({"submit_id": task_id}, {"$set": task_detail})
    logging.info(f"更新任务{task_id}详情{task_detail}成功")