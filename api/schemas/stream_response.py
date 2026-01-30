"""
流式响应处理 API schemas
Stream Response Processing API schemas for AgentBus

本模块定义流式响应处理相关的API数据模型，
包括流请求、数据块、状态等数据结构。
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# 枚举类型定义
class StreamEventType(str, Enum):
    """流事件类型"""
    START = "start"
    TOKEN = "token"
    PROGRESS = "progress"
    COMPLETE = "complete"
    ERROR = "error"
    CANCEL = "cancel"
    HEARTBEAT = "heartbeat"


class StreamStatus(str, Enum):
    """流状态"""
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class StreamHandlerType(str, Enum):
    """流处理器类型"""
    WEBSOCKET = "websocket"
    HTTP = "http"


# 数据模型
class StreamRequestBase(BaseModel):
    """流请求基础模型"""
    content: str = Field(..., description="请求内容")
    stream_type: str = Field(default="text", description="流类型")
    max_tokens: Optional[int] = Field(None, description="最大令牌数")
    temperature: float = Field(default=0.7, description="温度参数")
    chunk_size: int = Field(default=10, description="数据块大小")
    delay_ms: int = Field(default=50, description="延迟毫秒数")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class StreamRequestCreate(StreamRequestBase):
    """创建流请求"""
    stream_id: Optional[str] = Field(None, description="流ID(可选)")
    task_id: Optional[str] = Field(None, description="任务ID(可选)")
    handler_type: StreamHandlerType = Field(default=StreamHandlerType.WEBSOCKET, description="处理器类型")


class StreamRequestResponse(BaseModel):
    """流请求响应"""
    stream_id: str = Field(..., description="流ID")
    status: StreamStatus = Field(..., description="流状态")
    message: str = Field(..., description="响应消息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class StreamChunk(BaseModel):
    """流数据块"""
    stream_id: str = Field(..., description="流ID")
    event_type: StreamEventType = Field(..., description="事件类型")
    content: str = Field(default="", description="内容")
    token_count: int = Field(default=0, description="令牌数")
    progress: float = Field(default=0.0, description="进度(0-1)")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    error: Optional[str] = Field(None, description="错误信息")


class StreamStatusResponse(BaseModel):
    """流状态响应"""
    stream_id: str = Field(..., description="流ID")
    status: StreamStatus = Field(..., description="流状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    token_count: int = Field(default=0, description="已处理令牌数")
    progress: float = Field(default=0.0, description="进度")


class StreamStatistics(BaseModel):
    """流统计信息"""
    active_streams: int = Field(..., description="活跃流数量")
    total_streams: int = Field(..., description="总流数量")
    by_status: Dict[str, int] = Field(..., description="按状态统计")
    processing_tasks: int = Field(..., description="处理任务数量")
    avg_processing_time: float = Field(default=0.0, description="平均处理时间")
    total_tokens_processed: int = Field(default=0, description="总处理令牌数")


class StreamEventResponse(BaseModel):
    """流事件响应"""
    stream_id: str = Field(..., description="流ID")
    event: StreamEventType = Field(..., description="事件类型")
    data: Dict[str, Any] = Field(..., description="事件数据")


class HealthCheck(BaseModel):
    """健康检查"""
    status: str = Field(..., description="健康状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    active_streams: int = Field(..., description="活跃流数量")
    handlers: List[str] = Field(..., description="可用处理器")


# WebSocket消息模型
class WebSocketMessage(BaseModel):
    """WebSocket消息"""
    type: str = Field(..., description="消息类型")
    stream_id: Optional[str] = Field(None, description="流ID")
    data: Optional[Dict[str, Any]] = Field(None, description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class WebSocketStreamStart(BaseModel):
    """WebSocket流开始消息"""
    stream_id: str = Field(..., description="流ID")
    request: StreamRequestCreate = Field(..., description="流请求")


class WebSocketStreamChunk(BaseModel):
    """WebSocket流数据块消息"""
    stream_id: str = Field(..., description="流ID")
    chunk: StreamChunk = Field(..., description="数据块")


class WebSocketStreamControl(BaseModel):
    """WebSocket流控制消息"""
    action: str = Field(..., description="控制动作: cancel, pause, resume")
    stream_id: str = Field(..., description="流ID")


# 错误响应模型
class StreamErrorResponse(BaseModel):
    """流错误响应"""
    error: str = Field(..., description="错误信息")
    error_code: str = Field(..., description="错误代码")
    stream_id: Optional[str] = Field(None, description="流ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")


# 批量流请求模型
class BatchStreamRequest(BaseModel):
    """批量流请求"""
    streams: List[StreamRequestCreate] = Field(..., description="流请求列表")
    parallel: bool = Field(default=True, description="是否并行处理")


class BatchStreamResponse(BaseModel):
    """批量流响应"""
    batch_id: str = Field(..., description="批次ID")
    stream_count: int = Field(..., description="流数量")
    status: StreamStatus = Field(..., description="整体状态")
    stream_ids: List[str] = Field(..., description="流ID列表")


# 流配置模型
class StreamConfig(BaseModel):
    """流配置"""
    max_concurrent_streams: int = Field(default=100, description="最大并发流数")
    default_chunk_size: int = Field(default=10, description="默认数据块大小")
    default_delay_ms: int = Field(default=50, description="默认延迟毫秒")
    heartbeat_interval: int = Field(default=30, description="心跳间隔秒")
    stream_timeout: int = Field(default=300, description="流超时秒")


class StreamConfigUpdate(BaseModel):
    """流配置更新"""
    max_concurrent_streams: Optional[int] = None
    default_chunk_size: Optional[int] = None
    default_delay_ms: Optional[int] = None
    heartbeat_interval: Optional[int] = None
    stream_timeout: Optional[int] = None


# 分页响应模型
class PaginatedStreamsResponse(BaseModel):
    """分页流响应"""
    page: int = Field(..., description="页码")
    per_page: int = Field(..., description="每页数量")
    total: int = Field(..., description="总数量")
    pages: int = Field(..., description="总页数")
    streams: List[StreamStatusResponse] = Field(..., description="流列表")


# 流过滤器模型
class StreamFilter(BaseModel):
    """流过滤器"""
    status: Optional[StreamStatus] = Field(None, description="状态过滤")
    stream_type: Optional[str] = Field(None, description="流类型过滤")
    handler_type: Optional[StreamHandlerType] = Field(None, description="处理器类型过滤")
    created_after: Optional[datetime] = Field(None, description="创建时间过滤")
    created_before: Optional[datetime] = Field(None, description="创建时间过滤")


# 性能监控模型
class StreamPerformanceMetrics(BaseModel):
    """流性能指标"""
    stream_id: str = Field(..., description="流ID")
    start_time: datetime = Field(..., description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    total_tokens: int = Field(..., description="总令牌数")
    processing_time: float = Field(..., description="处理时间秒")
    tokens_per_second: float = Field(..., description="每秒令牌数")
    avg_chunk_delay: float = Field(default=0.0, description="平均数据块延迟")
    success: bool = Field(..., description="是否成功")


class StreamAnalytics(BaseModel):
    """流分析数据"""
    total_streams: int = Field(..., description="总流数")
    success_rate: float = Field(..., description="成功率")
    avg_processing_time: float = Field(..., description="平均处理时间")
    avg_tokens_per_second: float = Field(..., description="平均每秒令牌数")
    popular_stream_types: Dict[str, int] = Field(default_factory=dict, description="热门流类型")
    handler_performance: Dict[str, Dict[str, float]] = Field(default_factory=dict, description="处理器性能")