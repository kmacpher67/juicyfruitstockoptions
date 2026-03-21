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

from app.utils.logging_config import log_endpoint

def test_endpoint_logging():
    """Verify that calling a decorated function produces TRACE logs with duration."""
    log_file = "logs/stock_portal_debug.log"
    if os.path.exists(log_file):
        os.remove(log_file)
    
    with patch("app.config.settings.ENVIRONMENT", "development"):
        setup_logging()
        
        @log_endpoint
        async def mock_async_endpoint():
            return {"status": "ok"}
            
        @log_endpoint
        def mock_sync_endpoint():
            return {"status": "ok"}
            
        import asyncio
        asyncio.run(mock_async_endpoint())
        mock_sync_endpoint()
        
        # Read log file
        with open(log_file, "r") as f:
            log_content = f.read()
            
        assert "Entering endpoint: mock_async_endpoint" in log_content
        assert "Exiting endpoint: mock_async_endpoint" in log_content
        assert "Entering endpoint: mock_sync_endpoint" in log_content
        assert "Exiting endpoint: mock_sync_endpoint" in log_content
        assert "Duration:" in log_content
