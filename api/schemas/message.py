"""
AgentBus Message Schemas
AgentBus消息相关数据模型
"""

from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    """消息请求模型"""
    content: str = Field(..., description="消息内容")
    session_id: Optional[str] = Field(None, description="会话ID，为空则创建新会话")
    agent_id: Optional[str] = Field(None, description="Agent ID，为空则使用默认Agent")
    model: Optional[str] = Field(None, description="使用的模型，如gpt-4")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外上下文信息")
    priority: int = Field(default=5, ge=1, le=10, description="优先级（1-10）")


class MessageResponse(BaseModel):
    """消息响应模型"""
    id: str = Field(..., description="消息唯一ID")
    session_id: str = Field(..., description="会话ID")
    agent_id: str = Field(..., description="Agent ID")
    content: str = Field(..., description="响应内容")
    timestamp: datetime = Field(..., description="创建时间")
    execution_time: float = Field(..., description="执行时间（秒）")
    tokens_used: Optional[int] = Field(None, description="使用的token数量")
    cost: Optional[float] = Field(None, description="成本（美元）")
    status: str = Field(..., description="执行状态")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class HumanRequest(BaseModel):
    """人在回路请求模型"""
    request_id: str = Field(..., description="请求唯一ID")
    agent_id: str = Field(..., description="发起请求的Agent ID")
    message: str = Field(..., description="请求内容")
    urgency: str = Field(default="normal", description="紧急程度：low, normal, high, critical")
    options: List[str] = Field(default_factory=list, description="预设选项")
    timeout: int = Field(default=300, description="超时时间（秒）")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")
    hitl_status: str = Field(default="awaiting_confirmation", description="HITL状态")
    contact_source: str = Field(default="communication_map", description="联系人来源")
    target_user: Optional[str] = Field(None, description="目标用户")


class HumanResponse(BaseModel):
    """人在回路响应模型"""
    request_id: str = Field(..., description="关联的请求ID")
    response: str = Field(..., description="用户响应内容")
    selected_option: Optional[str] = Field(None, description="选择的选项")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    user_id: str = Field(..., description="响应用户ID")


class StreamingChunk(BaseModel):
    """流式响应块模型"""
    type: str = Field(..., description="响应类型：chunk, done, error")
    data: str = Field(..., description="数据内容")
    session_id: Optional[str] = Field(None, description="会话ID")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
