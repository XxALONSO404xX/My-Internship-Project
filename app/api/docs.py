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
    
    # Enhance paths with examples and better descriptions
    enhance_auth_endpoints(openapi_schema)
    enhance_device_endpoints(openapi_schema)
    enhance_scan_endpoints(openapi_schema)
    enhance_group_endpoints(openapi_schema)
    
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

def enhance_auth_endpoints(openapi_schema: Dict[str, Any]) -> None:
    """
    Enhance authentication endpoint documentation.
    """
    # Login example
    if "/api/v1/auth/login" in openapi_schema["paths"]:
        login_path = openapi_schema["paths"]["/api/v1/auth/login"]
        if "post" in login_path:
            login_path["post"]["description"] = "Login with username and password to get an access token and client information."
            login_path["post"]["requestBody"]["content"]["application/json"]["example"] = {
                "username": "user123",
                "password": "SecurePassword123!"
            }
            login_path["post"]["responses"]["200"]["content"]["application/json"]["example"] = {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "client": {
                    "id": "12345",
                    "username": "user123",
                    "email": "user@example.com",
                    "is_active": True,
                    "preferences": {"theme": "dark", "notifications": True}
                }
            }
    
    # Register example
    if "/api/v1/auth/register" in openapi_schema["paths"]:
        register_path = openapi_schema["paths"]["/api/v1/auth/register"]
        if "post" in register_path:
            register_path["post"]["description"] = "Register a new client account. Email verification will be sent to the provided email address."
            register_path["post"]["requestBody"]["content"]["application/json"]["example"] = {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePassword123!",
                "preferences": {"theme": "light", "notifications": True}
            }

def enhance_device_endpoints(openapi_schema: Dict[str, Any]) -> None:
    """
    Enhance device endpoint documentation.
    """
    # Get devices example
    if "/api/v1/devices/" in openapi_schema["paths"]:
        devices_path = openapi_schema["paths"]["/api/v1/devices/"]
        if "get" in devices_path:
            devices_path["get"]["description"] = "List all devices with optional filtering by type, status, or group."
            devices_path["get"]["parameters"].append({
                "name": "device_type",
                "in": "query",
                "description": "Filter devices by type (e.g., 'temperature_sensor', 'security_camera')",
                "required": False,
                "schema": {"type": "string"}
            })
            devices_path["get"]["parameters"].append({
                "name": "is_online",
                "in": "query",
                "description": "Filter devices by online status (true/false)",
                "required": False,
                "schema": {"type": "boolean"}
            })
            devices_path["get"]["responses"]["200"]["content"]["application/json"]["example"] = {
                "items": [
                    {
                        "hash_id": "6e32c0f12b7c4856a8f8f1b1a9c0a74f",
                        "name": "Living Room Sensor",
                        "device_type": "temperature_sensor",
                        "is_online": True,
                        "last_seen": "2025-05-26T12:30:45Z",
                        "firmware_version": "v1.2.0",
                        "ip_address": "192.168.1.120"
                    },
                    {
                        "hash_id": "2a7b9d4f5e8c1a3b6d9e7f8a1c4b5d6e",
                        "name": "Front Door Camera",
                        "device_type": "security_camera",
                        "is_online": True,
                        "last_seen": "2025-05-26T12:35:10Z",
                        "firmware_version": "v2.1.0",
                        "ip_address": "192.168.1.130"
                    }
                ],
                "total": 15,
                "page": 1,
                "page_size": 10
            }
    
    # Get device details example
    if "/api/v1/devices/{device_id}" in openapi_schema["paths"]:
        device_path = openapi_schema["paths"]["/api/v1/devices/{device_id}"]
        if "get" in device_path:
            device_path["get"]["description"] = "Get detailed information about a specific device."
            device_path["get"]["responses"]["200"]["content"]["application/json"]["example"] = {
                "hash_id": "6e32c0f12b7c4856a8f8f1b1a9c0a74f",
                "name": "Living Room Sensor",
                "device_type": "temperature_sensor",
                "manufacturer": "SenseTech",
                "model": "TempSense Pro",
                "firmware_version": "v1.2.0",
                "is_online": True,
                "last_seen": "2025-05-26T12:30:45Z",
                "ip_address": "192.168.1.120",
                "mac_address": "00:1B:44:11:3A:B7",
                "ports": {"http": 80, "mqtt": 1883},
                "supports_http": True,
                "supports_mqtt": True,
                "supports_coap": False,
                "supports_websocket": False,
                "supports_tls": True,
                "tls_version": "TLS 1.3",
                "device_metadata": {
                    "temperature": 22.5,
                    "humidity": 45,
                    "battery_level": 87
                },
                "created_at": "2025-03-15T10:20:30Z",
                "updated_at": "2025-05-26T12:30:45Z"
            }

