"""
AgentBus插件框架核心模块

此模块定义了插件系统的核心组件：
- PluginContext: 插件上下文，提供运行时环境
- AgentBusPlugin: 插件基类，所有插件都应该继承此类
- PluginTool: 插件工具定义
- PluginHook: 插件钩子定义
- PluginStatus: 插件状态枚举
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    Dict, Any, List, Callable, Optional, Union, 
    AsyncIterator, Awaitable, TypeVar, Generic
)
import asyncio
import logging
from enum import Enum
from uuid import uuid4
import inspect

# 类型变量定义
T = TypeVar('T')
PluginResult = Union[T, Exception]


class PluginStatus(Enum):
    """插件状态枚举"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVATING = "activating"
    ACTIVE = "active"
    DEACTIVATING = "deactivating"
    DEACTIVATED = "deactivated"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginContext:
    """
    插件上下文类
    
    为插件提供运行时环境，包括配置、日志器和运行时环境。
    插件通过上下文可以访问系统资源并记录日志。
    
    Attributes:
        config (Dict[str, Any]): 插件配置字典
        logger (logging.Logger): 日志记录器
        runtime (Dict[str, Any]): 运行时环境变量
    """
    config: Dict[str, Any]
    logger: logging.Logger
    runtime: Dict[str, Any]
    
    def __post_init__(self):
        """初始化后的处理"""
        if not isinstance(self.config, dict):
            raise TypeError("Config must be a dictionary")
        if not isinstance(self.logger, logging.Logger):
            raise TypeError("Logger must be a logging.Logger instance")
        if not isinstance(self.runtime, dict):
            raise TypeError("Runtime must be a dictionary")


@dataclass 
class PluginTool:
    """
    插件工具定义
    
    用于定义插件提供的工具，包括工具名称、描述和调用函数。
    
    Attributes:
        name (str): 工具名称
        description (str): 工具描述
        function (Callable): 工具函数
        parameters (Dict[str, Any]): 工具参数定义
        async_func (bool): 是否为异步函数
    """
    name: str
    description: str
    function: Callable
    parameters: Dict[str, Any]
    async_func: bool = False
    
    def __post_init__(self):
        """验证工具定义"""
        if not callable(self.function):
            raise TypeError("Tool function must be callable")
        
        # 检查函数签名
        sig = inspect.signature(self.function)
        self.parameters = {
            name: {
                'type': param.annotation.__name__ if hasattr(param.annotation, '__name__') else str(param.annotation),
                'default': param.default if param.default != inspect.Parameter.empty else None,
                'required': param.default == inspect.Parameter.empty
            }
            for name, param in sig.parameters.items()
        }


@dataclass
class PluginHook:
    """
    插件钩子定义
    
    用于定义插件的事件钩子，包括事件名称和处理函数。
    
    Attributes:
        event (str): 事件名称
        handler (Callable): 事件处理函数
        priority (int): 钩子优先级，数值越大优先级越高
        async_func (bool): 是否为异步函数
    """
    event: str
    handler: Callable
    priority: int = 0
    async_func: bool = False
    
    def __post_init__(self):
        """验证钩子定义"""
        if not callable(self.handler):
            raise TypeError("Hook handler must be callable")
        
        # 检查是否为异步函数
        self.async_func = inspect.iscoroutinefunction(self.handler)


