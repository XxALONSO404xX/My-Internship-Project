"""
Helper functions for API responses to ensure consistency
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

def standard_response(
    data: Any = None, 
    message: str = "Success", 
    success: bool = True,
    metadata: Dict = None
) -> Dict:
    """
    Create a standard response format for all API endpoints
    
    Args:
        data: The data to return
        message: A message describing the result
        success: Whether the operation was successful
        metadata: Any additional metadata
    
    Returns:
        A dictionary with standardized structure
    """
    return {
        "success": success,
        "message": message,
        "data": data,
        "metadata": metadata,
        "timestamp": datetime.utcnow().isoformat()
    }

def error_response(
    message: str, 
    status_code: int = 400, 
    error_details: List[Dict] = None
) -> JSONResponse:
    """
    Create a standard error response
    
    Args:
        message: Error message
        status_code: HTTP status code
        error_details: List of detailed errors
        
    Returns:
        JSONResponse with error details
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": message,
            "errors": error_details or [],
            "timestamp": datetime.utcnow().isoformat()
        }
    )

def paginated_response(
    items: List[Any],
    total: int,
    page: int = 1,
    page_size: int = 10,
    message: str = "Items retrieved successfully"
) -> Dict:
    """
    Create a standard response for paginated results
    
    Args:
        items: List of items for the current page
        total: Total number of items across all pages
        page: Current page number
        page_size: Number of items per page
        message: Response message
        
    Returns:
        Dictionary with standardized structure including pagination info
    """
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    return standard_response(
        data=items,
        message=message,
        metadata={
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": total_pages
            }
        }
    )
