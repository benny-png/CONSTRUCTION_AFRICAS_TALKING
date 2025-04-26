from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from typing import Annotated, List, Optional
import traceback

from models.user import User, UserRole, UserUpdate
from database.operations import get_users, get_user_by_id as get_user, update_user, delete_user, get_users_by_role
from routers.auth import get_current_user, check_user_role
from logging_config import logger

router = APIRouter()

# Get all users (manager only)
@router.get(
    "/", 
    response_model=List[User],
    summary="Get all users (Manager only)",
    description="""
    Retrieve a list of all users in the system.
    
    This endpoint is accessible only to users with the **manager** role.
    Returns a list of all registered users without their passwords.
    
    ### curl example:
    ```
    curl -X GET "https://construction.contactmanagers.xyz/users" \\
      -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    ```
    """,
    response_description="Returns a list of all users"
)
async def read_users(
    current_user: Annotated[dict, Depends(check_user_role([UserRole.MANAGER]))],
    request: Request = None
):
    """
    Get all users (manager only).
    """
    try:
        logger.info("Getting all users")
        users = await get_users()
        
        # Remove passwords from all users
        for user in users:
            user.pop("password", None)
        
        logger.info(f"Retrieved {len(users)} users")
        return users
    except Exception as e:
        logger.error(f"Error retrieving users: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving users: {str(e)}"
        )

# Get user by ID (manager only)
@router.get(
    "/{user_id}", 
    response_model=User,
    summary="Get user by ID (Manager only)",
    description="""
    Retrieve a specific user by their ID.
    
    This endpoint is accessible only to users with the **manager** role.
    Returns the user information without their password.
    
    If the user with the specified ID does not exist, a 404 error is returned.
    
    ### curl example:
    ```
    curl -X GET "https://construction.contactmanagers.xyz/users/USER_ID" \\
      -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    ```
    """,
    response_description="Returns the specified user information"
)
async def read_user(
    user_id: str,
    current_user: Annotated[dict, Depends(check_user_role([UserRole.MANAGER]))],
    request: Request = None
):
    """
    Get user by ID (manager only).
    """
    try:
        logger.info(f"Getting user with ID: {user_id}")
        
        user = await get_user(user_id)
        if not user:
            logger.warning(f"User not found with ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Remove password
        user.pop("password", None)
        
        logger.info(f"Retrieved user: {user['username']}")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user: {str(e)}"
        )

