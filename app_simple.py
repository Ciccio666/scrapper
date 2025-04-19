"""
Simplified FastAPI web scraper application.
Provides API endpoints for web scraping with Selenium and Trafilatura.
"""

import os
import time
import random
import logging
import base64
import io
import asyncio
from typing import Dict, Any, Optional, List, Union, Tuple
from urllib.parse import urlparse, urljoin

# FastAPI imports
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException

# HTML parsing imports
import trafilatura
from bs4 import BeautifulSoup
import lxml.html
from lxml import etree

# Browser automation import
import pyppeteer
from pyppeteer import launch

# Import web scraping utilities
from crawler import WebCrawler

# YAML parser for settings
import yaml

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Function to create a Chrome extension for proxy authentication
def create_proxy_auth_extension(proxy_host, proxy_port, proxy_username, proxy_password):
    """
    Creates a Chrome extension to authenticate with a proxy that requires username and password.
    
    Args:
        proxy_host: The proxy hostname or IP
        proxy_port: The proxy port
        proxy_username: Username for proxy authentication
        proxy_password: Password for proxy authentication
        
    Returns:
        Path to the generated extension file
    """
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "webRequest",
            "webRequestBlocking",
            "<all_urls>"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """
    
    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: parseInt(%s)
            },
            bypassList: ["localhost"]
        }
    };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        {urls: ["<all_urls>"]},
        ['blocking']
    );
    """ % (proxy_host, proxy_port, proxy_username, proxy_password)
    
    # Create a temporary directory for the extension
    import tempfile
    import zipfile
    import os
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write the manifest.json file
        with open(os.path.join(temp_dir, "manifest.json"), "w") as f:
            f.write(manifest_json)
        
        # Write the background.js file
        with open(os.path.join(temp_dir, "background.js"), "w") as f:
            f.write(background_js)
        
        # Create a .zip file (Chrome accepts zipped extensions)
        temp_extension_path = os.path.join(temp_dir, "proxy_auth_extension.zip")
        
        with zipfile.ZipFile(temp_extension_path, 'w') as zipf:
            zipf.write(os.path.join(temp_dir, "manifest.json"), "manifest.json")
            zipf.write(os.path.join(temp_dir, "background.js"), "background.js")
        
        return temp_extension_path

# Token management with persistent storage
import json
import os

API_TOKEN = "scraper-token-12345"  # Replace with a secure token in production
TOKEN_FILE = "validated_tokens.json"
VALIDATED_TOKENS = set()  # In-memory cache of validated tokens

# Load existing validated tokens from file if it exists
def load_validated_tokens():
    global VALIDATED_TOKENS
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as file:
                tokens = json.load(file)
                VALIDATED_TOKENS = set(tokens)
                logger.info(f"Loaded {len(VALIDATED_TOKENS)} validated tokens from storage")
    except Exception as e:
        logger.error(f"Error loading validated tokens: {str(e)}")
        VALIDATED_TOKENS = set()

# Save validated tokens to persistent storage
def save_validated_tokens():
    try:
        with open(TOKEN_FILE, 'w') as file:
            json.dump(list(VALIDATED_TOKENS), file)
        logger.debug("Saved validated tokens to persistent storage")
    except Exception as e:
        logger.error(f"Error saving validated tokens: {str(e)}")

def verify_token(token: str):
    """Verify token and store it if valid to maintain session persistence across restarts"""
    # First check in-memory cache
    if token in VALIDATED_TOKENS:
        return True
    
    # Validate against the master token
    is_valid = token == API_TOKEN
    if is_valid:
        VALIDATED_TOKENS.add(token)
        # Save to persistent storage immediately
        save_validated_tokens()
        logger.info(f"New token validated and saved to persistent storage")
    
    return is_valid

# Initialize the token storage on startup
load_validated_tokens()

# Initialize FastAPI app
app = FastAPI(
    title="Web Scraper API",
    description="A FastAPI-based web scraping API with Selenium and Trafilatura. Extracts content, metadata and screenshots from websites with support for JavaScript, recursive crawling, and proxy configuration.",
    version="1.0.0",
    servers=[
        {"url": "https://web-scraper.replit.app", "description": "Production Server"}
    ],
)

# App state management
class AppState:
    def __init__(self):
        self.settings = None  # Will hold our ScraperSettings object
        
app.state.store = AppState()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up templates
templates = Jinja2Templates(directory="templates")

# Mount static files if the directory exists
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Define common user agent strings
USER_AGENTS = {
    "chrome-windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "chrome-mac": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "mobile-android": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36",
    "mobile-iphone": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
}

# Define request models
class ProxyConfig(BaseModel):
    """Configuration for proxy support."""
    enabled: bool = False
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    
class SeleniumOptions(BaseModel):
    headless: bool = True
    disable_images: bool = True
    wait_time: float = 2.0
    proxy_config: Optional[ProxyConfig] = None

class CrawlOptions(BaseModel):
    """Options for recursive crawling functionality."""
    enabled: bool = False
    max_depth: int = Field(default=1, description="Maximum depth for recursive crawling (1 = current page only)")
    max_pages: int = Field(default=10, description="Maximum number of pages to crawl in total")
    follow_external_links: bool = Field(default=False, description="Whether to follow links to external domains")
    restrict_to_domain: bool = Field(default=True, description="Whether to restrict crawling to the original domain")
    ignore_query_strings: bool = Field(default=True, description="Whether to ignore query strings when determining if a URL has been visited")

