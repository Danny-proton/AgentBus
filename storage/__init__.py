"""
存储抽象层 - 为AgentBus提供统一的数据存储接口
支持多种存储后端：数据库、内存、文件系统等
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, TypeVar, Generic
from datetime import datetime
import asyncio

from ..models.user import (
    UserProfile, UserPreferences, UserMemory, UserSkills, 
    UserContext, UserIntegration, UserStats
)

T = TypeVar('T')


class StorageError(Exception):
    """存储相关异常"""
    pass


class StorageConnectionError(StorageError):
    """存储连接异常"""
    pass


class StorageOperationError(StorageError):
    """存储操作异常"""
    pass


class BaseStorage(ABC, Generic[T]):
    """基础存储抽象类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化存储"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭存储连接"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass


class UserStorage(BaseStorage[T]):
    """用户存储接口"""
    
    @abstractmethod
    async def create_user(self, user: UserProfile) -> UserProfile:
        """创建用户"""
        pass
    
    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        """获取用户"""
        pass
    
    @abstractmethod
    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Optional[UserProfile]:
        """更新用户"""
        pass
    
    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        pass
    
    @abstractmethod
    async def list_users(self, limit: int = 100, offset: int = 0) -> List[UserProfile]:
        """列出用户"""
        pass
    
    @abstractmethod
    async def find_user_by_email(self, email: str) -> Optional[UserProfile]:
        """通过邮箱查找用户"""
        pass


class PreferencesStorage(BaseStorage[T]):
    """用户偏好存储接口"""
    
    @abstractmethod
    async def save_preferences(self, user_id: str, preferences: UserPreferences) -> bool:
        """保存用户偏好"""
        pass
    
    @abstractmethod
    async def get_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """获取用户偏好"""
        pass
    
    @abstractmethod
    async def update_preferences(self, user_id: str, preferences_data: Dict[str, Any]) -> Optional[UserPreferences]:
        """更新用户偏好"""
        pass


class MemoryStorage(BaseStorage[T]):
    """用户记忆存储接口"""
    
    @abstractmethod
    async def store_memory(self, memory: UserMemory) -> str:
        """存储记忆"""
        pass
    
    @abstractmethod
    async def get_memory(self, memory_id: str) -> Optional[UserMemory]:
        """获取记忆"""
        pass
    
    @abstractmethod
    async def get_user_memories(self, user_id: str, memory_type: Optional[str] = None) -> List[UserMemory]:
        """获取用户记忆"""
        pass
    
    @abstractmethod
    async def update_memory(self, memory_id: str, content: str) -> Optional[UserMemory]:
        """更新记忆"""
        pass
    
    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        pass
    
    @abstractmethod
    async def search_memories(self, user_id: str, query: str, limit: int = 10) -> List[UserMemory]:
        """搜索记忆"""
        pass


class SkillsStorage(BaseStorage[T]):
    """用户技能存储接口"""
    
    @abstractmethod
    async def save_skill(self, skill: UserSkills) -> str:
        """保存技能"""
        pass
    
    @abstractmethod
    async def get_user_skills(self, user_id: str) -> List[UserSkills]:
        """获取用户技能"""
        pass
    
    @abstractmethod
    async def update_skill(self, skill_id: str, skill_data: Dict[str, Any]) -> Optional[UserSkills]:
        """更新技能"""
        pass
    
    @abstractmethod
    async def delete_skill(self, skill_id: str) -> bool:
        """删除技能"""
        pass


class ContextStorage(BaseStorage[T]):
    """用户上下文存储接口"""
    
    @abstractmethod
    async def save_context(self, context: UserContext) -> str:
        """保存上下文"""
        pass
    
    @abstractmethod
    async def get_context(self, session_id: str) -> Optional[UserContext]:
        """获取上下文"""
        pass
    
    @abstractmethod
    async def update_context(self, session_id: str, context_data: Dict[str, Any]) -> Optional[UserContext]:
        """更新上下文"""
        pass
    
    @abstractmethod
    async def get_user_contexts(self, user_id: str) -> List[UserContext]:
        """获取用户上下文"""
        pass


