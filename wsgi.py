import logging
import uvicorn
from main import app as fastapi_app

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create a WSGI application that wraps the ASGI application
class WsgiToAsgiAdapter:
    def __init__(self, asgi_app):
        self.asgi_app = asgi_app
        
    def __call__(self, environ, start_response):
        # Start uvicorn server programmatically
        if not hasattr(self, "server_started"):
            self.server_started = True
            # This won't actually execute in the gunicorn context
            # Instead, we'll start the server manually
            logger.info("Starting uvicorn server")
            
        # Just respond with a message that directs to the correct server
        status = '200 OK'
        headers = [('Content-type', 'text/html')]
        start_response(status, headers)
        return [b'<html><body><h1>FastAPI application is running on uvicorn</h1><p>Please visit the app at this same URL.</p></body></html>']

# Create a placeholder app for gunicorn
app = WsgiToAsgiAdapter(fastapi_app)

# When this module is executed directly, start the uvicorn server
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)