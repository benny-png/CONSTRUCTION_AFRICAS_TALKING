from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from typing import Annotated, List
from datetime import datetime
import traceback

from models.inventory import InventoryItemCreate, InventoryItem
from models.user import UserRole
from database.operations import add_inventory_item, get_inventory_by_project, get_project
from routers.auth import get_current_user, check_user_role
from logging_config import logger

router = APIRouter()

# Add inventory item (manager only)
@router.post(
    "", 
    response_model=InventoryItem,
    summary="Add inventory item (Manager only)",
    description="""
    Add a new item to the inventory for a specific project.
    
    This endpoint is accessible only to users with the **manager** role.
    
    The inventory item includes details such as name, quantity, unit, and
    the project it belongs to.
    """,
    response_description="Returns the newly created inventory item with an ID and creation timestamp"
)
async def add_item_to_inventory(
    item_data: InventoryItemCreate = Body(
        ...,
        example={
            "name": "Cement",
            "quantity": 100,
            "unit": "bags",
            "project_id": "60d21b4667d0d8992e610c85"
        }
    ),
    current_user: Annotated[dict, Depends(check_user_role([UserRole.MANAGER]))]=None,
    request: Request=None
):
    """
    Add a new item to the inventory for a specific project.
    
    Requires manager role.
    """
    try:
        logger.info(f"Adding inventory item: {item_data.name} for project: {item_data.project_id}")
        logger.debug(f"Inventory item data: {item_data.dict()}")
        
        # Verify project exists
        project = await get_project(item_data.project_id)
        if not project:
            logger.warning(f"Project not found: {item_data.project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Add item to inventory
        item_id = await add_inventory_item(item_data.dict())
        logger.debug(f"Inventory item created with ID: {item_id}")
        
        # Return the created item
        result = {
            **item_data.dict(),
            "id": item_id,
            "created_at": datetime.utcnow()
        }
        logger.info(f"Inventory item added successfully: {item_data.name}, ID: {item_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding inventory item: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding inventory item: {str(e)}"
        )

# Get inventory items for a project (manager only)
@router.get(
    "/{project_id}", 
    response_model=List[InventoryItem],
    summary="Get inventory items for a project (Manager only)",
    description="""
    Get all inventory items for a specific project.
    
    This endpoint is accessible only to users with the **manager** role.
    
    The response includes a list of all materials and assets currently
    in the inventory for the specified project.
    """,
    response_description="Returns a list of inventory items for the specified project"
)
async def get_inventory_items(
    project_id: str,
    current_user: Annotated[dict, Depends(check_user_role([UserRole.MANAGER]))]=None,
    request: Request=None
):
    """
    Get all inventory items for a specific project.
    
    Requires manager role.
    """
    try:
        logger.info(f"Getting inventory items for project: {project_id}")
        
        # Verify project exists
        project = await get_project(project_id)
        if not project:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Get inventory items
        items = await get_inventory_by_project(project_id)
        logger.debug(f"Found {len(items)} inventory items for project {project_id}")
        
        return items
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting inventory items: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting inventory items: {str(e)}"
        ) 