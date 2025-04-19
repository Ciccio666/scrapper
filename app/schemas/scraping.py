"""
Pydantic schemas for the scraping API.

This module defines the data models used in the scraping API,
including request and response models for the scraping endpoints.
"""
from typing import Dict, List, Optional, Union, Any

from pydantic import BaseModel, Field, HttpUrl


class SeleniumOptions(BaseModel):
    """Configuration options for Selenium-based scraping."""
    headless: bool = True
    disable_images: bool = True
    wait_time: float = 2.0


class CrawlOptions(BaseModel):
    """Options for recursive crawling functionality."""
    enabled: bool = False
    max_depth: int = Field(
        default=1, 
        description="Maximum depth for recursive crawling (1 = current page only)"
    )
    max_pages: int = Field(
        default=10, 
        description="Maximum number of pages to crawl in total"
    )
    follow_external_links: bool = Field(
        default=False, 
        description="Whether to follow links to external domains"
    )
    restrict_to_domain: bool = Field(
        default=True, 
        description="Whether to restrict crawling to the original domain"
    )
    ignore_query_strings: bool = Field(
        default=True, 
        description="Whether to ignore query strings when determining if a URL has been visited"
    )


class ScrapeRequest(BaseModel):
    """Request model for scraping endpoints."""
    url: str
    user_agent: str = "chrome-windows"
    selenium_options: Optional[SeleniumOptions] = None
    crawl_options: Optional[CrawlOptions] = None


class UrlInfo(BaseModel):
    """Information about the URL that was scraped."""
    original: str
    final: str
    was_redirected: bool


class ElementCounts(BaseModel):
    """Counts of various HTML elements on the page."""
    links: int
    images: int
    forms: int
    scripts: int
    total: int


class CrawlingData(BaseModel):
    """Data about the crawling operation."""
    enabled: bool
    pages_crawled: int
    max_depth: int
    crawled_urls: List[str] = []


class ScrapingMetadata(BaseModel):
    """Metadata about the scraping operation."""
    content_length: int
    scrape_time_seconds: float
    has_title: bool
    has_description: bool
    user_agent: str
    is_dynamic: bool
    elements: ElementCounts
    crawling: Optional[CrawlingData] = None


class ScrapedData(BaseModel):
    """Data extracted from a website."""
    title: str
    description: str
    content: str
    url: UrlInfo
    metadata: ScrapingMetadata


class SuccessResponse(BaseModel):
    """Success response model."""
    status: str = "success"
    data: ScrapedData


class ErrorResponse(BaseModel):
    """Error response model."""
    status: str = "error"
    error: str
    details: Optional[str] = None

from pydantic import BaseModel

class ScreenshotResponse(BaseModel):
    status: str
    image_base64: str
    width: int
    height: int

from pydantic import BaseModel

class ScreenshotResponse(BaseModel):
    status: str
    image_base64: str
    width: int
    height: int