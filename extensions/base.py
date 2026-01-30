"""
AgentBus扩展基类和接口定义
AgentBus Extension Base Classes and Interface Definitions

这个模块定义了扩展系统的核心接口和基类，为所有扩展提供统一的规范和生命周期管理。

This module defines core interfaces and base classes for the extension system,
providing unified specifications and lifecycle management for all extensions.

Author: MiniMax Agent
License: MIT
"""

import abc
import asyncio
import logging
from typing import (
    Any, Dict, List, Optional, Set, Union, Callable, 
    TypeVar, Generic, Protocol, runtime_checkable
)
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import importlib.util
import inspect
import traceback
import threading
from pathlib import Path

# 类型定义
ExtensionId = str
ExtensionName = str
VersionString = str
ExtensionType = str
CapabilityName = str

T = TypeVar('T')
ContextType = Dict[str, Any]


class ExtensionState(Enum):
    """扩展状态枚举"""
    DISCOVERED = "discovered"    # 已发现
    LOADED = "loaded"           # 已加载
    INITIALIZING = "initializing" # 初始化中
    ACTIVE = "active"          # 活跃
    INACTIVE = "inactive"      # 非活跃
    ERROR = "error"            # 错误
    DISABLED = "disabled"      # 已禁用
    UNLOADING = "unloading"    # 卸载中


class ExtensionError(Exception):
    """扩展系统基础异常"""
    pass


class ExtensionLoadError(ExtensionError):
    """扩展加载异常"""
    pass


class ExtensionDependencyError(ExtensionError):
    """扩展依赖异常"""
    pass


class ExtensionSecurityError(ExtensionError):
    """扩展安全异常"""
    pass


