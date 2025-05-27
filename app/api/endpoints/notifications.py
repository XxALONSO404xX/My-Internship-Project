"""API endpoints for notification management"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_client

from app.api import schemas
from app.models.database import get_db
from app.services.notification_service import NotificationService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[schemas.NotificationResponse])
async def get_notifications(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all notifications with pagination
    """
    try:
        notification_service = NotificationService(db)
        notifications = await notification_service.get_all_notifications(limit=limit, offset=offset)
        return notifications
    except Exception as e:
        logger.error(f"Error retrieving notifications: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving notifications: {str(e)}")

@router.get("/unread", response_model=List[schemas.NotificationResponse])
async def get_unread_notifications(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_client)
):
    """
    Get all unread notifications
    """
    notification_service = NotificationService(db)
    notifications = await notification_service.get_unread_notifications()
    return notifications

@router.get("/{notification_id}", response_model=schemas.NotificationResponse)
async def get_notification(
    notification_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific notification by ID
    """
    notification_service = NotificationService(db)
    notification = await notification_service.get_notification_by_id(notification_id)
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return notification

@router.post("/", response_model=schemas.NotificationResponse)
async def create_notification(
    notification_data: schemas.NotificationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new notification
    """
    notification_service = NotificationService(db)
    
    try:
        # Log the input parameters for debugging
        logger.info(f"Creating notification with data: {notification_data.dict()}")
        
        notification = await notification_service.create_notification(
            title=notification_data.title,
            content=notification_data.content,
            notification_type=notification_data.notification_type,
            source=notification_data.source,
            source_id=notification_data.source_id,
            target_type=notification_data.target_type,
            target_id=notification_data.target_id,
            target_name=notification_data.target_name,
            priority=notification_data.priority,
            recipients=notification_data.recipients,
            channels=notification_data.channels,
            metadata=notification_data.notification_metadata
        )
        
        return notification
    
    except Exception as e:
        logger.error(f"Error creating notification: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating notification: {str(e)}")

@router.post("/{notification_id}/mark-read", response_model=schemas.NotificationResponse)
async def mark_notification_as_read(
    notification_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark a notification as read
    """
    notification_service = NotificationService(db)
    
    notification = await notification_service.mark_as_read(notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return notification

@router.post("/mark-all-read", response_model=schemas.Response)
async def mark_all_notifications_as_read(
    db: AsyncSession = Depends(get_db)
):
    """
    Mark all unread notifications as read
    """
    notification_service = NotificationService(db)
    
    count = await notification_service.mark_all_as_read()
    
    return schemas.Response(
        status="success",
        message=f"Marked {count} notifications as read"
    )

@router.delete("/{notification_id}", response_model=schemas.Response)
async def delete_notification(
    notification_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a notification
    """
    notification_service = NotificationService(db)
    
    success = await notification_service.delete_notification(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return schemas.Response(
        status="success",
        message=f"Notification {notification_id} deleted successfully"
    )

@router.post("/clear-old", response_model=schemas.Response)
async def clear_old_notifications(
    days_to_keep: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete notifications older than the specified number of days
    """
    notification_service = NotificationService(db)
    
    count = await notification_service.delete_old_notifications(days_to_keep=days_to_keep)
    
    return schemas.Response(
        status="success",
        message=f"Deleted {count} old notifications"
    )

@router.get("/filter", response_model=List[schemas.NotificationResponse])
async def filter_notifications(
    filter_params: schemas.NotificationFilter = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Filter notifications by various parameters
    """
    notification_service = NotificationService(db)
    
    # This would typically call a service method, but we'll implement it directly here
    # since we don't have a specific filtering method in the service
    
    query = f"""
    SELECT n.* 
    FROM notifications n
    WHERE 1=1
    """
    params = {}
    
    if filter_params.notification_type:
        query += " AND n.notification_type = :notification_type"
        params["notification_type"] = filter_params.notification_type
        
    if filter_params.source:
        query += " AND n.source = :source"
        params["source"] = filter_params.source
        
    if filter_params.source_id is not None:
        query += " AND n.source_id = :source_id"
        params["source_id"] = filter_params.source_id
        
    if filter_params.target_type:
        query += " AND n.target_type = :target_type"
        params["target_type"] = filter_params.target_type
        
    if filter_params.target_id is not None:
        query += " AND n.target_id = :target_id"
        params["target_id"] = filter_params.target_id
        
    if filter_params.priority is not None:
        query += " AND n.priority = :priority"
        params["priority"] = filter_params.priority
        
    if filter_params.is_read is not None:
        query += " AND n.is_read = :is_read"
        params["is_read"] = filter_params.is_read
        
    if filter_params.start_time:
        query += " AND n.created_at >= :start_time"
        params["start_time"] = filter_params.start_time
        
    if filter_params.end_time:
        query += " AND n.created_at <= :end_time"
        params["end_time"] = filter_params.end_time
        
    query += " ORDER BY n.created_at DESC LIMIT :limit OFFSET :skip"
    params["limit"] = filter_params.limit
    params["skip"] = filter_params.skip
    
    result = await db.execute(query, params)
    return result.all()

@router.post("/with-clients", response_model=schemas.NotificationResponse)
async def create_notification_with_clients(
    notification_data: schemas.NotificationWithClientsCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new notification with client relationships
    """
    try:
        notification_service = NotificationService(db)
        
        notification = await notification_service.create_notification_with_clients(
            title=notification_data.title,
            content=notification_data.content,
            client_ids=notification_data.client_ids,
            notification_type=notification_data.notification_type,
            source=notification_data.source,
            source_id=notification_data.source_id,
            target_type=notification_data.target_type,
            target_id=notification_data.target_id,
            target_name=notification_data.target_name,
            priority=notification_data.priority,
            channels=notification_data.channels,
            metadata=notification_data.metadata
        )
        
        return notification.to_dict()
    except Exception as e:
        logger.error(f"Error creating notification with clients: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create notification: {str(e)}"
        )

@router.post("/test-sms")
async def test_sms_notification(
    db: AsyncSession = Depends(get_db)
):
    """Test endpoint for SMS notifications"""
    try:
        notification_service = NotificationService(db)
        notification = await notification_service.create_notification(
            title="Test SMS Notification",
            content="This is a test SMS notification from the IoT Platform",
            notification_type="info",
            channels=["sms"],
            recipients=["+212702174311"],  # Your Twilio number
            priority=3
        )
        return {"message": "SMS notification sent", "notification": notification}
    except Exception as e:
        logger.error(f"Error sending test SMS: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error sending test SMS: {str(e)}")

@router.post("/simulate/trigger")
async def simulate_notification_trigger(
    notification_type: str = Query(..., enum=["info", "warning", "error", "success"]),
    title: str = Query(...),
    content: str = Query(...),
    channels: List[str] = Query(..., enum=["sms", "email", "push", "in_app"]),
    recipients: List[str] = Query(...),
    priority: int = Query(3, ge=1, le=5),
    metadata: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Simulate a notification trigger
    
    This endpoint is used for testing and simulation purposes to trigger notifications
    with custom data
    """
    try:
        notification_service = NotificationService(db)
        
        # Create notification
        notification = await notification_service.create_notification(
            title=title,
            content=content,
            notification_type=notification_type,
            channels=channels,
            recipients=recipients,
            priority=priority,
            metadata=metadata
        )
        
        # Send notification through all specified channels
        for channel in channels:
            try:
                await notification_service.send_notification(notification.id, channel)
            except Exception as e:
                logger.error(f"Error sending notification through {channel}: {str(e)}")
        
        return {
            "success": True,
            "notification": notification,
            "channels_attempted": channels
        }
        
    except Exception as e:
        logger.error(f"Error simulating notification trigger: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 