class AgentBusPlugin(ABC):
    """
    AgentBus插件基类
    
    所有AgentBus插件都应该继承此类。该类提供了插件的基本功能，
    包括工具注册、钩子注册、生命周期管理等。
    
    插件子类需要实现以下方法：
    - get_info(): 返回插件信息
    - get_tools(): 返回插件提供的工具列表
    - get_hooks(): 返回插件注册的事件钩子列表
    
    Attributes:
        plugin_id (str): 插件唯一标识符
        context (PluginContext): 插件上下文
        status (PluginStatus): 插件当前状态
        _tools (List[PluginTool]): 注册的工具列表
        _hooks (Dict[str, List[PluginHook]]): 注册的钩子字典
        _commands (List[Dict[str, Any]]): 注册的命令列表
    """
    
    def __init__(self, plugin_id: str, context: PluginContext):
        """
        初始化插件
        
        Args:
            plugin_id: 插件唯一标识符
            context: 插件上下文
        """
        if not plugin_id or not isinstance(plugin_id, str):
            raise ValueError("Plugin ID must be a non-empty string")
        
        if not isinstance(context, PluginContext):
            raise TypeError("Context must be a PluginContext instance")
        
        self.plugin_id = plugin_id
        self.context = context
        self.status = PluginStatus.UNLOADED
        self._tools: List[PluginTool] = []
        self._hooks: Dict[str, List[PluginHook]] = {}
        self._commands: List[Dict[str, Any]] = []
        
        self.context.logger.info(f"Plugin {plugin_id} initialized")
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """
        获取插件信息
        
        Returns:
            包含插件信息的字典，包括名称、版本、描述等
        """
        pass
    
    def get_tools(self) -> List[PluginTool]:
        """
        获取插件提供的工具列表
        
        Returns:
            插件工具列表
        """
        return self._tools.copy()
    
    def get_hooks(self) -> Dict[str, List[PluginHook]]:
        """
        获取插件注册的事件钩子字典
        
        Returns:
            事件钩子字典，键为事件名称，值为钩子列表
        """
        return {event: hooks.copy() for event, hooks in self._hooks.items()}
    
    def get_commands(self) -> List[Dict[str, Any]]:
        """
        获取插件注册的命令列表
        
        Returns:
            命令列表
        """
        return self._commands.copy()
    
    async def activate(self) -> bool:
        """
        激活插件
        
        插件激活时被调用，子类可以重写此方法进行自定义激活逻辑。
        默认实现会记录日志并设置状态为ACTIVE。
        
        Returns:
            激活是否成功
        """
        try:
            self.status = PluginStatus.ACTIVATING
            self.context.logger.info(f"Activating plugin {self.plugin_id}")
            
            # 这里可以添加自定义激活逻辑
            # 例如：初始化资源、建立连接、注册服务等
            
            self.status = PluginStatus.ACTIVE
            self.context.logger.info(f"Plugin {self.plugin_id} activated successfully")
            return True
            
        except Exception as e:
            self.status = PluginStatus.ERROR
            self.context.logger.error(f"Failed to activate plugin {self.plugin_id}: {e}")
            return False
    
    async def deactivate(self) -> bool:
        """
        停用插件
        
        插件停用时被调用，子类可以重写此方法进行自定义停用逻辑。
        默认实现会记录日志并设置状态为DEACTIVATED。
        
        Returns:
            停用是否成功
        """
        try:
            self.status = PluginStatus.DEACTIVATING
            self.context.logger.info(f"Deactivating plugin {self.plugin_id}")
            
            # 这里可以添加自定义停用逻辑
            # 例如：清理资源、断开连接、保存状态等
            
            self.status = PluginStatus.DEACTIVATED
            self.context.logger.info(f"Plugin {self.plugin_id} deactivated successfully")
            return True
            
        except Exception as e:
            self.status = PluginStatus.ERROR
            self.context.logger.error(f"Failed to deactivate plugin {self.plugin_id}: {e}")
            return False
    
    def register_tool(self, name: str, description: str, 
                     function: Callable, **kwargs) -> PluginTool:
        """
        注册工具
        
        Args:
            name: 工具名称
            description: 工具描述
            function: 工具函数
            **kwargs: 额外的工具参数
            
        Returns:
            注册的工具实例
            
        Raises:
            ValueError: 工具名称已存在
        """
        # 检查工具名称是否已存在
        if any(tool.name == name for tool in self._tools):
            raise ValueError(f"Tool '{name}' already registered")
        
        tool = PluginTool(
            name=name,
            description=description,
            function=function,
            parameters={},
            async_func=inspect.iscoroutinefunction(function),
            **kwargs
        )
        
        self._tools.append(tool)
        self.context.logger.debug(f"Registered tool '{name}' for plugin {self.plugin_id}")
        return tool
    
    def register_hook(self, event: str, handler: Callable, 
                     priority: int = 0) -> PluginHook:
        """
        注册事件钩子
        
        Args:
            event: 事件名称
            handler: 事件处理函数
            priority: 钩子优先级，数值越大优先级越高
            
        Returns:
            注册的钩子实例
        """
        hook = PluginHook(
            event=event,
            handler=handler,
            priority=priority,
            async_func=inspect.iscoroutinefunction(handler)
        )
        
        if event not in self._hooks:
            self._hooks[event] = []
        
        self._hooks[event].append(hook)
        # 按优先级排序
        self._hooks[event].sort(key=lambda h: h.priority, reverse=True)
        
        self.context.logger.debug(
            f"Registered hook '{event}' for plugin {self.plugin_id} "
            f"with priority {priority}"
        )
        return hook
    
    def register_command(self, command: str, handler: Callable, 
                       description: str = "", **kwargs) -> Dict[str, Any]:
        """
        注册命令
        
        Args:
            command: 命令名称
            handler: 命令处理函数
            description: 命令描述
            **kwargs: 额外的命令参数
            
        Returns:
            注册的命令字典
        """
        cmd = {
            'command': command,
            'handler': handler,
            'description': description,
            'async_func': inspect.iscoroutinefunction(handler),
            **kwargs
        }
        
        self._commands.append(cmd)
        self.context.logger.debug(
            f"Registered command '{command}' for plugin {self.plugin_id}"
        )
        return cmd
    
    async def execute_tool(self, tool_name: str, *args, **kwargs) -> PluginResult:
        """
        执行插件工具
        
        Args:
            tool_name: 工具名称
            *args: 工具参数
            **kwargs: 工具关键字参数
            
        Returns:
            工具执行结果
            
        Raises:
            ValueError: 工具不存在
        """
        tool = next((t for t in self._tools if t.name == tool_name), None)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        try:
            if tool.async_func:
                return await tool.function(*args, **kwargs)
            else:
                return tool.function(*args, **kwargs)
        except Exception as e:
            self.context.logger.error(f"Tool execution failed: {e}")
            return e
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        return self.context.config.get(key, default)
    
    def set_config(self, key: str, value: Any):
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        self.context.config[key] = value
    
    def get_runtime(self, key: str, default: Any = None) -> Any:
        """
        获取运行时变量
        
        Args:
            key: 运行时键
            default: 默认值
            
        Returns:
            运行时变量值或默认值
        """
        return self.context.runtime.get(key, default)
    
    def set_runtime(self, key: str, value: Any):
        """
        设置运行时变量
        
        Args:
            key: 运行时键
            value: 运行时变量值
        """
        self.context.runtime[key] = value
    
    def __str__(self) -> str:
        """返回插件的字符串表示"""
        return f"AgentBusPlugin({self.plugin_id}, status={self.status.value})"
    
    def __repr__(self) -> str:
        """返回插件的详细字符串表示"""
        return (f"AgentBusPlugin(plugin_id='{self.plugin_id}', "
                f"status={self.status.value}, "
                f"tools={len(self._tools)}, "
                f"hooks={sum(len(hooks) for hooks in self._hooks.values())})")