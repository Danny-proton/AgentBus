"""
AgentBus - 插件化AI代理系统
Plugin-based AI Agent System

这是一个插件化的AI代理系统，支持多种消息平台和AI模型集成。
A plugin-based AI agent system supporting multiple message platforms and AI model integration.

Author: MiniMax Agent
License: MIT
"""

__version__ = "2.0.0"
__author__ = "MiniMax Agent"
__license__ = "MIT"

# 核心模块导入
from .core.app import AgentBusServer
from .core.settings import settings
from .plugins.manager import PluginManager
from .channels.manager import ChannelManager

# 扩展系统导入
from .extensions import (
    ExtensionManager,
    ExtensionRegistry,
    ExtensionSandbox,
    Extension,
    ExtensionType,
    ExtensionStatus,
    SecurityLevel,
    ExtensionError,
    ExtensionLoadError,
    ExtensionDependencyError,
    ExtensionSecurityError
)

# 版本信息
VERSION_INFO = {
    "version": __version__,
    "author": __author__,
    "license": __license__,
    "description": "插件化AI代理系统",
    "description_en": "Plugin-based AI Agent System",
}

__all__ = [
    "AgentBusServer",
    "PluginManager", 
    "ChannelManager",
    "settings",
    "VERSION_INFO",
    # 扩展系统
    "ExtensionManager",
    "ExtensionRegistry", 
    "ExtensionSandbox",
    "Extension",
    "ExtensionType",
    "ExtensionStatus",
    "SecurityLevel",
    "ExtensionError",
    "ExtensionLoadError",
    "ExtensionDependencyError",
    "ExtensionSecurityError"
]