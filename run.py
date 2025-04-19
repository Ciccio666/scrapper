#!/usr/bin/env python3
"""
Run script for the web scraper application.
This script starts the server and runs comprehensive tests.
"""

import os
import time
import json
import subprocess
import requests
from typing import Dict, Any, Optional, List

# Constants
SERVER_URL = "http://localhost:5000"
TEST_URL = "https://example.com"
USER_AGENT = "chrome-windows"
SERVER_LOG_FILE = "server.log"
TIMEOUT = 30  # seconds
MAX_CONTENT_PREVIEW = 100  # characters

def start_server() -> int:
    """Start the server in the background and return the PID."""
    # Kill any existing uvicorn process
    subprocess.run(["pkill", "-f", "uvicorn"], capture_output=True)
    
    # Start the server
    print("Starting server...")
    process = subprocess.Popen(
        ["python", "-m", "uvicorn", "app_simple:app", "--host", "0.0.0.0", "--port", "5000"],
        stdout=open(SERVER_LOG_FILE, "w"),
        stderr=subprocess.STDOUT
    )
    pid = process.pid
    print(f"Server started with PID: {pid}")
    
    # Wait for server to initialize
    print("Waiting for server to initialize...")
    time.sleep(3)
    return pid

def check_server_health() -> bool:
    """Check if the server is running."""
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

def test_trafilatura_endpoint() -> Optional[Dict[str, Any]]:
    """Test the Trafilatura scraping endpoint."""
    try:
        response = requests.post(
            f"{SERVER_URL}/api/scrape/trafilatura",
            json={"url": TEST_URL, "user_agent": USER_AGENT},
            timeout=TIMEOUT
        )
        return response.json()
    except requests.RequestException as e:
        print(f"Error testing Trafilatura endpoint: {e}")
        return None

def test_selenium_endpoint() -> Optional[Dict[str, Any]]:
    """Test the Selenium scraping endpoint."""
    try:
        response = requests.post(
            f"{SERVER_URL}/api/scrape",
            json={"url": TEST_URL, "user_agent": USER_AGENT},
            timeout=TIMEOUT
        )
        return response.json()
    except requests.RequestException as e:
        print(f"Error testing Selenium endpoint: {e}")
        return None

def display_result(result: Dict[str, Any], endpoint_name: str) -> None:
    """Display the scraping result."""
    if not result or result.get("status") != "success":
        print(f"❌ Failed to scrape with {endpoint_name}")
        if result:
            print(f"Error: {result.get('error', 'Unknown error')}")
        return
    
    data = result.get("data", {})
    title = data.get("title", "No title")
    content = data.get("content", "No content")
    
    print(f"✅ Successfully scraped: {title}")
    
    # Content information
    content_length = len(content)
    print(f"Content length: {content_length} characters")
    
    # Preview content
    if content:
        preview = content[:MAX_CONTENT_PREVIEW] + "..." if len(content) > MAX_CONTENT_PREVIEW else content
        print("\nContent preview:")
        print("-" * 60)
        print(preview)
        print("-" * 60)
    
    # Metadata
    metadata = data.get("metadata", {})
    scrape_time = metadata.get("scrape_time_seconds", 0)
    print(f"\nScrape time: {scrape_time:.2f} seconds")
    
    # Element counts if available
    elements = metadata.get("elements", {})
    if elements:
        print("\nElement counts:")
        for element_type, count in elements.items():
            if element_type != "total":
                print(f"- {element_type}: {count}")

def main():
    """Run the tests."""
    print("=== Web Scraper API Test ===\n")
    
    # Start the server
    pid = start_server()
    
    # Check server health
    if check_server_health():
        print("✅ Server is running.\n")
    else:
        print("❌ Server is not running. Check the logs for details.")
        return
    
    # Test Trafilatura endpoint
    print("Testing web scraping with Trafilatura...\n")
    trafilatura_result = test_trafilatura_endpoint()
    if trafilatura_result:
        display_result(trafilatura_result, "Trafilatura")
    
    # Test Selenium endpoint
    print("\nTesting web scraping with Selenium...\n")
    selenium_result = test_selenium_endpoint()
    if selenium_result:
        display_result(selenium_result, "Selenium")
    
    # Success message
    print("\n✅ Web scraping tests completed!")
    print(f"Server is still running with PID: {pid}")
    print(f"Use 'kill {pid}' to stop it when done.")
    print(f"Server logs are in {SERVER_LOG_FILE}")

if __name__ == "__main__":
    main()