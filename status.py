from fastapi import APIRouter, Query
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
