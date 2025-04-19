"""
Scraping service for the application.

This module contains the core scraping functionality using Selenium and Trafilatura,
separated from the API layer to allow for better testing and reuse.
"""
import asyncio
import random
import time
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from fastapi import Depends
from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
import trafilatura

from app.core.browser import BrowserPool, get_browser_pool_dependency
from app.core.config import Settings, get_settings_dependency
from app.core.logging import with_log_context
from app.schemas.scraping import (
    CrawlingData, 
    ElementCounts, 
    ScrapedData, 
    ScrapingMetadata, 
    UrlInfo,
)


def async_to_sync(func):
    """Decorator to run a synchronous function in an async context."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    return wrapper


class ScrapingService:
    """Service for web scraping operations."""
    
    def __init__(
        self, 
        browser_pool: BrowserPool = Depends(get_browser_pool_dependency),
        settings: Settings = Depends(get_settings_dependency)
    ):
        """
        Initialize the scraping service.
        
        Args:
            browser_pool: Pool of browser instances
            settings: Application settings
        """
        self.browser_pool = browser_pool
        self.settings = settings
        
        # Define user agent mapping
        self.user_agents = {
            "chrome-windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "chrome-mac": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "firefox": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "safari": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "mobile-android": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36",
            "mobile-iphone": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        }
    
    @with_log_context(service="scraping_service")
    @async_to_sync
    def scrape_with_selenium(
        self, 
        url: str,
        user_agent_key: str = "chrome-windows",
        headless: bool = True,
        disable_images: bool = True,
        dynamic_wait: Optional[float] = None,
        max_depth: int = 1,
        max_pages: int = 10,
        follow_external_links: bool = False,
        restrict_to_domain: bool = True,
        ignore_query_strings: bool = True,
    ) -> ScrapedData:
        """
        Scrape website content using Selenium.
        
        Args:
            url: URL to scrape
            user_agent_key: Key for user agent string
            headless: Whether to use headless browser
            disable_images: Whether to disable image loading
            dynamic_wait: Time to wait for dynamic content
            max_depth: Maximum crawl depth
            max_pages: Maximum pages to crawl
            follow_external_links: Whether to follow external links
            restrict_to_domain: Whether to restrict to original domain
            ignore_query_strings: Whether to ignore query strings in URLs
            
        Returns:
            ScrapedData: Extracted data from the website
        """
        # Get the actual user agent string
        user_agent = self.user_agents.get(user_agent_key, self.user_agents["chrome-windows"])
        
        # Start timing
        start_time = time.time()
        
        # Use browser from pool
        with self.browser_pool.get_browser(
            user_agent=user_agent,
            headless=headless,
            disable_images=disable_images
        ) as driver:
            # Load initial URL
            logger.debug(f"Loading URL: {url}")
            driver.get(url)
            
            # Handle chat.openai.com/share/... links
            was_redirected = False
            if "chat.openai.com/share/" in url:
                was_redirected = True
                chat_wait_time = random.uniform(
                    self.settings.CHATGPT_MIN_WAIT, 
                    self.settings.CHATGPT_MAX_WAIT
                )
                logger.debug(f"[ChatGPT redirect] Waiting {chat_wait_time:.2f}s for redirect...")
                time.sleep(chat_wait_time)
                driver.get(driver.current_url)
            
            # Use either the requested wait time or the default from settings
            wait_time = dynamic_wait if dynamic_wait is not None else self.settings.DYNAMIC_CONTENT_WAIT
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
            total_elements_count = len(driver.find_elements(By.XPATH, "//*"))
            
            # Check if crawling is enabled
            crawled_pages_data = []
            crawled_urls = []
            final_url = driver.current_url
            
            if max_depth > 1 and max_pages > 1:
                logger.info(f"Crawling enabled. Max depth: {max_depth}, Max pages: {max_pages}")
                
                # Create crawler with settings
                crawler = WebCrawler(
                    driver=driver,
                    settings={
                        "max_depth": max_depth,
                        "max_pages": max_pages,
                        "follow_external_links": follow_external_links,
                        "restrict_to_domains": [self._get_domain(url)] if restrict_to_domain else [],
                        "ignore_query_strings": ignore_query_strings,
                        "exclude_url_patterns": self.settings.EXCLUDE_URL_PATTERNS,
                        "dynamic_content_wait": wait_time,
                    }
                )
                
                # Perform crawling
                crawled_pages_data = crawler.crawl(url)
                
                # Extract just the URLs for metadata
                crawled_urls = [page["url"] for page in crawled_pages_data if "url" in page]
                
                # Add crawling data to content
                if crawled_pages_data:
                    content += "\n\n--- CRAWLED PAGES ---\n\n"
                    for idx, page in enumerate(crawled_pages_data, 1):
                        content += f"[Page {idx}] {page.get('title', 'No Title')} - {page.get('url', 'No URL')}\n"
                        content += f"{page.get('content', 'No content extracted')[:500]}...\n\n"
        
        # Calculate scrape time
        scrape_time = time.time() - start_time
        
        # Create response object
        scraped_data = ScrapedData(
            title=title,
            description=description,
            content=content,
            url=UrlInfo(
                original=url,
                final=final_url,
                was_redirected=was_redirected
            ),
            metadata=ScrapingMetadata(
                content_length=len(content),
                scrape_time_seconds=round(scrape_time, 2),
                has_title=bool(title),
                has_description=bool(description),
                user_agent=user_agent_key,
                is_dynamic=True,
                elements=ElementCounts(
                    links=links_count,
                    images=images_count,
                    forms=forms_count,
                    scripts=scripts_count,
                    total=total_elements_count
                ),
                crawling=CrawlingData(
                    enabled=max_depth > 1,
                    pages_crawled=len(crawled_urls),
                    max_depth=max_depth,
                    crawled_urls=crawled_urls
                ) if max_depth > 1 else None
            )
        )
        
        return scraped_data
    
    @with_log_context(service="scraping_service")
    @async_to_sync
    def scrape_with_trafilatura(self, url: str, user_agent_key: str = "chrome-windows") -> ScrapedData:
        """
        Scrape website content using Trafilatura.
        
        Args:
            url: URL to scrape
            user_agent_key: Key for user agent string
            
        Returns:
            ScrapedData: Extracted data from the website
        """
        # Get the actual user agent string
        user_agent = self.user_agents.get(user_agent_key, self.user_agents["chrome-windows"])
        
        # Start timing
        start_time = time.time()
        
        # Fetch and extract content with Trafilatura
        try:
            # Add proper user agent
            headers = {'User-Agent': user_agent}
            
            # Download content
            downloaded = trafilatura.fetch_url(url, headers=headers)
            if not downloaded:
                raise ValueError(f"Failed to download content from {url}")
            
            # Extract text content
            content = trafilatura.extract(downloaded)
            if not content:
                content = "No content could be extracted."
                
            # Extract metadata
            metadata = trafilatura.metadata.extract_metadata(downloaded)
            
            # Get title and description
            title = metadata.title if metadata and metadata.title else ""
            description = metadata.description if metadata and metadata.description else ""
            
            # Check for redirect (simple check - not as accurate as Selenium)
            final_url = url  # Trafilatura doesn't expose final URL easily
            was_redirected = False
            
        except Exception as e:
            logger.error(f"Error scraping with Trafilatura: {str(e)}")
            raise
            
        # Calculate scrape time
        scrape_time = time.time() - start_time
        
        # Create response object
        scraped_data = ScrapedData(
            title=title,
            description=description,
            content=content,
            url=UrlInfo(
                original=url,
                final=final_url,
                was_redirected=was_redirected
            ),
            metadata=ScrapingMetadata(
                content_length=len(content) if content else 0,
                scrape_time_seconds=round(scrape_time, 2),
                has_title=bool(title),
                has_description=bool(description),
                user_agent=user_agent_key,
                is_dynamic=False,
                elements=ElementCounts(
                    links=0,  # Trafilatura doesn't count elements
                    images=0,
                    forms=0,
                    scripts=0,
                    total=0
                ),
                crawling=None  # Trafilatura doesn't support crawling
            )
        )
        
        return scraped_data
    
    def _get_domain(self, url: str) -> str:
        """
        Extract the domain from a URL.
        
        Args:
            url: URL to extract domain from
            
        Returns:
            str: Domain name
        """
        return urlparse(url).netloc


class WebCrawler:
    """Web crawler that respects domain restrictions and depth controls."""
    
    def __init__(self, driver: webdriver.Chrome, settings: Dict[str, Any]):
        """
        Initialize the web crawler.
        
        Args:
            driver: Selenium WebDriver instance
            settings: Dictionary with crawler settings
        """
        self.driver = driver
        self.settings = settings
        self.visited_urls = set()
        self.pages_data = []
        
        # Validate required settings
        self.max_depth = settings.get("max_depth", 1)
        self.max_pages = settings.get("max_pages", 10)
        self.follow_external_links = settings.get("follow_external_links", False)
        self.restrict_to_domains = settings.get("restrict_to_domains", [])
        self.ignore_query_strings = settings.get("ignore_query_strings", True)
        self.exclude_url_patterns = settings.get("exclude_url_patterns", [])
        self.dynamic_content_wait = settings.get("dynamic_content_wait", 2.0)
        
        logger.debug(f"WebCrawler initialized with settings: {settings}")
        
    def crawl(self, start_url: str) -> List[Dict[str, Any]]:
        """
        Start the crawling process from a given URL.
        
        Args:
            start_url: URL to start crawling from
            
        Returns:
            List[Dict[str, Any]]: List of data from all crawled pages
        """
        # Clear state for new crawl
        self.visited_urls.clear()
        self.pages_data.clear()
        
        # Start recursive crawl
        self._crawl_recursive(start_url, depth=1)
        
        return self.pages_data
        
    def _crawl_recursive(self, url: str, depth: int) -> None:
        """
        Recursively crawl pages starting from the given URL.
        
        Args:
            url: URL to crawl
            depth: Current crawling depth
        """
        # Check termination conditions
        if depth > self.max_depth:
            logger.debug(f"Max depth reached at {url}")
            return
            
        if len(self.pages_data) >= self.max_pages:
            logger.debug(f"Max pages reached at {url}")
            return
            
        # Normalize URL if ignoring query strings
        normalized_url = self._normalize_url(url) if self.ignore_query_strings else url
        
        # Skip if already visited
        if normalized_url in self.visited_urls:
            logger.debug(f"Already visited: {url}")
            return
            
        # Mark as visited
        self.visited_urls.add(normalized_url)
        
        # Crawl current page
        page_data = self._crawl_page(url)
        if page_data:
            self.pages_data.append(page_data)
            
            # Extract links and crawl them if not at max depth
            if depth < self.max_depth and len(self.pages_data) < self.max_pages:
                links = self._extract_links(url)
                
                # Filter links based on domain restrictions
                filtered_links = [
                    link for link in links 
                    if self._should_follow_url(url, link)
                ]
                
                # Recursively crawl each link
                for link in filtered_links:
                    if len(self.pages_data) < self.max_pages:
                        self._crawl_recursive(link, depth + 1)
                    else:
                        break
        
    def _crawl_page(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Crawl a single page and extract its content.
        
        Args:
            url: URL to crawl
            
        Returns:
            Optional[Dict[str, Any]]: Data extracted from the page, or None if page should be skipped
        """
        try:
            # Navigate to the page
            logger.debug(f"Crawling: {url}")
            self.driver.get(url)
            
            # Wait for dynamic content
            time.sleep(self.dynamic_content_wait)
            
            # Extract content
            title = self.driver.title
            content = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Try to extract description
            description = ""
            try:
                description = self.driver.find_element(By.XPATH, "//meta[@name='description']").get_attribute("content")
            except NoSuchElementException:
                try:
                    description = self.driver.find_element(By.XPATH, "//meta[@property='og:description']").get_attribute("content")
                except NoSuchElementException:
                    pass
                    
            return {
                "url": url,
                "title": title,
                "description": description,
                "content": content
            }
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
            return None
            
    def _extract_links(self, url: str) -> List[str]:
        """
        Extract all links from a webpage.
        
        Args:
            url: URL to extract links from
            
        Returns:
            List[str]: List of URLs found on the page
        """
        try:
            # Find all links
            links = []
            elements = self.driver.find_elements(By.TAG_NAME, "a")
            
            # Extract href attributes
            for element in elements:
                try:
                    href = element.get_attribute("href")
                    if href and href.startswith(("http://", "https://")):
                        links.append(href)
                except Exception:
                    continue
                    
            return links
            
        except Exception as e:
            logger.error(f"Error extracting links from {url}: {str(e)}")
            return []
            
    def _should_follow_url(self, base_url: str, url: str) -> bool:
        """
        Determine if a URL should be followed based on domain restrictions.
        
        Args:
            base_url: Original URL being crawled
            url: URL being considered for following
            
        Returns:
            bool: True if URL should be followed, False otherwise
        """
        # Check for excluded patterns
        if any(pattern in url for pattern in self.exclude_url_patterns):
            return False
            
        # If no domain restrictions, follow all URLs
        if not self.restrict_to_domains:
            return True
            
        # Check if URLs have the same domain
        is_same_domain = self._is_same_domain(base_url, url)
        
        # If following external links is disabled, only follow same-domain links
        if not self.follow_external_links and not is_same_domain:
            return False
            
        # Check if URL domain is in the restricted domains list
        url_domain = self._get_domain(url)
        return url_domain in self.restrict_to_domains
        
    def _is_same_domain(self, url1: str, url2: str) -> bool:
        """
        Check if two URLs belong to the same domain.
        
        Args:
            url1: First URL
            url2: Second URL
            
        Returns:
            bool: True if URLs have the same domain, False otherwise
        """
        return self._get_domain(url1) == self._get_domain(url2)
        
    def _get_domain(self, url: str) -> str:
        """
        Extract the domain from a URL.
        
        Args:
            url: URL to extract domain from
            
        Returns:
            str: Domain name
        """
        return urlparse(url).netloc
        
    def _normalize_url(self, url: str) -> str:
        """
        Normalize a URL by removing query parameters.
        
        Args:
            url: URL to normalize
            
        Returns:
            str: Normalized URL
        """
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"