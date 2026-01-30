"""
会话管理器模块
Session Manager Module

负责会话的完整生命周期管理
提供会话创建、查找、更新、清理等核心功能
"""

from typing import Dict, Any, Optional, List, Set, Union
from datetime import datetime, timedelta
import asyncio
import logging
from contextlib import asynccontextmanager

from .context_manager import (
    SessionContext, SessionType, SessionStatus, Message, 
    MessageType, Platform, get_context_manager
)
from .session_storage import SessionStore, create_session_store, StorageType

logger = logging.getLogger(__name__)


class SessionManager:
    """会话管理器 - 负责会话的完整生命周期管理"""
    
    def __init__(
        self, 
        session_store: Optional[SessionStore] = None,
        enable_cleanup: bool = True,
        cleanup_interval: int = 300  # 5分钟
    ):
        self.store = session_store or create_session_store(StorageType.MEMORY)
        self.enable_cleanup = enable_cleanup
        self.cleanup_interval = cleanup_interval
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cleanup_task: Optional[asyncio.Task] = None
        self._context_manager = get_context_manager()
    
    async def start(self) -> None:
        """启动会话管理器"""
        if self.enable_cleanup:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            self.logger.info("Session manager started", cleanup_interval=self.cleanup_interval)
    
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
        chat_id: str = "",
        user_id: str = "",
        platform: Union[str, Platform] = "",
        session_type: Union[str, SessionType] = SessionType.PRIVATE,
        parent_session: Optional[str] = None,
        **metadata
    ) -> SessionContext:
        """创建新会话"""
        
        # 生成会话ID
        import uuid
        session_id = str(uuid.uuid4())
        
        # 创建会话上下文
        context = await self._context_manager.create_context(
            session_id=session_id,
            chat_id=chat_id,
            user_id=user_id,
            platform=platform,
            session_type=session_type,
            parent_session=parent_session,
            **metadata
        )
        
        # 设置默认配置
        context.metadata.setdefault("max_history", 50)
        context.metadata.setdefault("idle_timeout", 3600)  # 1小时
        context.metadata.setdefault("expires_in", None)  # 不过期
        context.metadata.setdefault("status", SessionStatus.ACTIVE.value)
        
        # 设置AI配置
        context.ai_model = metadata.get("ai_model")
        
        # 保存到存储
        await self.store.create_session(context)
        
        # 建立父子关系
        if parent_session:
            parent = await self.get_session(parent_session)
            if parent:
                parent.add_child_session(session_id)
                await self.update_session(parent)
        
        self.logger.info("Session created", 
                        session_id=session_id,
                        user_id=user_id,
                        chat_id=chat_id,
                        platform=str(platform))
        
        return context
    
    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """获取会话"""
        # 先从存储获取
        context = await self.store.get_session(session_id)
        
        if context:
            # 更新本地缓存
            await self._context_manager.update_context(context)
        
        return context
    
    async def get_user_session(
        self, 
        user_id: str, 
        chat_id: str, 
        platform: Union[str, Platform]
    ) -> Optional[SessionContext]:
        """获取用户的指定聊天会话"""
        sessions = await self.store.find_sessions(
            user_id=user_id,
            chat_id=chat_id,
            platform=str(platform)
        )
        
        # 优先返回活跃会话
        for session in sessions:
            if session.is_active():
                # 更新本地缓存
                await self._context_manager.update_context(session)
                return session
        
        return None
    
    async def update_session(self, context: SessionContext) -> None:
        """更新会话"""
        await self._context_manager.update_context(context)
        await self.store.update_session(context)
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        session = await self.get_session(session_id)
        if session:
            # 清理父子关系
            if session.parent_session:
                parent = await self.get_session(session.parent_session)
                if parent:
                    parent.remove_child_session(session_id)
                    await self.update_session(parent)
            
            # 清理子会话
            for child_id in list(session.child_sessions):
                await self.delete_session(child_id)
            
            # 从存储和缓存中删除
            await self.store.delete_session(session_id)
            await self._context_manager.remove_context(session_id)
            
            self.logger.info("Session deleted", session_id=session_id)
            return True
        return False
    
    async def add_message_to_session(
        self, 
        session_id: str, 
        message: Union[Message, Dict[str, Any]]
    ) -> bool:
        """添加消息到会话"""
        session = await self.get_session(session_id)
        if session:
            session.add_message(message)
            await self.update_session(session)
            return True
        return False
    
    async def cleanup_all_expired(self) -> int:
        """清理所有过期会话"""
        # 从存储清理
        storage_cleaned = await self.store.cleanup_expired()
        
        # 从上下文管理器清理
        context_cleaned = await self._context_manager.clear_expired_contexts()
        
        total_cleaned = max(storage_cleaned, context_cleaned)
        
        if total_cleaned > 0:
            self.logger.info("Cleanup completed", 
                           storage_cleaned=storage_cleaned,
                           context_cleaned=context_cleaned,
                           total=total_cleaned)
        
        return total_cleaned
    
    async def _periodic_cleanup(self) -> None:
        """定期清理过期会话"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                cleaned_count = await self.cleanup_all_expired()
                
                if cleaned_count > 0:
                    self.logger.debug("Periodic cleanup completed", 
                                   cleaned_count=cleaned_count,
                                   interval=self.cleanup_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error during periodic cleanup", error=str(e))
                await asyncio.sleep(self.cleanup_interval * 2)
    
    async def create_session_from_message(
        self,
        message: Union[Message, Dict[str, Any]]
    ) -> SessionContext:
        """从消息创建会话"""
        if isinstance(message, dict):
            msg = Message.from_dict(message)
        else:
            msg = message
        
        # 尝试获取现有会话
        existing_session = await self.get_user_session(
            user_id=msg.user_id,
            chat_id=msg.chat_id,
            platform=msg.platform
        )
        
        if existing_session:
            # 添加消息到现有会话
            existing_session.add_message(msg)
            await self.update_session(existing_session)
            return existing_session
        else:
            # 创建新会话
            new_session = await self.create_session(
                chat_id=msg.chat_id,
                user_id=msg.user_id,
                platform=msg.platform
            )
            
            # 添加第一条消息
            new_session.add_message(msg)
            await self.update_session(new_session)
            
            return new_session


# 会话上下文管理器
@asynccontextmanager
async def session_context(
    session_manager: SessionManager,
    chat_id: str,
    user_id: str,
    platform: Union[str, Platform],
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


async def init_session_manager(
    session_store: Optional[SessionStore] = None,
    enable_cleanup: bool = True
) -> SessionManager:
    """初始化全局会话管理器"""
    global _session_manager
    
    if session_store:
        _session_manager = SessionManager(session_store, enable_cleanup)
    else:
        _session_manager = SessionManager(enable_cleanup=enable_cleanup)
    
    await _session_manager.start()
    return _session_manager


async def shutdown_session_manager() -> None:
    """关闭全局会话管理器"""
    global _session_manager
    if _session_manager:
        await _session_manager.stop()
        _session_manager = None


# 便捷函数
async def create_session(
    chat_id: str = "",
    user_id: str = "",
    platform: Union[str, Platform] = "",
    **kwargs
) -> SessionContext:
    """创建会话的便捷函数"""
    manager = get_session_manager()
    return await manager.create_session(chat_id, user_id, platform, **kwargs)


async def get_session(session_id: str) -> Optional[SessionContext]:
    """获取会话的便捷函数"""
    manager = get_session_manager()
    return await manager.get_session(session_id)


async def add_message(session_id: str, message: Union[Message, Dict[str, Any]]) -> bool:
    """添加消息的便捷函数"""
    manager = get_session_manager()
    return await manager.add_message_to_session(session_id, message)