"""
Memory Management API Routes

This module provides REST API endpoints for memory management operations.
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid
from pydantic import BaseModel, Field
import asyncio

from ..core.dependencies import get_memory_service, get_user_service
from ..core.auth import verify_api_key, verify_user_permissions
from ..core.models import Memory

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Pydantic models for request/response
class MemoryCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    type: str = Field(..., description="Type of memory (note, task, idea, etc.)")
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MemoryUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    type: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class MemorySearch(BaseModel):
    query: str = Field(..., description="Search query")
    type: Optional[str] = Field(None, description="Filter by memory type")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    limit: int = Field(10, ge=1, le=100, description="Number of results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")
    sort: Optional[str] = Field("created_at", description="Field to sort by")
    order: Optional[str] = Field("desc", regex="^(asc|desc)$", description="Sort order")

class MemoryBatchCreate(BaseModel):
    memories: List[MemoryCreate] = Field(..., max_items=100, description="List of memories to create")

class MemoryResponse(BaseModel):
    id: str
    user_id: str
    content: str
    type: str
    tags: List[str]
    metadata: Dict[str, Any]
    relevance_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

class MemoryListResponse(BaseModel):
    memories: List[MemoryResponse]
    pagination: Dict[str, Any]

class MemorySearchResponse(BaseModel):
    results: List[MemoryResponse]
    total: int
    limit: int
    offset: int
    took_ms: int

class MemoryBatchResponse(BaseModel):
    created: List[MemoryResponse]
    failed: List[Dict[str, Any]]
    total: int
    created_count: int
    failed_count: int

class ApiResponse(BaseModel):
    success: bool
    data: Any = None
    error: Dict[str, str] = None
    timestamp: datetime

router = APIRouter(prefix="/memory", tags=["memory"])

def create_response(data: Any = None, error: Dict[str, str] = None, success: bool = True) -> ApiResponse:
    """Create standardized API response."""
    return ApiResponse(
        success=success,
        data=data,
        error=error,
        timestamp=datetime.utcnow()
    )

@router.post("/{user_id}", response_model=ApiResponse)
async def create_memory(
    user_id: str,
    memory_data: MemoryCreate,
    current_user: dict = Depends(verify_api_key),
    memory_service = Depends(get_memory_service),
    user_service = Depends(get_user_service)
):
    """
    Store a new memory entry.
    
    - **user_id**: Unique user identifier
    - **content**: Memory content (1-10000 characters)
    - **type**: Type of memory (note, task, idea, etc.)
    - **tags**: List of tags for categorization
    - **metadata**: Additional metadata dictionary
    """
    try:
        # Verify user exists
        user = await user_service.get_user(user_id)
        if not user:
            return create_response(
                error={
                    "code": "USER_NOT_FOUND",
                    "message": "User not found"
                },
                success=False
            )
        
        # Create memory
        memory = Memory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            content=memory_data.content,
            type=memory_data.type,
            tags=memory_data.tags,
            metadata=memory_data.metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        result = await memory_service.create_memory(memory)
        
        return create_response(data=result)
    
    except Exception as e:
        logger.error(f"Error creating memory for user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to create memory"
            },
            success=False
        )

@router.get("/{user_id}/{memory_id}", response_model=ApiResponse)
async def get_memory(
    user_id: str,
    memory_id: str,
    current_user: dict = Depends(verify_api_key),
    memory_service = Depends(get_memory_service)
):
    """
    Retrieve a specific memory entry.
    
    - **user_id**: Unique user identifier
    - **memory_id**: Unique memory identifier
    """
    try:
        memory = await memory_service.get_memory(memory_id, user_id)
        
        if not memory:
            return create_response(
                error={
                    "code": "MEMORY_NOT_FOUND",
                    "message": "Memory not found"
                },
                success=False
            )
        
        return create_response(data=memory)
    
    except Exception as e:
        logger.error(f"Error getting memory {memory_id} for user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to retrieve memory"
            },
            success=False
        )

@router.put("/{user_id}/{memory_id}", response_model=ApiResponse)
async def update_memory(
    user_id: str,
    memory_id: str,
    memory_data: MemoryUpdate,
    current_user: dict = Depends(verify_api_key),
    memory_service = Depends(get_memory_service)
):
    """
    Update a memory entry.
    
    - **user_id**: Unique user identifier
    - **memory_id**: Unique memory identifier
    """
    try:
        # Check if memory exists
        existing_memory = await memory_service.get_memory(memory_id, user_id)
        if not existing_memory:
            return create_response(
                error={
                    "code": "MEMORY_NOT_FOUND",
                    "message": "Memory not found"
                },
                success=False
            )
        
        # Update memory
        updated_data = {
            k: v for k, v in memory_data.dict(exclude_unset=True).items()
            if v is not None
        }
        updated_data["updated_at"] = datetime.utcnow()
        
        result = await memory_service.update_memory(memory_id, user_id, updated_data)
        
        return create_response(data=result)
    
    except Exception as e:
        logger.error(f"Error updating memory {memory_id} for user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to update memory"
            },
            success=False
        )

@router.delete("/{user_id}/{memory_id}", response_model=ApiResponse)
async def delete_memory(
    user_id: str,
    memory_id: str,
    current_user: dict = Depends(verify_api_key),
    memory_service = Depends(get_memory_service)
):
    """
    Delete a memory entry.
    
    - **user_id**: Unique user identifier
    - **memory_id**: Unique memory identifier
    """
    try:
        # Check if memory exists
        existing_memory = await memory_service.get_memory(memory_id, user_id)
        if not existing_memory:
            return create_response(
                error={
                    "code": "MEMORY_NOT_FOUND",
                    "message": "Memory not found"
                },
                success=False
            )
        
        # Delete memory
        await memory_service.delete_memory(memory_id, user_id)
        
        return create_response(data={"message": "Memory deleted successfully"})
    
    except Exception as e:
        logger.error(f"Error deleting memory {memory_id} for user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to delete memory"
            },
            success=False
        )

@router.get("/{user_id}", response_model=ApiResponse)
async def list_memories(
    user_id: str,
    type: Optional[str] = Query(None, description="Filter by memory type"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    sort: str = Query("created_at", description="Field to sort by"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    current_user: dict = Depends(verify_api_key),
    memory_service = Depends(get_memory_service)
):
    """
    List memory entries for a user.
    
    - **user_id**: Unique user identifier
    - **type**: Filter by memory type
    - **tags**: Filter by tags (comma-separated)
    - **limit**: Number of results (default: 10, max: 100)
    - **offset**: Number of results to skip (default: 0)
    - **sort**: Field to sort by (default: created_at)
    - **order**: Sort order (default: desc)
    """
    try:
        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        memories, total = await memory_service.list_memories(
            user_id=user_id,
            type_filter=type,
            tags=tag_list,
            limit=limit,
            offset=offset,
            sort=sort,
            order=order
        )
        
        pagination = {
            "limit": limit,
            "offset": offset,
            "total": total,
            "pages": (total + limit - 1) // limit,
            "has_next": offset + limit < total,
            "has_prev": offset > 0
        }
        
        result = {
            "memories": memories,
            "pagination": pagination
        }
        
        return create_response(data=result)
    
    except Exception as e:
        logger.error(f"Error listing memories for user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to list memories"
            },
            success=False
        )

@router.post("/{user_id}/search", response_model=ApiResponse)
async def search_memories(
    user_id: str,
    search_data: MemorySearch,
    current_user: dict = Depends(verify_api_key),
    memory_service = Depends(get_memory_service)
):
    """
    Search for memory entries using text search.
    
    - **user_id**: Unique user identifier
    - **query**: Search query string
    - **type**: Optional filter by memory type
    - **tags**: Optional filter by tags
    - **limit**: Number of results (default: 10, max: 100)
    - **offset**: Number of results to skip (default: 0)
    - **sort**: Field to sort by (default: created_at)
    - **order**: Sort order (default: desc)
    """
    try:
        start_time = datetime.utcnow()
        
        results = await memory_service.search_memories(
            user_id=user_id,
            query=search_data.query,
            type_filter=search_data.type,
            tags=search_data.tags,
            limit=search_data.limit,
            offset=search_data.offset,
            sort=search_data.sort,
            order=search_data.order
        )
        
        # Calculate search time
        end_time = datetime.utcnow()
        took_ms = int((end_time - start_time).total_seconds() * 1000)
        
        response_data = MemorySearchResponse(
            results=results,
            total=len(results),
            limit=search_data.limit,
            offset=search_data.offset,
            took_ms=took_ms
        )
        
        return create_response(data=response_data.dict())
    
    except Exception as e:
        logger.error(f"Error searching memories for user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to search memories"
            },
            success=False
        )

@router.post("/{user_id}/batch", response_model=ApiResponse)
async def batch_create_memories(
    user_id: str,
    batch_data: MemoryBatchCreate,
    current_user: dict = Depends(verify_api_key),
    memory_service = Depends(get_memory_service),
    user_service = Depends(get_user_service)
):
    """
    Create multiple memory entries at once.
    
    - **user_id**: Unique user identifier
    - **memories**: List of memories to create (max: 100)
    """
    try:
        # Verify user exists
        user = await user_service.get_user(user_id)
        if not user:
            return create_response(
                error={
                    "code": "USER_NOT_FOUND",
                    "message": "User not found"
                },
                success=False
            )
        
        created_memories = []
        failed_memories = []
        
        # Create memories in batch
        for i, memory_data in enumerate(batch_data.memories):
            try:
                memory = Memory(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    content=memory_data.content,
                    type=memory_data.type,
                    tags=memory_data.tags,
                    metadata=memory_data.metadata,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                result = await memory_service.create_memory(memory)
                created_memories.append(result)
            
            except Exception as e:
                logger.error(f"Error creating memory {i} for user {user_id}: {str(e)}")
                failed_memories.append({
                    "index": i,
                    "error": str(e),
                    "data": memory_data.dict()
                })
        
        response_data = MemoryBatchResponse(
            created=created_memories,
            failed=failed_memories,
            total=len(batch_data.memories),
            created_count=len(created_memories),
            failed_count=len(failed_memories)
        )
        
        return create_response(data=response_data.dict())
    
    except Exception as e:
        logger.error(f"Error batch creating memories for user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to batch create memories"
            },
            success=False
        )

@router.delete("/{user_id}", response_model=ApiResponse)
async def delete_user_memories(
    user_id: str,
    type: Optional[str] = Query(None, description="Optional type filter"),
    tags: Optional[str] = Query(None, description="Optional tags filter (comma-separated)"),
    current_user: dict = Depends(verify_api_key),
    memory_service = Depends(get_memory_service)
):
    """
    Delete multiple memories for a user.
    
    - **user_id**: Unique user identifier
    - **type**: Optional type filter for memories to delete
    - **tags**: Optional tags filter (comma-separated)
    """
    try:
        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Get memories to delete
        memories, _ = await memory_service.list_memories(
            user_id=user_id,
            type_filter=type,
            tags=tag_list,
            limit=10000,  # Get all matching memories
            offset=0,
            sort="created_at",
            order="asc"
        )
        
        if not memories:
            return create_response(data={"message": "No memories found to delete"})
        
        # Delete memories
        deleted_count = 0
        for memory in memories:
            try:
                await memory_service.delete_memory(memory["id"], user_id)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Error deleting memory {memory['id']}: {str(e)}")
        
        return create_response(
            data={
                "message": f"Deleted {deleted_count} memories",
                "deleted_count": deleted_count,
                "total_found": len(memories)
            }
        )
    
    except Exception as e:
        logger.error(f"Error deleting memories for user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to delete memories"
            },
            success=False
        )

@router.get("/{user_id}/stats", response_model=ApiResponse)
async def get_memory_stats(
    user_id: str,
    current_user: dict = Depends(verify_api_key),
    memory_service = Depends(get_memory_service)
):
    """
    Get memory statistics for a user.
    
    - **user_id**: Unique user identifier
    """
    try:
        stats = await memory_service.get_user_memory_stats(user_id)
        
        return create_response(data=stats)
    
    except Exception as e:
        logger.error(f"Error getting memory stats for user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to retrieve memory statistics"
            },
            success=False
        )

@router.get("/{user_id}/recent", response_model=ApiResponse)
async def get_recent_memories(
    user_id: str,
    limit: int = Query(10, ge=1, le=50, description="Number of recent memories to return"),
    current_user: dict = Depends(verify_api_key),
    memory_service = Depends(get_memory_service)
):
    """
    Get recently created memories for a user.
    
    - **user_id**: Unique user identifier
    - **limit**: Number of memories to return (default: 10, max: 50)
    """
    try:
        memories = await memory_service.get_recent_memories(user_id, limit)
        
        return create_response(data=memories)
    
    except Exception as e:
        logger.error(f"Error getting recent memories for user {user_id}: {str(e)}")
        return create_response(
            error={
                "code": "INTERNAL_ERROR",
                "message": "Failed to retrieve recent memories"
            },
            success=False
        )