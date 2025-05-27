"""
Enhanced API documentation for the IoT Management Platform.
This module adds detailed descriptions, examples, and tags to the OpenAPI schema.
"""
from fastapi.openapi.utils import get_openapi
from typing import Dict, Any, List

def custom_openapi(app) -> Dict[str, Any]:
    """
    Generate custom OpenAPI schema with enhanced documentation.
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=get_api_description(),
        routes=app.routes,
    )
    
    # Add components section if not exists
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "OAuth2PasswordBearer": {
            "type": "oauth2",
            "flows": {
                "password": {
                    "tokenUrl": "/api/v1/auth/token",
                    "scopes": {}
                }
            }
        },
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization"
        }
    }
    
    # Add tags with descriptions
    openapi_schema["tags"] = get_tags_metadata()
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

def get_api_description() -> str:
    """
    Get the full API description.
    """
    return """
# IoT Management Platform API

Welcome to the IoT Management Platform API documentation. This API allows you to manage and monitor IoT devices,
perform network scans, manage device groups, handle firmware updates, and receive real-time notifications.

## Authentication

Most API endpoints require authentication. You need to register a client account and then login to obtain a JWT token.
This token should be included in the `Authorization` header of subsequent requests using the Bearer scheme.

## Key Features

- **Device Management**: Discover, monitor, and control IoT devices
- **Network Scanning**: Scan your network for IoT devices
- **Device Grouping**: Organize devices into logical groups
- **Firmware Management**: View and update device firmware
- **Real-time Notifications**: Get alerts via WebSocket, email, or SMS
- **Security Monitoring**: Track device security status and vulnerabilities

## Getting Started

1. Register a client account at `/api/v1/auth/register`
2. Login at `/api/v1/auth/login` to get your access token
3. Start a network scan at `/api/v1/scans/` to discover devices
4. View your devices at `/api/v1/devices/`

For detailed information about each endpoint, browse the documentation below.
"""

def get_tags_metadata() -> List[Dict[str, str]]:
    """
    Get tags metadata with descriptions.
    """
    return [
        {
            "name": "authentication",
            "description": "Operations related to authentication, registration, and account management."
        },
        {
            "name": "devices",
            "description": "Operations for managing and interacting with IoT devices."
        },
        {
            "name": "scans",
            "description": "Network scanning operations to discover devices and check for vulnerabilities."
        },
        {
            "name": "groups",
            "description": "Operations for organizing devices into logical groups."
        },
        {
            "name": "firmware",
            "description": "Operations for managing device firmware and updates."
        },
        {
            "name": "notifications",
            "description": "Operations for managing notifications and alerts."
        },
        {
            "name": "security",
            "description": "Security-related operations and device security information."
        },
        {
            "name": "dashboard",
            "description": "Operations for retrieving dashboard and analytics data."
        },
        {
            "name": "websocket",
            "description": "WebSocket endpoints for real-time communication."
        }
    ]
