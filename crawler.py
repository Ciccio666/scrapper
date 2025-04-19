"""
Web Crawler module for the FastAPI web scraper application.
This module handles recursive crawling with domain restriction and depth controls.
"""

import re
import time
import logging
from urllib.parse import urlparse, urljoin
from typing import Set, List, Dict, Any, Optional, Tuple, Union
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException

# Configure logging
logger = logging.getLogger(__name__)

class WebCrawler:
    """Web crawler that respects domain restrictions and depth controls."""
    
    def __init__(self, driver: webdriver.Chrome, settings: Dict[str, Any]):
        """
        Initialize the web crawler with a Selenium driver and settings.
        
        Args:
            driver: The Selenium Chrome driver instance
            settings: Dictionary containing crawler settings
        """
        self.driver = driver
        self.settings = settings if settings is not None else {}
        self.visited_urls: Set[str] = set()
        self.url_queue: List[List[Union[str, int]]] = []  # [url, depth] as a list
        self.results: List[Dict[str, Any]] = []
        self.current_depth = 0
        self.pages_crawled_per_domain: Dict[str, int] = {}  # Tracks pages crawled per domain
    
    def get_domain(self, url: str) -> str:
        """Extract the domain from a URL."""
        parsed_url = urlparse(url)
        return parsed_url.netloc
    
    def is_same_domain(self, url1: str, url2: str) -> bool:
        """Check if two URLs belong to the same domain."""
        return self.get_domain(url1) == self.get_domain(url2)
    
    def should_follow_url(self, base_url: str, url: str) -> bool:
        """
        Determine if a URL should be followed based on domain restrictions.
        
        Args:
            base_url: The original URL being crawled
            url: The URL being considered for following
            
        Returns:
            bool: True if the URL should be followed, False otherwise
        """
        # Skip empty or javascript URLs
        if not url or url.startswith('javascript:') or url == '#':
            return False
            
        # Parse the URL to get the domain
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Skip if domain is empty (might be a relative URL)
        if not domain:
            return True  # Relative URLs are always from the same domain
            
        # Get base domain for comparison
        base_domain = self.get_domain(base_url)
            
        # Check domain restrictions
        restrict_domains = self.settings.get('restrict_to_domains', [])
        if restrict_domains and len(restrict_domains) > 0:
            # If we have a domain restriction list, check if this domain is allowed
            is_allowed_domain = False
            
            # Check if the domain exactly matches any in the restriction list
            if domain in restrict_domains:
                is_allowed_domain = True
            
            # Check if the domain is a subdomain of any in the restriction list
            if not is_allowed_domain:
                for allowed_domain in restrict_domains:
                    if domain.endswith('.' + allowed_domain) or domain == allowed_domain:
                        is_allowed_domain = True
                        break
            
            # If not allowed and we don't follow external links, skip it
            if not is_allowed_domain and not self.settings.get('follow_external_links', False):
                logger.debug(f"Skipping URL {url} - domain {domain} not in allowed list: {restrict_domains}")
                return False
        
        # Check if we should follow external domains (only if not already allowed by restriction list)
        if domain != base_domain:  # Different domains
            if not self.settings.get('follow_external_links', False):
                logger.debug(f"Skipping external URL {url} - not following external domains")
                return False
                
            # We're following an external link, check if we've reached the limit for this domain
            if domain in self.pages_crawled_per_domain:
                if self.pages_crawled_per_domain[domain] >= self.settings.get('max_pages_per_domain', 10):
                    logger.debug(f"Skipping URL {url} - reached max pages for domain {domain}")
                    return False
            
        # Check URL exclusion patterns
        for pattern in self.settings.get('exclude_url_patterns', []):
            if re.search(pattern, url):
                logger.debug(f"Skipping URL {url} - matches exclude pattern: {pattern}")
                return False
                
        # If ignoring query strings, normalize URLs before checking if visited
        if self.settings.get('ignore_query_strings', True):
            parsed = urlparse(url)
            normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # If we've visited this normalized URL before, skip it
            if normalized_url in self.visited_urls:
                logger.debug(f"Skipping URL {url} - normalized URL already visited")
                return False
        
        # Skip URLs we've already visited
        if url in self.visited_urls:
            logger.debug(f"Skipping URL {url} - already visited")
            return False
            
        return True
    
    def extract_links(self, url: str) -> List[str]:
        """
        Extract all links from a webpage.
        
        Args:
            url: The URL to extract links from
            
        Returns:
            List[str]: List of absolute URLs found on the page
        """
        links = []
        try:
            # Find all <a> tags in the page
            elements = self.driver.find_elements(By.TAG_NAME, "a")
            
            # Extract href attributes
            for element in elements:
                href = element.get_attribute("href")
                if href:
                    absolute_url = urljoin(url, href)
                    if self.should_follow_url(url, absolute_url):
                        links.append(absolute_url)
        except Exception as e:
            logger.error(f"Error extracting links from {url}: {str(e)}")
        
        return links
    
    def crawl_page(self, url: str, depth: int = 0) -> Optional[Dict[str, Any]]:
        """
        Crawl a single page and extract its content.
        
        Args:
            url: The URL to crawl
            depth: The current crawl depth
            
        Returns:
            Optional[Dict[str, Any]]: Data extracted from the page, or None if page should be skipped
        """
        # Skip if we've reached max depth
        if depth > self.settings.get('max_depth', 1):
            return None
            
        # Skip if we've already visited this URL
        if url in self.visited_urls:
            return None
            
        # Skip if we've reached the maximum pages for this domain
        domain = self.get_domain(url)
        if domain in self.pages_crawled_per_domain:
            if self.pages_crawled_per_domain[domain] >= self.settings.get('max_pages_per_domain', 10):
                logger.info(f"Reached maximum pages ({self.settings.get('max_pages_per_domain')}) for domain {domain}")
                return None
        else:
            self.pages_crawled_per_domain[domain] = 0
            
        logger.info(f"Crawling {url} (depth {depth})")
        
        # Mark as visited to prevent loops
        self.visited_urls.add(url)
        
        try:
            # Load the page
            self.driver.get(url)
            
            # Handle special cases (like ChatGPT)
            was_redirected = False
            if "chat.openai.com/share/" in url:
                was_redirected = True
                chat_wait_time = self.settings.get('chatgpt_min_wait', 5.0)
                logger.debug(f"[ChatGPT redirect] Waiting {chat_wait_time}s for redirect...")
                time.sleep(chat_wait_time)
                self.driver.get(self.driver.current_url)
                
            # Wait for dynamic content
            time.sleep(self.settings.get('dynamic_content_wait', 2.0))
            
            # Extract page content
            title = self.driver.title
            description = ""
            content = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Try to extract description meta tag
            try:
                description = self.driver.find_element(By.XPATH, "//meta[@name='description']").get_attribute("content")
            except NoSuchElementException:
                try:
                    description = self.driver.find_element(By.XPATH, "//meta[@property='og:description']").get_attribute("content")
                except NoSuchElementException:
                    logger.debug("No description meta tag found")
            
            # Count page elements
            links_count = len(self.driver.find_elements(By.TAG_NAME, "a"))
            images_count = len(self.driver.find_elements(By.TAG_NAME, "img"))
            forms_count = len(self.driver.find_elements(By.TAG_NAME, "form"))
            scripts_count = len(self.driver.find_elements(By.TAG_NAME, "script"))
            
            # Increment counter for this domain
            self.pages_crawled_per_domain[domain] += 1
            
            # If depth is not at max, extract links for further crawling
            if depth < self.settings.get('max_depth', 1):
                links = self.extract_links(url)
                
                # Add links to the queue for processing
                for link in links:
                    if link not in self.visited_urls:
                        # Store URL and depth as a list instead of tuple
                        self.url_queue.append([link, depth + 1])
            
            # Prepare the page data
            page_data = {
                "url": url,
                "title": title,
                "description": description,
                "content": content,
                "links_count": links_count,
                "images_count": images_count,
                "forms_count": forms_count,
                "scripts_count": scripts_count,
                "depth": depth,
                "domain": domain
            }
            
            return page_data
            
        except TimeoutException as e:
            logger.error(f"Timeout error crawling {url}: {str(e)}")
            return None
        except WebDriverException as e:
            logger.error(f"WebDriver error crawling {url}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
            return None
    
    def crawl(self, start_url: str) -> List[Dict[str, Any]]:
        """
        Start the crawling process from a given URL.
        
        Args:
            start_url: The URL to start crawling from
            
        Returns:
            List[Dict[str, Any]]: List of data extracted from all crawled pages
        """
        # Reset crawl state
        self.visited_urls = set()
        self.url_queue = [[start_url, 0]]  # [url, depth] as a list
        self.results = []
        self.pages_crawled_per_domain = {}
        
        # Process the queue until empty or until we hit limits
        while self.url_queue:
            current_item = self.url_queue.pop(0)
            url = str(current_item[0])
            depth = int(current_item[1])
            
            # Skip if we've already visited this URL
            if url in self.visited_urls:
                continue
                
            # Process the page
            page_data = self.crawl_page(url=url, depth=depth)
            
            # If we got data back, add it to the results
            if page_data:
                self.results.append(page_data)
                
        return self.results