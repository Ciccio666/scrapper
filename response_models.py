from pydantic import BaseModel
from typing import Optional, List

class HealthResponse(BaseModel):
    status: str = "ok"

class ScreenshotResponse(BaseModel):
    status: str
    image_base64: str
    width: int
    height: int

class SettingsResponse(BaseModel):
    status: str = "success"
    settings: dict

class CrawlStatusResponse(BaseModel):
    task_id: str
    pages_crawled: int
    queue: int
    depth: int

class UserAgentsResponse(BaseModel):
    agents: List[str]

class ProxyListResponse(BaseModel):
    proxies: List[dict]

class LogTailResponse(BaseModel):
    entries: List[str]
