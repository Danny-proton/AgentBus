"""
HITL 数据模型
HITL Data Models
"""

from typing import List, Optional, Dict, Any, Set
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class HITLPriority(str, Enum):
    """HITL优先级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class HITLStatus(str, Enum):
    """HITL状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ContactAvailability(str, Enum):
    """联系人可用性枚举"""
    ALWAYS = "always"
    WORK_HOURS = "work_hours"
    ON_CALL = "on_call"
    WEEKENDS = "weekends"


class HITLRequestCreate(BaseModel):
    """创建HITL请求的数据模型"""
    agent_id: str = Field(..., description="智能体ID")
    title: str = Field(..., description="请求标题", max_length=200)
    description: str = Field(..., description="请求描述", max_length=2000)
    context: Optional[Dict[str, Any]] = Field(default=None, description="上下文信息")
    priority: HITLPriority = Field(default=HITLPriority.MEDIUM, description="优先级")
    timeout_minutes: int = Field(default=30, ge=1, le=1440, description="超时时间（分钟）")
    assigned_to: Optional[str] = Field(default=None, description="分配的联系人ID")
    tags: Optional[List[str]] = Field(default=None, description="标签")


class HITLRequestResponse(BaseModel):
    """HITL请求响应数据模型"""
    id: str
    agent_id: str
    title: str
    description: str
    context: Dict[str, Any]
    priority: str
    status: str
    created_at: datetime
    timeout_minutes: int
    assigned_to: Optional[str]
    response: Optional[str]
    completed_at: Optional[datetime]
    tags: List[str]
    
    class Config:
        from_attributes = True


class HITLResponseCreate(BaseModel):
    """创建HITL响应的数据模型"""
    responder_id: str = Field(..., description="响应者ID")
    content: str = Field(..., description="响应内容", max_length=5000)
    is_final: bool = Field(default=True, description="是否为最终响应")
    attachments: Optional[List[Dict[str, Any]]] = Field(default=None, description="附件")


class HITLResponseResponse(BaseModel):
    """HITL响应响应数据模型"""
    request_id: str
    responder_id: str
    content: str
    created_at: datetime
    is_final: bool
    attachments: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class HITLStatistics(BaseModel):
    """HITL统计信息数据模型"""
    active_requests: int
    total_requests: int
    completed_requests: int
    timeout_requests: int
    completion_rate: float


class ContactCreate(BaseModel):
    """创建联系人的数据模型"""
    id: str = Field(..., description="联系人ID", max_length=100)
    name: str = Field(..., description="联系人姓名", max_length=100)
    role: str = Field(..., description="角色", max_length=100)
    expertise: Optional[List[str]] = Field(default=None, description="专业技能")
    availability: ContactAvailability = Field(default=ContactAvailability.WORK_HOURS, description="可用性")
    contact_methods: List[Dict[str, Any]] = Field(..., description="联系方式")
    timezone: str = Field(default="Asia/Shanghai", description="时区")
    language: str = Field(default="zh-CN", description="语言")
    priority_score: float = Field(default=1.0, ge=0.0, le=1.0, description="优先级评分")
    active: bool = Field(default=True, description="是否活跃")
    tags: Optional[List[str]] = Field(default=None, description="标签")
    response_time_estimate: int = Field(default=30, ge=1, le=1440, description="预估响应时间（分钟）")


class ContactResponse(BaseModel):
    """联系人响应数据模型"""
    id: str
    name: str
    role: str
    expertise: List[str]
    availability: str
    contact_methods: List[Dict[str, Any]]
    timezone: str
    language: str
    priority_score: float
    active: bool
    tags: List[str]
    last_active: Optional[datetime]
    response_time_estimate: int
    
    class Config:
        from_attributes = True


class ContactMatchRequest(BaseModel):
    """联系人匹配请求数据模型"""
    context: Dict[str, Any] = Field(..., description="匹配上下文")
    priority: str = Field(default="medium", description="优先级")
    max_results: int = Field(default=5, ge=1, le=20, description="最大匹配数量")


class ContactMatchResponse(BaseModel):
    """联系人匹配响应数据模型"""
    matches: List[ContactResponse]
    total_found: int


class ContactUpdate(BaseModel):
    """更新联系人的数据模型"""
    name: Optional[str] = Field(default=None, max_length=100)
    role: Optional[str] = Field(default=None, max_length=100)
    expertise: Optional[List[str]] = Field(default=None)
    availability: Optional[ContactAvailability] = Field(default=None)
    contact_methods: Optional[List[Dict[str, Any]]] = Field(default=None)
    timezone: Optional[str] = Field(default=None)
    language: Optional[str] = Field(default=None)
    priority_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    active: Optional[bool] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)
    response_time_estimate: Optional[int] = Field(default=None, ge=1, le=1440)


class MessageChannelRequest(BaseModel):
    """消息通道请求数据模型"""
    sender_id: str = Field(..., description="发送者ID")
    sender_type: str = Field(..., description="发送者类型")
    content: str = Field(..., description="消息内容")
    recipients: List[str] = Field(..., description="接收者列表")
    message_type: str = Field(default="text", description="消息类型")
    priority: str = Field(default="normal", description="消息优先级")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")
    attachments: Optional[List[Dict[str, Any]]] = Field(default=None, description="附件")
    is_hitl: bool = Field(default=False, description="是否为HITL消息")
    hitl_data: Optional[Dict[str, Any]] = Field(default=None, description="HITL数据")


class MessageChannelResponse(BaseModel):
    """消息通道响应数据模型"""
    message_id: str
    status: str
    timestamp: datetime
