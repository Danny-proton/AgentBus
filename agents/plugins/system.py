"""
AgentBus Plugin System
Agent插件系统
"""

from typing import Dict, List, Optional, Any, Callable, Set, Type, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import asyncio
import importlib
import inspect
import sys
import os
import json
import yaml
import shutil
from pathlib import Path
from abc import ABC, abstractmethod

from ..core.types import (
    PluginType, PluginManifest, AgentType, MessageType, Priority,
    AgentMessage, AgentStatus, AlertLevel
)


class PluginSystem:
    """插件系统"""
    
    def __init__(self, system_id: str = "default"):
        self.system_id = system_id
        self.logger = self._get_logger()
        
        # 插件管理
        self.plugin_manager = PluginManager()
        self.loaded_plugins: Dict[str, 'PluginInstance'] = {}
        self.plugin_dependencies: Dict[str, Set[str]] = {}
        
        # 插件路径
        self.plugin_paths = [
            Path("./plugins"),
            Path("./agent_plugins"),
            Path("./extensions")
        ]
        
        # 插件事件
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.plugin_hooks: Dict[str, List[Callable]] = {}
        
        # 安全和权限
        self.plugin_sandbox = PluginSandbox()
        self.permission_manager = PermissionManager()
        
        # 插件生命周期
        self.lifecycle_hooks = {
            "on_load": [],
            "on_unload": [],
            "on_enable": [],
            "on_disable": [],
            "on_agent_start": [],
            "on_agent_stop": []
        }
        
        # 统计信息
        self.stats = {
            "total_plugins": 0,
            "loaded_plugins": 0,
            "failed_loads": 0,
            "total_plugin_events": 0,
            "plugin_uptime": {}
        }
        
        # 运行状态
        self.running = False
    
    def _get_logger(self):
        """获取日志记录器"""
        return f"plugin.system.{self.system_id}"
    
    async def start(self):
        """启动插件系统"""
        if self.running:
            return
        
        self.running = True
        
        # 自动加载插件
        await self.auto_discover_plugins()
        
        self.logger.info("Plugin system started")
    
    async def stop(self):
        """停止插件系统"""
        if not self.running:
            return
        
        self.running = False
        
        # 卸载所有插件
        for plugin_id in list(self.loaded_plugins.keys()):
            await self.unload_plugin(plugin_id)
        
        self.logger.info("Plugin system stopped")
    
    async def auto_discover_plugins(self):
        """自动发现插件"""
        discovered_plugins = []
        
        for plugin_path in self.plugin_paths:
            if not plugin_path.exists():
                continue
            
            for plugin_file in plugin_path.glob("**/*.py"):
                if plugin_file.name.startswith("__"):
                    continue
                
                try:
                    # 加载插件模块
                    module = await self._load_plugin_module(plugin_file)
                    if module:
                        # 检查是否有插件清单
                        manifest = self._extract_plugin_manifest(module)
                        if manifest:
                            discovered_plugins.append({
                                "path": plugin_file,
                                "module": module,
                                "manifest": manifest
                            })
                            
                except Exception as e:
                    self.logger.error(f"Failed to discover plugin {plugin_file}: {e}")
        
        self.logger.info(f"Discovered {len(discovered_plugins)} plugins")
        return discovered_plugins
    
    async def load_plugin(self, plugin_path: Union[str, Path], config: Dict[str, Any] = None) -> bool:
        """加载插件"""
        try:
            plugin_path = Path(plugin_path)
            
            if not plugin_path.exists():
                self.logger.error(f"Plugin path does not exist: {plugin_path}")
                return False
            
            # 加载插件模块
            module = await self._load_plugin_module(plugin_path)
            if not module:
                return False
            
            # 提取插件清单
            manifest = self._extract_plugin_manifest(module)
            if not manifest:
                self.logger.error(f"No plugin manifest found in {plugin_path}")
                return False
            
            # 验证插件清单
            if not self._validate_plugin_manifest(manifest):
                self.logger.error(f"Invalid plugin manifest: {manifest.plugin_id}")
                return False
            
            # 检查依赖
            if not await self._check_plugin_dependencies(manifest):
                return False
            
            # 创建插件实例
            plugin_instance = await self._create_plugin_instance(manifest, module, config or {})
            if not plugin_instance:
                return False
            
            # 在沙箱中初始化插件
            if not await self.plugin_sandbox.initialize_plugin(plugin_instance):
                self.logger.error(f"Failed to initialize plugin sandbox: {manifest.plugin_id}")
                return False
            
            # 加载插件
            success = await plugin_instance.load()
            if not success:
                self.logger.error(f"Failed to load plugin: {manifest.plugin_id}")
                return False
            
            # 注册插件
            self.loaded_plugins[manifest.plugin_id] = plugin_instance
            self.stats["loaded_plugins"] = len(self.loaded_plugins)
            self.stats["total_plugins"] += 1
            
            # 触发加载事件
            await self._emit_plugin_event("on_load", plugin_instance)
            
            self.logger.info(f"Plugin loaded successfully: {manifest.plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load plugin {plugin_path}: {e}")
            self.stats["failed_loads"] += 1
            return False
    
    async def unload_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        if plugin_id not in self.loaded_plugins:
            return False
        
        try:
            plugin_instance = self.loaded_plugins[plugin_id]
            
            # 卸载插件
            success = await plugin_instance.unload()
            if not success:
                self.logger.warning(f"Plugin unload reported failure: {plugin_id}")
            
            # 从沙箱中清理
            await self.plugin_sandbox.cleanup_plugin(plugin_instance)
            
            # 移除插件
            del self.loaded_plugins[plugin_id]
            self.stats["loaded_plugins"] = len(self.loaded_plugins)
            
            # 触发卸载事件
            await self._emit_plugin_event("on_unload", plugin_instance)
            
            self.logger.info(f"Plugin unloaded: {plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unload plugin {plugin_id}: {e}")
            return False
    
    async def enable_plugin(self, plugin_id: str) -> bool:
        """启用插件"""
        if plugin_id not in self.loaded_plugins:
            return False
        
        try:
            plugin_instance = self.loaded_plugins[plugin_id]
            
            # 启用插件
            success = await plugin_instance.enable()
            if not success:
                return False
            
            # 触发启用事件
            await self._emit_plugin_event("on_enable", plugin_instance)
            
            self.logger.info(f"Plugin enabled: {plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enable plugin {plugin_id}: {e}")
            return False
    
    async def disable_plugin(self, plugin_id: str) -> bool:
        """禁用插件"""
        if plugin_id not in self.loaded_plugins:
            return False
        
        try:
            plugin_instance = self.loaded_plugins[plugin_id]
            
            # 禁用插件
            success = await plugin_instance.disable()
            if not success:
                return False
            
            # 触发禁用事件
            await self._emit_plugin_event("on_disable", plugin_instance)
            
            self.logger.info(f"Plugin disabled: {plugin_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disable plugin {plugin_id}: {e}")
            return False
    
    def get_plugin(self, plugin_id: str) -> Optional['PluginInstance']:
        """获取插件实例"""
        return self.loaded_plugins.get(plugin_id)
    
    def list_plugins(self, plugin_type: Optional[PluginType] = None) -> List[Dict[str, Any]]:
        """列出插件"""
        plugins = []
        
        for plugin_id, plugin_instance in self.loaded_plugins.items():
            if plugin_type and plugin_instance.manifest.plugin_type != plugin_type:
                continue
            
            plugins.append({
                "plugin_id": plugin_id,
                "name": plugin_instance.manifest.name,
                "version": plugin_instance.manifest.version,
                "type": plugin_instance.manifest.plugin_type.value,
                "status": plugin_instance.status,
                "description": plugin_instance.manifest.description,
                "author": plugin_instance.manifest.author,
                "enabled": plugin_instance.enabled,
                "loaded_at": plugin_instance.loaded_at.isoformat()
            })
        
        return plugins
    
    def add_plugin_path(self, path: Union[str, Path]):
        """添加插件路径"""
        plugin_path = Path(path)
        if plugin_path not in self.plugin_paths:
            self.plugin_paths.append(plugin_path)
            self.logger.info(f"Plugin path added: {plugin_path}")
    
    def register_event_handler(self, event_name: str, handler: Callable):
        """注册事件处理器"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    def register_plugin_hook(self, hook_name: str, handler: Callable):
        """注册插件钩子"""
        if hook_name not in self.plugin_hooks:
            self.plugin_hooks[hook_name] = []
        self.plugin_hooks[hook_name].append(handler)
    
    async def call_plugin_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """调用插件钩子"""
        results = []
        
        handlers = self.plugin_hooks.get(hook_name, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(*args, **kwargs)
                else:
                    result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Plugin hook {hook_name} handler failed: {e}")
        
        return results
    
    async def send_plugin_message(self, plugin_id: str, message: AgentMessage) -> bool:
        """向插件发送消息"""
        plugin_instance = self.get_plugin(plugin_id)
        if not plugin_instance:
            return False
        
        try:
            await plugin_instance.handle_message(message)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send message to plugin {plugin_id}: {e}")
            return False
    
    def get_plugin_capabilities(self, plugin_id: str) -> List[str]:
        """获取插件能力"""
        plugin_instance = self.get_plugin(plugin_id)
        if not plugin_instance:
            return []
        
        return plugin_instance.get_capabilities()
    
    def get_plugin_stats(self) -> Dict[str, Any]:
        """获取插件统计"""
        return {
            "system_id": self.system_id,
            "total_plugins": self.stats["total_plugins"],
            "loaded_plugins": self.stats["loaded_plugins"],
            "failed_loads": self.stats["failed_loads"],
            "plugin_paths": [str(p) for p in self.plugin_paths],
            "plugins": self.list_plugins(),
            "uptime_stats": self.stats["plugin_uptime"]
        }
    
    # === 私有方法 ===
    
    async def _load_plugin_module(self, plugin_path: Path):
        """加载插件模块"""
        try:
            # 动态导入插件模块
            spec = importlib.util.spec_from_file_location(plugin_path.stem, plugin_path)
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            
            # 添加到sys.modules以便后续导入
            sys.modules[plugin_path.stem] = module
            
            # 执行模块
            spec.loader.exec_module(module)
            
            return module
            
        except Exception as e:
            self.logger.error(f"Failed to load plugin module {plugin_path}: {e}")
            return None
    
    def _extract_plugin_manifest(self, module) -> Optional[PluginManifest]:
        """提取插件清单"""
        # 查找插件清单
        manifest_data = getattr(module, 'PLUGIN_MANIFEST', None)
        
        if isinstance(manifest_data, dict):
            try:
                return PluginManifest(**manifest_data)
            except Exception as e:
                self.logger.error(f"Invalid plugin manifest: {e}")
                return None
        
        # 尝试从文件加载
        manifest_file = getattr(module, 'MANIFEST_FILE', 'plugin.yaml')
        if os.path.exists(manifest_file):
            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest_data = yaml.safe_load(f)
                return PluginManifest(**manifest_data)
            except Exception as e:
                self.logger.error(f"Failed to load manifest file {manifest_file}: {e}")
                return None
        
        # 如果没有清单，创建一个默认的
        module_name = module.__name__
        return PluginManifest(
            plugin_id=module_name.lower(),
            name=module_name,
            version="1.0.0",
            description="Auto-discovered plugin",
            plugin_type=PluginType.CUSTOM
        )
    
    def _validate_plugin_manifest(self, manifest: PluginManifest) -> bool:
        """验证插件清单"""
        required_fields = ['plugin_id', 'name', 'version', 'plugin_type']
        
        for field in required_fields:
            if not getattr(manifest, field, None):
                self.logger.error(f"Missing required field in manifest: {field}")
                return False
        
        # 验证插件ID格式
        if not manifest.plugin_id.replace('_', '').replace('-', '').isalnum():
            self.logger.error(f"Invalid plugin ID format: {manifest.plugin_id}")
            return False
        
        return True
    
    async def _check_plugin_dependencies(self, manifest: PluginManifest) -> bool:
        """检查插件依赖"""
        missing_deps = []
        
        for dep in manifest.dependencies:
            # 检查是否已加载
            if dep not in self.loaded_plugins:
                missing_deps.append(dep)
        
        if missing_deps:
            self.logger.error(f"Missing dependencies for plugin {manifest.plugin_id}: {missing_deps}")
            return False
        
        return True
    
    async def _create_plugin_instance(self, manifest: PluginManifest, module, config: Dict[str, Any]) -> Optional['PluginInstance']:
        """创建插件实例"""
        try:
            # 查找插件类
            plugin_class = getattr(module, 'Plugin', None)
            
            if plugin_class and inspect.isclass(plugin_class):
                # 实例化插件
                instance = plugin_class(manifest, config)
                if isinstance(instance, PluginBase):
                    return PluginInstance(instance, manifest, module)
            
            # 如果没有找到插件类，创建一个默认实例
            return PluginInstance(PluginBase(manifest, config), manifest, module)
            
        except Exception as e:
            self.logger.error(f"Failed to create plugin instance: {e}")
            return None
    
    async def _emit_plugin_event(self, event_name: str, plugin_instance: 'PluginInstance'):
        """触发插件事件"""
        # 调用事件处理器
        handlers = self.event_handlers.get(event_name, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(plugin_instance)
                else:
                    handler(plugin_instance)
            except Exception as e:
                self.logger.error(f"Plugin event handler {event_name} failed: {e}")
        
        # 调用插件生命周期钩子
        lifecycle_hooks = self.lifecycle_hooks.get(event_name, [])
        for hook in lifecycle_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(plugin_instance)
                else:
                    hook(plugin_instance)
            except Exception as e:
                self.logger.error(f"Plugin lifecycle hook {event_name} failed: {e}")
        
        self.stats["total_plugin_events"] += 1


class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins: Dict[str, 'PluginInstance'] = {}
        self.plugin_metadata: Dict[str, Dict[str, Any]] = {}
    
    def register_plugin(self, plugin_instance: 'PluginInstance'):
        """注册插件"""
        self.plugins[plugin_instance.manifest.plugin_id] = plugin_instance
        self.plugin_metadata[plugin_instance.manifest.plugin_id] = {
            "loaded_at": datetime.now(),
            "version": plugin_instance.manifest.version
        }
    
    def unregister_plugin(self, plugin_id: str):
        """注销插件"""
        self.plugins.pop(plugin_id, None)
        self.plugin_metadata.pop(plugin_id, None)


class PluginSandbox:
    """插件沙箱"""
    
    def __init__(self):
        self.plugin_contexts: Dict[str, Dict[str, Any]] = {}
        self.restricted_builtins = {
            'eval', 'exec', 'open', 'input', '__import__', 
            'compile', 'globals', 'locals', 'vars'
        }
    
    async def initialize_plugin(self, plugin_instance: 'PluginInstance') -> bool:
        """初始化插件沙箱"""
        try:
            # 创建插件上下文
            context = {
                "plugin_id": plugin_instance.manifest.plugin_id,
                "permissions": plugin_instance.permissions,
                "restricted_builtins": self.restricted_builtins,
                "safe_globals": {
                    "__builtins__": self._get_safe_builtins()
                }
            }
            
            self.plugin_contexts[plugin_instance.manifest.plugin_id] = context
            return True
            
        except Exception as e:
            return False
    
    async def cleanup_plugin(self, plugin_instance: 'PluginInstance'):
        """清理插件沙箱"""
        self.plugin_contexts.pop(plugin_instance.manifest.plugin_id, None)
    
    def _get_safe_builtins(self) -> Dict[str, Any]:
        """获取安全的内置函数"""
        safe_builtins = {}
        builtin_names = [
            'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
            'callable', 'chr', 'complex', 'dict', 'divmod', 'enumerate', 'filter',
            'float', 'format', 'frozenset', 'hash', 'hex', 'id', 'int', 'isinstance',
            'issubclass', 'iter', 'len', 'list', 'map', 'max', 'min', 'next',
            'object', 'oct', 'ord', 'pow', 'print', 'range', 'repr', 'reversed',
            'round', 'set', 'slice', 'sorted', 'str', 'sum', 'tuple', 'type', 'zip'
        ]
        
        import builtins
        for name in builtin_names:
            safe_builtins[name] = getattr(builtins, name)
        
        return safe_builtins


class PermissionManager:
    """权限管理器"""
    
    def __init__(self):
        self.plugin_permissions: Dict[str, Set[str]] = {}
        self.default_permissions = {
            PluginType.CAPABILITY: {'read', 'write', 'execute'},
            PluginType.COMMUNICATION: {'read', 'write', 'send', 'receive'},
            PluginType.MONITORING: {'read', 'monitor'},
            PluginType.RESOURCE: {'read', 'allocate'},
            PluginType.UI: {'read', 'write', 'render'},
            PluginType.INTEGRATION: {'read', 'write', 'api_call'},
            PluginType.CUSTOM: {'read'}
        }
    
    def grant_permission(self, plugin_id: str, permission: str):
        """授予权限"""
        if plugin_id not in self.plugin_permissions:
            self.plugin_permissions[plugin_id] = set()
        self.plugin_permissions[plugin_id].add(permission)
    
    def revoke_permission(self, plugin_id: str, permission: str):
        """撤销权限"""
        if plugin_id in self.plugin_permissions:
            self.plugin_permissions[plugin_id].discard(permission)
    
    def check_permission(self, plugin_id: str, permission: str) -> bool:
        """检查权限"""
        plugin_perms = self.plugin_permissions.get(plugin_id, set())
        default_perms = self.default_permissions.get(
            self._get_plugin_type(plugin_id), set()
        )
        
        return permission in plugin_perms or permission in default_perms
    
    def _get_plugin_type(self, plugin_id: str) -> PluginType:
        """获取插件类型（简化实现）"""
        # 这里应该从插件清单中获取类型
        return PluginType.CUSTOM


class PluginInstance:
    """插件实例"""
    
    def __init__(self, plugin: 'PluginBase', manifest: PluginManifest, module: Any):
        self.plugin = plugin
        self.manifest = manifest
        self.module = module
        self.status = "loaded"
        self.enabled = False
        self.loaded_at = datetime.now()
        self.permissions: Set[str] = set()
        
        # 事件处理
        self.event_handlers: Dict[str, List[Callable]] = {}
    
    async def load(self) -> bool:
        """加载插件"""
        try:
            self.status = "loading"
            success = await self.plugin.on_load()
            if success:
                self.status = "loaded"
            return success
        except Exception as e:
            self.status = "error"
            return False
    
    async def unload(self) -> bool:
        """卸载插件"""
        try:
            self.status = "unloading"
            success = await self.plugin.on_unload()
            if success:
                self.status = "unloaded"
            return success
        except Exception as e:
            self.status = "error"
            return False
    
    async def enable(self) -> bool:
        """启用插件"""
        try:
            self.enabled = True
            success = await self.plugin.on_enable()
            return success
        except Exception as e:
            self.enabled = False
            return False
    
    async def disable(self) -> bool:
        """禁用插件"""
        try:
            self.enabled = False
            success = await self.plugin.on_disable()
            return success
        except Exception as e:
            self.enabled = True
            return False
    
    async def handle_message(self, message: AgentMessage):
        """处理消息"""
        if not self.enabled:
            return
        
        await self.plugin.on_message(message)
    
    def get_capabilities(self) -> List[str]:
        """获取能力"""
        return self.manifest.capabilities.copy()
    
    def add_event_handler(self, event_name: str, handler: Callable):
        """添加事件处理器"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    async def call_event(self, event_name: str, *args, **kwargs):
        """调用事件"""
        handlers = self.event_handlers.get(event_name, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args, **kwargs)
                else:
                    handler(*args, **kwargs)
            except Exception as e:
                pass  # 记录错误但不中断其他处理器


