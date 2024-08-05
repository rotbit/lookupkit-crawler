import logging
import os
import time
import sys
from fastapi import FastAPI, Header, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from services.services import getTaskList, getTaskDetail, generate_page_content
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


@app.post("/task/generate")
async def generate(request: GenerateRequest):
    generate_page_content(request.model_dump())
    return { "code": 0}
