from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from typing import Annotated, List, Optional
import traceback
from datetime import date, timedelta, datetime

from models.project import ProjectCreate, Project, ProgressReportCreate, ProjectSummary, ProjectStatus, ProjectUpdate
from models.user import UserRole
from database.operations import (
    create_project, 
    get_project, 
    get_projects_by_client, 
    add_progress_report, 
    get_progress_reports,
    get_project_summary,
    add_project,
    get_all_projects,
    update_project,
    delete_project,
    get_user
)
from routers.auth import get_current_user, check_user_role
from logging_config import logger

router = APIRouter()

# Create a new project (manager only)
@router.post(
    "", 
    response_model=Project,
    summary="Create a new project (Manager only)",
    description="""
    Create a new construction project.
    
    This endpoint is accessible only to users with the **manager** role.
    
    ### Input Parameters
    
    **Required:**
    - `name` (string): Name of the project.
      Example: "Kindaruma Heights Apartment Building"
    - `description` (string): Detailed description of the project.
      Example: "Construction of a 15-floor luxury apartment building"
    - `location` (string): Location where the project will be built.
      Example: "Kindaruma Road, Nairobi"
    - `budget` (number): Total project budget in currency units.
      Example: 150000000
    - `start_date` (string): Project start date in YYYY-MM-DD format.
      Example: "2023-09-01"
    - `end_date` (string): Expected project completion date in YYYY-MM-DD format.
      Example: "2025-03-31"
    - `client_id` (string): ID of the client who owns the project.
      Example: "60d21b4667d0d8992e610c85"
    
    ### Response Format
    
    ```json
    {
      "id": "61a23c4567d0d8992e610d96",
      "name": "Kindaruma Heights Apartment Building",
      "description": "Construction of a 15-floor luxury apartment building",
      "location": "Kindaruma Road, Nairobi",
      "budget": 150000000,
      "start_date": "2023-09-01",
      "end_date": "2025-03-31",
      "client_id": "60d21b4667d0d8992e610c85",
      "status": "planning",
      "created_at": "2023-08-15T14:25:30.123Z",
      "progress_reports": []
    }
    ```
    
    ### Authorization
    
    Requires a valid JWT token with manager role.
    
    ### curl Example
    ```bash
    curl -X 'POST' \\
      'https://construction.contactmanagers.xyz/projects' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \\
      -H 'Content-Type: application/json' \\
      -d '{
        "name": "Kindaruma Heights Apartment Building",
        "description": "Construction of a 15-floor luxury apartment building",
        "location": "Kindaruma Road, Nairobi",
        "budget": 150000000,
        "start_date": "2023-09-01",
        "end_date": "2025-03-31",
        "client_id": "60d21b4667d0d8992e610c85"
      }'
    ```
    """,
    response_description="Returns the newly created project with an ID and creation timestamp"
)
async def create_project(
    project: ProjectCreate = Body(
        ...,
        example={
            "name": "Kindaruma Heights Apartment Building",
            "description": "Construction of a 15-floor luxury apartment building",
            "location": "Kindaruma Road, Nairobi",
            "budget": 150000000,
            "start_date": "2023-09-01",
            "end_date": "2025-03-31",
            "client_id": "60d21b4667d0d8992e610c85"
        }
    ),
    token_data: dict = Depends(check_user_role([UserRole.MANAGER])),
    request: Request = None
):
    """
    Create a new construction project.
    
    Requires manager role.
    """
    try:
        # Access token data for user identification
        user_id = token_data.get("user_id", "unknown")
        username = token_data.get("sub", "unknown")
        logger.info(f"Creating new project: {project.name} by user {username} (ID: {user_id})")
        
        # Verify client exists
        client = await get_user(project.client_id)
        logger.debug(f"Client data type: {type(client)}, value: {client}")
        
        if not client:
            logger.warning(f"Client not found: {project.client_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found"
            )
        
        # Check if client data is valid
        if not isinstance(client, dict):
            logger.error(f"Invalid client data format: {client}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid client data format"
            )
        
        # Check if role field exists
        if "role" not in client:
            logger.error(f"Missing role field in client data: {client}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid client data: missing role field"
            )
        
        # Check if client is actually a client
        if client["role"] != UserRole.CLIENT.value:
            logger.warning(f"User {project.client_id} is not a client, role is {client['role']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User is not a client. User has role: {client['role']}"
            )
        
        # Create project
        project_data = project.dict()
        project_data["status"] = ProjectStatus.PLANNING.value  # Use the string value
        project_data["created_by"] = user_id  # Add creator information
        
        # Convert date objects to datetime objects for MongoDB compatibility
        if isinstance(project_data["start_date"], date):
            start_date = project_data["start_date"]
            project_data["start_date"] = datetime.combine(start_date, datetime.min.time())
            
        if isinstance(project_data["end_date"], date):
            end_date = project_data["end_date"]
            project_data["end_date"] = datetime.combine(end_date, datetime.min.time())
        
        logger.debug(f"Project data: {project_data}")
        
        project_id = await add_project(project_data)
        logger.debug(f"Project created with ID: {project_id}")
        
        # Return created project
        result = {
            **project_data,
            "id": project_id
        }
        
        logger.info(f"Project created successfully, ID: {project_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating project: {str(e)}"
        )

