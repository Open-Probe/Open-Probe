import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from ..models.search import SearchResult, SearchStatus
from ..services.session_manager import SessionManager
from ..services.websocket_service import WebSocketManager
from ..services.deepsearch_adapter import DeepSearchAdapter, create_adapter
from ..utils.exceptions import SearchException, DeepSearchIntegrationException
from ..utils.logging import get_logger

logger = get_logger("deepsearch.search_service")

class SearchService:
    """Main service for handling search operations."""
    
    def __init__(
        self, 
        session_manager: SessionManager,
        websocket_manager: WebSocketManager
    ):
        self.session_manager = session_manager
        self.websocket_manager = websocket_manager
        self.adapter = create_adapter(websocket_manager, session_manager)
        self._running_tasks: Dict[str, asyncio.Task] = {}
    
    async def start_search(self, query: str) -> str:
        """Start a new search operation."""
        try:
            # Validate query
            if not query or not query.strip():
                raise SearchException("Query cannot be empty")
            
            # Create new search session
            search_id = self.session_manager.create_search_session(query.strip())
            
            # Start the search task in background
            task = asyncio.create_task(self._execute_search_task(query.strip(), search_id))
            self._running_tasks[search_id] = task
            
            logger.info(f"Started search {search_id} for query: {query}")
            return search_id
            
        except Exception as e:
            logger.error(f"Failed to start search: {e}")
            raise SearchException(f"Failed to start search: {str(e)}")
    
    async def _execute_search_task(self, query: str, search_id: str):
        """Execute the actual search in a background task."""
        try:
            logger.info(f"Executing search task for {search_id}")
            
            # Execute the search using the adapter
            final_answer = await self.adapter.execute_search(query, search_id)
            
            # Set the final answer
            self.session_manager.set_final_answer(search_id, final_answer)
            
            # Send completion message
            session = self.session_manager.get_session(search_id)
            if session:
                duration = session.duration_seconds or 0
                await self.websocket_manager.send_search_complete(
                    search_id=search_id,
                    result=final_answer,
                    total_steps=len(session.steps),
                    duration=duration
                )
            
            logger.info(f"Search {search_id} completed successfully")
            
        except DeepSearchIntegrationException as e:
            logger.error(f"DeepSearch integration error for {search_id}: {e}")
            self.session_manager.update_session_status(
                search_id, 
                SearchStatus.ERROR, 
                f"Integration error: {e.message}"
            )
            await self.websocket_manager.send_error(
                f"Search system error: {e.message}",
                search_id=search_id
            )
            
        except asyncio.CancelledError:
            logger.info(f"Search {search_id} was cancelled")
            self.session_manager.update_session_status(
                search_id, 
                SearchStatus.CANCELLED, 
                "Search was cancelled"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in search {search_id}: {e}")
            self.session_manager.update_session_status(
                search_id, 
                SearchStatus.ERROR, 
                f"Unexpected error: {str(e)}"
            )
            await self.websocket_manager.send_error(
                f"Search failed: {str(e)}",
                search_id=search_id
            )
        
        finally:
            # Clean up the running task
            self._running_tasks.pop(search_id, None)
    
    async def cancel_search(self, search_id: str) -> bool:
        """Cancel an active search."""
        try:
            # Check if search exists and is active
            if not self.session_manager.is_search_active(search_id):
                raise SearchException(f"Search {search_id} is not active", search_id=search_id)
            
            # Cancel the running task
            task = self._running_tasks.get(search_id)
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Update session status
            await self.adapter.cancel_search(search_id)
            
            logger.info(f"Search {search_id} cancelled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel search {search_id}: {e}")
            raise SearchException(f"Failed to cancel search: {str(e)}", search_id=search_id)
    
    async def get_search_status(self, search_id: str) -> Optional[SearchResult]:
        """Get the current status of a search."""
        return self.session_manager.get_session(search_id)
    
    async def new_chat(self) -> bool:
        """Start a new chat session by clearing all data."""
        try:
            # Cancel all running searches
            for search_id, task in list(self._running_tasks.items()):
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            self._running_tasks.clear()
            
            # Clear session data
            await self.adapter.clear_session()
            
            logger.info("New chat session started - all data cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start new chat: {e}")
            raise SearchException(f"Failed to start new chat: {str(e)}")
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        session_stats = self.session_manager.get_session_stats()
        connection_stats = self.websocket_manager.get_connection_stats()
        
        return {
            "sessions": session_stats,
            "connections": connection_stats,
            "running_tasks": len(self._running_tasks),
            "active_searches": list(self._running_tasks.keys())
        }

# Function to create search service instance
def create_search_service(
    session_manager: SessionManager,
    websocket_manager: WebSocketManager
) -> SearchService:
    return SearchService(session_manager, websocket_manager)