class SelectorOptions(BaseModel):
    """Options for selector-based extraction."""
    selector: str = Field(..., description="CSS selector to extract content")
    attribute: Optional[str] = Field(None, description="Attribute to extract (if None, extracts text content)")
    multiple: bool = Field(default=True, description="Whether to extract multiple elements or just the first match")

class RenderOptions(BaseModel):
    """Options for JavaScript rendering."""
    wait_time: float = Field(default=5.0, description="Time to wait for JavaScript execution (in seconds)")
    wait_for_selector: Optional[str] = Field(None, description="Wait for a specific selector to appear")
    wait_for_navigation: bool = Field(default=True, description="Wait for navigation to complete")
    full_page: bool = Field(default=True, description="Whether to capture the full page or just the viewport")

class ScreenshotOptions(BaseModel):
    """Options for screenshot capture."""
    full_page: bool = Field(default=True, description="Whether to capture the full page or just the viewport")
    width: int = Field(default=1280, description="Viewport width")
    height: int = Field(default=800, description="Viewport height")
    format: str = Field(default="png", description="Image format (png or jpeg)")
    quality: Optional[int] = Field(None, description="Image quality (0-100, for jpeg only)")

class ScrapeRequest(BaseModel):
    url: str
    user_agent: str = "chrome-windows"
    selenium_options: Optional[SeleniumOptions] = None
    crawl_options: Optional[CrawlOptions] = None
    selector_options: Optional[SelectorOptions] = None
    render_options: Optional[RenderOptions] = None
    screenshot_options: Optional[ScreenshotOptions] = None

# Define response models
class UrlInfo(BaseModel):
    original: str
    final: str = ""
    was_redirected: bool = False

class ElementCounts(BaseModel):
    links: int = 0
    images: int = 0 
    forms: int = 0
    scripts: int = 0
    total: int = 0

class CrawlingData(BaseModel):
    enabled: bool = False
    pages_crawled: int = 0
    max_depth: int = 1
    crawled_urls: List[str] = []

class ScrapingMetadata(BaseModel):
    content_length: int = 0
    scrape_time_seconds: float = 0.0
    has_title: bool = False
    has_description: bool = False
    user_agent: str = ""
    is_dynamic: bool = False
    elements: Optional[ElementCounts] = None
    crawling: Optional[CrawlingData] = None

class ScrapedData(BaseModel):
    title: str = ""
    description: str = ""
    content: str = ""
    url: UrlInfo
    metadata: ScrapingMetadata

class SuccessResponse(BaseModel):
    status: str = "success"
    data: ScrapedData

class ErrorResponse(BaseModel):
    status: str = "error"
    error: str
    details: Optional[str] = None


# Health check route for deployment
@app.get("/health")
async def health_check():
    """
    Simple health check endpoint that returns a 200 OK status.
    Used by deployment systems to verify the application is running.
    """
    return {"status": "ok"}

# Frontend Routes
@app.get("/")
async def index(request: Request):
    """
    Render the main page with the web scraping form.
    """
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "user_agents": USER_AGENTS}
    )

@app.get("/settings")
async def settings_page(request: Request):
    """
    Render the settings page for configuring the scraper.
    
    This page provides a web interface for viewing and updating the global
    scraper settings, including time settings, domain restrictions, and crawling parameters.
    """
    return templates.TemplateResponse(
        "settings.html", 
        {"request": request, "user_agents": USER_AGENTS}
    )

