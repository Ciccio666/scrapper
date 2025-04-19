"""
Rate limiting functionality for the application.

This module configures and provides rate limiting functionality
for API endpoints, preventing abuse and ensuring fair usage.
"""
from fastapi import Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import Settings, get_settings_dependency


# Create global limiter instance
limiter = Limiter(key_func=get_remote_address)


def get_limiter_dependency() -> Limiter:
    """
    Get rate limiter as a FastAPI dependency.
    
    Returns:
        Limiter: Rate limiter instance
    """
    return limiter


def get_rate_limit_for_request(
    request: Request, 
    settings: Settings = Depends(get_settings_dependency)
) -> str:
    """
    Get rate limit for a request based on client type.
    
    Args:
        request: FastAPI request object
        settings: Application settings
        
    Returns:
        str: Rate limit string (e.g. "30/minute")
    """
    # Check for API key (could be expanded to check for valid API key)
    if request.headers.get("X-API-Key"):
        return settings.RATE_LIMIT_PREMIUM
        
    # Default rate limit
    return settings.RATE_LIMIT_STANDARD