class PluginBase(ABC):
    """插件基类"""
    
    def __init__(self, manifest: PluginManifest, config: Dict[str, Any]):
        self.manifest = manifest
        self.config = config
        self.logger = self._get_logger()
    
    def _get_logger(self):
        """获取日志记录器"""
        return f"plugin.{self.manifest.plugin_id}"
    
    @abstractmethod
    async def on_load(self) -> bool:
        """插件加载"""
        pass
    
    @abstractmethod
    async def on_unload(self) -> bool:
        """插件卸载"""
        pass
    
    async def on_enable(self) -> bool:
        """插件启用"""
        return True
    
    async def on_disable(self) -> bool:
        """插件禁用"""
        return True
    
    async def on_message(self, message: AgentMessage):
        """处理消息"""
        pass
    
    async def on_agent_event(self, event_type: str, event_data: Dict[str, Any]):
        """处理Agent事件"""
        pass
    
    async def get_capabilities(self) -> List[str]:
        """获取能力"""
        return self.manifest.capabilities.copy()


# 便利函数
def create_plugin_system(system_id: str = "default") -> PluginSystem:
    """创建插件系统"""
    return PluginSystem(system_id)


def get_plugin_system(system_id: str = "default") -> PluginSystem:
    """获取插件系统（单例）"""
    # 这里可以实现单例模式
    return PluginSystem(system_id)