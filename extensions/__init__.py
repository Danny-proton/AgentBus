"""
AgentBus扩展系统
AgentBus Extension System

这是一个功能强大的扩展系统，支持插件式功能扩展，
提供扩展的发现、加载、激活、停用、依赖解析、版本管理和安全沙箱功能。

This is a powerful extension system supporting plugin-based functionality extension,
providing extension discovery, loading, activation, deactivation, dependency resolution,
version management, and secure sandbox functionality.

Author: MiniMax Agent
License: MIT
"""

from .base import (
    Extension,
    ExtensionInterface,
    ExtensionManagerInterface,
    ExtensionRegistryInterface,
    ExtensionSandboxInterface,
    ExtensionDependency,
    ExtensionVersion,
    ExtensionState,
    ExtensionError,
    ExtensionLoadError,
    ExtensionDependencyError,
    ExtensionSecurityError
)

from .manager import ExtensionManager
from .registry import ExtensionRegistry
from .sandbox import ExtensionSandbox

# 扩展系统版本信息
EXTENSION_SYSTEM_VERSION = "1.0.0"

# 默认扩展配置
DEFAULT_EXTENSION_CONFIG = {
    "auto_discover": True,
    "auto_load": False,
    "security_level": "strict",
    "sandbox_enabled": True,
    "dependency_resolution": "strict",
    "version_check": True,
    "max_execution_time": 30,
    "memory_limit": "128MB"
}

# 扩展类型枚举
class ExtensionType:
    """扩展类型枚举"""
    CORE = "core"              # 核心扩展
    CHANNEL = "channel"        # 通道扩展
    AI_MODEL = "ai_model"       # AI模型扩展
    TOOL = "tool"             # 工具扩展
    PROCESSOR = "processor"    # 处理器扩展
    INTEGRATION = "integration" # 集成扩展
    UI = "ui"                 # UI扩展
    CUSTOM = "custom"          # 自定义扩展

# 扩展状态枚举
class ExtensionStatus:
    """扩展状态枚举"""
    DISCOVERED = "discovered"    # 已发现
    LOADED = "loaded"            # 已加载
    ACTIVE = "active"            # 活跃
    INACTIVE = "inactive"        # 非活跃
    ERROR = "error"              # 错误
    DISABLED = "disabled"        # 已禁用

# 安全性级别枚举
class SecurityLevel:
    """安全性级别枚举"""
    PERMISSIVE = "permissive"    # 宽松
    MODERATE = "moderate"        # 中等
    STRICT = "strict"           # 严格
    MAXIMUM = "maximum"          # 最高

__all__ = [
    # 核心类
    "Extension",
    "ExtensionInterface", 
    "ExtensionManagerInterface",
    "ExtensionRegistryInterface",
    "ExtensionSandboxInterface",
    "ExtensionDependency",
    "ExtensionVersion",
    "ExtensionState",
    
    # 异常类
    "ExtensionError",
    "ExtensionLoadError", 
    "ExtensionDependencyError",
    "ExtensionSecurityError",
    
    # 管理类
    "ExtensionManager",
    "ExtensionRegistry",
    "ExtensionSandbox",
    
    # 常量
    "EXTENSION_SYSTEM_VERSION",
    "DEFAULT_EXTENSION_CONFIG",
    "ExtensionType",
    "ExtensionStatus",
    "SecurityLevel"
]