# Get all projects (manager, client, worker)
@router.get(
    "", 
    response_model=List[Project],
    summary="Get all projects (All roles)",
    description="""
    Get a list of all projects.
    
    Accessible to users with any role, but with different results:
    - **managers**: see all projects
    - **clients**: see only their own projects
    - **workers**: see only projects they are assigned to
    
    Results can be filtered by status and client ID.
    
    ### curl Example
    ```bash
    curl -X 'GET' \\
      'https://construction.contactmanagers.xyz/projects?status=in_progress&client_id=60d21b4667d0d8992e610c85' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    ```
    """,
    response_description="Returns a list of projects with their details"
)
async def get_projects(
    status: Optional[ProjectStatus] = None,
    client_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    request: Request = None
):
    """
    Get a list of all projects with optional filtering.
    
    Accessible to all roles.
    """
    try:
        # Access user information from the combined user object
        username = current_user.get("username", "unknown")
        role = current_user.get("role", "unknown")
        user_id = current_user.get("id", "unknown")
        
        logger.info(f"Getting projects list for user {username}, role: {role}")
        logger.debug(f"Filters - status: {status}, client_id: {client_id}")
        
        # If client, override client_id filter with their own ID
        if role == UserRole.CLIENT.value:
            client_id = user_id
            logger.debug(f"Client user, filtering by their ID: {client_id}")
        
        # Get projects based on filters
        projects = await get_all_projects(status, client_id)
        
        # If worker, filter to only show projects they're assigned to
        # Note: Worker assignment feature to be implemented in database operations
        
        logger.debug(f"Found {len(projects)} projects matching filters")
        return projects
    except Exception as e:
        logger.error(f"Error getting projects: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting projects: {str(e)}"
        )

# Get a specific project (manager, client, worker)
@router.get(
    "/{project_id}", 
    response_model=Project,
    summary="Get a specific project (All roles)",
    description="""
    Get a specific project by its ID.
    
    Accessible to users with any role, but with restrictions:
    - **managers**: can access any project
    - **clients**: can only access their own projects
    - **workers**: can only access projects they are assigned to
    
    ### curl Example
    ```bash
    curl -X 'GET' \\
      'https://construction.contactmanagers.xyz/projects/61a23c4567d0d8992e610d96' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    ```
    """,
    response_description="Returns the project details"
)
async def get_project_by_id(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    request: Request = None
):
    """
    Get a specific project by its ID.
    
    Accessible to all roles with appropriate permissions.
    """
    try:
        # Access user information from the combined user object
        username = current_user.get("username", "unknown")
        role = current_user.get("role", "unknown")
        user_id = current_user.get("id", "unknown")
        
        logger.info(f"Getting project {project_id} for user {username}")
        
        # Get the project
        project = await get_project(project_id)
        if not project:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check access permissions
        if role == UserRole.CLIENT.value and project["client_id"] != user_id:
            logger.warning(f"Access denied to project {project_id} for client {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        # Note: Worker access control to be implemented
        
        logger.info(f"Project {project_id} accessed successfully")
        return project
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting project: {str(e)}"
        )

