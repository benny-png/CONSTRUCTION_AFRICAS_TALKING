import os
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import traceback
from starlette.middleware.base import BaseHTTPMiddleware

# Import logging
from logging_config import logger, log_request_info, log_response_info

# Import routers
from routers import auth, projects, inventory, requests, expenses, material_usage, notifications, ai_assistance
from database.db import init_db

# Create FastAPI app
app = FastAPI(
    title="Construction Management API",
    description="""
    # Construction Management API

    This API provides a comprehensive solution for managing construction projects, inventory, expenses, and more.
    
    ## Features
    
    - **User Management**: Register and authenticate users with role-based access control
    - **Project Management**: Create projects and submit progress reports
    - **Inventory Management**: Track materials and assets in the inventory
    - **Inventory Requests**: Workers can request inventory items needed for their tasks
    - **Material Usage**: Track daily material usage for efficient resource allocation
    - **Expense Tracking**: Monitor expenses and upload receipts for transactions
    - **Receipt Verification**: Clients can verify the authenticity of expenses by viewing receipts
    - **Analytics**: Get summary statistics for projects
    
    ## User Roles
    
    - **Manager**: Full access to project management, inventory, expenses, and receipts
    - **Worker**: Can only request inventory and view assigned projects
    - **Client**: Can only view project progress, expenses, and verify receipts
    
    ## Authentication
    
    All endpoints (except for registration and login) require authentication using JWT tokens.
    To authenticate, include the token in the Authorization header:
    
    ```
    Authorization: Bearer your_access_token
    ```
    
    You can get an access token by calling the `/auth/login` endpoint with valid credentials.
    """,
    version="1.0.0",
    contact={
        "name": "Construction Management Support",
        "email": "support@construction-mgmt.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "Operations related to user authentication, registration, and account management"
        },
        {
            "name": "Projects",
            "description": "Operations related to construction projects, progress reports, and summaries"
        },
        {
            "name": "Inventory",
            "description": "Operations related to inventory management and tracking"
        },
        {
            "name": "Requests",
            "description": "Operations related to inventory requests from workers"
        },
        {
            "name": "Expenses",
            "description": "Operations related to expense tracking, receipts, and verification"
        },
        {
            "name": "Material Usage",
            "description": "Operations related to tracking material usage in projects"
        },
        {
            "name": "Notifications",
            "description": "Operations related to user notifications"
        },
        {
            "name": "AI Assistance",
            "description": "AI-powered assistance for managers, workers, and clients"
        },
        {
            "name": "Root",
            "description": "Root endpoint for the API"
        }
    ]
)

# Logging middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        log_request_info(request)
        try:
            response = await call_next(request)
            log_response_info(response)
            return response
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            logger.error(traceback.format_exc())
            raise

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for receipts
os.makedirs("uploads/receipts", exist_ok=True)
app.mount("/receipts", StaticFiles(directory="uploads/receipts"), name="receipts")

# Mount static files for inventory images
os.makedirs("uploads/inventory", exist_ok=True)
app.mount("/inventory-images", StaticFiles(directory="uploads/inventory"), name="inventory_images")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
app.include_router(requests.router, prefix="/requests", tags=["Requests"])
app.include_router(expenses.router, prefix="/expenses", tags=["Expenses"])
app.include_router(material_usage.router, prefix="/material-usage", tags=["Material Usage"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
app.include_router(ai_assistance.router, prefix="/ai", tags=["AI Assistance"])

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to Construction Management API"}

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": f"An unexpected error occurred: {str(exc)}"}
    )

# Startup event to initialize database
@app.on_event("startup")
async def startup_event():
    logger.info("Starting application...")
    await init_db()
    logger.info("Application started successfully")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 