from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, UploadFile, File, Form
from typing import Annotated, List, Optional, Dict, Any
import traceback
import os
import base64
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

from models.user import UserRole
from models.project import ProjectStatus
from models.expense import VerificationStatus
from routers.auth import get_current_user, check_user_role
from logging_config import logger
from database.operations import (
    get_project, 
    get_project_summary, 
    get_expenses_by_project,
    get_expense,
    get_progress_reports,
    get_material_usage_by_project
)

# Force reload environment variables
load_dotenv(override=True)

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "your-openrouter-api-key-here")
SITE_URL = os.getenv("SITE_URL", "https://construction.contactmanagers.xyz")
SITE_NAME = os.getenv("SITE_NAME", "Construction Management System")

# Log API key status (masked for security)
if OPENROUTER_API_KEY and OPENROUTER_API_KEY != "your-openrouter-api-key-here":
    masked_key = OPENROUTER_API_KEY[:8] + "..." + OPENROUTER_API_KEY[-4:] if len(OPENROUTER_API_KEY) > 12 else "***masked***"
    logger.info(f"OpenRouter API key loaded: {masked_key}")
else:
    logger.error("OpenRouter API key not found or invalid")

# Initialize OpenAI client with OpenRouter
ai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

router = APIRouter()

# Helper function to process image files
async def process_image_file(image: UploadFile) -> str:
    """Process an uploaded image file and return base64 encoding."""
    # Create directory for temp files if it doesn't exist
    os.makedirs("uploads/temp", exist_ok=True)
    
    # Save the uploaded image temporarily
    image_path = f"uploads/temp/{datetime.utcnow().timestamp()}-{image.filename}"
    with open(image_path, "wb") as buffer:
        image_content = await image.read()
        buffer.write(image_content)
    
    # Convert image to base64
    with open(image_path, "rb") as img_file:
        base64_image = base64.b64encode(img_file.read()).decode('utf-8')
    
    # Clean up the temp file
    os.remove(image_path)
    
    return base64_image

# Helper function to get project context
async def get_project_context(project_id: str) -> Dict[str, Any]:
    """Retrieve comprehensive project context for AI analysis."""
    project_context = {}
    
    # Get basic project details
    project = await get_project(project_id)
    if not project:
        return {"error": "Project not found"}
    
    project_context["project"] = project
    
    # Get project summary with analytics
    summary = await get_project_summary(project_id)
    project_context["summary"] = summary
    
    # Get progress reports
    progress_reports = await get_progress_reports(project_id)
    project_context["progress_reports"] = progress_reports
    
    # Get expenses
    expenses = await get_expenses_by_project(project_id)
    project_context["expenses"] = expenses
    
    # Get material usage
    material_usage = await get_material_usage_by_project(project_id)
    project_context["material_usage"] = material_usage
    
    return project_context

