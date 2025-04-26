import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def print_response(response):
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    print("Response Body:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    print("-" * 50)

def register_user(username, password, email, role):
    print(f"\nRegistering user: {username}")
    url = f"{BASE_URL}/auth/register"
    data = {
        "username": username,
        "password": password,
        "email": email,
        "role": role
    }
    response = requests.post(url, json=data)
    print_response(response)
    return response

def login_user(username, password):
    print(f"\nLogging in user: {username}")
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": username,
        "password": password
    }
    response = requests.post(url, data=data)
    print_response(response)
    return response

def get_current_user(token):
    print("\nGetting current user")
    url = f"{BASE_URL}/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    print_response(response)
    return response

def main():
    # Register a manager
    username = "manager1"
    password = "password123"
    email = "manager@example.com"
    role = "manager"
    
    register_response = register_user(username, password, email, role)
    
    # If registration is successful, try to login
    if register_response.status_code == 200:
        login_response = login_user(username, password)
        
        # If login is successful, get the token and try to access protected endpoint
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            get_current_user(token)
    
    print("\nTest completed.")

if __name__ == "__main__":
    main() 