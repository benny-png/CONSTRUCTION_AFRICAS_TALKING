from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class InventoryItemBase(BaseModel):
    name: str
    quantity: float = Field(..., gt=0)
    unit: str
    project_id: str

class InventoryItemCreate(InventoryItemBase):
    pass

class InventoryItem(InventoryItemBase):
    id: str
    created_at: datetime

class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = None 