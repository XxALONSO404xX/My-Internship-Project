"""Dashboard API endpoints for IoT platform"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case, and_

from app.models.database import get_db
from app.models.device import Device
from app.models.activity import Activity
from app.models.firmware import FirmwareUpdate
from app.services.device_management_service import DeviceService
from app.services.activity_service import ActivityService
from app.api.deps import get_current_client

router = APIRouter()

@router.get("/summary", response_model=Dict[str, Any])
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """
    Get a comprehensive dashboard summary including:
    - Device status counts
    - Recent activity counts
    - Security status overview
    - Firmware update status
    - System health metrics
    """
    # Get device service
    device_service = DeviceService(db)
    
    # Calculate device summary
    device_summary = await device_service.get_device_summary()
    
    # Calculate recent activities (last 24 hours)
    activity_service = ActivityService(db)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    recent_activities = await activity_service.get_activities_count_by_time_range(
        start_time=start_time,
        end_time=end_time
    )
    
    # Get security overview
    security_overview = await get_security_overview(db)
    
    # Get firmware update status
    firmware_update_status = await get_firmware_update_status(db)
    
    # Get system health metrics (from system service)
    system_health = {
        "cpu_usage": 35,  # Placeholder - would come from actual system metrics
        "memory_usage": 42,
        "disk_usage": 28,
        "network_traffic": {
            "in": 1024,  # KB/s
            "out": 512   # KB/s
        }
    }
    
    return {
        "device_summary": device_summary,
        "recent_activities": recent_activities,
        "security_overview": security_overview,
        "firmware_update_status": firmware_update_status,
        "system_health": system_health,
        "last_updated": datetime.utcnow().isoformat()
    }

@router.get("/devices/status", response_model=Dict[str, Any])
async def get_device_status_summary(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """
    Get a summary of device statuses including:
    - Count of online/offline devices
    - Count by device type
    - Count by connection status
    - Recently added devices
    """
    device_service = DeviceService(db)
    summary = await device_service.get_device_summary()
    
    # Get recently added devices (last 7 days)
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    
    query = select(Device).where(Device.created_at >= one_week_ago).order_by(desc(Device.created_at)).limit(5)
    result = await db.execute(query)
    recent_devices = result.scalars().all()
    
    # Add recently added devices to summary
    summary["recently_added"] = [
        {
            "id": device.hash_id,
            "name": device.name,
            "type": device.device_type,
            "created_at": device.created_at.isoformat() if device.created_at else None,
            "status": "online" if device.is_online else "offline",
        }
        for device in recent_devices
    ]
    
    return summary

@router.get("/activities/summary", response_model=Dict[str, Any])
async def get_activity_summary(
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """
    Get a summary of activities for the dashboard including:
    - Count by activity type
    - Count by action
    - Daily activity trend
    - Most active devices
    """
    activity_service = ActivityService(db)
    
    # Get range for queries
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)
    
    # Get activity counts by type
    activities_by_type = await activity_service.get_activities_count_by_type(
        start_time=start_time,
        end_time=end_time
    )
    
    # Get activity counts by action
    activities_by_action = await activity_service.get_activities_count_by_action(
        start_time=start_time,
        end_time=end_time
    )
    
    # Get daily activity trend
    daily_trend = await activity_service.get_daily_activity_trend(
        start_time=start_time,
        end_time=end_time
    )
    
    # Get most active devices
    most_active_devices = await activity_service.get_most_active_devices(
        start_time=start_time,
        end_time=end_time,
        limit=5
    )
    
    return {
        "total_count": sum(activities_by_type.values()),
        "by_type": activities_by_type,
        "by_action": activities_by_action,
        "daily_trend": daily_trend,
        "most_active_devices": most_active_devices,
        "time_range": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        }
    }

@router.get("/security/overview", response_model=Dict[str, Any])
async def get_security_overview(
    db: AsyncSession = Depends(get_db)
):
    """
    Get a security overview for the dashboard including:
    - TLS adoption rate
    - Certificate status summary
    - Security rating distribution
    - Devices with security issues
    """
    # Query for TLS support statistics
    tls_query = select(
        func.count(Device.id).label("total"),
        func.sum(case((Device.supports_tls == True, 1), else_=0)).label("tls_enabled"),
        func.sum(case((and_(Device.supports_tls == True, Device.tls_version == "TLS 1.3"), 1), else_=0)).label("tls_1_3"),
        func.sum(case((and_(Device.supports_tls == True, Device.tls_version == "TLS 1.2"), 1), else_=0)).label("tls_1_2"),
        func.sum(case((and_(Device.supports_tls == True, Device.tls_version < "TLS 1.2"), 1), else_=0)).label("tls_older")
    )
    
    tls_result = await db.execute(tls_query)
    tls_stats = tls_result.mappings().one()
    
    # Calculate TLS adoption rate
    total_devices = tls_stats["total"] or 0
    tls_enabled = tls_stats["tls_enabled"] or 0
    tls_adoption_rate = (tls_enabled / total_devices * 100) if total_devices > 0 else 0
    
    # Query for certificate status
    now = datetime.utcnow()
    cert_query = select(
        func.sum(case((Device.cert_expiry == None, 1), else_=0)).label("no_cert"),
        func.sum(case((Device.cert_expiry < now, 1), else_=0)).label("expired"),
        func.sum(case((and_(Device.cert_expiry >= now, Device.cert_expiry < (now + timedelta(days=30))), 1), else_=0)).label("expiring_soon"),
        func.sum(case((Device.cert_expiry >= (now + timedelta(days=30)), 1), else_=0)).label("valid")
    ).where(Device.supports_tls == True)
    
    cert_result = await db.execute(cert_query)
    cert_stats = cert_result.mappings().one()
    
    # Query for security rating distribution
    # This would require implementing a security rating calculation
    # For now, we'll use a placeholder distribution
    
    # Get devices with security issues (expired certs, low rating, etc.)
    security_issues_query = select(Device).where(
        (Device.supports_tls == True) & 
        ((Device.cert_expiry < now) | (Device.cert_expiry == None))
    ).limit(5)
    
    security_issues_result = await db.execute(security_issues_query)
    devices_with_issues = security_issues_result.scalars().all()
    
    return {
        "tls_adoption": {
            "rate": round(tls_adoption_rate, 1),
            "total_devices": total_devices,
            "tls_enabled": tls_enabled,
            "by_version": {
                "TLS 1.3": tls_stats["tls_1_3"] or 0,
                "TLS 1.2": tls_stats["tls_1_2"] or 0,
                "Older": tls_stats["tls_older"] or 0
            }
        },
        "certificate_status": {
            "no_cert": cert_stats["no_cert"] or 0,
            "expired": cert_stats["expired"] or 0,
            "expiring_soon": cert_stats["expiring_soon"] or 0,
            "valid": cert_stats["valid"] or 0
        },
        "security_rating_distribution": {
            "high": int(total_devices * 0.6),  # Placeholder values
            "medium": int(total_devices * 0.3),
            "low": int(total_devices * 0.1)
        },
        "devices_with_issues": [
            {
                "id": device.hash_id,
                "name": device.name,
                "issue": "Expired certificate" if (device.cert_expiry and device.cert_expiry < now) else "Missing certificate",
                "last_updated": device.updated_at.isoformat() if device.updated_at else None
            }
            for device in devices_with_issues
        ]
    }

@router.get("/firmware/status", response_model=Dict[str, Any])
async def get_firmware_update_status(
    db: AsyncSession = Depends(get_db)
):
    """
    Get firmware update status for the dashboard including:
    - Recent updates count
    - Success/failure rate
    - Devices needing updates
    - Update history trend
    """
    # Query for firmware update statistics
    now = datetime.utcnow()
    last_month = now - timedelta(days=30)
    
    # Count recent updates
    updates_query = select(
        func.count(FirmwareUpdate.id).label("total"),
        func.sum(case((FirmwareUpdate.status == "success", 1), else_=0)).label("successful"),
        func.sum(case((FirmwareUpdate.status == "failed", 1), else_=0)).label("failed"),
        func.sum(case((FirmwareUpdate.status == "in_progress", 1), else_=0)).label("in_progress")
    ).where(FirmwareUpdate.created_at >= last_month)
    
    updates_result = await db.execute(updates_query)
    update_stats = updates_result.mappings().one()
    
    # Calculate success rate
    total_completed = (update_stats["successful"] or 0) + (update_stats["failed"] or 0)
    success_rate = ((update_stats["successful"] or 0) / total_completed * 100) if total_completed > 0 else 0
    
    # Get devices needing updates (placeholder - this would need device firmware version comparison logic)
    # For this example, we'll just select some random devices
    devices_needing_updates_query = select(Device).where(
        Device.last_firmware_check < (now - timedelta(days=60))
    ).limit(5)
    
    devices_result = await db.execute(devices_needing_updates_query)
    devices_needing_updates = devices_result.scalars().all()
    
    # Generate update history trend (placeholder)
    # In a real implementation, you would query daily update counts
    days = 7
    update_trend = []
    for i in range(days):
        day = now - timedelta(days=days-i-1)
        update_trend.append({
            "date": day.strftime("%Y-%m-%d"),
            "count": 5 + i  # Placeholder data
        })
    
    return {
        "recent_updates": {
            "total": update_stats["total"] or 0,
            "successful": update_stats["successful"] or 0,
            "failed": update_stats["failed"] or 0,
            "in_progress": update_stats["in_progress"] or 0,
            "success_rate": round(success_rate, 1)
        },
        "devices_needing_updates": [
            {
                "id": device.hash_id,
                "name": device.name,
                "current_version": "1.0.0",  # Placeholder
                "latest_version": "1.1.0",   # Placeholder
                "last_checked": device.last_firmware_check.isoformat() if device.last_firmware_check else None
            }
            for device in devices_needing_updates
        ],
        "update_history_trend": update_trend,
        "time_range": {
            "start": last_month.isoformat(),
            "end": now.isoformat()
        }
    }
