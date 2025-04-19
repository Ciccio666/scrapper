"""
Main application file for the FastAPI web scraper.
This is a simpler version of the app that just imports and runs the FastAPI app.
The actual application code is in app_simple.py.
"""

# Just import the app from app_simple.py
from app_simple import app

# This allows running with 'python app.py'
if __name__ == "__main__":
    import uvicorn
    print("Starting web scraper application...")
    uvicorn.run(app, host="0.0.0.0", port=5000)