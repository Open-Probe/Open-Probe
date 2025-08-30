import logging
import sys
from typing import Optional
from ..config import settings

def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None
) -> None:
    """Configure logging for the application."""
    
    log_level = level or settings.LOG_LEVEL
    log_format = format_string or settings.LOG_FORMAT
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("socketio").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(name)

# Application loggers
app_logger = get_logger("deepsearch.app")
api_logger = get_logger("deepsearch.api")
ws_logger = get_logger("deepsearch.websocket")
search_logger = get_logger("deepsearch.search")
