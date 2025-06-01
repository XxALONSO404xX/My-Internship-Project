"""API dependencies"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_client(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current authenticated user based on the JWT token
    """
    auth_service = AuthService(db)
    user = await auth_service.get_current_client(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user 

# For backward compatibility with existing code
get_current_user = get_current_client

# Function to get client IP address
async def get_client_ip(request: Request) -> str:
    """
    Extract the client IP address from the request.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        The client IP address as a string
    """
    # Try to get X-Forwarded-For header first (for clients behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Return the first IP if there are multiple
        return forwarded_for.split(",")[0].strip()
    
    # Otherwise get the direct client IP
    return request.client.host if request.client else "unknown"