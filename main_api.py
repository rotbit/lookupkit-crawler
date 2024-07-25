import logging
import os
import time
from typing import List, Optional

from supabase import create_client, Client
from dotenv import load_dotenv
from fastapi import FastAPI, Header, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from website_crawler import WebsitCrawler
from cachetools import TTLCache
from httpx import Timeout

task_cache = TTLCache(maxsize=10240, ttl=3600)

from entity import URLRequest, TaskListRequest, GenerateRequest, TaskDetailRequest

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

website_crawler = WebsitCrawler()
load_dotenv()
system_auth_secret = os.getenv('AUTH_SECRET')

# 从supabase获取数据
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
    
# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.post('/task/detail')
async def task_detail(request: TaskDetailRequest, authorization: Optional[str] = Header(None)):
    id = request.id
    if system_auth_secret:
        # 配置了非空的auth_secret，才验证
        validate_authorization(authorization)
    print(f'GetRequest :{request}')
    
    supabase: Client = create_client(url, key)
    submit = supabase.table('submit').select('*').eq('id', id).execute()

    taskDetail = supabase.table('task_detail').select('*').eq('submit_id', id).execute()
    
    submitData = {}
    taskDetailData = {}
    if len(submit.data) > 0:
        submitData = submit.data[0]
    if len(taskDetail.data) > 0:
        taskDetailData = taskDetail.data[0]
    
    response = {
        'code': 200,
        'msg': 'success',
        'data': {
            "id": submitData.get('id', ''),
            "url": submitData.get('url', ''),
            "name": submitData.get('name', ''),
            "model": taskDetailData.get('model', ''),
            "keyword": taskDetailData.get('keyword', ''),
            "keyword_density": taskDetailData.get('keyword_density', ''),
            "language": taskDetailData.get('language', ''),
            "reference_content": taskDetailData.get('reference_content', ''),
        }
    }
    return response

@app.post('/task/list')
async def list_tasks(request: TaskListRequest, authorization: Optional[str] = Header(None)):
    if system_auth_secret:
        # 配置了非空的auth_secret，才验证
        validate_authorization(authorization)

    supabase: Client = create_client(url, key)
    data = supabase.table('submit').select('*').execute()

    response = {
        'code': 200,
        'msg': 'success',
        'data': data.data
    }
    return response

@app.post('/site/crawl')
async def scrape(request: URLRequest, authorization: Optional[str] = Header(None)):
    url = request.url
    tags = request.tags  # tag数组
    languages = request.languages  # 需要翻译的多语言列表
    logger.info(f'crawl url:{url}, tags:{tags}, languages:{languages}')
    if system_auth_secret:
        # 配置了非空的auth_secret，才验证
        validate_authorization(authorization)

    result = await website_crawler.scrape_website(url.strip(), tags, languages)

    # 若result为None,则 code="10001"，msg="处理异常，请稍后重试"
    code = 200
    msg = 'success'
    if result is None:
        code = 10001
        msg = 'fail'

    # 将数据映射到 'data' 键下
    response = {
        'code': code,
        'msg': msg,
        'data': result
    }
    return response

@app.post('/task/get_step')
async def get_step(request: URLRequest, authorization: Optional[str] = Header(None)):
    url = request.url
    tags = request.tags

@app.post('/task/generate')
async def generate(background_tasks :BackgroundTasks,request: GenerateRequest, authorization: Optional[str] = Header(None)):
    if system_auth_secret:
        # 配置了非空的auth_secret，才验证
        validate_authorization(authorization)
    # 将任务信息写入到supabase
    supabase: Client = create_client(url, key)
    supabase.table('task_detail').insert(
        [{ 'submit_id': request.task_id, 
            'references_url': request.reference_url,
            'keyword': request.keyword,
            'keyword_density': request.keyword_density,
            'language': request.language,
            'model': request.model,
        }]).execute()

    # 直接发起异步请求:使用background_tasks后台运行
    background_tasks.add_task(generate_task, request)
    
    # 设置任务状态
    task_cache[request.task_id] = {"step": "start", "start_time": time.time()}
    # 若result为None,则 code="10001"，msg="处理异常，请稍后重试"
    code = 200
    msg = 'success'
    response = {
        'code': code,
        'msg': msg,
        'data': {
            'task_id': request.task_id
        }
    }
    return response

def generate_task(request :GenerateRequest):
    # 爬虫处理封装为一个异步任务
    url = request.url
    languages = request.language
    #website_crawler.scrape_website(url.strip(), [], languages)
   
def get_task_cache_key(task_id) -> str:
    return f"task_{task_id}"
     
def validate_authorization(authorization):
    if not authorization:
        raise HTTPException(status_code=400, detail="Missing Authorization header")
    if 'Bearer ' + system_auth_secret != authorization:
        raise HTTPException(status_code=401, detail="Authorization is error")
    


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")
