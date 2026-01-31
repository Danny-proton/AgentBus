"""
AgentBus 扩展设置管理
Extended Settings Management for AgentBus

基于原有settings.py的扩展版本，提供更完整的配置管理功能。
"""

import os
import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Literal
from datetime import datetime
from enum import Enum
from pydantic import Field, validator, root_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ConfigDict

from .config_types import EnvironmentType, ConfigFormat


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseType(str, Enum):
    """数据库类型枚举"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"


class CacheBackend(str, Enum):
    """缓存后端枚举"""
    MEMORY = "memory"
    REDIS = "redis"
    MEMCACHED = "memcached"


class SecurityLevel(str, Enum):
    """安全级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class ExtendedSettings(BaseSettings):
    """AgentBus 扩展应用设置"""
    
    model_config = SettingsConfigDict(
        env_prefix="AGENTBUS_",
        case_sensitive=False,
        extra="allow",
        env_file=".env",
        env_file_encoding="utf-8"
    )
    
    # ============================================================================
    # 基础配置
    # ============================================================================
    app_name: str = Field(default="AgentBus", description="应用名称")
    app_version: str = Field(default="2.0.0", description="应用版本")
    app_description: str = Field(default="AgentBus 智能协作平台", description="应用描述")
    debug: bool = Field(default=False, description="调试模式")
    environment: EnvironmentType = Field(default="development", description="运行环境")
    
    # ============================================================================
    # 服务器配置
    # ============================================================================
    host: str = Field(default="127.0.0.1", description="服务器主机地址")
    port: int = Field(default=8000, ge=1, le=65535, description="服务器端口")
    reload: bool = Field(default=False, description="自动重载")
    workers: int = Field(default=1, ge=1, le=32, description="工作进程数")
    worker_class: str = Field(default="uvicorn.workers.UvicornWorker", description="工作进程类")
    max_requests: int = Field(default=1000, ge=1, description="最大请求数")
    max_requests_jitter: int = Field(default=100, ge=0, description="请求抖动")
    timeout: int = Field(default=30, ge=1, description="超时时间")
    keepalive: int = Field(default=2, ge=0, description="保持连接时间")
    
    # ============================================================================
    # 协议配置
    # ============================================================================
    protocol: Literal["http", "https"] = Field(default="http", description="协议类型")
    ssl_cert_path: Optional[str] = Field(default=None, description="SSL证书路径")
    ssl_key_path: Optional[str] = Field(default=None, description="SSL密钥路径")
    
    # ============================================================================
    # 日志配置
    # ============================================================================
    log_level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")
    log_format: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        description="日志格式"
    )
    log_file: Optional[str] = Field(default=None, description="日志文件路径")
    log_max_size: int = Field(default=10485760, ge=1024, description="日志文件最大大小（字节）")
    log_backup_count: int = Field(default=5, ge=0, description="日志备份文件数量")
    log_json: bool = Field(default=False, description="使用JSON格式日志")
    
    # ============================================================================
    # 文件路径配置
    # ============================================================================
    workspace_path: str = Field(default="./workspace", description="工作空间路径")
    data_path: str = Field(default="./data", description="数据文件路径")
    temp_path: str = Field(default="./temp", description="临时文件路径")
    config_path: str = Field(default="./config", description="配置文件路径")
    logs_path: str = Field(default="./logs", description="日志文件路径")
    
    # 特定文件路径
    communication_map_file: str = Field(default="./data/communication_map.yaml", description="沟通地图文件")
    knowledge_bus_file: str = Field(default="./data/knowledge_bus.json", description="知识总线文件")
    user_preferences_file: str = Field(default="./data/user_preferences.json", description="用户偏好文件")
    
    # ============================================================================
    # 数据库配置
    # ============================================================================
    database_url: Optional[str] = Field(default=None, description="数据库连接URL")
    database_type: DatabaseType = Field(default=DatabaseType.SQLITE, description="数据库类型")
    database_pool_size: int = Field(default=5, ge=1, description="数据库连接池大小")
    database_max_overflow: int = Field(default=10, ge=0, description="数据库连接池最大溢出")
    database_pool_timeout: int = Field(default=30, ge=1, description="数据库连接池超时")
    database_pool_recycle: int = Field(default=3600, ge=0, description="数据库连接池回收时间")
    database_echo: bool = Field(default=False, description="显示SQL语句")
    database_ssl_mode: Optional[str] = Field(default=None, description="数据库SSL模式")
    
    # ============================================================================
    # Redis 配置
    # ============================================================================
    redis_url: Optional[str] = Field(default=None, description="Redis连接URL")
    redis_host: str = Field(default="localhost", description="Redis主机")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis端口")
    redis_db: int = Field(default=0, ge=0, description="Redis数据库编号")
    redis_password: Optional[str] = Field(default=None, description="Redis密码")
    redis_ssl: bool = Field(default=False, description="Redis SSL连接")
    redis_timeout: int = Field(default=5, ge=1, description="Redis超时时间")
    redis_max_connections: int = Field(default=10, ge=1, description="Redis最大连接数")
    
    # ============================================================================
    # API 配置
    # ============================================================================
    api_prefix: str = Field(default="/api/v1", description="API前缀")
    api_title: str = Field(default="AgentBus API", description="API标题")
    api_description: str = Field(default="AgentBus 智能协作平台 API", description="API描述")
    api_version: str = Field(default="v1", description="API版本")
    api_docs_enabled: bool = Field(default=True, description="启用API文档")
    
    # API 限流配置
    rate_limit_enabled: bool = Field(default=True, description="启用API限流")
    rate_limit_requests_per_minute: int = Field(default=100, ge=1, description="每分钟请求数限制")
    rate_limit_burst_size: int = Field(default=20, ge=1, description="突发请求数限制")
    
    # ============================================================================
    # CORS 配置
    # ============================================================================
    cors_origins: Union[str, List[str]] = Field(default="*", description="CORS允许的源")
    cors_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE", "OPTIONS"], description="CORS允许的方法")
    cors_headers: List[str] = Field(default=["*"], description="CORS允许的头")
    cors_credentials: bool = Field(default=True, description="允许凭据")
    cors_max_age: int = Field(default=86400, ge=0, description="CORS预检缓存时间")
    
    # ============================================================================
    # 安全配置
    # ============================================================================
    secret_key: str = Field(default="your-secret-key-here-change-in-production", description="应用密钥")
    jwt_secret: str = Field(default="your-jwt-secret-key-change-in-production-please", description="JWT密钥")
    jwt_algorithm: str = Field(default="HS256", description="JWT算法")
    jwt_access_token_expire_minutes: int = Field(default=30, ge=1, description="JWT访问令牌过期时间（分钟）")
    jwt_refresh_token_expire_days: int = Field(default=7, ge=1, description="JWT刷新令牌过期时间（天）")
    security_level: SecurityLevel = Field(default=SecurityLevel.MEDIUM, description="安全级别")
    encryption_enabled: bool = Field(default=True, description="启用加密")
    
    # 密码策略
    password_min_length: int = Field(default=8, ge=4, description="密码最小长度")
    password_require_uppercase: bool = Field(default=True, description="密码需要大写字母")
    password_require_lowercase: bool = Field(default=True, description="密码需要小写字母")
    password_require_numbers: bool = Field(default=True, description="密码需要数字")
    password_require_symbols: bool = Field(default=False, description="密码需要特殊符号")
    
    # 会话配置
    session_timeout_minutes: int = Field(default=30, ge=1, description="会话超时时间（分钟）")
    session_max_concurrent: int = Field(default=100, ge=1, description="最大并发会话数")
    
    # ============================================================================
    # 外部服务 API 配置
    # ============================================================================
    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API密钥")
    openai_base_url: str = Field(default="https://api.openai.com/v1", description="OpenAI基础URL")
    openai_timeout: int = Field(default=60, ge=1, description="OpenAI超时时间")
    openai_max_retries: int = Field(default=3, ge=0, description="OpenAI最大重试次数")
    
    # Anthropic
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API密钥")
    anthropic_base_url: str = Field(default="https://api.anthropic.com", description="Anthropic基础URL")
    anthropic_timeout: int = Field(default=60, ge=1, description="Anthropic超时时间")
    anthropic_max_retries: int = Field(default=3, ge=0, description="Anthropic最大重试次数")
    
    # Google
    google_api_key: Optional[str] = Field(default=None, description="Google API密钥")
    google_project_id: Optional[str] = Field(default=None, description="Google项目ID")
    
    # Minimax
    minimax_api_key: Optional[str] = Field(default=None, description="Minimax API密钥")
    minimax_group_id: Optional[str] = Field(default=None, description="Minimax组ID")

    # ZhipuAI (GLM)
    zhipu_api_key: Optional[str] = Field(default=None, description="ZhipuAI API密钥")
    zhipu_base_url: str = Field(default="https://open.bigmodel.cn/api/paas/v4/", description="ZhipuAI基础URL")

    # Local Model (vLLM/Ollama)
    local_model_id: str = Field(default="qwen3_32B", description="本地模型ID")
    local_model_base_url: str = Field(default="http://127.0.0.1:8030/v1", description="本地模型基础URL")
    local_model_api_key: str = Field(default="empty", description="本地模型API密钥")

    
    # ============================================================================
    # HITL (Human-in-the-Loop) 配置
    # ============================================================================
    hitl_enabled: bool = Field(default=False, description="启用HITL模式")
    hitl_timeout_default: int = Field(default=30, ge=1, description="HITL默认超时时间")
    hitl_max_retry: int = Field(default=3, ge=0, description="HITL最大重试次数")
    hitl_approval_required: bool = Field(default=False, description="HITL需要审批")
    hitl_auto_approve_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="HITL自动批准阈值")
    
    # ============================================================================
    # 记忆系统配置
    # ============================================================================
    memory_enabled: bool = Field(default=True, description="启用记忆系统")
    memory_retention_days: int = Field(default=365, ge=1, description="记忆保留天数")
    memory_max_entries: int = Field(default=10000, ge=1, description="最大记忆条目数")
    memory_auto_cleanup: bool = Field(default=True, description="自动清理记忆")
    memory_compression_enabled: bool = Field(default=True, description="启用记忆压缩")
    memory_embedding_model: str = Field(default="text-embedding-ada-002", description="记忆嵌入模型")
    memory_similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="记忆相似度阈值")
    
    # ============================================================================
    # 知识总线配置
    # ============================================================================
    knowledge_enabled: bool = Field(default=True, description="启用知识总线")
    knowledge_retention_days: int = Field(default=730, ge=1, description="知识保留天数")
    knowledge_auto_cleanup: bool = Field(default=True, description="自动清理知识")
    knowledge_max_entries: int = Field(default=50000, ge=1, description="最大知识条目数")
    knowledge_vector_search_enabled: bool = Field(default=True, description="启用向量搜索")
    knowledge_auto_indexing: bool = Field(default=True, description="自动索引")
    
    # ============================================================================
    # 多模型协调器配置
    # ============================================================================
    multi_model_enabled: bool = Field(default=True, description="启用多模型协调")
    multi_model_max_concurrent_tasks: int = Field(default=10, ge=1, description="最大并发任务数")
    multi_model_default_timeout: int = Field(default=300, ge=1, description="默认超时时间")
    multi_model_fallback_enabled: bool = Field(default=True, description="启用降级机制")
    multi_model_cost_tracking: bool = Field(default=True, description="启用成本跟踪")
    multi_model_quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="质量阈值")
    multi_model_load_balancing: str = Field(default="round_robin", description="负载均衡策略")
    
    # ============================================================================
    # 缓存配置
    # ============================================================================
    cache_enabled: bool = Field(default=True, description="启用缓存")
    cache_backend: CacheBackend = Field(default=CacheBackend.MEMORY, description="缓存后端")
    cache_ttl: int = Field(default=3600, ge=0, description="缓存TTL（秒）")
    cache_max_size: int = Field(default=1000, ge=1, description="缓存最大大小")
    cache_cleanup_interval: int = Field(default=300, ge=1, description="缓存清理间隔（秒）")
    
    # ============================================================================
    # 监控和指标配置
    # ============================================================================
    monitoring_enabled: bool = Field(default=False, description="启用监控")
    metrics_enabled: bool = Field(default=False, description="启用指标")
    health_check_enabled: bool = Field(default=True, description="启用健康检查")
    metrics_port: int = Field(default=9090, ge=1, le=65535, description="指标端口")
    health_endpoint: str = Field(default="/health", description="健康检查端点")
    metrics_endpoint: str = Field(default="/metrics", description="指标端点")
    
    # Prometheus 配置
    prometheus_enabled: bool = Field(default=False, description="启用Prometheus")
    prometheus_port: int = Field(default=9091, ge=1, le=65535, description="Prometheus端口")
    
    # ============================================================================
    # 消息系统配置
    # ============================================================================
    message_max_length: int = Field(default=8192, ge=1, description="消息最大长度")
    message_batch_size: int = Field(default=10, ge=1, description="消息批处理大小")
    message_timeout: int = Field(default=30, ge=1, description="消息超时时间")
    message_retry_attempts: int = Field(default=3, ge=0, description="消息重试次数")
    message_queue_size: int = Field(default=1000, ge=1, description="消息队列大小")
    
    # 媒体消息配置
    media_enabled: bool = Field(default=True, description="启用媒体消息")
    media_max_file_size: int = Field(default=52428800, ge=1024, description="媒体文件最大大小（字节）")
    media_allowed_types: List[str] = Field(
        default=["image/jpeg", "image/png", "image/gif", "audio/mpeg", "video/mp4", "application/pdf"],
        description="允许的媒体类型"
    )
    media_processing_enabled: bool = Field(default=True, description="启用媒体处理")
    
    # ============================================================================
    # 插件系统配置
    # ============================================================================
    plugins_enabled: bool = Field(default=True, description="启用插件系统")
    plugins_auto_load: bool = Field(default=True, description="自动加载插件")
    plugins_scan_directories: List[str] = Field(
        default=["./plugins", "./extensions"],
        description="插件扫描目录"
    )
    plugins_max_loaded: int = Field(default=50, ge=1, description="最大加载插件数")
    plugins_sandbox_enabled: bool = Field(default=True, description="启用插件沙盒")
    plugins_security_level: SecurityLevel = Field(default=SecurityLevel.MEDIUM, description="插件安全级别")
    
    # ============================================================================
    # 技能系统配置
    # ============================================================================
    skills_enabled: bool = Field(default=True, description="启用技能系统")
    skills_auto_register: bool = Field(default=True, description="自动注册技能")
    skills_scan_directories: List[str] = Field(
        default=["./skills"],
        description="技能扫描目录"
    )
    skills_max_concurrent: int = Field(default=10, ge=1, description="最大并发技能数")
    skills_timeout: int = Field(default=300, ge=1, description="技能执行超时时间")
    skills_memory_limit: str = Field(default="512MB", description="技能内存限制")
    
    # ============================================================================
    # 性能配置
    # ============================================================================
    performance_monitoring_enabled: bool = Field(default=False, description="启用性能监控")
    performance_profiling_enabled: bool = Field(default=False, description="启用性能分析")
    performance_alerts_enabled: bool = Field(default=False, description="启用性能告警")
    performance_alert_thresholds: Dict[str, float] = Field(
        default={
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "response_time": 1000.0,
            "error_rate": 5.0
        },
        description="性能告警阈值"
    )
    
    # ============================================================================
    # 开发配置
    # ============================================================================
    development_hot_reload: bool = Field(default=False, description="热重载")
    development_debug_toolbar: bool = Field(default=False, description="调试工具栏")
    development_test_mode: bool = Field(default=False, description="测试模式")
    development_profiling: bool = Field(default=False, description="性能分析")
    development_mock_external: bool = Field(default=False, description="模拟外部服务")
    
    # ============================================================================
    # 备份和恢复配置
    # ============================================================================
    backup_enabled: bool = Field(default=True, description="启用备份")
    backup_interval_hours: int = Field(default=24, ge=1, description="备份间隔（小时）")
    backup_retention_days: int = Field(default=30, ge=1, description="备份保留天数")
    backup_path: str = Field(default="./backups", description="备份路径")
    backup_compression: bool = Field(default=True, description="压缩备份")
    backup_encryption: bool = Field(default=False, description="加密备份")
    
    # ============================================================================
    # 通知配置
    # ============================================================================
    notifications_enabled: bool = Field(default=False, description="启用通知")
    notifications_email_enabled: bool = Field(default=False, description="启用邮件通知")
    notifications_webhook_enabled: bool = Field(default=False, description="启用Webhook通知")
    smtp_host: Optional[str] = Field(default=None, description="SMTP主机")
    smtp_port: int = Field(default=587, ge=1, le=65535, description="SMTP端口")
    smtp_username: Optional[str] = Field(default=None, description="SMTP用户名")
    smtp_password: Optional[str] = Field(default=None, description="SMTP密码")
    smtp_use_tls: bool = Field(default=True, description="使用TLS")
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL")
    
    # ============================================================================
    # 验证器
    # ============================================================================
    
    @validator("secret_key")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("密钥长度至少32个字符")
        return v
    
    @validator("jwt_secret")
    def validate_jwt_secret(cls, v):
        if len(v) < 32:
            raise ValueError("JWT密钥长度至少32个字符")
        return v
    
    @validator("host")
    def validate_host(cls, v):
        import socket
        try:
            socket.inet_aton(v)
        except socket.error:
            raise ValueError("无效的主机地址")
        return v
    
    @validator("redis_host")
    def validate_redis_host(cls, v):
        if v not in ["localhost", "127.0.0.1"]:
            import socket
            try:
                socket.inet_aton(v)
            except socket.error:
                raise ValueError("无效的Redis主机地址")
        return v
    
    @validator("workspace_path", "data_path", "temp_path", "config_path", "logs_path")
    def validate_paths(cls, v):
        path = Path(v)
        return str(path.absolute())
    
    @root_validator(skip_on_failure=True)
    def validate_dependencies(cls, values):
        """验证配置依赖关系"""
        # Redis 配置依赖
        if values.get("redis_url") and values.get("redis_password"):
            if not values.get("redis_host"):
                raise ValueError("Redis主机地址不能为空")
        
        # SSL 配置依赖
        if values.get("protocol") == "https":
            if not values.get("ssl_cert_path") or not values.get("ssl_key_path"):
                raise ValueError("HTTPS协议需要SSL证书和密钥文件")
        
        # 数据库配置依赖
        if values.get("database_url"):
            db_type = values.get("database_type")
            if db_type == DatabaseType.POSTGRESQL:
                if "postgresql" not in values["database_url"]:
                    raise ValueError("数据库URL与数据库类型不匹配")
            elif db_type == DatabaseType.MYSQL:
                if "mysql" not in values["database_url"]:
                    raise ValueError("数据库URL与数据库类型不匹配")
            elif db_type == DatabaseType.SQLITE:
                if "sqlite" not in values["database_url"]:
                    raise ValueError("数据库URL与数据库类型不匹配")
        
        return values
    
    # ============================================================================
    # 实例方法
    # ============================================================================
    
    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """转换为字典"""
        data = self.model_dump()
        
        if not include_secrets:
            # 隐藏敏感信息
            secret_fields = [
                "secret_key", "jwt_secret", "openai_api_key", "anthropic_api_key",
                "google_api_key", "minimax_api_key", "zhipu_api_key", "redis_password", "smtp_password",
                "local_model_api_key"
            ]
            for field in secret_fields:
                if field in data:
                    data[field] = "***"
        
        return data
    
    def to_yaml(self, include_secrets: bool = False) -> str:
        """转换为YAML格式"""
        return yaml.dump(self.to_dict(include_secrets=include_secrets), default_flow_style=False, allow_unicode=True)
    
    def to_json(self, include_secrets: bool = False) -> str:
        """转换为JSON格式"""
        return json.dumps(self.to_dict(include_secrets=include_secrets), indent=2, ensure_ascii=False)
    
    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        if self.database_url:
            return self.database_url
        
        # 根据数据库类型构建URL
        if self.database_type == DatabaseType.SQLITE:
            return f"sqlite:///{self.data_path}/agentbus.db"
        elif self.database_type == DatabaseType.POSTGRESQL:
            return f"postgresql://user:password@localhost:5432/agentbus"
        elif self.database_type == DatabaseType.MYSQL:
            return f"mysql://user:password@localhost:3306/agentbus"
        else:
            raise ValueError(f"不支持的数据库类型: {self.database_type}")
    
    def get_redis_url(self) -> Optional[str]:
        """获取Redis连接URL"""
        if self.redis_url:
            return self.redis_url
        
        auth_part = ""
        if self.redis_password:
            auth_part = f":{self.redis_password}@"
        
        return f"redis://{auth_part}{self.redis_host}:{self.redis_db}"
    
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == "development"
    
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == "production"
    
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.environment == "testing"
    
    def get_log_level(self) -> str:
        """获取日志级别字符串"""
        return self.log_level.value
    
    def get_security_config(self) -> Dict[str, Any]:
        """获取安全配置"""
        return {
            "secret_key": self.secret_key,
            "jwt_secret": self.jwt_secret,
            "jwt_algorithm": self.jwt_algorithm,
            "security_level": self.security_level.value,
            "encryption_enabled": self.encryption_enabled,
            "password_policy": {
                "min_length": self.password_min_length,
                "require_uppercase": self.password_require_uppercase,
                "require_lowercase": self.password_require_lowercase,
                "require_numbers": self.password_require_numbers,
                "require_symbols": self.password_require_symbols,
            }
        }
    
    def validate_environment(self) -> List[str]:
        """验证环境配置"""
        errors = []
        
        # 检查必要的目录
        required_paths = [self.workspace_path, self.data_path]
        for path in required_paths:
            if not Path(path).exists():
                errors.append(f"必要目录不存在: {path}")
        
        # 检查文件权限
        if self.is_production():
            # 生产环境需要更严格的权限检查
            if not os.access(self.config_path, os.R_OK):
                errors.append(f"配置文件目录不可读: {self.config_path}")
        
        return errors