# Update a project (manager only)
@router.put(
    "/{project_id}", 
    response_model=Project,
    summary="Update a project (Manager only)",
    description="""
    Update an existing project's details.
    
    This endpoint is accessible only to users with the **manager** role.
    
    Any field that is not provided will remain unchanged.
    
    ### curl Example
    ```bash
    curl -X 'PUT' \\
      'https://construction.contactmanagers.xyz/projects/61a23c4567d0d8992e610d96' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \\
      -H 'Content-Type: application/json' \\
      -d '{
        "name": "Kindaruma Heights Phase 2",
        "budget": 175000000,
        "status": "in_progress",
        "end_date": "2025-06-30"
      }'
    ```
    """,
    response_description="Returns the updated project with all fields"
)
async def update_project_details(
    project_id: str,
    project_update: ProjectUpdate = Body(
        ...,
        example={
            "name": "Kindaruma Heights Phase 2",
            "budget": 175000000,
            "status": "in_progress",
            "end_date": "2025-06-30"
        }
    ),
    token_data: dict = Depends(check_user_role([UserRole.MANAGER])),
    request: Request = None
):
    """
    Update an existing project's details.
    
    Requires manager role.
    """
    try:
        # Access token data for user identification
        user_id = token_data.get("user_id", "unknown")
        username = token_data.get("sub", "unknown")
        logger.info(f"Updating project: {project_id} by user {username} (ID: {user_id})")
        logger.debug(f"Update data: {project_update.dict(exclude_unset=True)}")
        
        # Verify project exists
        project = await get_project(project_id)
        if not project:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # If client_id is being updated, verify new client exists
        if project_update.client_id is not None and project_update.client_id != project["client_id"]:
            client = await get_user(project_update.client_id)
            if not client:
                logger.warning(f"Client not found: {project_update.client_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="New client not found"
                )
            
            # Check if client is actually a client
            if client["role"] != UserRole.CLIENT.value:
                logger.warning(f"User {project_update.client_id} is not a client")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is not a client"
                )
        
        # Update the project
        update_data = project_update.dict(exclude_unset=True)
        
        # Convert date objects to datetime objects for MongoDB compatibility
        if "start_date" in update_data and isinstance(update_data["start_date"], date):
            start_date = update_data["start_date"]
            update_data["start_date"] = datetime.combine(start_date, datetime.min.time())
            
        if "end_date" in update_data and isinstance(update_data["end_date"], date):
            end_date = update_data["end_date"]
            update_data["end_date"] = datetime.combine(end_date, datetime.min.time())
            
        # Record who made the update
        update_data["updated_by"] = user_id
        update_data["updated_at"] = datetime.utcnow()
        
        logger.debug(f"Applying updates: {update_data}")
        
        updated_project = await update_project(project_id, update_data)
        if not updated_project:
            logger.error(f"Failed to update project: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update project"
            )
        
        logger.info(f"Project {project_id} updated successfully")
        return updated_project
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating project: {str(e)}"
        )

