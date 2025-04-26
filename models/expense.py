from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date as date_type
from enum import Enum

class VerificationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    FLAGGED = "flagged"

class ExpenseBase(BaseModel):
    amount: float = Field(..., gt=0)
    description: str
    date: date_type = Field(default_factory=date_type.today)
    project_id: str

class ExpenseCreate(ExpenseBase):
    pass

class Expense(ExpenseBase):
    id: str
    receipt_url: Optional[str] = None
    verified: VerificationStatus
    created_at: datetime

class ExpenseUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    description: Optional[str] = None
    date: Optional[date_type] = None

class ExpenseVerify(BaseModel):
    status: VerificationStatus 