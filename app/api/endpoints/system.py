import platform
import socket
import time
import psutil
from typing import List
from fastapi import APIRouter, Depends
import ipaddress
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.services.device_management_service import create_device_scanner
from app.api.schemas import SystemInfo, NetworkInterface, Response

router = APIRouter()
start_time = time.time()

@router.get("/info", response_model=SystemInfo)
async def get_system_info(db: AsyncSession = Depends(get_db)):
    """
    Get system information
    """
    scanner = create_device_scanner(db)
    # Get network interfaces directly
    interfaces = []
    
    try:
        # Create a socket and connect to an external address to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to Google's DNS - this doesn't send any data
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Use the local IP to determine the network
        network_prefix = '.'.join(local_ip.split('.')[:3])
        
        interfaces.append({
            "name": "default",
            "ip": local_ip,
            "netmask": "255.255.255.0",  # Assume /24 network
            "broadcast": f"{network_prefix}.255"
        })
    except:
        # Fallback to localhost
        interfaces.append({
            "name": "loopback",
            "ip": "127.0.0.1",
            "netmask": "255.0.0.0",
            "broadcast": None
        })
    
    return SystemInfo(
        version="1.0.0",  # App version
        uptime=time.time() - start_time,  # Uptime in seconds
        hostname=socket.gethostname(),
        network_interfaces=[
            NetworkInterface(
                name=iface["name"],
                ip=iface["ip"],
                netmask=iface.get("netmask"),
                broadcast=iface.get("broadcast")
            ) for iface in interfaces
        ]
    )

@router.get("/health", response_model=Response)
async def health_check():
    """
    Simple health check endpoint
    """
    return Response(status="ok", message="Service is running")

@router.get("/metrics")
async def get_system_metrics():
    """
    Get system resource metrics
    """
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "cpu": {
            "usage_percent": cpu_percent,
            "core_count": psutil.cpu_count()
        },
        "memory": {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "usage_percent": memory.percent
        },
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "usage_percent": disk.percent
        }
    } 