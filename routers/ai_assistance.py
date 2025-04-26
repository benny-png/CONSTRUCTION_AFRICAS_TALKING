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
    
    ### Input Parameters
    
    | Parameter | Type | Required | Description | Example |
    |-----------|------|----------|-------------|---------|
    | `query` | string | **Required** | The manager's question or request for advice | "I need to plan a 15-floor apartment building project. What are the key milestones I should include?" |
    | `project_type` | string | Optional | Type of project: residential, commercial, or infrastructure | "residential" |
    | `budget_constraint` | string | Optional | Budget level: low, medium, or high | "high" |
    | `project_id` | string | Optional | Project ID to get context-specific advice based on the current state of a specific project | "61a23c4567d0d8992e610d96" |
    
    ### Response Format
    
    ```json
    {
      "query": "I need to plan a 15-floor apartment building project. What are the key milestones I should include?",
      "advice": "Here is your AI-generated advice...",
      "timestamp": "2023-07-15T08:30:45.123Z",
      "project_id": "61a23c4567d0d8992e610d96",
      "context_used": true
    }
    ```
    
    ### Authorization
    
    Requires a valid JWT token with manager role.
    
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
    response_description="Returns AI-generated advice and recommendations with details about the query context"
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
    
    ### Input Parameters
    
    | Parameter | Type | Required | Description | Example |
    |-----------|------|----------|-------------|---------|
    | `query` | string | **Required** | The worker's question or request for help | "How do I properly install electrical conduit in a concrete wall?" |
    | `image` | file | Optional | Image of the construction issue or situation (JPG, PNG) | *A photo of the work area or problem* |
    | `project_id` | string | Optional | Project ID to provide context for the AI response | "61a23c4567d0d8992e610d96" |
    
    ### Response Format
    
    ```json
    {
      "query": "How do I properly install electrical conduit in a concrete wall?",
      "guidance": "Here is your AI-generated construction guidance...",
      "timestamp": "2023-07-15T08:30:45.123Z",
      "project_id": "61a23c4567d0d8992e610d96",
      "image_provided": true
    }
    ```
    
    ### Authorization
    
    Requires a valid JWT token with worker role.
    
    ### Note on File Upload
    
    This endpoint accepts `multipart/form-data` because it allows for file upload. Make sure to use the correct content type in your request.
    
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
    response_description="Returns AI-generated construction guidance with context information"
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
    
    ### Input Parameters
    
    | Parameter | Type | Required | Description | Example |
    |-----------|------|----------|-------------|---------|
    | `project_id` | string | **Required** | ID of the client's project | "61a23c4567d0d8992e610d96" |
    | `query` | string | **Required** | The client's question about project progress | "Is my project on schedule? What are the next major milestones?" |
    
    ### Response Format
    
    ```json
    {
      "project_id": "61a23c4567d0d8992e610d96",
      "query": "Is my project on schedule? What are the next major milestones?",
      "analysis": "Here is your AI-generated progress analysis...",
      "timestamp": "2023-07-15T08:30:45.123Z",
      "context_used": true
    }
    ```
    
    ### Authorization
    
    Requires a valid JWT token with client role.
    
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
    response_description="Returns AI-generated analysis of project progress tailored for clients"
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

