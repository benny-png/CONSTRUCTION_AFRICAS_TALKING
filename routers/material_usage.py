from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, List
from datetime import datetime

from models.material_usage import MaterialUsageCreate, MaterialUsage
from models.user import UserRole
from database.operations import log_material_usage, get_material_usage_by_project, get_project
from routers.auth import get_current_user, check_user_role

router = APIRouter()

# Log material usage (manager only)
@router.post("", response_model=MaterialUsage)
async def log_daily_material_usage(
    usage_data: MaterialUsageCreate,
    current_user: Annotated[dict, Depends(check_user_role([UserRole.MANAGER]))]
):
    # Verify project exists
    project = await get_project(usage_data.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Log material usage
    usage_id = await log_material_usage(usage_data.dict())
    
    # Return the created usage log
    return {
        **usage_data.dict(),
        "id": usage_id,
        "created_at": datetime.utcnow()
    }

# Get material usage logs for a project (manager only)
@router.get("/{project_id}", response_model=List[MaterialUsage])
async def get_project_material_usage(
    project_id: str,
    current_user: Annotated[dict, Depends(check_user_role([UserRole.MANAGER]))]
):
    # Verify project exists
    project = await get_project(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Get material usage logs
    logs = await get_material_usage_by_project(project_id)
    return logs 