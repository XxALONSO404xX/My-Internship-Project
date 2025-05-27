import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Enhanced WebSocket manager for notifications with connection tracking"""
    
    def __init__(self):
        # Store active connections with metadata
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        # Set up periodic cleanup task
        self._setup_cleanup_task()
    
    def _setup_cleanup_task(self):
        """Set up a periodic task to clean up stale connections"""
        try:
            loop = asyncio.get_event_loop()
            self._cleanup_task = loop.create_task(self._periodic_cleanup())
        except RuntimeError:
            logger.warning("Could not setup WebSocket cleanup task - no event loop available")
    
    async def _periodic_cleanup(self):
        """Periodically check and clean up inactive connections"""
        while True:
            try:
                # Run cleanup every 5 minutes
                await asyncio.sleep(300)
                # Check all connections
                now = asyncio.get_event_loop().time()
                for client_id in list(self.active_connections.keys()):
                    conn_data = self.active_connections[client_id]
                    # Clean up connections inactive for more than 10 minutes
                    if now - conn_data.get('last_activity', 0) > 600:
                        logger.info(f"Cleaning up inactive connection for client {client_id}")
                        await self._close_connection(client_id)
            except asyncio.CancelledError:
                # Task being cancelled, clean up
                break
            except Exception as e:
                logger.error(f"Error in WebSocket cleanup: {str(e)}")
                # Keep the task running despite errors
                await asyncio.sleep(60)
    
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept a new WebSocket connection with improved tracking"""
        # Check if connection ID already exists - close the old one
        if client_id in self.active_connections:
            logger.warning(f"Client {client_id} reconnecting - closing previous connection")
            await self._close_connection(client_id)
            
        # Accept new connection
        await websocket.accept()
        
        # Store connection with metadata
        self.active_connections[client_id] = {
            'websocket': websocket,
            'connected_at': asyncio.get_event_loop().time(),
            'last_activity': asyncio.get_event_loop().time(),
            'message_count': 0
        }
        
        logger.info(f"Client {client_id} connected to notification stream")
    
    async def _close_connection(self, client_id: str) -> None:
        """Properly close a WebSocket connection"""
        if client_id in self.active_connections:
            try:
                conn_data = self.active_connections[client_id]
                websocket = conn_data.get('websocket')
                if websocket:
                    await websocket.close(code=1000)
            except Exception as e:
                logger.error(f"Error closing WebSocket for client {client_id}: {str(e)}")
            finally:
                # Always remove from active connections
                self.active_connections.pop(client_id, None)
    
    def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection"""
        # Schedule the proper async close
        if client_id in self.active_connections:
            asyncio.create_task(self._close_connection(client_id))
            logger.info(f"Client {client_id} disconnected from notification stream")
    
    async def broadcast(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send a notification to all connected clients with proper error handling"""
        results = {
            "success": False,
            "total": len(self.active_connections),
            "delivered": 0,
            "failed": 0,
            "errors": []
        }
        
        # Add timestamp to the message
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        # Send to each client with proper error handling
        for client_id in list(self.active_connections.keys()):
            try:
                success = await self.send_to_client(client_id, message)
                if success:
                    results["delivered"] += 1
                else:
                    results["failed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Error for client {client_id}: {str(e)}")
                logger.error(f"Broadcast error for client {client_id}: {str(e)}")
        
        # Log delivery stats
        logger.info(f"Notification broadcast results: {results['delivered']}/{results['total']} delivered")
        
        results["success"] = results["delivered"] > 0
        return results
    
    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Send a notification to a specific client with proper error handling"""
        if client_id not in self.active_connections:
            return False
        
        conn_data = self.active_connections[client_id]
        websocket = conn_data.get('websocket')
        if not websocket:
            logger.warning(f"Client {client_id} has no active websocket")
            await self._close_connection(client_id)
            return False
        
        try:
            # Send the message
            await websocket.send_json(message)
            
            # Update activity tracking
            conn_data['last_activity'] = asyncio.get_event_loop().time()
            conn_data['message_count'] += 1
            
            return True
        except RuntimeError as e:
            logger.error(f"Error sending notification to client {client_id}: {str(e)}")
            # Properly close the connection
            await self._close_connection(client_id)
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending to client {client_id}: {str(e)}")
            await self._close_connection(client_id)
            return False

# Create a global WebSocket manager instance
websocket_manager = WebSocketManager()

async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """Simple WebSocket endpoint for notification delivery"""
    # Add connection timeout for inactive clients
    websocket.client.timeout = 60.0  # 60 seconds timeout
    
    # Track connection in manager and send confirmation message
    await websocket_manager.connect(websocket, client_id)
    
    # Send welcome message to confirm connection
    try:
        await websocket.send_json({
            "type": "system",
            "event": "connected",
            "client_id": client_id,
            "message": "Successfully connected to notification service"
        })
    except Exception as e:
        logger.error(f"Failed to send welcome message to client {client_id}: {str(e)}")
        websocket_manager.disconnect(client_id)
        return
    
    try:
        # Set a ping interval to detect disconnected clients
        ping_interval = 30  # seconds
        last_ping = asyncio.get_event_loop().time()
        
        # Keep the connection alive
        while True:
            # Use wait_for to implement ping timeout mechanism
            try:
                # Wait for either client message or timeout
                message = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=ping_interval
                )
                
                # If client sends 'ping', respond with 'pong'
                if message == "ping":
                    await websocket.send_json({"type": "pong"})
                    
                # Update last ping time
                last_ping = asyncio.get_event_loop().time()
                    
            except asyncio.TimeoutError:
                # Send ping to check if client is still connected
                current_time = asyncio.get_event_loop().time()
                if current_time - last_ping >= ping_interval:
                    try:
                        await websocket.send_json({"type": "ping"})
                        last_ping = current_time
                    except Exception:
                        # Client likely disconnected
                        logger.info(f"Client {client_id} ping failed, disconnecting")
                        raise WebSocketDisconnect()
    
    except WebSocketDisconnect:
        # Normal disconnect
        logger.info(f"Client {client_id} disconnected normally")
        websocket_manager.disconnect(client_id)
    except Exception as e:
        # Error occurred
        logger.error(f"WebSocket error for client {client_id}: {str(e)}")
        websocket_manager.disconnect(client_id)

# Improved function to publish notifications with better error handling
async def publish_event(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a notification to all connected WebSocket clients
    
    Args:
        data: Notification data to send
        
    Returns:
        Dict with delivery results
        
    Raises:
        Exception: If there's a critical error that should interrupt notification flow
    """
    message = {
        "type": "notification",
        "data": data
    }
    
    try:
        # Send to all connected clients
        results = await websocket_manager.broadcast(message)
        
        # Log results but don't stop notification delivery if WebSocket fails
        if not results["success"]:
            logger.warning(f"WebSocket broadcast had issues: {results['delivered']}/{results['total']} delivered")
            if results["errors"]:
                for error in results["errors"][:3]:  # Log first few errors
                    logger.warning(f"WebSocket error: {error}")
                if len(results["errors"]) > 3:
                    logger.warning(f"...and {len(results['errors']) - 3} more errors")
        
        return results
    except Exception as e:
        # Log the error but don't re-raise - allow notification creation to continue
        logger.error(f"Failed to publish WebSocket event: {str(e)}", exc_info=True)
        return {
            "success": False, 
            "error": str(e),
            "total": 0,
            "delivered": 0,
            "failed": 0
        } 