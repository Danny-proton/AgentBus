"""
AgentBus Agent System Base Types
Agent系统基础类型定义
"""

from typing import Dict, List, Optional, Any, Set, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from abc import ABC, abstractmethod
import uuid
import asyncio
import json


class AgentType(Enum):
    """Agent类型枚举"""
    # 基础类型
    TEXT_GENERATION = "text_generation"      # 文本生成
    CODE_GENERATION = "code_generation"      # 代码生成
    IMAGE_GENERATION = "image_generation"    # 图像生成
    IMAGE_UNDERSTANDING = "image_understanding"  # 图像理解
    AUDIO_PROCESSING = "audio_processing"    # 音频处理
    VIDEO_PROCESSING = "video_processing"    # 视频处理
    REASONING = "reasoning"                  # 推理
    CONVERSATION = "conversation"            # 对话
    TASK_EXECUTION = "task_execution"        # 任务执行
    
    # 扩展类型
    DATA_ANALYSIS = "data_analysis"           # 数据分析
    WEB_SCRAPING = "web_scraping"           # 网页爬取
    FILE_PROCESSING = "file_processing"      # 文件处理
    DATABASE_QUERY = "database_query"        # 数据库查询
    API_INTEGRATION = "api_integration"      # API集成
    WORKFLOW_ORCHESTRATION = "workflow_orchestration"  # 工作流编排
    
    # 自定义类型
    CUSTOM = "custom"                        # 自定义


class AgentStatus(Enum):
    """Agent状态枚举"""
    INITIALIZING = "initializing"           # 初始化中
    IDLE = "idle"                          # 空闲
    BUSY = "busy"                          # 忙碌
    ERROR = "error"                        # 错误
    MAINTENANCE = "maintenance"             # 维护
    OFFLINE = "offline"                    # 离线
    SUSPENDED = "suspended"                 # 暂停
    TERMINATING = "terminating"             # 终止中


class AgentState(Enum):
    """Agent内部状态"""
    CREATED = "created"                     # 已创建
    STARTING = "starting"                  # 启动中
    RUNNING = "running"                    # 运行中
    PAUSED = "paused"                      # 暂停
    STOPPING = "stopping"                  # 停止中
    STOPPED = "stopped"                    # 已停止
    FAILED = "failed"                      # 已失败


class ResourceType(Enum):
    """资源类型"""
    CPU = "cpu"                           # CPU
    MEMORY = "memory"                     # 内存
    STORAGE = "storage"                   # 存储
    NETWORK = "network"                   # 网络
    GPU = "gpu"                           # GPU
    DATABASE_CONNECTIONS = "db_connections"  # 数据库连接
    API_RATE_LIMIT = "api_rate_limit"     # API速率限制
    CONCURRENT_TASKS = "concurrent_tasks" # 并发任务数


class MessageType(Enum):
    """消息类型"""
    HEARTBEAT = "heartbeat"               # 心跳
    TASK_REQUEST = "task_request"         # 任务请求
    TASK_RESPONSE = "task_response"       # 任务响应
    STATUS_UPDATE = "status_update"       # 状态更新
    ERROR = "error"                       # 错误
    BROADCAST = "broadcast"               # 广播
    DIRECT = "direct"                     # 直接消息
    SYSTEM = "system"                     # 系统消息
    PLUGIN = "plugin"                     # 插件消息


class Priority(Enum):
    """消息优先级"""
    LOW = 0                               # 低
    NORMAL = 1                            # 普通
    HIGH = 2                              # 高
    CRITICAL = 3                          # 关键


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"                   # 健康
    DEGRADED = "degraded"                # 降级
    UNHEALTHY = "unhealthy"              # 不健康
    CRITICAL = "critical"                # 严重
    UNKNOWN = "unknown"                  # 未知


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"                        # 信息
    WARNING = "warning"                  # 警告
    ERROR = "error"                      # 错误
    CRITICAL = "critical"                # 严重


class LifecycleEvent(Enum):
    """生命周期事件"""
    INITIALIZE = "initialize"             # 初始化
    START = "start"                      # 启动
    PAUSE = "pause"                      # 暂停
    RESUME = "resume"                    # 恢复
    STOP = "stop"                        # 停止
    TERMINATE = "terminate"              # 终止
    ERROR = "error"                       # 错误


class PluginType(Enum):
    """插件类型"""
    CAPABILITY = "capability"             # 能力插件
    COMMUNICATION = "communication"       # 通信插件
    MONITORING = "monitoring"             # 监控插件
    RESOURCE = "resource"                # 资源插件
    UI = "ui"                           # UI插件
    INTEGRATION = "integration"          # 集成插件
    CUSTOM = "custom"                    # 自定义插件


