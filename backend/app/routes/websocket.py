import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.websocket_service import WebSocketManager
from ..utils.exceptions import WebSocketException
from ..utils.logging import get_logger

logger = get_logger("deepsearch.routes.websocket")

router = APIRouter(tags=["WebSocket"])

# Dependency to get WebSocket manager (will be injected)
async def get_websocket_manager() -> WebSocketManager:
    """Dependency to get the WebSocket manager instance."""
    from ..main import websocket_manager
    return websocket_manager

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time communication.
    
    Handles:
    - Client connections and disconnections
    - Real-time step updates during search
    - Search completion notifications
    - Error notifications
    - Session reset messages
    """
    # Get the WebSocket manager
    from ..main import websocket_manager
    
    client_id = None
    
    try:
        # Connect the client
        client_id = await websocket_manager.connect_client(websocket)
        logger.info(f"WebSocket client {client_id} connected")
        
        # Keep the connection alive and handle incoming messages
        while True:
            try:
                # Wait for incoming messages (mainly for connection testing)
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    await _handle_client_message(client_id, message, websocket_manager)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from client {client_id}: {data}")
                except Exception as e:
                    logger.error(f"Error handling message from client {client_id}: {e}")
                    
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected normally")
                break
            except Exception as e:
                logger.error(f"WebSocket error for client {client_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        if client_id:
            await websocket_manager.send_error(
                f"Connection error: {str(e)}",
                search_id=None
            )
    
    finally:
        # Clean up the client connection
        if client_id:
            await websocket_manager.disconnect_client(client_id)
            logger.info(f"WebSocket client {client_id} cleaned up")

async def _handle_client_message(
    client_id: str, 
    message: dict, 
    websocket_manager: WebSocketManager
):
    """Handle incoming messages from WebSocket clients."""
    
    message_type = message.get("type")
    
    if message_type == "ping":
        # Respond to ping with pong
        await websocket_manager.send_message_to_client(
            client_id,
            {
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {"message": "pong"}
            }
        )
        logger.debug(f"Responded to ping from client {client_id}")
        
    elif message_type == "subscribe":
        # Handle subscription requests (future feature)
        logger.info(f"Client {client_id} subscribed to updates")
        
    elif message_type == "unsubscribe":
        # Handle unsubscription requests (future feature)
        logger.info(f"Client {client_id} unsubscribed from updates")
        
    else:
        logger.warning(f"Unknown message type from client {client_id}: {message_type}")

# WebSocket connection management utilities
async def broadcast_to_all_clients(message: dict, websocket_manager: WebSocketManager):
    """Utility function to broadcast a message to all connected clients."""
    try:
        await websocket_manager.broadcast_message(message)
        logger.debug(f"Broadcasted message type: {message.get('type')}")
    except Exception as e:
        logger.error(f"Error broadcasting message: {e}")

async def send_to_client(client_id: str, message: dict, websocket_manager: WebSocketManager):
    """Utility function to send a message to a specific client."""
    try:
        await websocket_manager.send_message_to_client(client_id, message)
        logger.debug(f"Sent message to client {client_id}, type: {message.get('type')}")
    except WebSocketException as e:
        logger.error(f"WebSocket error sending to client {client_id}: {e.message}")
    except Exception as e:
        logger.error(f"Unexpected error sending to client {client_id}: {e}")
