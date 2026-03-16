import logging
import os
from unittest.mock import patch
from app.utils.logging_config import setup_logging, TRACE_LEVEL_NUM
from app.config import settings

def test_trace_level_defined():
    """Verify TRACE level is correctly added to logging."""
    assert logging.getLevelName(TRACE_LEVEL_NUM) == "TRACE"
    logger = logging.getLogger("test_trace")
    assert hasattr(logger, "trace")

def test_logging_setup_development():
    """Verify development mode sets TRACE level."""
    with patch("app.config.settings.ENVIRONMENT", "development"):
        setup_logging()
        root_logger = logging.getLogger()
        assert root_logger.level == TRACE_LEVEL_NUM

def test_logging_setup_production():
    """Verify production mode sets DEBUG level."""
    with patch("app.config.settings.ENVIRONMENT", "production"):
        setup_logging()
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

def test_log_file_created():
    """Verify log file is created upon setup."""
    log_file = "logs/stock_portal_debug.log"
    if os.path.exists(log_file):
        os.remove(log_file)
    
    setup_logging()
    assert os.path.exists(log_file)
