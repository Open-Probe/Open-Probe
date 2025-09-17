import time
from datetime import datetime
from fastapi import APIRouter
from ..models.search import HealthResponse
from ..config import settings
from ..utils.logging import get_logger

logger = get_logger("deepsearch.health")

router = APIRouter()

# Track application start time
app_start_time = time.time()

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify the API is running.
    
    Returns basic information about the service status and uptime.
    """
    current_time = time.time()
    uptime_seconds = current_time - app_start_time
    
    response = HealthResponse(
        status="healthy",
        version=settings.VERSION,
        timestamp=datetime.utcnow(),
        uptime_seconds=uptime_seconds
    )
    
    logger.debug("Health check requested")
    return response

@router.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """
    Detailed health check with system information.
    """
    current_time = time.time()
    uptime_seconds = current_time - app_start_time
    
    # Import here to avoid circular imports
    from ..services.session_manager import session_manager
    from ..services.websocket_service import websocket_manager
    
    session_stats = session_manager.get_session_stats()
    connection_stats = websocket_manager.get_connection_stats()
    
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "timestamp": datetime.utcnow(),
        "uptime_seconds": uptime_seconds,
        "config": {
            "max_concurrent_searches": settings.MAX_CONCURRENT_SEARCHES,
            "search_timeout": settings.SEARCH_TIMEOUT,
            "max_replan_iter": settings.MAX_REPLAN_ITER,
        },
        "sessions": session_stats,
        "websocket_connections": {
            "total_clients": connection_stats.get("total_clients", 0),
            "heartbeat_interval": settings.WS_HEARTBEAT_INTERVAL
        }
    }
