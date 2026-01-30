"""
AgentBus扩展管理器
AgentBus Extension Manager

扩展管理器是扩展系统的核心组件，负责扩展的发现、加载、
激活、停用、依赖解析和版本管理等核心功能。

The Extension Manager is the core component of the extension system,
responsible for extension discovery, loading, activation, deactivation,
dependency resolution, version management, and other core functions.

Author: MiniMax Agent
License: MIT
"""

import asyncio
import logging
import os
import sys
import importlib
import importlib.util
import inspect
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple, Union
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, deque
from dataclasses import dataclass

from .base import (
    Extension, ExtensionId, ExtensionName, ExtensionType, CapabilityName,
    ExtensionManagerInterface, ExtensionState, ExtensionDependency,
    ExtensionVersion, ExtensionError, ExtensionLoadError, ExtensionDependencyError,
    ExtensionSandboxInterface
)
from .registry import ExtensionRegistry
from .sandbox import ExtensionSandbox


@dataclass
class DiscoveryResult:
    """扩展发现结果"""
    path: Path
    extension_class: type
    metadata: Dict[str, Any]
    load_time: float


@dataclass
class LoadResult:
    """扩展加载结果"""
    extension: Extension
    success: bool
    error: Optional[str] = None
    load_time: float = 0.0