# AI assistant for managers - Project planning and advice with specific project context
@router.post(
    "/manager/project-advice", 
    summary="Get AI advice for project planning (Manager only)",
    description="""
    Get AI-powered advice and suggestions for project planning and management.
    
    This endpoint is accessible only to users with the **manager** role.
    
    Managers can describe their project needs, challenges or questions to get
    AI-generated recommendations, best practices, and advice.
    
    You can optionally provide a project_id to get context-aware advice based on the
    current state of a specific project.
    
    ### curl Example
    ```bash
    curl -X 'POST' \\
      'https://construction.contactmanagers.xyz/ai/manager/project-advice' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \\
      -H 'Content-Type: application/json' \\
      -d '{
        "query": "I need to plan a 15-floor apartment building project. What are the key milestones I should include?",
        "project_type": "residential",
        "budget_constraint": "high",
        "project_id": "61a23c4567d0d8992e610d96"
      }'
    ```
    """,
    response_description="Returns AI-generated advice and recommendations"
)
async def get_manager_project_advice(
    token_data: dict = Depends(check_user_role([UserRole.MANAGER])),
    query: str = Body(..., description="The manager's question or request for advice"),
    project_type: Optional[str] = Body(None, description="Type of project (residential, commercial, infrastructure)"),
    budget_constraint: Optional[str] = Body(None, description="Budget level (low, medium, high)"),
    project_id: Optional[str] = Body(None, description="Optional project ID to get context-specific advice"),
    request: Request = None
):
    """
    Get AI advice for project planning and management.
    
    Requires manager role.
    """
    try:
        # Access token data for user identification
        user_id = token_data.get("user_id", "unknown")
        username = token_data.get("sub", "unknown")
        logger.info(f"Manager {username} requesting AI project advice")
        
        # Prepare prompt with context
        prompt = f"You are an expert construction project manager advisor. Provide detailed, professional advice for this query from a construction manager.\n\n"
        prompt += f"Query: {query}\n"
        
        if project_type:
            prompt += f"Project Type: {project_type}\n"
        
        if budget_constraint:
            prompt += f"Budget Level: {budget_constraint}\n"
        
        # Get project-specific context if project_id is provided
        project_context = None
        if project_id:
            project_context = await get_project_context(project_id)
            if "error" not in project_context:
                prompt += "\n--- PROJECT CONTEXT ---\n"
                
                # Add basic project info
                project = project_context.get("project", {})
                prompt += f"Project Name: {project.get('name')}\n"
                prompt += f"Project Description: {project.get('description')}\n"
                prompt += f"Project Location: {project.get('location')}\n"
                prompt += f"Project Budget: ${project.get('budget', 0):,.2f}\n"
                prompt += f"Project Timeline: {project.get('start_date')} to {project.get('end_date')}\n"
                
                # Add summary analytics
                summary = project_context.get("summary", {})
                prompt += f"Current Progress: {summary.get('progress_percentage', 0)}%\n"
                prompt += f"Total Expenses to Date: ${summary.get('total_expenses', 0):,.2f}\n"
                
                # List key progress reports
                progress_reports = project_context.get("progress_reports", [])
                if progress_reports:
                    prompt += "\nRecent Progress Reports:\n"
                    for report in progress_reports[-3:]:  # Last 3 reports
                        prompt += f"- {report.get('report_date')}: {report.get('percentage_complete')}% - {report.get('description')[:100]}...\n"
                
                # Include material usage summary
                material_usage = summary.get("material_usage", {})
                if material_usage:
                    prompt += "\nKey Materials Used:\n"
                    for material, quantity in material_usage.items():
                        prompt += f"- {material}: {quantity} units\n"
            else:
                logger.warning(f"Project context error: {project_context.get('error')}")
        
        logger.debug(f"Sending AI request with prompt: {prompt[:100]}...")
        
        # Check if API key is available
        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your-openrouter-api-key-here":
            logger.error("OpenRouter API key is not set or invalid")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI service not properly configured. Please contact the administrator."
            )
        
        # Call AI model through OpenRouter
        completion = ai_client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME
            },
            model="google/gemini-2.0-flash-exp:free",
            messages=[{"role": "user", "content": prompt}]
        )
        
        ai_response = completion.choices[0].message.content
        logger.debug(f"Received AI response: {ai_response[:100]}...")
        
        # Return formatted response
        return {
            "query": query,
            "advice": ai_response,
            "timestamp": datetime.utcnow().isoformat(),
            "project_id": project_id if project_id else None,
            "context_used": bool(project_context and "error" not in project_context)
        }
        
    except Exception as e:
        logger.error(f"Error getting AI project advice: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting AI advice: {str(e)}"
        )

# AI assistant for workers - Construction techniques and troubleshooting
@router.post(
    "/worker/construction-help", 
    summary="Get AI construction help (Worker only)",
    description="""
    Get AI-powered assistance for construction techniques and troubleshooting.
    
    This endpoint is accessible only to users with the **worker** role.
    
    Workers can describe construction problems, ask about techniques, or request
    help with specific tasks to get AI-generated guidance.
    
    ### curl Example
    ```bash
    curl -X 'POST' \\
      'https://construction.contactmanagers.xyz/ai/worker/construction-help' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \\
      -H 'Content-Type: multipart/form-data' \\
      -F 'query=How do I properly install electrical conduit in a concrete wall?' \\
      -F 'image=@photo_of_wall.jpg' \\
      -F 'project_id=61a23c4567d0d8992e610d96'
    ```
    """,
    response_description="Returns AI-generated construction guidance"
)
async def get_worker_construction_help(
    token_data: dict = Depends(check_user_role([UserRole.WORKER])),
    query: str = Form(..., description="The worker's question or request for help"),
    image: Optional[UploadFile] = File(None, description="Optional image of the construction issue"),
    project_id: Optional[str] = Form(None, description="Optional project ID for context"),
    request: Request = None
):
    """
    Get AI help for construction techniques and troubleshooting.
    
    Requires worker role.
    """
    try:
        # Access token data for user identification
        user_id = token_data.get("user_id", "unknown")
        username = token_data.get("sub", "unknown")
        logger.info(f"Worker {username} requesting AI construction help")
        
        # Process image if provided
        messages = []
        content = []
        
        # Add text query with project context if available
        query_text = f"You are an expert construction advisor. I'm a construction worker with this question: {query}"
        
        # Add project context if project_id is provided
        if project_id:
            project_context = await get_project_context(project_id)
            if "error" not in project_context:
                project = project_context.get("project", {})
                query_text += f"\n\nThis question relates to project '{project.get('name')}', which is a {project.get('description')} at {project.get('location')}."
        
        content.append({
            "type": "text",
            "text": query_text
        })
        
        # Process image if provided
        if image:
            base64_image = await process_image_file(image)
                
            # Add image to content
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            })
            
            logger.debug("Image processed and added to AI request")
        
        # Add content to messages
        messages.append({
            "role": "user",
            "content": content
        })
        
        logger.debug(f"Sending AI request with query: {query}")
        
        # Call AI model through OpenRouter
        completion = ai_client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME
            },
            model="google/gemini-2.0-flash-exp:free",
            messages=messages
        )
        
        ai_response = completion.choices[0].message.content
        logger.debug(f"Received AI response: {ai_response[:100]}...")
        
        # Return formatted response
        return {
            "query": query,
            "guidance": ai_response,
            "timestamp": datetime.utcnow().isoformat(),
            "project_id": project_id if project_id else None,
            "image_provided": image is not None
        }
        
    except Exception as e:
        logger.error(f"Error getting AI construction help: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting AI help: {str(e)}"
        )

