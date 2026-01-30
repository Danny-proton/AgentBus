"""
配置管理系统
Configuration Management System
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import os
from pydantic import field_validator, Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    database_url: str = "sqlite:///./data/moltbot.db"
    redis_url: str = "redis://localhost:6379/0"
    mongodb_url: str = "mongodb://localhost:27017/moltbot"
    
    # 数据库连接池配置
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_timeout: int = 30


class AISettings(BaseSettings):
    """AI模型配置"""
    openai_api_key: Optional[str] = None
    google_ai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    
    # 默认AI模型配置
    default_model: str = "gpt-4"
    max_tokens: int = 4000
    temperature: float = 0.7
    
    # 流式响应配置
    enable_streaming: bool = True


class MessagePlatformSettings(BaseSettings):
    """消息平台配置"""
    # Discord配置
    discord_bot_token: Optional[str] = None
    discord_guild_id: Optional[str] = None
    
    # Telegram配置
    telegram_bot_token: Optional[str] = None
    telegram_webhook_url: Optional[str] = None
    
    # Slack配置
    slack_bot_token: Optional[str] = None
    slack_app_token: Optional[str] = None
    slack_signing_secret: Optional[str] = None
    
    # WhatsApp配置
    whatsapp_api_token: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    
    # Signal配置
    signal_api_token: Optional[str] = None
    
    # iMessage配置
    imessage_config: Optional[str] = None


class SecuritySettings(BaseSettings):
    """安全配置"""
    secret_key: str = "your-secret-key-change-in-production"
    jwt_secret_key: str = "your-jwt-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    
    # 加密配置
    encryption_enabled: bool = True
    encryption_key: Optional[str] = None


class MediaSettings(BaseSettings):
    """媒体处理配置"""
    # 存储路径
    audio_storage_path: str = "./data/audio"
    image_storage_path: str = "./data/images"
    video_storage_path: str = "./data/videos"
    
    # TTS配置
    tts_engine: str = "gtts"
    tts_language: str = "zh-cn"
    tts_cache_enabled: bool = True
    
    # 图像处理配置
    max_image_size: int = 10 * 1024 * 1024  # 10MB
    supported_image_formats: List[str] = ["jpg", "jpeg", "png", "gif", "webp", "bmp"]
    
    # 音频处理配置
    max_audio_duration: int = 300  # 5分钟
    audio_sample_rate: int = 16000


class WebSettings(BaseSettings):
    """Web服务配置"""
    host: str = "0.0.0.0"
    port: int = 8080
    websocket_port: int = 8081
    
    # FastAPI配置
    debug: bool = False
    reload: bool = False
    workers: int = 1
    
    # CORS配置
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]


class LoggingSettings(BaseSettings):
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    backup_count: int = 5
    
    # 结构化日志
    structured_logging: bool = True


class PluginSettings(BaseSettings):
    """插件系统配置"""
    enable_plugins: bool = True
    plugins_path: str = "./plugins"
    skills_path: str = "./skills"
    extensions_path: str = "./extensions"
    
    # 插件安全配置
    plugin_sandbox_enabled: bool = True
    plugin_timeout: int = 30
    max_plugin_memory: int = 256  # MB


class MetricsSettings(BaseSettings):
    """监控配置"""
    enable_metrics: bool = True
    metrics_port: int = 9090
    health_check_port: int = 9091
    
    # 性能监控
    enable_profiling: bool = False
    slow_query_threshold: float = 1.0  # 秒


class Settings(BaseSettings):
    """主配置类"""
    # 应用配置
    app_name: str = "py-moltbot"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    
    # 子配置模块
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    ai: AISettings = Field(default_factory=AISettings)
    message_platforms: MessagePlatformSettings = Field(default_factory=MessagePlatformSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    media: MediaSettings = Field(default_factory=MediaSettings)
    web: WebSettings = Field(default_factory=WebSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    plugins: PluginSettings = Field(default_factory=PluginSettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow"
    }
    
    def get_database_url(self) -> str:
        """获取数据库URL"""
        return self.database.database_url
    
    def get_redis_url(self) -> str:
        """获取Redis URL"""
        return self.database.redis_url
    
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == "development"
    
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == "production"
    
    def get_storage_paths(self) -> Dict[str, Path]:
        """获取存储路径"""
        base_path = Path.cwd() / "data"
        return {
            "audio": Path(self.media.audio_storage_path),
            "images": Path(self.media.image_storage_path),
            "videos": Path(self.media.video_storage_path),
            "temp": base_path / "temp",
            "logs": base_path / "logs",
        }
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """验证环境变量"""
        allowed = ["development", "testing", "production"]
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}, got {v}")
        return v


# 全局配置实例
settings = Settings()