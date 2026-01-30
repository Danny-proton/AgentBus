"""
AgentBus 设置管理
Settings management for AgentBus
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """AgentBus 应用设置"""
    
    model_config = ConfigDict(
        env_prefix="AGENTBUS_",
        case_sensitive=False,
        extra="ignore"
    )
    
    # 应用基础设置
    app_name: str = Field(default="AgentBus")
    app_version: str = Field(default="2.0.0")
    debug: bool = Field(default=False)
    
    # 服务器设置
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    reload: bool = Field(default=False)
    workers: int = Field(default=1)
    
    # 日志设置
    log_level: str = Field(default="INFO")
    log_file: Optional[str] = Field(default=None)
    log_format: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"
    )
    
    # 工作空间设置
    workspace_path: str = Field(default="./workspace")
    
    # 沟通地图设置
    communication_map_file: str = Field(default="./data/communication_map.yaml")
    
    # 数据库设置
    database_url: Optional[str] = Field(default=None)
    
    # API 设置
    api_prefix: str = Field(default="/api/v1")
    api_title: str = Field(default="AgentBus API")
    api_description: str = Field(default="AgentBus 智能协作平台 API")
    
    # 安全设置
    secret_key: str = Field(default="your-secret-key-here")
    access_token_expire_minutes: int = Field(default=30)
    
    # CORS 设置
    cors_origins: str = Field(default="*")
    
    # Redis 设置 (可选)
    redis_url: Optional[str] = Field(default=None)
    
    # 外部服务设置
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    
    # HITL 设置
    hitl_timeout_default: int = Field(default=30)
    hitl_max_retry: int = Field(default=3)
    
    # 记忆系统设置
    memory_enabled: bool = Field(default=True)
    memory_retention_days: int = Field(default=365)
    
    # 知识总线设置
    knowledge_bus_file: Optional[str] = Field(default="./data/knowledge_bus.json")
    knowledge_enabled: bool = Field(default=True)
    knowledge_retention_days: int = Field(default=730)
    knowledge_auto_cleanup: bool = Field(default=True)
    
    # 多模型协调器设置
    multi_model_enabled: bool = Field(default=True)
    multi_model_max_concurrent_tasks: int = Field(default=10)
    multi_model_default_timeout: int = Field(default=300)
    multi_model_fallback_enabled: bool = Field(default=True)
    multi_model_cost_tracking: bool = Field(default=True)
    multi_model_quality_threshold: float = Field(default=0.7)


# 全局设置实例
settings = Settings()


def get_settings() -> Settings:
    """获取应用设置"""
    return settings


def setup_directories():
    """设置必要的目录"""
    directories = [
        settings.workspace_path,
        os.path.dirname(settings.communication_map_file),
        "./data",
        "./logs",
        "./temp"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def load_environment_overrides():
    """加载环境变量覆盖"""
    # 将字符串逗号分隔的CORS来源转换为列表
    if hasattr(settings, 'cors_origins') and settings.cors_origins:
        settings.cors_origins = [
            origin.strip() for origin in settings.cors_origins.split(",")
        ]
    
    # 设置工作空间绝对路径
    settings.workspace_path = os.path.abspath(settings.workspace_path)
    settings.communication_map_file = os.path.abspath(settings.communication_map_file)
