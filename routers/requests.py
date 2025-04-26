from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated, List
from datetime import datetime

from models.request import RequestCreate, Request, RequestUpdate, RequestStatus
from models.user import UserRole
from database.operations import (
    create_request, 
    get_requests_by_project, 
    get_requests_by_worker,
    get_project,
    get_user_by_id
)
from routers.auth import get_current_user, check_user_role

router = APIRouter()

# Create inventory request (worker only)
@router.post("", response_model=Request)
async def request_inventory_item(
    request_data: RequestCreate,
    current_user: Annotated[dict, Depends(check_user_role([UserRole.WORKER]))]
):
    # Verify project exists
    project = await get_project(request_data.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Ensure worker is requesting for themselves
    if request_data.worker_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create requests for yourself"
        )
    
    # Add manager_id to the request data
    # For this example, we'll just use a simpler approach
    # In a real app, we would need to find the manager associated with the project
    project_manager = await get_user_by_id(project.get("manager_id", ""))
    if project_manager:
        request_data_dict = request_data.dict()
        request_data_dict["manager_id"] = project_manager["id"]
    else:
        request_data_dict = request_data.dict()
    
    # Create the request
    request_id = await create_request(request_data_dict)
    
    # Return the created request
    return {
        **request_data_dict,
        "id": request_id,
        "status": RequestStatus.PENDING,
        "created_at": datetime.utcnow()
    }

# Get requests for a project (manager only)
@router.get("/{project_id}", response_model=List[Request])
async def get_project_requests(
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
    
    # Get requests for the project
    requests = await get_requests_by_project(project_id)
    return requests

# Get requests for a worker (worker only)
@router.get("/worker/{worker_id}", response_model=List[Request])
async def get_worker_requests(
    worker_id: str,
    current_user: Annotated[dict, Depends(check_user_role([UserRole.WORKER]))]
):
    # Ensure worker is requesting their own requests
    if worker_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own requests"
        )
    
    # Get requests for the worker
    requests = await get_requests_by_worker(worker_id)
    return requests 