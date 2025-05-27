from fastapi import APIRouter

from app.api.endpoints import devices, system, ws, activities, notifications, clients, auth, security, rules, scans, firmware, security_info, dashboard, groups, group_security, desktop_auth

api_router = APIRouter()
 
# Include routers from endpoints
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(system.router, prefix="/system", tags=["system"]) 
api_router.include_router(ws.router, prefix="/ws", tags=["websocket"]) 
api_router.include_router(activities.router, prefix="/activities", tags=["activities"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"]) 
api_router.include_router(security.router, prefix="/security", tags=["security"])
api_router.include_router(rules.router, prefix="/rules", tags=["rules"]) 
# New consolidated scans API
api_router.include_router(scans.router, prefix="/scans", tags=["scans"])
# Firmware management API
api_router.include_router(firmware.router, prefix="/firmware", tags=["firmware"])
# Device security information API
api_router.include_router(security_info.router, prefix="/security-info", tags=["security-info"])
# Dashboard API
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
# Device groups API
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
# Group security API
api_router.include_router(group_security.router, prefix="/group-security", tags=["group-security"])
# Desktop application auth API
api_router.include_router(desktop_auth.router, prefix="/auth", tags=["desktop-auth"])