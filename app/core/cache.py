"""
Caching functionality for the application.

This module provides caching mechanisms for API responses,
reducing load on the server and improving response times.
"""
import functools
from datetime import timedelta
from typing import Any, Callable, Optional, TypeVar, cast

from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache

from app.core.config import Settings


# Type variable for the decorated function
F = TypeVar("F", bound=Callable[..., Any])


def setup_cache(app: FastAPI, settings: Settings) -> None:
    """
    Initialize the caching system.
    
    Args:
        app: FastAPI application instance
        settings: Application settings
    """
    # Register cache initialization at startup
    @app.on_event("startup")
    async def startup_cache_init() -> None:
        """Initialize cache system on application startup."""
        if settings.CACHE_ENABLED:
            # Initialize with in-memory backend
            FastAPICache.init(
                InMemoryBackend(),
                prefix="webscraper-cache:",
                expire=settings.CACHE_TTL,
            )


def custom_cache(
    expire: Optional[int] = None,
    namespace: Optional[str] = None,
    key_builder: Optional[Callable[..., str]] = None
) -> Callable[[F], F]:
    """
    Custom cache decorator with additional features.
    
    Args:
        expire: Cache expiration time in seconds
        namespace: Cache namespace
        key_builder: Function to build cache key
        
    Returns:
        Callable: Decorator for caching function results
    """
    # Get key builder function
    actual_key_builder = key_builder or custom_key_builder
    
    # Create decorator using fastapi_cache
    decorator = cache(
        expire=expire,
        namespace=namespace or "custom",
        key_builder=actual_key_builder,
    )
    
    def wrapper(func: F) -> F:
        # Apply cache decorator
        return cast(F, decorator(func))
        
    return wrapper


def custom_key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    **kwargs: Any
) -> str:
    """
    Build a cache key based on function arguments.
    
    This key builder incorporates the function name, namespace,
    and all arguments (including keyword arguments) into the key.
    
    Args:
        func: Function being cached
        namespace: Cache namespace
        **kwargs: Additional arguments
        
    Returns:
        str: Cache key
    """
    # Extract cache arguments from kwargs
    cache_kwargs = kwargs.get("cache_kwargs", {})
    
    # Get function module and name
    module = func.__module__
    function_name = func.__name__
    
    # Build key components
    prefix = f"{namespace}:{module}.{function_name}"
    
    # Extract request from args if present
    request = cache_kwargs.get("request")
    if request:
        # Include URL path, query string, and body in key
        url = str(request.url)
        body = cache_kwargs.get("request_body", "")
        key = f"{prefix}:{url}:{body}"
    else:
        # Default key is just prefix
        key = prefix
        
    return key