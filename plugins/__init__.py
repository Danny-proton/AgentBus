"""
AgentBus 插件框架

AgentBus插件框架提供了完整的插件系统，支持动态加载、注册工具、
钩子、渠道等功能。框架采用模块化设计，允许开发者创建自定义插件
来扩展AgentBus的功能。

主要组件:
- AgentBusPlugin: 插件基类，所有插件都应该继承此类
- PluginContext: 插件上下文，提供配置、日志器和运行时环境
- PluginManager: 插件管理器，负责插件的生命周期管理
"""

from .core import (
    PluginContext,
    AgentBusPlugin,
    PluginTool,
    PluginHook,
    PluginStatus
)
from .manager import PluginManager

__version__ = "1.0.0"
__all__ = [
    "PluginContext",
    "AgentBusPlugin", 
    "PluginTool",
    "PluginHook",
    "PluginStatus",
    "PluginManager"
]