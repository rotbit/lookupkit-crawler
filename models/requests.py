from typing import List, Optional

from pydantic import BaseModel

class AddTaskRequest(BaseModel):
    name: str
    web_url: str
    
class CrawlingRequest(BaseModel):
    url: str
    
class PublishTaskRequest(BaseModel):
    task_id: str
    language: str
    model:str
    introduction:str
    feature:str
class GenerateRequest(BaseModel):
    model: str
    keyword: str
    density: int
    language: str
    name: str
    url:str
    prompt: str
    tags: str
    section_type: str

class RewriteRequest(BaseModel):
    model: str
    prompt: str
    content: str
    url: str
    section_type: str    

class TaskResultRequest(BaseModel):
    task_id: str
    language: str
    
class DeleteTaskRequest(BaseModel):
    task_id: int
    
class UserLoginRequest(BaseModel):
    username: str
    password: str
    
class TranslateRequest(BaseModel):
    text: str
    model: str
    language: str
    field: str
    url: str
    
class SaveDataRequest(BaseModel):
    model: str
    keyword: str
    density: int
    language: str
    name: str
    web_url:str
    tags: str
    title: str
    desc: str
    feature: str
    introd: str