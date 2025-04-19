"""
Browser management functionality for the application.

This module provides a browser pool for reusing Selenium WebDriver instances,
which improves performance and resource utilization.
"""
import os
import threading
import time
from contextlib import contextmanager
from functools import lru_cache
from queue import Empty, Queue
from typing import Dict, List, Optional, Generator, Any

from fastapi import Depends
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from app.core.config import Settings, get_settings_dependency
from app.core.logging import with_log_context


class BrowserInstance:
    """Container for a browser instance with metadata."""
    
    def __init__(self, driver: webdriver.Chrome):
        """
        Initialize a browser instance.
        
        Args:
            driver: Selenium WebDriver instance
        """
        self.driver = driver
        self.last_used = time.time()
        self.in_use = False


class BrowserPool:
    """Pool of browser instances for reuse."""
    
    def __init__(self, settings: Settings):
        """
        Initialize the browser pool.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.pool: List[BrowserInstance] = []
        self.lock = threading.RLock()
        self.cleanup_thread = None
        self.running = True
        
        # Start the cleanup thread
        self._start_cleanup_thread()
        
        logger.info(f"Browser pool initialized with size {settings.BROWSER_POOL_SIZE}")
    
    @with_log_context(service="browser_pool")
    def _create_browser(self, user_agent: str, headless: bool, disable_images: bool) -> webdriver.Chrome:
        """
        Create a new browser instance.
        
        Args:
            user_agent: User agent string
            headless: Whether to use headless mode
            disable_images: Whether to disable image loading
            
        Returns:
            webdriver.Chrome: New WebDriver instance
        """
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
        
        if disable_images:
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)
        
        # Get Chrome binary and chromedriver paths from environment
        chrome_binary = os.environ.get('CHROME_BINARY')
        if chrome_binary:
            options.binary_location = chrome_binary
            logger.debug(f"Using Chrome binary at: {chrome_binary}")
        
        chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')
        
        try:
            # Start browser
            if chromedriver_path and os.path.exists(chromedriver_path):
                logger.debug(f"Using ChromeDriver at: {chromedriver_path}")
                service = Service(executable_path=chromedriver_path)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                logger.debug("Using default ChromeDriver")
                driver = webdriver.Chrome(options=options)
            
            # Set timeouts
            driver.set_page_load_timeout(self.settings.PAGE_LOAD_TIMEOUT)
            
            return driver
            
        except Exception as e:
            logger.error(f"Error creating WebDriver: {str(e)}")
            raise
    
    @contextmanager
    def get_browser(
        self, 
        user_agent: str = "Mozilla/5.0", 
        headless: bool = True, 
        disable_images: bool = True
    ) -> Generator[webdriver.Chrome, None, None]:
        """
        Get a browser from the pool or create a new one.
        
        Args:
            user_agent: User agent string
            headless: Whether to use headless mode
            disable_images: Whether to disable image loading
            
        Yields:
            webdriver.Chrome: WebDriver instance
        """
        browser_instance = None
        
        try:
            # Try to get a browser from the pool
            with self.lock:
                for instance in self.pool:
                    if not instance.in_use:
                        instance.in_use = True
                        instance.last_used = time.time()
                        browser_instance = instance
                        break
                
                # Create a new browser if the pool is not full
                if not browser_instance and len(self.pool) < self.settings.BROWSER_POOL_SIZE:
                    driver = self._create_browser(user_agent, headless, disable_images)
                    browser_instance = BrowserInstance(driver)
                    browser_instance.in_use = True
                    self.pool.append(browser_instance)
            
            # Wait for an available browser if needed
            if not browser_instance:
                # Create a temporary browser that won't be added to the pool
                logger.warning("Browser pool full, creating temporary browser")
                driver = self._create_browser(user_agent, headless, disable_images)
                browser_instance = BrowserInstance(driver)
                browser_instance.in_use = True
            
            # Yield the driver to the caller
            yield browser_instance.driver
            
        finally:
            # Return the browser to the pool
            if browser_instance:
                with self.lock:
                    browser_instance.in_use = False
                    browser_instance.last_used = time.time()
    
    def _start_cleanup_thread(self) -> None:
        """Start a thread to clean up idle browsers."""
        def cleanup():
            while self.running:
                # Sleep for a bit before checking
                time.sleep(60)
                
                with self.lock:
                    current_time = time.time()
                    # Remove browsers that have been idle for too long
                    browsers_to_remove = [
                        instance for instance in self.pool
                        if (not instance.in_use and 
                            current_time - instance.last_used > self.settings.BROWSER_MAX_IDLE_TIME)
                    ]
                    
                    # Remove and quit each browser
                    for instance in browsers_to_remove:
                        try:
                            instance.driver.quit()
                        except Exception as e:
                            logger.error(f"Error quitting browser: {str(e)}")
                        self.pool.remove(instance)
                    
                    if browsers_to_remove:
                        logger.debug(f"Cleaned up {len(browsers_to_remove)} idle browsers")
        
        # Start the thread
        self.cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        self.cleanup_thread.start()
    
    def shutdown(self) -> None:
        """Shutdown the browser pool."""
        self.running = False
        
        with self.lock:
            for instance in self.pool:
                try:
                    instance.driver.quit()
                except Exception as e:
                    logger.error(f"Error quitting browser: {str(e)}")
            
            self.pool.clear()


@lru_cache()
def setup_browser_pool(settings: Settings) -> BrowserPool:
    """
    Set up the browser pool with caching.
    
    Args:
        settings: Application settings
        
    Returns:
        BrowserPool: Browser pool instance
    """
    return BrowserPool(settings)


def get_browser_pool_dependency(
    settings: Settings = Depends(get_settings_dependency)
) -> BrowserPool:
    """
    Get browser pool as a FastAPI dependency.
    
    Args:
        settings: Application settings
        
    Returns:
        BrowserPool: Browser pool instance
    """
    return setup_browser_pool(settings)