class LifecycleState(Enum):
    """生命周期状态"""
    UNINITIALIZED = "uninitialized"       # 未初始化
    INITIALIZING = "initializing"         # 初始化中
    INITIALIZED = "initialized"           # 已初始化
    STARTING = "starting"                 # 启动中
    RUNNING = "running"                   # 运行中
    PAUSING = "pausing"                   # 暂停中
    PAUSED = "paused"                     # 已暂停
    STOPPING = "stopping"                 # 停止中
    STOPPED = "stopped"                   # 已停止
    TERMINATING = "terminating"           # 终止中
    TERMINATED = "terminated"             # 已终止
    ERROR = "error"                       # 错误状态


@dataclass
class AgentCapability:
    """Agent能力"""
    name: str                            # 能力名称
    description: str                     # 描述
    input_types: Set[str] = field(default_factory=set)   # 输入类型
    output_types: Set[str] = field(default_factory=set)  # 输出类型
    parameters: Dict[str, Any] = field(default_factory=dict)  # 参数
    cost_per_request: float = 0.0       # 每次请求成本
    estimated_time: float = 1.0          # 预估时间（秒）
    resource_requirements: Dict[str, float] = field(default_factory=dict)  # 资源需求


@dataclass
class AgentMetadata:
    """Agent元数据"""
    agent_id: str                        # Agent ID
    name: str                           # Agent名称
    version: str = "1.0.0"              # 版本
    description: str = ""               # 描述
    author: str = ""                    # 作者
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)    # 更新时间
    tags: Set[str] = field(default_factory=set)  # 标签
    dependencies: List[str] = field(default_factory=list)  # 依赖
    configuration_schema: Dict[str, Any] = field(default_factory=dict)  # 配置架构


@dataclass
class AgentConfig:
    """Agent配置"""
    agent_id: str                       # Agent ID
    agent_type: AgentType               # Agent类型
    model_config: Dict[str, Any] = field(default_factory=dict)  # 模型配置
    resource_limits: Dict[str, float] = field(default_factory=dict)  # 资源限制
    timeout: float = 60.0              # 超时时间
    retry_count: int = 3               # 重试次数
    max_concurrent_tasks: int = 1      # 最大并发任务数
    enabled_capabilities: List[str] = field(default_factory=list)  # 启用的能力
    custom_settings: Dict[str, Any] = field(default_factory=dict)  # 自定义设置
    environment_vars: Dict[str, str] = field(default_factory=dict)  # 环境变量


@dataclass
class AgentMetrics:
    """Agent指标"""
    # 基本指标
    total_requests: int = 0             # 总请求数
    successful_requests: int = 0       # 成功请求数
    failed_requests: int = 0           # 失败请求数
    total_tokens: int = 0              # 总令牌数
    total_cost: float = 0.0            # 总成本
    average_response_time: float = 0.0 # 平均响应时间
    
    # 时间指标
    uptime: float = 0.0                # 运行时间
    last_used: Optional[datetime] = None  # 最后使用时间
    last_error: Optional[datetime] = None  # 最后错误时间
    
    # 性能指标
    error_rate: float = 0.0            # 错误率
    throughput: float = 0.0           # 吞吐量
    memory_usage: float = 0.0           # 内存使用
    cpu_usage: float = 0.0             # CPU使用
    
    # 自定义指标
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def update_metrics(self, success: bool, tokens: int = 0, cost: float = 0.0, 
                      response_time: float = 0.0, memory: float = 0.0, cpu: float = 0.0):
        """更新指标"""
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            self.last_error = datetime.now()
        
        self.total_tokens += tokens
        self.total_cost += cost
        self.last_used = datetime.now()
        
        # 计算平均响应时间
        if self.total_requests > 0:
            self.average_response_time = (
                (self.average_response_time * (self.total_requests - 1) + response_time) 
                / self.total_requests
            )
        
        # 更新资源使用
        self.memory_usage = memory
        self.cpu_usage = cpu
        
        # 计算错误率
        if self.total_requests > 0:
            self.error_rate = self.failed_requests / self.total_requests
        
        # 计算吞吐量（每分钟请求数）
        if self.uptime > 0:
            self.throughput = (self.total_requests / self.uptime) * 60.0
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.get_success_rate(),
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "average_response_time": self.average_response_time,
            "uptime": self.uptime,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "last_error": self.last_error.isoformat() if self.last_error else None,
            "error_rate": self.error_rate,
            "throughput": self.throughput,
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
            "custom_metrics": self.custom_metrics
        }


