from fastapi import APIRouter, Query
from app.schemas.response_models import (
    UserAgentsResponse, ProxiesResponse,
    CrawlStatusResponse, StatusResponse
)

router = APIRouter()

@router.get("/api/user_agents", response_model=UserAgentsResponse)
def get_user_agents():
    return {"agents": ["chrome-windows", "firefox-linux", "safari-mac"]}

@router.get("/api/proxies", response_model=ProxiesResponse)
def get_proxies():
    return {"proxies": [{"host": "123.45.67.89", "port": 8080}]}

@router.get("/api/crawl_status", response_model=CrawlStatusResponse)
def crawl_status(task_id: str = Query(...)):
    return {"pages_crawled": 10, "queue": 2, "depth": 3}

@router.get("/api/status", response_model=StatusResponse)
def get_status():
    return {
        "uptime": 3600.5,
        "active_sessions": 4,
        "memory_usage_mb": 142.3
    }

@router.get("/api/logs")
def get_logs(lines: int = 200):
    return "Log output would be here."
