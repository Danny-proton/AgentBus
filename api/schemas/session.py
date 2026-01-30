"""
AgentBus Session Schemas
AgentBus会话相关数据模型
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """会话状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    ERROR = "error"


class SessionCreate(BaseModel):
    """创建会话请求模型"""
    workspace: Optional[str] = Field(None, description="工作空间路径")
    agent_id: Optional[str] = Field(None, description="Agent ID，为空则使用默认")
    model: Optional[str] = Field(None, description="默认模型")
    config: Dict[str, Any] = Field(default_factory=dict, description="额外配置")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="会话元数据")


class SessionResponse(BaseModel):
    """会话响应模型"""
    id: str = Field(..., description="会话唯一ID")
    status: SessionStatus = Field(..., description="会话状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")
    agent_id: str = Field(..., description="关联的Agent ID")
    workspace: Optional[str] = Field(None, description="工作空间路径")
    message_count: int = Field(default=0, description="消息数量")
    token_usage: int = Field(default=0, description="Token使用量")
    cost: float = Field(default=0.0, description="总成本")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class SessionUpdate(BaseModel):
    """更新会话请求模型"""
    status: Optional[SessionStatus] = Field(None, description="更新状态")
    metadata: Optional[Dict[str, Any]] = Field(None, description="更新元数据")
    config: Optional[Dict[str, Any]] = Field(None, description="更新配置")


class SessionList(BaseModel):
    """会话列表响应模型"""
    sessions: List[SessionResponse] = Field(..., description="会话列表")
    total: int = Field(..., description="总数")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=20, description="每页大小")


class SessionStats(BaseModel):
    """会话统计信息模型"""
    session_id: str = Field(..., description="会话ID")
    total_messages: int = Field(..., description="总消息数")
    total_tokens: int = Field(..., description="总Token数")
    total_cost: float = Field(..., description="总成本")
    avg_response_time: float = Field(..., description="平均响应时间")
    active_time: float = Field(..., description="活跃时间（小时）")
    last_activity: datetime = Field(..., description="最后活动时间")


class SessionConfig(BaseModel):
    """会话配置模型"""
    max_tokens: int = Field(default=4096, description="最大Token数")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    tools_enabled: bool = Field(default=True, description="是否启用工具")
    workspace_enabled: bool = Field(default=True, description="是否启用工作空间")
    logging_enabled: bool = Field(default=True, description="是否启用日志")