@dataclass
class AgentMessage:
    """Agent消息"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.DIRECT
    sender_id: str = ""
    receiver_id: str = ""
    priority: Priority = Priority.NORMAL
    content: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "priority": self.priority.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to
        }


@dataclass
class AgentHealth:
    """Agent健康状态"""
    agent_id: str                        # Agent ID
    status: HealthStatus = HealthStatus.UNKNOWN  # 健康状态
    last_check: datetime = field(default_factory=datetime.now)  # 最后检查时间
    response_time: float = 0.0           # 响应时间
    error_count: int = 0                 # 错误计数
    consecutive_failures: int = 0        # 连续失败次数
    last_error: Optional[str] = None     # 最后错误信息
    details: Dict[str, Any] = field(default_factory=dict)  # 详细信息
    
    def update_health(self, success: bool, response_time: float = 0.0, error_msg: str = ""):
        """更新健康状态"""
        self.last_check = datetime.now()
        self.response_time = response_time
        
        if success:
            self.consecutive_failures = 0
            if self.status == HealthStatus.UNHEALTHY or self.status == HealthStatus.CRITICAL:
                self.status = HealthStatus.DEGRADED
            elif self.status == HealthStatus.DEGRADED:
                self.status = HealthStatus.HEALTHY
            self.error_count = 0
            self.last_error = None
        else:
            self.consecutive_failures += 1
            self.error_count += 1
            self.last_error = error_msg
            
            if self.consecutive_failures >= 5:
                self.status = HealthStatus.CRITICAL
            elif self.consecutive_failures >= 3:
                self.status = HealthStatus.UNHEALTHY
            elif self.consecutive_failures >= 1:
                self.status = HealthStatus.DEGRADED


@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: datetime = field(default_factory=datetime.now)
    total_agents: int = 0               # 总Agent数
    active_agents: int = 0              # 活跃Agent数
    idle_agents: int = 0                # 空闲Agent数
    busy_agents: int = 0                # 忙碌Agent数
    error_agents: int = 0               # 错误Agent数
    total_requests: int = 0             # 总请求数
    successful_requests: int = 0        # 成功请求数
    failed_requests: int = 0             # 失败请求数
    system_cpu_usage: float = 0.0       # 系统CPU使用率
    system_memory_usage: float = 0.0     # 系统内存使用率
    system_storage_usage: float = 0.0    # 系统存储使用率
    network_io: Dict[str, float] = field(default_factory=dict)  # 网络IO
    custom_metrics: Dict[str, Any] = field(default_factory=dict)  # 自定义指标
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_agents": self.total_agents,
            "active_agents": self.active_agents,
            "idle_agents": self.idle_agents,
            "busy_agents": self.busy_agents,
            "error_agents": self.error_agents,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "system_cpu_usage": self.system_cpu_usage,
            "system_memory_usage": self.system_memory_usage,
            "system_storage_usage": self.system_storage_usage,
            "network_io": self.network_io,
            "custom_metrics": self.custom_metrics
        }


@dataclass
class ResourceQuota:
    """资源配额"""
    resource_type: ResourceType         # 资源类型
    limit: float                        # 限制值
    reserved: float = 0.0              # 预留值
    available: float = 0.0             # 可用值
    used: float = 0.0                  # 已使用值
    unit: str = ""                     # 单位
    
    def __post_init__(self):
        """初始化后处理"""
        if self.available == 0.0:
            self.available = self.limit - self.reserved - self.used
    
    def allocate(self, amount: float) -> bool:
        """分配资源"""
        if amount <= self.available:
            self.used += amount
            self.available -= amount
            return True
        return False
    
    def deallocate(self, amount: float) -> bool:
        """释放资源"""
        if amount <= self.used:
            self.used -= amount
            self.available += amount
            return True
        return False
    
    def get_usage_rate(self) -> float:
        """获取使用率"""
        if self.limit == 0:
            return 0.0
        return self.used / self.limit


@dataclass
class PluginManifest:
    """插件清单"""
    plugin_id: str                      # 插件ID
    name: str                           # 插件名称
    version: str                        # 版本
    description: str                    # 描述
    plugin_type: PluginType             # 插件类型
    author: str = ""                   # 作者
    license: str = ""                   # 许可证
    homepage: str = ""                  # 主页
    repository: str = ""               # 仓库
    dependencies: List[str] = field(default_factory=list)  # 依赖
    capabilities: List[str] = field(default_factory=list)  # 能力
    configuration_schema: Dict[str, Any] = field(default_factory=dict)  # 配置架构
    permissions: List[str] = field(default_factory=list)  # 权限
    entry_point: str = ""              # 入口点
    assets: List[str] = field(default_factory=list)  # 资源文件
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)    # 更新时间


@dataclass
class Alert:
    """告警"""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""                    # 告警标题
    message: str = ""                   # 告警消息
    level: AlertLevel = AlertLevel.INFO  # 告警级别
    source: str = ""                    # 告警来源
    agent_id: Optional[str] = None      # 相关Agent ID
    timestamp: datetime = field(default_factory=datetime.now)  # 告警时间
    acknowledged: bool = False          # 是否已确认
    resolved: bool = False              # 是否已解决
    metadata: Dict[str, Any] = field(default_factory=dict)  # 附加信息
    assets: List[str] = field(default_factory=list)  # 资源文件
    created_at: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_at: datetime = field(default_factory=datetime.now)    # 更新时间