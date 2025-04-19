"""
Simple test script for the web scraper API endpoints
"""
import sys
import json
import requests
import time
from typing import Dict, Any

def test_trafilatura_endpoint() -> bool:
    """Test the Trafilatura API endpoint"""
    print("\n=== Testing /api/scrape/trafilatura endpoint ===")
    url = "http://localhost:5000/api/scrape/trafilatura"
    data = {
        "url": "https://example.com",
        "user_agent": "chrome-windows"
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Status: {result.get('status', 'unknown')}")
            print(f"Title: {result.get('data', {}).get('title', 'No title')}")
            content = result.get('data', {}).get('content', 'No content')
            print(f"Content snippet: {content[:150]}...")
            print("✅ Test passed!")
            return True
        else:
            print(f"Error: {response.text}")
            print("❌ Test failed!")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        print("❌ Test failed!")
        return False

def test_selenium_endpoint() -> bool:
    """Test the Selenium API endpoint"""
    print("\n=== Testing /api/scrape endpoint ===")
    url = "http://localhost:5000/api/scrape"
    data = {
        "url": "https://example.com",
        "user_agent": "chrome-windows",
        "selenium_options": {
            "headless": True,
            "disable_images": True,
            "wait_time": 2.0
        }
    }
    
    try:
        response = requests.post(url, json=data, timeout=60)  # Longer timeout for Selenium
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Status: {result.get('status', 'unknown')}")
            print(f"Title: {result.get('data', {}).get('title', 'No title')}")
            content = result.get('data', {}).get('content', 'No content')
            print(f"Content snippet: {content[:150]}...")
            print("✅ Test passed!")
            return True
        else:
            print(f"Error: {response.text}")
            print("❌ Test failed!")
            return False
    except Exception as e:
        print(f"Error: {str(e)}")
        print("❌ Test failed!")
        return False

def main():
    """Run all test functions"""
    print("Starting API tests...")
    
    # Test trafilatura endpoint
    trafilatura_success = test_trafilatura_endpoint()
    
    # Test selenium endpoint
    selenium_success = test_selenium_endpoint()
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Trafilatura API: {'✅ PASSED' if trafilatura_success else '❌ FAILED'}")
    print(f"Selenium API: {'✅ PASSED' if selenium_success else '❌ FAILED'}")
    
    # Return success only if both tests pass
    return 0 if (trafilatura_success and selenium_success) else 1

if __name__ == "__main__":
    sys.exit(main())