@app.post("/api/scrape", response_model=Union[SuccessResponse, ErrorResponse])
async def scrape_web_content(scrape_request: ScrapeRequest, token: str = None):
    """
    Scrapes web content using Selenium and performs recursive crawling if enabled. 
    Extracts content from URLs with headless Chrome browser, with special handling for ChatGPT shared links.
    """
    if token is not None and not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    driver = None
    try:
        # Extract request data
        url = scrape_request.url
        user_agent_key = scrape_request.user_agent
        
        # Safely get options with default fallbacks
        selenium_options = scrape_request.selenium_options or SeleniumOptions()
        headless = selenium_options.headless
        disable_images = selenium_options.disable_images
        wait_time = selenium_options.wait_time
        
        # Make sure crawl_options is initialized
        crawl_options = scrape_request.crawl_options or CrawlOptions()
        
        # Validate input
        if not url:
            raise HTTPException(status_code=400, detail="Missing URL")
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Get the actual user agent string
        user_agent = USER_AGENTS.get(user_agent_key, USER_AGENTS["chrome-windows"])
        
        logger.debug(f"Starting scrape of URL: {url} with user agent: {user_agent_key}")
        
        # Configure Chrome options
        options = Options()
        # Always use headless mode in Replit
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-setuid-sandbox")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument(f"user-agent={user_agent}")
        
        # Configure proxy if enabled
        proxy_config = selenium_options.proxy_config
        if proxy_config and proxy_config.enabled and proxy_config.host and proxy_config.port:
            proxy_string = f"{proxy_config.host}:{proxy_config.port}"
            
            # Add authentication if provided
            if proxy_config.username and proxy_config.password:
                auth_plugin_path = create_proxy_auth_extension(
                    proxy_config.host,
                    proxy_config.port,
                    proxy_config.username,
                    proxy_config.password
                )
                options.add_extension(auth_plugin_path)
                logger.debug(f"Using authenticated proxy: {proxy_config.host}:{proxy_config.port}")
            else:
                options.add_argument(f'--proxy-server={proxy_string}')
                logger.debug(f"Using proxy: {proxy_string}")
                
            # Add country info for logging purposes
            if proxy_config.country:
                logger.info(f"Using proxy from country: {proxy_config.country}")
        
        if disable_images:
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)
        
        # Start browser with appropriate configuration
        try:
            driver = webdriver.Chrome(options=options)
            logger.debug("WebDriver created successfully")
        except Exception as e:
            logger.error(f"Error creating WebDriver: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to initialize WebDriver: {str(e)}")
            
        # Use settings for timeouts
        driver.set_page_load_timeout(30)
        
        start_time = time.time()
        
        # Load initial URL
        logger.debug(f"Loading URL: {url}")
        driver.get(url)
        
        # Handle chat.openai.com/share/... links
        was_redirected = False
        if "chat.openai.com/share/" in url:
            was_redirected = True
            chat_wait_time = random.uniform(5.0, 8.0)
            logger.debug(f"[ChatGPT redirect] Waiting {chat_wait_time:.2f}s for redirect...")
            time.sleep(chat_wait_time)
            driver.get(driver.current_url)
        
        # Wait for dynamic content to load
        logger.debug(f"Waiting {wait_time}s for dynamic content to load...")
        time.sleep(wait_time)
        
        # Extract content
        title = driver.title
        description = ""
        content = driver.find_element(By.TAG_NAME, "body").text
        
        # Try to extract description meta tag
        try:
            description = driver.find_element(By.XPATH, "//meta[@name='description']").get_attribute("content")
        except NoSuchElementException:
            try:
                description = driver.find_element(By.XPATH, "//meta[@property='og:description']").get_attribute("content")
            except NoSuchElementException:
                logger.debug("No description meta tag found")
        
        # Count various page elements for metadata
        links_count = len(driver.find_elements(By.TAG_NAME, "a"))
        images_count = len(driver.find_elements(By.TAG_NAME, "img"))
        forms_count = len(driver.find_elements(By.TAG_NAME, "form"))
        scripts_count = len(driver.find_elements(By.TAG_NAME, "script"))
        dynamic_elements_count = len(driver.find_elements(By.XPATH, "//*"))
        
        # Check if crawling is enabled
        crawled_pages_data = []
        crawled_urls = []
        is_crawling_enabled = crawl_options and crawl_options.enabled
        
        if is_crawling_enabled:
            logger.info(f"Crawling enabled. Max depth: {crawl_options.max_depth}, Max pages: {crawl_options.max_pages}")
            
            # Create a crawler instance
            crawler_settings = {
                "max_depth": crawl_options.max_depth,
                "max_pages_per_domain": crawl_options.max_pages,
                "follow_external_links": crawl_options.follow_external_links,
                "restrict_to_domains": [urlparse(url).netloc] if crawl_options.restrict_to_domain else [],
                "ignore_query_strings": crawl_options.ignore_query_strings,
                "exclude_url_patterns": [],
                "dynamic_content_wait": wait_time,
                "chatgpt_min_wait": 5.0,
                "chatgpt_max_wait": 8.0
            }
            
            crawler = WebCrawler(driver, crawler_settings)
            crawled_pages_data = crawler.crawl(url)
            
            # Extract just the URLs for metadata
            crawled_urls = [page["url"] for page in crawled_pages_data if "url" in page]
            
            # Add crawling data to content
            if crawled_pages_data:
                content += "\n\n--- CRAWLED PAGES ---\n\n"
                for idx, page in enumerate(crawled_pages_data, 1):
                    content += f"[Page {idx}] {page.get('title', 'No Title')} - {page.get('url', 'No URL')}\n"
                    content += f"{page.get('content', 'No content extracted')[:500]}...\n\n"
        
        # Prepare result
        scrape_time = time.time() - start_time
        
        return {
            "status": "success",
            "data": {
                "title": title,
                "description": description,
                "content": content,
                "url": {
                    "original": url,
                    "final": driver.current_url,
                    "was_redirected": was_redirected or (url != driver.current_url)
                },
                "metadata": {
                    "content_length": len(content),
                    "scrape_time_seconds": scrape_time,
                    "has_title": bool(title),
                    "has_description": bool(description),
                    "user_agent": user_agent_key,
                    "is_dynamic": True,
                    "elements": {
                        "links": links_count,
                        "images": images_count,
                        "forms": forms_count,
                        "scripts": scripts_count,
                        "total": dynamic_elements_count
                    },
                    "crawling": {
                        "enabled": is_crawling_enabled,
                        "pages_crawled": len(crawled_pages_data),
                        "max_depth": crawl_options.max_depth if is_crawling_enabled else 1,
                        "crawled_urls": crawled_urls
                    } if is_crawling_enabled else None
                }
            }
        }
        
    except TimeoutException as e:
        logger.error(f"Timeout error: {str(e)}")
        return JSONResponse(
            status_code=504,
            content={"status": "error", "error": "Request timeout", "details": str(e)}
        )
    except WebDriverException as e:
        logger.error(f"WebDriver error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "Browser automation error", "details": str(e)}
        )
    except Exception as e:
        logger.error(f"General error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "Internal server error", "details": str(e)}
        )
    finally:
        # Close the browser if it's still open
        if driver:
            try:
                driver.quit()
            except:
                pass


