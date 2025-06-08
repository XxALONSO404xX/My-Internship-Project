"""Error handling middleware for the IoT platform API"""
import logging
import traceback
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """
    Handle SQLAlchemy exceptions globally
    
    Log the error details and return a consistent error response
    """
    logger.error(f"Database error: {str(exc)}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Database error",
            "message": str(exc),
            "path": request.url.path
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors globally
    
    Log the error details and return a consistent error response with validation details
    """
    errors = exc.errors()
    # sanitize errors: convert non-serializable context values to strings
    sanitized_errors = []
    for err in errors:
        err_copy = err.copy()
        if 'ctx' in err_copy:
            err_copy['ctx'] = {k: str(v) for k, v in err_copy['ctx'].items()}
        sanitized_errors.append(err_copy)
    logger.warning(f"Validation error: {sanitized_errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation error",
            "message": "Invalid request parameters",
            "details": sanitized_errors,
            "path": request.url.path
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle all unhandled exceptions globally
    
    Log the error details and return a consistent error response
    """
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Server error",
            "message": str(exc),
            "path": request.url.path
        }
    )