# New endpoint for financial accuracy verification
@router.post(
    "/verify-transaction", 
    summary="Verify expense financial accuracy using AI (Manager/Client)",
    description="""
    Get AI-powered verification of expense financial accuracy.
    
    This endpoint is accessible to users with the **manager** or **client** role.
    
    Verifies if the recorded expense amount matches what's shown on the receipt, helping
    to maintain financial trust and transparency in the project accounting.
    
    The AI will analyze the receipt image to extract amount information and compare it
    with the recorded expense data in the system.
    
    ### Input Parameters
    
    | Parameter | Type | Required | Description | Example |
    |-----------|------|----------|-------------|---------|
    | `expense_id` | string | **Required** | ID of the expense to verify | "61a23c4567d0d8992e610d96" |
    | `verification_type` | string | Optional | Type of verification to perform (default: "financial_accuracy") | "financial_accuracy" |
    | `notes` | string | Optional | Additional notes about the verification request | "This receipt appears blurry, please check if the amount matches $1,250.75" |
    
    ### Response Format
    
    ```json
    {
      "expense_id": "61a23c4567d0d8992e610d96",
      "recorded_amount": 1250.75,
      "description": "Purchase of concrete and cement",
      "date": "2023-07-15",
      "verification_type": "financial_accuracy",
      "analysis": "Here is your AI-generated financial verification analysis...",
      "verification_result": "MATCH",
      "timestamp": "2023-07-15T08:30:45.123Z"
    }
    ```
    
    The `verification_result` will be one of:
    - `MATCH`: The receipt amount matches the recorded amount
    - `DISCREPANCY`: There is a difference between the receipt amount and recorded amount
    - `NEEDS_REVIEW`: The AI couldn't make a clear determination
    
    ### Authorization
    
    Requires a valid JWT token with manager or client role.
    
    ### curl Example
    ```bash
    curl -X 'POST' \\
      'https://construction.contactmanagers.xyz/ai/verify-transaction' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \\
      -H 'Content-Type: multipart/form-data' \\
      -F 'expense_id=61a23c4567d0d8992e610d96' \\
      -F 'verification_type=financial_accuracy' \\
      -F 'notes=Please check if this receipt matches our records'
    ```
    """,
    response_description="Returns AI-generated financial accuracy analysis with verification results"
)
async def verify_expense_financial_accuracy(
    token_data: dict = Depends(check_user_role([UserRole.MANAGER, UserRole.CLIENT])),
    expense_id: str = Form(..., description="ID of the expense to verify"),
    verification_type: str = Form("financial_accuracy", description="Type of verification to perform"),
    notes: Optional[str] = Form(None, description="Additional notes about the verification request"),
    request: Request = None
):
    """
    Verify expense financial accuracy using AI.
    
    Requires manager or client role.
    """
    try:
        # Access token data for user identification
        user_id = token_data.get("user_id", "unknown")
        username = token_data.get("sub", "unknown")
        user_role = token_data.get("role", "unknown")
        logger.info(f"{user_role.capitalize()} {username} requesting expense financial accuracy verification for expense {expense_id}")
        
        # Get expense details
        expense = await get_expense(expense_id)
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Expense with ID {expense_id} not found"
            )
        
        # Check if API key is available
        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your-openrouter-api-key-here":
            logger.error("OpenRouter API key is not set or invalid")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI service not properly configured. Please contact the administrator."
            )
        
        # Prepare for AI request
        messages = []
        content = []
        
        # Build the instruction text
        instruction_text = f"""You are an expert financial auditor specializing in construction expenses and receipt analysis. 
        
TASK: Analyze the receipt image and verify if the amount on the receipt matches the recorded expense amount in our system.

RECORDED EXPENSE DETAILS:
- Expense ID: {expense_id}
- Recorded Amount: ${expense.get('amount', 0):,.2f}
- Description: {expense.get('description', '')}
- Date: {expense.get('date', '')}

YOUR OBJECTIVE:
1. Carefully examine the receipt image
2. Extract the total amount from the receipt
3. Determine if the total amount on the receipt matches the recorded amount in our system
4. Note any discrepancies in amounts, dates, or other relevant financial details
5. Assess if there are any red flags or suspicious elements in the receipt
6. Provide a final determination if the expense record is accurate and matches the receipt

This verification is crucial for maintaining financial trust and transparency with our clients.
"""
        
        # Add project context if available
        project_id = expense.get('project_id')
        if project_id:
            project = await get_project(project_id)
            if project:
                instruction_text += f"\nPROJECT CONTEXT: This expense is for project '{project.get('name', 'Unknown')}'"
        
        # Add any notes if provided
        if notes:
            instruction_text += f"\n\nADDITIONAL NOTES: {notes}"
        
        content.append({
            "type": "text",
            "text": instruction_text
        })
        
        # Get stored receipt URL - this is the receipt we need to analyze
        receipt_url = expense.get('receipt_url')
        if not receipt_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This expense does not have an associated receipt to verify"
            )
        
        # Process the stored receipt
        receipt_path = receipt_url
        if not os.path.exists(receipt_path) and not receipt_path.startswith("/"):
            receipt_path = os.path.join("uploads/receipts", os.path.basename(receipt_url))
        
        if not os.path.exists(receipt_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Receipt file not found in storage"
            )
            
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
            
        logger.debug("Receipt image added to AI request for financial verification")
        
        # Add content to messages
        messages.append({
            "role": "user",
            "content": content
        })
        
        logger.debug(f"Sending AI request for expense financial accuracy verification")
        
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
        
        # Extract a simple verification result if possible (look for true/false indicators in the response)
        verification_result = "NEEDS_REVIEW"  # Default
        if "match" in ai_response.lower() and "confirm" in ai_response.lower():
            verification_result = "MATCH"
        elif "discrepancy" in ai_response.lower() or "does not match" in ai_response.lower() or "doesn't match" in ai_response.lower():
            verification_result = "DISCREPANCY"
        
        # Return formatted response
        return {
            "expense_id": expense_id,
            "recorded_amount": expense.get("amount"),
            "description": expense.get("description"),
            "date": expense.get("date"),
            "verification_type": verification_type,
            "analysis": ai_response,
            "verification_result": verification_result,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logger.error(f"Error verifying expense financial accuracy: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying expense: {str(e)}"
        ) 