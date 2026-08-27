"""
REST API Application using FastAPI
Supports:
- GET /api/items - List all items
- GET /api/items/{id} - Get item by ID
- POST /api/items - Create new item
- PUT /api/items/{id} - Update item
- DELETE /api/items/{id} - Delete item
- GET /api/health - Health check endpoint
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

app = FastAPI(
    title="REST API",
    description="A simple REST API for managing items",
    version="1.0.0"
)

# In-memory data store
items_db: dict = {}
next_id = 1


# Pydantic models for request/response validation
class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Item name is required")
    price: float = Field(..., ge=0, description="Price must be non-negative")
    description: Optional[str] = Field(default="", description="Item description")


class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="Item name is required")
    price: Optional[float] = Field(None, ge=0, description="Price must be non-negative")
    description: Optional[str] = None


class ItemResponse(BaseModel):
    id: str
    name: str
    description: str
    price: float
    created_at: str


class ItemListResponse(BaseModel):
    items: List[ItemResponse]
    count: int


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str


class ErrorResponse(BaseModel):
    error: str
    message: str


# Health check endpoint
@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0"
    )


# List all items
@app.get("/api/items", response_model=ItemListResponse)
async def get_items():
    """Get all items"""
    items_list = []
    for item_id, item in items_db.items():
        items_list.append(ItemResponse(
            id=item_id,
            name=item["name"],
            description=item["description"],
            price=item["price"],
            created_at=item["created_at"]
        ))
    return ItemListResponse(items=items_list, count=len(items_list))


# Get single item by ID
@app.get("/api/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str):
    """Get item by ID"""
    if item_id not in items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )
    
    item = items_db[item_id]
    return ItemResponse(
        id=item_id,
        name=item["name"],
        description=item["description"],
        price=item["price"],
        created_at=item["created_at"]
    )


# Create new item
@app.post("/api/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate):
    """Create a new item"""
    global next_id
    
    # Generate new ID
    new_id = str(next_id)
    next_id += 1
    
    # Create item
    new_item = {
        "id": new_id,
        "name": item.name,
        "description": item.description or "",
        "price": item.price,
        "created_at": datetime.utcnow().isoformat()
    }
    
    items_db[new_id] = new_item
    
    return ItemResponse(
        id=new_id,
        name=new_item["name"],
        description=new_item["description"],
        price=new_item["price"],
        created_at=new_item["created_at"]
    )


# Update item
@app.put("/api/items/{item_id}", response_model=ItemResponse)
async def update_item(item_id: str, item_update: ItemUpdate):
    """Update an existing item"""
    # Check if item exists
    if item_id not in items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )
    
    # Update item
    items_db[item_id]["name"] = item_update.name or items_db[item_id]["name"]
    if item_update.price is not None:
        items_db[item_id]["price"] = item_update.price
    if item_update.description is not None:
        items_db[item_id]["description"] = item_update.description
    
    item = items_db[item_id]
    return ItemResponse(
        id=item_id,
        name=item["name"],
        description=item["description"],
        price=item["price"],
        created_at=item["created_at"]
    )


# Delete item
@app.delete("/api/items/{item_id}", status_code=status.HTTP_200_OK)
async def delete_item(item_id: str):
    """Delete an item"""
    # Check if item exists
    if item_id not in items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with ID {item_id} not found"
        )
    
    # Delete item
    del items_db[item_id]
    
    return {"message": f"Item {item_id} deleted successfully"}


# Root endpoint
@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to the REST API",
        "version": "1.0.0",
        "endpoints": {
            "GET /api/health": "Health check",
            "GET /api/items": "List all items",
            "GET /api/items/{id}": "Get item by ID",
            "POST /api/items": "Create new item",
            "PUT /api/items/{id}": "Update item",
            "DELETE /api/items/{id}": "Delete item"
        }
    }


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("REST API Server Starting...")
    print("=" * 60)
    print("Available endpoints:")
    print("  GET  /              - API information")
    print("  GET  /api/health    - Health check")
    print("  GET  /api/items     - List all items")
    print("  GET  /api/items/{id} - Get item by ID")
    print("  POST /api/items     - Create new item")
    print("  PUT  /api/items/{id} - Update item")
    print("  DELETE /api/items/{id} - Delete item")
    print("=" * 60)
    print("Starting server on http://localhost:8000")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