# Update user by ID (manager only)
@router.put(
    "/{user_id}", 
    response_model=User,
    summary="Update user by ID (Manager only)",
    description="""
    Update an existing user's profile by their ID.
    
    This endpoint is accessible only to users with the **manager** role.
    Managers can update any user's name, email, phone number, role, and password.
    
    Fields that are not provided will remain unchanged.
    Returns the updated user information without their password.
    
    ### curl example:
    ```
    curl -X PUT "https://construction.contactmanagers.xyz/users/USER_ID" \\
      -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
      -H "Content-Type: application/json" \\
      -d '{
        "name": "Updated Name",
        "email": "updated.email@example.com",
        "phone_number": "+254712345678",
        "role": "worker",
        "password": "NewSecurePassword456"
      }'
    ```
    """,
    response_description="Returns the updated user information"
)
async def update_user_by_id(
    user_id: str,
    current_user: Annotated[dict, Depends(check_user_role([UserRole.MANAGER]))],
    request: Request = None,
    user_update: UserUpdate = Body(
        ...,
        example={
            "name": "Updated Name",
            "email": "updated.email@example.com",
            "phone_number": "+254712345678",
            "role": "worker",
            "password": "NewSecurePassword456"
        }
    )
):
    """
    Update user by ID (manager only).
    """
    try:
        logger.info(f"Updating user with ID: {user_id}")
        
        # Check if user exists
        user = await get_user(user_id)
        if not user:
            logger.warning(f"User not found with ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prepare update data
        update_data = user_update.dict(exclude_unset=True, exclude_none=True)
        
        # Hash password if it's being updated
        if "password" in update_data:
            from routers.auth import get_password_hash
            update_data["password"] = get_password_hash(update_data["password"])
            logger.debug("Password hashed for update")
        
        # Update the user
        updated_user = await update_user(user_id, update_data)
        if not updated_user:
            logger.error(f"Failed to update user: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )
        
        # Remove password from response
        updated_user.pop("password", None)
        
        logger.info(f"User updated successfully: {updated_user['username']}")
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )

# Delete user by ID (manager only)
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user by ID (Manager only)",
    description="""
    Delete a user by their ID.
    
    This endpoint is accessible only to users with the **manager** role.
    Permanently removes the user from the system.
    
    If the user with the specified ID does not exist, a 404 error is returned.
    No content is returned upon successful deletion.
    
    ### curl example:
    ```
    curl -X DELETE "https://construction.contactmanagers.xyz/users/USER_ID" \\
      -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    ```
    """,
    response_description="No content is returned on successful deletion"
)
async def delete_user_by_id(
    user_id: str,
    current_user: Annotated[dict, Depends(check_user_role([UserRole.MANAGER]))],
    request: Request = None
):
    """
    Delete user by ID (manager only).
    """
    try:
        logger.info(f"Deleting user with ID: {user_id}")
        
        # Check if user exists
        user = await get_user(user_id)
        if not user:
            logger.warning(f"User not found with ID: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if trying to delete the current user
        if user_id == current_user["id"]:
            logger.warning("User attempted to delete their own account")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        # Delete the user
        success = await delete_user(user_id)
        if not success:
            logger.error(f"Failed to delete user: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user"
            )
        
        logger.info(f"User deleted successfully: {user_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )

# Get all clients (accessible to all authenticated users)
@router.get(
    "/clients", 
    response_model=List[User],
    summary="Get all clients",
    description="""
    Retrieve a list of all clients in the system.
    
    This endpoint is accessible to any authenticated user.
    This is particularly useful when creating projects and you need to assign a client.
    
    ### curl example:
    ```
    curl -X GET "https://construction.contactmanagers.xyz/users/clients" \\
      -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    ```
    """,
    response_description="Returns a list of all client users"
)
async def read_clients(
    current_user: Annotated[dict, Depends(get_current_user)],
    request: Request = None
):
    """
    Get all client users.
    """
    try:
        username = current_user.get('username', 'unknown')
        logger.info(f"Getting all clients by user: {username}")
        clients = await get_users_by_role(UserRole.CLIENT.value)
        
        logger.info(f"Retrieved {len(clients)} clients")
        return clients
    except Exception as e:
        logger.error(f"Error retrieving clients: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving clients: {str(e)}"
        )

# Get all managers (accessible to all authenticated users)
@router.get(
    "/managers", 
    response_model=List[User],
    summary="Get all managers",
    description="""
    Retrieve a list of all managers in the system.
    
    This endpoint is accessible to any authenticated user.
    
    ### curl example:
    ```
    curl -X GET "https://construction.contactmanagers.xyz/users/managers" \\
      -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    ```
    """,
    response_description="Returns a list of all manager users"
)
async def read_managers(
    current_user: Annotated[dict, Depends(get_current_user)],
    request: Request = None
):
    """
    Get all manager users.
    """
    try:
        username = current_user.get('username', 'unknown')
        logger.info(f"Getting all managers by user: {username}")
        managers = await get_users_by_role(UserRole.MANAGER.value)
        
        logger.info(f"Retrieved {len(managers)} managers")
        return managers
    except Exception as e:
        logger.error(f"Error retrieving managers: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving managers: {str(e)}"
        )

# Get all workers (accessible to all authenticated users)
@router.get(
    "/workers", 
    response_model=List[User],
    summary="Get all workers",
    description="""
    Retrieve a list of all workers in the system.
    
    This endpoint is accessible to any authenticated user.
    
    ### curl example:
    ```
    curl -X GET "https://construction.contactmanagers.xyz/users/workers" \\
      -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    ```
    """,
    response_description="Returns a list of all worker users"
)
async def read_workers(
    current_user: Annotated[dict, Depends(get_current_user)],
    request: Request = None
):
    """
    Get all worker users.
    """
    try:
        username = current_user.get('username', 'unknown')
        logger.info(f"Getting all workers by user: {username}")
        workers = await get_users_by_role(UserRole.WORKER.value)
        
        logger.info(f"Retrieved {len(workers)} workers")
        return workers
    except Exception as e:
        logger.error(f"Error retrieving workers: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving workers: {str(e)}"
        ) 