"""
数据库存储接口 - 基于SQLite的实现
为Java用户提供持久化存储能力
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiosqlite
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


class DatabaseStorage(UserStorage, PreferencesStorage, MemoryStorage, SkillsStorage, 
                     ContextStorage, IntegrationStorage, StatsStorage):
    """数据库存储实现"""
    
    def __init__(self, db_path: str = "agentbus.db"):
        self.db_path = db_path
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化数据库连接和表结构"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA journal_mode=WAL")
                await db.execute("PRAGMA foreign_keys=ON")
                await self._create_tables(db)
                await db.commit()
            
            self._initialized = True
            logger.info("Database storage initialized successfully")
            
        except Exception as e:
            raise StorageConnectionError(f"Failed to initialize database: {e}")
    
    async def _create_tables(self, db: aiosqlite.Connection):
        """创建数据库表"""
        
        # 用户表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT,
                avatar_url TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                preferences_json TEXT DEFAULT '{}',
                memory_count INTEGER DEFAULT 0
            )
        """)
        
        # 用户偏好表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY REFERENCES users(user_id),
                language TEXT DEFAULT 'zh-CN',
                timezone TEXT DEFAULT 'Asia/Shanghai',
                theme TEXT DEFAULT 'light',
                notifications BOOLEAN DEFAULT 1,
                auto_save BOOLEAN DEFAULT 1,
                skill_level TEXT DEFAULT 'beginner',
                java_version TEXT,
                ide_preference TEXT,
                coding_style_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 用户记忆表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_memories (
                memory_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL REFERENCES users(user_id),
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                importance INTEGER DEFAULT 5,
                tags_json TEXT DEFAULT '[]',
                metadata_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 用户技能表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_skills (
                skill_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(user_id),
                skill_name TEXT NOT NULL,
                skill_level TEXT NOT NULL,
                experience_points INTEGER DEFAULT 0,
                last_practiced TIMESTAMP,
                is_enabled BOOLEAN DEFAULT 1,
                custom_config_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 用户上下文表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_contexts (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(user_id),
                current_context_json TEXT DEFAULT '{}',
                conversation_history_json TEXT DEFAULT '[]',
                learning_progress_json TEXT DEFAULT '{}',
                workspace_state_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 用户集成表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_integrations (
                integration_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(user_id),
                integration_type TEXT NOT NULL,
                integration_name TEXT NOT NULL,
                config_json TEXT DEFAULT '{}',
                credentials_json TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 用户统计表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id TEXT PRIMARY KEY REFERENCES users(user_id),
                total_sessions INTEGER DEFAULT 0,
                total_messages INTEGER DEFAULT 0,
                total_skills_practiced INTEGER DEFAULT 0,
                learning_hours REAL DEFAULT 0.0,
                achievements_json TEXT DEFAULT '[]',
                streak_days INTEGER DEFAULT 0,
                last_activity TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        await db.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_memories_user_id ON user_memories(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON user_memories(memory_type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_skills_user_id ON user_skills(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_contexts_user_id ON user_contexts(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_integrations_user_id ON user_integrations(user_id)")
    
    # UserStorage 实现
    async def create_user(self, user: UserProfile) -> UserProfile:
        """创建用户"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT INTO users (user_id, username, email, full_name, avatar_url, 
                                         status, created_at, updated_at, preferences_json, memory_count)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user.user_id, user.username, user.email, user.full_name,
                        user.avatar_url, user.status.value, user.created_at, user.updated_at,
                        user.preferences.json(), user.memory_count
                    )
                )
                await db.commit()
            
            # 初始化用户偏好和统计
            await self._initialize_user_data(user.user_id)
            
            logger.info(f"User created successfully: {user.user_id}")
            return user
            
        except Exception as e:
            raise StorageOperationError(f"Failed to create user: {e}")
    
    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        """获取用户"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM users WHERE user_id = ?", (user_id,)
                )
                row = await cursor.fetchone()
                
                if row:
                    return self._row_to_user_profile(row)
                return None
                
        except Exception as e:
            raise StorageOperationError(f"Failed to get user: {e}")
    
    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Optional[UserProfile]:
        """更新用户"""
        try:
            # 获取现有用户数据
            existing_user = await self.get_user(user_id)
            if not existing_user:
                return None
            
            # 合并数据
            updated_data = existing_user.dict()
            updated_data.update(user_data)
            updated_data['updated_at'] = datetime.now()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """UPDATE users SET username=?, full_name=?, avatar_url=?, 
                       status=?, updated_at=?, last_login=?, preferences_json=?, memory_count=?
                       WHERE user_id=?""",
                    (
                        updated_data.get('username'), updated_data.get('full_name'),
                        updated_data.get('avatar_url'), updated_data.get('status'),
                        updated_data.get('updated_at'), updated_data.get('last_login'),
                        updated_data.get('preferences', {}).json() if updated_data.get('preferences') else '{}',
                        updated_data.get('memory_count'), user_id
                    )
                )
                await db.commit()
            
            return await self.get_user(user_id)
            
        except Exception as e:
            raise StorageOperationError(f"Failed to update user: {e}")
    
    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 删除相关数据
                await db.execute("DELETE FROM user_memories WHERE user_id = ?", (user_id,))
                await db.execute("DELETE FROM user_skills WHERE user_id = ?", (user_id,))
                await db.execute("DELETE FROM user_contexts WHERE user_id = ?", (user_id,))
                await db.execute("DELETE FROM user_integrations WHERE user_id = ?", (user_id,))
                await db.execute("DELETE FROM user_stats WHERE user_id = ?", (user_id,))
                await db.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
                await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                
                await db.commit()
            
            logger.info(f"User deleted successfully: {user_id}")
            return True
            
        except Exception as e:
            raise StorageOperationError(f"Failed to delete user: {e}")
    
    async def list_users(self, limit: int = 100, offset: int = 0) -> List[UserProfile]:
        """列出用户"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM users LIMIT ? OFFSET ?", (limit, offset)
                )
                rows = await cursor.fetchall()
                
                return [self._row_to_user_profile(row) for row in rows]
                
        except Exception as e:
            raise StorageOperationError(f"Failed to list users: {e}")
    
    async def find_user_by_email(self, email: str) -> Optional[UserProfile]:
        """通过邮箱查找用户"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM users WHERE email = ?", (email,)
                )
                row = await cursor.fetchone()
                
                if row:
                    return self._row_to_user_profile(row)
                return None
                
        except Exception as e:
            raise StorageOperationError(f"Failed to find user by email: {e}")
    
    # PreferencesStorage 实现
    async def save_preferences(self, user_id: str, preferences: UserPreferences) -> bool:
        """保存用户偏好"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT OR REPLACE INTO user_preferences 
                       (user_id, language, timezone, theme, notifications, auto_save, 
                        skill_level, java_version, ide_preference, coding_style_json, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id, preferences.language, preferences.timezone,
                        preferences.theme, preferences.notifications, preferences.auto_save,
                        preferences.skill_level.value, preferences.java_version,
                        preferences.ide_preference, json.dumps(preferences.coding_style),
                        datetime.now()
                    )
                )
                await db.commit()
            
            return True
            
        except Exception as e:
            raise StorageOperationError(f"Failed to save preferences: {e}")
    
    async def get_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """获取用户偏好"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)
                )
                row = await cursor.fetchone()
                
                if row:
                    return self._row_to_user_preferences(row)
                return None
                
        except Exception as e:
            raise StorageOperationError(f"Failed to get preferences: {e}")
    
    async def update_preferences(self, user_id: str, preferences_data: Dict[str, Any]) -> Optional[UserPreferences]:
        """更新用户偏好"""
        try:
            existing = await self.get_preferences(user_id)
            if not existing:
                return None
            
            # 更新字段
            for key, value in preferences_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            
            existing.updated_at = datetime.now()
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """UPDATE user_preferences SET language=?, timezone=?, theme=?, 
                       notifications=?, auto_save=?, skill_level=?, java_version=?, 
                       ide_preference=?, coding_style_json=?, updated_at=?
                       WHERE user_id=?""",
                    (
                        existing.language, existing.timezone, existing.theme,
                        existing.notifications, existing.auto_save,
                        existing.skill_level.value, existing.java_version,
                        existing.ide_preference, json.dumps(existing.coding_style),
                        existing.updated_at, user_id
                    )
                )
                await db.commit()
            
            return existing
            
        except Exception as e:
            raise StorageOperationError(f"Failed to update preferences: {e}")
    
    # MemoryStorage 实现
    async def store_memory(self, memory: UserMemory) -> str:
        """存储记忆"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT OR REPLACE INTO user_memories 
                       (memory_id, session_id, user_id, content, memory_type, 
                        importance, tags_json, metadata_json, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        memory.memory_id, memory.session_id, memory.user_id,
                        memory.content, memory.memory_type, memory.importance,
                        json.dumps(memory.tags), json.dumps(memory.metadata),
                        memory.created_at, memory.updated_at
                    )
                )
                await db.commit()
            
            return memory.memory_id
            
        except Exception as e:
            raise StorageOperationError(f"Failed to store memory: {e}")
    
    async def get_memory(self, memory_id: str) -> Optional[UserMemory]:
        """获取记忆"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM user_memories WHERE memory_id = ?", (memory_id,)
                )
                row = await cursor.fetchone()
                
                if row:
                    return self._row_to_user_memory(row)
                return None
                
        except Exception as e:
            raise StorageOperationError(f"Failed to get memory: {e}")
    
    async def get_user_memories(self, user_id: str, memory_type: Optional[str] = None) -> List[UserMemory]:
        """获取用户记忆"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                if memory_type:
                    cursor = await db.execute(
                        """SELECT * FROM user_memories WHERE user_id = ? AND memory_type = ? 
                           ORDER BY importance DESC, created_at DESC""",
                        (user_id, memory_type)
                    )
                else:
                    cursor = await db.execute(
                        """SELECT * FROM user_memories WHERE user_id = ? 
                           ORDER BY importance DESC, created_at DESC""",
                        (user_id,)
                    )
                
                rows = await cursor.fetchall()
                return [self._row_to_user_memory(row) for row in rows]
                
        except Exception as e:
            raise StorageOperationError(f"Failed to get user memories: {e}")
    
    async def update_memory(self, memory_id: str, content: str) -> Optional[UserMemory]:
        """更新记忆"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE user_memories SET content=?, updated_at=? WHERE memory_id=?",
                    (content, datetime.now(), memory_id)
                )
                await db.commit()
            
            return await self.get_memory(memory_id)
            
        except Exception as e:
            raise StorageOperationError(f"Failed to update memory: {e}")
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM user_memories WHERE memory_id = ?", (memory_id,))
                await db.commit()
            
            return True
            
        except Exception as e:
            raise StorageOperationError(f"Failed to delete memory: {e}")
    
    async def search_memories(self, user_id: str, query: str, limit: int = 10) -> List[UserMemory]:
        """搜索记忆"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    """SELECT * FROM user_memories WHERE user_id = ? AND content LIKE ? 
                       ORDER BY importance DESC, created_at DESC LIMIT ?""",
                    (user_id, f"%{query}%", limit)
                )
                rows = await cursor.fetchall()
                return [self._row_to_user_memory(row) for row in rows]
                
        except Exception as e:
            raise StorageOperationError(f"Failed to search memories: {e}")
    
    # 辅助方法
    async def _initialize_user_data(self, user_id: str):
        """初始化用户数据"""
        # 初始化偏好
        default_preferences = UserPreferences()
        await self.save_preferences(user_id, default_preferences)
        
        # 初始化统计
        default_stats = UserStats(user_id=user_id)
        await self.save_stats(default_stats)
    
    def _row_to_user_profile(self, row: aiosqlite.Row) -> UserProfile:
        """将数据库行转换为用户档案"""
        preferences_data = json.loads(row['preferences_json'] or '{}')
        preferences = UserPreferences(**preferences_data)
        
        return UserProfile(
            user_id=row['user_id'],
            username=row['username'],
            email=row['email'],
            full_name=row['full_name'],
            avatar_url=row['avatar_url'],
            status=UserStatus(row['status']),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.now(),
            last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None,
            preferences=preferences,
            memory_count=row['memory_count']
        )
    
    def _row_to_user_preferences(self, row: aiosqlite.Row) -> UserPreferences:
        """将数据库行转换为用户偏好"""
        coding_style = json.loads(row['coding_style_json'] or '{}')
        
        return UserPreferences(
            language=row['language'],
            timezone=row['timezone'],
            theme=row['theme'],
            notifications=bool(row['notifications']),
            auto_save=bool(row['auto_save']),
            skill_level=SkillLevel(row['skill_level']),
            java_version=row['java_version'],
            ide_preference=row['ide_preference'],
            coding_style=coding_style
        )
    
    def _row_to_user_memory(self, row: aiosqlite.Row) -> UserMemory:
        """将数据库行转换为用户记忆"""
        tags = json.loads(row['tags_json'] or '[]')
        metadata = json.loads(row['metadata_json'] or '{}')
        
        return UserMemory(
            memory_id=row['memory_id'],
            session_id=row['session_id'],
            user_id=row['user_id'],
            content=row['content'],
            memory_type=row['memory_type'],
            importance=row['importance'],
            tags=tags,
            metadata=metadata,
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.now()
        )
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("SELECT 1")
            return True
        except:
            return False
    
    async def close(self):
        """关闭数据库连接"""
        self._initialized = False


class DatabaseStorageManager:
    """数据库存储管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_path = config.get('db_path', 'agentbus.db')
        self.storage = DatabaseStorage(self.db_path)
        
        # 分配存储接口
        self.user_storage = self.storage
        self.preferences_storage = self.storage
        self.memory_storage = self.storage
        self.skills_storage = self.storage
        self.context_storage = self.storage
        self.integration_storage = self.storage
        self.stats_storage = self.storage
    
    async def initialize(self):
        """初始化数据库存储"""
        await self.storage.initialize()
    
    async def close(self):
        """关闭数据库存储"""
        await self.storage.close()
    
    async def health_check(self) -> bool:
        """健康检查"""
        return await self.storage.health_check()