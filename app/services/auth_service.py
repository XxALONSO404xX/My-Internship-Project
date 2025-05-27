"""Authentication service for client login and security"""
import logging
import jwt
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from passlib.context import CryptContext
from sqlalchemy import select
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
        if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        return len(errors) == 0, errors
        
    async def authenticate_client(self, username: str, password: str) -> Optional[Client]:
        """Authenticate a client by username and password"""
        try:
            # Find client by username
            query = select(Client).where(Client.username == username)
            result = await self.db.execute(query)
            client = result.scalar_one_or_none()
            
            if not client:
                return None
                
            if not self.verify_password(password, client.password_hash):
                return None
                
            return client
        except Exception as e:
            logger.error(f"Error authenticating client: {str(e)}")
            return None
    
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