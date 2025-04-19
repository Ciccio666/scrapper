#!/usr/bin/env python3
"""
Simple test script for the web scraper API endpoints.
This script runs directly with Python and will test the Trafilatura API endpoint.
"""
import sys
import requests
import json
import time

def test_health_endpoint():
    """Test the health endpoint to check if server is running."""
    try:
        response = requests.get("http://localhost:5000/health")
        if response.status_code == 200:
            print("✅ Health check passed!")
            return True
        else:
            print(f"❌ Health check failed with status code {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error connecting to server: {str(e)}")
        return False

def test_trafilatura_endpoint():
    """Test the Trafilatura API endpoint."""
    try:
        # Make the request
        response = requests.post(
            "http://localhost:5000/api/scrape/trafilatura",
            json={"url": "https://example.com", "user_agent": "chrome-windows"}
        )
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            print("Success! API returned:")
            print(json.dumps(result, indent=2)[:500] + "...")  # Show truncated response
            print("\n✅ Trafilatura API test passed!")
            return True
        else:
            print(f"❌ API test failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing API: {str(e)}")
        return False

def main():
    """Run all test functions."""
    
    # Try health check first
    server_running = test_health_endpoint()
    
    if not server_running:
        print("Server doesn't appear to be running.")
        print("Make sure to start the server with: uvicorn app_simple:app --host 0.0.0.0 --port 5000")
        return 1
    
    # Test Trafilatura API
    print("\nTesting Trafilatura API...")
    api_success = test_trafilatura_endpoint()
    
    # Return appropriate exit code
    if api_success:
        print("\nAll tests passed successfully!")
        return 0
    else:
        print("\nSome tests failed. See output for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())