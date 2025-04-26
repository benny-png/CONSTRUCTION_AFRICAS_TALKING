from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import EmailStr
from typing import Annotated, List, Optional
from datetime import datetime, timedelta
import traceback
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv
from functools import wraps

from models.user import UserCreate, User, UserLogin, Token, TokenData, UserRole, UserUpdate, TokenResponse
from database.auth import verify_password, get_password_hash, create_access_token
from database.operations import create_user, get_user_by_username, get_user_by_id as get_user, update_user
from database.auth import decode_access_token
from logging_config import logger

# Load environment variables
load_dotenv()

# Security configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "a9ddbcaba8c0ac1a0a812dc0c2f08514f5593b02f0a1a9fdd4da1e28d6391cb7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

router = APIRouter()

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def authenticate_user(username: str, password: str):
    user = await get_user_by_username(username)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

# Helper to get current user from token
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    logger.debug(f"Decoding token: {token[:10]}...")
    
    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("Username missing from token")
            raise credentials_exception
            
        # Get user from database
        logger.debug(f"Getting user by username: {username}")
        user = await get_user_by_username(username)
        
        if user is None:
            logger.warning(f"User not found: {username}")
            raise credentials_exception
            
        # Combine user data with token payload for consistent access
        # This ensures both the check_user_role and other functions can access the same data
        user_data = {
            **user,
            "token_payload": payload  # Include the original token payload
        }
            
        logger.debug(f"User found: {username}")
        return user_data
    except JWTError as e:
        logger.error(f"JWT error: {str(e)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating credentials: {str(e)}"
        )

# Helper to check role
def check_user_role(allowed_roles: List[UserRole]):
    async def _check_user_role(token: Annotated[str, Depends(oauth2_scheme)]):
        try:
            # Decode the token first
            logger.debug(f"Decoding token for role check: {token[:10]}...")
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Extract user role from payload
            role = payload.get("role")
            if not role:
                logger.warning("No role found in token")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token: missing role",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            logger.debug(f"Checking user role. User role: {role}, Required roles: {[role.value for role in allowed_roles]}")
            
            # Check if user has required role
            if UserRole(role) not in allowed_roles:
                logger.warning(f"Insufficient permissions. User role: {role}, Required roles: {[role.value for role in allowed_roles]}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {[role.value for role in allowed_roles]}"
                )
            
            logger.debug("Role check passed")
            return payload  # Return the full decoded payload
        except JWTError as e:
            logger.error(f"JWT error during role check: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.error(f"Error checking user role: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error validating credentials: {str(e)}"
            )
    return _check_user_role

# Register a new user
@router.post(
    "/register", 
    response_model=User,
    summary="Register a new user",
    description="""
    Register a new user in the system with the specified role.
    
    The user can be a project manager, worker, or client. 
    Each role has different permissions within the system.
    
    - **manager**: Full access to project management, inventory, expenses, and receipts
    - **worker**: Can only request inventory
    - **client**: Can only view project progress, expenses, and receipts
    
    ### curl Example
    ```bash
    curl -X 'POST' \\
      'https://construction.contactmanagers.xyz/auth/register' \\
      -H 'accept: application/json' \\
      -H 'Content-Type: application/json' \\
      -d '{
        "username": "john_doe",
        "password": "password123",
        "email": "john.doe@example.com",
        "role": "manager"
      }'
    ```
    """,
    response_description="Returns the newly created user with an ID and creation timestamp"
)
async def register_user(
    user_data: UserCreate = Body(
        ...,
        example={
            "username": "john_doe",
            "password": "password123",
            "email": "john.doe@example.com",
            "role": "manager"
        }
    ), 
    request: Request = None
):
    logger.info(f"Registering new user: {user_data.username}, Role: {user_data.role}")
    
    try:
        # Log the entire user data for debugging
        user_dict = user_data.dict()
        user_dict_safe = user_dict.copy()
        if "password" in user_dict_safe:
            user_dict_safe["password"] = "********"
        logger.debug(f"User registration data: {user_dict_safe}")
        
        # Check if username already exists
        existing_user = await get_user_by_username(user_data.username)
        if existing_user:
            logger.warning(f"Username already exists: {user_data.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Hash the password
        logger.debug("Hashing password")
        hashed_password = get_password_hash(user_data.password)
        
        # Create user in database
        logger.debug("Creating user in database")
        user_dict = user_data.dict()
        user_dict.pop("password")
        user_dict["hashed_password"] = hashed_password
        
        logger.debug(f"Inserting user into database: {user_data.username}")
        user_id = await create_user(user_dict)
        logger.info(f"User created successfully: {user_data.username}, ID: {user_id}")
        
        # Return user without password but with created_at datetime
        response_data = {**user_dict, "id": user_id, "created_at": datetime.utcnow()}
        logger.debug(f"Returning response data: {response_data}")
        return response_data
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        logger.warning(f"HTTP exception in user registration: {str(he)}")
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error registering user: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering user: {str(e)}"
        )

