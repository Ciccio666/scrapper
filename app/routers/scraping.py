# scraping.py
from fastapi import APIRouter, Request, Query
from app.schemas.scraping import ScrapeRequest
from app.schemas.response_models import SuccessResponse, ErrorResponse, ScreenshotResponse
from app.services.scraping_service import (
    scrape_with_selenium,
    scrape_with_trafilatura,
    extract_by_selector,
    render_js_content,
    extract_metadata,
    extract_links,
    take_screenshot
)

router = APIRouter(prefix="/api", tags=["scraping"])


@router.post("/scrape", response_model=SuccessResponse | ErrorResponse)
async def scrape_web_content(request: ScrapeRequest, token: str = Query(None)):
    return await scrape_with_selenium(request)


@router.post("/scrape/trafilatura", response_model=SuccessResponse | ErrorResponse)
async def scrape_with_trafilatura_endpoint(request: ScrapeRequest, token: str = Query(None)):
    return await scrape_with_trafilatura(request)


@router.post("/extract", response_model=SuccessResponse | ErrorResponse)
async def extract_by_selector_endpoint(request: ScrapeRequest, token: str = Query(None)):
    return await extract_by_selector(request)


@router.post("/render", response_model=SuccessResponse | ErrorResponse)
async def render_javascript_content(request: ScrapeRequest, token: str = Query(None)):
    return await render_js_content(request)


@router.post("/metadata", response_model=SuccessResponse | ErrorResponse)
async def extract_page_metadata(request: ScrapeRequest, token: str = Query(None)):
    return await extract_metadata(request)


@router.post("/links", response_model=SuccessResponse | ErrorResponse)
async def extract_page_links(request: ScrapeRequest, token: str = Query(None)):
    return await extract_links(request)


@router.post("/screenshot", response_model=ScreenshotResponse)
async def take_screenshot_endpoint(request: ScrapeRequest, token: str = Query(None)):
    return await take_screenshot(request)
