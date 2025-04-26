from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, UploadFile, File, Form
from typing import Annotated, List, Optional
import traceback
import os
import base64
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

from models.user import UserRole
from routers.auth import get_current_user, check_user_role
from logging_config import logger

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

# AI assistant for managers - Project planning and advice
@router.post(
    "/manager/project-advice", 
    summary="Get AI advice for project planning (Manager only)",
    description="""
    Get AI-powered advice and suggestions for project planning and management.
    
    This endpoint is accessible only to users with the **manager** role.
    
    Managers can describe their project needs, challenges or questions to get
    AI-generated recommendations, best practices, and advice.
    
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
        "budget_constraint": "high"
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
            "timestamp": datetime.utcnow().isoformat()
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
      -F 'image=@photo_of_wall.jpg'
    ```
    """,
    response_description="Returns AI-generated construction guidance"
)
async def get_worker_construction_help(
    token_data: dict = Depends(check_user_role([UserRole.WORKER])),
    query: str = Form(..., description="The worker's question or request for help"),
    image: Optional[UploadFile] = File(None, description="Optional image of the construction issue"),
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
        
        # Add text query
        content.append({
            "type": "text",
            "text": f"You are an expert construction advisor. I'm a construction worker with this question: {query}"
        })
        
        # Process image if provided
        if image:
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
                
            # Add image to content
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            })
            
            # Clean up the temp file
            os.remove(image_path)
            
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
            "timestamp": datetime.utcnow().isoformat()
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
        
        # In a real implementation, you would fetch the actual project data here
        # For now, we'll simulate with a generic response
        
        # Prepare prompt with context
        prompt = f"You are an expert construction project interpreter for clients. Explain project progress in clear, non-technical terms.\n\n"
        prompt += f"Client query: {query}\n"
        prompt += f"Regarding project ID: {project_id}\n"
        prompt += "Note: For this demo, provide a helpful response without actual project data. Explain what information would normally be analyzed to answer this question."
        
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
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting AI progress analysis: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting AI analysis: {str(e)}"
        ) 