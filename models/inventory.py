from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class InventoryItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    quantity: float = Field(..., gt=0)
    unit: str
    cost_per_unit: Optional[float] = None
    project_id: str

class InventoryItemCreate(InventoryItemBase):
    pass

class InventoryItem(InventoryItemBase):
    id: str
    image_url: Optional[str] = None
    created_at: datetime

class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = None
    cost_per_unit: Optional[float] = None
    image_url: Optional[str] = None 