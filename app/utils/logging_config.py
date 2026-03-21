import logging
import os
import sys
from typing import Optional


# Define TRACE level
TRACE_LEVEL_NUM = 5
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")

def trace(self, message, *args, **kws):
    if self.isEnabledFor(TRACE_LEVEL_NUM):
        # Yes, logger takes its '*args' as 'args'.
        self._log(TRACE_LEVEL_NUM, message, args, **kws)

logging.Logger.trace = trace

def setup_logging():
    """
    Standardizes logging across the application.
    Format: {datetime stamp} - {filename-class-method/function_name} - {LEVEL} - {message text}
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Determine log level based on environment
    from app.config import settings
    env = settings.ENVIRONMENT.lower()
    if env == "production":
        log_level = logging.DEBUG
    else:
        log_level = TRACE_LEVEL_NUM

    log_format = '%(asctime)s - %(filename)s-%(name)s-%(funcName)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler("logs/stock_portal_debug.log", delay=True)
        ],
        force=True
    )

    # Silence noisy libraries
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    
    # Root logger exists now, use it to log initialization
    logging.info(f"Logging initialized in {env} mode (Level: {logging.getLevelName(log_level)})")

from functools import wraps
import time

def log_endpoint(func):
    """
    Decorator to log endpoint entry, exit, and duration at TRACE level.
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.trace(f"Entering endpoint: {func.__name__}")
        start_time = time.perf_counter()
        try:
            return await func(*args, **kwargs)
        finally:
            duration = time.perf_counter() - start_time
            logger.trace(f"Exiting endpoint: {func.__name__} (Duration: {duration:.4f}s)")

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.trace(f"Entering endpoint: {func.__name__}")
        start_time = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            duration = time.perf_counter() - start_time
            logger.trace(f"Exiting endpoint: {func.__name__} (Duration: {duration:.4f}s)")

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper
