from fastapi import APIRouter

# Import directly from the endpoint modules to avoid import issues
from app.api.endpoints.devices import router as devices_router
from app.api.endpoints.system import router as system_router
from app.api.endpoints.ws import router as ws_router
from app.api.endpoints.activities import router as activities_router
from app.api.endpoints.notifications import router as notifications_router
from app.api.endpoints.clients import router as clients_router
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.dashboard import router as dashboard_router
from app.api.endpoints.groups import router as groups_router
from app.api.endpoints.group_security import router as group_security_router
from app.api.endpoints.security import router as security_router
from app.api.endpoints.firmware import router as firmware_router
from app.api.endpoints.network_security import router as network_security_router
from app.api.endpoints.rules import router as rules_router
# Removed bulk_operations import to fix syntax error
# Removed jobs_router to simplify the platform
# Note: Desktop auth has been consolidated into the auth module

api_router = APIRouter()

# === CORE RESOURCE ENDPOINTS ===
# Follows RESTful resource patterns with consistent naming
 
# Device Management - Primary resource
api_router.include_router(devices_router, prefix="/devices", tags=["devices"])

# Group Management
api_router.include_router(groups_router, prefix="/groups", tags=["groups"])
api_router.include_router(group_security_router, prefix="/group-security", tags=["security"])
# Removed non-existent group_firmware router

# Jobs Management - Removed to simplify platform
# api_router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])

# === FUNCTIONALITY-FOCUSED ENDPOINTS ===

# Security Management - Consolidated vulnerability and remediation endpoints
api_router.include_router(security_router, prefix="/security", tags=["security", "vulnerability"])

# Firmware Management - Consolidated endpoints
api_router.include_router(firmware_router, prefix="/firmware", tags=["firmware"])

# Bulk Operations - Removed due to syntax errors
# api_router.include_router(bulk_router, prefix="/bulk", tags=["bulk-operations"])

# Legacy router - Removed due to syntax errors
# api_router.include_router(bulk_operations_router, tags=["legacy-bulk-operations"])

# System Management
api_router.include_router(system_router, prefix="/system", tags=["system"])
# Dashboard - Consolidated view
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
# Network Security Monitoring
api_router.include_router(network_security_router, prefix="/network-security", tags=["security", "network"])

# Authentication
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])

# === SUPPORTING SERVICES ===

# WebSocket for real-time updates
api_router.include_router(ws_router, prefix="/ws", tags=["websocket"])

# Activities and audit log
api_router.include_router(activities_router, prefix="/activities", tags=["activities"])

# Notifications
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])

# Clients management
api_router.include_router(clients_router, prefix="/clients", tags=["clients"])

# === TESTING ENDPOINTS ===
# Clearly separated from production endpoints

# Remediation router has been consolidated into security_router
# api_router.include_router(remediation_router, prefix="/test", tags=["testing"])

# === DEPRECATED ENDPOINTS ===
# These will be removed in future versions but maintained for backward compatibility
# Use the new consolidated endpoints instead

# Note: Old security, scans, security-info, and group-security endpoints 
# have been consolidated into the primary resource endpoints or the vulnerabilities endpoint
# Firmware has been simplified and aligned with the job-based approach