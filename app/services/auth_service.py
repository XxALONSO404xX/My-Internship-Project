"""Authentication service for client login and security"""
import logging
import jwt
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.client import Client
from app.api.schemas import TokenData
from config.settings import settings

logger = logging.getLogger(__name__)

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """Service for authentication operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        from app.services.token_service import TokenService
        self.token_service = TokenService(db)
        from app.services.messaging_service import email_service
        self.email_service = email_service
        
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
        
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def validate_password(self, password: str) -> Tuple[bool, List[str]]:
        """
        Validate a password against the password policy
        
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        errors = []
        
        # Check length
        if len(password) < settings.PASSWORD_MIN_LENGTH:
            errors.append(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long")
        
        # Check uppercase
        if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        # Check lowercase
        if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        # Check digit
        if settings.PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        # Check special character
        if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}<>]', password):
            errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, errors
    
    async def find_client_by_email(self, email: str) -> Optional[Client]:
        """Find a client by email address"""
        query = select(Client).where(Client.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def find_client_by_username_or_email(self, username_or_email: str) -> Optional[Client]:
        """Find a client by username or email"""
        query = select(Client).where(
            (Client.username == username_or_email) | (Client.email == username_or_email)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
        
    async def authenticate_client(self, username: str, password: str, require_verification: bool = True) -> Optional[Client]:
        """Authenticate a client by username and password"""
        try:
            # Find client by username or email using the consolidated method
            client = await self.find_client_by_username_or_email(username)
            
            if not client:
                return None
                
            if not self.verify_password(password, client.hashed_password):
                return None
                
            # Check if email verification is required and if client is verified
            if require_verification and not client.is_verified:
                logger.warning(f"Login attempt for unverified account: {username}")
                return None
            
            # Update last_login timestamp
            client.last_login = datetime.utcnow()
            await self.db.commit()
                
            return client
        except Exception as e:
            logger.error(f"Error authenticating client: {str(e)}")
            return None
    
    async def handle_verification_request(self, email: str) -> Tuple[bool, str]:
        """
        Handle verification request
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Find client by email
            client = await self.find_client_by_email(email)
            
            if not client:
                logger.warning(f"Verification requested for non-existent email: {email}")
                return False, "Email not found"
                
            if client.is_verified:
                logger.info(f"Verification requested for already verified email: {email}")
                return False, "Email already verified"
                
            # Create verification token
            token = await self.token_service.create_verification_token(client)
            
            # Send verification email with enhanced error handling
            try:
                email_result = await self.email_service.send_verification_email(
                    email=client.email,
                    username=client.username,
                    token=token.token
                )
                
                if not email_result.get("success"):
                    # Log the failure but provide user-friendly message
                    logger.error(f"Failed to send verification email to {client.email}: {email_result.get('message')}")
                    return False, "Failed to send verification email. Please try again later."
                    
                logger.info(f"Verification email successfully sent to {client.email}")
                return True, "Verification email sent"
                
            except Exception as email_error:
                # Log the specific email error
                logger.error(f"Exception sending verification email to {client.email}: {str(email_error)}", exc_info=True)
                return False, "Failed to send verification email. Please try again later."
                
        except Exception as e:
            # Log the general error
            logger.error(f"Error processing verification request: {str(e)}", exc_info=True)
            return False, "An error occurred while processing your request"

    async def handle_password_reset_request(self, email: str) -> Tuple[bool, str]:
        """
        Handle password reset request
        
        Returns:
            Tuple[bool, str]: (success, message)
            
        Note: This function clearly informs users if an account exists or not,
        rather than using a generic message.
        """
        try:
            # Find client by email
            client = await self.find_client_by_email(email)
            
            if not client:
                # Explicitly tell the user the account doesn't exist
                logger.info(f"Password reset requested for non-existent email: {email}")
                return False, f"No account found with email: {email}"
            
            # Generate password reset token using the integrated token service
            token = await self.token_service.create_reset_token(client)
            
            # Send password reset email using the integrated email service
            try:
                email_result = await self.email_service.send_password_reset_email(
                    email=client.email,
                    username=client.username,
                    token=token.token
                )
                
                if not email_result.get("success"):
                    # Log email failure and inform the user
                    logger.error(f"Failed to send password reset email to {client.email}: {email_result.get('message')}")
                    return False, "Failed to send password reset email. Please try again."
                    
                # Log successful email sending and give clear success message
                logger.info(f"Password reset email successfully sent to {client.email}")
                return True, "Password reset email sent"
                
            except Exception as email_error:
                # Log the specific email error
                logger.error(f"Exception sending password reset email to {client.email}: {str(email_error)}")
                return False, "Error sending password reset email. Please try again."
                
        except Exception as e:
            # Log the general error
            logger.error(f"Error processing password reset request: {str(e)}")
            return False, "An error occurred while processing your request. Please try again."

    async def update_client_password(self, client_id: str, new_password: str) -> bool:
        """
        Update a client's password
        
        Returns:
            bool: Success status
        """
        hashed_password = self.get_password_hash(new_password)
        
        query = update(Client).where(Client.id == client_id).values(
            hashed_password=hashed_password,
            updated_at=datetime.utcnow()
        )
        await self.db.execute(query)
        await self.db.commit()
        
        return True
        
    async def register_client(self, username: str, email: str, password: str) -> Tuple[bool, Optional[Client], Optional[str]]:
        """
        Register a new client
        
        Args:
            username: Username for the new client
            email: Email for the new client
            password: Password for the new client
            
        Returns:
            Tuple containing:
            - Boolean indicating if registration was successful
            - Created Client object or None if failed
            - Error message or None if successful
        """
        try:
            # Validate password
            is_valid_password, password_errors = self.validate_password(password)
            if not is_valid_password:
                return False, None, f"Password validation failed: {', '.join(password_errors)}"
            
            # Check if username is taken
            existing_username = await self.find_client_by_username_or_email(username)
            if existing_username:
                return False, None, "Username is already taken"
                
            # Check if email is taken
            existing_email = await self.find_client_by_email(email)
            if existing_email:
                return False, None, "Email is already registered"
                
            # Create client
            from app.models.client import Client
            import uuid
            hashed_password = self.get_password_hash(password)
            
            client = Client(
                id=str(uuid.uuid4()),  # Generate a unique ID for the client
                username=username,
                email=email,
                hashed_password=hashed_password,
                is_active=True,
                is_verified=False,  # Requires email verification
                created_at=datetime.utcnow()
            )
            
            self.db.add(client)
            await self.db.commit()
            await self.db.refresh(client)
            
            # Create verification token using the integrated token service
            token = await self.token_service.create_verification_token(client)
            
            # Send verification email using the integrated email service
            await self.email_service.send_verification_email(
                email=client.email,
                username=client.username,
                token=token.token
            )
            
            return True, client, None
            
        except Exception as e:
            logger.error(f"Error registering client: {str(e)}")
            await self.db.rollback()
            return False, None, f"Registration failed: {str(e)}"
    
    async def verify_client(self, token_value: str) -> Tuple[bool, Optional[Client], Optional[str]]:
        """
        Verify a client's email using a verification token
        
        Args:
            token_value: Verification token
            
        Returns:
            Tuple containing:
            - Boolean indicating if verification was successful
            - Client object or None if verification failed
            - Error message or None if successful
        """
        try:
            # Verify the token using the token service
            is_valid, client, error = await self.token_service.verify_token(token_value, "verification")
            
            if not is_valid or not client:
                return False, None, error or "Invalid verification token"
            
            # Mark client as verified
            await self.token_service.mark_client_verified(client.id)
            
            # Mark token as used
            await self.token_service.mark_token_used(token_value)
            
            return True, client, None
            
        except Exception as e:
            logger.error(f"Error verifying client: {str(e)}")
            return False, None, f"Verification failed: {str(e)}"
            
    async def verify_reset_token_and_update_password(self, token_value: str, new_password: str) -> Tuple[bool, Optional[Client], Optional[str]]:
        """
        Verify a reset token and update the client's password
        
        Args:
            token_value: Reset token
            new_password: New password
            
        Returns:
            Tuple containing:
            - Boolean indicating if password reset was successful
            - Client object or None if reset failed
            - Error message or None if successful
        """
        try:
            # Validate the new password
            is_valid_password, password_errors = self.validate_password(new_password)
            if not is_valid_password:
                return False, None, f"Password validation failed: {', '.join(password_errors)}"
            
            # Verify the token
            is_valid, client, error = await self.token_service.verify_token(token_value, "reset")
            
            if not is_valid or not client:
                return False, None, error or "Invalid reset token"
            
            # Update the password
            await self.update_client_password(client.id, new_password)
            
            # Mark token as used
            await self.token_service.mark_token_used(token_value)
            
            return True, client, None
            
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            return False, None, f"Password reset failed: {str(e)}"
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        
        # Set expiration
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode.update({"exp": expire})
        
        # Create JWT token
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
        
    async def get_current_client(self, token: str) -> Optional[Client]:
        """Get the current client from a token"""
        try:
            # Decode token
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            client_id: str = payload.get("sub")
            
            if client_id is None:
                return None
                
            token_data = TokenData(client_id=client_id)
            
            # Get client from database
            query = select(Client).where(Client.id == token_data.client_id)
            result = await self.db.execute(query)
            client = result.scalar_one_or_none()
            
            if not client:
                return None
                
            if not client.is_active:
                return None
                
            return client
            
        except jwt.PyJWTError:
            return None
        except Exception as e:
            logger.error(f"Error getting current client: {str(e)}")
            return None