from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, UploadFile, File, Form
from typing import Annotated, List, Optional
from datetime import datetime
import traceback
import os
import shutil
import uuid

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
    
    Optionally, an image of the item can be uploaded for better visualization.
    """,
    response_description="Returns the newly created inventory item with an ID and creation timestamp"
)
async def add_item_to_inventory(
    name: str = Form(..., description="Name of the inventory item", example="Portland Cement"),
    quantity: float = Form(..., description="Quantity of the item", example=100),
    unit: str = Form(..., description="Unit of measurement", example="bags"),
    project_id: str = Form(..., description="ID of the project", example="60d21b4667d0d8992e610c85"),
    description: Optional[str] = Form(None, description="Description of the item", example="50kg bags of Portland cement"),
    cost_per_unit: Optional[float] = Form(None, description="Cost per unit", example=750),
    item_image: Optional[UploadFile] = File(None, description="Image of the inventory item"),
    current_user: Annotated[dict, Depends(check_user_role([UserRole.MANAGER]))]=None,
    request: Request=None
):
    """
    Add a new item to the inventory for a specific project.
    
    Requires manager role.
    """
    try:
        logger.info(f"Adding inventory item: {name} for project: {project_id}")
        
        # Verify project exists
        project = await get_project(project_id)
        if not project:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Process image if provided
        image_url = None
        if item_image:
            try:
                # Ensure directory exists
                os.makedirs("uploads/inventory", exist_ok=True)
                
                # Generate unique filename
                file_extension = os.path.splitext(item_image.filename)[1]
                image_filename = f"{uuid.uuid4()}{file_extension}"
                image_path = f"uploads/inventory/{image_filename}"
                
                logger.debug(f"Saving inventory item image to: {image_path}")
                
                # Save file
                with open(image_path, "wb") as buffer:
                    shutil.copyfileobj(item_image.file, buffer)
                
                image_url = f"/inventory-images/{image_filename}"
                logger.debug(f"Image saved successfully: {image_filename}")
            except Exception as e:
                logger.error(f"Error saving image file: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error saving image file: {str(e)}"
                )
            finally:
                item_image.file.close()
        
        # Create inventory item data
        item_data = {
            "name": name,
            "quantity": quantity,
            "unit": unit,
            "project_id": project_id,
            "description": description,
            "cost_per_unit": cost_per_unit,
            "image_url": image_url
        }
        
        logger.debug(f"Inventory item data: {item_data}")
        
        # Add item to inventory
        item_id = await add_inventory_item(item_data)
        logger.debug(f"Inventory item created with ID: {item_id}")
        
        # Return the created item
        result = {
            **item_data,
            "id": item_id,
            "created_at": datetime.utcnow()
        }
        logger.info(f"Inventory item added successfully: {name}, ID: {item_id}")
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
    in the inventory for the specified project, including their images if available.
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

# Get inventory item image (manager only)
@router.get(
    "/image/{image_filename}",
    summary="Get inventory item image (Manager only)",
    description="""
    Get an inventory item image by its filename.
    
    This endpoint is accessible only to users with the **manager** role.
    
    The response is the actual image file that can be displayed in the UI.
    """,
    response_description="Returns the inventory item image file"
)
async def get_inventory_image(
    image_filename: str,
    current_user: Annotated[dict, Depends(check_user_role([UserRole.MANAGER]))]=None,
    request: Request=None
):
    """
    Get an inventory item image by its filename.
    
    Requires manager role.
    """
    try:
        logger.info(f"Getting inventory item image: {image_filename}")
        
        image_path = f"uploads/inventory/{image_filename}"
        
        if not os.path.exists(image_path):
            logger.warning(f"Image file not found: {image_filename}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image file not found"
            )
        
        logger.debug(f"Returning image file: {image_path}")
        return FileResponse(image_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting inventory image: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting inventory image: {str(e)}"
        ) 