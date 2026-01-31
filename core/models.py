from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field

class User(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    roles: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    status: str
    created_at: datetime
    updated_at: datetime

class Session(BaseModel):
    id: str
    user_id: str
    agent_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    title: Optional[str] = None

class Memory(BaseModel):
    id: str
    user_id: str
    content: str
    type: str
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    relevance_score: Optional[float] = None
    related_knowledge: Set[str] = Field(default_factory=set)
