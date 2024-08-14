import logging
import os
import time
import sys
from supabase import create_client, Client
from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from utils.common_util import GetLangeageCode

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

@app.post("/task/result")
async def task_result(request: TaskResultRequest):
    task_result = get_task_result(request.task_id, request.language)
    if task_result is None:
        return {"code": 1, "message": "任务不存在"}
    result = {k:v for k,v in task_result.items() if k != "_id"}
    return {"data": result, "code": 0}

@app.get("/task/list")
async def task_list(auth: str = Header(None)):
    results = getTaskList()
    return {"data": results, "code": 0}

@app.get("/task/detail/{task_id}")
async def task_detail(task_id: str):
   task_detail = getTaskDetail(task_id)
   return {"data": task_detail, "code": 0}

@app.get("/task/progress/{task_id}")
async def task_progress(task_id: str):
    task_progress = get_task_progress(task_id)
    if task_progress is None:
        return {"code": 1, "message": "任务不存在"}
    return {"code": 0, "status": task_progress['status']}

@app.post("/task/generate")
async def generate(request: GenerateRequest):
    # 更新任务信息
    update_task_detail(request.task_id, request.dict())
    # 创建任务进度
    create_task_progress(request.task_id, "collect_data")
    
    step = {
        "generate_intro": True,
        "generate_feature": True,
        "generate_tags": True
    }
    generate_page_content(request.model_dump(), step)
    return { "code": 0, "status": "collect_data", "message": "任务已经开始生成，请稍后查看" }


@app.post("/task/generate_intro")
async def generate_introd(request: GenerateRequest):
    # 更新任务信息
    update_task_detail(request.task_id, request.dict())
    # 创建任务进度
    create_task_progress(request.task_id, "generate_introd")
        
    step = {
        "generate_intro": True,
        "generate_feature": False,
        "generate_tags": False
    }
    generate_page_content(request.model_dump(), step)
    return { "code": 0, "status": "generate_introd", "message": "任务已经开始生成，请稍后查看" }

@app.post("/task/generate_feature")
async def generate_introd(request: GenerateRequest):
    # 更新任务信息
    update_task_detail(request.task_id, request.dict())
    # 创建任务进度
    create_task_progress(request.task_id, "generate_introd")
        
    step = {
        "generate_intro": False,
        "generate_feature": True,
        "generate_tags": False
    }
    generate_page_content(request.model_dump(), step)
    return { "code": 0, "status": "generate_feature", "message": "任务已经开始生成，请稍后查看" }

@app.post("/task/delete")
async def delete_task(request: DeleteTaskRequest):
    client = GetMongoClient("submit")
    client.delete_one({"id": request.task_id})
    
    return {"code": 0, "message": "删除成功"}

@app.post("/task/add_task")
async def add_task(request: AddTaskRequest):
    client = GetMongoClient("submit")
    submit_data = request.model_dump()
    submit_data['id'] = int(time.time())
    submit_data['email'] = ''
    client.insert_one(submit_data)
    return {"code": 0, "task_id": submit_data['id'] }

@app.post("/task/publish")
async def publish_task(request: PublishTaskRequest):
    # 创建web_navigation
    web_nav = create_web_navigation(request.task_id, request.language)
    
    # 同步到supabase
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    
    supabase.table('web_navigation').insert(web_nav).execute()    
        
    translate_process = Process(target=run_async_translate_process, args=(web_nav, request.model, request.language))
    translate_process.start()
    
    return {"code": 0, "message": "任务已经开始发布，请稍后查看" }
