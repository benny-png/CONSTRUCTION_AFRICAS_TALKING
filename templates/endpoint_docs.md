# Endpoint Documentation Template

Use this template for documenting API endpoints in a standardized way. Copy and adapt this format for each endpoint to maintain consistency across the API.

## Basic Structure

```python
@router.METHOD(
    "path", 
    response_model=ResponseModel,
    summary="Short summary (Role)",
    description="""
    Detailed description of what the endpoint does.
    
    Mention which roles can access this endpoint.
    
    ### Input Parameters
    
    **Required:**
    - `param1` (type): Description of parameter.
      Example: "example value"
    - `param2` (type): Description of parameter.
      Example: value
    
    **Optional:**
    - `param3` (type): Description of parameter.
      Example: "example value"
    - `param4` (type): Description of parameter.
      Example: value
    
    ### Response Format
    
    ```json
    {
      "field1": "example value",
      "field2": 123,
      "nested": {
        "subfield": "value"
      }
    }
    ```
    
    ### Authorization
    
    Mention required authorization (e.g., JWT token with specific role).
    
    ### curl Example
    ```bash
    curl -X 'METHOD' \\
      'https://construction.contactmanagers.xyz/path' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \\
      -H 'Content-Type: content-type' \\
      -d '{
        "param1": "value1",
        "param2": "value2"
      }'
    ```
    """,
    response_description="Description of the response returned"
)
```

## Examples

### POST Endpoint

```python
@router.post(
    "/items", 
    response_model=Item,
    summary="Create a new item (Manager only)",
    description="""
    Create a new item in the system.
    
    This endpoint is accessible only to users with the **manager** role.
    
    ### Input Parameters
    
    **Required:**
    - `name` (string): Name of the item.
      Example: "Cement Bags"
    - `quantity` (integer): Initial quantity of the item.
      Example: 50
    
    **Optional:**
    - `description` (string): Detailed description of the item.
      Example: "Portland Cement Type I/II"
    - `unit` (string): Unit of measurement.
      Example: "kg"
    
    ### Response Format
    
    ```json
    {
      "id": "61a23c4567d0d8992e610d96",
      "name": "Cement Bags",
      "quantity": 50,
      "description": "Portland Cement Type I/II",
      "unit": "kg",
      "created_at": "2023-08-15T14:25:30.123Z"
    }
    ```
    
    ### Authorization
    
    Requires a valid JWT token with manager role.
    
    ### curl Example
    ```bash
    curl -X 'POST' \\
      'https://construction.contactmanagers.xyz/items' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \\
      -H 'Content-Type: application/json' \\
      -d '{
        "name": "Cement Bags",
        "quantity": 50,
        "description": "Portland Cement Type I/II",
        "unit": "kg"
      }'
    ```
    """,
    response_description="Returns the newly created item with an ID and creation timestamp"
)
```

### GET Endpoint

```python
@router.get(
    "/items/{item_id}", 
    response_model=Item,
    summary="Get item details (All roles)",
    description="""
    Get details of a specific item by its ID.
    
    This endpoint is accessible to all authenticated users.
    
    ### Path Parameters
    
    - `item_id` (string): ID of the item to retrieve.
      Example: "61a23c4567d0d8992e610d96"
    
    ### Query Parameters
    
    **Optional:**
    - `include_history` (boolean): Whether to include the item's history.
      Example: true
    
    ### Response Format
    
    ```json
    {
      "id": "61a23c4567d0d8992e610d96",
      "name": "Cement Bags",
      "quantity": 50,
      "description": "Portland Cement Type I/II",
      "unit": "kg",
      "created_at": "2023-08-15T14:25:30.123Z",
      "history": [
        {
          "action": "created",
          "timestamp": "2023-08-15T14:25:30.123Z"
        }
      ]
    }
    ```
    
    ### Authorization
    
    Requires a valid JWT token (any role).
    
    ### curl Example
    ```bash
    curl -X 'GET' \\
      'https://construction.contactmanagers.xyz/items/61a23c4567d0d8992e610d96?include_history=true' \\
      -H 'accept: application/json' \\
      -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
    ```
    """,
    response_description="Returns the item details with optional history"
)
```

## Best Practices

1. Always include:
   - Clear summary with role information in parentheses
   - Detailed description
   - Parameter documentation with types and examples
   - Response format example
   - Authorization requirements
   - curl example

2. Use proper formatting:
   - Bold for role names using `**role**`
   - Code blocks for examples using triple backticks
   - Separate sections with headers (### Header)

3. Document parameters correctly:
   - Group by required and optional
   - Include type information in parentheses
   - Provide an example value for each parameter
   - For path and query parameters, document them in separate sections

4. Keep documentation up to date:
   - When changing parameters, update the documentation
   - When changing response models, update the example response
   - When changing authorization, update the requirements section 