# Delete a project (manager only)
@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project (Manager only)",
    description="""
    Delete a project completely from the system.
    
    This endpoint is accessible only to users with the **manager** role.
    
    This operation is permanent and cannot be undone. All associated data
    (expenses, tasks, etc.) will also be deleted.
    
    ### curl Example
    ```bash
    curl -X 'DELETE' \\
      'https://construction.contactmanagers.xyz/projects/61a23c4567d0d8992e610d96' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    ```
    """,
    response_description="No content is returned on successful deletion"
)
async def delete_project_by_id(
    project_id: str,
    token_data: dict = Depends(check_user_role([UserRole.MANAGER])),
    request: Request = None
):
    """
    Delete a project completely from the system.
    
    Requires manager role.
    """
    try:
        # Access token data for user identification
        user_id = token_data.get("user_id", "unknown")
        username = token_data.get("sub", "unknown")
        logger.info(f"Deleting project: {project_id} by user {username} (ID: {user_id})")
        
        # Verify project exists
        project = await get_project(project_id)
        if not project:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Delete the project
        success = await delete_project(project_id)
        if not success:
            logger.error(f"Failed to delete project: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete project"
            )
        
        logger.info(f"Project {project_id} deleted successfully by {username}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting project: {str(e)}"
        )

# Get projects by client ID (manager & client)
@router.get(
    "/client/{client_id}", 
    response_model=List[Project],
    summary="Get projects for a client (Manager & Client)",
    description="""
    Get all projects associated with a specific client.
    
    This endpoint is accessible to:
    - **managers**: can access projects for any client
    - **clients**: can only access their own projects
    
    Workers cannot access this endpoint.
    """,
    response_description="Returns a list of projects for the specified client"
)
async def get_projects_for_client(
    client_id: str,
    token_data: Annotated[dict, Depends(check_user_role([UserRole.MANAGER, UserRole.CLIENT]))]=None,
    request: Request=None
):
    """
    Get all projects associated with a specific client.
    
    Requires manager or client role.
    """
    try:
        # Access token data for user identification
        user_id = token_data.get("user_id", "unknown")
        username = token_data.get("sub", "unknown")
        role = token_data.get("role", "unknown")
        
        logger.info(f"Getting projects for client: {client_id} by user {username} (role: {role})")
        
        # If client, check if they are requesting their own projects
        if role == UserRole.CLIENT.value and client_id != user_id:
            logger.warning(f"Access denied to projects for client {client_id} by client {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to other client's projects"
            )
        
        projects = await get_projects_by_client(client_id)
        logger.debug(f"Found {len(projects)} projects for client {client_id}")
        return projects
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting projects for client: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting projects for client: {str(e)}"
        )

# Submit progress report (manager only)
@router.post(
    "/{project_id}/progress", 
    status_code=status.HTTP_201_CREATED,
    summary="Submit progress report (Manager only)",
    description="""
    Submit a progress report for a specific project.
    
    This endpoint is accessible only to users with the **manager** role.
    
    The progress report includes the current completion percentage and a 
    description of the work done.
    
    ### curl Example
    ```bash
    curl -X 'POST' \\
      'https://construction.contactmanagers.xyz/projects/61a23c4567d0d8992e610d96/progress' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \\
      -H 'Content-Type: application/json' \\
      -d '{
        "report_date": "2023-10-01",
        "description": "Completed foundation work and started framing",
        "percentage_complete": 25.5
      }'
    ```
    """,
    response_description="Returns a confirmation message"
)
async def submit_progress_report(
    project_id: str,
    report_data: ProgressReportCreate = Body(
        ...,
        example={
            "report_date": str(date.today()),
            "description": "Completed foundation work and started framing",
            "percentage_complete": 25.5
        }
    ),
    token_data: Annotated[dict, Depends(check_user_role([UserRole.MANAGER]))]=None,
    request: Request=None
):
    """
    Submit a progress report for a specific project.
    
    Requires manager role.
    """
    try:
        # Access token data for user identification
        user_id = token_data.get("user_id", "unknown")
        username = token_data.get("sub", "unknown")
        
        logger.info(f"Submitting progress report for project: {project_id} by user {username}")
        logger.debug(f"Report data: {report_data.dict()}")
        
        # Verify project exists
        project = await get_project(project_id)
        if not project:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Add submitter information to the report
        report_dict = report_data.dict()
        report_dict["submitted_by"] = user_id
        
        # Convert date objects to datetime objects for MongoDB compatibility
        if "report_date" in report_dict and isinstance(report_dict["report_date"], date):
            report_date = report_dict["report_date"]
            report_dict["report_date"] = datetime.combine(report_date, datetime.min.time())
        
        # Add progress report
        await add_progress_report(project_id, report_dict)
        logger.info(f"Progress report submitted successfully for project: {project_id} by {username}")
        
        return {"message": "Progress report submitted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting progress report: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting progress report: {str(e)}"
        )

