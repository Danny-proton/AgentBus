"""
上下文管理模块
Context Manager Module

负责会话上下文的创建、管理和维护
提供上下文的序列化、反序列化和验证功能
"""

from typing import Dict, Any, Optional, List, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
import uuid
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


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


class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    LOCATION = "location"
    SYSTEM = "system"


class Platform(Enum):
    """平台枚举"""
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    WECHAT = "wechat"
    WEB = "web"
    API = "api"


@dataclass
class Message:
    """消息类"""
    id: str
    content: Any
    user_id: str
    timestamp: datetime
    message_type: MessageType
    platform: Platform
    chat_id: str = ""
    session_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": str(self.content) if hasattr(self.content, '__str__') else self.content,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "message_type": self.message_type.value if hasattr(self.message_type, 'value') else str(self.message_type),
            "platform": self.platform.value if hasattr(self.platform, 'value') else str(self.platform),
            "chat_id": self.chat_id,
            "session_id": self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建消息"""
        return cls(
            id=data["id"],
            content=data["content"],
            user_id=data["user_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            message_type=data["message_type"],
            platform=data["platform"],
            chat_id=data.get("chat_id", ""),
            session_id=data.get("session_id", "")
        )


@dataclass
class SessionContext:
    """会话上下文数据类"""
    session_id: str
    chat_id: str
    platform: Union[str, Platform]
    user_id: str
    session_type: Union[str, SessionType]
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
    
    def add_message(self, message: Union[Message, Dict[str, Any]]) -> None:
        """添加消息到历史记录"""
        if isinstance(message, dict):
            message_data = message
        else:
            message_data = message.to_dict()
        
        # 确保必要字段存在
        if "timestamp" in message_data and isinstance(message_data["timestamp"], datetime):
            message_data["timestamp"] = message_data["timestamp"].isoformat()
        
        # 保持历史记录在合理范围内
        max_history = self.metadata.get("max_history", 50)
        self.conversation_history.append(message_data)
        
        if len(self.conversation_history) > max_history:
            self.conversation_history = self.conversation_history[-max_history:]
        
        # 更新最后活动时间
        self.last_activity = datetime.now()
        
        logger.debug("Message added to session", 
                    session_id=self.session_id,
                    message_id=message_data.get("id", "unknown"),
                    history_size=len(self.conversation_history))
    
    def get_conversation_context(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """获取对话上下文"""
        return self.conversation_history[-max_messages:]
    
    def set_data(self, key: str, value: Any) -> None:
        """设置会话数据"""
        self.data[key] = value
        self.last_activity = datetime.now()
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """获取会话数据"""
        return self.data.get(key, default)
    
    def remove_data(self, key: str) -> bool:
        """删除会话数据"""
        if key in self.data:
            del self.data[key]
            self.last_activity = datetime.now()
            return True
        return False
    
    def is_expired(self) -> bool:
        """检查会话是否过期"""
        if not self.metadata.get("expires_in"):
            return False
        
        try:
            expiry_seconds = int(self.metadata["expires_in"])
            expiry_time = self.created_at + timedelta(seconds=expiry_seconds)
            return datetime.now() > expiry_time
        except (ValueError, TypeError):
            return False
    
    def is_idle_timeout(self) -> bool:
        """检查是否空闲超时"""
        try:
            idle_timeout = int(self.metadata.get("idle_timeout", 3600))  # 默认1小时
            return (datetime.now() - self.last_activity).total_seconds() > idle_timeout
        except (ValueError, TypeError):
            return False
    
    def is_active(self) -> bool:
        """检查会话是否活跃"""
        return (not self.is_expired() and 
                not self.is_idle_timeout() and
                self.metadata.get("status") != SessionStatus.CLOSED.value)
    
    def get_status(self) -> SessionStatus:
        """获取会话状态"""
        status_str = self.metadata.get("status", SessionStatus.ACTIVE.value)
        try:
            return SessionStatus(status_str)
        except ValueError:
            return SessionStatus.ACTIVE
    
    def set_status(self, status: SessionStatus) -> None:
        """设置会话状态"""
        self.metadata["status"] = status.value
        self.last_activity = datetime.now()
    
    def add_child_session(self, child_session_id: str) -> None:
        """添加子会话"""
        self.child_sessions.add(child_session_id)
        self.last_activity = datetime.now()
    
    def remove_child_session(self, child_session_id: str) -> None:
        """移除子会话"""
        self.child_sessions.discard(child_session_id)
        self.last_activity = datetime.now()
    
    def get_summary(self) -> Dict[str, Any]:
        """获取会话摘要信息"""
        return {
            "session_id": self.session_id,
            "chat_id": self.chat_id,
            "user_id": self.user_id,
            "platform": self.platform.value if hasattr(self.platform, 'value') else str(self.platform),
            "session_type": self.session_type.value if hasattr(self.session_type, 'value') else str(self.session_type),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "status": self.get_status().value,
            "is_expired": self.is_expired(),
            "is_idle_timeout": self.is_idle_timeout(),
            "is_active": self.is_active(),
            "message_count": len(self.conversation_history),
            "data_keys": list(self.data.keys()),
            "metadata_keys": list(self.metadata.keys()),
            "child_sessions_count": len(self.child_sessions),
            "has_parent": self.parent_session is not None,
            "ai_model": self.ai_model
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "chat_id": self.chat_id,
            "platform": self.platform.value if hasattr(self.platform, 'value') else str(self.platform),
            "user_id": self.user_id,
            "session_type": self.session_type.value if hasattr(self.session_type, 'value') else str(self.session_type),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "data": self.data,
            "metadata": self.metadata,
            "parent_session": self.parent_session,
            "child_sessions": list(self.child_sessions),
            "ai_model": self.ai_model,
            "conversation_history": self.conversation_history
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionContext':
        """从字典创建会话上下文"""
        # 处理日期时间字段
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
        
        last_activity = data.get("last_activity")
        if isinstance(last_activity, str):
            last_activity = datetime.fromisoformat(last_activity)
        elif last_activity is None:
            last_activity = datetime.now()
        
        # 处理child_sessions
        child_sessions = set(data.get("child_sessions", []))
        
        return cls(
            session_id=data["session_id"],
            chat_id=data["chat_id"],
            platform=data["platform"],
            user_id=data["user_id"],
            session_type=data["session_type"],
            created_at=created_at,
            last_activity=last_activity,
            data=data.get("data", {}),
            metadata=data.get("metadata", {}),
            parent_session=data.get("parent_session"),
            child_sessions=child_sessions,
            ai_model=data.get("ai_model"),
            conversation_history=data.get("conversation_history", [])
        )
    
    def validate(self) -> bool:
        """验证会话上下文的有效性"""
        required_fields = ["session_id", "chat_id", "platform", "user_id", "session_type"]
        
        for field in required_fields:
            if not hasattr(self, field) or getattr(self, field) is None:
                logger.warning("Invalid session context", field=field, session_id=self.session_id)
                return False
        
        # 验证会话ID格式
        try:
            uuid.UUID(self.session_id)
        except ValueError:
            logger.warning("Invalid session ID format", session_id=self.session_id)
            return False
        
        # 验证时间字段
        if self.created_at > datetime.now() + timedelta(days=1):
            logger.warning("Created time is in the future", session_id=self.session_id)
            return False
        
        return True
    
    def update_activity(self) -> None:
        """更新会话活动时间"""
        self.now()
    
    def extend_lifetime(self, seconds: int) -> None:
        """延长会话生命周期"""
        current_expires = self.metadata.get("expires_in", 0)
        if current_expires:
            self.metadata["expires_in"] = int(current_expires) + seconds
        else:
            self.metadata["expires_in"] = seconds
        self.last_activity = datetime.now()
    
    def reset_conversation_history(self, keep_recent: int = 0) -> None:
        """重置对话历史"""
        if keep_recent > 0:
            self.conversation_history = self.conversation_history[-keep_recent:]
        else:
            self.conversation_history = []
        self.last_activity = datetime.now()
        logger.debug("Conversation history reset", 
                    session_id=self.session_id,
                    kept_messages=keep_recent)
    
    def get_recent_messages(self, count: int = 5) -> List[Dict[str, Any]]:
        """获取最近的N条消息"""
        return self.conversation_history[-count:] if count > 0 else []
    
    def get_messages_by_user(self, user_id: str = None) -> List[Dict[str, Any]]:
        """获取指定用户的消息"""
        if user_id is None:
            return self.conversation_history.copy()
        
        return [msg for msg in self.conversation_history 
                if msg.get("user_id") == user_id]
    
    def search_messages(self, keyword: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """搜索消息内容"""
        if not case_sensitive:
            keyword = keyword.lower()
        
        results = []
        for msg in self.conversation_history:
            content = str(msg.get("content", ""))
            if not case_sensitive:
                content = content.lower()
            
            if keyword in content:
                results.append(msg)
        
        return results


class ContextManager:
    """上下文管理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._context_cache: Dict[str, SessionContext] = {}
        self._cache_lock = asyncio.Lock() if False else None  # 简化版本，暂时不使用锁
    
    async def create_context(
        self,
        session_id: Optional[str] = None,
        chat_id: str = "",
        user_id: str = "",
        platform: Union[str, Platform] = "",
        session_type: Union[str, SessionType] = SessionType.PRIVATE,
        **kwargs
    ) -> SessionContext:
        """创建新的会话上下文"""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # 创建上下文
        context = SessionContext(
            session_id=session_id,
            chat_id=chat_id,
            platform=platform,
            user_id=user_id,
            session_type=session_type,
            **kwargs
        )
        
        # 设置默认值
        context.metadata.setdefault("max_history", 50)
        context.metadata.setdefault("idle_timeout", 3600)  # 1小时
        context.metadata.setdefault("expires_in", None)  # 不过期
        context.metadata.setdefault("status", SessionStatus.ACTIVE.value)
        
        # 验证上下文
        if not context.validate():
            raise ValueError(f"Invalid session context: {session_id}")
        
        # 添加到缓存
        self._context_cache[session_id] = context
        
        self.logger.info("Context created", 
                        session_id=session_id,
                        user_id=user_id,
                        chat_id=chat_id,
                        platform=platform.value if hasattr(platform, 'value') else str(platform))
        
        return context
    
    async def get_context(self, session_id: str) -> Optional[SessionContext]:
        """获取会话上下文"""
        context = self._context_cache.get(session_id)
        
        if context and not context.is_expired():
            return context
        
        # 如果上下文过期，从缓存中移除
        if context:
            await self.remove_context(session_id)
        
        return None
    
    async def update_context(self, context: SessionContext) -> None:
        """更新会话上下文"""
        # 验证上下文
        if not context.validate():
            raise ValueError(f"Invalid session context: {context.session_id}")
        
        # 更新缓存
        self._context_cache[context.session_id] = context
        
        self.logger.debug("Context updated", session_id=context.session_id)
    
    async def remove_context(self, session_id: str) -> bool:
        """移除会话上下文"""
        if session_id in self._context_cache:
            del self._context_cache[session_id]
            self.logger.debug("Context removed", session_id=session_id)
            return True
        return False
    
    async def clear_expired_contexts(self) -> int:
        """清理过期的上下文"""
        expired_ids = []
        
        for session_id, context in self._context_cache.items():
            if context.is_expired() or context.is_idle_timeout():
                expired_ids.append(session_id)
        
        for session_id in expired_ids:
            await self.remove_context(session_id)
        
        if expired_ids:
            self.logger.info("Expired contexts cleared", count=len(expired_ids))
        
        return len(expired_ids)
    
    async def get_contexts_by_user(self, user_id: str) -> List[SessionContext]:
        """获取用户的所有上下文"""
        return [ctx for ctx in self._context_cache.values() 
                if ctx.user_id == user_id and not ctx.is_expired()]
    
    async def get_contexts_by_chat(self, chat_id: str) -> List[SessionContext]:
        """获取指定聊天的所有上下文"""
        return [ctx for ctx in self._context_cache.values() 
                if ctx.chat_id == chat_id and not ctx.is_expired()]
    
    async def get_contexts_by_platform(self, platform: Union[str, Platform]) -> List[SessionContext]:
        """获取指定平台的所有上下文"""
        platform_str = platform.value if hasattr(platform, 'value') else str(platform)
        return [ctx for ctx in self._context_cache.values() 
                if (ctx.platform.value if hasattr(ctx.platform, 'value') else str(ctx.platform)) == platform_str 
                and not ctx.is_expired()]
    
    async def export_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """导出上下文数据"""
        context = await self.get_context(session_id)
        if context:
            return context.to_dict()
        return None
    
    async def import_context(self, context_data: Dict[str, Any]) -> Optional[SessionContext]:
        """导入上下文数据"""
        try:
            context = SessionContext.from_dict(context_data)
            
            # 验证上下文
            if not context.validate():
                self.logger.warning("Invalid context data during import", session_id=context.session_id)
                return None
            
            # 添加到缓存
            await self.update_context(context)
            
            self.logger.info("Context imported", session_id=context.session_id)
            return context
        
        except Exception as e:
            self.logger.error("Error importing context", error=str(e))
            return None
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_contexts = len(self._context_cache)
        active_contexts = sum(1 for ctx in self._context_cache.values() if ctx.is_active())
        expired_contexts = sum(1 for ctx in self._context_cache.values() if ctx.is_expired())
        
        # 按平台统计
        platform_stats = {}
        for ctx in self._context_cache.values():
            platform = ctx.platform.value if hasattr(ctx.platform, 'value') else str(ctx.platform)
            platform_stats[platform] = platform_stats.get(platform, 0) + 1
        
        # 按类型统计
        type_stats = {}
        for ctx in self._context_cache.values():
            session_type = ctx.session_type.value if hasattr(ctx.session_type, 'value') else str(ctx.session_type)
            type_stats[session_type] = type_stats.get(session_type, 0) + 1
        
        return {
            "total_contexts": total_contexts,
            "active_contexts": active_contexts,
            "expired_contexts": expired_contexts,
            "platform_stats": platform_stats,
            "type_stats": type_stats,
            "user_count": len(set(ctx.user_id for ctx in self._context_cache.values())),
            "chat_count": len(set(ctx.chat_id for ctx in self._context_cache.values()))
        }
    
    async def cleanup_all(self) -> int:
        """清理所有过期和无效的上下文"""
        expired_count = await self.clear_expired_contexts()
        
        # 移除无效的上下文
        invalid_count = 0
        invalid_ids = []
        
        for session_id, context in self._context_cache.items():
            if not context.validate():
                invalid_ids.append(session_id)
        
        for session_id in invalid_ids:
            await self.remove_context(session_id)
            invalid_count += 1
        
        if invalid_count > 0:
            self.logger.info("Invalid contexts removed", count=invalid_count)
        
        total_cleaned = expired_count + invalid_count
        
        if total_cleaned > 0:
            self.logger.info("Cleanup completed", 
                           expired=expired_count, 
                           invalid=invalid_count, 
                           total=total_cleaned)
        
        return total_cleaned


# 全局上下文管理器实例
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """获取全局上下文管理器"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


async def init_context_manager() -> None:
    """初始化全局上下文管理器"""
    manager = get_context_manager()
    await manager.cleanup_all()  # 启动时清理过期上下文


async def shutdown_context_manager() -> None:
    """关闭全局上下文管理器"""
    global _context_manager
    if _context_manager:
        _context_manager = None