class IntegrationStorage(BaseStorage[T]):
    """用户集成存储接口"""
    
    @abstractmethod
    async def save_integration(self, integration: UserIntegration) -> str:
        """保存集成"""
        pass
    
    @abstractmethod
    async def get_integration(self, integration_id: str) -> Optional[UserIntegration]:
        """获取集成"""
        pass
    
    @abstractmethod
    async def get_user_integrations(self, user_id: str) -> List[UserIntegration]:
        """获取用户集成"""
        pass
    
    @abstractmethod
    async def update_integration(self, integration_id: str, config: Dict[str, Any]) -> Optional[UserIntegration]:
        """更新集成"""
        pass
    
    @abstractmethod
    async def delete_integration(self, integration_id: str) -> bool:
        """删除集成"""
        pass


class StatsStorage(BaseStorage[T]):
    """用户统计存储接口"""
    
    @abstractmethod
    async def save_stats(self, stats: UserStats) -> str:
        """保存统计"""
        pass
    
    @abstractmethod
    async def get_stats(self, user_id: str) -> Optional[UserStats]:
        """获取统计"""
        pass
    
    @abstractmethod
    async def update_stats(self, user_id: str, stats_data: Dict[str, Any]) -> Optional[UserStats]:
        """更新统计"""
        pass


class StorageManager:
    """存储管理器 - 统一管理所有存储接口"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.user_storage: Optional[UserStorage] = None
        self.preferences_storage: Optional[PreferencesStorage] = None
        self.memory_storage: Optional[MemoryStorage] = None
        self.skills_storage: Optional[SkillsStorage] = None
        self.context_storage: Optional[ContextStorage] = None
        self.integration_storage: Optional[IntegrationStorage] = None
        self.stats_storage: Optional[StatsStorage] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化所有存储"""
        # 根据配置初始化相应的存储实现
        storage_type = self.config.get('type', 'memory')
        
        if storage_type == 'database':
            from .database import DatabaseStorageManager
            db_manager = DatabaseStorageManager(self.config)
            await db_manager.initialize()
            self._assign_storages(db_manager)
        elif storage_type == 'memory':
            from .memory import MemoryStorageManager
            mem_manager = MemoryStorageManager(self.config)
            await mem_manager.initialize()
            self._assign_storages(mem_manager)
        else:
            raise StorageError(f"Unsupported storage type: {storage_type}")
        
        self._initialized = True
    
    def _assign_storages(self, manager: 'StorageManager'):
        """分配存储实例"""
        self.user_storage = manager.user_storage
        self.preferences_storage = manager.preferences_storage
        self.memory_storage = manager.memory_storage
        self.skills_storage = manager.skills_storage
        self.context_storage = manager.context_storage
        self.integration_storage = manager.integration_storage
        self.stats_storage = manager.stats_storage
    
    async def close(self) -> None:
        """关闭所有存储连接"""
        if self._initialized:
            # 关闭各个存储连接
            if hasattr(self, '_storages'):
                for storage in self._storages:
                    if storage:
                        await storage.close()
            self._initialized = False
    
    async def health_check(self) -> Dict[str, bool]:
        """健康检查"""
        results = {}
        
        if self.user_storage:
            results['user_storage'] = await self.user_storage.health_check()
        if self.preferences_storage:
            results['preferences_storage'] = await self.preferences_storage.health_check()
        if self.memory_storage:
            results['memory_storage'] = await self.memory_storage.health_check()
        if self.skills_storage:
            results['skills_storage'] = await self.skills_storage.health_check()
        if self.context_storage:
            results['context_storage'] = await self.context_storage.health_check()
        if self.integration_storage:
            results['integration_storage'] = await self.integration_storage.health_check()
        if self.stats_storage:
            results['stats_storage'] = await self.stats_storage.health_check()
        
        return results


# 导出主要的存储管理器
__all__ = [
    'StorageManager',
    'UserStorage',
    'PreferencesStorage', 
    'MemoryStorage',
    'SkillsStorage',
    'ContextStorage',
    'IntegrationStorage',
    'StatsStorage',
    'StorageError',
    'StorageConnectionError',
    'StorageOperationError'
]