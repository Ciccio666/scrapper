"""
Main entry point for the application.

This module imports the FastAPI application and starts the server.
"""

# Import the app from app_simple.py
import yaml
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import Dict, Any, Optional

from app_simple import app

# Add settings API endpoints directly to the app
@app.get("/api/settings_yaml", response_class=PlainTextResponse)
async def get_settings_yaml():
    """Get current settings in YAML format."""
    try:
        # Default settings
        settings = {
            "page_load_timeout": 30,
            "dynamic_content_wait": 2.0,
            "chatgpt_min_wait": 5.0,
            "chatgpt_max_wait": 8.0,
            "max_depth": 1,
            "max_pages_per_domain": 10,
            "restrict_to_domains": [],
            "follow_external_links": False,
            "ignore_query_strings": True,
            "exclude_url_patterns": []
        }
        
        return yaml.dump(settings, sort_keys=False)
    except Exception as e:
        print(f"Error getting settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting settings: {str(e)}")

@app.post("/api/settings_yaml", response_class=JSONResponse)
async def update_settings_yaml(request: Request):
    """Update settings from YAML format."""
    try:
        yaml_text = await request.body()
        settings = yaml.safe_load(yaml_text)
        
        # Validate settings
        if not isinstance(settings, dict):
            raise HTTPException(status_code=400, detail="Invalid YAML format")
        
        # Return the updated settings
        return settings
    except yaml.YAMLError as e:
        print(f"YAML parsing error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"YAML parsing error: {str(e)}")
    except Exception as e:
        print(f"Error updating settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating settings: {str(e)}")

# Also add a JSON endpoint for settings
@app.get("/api/settings", response_class=JSONResponse)
async def get_settings_json():
    """Get current settings in JSON format."""
    try:
        # Default settings
        settings = {
            "page_load_timeout": 30,
            "dynamic_content_wait": 2.0,
            "chatgpt_min_wait": 5.0,
            "chatgpt_max_wait": 8.0,
            "max_depth": 1,
            "max_pages_per_domain": 10,
            "restrict_to_domains": [],
            "follow_external_links": False,
            "ignore_query_strings": True,
            "exclude_url_patterns": []
        }
        
        return settings
    except Exception as e:
        print(f"Error getting settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting settings: {str(e)}")

@app.post("/api/settings", response_class=JSONResponse)
async def update_settings_json(settings: Dict[str, Any]):
    """Update settings from JSON format."""
    try:
        # Validate settings
        if not isinstance(settings, dict):
            raise HTTPException(status_code=400, detail="Invalid JSON format")
        
        # Return the updated settings
        return settings
    except Exception as e:
        print(f"Error updating settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating settings: {str(e)}")

# This allows running with 'python main.py'
if __name__ == "__main__":
    import uvicorn
    print("Starting web scraper application...")
    uvicorn.run(app, host="0.0.0.0", port=5000)