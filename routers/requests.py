from fastapi import APIRouter, Depends, HTTPException, status, Body
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
@router.post(
    "", 
    response_model=Request,
    summary="Create inventory request (Worker only)",
    description="""
    Create a new inventory request for materials or tools.
    
    This endpoint is accessible only to users with the **worker** role.
    
    Workers can only create requests for themselves.
    
    ### curl Example
    ```bash
    curl -X 'POST' \\
      'https://construction.contactmanagers.xyz/requests' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \\
      -H 'Content-Type: application/json' \\
      -d '{
        "project_id": "61a23c4567d0d8992e610d96",
        "worker_id": "60d21b4667d0d8992e610c87",
        "item_name": "Cement bags",
        "quantity": 10,
        "urgency": "high",
        "notes": "Needed for foundation work tomorrow"
      }'
    ```
    """,
    response_description="Returns the created request with an ID, status, and timestamp"
)
async def request_inventory_item(
    current_user: Annotated[dict, Depends(check_user_role([UserRole.WORKER]))],
    request_data: RequestCreate = Body(
        ...,
        example={
            "project_id": "61a23c4567d0d8992e610d96",
            "worker_id": "60d21b4667d0d8992e610c87",
            "item_name": "Cement bags",
            "quantity": 10,
            "urgency": "high",
            "notes": "Needed for foundation work tomorrow"
        }
    )
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
@router.get(
    "/{project_id}", 
    response_model=List[Request],
    summary="Get project requests (Manager only)",
    description="""
    Get all inventory requests for a specific project.
    
    This endpoint is accessible only to users with the **manager** role.
    
    ### curl Example
    ```bash
    curl -X 'GET' \\
      'https://construction.contactmanagers.xyz/requests/61a23c4567d0d8992e610d96' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    ```
    """,
    response_description="Returns a list of inventory requests for the specified project"
)
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
@router.get(
    "/worker/{worker_id}", 
    response_model=List[Request],
    summary="Get worker requests (Worker only)",
    description="""
    Get all inventory requests made by a specific worker.
    
    This endpoint is accessible only to users with the **worker** role.
    
    Workers can only view their own requests.
    
    ### curl Example
    ```bash
    curl -X 'GET' \\
      'https://construction.contactmanagers.xyz/requests/worker/60d21b4667d0d8992e610c87' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    ```
    """,
    response_description="Returns a list of inventory requests made by the specified worker"
)
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