def enhance_scan_endpoints(openapi_schema: Dict[str, Any]) -> None:
    """
    Enhance scan endpoint documentation.
    """
    # Start scan example
    if "/api/v1/scans/" in openapi_schema["paths"]:
        scans_path = openapi_schema["paths"]["/api/v1/scans/"]
        if "post" in scans_path:
            scans_path["post"]["description"] = "Start a new scan to discover devices on the network or check existing devices for vulnerabilities."
            scans_path["post"]["requestBody"]["content"]["application/json"]["example"] = {
                "scan_type": "discovery",
                "network_range": "192.168.1.0/24"
            }
            scans_path["post"]["responses"]["200"]["content"]["application/json"]["example"] = {
                "scan_id": "f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2",
                "status": "pending",
                "type": "discovery",
                "start_time": "2025-05-27T00:51:32Z"
            }
    
    # Get scan results example
    if "/api/v1/scans/{scan_id}/results" in openapi_schema["paths"]:
        scan_results_path = openapi_schema["paths"]["/api/v1/scans/{scan_id}/results"]
        if "get" in scan_results_path:
            scan_results_path["get"]["description"] = "Get detailed results of a completed scan."
            scan_results_path["get"]["responses"]["200"]["content"]["application/json"]["example"] = {
                "scan_id": "f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2",
                "status": "completed",
                "type": "discovery",
                "start_time": "2025-05-27T00:51:32Z",
                "end_time": "2025-05-27T00:52:45Z",
                "results": {
                    "devices_found": 15,
                    "devices": [
                        {
                            "hash_id": "6e32c0f12b7c4856a8f8f1b1a9c0a74f",
                            "name": "Living Room Sensor",
                            "device_type": "temperature_sensor",
                            "is_online": True,
                            "ip_address": "192.168.1.120"
                        },
                        {
                            "hash_id": "2a7b9d4f5e8c1a3b6d9e7f8a1c4b5d6e",
                            "name": "Front Door Camera",
                            "device_type": "security_camera",
                            "is_online": True,
                            "ip_address": "192.168.1.130"
                        }
                    ]
                }
            }

def enhance_group_endpoints(openapi_schema: Dict[str, Any]) -> None:
    """
    Enhance group endpoint documentation.
    """
    # Create group example
    if "/api/v1/groups/" in openapi_schema["paths"]:
        groups_path = openapi_schema["paths"]["/api/v1/groups/"]
        if "post" in groups_path:
            groups_path["post"]["description"] = "Create a new device group."
            groups_path["post"]["requestBody"]["content"]["application/json"]["example"] = {
                "name": "Living Room",
                "description": "Devices in the living room",
                "color": "#4A90E2",
                "icon": "living-room"
            }
            groups_path["post"]["responses"]["201"]["content"]["application/json"]["example"] = {
                "id": "g123456",
                "name": "Living Room",
                "description": "Devices in the living room",
                "color": "#4A90E2",
                "icon": "living-room",
                "device_count": 0,
                "created_at": "2025-05-27T00:55:12Z"
            }
    
    # Add device to group example
    if "/api/v1/groups/{group_id}/devices" in openapi_schema["paths"]:
        add_device_path = openapi_schema["paths"]["/api/v1/groups/{group_id}/devices"]
        if "post" in add_device_path:
            add_device_path["post"]["description"] = "Add one or more devices to a group."
            add_device_path["post"]["requestBody"]["content"]["application/json"]["example"] = {
                "device_ids": ["6e32c0f12b7c4856a8f8f1b1a9c0a74f", "2a7b9d4f5e8c1a3b6d9e7f8a1c4b5d6e"]
            }

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