# Login user
@router.post(
    "/login", 
    response_model=TokenResponse,
    summary="Login to get access token",
    description="""
    Login with username and password to get an access token.
    
    The access token is required for all authenticated endpoints and should be 
    included in the Authorization header as a Bearer token.
    
    **Example header**: `Authorization: Bearer <token>`
    
    ### curl Example
    ```bash
    curl -X 'POST' \\
      'https://construction.contactmanagers.xyz/auth/login' \\
      -H 'accept: application/json' \\
      -H 'Content-Type: application/x-www-form-urlencoded' \\
      -d 'username=john_doe&password=password123'
    ```
    """,
    response_description="Returns an access token and token type"
)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request = None
):
    """
    Login with username and password to get an access token.
    
    - **username**: User's username
    - **password**: User's password
    """
    logger.info(f"Login attempt: {form_data.username}")
    try:
        # Get user from database
        logger.debug(f"Getting user from database: {form_data.username}")
        user = await authenticate_user(form_data.username, form_data.password)
        if not user:
            logger.warning(f"Invalid credentials for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["username"], "user_id": user["id"], "role": user["role"]},
            expires_delta=access_token_expires
        )
        
        logger.info(f"Login successful: {form_data.username}")
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error during login: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during login: {str(e)}"
        )

# Get current user info
@router.get(
    "/me", 
    response_model=User,
    summary="Get current user information",
    description="""
    Get information about the currently authenticated user.
    
    This endpoint requires authentication with a valid token.
    
    ### curl Example
    ```bash
    curl -X 'GET' \\
      'https://construction.contactmanagers.xyz/auth/me' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    ```
    """,
    response_description="Returns the authenticated user's information"
)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    """
    Get information about the currently authenticated user.
    """
    logger.info(f"Getting current user info: {current_user['username']}")
    return current_user 

# Create manager or worker account (manager only)
@router.post(
    "/create-staff", 
    response_model=User,
    summary="Create staff account (Manager only)",
    description="""
    Create a new staff account (manager or worker).
    
    This endpoint is accessible only to users with the **manager** role.
    It allows managers to create new manager or worker accounts.
    
    Required fields include username, password, name, email, phone_number, and role.
    
    ### curl Example
    ```bash
    curl -X 'POST' \\
      'https://construction.contactmanagers.xyz/auth/create-staff' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \\
      -H 'Content-Type: application/json' \\
      -d '{
        "username": "site_manager",
        "password": "StaffPassword123",
        "email": "jane.smith@construction.com",
        "role": "manager"
      }'
    ```
    """,
    response_description="Returns the registered staff information without the password"
)
async def create_staff_account(
    current_user: Annotated[dict, Depends(check_user_role([UserRole.MANAGER]))],
    user_data: UserCreate = Body(
        ...,
        example={
            "username": "site_manager",
            "password": "StaffPassword123",
            "email": "jane.smith@construction.com",
            "role": "manager"
        }
    ),
    request: Request = None
):
    """
    Create a new staff account (manager or worker).
    
    Requires manager role.
    """
    try:
        logger.info(f"Creating staff account: {user_data.username}, role: {user_data.role}")
        
        # Validate role
        if user_data.role not in [UserRole.MANAGER.value, UserRole.WORKER.value]:
            logger.warning(f"Invalid role for staff account: {user_data.role}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be manager or worker for staff accounts"
            )
        
        # Check if username already exists
        existing_user = await get_user_by_username(user_data.username)
        if existing_user:
            logger.warning(f"Username already exists: {user_data.username}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Hash the password
        hashed_password = get_password_hash(user_data.password)
        logger.debug("Password hashed successfully")
        
        # Create user data
        user_dict = user_data.dict()
        user_dict.pop("password")
        user_dict["hashed_password"] = hashed_password
        
        # Create user in database
        user_id = await create_user(user_dict)
        if not user_id:
            logger.error("Failed to create staff account in database")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create staff account"
            )
        
        logger.info(f"Staff account created successfully: {user_data.username}")
        
        # Return user without password
        return_data = {**user_dict, "id": user_id, "created_at": datetime.utcnow()}
        
        return return_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating staff account: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating staff account: {str(e)}"
        ) 