# AI for clients - Project progress interpretation
@router.post(
    "/client/progress-analysis", 
    summary="Get AI analysis of project progress (Client only)",
    description="""
    Get AI-powered analysis and explanation of your project's progress.
    
    This endpoint is accessible only to users with the **client** role.
    
    Clients can ask questions about their project's progress, timelines, or budget
    to get AI-generated explanations in non-technical terms.
    
    ### curl Example
    ```bash
    curl -X 'POST' \\
      'https://construction.contactmanagers.xyz/ai/client/progress-analysis' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \\
      -H 'Content-Type: application/json' \\
      -d '{
        "project_id": "61a23c4567d0d8992e610d96",
        "query": "Is my project on schedule? What are the next major milestones?"
      }'
    ```
    """,
    response_description="Returns AI-generated analysis of project progress"
)
async def get_client_progress_analysis(
    token_data: dict = Depends(check_user_role([UserRole.CLIENT])),
    project_id: str = Body(..., description="ID of the client's project"),
    query: str = Body(..., description="The client's question about project progress"),
    request: Request = None
):
    """
    Get AI analysis of project progress.
    
    Requires client role.
    """
    try:
        # Access token data for user identification
        user_id = token_data.get("user_id", "unknown")
        username = token_data.get("sub", "unknown")
        logger.info(f"Client {username} requesting AI progress analysis for project {project_id}")
        
        # Get project context
        project_context = await get_project_context(project_id)
        
        # Prepare prompt with context
        prompt = f"You are an expert construction project interpreter for clients. Explain project progress in clear, non-technical terms.\n\n"
        prompt += f"Client query: {query}\n"
        
        if "error" not in project_context:
            prompt += "\n--- PROJECT CONTEXT ---\n"
                
            # Add basic project info
            project = project_context.get("project", {})
            prompt += f"Project Name: {project.get('name')}\n"
            prompt += f"Project Description: {project.get('description')}\n"
            prompt += f"Project Location: {project.get('location')}\n"
            prompt += f"Project Budget: ${project.get('budget', 0):,.2f}\n"
            prompt += f"Project Timeline: {project.get('start_date')} to {project.get('end_date')}\n"
            
            # Add summary analytics
            summary = project_context.get("summary", {})
            prompt += f"Current Progress: {summary.get('progress_percentage', 0)}%\n"
            prompt += f"Total Expenses to Date: ${summary.get('total_expenses', 0):,.2f}\n"
            
            # List key progress reports
            progress_reports = project_context.get("progress_reports", [])
            if progress_reports:
                prompt += "\nRecent Progress Reports:\n"
                for report in progress_reports[-3:]:  # Last 3 reports
                    prompt += f"- {report.get('report_date')}: {report.get('percentage_complete')}% - {report.get('description')[:100]}...\n"
        else:
            prompt += f"Regarding project ID: {project_id}\n"
            prompt += "Note: This project data couldn't be found. Please provide a general response about what information would normally be analyzed to answer this question."
        
        logger.debug(f"Sending AI request with prompt: {prompt[:100]}...")
        
        # Call AI model through OpenRouter
        completion = ai_client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME
            },
            model="google/gemini-2.0-flash-exp:free",
            messages=[{"role": "user", "content": prompt}]
        )
        
        ai_response = completion.choices[0].message.content
        logger.debug(f"Received AI response: {ai_response[:100]}...")
        
        # Return formatted response
        return {
            "project_id": project_id,
            "query": query,
            "analysis": ai_response,
            "timestamp": datetime.utcnow().isoformat(),
            "context_used": "error" not in project_context
        }
        
    except Exception as e:
        logger.error(f"Error getting AI progress analysis: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting AI analysis: {str(e)}"
        )