@app.post("/api/scrape/trafilatura", response_model=Union[SuccessResponse, ErrorResponse])
async def scrape_with_trafilatura_endpoint(scrape_request: ScrapeRequest, token: str = None):
    """
    Extracts clean text from websites using Trafilatura. Optimized for articles, blog posts, and news content with cleaner results than Selenium-based extraction.
    """
    if token is not None and not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        # Extract request data
        url = scrape_request.url
        user_agent_key = scrape_request.user_agent
        
        # Validate input
        if not url:
            raise HTTPException(status_code=400, detail="Missing URL")
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        logger.debug(f"Starting Trafilatura scrape of URL: {url}")
        
        start_time = time.time()
        
        # Use web_scraper.py's function to scrape with Trafilatura
        from web_scraper import scrape_with_trafilatura
        result = scrape_with_trafilatura(url)
        
        # Check for errors
        if result.get("status") == "error":
            return JSONResponse(
                status_code=500,
                content=result
            )
        
        # Prepare result
        scrape_time = time.time() - start_time
        
        # Extract data from the result
        content = result.get("data", {}).get("content", "")
        title = result.get("data", {}).get("title", "")
        description = result.get("data", {}).get("description", "")
        
        return {
            "status": "success",
            "data": {
                "title": title,
                "description": description,
                "content": content,
                "url": {
                    "original": url,
                    "final": url,
                    "was_redirected": False
                },
                "metadata": {
                    "content_length": len(content),
                    "scrape_time_seconds": scrape_time,
                    "has_title": bool(title),
                    "has_description": bool(description),
                    "user_agent": user_agent_key,
                    "is_dynamic": False,
                    "elements": {
                        "links": 0,
                        "images": 0,
                        "forms": 0,
                        "scripts": 0,
                        "total": 0
                    },
                    "crawling": None
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error with Trafilatura scraping: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "Scraping error", "details": str(e)}
        )


@app.post("/api/extract", response_model=Union[SuccessResponse, ErrorResponse])
async def extract_by_selector(scrape_request: ScrapeRequest, token: str = None):
    """
    Extract content from a webpage using CSS selectors. Retrieve specific elements or attributes with precise targeting.
    """
    if token is not None and not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    driver = None
    try:
        # Extract request data
        url = scrape_request.url
        user_agent_key = scrape_request.user_agent
        
        # Validate input
        if not url:
            raise HTTPException(status_code=400, detail="Missing URL")
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Get selector options or use defaults
        selector_options = scrape_request.selector_options
        if not selector_options:
            raise HTTPException(status_code=400, detail="Missing selector options")
        
        # Get the actual user agent string
        user_agent = USER_AGENTS.get(user_agent_key, USER_AGENTS["chrome-windows"])
        
        logger.debug(f"Starting selector extraction from URL: {url} with selector: {selector_options.selector}")
        
        start_time = time.time()
        
        # Configure Chrome options
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"user-agent={user_agent}")
        
        # Configure proxy if provided
        if scrape_request.selenium_options and scrape_request.selenium_options.proxy_config:
            proxy_config = scrape_request.selenium_options.proxy_config
            if proxy_config.enabled and proxy_config.host and proxy_config.port:
                proxy_string = f"{proxy_config.host}:{proxy_config.port}"
                
                # Add authentication if provided
                if proxy_config.username and proxy_config.password:
                    auth_plugin_path = create_proxy_auth_extension(
                        proxy_config.host,
                        proxy_config.port,
                        proxy_config.username,
                        proxy_config.password
                    )
                    options.add_extension(auth_plugin_path)
                    logger.debug(f"Using authenticated proxy for extraction: {proxy_config.host}:{proxy_config.port}")
                else:
                    options.add_argument(f'--proxy-server={proxy_string}')
                    logger.debug(f"Using proxy for extraction: {proxy_string}")
                
                # Add country info for logging
                if proxy_config.country:
                    logger.info(f"Using proxy from country: {proxy_config.country}")
        
        # Start browser
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        
        # Load URL
        driver.get(url)
        
        # Wait a bit for content to load
        time.sleep(2)
        
        # Extract content based on selector
        results = []
        elements = driver.find_elements(By.CSS_SELECTOR, selector_options.selector)
        
        if not elements:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "error": "No elements found matching the selector", "details": f"Selector: {selector_options.selector}"}
            )
        
        # Extract text or attribute from elements
        if selector_options.multiple:
            if selector_options.attribute:
                results = [el.get_attribute(selector_options.attribute) for el in elements]
            else:
                results = [el.text for el in elements]
        else:
            if selector_options.attribute:
                results = elements[0].get_attribute(selector_options.attribute)
            else:
                results = elements[0].text
        
        # Prepare result
        content = str(results)
        title = driver.title
        description = ""
        
        # Try to extract description meta tag
        try:
            description = driver.find_element(By.XPATH, "//meta[@name='description']").get_attribute("content")
        except NoSuchElementException:
            try:
                description = driver.find_element(By.XPATH, "//meta[@property='og:description']").get_attribute("content")
            except NoSuchElementException:
                logger.debug("No description meta tag found")
        
        # Prepare result
        scrape_time = time.time() - start_time
        
        return {
            "status": "success",
            "data": {
                "title": title,
                "description": description,
                "content": content,
                "url": {
                    "original": url,
                    "final": driver.current_url,
                    "was_redirected": url != driver.current_url
                },
                "metadata": {
                    "content_length": len(content),
                    "scrape_time_seconds": scrape_time,
                    "has_title": bool(title),
                    "has_description": bool(description),
                    "user_agent": user_agent_key,
                    "is_dynamic": True,
                    "elements": {
                        "links": 0,
                        "images": 0,
                        "forms": 0,
                        "scripts": 0,
                        "total": len(elements)
                    },
                    "crawling": None
                }
            }
        }
    
    except Exception as e:
        logger.error(f"Error with selector extraction: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "Extraction error", "details": str(e)}
        )
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


