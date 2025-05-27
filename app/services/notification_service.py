"""Notification service for IoT Platform"""
import logging
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from sqlalchemy import select, desc, and_, or_, update, func
from sqlalchemy.ext.asyncio import AsyncSession
import re

from app.models.notification import Notification
from app.services.activity_service import ActivityService
from app.services.websocket_service import publish_event
from app.services.sms_service import sms_service
from config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for managing notifications"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.activity_service = ActivityService(db)
    
    async def get_all_notifications(self, 
                                   limit: int = 100, 
                                   offset: int = 0) -> List[Notification]:
        """Get all notifications with pagination"""
        query = select(Notification).order_by(desc(Notification.created_at)).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_notification_by_id(self, notification_id: int) -> Optional[Notification]:
        """Get a notification by ID"""
        return await self.db.get(Notification, notification_id)
    
    async def get_unread_notifications(self) -> List[Notification]:
        """Get all unread notifications"""
        query = select(Notification).where(Notification.is_read == False).order_by(desc(Notification.created_at))
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_notifications_by_priority(self, priority: int) -> List[Notification]:
        """Get notifications by priority level"""
        query = select(Notification).where(Notification.priority == priority).order_by(desc(Notification.created_at))
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_notification(self, 
                                 title: str,
                                 content: str,
                                 notification_type: str = "info",
                                 source: str = "system",
                                 source_id: Optional[int] = None,
                                 target_type: Optional[str] = None,
                                 target_id: Optional[int] = None,
                                 target_name: Optional[str] = None,
                                 priority: int = 3,
                                 recipients: List[str] = None,
                                 channels: List[str] = None,
                                 metadata: Dict[str, Any] = None) -> Notification:
        """
        Create a new notification
        
        Args:
            title: Notification title
            content: Notification content/body
            notification_type: Type of notification (info, warning, alert, error)
            source: Source of the notification (system, rule, user)
            source_id: ID of the source (e.g., rule_id)
            target_type: Type of target (device, group, system)
            target_id: ID of the target
            target_name: Name of the target
            priority: Priority level (1-5, where 5 is highest)
            recipients: List of recipient IDs or addresses
            channels: List of delivery channels
            metadata: Additional metadata for the notification_metadata field
        
        Returns:
            Created notification object
        """
        try:
            # Set default values for optional parameters
            if channels is None:
                channels = ["in_app"]
            
            if recipients is None:
                recipients = []
            
            if metadata is None:
                metadata = {}
            
            # Log inputs for debugging
            logger.debug(f"Creating notification with: title={title}, type={notification_type}, source={source}, "
                        f"channels={channels}, metadata={metadata}")
            
            # Create notification object
            notification = Notification(
                title=title,
                content=content,
                notification_type=notification_type,
                source=source,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                target_name=target_name,
                priority=priority,
                recipients=recipients,
                channels=channels,
                notification_metadata=metadata,  # This maps to the notification_metadata column
                status="pending",
                delivery_attempts=0
            )
            
            # Add to database and commit
            self.db.add(notification)
            await self.db.commit()
            await self.db.refresh(notification)
            
            # Log notification creation as a separate operation that won't cause the entire process to fail
            try:
                await self.activity_service.log_system_event(
                    action="create_notification",
                    description=f"Notification created: {notification.title}",
                    target_type="notification",
                    target_id=notification.id,
                    metadata={
                        "notification_type": notification_type,
                        "priority": priority,
                        "channels": channels
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log notification creation: {str(e)}")
            
            # Process notification delivery, but don't let delivery failure prevent creation
            try:
                await self._deliver_notification(notification)
            except Exception as e:
                logger.error(f"Failed to deliver notification {notification.id}: {str(e)}")
                notification.status = "delivery_failed"
                notification.status_message = f"Delivery error: {str(e)}"
                await self.db.commit()
            
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}", exc_info=True)
            raise
    
    async def mark_as_read(self, notification_id: int) -> Optional[Notification]:
        """Mark a notification as read"""
        notification = await self.get_notification_by_id(notification_id)
        if not notification:
            return None
        
        if notification.is_read:
            return notification
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(notification)
        
        return notification
    
    async def mark_all_as_read(self) -> int:
        """Mark all unread notifications as read"""
        query = select(Notification).where(Notification.is_read == False)
        result = await self.db.execute(query)
        notifications = result.scalars().all()
        
        count = 0
        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            count += 1
        
        await self.db.commit()
        return count
    
    async def delete_notification(self, notification_id: int) -> bool:
        """Delete a notification"""
        notification = await self.get_notification_by_id(notification_id)
        if not notification:
            return False
        
        await self.db.delete(notification)
        await self.db.commit()
        
        return True
    
    async def delete_old_notifications(self, days_to_keep: int = 30) -> int:
        """Delete notifications older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Delete old notifications
        query = Notification.__table__.delete().where(Notification.created_at < cutoff_date)
        result = await self.db.execute(query)
        await self.db.commit()
        
        return result.rowcount
    
    async def _deliver_notification(self, notification: Notification) -> Dict[str, Any]:
        """
        Process notification delivery through all specified channels
        
        Returns:
            Dict with delivery results for each channel
        """
        results = {}
        
        # Process each delivery channel
        for channel in notification.channels:
            try:
                # In-app notifications are always processed
                if channel == "in_app":
                    results["in_app"] = await self._deliver_in_app(notification)
                
                # Email delivery
                elif channel == "email":
                    results["email"] = await self._deliver_email(notification)
                
                # SMS delivery
                elif channel == "sms":
                    results["sms"] = await self._deliver_sms(notification)
                
                # Webhook delivery
                elif channel == "webhook":
                    results["webhook"] = await self._deliver_webhook(notification)
                
                else:
                    logger.warning(f"Unknown notification channel: {channel}")
                    results[channel] = {"success": False, "error": "Unknown channel"}
            
            except Exception as e:
                logger.error(f"Error delivering notification to {channel}: {str(e)}")
                results[channel] = {"success": False, "error": str(e)}
        
        # Update notification status
        if any(result.get("success", False) for result in results.values()):
            notification.status = "sent"
        else:
            notification.status = "failed"
            notification.status_message = "Failed to deliver to any channel"
        
        notification.delivery_attempts += 1
        notification.last_attempt = datetime.utcnow()
        if notification.notification_metadata is None:
            notification.notification_metadata = {}
        notification.notification_metadata["delivery_results"] = results
        
        await self.db.commit()
        
        return results
    
    async def _deliver_in_app(self, notification: Notification) -> Dict[str, Any]:
        """Deliver notification in-app via WebSocket with improved error handling"""
        try:
            # Prepare notification data
            notification_data = notification.to_dict()
            
            # Add theme-related styling for frontend to use
            # Include the soft green color scheme that user prefers
            notification_data["ui"] = {
                "theme": "green",
                "colors": {
                    "primary": "#4ade80",
                    "primaryDark": "#16a34a",
                    "primaryLight": "#dcfce7",
                    "background": "#f0fdf4"
                },
                "priority_style": self._get_priority_style(notification.priority)
            }
            
            # Send to WebSocket service with timeout to prevent blocking
            try:
                # Use asyncio.wait_for to add timeout
                import asyncio
                result = await asyncio.wait_for(
                    publish_event(notification_data),
                    timeout=2.0  # 2 second timeout for WebSocket delivery
                )
                
                # Check delivery stats
                if result.get("delivered", 0) > 0:
                    return {"success": True, "clients": result.get("delivered", 0)}
                else:
                    # No connected clients
                    return {"success": True, "warning": "No connected clients"}
                    
            except asyncio.TimeoutError:
                logger.warning(f"WebSocket delivery timed out for notification {notification.id}")
                return {"success": True, "warning": "WebSocket delivery timed out"}
            except Exception as ws_error:
                logger.warning(f"WebSocket delivery failed: {str(ws_error)}")
                return {"success": True, "warning": f"WebSocket delivery failed: {str(ws_error)}"}
                
        except Exception as e:
            logger.error(f"Failed to deliver in-app notification: {str(e)}")
            return {"success": False, "error": str(e)}
        
    def _get_priority_style(self, priority: str) -> Dict[str, str]:
        """Get UI styling based on notification priority while maintaining green theme"""
        if priority == "high":
            return {
                "backgroundColor": "#dcfce7",
                "borderColor": "#16a34a",
                "textColor": "#166534",
                "iconColor": "#16a34a"
            }
        elif priority == "medium":
            return {
                "backgroundColor": "#f0fdf4",
                "borderColor": "#4ade80",
                "textColor": "#166534",
                "iconColor": "#4ade80"
            }
        else:  # low priority
            return {
                "backgroundColor": "#f0fdf4",
                "borderColor": "#dcfce7",
                "textColor": "#14532d",
                "iconColor": "#86efac"
            }
    
    def _is_valid_email(self, email: str) -> bool:
        """
        Validate email address format using a more robust regex pattern
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        # More comprehensive email validation pattern
        # This checks for proper domain formation and standard email structure
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    async def _deliver_email(self, notification: Notification) -> Dict[str, Any]:
        """Deliver notification via email"""
        # Check if email sending is configured
        if not settings.SMTP_SERVER or not settings.SMTP_PORT:
            return {"success": False, "error": "Email delivery not configured"}
        
        # Check if there are recipients
        if not notification.recipients:
            return {"success": False, "error": "No email recipients specified"}
        
        # Validate email addresses
        valid_emails = []
        invalid_emails = []
        
        for email in notification.recipients:
            if self._is_valid_email(email):
                valid_emails.append(email)
            else:
                invalid_emails.append(email)
        
        if invalid_emails:
            logger.warning(f"Skipping invalid email addresses: {invalid_emails}")
        
        if not valid_emails:
            return {"success": False, "error": "No valid email addresses found in recipients"}
        
        try:
            # Create email
            msg = MIMEMultipart()
            msg["Subject"] = notification.title
            msg["From"] = settings.EMAIL_FROM_ADDRESS
            msg["To"] = ", ".join(valid_emails)
            
            # Email body - can be HTML or plain text
            body = notification.content
            msg.attach(MIMEText(body, "plain"))
            
            # Connect to SMTP server
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            
            # TLS if configured
            if settings.SMTP_USE_TLS:
                server.starttls()
            
            # Login if credentials provided
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to deliver email notification: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _deliver_sms(self, notification: Notification) -> Dict[str, Any]:
        """Deliver notification via SMS using SMS Service"""
        try:
            # Check if there are recipients
            if not notification.recipients:
                return {"success": False, "error": "No SMS recipients specified"}
            
            results = []
            
            # Send to each recipient
            for recipient in notification.recipients:
                try:
                    # Send via SMS service (which handles validation, retries and rate limiting)
                    result = await sms_service.send_alert_notification(
                        phone_number=recipient,
                        title=notification.title,
                        content=notification.content
                    )
                    
                    if result["success"]:
                        results.append({
                            "recipient": recipient,
                            "success": True,
                            "message_sid": result.get("message_sid", "unknown")
                        })
                    else:
                        results.append({
                            "recipient": recipient,
                            "success": False,
                            "error": result.get("error", "Unknown error"),
                            "queued": result.get("queued", False)
                        })
                except Exception as e:
                    results.append({
                        "recipient": recipient,
                        "success": False,
                        "error": str(e)
                    })
            
            # Check if any messages were sent successfully or queued for retry
            if any(r["success"] for r in results) or any(r.get("queued", False) for r in results):
                return {
                    "success": True,
                    "results": results
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to send SMS to any recipient",
                    "results": results
                }
            
        except Exception as e:
            logger.error(f"Failed to deliver SMS notification: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _deliver_webhook(self, notification: Notification) -> Dict[str, Any]:
        """Deliver notification via webhook (mock implementation)"""
        # In a real implementation, this would make HTTP requests to configured webhook URLs
        webhook_urls = notification.notification_metadata.get("webhook_urls", [])
        if not webhook_urls:
            return {"success": False, "error": "No webhook URLs configured"}
        
        logger.info(f"Webhook would be sent to {webhook_urls}: {notification.title}")
        return {"success": True, "mock": True}
    
    async def create_notification_with_clients(self, 
                                      title: str,
                                      content: str,
                                      client_ids: List[int],
                                      channels: List[str] = None,
                                      notification_type: str = "info",
                                      source: str = "system",
                                      source_id: Optional[int] = None,
                                      target_type: Optional[str] = None,
                                      target_id: Optional[int] = None,
                                      target_name: Optional[str] = None,
                                      priority: int = 3,
                                      metadata: Dict[str, Any] = None) -> Notification:
        """
        Create a new notification with proper client relationships
        
        Args:
            title: Notification title
            content: Notification content/body
            client_ids: List of client IDs who should receive this notification
            channels: List of delivery channels to use per client (in_app, email, sms, etc.)
            notification_type: Type of notification (info, warning, alert, error)
            source: Source of the notification (system, rule, user)
            source_id: ID of the source (e.g., rule_id)
            target_type: Type of target (device, group, system)
            target_id: ID of the target
            target_name: Name of the target
            priority: Priority level (1-5, where 5 is highest)
            metadata: Additional metadata
        
        Returns:
            Created notification object with client relationships
        """
        from app.models.notification_recipient import NotificationRecipient
        from app.models.client import Client
        
        try:
            # Set default values
            if channels is None:
                channels = ["in_app"]
            
            if metadata is None:
                metadata = {}
                
            # Create the notification object
            notification = Notification(
                title=title,
                content=content,
                notification_type=notification_type,
                source=source,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                target_name=target_name,
                priority=priority,
                notification_metadata=metadata,
                status="pending",
                delivery_attempts=0
            )
            
            # Add notification to database first to get an ID
            self.db.add(notification)
            await self.db.flush()
            
            # Query the clients to make sure they exist
            client_records = []
            if client_ids:
                query = select(Client).where(Client.id.in_(client_ids))
                result = await self.db.execute(query)
                client_records = result.scalars().all()
            
            # Create notification recipient records
            for client in client_records:
                for channel in channels:
                    recipient = NotificationRecipient(
                        notification_id=notification.id,
                        client_id=client.id,
                        delivery_channel=channel,
                        is_read=False,
                        is_delivered=False
                    )
                    self.db.add(recipient)
            
            # Commit changes
            await self.db.commit()
            await self.db.refresh(notification)
            
            # Log notification creation
            try:
                await self.activity_service.log_system_event(
                    action="create_notification",
                    description=f"Notification created for {len(client_records)} clients: {notification.title}",
                    target_type="notification",
                    target_id=notification.id,
                    metadata={
                        "notification_type": notification_type,
                        "priority": priority,
                        "channels": channels,
                        "client_count": len(client_records)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to log notification creation: {str(e)}")
            
            # Process notification delivery
            try:
                await self._deliver_notification(notification)
            except Exception as e:
                logger.error(f"Failed to deliver notification {notification.id}: {str(e)}")
                notification.status = "delivery_failed"
                notification.status_message = f"Delivery error: {str(e)}"
                await self.db.commit()
            
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification with clients: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise 