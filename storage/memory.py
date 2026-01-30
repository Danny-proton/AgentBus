"""
记忆存储接口 - 基于内存的实现
为Java用户提供快速临时存储能力
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from collections import defaultdict
import logging

from ..models.user import (
    UserProfile, UserPreferences, UserMemory, UserSkills,
    UserContext, UserIntegration, UserStats, UserStatus, SkillLevel
)
from . import (
    UserStorage, PreferencesStorage, MemoryStorage, SkillsStorage,
    ContextStorage, IntegrationStorage, StatsStorage,
    StorageError, StorageConnectionError, StorageOperationError
)

logger = logging.getLogger(__name__)


class MemoryStorage(UserStorage, PreferencesStorage, MemoryStorage, SkillsStorage, 
                   ContextStorage, IntegrationStorage, StatsStorage):
    """内存存储实现"""
    
    def __init__(self, max_memory_size: int = 10000):
        self.max_memory_size = max_memory_size
        self._initialized = False
        
        # 内存数据结构
        self.users: Dict[str, UserProfile] = {}
        self.user_preferences: Dict[str, UserPreferences] = {}
        self.user_memories: Dict[str, UserMemory] = {}
        self.user_skills: Dict[str, UserSkills] = {}
        self.user_contexts: Dict[str, UserContext] = {}
        self.user_integrations: Dict[str, UserIntegration] = {}
        self.user_stats: Dict[str, UserStats] = {}
        
        # 索引用于快速查找
        self.users_by_email: Dict[str, str] = {}  # email -> user_id
        self.memories_by_user: Dict[str, List[str]] = defaultdict(list)  # user_id -> [memory_id]
        self.memories_by_type: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))  # memory_type -> user_id -> [memory_id]
        self.skills_by_user: Dict[str, List[str]] = defaultdict(list)
        self.contexts_by_user: Dict[str, List[str]] = defaultdict(list)
        self.integrations_by_user: Dict[str, List[str]] = defaultdict(list)
    
    async def initialize(self) -> None:
        """初始化内存存储"""
        try:
            self._initialized = True
            logger.info("Memory storage initialized successfully")
        except Exception as e:
            raise StorageConnectionError(f"Failed to initialize memory storage: {e}")
    
    # UserStorage 实现
    async def create_user(self, user: UserProfile) -> UserProfile:
        """创建用户"""
        try:
            if user.user_id in self.users:
                raise StorageOperationError(f"User {user.user_id} already exists")
            
            if user.email in self.users_by_email:
                raise StorageOperationError(f"User with email {user.email} already exists")
            
            # 存储用户
            self.users[user.user_id] = user
            self.users_by_email[user.email] = user.user_id
            
            # 初始化用户相关数据
            await self._initialize_user_data(user.user_id)
            
            logger.info(f"User created successfully: {user.user_id}")
            return user
            
        except Exception as e:
            raise StorageOperationError(f"Failed to create user: {e}")
    
    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        """获取用户"""
        try:
            return self.users.get(user_id)
        except Exception as e:
            raise StorageOperationError(f"Failed to get user: {e}")
    
    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Optional[UserProfile]:
        """更新用户"""
        try:
            if user_id not in self.users:
                return None
            
            user = self.users[user_id]
            
            # 更新字段
            for key, value in user_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            user.updated_at = datetime.now()
            
            # 如果邮箱被更新，更新索引
            if 'email' in user_data and user_data['email'] != user.email:
                # 移除旧的邮箱索引
                if user.email in self.users_by_email:
                    del self.users_by_email[user.email]
                # 添加新的邮箱索引
                self.users_by_email[user_data['email']] = user_id
            
            return user
            
        except Exception as e:
            raise StorageOperationError(f"Failed to update user: {e}")
    
    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        try:
            if user_id not in self.users:
                return False
            
            user = self.users[user_id]
            
            # 删除用户
            del self.users[user_id]
            
            # 删除邮箱索引
            if user.email in self.users_by_email:
                del self.users_by_email[user.email]
            
            # 删除相关数据
            await self._cleanup_user_data(user_id)
            
            logger.info(f"User deleted successfully: {user_id}")
            return True
            
        except Exception as e:
            raise StorageOperationError(f"Failed to delete user: {e}")
    
    async def list_users(self, limit: int = 100, offset: int = 0) -> List[UserProfile]:
        """列出用户"""
        try:
            users_list = list(self.users.values())
            users_list.sort(key=lambda u: u.created_at, reverse=True)
            
            return users_list[offset:offset + limit]
            
        except Exception as e:
            raise StorageOperationError(f"Failed to list users: {e}")
    
    async def find_user_by_email(self, email: str) -> Optional[UserProfile]:
        """通过邮箱查找用户"""
        try:
            user_id = self.users_by_email.get(email)
            if user_id:
                return self.users.get(user_id)
            return None
            
        except Exception as e:
            raise StorageOperationError(f"Failed to find user by email: {e}")
    
    # PreferencesStorage 实现
    async def save_preferences(self, user_id: str, preferences: UserPreferences) -> bool:
        """保存用户偏好"""
        try:
            self.user_preferences[user_id] = preferences
            return True
            
        except Exception as e:
            raise StorageOperationError(f"Failed to save preferences: {e}")
    
    async def get_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """获取用户偏好"""
        try:
            return self.user_preferences.get(user_id)
            
        except Exception as e:
            raise StorageOperationError(f"Failed to get preferences: {e}")
    
    async def update_preferences(self, user_id: str, preferences_data: Dict[str, Any]) -> Optional[UserPreferences]:
        """更新用户偏好"""
        try:
            if user_id not in self.user_preferences:
                return None
            
            preferences = self.user_preferences[user_id]
            
            # 更新字段
            for key, value in preferences_data.items():
                if hasattr(preferences, key):
                    setattr(preferences, key, value)
            
            preferences.updated_at = datetime.now()
            
            return preferences
            
        except Exception as e:
            raise StorageOperationError(f"Failed to update preferences: {e}")
    
    # MemoryStorage 实现
    async def store_memory(self, memory: UserMemory) -> str:
        """存储记忆"""
        try:
            # 检查内存大小限制
            if len(self.user_memories) >= self.max_memory_size:
                # 删除最旧的记忆
                oldest_memory = min(self.user_memories.values(), key=lambda m: m.created_at)
                await self.delete_memory(oldest_memory.memory_id)
            
            self.user_memories[memory.memory_id] = memory
            
            # 更新索引
            self.memories_by_user[memory.user_id].append(memory.memory_id)
            self.memories_by_type[memory.memory_type][memory.user_id].append(memory.memory_id)
            
            return memory.memory_id
            
        except Exception as e:
            raise StorageOperationError(f"Failed to store memory: {e}")
    
    async def get_memory(self, memory_id: str) -> Optional[UserMemory]:
        """获取记忆"""
        try:
            return self.user_memories.get(memory_id)
            
        except Exception as e:
            raise StorageOperationError(f"Failed to get memory: {e}")
    
    async def get_user_memories(self, user_id: str, memory_type: Optional[str] = None) -> List[UserMemory]:
        """获取用户记忆"""
        try:
            if memory_type:
                memory_ids = self.memories_by_type.get(memory_type, {}).get(user_id, [])
            else:
                memory_ids = self.memories_by_user.get(user_id, [])
            
            memories = []
            for memory_id in memory_ids:
                if memory_id in self.user_memories:
                    memories.append(self.user_memories[memory_id])
            
            # 按重要性和创建时间排序
            memories.sort(key=lambda m: (m.importance, m.created_at), reverse=True)
            
            return memories
            
        except Exception as e:
            raise StorageOperationError(f"Failed to get user memories: {e}")
    
    async def update_memory(self, memory_id: str, content: str) -> Optional[UserMemory]:
        """更新记忆"""
        try:
            if memory_id not in self.user_memories:
                return None
            
            memory = self.user_memories[memory_id]
            memory.content = content
            memory.updated_at = datetime.now()
            
            return memory
            
        except Exception as e:
            raise StorageOperationError(f"Failed to update memory: {e}")
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        try:
            if memory_id not in self.user_memories:
                return False
            
            memory = self.user_memories[memory_id]
            
            # 从索引中删除
            if memory.user_id in self.memories_by_user:
                if memory_id in self.memories_by_user[memory.user_id]:
                    self.memories_by_user[memory.user_id].remove(memory_id)
            
            if memory.memory_type in self.memories_by_type:
                if memory.user_id in self.memories_by_type[memory.memory_type]:
                    if memory_id in self.memories_by_type[memory.memory_type][memory.user_id]:
                        self.memories_by_type[memory.memory_type][memory.user_id].remove(memory_id)
            
            # 删除记忆
            del self.user_memories[memory_id]
            
            return True
            
        except Exception as e:
            raise StorageOperationError(f"Failed to delete memory: {e}")
    
    async def search_memories(self, user_id: str, query: str, limit: int = 10) -> List[UserMemory]:
        """搜索记忆"""
        try:
            memories = await self.get_user_memories(user_id)
            
            # 搜索匹配的记忆
            matching_memories = [
                memory for memory in memories
                if query.lower() in memory.content.lower()
            ]
            
            # 按重要性排序并限制数量
            matching_memories.sort(key=lambda m: (m.importance, m.created_at), reverse=True)
            
            return matching_memories[:limit]
            
        except Exception as e:
            raise StorageOperationError(f"Failed to search memories: {e}")
    
    # SkillsStorage 实现
    async def save_skill(self, skill: UserSkills) -> str:
        """保存技能"""
        try:
            self.user_skills[skill.skill_id] = skill
            
            # 更新索引
            self.skills_by_user[skill.user_id].append(skill.skill_id)
            
            return skill.skill_id
            
        except Exception as e:
            raise StorageOperationError(f"Failed to save skill: {e}")
    
    async def get_user_skills(self, user_id: str) -> List[UserSkills]:
        """获取用户技能"""
        try:
            skill_ids = self.skills_by_user.get(user_id, [])
            skills = []
            
            for skill_id in skill_ids:
                if skill_id in self.user_skills:
                    skills.append(self.user_skills[skill_id])
            
            return skills
            
        except Exception as e:
            raise StorageOperationError(f"Failed to get user skills: {e}")
    
    async def update_skill(self, skill_id: str, skill_data: Dict[str, Any]) -> Optional[UserSkills]:
        """更新技能"""
        try:
            if skill_id not in self.user_skills:
                return None
            
            skill = self.user_skills[skill_id]
            
            # 更新字段
            for key, value in skill_data.items():
                if hasattr(skill, key):
                    setattr(skill, key, value)
            
            skill.updated_at = datetime.now()
            
            return skill
            
        except Exception as e:
            raise StorageOperationError(f"Failed to update skill: {e}")
    
    async def delete_skill(self, skill_id: str) -> bool:
        """删除技能"""
        try:
            if skill_id not in self.user_skills:
                return False
            
            skill = self.user_skills[skill_id]
            
            # 从索引中删除
            if skill.user_id in self.skills_by_user:
                if skill_id in self.skills_by_user[skill.user_id]:
                    self.skills_by_user[skill.user_id].remove(skill_id)
            
            # 删除技能
            del self.user_skills[skill_id]
            
            return True
            
        except Exception as e:
            raise StorageOperationError(f"Failed to delete skill: {e}")
    
    # ContextStorage 实现
    async def save_context(self, context: UserContext) -> str:
        """保存上下文"""
        try:
            self.user_contexts[context.session_id] = context
            
            # 更新索引
            self.contexts_by_user[context.user_id].append(context.session_id)
            
            return context.session_id
            
        except Exception as e:
            raise StorageOperationError(f"Failed to save context: {e}")
    
    async def get_context(self, session_id: str) -> Optional[UserContext]:
        """获取上下文"""
        try:
            return self.user_contexts.get(session_id)
            
        except Exception as e:
            raise StorageOperationError(f"Failed to get context: {e}")
    
    async def update_context(self, session_id: str, context_data: Dict[str, Any]) -> Optional[UserContext]:
        """更新上下文"""
        try:
            if session_id not in self.user_contexts:
                return None
            
            context = self.user_contexts[session_id]
            
            # 更新上下文数据
            if 'current_context' in context_data:
                context.current_context.update(context_data['current_context'])
            if 'conversation_history' in context_data:
                context.conversation_history.extend(context_data['conversation_history'])
            if 'learning_progress' in context_data:
                context.learning_progress.update(context_data['learning_progress'])
            if 'workspace_state' in context_data:
                context.workspace_state.update(context_data['workspace_state'])
            
            context.updated_at = datetime.now()
            
            return context
            
        except Exception as e:
            raise StorageOperationError(f"Failed to update context: {e}")
    
    async def get_user_contexts(self, user_id: str) -> List[UserContext]:
        """获取用户上下文"""
        try:
            session_ids = self.contexts_by_user.get(user_id, [])
            contexts = []
            
            for session_id in session_ids:
                if session_id in self.user_contexts:
                    contexts.append(self.user_contexts[session_id])
            
            # 按更新时间排序
            contexts.sort(key=lambda c: c.updated_at, reverse=True)
            
            return contexts
            
        except Exception as e:
            raise StorageOperationError(f"Failed to get user contexts: {e}")
    
    # IntegrationStorage 实现
    async def save_integration(self, integration: UserIntegration) -> str:
        """保存集成"""
        try:
            self.user_integrations[integration.integration_id] = integration
            
            # 更新索引
            self.integrations_by_user[integration.user_id].append(integration.integration_id)
            
            return integration.integration_id
            
        except Exception as e:
            raise StorageOperationError(f"Failed to save integration: {e}")
    
    async def get_integration(self, integration_id: str) -> Optional[UserIntegration]:
        """获取集成"""
        try:
            return self.user_integrations.get(integration_id)
            
        except Exception as e:
            raise StorageOperationError(f"Failed to get integration: {e}")
    
    async def get_user_integrations(self, user_id: str) -> List[UserIntegration]:
        """获取用户集成"""
        try:
            integration_ids = self.integrations_by_user.get(user_id, [])
            integrations = []
            
            for integration_id in integration_ids:
                if integration_id in self.user_integrations:
                    integration = self.user_integrations[integration_id]
                    if integration.is_active:
                        integrations.append(integration)
            
            # 按名称排序
            integrations.sort(key=lambda i: i.integration_name)
            
            return integrations
            
        except Exception as e:
            raise StorageOperationError(f"Failed to get user integrations: {e}")
    
    async def update_integration(self, integration_id: str, config: Dict[str, Any]) -> Optional[UserIntegration]:
        """更新集成"""
        try:
            if integration_id not in self.user_integrations:
                return None
            
            integration = self.user_integrations[integration_id]
            
            # 更新配置
            integration.config.update(config)
            integration.updated_at = datetime.now()
            
            return integration
            
        except Exception as e:
            raise StorageOperationError(f"Failed to update integration: {e}")
    
    async def delete_integration(self, integration_id: str) -> bool:
        """删除集成"""
        try:
            if integration_id not in self.user_integrations:
                return False
            
            integration = self.user_integrations[integration_id]
            
            # 从索引中删除
            if integration.user_id in self.integrations_by_user:
                if integration_id in self.integrations_by_user[integration.user_id]:
                    self.integrations_by_user[integration.user_id].remove(integration_id)
            
            # 标记为非活跃而不是删除
            integration.is_active = False
            integration.updated_at = datetime.now()
            
            return True
            
        except Exception as e:
            raise StorageOperationError(f"Failed to delete integration: {e}")
    
    # StatsStorage 实现
    async def save_stats(self, stats: UserStats) -> str:
        """保存统计"""
        try:
            self.user_stats[stats.user_id] = stats
            return stats.user_id
            
        except Exception as e:
            raise StorageOperationError(f"Failed to save stats: {e}")
    
    async def get_stats(self, user_id: str) -> Optional[UserStats]:
        """获取统计"""
        try:
            return self.user_stats.get(user_id)
            
        except Exception as e:
            raise StorageOperationError(f"Failed to get stats: {e}")
    
    async def update_stats(self, user_id: str, stats_data: Dict[str, Any]) -> Optional[UserStats]:
        """更新统计"""
        try:
            if user_id not in self.user_stats:
                # 创建新的统计记录
                stats = UserStats(user_id=user_id)
                self.user_stats[user_id] = stats
            else:
                stats = self.user_stats[user_id]
            
            # 更新字段
            for key, value in stats_data.items():
                if hasattr(stats, key):
                    setattr(stats, key, value)
            
            stats.updated_at = datetime.now()
            
            return stats
            
        except Exception as e:
            raise StorageOperationError(f"Failed to update stats: {e}")
    
    # 辅助方法
    async def _initialize_user_data(self, user_id: str):
        """初始化用户数据"""
        # 初始化偏好
        default_preferences = UserPreferences()
        await self.save_preferences(user_id, default_preferences)
        
        # 初始化统计
        default_stats = UserStats(user_id=user_id)
        await self.save_stats(default_stats)
    
    async def _cleanup_user_data(self, user_id: str):
        """清理用户相关数据"""
        # 清理偏好
        if user_id in self.user_preferences:
            del self.user_preferences[user_id]
        
        # 清理记忆
        if user_id in self.memories_by_user:
            for memory_id in self.memories_by_user[user_id]:
                if memory_id in self.user_memories:
                    memory = self.user_memories[memory_id]
                    if memory.memory_type in self.memories_by_type:
                        if user_id in self.memories_by_type[memory.memory_type]:
                            if memory_id in self.memories_by_type[memory.memory_type][user_id]:
                                self.memories_by_type[memory.memory_type][user_id].remove(memory_id)
                    del self.user_memories[memory_id]
            del self.memories_by_user[user_id]
        
        # 清理技能
        if user_id in self.skills_by_user:
            for skill_id in self.skills_by_user[user_id]:
                if skill_id in self.user_skills:
                    del self.user_skills[skill_id]
            del self.skills_by_user[user_id]
        
        # 清理上下文
        if user_id in self.contexts_by_user:
            for session_id in self.contexts_by_user[user_id]:
                if session_id in self.user_contexts:
                    del self.user_contexts[session_id]
            del self.contexts_by_user[user_id]
        
        # 清理集成
        if user_id in self.integrations_by_user:
            for integration_id in self.integrations_by_user[user_id]:
                if integration_id in self.user_integrations:
                    integration = self.user_integrations[integration_id]
                    integration.is_active = False
            del self.integrations_by_user[user_id]
        
        # 清理统计
        if user_id in self.user_stats:
            del self.user_stats[user_id]
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 检查内存使用情况
            memory_usage = len(self.user_memories)
            return memory_usage < self.max_memory_size * 1.1  # 允许10%的缓冲
        except:
            return False
    
    async def close(self):
        """关闭内存存储"""
        # 清理所有数据
        self.users.clear()
        self.user_preferences.clear()
        self.user_memories.clear()
        self.user_skills.clear()
        self.user_contexts.clear()
        self.user_integrations.clear()
        self.user_stats.clear()
        
        # 清理索引
        self.users_by_email.clear()
        self.memories_by_user.clear()
        self.memories_by_type.clear()
        self.skills_by_user.clear()
        self.contexts_by_user.clear()
        self.integrations_by_user.clear()
        
        self._initialized = False


class MemoryStorageManager:
    """内存存储管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_memory_size = config.get('max_memory_size', 10000)
        self.storage = MemoryStorage(self.max_memory_size)
        
        # 分配存储接口
        self.user_storage = self.storage
        self.preferences_storage = self.storage
        self.memory_storage = self.storage
        self.skills_storage = self.storage
        self.context_storage = self.storage
        self.integration_storage = self.storage
        self.stats_storage = self.storage
    
    async def initialize(self):
        """初始化内存存储"""
        await self.storage.initialize()
    
    async def close(self):
        """关闭内存存储"""
        await self.storage.close()
    
    async def health_check(self) -> bool:
        """健康检查"""
        return await self.storage.health_check()