@app.post("/api/render", response_model=Union[SuccessResponse, ErrorResponse])
async def render_javascript_content(scrape_request: ScrapeRequest, token: str = None):
    """Render JS for SPAs and return complete HTML with configurable wait times."""
    if token is not None and not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    browser = None
    try:
        # Extract request data
        url = scrape_request.url
        user_agent_key = scrape_request.user_agent
        
        # Validate input
        if not url:
            raise HTTPException(status_code=400, detail="Missing URL")
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Get render options or use defaults
        render_options = scrape_request.render_options or RenderOptions()
        
        # Get the actual user agent string
        user_agent = USER_AGENTS.get(user_agent_key, USER_AGENTS["chrome-windows"])
        
        logger.debug(f"Starting JavaScript rendering of URL: {url}")
        
        start_time = time.time()
        
        # Configure launch options
        launch_options = {
            'headless': True,
            'args': ['--no-sandbox', '--disable-dev-shm-usage'],
            'ignoreHTTPSErrors': True
        }
        
        # Configure proxy if provided
        if scrape_request.selenium_options and scrape_request.selenium_options.proxy_config:
            proxy_config = scrape_request.selenium_options.proxy_config
            if proxy_config.enabled and proxy_config.host and proxy_config.port:
                proxy_string = f"{proxy_config.host}:{proxy_config.port}"
                
                # Add proxy to launch arguments
                if not '--proxy-server=' in ' '.join(launch_options.get('args', [])):
                    launch_options['args'].append(f'--proxy-server={proxy_string}')
                
                # Handle authentication if needed
                if proxy_config.username and proxy_config.password:
                    logger.debug(f"Using authenticated proxy for JavaScript rendering: {proxy_config.host}:{proxy_config.port}")
                    # We'll authenticate in the page.authenticate() call below
                else:
                    logger.debug(f"Using proxy for JavaScript rendering: {proxy_string}")
                
                # Add country info for logging
                if proxy_config.country:
                    logger.info(f"Using proxy from country: {proxy_config.country}")
        
        # Launch browser asynchronously
        browser = await launch(launch_options)
        
        page = await browser.newPage()
        
        # Set user agent
        await page.setUserAgent(user_agent)
        
        # Set viewport
        await page.setViewport({'width': 1280, 'height': 800})
        
        # Navigate to URL
        response = await page.goto(url, {
            'waitUntil': 'networkidle0' if render_options.wait_for_navigation else 'domcontentloaded',
            'timeout': 30000
        })
        
        # Wait specified time for JavaScript execution
        if render_options.wait_time > 0:
            await asyncio.sleep(render_options.wait_time)
        
        # Wait for specific selector if provided
        if render_options.wait_for_selector:
            try:
                await page.waitForSelector(render_options.wait_for_selector, {'timeout': 5000})
            except:
                logger.warning(f"Selector '{render_options.wait_for_selector}' not found within timeout")
        
        # Get page title
        title = await page.title()
        
        # Get rendered HTML content
        content = await page.content()
        
        # Get final URL after any redirects
        final_url = page.url
        
        # Extract description from meta tags
        description = ""
        try:
            description = await page.evaluate('''() => {
                const meta = document.querySelector('meta[name="description"]') || 
                             document.querySelector('meta[property="og:description"]');
                return meta ? meta.getAttribute('content') : '';
            }''')
        except:
            logger.debug("Failed to extract description from meta tags")
        
        # Prepare result
        scrape_time = time.time() - start_time
        
        return {
            "status": "success",
            "data": {
                "title": title,
                "description": description,
                "content": content,
                "url": {
                    "original": url,
                    "final": final_url,
                    "was_redirected": url != final_url
                },
                "metadata": {
                    "content_length": len(content),
                    "scrape_time_seconds": scrape_time,
                    "has_title": bool(title),
                    "has_description": bool(description),
                    "user_agent": user_agent_key,
                    "is_dynamic": True,
                    "elements": {
                        "links": 0,
                        "images": 0,
                        "forms": 0,
                        "scripts": 0,
                        "total": 0
                    },
                    "crawling": None
                }
            }
        }
    
    except Exception as e:
        logger.error(f"Error with JavaScript rendering: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "Rendering error", "details": str(e)}
        )
    finally:
        if browser:
            try:
                await browser.close()
            except:
                pass


