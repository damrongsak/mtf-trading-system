import json
import functools
import logging
import hashlib
from typing import Optional, Any, Callable
from fastapi import Request, Response
from app.utils.redis_client import redis_client

logger = logging.getLogger(__name__)

def cached_response(ttl: int = 300, key_prefix: str = "api_cache"):
    """
    Decorator to cache FastAPI JSON responses in Redis.
    
    Args:
        ttl: Time to live in seconds (default 5 minutes).
        key_prefix: Prefix for the Redis key.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and current_user if available
            request = None
            user_id: str = "anonymous"
            
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # Try to find request in kwargs
                request = kwargs.get("request")
            
            # If no request object found, we can't reliably cache based on query params/user
            if not request:
                logger.warning(f"No Request object found in {func.__name__}, skipping cache")
                return await func(*args, **kwargs)

            # Check for Cache-Control: no-cache to bypass
            if request.headers.get("Cache-Control") == "no-cache":
                logger.info(f"Cache bypass requested for {request.url.path}")
                return await func(*args, **kwargs)

            # Get user from Depends(get_current_user) if present in kwargs
            current_user = kwargs.get("current_user")
            if current_user and hasattr(current_user, "id"):
                user_id = str(current_user.id)

            # Generate cache key based on path, query params, and user
            query_str = str(request.query_params)
            key_content = f"{request.url.path}:{query_str}:{user_id}"
            key_hash = hashlib.md5(key_content.encode()).hexdigest()
            cache_key = f"{key_prefix}:{key_hash}"

            try:
                client = await redis_client.get_client()
                cached_data = await client.get(cache_key)
                
                if cached_data:
                    logger.info(f"Cache HIT for {request.url.path} (key: {cache_key})")
                    return json.loads(cached_data)
                
                logger.info(f"Cache MISS for {request.url.path}")
                result = await func(*args, **kwargs)
                
                # Only cache successful success_response (dictionary)
                if isinstance(result, dict) and result.get("status") == "success":
                    await client.setex(
                        cache_key,
                        ttl,
                        json.dumps(result, default=str)
                    )
                
                return result
            except Exception as e:
                logger.error(f"Cache error: {e}")
                # Fallback to direct execution if Redis fails
                return await func(*args, **kwargs)
                
        return wrapper
    return decorator
from app.utils.redis_client import redis_client

class ExecutionCache:
    """
    Lightweight bridge for api-gateway to access Redis data 
    that is populated by the execution service (Events, NAV, etc).
    """
    @property
    def redis(self):
        # This is a bit of a hack to support the .redis.get() pattern in existing routers
        # In a real async context, we'd need to await get_client() first, but
        # decorators/routers might not be ready for that.
        # However, redis_client.client is set after the first get_client call.
        return MockRedisProxy()

class MockRedisProxy:
    """Helper to allow execution_cache.redis.xxx calls in a non-awaited way if needed, 
    but analytics.py uses 'await execution_cache.redis.get', so we just need to return the client."""
    def __getattr__(self, name):
        async def async_call(*args, **kwargs):
            client = await redis_client.get_client()
            method = getattr(client, name)
            return await method(*args, **kwargs)
        return async_call

execution_cache = ExecutionCache()
