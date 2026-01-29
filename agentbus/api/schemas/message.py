"""
API Schemas - Pydantic 数据模型定义
"""

from datetime import datetime
from typing import Optional, List, Any, Dict, Union
from enum import Enum
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """消息类型"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    INTERRUPT = "interrupt"


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class MessageBase(BaseModel):
    """消息基础模型"""
    content: str
    role: MessageRole
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class UserMessage(MessageBase):
    """用户消息"""
    role: MessageRole = MessageRole.USER
    attachments: Optional[List[str]] = None


class AssistantMessage(MessageBase):
    """助手消息"""
    role: MessageRole = MessageRole.ASSISTANT
    model: Optional[str] = None
    tokens: Optional[int] = None
    cost: Optional[float] = None


class ToolCall(BaseModel):
    """工具调用"""
    id: str
    name: str
    arguments: Dict[str, Any]
    timestamp: Optional[datetime] = None


class ToolResult(BaseModel):
    """工具结果"""
    call_id: str
    success: bool
    content: str
    error: Optional[str] = None


class Message(MessageBase):
    """完整消息模型"""
    id: str
    type: MessageType = MessageType.ASSISTANT
    tool_calls: Optional[List[ToolCall]] = None
    tool_results: Optional[List[ToolResult]] = None


class SessionStatus(str, Enum):
    """会话状态"""
    ACTIVE = "active"
    IDLE = "idle"
    THINKING = "thinking"
    ERROR = "error"


class SessionCreate(BaseModel):
    """创建会话请求"""
    workspace: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None


class SessionResponse(BaseModel):
    """会话响应"""
    id: str
    status: SessionStatus
    workspace: Optional[str]
    current_model: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class SessionDetail(SessionResponse):
    """会话详细信息"""
    messages: List[Message]
    system_prompt: Optional[str]


class AgentRequest(BaseModel):
    """Agent 请求"""
    session_id: str
    message: str
    model: Optional[str] = None
    stream: bool = True
    attachments: Optional[List[str]] = None


class AgentResponse(BaseModel):
    """Agent 响应"""
    session_id: str
    message: Message
    stream_url: Optional[str] = None


class TokenUsage(BaseModel):
    """Token 使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class CostInfo(BaseModel):
    """成本信息"""
    model: str
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    token_usage: TokenUsage


class CostSummary(BaseModel):
    """成本汇总"""
    total_cost: float = 0.0
    by_model: Dict[str, CostInfo]
    session_id: Optional[str] = None


class ModelConfig(BaseModel):
    """模型配置"""
    name: str
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str
    context_window: int = 128000
    max_output_tokens: int = 4096


class ModelPointerConfig(BaseModel):
    """模型指针配置"""
    main: str = "default"
    task: str = "default"
    reasoning: str = "default"
    quick: str = "default"


class ConfigUpdate(BaseModel):
    """配置更新请求"""
    model_profiles: Optional[Dict[str, ModelConfig]] = None
    model_pointers: Optional[ModelPointerConfig] = None
    safe_mode: Optional[bool] = None


class FileOperation(BaseModel):
    """文件操作请求"""
    path: str
    operation: str  # read, write, edit, glob
    content: Optional[str] = None
    pattern: Optional[str] = None


class CommandExecution(BaseModel):
    """命令执行请求"""
    command: str
    timeout: Optional[int] = 60
    working_dir: Optional[str] = None


class EnvironmentInfo(BaseModel):
    """环境信息"""
    type: str  # local, remote
    host: Optional[str] = None
    workspace: str
    os: Optional[str] = None
    python_version: Optional[str] = None


class WebSocketMessage(BaseModel):
    """WebSocket 消息格式"""
    type: str  # user_message, interrupt, heartbeat
    content: Any
    timestamp: datetime = Field(default_factory=datetime.now)


class StreamChunk(BaseModel):
    """流式响应块"""
    chunk: str
    done: bool = False
    session_id: str
