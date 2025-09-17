from fastapi import APIRouter, HTTPException, Depends
from ..models.search import (
    SearchRequest, 
    SearchResponse, 
    SearchStatusResponse, 
    NewChatResponse,
    CancelResponse,
    SearchResult
)
from ..services.search_service import SearchService
from ..utils.exceptions import (
    SearchException,
    search_not_found_exception,
    invalid_search_query_exception,
    internal_server_error_exception
)
from ..utils.logging import get_logger

logger = get_logger("deepsearch.routes.search")

router = APIRouter(prefix="/api/v1", tags=["Search"])

# Dependency to get search service (will be injected)
async def get_search_service() -> SearchService:
    """Dependency to get the search service instance."""
    # This will be set by the main application
    from ..main import search_service
    return search_service

@router.post("/search", response_model=SearchResponse)
async def start_search(
    request: SearchRequest,
    search_service: SearchService = Depends(get_search_service)
):
    """
    Start a new search operation.
    
    The search will be executed asynchronously and updates will be sent
    via WebSocket. The response contains a search ID to track progress.
    """
    try:
        # Validate query
        query = request.query.strip()
        if not query:
            raise invalid_search_query_exception("Query cannot be empty")
        
        if len(query) > 1000:
            raise invalid_search_query_exception("Query too long (max 1000 characters)")
        
        # Start the search
        search_id = await search_service.start_search(query)
        
        logger.info(f"Search started successfully: {search_id}")
        return SearchResponse(search_id=search_id)
        
    except SearchException as e:
        logger.error(f"Search error: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error starting search: {e}")
        raise internal_server_error_exception(f"Failed to start search: {str(e)}")

@router.get("/search/{search_id}/status", response_model=SearchStatusResponse)
async def get_search_status(
    search_id: str,
    search_service: SearchService = Depends(get_search_service)
):
    """
    Get the current status of a search operation.
    
    Returns the search status, current step information, and progress.
    """
    try:
        session = await search_service.get_search_status(search_id)
        
        if not session:
            raise search_not_found_exception(search_id)
        
        # Determine current step
        current_step = "idle"
        if session.steps:
            running_steps = [s for s in session.steps if s.status == "running"]
            if running_steps:
                current_step = running_steps[-1].title
            elif session.status == "thinking":
                current_step = "processing"
            elif session.status == "completed":
                current_step = "completed"
        
        # Calculate progress (rough estimate based on completed steps)
        progress = None
        if session.steps:
            completed_steps = sum(1 for s in session.steps if s.status == "completed")
            total_estimated_steps = max(len(session.steps), 4)  # Minimum 4 steps expected
            progress = min(int((completed_steps / total_estimated_steps) * 100), 95)
            
            if session.status == "completed":
                progress = 100
        
        return SearchStatusResponse(
            search_id=search_id,
            status=session.status,
            current_step=current_step,
            progress=progress
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting search status for {search_id}: {e}")
        raise internal_server_error_exception(f"Failed to get search status: {str(e)}")

@router.post("/search/{search_id}/cancel", response_model=CancelResponse)
async def cancel_search(
    search_id: str,
    search_service: SearchService = Depends(get_search_service)
):
    """
    Cancel an active search operation.
    
    This will stop the search process and mark it as cancelled.
    """
    try:
        success = await search_service.cancel_search(search_id)
        
        if not success:
            raise SearchException(f"Failed to cancel search {search_id}", search_id=search_id)
        
        logger.info(f"Search {search_id} cancelled successfully")
        return CancelResponse(message=f"Search {search_id} cancelled successfully")
        
    except SearchException as e:
        logger.error(f"Error cancelling search {search_id}: {e.message}")
        if "not found" in e.message.lower():
            raise search_not_found_exception(search_id)
        else:
            raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error cancelling search {search_id}: {e}")
        raise internal_server_error_exception(f"Failed to cancel search: {str(e)}")

@router.post("/new-chat", response_model=NewChatResponse)
async def new_chat(
    search_service: SearchService = Depends(get_search_service)
):
    """
    Start a new chat session.
    
    This will clear all previous search data and cancel any running searches.
    """
    try:
        success = await search_service.new_chat()
        
        if not success:
            raise SearchException("Failed to start new chat")
        
        logger.info("New chat session started")
        return NewChatResponse(message="Previous session cleared, ready for new search")
        
    except SearchException as e:
        logger.error(f"Error starting new chat: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error starting new chat: {e}")
        raise internal_server_error_exception(f"Failed to start new chat: {str(e)}")

@router.get("/search/{search_id}", response_model=SearchResult)
async def get_search_result(
    search_id: str,
    search_service: SearchService = Depends(get_search_service)
):
    """
    Get the complete search result including all steps and final answer.
    
    This endpoint returns the full search data for a given search ID.
    """
    try:
        session = await search_service.get_search_status(search_id)
        
        if not session:
            raise search_not_found_exception(search_id)
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting search result for {search_id}: {e}")
        raise internal_server_error_exception(f"Failed to get search result: {str(e)}")

@router.get("/stats")
async def get_service_stats(
    search_service: SearchService = Depends(get_search_service)
):
    """
    Get service statistics and metrics.
    
    Returns information about current sessions, connections, and performance.
    """
    try:
        return search_service.get_service_stats()
    except Exception as e:
        logger.error(f"Error getting service stats: {e}")
        raise internal_server_error_exception(f"Failed to get service stats: {str(e)}")
