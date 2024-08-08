import logging
import os
import time
import sys
from fastapi import FastAPI, Header, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from services.services import *
from models.requests import GenerateRequest

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

load_dotenv()

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
    return {"code": 0, "status": task_progress['status']}

@app.post("/task/generate")
async def generate(request: GenerateRequest):
    # 更新任务信息
    update_task_detail(request.task_id, request.dict())
    # 创建任务进度
    create_task_progress(request.task_id, "collect_data")
        
    generate_page_content(request.model_dump())
    return { "code": 0, "status": "collect_data", "message": "任务已经开始生成，请稍后查看" }
