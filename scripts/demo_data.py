#!/usr/bin/env python3
"""
Demo Data Generator Script for Construction Management System

This script populates the MongoDB database with demonstration data
for testing and presentation purposes.
"""

import asyncio
import os
import sys
import random
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path so we can import from the main application
sys.path.append(str(Path(__file__).parent.parent))

# Import database related modules
from database.db import init_db, get_db
from database.operations import (
    create_user,
    add_project,
    add_inventory_item,
    add_expense,
    add_progress_report,
    create_request,
    verify_expense
)

# Import models
from models.user import UserRole
from models.project import ProjectStatus
from models.expense import VerificationStatus

# Import utility for hashing passwords
from routers.auth import get_password_hash

# Configuration
NUM_MANAGERS = 2
NUM_WORKERS = 5
NUM_CLIENTS = 3
NUM_PROJECTS_PER_CLIENT = 2
NUM_INVENTORY_ITEMS_PER_PROJECT = 5
NUM_EXPENSES_PER_PROJECT = 4
NUM_PROGRESS_REPORTS_PER_PROJECT = 3

# Demo data
NAMES = {
    "first": ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth", 
              "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"],
    "last": ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor", 
             "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson"]
}

PROJECT_TYPES = [
    "Residential Building", "Commercial Complex", "Road Construction", "Bridge Construction",
    "School Building", "Hospital Construction", "Mall Construction", "Office Building",
    "Apartment Complex", "Warehouse Construction"
]

PROJECT_LOCATIONS = [
    "Nairobi, Kenya", "Mombasa, Kenya", "Kisumu, Kenya", "Nakuru, Kenya", 
    "Eldoret, Kenya", "Thika, Kenya", "Malindi, Kenya", "Kitale, Kenya",
    "Garissa, Kenya", "Kakamega, Kenya"
]

INVENTORY_ITEMS = [
    {"name": "Cement Bags", "unit": "bags", "cost_per_unit": 550.0},
    {"name": "Sand", "unit": "tonnes", "cost_per_unit": 2500.0},
    {"name": "Gravel", "unit": "tonnes", "cost_per_unit": 2800.0},
    {"name": "Steel Bars (10mm)", "unit": "pieces", "cost_per_unit": 850.0},
    {"name": "Steel Bars (12mm)", "unit": "pieces", "cost_per_unit": 1200.0},
    {"name": "Steel Bars (16mm)", "unit": "pieces", "cost_per_unit": 1950.0},
    {"name": "Wood Planks", "unit": "pieces", "cost_per_unit": 450.0},
    {"name": "Concrete Blocks", "unit": "pieces", "cost_per_unit": 55.0},
    {"name": "PVC Pipes (4 inch)", "unit": "pieces", "cost_per_unit": 750.0},
    {"name": "Electrical Wire", "unit": "meters", "cost_per_unit": 120.0},
    {"name": "Paint (White)", "unit": "gallons", "cost_per_unit": 2500.0},
    {"name": "Paint (Color)", "unit": "gallons", "cost_per_unit": 3000.0},
    {"name": "Tiles", "unit": "boxes", "cost_per_unit": 3500.0},
    {"name": "Roofing Sheets", "unit": "pieces", "cost_per_unit": 1200.0},
    {"name": "Door Frames", "unit": "pieces", "cost_per_unit": 3500.0},
    {"name": "Window Frames", "unit": "pieces", "cost_per_unit": 2800.0},
    {"name": "Screws and Nails", "unit": "kg", "cost_per_unit": 280.0},
    {"name": "Waterproofing Material", "unit": "kg", "cost_per_unit": 800.0}
]

EXPENSE_DESCRIPTIONS = [
    "Purchase of cement", "Purchase of sand", "Purchase of gravel", "Purchase of steel bars",
    "Payment for mason labor", "Payment for carpenter labor", "Payment for electrical work", 
    "Purchase of plumbing materials", "Transportation of materials", "Equipment rental",
    "Purchase of safety gear", "Site supervision fees", "Consulting fees", "Municipal permits",
    "Purchase of electrical fixtures", "Purchase of plumbing fixtures", "Quality testing fees"
]

