import os

files_to_write = {
    "response_models.py": """from pydantic import BaseModel
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
""",

    "status.py": """from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from app.core.logging import logger
from app.core.config import get_settings
from app.core.crawler import get_crawl_status
from app.response_models import CrawlStatusResponse, LogTailResponse

router = APIRouter()

@router.get("/api/status", response_model=dict)
def get_status():
    return {"status": "running"}

@router.get("/api/crawl_status", response_model=CrawlStatusResponse)
def crawl_status(task_id: str = Query(...)):
    return get_crawl_status(task_id)

@router.get("/api/logs", response_class=PlainTextResponse)
def get_logs(lines: int = 200):
    try:
        with open("scraper.log", "r") as f:
            all_lines = f.readlines()
            return "".join(all_lines[-lines:])
    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        return PlainTextResponse("Error reading logs", status_code=500)
""",

    "user_agents.py": """from fastapi import APIRouter
from app.response_models import UserAgentsResponse

router = APIRouter()

VALID_USER_AGENTS = [
    "chrome-windows", "firefox-linux", "safari-mac", "edge-windows"
]

@router.get("/api/user_agents", response_model=UserAgentsResponse)
def list_user_agents():
    return {"agents": VALID_USER_AGENTS}
""",

    "proxies.py": """from fastapi import APIRouter
from app.response_models import ProxyListResponse

router = APIRouter()

PROXIES = [
    {"host": "proxy1.com", "port": 8000, "country": "US"},
    {"host": "proxy2.com", "port": 8080, "country": "UK"},
]

@router.get("/api/proxies", response_model=ProxyListResponse)
def list_proxies():
    return {"proxies": PROXIES}

@router.post("/api/proxies")
def add_proxy(proxy: dict):
    PROXIES.append(proxy)
    return {"status": "added", "proxy": proxy}
""",
}

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote: {path}")

def main():
    for filename, content in files_to_write.items():
        write_file(filename, content)

    print("\nUpdate complete. Only updated and new files were written.")
    print("Run your FastAPI app and recheck OpenAPI if needed.")

if __name__ == "__main__":
    main()
