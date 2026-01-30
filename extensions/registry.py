"""
AgentBus扩展注册表
AgentBus Extension Registry

扩展注册表负责管理所有扩展的注册、查找和分类，
提供高效的扩展检索和管理功能。

The Extension Registry is responsible for managing registration, 
searching, and categorization of all extensions, providing efficient
extension retrieval and management functionality.

Author: MiniMax Agent
License: MIT
"""

import logging
from typing import Dict, List, Optional, Set, Any, Callable
from collections import defaultdict, OrderedDict
from threading import RLock
import weakref
from datetime import datetime

from .base import (
    Extension, ExtensionId, ExtensionName, ExtensionType, CapabilityName,
    ExtensionRegistryInterface, ExtensionState
)


class ExtensionRegistry(ExtensionRegistryInterface):
    """扩展注册表实现"""
    
    def __init__(self):
        self._extensions: Dict[ExtensionId, Extension] = {}
        self._extensions_by_type: Dict[ExtensionType, Set[ExtensionId]] = defaultdict(set)
        self._extensions_by_capability: Dict[CapabilityName, Set[ExtensionId]] = defaultdict(set)
        self._extensions_by_state: Dict[ExtensionState, Set[ExtensionId]] = defaultdict(set)
        self._name_index: Dict[ExtensionName, ExtensionId] = {}
        self._active_extensions: Set[ExtensionId] = set()
        
        self._lock = RLock()
        self._logger = logging.getLogger("extension.registry")
        self._registration_history: List[Dict[str, Any]] = []
        
        # 回调函数
        self._registration_callbacks: List[Callable] = []
        self._deregistration_callbacks: List[Callable] = []
    
    def register_extension(self, extension: Extension) -> bool:
        """注册扩展"""
        with self._lock:
            try:
                extension_id = extension.id
                
                # 检查是否已存在
                if extension_id in self._extensions:
                    self._logger.warning(f"扩展 {extension_id} 已存在，将覆盖")
                    self._unregister_internal(extension_id)
                
                # 验证扩展
                if not self._validate_extension(extension):
                    self._logger.error(f"扩展 {extension_id} 验证失败")
                    return False
                
                # 注册扩展
                self._extensions[extension_id] = extension
                self._name_index[extension.name] = extension_id
                
                # 更新索引
                self._extensions_by_type[extension.type].add(extension_id)
                for capability in extension.capabilities:
                    self._extensions_by_capability[capability].add(extension_id)
                self._extensions_by_state[extension.state].add(extension_id)
                
                # 记录注册历史
                self._registration_history.append({
                    "extension_id": extension_id,
                    "name": extension.name,
                    "type": extension.type,
                    "version": str(extension.version),
                    "timestamp": datetime.now().isoformat(),
                    "action": "register"
                })
                
                # 保持历史记录大小
                if len(self._registration_history) > 1000:
                    self._registration_history = self._registration_history[-500:]
                
                self._logger.info(f"扩展 {extension.name}({extension_id}) 注册成功")
                
                # 触发回调
                self._trigger_callbacks(self._registration_callbacks, extension)
                
                return True
                
            except Exception as e:
                self._logger.error(f"注册扩展失败: {e}")
                return False
    
    def unregister_extension(self, extension_id: ExtensionId) -> bool:
        """取消注册扩展"""
        with self._lock:
            return self._unregister_internal(extension_id)
    
    def _unregister_internal(self, extension_id: ExtensionId) -> bool:
        """内部取消注册方法（假设已经持有锁）"""
        try:
            if extension_id not in self._extensions:
                self._logger.warning(f"扩展 {extension_id} 不存在")
                return False
            
            extension = self._extensions[extension_id]
            
            # 从各索引中移除
            del self._extensions[extension_id]
            if extension.name in self._name_index:
                del self._name_index[extension.name]
            
            self._extensions_by_type[extension.type].discard(extension_id)
            for capability in extension.capabilities:
                self._extensions_by_capability[capability].discard(extension_id)
            self._extensions_by_state[extension.state].discard(extension_id)
            self._active_extensions.discard(extension_id)
            
            # 记录注销历史
            self._registration_history.append({
                "extension_id": extension_id,
                "name": extension.name,
                "type": extension.type,
                "version": str(extension.version),
                "timestamp": datetime.now().isoformat(),
                "action": "unregister"
            })
            
            # 保持历史记录大小
            if len(self._registration_history) > 1000:
                self._registration_history = self._registration_history[-500:]
            
            self._logger.info(f"扩展 {extension.name}({extension_id}) 注销成功")
            
            # 触发回调
            self._trigger_callbacks(self._deregistration_callbacks, extension)
            
            return True
            
        except Exception as e:
            self._logger.error(f"取消注册扩展失败: {e}")
            return False
    
    def get_extension(self, extension_id: ExtensionId) -> Optional[Extension]:
        """获取扩展"""
        with self._lock:
            return self._extensions.get(extension_id)
    
    def get_extension_by_name(self, name: ExtensionName) -> Optional[Extension]:
        """通过名称获取扩展"""
        with self._lock:
            extension_id = self._name_index.get(name)
            if extension_id:
                return self._extensions.get(extension_id)
            return None
    
    def find_extensions_by_type(self, extension_type: ExtensionType) -> List[Extension]:
        """按类型查找扩展"""
        with self._lock:
            extension_ids = self._extensions_by_type.get(extension_type, set())
            return [self._extensions[ext_id] for ext_id in extension_ids if ext_id in self._extensions]
    
    def find_extensions_by_capability(self, capability: CapabilityName) -> List[Extension]:
        """按能力查找扩展"""
        with self._lock:
            extension_ids = self._extensions_by_capability.get(capability, set())
            return [self._extensions[ext_id] for ext_id in extension_ids if ext_id in self._extensions]
    
    def find_extensions_by_state(self, state: ExtensionState) -> List[Extension]:
        """按状态查找扩展"""
        with self._lock:
            extension_ids = self._extensions_by_state.get(state, set())
            return [self._extensions[ext_id] for ext_id in extension_ids if ext_id in self._extensions]
    
    def find_active_extensions(self) -> List[Extension]:
        """查找活跃扩展"""
        with self._lock:
            return [self._extensions[ext_id] for ext_id in self._active_extensions if ext_id in self._extensions]
    
    def find_extensions_by_criteria(self, **criteria) -> List[Extension]:
        """按多个条件查找扩展"""
        with self._lock:
            results = list(self._extensions.values())
            
            # 按类型过滤
            if 'type' in criteria:
                results = [ext for ext in results if ext.type == criteria['type']]
            
            # 按状态过滤
            if 'state' in criteria:
                results = [ext for ext in results if ext.state == criteria['state']]
            
            # 按能力过滤
            if 'capability' in criteria:
                results = [ext for ext in results if ext.has_capability(criteria['capability'])]
            
            # 按作者过滤
            if 'author' in criteria:
                results = [ext for ext in results if ext.author == criteria['author']]
            
            # 按名称过滤（支持模糊匹配）
            if 'name_contains' in criteria:
                name_filter = criteria['name_contains'].lower()
                results = [ext for ext in results if name_filter in ext.name.lower()]
            
            return results
    
    def update_extension_state(self, extension_id: ExtensionId, new_state: ExtensionState) -> bool:
        """更新扩展状态"""
        with self._lock:
            if extension_id not in self._extensions:
                return False
            
            extension = self._extensions[extension_id]
            old_state = extension.state
            
            # 从旧状态集合中移除
            self._extensions_by_state[old_state].discard(extension_id)
            
            # 更新扩展状态
            extension._set_state(new_state)
            
            # 添加到新状态集合
            self._extensions_by_state[new_state].add(extension_id)
            
            # 更新活跃扩展集合
            if new_state == ExtensionState.ACTIVE:
                self._active_extensions.add(extension_id)
            else:
                self._active_extensions.discard(extension_id)
            
            self._logger.debug(f"扩展 {extension_id} 状态更新: {old_state.value} -> {new_state.value}")
            return True
    
    def mark_as_active(self, extension_id: ExtensionId):
        """标记扩展为活跃"""
        with self._lock:
            self._active_extensions.add(extension_id)
    
    def mark_as_inactive(self, extension_id: ExtensionId):
        """标记扩展为非活跃"""
        with self._lock:
            self._active_extensions.discard(extension_id)
    
    def list_all_extensions(self) -> List[Extension]:
        """列出所有扩展"""
        with self._lock:
            return list(self._extensions.values())
    
    def list_extension_ids(self) -> List[ExtensionId]:
        """列出所有扩展ID"""
        with self._lock:
            return list(self._extensions.keys())
    
    def list_extension_names(self) -> List[ExtensionName]:
        """列出所有扩展名称"""
        with self._lock:
            return list(self._name_index.keys())
    
    def get_extension_types(self) -> Set[ExtensionType]:
        """获取所有扩展类型"""
        with self._lock:
            return set(self._extensions_by_type.keys())
    
    def get_all_capabilities(self) -> Set[CapabilityName]:
        """获取所有扩展能力"""
        with self._lock:
            return set(self._extensions_by_capability.keys())
    
    def get_extension_count_by_type(self) -> Dict[ExtensionType, int]:
        """获取按类型分组的扩展数量"""
        with self._lock:
            return {ext_type: len(ext_ids) for ext_type, ext_ids in self._extensions_by_type.items()}
    
    def get_extension_count_by_state(self) -> Dict[ExtensionState, int]:
        """获取按状态分组的扩展数量"""
        with self._lock:
            return {state: len(ext_ids) for state, ext_ids in self._extensions_by_state.items()}
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取注册表统计信息"""
        with self._lock:
            return {
                "total_extensions": len(self._extensions),
                "active_extensions": len(self._active_extensions),
                "extension_types": self.get_extension_count_by_type(),
                "extension_states": self.get_extension_count_by_state(),
                "available_capabilities": list(self.get_all_capabilities()),
                "registration_history_size": len(self._registration_history),
                "last_registration": self._registration_history[-1] if self._registration_history else None
            }
    
    def get_registration_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取注册历史"""
        with self._lock:
            return self._registration_history[-limit:]
    
    def add_registration_callback(self, callback):
        """添加注册回调"""
        with self._lock:
            self._registration_callbacks.append(callback)
    
    def add_deregistration_callback(self, callback):
        """添加注销回调"""
        with self._lock:
            self._deregistration_callbacks.append(callback)
    
    def remove_callback(self, callback):
        """移除回调"""
        with self._lock:
            if callback in self._registration_callbacks:
                self._registration_callbacks.remove(callback)
            if callback in self._deregistration_callbacks:
                self._deregistration_callbacks.remove(callback)
    
    def _trigger_callbacks(self, callbacks: List, *args):
        """触发回调"""
        for callback in callbacks:
            try:
                if callable(callback):
                    callback(*args)
            except Exception as e:
                self._logger.error(f"回调执行失败: {e}")
    
    def _validate_extension(self, extension: Extension) -> bool:
        """验证扩展"""
        # 基本验证
        if not extension.id:
            self._logger.error("扩展ID不能为空")
            return False
        
        if not extension.name:
            self._logger.error("扩展名称不能为空")
            return False
        
        # 检查ID和名称的唯一性
        for existing_ext in self._extensions.values():
            if existing_ext.id == extension.id:
                self._logger.error(f"扩展ID {extension.id} 已存在")
                return False
            if existing_ext.name == extension.name:
                self._logger.error(f"扩展名称 {extension.name} 已存在")
                return False
        
        return True
    
    def export_registry_data(self) -> Dict[str, Any]:
        """导出注册表数据"""
        with self._lock:
            return {
                "extensions": [ext.get_info() for ext in self._extensions.values()],
                "indexes": {
                    "by_type": {k: list(v) for k, v in self._extensions_by_type.items()},
                    "by_capability": {k: list(v) for k, v in self._extensions_by_capability.items()},
                    "by_state": {k: list(v) for k, v in self._extensions_by_state.items()},
                    "name_index": self._name_index.copy(),
                    "active_extensions": list(self._active_extensions)
                },
                "statistics": self.get_statistics(),
                "export_timestamp": datetime.now().isoformat()
            }
    
    def import_registry_data(self, data: Dict[str, Any]) -> bool:
        """导入注册表数据"""
        try:
            # 清空现有数据
            with self._lock:
                self._extensions.clear()
                self._extensions_by_type.clear()
                self._extensions_by_capability.clear()
                self._extensions_by_state.clear()
                self._name_index.clear()
                self._active_extensions.clear()
            
            # 重建索引
            if "indexes" in data:
                indexes = data["indexes"]
                self._extensions_by_type = defaultdict(set, 
                    {k: set(v) for k, v in indexes.get("by_type", {}).items()})
                self._extensions_by_capability = defaultdict(set,
                    {k: set(v) for k, v in indexes.get("by_capability", {}).items()})
                self._extensions_by_state = defaultdict(set,
                    {k: set(v) for k, v in indexes.get("by_state", {}).items()})
                self._name_index = indexes.get("name_index", {}).copy()
                self._active_extensions = set(indexes.get("active_extensions", []))
            
            self._logger.info("注册表数据导入成功")
            return True
            
        except Exception as e:
            self._logger.error(f"导入注册表数据失败: {e}")
            return False
    
    def clear(self):
        """清空注册表"""
        with self._lock:
            self._extensions.clear()
            self._extensions_by_type.clear()
            self._extensions_by_capability.clear()
            self._extensions_by_state.clear()
            self._name_index.clear()
            self._active_extensions.clear()
            self._registration_history.clear()
            self._logger.info("注册表已清空")
    
    def __len__(self) -> int:
        """返回注册扩展数量"""
        with self._lock:
            return len(self._extensions)
    
    def __contains__(self, extension_id: ExtensionId) -> bool:
        """检查扩展是否存在"""
        with self._lock:
            return extension_id in self._extensions
    
    def __iter__(self):
        """迭代器"""
        with self._lock:
            return iter(self._extensions.values())
    
    def __repr__(self) -> str:
        """字符串表示"""
        with self._lock:
            return f"ExtensionRegistry(count={len(self._extensions)}, types={len(self._extensions_by_type)})"