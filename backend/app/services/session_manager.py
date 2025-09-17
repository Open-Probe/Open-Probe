import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from ..models.search import SearchResult, SearchStatus, ThinkingStep
from ..utils.exceptions import SessionException, SearchException
from ..utils.logging import get_logger

logger = get_logger("deepsearch.session")

class SessionManager:
    """In-memory session manager for handling search sessions."""
    
    def __init__(self):
        self._sessions: Dict[str, SearchResult] = {}
        self._active_searches: Set[str] = set()
        self._cleanup_interval = 300  # 5 minutes
        self._session_timeout = 1800  # 30 minutes
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def start_cleanup_task(self):
        """Start the background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
            logger.info("Session cleanup task started")
    
    async def stop_cleanup_task(self):
        """Stop the background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Session cleanup task stopped")
    
    async def _cleanup_expired_sessions(self):
        """Background task to clean up expired sessions."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._remove_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    async def _remove_expired_sessions(self):
        """Remove expired sessions from memory."""
        current_time = datetime.utcnow()
        expired_sessions = []
        
        for search_id, session in self._sessions.items():
            # Remove sessions that are completed and older than timeout
            if (session.status in [SearchStatus.COMPLETED, SearchStatus.ERROR, SearchStatus.CANCELLED] and
                session.end_time and 
                current_time - session.end_time > timedelta(seconds=self._session_timeout)):
                expired_sessions.append(search_id)
        
        for search_id in expired_sessions:
            del self._sessions[search_id]
            self._active_searches.discard(search_id)
            logger.info(f"Cleaned up expired session: {search_id}")
    
    def create_search_session(self, query: str) -> str:
        """Create a new search session."""
        search_id = str(uuid.uuid4())
        
        session = SearchResult(
            id=search_id,
            query=query,
            status=SearchStatus.THINKING,
            steps=[],
            start_time=datetime.utcnow()
        )
        
        self._sessions[search_id] = session
        self._active_searches.add(search_id)
        
        logger.info(f"Created new search session: {search_id}")
        return search_id
    
    def get_session(self, search_id: str) -> Optional[SearchResult]:
        """Get a search session by ID."""
        return self._sessions.get(search_id)
    
    def update_session_status(self, search_id: str, status: SearchStatus, error: Optional[str] = None):
        """Update the status of a search session."""
        session = self._sessions.get(search_id)
        if not session:
            raise SearchException(f"Session {search_id} not found", search_id=search_id)
        
        session.status = status
        if error:
            session.error = error
        
        if status in [SearchStatus.COMPLETED, SearchStatus.ERROR, SearchStatus.CANCELLED]:
            session.end_time = datetime.utcnow()
            session.duration_seconds = (session.end_time - session.start_time).total_seconds()
            self._active_searches.discard(search_id)
        
        logger.info(f"Updated session {search_id} status to {status}")
    
    def add_step(self, search_id: str, step: ThinkingStep):
        """Add a thinking step to a search session."""
        session = self._sessions.get(search_id)
        if not session:
            raise SearchException(f"Session {search_id} not found", search_id=search_id)
        
        # Check if step already exists and update it, otherwise add new
        existing_step_index = next(
            (i for i, s in enumerate(session.steps) if s.id == step.id), 
            None
        )
        
        if existing_step_index is not None:
            session.steps[existing_step_index] = step
            logger.debug(f"Updated step {step.id} in session {search_id}")
        else:
            session.steps.append(step)
            logger.debug(f"Added new step {step.id} to session {search_id}")
    
    def set_final_answer(self, search_id: str, answer: str):
        """Set the final answer for a search session."""
        session = self._sessions.get(search_id)
        if not session:
            raise SearchException(f"Session {search_id} not found", search_id=search_id)
        
        session.final_answer = answer
        self.update_session_status(search_id, SearchStatus.COMPLETED)
        logger.info(f"Set final answer for session {search_id}")
    
    def cancel_search(self, search_id: str, reason: Optional[str] = None):
        """Cancel an active search session."""
        session = self._sessions.get(search_id)
        if not session:
            raise SearchException(f"Session {search_id} not found", search_id=search_id)
        
        if search_id not in self._active_searches:
            raise SearchException(f"Search {search_id} is not active", search_id=search_id)
        
        self.update_session_status(search_id, SearchStatus.CANCELLED, error=reason)
        logger.info(f"Cancelled search session {search_id}: {reason}")
    
    def clear_all_sessions(self):
        """Clear all sessions (for new chat functionality)."""
        session_count = len(self._sessions)
        self._sessions.clear()
        self._active_searches.clear()
        logger.info(f"Cleared all sessions ({session_count} removed)")
    
    def get_session_stats(self) -> Dict[str, int]:
        """Get current session statistics."""
        total_sessions = len(self._sessions)
        active_sessions = len(self._active_searches)
        completed_sessions = sum(1 for s in self._sessions.values() 
                               if s.status == SearchStatus.COMPLETED)
        failed_sessions = sum(1 for s in self._sessions.values() 
                            if s.status == SearchStatus.ERROR)
        
        return {
            "total": total_sessions,
            "active": active_sessions,
            "completed": completed_sessions,
            "failed": failed_sessions
        }
    
    def is_search_active(self, search_id: str) -> bool:
        """Check if a search is currently active."""
        return search_id in self._active_searches

# Global session manager instance
session_manager = SessionManager()
