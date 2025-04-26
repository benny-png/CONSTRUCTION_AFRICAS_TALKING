import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request, Body
from fastapi.responses import FileResponse
from typing import Annotated, List
import uuid
from datetime import datetime
import traceback

from models.expense import ExpenseCreate, Expense, ExpenseVerify, VerificationStatus
from models.user import UserRole
from database.operations import (
    add_expense, 
    get_expenses_by_project, 
    get_expense,
    verify_expense,
    get_project
)
from routers.auth import get_current_user, check_user_role
from logging_config import logger

router = APIRouter()

# Add expense with receipt (manager only)
@router.post(
    "", 
    response_model=Expense,
    summary="Add expense with receipt (Manager only)",
    description="""
    Add a new expense with an uploaded receipt for a specific project.
    
    This endpoint is accessible only to users with the **manager** role.
    
    The expense includes details such as amount, description, date, and
    the receipt file as a multipart/form-data upload.
    
    The receipt file will be stored and made available for verification
    by the client.
    """,
    response_description="Returns the newly created expense with an ID, receipt URL, and creation timestamp"
)
async def add_project_expense(
    amount: float = Form(..., description="Expense amount (must be greater than 0)", example=1250.75),
    description: str = Form(..., description="Description of the expense", example="Purchase of concrete and cement"),
    date: str = Form(..., description="Expense date in YYYY-MM-DD format", example="2023-07-15"),
    project_id: str = Form(..., description="ID of the project", example="60d21b4667d0d8992e610c85"),
    receipt_file: UploadFile = File(..., description="Receipt file (image or PDF)"),
    current_user: dict = Depends(check_user_role([UserRole.MANAGER])),
    request: Request = None
):
    """
    Add a new expense with an uploaded receipt for a specific project.
    
    Requires manager role.
    """
    try:
        logger.info(f"Adding expense for project: {project_id}, amount: {amount}")
        
        # Verify project exists
        project = await get_project(project_id)
        if not project:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Generate a unique filename for the receipt
        file_extension = os.path.splitext(receipt_file.filename)[1]
        receipt_filename = f"{uuid.uuid4()}{file_extension}"
        receipt_path = f"uploads/receipts/{receipt_filename}"
        
        logger.debug(f"Saving receipt to: {receipt_path}")
        
        # Save the receipt file
        try:
            # Ensure the directory exists
            os.makedirs("uploads/receipts", exist_ok=True)
            
            # Save the file
            with open(receipt_path, "wb") as buffer:
                shutil.copyfileobj(receipt_file.file, buffer)
            
            logger.debug(f"Receipt saved successfully: {receipt_filename}")
        except Exception as e:
            logger.error(f"Error saving receipt file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving receipt file: {str(e)}"
            )
        finally:
            receipt_file.file.close()
        
        # Create expense data
        expense_data = {
            "amount": amount,
            "description": description,
            "date": date,
            "project_id": project_id,
            "receipt_url": f"/receipts/{receipt_filename}"
        }
        
        logger.debug(f"Expense data: {expense_data}")
        
        # Add expense to database
        expense_id = await add_expense(expense_data)
        logger.debug(f"Expense created with ID: {expense_id}")
        
        # Return the created expense
        result = {
            **expense_data,
            "id": expense_id,
            "verified": VerificationStatus.PENDING,
            "created_at": datetime.utcnow()
        }
        
        logger.info(f"Expense added successfully, ID: {expense_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding expense: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding expense: {str(e)}"
        )

