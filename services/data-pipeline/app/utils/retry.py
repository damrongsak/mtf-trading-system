import asyncio
import logging
import functools
import random

logger = logging.getLogger(__name__)

def async_retry(max_retries=3, initial_delay=1, max_delay=10, exponential_base=2, exceptions=(Exception,)):
    """
    Decorator for async functions to retry on exception.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries. Error: {e}")
                        raise e
                    
                    logger.warning(f"Retry {retries}/{max_retries} for {func.__name__} after error: {e}. Waiting {delay}s...")
                    await asyncio.sleep(delay)
                    
                    delay = min(delay * exponential_base, max_delay)
                    # Add jitter
                    delay += random.uniform(0, 0.5)
        return wrapper
    return decorator
