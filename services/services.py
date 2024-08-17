import logging
import os
import time
import sys
import asyncio
from dotenv import load_dotenv
from multiprocessing import Process

from supabase import Client, create_client


sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
                
from utils.common_util import GetLangeageCode, GetSupportLanguages
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
    
    if task_detail is None:
        logging.error(f"任务详情{task_id}不存在")
        return None
    
    result = {k:v for k,v in task_detail.items() if k != "_id"}
    
    # 检查提示词，没有提示词则使用默认提示词
    if result.get("introd_prompt") is None:
        result["introd_prompt"] = os.getenv("INTRODUCTION_SYS_PROMPT")
    
    if result.get("feature_prompt") is None:
        result["feature_prompt"] = os.getenv("FEATURE_SYS_PROMPT")
        
    return result
   

def generate_page_content(task_detail: dict, step:dict):
    # 更新任务详情
    client = GetMongoClient("task_detail")
    task_id = task_detail.get("submit_id")
    client.update_one({"submit_id": task_id}, {"$set": task_detail})
    # 开启生成进程
    generate_process = Process(target=run_async_crawler_process, args=(task_detail,step))
    generate_process.start()
    
    return task_detail

async def generate_translate(web_nav: dict, model_name:str, language:str):
      # 同步到supabase
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
      # 多语言翻译
    model = get_llm_model(model_name)
    support_languages = GetSupportLanguages()
    for support_language  in support_languages:
        if support_language == language:
            continue
        
        locale = GetLangeageCode(support_language)
        exist = supabase.table('web_navigation').select('*').eq('url', web_nav['url']).eq('locale', locale).execute()
        if len(exist.data) > 0:
            continue
        
        web_nav['locale'] = locale
        web_nav['title'] = model.process_language(support_language, web_nav['title'])
        web_nav['introds'] = model.process_language(support_language, web_nav['introds'])
        web_nav['feature'] = model.process_language(support_language, web_nav['feature'])
        web_nav['content'] = model.process_language(support_language, web_nav['content'])
        
        supabase.table('web_navigation').insert(web_nav).execute()   
    logging.info(f"翻译完成{web_nav['url']}") 

# 异步执行翻译
def run_async_translate_process(web_nav: dict, model_name:str, language:str):
    # 启动翻译进程
    asyncio.run(generate_translate(web_nav, model_name, language))

def run_async_crawler_process(task_detail: dict, step:dict):
    # 启动网站数据爬虫
    asyncio.run(generate_start(task_detail, step))
    
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

def get_collect_data(task_id:str) -> dict:
    client = GetMongoClient("collect_data")
    collect_data = client.find_one({"task_id": task_id})
    return collect_data

def get_category_data() -> list:
    client = GetMongoClient("navigation_category")
    category_data = client.find()
    results = []
    for doc in category_data:
        results.append(doc["name"])
    return results

async def generate_start(task_detail: dict, step:dict):
    collect_data = get_collect_data(task_detail["task_url"])
    update_task_progress(task_detail["task_id"], 10, "collect_data")
    if collect_data is None:
        # 启动网站数据爬虫
        websiteCrawler = WebsiteCrawler()
        collect_data = await websiteCrawler.collect_website_info(task_detail["task_url"])
        # collect_data = get_collect_data(task_detail["task_url"])
        collect_data['task_id'] = task_detail["task_id"]
        # 保存网站数据到mongodb
        client = GetMongoClient("collect_data")
        client.insert_one(collect_data)
        
    page_detail = {
        "task_id": task_detail["task_id"],
        "url": task_detail["task_url"],
        "language": task_detail["language"],
    }
    
    llm_model = get_llm_model(task_detail["model"])
    # 更新任务进度
    if step['generate_intro'] == True:
        update_task_progress(task_detail["task_id"], 20, "generate_intro")
        # 使用大模型生成内容
        introduction = llm_model.generate_introduction(task_detail['introd_prompt'],collect_data["content"])
        page_detail["introduction"] = introduction
        
    if step['generate_feature'] == True:
        update_task_progress(task_detail["task_id"], 20, "generate_feature")
        features = llm_model.generate_features(task_detail['feature_prompt'],collect_data["content"])
        page_detail["features"] = features
        
    # 生成分类
    if step['generate_tags'] == True:
        tags = get_category_data()
        prompt =  'tag_list is:' + ','.join(tags) + '. content is: ' + introduction + features
        update_task_progress(task_detail["task_id"], 20, "generate_tags")
        selected_tags = llm_model.process_tags(prompt)
        page_detail["tags"] = selected_tags
        print(selected_tags)
        
    # 保存网页数据到mongodb
    client = GetMongoClient("page_detail")
    client.update_one({"task_id": task_detail["task_id"], "language": task_detail["language"]}, {"$set": page_detail}, upsert=True)
    
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
    client.update_one({"submit_id": task_id}, {"$set": task_detail})
    
def get_task_result(task_id: str, language: str)-> dict:
    client = GetMongoClient("page_detail")
    task_result = client.find_one({"task_id": task_id, "language": language})
    return task_result

def get_page_data(task_id: str, language: str)-> dict:
    client = GetMongoClient("page_detail")
    page_data = client.find_one({"task_id": task_id, "language": language})
    return page_data
        
def create_web_navigation(task_id: str, language: str):
    web_nav ={}
    # 查询网站数据
    collect_data = get_collect_data(task_id)
    
    # 构建存储数据
    web_nav['name'] = collect_data['name']
    web_nav['title'] = collect_data['title']
    web_nav['url'] = collect_data['url']
    web_nav['image_url'] = collect_data['screenshot']
    web_nav['thumbnail_url'] = collect_data['thumbnail']
    
    web_nav['content'] = collect_data['description']
    
     # 查询生成的页面数据
    page_detail = get_page_data(task_id, language)
    
    if len(page_detail['tags']) > 0:
        web_nav['category_name'] = page_detail['tags'][0]
    web_nav['locale'] =  GetLangeageCode(page_detail['language'])
    web_nav['introds'] = page_detail['introduction']
    web_nav['feature'] = page_detail['features']
    return web_nav