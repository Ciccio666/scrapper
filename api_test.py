"""
Simplified test script for directly calling the API endpoints.
"""
import os
import sys
import time
import logging
from typing import Dict, Any, Optional, List, Union

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import FastAPI app and models
from app_simple import (
    app, scrape_web_content, scrape_with_trafilatura_endpoint,
    ScrapeRequest, SeleniumOptions, CrawlOptions
)

def test_trafilatura_directly():
    """Test the Trafilatura scraping function directly."""
    try:
        # Create a request object
        req = ScrapeRequest(
            url="https://example.com",
            user_agent="chrome-windows"
        )
        
        # Call the function directly
        logger.info("Testing Trafilatura scraping...")
        result = scrape_with_trafilatura_endpoint(req)
        
        # Print results
        logger.info(f"Result: {result}")
        return True
    except Exception as e:
        logger.error(f"Error in Trafilatura test: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing API functions directly...")
    success = test_trafilatura_directly()
    
    if success:
        print("Test passed!")
        sys.exit(0)
    else:
        print("Test failed!")
        sys.exit(1)