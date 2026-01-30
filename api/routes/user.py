"""
User Management API Routes

This module provides REST API endpoints for user management operations.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid
from pydantic import BaseModel, EmailStr, Field
import asyncio

from ..core.dependencies import get_user_service, get_session_service, get_memory_service
from ..core.auth import verify_api_key, verify_user_permissions
from ..core.models import User, Session, Memory

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Pydantic models for request/response
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., max_length=100)
    roles: List[str] = Field(default_factory=lambda: ["user"])
    preferences: Dict[str, Any] = Field(default_factory=dict)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    roles: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    roles: List[str]
    preferences: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime

class UserListResponse(BaseModel):
    users: List[UserResponse]
    pagination: Dict[str, Any]

class UserStats(BaseModel):
    user_id: str
    session_count: int
    memory_count: int
    memory_by_type: Dict[str, int]
    recent_activity: List[Dict[str, Any]]
    period_stats: Dict[str, Dict[str, int]]

class ApiResponse(BaseModel):
    success: bool
    data: Any = None
    error: Dict[str, str] = None
    timestamp: datetime

router = APIRouter(prefix="/users", tags=["users"])

def create_response(data: Any = None, error: Dict[str, str] = None, success: bool = True) -> ApiResponse:
    """Create standardized API response."""
    return ApiResponse(
        success=success,
        data=data,
        error=error,
        timestamp=datetime.utcnow()
    )

@router.post("/", response_model=ApiResponse)
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(verify_api_key),
    user_service = Depends(get_user_service)
):
    """
    Create a new user account.
    
    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **full_name**: User's full name
    - **roles**: List of user roles (default: ["user"])
    - **preferences**: User preferences dictionary
    """
    try:
        # Check if user already exists
        existing_user = await user_service.get_user_by_username(user_data.username)
        if existing_user:
            return create_response(
                error={
                    "code": "USER_EXISTS",
                    "message": "Username already exists"
                },
                success=False
            )
        
        existing_email = await user_service.get_user_by_email(user_data.email)
        if existing_email:
            return create_response(
                error={
                    "code": "USER_EXISTS",
                    "message": "Email already exists"
                },
                success=False
            )
        
        # Create user
        new_user = User(
            id=str(uuid.uuid4()),
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            roles=user_data.roles,
            preferences=user_data.preferences,
            status="active",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        result = await user_service.create_user(new_user)
        
        return create_response(data=result)
    
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to create user"
            },
            success=False
        )

@router.get("/{user_id}", response_model=ApiResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(verify_api_key),
    user_service = Depends(get_user_service)
):
    """
    Get user profile information.
    
    - **user_id**: Unique user identifier
    """
    try:
        user = await user_service.get_user(user_id)
        
        if not user:
            return create_response(
                error={
                    "code": "USER_NOT_FOUND",
                    "message": "User not found"
                },
                success=False
            )
        
        return create_response(data=user)
    
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to retrieve user"
            },
            success=False
        )

@router.put("/{user_id}", response_model=ApiResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(verify_api_key),
    user_service = Depends(get_user_service)
):
    """
    Update user profile information.
    
    - **user_id**: Unique user identifier
    """
    try:
        # Check if user exists
        existing_user = await user_service.get_user(user_id)
        if not existing_user:
            return create_response(
                error={
                    "code": "USER_NOT_FOUND",
                    "message": "User not found"
                },
                success=False
            )
        
        # Check email uniqueness if email is being updated
        if user_data.email and user_data.email != existing_user.email:
            email_check = await user_service.get_user_by_email(user_data.email)
            if email_check:
                return create_response(
                    error={
                        "code": "USER_EXISTS",
                        "message": "Email already exists"
                    },
                    success=False
                )
        
        # Update user
        updated_data = {
            k: v for k, v in user_data.dict(exclude_unset=True).items()
            if v is not None
        }
        updated_data["updated_at"] = datetime.utcnow()
        
        result = await user_service.update_user(user_id, updated_data)
        
        return create_response(data=result)
    
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to update user"
            },
            success=False
        )

@router.get("/", response_model=ApiResponse)
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search term for username or email"),
    current_user: dict = Depends(verify_api_key),
    user_service = Depends(get_user_service)
):
    """
    List users with pagination.
    
    - **page**: Page number (default: 1)
    - **size**: Page size (default: 20, max: 100)
    - **search**: Search term for filtering
    """
    try:
        offset = (page - 1) * size
        users, total = await user_service.list_users(
            limit=size,
            offset=offset,
            search=search
        )
        
        pagination = {
            "page": page,
            "size": size,
            "total": total,
            "pages": (total + size - 1) // size,
            "has_next": page * size < total,
            "has_prev": page > 1
        }
        
        result = {
            "users": users,
            "pagination": pagination
        }
        
        return create_response(data=result)
    
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to list users"
            },
            success=False
        )

@router.delete("/{user_id}", response_model=ApiResponse)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(verify_api_key),
    user_service = Depends(get_user_service),
    session_service = Depends(get_session_service),
    memory_service = Depends(get_memory_service)
):
    """
    Delete a user account and all associated data.
    
    - **user_id**: Unique user identifier
    """
    try:
        # Check if user exists
        user = await user_service.get_user(user_id)
        if not user:
            return create_response(
                error={
                    "code": "USER_NOT_FOUND",
                    "message": "User not found"
                },
                success=False
            )
        
        # Delete user and associated data
        await asyncio.gather(
            user_service.delete_user(user_id),
            session_service.delete_user_sessions(user_id),
            memory_service.delete_user_memories(user_id)
        )
        
        return create_response(data={"message": "User deleted successfully"})
    
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to delete user"
            },
            success=False
        )

@router.get("/{user_id}/stats", response_model=ApiResponse)
async def get_user_stats(
    user_id: str,
    current_user: dict = Depends(verify_api_key),
    user_service = Depends(get_user_service),
    session_service = Depends(get_session_service),
    memory_service = Depends(get_memory_service)
):
    """
    Get usage statistics for a user.
    
    - **user_id**: Unique user identifier
    """
    try:
        # Check if user exists
        user = await user_service.get_user(user_id)
        if not user:
            return create_response(
                error={
                    "code": "USER_NOT_FOUND",
                    "message": "User not found"
                },
                success=False
            )
        
        # Get statistics
        session_count = await session_service.count_user_sessions(user_id)
        memory_count = await memory_service.count_user_memories(user_id)
        memory_by_type = await memory_service.get_memory_stats_by_type(user_id)
        
        # Get recent activity
        recent_sessions = await session_service.get_recent_sessions(user_id, limit=5)
        recent_memories = await memory_service.get_recent_memories(user_id, limit=5)
        
        recent_activity = []
        for session in recent_sessions:
            recent_activity.append({
                "type": "session_created",
                "description": f"Created session '{session.get('title', 'Untitled')}'",
                "timestamp": session.get("created_at")
            })
        
        for memory in recent_memories:
            recent_activity.append({
                "type": "memory_created",
                "description": f"Created {memory.get('type', 'memory')} '{memory.get('content', '')[:50]}...'",
                "timestamp": memory.get("created_at")
            })
        
        # Sort recent activity by timestamp
        recent_activity.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        recent_activity = recent_activity[:10]
        
        # Calculate period statistics
        last_7_days = datetime.utcnow().timestamp() - (7 * 24 * 60 * 60)
        last_30_days = datetime.utcnow().timestamp() - (30 * 24 * 60 * 60)
        
        sessions_7d = await session_service.count_sessions_since(user_id, last_7_days)
        memories_7d = await memory_service.count_memories_since(user_id, last_7_days)
        sessions_30d = await session_service.count_sessions_since(user_id, last_30_days)
        memories_30d = await memory_service.count_memories_since(user_id, last_30_days)
        
        period_stats = {
            "last_7_days": {
                "sessions": sessions_7d,
                "memories": memories_7d
            },
            "last_30_days": {
                "sessions": sessions_30d,
                "memories": memories_30d
            }
        }
        
        stats = UserStats(
            user_id=user_id,
            session_count=session_count,
            memory_count=memory_count,
            memory_by_type=memory_by_type,
            recent_activity=recent_activity,
            period_stats=period_stats
        )
        
        return create_response(data=stats.dict())
    
    except Exception as e:
        logger.error(f"Error getting stats for user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to retrieve user statistics"
            },
            success=False
        )

@router.post("/{user_id}/reset", response_model=ApiResponse)
async def reset_user(
    user_id: str,
    current_user: dict = Depends(verify_api_key),
    user_service = Depends(get_user_service),
    session_service = Depends(get_session_service),
    memory_service = Depends(get_memory_service)
):
    """
    Reset user data (sessions and memories) while keeping user account.
    
    - **user_id**: Unique user identifier
    """
    try:
        # Check if user exists
        user = await user_service.get_user(user_id)
        if not user:
            return create_response(
                error={
                    "code": "USER_NOT_FOUND",
                    "message": "User not found"
                },
                success=False
            )
        
        # Reset user data
        await asyncio.gather(
            session_service.delete_user_sessions(user_id),
            memory_service.delete_user_memories(user_id)
        )
        
        return create_response(data={"message": "User data reset successfully"})
    
    except Exception as e:
        logger.error(f"Error resetting user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to reset user data"
            },
            success=False
        )