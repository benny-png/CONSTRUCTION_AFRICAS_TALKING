from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from models.notification import Notification
from models.user import UserRole
from database.operations import get_notifications, mark_notification_read
from routers.auth import get_current_user, check_user_role

router = APIRouter()

# Get notifications for a user
@router.get("/{user_id}", response_model=List[Notification])
async def get_user_notifications(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Ensure user is getting their own notifications
    if user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own notifications"
        )
    
    # Get notifications
    notifications = await get_notifications(user_id)
    return notifications

# Mark notification as read
@router.patch("/{notification_id}/read", status_code=status.HTTP_200_OK)
async def mark_notification_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Mark as read
    success = await mark_notification_read(notification_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as read"
        )
    
    return {"message": "Notification marked as read"} 