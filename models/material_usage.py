from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date as date_type

class MaterialUsageBase(BaseModel):
    item_name: str
    quantity_used: float = Field(..., gt=0)
    date: date_type = Field(default_factory=date_type.today)
    project_id: str

class MaterialUsageCreate(MaterialUsageBase):
    pass

class MaterialUsage(MaterialUsageBase):
    id: str
    created_at: datetime 