"""
AgentBus插件管理器

PluginManager类负责管理插件的整个生命周期，包括加载、激活、停用、
卸载等操作。管理器维护插件注册表，调度插件事件，并提供统一的
插件操作接口。

主要功能：
- 插件加载和卸载
- 插件激活和停用
- 插件事件调度
- 插件工具和钩子管理
- 插件依赖解析
- 插件状态监控
"""

import asyncio
import importlib
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import (
    Dict, List, Optional, Type, Any, Callable, Set, 
    Union, Tuple, AsyncIterator
)
from dataclasses import dataclass
from collections import defaultdict
import json

from .core import (
    AgentBusPlugin, PluginContext, PluginTool, PluginHook, 
    PluginStatus, PluginResult
)


@dataclass
class PluginInfo:
    """插件信息数据类"""
    plugin_id: str
    name: str
    version: str
    description: str
    author: str
    class_name: str
    module_path: str
    dependencies: List[str]
    status: PluginStatus = PluginStatus.UNLOADED
    error_message: Optional[str] = None


class PluginLoadError(Exception):
    """插件加载异常"""
    pass


class PluginActivationError(Exception):
    """插件激活异常"""
    pass


class PluginManager:
    """
    插件管理器
    
    负责管理AgentBus插件的完整生命周期，包括加载、激活、停用、
    卸载等操作。管理器维护插件注册表，调度插件事件，并提供
    统一的插件操作接口。
    
    Attributes:
        _plugins (Dict[str, AgentBusPlugin]): 已加载的插件实例
        _plugin_info (Dict[str, PluginInfo]): 插件信息
        _plugin_modules (Dict[str, Type[AgentBusPlugin]]): 插件类映射
        _event_hooks (Dict[str, List[Tuple[str, PluginHook]]]): 事件钩子
        _tool_registry (Dict[str, Tuple[str, AgentBusPlugin]]): 工具注册表
        _command_registry (Dict[str, Tuple[str, AgentBusPlugin]]): 命令注册表
        _context (PluginContext): 全局插件上下文
        _logger (logging.Logger): 日志记录器
        _lock (asyncio.Lock): 异步锁
    """
    
    def __init__(self, context: Optional[PluginContext] = None, 
                 plugin_dirs: Optional[List[str]] = None):
        """
        初始化插件管理器
        
        Args:
            context: 全局插件上下文，如果为None则创建默认上下文
            plugin_dirs: 插件搜索目录列表
        """
        self._plugins: Dict[str, AgentBusPlugin] = {}
        self._plugin_info: Dict[str, PluginInfo] = {}
        self._plugin_modules: Dict[str, Type[AgentBusPlugin]] = {}
        self._event_hooks: Dict[str, List[Tuple[str, PluginHook]]] = defaultdict(list)
        self._tool_registry: Dict[str, Tuple[str, AgentBusPlugin]] = {}
        self._command_registry: Dict[str, Tuple[str, AgentBusPlugin]] = {}
        
        # 设置上下文
        if context is None:
            self._context = PluginContext(
                config={},
                logger=logging.getLogger("agentbus.plugins"),
                runtime={}
            )
        else:
            self._context = context
        
        self._logger = self._context.logger
        self._lock = asyncio.Lock()
        
        # 设置插件搜索目录
        self._plugin_dirs = plugin_dirs or self._get_default_plugin_dirs()
        
        self._logger.info("PluginManager initialized")
    def _get_default_plugin_dirs(self) -> List[str]:
        """获取默认插件搜索目录"""
        dirs = [
            os.path.normcase(os.path.abspath(os.path.join(os.path.dirname(__file__), "extensions"))),
            os.path.normcase(os.path.abspath(os.path.join(os.getcwd(), "plugins"))),
            os.path.normcase(os.path.abspath(os.path.join(os.path.expanduser("~"), ".agentbus", "plugins"))),
        ]
        
        # 添加环境变量中指定的目录
        if env_dirs := os.getenv("AGENTBUS_PLUGIN_DIRS"):
            for d in env_dirs.split(os.pathsep):
                dirs.append(os.path.normcase(os.path.abspath(d)))
        
        return dirs
    
    async def discover_plugins(self) -> List[PluginInfo]:
        """
        发现可用的插件
        
        扫描插件搜索目录，查找所有可用的插件模块。
        
        Returns:
            发现的所有插件信息列表
        """
        discovered = []
        
        for plugin_dir in self._plugin_dirs:
            if not os.path.exists(plugin_dir):
                continue
            
            self._logger.debug(f"Scanning plugin directory: {plugin_dir}")
            
            for root, dirs, files in os.walk(plugin_dir):
                # 查找Python模块文件
                for file in files:
                    if file.endswith('.py') and not file.startswith('_'):
                        module_path = os.path.join(root, file)
                        try:
                            plugin_info = await self._load_plugin_info(module_path)
                            if plugin_info:
                                discovered.append(plugin_info)
                                self._logger.debug(f"Discovered plugin: {plugin_info.plugin_id}")
                        except Exception as e:
                            self._logger.error(f"Failed to load plugin info from {module_path}: {e}")
        
        return discovered
    
    async def _load_plugin_info(self, module_path: str) -> Optional[PluginInfo]:
        """加载插件信息"""
        try:
            # 动态导入模块
            spec = importlib.util.spec_from_file_location("temp_module", module_path)
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找插件类
            plugin_classes = []
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, AgentBusPlugin) and 
                    obj != AgentBusPlugin):
                    plugin_classes.append((name, obj))
            
            if not plugin_classes:
                return None
            
            # 取第一个插件类（如果有多个）
            class_name, plugin_class = plugin_classes[0]
            
            # 获取插件信息
            info = self._extract_plugin_info(plugin_class, module_path, class_name)
            return info
            
        except Exception as e:
            self._logger.error(f"Failed to load plugin info: {e}")
            return None
        finally:
            # 清理模块
            if 'temp_module' in sys.modules:
                del sys.modules['temp_module']
    
    def _extract_plugin_info(self, plugin_class: Type[AgentBusPlugin], 
                           module_path: str, class_name: str) -> PluginInfo:
        """从插件类提取插件信息"""
        # 创建临时实例获取信息
        temp_context = PluginContext(
            config={},
            logger=self._logger,
            runtime={}
        )
        
        try:
            temp_plugin = plugin_class("temp", temp_context)
            plugin_info = temp_plugin.get_info()
            
            return PluginInfo(
                plugin_id=plugin_info.get('id', class_name.lower()),
                name=plugin_info.get('name', class_name),
                version=plugin_info.get('version', '1.0.0'),
                description=plugin_info.get('description', ''),
                author=plugin_info.get('author', 'Unknown'),
                class_name=class_name,
                module_path=module_path,
                dependencies=plugin_info.get('dependencies', [])
            )
        except Exception as e:
            self._logger.error(f"Failed to extract plugin info: {e}")
            raise PluginLoadError(f"Invalid plugin class: {e}")
    
    async def load_plugin(self, plugin_id: str, module_path: str, 
                        class_name: str = None) -> AgentBusPlugin:
        """
        加载插件
        
        Args:
            plugin_id: 插件标识符
            module_path: 插件模块路径
            class_name: 插件类名，如果为None则自动检测
            
        Returns:
            加载的插件实例
            
        Raises:
            PluginLoadError: 插件加载失败
        """
        async with self._lock:
            if plugin_id in self._plugins:
                self._logger.info(f"Plugin {plugin_id} already loaded")
                return self._plugins[plugin_id]
            
            # 确定模块路径
            if not module_path:
                module_path = self._find_plugin_module(plugin_id)
            
            if not module_path:
                raise PluginLoadError(f"Cannot find plugin module: {plugin_id}")
            
            if not os.path.isabs(module_path):
                # 尝试相对于搜索目录查找
                found = False
                for d in self._plugin_dirs:
                    full_path = os.path.join(d, module_path)
                    if os.path.exists(full_path):
                        module_path = full_path
                        found = True
                        break
                if not found:
                    raise PluginLoadError(f"Cannot find plugin module: {module_path}")
            
            if not os.path.exists(module_path):
                raise PluginLoadError(f"Cannot find module: {module_path}")
                
            try:
                self._logger.info(f"Loading plugin: {plugin_id}")
                
                # 加载插件模块
                plugin_class = await self._import_plugin_class(module_path, class_name)
                
                # 创建插件实例
                context = PluginContext(
                    config=self._context.config.get(plugin_id, {}),
                    logger=logging.getLogger(f"agentbus.plugins.{plugin_id}"),
                    runtime=self._context.runtime
                )
                
                plugin = plugin_class(plugin_id, context)
                
                # 验证插件
                self._validate_plugin(plugin)
                
                # 注册插件
                self._plugins[plugin_id] = plugin
                self._plugin_modules[plugin_id] = plugin_class
                
                # 核心修复：更新或创建插件信息，确保 status 正确
                if plugin_id not in self._plugin_info:
                    info = plugin.get_info()
                    self._plugin_info[plugin_id] = PluginInfo(
                        plugin_id=plugin_id,
                        name=info.get('name', plugin_id),
                        version=info.get('version', '0.0.0'),
                        description=info.get('description', ''),
                        author=info.get('author', ''),
                        dependencies=info.get('dependencies', []),
                        module_path=module_path,
                        class_name=class_name or plugin_class.__name__
                    )
                
                # 核心修复：同时更新插件实例和信息的状态
                self._plugin_info[plugin_id].status = PluginStatus.LOADED
                if hasattr(plugin, 'status'):
                    plugin.status = PluginStatus.LOADED
                
                self._logger.info(f"Plugin {plugin_id} loaded successfully")
                return plugin
                
            except Exception as e:
                # 如果是业务逻辑抛出的异常，直接透传或包装
                if isinstance(e, PluginLoadError):
                    raise
                self._logger.error(f"Failed to load plugin {plugin_id}: {e}")
                raise PluginLoadError(f"Plugin loading failed: {e}")
    
    async def _import_plugin_class(self, module_path: str, class_name: str = None) -> Type[AgentBusPlugin]:
        """导入插件类"""
        # 计算模块名
        module_name = f"agentbus_plugin_{hash(module_path)}"
        
        # 动态导入模块
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if not spec or not spec.loader:
            raise PluginLoadError(f"Cannot find module: {module_path}")
        
        module = importlib.util.module_from_spec(spec)
        module.__package__ = 'plugins'  # 核心修复：设置正确的包名以支持相对导入
        spec.loader.exec_module(module)
        
        # 查找插件类
        if class_name:
            if not hasattr(module, class_name):
                raise PluginLoadError(f"Class {class_name} not found in module")
            plugin_class = getattr(module, class_name)
        else:
            plugin_classes = []
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, AgentBusPlugin) and 
                    obj != AgentBusPlugin):
                    plugin_classes.append(obj)
            
            if not plugin_classes:
                raise PluginLoadError("No valid plugin class found")
            
            plugin_class = plugin_classes[0]
        
        if not issubclass(plugin_class, AgentBusPlugin):
            raise PluginLoadError("Invalid plugin class")
        
        return plugin_class
    
    def _validate_plugin(self, plugin: AgentBusPlugin):
        """验证插件"""
        # 检查插件信息
        info = plugin.get_info()
        required_fields = ['id', 'name', 'version']
        
        for field in required_fields:
            if field not in info:
                raise PluginLoadError(f"Missing required field: {field}")
        
        # 检查工具
        tools = plugin.get_tools()
        tool_names = set()
        for tool in tools:
            if tool.name in tool_names:
                raise PluginLoadError(f"Duplicate tool name: {tool.name}")
            tool_names.add(tool.name)
        
        # 检查钩子
        hooks = plugin.get_hooks()
        for event, event_hooks in hooks.items():
            hook_handlers = set()
            for hook in event_hooks:
                handler_id = id(hook.handler)
                if handler_id in hook_handlers:
                    raise PluginLoadError(f"Duplicate hook handler for event: {event}")
                hook_handlers.add(handler_id)
    
    async def unload_plugin(self, plugin_id: str) -> bool:
        """
        卸载插件
        
        Args:
            plugin_id: 插件标识符
            
        Returns:
            卸载是否成功
        """
        async with self._lock:
            if plugin_id not in self._plugins:
                self._logger.warning(f"Plugin {plugin_id} not loaded")
                return False
            
            try:
                self._logger.info(f"Unloading plugin: {plugin_id}")
                
                # 停用插件（如果已激活）
                if self._plugins[plugin_id].status == PluginStatus.ACTIVE:
                    await self.deactivate_plugin(plugin_id)
                
                # 清理注册表
                self._cleanup_plugin_registrations(plugin_id)
                
                # 核心修复：更新插件状态
                plugin = self._plugins[plugin_id]
                if hasattr(plugin, 'status'):
                    plugin.status = PluginStatus.UNLOADED
                
                # 移除插件
                del self._plugins[plugin_id]
                del self._plugin_modules[plugin_id]
                
                # 更新插件信息
                if plugin_id in self._plugin_info:
                    self._plugin_info[plugin_id].status = PluginStatus.UNLOADED
                
                self._logger.info(f"Plugin {plugin_id} unloaded successfully")
                return True
                
            except Exception as e:
                self._logger.error(f"Failed to unload plugin {plugin_id}: {e}")
                return False
    
    def _cleanup_plugin_registrations(self, plugin_id: str):
        """清理插件注册"""
        # 清理工具注册
        tools_to_remove = [
            tool_name for tool_name, (owner_id, _) in self._tool_registry.items()
            if owner_id == plugin_id
        ]
        for tool_name in tools_to_remove:
            del self._tool_registry[tool_name]
        
        # 清理命令注册
        commands_to_remove = [
            cmd_name for cmd_name, (owner_id, _) in self._command_registry.items()
            if owner_id == plugin_id
        ]
        for cmd_name in commands_to_remove:
            del self._command_registry[cmd_name]
        
        # 清理钩子注册
        for event in list(self._event_hooks.keys()):
            self._event_hooks[event] = [
                (owner_id, hook) for owner_id, hook in self._event_hooks[event]
                if owner_id != plugin_id
            ]
            # 如果没有钩子了，删除事件
            if not self._event_hooks[event]:
                del self._event_hooks[event]
    
    async def activate_plugin(self, plugin_id: str) -> bool:
        """
        激活插件
        
        Args:
            plugin_id: 插件标识符
            
        Returns:
            激活是否成功
        """
        if plugin_id not in self._plugins:
            self._logger.error(f"Plugin {plugin_id} not loaded")
            return False
        
        plugin = self._plugins[plugin_id]
        
        try:
            self._logger.info(f"Activating plugin: {plugin_id}")
            
            # 激活插件
            success = await plugin.activate()
            # 核心修复：如果 activate() 返回 None 或者 True，都视为成功
            if success is False:
                raise PluginActivationError("Plugin.activate() returned False")
            
            # 注册插件的工具和钩子
            await self._register_plugin_resources(plugin_id)
            
            # 更新插件信息
            if plugin_id in self._plugin_info:
                self._plugin_info[plugin_id].status = PluginStatus.ACTIVE
            
            self._logger.info(f"Plugin {plugin_id} activated successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to activate plugin {plugin_id}: {e}")
            plugin.status = PluginStatus.ERROR
            
            if plugin_id in self._plugin_info:
                self._plugin_info[plugin_id].status = PluginStatus.ERROR
                self._plugin_info[plugin_id].error_message = str(e)
            
            return False
    
    async def _register_plugin_resources(self, plugin_id: str):
        """注册插件资源"""
        plugin = self._plugins[plugin_id]
        
        # 注册工具
        tools = plugin.get_tools()
        for tool in tools:
            if tool.name in self._tool_registry:
                self._logger.warning(
                    f"Tool '{tool.name}' already registered by "
                    f"{self._tool_registry[tool.name][0]}"
                )
                continue
            
            self._tool_registry[tool.name] = (plugin_id, plugin)
            self._logger.debug(f"Registered tool '{tool.name}' from plugin {plugin_id}")
        
        # 注册命令
        commands = plugin.get_commands()
        for cmd in commands:
            command_name = cmd['command']
            if command_name in self._command_registry:
                self._logger.warning(
                    f"Command '{command_name}' already registered by "
                    f"{self._command_registry[command_name][0]}"
                )
                continue
            
            self._command_registry[command_name] = (plugin_id, plugin)
            self._logger.debug(f"Registered command '{command_name}' from plugin {plugin_id}")
        
        # 注册钩子
        hooks = plugin.get_hooks()
        for event, event_hooks in hooks.items():
            for hook in event_hooks:
                self._event_hooks[event].append((plugin_id, hook))
            
            # 按优先级排序
            self._event_hooks[event].sort(
                key=lambda x: x[1].priority, reverse=True
            )
            
            self._logger.debug(
                f"Registered {len(event_hooks)} hooks for event '{event}' "
                f"from plugin {plugin_id}"
            )
    
    async def deactivate_plugin(self, plugin_id: str) -> bool:
        """
        停用插件
        
        Args:
            plugin_id: 插件标识符
            
        Returns:
            停用是否成功
        """
        if plugin_id not in self._plugins:
            self._logger.error(f"Plugin {plugin_id} not loaded")
            return False
        
        plugin = self._plugins[plugin_id]
        
        try:
            self._logger.info(f"Deactivating plugin: {plugin_id}")
            
            # 停用插件
            success = await plugin.deactivate()
            if not success:
                self._logger.error(f"Plugin {plugin_id} deactivation failed")
            
            # 清理注册表
            self._cleanup_plugin_registrations(plugin_id)
            
            # 更新插件信息
            if plugin_id in self._plugin_info:
                self._plugin_info[plugin_id].status = PluginStatus.DEACTIVATED
            
            self._logger.info(f"Plugin {plugin_id} deactivated successfully")
            return success
            
        except Exception as e:
            self._logger.error(f"Failed to deactivate plugin {plugin_id}: {e}")
            plugin.status = PluginStatus.ERROR
            return False
    
    async def reload_plugin(self, plugin_id: str) -> bool:
        """
        重新加载插件
        
        Args:
            plugin_id: 插件标识符
            
        Returns:
            重新加载是否成功
        """
        if plugin_id not in self._plugin_info:
            self._logger.error(f"Plugin {plugin_id} not found")
            return False
        
        plugin_info = self._plugin_info[plugin_id]
        was_active = self._plugins[plugin_id].status == PluginStatus.ACTIVE
        
        try:
            # 卸载插件
            if not await self.unload_plugin(plugin_id):
                return False
            
            # 重新加载插件
            plugin = await self.load_plugin(
                plugin_id, 
                plugin_info.module_path, 
                plugin_info.class_name
            )
            
            # 重新激活（如果之前是激活状态）
            if was_active:
                await self.activate_plugin(plugin_id)
            
            self._logger.info(f"Plugin {plugin_id} reloaded successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to reload plugin {plugin_id}: {e}")
            return False
    
    async def execute_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """
        执行事件钩子
        
        Args:
            event: 事件名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            所有钩子的执行结果列表
        """
        if event not in self._event_hooks:
            return []
        
        results = []
        
        for plugin_id, hook in self._event_hooks[event]:
            try:
                if hook.async_func:
                    result = await hook.handler(*args, **kwargs)
                else:
                    result = hook.handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                self._logger.error(
                    f"Hook execution failed for plugin {plugin_id}: {e}"
                )
        
        return results
    
    async def execute_tool(self, tool_name: str, *args, **kwargs) -> PluginResult:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            工具执行结果
            
        Raises:
            ValueError: 工具不存在
        """
        if tool_name not in self._tool_registry:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        plugin_id, plugin = self._tool_registry[tool_name]
        
        try:
            return await plugin.execute_tool(tool_name, *args, **kwargs)
        except Exception as e:
            self._logger.error(f"Tool execution failed: {e}")
            return e
    
    def get_plugin(self, plugin_id: str) -> Optional[AgentBusPlugin]:
        """
        获取插件实例
        
        Args:
            plugin_id: 插件标识符
            
        Returns:
            插件实例，如果不存在则返回None
        """
        return self._plugins.get(plugin_id)
    
    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """
        获取插件信息
        
        Args:
            plugin_id: 插件标识符
            
        Returns:
            插件信息，如果不存在则返回None
        """
        return self._plugin_info.get(plugin_id)
    
    def list_plugins(self) -> List[str]:
        """
        列出所有已加载的插件ID
        
        Returns:
            插件ID列表
        """
        return list(self._plugins.keys())
    
    def list_plugin_info(self) -> List[PluginInfo]:
        """
        列出所有插件信息
        
        Returns:
            插件信息列表
        """
        return list(self._plugin_info.values())
    
    def get_tools(self) -> Dict[str, Tuple[str, PluginTool]]:
        """
        获取所有工具注册信息
        
        Returns:
            工具注册信息字典，键为工具名，值为(插件ID, 工具)元组
        """
        result = {}
        for plugin_id, plugin in self._plugins.items():
            for tool in plugin.get_tools():
                result[tool.name] = (plugin_id, tool)
        return result
    
    def get_commands(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有命令注册信息
        
        Returns:
            命令注册信息字典，键为命令名，值为命令信息
        """
        result = {}
        for plugin_id, plugin in self._plugins.items():
            for cmd in plugin.get_commands():
                result[cmd['command']] = {
                    'plugin_id': plugin_id,
                    'handler': cmd['handler'],
                    'description': cmd.get('description', ''),
                    'async_func': cmd.get('async_func', False)
                }
        return result
    
    def get_hooks(self) -> Dict[str, List[Tuple[str, PluginHook]]]:
        """
        获取所有钩子注册信息
        
        Returns:
            钩子注册信息字典，键为事件名，值为(插件ID, 钩子)元组列表
        """
        return dict(self._event_hooks)
    
    def get_plugin_status(self, plugin_id: str) -> Optional[PluginStatus]:
        """
        获取插件状态
        
        Args:
            plugin_id: 插件标识符
            
        Returns:
            插件状态，如果插件不存在则返回None
        """
        if plugin_id not in self._plugins:
            return None
        return self._plugins[plugin_id].status
    
    async def get_plugin_stats(self) -> Dict[str, Any]:
        """
        获取插件系统统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            'total_plugins': len(self._plugins),
            'active_plugins': len([p for p in self._plugins.values() 
                                 if p.status == PluginStatus.ACTIVE]),
            'loaded_plugins': len([p for p in self._plugins.values() 
                                if p.status == PluginStatus.LOADED]),
            'error_plugins': len([p for p in self._plugins.values() 
                               if p.status == PluginStatus.ERROR]),
            'total_tools': len(self._tool_registry),
            'total_commands': len(self._command_registry),
            'total_hooks': sum(len(hooks) for hooks in self._event_hooks.values()),
            'plugins_by_status': {}
        }
        
        # 按状态统计插件数量
        for status in PluginStatus:
            count = len([p for p in self._plugins.values() if p.status == status])
            stats['plugins_by_status'][status.value] = count
        
        return stats