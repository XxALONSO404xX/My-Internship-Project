"""
Consolidated messaging service for the IoT Platform.
This module combines functionality from:
- email_service.py: Email sending capabilities
- sms_service.py: SMS sending capabilities  
- notification_service.py: Platform notification management

The consolidation improves maintainability and reduces fragmentation
while preserving all original functionality.
"""
import logging
import smtplib
import ssl
import re
import asyncio
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from sqlalchemy import select, desc, and_, or_, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.models.notification import Notification
from app.services.activity_service import ActivityService
from app.services.websocket_service import publish_event
from config import settings

logger = logging.getLogger(__name__)


#
# ===== EMAIL SERVICE =====
#

class EmailService:
    """Service for sending emails with retry mechanism"""
    
    def __init__(self):
        # Initialize with empty values - will refresh before each send
        self.smtp_server = None
        self.smtp_port = None
        self.smtp_username = None
        self.smtp_password = None
        self.use_tls = None
        self.from_email = None
        self.from_name = None
        
        # Force TLS for Gmail (always required)
        self.is_gmail = False
        
        # Do initial refresh of credentials
        self.refresh_credentials()
        
    def refresh_credentials(self):
        """Refresh email credentials from settings"""
        # Fetch the latest credentials from settings
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM_ADDRESS
        self.from_name = settings.EMAIL_FROM_NAME
        
        # Check if using Gmail and force proper settings
        self.is_gmail = 'gmail.com' in self.smtp_server.lower()
        if self.is_gmail:
            # Gmail always requires TLS/SSL
            self.use_tls = True
            # Set proper port if using default Gmail
            if self.smtp_server == 'smtp.gmail.com' and self.smtp_port == 587:
                logger.info("Using Gmail SMTP with STARTTLS")
            elif self.smtp_server == 'smtp.gmail.com' and self.smtp_port == 465:
                logger.info("Using Gmail SMTP with SSL")
            else:
                # Fall back to standard TLS for other ports
                logger.warning(f"Unusual port {self.smtp_port} for Gmail - attempting TLS connection")
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)
        else:
            # For non-Gmail, use setting from config
            self.use_tls = settings.SMTP_USE_TLS
        
        # Log credential refresh (without sensitive details)
        logger.info(f"Email credentials refreshed for {self.from_email} using server {self.smtp_server}:{self.smtp_port} with TLS={self.use_tls}")
        
        # Queue for retrying failed emails
        self.retry_queue = []
        
        # Start background task for processing email queue
        self.is_processing_queue = False
        
    async def send_email(self, 
                         to_email: str, 
                         subject: str, 
                         body_html: str, 
                         body_text: str = None, 
                         reply_to: str = None,
                         cc: List[str] = None,
                         retry_on_failure: bool = True) -> Dict[str, Any]:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML body of the email
            body_text: Plain text body of the email (optional)
            reply_to: Reply-to email address (optional)
            cc: List of CC recipients (optional)
            retry_on_failure: Whether to retry sending on failure
            
        Returns:
            Dictionary with result of sending
        """
        # Refresh credentials before sending to ensure we have the latest
        self.refresh_credentials()
        
        try:
            # Check if email is configured
            if not self.smtp_server or not self.from_email:
                logger.warning("Email is not configured, skipping send")
                return {
                    "success": False,
                    "message": "Email service not configured",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Validate email address
            if not self._validate_email(to_email):
                logger.warning(f"Invalid email address: {to_email}")
                return {
                    "success": False,
                    "message": f"Invalid email address: {to_email}",
                    "timestamp": datetime.utcnow().isoformat()
                }

            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add CC if provided
            if cc:
                msg['Cc'] = ", ".join(cc)
                
            # Add Reply-To if provided
            if reply_to:
                msg['Reply-To'] = reply_to
                
            # Add plain text part if provided
            if body_text:
                part1 = MIMEText(body_text, 'plain')
                msg.attach(part1)
                
            # Add HTML part
            part2 = MIMEText(body_html, 'html')
            msg.attach(part2)
            
            # Connect to SMTP server with Gmail-specific handling
            try:
                # Gmail-specific connection handling
                if self.is_gmail:
                    if self.smtp_port == 587:
                        # Use STARTTLS for port 587 (Gmail standard)
                        logger.info(f"Using Gmail STARTTLS connection method on port 587")
                        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                        server.ehlo()
                        server.starttls()
                        server.ehlo()
                    elif self.smtp_port == 465:
                        # Use direct SSL for port 465
                        logger.info(f"Using Gmail direct SSL connection method on port 465")
                        context = ssl.create_default_context()
                        server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)
                    else:
                        # Fall back to standard TLS for other ports
                        logger.warning(f"Unusual port {self.smtp_port} for Gmail - attempting TLS connection")
                        context = ssl.create_default_context()
                        server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)
                else:
                    # Non-Gmail connection handling
                    if self.use_tls and self.smtp_port == 465:
                        # Direct SSL connection
                        logger.info(f"Using direct SSL connection to {self.smtp_server}:{self.smtp_port}")
                        context = ssl.create_default_context()
                        server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)
                    elif self.use_tls:
                        # STARTTLS for TLS on other ports
                        logger.info(f"Using STARTTLS connection to {self.smtp_server}:{self.smtp_port}")
                        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                        server.ehlo()
                        server.starttls()
                        server.ehlo()
                    else:
                        # Plain connection
                        logger.info(f"Using plain connection to {self.smtp_server}:{self.smtp_port}")
                        server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                        server.ehlo()
                
                # Login and send
                if self.smtp_username and self.smtp_password:
                    logger.info(f"Attempting login for {self.smtp_username}")
                    server.login(self.smtp_username, self.smtp_password)
                    logger.info(f"SMTP login successful for {self.smtp_username}")
                
                logger.info(f"Sending email to {to_email} with subject '{subject}'")
                server.send_message(msg)
                logger.info(f"Email sent successfully to {to_email}")
                
                # Close connection
                server.quit()
                
            except Exception as smtp_error:
                logger.error(f"SMTP Error: {str(smtp_error)}", exc_info=True)
                raise
                    
            logger.info(f"Email sent to {to_email}: {subject}")
            return {
                "success": True,
                "message": "Email sent successfully",
                "timestamp": datetime.utcnow().isoformat(),
                "to": to_email,
                "subject": subject
            }
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            
            # Add to retry queue if needed
            if retry_on_failure:
                self.retry_queue.append({
                    "to_email": to_email,
                    "subject": subject,
                    "body_html": body_html,
                    "body_text": body_text,
                    "reply_to": reply_to,
                    "cc": cc,
                    "timestamp": datetime.utcnow().isoformat(),
                    "retries": 0
                })
                
                # Start processing the queue if not already running
                if not self.is_processing_queue:
                    asyncio.create_task(self._process_retry_queue())
                    
            return {
                "success": False,
                "message": f"Error sending email: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
                "to": to_email,
                "subject": subject,
                "error": str(e),
                "in_retry_queue": retry_on_failure
            }
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address format"""
        # Basic email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    async def _process_retry_queue(self):
        """Process retry queue for failed emails"""
        if self.is_processing_queue:
            return
            
        self.is_processing_queue = True
        logger.info(f"Starting to process email retry queue, {len(self.retry_queue)} items")
        
        try:
            while self.retry_queue:
                # Get oldest item
                email_data = self.retry_queue[0]
                
                # Check if we've retried too many times (max 5 retries)
                if email_data.get("retries", 0) >= 5:
                    logger.warning(f"Dropping email after 5 retries: {email_data['subject']} to {email_data['to_email']}")
                    self.retry_queue.pop(0)
                    continue
                
                # Increment retry count
                email_data["retries"] += 1
                
                # Try to send again
                result = await self.send_email(
                    to_email=email_data["to_email"],
                    subject=email_data["subject"],
                    body_html=email_data["body_html"],
                    body_text=email_data["body_text"],
                    reply_to=email_data["reply_to"],
                    cc=email_data["cc"],
                    retry_on_failure=False  # Don't add to queue again to avoid recursion
                )
                
                if result["success"]:
                    # If successful, remove from queue
                    self.retry_queue.pop(0)
                    logger.info(f"Successfully sent email from retry queue: {email_data['subject']} to {email_data['to_email']}")
                else:
                    # Move to end of queue for later retry
                    self.retry_queue.pop(0)
                    self.retry_queue.append(email_data)
                    
                # Sleep between retries to avoid overwhelming the server
                await asyncio.sleep(10)
                
        except Exception as e:
            logger.error(f"Error processing email retry queue: {str(e)}")
            
        finally:
            self.is_processing_queue = False
    
    async def send_verification_email(self, email: str, username: str, token: str) -> Dict[str, Any]:
        """Send email verification email
        
        Args:
            email: Recipient email address
            username: Username of the recipient
            token: Verification token
            
        Returns:
            Result of sending the email
        """
        subject = "Verify Your IoT Platform Account"
        
        # Create HTML body
        verification_url = f"{settings.FRONTEND_URL.rstrip('/')}/verify-email/{token}"
        logger.info(f"MessagingService: sending verification email to {email} with URL: {verification_url}")
        body_html = f"""
        <html>
        <body>
            <h2>IoT Platform Account Verification</h2>
            <p>Hello {username},</p>
            <p>Thank you for registering! Please verify your email address by clicking the link below:</p>
            <p><a href="{verification_url}">Verify Email</a></p>
            <p>If you didn't register for an IoT Platform account, please ignore this email.</p>
            <p>The verification link will expire in 24 hours.</p>
            <p>Regards,<br>IoT Platform Team</p>
        </body>
        </html>
        """
        
        # Create plain text body
        body_text = f"""
        IoT Platform Account Verification
        
        Hello {username},
        
        Thank you for registering! Please verify your email address by visiting the link below:
        
        {verification_url}
        
        If you didn't register for an IoT Platform account, please ignore this email.
        
        The verification link will expire in 24 hours.
        
        Regards,
        IoT Platform Team
        """
        
        # Send the email
        result = await self.send_email(
            to_email=email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            retry_on_failure=True
        )
        
        return result
    
    async def send_password_reset_email(self, email: str, username: str, token: str) -> Dict[str, Any]:
        """Send password reset email
        
        Args:
            email: Recipient email address
            username: Username of the recipient
            token: Password reset token
            
        Returns:
            Result of sending the email
        """
        subject = "Reset Your IoT Platform Password"
        
        # Create HTML body
        reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password/{token}"
        logger.info(f"MessagingService: sending password reset email to {email} with URL: {reset_url}")
        body_html = f"""
        <html>
        <body>
            <h2>IoT Platform Password Reset</h2>
            <p>Hello {username},</p>
            <p>We received a request to reset your password. If you did not make this request, please ignore this email.</p>
            <p>To reset your password, click the link below:</p>
            <p><a href="{reset_url}">Reset Password</a></p>
            <p>The reset link will expire in 1 hour.</p>
            <p>Regards,<br>IoT Platform Team</p>
        </body>
        </html>
        """
        
        # Create plain text body
        body_text = f"""
        IoT Platform Password Reset
        
        Hello {username},
        
        We received a request to reset your password. If you did not make this request, please ignore this email.
        
        To reset your password, visit the link below:
        
        {reset_url}
        
        The reset link will expire in 1 hour.
        
        Regards,
        IoT Platform Team
        """
        
        # Send the email
        result = await self.send_email(
            to_email=email,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            retry_on_failure=True
        )
        
        return result


