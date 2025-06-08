import asyncio
import json
import logging
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Enhanced WebSocket manager for notifications with connection tracking"""
    
    def __init__(self):
        # Store active connections with metadata
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        # Recent message signatures for deduplication
        self._recent_signatures: Dict[str, float] = {}
        # Deduplication window in seconds
        self._dedup_window: int = 2
        # Lock to protect signature map in concurrent broadcasts
        self._dedup_lock = asyncio.Lock()
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
        """Send a notification to all connected clients with proper error handling (with dedup)."""
        results = {
            "success": False,
            "total": len(self.active_connections),
            "delivered": 0,
            "failed": 0,
            "errors": []
        }

        # Deduplication check (concurrency-safe)
        signature = self._generate_signature(message)
        now = time.time()
        async with self._dedup_lock:
            last_sent_time = self._recent_signatures.get(signature)
            if last_sent_time and (now - last_sent_time) < self._dedup_window:
                logger.debug("Duplicate broadcast suppressed within dedup window")
                results["skipped"] = True
                return results
            # Record this message signature
            self._recent_signatures[signature] = now
            # Clean up old signatures
            expired = [sig for sig, ts in self._recent_signatures.items() if (now - ts) >= self._dedup_window]
            for sig in expired:
                self._recent_signatures.pop(sig, None)
        
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
        
        # Log delivery stats only if there were connections to deliver to
        if results["total"] > 0:
            logger.info(f"Notification broadcast results: {results['delivered']}/{results['total']} delivered")
        
        results["success"] = results["delivered"] > 0
        return results
    
    async def _generate_signature(self, message: Dict[str, Any]) -> str:
        """Generate a stable signature for a message excluding volatile timestamp fields"""
        def _strip_ts(obj: Any):
            if isinstance(obj, dict):
                return {k: _strip_ts(v) for k, v in obj.items() if k not in {"timestamp", "connected_at", "last_activity"}}
            if isinstance(obj, list):
                return [_strip_ts(v) for v in obj]
            return obj
        sanitized = _strip_ts(message)
        try:
            raw = json.dumps(sanitized, sort_keys=True, default=str)
        except Exception:
            # Fallback – non-serialisable objects
            raw = str(sanitized)
        return hashlib.md5(raw.encode()).hexdigest()
    
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
    # Note: FastAPI's WebSocket client attribute is just the remote address;
    # it does not support a timeout field. Attempting to set it breaks the
    # handshake with "'Address' object has no attribute 'timeout'".
    # Any inactivity timeout should be implemented via ping/pong (see below).
    
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

# Improved functions to publish notifications with better error handling
async def publish_event(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a notification to all connected WebSocket clients
    
    The payload sent over the wire follows this shape so that the
    frontend can easily pattern-match it:
    
        {
            "type": "notification",
            "data": { ... original notification dict ... }
        }
    """
    payload: Dict[str, Any] = {
        "type": "notification",
        "data": data.copy(),
    }
    # Enrich the inner data with mandatory fields
    if "timestamp" not in payload["data"]:
        payload["data"]["timestamp"] = datetime.utcnow().isoformat()
        
    try:
        # Send to all connected clients
        results = await websocket_manager.broadcast(payload)
        
        # Log results but don't stop notification delivery if WebSocket fails
        if not results["success"]:
            # Only log as warning if there were actually clients that failed to receive messages
            if results["total"] > 0:
                logger.warning(f"WebSocket broadcast had issues: {results['delivered']}/{results['total']} delivered")
                if results["errors"]:
                    for error in results["errors"][:3]:  # Log first few errors
                        logger.warning(f"WebSocket error: {error}")
                    if len(results["errors"]) > 3:
                        logger.warning(f"...and {len(results['errors']) - 3} more errors")
            else:
                # No clients connected, log at info level only
                logger.debug(f"WebSocket broadcast: No connected clients")
        
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

async def publish_notification(title: str, content: str, notification_type: str = "info", 
                          priority: int = 3, source: str = "system", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Specialized function to send a notification through WebSockets
    
    Args:
        title: Notification title
        content: Notification content
        notification_type: Type of notification (info, warning, error, success)
        priority: Priority level (1-5, where 5 is highest)
        source: Source of the notification
        metadata: Additional notification data
        
    Returns:
        Dict with delivery results
    """
    # Create notification data structure
    notification = {
        "title": title,
        "content": content,
        "type": notification_type,
        "priority": priority,
        "source": source,
        "read": False,
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": "notification",
        "id": f"notif_{int(datetime.utcnow().timestamp())}"
    }
    
    # Add metadata if provided
    if metadata:
        notification["metadata"] = metadata
    
    # Send as notification event
    return await publish_event(notification)