@app.post("/api/metadata", response_model=Union[SuccessResponse, ErrorResponse])
async def extract_page_metadata(scrape_request: ScrapeRequest, token: str = None):
    """Extract webpage metadata: title, meta tags, Open Graph and Twitter Cards."""
    if token is not None and not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    driver = None
    try:
        # Extract request data
        url = scrape_request.url
        user_agent_key = scrape_request.user_agent
        
        # Validate input
        if not url:
            raise HTTPException(status_code=400, detail="Missing URL")
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Get the actual user agent string
        user_agent = USER_AGENTS.get(user_agent_key, USER_AGENTS["chrome-windows"])
        
        logger.debug(f"Starting metadata extraction from URL: {url}")
        
        start_time = time.time()
        
        # Configure Chrome options
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"user-agent={user_agent}")
        
        # Configure proxy if provided
        if scrape_request.selenium_options and scrape_request.selenium_options.proxy_config:
            proxy_config = scrape_request.selenium_options.proxy_config
            if proxy_config.enabled and proxy_config.host and proxy_config.port:
                proxy_string = f"{proxy_config.host}:{proxy_config.port}"
                
                # Add authentication if provided
                if proxy_config.username and proxy_config.password:
                    auth_plugin_path = create_proxy_auth_extension(
                        proxy_config.host,
                        proxy_config.port,
                        proxy_config.username,
                        proxy_config.password
                    )
                    options.add_extension(auth_plugin_path)
                    logger.debug(f"Using authenticated proxy for metadata extraction: {proxy_config.host}:{proxy_config.port}")
                else:
                    options.add_argument(f'--proxy-server={proxy_string}')
                    logger.debug(f"Using proxy for metadata extraction: {proxy_string}")
                
                # Add country info for logging
                if proxy_config.country:
                    logger.info(f"Using proxy from country: {proxy_config.country}")
        
        # Start browser
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        
        # Load URL
        driver.get(url)
        
        # Wait a bit for content to load
        time.sleep(2)
        
        # Extract title
        title = driver.title
        
        # Extract all meta tags
        meta_tags = {}
        for meta in driver.find_elements(By.TAG_NAME, "meta"):
            name = meta.get_attribute("name") or meta.get_attribute("property")
            if name:
                meta_tags[name] = meta.get_attribute("content")
        
        # Extract description
        description = meta_tags.get("description", meta_tags.get("og:description", ""))
        
        # Extract canonical URL
        canonical_url = ""
        try:
            canonical = driver.find_element(By.CSS_SELECTOR, "link[rel='canonical']")
            canonical_url = canonical.get_attribute("href")
        except:
            pass
        
        # Extract favicon
        favicon_url = ""
        try:
            # Try different favicon patterns
            for selector in ["link[rel='icon']", "link[rel='shortcut icon']", "link[rel='apple-touch-icon']"]:
                try:
                    favicon = driver.find_element(By.CSS_SELECTOR, selector)
                    favicon_url = favicon.get_attribute("href")
                    if favicon_url:
                        # Make relative URLs absolute
                        if not favicon_url.startswith(('http://', 'https://')):
                            favicon_url = urljoin(url, favicon_url)
                        break
                except:
                    pass
        except:
            pass
        
        # Organize metadata by categories
        metadata_content = {
            "basic": {
                "title": title,
                "description": description,
                "canonical_url": canonical_url,
                "favicon_url": favicon_url
            },
            "meta_tags": meta_tags,
            "open_graph": {k.replace("og:", ""): v for k, v in meta_tags.items() if k and k.startswith("og:")},
            "twitter_card": {k.replace("twitter:", ""): v for k, v in meta_tags.items() if k and k.startswith("twitter:")}
        }
        
        # Convert to string for response
        content = str(metadata_content)
        
        # Prepare result
        scrape_time = time.time() - start_time
        
        return {
            "status": "success",
            "data": {
                "title": title,
                "description": description,
                "content": content,
                "url": {
                    "original": url,
                    "final": driver.current_url,
                    "was_redirected": url != driver.current_url
                },
                "metadata": {
                    "content_length": len(content),
                    "scrape_time_seconds": scrape_time,
                    "has_title": bool(title),
                    "has_description": bool(description),
                    "user_agent": user_agent_key,
                    "is_dynamic": True,
                    "elements": {
                        "links": 0,
                        "images": 0,
                        "forms": 0,
                        "scripts": 0,
                        "total": 0
                    },
                    "crawling": None
                }
            }
        }
    
    except Exception as e:
        logger.error(f"Error with metadata extraction: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "Metadata extraction error", "details": str(e)}
        )
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


