"""
会话存储模块
Session Storage Module

负责会话数据的持久化存储和管理
支持内存存储、文件存储和数据库存储
"""

from typing import Dict, Any, Optional, List, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
import asyncio
import json
import sqlite3
import pickle
import os
import logging
from pathlib import Path
import aiosqlite
from contextlib import asynccontextmanager

from .context_manager import SessionContext, SessionType, SessionStatus

logger = logging.getLogger(__name__)


class StorageType(Enum):
    """存储类型枚举"""
    MEMORY = "memory"      # 内存存储
    FILE = "file"         # 文件存储
    DATABASE = "database"  # 数据库存储
    REDIS = "redis"       # Redis存储（预留）


class SessionStore:
    """会话存储抽象基类"""
    
    async def create_session(self, context: SessionContext) -> None:
        """创建会话"""
        raise NotImplementedError
    
    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """获取会话"""
        raise NotImplementedError
    
    async def update_session(self, context: SessionContext) -> None:
        """更新会话"""
        raise NotImplementedError
    
    async def delete_session(self, session_id: str) -> None:
        """删除会话"""
        raise NotImplementedError
    
    async def find_sessions(self, **filters) -> List[SessionContext]:
        """查找会话"""
        raise NotImplementedError
    
    async def cleanup_expired(self) -> int:
        """清理过期会话"""
        raise NotImplementedError
    
    async def get_session_count(self) -> int:
        """获取会话总数"""
        raise NotImplementedError
    
    async def close(self) -> None:
        """关闭存储连接"""
        pass


