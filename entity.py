from typing import List, Optional

from pydantic import BaseModel

class URLRequest(BaseModel):
    url: str
    tags: Optional[List[str]] = None
    languages: Optional[List[str]] = None

class TaskListRequest(BaseModel):
    optionals: Optional[str] = None

class AsyncURLRequest(URLRequest):
    callback_url: str
    key: str

class TaskDetailRequest(BaseModel):
    id: str
    
class GenerateRequest(BaseModel):
    model: str
    keyword: Optional[str] = None
    keyword_density: str
    language: str
    reference_url: Optional[str] = None
    url: str
    name: str
    task_id: str
    