@app.post("/api/links", response_model=Union[SuccessResponse, ErrorResponse])
async def extract_page_links(scrape_request: ScrapeRequest, token: str = None):
    """Extract webpage links with text, URL and internal/external status."""
    if token is not None and not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    driver = None
    try:
        # Extract request data
        url = scrape_request.url
        user_agent_key = scrape_request.user_agent
        
        # Validate input
        if not url:
            raise HTTPException(status_code=400, detail="Missing URL")
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Get the actual user agent string
        user_agent = USER_AGENTS.get(user_agent_key, USER_AGENTS["chrome-windows"])
        
        logger.debug(f"Starting link extraction from URL: {url}")
        
        start_time = time.time()
        
        # Configure Chrome options
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"user-agent={user_agent}")
        
        # Configure proxy if provided
        if scrape_request.selenium_options and scrape_request.selenium_options.proxy_config:
            proxy_config = scrape_request.selenium_options.proxy_config
            if proxy_config.enabled and proxy_config.host and proxy_config.port:
                proxy_string = f"{proxy_config.host}:{proxy_config.port}"
                
                # Add authentication if provided
                if proxy_config.username and proxy_config.password:
                    auth_plugin_path = create_proxy_auth_extension(
                        proxy_config.host,
                        proxy_config.port,
                        proxy_config.username,
                        proxy_config.password
                    )
                    options.add_extension(auth_plugin_path)
                    logger.debug(f"Using authenticated proxy for link extraction: {proxy_config.host}:{proxy_config.port}")
                else:
                    options.add_argument(f'--proxy-server={proxy_string}')
                    logger.debug(f"Using proxy for link extraction: {proxy_string}")
                
                # Add country info for logging
                if proxy_config.country:
                    logger.info(f"Using proxy from country: {proxy_config.country}")
        
        # Start browser
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        
        # Load URL
        driver.get(url)
        
        # Wait a bit for content to load
        time.sleep(2)
        
        # Extract title and description
        title = driver.title
        description = ""
        try:
            description = driver.find_element(By.XPATH, "//meta[@name='description']").get_attribute("content")
        except NoSuchElementException:
            try:
                description = driver.find_element(By.XPATH, "//meta[@property='og:description']").get_attribute("content")
            except NoSuchElementException:
                logger.debug("No description meta tag found")
        
        # Extract all links
        links = []
        base_domain = urlparse(url).netloc
        
        for a in driver.find_elements(By.TAG_NAME, "a"):
            href = a.get_attribute("href")
            if href:
                # Skip javascript: and mailto: links
                if href.startswith(("javascript:", "mailto:", "tel:")):
                    continue
                
                # Make relative URLs absolute
                if not href.startswith(('http://', 'https://')):
                    href = urljoin(url, href)
                
                # Check if internal or external
                link_domain = urlparse(href).netloc
                is_internal = link_domain == base_domain or not link_domain
                
                # Get additional attributes
                attributes = {
                    "target": a.get_attribute("target"),
                    "rel": a.get_attribute("rel"),
                    "title": a.get_attribute("title"),
                    "id": a.get_attribute("id"),
                    "class": a.get_attribute("class")
                }
                
                # Clean up empty attributes
                attributes = {k: v for k, v in attributes.items() if v}
                
                links.append({
                    "url": href,
                    "text": a.text.strip(),
                    "is_internal": is_internal,
                    "attributes": attributes
                })
        
        # Convert to string for response
        content = str(links)
        
        # Prepare result
        scrape_time = time.time() - start_time
        
        return {
            "status": "success",
            "data": {
                "title": title,
                "description": description,
                "content": content,
                "url": {
                    "original": url,
                    "final": driver.current_url,
                    "was_redirected": url != driver.current_url
                },
                "metadata": {
                    "content_length": len(content),
                    "scrape_time_seconds": scrape_time,
                    "has_title": bool(title),
                    "has_description": bool(description),
                    "user_agent": user_agent_key,
                    "is_dynamic": True,
                    "elements": {
                        "links": len(links),
                        "images": 0,
                        "forms": 0,
                        "scripts": 0,
                        "total": 0
                    },
                    "crawling": None
                }
            }
        }
    
    except Exception as e:
        logger.error(f"Error with link extraction: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "Link extraction error", "details": str(e)}
        )
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass


@app.post("/api/screenshot")
async def take_screenshot(scrape_request: ScrapeRequest, token: str = None):
    """Capture webpage screenshots with configurable dimensions and format."""
    if token is not None and not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    browser = None
    try:
        # Extract request data
        url = scrape_request.url
        user_agent_key = scrape_request.user_agent
        
        # Validate input
        if not url:
            raise HTTPException(status_code=400, detail="Missing URL")
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Get screenshot options or use defaults
        screenshot_options = scrape_request.screenshot_options or ScreenshotOptions()
        
        # Get the actual user agent string
        user_agent = USER_AGENTS.get(user_agent_key, USER_AGENTS["chrome-windows"])
        
        logger.debug(f"Taking screenshot of URL: {url}")
        
        # Configure launch options
        launch_options = {
            'headless': True,
            'args': ['--no-sandbox', '--disable-dev-shm-usage'],
            'ignoreHTTPSErrors': True
        }
        
        # Configure proxy if provided
        if scrape_request.selenium_options and scrape_request.selenium_options.proxy_config:
            proxy_config = scrape_request.selenium_options.proxy_config
            if proxy_config.enabled and proxy_config.host and proxy_config.port:
                proxy_string = f"{proxy_config.host}:{proxy_config.port}"
                
                # Add proxy to launch arguments
                if not '--proxy-server=' in ' '.join(launch_options.get('args', [])):
                    launch_options['args'].append(f'--proxy-server={proxy_string}')
                
                # Handle authentication if needed
                if proxy_config.username and proxy_config.password:
                    logger.debug(f"Using authenticated proxy for screenshot: {proxy_config.host}:{proxy_config.port}")
                    # We'll authenticate in the page.authenticate() call below
                else:
                    logger.debug(f"Using proxy for screenshot: {proxy_string}")
                
                # Add country info for logging
                if proxy_config.country:
                    logger.info(f"Using proxy from country: {proxy_config.country}")
        
        # Launch browser asynchronously
        browser = await launch(launch_options)
        
        page = await browser.newPage()
        
        # Set user agent
        await page.setUserAgent(user_agent)
        
        # Set viewport
        await page.setViewport({
            'width': screenshot_options.width,
            'height': screenshot_options.height
        })
        
        # Navigate to URL
        await page.goto(url, {
            'waitUntil': 'networkidle0',
            'timeout': 30000
        })
        
        # Wait a bit for any animations or delayed content
        await asyncio.sleep(2)
        
        # Take screenshot
        screenshot_options_dict = {
            'fullPage': screenshot_options.full_page,
            'type': screenshot_options.format
        }
        
        # Add quality for JPEG
        if screenshot_options.format == 'jpeg' and screenshot_options.quality:
            screenshot_options_dict['quality'] = screenshot_options.quality
        
        screenshot_binary = await page.screenshot(screenshot_options_dict)
        
        # Return the image directly
        media_type = f"image/{screenshot_options.format}"
        return Response(content=screenshot_binary, media_type=media_type)
    
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "Screenshot error", "details": str(e)}
        )
    finally:
        if browser:
            try:
                await browser.close()
            except:
                pass