#
# ===== SMS SERVICE =====
#

class SMSService:
    """Service for sending SMS messages with retry mechanism and rate limiting"""
    
    def __init__(self):
        # SMS configuration from settings
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_PHONE_NUMBER
        
        # Queue for retrying failed SMS
        self.retry_queue = []
        
        # Rate limiting
        self.sent_messages = {}  # {phone_number: [timestamps]}
        self.max_per_hour = 5    # Maximum SMS per hour for one recipient
        self.max_per_day = 20    # Maximum SMS per day for one recipient
        
        # Start background task for processing SMS queue
        self.is_processing_queue = False
        
    async def send_sms(self, 
                      to_number: str, 
                      message: str,
                      retry_on_failure: bool = True) -> Dict[str, Any]:
        """
        Send an SMS message
        
        Args:
            to_number: Recipient phone number
            message: SMS message content
            retry_on_failure: Whether to retry sending on failure
            
        Returns:
            Dictionary with result of sending
        """
        try:
            # Check if SMS is configured
            if not self.account_sid or not self.auth_token or not self.from_number:
                logger.warning("SMS is not configured, skipping send")
                return {
                    "success": False,
                    "message": "SMS service not configured",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Validate phone number
            if not self._validate_phone_number(to_number):
                logger.warning(f"Invalid phone number: {to_number}")
                return {
                    "success": False,
                    "message": f"Invalid phone number: {to_number}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            # Check rate limits
            if not self._check_rate_limits(to_number):
                logger.warning(f"Rate limit exceeded for {to_number}")
                
                # Add to retry queue if needed, with delay
                if retry_on_failure:
                    self.retry_queue.append({
                        "to_number": to_number,
                        "message": message,
                        "timestamp": datetime.utcnow().isoformat(),
                        "retry_after": datetime.utcnow() + timedelta(hours=1),  # Try again after an hour
                        "retries": 0
                    })
                    
                    # Start processing the queue if not already running
                    if not self.is_processing_queue:
                        asyncio.create_task(self._process_retry_queue())
                        
                return {
                    "success": False,
                    "message": "Rate limit exceeded",
                    "timestamp": datetime.utcnow().isoformat(),
                    "to": to_number,
                    "in_retry_queue": retry_on_failure
                }
            
            # Initialize Twilio client
            client = Client(self.account_sid, self.auth_token)
            
            # Send SMS
            message = client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            
            # Record message for rate limiting
            self._record_sent_message(to_number)
            
            logger.info(f"SMS sent to {to_number}: {message.sid}")
            return {
                "success": True,
                "message": "SMS sent successfully",
                "timestamp": datetime.utcnow().isoformat(),
                "to": to_number,
                "message_sid": message.sid
            }
            
        except TwilioRestException as e:
            logger.error(f"Twilio error sending SMS to {to_number}: {str(e)}")
            
            # Add to retry queue if needed
            if retry_on_failure:
                self.retry_queue.append({
                    "to_number": to_number,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat(),
                    "retries": 0
                })
                
                # Start processing the queue if not already running
                if not self.is_processing_queue:
                    asyncio.create_task(self._process_retry_queue())
                    
            return {
                "success": False,
                "message": f"Twilio error: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
                "to": to_number,
                "error": str(e),
                "error_code": e.code,
                "in_retry_queue": retry_on_failure
            }
            
        except Exception as e:
            logger.error(f"Error sending SMS to {to_number}: {str(e)}")
            
            # Add to retry queue if needed
            if retry_on_failure:
                self.retry_queue.append({
                    "to_number": to_number,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat(),
                    "retries": 0
                })
                
                # Start processing the queue if not already running
                if not self.is_processing_queue:
                    asyncio.create_task(self._process_retry_queue())
                    
            return {
                "success": False,
                "message": f"Error sending SMS: {str(e)}",
                "timestamp": datetime.utcnow().isoformat(),
                "to": to_number,
                "error": str(e),
                "in_retry_queue": retry_on_failure
            }
    
    def _validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format"""
        # Basic phone validation (E.164 format)
        pattern = r'^\+[1-9]\d{1,14}$'
        return re.match(pattern, phone_number) is not None
    
    def _check_rate_limits(self, phone_number: str) -> bool:
        """Check if sending would exceed rate limits"""
        now = datetime.utcnow()
        
        # Initialize if this is first message to this number
        if phone_number not in self.sent_messages:
            self.sent_messages[phone_number] = []
            return True
            
        # Clean up old timestamps
        self.sent_messages[phone_number] = [
            ts for ts in self.sent_messages[phone_number] 
            if now - ts < timedelta(days=1)  # Keep messages from last 24 hours
        ]
        
        # Count messages in last hour
        hourly_count = sum(1 for ts in self.sent_messages[phone_number] 
                          if now - ts < timedelta(hours=1))
                          
        # Count messages in last day
        daily_count = len(self.sent_messages[phone_number])
        
        # Check limits
        return hourly_count < self.max_per_hour and daily_count < self.max_per_day
    
    def _record_sent_message(self, phone_number: str):
        """Record a sent message for rate limiting"""
        now = datetime.utcnow()
        
        if phone_number not in self.sent_messages:
            self.sent_messages[phone_number] = []
            
        self.sent_messages[phone_number].append(now)
    
    async def _process_retry_queue(self):
        """Process retry queue for failed SMS messages"""
        if self.is_processing_queue:
            return
            
        self.is_processing_queue = True
        logger.info(f"Starting to process SMS retry queue, {len(self.retry_queue)} items")
        
        try:
            while self.retry_queue:
                # Get oldest item
                sms_data = self.retry_queue[0]
                
                # Check if this is a rate-limited message with a retry_after time
                if "retry_after" in sms_data and datetime.utcnow() < datetime.fromisoformat(sms_data["retry_after"]):
                    # Move to end of queue for later retry
                    self.retry_queue.pop(0)
                    self.retry_queue.append(sms_data)
                    continue
                
                # Check if we've retried too many times (max 5 retries)
                if sms_data.get("retries", 0) >= 5:
                    logger.warning(f"Dropping SMS after 5 retries to {sms_data['to_number']}")
                    self.retry_queue.pop(0)
                    continue
                
                # Increment retry count
                sms_data["retries"] += 1
                
                # Try to send again
                result = await self.send_sms(
                    to_number=sms_data["to_number"],
                    message=sms_data["message"],
                    retry_on_failure=False  # Don't add to queue again to avoid recursion
                )
                
                if result["success"]:
                    # If successful, remove from queue
                    self.retry_queue.pop(0)
                    logger.info(f"Successfully sent SMS from retry queue to {sms_data['to_number']}")
                else:
                    # Move to end of queue for later retry
                    self.retry_queue.pop(0)
                    self.retry_queue.append(sms_data)
                    
                # Sleep between retries to avoid overwhelming the service
                await asyncio.sleep(10)
                
        except Exception as e:
            logger.error(f"Error processing SMS retry queue: {str(e)}")
            
        finally:
            self.is_processing_queue = False


#
# ===== NOTIFICATION SERVICE =====
#

class NotificationService:
    """Service for managing notifications with multi-channel delivery"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.activity_service = ActivityService(db)
        self.email_service = EmailService()
        self.sms_service = SMSService()
    
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
            notification_metadata=json.dumps(metadata) if metadata else None
        )
        
        # Add to database
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        
        # Record activity
        await self.activity_service.log_activity(
            activity_type="system_event",
            action="notification_created",
            description=f"Notification created: {title}",
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            metadata={
                "notification_id": notification.id,
                "notification_type": notification_type,
                "priority": priority,
                "source": source,
                "source_id": source_id
            }
        )
        
        # Dispatch to appropriate channels if specified
        if channels:
            await self._dispatch_notification(notification, recipients or [], channels)
        
        return notification
    
    async def mark_as_read(self, notification_id: int) -> bool:
        """Mark a notification as read"""
        notification = await self.get_notification_by_id(notification_id)
        if not notification:
            return False
            
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        await self.db.commit()
        return True
    
    async def mark_all_as_read(self) -> int:
        """Mark all notifications as read"""
        query = update(Notification).where(Notification.is_read == False).values(
            is_read=True,
            read_at=datetime.utcnow()
        )
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount
    
    async def delete_notification(self, notification_id: int) -> bool:
        """Delete a notification"""
        notification = await self.get_notification_by_id(notification_id)
        if not notification:
            return False
            
        await self.db.delete(notification)
        await self.db.commit()
        return True
    
    async def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        # Total count
        total_query = select(func.count()).select_from(Notification)
        total_result = await self.db.execute(total_query)
        total_count = total_result.scalar()
        
        # Unread count
        unread_query = select(func.count()).select_from(Notification).where(Notification.is_read == False)
        unread_result = await self.db.execute(unread_query)
        unread_count = unread_result.scalar()
        
        # Count by priority
        priority_counts = {}
        for priority in range(1, 6):  # Priorities 1-5
            priority_query = select(func.count()).select_from(Notification).where(Notification.priority == priority)
            priority_result = await self.db.execute(priority_query)
            priority_counts[f"priority_{priority}"] = priority_result.scalar()
        
        # Count by type
        type_query = select(Notification.notification_type, func.count())\
            .group_by(Notification.notification_type)
        type_result = await self.db.execute(type_query)
        type_counts = {row[0]: row[1] for row in type_result}
        
        return {
            "total": total_count,
            "unread": unread_count,
            "by_priority": priority_counts,
            "by_type": type_counts,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    async def _dispatch_notification(self, 
                                    notification: Notification, 
                                    recipients: List[str] = None,
                                    channels: List[str] = None) -> Dict[str, Any]:
        """Dispatch notification to specified channels"""
        if not channels:
            # Default to websocket notification
            channels = ["websocket"]
            
        results = {}
        
        # Convert notification to dict for transmission
        notification_data = {
            "id": notification.id,
            "title": notification.title,
            "content": notification.content,
            "type": notification.notification_type,
            "priority": notification.priority,
            "source": notification.source,
            "target_type": notification.target_type,
            "target_name": notification.target_name,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
            "is_read": notification.is_read
        }
        
        # Add metadata if present
        if notification.notification_metadata:
            try:
                metadata = json.loads(notification.notification_metadata)
                notification_data["metadata"] = metadata
            except:
                pass
        
        # Websocket notification
        if "websocket" in channels:
            try:
                # Publish the notification using a single dictionary argument as required
                await publish_event(notification_data)
                results["websocket"] = {"success": True}
            except Exception as e:
                logger.error(f"Error publishing websocket notification: {str(e)}")
                results["websocket"] = {"success": False, "error": str(e)}
        
        # Email notification
        if "email" in channels and recipients:
            email_results = []
            for recipient in recipients:
                if self._validate_email(recipient):
                    # Create HTML email body
                    html_body = f"""
                    <html>
                    <body>
                        <h2>{notification.title}</h2>
                        <p>{notification.content}</p>
                        <p>Priority: {notification.priority}</p>
                        <p>Time: {notification.created_at.isoformat() if notification.created_at else datetime.utcnow().isoformat()}</p>
                    </body>
                    </html>
                    """
                    
                    # Send email
                    try:
                        email_result = await self.email_service.send_email(
                            to_email=recipient,
                            subject=f"[IoT Platform] {notification.title}",
                            body_html=html_body,
                            body_text=notification.content
                        )
                        email_results.append({"recipient": recipient, "result": email_result})
                    except Exception as e:
                        logger.error(f"Error sending email notification to {recipient}: {str(e)}")
                        email_results.append({"recipient": recipient, "error": str(e)})
                        
            results["email"] = email_results
            
        # SMS notification
        if "sms" in channels and recipients:
            sms_results = []
            for recipient in recipients:
                if self._validate_phone_number(recipient):
                    # Create SMS message
                    sms_content = f"{notification.title}: {notification.content}"
                    if len(sms_content) > 160:
                        sms_content = sms_content[:157] + "..."
                    
                    # Send SMS
                    try:
                        sms_result = await self.sms_service.send_sms(
                            to_number=recipient,
                            message=sms_content
                        )
                        sms_results.append({"recipient": recipient, "result": sms_result})
                    except Exception as e:
                        logger.error(f"Error sending SMS notification to {recipient}: {str(e)}")
                        sms_results.append({"recipient": recipient, "error": str(e)})
                        
            results["sms"] = sms_results
            
        return results
    
    # ------------------------------------------------------------------
    # Internal validation helpers (proxy to EmailService / SMSService)
    # ------------------------------------------------------------------
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address using the underlying EmailService helper."""
        return self.email_service._validate_email(email)
    
    def _validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number using the underlying SMSService helper."""
        return self.sms_service._validate_phone_number(phone_number)
    
    async def send_notification(self, notification_id: int, channel: str) -> Dict[str, Any]:
        """
        Send a notification through a specific channel
        
        Args:
            notification_id: ID of the notification to send
            channel: Channel to send through (email, sms, websocket, in_app)
            
        Returns:
            Result of the sending operation
        """
        # Get the notification
        notification = await self.get_notification_by_id(notification_id)
        if not notification:
            return {"success": False, "error": f"Notification with ID {notification_id} not found"}
        
        # Check if notification has recipients info in metadata
        recipients = []
        if notification.notification_metadata:
            try:
                metadata = json.loads(notification.notification_metadata)
                if "recipients" in metadata and isinstance(metadata["recipients"], list):
                    recipients = metadata["recipients"]
            except Exception as e:
                logger.error(f"Error parsing notification metadata: {str(e)}")
        
        # If no recipients in metadata, return error
        if not recipients:
            return {"success": False, "error": "No recipients found for notification"}
        
        # Dispatch to the specified channel
        results = await self._dispatch_notification(notification, recipients, [channel])
        
        # Update notification with delivery status
        notification.delivery_status = json.dumps(results)
        notification.updated_at = datetime.utcnow()
        await self.db.commit()
        
        return {"success": True, "results": results}


# Create singleton instances
email_service = EmailService()
sms_service = SMSService()


def create_notification_service(db: AsyncSession) -> NotificationService:
    """Factory function to create a notification service instance"""
    return NotificationService(db)