class ExtensionManager(ExtensionManagerInterface):
    """扩展管理器实现"""
    
    def __init__(
        self,
        sandbox: Optional[ExtensionSandboxInterface] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self._registry = ExtensionRegistry()
        self._sandbox = sandbox or ExtensionSandbox()
        self._config = config or {}
        
        self._logger = logging.getLogger("extension.manager")
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        # 扩展发现和加载状态
        self._discovery_paths: List[Path] = []
        self._loading_extensions: Set[ExtensionId] = set()
        self._dependency_graph: Dict[ExtensionId, Set[ExtensionId]] = {}
        self._load_queue = deque()
        self._load_stats = defaultdict(int)
        
        # 事件回调
        self._discovery_callbacks: List[Callable] = []
        self._load_callbacks: List[Callable] = []
        self._activate_callbacks: List[Callable] = []
        self._deactivate_callbacks: List[Callable] = []
        
        # 默认配置
        self._default_config = {
            "auto_discover": True,
            "auto_load": False,
            "dependency_resolution": "strict",
            "parallel_loading": True,
            "max_concurrent_loads": 3,
            "discovery_recursive": True,
            "load_timeout": 30.0,
            "validate_dependencies": True,
            "sandbox_enabled": True,
            "security_checks": True
        }
        self._config = {**self._default_config, **self._config}
        
        # 初始化默认发现路径
        self._init_default_discovery_paths()
        
        self._logger.info("扩展管理器初始化完成")
    
    def _init_default_discovery_paths(self):
        """初始化默认发现路径"""
        current_dir = Path(__file__).parent
        extensions_dir = current_dir / "extensions"
        
        # 添加内置扩展目录
        if extensions_dir.exists():
            self._discovery_paths.append(extensions_dir)
        
        # 添加用户扩展目录
        user_extensions_dir = Path.home() / ".agentbus" / "extensions"
        if user_extensions_dir.exists():
            self._discovery_paths.append(user_extensions_dir)
        
        # 添加当前工作目录扩展
        cwd_extensions = Path.cwd() / "extensions"
        if cwd_extensions.exists():
            self._discovery_paths.append(cwd_extensions)
        
        self._logger.debug(f"发现路径: {[str(p) for p in self._discovery_paths]}")
    
    def add_discovery_path(self, path: Union[str, Path]):
        """添加扩展发现路径"""
        path_obj = Path(path)
        if not path_obj.exists():
            self._logger.warning(f"发现路径不存在: {path_obj}")
            return False
        
        with self._lock:
            if path_obj not in self._discovery_paths:
                self._discovery_paths.append(path_obj)
                self._logger.info(f"添加发现路径: {path_obj}")
                return True
        
        return False
    
    def remove_discovery_path(self, path: Union[str, Path]):
        """移除扩展发现路径"""
        path_obj = Path(path)
        with self._lock:
            if path_obj in self._discovery_paths:
                self._discovery_paths.remove(path_obj)
                self._logger.info(f"移除发现路径: {path_obj}")
                return True
        
        return False
    
    def discover_extensions(self, paths: Optional[List[Path]] = None) -> List[Extension]:
        """发现扩展"""
        discovery_paths = paths or self._discovery_paths
        discovered_extensions = []
        
        self._logger.info(f"开始发现扩展，路径: {[str(p) for p in discovery_paths]}")
        
        for path in discovery_paths:
            try:
                extensions = self._discover_in_path(path)
                discovered_extensions.extend(extensions)
                self._logger.debug(f"在 {path} 中发现 {len(extensions)} 个扩展")
            except Exception as e:
                self._logger.error(f"发现扩展失败 {path}: {e}")
        
        # 触发发现回调
        for callback in self._discovery_callbacks:
            try:
                callback(discovered_extensions)
            except Exception as e:
                self._logger.error(f"发现回调执行失败: {e}")
        
        self._logger.info(f"扩展发现完成，总共发现 {len(discovered_extensions)} 个扩展")
        return discovered_extensions
    
    def _discover_in_path(self, path: Path) -> List[Extension]:
        """在指定路径中发现扩展"""
        extensions = []
        
        if not path.exists():
            return extensions
        
        # 递归搜索或非递归搜索
        pattern = "**/*.py" if self._config.get("discovery_recursive", True) else "*.py"
        
        for file_path in path.glob(pattern):
            if file_path.name.startswith("_") or file_path.name.startswith("test_"):
                continue
            
            try:
                extension = self._load_extension_from_file(file_path)
                if extension:
                    extensions.append(extension)
            except Exception as e:
                self._logger.debug(f"加载扩展失败 {file_path}: {e}")
        
        return extensions
    
    def _load_extension_from_file(self, file_path: Path) -> Optional[Extension]:
        """从文件中加载扩展"""
        try:
            # 动态导入模块
            module_name = file_path.stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # 查找扩展类
            extension_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (hasattr(obj, '__bases__') and 
                    any(base.__name__ == 'Extension' for base in obj.__mro__)):
                    extension_class = obj
                    break
            
            if not extension_class:
                return None
            
            # 创建扩展实例
            try:
                extension = extension_class()
                
                # 验证扩展
                if not self._validate_extension(extension):
                    return None
                
                # 设置扩展文件路径
                if hasattr(extension, '_file_path'):
                    extension._file_path = file_path
                
                self._logger.debug(f"从 {file_path} 加载扩展: {extension.name}")
                return extension
                
            except Exception as e:
                self._logger.error(f"创建扩展实例失败 {file_path}: {e}")
                return None
                
        except Exception as e:
            self._logger.error(f"加载模块失败 {file_path}: {e}")
            return None
    
    def _validate_extension(self, extension: Extension) -> bool:
        """验证扩展"""
        try:
            # 基本属性检查
            if not extension.id or not extension.name:
                return False
            
            # 安全检查
            if self._config.get("security_checks", True):
                if not self._sandbox.check_security(extension):
                    self._logger.warning(f"扩展 {extension.id} 安全检查失败")
                    return False
            
            return True
            
        except Exception as e:
            self._logger.error(f"扩展验证失败 {extension.id}: {e}")
            return False
    
    def load_extension(self, extension: Extension) -> bool:
        """加载扩展"""
        extension_id = extension.id
        
        with self._lock:
            if extension_id in self._loading_extensions:
                self._logger.warning(f"扩展 {extension_id} 正在加载中")
                return False
            
            if extension_id in self._registry:
                self._logger.warning(f"扩展 {extension_id} 已存在")
                return True
            
            self._loading_extensions.add(extension_id)
        
        try:
            self._logger.info(f"开始加载扩展: {extension.name} ({extension_id})")
            
            # 验证扩展依赖
            if not self._validate_dependencies(extension):
                raise ExtensionDependencyError(f"依赖验证失败: {extension_id}")
            
            # 注册扩展
            if not self._registry.register_extension(extension):
                raise ExtensionLoadError(f"注册扩展失败: {extension_id}")
            
            # 初始化扩展
            context = self._create_extension_context(extension)
            
            # 在沙箱中初始化扩展
            if self._config.get("sandbox_enabled", True):
                success = self._sandbox.execute_in_sandbox(
                    extension, extension.initialize, context
                )
            else:
                success = extension.initialize(context)
            
            if not success:
                raise ExtensionLoadError(f"扩展初始化失败: {extension_id}")
            
            self._load_stats[f"{extension.type}_loaded"] += 1
            self._logger.info(f"扩展加载成功: {extension.name}")
            
            # 触发加载回调
            for callback in self._load_callbacks:
                try:
                    callback(extension, True, None)
                except Exception as e:
                    self._logger.error(f"加载回调执行失败: {e}")
            
            return True
            
        except Exception as e:
            self._logger.error(f"加载扩展失败 {extension.name}: {e}")
            
            # 触发加载失败回调
            for callback in self._load_callbacks:
                try:
                    callback(extension, False, str(e))
                except Exception as cb_error:
                    self._logger.error(f"加载失败回调执行失败: {cb_error}")
            
            # 清理
            self._cleanup_failed_load(extension_id)
            return False
            
        finally:
            with self._lock:
                self._loading_extensions.discard(extension_id)
    
    def unload_extension(self, extension_id: ExtensionId) -> bool:
        """卸载扩展"""
        with self._lock:
            if extension_id not in self._registry:
                self._logger.warning(f"扩展 {extension_id} 不存在")
                return False
        
        try:
            extension = self._registry.get_extension(extension_id)
            if not extension:
                return False
            
            # 检查是否有其他扩展依赖此扩展
            dependents = self._find_dependents(extension_id)
            if dependents:
                self._logger.error(f"无法卸载扩展 {extension_id}，有其他扩展依赖: {dependents}")
                return False
            
            self._logger.info(f"开始卸载扩展: {extension.name}")
            
            # 先停用扩展
            if extension.is_active:
                self.deactivate_extension(extension_id)
            
            # 清理扩展
            extension.cleanup()
            
            # 从注册表移除
            self._registry.unregister_extension(extension_id)
            
            # 从依赖图中移除
            self._dependency_graph.pop(extension_id, None)
            for deps in self._dependency_graph.values():
                deps.discard(extension_id)
            
            self._logger.info(f"扩展卸载成功: {extension.name}")
            return True
            
        except Exception as e:
            self._logger.error(f"卸载扩展失败 {extension_id}: {e}")
            return False
    
    def activate_extension(self, extension_id: ExtensionId) -> bool:
        """激活扩展"""
        extension = self._registry.get_extension(extension_id)
        if not extension:
            self._logger.error(f"扩展 {extension_id} 不存在")
            return False
        
        if extension.is_active:
            self._logger.warning(f"扩展 {extension_id} 已经激活")
            return True
        
        try:
            self._logger.info(f"开始激活扩展: {extension.name}")
            
            # 验证依赖是否已激活
            if not self._validate_active_dependencies(extension):
                raise ExtensionDependencyError(f"依赖扩展未激活: {extension_id}")
            
            # 激活扩展
            if self._config.get("sandbox_enabled", True):
                success = self._sandbox.execute_in_sandbox(extension, extension.activate)
            else:
                success = extension.activate()
            
            if not success:
                raise ExtensionLoadError(f"扩展激活失败: {extension_id}")
            
            # 更新注册表状态
            self._registry.update_extension_state(extension_id, ExtensionState.ACTIVE)
            self._registry.mark_as_active(extension_id)
            
            self._logger.info(f"扩展激活成功: {extension.name}")
            
            # 触发激活回调
            for callback in self._activate_callbacks:
                try:
                    callback(extension)
                except Exception as e:
                    self._logger.error(f"激活回调执行失败: {e}")
            
            return True
            
        except Exception as e:
            self._logger.error(f"激活扩展失败 {extension.name}: {e}")
            
            # 恢复状态
            self._registry.update_extension_state(extension_id, ExtensionState.LOADED)
            self._registry.mark_as_inactive(extension_id)
            
            return False
    
    def deactivate_extension(self, extension_id: ExtensionId) -> bool:
        """停用扩展"""
        extension = self._registry.get_extension(extension_id)
        if not extension:
            self._logger.error(f"扩展 {extension_id} 不存在")
            return False
        
        if not extension.is_active:
            self._logger.warning(f"扩展 {extension_id} 未激活")
            return True
        
        try:
            self._logger.info(f"开始停用扩展: {extension.name}")
            
            # 检查是否有其他活跃扩展依赖此扩展
            dependents = self._find_active_dependents(extension_id)
            if dependents:
                self._logger.error(f"无法停用扩展 {extension_id}，有其他活跃扩展依赖: {dependents}")
                return False
            
            # 停用扩展
            if self._config.get("sandbox_enabled", True):
                success = self._sandbox.execute_in_sandbox(extension, extension.deactivate)
            else:
                success = extension.deactivate()
            
            # 更新注册表状态
            self._registry.update_extension_state(extension_id, ExtensionState.INACTIVE)
            self._registry.mark_as_inactive(extension_id)
            
            if not success:
                self._logger.warning(f"扩展停用时出现问题: {extension.name}")
            
            self._logger.info(f"扩展停用成功: {extension.name}")
            
            # 触发停用回调
            for callback in self._deactivate_callbacks:
                try:
                    callback(extension)
                except Exception as e:
                    self._logger.error(f"停用回调执行失败: {e}")
            
            return True
            
        except Exception as e:
            self._logger.error(f"停用扩展失败 {extension.name}: {e}")
            return False
    
    def get_extension(self, extension_id: ExtensionId) -> Optional[Extension]:
        """获取扩展"""
        return self._registry.get_extension(extension_id)
    
    def list_extensions(self, state: Optional[ExtensionState] = None) -> List[Extension]:
        """列出扩展"""
        if state:
            return self._registry.find_extensions_by_state(state)
        return self._registry.list_all_extensions()
    
    def resolve_dependencies(self, extensions: List[Extension]) -> bool:
        """解析依赖"""
        self._logger.info("开始解析扩展依赖")
        
        try:
            # 构建依赖图
            self._dependency_graph.clear()
            
            for extension in extensions:
                self._dependency_graph[extension.id] = set()
                
                for dep in extension.dependencies:
                    # 查找依赖的扩展
                    dep_extension = None
                    for ext in extensions:
                        if ext.id == dep.name or ext.name == dep.name:
                            dep_extension = ext
                            break
                    
                    if dep_extension:
                        self._dependency_graph[extension.id].add(dep_extension.id)
                    elif not dep.optional:
                        self._logger.warning(f"找不到必需依赖 {dep.name} for {extension.id}")
            
            # 验证依赖环
            if self._has_circular_dependencies():
                raise ExtensionDependencyError("检测到循环依赖")
            
            # 验证依赖版本
            if not self._validate_dependency_versions(extensions):
                raise ExtensionDependencyError("依赖版本不兼容")
            
            self._logger.info("依赖解析成功")
            return True
            
        except Exception as e:
            self._logger.error(f"依赖解析失败: {e}")
            return False
    
    def _validate_dependencies(self, extension: Extension) -> bool:
        """验证扩展依赖"""
        for dep in extension.dependencies:
            # 检查依赖是否存在
            dep_exists = any(
                ext.id == dep.name or ext.name == dep.name
                for ext in self._registry.list_all_extensions()
            )
            
            if not dep_exists and not dep.optional:
                self._logger.error(f"扩展 {extension.id} 的必需依赖 {dep.name} 不存在")
                return False
            
            # 如果依赖存在，检查版本
            if dep_exists:
                for ext in self._registry.list_all_extensions():
                    if ext.id == dep.name or ext.name == dep.name:
                        if not dep.is_satisfied_by(ext.version):
                            self._logger.error(f"扩展 {extension.id} 依赖 {dep.name} 版本不兼容")
                            return False
                        break
        
        return True
    
    def _validate_active_dependencies(self, extension: Extension) -> bool:
        """验证活跃依赖"""
        for dep in extension.dependencies:
            # 检查依赖是否激活
            dep_active = any(
                ext.id == dep.name or ext.name == dep.name
                for ext in self._registry.find_active_extensions()
            )
            
            if not dep_active and not dep.optional:
                self._logger.error(f"扩展 {extension.id} 的必需依赖 {dep.name} 未激活")
                return False
        
        return True
    
    def _create_extension_context(self, extension: Extension) -> Dict[str, Any]:
        """创建扩展上下文"""
        return {
            "extension_id": extension.id,
            "extension_name": extension.name,
            "extension_version": str(extension.version),
            "manager": self,
            "registry": self._registry,
            "sandbox": self._sandbox,
            "config": self._config,
            "logger": logging.getLogger(f"extension.{extension.id}"),
            "start_time": time.time()
        }
    
    def _find_dependents(self, extension_id: ExtensionId) -> List[ExtensionId]:
        """查找依赖指定扩展的其他扩展"""
        dependents = []
        for ext_id, deps in self._dependency_graph.items():
            if extension_id in deps:
                dependents.append(ext_id)
        return dependents
    
    def _find_active_dependents(self, extension_id: ExtensionId) -> List[ExtensionId]:
        """查找依赖指定扩展的活跃扩展"""
        active_dependents = []
        for ext_id in self._find_dependents(extension_id):
            extension = self._registry.get_extension(ext_id)
            if extension and extension.is_active:
                active_dependents.append(ext_id)
        return active_dependents
    
    def _has_circular_dependencies(self) -> bool:
        """检查循环依赖"""
        visited = set()
        rec_stack = set()
        
        def has_cycle(extension_id: ExtensionId) -> bool:
            if extension_id in rec_stack:
                return True
            if extension_id in visited:
                return False
            
            visited.add(extension_id)
            rec_stack.add(extension_id)
            
            for dep in self._dependency_graph.get(extension_id, set()):
                if has_cycle(dep):
                    return True
            
            rec_stack.discard(extension_id)
            return False
        
        for ext_id in self._dependency_graph:
            if ext_id not in visited:
                if has_cycle(ext_id):
                    return True
        
        return False
    
    def _validate_dependency_versions(self, extensions: List[Extension]) -> bool:
        """验证依赖版本兼容性"""
        # 这里可以实现更复杂的版本兼容性检查
        # 目前使用简单的检查
        return True
    
    def _cleanup_failed_load(self, extension_id: ExtensionId):
        """清理加载失败的扩展"""
        try:
            if extension_id in self._registry:
                self._registry.unregister_extension(extension_id)
        except Exception as e:
            self._logger.error(f"清理失败扩展时出错: {e}")
    
    def add_discovery_callback(self, callback):
        """添加发现回调"""
        self._discovery_callbacks.append(callback)
    
    def add_load_callback(self, callback):
        """添加加载回调"""
        self._load_callbacks.append(callback)
    
    def add_activate_callback(self, callback):
        """添加激活回调"""
        self._activate_callbacks.append(callback)
    
    def add_deactivate_callback(self, callback):
        """添加停用回调"""
        self._deactivate_callbacks.append(callback)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        return {
            "registry_stats": self._registry.get_statistics(),
            "discovery_paths": [str(p) for p in self._discovery_paths],
            "loading_extensions": list(self._loading_extensions),
            "load_statistics": dict(self._load_stats),
            "dependency_graph_size": len(self._dependency_graph),
            "configuration": self._config
        }
    
    def shutdown(self):
        """关闭管理器"""
        self._logger.info("关闭扩展管理器")
        
        # 停用所有活跃扩展
        for extension in self._registry.find_active_extensions():
            try:
                self.deactivate_extension(extension.id)
            except Exception as e:
                self._logger.error(f"停用扩展失败 {extension.id}: {e}")
        
        # 清理注册表
        self._registry.clear()
        
        # 关闭线程池
        self._executor.shutdown(wait=True)
        
        self._logger.info("扩展管理器已关闭")