# New endpoint for transaction authenticity verification
@router.post(
    "/verify-transaction", 
    summary="Verify transaction authenticity using AI (Manager/Client)",
    description="""
    Get AI-powered verification and analysis of expense receipts.
    
    This endpoint is accessible to users with the **manager** or **client** role.
    
    Verify the authenticity of expenses by providing an expense ID and optionally 
    uploading receipts for the AI to analyze and compare with the stored receipt.
    
    ### curl Example
    ```bash
    curl -X 'POST' \\
      'https://construction.contactmanagers.xyz/ai/verify-transaction' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \\
      -H 'Content-Type: multipart/form-data' \\
      -F 'expense_id=61a23c4567d0d8992e610d96' \\
      -F 'query=Verify if this expense receipt is authentic and matches the claimed amount' \\
      -F 'receipt_image=@receipt.jpg'
    ```
    """,
    response_description="Returns AI-generated verification analysis"
)
async def verify_transaction_authenticity(
    token_data: dict = Depends(check_user_role([UserRole.MANAGER, UserRole.CLIENT])),
    expense_id: str = Form(..., description="ID of the expense to verify"),
    query: str = Form(..., description="Specific verification questions or concerns"),
    receipt_image: Optional[UploadFile] = File(None, description="Optional receipt image to compare with stored receipt"),
    request: Request = None
):
    """
    Verify expense authenticity using AI.
    
    Requires manager or client role.
    """
    try:
        # Access token data for user identification
        user_id = token_data.get("user_id", "unknown")
        username = token_data.get("sub", "unknown")
        user_role = token_data.get("role", "unknown")
        logger.info(f"{user_role.capitalize()} {username} requesting transaction verification for expense {expense_id}")
        
        # Get expense details
        expense = await get_expense(expense_id)
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Expense with ID {expense_id} not found"
            )
        
        # Process uploaded receipt image if provided
        messages = []
        content = []
        
        # Build the query text
        query_text = f"""You are an expert financial auditor specializing in construction expenses. Analyze the following expense and verify its authenticity:

Expense ID: {expense_id}
Amount: ${expense.get('amount', 0):,.2f}
Description: {expense.get('description', '')}
Date: {expense.get('date', '')}
Current verification status: {expense.get('verified', 'pending')}

User query: {query}
"""
        
        # Add project context if available
        project_id = expense.get('project_id')
        if project_id:
            project = await get_project(project_id)
            if project:
                query_text += f"\nRelated to project: {project.get('name', 'Unknown')}"
        
        content.append({
            "type": "text",
            "text": query_text
        })
        
        # Get stored receipt URL
        receipt_url = expense.get('receipt_url')
        if receipt_url:
            # Check if the file exists (handle both relative and absolute paths)
            receipt_path = receipt_url
            if not os.path.exists(receipt_path) and not receipt_path.startswith("/"):
                receipt_path = os.path.join("uploads/receipts", os.path.basename(receipt_url))
            
            if os.path.exists(receipt_path):
                # Convert stored receipt to base64
                with open(receipt_path, "rb") as img_file:
                    base64_stored = base64.b64encode(img_file.read()).decode('utf-8')
                    
                # Add stored receipt to content
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_stored}"
                    }
                })
                content.append({
                    "type": "text",
                    "text": "Above is the stored receipt from the database."
                })
                
                logger.debug("Stored receipt image added to AI request")
        
        # Process uploaded receipt image if provided
        if receipt_image:
            base64_uploaded = await process_image_file(receipt_image)
                
            # Add image to content
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_uploaded}"
                }
            })
            content.append({
                "type": "text",
                "text": "Above is the receipt image uploaded by the user for verification."
            })
            
            logger.debug("Uploaded receipt image added to AI request")
        
        # Add content to messages
        messages.append({
            "role": "user",
            "content": content
        })
        
        logger.debug(f"Sending AI request for transaction verification")
        
        # Call AI model through OpenRouter
        completion = ai_client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME
            },
            model="google/gemini-2.0-flash-exp:free",
            messages=messages
        )
        
        ai_response = completion.choices[0].message.content
        logger.debug(f"Received AI response: {ai_response[:100]}...")
        
        # Return formatted response
        return {
            "expense_id": expense_id,
            "amount": expense.get("amount"),
            "description": expense.get("description"),
            "query": query,
            "verification_analysis": ai_response,
            "timestamp": datetime.utcnow().isoformat(),
            "stored_receipt_available": receipt_url is not None,
            "user_receipt_provided": receipt_image is not None
        }
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logger.error(f"Error verifying transaction authenticity: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying transaction: {str(e)}"
        ) 