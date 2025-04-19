import trafilatura
import logging
from urllib.parse import urlparse
from typing import Dict, Optional, Any, Union, List

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_website_text_content(url: str) -> str:
    """
    This function takes a url and returns the main text content of the website.
    The text content is extracted using trafilatura and easier to understand.
    The results are not raw HTML but clean text, making it more readable and
    easier to be summarized or processed.

    Args:
        url: The URL of the website to scrape

    Returns:
        str: The extracted text content of the website
        
    Some common website to crawl information from:
    MLB scores: https://www.mlb.com/scores/YYYY-MM-DD
    """
    logger.debug(f"Extracting text content from URL: {url}")
    
    # Send a request to the website
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        logger.warning(f"Failed to download content from {url}")
        return "Failed to download content from the provided URL."
    
    # Extract the main text content
    text = trafilatura.extract(downloaded)
    if not text:
        logger.warning(f"No text content extracted from {url}")
        return "No text content could be extracted from the provided URL."
    
    logger.debug(f"Successfully extracted {len(text)} characters of text from {url}")
    return text

def extract_metadata(url: str) -> Dict[str, Any]:
    """
    Extract metadata from a webpage using trafilatura.
    
    Args:
        url: The URL of the website to extract metadata from
        
    Returns:
        Dict[str, Any]: A dictionary containing metadata such as title, author, date, etc.
    """
    logger.debug(f"Extracting metadata from URL: {url}")
    
    # Send a request to the website
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        logger.warning(f"Failed to download content from {url}")
        return {"error": "Failed to download content"}
    
    # Extract metadata
    metadata = trafilatura.extract_metadata(downloaded)
    if not metadata:
        logger.warning(f"No metadata extracted from {url}")
        return {"title": "", "author": "", "date": "", "description": ""}
    
    # Convert trafilatura metadata to dictionary
    result = {
        "title": metadata.title if metadata.title else "",
        "author": metadata.author if metadata.author else "",
        "date": metadata.date if metadata.date else "",
        "description": metadata.description if metadata.description else "",
        "sitename": metadata.sitename if metadata.sitename else "",
        "categories": metadata.categories if metadata.categories else []
    }
    
    logger.debug(f"Successfully extracted metadata from {url}")
    return result

def get_domain(url: str) -> str:
    """
    Extract the domain from a URL.
    
    Args:
        url: The URL to extract the domain from
        
    Returns:
        str: The domain name
    """
    parsed_url = urlparse(url)
    return parsed_url.netloc

def is_valid_url(url: str) -> bool:
    """
    Check if a URL is valid.
    
    Args:
        url: The URL to validate
        
    Returns:
        bool: True if the URL is valid, False otherwise
    """
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def scrape_with_trafilatura(url: str, extract_metadata: bool = True) -> Dict[str, Any]:
    """
    Comprehensive function to scrape a website using trafilatura,
    including both content and metadata extraction.
    
    Args:
        url: The URL of the website to scrape
        extract_metadata: Whether to extract metadata along with content
        
    Returns:
        Dict[str, Any]: A dictionary containing the extracted content and metadata
    """
    if not is_valid_url(url):
        # Try adding https:// prefix if the URL doesn't have a scheme
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            if not is_valid_url(url):
                return {
                    "status": "error",
                    "error": "Invalid URL format",
                    "details": "The provided URL is not valid. Please include the protocol (http:// or https://)"
                }
        else:
            return {
                "status": "error",
                "error": "Invalid URL format",
                "details": "The provided URL is not valid. Please include the protocol (http:// or https://)"
            }
    
    logger.debug(f"Starting scrape of URL: {url}")
    
    try:
        # Send a request to the website
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {
                "status": "error",
                "error": "Failed to download content",
                "details": "The server was unable to download content from the provided URL."
            }
        
        # Extract the main text content
        content = trafilatura.extract(downloaded)
        
        result = {
            "status": "success",
            "data": {
                "content": content if content else "",
                "url": {
                    "original": url,
                    "domain": get_domain(url)
                },
                "metadata": {
                    "content_length": len(content) if content else 0,
                    "is_dynamic": False,  # Trafilatura doesn't use a browser
                }
            }
        }
        
        # Add metadata if requested
        if extract_metadata:
            metadata = trafilatura.extract_metadata(downloaded)
            if metadata:
                result["data"]["title"] = metadata.title if metadata.title else ""
                result["data"]["description"] = metadata.description if metadata.description else ""
                result["data"]["metadata"]["author"] = metadata.author if metadata.author else ""
                result["data"]["metadata"]["date"] = metadata.date if metadata.date else ""
                result["data"]["metadata"]["sitename"] = metadata.sitename if metadata.sitename else ""
                result["data"]["metadata"]["categories"] = metadata.categories if metadata.categories else []
            else:
                result["data"]["title"] = ""
                result["data"]["description"] = ""
        
        return result
        
    except Exception as e:
        logger.error(f"Error scraping URL {url}: {str(e)}")
        return {
            "status": "error",
            "error": "Scraping error",
            "details": str(e)
        }