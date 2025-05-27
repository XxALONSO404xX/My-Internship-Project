"""API endpoints for authentication"""
import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import EmailStr

from app.models.database import get_db
from app.models.client import Client
from app.services.auth_service import AuthService
from app.services.token_service import TokenService
from app.services.email_service import email_service
from app.api.schemas import Token, ClientLogin, ClientCreate, ClientInDB, Response, PasswordResetRequest, PasswordResetConfirm, EmailVerificationConfirm
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    auth_service = AuthService(db)
    
    client = await auth_service.authenticate_client(form_data.username, form_data.password)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": client.id},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")

@router.post("/login", response_model=dict)
async def client_login(
    login_data: ClientLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Client login with username and password
    """
    auth_service = AuthService(db)
    
    # Authenticate client
    client = await auth_service.authenticate_client(login_data.username, login_data.password)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": client.id},
        expires_delta=access_token_expires
    )
    
    # Return token and user info
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "client": {
            "id": client.id,
            "username": client.username,
            "email": client.email,
            "is_active": client.is_active,
            "preferences": client.preferences
        }
    }

@router.get("/me", response_model=dict)
async def read_current_client(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current client data
    """
    auth_service = AuthService(db)
    client = await auth_service.get_current_client(token)
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return {
        "id": client.id,
        "username": client.username,
        "email": client.email,
        "is_active": client.is_active,
        "preferences": client.preferences,
        "last_login": client.last_login.isoformat() if client.last_login else None
    }

@router.post("/logout", response_model=Response)
async def logout():
    """
    Client logout - doesn't actually do anything on the server side
    since we're using stateless JWT tokens
    """
    return Response(
        status="success",
        message="Logged out successfully"
    )

@router.post("/register", response_model=dict)
async def register_client(
    client_data: ClientCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new client
    """
    try:
        auth_service = AuthService(db)
        
        # Check if username already exists
        query = select(Client).where(Client.username == client_data.username)
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
            
        # Check if email already exists
        query = select(Client).where(Client.email == client_data.email)
        result = await db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate password against policy
        is_valid, password_errors = auth_service.validate_password(client_data.password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Password does not meet security requirements",
                    "errors": password_errors
                }
            )
        
        # Generate ID if not provided
        if not client_data.id:
            import uuid
            client_data.id = str(uuid.uuid4())
        
        # Hash the password
        hashed_password = auth_service.get_password_hash(client_data.password)
        
        # Create client
        client = Client(
            id=client_data.id,
            username=client_data.username,
            email=client_data.email,
            password_hash=hashed_password,
            is_active=client_data.is_active,
            is_verified=False,  # Set as not verified
            preferences=client_data.preferences or {}
        )
        
        db.add(client)
        await db.commit()
        await db.refresh(client)
        
        # Generate verification token and send verification email
        token_service = TokenService(db)
        token = await token_service.create_verification_token(client)
        
        # Send verification email
        await email_service.send_verification_email(
            email=client.email,
            username=client.username,
            token=token.token
        )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_service.create_access_token(
            data={"sub": client.id},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "client": {
                "id": client.id,
                "username": client.username,
                "email": client.email,
                "is_active": client.is_active,
                "is_verified": client.is_verified
            },
            "message": "Registration successful. Please check your email to verify your account."
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/verify-email", response_model=Response)
async def verify_email(
    verify_data: EmailVerificationConfirm,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify email with token
    """
    token_service = TokenService(db)
    
    # Verify token
    is_valid, client, error = await token_service.verify_token(verify_data.token, "verification")
    
    if not is_valid or not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification token: {error}"
        )
    
    # Mark client as verified
    await token_service.mark_client_verified(client.id)
    
    # Mark token as used
    await token_service.mark_token_used(verify_data.token)
    
    return Response(
        status="success",
        message="Email verified successfully"
    )

@router.post("/resend-verification", response_model=Response)
async def resend_verification_email(
    email: EmailStr = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    """
    Resend verification email
    """
    # Find client by email
    query = select(Client).where(Client.email == email)
    result = await db.execute(query)
    client = result.scalar_one_or_none()
    
    if not client:
        # Don't reveal if email exists or not
        return Response(
            status="success",
            message="If the email exists, a verification email will be sent"
        )
    
    # Check if already verified
    if client.is_verified:
        return Response(
            status="success",
            message="Account is already verified"
        )
    
    # Generate new verification token
    token_service = TokenService(db)
    token = await token_service.create_verification_token(client)
    
    # Send verification email
    await email_service.send_verification_email(
        email=client.email,
        username=client.username,
        token=token.token
    )
    
    return Response(
        status="success",
        message="Verification email sent"
    )

@router.post("/forgot-password", response_model=Response)
async def forgot_password(
    reset_request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset email
    """
    # Find client by email
    query = select(Client).where(Client.email == reset_request.email)
    result = await db.execute(query)
    client = result.scalar_one_or_none()
    
    if not client:
        # Don't reveal if email exists or not for security
        return Response(
            status="success",
            message="If the email exists, a password reset link will be sent"
        )
    
    # Generate password reset token
    token_service = TokenService(db)
    token = await token_service.create_reset_token(client)
    
    # Send password reset email
    await email_service.send_password_reset_email(
        email=client.email,
        username=client.username,
        token=token.token
    )
    
    return Response(
        status="success",
        message="Password reset email sent"
    )

@router.post("/reset-password", response_model=Response)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password with token
    """
    auth_service = AuthService(db)
    token_service = TokenService(db)
    
    # Verify password meets requirements
    is_valid, password_errors = auth_service.validate_password(reset_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Password does not meet security requirements",
                "errors": password_errors
            }
        )
    
    # Verify token
    is_valid, client, error = await token_service.verify_token(reset_data.token, "reset")
    
    if not is_valid or not client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reset token: {error}"
        )
    
    # Update password
    hashed_password = auth_service.get_password_hash(reset_data.new_password)
    client.password_hash = hashed_password
    
    # Mark token as used
    await token_service.mark_token_used(reset_data.token)
    
    await db.commit()
    
    return Response(
        status="success",
        message="Password reset successful"
    ) 