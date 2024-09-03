import logging
import os
import time
import sys
import jwt
from supabase import create_client, Client
from fastapi import Depends, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status

from dotenv import load_dotenv

from utils.common_util import GetLangeageCode
from utils.schedule import start_sync_scheduler_once

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from services.services import *
from models.requests import *

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_token(token: str = Depends(oauth2_scheme)):
    secret_key = os.environ.get("AUTH_SECRET")
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.post("/task/result")
async def task_result(request: TaskResultRequest,token: str = Depends(verify_token)):
    task_result = get_task_result(request.task_id, request.language)
    if task_result is None:
        return {"code": 1, "message": "任务不存在"}
    result = {k:v for k,v in task_result.items() if k != "_id"}
    return {"data": result, "code": 0}

@app.get("/task/web_navs")
async def get_web_navs(token: str = Depends(verify_token)):
    results = getWebNavs()
    return {"data": results, "code": 0}

@app.get("/task/list")
async def task_list(token: str = Depends(verify_token)):
    results = getSubmitWebUrlList()
    return {"data": results, "code": 0}

@app.get("/task/detail/{task_id}")
async def task_detail(task_id: str,token: str = Depends(verify_token)):
   task_detail = getTaskDetail(task_id)
   return {"data": task_detail, "code": 0}

@app.get("/task/progress/{task_id}")
async def task_progress(task_id: str,token: str = Depends(verify_token)):
    task_progress = get_task_progress(task_id)
    if task_progress is None:
        return {"code": 1, "message": "任务不存在"}
    return {"code": 0, "status": task_progress['status']}


@app.post("/task/generate")
async def generate(request: GenerateRequest,token: str = Depends(verify_token)):
    # 设置默认提示词
    prompt = os.environ.get("INTRODUCTION_SYS_PROMPT")
    if request.section_type == "feature":
        prompt = os.environ.get("FEATURE_SYS_PROMPT")
    
    # 请求中的提示词不为空，使用请求中的提示词
    if request.prompt and request.prompt != "":
        prompt = request.prompt
    
    # 更新prompt参数
    if request.section_type == "feature":
        GetMongoClient("web_nav").update_one({"web_url": request.url}, {"$set": {"feature_prompt": prompt}})
    if request.section_type == "introduction":
        GetMongoClient("web_nav").update_one({"web_url": request.url}, {"$set": {"intro_prompt": prompt}})
        
    # 更新公共参数
    GetMongoClient("web_nav").update_one({"web_url": request.url}, {"$set": {
            "model": request.model, 
            "language": request.language, 
            "keyword": request.keyword, 
            "density": request.density,
            "tags": request.tags,
        }})
    
    # 获取收集的数据
    client = GetMongoClient("crawl_data")
    crawl_data = client.find_one({"url": request.url})
    if crawl_data is None:
        return {"code": 1, "message": f"crawl data not found {request.name}"}
    
    content = crawl_data["content"] + " " + crawl_data["title"] + " " + crawl_data["description"]
    # 生成内容
    llm_model = get_llm_model(request.model)
    prompt = get_format_prompt(request, prompt)
    generated_content = llm_model.generate_introduction(prompt, content)
    
    if request.section_type == "feature":
        GetMongoClient("web_nav").update_one({"web_url": request.url}, {"$set": {"feature": generated_content}})
    if request.section_type == "introduction":
        GetMongoClient("web_nav").update_one({"web_url": request.url}, {"$set": {"introduction": generated_content}})
        
    return { "code": 0, "message": f"{request.section_type} was generated", "content": generated_content}


@app.post("/task/delete")
async def delete_task(request: DeleteTaskRequest,token: str = Depends(verify_token)):
    client = GetMongoClient("submit")
    client.delete_one({"id": request.task_id})
    
    return {"code": 0, "message": "删除成功"}

@app.post("/task/add_task")
async def add_task(request: AddTaskRequest,token: str = Depends(verify_token)):
    client = GetMongoClient("web_nav")
    new_web_nav = {
        "name": request.name,
        "web_url": request.url,
        "preview_url": "",
        "model": "gpt-3.5-Turbo",
        "keyword": "",
        "density": 5,
        "language": "en",
        "title":"",
        "desc":"",
        "img_url":"",
        "thumbnail":"",
        "introduction":"",
        "intro_prompt":"",
        "feature":"",
        "feature_prompt":"",
        "tags":"",
        "status": "0",
        "origin_content": "",
    }
    client.insert_one(new_web_nav)
    
    # 更新submit_web_url表状态为任务已加入
    client = GetMongoClient("submit_web_url")
    client.update_one({"id": request.task_id}, {"$set": {"status": "1"}})
    
    return {"code": 0, "msg": "success"}

@app.post("/user/login")
async def user_login(request: UserLoginRequest):
    client = GetMongoClient("user")
    username = client.find_one({"username": request.username, "password": request.password})
    if username is None:
        return {"code": 1, "message": "用户不存在"}
    
    # 更新用户登录时间，生成token  
    client.update_one({"username": request.username}, {"$set": {"last_login": time.time()}})
    # 生成JWT token
    secret_key = os.environ.get("AUTH_SECRET")
    token = jwt.encode({"username": request.username, "exp": time.time() + 3600 * 24 * 30}, secret_key, algorithm="HS256")
    # 更新token
    client.update_one({"username": request.username}, {"$set": {"token": token}})
    
    return {"code": 0, "token": token}

@app.post("/task/publish")
async def publish_task(request: PublishTaskRequest,token: str = Depends(verify_token)):
    # 创建web_navigation
    web_nav = create_web_navigation(request.task_id, request.language, request.introduction, request.feature)
        
    translate_process = Process(target=run_async_translate_process, args=(web_nav, request.model, request.language))
    translate_process.start()
    
    return {"code": 0, "message": "任务已经开始发布，请稍后查看" }

@app.get("/task/categories")
async def get_categories(token: str = Depends(verify_token)):
    client = GetMongoClient("navigation_category")
    categories = client.find()

    results = []
    for doc in categories:
        item = {k:v for k,v in doc.items() if k != "_id"}
        results.append(item["name"])
    return {"data": results, "code": 0}

@app.get("/task/web_nav/{name}")
async def get_web_navs_by_name(name: str,token: str = Depends(verify_token)):
    client = GetMongoClient("web_nav")
    web_nav = client.find_one({"name": name})
    web_nav = {k:v for k,v in web_nav.items() if k != "_id"}
    return {"data": web_nav, "code": 0}

@app.post("/task/crawling_data")
async def collect_data(request: CrawlingRequest,token: str = Depends(verify_token)):
    if not request.url:
        return {"code": 1, "message": "url is empty, please check"}

    websiteCrawler = WebsiteCrawler()
    crawler_data = await websiteCrawler.collect_website_info(request.url)
    
    client = GetMongoClient("web_nav")
    client.update_one({"web_url": crawler_data["url"]}, 
                      {"$set": {
                          "title": crawler_data["title"],
                          "desc": crawler_data["description"],
                          "origin_content": crawler_data["content"],
                          "img_url": crawler_data["screenshot"],
                      }}, 
                      upsert=True)
    
    return {
            "code": 0, 
            "message": "Collect Data finished",
            "data": {"title": crawler_data["title"],
                "desc": crawler_data["description"], 
                "img_url": crawler_data["screenshot"], 
                "thumbnail": crawler_data["thumbnail"]
                }
            }