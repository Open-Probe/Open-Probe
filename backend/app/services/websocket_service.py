import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Set, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
from ..models.websocket import (
    WSMessage, 
    StepUpdateMessage, 
    SearchCompleteMessage, 
    ErrorMessage, 
    SessionResetMessage,
    ConnectionMessage,
    HeartbeatMessage,
    StepUpdateData,
    SearchCompleteData,
    ErrorData,
    SessionResetData,
    ConnectionData,
    HeartbeatData
)
from ..models.search import ThinkingStep
from ..utils.exceptions import WebSocketException
from ..utils.logging import get_logger

logger = get_logger("deepsearch.websocket")

class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}
        self._client_metadata: Dict[str, Dict] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_interval = 30  # seconds
        
    async def start_heartbeat(self):
        """Start the heartbeat task."""
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("WebSocket heartbeat started")
    
    async def stop_heartbeat(self):
        """Stop the heartbeat task."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            logger.info("WebSocket heartbeat stopped")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages to all connected clients."""
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                if self._connections:
                    await self._broadcast_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
    
    async def _broadcast_heartbeat(self):
        """Broadcast heartbeat to all connected clients."""
        message = HeartbeatMessage(
            timestamp=datetime.utcnow(),
            data=HeartbeatData(
                server_time=datetime.utcnow(),
                client_count=len(self._connections)
            )
        )
        await self.broadcast_message(message)
    
    async def connect_client(self, websocket: WebSocket) -> str:
        """Connect a new WebSocket client."""
        await websocket.accept()
        client_id = str(uuid.uuid4())
        
        self._connections[client_id] = websocket
        self._client_metadata[client_id] = {
            "connected_at": datetime.utcnow(),
            "last_seen": datetime.utcnow(),
        }
        
        logger.info(f"Client {client_id} connected. Total clients: {len(self._connections)}")
        
        # Send connection confirmation
        connection_message = ConnectionMessage(
            timestamp=datetime.utcnow(),
            data=ConnectionData(
                connected=True,
                client_id=client_id,
                server_time=datetime.utcnow()
            )
        )
        await self.send_message_to_client(client_id, connection_message)
        
        return client_id
    
    async def disconnect_client(self, client_id: str):
        """Disconnect a WebSocket client."""
        if client_id in self._connections:
            del self._connections[client_id]
            del self._client_metadata[client_id]
            logger.info(f"Client {client_id} disconnected. Total clients: {len(self._connections)}")
    
    async def send_message_to_client(self, client_id: str, message: WSMessage):
        """Send a message to a specific client."""
        websocket = self._connections.get(client_id)
        if not websocket:
            raise WebSocketException(f"Client {client_id} not found", client_id=client_id)
        
        try:
            # Convert message to dict and handle datetime serialization
            if hasattr(message, 'model_dump'):
                message_dict = message.model_dump()
            else:
                message_dict = message
            await websocket.send_text(json.dumps(message_dict, default=str))
            self._client_metadata[client_id]["last_seen"] = datetime.utcnow()
            logger.debug(f"Sent {message.type} message to client {client_id}")
        except Exception as e:
            logger.error(f"Failed to send message to client {client_id}: {e}")
            await self.disconnect_client(client_id)
    
    async def broadcast_message(self, message: WSMessage):
        """Broadcast a message to all connected clients."""
        if not self._connections:
            logger.debug("No clients to broadcast to")
            return
        
        disconnected_clients = []
        
        for client_id, websocket in self._connections.items():
            try:
                # Convert message to dict and handle datetime serialization
                if hasattr(message, 'model_dump'):
                    message_dict = message.model_dump()
                else:
                    message_dict = message
                await websocket.send_text(json.dumps(message_dict, default=str))
                self._client_metadata[client_id]["last_seen"] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Failed to send message to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect_client(client_id)
        
        logger.debug(f"Broadcasted {message.type} message to {len(self._connections)} clients")
    
    async def send_step_update(self, step: ThinkingStep, search_id: Optional[str] = None):
        """Send a step update to all clients."""
        message = StepUpdateMessage(
            timestamp=datetime.utcnow(),
            search_id=search_id,
            data=StepUpdateData(
                step_id=step.id,
                step_type=step.type,
                status=step.status,
                title=step.title,
                content=step.content,
                metadata=step.metadata
            )
        )
        await self.broadcast_message(message)
    
    async def send_search_complete(self, search_id: str, result: str, total_steps: int, duration: float):
        """Send search completion notification to all clients."""
        message = SearchCompleteMessage(
            timestamp=datetime.utcnow(),
            search_id=search_id,
            data=SearchCompleteData(
                search_id=search_id,
                result=result,
                total_steps=total_steps,
                duration=duration,
                final_answer=result
            )
        )
        await self.broadcast_message(message)
    
    async def send_error(self, error: str, search_id: Optional[str] = None, step_id: Optional[str] = None):
        """Send error notification to all clients."""
        message = ErrorMessage(
            timestamp=datetime.utcnow(),
            search_id=search_id,
            data=ErrorData(
                error=error,
                step_id=step_id,
                recoverable=True
            )
        )
        await self.broadcast_message(message)
    
    async def send_session_reset(self, reason: Optional[str] = None):
        """Send session reset notification to all clients."""
        message = SessionResetMessage(
            timestamp=datetime.utcnow(),
            data=SessionResetData(
                message="Session has been reset",
                reason=reason
            )
        )
        await self.broadcast_message(message)
    
    def get_connected_clients(self) -> List[str]:
        """Get list of connected client IDs."""
        return list(self._connections.keys())
    
    def get_client_count(self) -> int:
        """Get the number of connected clients."""
        return len(self._connections)
    
    def get_connection_stats(self) -> Dict:
        """Get connection statistics."""
        now = datetime.utcnow()
        return {
            "total_clients": len(self._connections),
            "client_metadata": {
                client_id: {
                    "connected_duration": (now - metadata["connected_at"]).total_seconds(),
                    "last_seen": metadata["last_seen"].isoformat()
                }
                for client_id, metadata in self._client_metadata.items()
            }
        }

# Global WebSocket manager instance
websocket_manager = WebSocketManager()
