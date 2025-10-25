import asyncio
import functools
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from backend.utils.logger import get_logger

logger = get_logger(__name__)

def with_retry(retries = 3, delay = 0.5, backoff = 2, exceptions=(OperationalError,)):
    """
        Decorator to retry async functions with exponential backoff.
        
        Parameters:
            -retries: max attempts
            -delay: initial delay in seconds
            -backoff: multiplier for delay
            -exceptions: tuple of exceptions to retry on
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == retries:
                        logger.exception(
                            "Function failed after max retries",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt,
                                "retries": retries,
                                "delay": current_delay,
                                "error": str(e),
                            }
                        )
                        raise
                    logger.exception(
                        "Retry attempt failed",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "retries": retries,
                            "delay": current_delay,
                            "error": str(e),
                        }
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        
        return wrapper
    return decorator