# 创建全局设置实例
extended_settings = ExtendedSettings()


def get_extended_settings() -> ExtendedSettings:
    """获取扩展设置实例"""
    return extended_settings


def create_settings_from_env(env_vars: Dict[str, str]) -> ExtendedSettings:
    """从环境变量创建设置实例"""
    return ExtendedSettings(**env_vars)


def load_settings_from_file(file_path: Union[str, Path], format: ConfigFormat = ConfigFormat.YAML) -> ExtendedSettings:
    """从文件加载设置"""
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        if format == ConfigFormat.YAML:
            data = yaml.safe_load(f)
        elif format == ConfigFormat.JSON:
            data = json.load(f)
        else:
            raise ValueError(f"不支持的配置文件格式: {format}")
    
    return ExtendedSettings(**data)


def validate_settings(settings: ExtendedSettings) -> bool:
    """验证设置"""
    try:
        # Pydantic会自动验证字段
        settings.model_validate(settings.model_dump())
        return True
    except Exception as e:
        raise ValueError(f"设置验证失败: {e}")


def merge_settings(*settings_list: ExtendedSettings) -> ExtendedSettings:
    """合并多个设置实例"""
    if not settings_list:
        return ExtendedSettings()
    
    # 合并字典
    merged_dict = {}
    for settings in settings_list:
        merged_dict.update(settings.model_dump())
    
    return ExtendedSettings(**merged_dict)


# 向后兼容的函数
def get_settings() -> ExtendedSettings:
    """获取设置（向后兼容）"""
    return extended_settings


def setup_directories():
    """设置必要的目录"""
    directories = [
        extended_settings.workspace_path,
        extended_settings.data_path,
        extended_settings.temp_path,
        extended_settings.config_path,
        extended_settings.logs_path,
        os.path.dirname(extended_settings.communication_map_file),
        extended_settings.backup_path,
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def load_environment_overrides():
    """加载环境变量覆盖"""
    # 将字符串逗号分隔的CORS来源转换为列表
    if hasattr(extended_settings, 'cors_origins') and extended_settings.cors_origins:
        if isinstance(extended_settings.cors_origins, str):
            extended_settings.cors_origins = [
                origin.strip() for origin in extended_settings.cors_origins.split(",")
            ]
    
    # 设置绝对路径
    extended_settings.workspace_path = os.path.abspath(extended_settings.workspace_path)
    extended_settings.communication_map_file = os.path.abspath(extended_settings.communication_map_file)
    extended_settings.knowledge_bus_file = os.path.abspath(extended_settings.knowledge_bus_file)
