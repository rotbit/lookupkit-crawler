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

@app.get("/task/list")
async def task_list(token: str = Depends(verify_token)):
    # 异步更新数据
    Process(target=start_sync_scheduler_once).start()
    
    results = getTaskList()
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
    print(token)
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
async def generate_introd(request: GenerateRequest,token: str = Depends(verify_token)):
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
async def generate_introd(request: GenerateRequest,token: str = Depends(verify_token)):
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
async def delete_task(request: DeleteTaskRequest,token: str = Depends(verify_token)):
    client = GetMongoClient("submit")
    client.delete_one({"id": request.task_id})
    
    return {"code": 0, "message": "删除成功"}

@app.post("/task/add_task")
async def add_task(request: AddTaskRequest,token: str = Depends(verify_token)):
    client = GetMongoClient("submit")
    submit_data = request.model_dump()
    submit_data['id'] = int(time.time())
    submit_data['email'] = ''
    client.insert_one(submit_data)
    return {"code": 0, "task_id": submit_data['id'] }

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
    token = jwt.encode({"username": request.username, "exp": time.time() + 3600}, secret_key, algorithm="HS256")
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
