"""Authentication Module for IoT Platform Desktop Application

Provides a complete authentication system with the following features:

1. LOGIN & SESSION MANAGEMENT
   - Standard OAuth2 token-based authentication
   - Extended desktop sessions with refresh tokens
   - Session logout and token revocation

2. USER MANAGEMENT
   - User registration
   - Email verification
   - Profile access

3. PASSWORD MANAGEMENT
   - Password reset flow
   - Forgot password functionality
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional, List, Tuple
from pydantic import EmailStr

from app.models.database import get_db
from app.models.client import Client
from app.services.auth_service import AuthService
from app.services.refresh_token_service import create_refresh_token_service, RefreshTokenService
from app.services.token_service import TokenService
from app.services.messaging_service import email_service
from app.api.schemas import (Token, ClientLogin, TokenResponse, AuthResponse, RefreshTokenRequest, 
                             ClientCreate, ClientInDB, Response, PasswordResetRequest, 
                             PasswordResetConfirm, EmailVerificationConfirm)
from app.api.deps import get_current_client
from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# OAuth2 scheme for compatibility with existing clients
# =============================================================================
# AUTHENTICATION SETUP
# =============================================================================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# =============================================================================
# LOGIN & SESSION MANAGEMENT ENDPOINTS
# =============================================================================

@router.post("/login", response_model=TokenResponse)
async def client_login(
    login_data: ClientLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Desktop application login with extended session support
    Returns both access token and refresh token
    """
    auth_service = AuthService(db)
    refresh_token_service = create_refresh_token_service(db)
    
    # Authenticate client (with email verification required)
    client = await auth_service.authenticate_client(
        login_data.username, 
        login_data.password,
        require_verification=True
    )
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or unverified account"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": client.id},
        expires_delta=access_token_expires
    )
    
    # Create refresh token (for extended desktop sessions)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    device_info = f"{request.client.host} - {request.headers.get('user-agent', 'Unknown')}"
    refresh_token = await refresh_token_service.create_refresh_token(
        client, 
        expires_delta=refresh_token_expires,
        device_info=device_info
    )
    
    # Calculate expiration time
    expires_at = datetime.now() + access_token_expires
    
    # Prepare client info
    client_dict = {
        "id": client.id,
        "username": client.username,
        "email": client.email,
        "is_active": client.is_active,
        "is_verified": client.is_verified
    }
    
    # Use the standard response format
    return TokenResponse.create(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token.token,
        expires_at=expires_at,
        client=client_dict
    )

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    auth_service = AuthService(db)
    
    # Authenticate client (with email verification required)
    client = await auth_service.authenticate_client(
        form_data.username, 
        form_data.password,
        require_verification=True
    )
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or unverified account",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": client.id},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer"
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a new access token using a refresh token
    """
    refresh_token_service = create_refresh_token_service(db)
    auth_service = AuthService(db)
    
    # Validate refresh token
    is_valid, client, error_message = await refresh_token_service.validate_refresh_token(refresh_request.refresh_token)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_message or "Invalid refresh token"
        )
    
    # Client will be available here since is_valid is True
    
    # Create a new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": client.id},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")

@router.post("/logout", response_model=Dict[str, Any])
async def logout(
    refresh_request: RefreshTokenRequest,
    current_client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout from the desktop application
    Revokes the refresh token so it can't be used again
    """
    refresh_token_service = create_refresh_token_service(db)
    
    # Revoke the refresh token if provided
    if refresh_request.refresh_token:
        await refresh_token_service.revoke_token(refresh_request.refresh_token)
    
    return {
        "message": "Successfully logged out",
        "timestamp": datetime.utcnow().isoformat()
    }

# This duplicate token endpoint has been removed since we already have the standard OAuth2 endpoint

# =============================================================================
# USER PROFILE & ACCOUNT MANAGEMENT
# =============================================================================

@router.get("/me", response_model=dict)
async def read_current_client(
    current_client: Client = Depends(get_current_client)
):
    """
    Get current client data
    """
    return {
        "id": current_client.id,
        "username": current_client.username,
        "email": current_client.email,
        "is_active": current_client.is_active,
        "preferences": current_client.preferences,
        "last_login": current_client.last_login.isoformat() if current_client.last_login else None
    }

# =============================================================================
# USER REGISTRATION & VERIFICATION 
# =============================================================================

@router.post("/register", response_model=AuthResponse)
async def register_client(
    client_data: ClientCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new client
    """
    auth_service = AuthService(db)
    
    # Use the consolidated service method to register the client
    success, client, error_message = await auth_service.register_client(
        username=client_data.username,
        email=client_data.email,
        password=client_data.password
    )
    
    if not success:
        # Registration failed with a specific error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Return standardized response
    return AuthResponse(
        status="success",
        message="Registration successful. Please check your email to verify your account.",
        data={
            "username": client_data.username,
            "email": client_data.email,
            "verification_required": True
        }
    )

@router.post("/verify-email", response_model=AuthResponse)
async def verify_email(
    verify_data: EmailVerificationConfirm,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify email with token
    """
    auth_service = AuthService(db)
    
    # Use the consolidated service method for client verification
    success, client, error_message = await auth_service.verify_client(verify_data.token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Return standardized response
    return AuthResponse(
        status="success",
        message="Email verified successfully",
        data={
            "username": client.username,
            "email": client.email,
            "is_verified": True
        }
    )

@router.post("/resend-verification", response_model=AuthResponse)
async def resend_verification_email(
    email: EmailStr = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
):
    """
    Resend verification email
    """
    # Use the AuthService to handle verification request
    auth_service = AuthService(db)
    success, message = await auth_service.handle_verification_request(email)
    
    # Return standardized response
    return AuthResponse(
        status="success" if success else "error",
        message=message,
        data={"email": email} if success else None
    )

@router.post("/forgot-password", response_model=AuthResponse)
async def forgot_password(
    reset_request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset email
    """
    # Use the AuthService to handle password reset request
    auth_service = AuthService(db)
    success, message = await auth_service.handle_password_reset_request(reset_request.email)
    
    # Return standardized response
    return AuthResponse(
        status="success" if success else "error",
        message=message,
        data={"email": reset_request.email} if success else None
    )

@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset password with token
    """
    auth_service = AuthService(db)
    
    # Use the consolidated service method for password reset
    success, client, error_message = await auth_service.verify_reset_token_and_update_password(
        token_value=reset_data.token,
        new_password=reset_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Return standardized response
    return AuthResponse(
        status="success",
        message="Password reset successful",
        data={
            "email": client.email,
            "password_updated": True
        }
    )