# Settings routes - Create a new API route for settings under /api/settings_yaml

@app.get("/api/settings_yaml", response_class=PlainTextResponse)
async def get_settings_yaml(token: str = None):
    """Get current settings in YAML format."""
    if token is not None and not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        # Load settings from environment variable
        settings = load_settings()
        return yaml.dump(settings.dict(), sort_keys=False)
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting settings: {str(e)}")

@app.post("/api/settings_yaml", response_class=JSONResponse)
async def update_settings_yaml(request: Request, token: str = None):
    """Update settings from YAML format."""
    if token is not None and not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        yaml_text = await request.body()
        yaml_text = yaml_text.decode('utf-8')
        settings_dict = yaml.safe_load(yaml_text)
        
        # Validate settings
        if not isinstance(settings_dict, dict):
            raise HTTPException(status_code=400, detail="Invalid YAML format")
        
        # Use Pydantic for validation
        try:
            settings = ScraperSettings(**settings_dict)
            # Save settings to environment variable instead of file
            save_settings(settings)
            return settings.dict()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid settings: {str(e)}")
        
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"YAML parsing error: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating settings: {str(e)}")

@app.get("/api/settings/json", response_class=JSONResponse)
async def get_settings_json(token: str = None):
    """Get current settings in JSON format."""
    if token is not None and not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        # Load settings from environment variable
        settings = load_settings()
        return settings.dict()
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting settings: {str(e)}")

# Define a Pydantic model for settings to fix schema issues
class ScraperSettings(BaseModel):
    page_load_timeout: int = 30
    dynamic_content_wait: float = 2.0
    chatgpt_min_wait: float = 5.0
    chatgpt_max_wait: float = 8.0
    max_depth: int = 1
    max_pages_per_domain: int = 10
    restrict_to_domains: List[str] = []
    follow_external_links: bool = False
    ignore_query_strings: bool = True
    exclude_url_patterns: List[str] = []

# Use application-level global variable for settings persistence
import os
import json

# Global variables for settings persistence
# Default settings stored in memory
GLOBAL_SETTINGS = None
SETTINGS_ENV_VAR = "SCRAPER_SETTINGS"

def load_settings():
    """Load settings from global variable, environment variable, or return defaults."""
    global GLOBAL_SETTINGS
    
    try:
        # First check if we have settings in our global variable
        if GLOBAL_SETTINGS is not None:
            print("Using in-memory settings")
            return GLOBAL_SETTINGS
            
        # Next, check if settings environment variable exists
        settings_json = os.environ.get(SETTINGS_ENV_VAR)
        if settings_json:
            print(f"Loading settings from environment variable {SETTINGS_ENV_VAR}")
            try:
                settings_dict = json.loads(settings_json)
                print(f"Loaded settings: {settings_dict}")
                GLOBAL_SETTINGS = ScraperSettings(**settings_dict)
                return GLOBAL_SETTINGS
            except Exception as parse_e:
                print(f"Error parsing settings from environment variable: {str(parse_e)}")
        
        # If we get here, use default settings
        print("Using default settings")
        GLOBAL_SETTINGS = ScraperSettings()
        return GLOBAL_SETTINGS
    except Exception as e:
        # Print the error to console
        print(f"Error loading settings: {str(e)}")
        logger.error(f"Error loading settings: {str(e)}")
        GLOBAL_SETTINGS = ScraperSettings()  # Return defaults on error
        return GLOBAL_SETTINGS

def save_settings(settings):
    """Save settings to global variable and environment variable."""
    global GLOBAL_SETTINGS
    
    try:
        # Store in global variable for persistence within this process
        GLOBAL_SETTINGS = settings
        
        # Convert settings to JSON string - ensure it's a dict first
        if isinstance(settings, ScraperSettings):
            settings_dict = settings.dict()
        else:
            settings_dict = settings
        
        # Convert to JSON and store in environment variable as backup
        settings_json = json.dumps(settings_dict)
        os.environ[SETTINGS_ENV_VAR] = settings_json
        
        print(f"Settings saved successfully to global variable and environment variable")
        return True
    except Exception as e:
        # Print the error to console
        print(f"Error saving settings: {str(e)}")
        logger.error(f"Error saving settings: {str(e)}")
        return False

@app.post("/api/settings/json", response_class=JSONResponse)
async def update_settings_json(settings: ScraperSettings, token: str = None):
    """Update settings from JSON format."""
    if token is not None and not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        # Save settings to environment variable
        save_settings(settings)
        return settings.dict()
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating settings: {str(e)}")

# Run the application
if __name__ == "__main__":
    import uvicorn
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)