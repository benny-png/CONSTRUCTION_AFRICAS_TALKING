from bson import ObjectId
from datetime import datetime
from typing import List, Dict, Any, Optional

from database.db import (
    users_collection, 
    projects_collection, 
    inventory_collection, 
    expenses_collection, 
    receipts_collection, 
    requests_collection, 
    material_usage_collection,
    notifications_collection
)

# Helper to convert ObjectId to string
def serialize_object_id(doc):
    if doc.get("_id"):
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc

# User operations
async def create_user(user_data: Dict[str, Any]) -> str:
    user_data["created_at"] = datetime.utcnow()
    result = await users_collection.insert_one(user_data)
    return str(result.inserted_id)

async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    user = await users_collection.find_one({"username": username})
    if user:
        return serialize_object_id(user)
    return None

async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(user_id):
        return None
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if user:
        return serialize_object_id(user)
    return None

async def get_users() -> List[Dict[str, Any]]:
    cursor = users_collection.find()
    users = []
    async for user in cursor:
        users.append(serialize_object_id(user))
    return users

async def update_user(user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(user_id):
        return None
    
    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        return None
    
    # Return the updated user
    return await get_user_by_id(user_id)

async def delete_user(user_id: str) -> bool:
    if not ObjectId.is_valid(user_id):
        return False
    
    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    return result.deleted_count > 0

async def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Alias for get_user_by_id for consistent naming."""
    return await get_user_by_id(user_id)

# Project operations
async def create_project(project_data: Dict[str, Any]) -> str:
    project_data["created_at"] = datetime.utcnow()
    result = await projects_collection.insert_one(project_data)
    return str(result.inserted_id)

# Alias for create_project for consistent naming
async def add_project(project_data: Dict[str, Any]) -> str:
    return await create_project(project_data)

async def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(project_id):
        return None
    project = await projects_collection.find_one({"_id": ObjectId(project_id)})
    if project:
        return serialize_object_id(project)
    return None

async def get_projects_by_client(client_id: str) -> List[Dict[str, Any]]:
    if not ObjectId.is_valid(client_id):
        return []
    cursor = projects_collection.find({"client_id": client_id})
    projects = []
    async for project in cursor:
        projects.append(serialize_object_id(project))
    return projects

async def add_progress_report(project_id: str, report_data: Dict[str, Any]) -> str:
    if not ObjectId.is_valid(project_id):
        return None
    report_data["created_at"] = datetime.utcnow()
    report_data["project_id"] = project_id
    
    # Add the progress report to the project
    await projects_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$push": {"progress_reports": report_data}}
    )
    
    return project_id

async def get_progress_reports(project_id: str) -> List[Dict[str, Any]]:
    if not ObjectId.is_valid(project_id):
        return []
    project = await projects_collection.find_one(
        {"_id": ObjectId(project_id)},
        {"progress_reports": 1}
    )
    if project and "progress_reports" in project:
        return project["progress_reports"]
    return []

async def get_all_projects(status: Optional[str] = None, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all projects with optional filtering by status and client_id."""
    query = {}
    
    if status:
        query["status"] = status
        
    if client_id and ObjectId.is_valid(client_id):
        query["client_id"] = client_id
    
    cursor = projects_collection.find(query)
    projects = []
    async for project in cursor:
        projects.append(serialize_object_id(project))
    return projects

async def update_project(project_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a project's details."""
    if not ObjectId.is_valid(project_id):
        return None
    
    result = await projects_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        return None
    
    # Return the updated project
    return await get_project(project_id)

async def delete_project(project_id: str) -> bool:
    """Delete a project and its associated data."""
    if not ObjectId.is_valid(project_id):
        return False
    
    # Delete the project
    result = await projects_collection.delete_one({"_id": ObjectId(project_id)})
    
    # Note: In a production environment, you might want to also delete or archive
    # related data like expenses, material usage, etc.
    
    return result.deleted_count > 0

# Inventory operations
async def add_inventory_item(item_data: Dict[str, Any]) -> str:
    item_data["created_at"] = datetime.utcnow()
    result = await inventory_collection.insert_one(item_data)
    return str(result.inserted_id)

async def get_inventory_by_project(project_id: str) -> List[Dict[str, Any]]:
    if not ObjectId.is_valid(project_id):
        return []
    cursor = inventory_collection.find({"project_id": project_id})
    items = []
    async for item in cursor:
        items.append(serialize_object_id(item))
    return items

async def update_inventory_quantity(item_id: str, quantity_change: int) -> bool:
    if not ObjectId.is_valid(item_id):
        return False
    result = await inventory_collection.update_one(
        {"_id": ObjectId(item_id)},
        {"$inc": {"quantity": quantity_change}}
    )
    return result.modified_count > 0

# Request operations
async def create_request(request_data: Dict[str, Any]) -> str:
    request_data["created_at"] = datetime.utcnow()
    request_data["status"] = "pending"  # Initial status
    result = await requests_collection.insert_one(request_data)
    
    # Create notification for project manager
    notification = {
        "user_id": request_data.get("manager_id"),
        "type": "inventory_request",
        "message": f"New inventory request for {request_data.get('item_name')}",
        "created_at": datetime.utcnow(),
        "read": False,
        "request_id": str(result.inserted_id)
    }
    await notifications_collection.insert_one(notification)
    
    return str(result.inserted_id)

async def get_requests_by_project(project_id: str) -> List[Dict[str, Any]]:
    if not ObjectId.is_valid(project_id):
        return []
    cursor = requests_collection.find({"project_id": project_id})
    requests = []
    async for request in cursor:
        requests.append(serialize_object_id(request))
    return requests

async def get_requests_by_worker(worker_id: str) -> List[Dict[str, Any]]:
    if not ObjectId.is_valid(worker_id):
        return []
    cursor = requests_collection.find({"worker_id": worker_id})
    requests = []
    async for request in cursor:
        requests.append(serialize_object_id(request))
    return requests

# Material usage operations
async def log_material_usage(usage_data: Dict[str, Any]) -> str:
    usage_data["created_at"] = datetime.utcnow()
    result = await material_usage_collection.insert_one(usage_data)
    
    # Update inventory quantity
    item_name = usage_data.get("item_name")
    project_id = usage_data.get("project_id")
    quantity_used = usage_data.get("quantity_used", 0)
    
    # Find the inventory item
    inventory_item = await inventory_collection.find_one({
        "name": item_name,
        "project_id": project_id
    })
    
    if inventory_item:
        # Update inventory quantity
        await inventory_collection.update_one(
            {"_id": inventory_item["_id"]},
            {"$inc": {"quantity": -quantity_used}}
        )
    
    return str(result.inserted_id)

async def get_material_usage_by_project(project_id: str) -> List[Dict[str, Any]]:
    if not ObjectId.is_valid(project_id):
        return []
    cursor = material_usage_collection.find({"project_id": project_id})
    usage_logs = []
    async for log in cursor:
        usage_logs.append(serialize_object_id(log))
    return usage_logs

# Expense operations
async def add_expense(expense_data: Dict[str, Any]) -> str:
    expense_data["created_at"] = datetime.utcnow()
    expense_data["verified"] = "pending"  # Initial verification status
    result = await expenses_collection.insert_one(expense_data)
    return str(result.inserted_id)

async def get_expenses_by_project(project_id: str) -> List[Dict[str, Any]]:
    if not ObjectId.is_valid(project_id):
        return []
    cursor = expenses_collection.find({"project_id": project_id})
    expenses = []
    async for expense in cursor:
        expenses.append(serialize_object_id(expense))
    return expenses

async def get_expense(expense_id: str) -> Optional[Dict[str, Any]]:
    if not ObjectId.is_valid(expense_id):
        return None
    expense = await expenses_collection.find_one({"_id": ObjectId(expense_id)})
    if expense:
        return serialize_object_id(expense)
    return None

async def verify_expense(expense_id: str, status: str) -> bool:
    if not ObjectId.is_valid(expense_id):
        return False
    result = await expenses_collection.update_one(
        {"_id": ObjectId(expense_id)},
        {"$set": {"verified": status}}
    )
    return result.modified_count > 0

# Notification operations
async def get_notifications(user_id: str) -> List[Dict[str, Any]]:
    if not ObjectId.is_valid(user_id):
        return []
    cursor = notifications_collection.find({"user_id": user_id})
    notifications = []
    async for notification in cursor:
        notifications.append(serialize_object_id(notification))
    return notifications

async def mark_notification_read(notification_id: str) -> bool:
    if not ObjectId.is_valid(notification_id):
        return False
    result = await notifications_collection.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {"read": True}}
    )
    return result.modified_count > 0

# Project summary analytics
async def get_project_summary(project_id: str) -> Dict[str, Any]:
    if not ObjectId.is_valid(project_id):
        return {}
    
    # Get project details
    project = await get_project(project_id)
    if not project:
        return {}
    
    # Calculate total expenses
    expenses = await get_expenses_by_project(project_id)
    total_expenses = sum(expense.get("amount", 0) for expense in expenses)
    
    # Calculate total materials used
    usage_logs = await get_material_usage_by_project(project_id)
    material_usage = {}
    for log in usage_logs:
        item_name = log.get("item_name")
        quantity = log.get("quantity_used", 0)
        if item_name in material_usage:
            material_usage[item_name] += quantity
        else:
            material_usage[item_name] = quantity
    
    # Get latest progress report
    progress_reports = await get_progress_reports(project_id)
    latest_progress = progress_reports[-1] if progress_reports else {"percentage_complete": 0}
    
    return {
        "project_name": project.get("name"),
        "total_expenses": total_expenses,
        "material_usage": material_usage,
        "progress_percentage": latest_progress.get("percentage_complete", 0),
        "start_date": project.get("start_date"),
        "end_date": project.get("end_date"),
        "expenses_count": len(expenses),
        "material_usage_count": len(usage_logs)
    } 