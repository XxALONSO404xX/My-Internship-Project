"""Service for sending SMS messages in the IoT platform"""
import logging
import re
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from config import settings

logger = logging.getLogger(__name__)

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
                logger.warning("Twilio not properly configured. SMS not sent.")
                return {"success": False, "error": "Twilio not configured"}
            
            # Validate phone number
            if not self._is_valid_phone_number(to_number):
                return {"success": False, "error": f"Invalid phone number format: {to_number}"}
            
            # Check rate limits
            rate_limit_check = self._check_rate_limits(to_number)
            if not rate_limit_check["allowed"]:
                logger.warning(f"Rate limit reached for {to_number}: {rate_limit_check['reason']}")
                
                # Add to retry queue if desired
                if retry_on_failure:
                    self._add_to_retry_queue(to_number, message, rate_limit_check["retry_after"])
                    return {"success": False, "queued": True, "error": rate_limit_check["reason"]}
                
                return {"success": False, "error": rate_limit_check["reason"]}
            
            # Initialize Twilio client
            client = Client(self.account_sid, self.auth_token)
            
            # Truncate message if too long (SMS standard is 160 chars)
            if len(message) > 1600:  # Allow for 10 segments
                message = message[:1597] + "..."
                
            # Send message
            twilio_message = client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            
            # Record this message for rate limiting
            self._record_sent_message(to_number)
            
            logger.info(f"SMS sent to {to_number}: {twilio_message.sid}")
            return {"success": True, "message_sid": twilio_message.sid}
            
        except TwilioRestException as e:
            error_msg = f"Twilio error sending SMS: {str(e)}"
            logger.error(error_msg)
            
            # Add to retry queue if requested and it's a recoverable error
            if retry_on_failure and self._is_recoverable_error(e):
                self._add_to_retry_queue(to_number, message)
            
            return {"success": False, "error": error_msg, "code": e.code}
            
        except Exception as e:
            error_msg = f"Error sending SMS: {str(e)}"
            logger.error(error_msg)
            
            # Add to retry queue if requested
            if retry_on_failure:
                self._add_to_retry_queue(to_number, message)
            
            return {"success": False, "error": error_msg}
    
    async def send_verification_code(self, phone_number: str, code: str) -> Dict[str, Any]:
        """
        Send verification code via SMS
        
        Args:
            phone_number: Recipient phone number
            code: Verification code
            
        Returns:
            Dictionary with result of sending
        """
        message = f"Your IoT Platform verification code is: {code}. This code will expire in 10 minutes."
        return await self.send_sms(to_number=phone_number, message=message)
    
    async def send_alert_notification(self, 
                                     phone_number: str, 
                                     title: str, 
                                     content: str) -> Dict[str, Any]:
        """
        Send alert notification via SMS
        
        Args:
            phone_number: Recipient phone number
            title: Alert title
            content: Alert content
            
        Returns:
            Dictionary with result of sending
        """
        message = f"{title}\n\n{content}"
        return await self.send_sms(to_number=phone_number, message=message)
    
    def _is_valid_phone_number(self, phone: str) -> bool:
        """
        Validate phone number format
        
        Args:
            phone: Phone number to validate
            
        Returns:
            True if valid, False otherwise
        """
        # International format with + prefix and 8-15 digits
        pattern = r'^\+?[0-9]{8,15}$'
        return bool(re.match(pattern, phone))
    
    def _is_recoverable_error(self, exception: TwilioRestException) -> bool:
        """
        Check if a Twilio error is recoverable (worth retrying)
        
        Args:
            exception: Twilio exception
            
        Returns:
            True if recoverable, False otherwise
        """
        # List of Twilio error codes that are temporary/recoverable
        recoverable_codes = [
            20001,  # Authentication required
            20003,  # Authentication Error
            20429,  # Too Many Requests
            20500,  # Internal Server Error
            20503,  # Service Unavailable
            30001,  # Queue overflow
            30004,  # Message blocked
            30005,  # Unknown destination
            30006,  # Landline or unreachable carrier
            30007,  # Carrier violations
            30008,  # Unknown error
        ]
        
        return exception.code in recoverable_codes
    
    def _add_to_retry_queue(self, to_number: str, message: str, delay_seconds: int = 0) -> None:
        """
        Add message to retry queue
        
        Args:
            to_number: Recipient phone number
            message: Message content
            delay_seconds: Optional delay before retry
        """
        self.retry_queue.append({
            "to_number": to_number,
            "message": message,
            "attempts": 1,
            "last_attempt": datetime.utcnow(),
            "next_attempt": datetime.utcnow() + timedelta(seconds=delay_seconds),
            "delay": delay_seconds
        })
        
        # Start processing queue if not already running
        if not self.is_processing_queue:
            asyncio.create_task(self._process_retry_queue())
    
    def _record_sent_message(self, phone_number: str) -> None:
        """
        Record a sent message for rate limiting
        
        Args:
            phone_number: Recipient phone number
        """
        current_time = datetime.utcnow()
        
        if phone_number not in self.sent_messages:
            self.sent_messages[phone_number] = []
            
        # Add the current timestamp
        self.sent_messages[phone_number].append(current_time)
        
        # Remove timestamps older than 24 hours
        self.sent_messages[phone_number] = [
            t for t in self.sent_messages[phone_number] 
            if t > current_time - timedelta(days=1)
        ]
    
    def _check_rate_limits(self, phone_number: str) -> Dict[str, Any]:
        """
        Check if sending an SMS would exceed rate limits
        
        Args:
            phone_number: Recipient phone number
            
        Returns:
            Dict containing: 
            - allowed: True if sending is allowed
            - reason: Reason if not allowed
            - retry_after: Seconds to wait if rate limited
        """
        current_time = datetime.utcnow()
        
        # If no previous messages, allow
        if phone_number not in self.sent_messages:
            return {"allowed": True}
            
        # Filter timestamps to last 24 hours
        timestamps = [
            t for t in self.sent_messages[phone_number] 
            if t > current_time - timedelta(days=1)
        ]
        
        # Check daily limit
        if len(timestamps) >= self.max_per_day:
            oldest = min(timestamps)
            retry_after = 86400 - (current_time - oldest).total_seconds()
            return {
                "allowed": False, 
                "reason": f"Daily limit reached ({self.max_per_day} messages per day)",
                "retry_after": int(retry_after)
            }
            
        # Filter timestamps to last hour
        hour_timestamps = [
            t for t in timestamps 
            if t > current_time - timedelta(hours=1)
        ]
        
        # Check hourly limit
        if len(hour_timestamps) >= self.max_per_hour:
            oldest = min(hour_timestamps)
            retry_after = 3600 - (current_time - oldest).total_seconds()
            return {
                "allowed": False,
                "reason": f"Hourly limit reached ({self.max_per_hour} messages per hour)",
                "retry_after": int(retry_after)
            }
            
        return {"allowed": True}
    
    async def _process_retry_queue(self) -> None:
        """Process the retry queue for failed SMS messages"""
        if self.is_processing_queue:
            return
            
        self.is_processing_queue = True
        
        try:
            while self.retry_queue:
                # Get current time
                current_time = datetime.utcnow()
                
                # Find the next message eligible for retry
                next_index = None
                for i, sms_data in enumerate(self.retry_queue):
                    if sms_data["next_attempt"] <= current_time:
                        next_index = i
                        break
                
                # If no eligible message, wait and check again
                if next_index is None:
                    # Find the soonest next_attempt time
                    if self.retry_queue:
                        soonest = min(self.retry_queue, key=lambda x: x["next_attempt"])
                        wait_seconds = max(1, (soonest["next_attempt"] - current_time).total_seconds())
                        await asyncio.sleep(min(wait_seconds, 60))  # Cap at 60 seconds
                        continue
                    else:
                        break
                
                # Get the message to retry
                sms_data = self.retry_queue.pop(next_index)
                
                # Check if max attempts reached
                if sms_data["attempts"] >= 3:
                    logger.warning(f"Max retry attempts reached for SMS to {sms_data['to_number']}")
                    continue
                
                # Check rate limits
                rate_limit_check = self._check_rate_limits(sms_data["to_number"])
                if not rate_limit_check["allowed"]:
                    # Update next attempt time and put back in queue
                    sms_data["next_attempt"] = current_time + timedelta(seconds=rate_limit_check["retry_after"])
                    self.retry_queue.append(sms_data)
                    logger.info(f"Rate limit still applies, rescheduling SMS to {sms_data['to_number']} in {rate_limit_check['retry_after']} seconds")
                    continue
                
                # Try sending again
                try:
                    await self.send_sms(
                        to_number=sms_data["to_number"],
                        message=sms_data["message"],
                        retry_on_failure=False  # Don't add to queue again from send_sms
                    )
                    logger.info(f"Successfully resent SMS to {sms_data['to_number']} on attempt {sms_data['attempts']}")
                except Exception as e:
                    logger.error(f"Retry failed for SMS to {sms_data['to_number']}: {str(e)}")
                    
                    # Increment attempts and add back to queue with exponential backoff
                    sms_data["attempts"] += 1
                    sms_data["last_attempt"] = current_time
                    
                    # Calculate backoff: 1 min, 5 min, 15 min
                    backoff_seconds = 60 * (5 ** (sms_data["attempts"] - 1))
                    sms_data["next_attempt"] = current_time + timedelta(seconds=backoff_seconds)
                    
                    self.retry_queue.append(sms_data)
                
                # Wait between retries to avoid bursts
                await asyncio.sleep(1)
        finally:
            self.is_processing_queue = False

# Singleton instance
sms_service = SMSService() 