class MemorySessionStore(SessionStore):
    """内存会话存储实现"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionContext] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> session_ids
        self.chat_sessions: Dict[str, Set[str]] = {}  # chat_id -> session_ids
        self.platform_sessions: Dict[str, Set[str]] = {}  # platform -> session_ids
        self.lock = asyncio.Lock()
    
    async def create_session(self, context: SessionContext) -> None:
        """创建会话"""
        async with self.lock:
            self.sessions[context.session_id] = context
            
            # 更新索引
            if context.user_id not in self.user_sessions:
                self.user_sessions[context.user_id] = set()
            self.user_sessions[context.user_id].add(context.session_id)
            
            if context.chat_id not in self.chat_sessions:
                self.chat_sessions[context.chat_id] = set()
            self.chat_sessions[context.chat_id].add(context.session_id)
            
            platform_key = context.platform.value if hasattr(context.platform, 'value') else str(context.platform)
            if platform_key not in self.platform_sessions:
                self.platform_sessions[platform_key] = set()
            self.platform_sessions[platform_key].add(context.session_id)
            
            logger.debug("Session created", session_id=context.session_id)
    
    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """获取会话"""
        session = self.sessions.get(session_id)
        if session and (session.is_expired() or session.is_idle_timeout()):
            await self.delete_session(session_id)
            return None
        return session
    
    async def update_session(self, context: SessionContext) -> None:
        """更新会话"""
        async with self.lock:
            if context.session_id in self.sessions:
                self.sessions[context.session_id] = context
                logger.debug("Session updated", session_id=context.session_id)
    
    async def delete_session(self, session_id: str) -> None:
        """删除会话"""
        async with self.lock:
            session = self.sessions.pop(session_id, None)
            if session:
                # 清理索引
                if session.user_id in self.user_sessions:
                    self.user_sessions[session.user_id].discard(session_id)
                    if not self.user_sessions[session.user_id]:
                        del self.user_sessions[session.user_id]
                
                if session.chat_id in self.chat_sessions:
                    self.chat_sessions[session.chat_id].discard(session_id)
                    if not self.chat_sessions[session.chat_id]:
                        del self.chat_sessions[session.chat_id]
                
                platform_key = session.platform.value if hasattr(session.platform, 'value') else str(session.platform)
                if platform_key in self.platform_sessions:
                    self.platform_sessions[platform_key].discard(session_id)
                    if not self.platform_sessions[platform_key]:
                        del self.platform_sessions[platform_key]
                
                logger.debug("Session deleted", session_id=session_id)
    
    async def find_sessions(self, **filters) -> List[SessionContext]:
        """查找会话"""
        results = []
        
        for session in self.sessions.values():
            match = True
            
            # 按用户ID过滤
            if "user_id" in filters and session.user_id != filters["user_id"]:
                match = False
            
            # 按聊天ID过滤
            if "chat_id" in filters and session.chat_id != filters["chat_id"]:
                match = False
            
            # 按平台过滤
            if "platform" in filters:
                platform_filter = filters["platform"]
                session_platform = session.platform.value if hasattr(session.platform, 'value') else str(session.platform)
                if session_platform != platform_filter:
                    match = False
            
            # 按状态过滤
            if "status" in filters and session.metadata.get("status") != filters["status"]:
                match = False
            
            # 按会话类型过滤
            if "session_type" in filters and session.session_type != filters["session_type"]:
                match = False
            
            if match:
                results.append(session)
        
        return results
    
    async def cleanup_expired(self) -> int:
        """清理过期会话"""
        expired_sessions = []
        
        async with self.lock:
            for session_id, session in self.sessions.items():
                if session.is_expired() or session.is_idle_timeout():
                    expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.delete_session(session_id)
        
        if expired_sessions:
            logger.info("Cleaned up expired sessions", count=len(expired_sessions))
        
        return len(expired_sessions)
    
    async def get_session_count(self) -> int:
        """获取会话总数"""
        return len(self.sessions)
    
    async def get_sessions_by_user(self, user_id: str) -> List[SessionContext]:
        """获取用户的所有会话"""
        session_ids = self.user_sessions.get(user_id, set())
        return [self.sessions[sid] for sid in session_ids if sid in self.sessions and not self.sessions[sid].is_expired()]
    
    async def get_sessions_by_chat(self, chat_id: str) -> List[SessionContext]:
        """获取指定聊天的所有会话"""
        session_ids = self.chat_sessions.get(chat_id, set())
        return [self.sessions[sid] for sid in session_ids if sid in self.sessions and not self.sessions[sid].is_expired()]


class FileSessionStore(SessionStore):
    """文件会话存储实现"""
    
    def __init__(self, storage_dir: str = "sessions_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # 创建子目录
        (self.storage_dir / "sessions").mkdir(exist_ok=True)
        (self.storage_dir / "index").mkdir(exist_ok=True)
        
        self.sessions_file = self.storage_dir / "sessions.json"
        self.index_file = self.storage_dir / "index.json"
        self.lock = asyncio.Lock()
        
        # 加载现有数据
        self.sessions: Dict[str, SessionContext] = {}
        self.user_sessions: Dict[str, Set[str]] = {}
        self.chat_sessions: Dict[str, Set[str]] = {}
        self.platform_sessions: Dict[str, Set[str]] = {}
        
        asyncio.create_task(self._load_data())
    
    async def _load_data(self) -> None:
        """加载存储的数据"""
        try:
            # 加载会话数据
            if self.sessions_file.exists():
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
                    for session_data in sessions_data.values():
                        context = SessionContext.from_dict(session_data)
                        self.sessions[context.session_id] = context
            
            # 加载索引数据
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    self.user_sessions = {k: set(v) for k, v in index_data.get("user_sessions", {}).items()}
                    self.chat_sessions = {k: set(v) for k, v in index_data.get("chat_sessions", {}).items()}
                    self.platform_sessions = {k: set(v) for k, v in index_data.get("platform_sessions", {}).items()}
            
            logger.info("File session store loaded", 
                       sessions_count=len(self.sessions),
                       users_count=len(self.user_sessions),
                       chats_count=len(self.chat_sessions))
        
        except Exception as e:
            logger.error("Error loading file session store", error=str(e))
    
    async def _save_data(self) -> None:
        """保存数据到文件"""
        async with self.lock:
            try:
                # 保存会话数据
                sessions_data = {sid: context.to_dict() for sid, context in self.sessions.items()}
                with open(self.sessions_file, 'w', encoding='utf-8') as f:
                    json.dump(sessions_data, f, ensure_ascii=False, indent=2, default=str)
                
                # 保存索引数据
                index_data = {
                    "user_sessions": {k: list(v) for k, v in self.user_sessions.items()},
                    "chat_sessions": {k: list(v) for k, v in self.chat_sessions.items()},
                    "platform_sessions": {k: list(v) for k, v in self.platform_sessions.items()}
                }
                with open(self.index_file, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)
                
            except Exception as e:
                logger.error("Error saving file session store", error=str(e))
    
    async def create_session(self, context: SessionContext) -> None:
        """创建会话"""
        async with self.lock:
            self.sessions[context.session_id] = context
            
            # 更新索引
            if context.user_id not in self.user_sessions:
                self.user_sessions[context.user_id] = set()
            self.user_sessions[context.user_id].add(context.session_id)
            
            if context.chat_id not in self.chat_sessions:
                self.chat_sessions[context.chat_id] = set()
            self.chat_sessions[context.chat_id].add(context.session_id)
            
            platform_key = context.platform.value if hasattr(context.platform, 'value') else str(context.platform)
            if platform_key not in self.platform_sessions:
                self.platform_sessions[platform_key] = set()
            self.platform_sessions[platform_key].add(context.session_id)
            
            # 异步保存数据
            asyncio.create_task(self._save_data())
            logger.debug("Session created", session_id=context.session_id)
    
    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """获取会话"""
        session = self.sessions.get(session_id)
        if session and (session.is_expired() or session.is_idle_timeout()):
            await self.delete_session(session_id)
            return None
        return session
    
    async def update_session(self, context: SessionContext) -> None:
        """更新会话"""
        async with self.lock:
            if context.session_id in self.sessions:
                self.sessions[context.session_id] = context
                # 异步保存数据
                asyncio.create_task(self._save_data())
                logger.debug("Session updated", session_id=context.session_id)
    
    async def delete_session(self, session_id: str) -> None:
        """删除会话"""
        async with self.lock:
            session = self.sessions.pop(session_id, None)
            if session:
                # 清理索引
                if session.user_id in self.user_sessions:
                    self.user_sessions[session.user_id].discard(session_id)
                    if not self.user_sessions[session.user_id]:
                        del self.user_sessions[session.user_id]
                
                if session.chat_id in self.chat_sessions:
                    self.chat_sessions[session.chat_id].discard(session_id)
                    if not self.chat_sessions[session.chat_id]:
                        del self.chat_sessions[session.chat_id]
                
                platform_key = session.platform.value if hasattr(session.platform, 'value') else str(session.platform)
                if platform_key in self.platform_sessions:
                    self.platform_sessions[platform_key].discard(session_id)
                    if not self.platform_sessions[platform_key]:
                        del self.platform_sessions[platform_key]
                
                # 异步保存数据
                asyncio.create_task(self._save_data())
                logger.debug("Session deleted", session_id=session_id)
    
    async def find_sessions(self, **filters) -> List[SessionContext]:
        """查找会话"""
        results = []
        
        for session in self.sessions.values():
            match = True
            
            # 按用户ID过滤
            if "user_id" in filters and session.user_id != filters["user_id"]:
                match = False
            
            # 按聊天ID过滤
            if "chat_id" in filters and session.chat_id != filters["chat_id"]:
                match = False
            
            # 按平台过滤
            if "platform" in filters:
                platform_filter = filters["platform"]
                session_platform = session.platform.value if hasattr(session.platform, 'value') else str(session.platform)
                if session_platform != platform_filter:
                    match = False
            
            # 按状态过滤
            if "status" in filters and session.metadata.get("status") != filters["status"]:
                match = False
            
            # 按会话类型过滤
            if "session_type" in filters and session.session_type != filters["session_type"]:
                match = False
            
            if match:
                results.append(session)
        
        return results
    
    async def cleanup_expired(self) -> int:
        """清理过期会话"""
        expired_sessions = []
        
        async with self.lock:
            for session_id, session in self.sessions.items():
                if session.is_expired() or session.is_idle_timeout():
                    expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.delete_session(session_id)
        
        if expired_sessions:
            logger.info("Cleaned up expired sessions", count=len(expired_sessions))
        
        return len(expired_sessions)
    
    async def get_session_count(self) -> int:
        """获取会话总数"""
        return len(self.sessions)
    
    async def get_sessions_by_user(self, user_id: str) -> List[SessionContext]:
        """获取用户的所有会话"""
        session_ids = self.user_sessions.get(user_id, set())
        return [self.sessions[sid] for sid in session_ids if sid in self.sessions and not self.sessions[sid].is_expired()]
    
    async def get_sessions_by_chat(self, chat_id: str) -> List[SessionContext]:
        """获取指定聊天的所有会话"""
        session_ids = self.chat_sessions.get(chat_id, set())
        return [self.sessions[sid] for sid in session_ids if sid in self.sessions and not self.sessions[sid].is_expired()]


class DatabaseSessionStore(SessionStore):
    """数据库会话存储实现（SQLite）"""
    
    def __init__(self, db_path: str = "agentbus_sessions.db"):
        self.db_path = db_path
        self.lock = asyncio.Lock()
        asyncio.create_task(self._init_database())
    
    async def _init_database(self) -> None:
        """初始化数据库"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    session_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data TEXT,
                    metadata TEXT,
                    parent_session TEXT,
                    child_sessions TEXT,
                    ai_model TEXT,
                    conversation_history TEXT
                )
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_id ON sessions(user_id)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_id ON sessions(chat_id)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_platform ON sessions(platform)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_activity ON sessions(last_activity)
            """)
            
            await db.commit()
            logger.info("Database session store initialized")
    
    def _serialize_context(self, context: SessionContext) -> Dict[str, Any]:
        """序列化会话上下文"""
        return {
            "session_id": context.session_id,
            "chat_id": context.chat_id,
            "user_id": context.user_id,
            "platform": context.platform.value if hasattr(context.platform, 'value') else str(context.platform),
            "session_type": context.session_type.value if hasattr(context.session_type, 'value') else str(context.session_type),
            "created_at": context.created_at.isoformat(),
            "last_activity": context.last_activity.isoformat(),
            "data": json.dumps(context.data),
            "metadata": json.dumps(context.metadata),
            "parent_session": context.parent_session,
            "child_sessions": json.dumps(list(context.child_sessions)),
            "ai_model": context.ai_model,
            "conversation_history": json.dumps(context.conversation_history)
        }
    
    def _deserialize_context(self, row: aiosqlite.Row) -> SessionContext:
        """反序列化会话上下文"""
        from datetime import datetime
        
        # 解析JSON字段
        data = json.loads(row["data"]) if row["data"] else {}
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        child_sessions = json.loads(row["child_sessions"]) if row["child_sessions"] else []
        conversation_history = json.loads(row["conversation_history"]) if row["conversation_history"] else []
        
        # 解析枚举值
        platform = row["platform"]
        session_type = row["session_type"]
        
        return SessionContext(
            session_id=row["session_id"],
            chat_id=row["chat_id"],
            user_id=row["user_id"],
            platform=platform,
            session_type=session_type,
            created_at=datetime.fromisoformat(row["created_at"]),
            last_activity=datetime.fromisoformat(row["last_activity"]),
            data=data,
            metadata=metadata,
            parent_session=row["parent_session"],
            child_sessions=set(child_sessions),
            ai_model=row["ai_model"],
            conversation_history=conversation_history
        )
    
    async def create_session(self, context: SessionContext) -> None:
        """创建会话"""
        session_data = self._serialize_context(context)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO sessions (
                    session_id, chat_id, user_id, platform, session_type,
                    created_at, last_activity, data, metadata,
                    parent_session, child_sessions, ai_model, conversation_history
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_data["session_id"], session_data["chat_id"], session_data["user_id"],
                session_data["platform"], session_data["session_type"],
                session_data["created_at"], session_data["last_activity"],
                session_data["data"], session_data["metadata"],
                session_data["parent_session"], session_data["child_sessions"],
                session_data["ai_model"], session_data["conversation_history"]
            ))
            await db.commit()
            logger.debug("Session created", session_id=context.session_id)
    
    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """获取会话"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    context = self._deserialize_context(row)
                    # 检查是否过期
                    if context.is_expired() or context.is_idle_timeout():
                        await self.delete_session(session_id)
                        return None
                    return context
        return None
    
    async def update_session(self, context: SessionContext) -> None:
        """更新会话"""
        session_data = self._serialize_context(context)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions SET
                    chat_id = ?, user_id = ?, platform = ?, session_type = ?,
                    last_activity = ?, data = ?, metadata = ?,
                    parent_session = ?, child_sessions = ?, ai_model = ?,
                    conversation_history = ?
                WHERE session_id = ?
            """, (
                session_data["chat_id"], session_data["user_id"],
                session_data["platform"], session_data["session_type"],
                session_data["last_activity"], session_data["data"], session_data["metadata"],
                session_data["parent_session"], session_data["child_sessions"],
                session_data["ai_model"], session_data["conversation_history"],
                session_data["session_id"]
            ))
            await db.commit()
            logger.debug("Session updated", session_id=context.session_id)
    
    async def delete_session(self, session_id: str) -> None:
        """删除会话"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            await db.commit()
            logger.debug("Session deleted", session_id=session_id)
    
    async def find_sessions(self, **filters) -> List[SessionContext]:
        """查找会话"""
        where_clauses = []
        params = []
        
        for key, value in filters.items():
            if key == "user_id":
                where_clauses.append("user_id = ?")
                params.append(value)
            elif key == "chat_id":
                where_clauses.append("chat_id = ?")
                params.append(value)
            elif key == "platform":
                where_clauses.append("platform = ?")
                params.append(value)
            elif key == "status":
                where_clauses.append("metadata LIKE ?")
                params.append(f'%"status": "{value}"%')
            elif key == "session_type":
                where_clauses.append("session_type = ?")
                params.append(value)
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = f"SELECT * FROM sessions WHERE {where_clause}"
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [self._deserialize_context(row) for row in rows]
    
    async def cleanup_expired(self) -> int:
        """清理过期会话"""
        from datetime import datetime
        
        # 查找过期的会话
        expired_sessions = []
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions") as cursor:
                rows = await cursor.fetchall()
                
                for row in rows:
                    context = self._deserialize_context(row)
                    if context.is_expired() or context.is_idle_timeout():
                        expired_sessions.append(context.session_id)
        
        # 删除过期会话
        for session_id in expired_sessions:
            await self.delete_session(session_id)
        
        if expired_sessions:
            logger.info("Cleaned up expired sessions", count=len(expired_sessions))
        
        return len(expired_sessions)
    
    async def get_session_count(self) -> int:
        """获取会话总数"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) as count FROM sessions") as cursor:
                row = await cursor.fetchone()
                return row["count"]
    
    async def get_sessions_by_user(self, user_id: str) -> List[SessionContext]:
        """获取用户的所有会话"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions WHERE user_id = ?", (user_id,)) as cursor:
                rows = await cursor.fetchall()
                sessions = []
                for row in rows:
                    context = self._deserialize_context(row)
                    if not context.is_expired():
                        sessions.append(context)
                return sessions
    
    async def get_sessions_by_chat(self, chat_id: str) -> List[SessionContext]:
        """获取指定聊天的所有会话"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM sessions WHERE chat_id = ?", (chat_id,)) as cursor:
                rows = await cursor.fetchall()
                sessions = []
                for row in rows:
                    context = self._deserialize_context(row)
                    if not context.is_expired():
                        sessions.append(context)
                return sessions
    
    async def close(self) -> None:
        """关闭数据库连接"""
        # SQLite连接会自动关闭，这里主要用于清理资源
        logger.info("Database session store closed")


def create_session_store(storage_type: StorageType, **kwargs) -> SessionStore:
    """创建会话存储实例"""
    if storage_type == StorageType.MEMORY:
        return MemorySessionStore()
    elif storage_type == StorageType.FILE:
        storage_dir = kwargs.get("storage_dir", "sessions_data")
        return FileSessionStore(storage_dir)
    elif storage_type == StorageType.DATABASE:
        db_path = kwargs.get("db_path", "agentbus_sessions.db")
        return DatabaseSessionStore(db_path)
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")


# 默认会话存储实例
_default_store: Optional[SessionStore] = None


def get_default_session_store() -> SessionStore:
    """获取默认会话存储实例"""
    global _default_store
    if _default_store is None:
        _default_store = MemorySessionStore()  # 默认使用内存存储
    return _default_store


async def set_default_session_store(store: SessionStore) -> None:
    """设置默认会话存储实例"""
    global _default_store
    _default_store = store