class ExtensionVersion:
    """扩展版本管理"""
    
    def __init__(self, version_string: str):
        self.version_string = version_string
        self._parse_version(version_string)
    
    def _parse_version(self, version_string: str):
        """解析版本字符串"""
        try:
            parts = version_string.split('.')
            self.major = int(parts[0]) if len(parts) > 0 else 0
            self.minor = int(parts[1]) if len(parts) > 1 else 0
            self.patch = int(parts[2]) if len(parts) > 2 else 0
            self.prerelease = parts[3] if len(parts) > 3 else None
        except (ValueError, IndexError):
            raise ValueError(f"无效的版本字符串: {version_string}")
    
    def __str__(self) -> str:
        return self.version_string
    
    def __repr__(self) -> str:
        return f"ExtensionVersion('{self.version_string}')"
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, ExtensionVersion):
            return False
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)
    
    def __lt__(self, other) -> bool:
        if not isinstance(other, ExtensionVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
    
    def __le__(self, other) -> bool:
        return self == other or self < other
    
    def __gt__(self, other) -> bool:
        if not isinstance(other, ExtensionVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)
    
    def __ge__(self, other) -> bool:
        return self == other or self > other
    
    def is_compatible_with(self, other: 'ExtensionVersion') -> bool:
        """检查版本兼容性"""
        return self.major == other.major


@dataclass
class ExtensionDependency:
    """扩展依赖定义"""
    name: ExtensionName
    version_constraint: Optional[str] = None  # 如: ">=1.0.0,<2.0.0"
    optional: bool = False
    description: Optional[str] = None
    
    def is_satisfied_by(self, version: ExtensionVersion) -> bool:
        """检查依赖是否满足"""
        if not self.version_constraint:
            return True
        
        # 简化的版本约束检查
        # 实际实现可以使用packaging.version处理复杂的约束
        try:
            if self.version_constraint.startswith(">="):
                required = ExtensionVersion(self.version_constraint[2:])
                return version >= required
            elif self.version_constraint.startswith("=="):
                required = ExtensionVersion(self.version_constraint[2:])
                return version == required
            elif self.version_constraint.startswith(">"):
                required = ExtensionVersion(self.version_constraint[1:])
                return version > required
            elif self.version_constraint.startswith("<="):
                required = ExtensionVersion(self.version_constraint[2:])
                return version <= required
            elif self.version_constraint.startswith("<"):
                required = ExtensionVersion(self.version_constraint[1:])
                return version < required
            elif self.version_constraint.startswith("!="):
                required = ExtensionVersion(self.version_constraint[2:])
                return version != required
            else:
                # 默认视为相等约束
                required = ExtensionVersion(self.version_constraint)
                return version == required
        except ValueError:
            return False


@runtime_checkable
class ExtensionInterface(Protocol):
    """扩展接口定义"""
    
    @property
    def id(self) -> ExtensionId:
        """扩展唯一标识符"""
        ...
    
    @property
    def name(self) -> ExtensionName:
        """扩展名称"""
        ...
    
    @property
    def version(self) -> ExtensionVersion:
        """扩展版本"""
        ...
    
    @property
    def description(self) -> str:
        """扩展描述"""
        ...
    
    @property
    def author(self) -> str:
        """扩展作者"""
        ...
    
    @property
    def type(self) -> ExtensionType:
        """扩展类型"""
        ...
    
    @property
    def capabilities(self) -> Set[CapabilityName]:
        """扩展能力列表"""
        ...
    
    @property
    def dependencies(self) -> List[ExtensionDependency]:
        """扩展依赖列表"""
        ...
    
    @property
    def state(self) -> ExtensionState:
        """扩展状态"""
        ...
    
    def initialize(self, context: ContextType) -> bool:
        """初始化扩展"""
        ...
    
    def activate(self) -> bool:
        """激活扩展"""
        ...
    
    def deactivate(self) -> bool:
        """停用扩展"""
        ...
    
    def cleanup(self) -> bool:
        """清理扩展资源"""
        ...
    
    def get_config_schema(self) -> Dict[str, Any]:
        """获取配置模式"""
        ...
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        ...


class Extension(ExtensionInterface):
    """扩展基类实现"""
    
    def __init__(
        self,
        extension_id: ExtensionId,
        name: ExtensionName,
        version: Union[str, ExtensionVersion],
        description: str = "",
        author: str = "",
        extension_type: ExtensionType = "custom",
        capabilities: Optional[Set[CapabilityName]] = None,
        dependencies: Optional[List[ExtensionDependency]] = None,
        config_schema: Optional[Dict[str, Any]] = None
    ):
        self._id = extension_id
        self._name = name
        self._version = version if isinstance(version, ExtensionVersion) else ExtensionVersion(version)
        self._description = description
        self._author = author
        self._type = extension_type
        self._capabilities = capabilities or set()
        self._dependencies = dependencies or []
        self._config_schema = config_schema or {}
        self._state = ExtensionState.DISCOVERED
        self._logger = logging.getLogger(f"extension.{extension_id}")
        self._context: ContextType = {}
        self._initialized = False
        self._active = False
        self._start_time: Optional[datetime] = None
    
    @property
    def id(self) -> ExtensionId:
        return self._id
    
    @property
    def name(self) -> ExtensionName:
        return self._name
    
    @property
    def version(self) -> ExtensionVersion:
        return self._version
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def author(self) -> str:
        return self._author
    
    @property
    def type(self) -> ExtensionType:
        return self._type
    
    @property
    def capabilities(self) -> Set[CapabilityName]:
        return self._capabilities.copy()
    
    @property
    def dependencies(self) -> List[ExtensionDependency]:
        return self._dependencies.copy()
    
    @property
    def state(self) -> ExtensionState:
        return self._state
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    @property
    def is_active(self) -> bool:
        return self._active
    
    @property
    def start_time(self) -> Optional[datetime]:
        return self._start_time
    
    def _set_state(self, new_state: ExtensionState):
        """设置扩展状态"""
        old_state = self._state
        self._state = new_state
        self._logger.debug(f"扩展状态变更: {old_state.value} -> {new_state.value}")
    
    def initialize(self, context: ContextType) -> bool:
        """初始化扩展"""
        try:
            self._set_state(ExtensionState.INITIALIZING)
            self._context = context.copy()
            
            # 调用子类实现
            if not self._do_initialize():
                return False
            
            self._initialized = True
            self._set_state(ExtensionState.LOADED)
            self._logger.info(f"扩展 {self.name} 初始化成功")
            return True
            
        except Exception as e:
            self._set_state(ExtensionState.ERROR)
            self._logger.error(f"扩展 {self.name} 初始化失败: {e}")
            self._logger.debug(traceback.format_exc())
            return False
    
    def _do_initialize(self) -> bool:
        """子类重写此方法来实现具体的初始化逻辑"""
        return True
    
    def activate(self) -> bool:
        """激活扩展"""
        try:
            if not self._initialized:
                self._logger.error(f"扩展 {self.name} 未初始化，无法激活")
                return False
            
            if self._active:
                self._logger.warning(f"扩展 {self.name} 已经激活")
                return True
            
            self._set_state(ExtensionState.ACTIVE)
            
            # 调用子类实现
            if not self._do_activate():
                self._set_state(ExtensionState.ERROR)
                return False
            
            self._active = True
            self._start_time = datetime.now()
            self._logger.info(f"扩展 {self.name} 激活成功")
            return True
            
        except Exception as e:
            self._set_state(ExtensionState.ERROR)
            self._logger.error(f"扩展 {self.name} 激活失败: {e}")
            self._logger.debug(traceback.format_exc())
            return False
    
    def _do_activate(self) -> bool:
        """子类重写此方法来实现具体的激活逻辑"""
        return True
    
    def deactivate(self) -> bool:
        """停用扩展"""
        try:
            if not self._active:
                self._logger.warning(f"扩展 {self.name} 未激活")
                return True
            
            self._set_state(ExtensionState.UNLOADING)
            
            # 调用子类实现
            if not self._do_deactivate():
                self._logger.warning(f"扩展 {self.name} 停用时出现问题")
            
            self._active = False
            self._start_time = None
            self._set_state(ExtensionState.INACTIVE)
            self._logger.info(f"扩展 {self.name} 停用成功")
            return True
            
        except Exception as e:
            self._set_state(ExtensionState.ERROR)
            self._logger.error(f"扩展 {self.name} 停用失败: {e}")
            self._logger.debug(traceback.format_exc())
            return False
    
    def _do_deactivate(self) -> bool:
        """子类重写此方法来实现具体的停用逻辑"""
        return True
    
    def cleanup(self) -> bool:
        """清理扩展资源"""
        try:
            if self._active:
                if not self.deactivate():
                    return False
            
            # 调用子类实现
            if not self._do_cleanup():
                return False
            
            self._initialized = False
            self._context.clear()
            self._set_state(ExtensionState.DISCOVERED)
            self._logger.info(f"扩展 {self.name} 清理成功")
            return True
            
        except Exception as e:
            self._logger.error(f"扩展 {self.name} 清理失败: {e}")
            self._logger.debug(traceback.format_exc())
            return False
    
    def _do_cleanup(self) -> bool:
        """子类重写此方法来实现具体的清理逻辑"""
        return True
    
    def get_config_schema(self) -> Dict[str, Any]:
        """获取配置模式"""
        return self._config_schema.copy()
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        try:
            # 简化的配置验证
            # 实际实现可以根据_config_schema进行更严格的验证
            if not isinstance(config, dict):
                return False
            
            required_fields = self._config_schema.get("required", [])
            for field in required_fields:
                if field not in config:
                    return False
            
            return True
            
        except Exception as e:
            self._logger.error(f"配置验证失败: {e}")
            return False
    
    def has_capability(self, capability: CapabilityName) -> bool:
        """检查是否具有指定能力"""
        return capability in self._capabilities
    
    def add_capability(self, capability: CapabilityName):
        """添加能力"""
        self._capabilities.add(capability)
    
    def remove_capability(self, capability: CapabilityName):
        """移除能力"""
        self._capabilities.discard(capability)
    
    def add_dependency(self, dependency: ExtensionDependency):
        """添加依赖"""
        self._dependencies.append(dependency)
    
    def get_info(self) -> Dict[str, Any]:
        """获取扩展信息"""
        return {
            "id": self._id,
            "name": self._name,
            "version": str(self._version),
            "description": self._description,
            "author": self._author,
            "type": self._type,
            "capabilities": list(self._capabilities),
            "dependencies": [dep.name for dep in self._dependencies],
            "state": self._state.value,
            "initialized": self._initialized,
            "active": self._active,
            "start_time": self._start_time.isoformat() if self._start_time else None
        }
    
    def __repr__(self) -> str:
        return f"Extension(id='{self._id}', name='{self._name}', version='{self._version}', state='{self._state.value}')"


@runtime_checkable
class ExtensionManagerInterface(Protocol):
    """扩展管理器接口"""
    
    def discover_extensions(self, paths: Optional[List[Path]] = None) -> List[Extension]:
        """发现扩展"""
        ...
    
    def load_extension(self, extension: Extension) -> bool:
        """加载扩展"""
        ...
    
    def unload_extension(self, extension_id: ExtensionId) -> bool:
        """卸载扩展"""
        ...
    
    def activate_extension(self, extension_id: ExtensionId) -> bool:
        """激活扩展"""
        ...
    
    def deactivate_extension(self, extension_id: ExtensionId) -> bool:
        """停用扩展"""
        ...
    
    def get_extension(self, extension_id: ExtensionId) -> Optional[Extension]:
        """获取扩展"""
        ...
    
    def list_extensions(self, state: Optional[ExtensionState] = None) -> List[Extension]:
        """列出扩展"""
        ...
    
    def resolve_dependencies(self, extensions: List[Extension]) -> bool:
        """解析依赖"""
        ...


@runtime_checkable  
class ExtensionRegistryInterface(Protocol):
    """扩展注册表接口"""
    
    def register_extension(self, extension: Extension) -> bool:
        """注册扩展"""
        ...
    
    def unregister_extension(self, extension_id: ExtensionId) -> bool:
        """取消注册扩展"""
        ...
    
    def get_extension(self, extension_id: ExtensionId) -> Optional[Extension]:
        """获取扩展"""
        ...
    
    def find_extensions_by_type(self, extension_type: ExtensionType) -> List[Extension]:
        """按类型查找扩展"""
        ...
    
    def find_extensions_by_capability(self, capability: CapabilityName) -> List[Extension]:
        """按能力查找扩展"""
        ...


@runtime_checkable
class ExtensionSandboxInterface(Protocol):
    """扩展沙箱接口"""
    
    def execute_in_sandbox(self, extension: Extension, func: Callable, *args, **kwargs) -> Any:
        """在沙箱中执行函数"""
        ...
    
    def check_security(self, extension: Extension) -> bool:
        """安全检查"""
        ...
    
    def set_resource_limits(self, extension: Extension, **limits) -> bool:
        """设置资源限制"""
        ...
    
    def monitor_execution(self, extension: Extension) -> Dict[str, Any]:
        """监控执行"""
        ...