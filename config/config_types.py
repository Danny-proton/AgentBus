"""
AgentBus 配置类型定义
Configuration Types for AgentBus
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable, Literal
from dataclasses import dataclass
from pathlib import Path
import json as json_module

EnvironmentType = Literal["development", "testing", "staging", "production"]


class ConfigSource(Enum):
    """配置来源枚举"""
    DEFAULT = "default"
    ENVIRONMENT = "environment"
    FILE = "file"
    DATABASE = "database"
    REMOTE = "remote"


class ConfigEvent(Enum):
    """配置事件类型"""
    LOADED = "loaded"
    RELOADED = "reloaded"
    UPDATED = "updated"
    VALIDATED = "validated"
    ERROR = "error"
    WATCH_STARTED = "watch_started"
    WATCH_STOPPED = "watch_stopped"


@dataclass
class ConfigProfile:
    """配置文件定义"""
    name: str
    environment: EnvironmentType
    file_path: Optional[Path] = None
    env_prefix: str = "AGENTBUS"
    priority: int = 1
    enabled: bool = True
    variables: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.variables is None:
            self.variables = {}


@dataclass
class ConfigSection:
    """配置节定义"""
    name: str
    source: ConfigSource
    priority: int
    data: Dict[str, Any]
    schema: Optional[Dict[str, Any]] = None
    validation_rules: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """配置验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.suggestions is None:
            self.suggestions = []


@dataclass
class WatchEvent:
    """配置监听事件"""
    event_type: ConfigEvent
    path: Path
    timestamp: float
    data: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None


@dataclass
class EncryptedConfig:
    """加密配置数据"""
    encrypted_data: str
    checksum: str
    algorithm: str
    version: str
    timestamp: float


@dataclass
class ConfigSnapshot:
    """配置快照"""
    id: str
    timestamp: float
    environment: EnvironmentType
    profile: str
    data: Dict[str, Any]
    checksum: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ConfigFormat(Enum):
    """配置文件格式"""
    YAML = "yaml"
    JSON = "json"
    TOML = "toml"
    ENV = "env"


class ConfigScope(Enum):
    """配置作用域"""
    GLOBAL = "global"
    APPLICATION = "application"
    SERVICE = "service"
    COMPONENT = "component"


@dataclass
class ConfigSchema:
    """配置模式定义"""
    name: str
    version: str
    schema: Dict[str, Any]
    required: List[str] = None
    defaults: Dict[str, Any] = None
    validators: Dict[str, Callable] = None
    
    def __post_init__(self):
        if self.required is None:
            self.required = []
        if self.defaults is None:
            self.defaults = {}
        if self.validators is None:
            self.validators = {}


@dataclass
class ConfigHistory:
    """配置历史记录"""
    id: str
    timestamp: float
    action: Literal["created", "updated", "deleted", "restored"]
    path: Path
    old_data: Optional[Dict[str, Any]]
    new_data: Optional[Dict[str, Any]]
    user: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class ConfigChange:
    """配置变更记录"""
    timestamp: float
    path: Path
    field: str
    old_value: Any
    new_value: Any
    source: ConfigSource
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# 配置回调函数类型
ConfigCallback = Callable[[WatchEvent], None]
ValidationCallback = Callable[[Dict[str, Any], ValidationResult], None]


# 常用配置模式
DEFAULT_CONFIG_SCHEMAS = {
    "server": ConfigSchema(
        name="server",
        version="1.0",
        schema={
            "host": {"type": "string", "default": "127.0.0.1"},
            "port": {"type": "integer", "default": 8000, "min": 1, "max": 65535},
            "workers": {"type": "integer", "default": 1, "min": 1},
            "reload": {"type": "boolean", "default": False},
        },
        required=["host", "port"]
    ),
    
    "database": ConfigSchema(
        name="database",
        version="1.0",
        schema={
            "url": {"type": "string", "required": True},
            "pool_size": {"type": "integer", "default": 5, "min": 1, "max": 100},
            "max_overflow": {"type": "integer", "default": 10, "min": 0},
            "timeout": {"type": "integer", "default": 30, "min": 1},
        },
        required=["url"]
    ),
    
    "logging": ConfigSchema(
        name="logging",
        version="1.0",
        schema={
            "level": {"type": "string", "default": "INFO", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
            "format": {"type": "string", "default": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
            "file": {"type": "string", "default": None},
            "handlers": {"type": "list", "default": ["console"]},
        },
        required=["level"]
    ),
    
    "security": ConfigSchema(
        name="security",
        version="1.0",
        schema={
            "secret_key": {"type": "string", "required": True, "min_length": 32},
            "jwt_secret": {"type": "string", "required": True},
            "access_token_expire_minutes": {"type": "integer", "default": 30, "min": 1},
            "cors_origins": {"type": "list", "default": ["*"]},
            "encryption_enabled": {"type": "boolean", "default": True},
        },
        required=["secret_key", "jwt_secret"]
    ),
    
    "cache": ConfigSchema(
        name="cache",
        version="1.0",
        schema={
            "enabled": {"type": "boolean", "default": True},
            "backend": {"type": "string", "default": "memory", "enum": ["memory", "redis", "memcached"]},
            "ttl": {"type": "integer", "default": 3600, "min": 0},
            "max_size": {"type": "integer", "default": 1000, "min": 1},
        },
        required=[]
    ),
    
    "monitoring": ConfigSchema(
        name="monitoring",
        version="1.0",
        schema={
            "enabled": {"type": "boolean", "default": False},
            "metrics_endpoint": {"type": "string", "default": "/metrics"},
            "health_endpoint": {"type": "string", "default": "/health"},
            "prometheus": {"type": "boolean", "default": False},
            "jaeger": {"type": "boolean", "default": False},
        },
        required=[]
    )
}