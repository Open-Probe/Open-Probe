"""
Dependency injection for FastAPI routes.

This module provides dependency functions that can be injected into FastAPI routes
for accessing shared resources like services and managers.
"""

from .services.search_service import SearchService
from .services.session_manager import SessionManager
from .services.websocket_service import WebSocketManager

# These will be set by main.py
_search_service: SearchService = None
_session_manager: SessionManager = None  
_websocket_manager: WebSocketManager = None

def set_dependencies(
    search_service: SearchService,
    session_manager: SessionManager,
    websocket_manager: WebSocketManager
):
    """Set the dependency instances (called from main.py)."""
    global _search_service, _session_manager, _websocket_manager
    _search_service = search_service
    _session_manager = session_manager
    _websocket_manager = websocket_manager

async def get_search_service() -> SearchService:
    """Get the search service instance."""
    if _search_service is None:
        raise RuntimeError("Search service not initialized")
    return _search_service

async def get_session_manager() -> SessionManager:
    """Get the session manager instance."""
    if _session_manager is None:
        raise RuntimeError("Session manager not initialized")
    return _session_manager

async def get_websocket_manager() -> WebSocketManager:
    """Get the WebSocket manager instance."""
    if _websocket_manager is None:
        raise RuntimeError("WebSocket manager not initialized")
    return _websocket_manager
