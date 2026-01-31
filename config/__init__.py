"""
AgentBus 配置管理系统
Configuration Management System for AgentBus

基于Moltbot的配置系统实现，提供完整的配置管理功能。
"""

from .config_manager import ConfigManager
from .profile_manager import ProfileManager
from .env_loader import EnvironmentLoader
from .settings import ExtendedSettings
from .security import ConfigEncryption, ConfigValidator
from .watcher import ConfigWatcher
from .backup_manager import ConfigBackupManager as BackupManager
from .file_manager import ConfigFileManager as FileManager
from .config_types import (
    EnvironmentType,
    ConfigProfile,
    ConfigSection,
    ValidationResult,
    WatchEvent,
    EncryptedConfig,
)

__version__ = "1.0.0"
__author__ = "AgentBus Team"

# 导出主要类和函数
__all__ = [
    "ConfigManager",
    "ProfileManager", 
    "EnvironmentLoader",
    "ExtendedSettings",
    "ConfigEncryption",
    "ConfigValidator",
    "ConfigWatcher",
    "BackupManager",
    "FileManager",
    "EnvironmentType",
    "ConfigProfile",
    "ConfigSection",
    "ValidationResult",
    "WatchEvent",
    "EncryptedConfig",
]

# 配置系统实例
_config_manager = None

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def initialize_config(env_type: EnvironmentType = None, profile: str = None):
    """初始化配置系统
    
    Args:
        env_type: 环境类型 (development, testing, production)
        profile: 配置配置文件名
    """
    manager = get_config_manager()
    return manager.initialize(env_type, profile)

def reload_config():
    """重新加载配置"""
    manager = get_config_manager()
    return manager.reload()

def get_settings():
    """获取当前设置"""
    manager = get_config_manager()
    return manager.get_settings()

def get_config():
    """获取当前配置"""
    manager = get_config_manager()
    return manager.get_config()

def validate_config() -> ValidationResult:
    """验证当前配置"""
    manager = get_config_manager()
    return manager.validate()

def watch_config(callback=None):
    """监听配置变化"""
    manager = get_config_manager()
    watcher = manager.get_watcher()
    if callback:
        watcher.add_callback(callback)
    return watcher

def create_backup(tag=None) -> str:
    """创建配置备份"""
    manager = get_config_manager()
    return manager.create_backup(tag)

def restore_backup(backup_name: str) -> bool:
    """恢复配置备份"""
    manager = get_config_manager()
    return manager.restore_backup(backup_name)

def list_backups() -> list:
    """列出所有备份"""
    manager = get_config_manager()
    return manager.list_backups()

def read_config_file(file_name: str) -> dict:
    """读取配置文件"""
    manager = get_config_manager()
    return manager.read_config_file(file_name)

def write_config_file(file_name: str, data: dict, overwrite: bool = False) -> bool:
    """写入配置文件"""
    manager = get_config_manager()
    return manager.write_config_file(file_name, data, overwrite)

def delete_config_file(file_name: str) -> bool:
    """删除配置文件"""
    manager = get_config_manager()
    return manager.delete_config_file(file_name)

def validate_config_file(file_name: str) -> ValidationResult:
    """验证配置文件"""
    manager = get_config_manager()
    return manager.validate_config_file(file_name)