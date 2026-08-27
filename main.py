from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import uuid

app = FastAPI(
    title="User Management API",
    description="A REST API for managing users with CRUD operations",
    version="1.0.0"
)

# In-memory storage (replace with database in production)
users_db = {}
next_id = 1

# Pydantic models
class UserBase(BaseModel):
    name: str
    email: EmailStr
    age: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    age: Optional[int] = None
    password: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    age: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Helper functions
def generate_id() -> int:
    global next_id
    user_id = next_id
    next_id += 1
    return user_id

def generate_uuid() -> str:
    return str(uuid.uuid4())

# API Endpoints

@app.get("/", response_model=dict)
async def root():
    """Root endpoint - API information"""
    return {
        "message": "Welcome to User Management API",
        "version": "1.0.0",
        "endpoints": [
            "/users",
            "/users/{user_id}",
            "/users/{user_id}/profile",
            "/users/{user_id}/update",
            "/users/{user_id}/delete"
        ]
    }

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """Create a new user"""
    global users_db
    
    # Check if email already exists
    for existing_user in users_db.values():
        if existing_user.email == user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    user_id = generate_id()
    now = datetime.now()
    
    user_data = UserResponse(
        id=user_id,
        name=user.name,
        email=user.email,
        age=user.age,
        created_at=now,
        updated_at=now
    )
    
    users_db[user_id] = user_data
    return user_data

@app.get("/users", response_model=List[UserResponse])
async def get_all_users(skip: int = 0, limit: int = 100):
    """Get all users with pagination"""
    all_users = list(users_db.values())
    return all_users[skip:skip + limit]

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    """Get a specific user by ID"""
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return users_db[user_id]

@app.get("/users/{user_id}/profile", response_model=UserResponse)
async def get_user_profile(user_id: int):
    """Get user profile (public information only)"""
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    user = users_db[user_id]
    # Return only public fields
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        age=user.age,
        created_at=user.created_at,
        updated_at=user.updated_at
    )

@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserUpdate):
    """Update an existing user"""
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    existing_user = users_db[user_id]
    now = datetime.now()
    
    # Update fields
    if user_update.name is not None:
        existing_user.name = user_update.name
    if user_update.email is not None:
        existing_user.email = user_update.email
    if user_update.age is not None:
        existing_user.age = user_update.age
    if user_update.password is not None:
        # In production, hash the password
        existing_user.password = user_update.password
    
    existing_user.updated_at = now
    return existing_user

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int):
    """Delete a user"""
    if user_id not in users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    del users_db[user_id]
    return None

# Health check endpoint
@app.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "users_count": len(users_db)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