# Get expenses for a project (manager & client)
@router.get(
    "/{project_id}", 
    response_model=List[Expense],
    summary="Get expenses for a project (Manager & Client)",
    description="""
    Get all expenses for a specific project.
    
    This endpoint is accessible to:
    - **managers**: can access expenses for any project
    - **clients**: can only access expenses for their own projects
    
    The response includes a list of all expenses with their receipt URLs
    and verification status.
    
    Workers cannot access this endpoint.
    """,
    response_description="Returns a list of expenses for the specified project"
)
async def get_project_expenses(
    project_id: str,
    current_user: dict = Depends(check_user_role([UserRole.MANAGER, UserRole.CLIENT])),
    request: Request = None
):
    """
    Get all expenses for a specific project.
    
    Requires manager or client role.
    """
    try:
        logger.info(f"Getting expenses for project: {project_id}")
        
        # Verify project exists
        project = await get_project(project_id)
        if not project:
            logger.warning(f"Project not found: {project_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # If client, check if they are the client for this project
        if current_user["role"] == UserRole.CLIENT.value and project["client_id"] != current_user["id"]:
            logger.warning(f"Access denied to project {project_id} for client {current_user['id']}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project"
            )
        
        # Get expenses
        expenses = await get_expenses_by_project(project_id)
        logger.debug(f"Found {len(expenses)} expenses for project {project_id}")
        
        return expenses
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting expenses: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting expenses: {str(e)}"
        )

# Get receipt file (manager & client)
@router.get(
    "/receipt/{receipt_filename}",
    summary="Get receipt file (Manager & Client)",
    description="""
    Get a receipt file by its filename.
    
    This endpoint is accessible to:
    - **managers**: can access receipts for any project
    - **clients**: can only access receipts for their own projects
    
    The response is the actual file (image or PDF) that can be displayed
    or downloaded.
    
    Workers cannot access this endpoint.
    """,
    response_description="Returns the receipt file"
)
async def get_receipt_file(
    receipt_filename: str,
    current_user: dict = Depends(check_user_role([UserRole.MANAGER, UserRole.CLIENT])),
    request: Request = None
):
    """
    Get a receipt file by its filename.
    
    Requires manager or client role.
    """
    try:
        logger.info(f"Getting receipt file: {receipt_filename}")
        
        receipt_path = f"uploads/receipts/{receipt_filename}"
        
        if not os.path.exists(receipt_path):
            logger.warning(f"Receipt file not found: {receipt_filename}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receipt file not found"
            )
        
        logger.debug(f"Returning receipt file: {receipt_path}")
        return FileResponse(receipt_path)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting receipt file: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting receipt file: {str(e)}"
        )

# Verify expense (client only)
@router.patch(
    "/{expense_id}/verify", 
    status_code=status.HTTP_200_OK,
    summary="Verify expense (Client only)",
    description="""
    Verify an expense by approving or flagging it.
    
    This endpoint is accessible only to users with the **client** role.
    
    The client can review the expense and receipt, then either approve it
    or flag it for further investigation.
    
    Status can be:
    - **approved**: Expense is verified and approved
    - **flagged**: Expense is flagged for further investigation
    """,
    response_description="Returns a confirmation message"
)
async def verify_expense_authenticity(
    expense_id: str,
    verification: ExpenseVerify = Body(
        ...,
        example={
            "status": "approved"
        },
        description="Verification status (approved or flagged)"
    ),
    current_user: dict = Depends(check_user_role([UserRole.CLIENT])),
    request: Request = None
):
    """
    Verify an expense by approving or flagging it.
    
    Requires client role.
    """
    try:
        logger.info(f"Verifying expense: {expense_id}, status: {verification.status}")
        
        # Get the expense
        expense = await get_expense(expense_id)
        if not expense:
            logger.warning(f"Expense not found: {expense_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found"
            )
        
        # Get the project
        project = await get_project(expense["project_id"])
        if not project:
            logger.warning(f"Project not found: {expense['project_id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check if client is the client for this project
        if project["client_id"] != current_user["id"]:
            logger.warning(f"Access denied to expense {expense_id} for client {current_user['id']}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this expense"
            )
        
        # Update verification status
        logger.debug(f"Updating verification status: {verification.status}")
        success = await verify_expense(expense_id, verification.status)
        if not success:
            logger.error(f"Failed to update verification status for expense: {expense_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update verification status"
            )
        
        logger.info(f"Expense verification updated successfully: {expense_id}, status: {verification.status}")
        return {"message": f"Expense verification status updated to {verification.status}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying expense: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying expense: {str(e)}"
        ) 