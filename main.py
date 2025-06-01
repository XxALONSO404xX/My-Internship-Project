import logging
import os
import asyncio
from fastapi import FastAPI, Request
from typing import Any  # Use for type hints
# Exception is a built-in Python class, not from FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import uvicorn
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from docs_enhancer import custom_openapi
from app.api.error_handlers import sqlalchemy_exception_handler, validation_exception_handler, general_exception_handler

from app.api.router import api_router
from app.models.database import AsyncSessionLocal, get_db
from app.services.init_service import init_system
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Store application start time
START_TIME = datetime.utcnow()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup tasks
    logger.info("Application starting up")
    
    # Initialize system with required data
    async for db in get_db():
        await init_system(db)
        break
    
    logger.info("System initialized")
    
    # Start background services with a dedicated DB session
    from app.startup import run_startup_tasks
    
    # Create a dedicated session directly (not using the context manager)
    # to avoid session conflicts
    db = AsyncSessionLocal()
    await run_startup_tasks(db)
    
    logger.info("Background services started")
    
    # Yield control to FastAPI
    yield
    
    # Shutdown tasks
    logger.info("Application shutting down")

def get_application() -> FastAPI:
    """Create and configure the FastAPI application"""
    _app = FastAPI(
        title=settings.PROJECT_NAME,
        description="IoT Management and Security Platform API - For managing, monitoring, and securing IoT devices",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan
    )
    
    # CORS middleware configuration
    if settings.ALLOW_ALL_ORIGINS_FOR_DESKTOP:
        # For development with desktop app, allow all origins
        _app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        )
    else:
        # For production, use the configured origins
        _app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        )
    
    # Include API router
    _app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    
    # Register exception handlers
    _app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    _app.add_exception_handler(RequestValidationError, validation_exception_handler)
    _app.add_exception_handler(Exception, general_exception_handler)
    
    return _app

# Initialize the application
app = get_application()

# Set custom OpenAPI schema with enhanced documentation
app.openapi = lambda: custom_openapi(app)

# Create a dedicated database session for background tasks in the lifespan context manager
# which is handled by the lifespan function defined earlier

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to the IoT Management Platform API. Visit /api/docs for documentation."}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    uptime = datetime.utcnow() - START_TIME
    return {
        "status": "ok", 
        "uptime": str(uptime), 
        "server_time": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host, 
        port=port,
        reload=settings.DEBUG
    ) 