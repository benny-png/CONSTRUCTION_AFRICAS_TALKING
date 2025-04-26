from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class NotificationType(str, Enum):
    INVENTORY_REQUEST = "inventory_request"
    EXPENSE_VERIFICATION = "expense_verification"
    PROJECT_UPDATE = "project_update"

class NotificationBase(BaseModel):
    user_id: str
    type: NotificationType
    message: str
    read: bool = False
    request_id: Optional[str] = None
    expense_id: Optional[str] = None
    project_id: Optional[str] = None

class Notification(NotificationBase):
    id: str
    created_at: datetime 