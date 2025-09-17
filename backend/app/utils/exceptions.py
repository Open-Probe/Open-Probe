from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import HTTPException, status

class DeepSearchException(Exception):
    """Base exception for DeepSearch application."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "DEEPSEARCH_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)

class SearchException(DeepSearchException):
    """Exception raised during search operations."""
    
    def __init__(
        self,
        message: str,
        search_id: Optional[str] = None,
        step_id: Optional[str] = None,
        error_code: str = "SEARCH_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.search_id = search_id
        self.step_id = step_id
        super().__init__(message, error_code, details)

class WebSocketException(DeepSearchException):
    """Exception raised during WebSocket operations."""
    
    def __init__(
        self,
        message: str,
        client_id: Optional[str] = None,
        error_code: str = "WEBSOCKET_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.client_id = client_id
        super().__init__(message, error_code, details)

class SessionException(DeepSearchException):
    """Exception raised during session operations."""
    
    def __init__(
        self,
        message: str,
        session_id: Optional[str] = None,
        error_code: str = "SESSION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.session_id = session_id
        super().__init__(message, error_code, details)

class DeepSearchIntegrationException(DeepSearchException):
    """Exception raised when integrating with the DeepSearch system."""
    
    def __init__(
        self,
        message: str,
        graph_error: Optional[Exception] = None,
        error_code: str = "INTEGRATION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.graph_error = graph_error
        if details is None:
            details = {}
        if graph_error:
            details["original_error"] = str(graph_error)
        super().__init__(message, error_code, details)

# HTTP Exception builders
def create_http_exception(
    status_code: int,
    message: str,
    error_code: str,
    search_id: Optional[str] = None
) -> HTTPException:
    """Create a standardized HTTP exception."""
    detail = {
        "detail": message,
        "error_code": error_code,
        "timestamp": datetime.utcnow().isoformat(),
        "search_id": search_id
    }
    return HTTPException(status_code=status_code, detail=detail)

def search_not_found_exception(search_id: str) -> HTTPException:
    """Create a search not found exception."""
    return create_http_exception(
        status_code=status.HTTP_404_NOT_FOUND,
        message=f"Search with ID {search_id} not found",
        error_code="SEARCH_NOT_FOUND",
        search_id=search_id
    )

def search_already_running_exception(search_id: str) -> HTTPException:
    """Create a search already running exception."""
    return create_http_exception(
        status_code=status.HTTP_409_CONFLICT,
        message=f"Search {search_id} is already running",
        error_code="SEARCH_ALREADY_RUNNING",
        search_id=search_id
    )

def invalid_search_query_exception(query: str) -> HTTPException:
    """Create an invalid search query exception."""
    return create_http_exception(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=f"Invalid search query: {query}",
        error_code="INVALID_QUERY"
    )

def search_timeout_exception(search_id: str) -> HTTPException:
    """Create a search timeout exception."""
    return create_http_exception(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        message=f"Search {search_id} timed out",
        error_code="SEARCH_TIMEOUT",
        search_id=search_id
    )

def internal_server_error_exception(message: str = "Internal server error") -> HTTPException:
    """Create an internal server error exception."""
    return create_http_exception(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message=message,
        error_code="INTERNAL_ERROR"
    )
