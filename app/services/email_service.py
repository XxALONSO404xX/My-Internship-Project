"""Service for sending emails in the IoT platform"""
import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails"""
    
    def __init__(self):
        # Email configuration from settings
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.use_tls = settings.SMTP_USE_TLS
        self.from_email = settings.EMAIL_FROM_ADDRESS
        self.from_name = settings.EMAIL_FROM_NAME
        
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
        try:
            if not self.smtp_server or not self.smtp_username or not self.smtp_password:
                logger.warning("SMTP not properly configured. Email not sent.")
                return {"success": False, "error": "SMTP not configured"}
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>" if self.from_name else self.from_email
            msg['To'] = to_email
            
            # Add CC if provided
            if cc:
                msg['Cc'] = ", ".join(cc)
                
            # Add Reply-To if provided
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # Add plain text body if provided, otherwise use HTML
            if body_text:
                msg.attach(MIMEText(body_text, 'plain'))
            else:
                # Extract text from HTML as fallback
                body_text = self._html_to_text(body_html)
                msg.attach(MIMEText(body_text, 'plain'))
            
            # Add HTML body
            msg.attach(MIMEText(body_html, 'html'))
            
            # Create SMTP connection
            if self.use_tls:
                context = ssl.create_default_context()
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls(context=context)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
            # Login and send
            server.login(self.smtp_username, self.smtp_password)
            
            # Get all recipients
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
                
            server.sendmail(self.from_email, recipients, msg.as_string())
            server.quit()
            
            logger.info(f"Email sent to {to_email}: {subject}")
            return {"success": True}
            
        except Exception as e:
            error_msg = f"Error sending email: {str(e)}"
            logger.error(error_msg)
            
            # Add to retry queue if requested
            if retry_on_failure:
                self.retry_queue.append({
                    "to_email": to_email,
                    "subject": subject,
                    "body_html": body_html,
                    "body_text": body_text,
                    "reply_to": reply_to,
                    "cc": cc,
                    "attempts": 1,
                    "last_attempt": datetime.utcnow()
                })
                
                # Start processing queue if not already running
                if not self.is_processing_queue:
                    asyncio.create_task(self._process_retry_queue())
            
            return {"success": False, "error": error_msg}
    
    async def send_verification_email(self, email: str, username: str, token: str) -> Dict[str, Any]:
        """
        Send account verification email
        
        Args:
            email: Recipient email address
            username: Username of the recipient
            token: Verification token
            
        Returns:
            Dictionary with result of sending
        """
        subject = "Verify Your Account"
        
        # Create verification link
        base_url = settings.FRONTEND_URL
        verification_link = f"{base_url}/verify-email?token={token}"
        
        # Create HTML body
        body_html = f"""
        <html>
            <body>
                <h2>Welcome to the IoT Platform!</h2>
                <p>Hello {username},</p>
                <p>Thank you for registering. Please verify your account by clicking the button below:</p>
                <p>
                    <a href="{verification_link}" style="background-color: #4CAF50; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">
                        Verify Account
                    </a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p>{verification_link}</p>
                <p>This link will expire in 24 hours.</p>
                <p>If you didn't create this account, please ignore this email.</p>
                <p>Best regards,</p>
                <p>IoT Platform Team</p>
            </body>
        </html>
        """
        
        # Send email
        return await self.send_email(to_email=email, subject=subject, body_html=body_html)
    
    async def send_password_reset_email(self, email: str, username: str, token: str) -> Dict[str, Any]:
        """
        Send password reset email
        
        Args:
            email: Recipient email address
            username: Username of the recipient
            token: Password reset token
            
        Returns:
            Dictionary with result of sending
        """
        subject = "Reset Your Password"
        
        # Create reset link
        base_url = settings.FRONTEND_URL
        reset_link = f"{base_url}/reset-password?token={token}"
        
        # Create HTML body
        body_html = f"""
        <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Hello {username},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <p>
                    <a href="{reset_link}" style="background-color: #2196F3; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px;">
                        Reset Password
                    </a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p>{reset_link}</p>
                <p>This link will expire in 1 hour. If you didn't request a password reset, please ignore this email.</p>
                <p>Best regards,</p>
                <p>IoT Platform Team</p>
            </body>
        </html>
        """
        
        # Send email
        return await self.send_email(to_email=email, subject=subject, body_html=body_html)
    
    async def _process_retry_queue(self) -> None:
        """Process the retry queue for failed emails"""
        if self.is_processing_queue:
            return
            
        self.is_processing_queue = True
        
        try:
            while self.retry_queue:
                # Get oldest email from queue
                email_data = self.retry_queue.pop(0)
                
                # Check if max attempts reached
                if email_data["attempts"] >= 3:
                    logger.warning(f"Max retry attempts reached for email to {email_data['to_email']}: {email_data['subject']}")
                    continue
                
                # Try sending again
                try:
                    await self.send_email(
                        to_email=email_data["to_email"],
                        subject=email_data["subject"],
                        body_html=email_data["body_html"],
                        body_text=email_data["body_text"],
                        reply_to=email_data["reply_to"],
                        cc=email_data["cc"],
                        retry_on_failure=False  # Don't add to queue again
                    )
                except Exception as e:
                    logger.error(f"Retry failed for email to {email_data['to_email']}: {str(e)}")
                    
                    # Increment attempts and add back to queue
                    email_data["attempts"] += 1
                    email_data["last_attempt"] = datetime.utcnow()
                    self.retry_queue.append(email_data)
                
                # Wait between retries
                await asyncio.sleep(5)
        finally:
            self.is_processing_queue = False
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (simple version)"""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Replace multiple newlines with single newline
        text = re.sub(r'\n+', '\n', text)
        return text.strip()

# Singleton instance
email_service = EmailService() 