PROGRESS_REPORT_DESCRIPTIONS = [
    "Foundation work completed", "Ground floor column work completed", "First floor slab completed",
    "Brickwork in progress", "Electrical wiring started", "Plumbing work in progress",
    "Plastering completed", "Tiling started", "Painting in progress", "Finishing work started",
    "External works in progress", "Roof installation completed", "Windows and doors installed",
    "Compound wall construction started", "Final inspection completed", "Site cleared and ready",
    "Interior finishing in progress", "External painting completed", "Landscaping work started"
]

# Helper functions
def random_phone():
    """Generate a random Kenyan phone number."""
    return f"+2547{random.randint(10000000, 99999999)}"

def random_date_between(start_date, end_date):
    """Generate a random date between two dates."""
    days_between = (end_date - start_date).days
    random_days = random.randint(0, days_between)
    return start_date + timedelta(days=random_days)

def random_name():
    """Generate a random full name."""
    first = random.choice(NAMES["first"])
    last = random.choice(NAMES["last"])
    return f"{first} {last}"

def random_username(name):
    """Generate a username from a name."""
    parts = name.lower().split()
    return f"{parts[0]}{parts[1][0]}{random.randint(1, 99)}"

def random_email(name):
    """Generate an email from a name."""
    parts = name.lower().split()
    return f"{parts[0]}.{parts[1]}@example.com"

# Main data generation functions
async def create_demo_users():
    """Create demo users with different roles."""
    users = {
        "managers": [],
        "workers": [],
        "clients": []
    }
    
    print("Creating users...")
    
    # Create manager users
    for i in range(NUM_MANAGERS):
        name = random_name()
        username = random_username(name)
        email = random_email(name)
        phone = random_phone()
        
        user_data = {
            "username": username,
            "email": email,
            "hashed_password": get_password_hash("password123"),
            "role": UserRole.MANAGER.value,
            "phone_number": phone,
            "name": name,
            "created_at": datetime.utcnow()
        }
        
        user_id = await create_user(user_data)
        users["managers"].append({"id": user_id, "name": name, "username": username})
        print(f"  Created manager: {username}")
    
    # Create worker users
    for i in range(NUM_WORKERS):
        name = random_name()
        username = random_username(name)
        email = random_email(name)
        phone = random_phone()
        
        user_data = {
            "username": username,
            "email": email,
            "hashed_password": get_password_hash("password123"),
            "role": UserRole.WORKER.value,
            "phone_number": phone,
            "name": name,
            "created_at": datetime.utcnow()
        }
        
        user_id = await create_user(user_data)
        users["workers"].append({"id": user_id, "name": name, "username": username})
        print(f"  Created worker: {username}")
    
    # Create client users
    for i in range(NUM_CLIENTS):
        name = random_name()
        username = random_username(name)
        email = random_email(name)
        phone = random_phone()
        
        user_data = {
            "username": username,
            "email": email,
            "hashed_password": get_password_hash("password123"),
            "role": UserRole.CLIENT.value,
            "phone_number": phone,
            "name": name,
            "created_at": datetime.utcnow()
        }
        
        user_id = await create_user(user_data)
        users["clients"].append({"id": user_id, "name": name, "username": username})
        print(f"  Created client: {username}")
    
    return users

