import logging
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

from app.services.websocket_service import websocket_manager, websocket_endpoint

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/notifications")
async def notifications_websocket(websocket: WebSocket, client_id: Optional[str] = Query(None)):
    """
    WebSocket connection endpoint for real-time notifications
    
    To connect:
    1. Connect to /api/ws/notifications
    2. Optionally provide a client_id query parameter
    3. If no client_id is provided, a UUID will be generated
    
    This is a one-way connection where the server will push notifications to connected clients.
    No client messages are expected or processed.
    """
    # Generate client ID if not provided
    if not client_id:
        client_id = str(uuid.uuid4())
        
    try:
        # Handle WebSocket connection through the simplified connection manager
        await websocket_endpoint(websocket, client_id)
        
    except WebSocketDisconnect:
        logger.info(f"Notification client {client_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket notification error: {str(e)}") 