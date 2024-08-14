from typing import List, Optional

from pydantic import BaseModel

class AddTaskRequest(BaseModel):
    name: str
    url: str
    status:str
    
class PublishTaskRequest(BaseModel):
    task_id: str
    language: str
    model:str
class GenerateRequest(BaseModel):
    model: str
    keyword: str
    keyword_density: str
    language: str
    reference_content: Optional[str] = None
    task_url: str
    name: str
    task_id: str
    feature_prompt:str
    introd_prompt:str
    
class TaskResultRequest(BaseModel):
    task_id: str
    language: str
    
class DeleteTaskRequest(BaseModel):
    task_id: int
    