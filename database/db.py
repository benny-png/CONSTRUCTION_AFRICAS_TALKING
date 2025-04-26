from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection string
MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING", "mongodb+srv://mazikuben2:F7F5eKbqK67eRX4c@cluster0.pom2hgm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DATABASE_NAME = os.getenv("DATABASE_NAME", "construction_management")

# Async client for API operations
async_client = AsyncIOMotorClient(MONGO_CONNECTION_STRING)
async_db = async_client[DATABASE_NAME]

# Sync client for operations that need synchronous access
sync_client = MongoClient(MONGO_CONNECTION_STRING)
sync_db = sync_client[DATABASE_NAME]

# Collections
users_collection = async_db.users
projects_collection = async_db.projects
inventory_collection = async_db.inventory
expenses_collection = async_db.expenses
receipts_collection = async_db.receipts
requests_collection = async_db.requests
material_usage_collection = async_db.material_usage
notifications_collection = async_db.notifications

# Create indexes for better performance
async def create_indexes():
    # User indexes
    await users_collection.create_index("username", unique=True)
    await users_collection.create_index("email", unique=True)
    
    # Project indexes
    await projects_collection.create_index("client_id")
    
    # Inventory indexes
    await inventory_collection.create_index("project_id")
    
    # Expense indexes
    await expenses_collection.create_index("project_id")
    
    # Request indexes
    await requests_collection.create_index("project_id")
    await requests_collection.create_index("worker_id")
    
    # Material usage indexes
    await material_usage_collection.create_index("project_id")
    
    # Notification indexes
    await notifications_collection.create_index("user_id")

# Initialize database
async def init_db():
    try:
        await create_indexes()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}") 