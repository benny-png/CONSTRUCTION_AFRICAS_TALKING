from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class RequestBase(BaseModel):
    item_name: str
    quantity: float = Field(..., gt=0)
    project_id: str
    worker_id: str
    manager_id: Optional[str] = None

class RequestCreate(RequestBase):
    pass

class Request(RequestBase):
    id: str
    status: RequestStatus
    created_at: datetime

class RequestUpdate(BaseModel):
    status: RequestStatus 