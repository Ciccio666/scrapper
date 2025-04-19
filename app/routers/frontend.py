"""
Frontend routes for the web application.

This module contains routes for rendering HTML templates for the web interface.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from app.core.config import Settings, get_settings_dependency
from app.core.logging import get_logger_dependency


# Create router
router = APIRouter(tags=["Frontend"])

# Set up templates
templates = Jinja2Templates(directory="templates")

# Define user agent mapping
USER_AGENTS = {
    "chrome-windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "chrome-mac": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "mobile-android": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36",
    "mobile-iphone": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
}


@router.get(
    "/",
    response_class=HTMLResponse,
    summary="Main application page",
    description="Renders the home page with the web scraping form"
)
async def index(
    request: Request,
    settings: Settings = Depends(get_settings_dependency),
    logger = Depends(get_logger_dependency),
):
    """
    Render the main page with the web scraping form.
    
    This endpoint serves the home page of the application, where users
    can enter a URL to scrape and configure scraping options.
    
    Args:
        request: FastAPI request object
        settings: Application settings
        logger: Logger instance
        
    Returns:
        HTMLResponse: Rendered HTML template
    """
    logger.info("Rendering index page")
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "user_agents": USER_AGENTS}
    )
    

@router.get(
    "/settings",
    response_class=HTMLResponse,
    summary="Settings page",
    description="Renders the settings configuration page"
)
async def settings_page(
    request: Request,
    settings: Settings = Depends(get_settings_dependency),
    logger = Depends(get_logger_dependency),
):
    """
    Render the settings page for configuring the scraper.
    
    This page provides a web interface for viewing and updating the global
    scraper settings, including time settings, domain restrictions, and crawling parameters.
    
    Args:
        request: FastAPI request object
        settings: Application settings
        logger: Logger instance
        
    Returns:
        HTMLResponse: Rendered HTML template
    """
    logger.info("Rendering settings page")
    return templates.TemplateResponse(
        "settings.html",
        {"request": request}
    )