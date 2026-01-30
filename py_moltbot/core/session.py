"""
会话管理系统
Session Management System
"""

from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import asyncio
import json
import uuid
from contextlib import asynccontextmanager

from ..core.logger import get_logger
from ..core.config import settings
from ..adapters.base import User, Message, AdapterType

logger = get_logger(__name__)


class SessionType(Enum):
    """会话类型枚举"""
    PRIVATE = "private"      # 私聊会话
    GROUP = "group"          # 群组会话
    SYSTEM = "system"        # 系统会话
    TEMPORARY = "temporary"  # 临时会话


class SessionStatus(Enum):
    """会话状态枚举"""
    ACTIVE = "active"        # 活跃
    IDLE = "idle"           # 空闲
    SUSPENDED = "suspended"  # 暂停
    EXPIRED = "expired"     # 过期
    CLOSED = "closed"       # 关闭


@dataclass
class SessionContext:
    """会话上下文数据"""
    session_id: str
    chat_id: str
    platform: AdapterType
    user_id: str
    session_type: SessionType
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    # 会话数据
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 引用其他会话
    parent_session: Optional[str] = None
    child_sessions: Set[str] = field(default_factory=set)
    
    # AI相关
    ai_model: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_message(self, message: Message) -> None:
        """添加消息到历史记录"""
        message_data = {
            "id": message.id,
            "timestamp": message.timestamp.isoformat(),
            "user_id": message.user_id,
            "content": str(message.content),
            "message_type": message.message_type.value,
            "platform": message.platform.value
        }
        
        # 保持历史记录在合理范围内
        max_history = self.metadata.get("max_history", 50)
        self.conversation_history.append(message_data)
        
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
        
        # 更新最后活动时间
        self.last_activity = datetime.now()
    
    def get_conversation_context(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """获取对话上下文"""
        return self.conversation_history[-max_messages:]
    
    def set_data(self, key: str, value: Any) -> None:
        """设置会话数据"""
        self.data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """获取会话数据"""
        return self.data.get(key, default)
    
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        if not self.metadata.get("expires_in"):
            return False
        
        expiry_time = self.created_at + timedelta(seconds=self.metadata["expires_in"])
        return datetime.now() > expiry_time
    
    def is_idle_timeout(self) -> bool:
        """检查是否空闲超时"""
        idle_timeout = self.metadata.get("idle_timeout", 3600)  # 默认1小时
        return (datetime.now() - self.last_activity).total_seconds() > idle_timeout


class SessionStore:
    """会话存储抽象"""
    
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


class MemorySessionStore(SessionStore):
    """内存会话存储（用于开发和小规模部署）"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionContext] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> session_ids
        self.chat_sessions: Dict[str, Set[str]] = {}  # chat_id -> session_ids
        self.logger = get_logger(self.__class__.__name__)
    
    async def create_session(self, context: SessionContext) -> None:
        """创建会话"""
        self.sessions[context.session_id] = context
        
        # 更新索引
        if context.user_id not in self.user_sessions:
            self.user_sessions[context.user_id] = set()
        self.user_sessions[context.user_id].add(context.session_id)
        
        if context.chat_id not in self.chat_sessions:
            self.chat_sessions[context.chat_id] = set()
        self.chat_sessions[context.chat_id].add(context.session_id)
        
        self.logger.debug("Session created", session_id=context.session_id)
    
    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """获取会话"""
        session = self.sessions.get(session_id)
        if session and session.is_expired():
            await self.delete_session(session_id)
            return None
        return session
    
    async def update_session(self, context: SessionContext) -> None:
        """更新会话"""
        if context.session_id in self.sessions:
            self.sessions[context.session_id] = context
            self.logger.debug("Session updated", session_id=context.session_id)
    
    async def delete_session(self, session_id: str) -> None:
        """删除会话"""
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
            
            self.logger.debug("Session deleted", session_id=session_id)
    
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
            if "platform" in filters and session.platform != filters["platform"]:
                match = False
            
            # 按状态过滤
            if "status" in filters and session.metadata.get("status") != filters["status"]:
                match = False
            
            if match:
                results.append(session)
        
        return results
    
    async def cleanup_expired(self) -> int:
        """清理过期会话"""
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.is_expired() or session.is_idle_timeout():
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.delete_session(session_id)
        
        if expired_sessions:
            self.logger.info("Cleaned up expired sessions", count=len(expired_sessions))
        
        return len(expired_sessions)


class SessionManager:
    """会话管理器"""
    
    def __init__(self, session_store: Optional[SessionStore] = None):
        self.store = session_store or MemorySessionStore()
        self.logger = get_logger(self.__class__.__name__)
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """启动会话管理器"""
        # 启动定期清理任务
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        self.logger.info("Session manager started")
    
    async def stop(self) -> None:
        """停止会话管理器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Session manager stopped")
    
    async def create_session(
        self,
        chat_id: str,
        user_id: str,
        platform: AdapterType,
        session_type: SessionType = SessionType.PRIVATE,
        parent_session: Optional[str] = None,
        **metadata
    ) -> SessionContext:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        
        # 创建会话上下文
        context = SessionContext(
            session_id=session_id,
            chat_id=chat_id,
            platform=platform,
            user_id=user_id,
            session_type=session_type,
            parent_session=parent_session,
            metadata=metadata
        )
        
        # 设置默认配置
        context.metadata.setdefault("max_history", 50)
        context.metadata.setdefault("idle_timeout", 3600)  # 1小时
        context.metadata.setdefault("expires_in", None)  # 不过期
        
        # 设置AI配置
        context.ai_model = metadata.get("ai_model", settings.ai.default_model)
        
        # 保存到存储
        await self.store.create_session(context)
        
        # 建立父子关系
        if parent_session:
            parent = await self.get_session(parent_session)
            if parent:
                parent.child_sessions.add(session_id)
        
        self.logger.info("Session created", 
                        session_id=session_id,
                        user_id=user_id,
                        chat_id=chat_id,
                        platform=platform.value)
        
        return context
    
    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """获取会话"""
        return await self.store.get_session(session_id)
    
    async def get_user_session(
        self, 
        user_id: str, 
        chat_id: str, 
        platform: AdapterType
    ) -> Optional[SessionContext]:
        """获取用户的指定聊天会话"""
        sessions = await self.store.find_sessions(
            user_id=user_id,
            chat_id=chat_id,
            platform=platform
        )
        
        # 优先返回活跃会话
        for session in sessions:
            if not session.is_expired() and not session.is_idle_timeout():
                return session
        
        return None
    
    async def get_user_sessions(self, user_id: str) -> List[SessionContext]:
        """获取用户的所有会话"""
        sessions = await self.store.find_sessions(user_id=user_id)
        return [s for s in sessions if not s.is_expired()]
    
    async def update_session(self, context: SessionContext) -> None:
        """更新会话"""
        await self.store.update_session(context)
    
    async def add_message_to_session(self, session_id: str, message: Message) -> None:
        """添加消息到会话"""
        session = await self.get_session(session_id)
        if session:
            session.add_message(message)
            await self.update_session(session)
    
    async def delete_session(self, session_id: str) -> None:
        """删除会话"""
        session = await self.get_session(session_id)
        if session:
            # 清理父子关系
            if session.parent_session:
                parent = await self.get_session(session.parent_session)
                if parent:
                    parent.child_sessions.discard(session_id)
            
            # 清理子会话
            for child_id in list(session.child_sessions):
                await self.delete_session(child_id)
            
            await self.store.delete_session(session_id)
    
    async def close_user_sessions(self, user_id: str) -> int:
        """关闭用户的所有会话"""
        sessions = await self.get_user_sessions(user_id)
        count = len(sessions)
        
        for session in sessions:
            session.metadata["status"] = SessionStatus.CLOSED.value
            await self.update_session(session)
        
        self.logger.info("Closed user sessions", user_id=user_id, count=count)
        return count
    
    async def cleanup_all_expired(self) -> int:
        """清理所有过期会话"""
        return await self.store.cleanup_expired()
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        all_sessions = await self.store.find_sessions()
        
        active_sessions = [s for s in all_sessions if not s.is_expired()]
        expired_sessions = [s for s in all_sessions if s.is_expired()]
        
        # 按平台统计
        platform_stats = {}
        for session in active_sessions:
            platform = session.platform.value
            platform_stats[platform] = platform_stats.get(platform, 0) + 1
        
        # 按类型统计
        type_stats = {}
        for session in active_sessions:
            session_type = session.session_type.value
            type_stats[session_type] = type_stats.get(session_type, 0) + 1
        
        return {
            "total_sessions": len(all_sessions),
            "active_sessions": len(active_sessions),
            "expired_sessions": len(expired_sessions),
            "platform_stats": platform_stats,
            "type_stats": type_stats,
            "user_count": len(set(s.user_id for s in active_sessions)),
            "chat_count": len(set(s.chat_id for s in active_sessions))
        }
    
    async def _periodic_cleanup(self) -> None:
        """定期清理过期会话"""
        while True:
            try:
                await asyncio.sleep(300)  # 5分钟清理一次
                expired_count = await self.cleanup_all_expired()
                if expired_count > 0:
                    self.logger.debug("Periodic cleanup completed", expired_count=expired_count)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error during periodic cleanup", error=str(e))


# 会话上下文管理器
@asynccontextmanager
async def session_context(
    session_manager: SessionManager,
    chat_id: str,
    user_id: str,
    platform: AdapterType,
    **kwargs
):
    """会话上下文管理器"""
    session = None
    try:
        # 尝试获取现有会话
        session = await session_manager.get_user_session(user_id, chat_id, platform)
        
        if not session:
            # 创建新会话
            session = await session_manager.create_session(
                chat_id=chat_id,
                user_id=user_id,
                platform=platform,
                **kwargs
            )
        
        yield session
        
    finally:
        # 更新会话（如果被修改）
        if session:
            await session_manager.update_session(session)


# 全局会话管理器实例
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """获取全局会话管理器"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


async def init_session_manager() -> None:
    """初始化全局会话管理器"""
    manager = get_session_manager()
    await manager.start()


async def shutdown_session_manager() -> None:
    """关闭全局会话管理器"""
    global _session_manager
    if _session_manager:
        await _session_manager.stop()
        _session_manager = None