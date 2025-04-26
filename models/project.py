from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date as date_type
from enum import Enum

class ProjectStatus(str, Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"

class ProgressReport(BaseModel):
    report_date: date_type
    description: str
    percentage_complete: float = Field(..., ge=0, le=100)
    created_at: Optional[datetime] = None

class ProjectBase(BaseModel):
    name: str
    description: str
    location: str
    budget: float
    start_date: date_type
    end_date: date_type
    client_id: str

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: str
    created_at: datetime
    progress_reports: List[ProgressReport] = []

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date_type] = None
    end_date: Optional[date_type] = None

class ProgressReportCreate(BaseModel):
    report_date: date_type = Field(default_factory=date_type.today)
    description: str
    percentage_complete: float = Field(..., ge=0, le=100)

class ProjectSummary(BaseModel):
    project_name: str
    total_expenses: float
    material_usage: dict
    progress_percentage: float
    start_date: date_type
    end_date: date_type
    expenses_count: int
    material_usage_count: int 