async def create_demo_projects(users):
    """Create demo projects assigned to clients."""
    projects = []
    
    print("Creating projects...")
    
    for client in users["clients"]:
        for i in range(NUM_PROJECTS_PER_CLIENT):
            # Project details
            project_type = random.choice(PROJECT_TYPES)
            project_name = f"{project_type} - {random.choice(['Phase', 'Block', 'Tower', 'Section'])} {random.randint(1, 5)}"
            project_location = random.choice(PROJECT_LOCATIONS)
            
            # Random date calculation
            today = date.today()
            start_date = random_date_between(
                today - timedelta(days=180),  # 6 months ago
                today - timedelta(days=30)    # 1 month ago
            )
            end_date = random_date_between(
                today + timedelta(days=180),  # 6 months from now
                today + timedelta(days=365)   # 1 year from now
            )
            
            # Random budget based on project type
            if "Residential" in project_type:
                budget = random.uniform(5000000, 15000000)
            elif "Commercial" in project_type:
                budget = random.uniform(20000000, 50000000)
            elif "Road" in project_type or "Bridge" in project_type:
                budget = random.uniform(50000000, 200000000)
            else:
                budget = random.uniform(10000000, 30000000)
            
            # Random status
            status_weights = [
                (ProjectStatus.PLANNING.value, 0.2),
                (ProjectStatus.IN_PROGRESS.value, 0.6),
                (ProjectStatus.COMPLETED.value, 0.1),
                (ProjectStatus.ON_HOLD.value, 0.05),
                (ProjectStatus.CANCELLED.value, 0.05)
            ]
            status = random.choices(
                [s[0] for s in status_weights],
                weights=[s[1] for s in status_weights],
                k=1
            )[0]
            
            # Project data
            project_data = {
                "name": project_name,
                "description": f"Construction of {project_type.lower()} in {project_location}",
                "location": project_location,
                "budget": budget,
                "start_date": start_date,
                "end_date": end_date,
                "client_id": client["id"],
                "status": status,
                "created_by": random.choice(users["managers"])["id"]
            }
            
            # Convert date objects to datetime for MongoDB compatibility
            if isinstance(project_data["start_date"], date):
                project_data["start_date"] = datetime.combine(project_data["start_date"], datetime.min.time())
                
            if isinstance(project_data["end_date"], date):
                project_data["end_date"] = datetime.combine(project_data["end_date"], datetime.min.time())
            
            # Create project
            project_id = await add_project(project_data)
            projects.append({"id": project_id, "name": project_name, "client_id": client["id"]})
            print(f"  Created project: {project_name} for client {client['username']}")
    
    return projects

async def create_demo_inventory(projects, users):
    """Create demo inventory items for projects."""
    inventory_items = []
    
    print("Creating inventory items...")
    
    for project in projects:
        # Select random inventory items
        selected_items = random.sample(INVENTORY_ITEMS, NUM_INVENTORY_ITEMS_PER_PROJECT)
        
        for item_template in selected_items:
            # Item data
            item_data = {
                "name": item_template["name"],
                "description": f"Standard {item_template['name'].lower()} for construction use",
                "quantity": random.randint(10, 1000),
                "unit": item_template["unit"],
                "cost_per_unit": item_template["cost_per_unit"],
                "project_id": project["id"],
                "created_by": random.choice(users["managers"])["id"]
            }
            
            # Create inventory item
            item_id = await add_inventory_item(item_data)
            inventory_items.append({"id": item_id, "name": item_template["name"]})
            print(f"  Created inventory item: {item_template['name']} for project {project['name']}")
    
    return inventory_items

async def create_demo_expenses(projects, users):
    """Create demo expenses for projects."""
    expenses = []
    
    print("Creating expenses...")
    
    for project in projects:
        for i in range(NUM_EXPENSES_PER_PROJECT):
            # Expense data
            description = random.choice(EXPENSE_DESCRIPTIONS)
            amount = random.uniform(5000, 100000)
            
            # Random date calculation
            today = date.today()
            expense_date = random_date_between(
                today - timedelta(days=90),  # 3 months ago
                today - timedelta(days=1)    # Yesterday
            )
            
            # Expense data
            expense_data = {
                "amount": amount,
                "description": description,
                "date": expense_date,
                "project_id": project["id"],
                "verified": VerificationStatus.PENDING.value,
                "created_by": random.choice(users["managers"])["id"]
            }
            
            # Convert date objects to datetime for MongoDB compatibility
            if isinstance(expense_data["date"], date):
                expense_data["date"] = datetime.combine(expense_data["date"], datetime.min.time())
            
            # Create expense
            expense_id = await add_expense(expense_data)
            expenses.append({"id": expense_id, "description": description})
            print(f"  Created expense: {description} for project {project['name']}")
            
            # Randomly verify some expenses
            if random.random() < 0.7:  # 70% of expenses get verified
                status = random.choices(
                    [VerificationStatus.APPROVED.value, VerificationStatus.FLAGGED.value],
                    weights=[0.8, 0.2],  # 80% approved, 20% flagged
                    k=1
                )[0]
                
                await verify_expense(expense_id, status)
                print(f"    Verified expense as {status}")
    
    return expenses

