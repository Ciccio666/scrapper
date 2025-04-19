from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str = "ok"

class ScreenshotResponse(BaseModel):
    status: str
    image_base64: str
    width: int
    height: int

class SettingsResponse(BaseModel):
    settings: dict

class CrawlStatusResponse(BaseModel):
    pages_crawled: int
    queue: int
    depth: int

class LogEntriesResponse(BaseModel):
    entries: list[str]

class UserAgentListResponse(BaseModel):
    agents: list[str]

class ProxyListResponse(BaseModel):
    proxies: list[dict]