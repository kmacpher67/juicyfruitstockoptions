import logging
import os
import sys
from typing import Optional
from app.config import settings

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
            logging.FileHandler("logs/stock_portal_debug.log"),
            logging.StreamHandler(sys.stdout)
        ],
        force=True
    )

    # Silence noisy libraries
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized in {env} mode (Level: {logging.getLevelName(log_level)})")