async def create_demo_progress_reports(projects, users):
    """Create demo progress reports for projects."""
    progress_reports = []
    
    print("Creating progress reports...")
    
    for project in projects:
        # Skip projects in planning or cancelled state
        if project.get("status") in [ProjectStatus.PLANNING.value, ProjectStatus.CANCELLED.value]:
            continue
            
        for i in range(NUM_PROGRESS_REPORTS_PER_PROJECT):
            # Report data
            description = random.choice(PROGRESS_REPORT_DESCRIPTIONS)
            
            # Calculate percentage complete based on report number
            percentage = (i + 1) * (100 / NUM_PROGRESS_REPORTS_PER_PROJECT)
            if percentage > 100:
                percentage = 100
                
            # Random date calculation 
            today = date.today()
            report_date = random_date_between(
                today - timedelta(days=60),  # 2 months ago
                today - timedelta(days=1)    # Yesterday
            )
            
            # Report data
            report_data = {
                "report_date": report_date,
                "description": description,
                "percentage_complete": percentage,
                "submitted_by": random.choice(users["managers"])["id"]
            }
            
            # Convert date objects to datetime for MongoDB compatibility
            if isinstance(report_data["report_date"], date):
                report_data["report_date"] = datetime.combine(report_data["report_date"], datetime.min.time())
            
            # Create progress report
            await add_progress_report(project["id"], report_data)
            print(f"  Created progress report: {percentage:.1f}% - {description} for project {project['name']}")
    
    return progress_reports

async def create_demo_inventory_requests(projects, users, inventory_items):
    """Create demo inventory requests from workers."""
    requests = []
    
    print("Creating inventory requests...")
    
    # Select projects that are in progress
    in_progress_projects = [p for p in projects if p.get("status") == ProjectStatus.IN_PROGRESS.value]
    
    if not in_progress_projects:
        print("  No in-progress projects found for inventory requests")
        return requests
        
    for project in in_progress_projects:
        # Create 2-3 requests per project
        num_requests = random.randint(2, 3)
        
        for i in range(num_requests):
            worker = random.choice(users["workers"])
            manager = random.choice(users["managers"])
            
            # Request data
            request_data = {
                "item_name": random.choice(inventory_items)["name"],
                "quantity": random.randint(5, 20),
                "project_id": project["id"],
                "worker_id": worker["id"],
                "manager_id": manager["id"],
                "reason": f"Needed for {random.choice(['foundation work', 'column work', 'slab work', 'brickwork', 'electrical', 'plumbing', 'finishing'])}",
                "status": random.choice(["pending", "approved", "rejected"])
            }
            
            # Create request
            request_id = await create_request(request_data)
            requests.append({"id": request_id, "item": request_data["item_name"]})
            print(f"  Created inventory request: {request_data['item_name']} by {worker['username']} for project {project['name']}")
    
    return requests

async def main():
    """Main function to create all demo data."""
    print("Initializing database connection...")
    await init_db()
    
    print("\n=== CONSTRUCTION MANAGEMENT SYSTEM DEMO DATA GENERATOR ===\n")
    
    # Create demo users
    users = await create_demo_users()
    
    # Create demo projects
    projects = await create_demo_projects(users)
    
    # Create demo inventory
    inventory_items = await create_demo_inventory(projects, users)
    
    # Create demo expenses
    expenses = await create_demo_expenses(projects, users)
    
    # Create demo progress reports
    progress_reports = await create_demo_progress_reports(projects, users)
    
    # Create demo inventory requests
    requests = await create_demo_inventory_requests(projects, users, inventory_items)
    
    print("\n=== DEMO DATA GENERATION COMPLETE ===\n")
    print(f"Created {len(users['managers'])} managers, {len(users['workers'])} workers, and {len(users['clients'])} clients")
    print(f"Created {len(projects)} projects")
    print(f"Created {len(inventory_items)} inventory items")
    print(f"Created {len(expenses)} expenses")
    print(f"Created {len(requests)} inventory requests")
    
    print("\nDemo account credentials:")
    print("  All users have password: password123")
    print("  Manager accounts:")
    for manager in users["managers"]:
        print(f"    Username: {manager['username']}")
    print("  Client accounts:")
    for client in users["clients"]:
        print(f"    Username: {client['username']}")
    print("  Worker accounts:")
    for worker in users["workers"]:
        print(f"    Username: {worker['username']}")

if __name__ == "__main__":
    asyncio.run(main()) 