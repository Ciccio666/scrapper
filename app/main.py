# main.py
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import setup_logging
from app.core.config import get_settings
from app.routers import (
    scraping, health, status, settings, proxies,
    user_agents, frontend, extra_features
)

setup_logging()
app_settings = get_settings()

app = FastAPI(
    title="Web Scraper API",
    description="A FastAPI-based web scraping API with Selenium and Trafilatura. Extracts content, metadata and screenshots from websites with support for JavaScript, recursive crawling, and proxy configuration.",
    version="1.0.0",
    openapi_version="3.1.0",
    servers=[{"url": "https://web-scraper.replit.app", "description": "Production Server"}]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(scraping.router)
app.include_router(status.router)
app.include_router(settings.router)
app.include_router(proxies.router)
app.include_router(user_agents.router)
app.include_router(frontend.router)
app.include_router(extra_features.router)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
