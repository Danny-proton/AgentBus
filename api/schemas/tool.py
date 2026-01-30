"""
AgentBus Tool Schemas
AgentBus工具相关数据模型
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field


class ToolStatus(str, Enum):
    """工具状态枚举"""
    AVAILABLE = "available"
    BUSY = "busy"
    ERROR = "error"
    DISABLED = "disabled"


class ToolType(str, Enum):
    """工具类型枚举"""
    BUILTIN = "builtin"
    CUSTOM = "custom"
    EXTERNAL = "external"
    SYSTEM = "system"


class ToolCallRequest(BaseModel):
    """工具调用请求模型"""
    tool_name: str = Field(..., description="工具名称")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="工具参数")
    agent_id: Optional[str] = Field(None, description="调用Agent ID")
    session_id: Optional[str] = Field(None, description="会话ID")
    timeout: int = Field(default=30, description="超时时间（秒）")
    priority: int = Field(default=5, ge=1, le=10, description="优先级（1-10）")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文信息")


class ToolCallResponse(BaseModel):
    """工具调用响应模型"""
    call_id: str = Field(..., description="调用唯一ID")
    tool_name: str = Field(..., description="工具名称")
    agent_id: str = Field(..., description="Agent ID")
    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="执行状态")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    execution_time: float = Field(..., description="执行时间（秒）")
    result: Optional[Dict[str, Any]] = Field(None, description="执行结果")
    error: Optional[str] = Field(None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class ToolResult(BaseModel):
    """工具执行结果模型"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Union[str, Dict[str, Any]]] = Field(None, description="返回数据")
    message: Optional[str] = Field(None, description="结果消息")
    execution_time: float = Field(..., description="执行时间（秒）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class ToolDefinition(BaseModel):
    """工具定义模型"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    tool_type: ToolType = Field(..., description="工具类型")
    parameters_schema: Dict[str, Any] = Field(default_factory=dict, description="参数模式")
    required_params: List[str] = Field(default_factory=list, description="必需参数")
    optional_params: List[str] = Field(default_factory=list, description="可选参数")
    examples: List[Dict[str, Any]] = Field(default_factory=list, description="使用示例")
    version: str = Field(default="1.0.0", description="版本号")
    tags: List[str] = Field(default_factory=list, description="标签")


class ToolRegistryResponse(BaseModel):
    """工具注册响应模型"""
    tools: List[ToolDefinition] = Field(..., description="工具列表")
    total: int = Field(..., description="总数")
    categories: Dict[str, int] = Field(default_factory=dict, description="分类统计")


class ToolExecutionLog(BaseModel):
    """工具执行日志模型"""
    call_id: str = Field(..., description="调用ID")
    tool_name: str = Field(..., description="工具名称")
    agent_id: str = Field(..., description="Agent ID")
    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="执行状态")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="调用参数")
    result_summary: str = Field(..., description="结果摘要")
    timestamp: datetime = Field(..., description="执行时间")
    execution_time: float = Field(..., description="执行时间（秒）")


class ToolStatistics(BaseModel):
    """工具统计信息模型"""
    tool_name: str = Field(..., description="工具名称")
    total_calls: int = Field(..., description="总调用次数")
    success_rate: float = Field(..., description="成功率")
    avg_execution_time: float = Field(..., description="平均执行时间")
    total_execution_time: float = Field(..., description="总执行时间")
    last_used: datetime = Field(..., description="最后使用时间")
    error_count: int = Field(default=0, description="错误次数")


class ToolCapability(BaseModel):
    """工具能力描述模型"""
    name: str = Field(..., description="能力名称")
    description: str = Field(..., description="能力描述")
    input_types: List[str] = Field(default_factory=list, description="支持输入类型")
    output_types: List[str] = Field(default_factory=list, description="支持输出类型")
    limitations: List[str] = Field(default_factory=list, description="使用限制")


class ToolHealth(BaseModel):
    """工具健康状态模型"""
    tool_name: str = Field(..., description="工具名称")
    status: ToolStatus = Field(..., description="工具状态")
    uptime: float = Field(..., description="运行时间（秒）")
    response_time: float = Field(..., description="平均响应时间（毫秒）")
    error_rate: float = Field(..., description="错误率（%）")
    last_check: datetime = Field(..., description="最后检查时间")
    dependencies: List[str] = Field(default_factory=list, description="依赖项")
