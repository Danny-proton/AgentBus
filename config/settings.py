"""
配置管理模块
处理应用配置加载和管理
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


class ServerConfig(BaseSettings):
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    log_level: str = "info"
    
    model_config = SettingsConfigDict(env_prefix="AGENTBUS_SERVER_")


class MemoryConfig(BaseSettings):
    """内存配置"""
    max_messages: int = 100
    max_tokens: int = 100000
    compression_threshold: float = 0.85
    
    model_config = SettingsConfigDict(env_prefix="AGENTBUS_MEMORY_")


class LLMConfig(BaseSettings):
    """LLM 配置"""
    default_provider: str = "openai"
    default_model: str = "gpt-4"
    timeout: int = 60
    max_retries: int = 3
    stream: bool = True
    
    model_config = SettingsConfigDict(env_prefix="AGENTBUS_LLM_")


class ModelProfile(BaseSettings):
    """模型配置"""
    name: str
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str
    context_window: int = 128000
    max_output_tokens: int = 4096
    cost_per_input: float = 0.0
    cost_per_output: float = 0.0
    enabled: bool = True


class ModelPointers(BaseSettings):
    """模型指针配置"""
    main: str = "default"
    task: str = "default"
    reasoning: str = "default"
    quick: str = "default"


class RemoteConfig(BaseSettings):
    """远程环境配置"""
    enabled: bool = False
    host: Optional[str] = None
    port: int = 22
    username: Optional[str] = None
    password: Optional[str] = None
    private_key_path: Optional[str] = None
    workspace: str = "/workspace"
    
    model_config = SettingsConfigDict(env_prefix="AGENTBUS_REMOTE_")


class SecurityConfig(BaseSettings):
    """安全配置"""
    safe_mode: bool = False
    require_approval_for_dangerous: bool = True
    allowed_commands: list = Field(default_factory=list)
    blocked_commands: list = Field(default_factory=lambda: ["rm -rf", "format", "mkfs"])
    
    model_config = SettingsConfigDict(env_prefix="AGENTBUS_SECURITY_")


class LoggingConfig(BaseSettings):
    """日志配置"""
    enabled: bool = True
    level: str = "DEBUG"
    directory: str = "./workspace/logs"
    flush_interval: float = 5.0
    batch_size: int = 100
    
    model_config = SettingsConfigDict(env_prefix="AGENTBUS_LOGGING_")


class WorkspaceConfig(BaseSettings):
    """工作空间配置"""
    path: str = "./workspace"
    create_if_not_exists: bool = True
    max_temp_age_hours: int = 24
    
    model_config = SettingsConfigDict(env_prefix="AGENTBUS_WORKSPACE_")


class KnowledgeBusConfig(BaseSettings):
    """知识总线配置"""
    enabled: bool = True
    auto_cleanup: bool = False
    max_entries: int = 1000
    
    model_config = SettingsConfigDict(env_prefix="AGENTBUS_KNOWLEDGE_")


class HumanLoopConfig(BaseSettings):
    """人在回路配置"""
    enabled: bool = True
    default_timeout: int = 300
    max_pending_requests: int = 10
    
    model_config = SettingsConfigDict(env_prefix="AGENTBUS_HUMAN_")


class Settings(BaseSettings):
    """主配置类"""
    server: ServerConfig = Field(default_factory=ServerConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    remote: RemoteConfig = Field(default_factory=RemoteConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    knowledge_bus: KnowledgeBusConfig = Field(default_factory=KnowledgeBusConfig)
    human_loop: HumanLoopConfig = Field(default_factory=HumanLoopConfig)
    
    # 模型配置
    model_profiles: Dict[str, ModelProfile] = Field(default_factory=dict)
    model_pointers: ModelPointers = Field(default_factory=ModelPointers)
    
    # 路径配置
    data_dir: str = "~/.agentbus"
    config_file: str = "~/.agentbus.json"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载配置文件"""
    import json
    
    config_file = config_path or os.path.expanduser("~/.agentbus.json")
    
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    return {}


@lru_cache()
def get_settings():
    """获取配置实例（单例）"""
    # 加载 .env 文件
    load_dotenv()
    
    # 加载配置文件
    config_data = load_config()
    
    if config_data:
        # 将配置文件数据转换为设置
        settings = Settings(**config_data)
    else:
        settings = Settings()
    
    return settings


def get_model_config(model_name: str) -> Optional[ModelProfile]:
    """获取指定模型的配置"""
    settings = get_settings()
    return settings.model_profiles.get(model_name)


def get_active_model_pointer(pointer_type: str = "main") -> str:
    """获取活跃模型指针"""
    settings = get_settings()
    pointers = settings.model_pointers
    
    pointer_map = {
        "main": pointers.main,
        "task": pointers.task,
        "reasoning": pointers.reasoning,
        "quick": pointers.quick
    }
    
    return pointer_map.get(pointer_type, pointers.main)