# Get progress reports for a project (manager & client)
@router.get(
    "/{project_id}/progress", 
    response_model=List[ProgressReportCreate],
    summary="Get project progress reports (Manager & Client)",
    description="""
    Get all progress reports for a specific project.
    
    This endpoint is accessible to:
    - **managers**: can access progress reports for any project
    - **clients**: can only access progress reports for their own projects
    
    Workers cannot access this endpoint.
    """,
    response_description="Returns a list of progress reports for the specified project"
)
async def get_project_progress(
    project_id: str,
    token_data: Annotated[dict, Depends(check_user_role([UserRole.MANAGER, UserRole.CLIENT]))]=None,
    request: Request=None
):
    """
    Get all progress reports for a specific project.
    
    Requires manager or client role.
    """
    try:
        # Access token data for user identification
        user_id = token_data.get("user_id", "unknown")
        username = token_data.get("sub", "unknown")
        role = token_data.get("role", "unknown")
        
        logger.info(f"Getting progress reports for project: {project_id} by user {username} (role: {role})")
        
        # Verify project exists
        project = await get_project(project_id)
        if not project:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # If client, check if they are the client for this project
        if role == UserRole.CLIENT.value and project["client_id"] != user_id:
            logger.warning(f"Access denied to project {project_id} for client {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        # Get progress reports
        reports = await get_progress_reports(project_id)
        logger.debug(f"Found {len(reports)} progress reports for project {project_id}")
        
        return reports
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting progress reports: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting progress reports: {str(e)}"
        )

# Get project summary statistics (manager & client)
@router.get(
    "/{project_id}/summary", 
    response_model=ProjectSummary,
    summary="Get project summary statistics (Manager & Client)",
    description="""
    Get summary statistics for a specific project.
    
    This endpoint is accessible to:
    - **managers**: can access summary for any project
    - **clients**: can only access summary for their own projects
    
    The summary includes:
    - Total expenses
    - Total materials used
    - Current progress percentage
    - Project timeline
    - Material usage counts
    
    Workers cannot access this endpoint.
    
    ### curl Example
    ```bash
    curl -X 'GET' \\
      'https://construction.contactmanagers.xyz/projects/61a23c4567d0d8992e610d96/summary' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    ```
    """,
    response_description="Returns a summary of project statistics"
)
async def get_project_stats(
    project_id: str,
    token_data: Annotated[dict, Depends(check_user_role([UserRole.MANAGER, UserRole.CLIENT]))]=None,
    request: Request=None
):
    """
    Get summary statistics for a specific project.
    
    Requires manager or client role.
    """
    try:
        # Access token data for user identification
        user_id = token_data.get("user_id", "unknown")
        username = token_data.get("sub", "unknown")
        role = token_data.get("role", "unknown")
        
        logger.info(f"Getting summary for project: {project_id} by user {username} (role: {role})")
        
        # Verify project exists
        project = await get_project(project_id)
        if not project:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # If client, check if they are the client for this project
        if role == UserRole.CLIENT.value and project["client_id"] != user_id:
            logger.warning(f"Access denied to project {project_id} for client {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        # Get summary
        summary = await get_project_summary(project_id)
        logger.debug(f"Project summary generated for project {project_id}")
        
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project summary: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting project summary: {str(e)}"
        ) 