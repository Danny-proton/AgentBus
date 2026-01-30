"""
AgentBus Agent Schemas
AgentBus Agent相关数据模型
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BUSY = "busy"
    ERROR = "error"


class AgentType(str, Enum):
    """Agent类型枚举"""
    MAIN = "main"
    SUB = "sub"
    TOOL = "tool"
    SYSTEM = "system"


class AgentCreate(BaseModel):
    """创建Agent请求模型"""
    name: str = Field(..., description="Agent名称")
    agent_type: AgentType = Field(default=AgentType.SUB, description="Agent类型")
    model: Optional[str] = Field(None, description="使用的模型")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent配置")
    tools: List[str] = Field(default_factory=list, description="启用的工具列表")
    dependencies: List[str] = Field(default_factory=list, description="依赖的Agent ID列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class AgentResponse(BaseModel):
    """Agent响应模型"""
    id: str = Field(..., description="Agent唯一ID")
    name: str = Field(..., description="Agent名称")
    agent_type: AgentType = Field(..., description="Agent类型")
    status: AgentStatus = Field(..., description="Agent状态")
    model: Optional[str] = Field(None, description="使用的模型")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")
    tools: List[str] = Field(default_factory=list, description="工具列表")
    dependencies: List[str] = Field(default_factory=list, description="依赖列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class AgentUpdate(BaseModel):
    """更新Agent请求模型"""
    name: Optional[str] = Field(None, description="Agent名称")
    status: Optional[AgentStatus] = Field(None, description="Agent状态")
    config: Optional[Dict[str, Any]] = Field(None, description="Agent配置")
    tools: Optional[List[str]] = Field(None, description="工具列表")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class AgentStats(BaseModel):
    """Agent统计信息模型"""
    agent_id: str = Field(..., description="Agent ID")
    total_sessions: int = Field(..., description="总会话数")
    total_messages: int = Field(..., description="总消息数")
    total_tokens: int = Field(..., description="总Token数")
    total_cost: float = Field(..., description="总成本")
    avg_response_time: float = Field(..., description="平均响应时间")
    success_rate: float = Field(..., description="成功率")
    last_activity: datetime = Field(..., description="最后活动时间")


class AgentCapability(BaseModel):
    """Agent能力描述模型"""
    name: str = Field(..., description="能力名称")
    description: str = Field(..., description="能力描述")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="参数描述")
    examples: List[str] = Field(default_factory=list, description="使用示例")


class AgentTool(BaseModel):
    """Agent工具描述模型"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    parameters_schema: Dict[str, Any] = Field(default_factory=dict, description="参数模式")
    required: List[str] = Field(default_factory=list, description="必需参数")
    examples: List[Dict[str, Any]] = Field(default_factory=list, description="使用示例")


class AgentHealth(BaseModel):
    """Agent健康状态模型"""
    agent_id: str = Field(..., description="Agent ID")
    status: str = Field(..., description="健康状态")
    uptime: float = Field(..., description="运行时间（秒）")
    memory_usage: float = Field(..., description="内存使用量（MB）")
    cpu_usage: float = Field(..., description="CPU使用率（%）")
    last_heartbeat: datetime = Field(..., description="最后心跳时间")
    error_count: int = Field(default=0, description="错误计数")
