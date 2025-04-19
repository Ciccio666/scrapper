"""
Application configuration and settings.

This module contains all configuration settings for the application,
with defaults that can be overridden via environment variables.
"""
import os
from functools import lru_cache
from typing import Dict, List, Optional, Union, Any

from fastapi import Depends
from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings container with environment variable mapping."""
    
    # Application metadata
    APP_NAME: str = "Web Scraper API"
    APP_DESCRIPTION: str = """
    A FastAPI-based web scraping application using Selenium for dynamic content extraction
    
    ## Features
    
    * Extract content from any website with Selenium (handles JavaScript)
    * Clean text extraction with Trafilatura for better readability
    * Recursive crawling with domain restriction and depth control
    * Configurable scraping parameters via YAML/JSON
    * Special handling for chat.openai.com shared links
    
    ## Main Endpoints
    
    * `/` - Web interface for scraping
    * `/settings` - UI for configuring scraper settings
    * `/api/scrape` - Scrape with Selenium
    * `/api/scrape/trafilatura` - Scrape with Trafilatura
    * `/api/settings` - Get/update configuration
    """
    APP_VERSION: str = "1.0.0"
    OPENAPI_VERSION: str = "3.1.0"
    PRODUCTION_URL: str = "https://Scrape-it.replit.app"
    DEVELOPMENT_URL: str = "http://localhost:5000"
    OPENAPI_TAG_METADATA: List[Dict[str, Any]] = [
        {
            "name": "Scraping",
            "description": "API endpoints for web scraping operations",
        },
        {
            "name": "Settings",
            "description": "API endpoints for managing application settings",
        },
        {
            "name": "System",
            "description": "System endpoints for health checks and status monitoring",
        },
        {
            "name": "Frontend",
            "description": "Frontend web pages for the application",
        },
    ]
    
    # Server settings
    SERVER_HOST: str = "0.0.0.0"  # IP to bind to
    SERVER_PORT: int = 5000  # Port to bind to
    DEBUG: bool = bool(os.getenv("DEBUG", "True"))
    RELOAD: bool = bool(os.getenv("RELOAD", "True"))
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Scraper settings (mutable)
    PAGE_LOAD_TIMEOUT: int = 30  # Max time to wait for page load (seconds)
    DYNAMIC_CONTENT_WAIT: float = 2.0  # Time to wait for dynamic content (seconds)
    CHATGPT_MIN_WAIT: float = 5.0  # Min wait time for ChatGPT links (seconds)
    CHATGPT_MAX_WAIT: float = 8.0  # Max wait time for ChatGPT links (seconds)
    
    # Crawling settings (mutable)
    MAX_DEPTH: int = 1  # Default max crawl depth
    MAX_PAGES_PER_DOMAIN: int = 10  # Default max pages per domain
    RESTRICT_TO_DOMAINS: List[str] = []  # Domains to restrict crawling to
    FOLLOW_EXTERNAL_LINKS: bool = False  # Whether to follow links to external domains
    IGNORE_QUERY_STRINGS: bool = True  # Whether to ignore query strings in URLs
    EXCLUDE_URL_PATTERNS: List[str] = []  # URL patterns to exclude from crawling
    
    # Browser pool settings
    BROWSER_POOL_SIZE: int = 2  # Number of Chrome instances to keep in the pool
    BROWSER_MAX_IDLE_TIME: int = 300  # Maximum idle time for a browser (seconds)
    
    # Rate limiting settings
    RATE_LIMIT_STANDARD: str = "30/minute"  # Standard rate limit
    RATE_LIMIT_PREMIUM: str = "120/minute"  # Premium rate limit
    
    # Cache settings
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600  # Default TTL for cached responses (seconds)
    
    class Config:
        """Pydantic configuration for Settings."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings with caching.
    
    Returns:
        Settings: Application settings object
    """
    return Settings()


def get_settings_dependency() -> Settings:
    """
    Get application settings as a FastAPI dependency.
    
    Returns:
        Settings: Application settings object
    """
    return get_settings()