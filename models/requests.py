from typing import List, Optional

from pydantic import BaseModel

class AddTaskRequest(BaseModel):
    task_id: int
    name: str
    url: str
    
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
    