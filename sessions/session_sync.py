"""
会话同步模块
Session Synchronization Module

负责跨通道会话同步和会话聚合功能
支持多平台、多通道的会话关联和同步
"""

from typing import Dict, List, Optional, Set, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum, auto
import asyncio
import logging
import json
import hashlib
from pathlib import Path

from .context_manager import SessionContext, Platform, SessionType
from .session_storage import SessionStore

logger = logging.getLogger(__name__)


class SyncStrategy(Enum):
    """同步策略枚举"""
    MANUAL = "manual"              # 手动同步
    AUTO = "auto"                  # 自动同步
    DELAYED = "delayed"           # 延迟同步
    BATCH = "batch"               # 批量同步


class SyncStatus(Enum):
    """同步状态枚举"""
    PENDING = "pending"           # 待同步
    SYNCING = "syncing"          # 同步中
    COMPLETED = "completed"       # 同步完成
    FAILED = "failed"            # 同步失败
    CONFLICT = "conflict"        # 冲突


@dataclass
class SessionSyncConfig:
    """会话同步配置"""
    strategy: SyncStrategy = SyncStrategy.AUTO
    sync_interval: int = 60  # 同步间隔（秒）
    max_sync_retries: int = 3
    conflict_resolution: str = "latest_wins"  # latest_wins, manual, source_priority
    enable_cross_platform: bool = True
    enable_identity_linking: bool = True
    priority_source: Optional[str] = None  # 优先级源平台


@dataclass
class SessionIdentity:
    """会话身份标识"""
    identity_key: str
    display_name: Optional[str] = None
    platform_sources: Set[str] = field(default_factory=set)
    last_seen: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncOperation:
    """同步操作记录"""
    operation_id: str
    source_session: str
    target_sessions: List[str]
    operation_type: str  # create, update, delete, merge
    timestamp: datetime = field(default_factory=datetime.now)
    status: SyncStatus = SyncStatus.PENDING
    error_message: Optional[str] = None
    retry_count: int = 0


class SessionSynchronizer:
    """会话同步器"""
    
    def __init__(
        self, 
        session_store: SessionStore,
        sync_config: Optional[SessionSyncConfig] = None
    ):
        self.store = session_store
        self.config = sync_config or SessionSyncConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 身份映射
        self.identity_map: Dict[str, SessionIdentity] = {}
        self.session_to_identity: Dict[str, str] = {}
        
        # 同步记录
        self.sync_operations: Dict[str, SyncOperation] = {}
        self.sync_history: List[SyncOperation] = []
        
        # 同步任务
        self._sync_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self) -> None:
        """启动同步器"""
        self._running = True
        
        # 加载身份映射
        await self._load_identity_mappings()
        
        # 启动定期同步任务
        if self.config.strategy in [SyncStrategy.AUTO, SyncStrategy.DELAYED]:
            self._sync_task = asyncio.create_task(self._periodic_sync())
            
        self.logger.info("Session synchronizer started", 
                        strategy=self.config.strategy.value,
                        interval=self.config.sync_interval)
    
    async def stop(self) -> None:
        """停止同步器"""
        self._running = False
        
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        
        # 保存身份映射
        await self._save_identity_mappings()
        
        self.logger.info("Session synchronizer stopped")
    
    async def link_identities(
        self, 
        identity_key: str, 
        session_ids: List[str],
        display_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """链接会话身份"""
        try:
            # 获取或创建身份
            if identity_key not in self.identity_map:
                identity = SessionIdentity(
                    identity_key=identity_key,
                    display_name=display_name,
                    metadata=metadata or {}
                )
            else:
                identity = self.identity_map[identity_key]
                if display_name:
                    identity.display_name = display_name
                if metadata:
                    identity.metadata.update(metadata)
            
            # 关联会话
            for session_id in session_ids:
                self.session_to_identity[session_id] = identity_key
                identity.platform_sources.add(session_id)
            
            # 更新时间戳
            identity.last_seen = datetime.now()
            
            self.logger.info("Identities linked", 
                           identity_key=identity_key,
                           session_count=len(session_ids))
            return True
            
        except Exception as e:
            self.logger.error("Failed to link identities", 
                            identity_key=identity_key, 
                            error=str(e))
            return False
    
    async def unlink_identity(self, session_id: str) -> bool:
        """取消会话身份关联"""
        try:
            if session_id in self.session_to_identity:
                identity_key = self.session_to_identity.pop(session_id)
                
                # 从身份源中移除
                if identity_key in self.identity_map:
                    identity = self.identity_map[identity_key]
                    identity.platform_sources.discard(session_id)
                    
                    # 如果没有源了，删除身份
                    if not identity.platform_sources:
                        del self.identity_map[identity_key]
                
                self.logger.info("Identity unlinked", session_id=session_id)
                return True
            return False
            
        except Exception as e:
            self.logger.error("Failed to unlink identity", 
                            session_id=session_id, 
                            error=str(e))
            return False
    
    async def sync_sessions(
        self, 
        source_session_id: str,
        target_identity_key: Optional[str] = None
    ) -> List[str]:
        """同步会话到关联的会话"""
        try:
            # 获取源会话
            source_session = await self.store.get_session(source_session_id)
            if not source_session:
                self.logger.warning("Source session not found", session_id=source_session_id)
                return []
            
            # 获取目标身份键
            if not target_identity_key:
                target_identity_key = self.session_to_identity.get(source_session_id)
                if not target_identity_key:
                    self.logger.warning("No identity mapping found", session_id=source_session_id)
                    return []
            
            # 获取目标会话
            identity = self.identity_map.get(target_identity_key)
            if not identity:
                self.logger.warning("Identity not found", identity_key=target_identity_key)
                return []
            
            synced_session_ids = []
            
            for target_session_id in identity.platform_sources:
                if target_session_id == source_session_id:
                    continue  # 跳过源会话自身
                
                target_session = await self.store.get_session(target_session_id)
                if not target_session:
                    continue
                
                # 执行同步
                if await self._sync_session_data(source_session, target_session):
                    synced_session_ids.append(target_session_id)
            
            if synced_session_ids:
                self.logger.info("Sessions synced", 
                               source=source_session_id,
                               targets=synced_session_ids)
            
            return synced_session_ids
            
        except Exception as e:
            self.logger.error("Failed to sync sessions", 
                            source=source_session_id, 
                            error=str(e))
            return []
    
    async def create_sync_operation(
        self,
        source_session_id: str,
        operation_type: str,
        target_criteria: Optional[Dict[str, Any]] = None
    ) -> str:
        """创建同步操作"""
        operation_id = f"sync_{datetime.now().timestamp()}_{hash(source_session_id) % 10000}"
        
        # 获取关联的会话
        identity_key = self.session_to_identity.get(source_session_id)
        if identity_key:
            identity = self.identity_map.get(identity_key)
            target_sessions = [
                s for s in identity.platform_sources 
                if s != source_session_id
            ] if identity else []
        else:
            target_sessions = []
        
        operation = SyncOperation(
            operation_id=operation_id,
            source_session=source_session_id,
            target_sessions=target_sessions,
            operation_type=operation_type
        )
        
        self.sync_operations[operation_id] = operation
        self.sync_history.append(operation)
        
        # 限制历史记录数量
        if len(self.sync_history) > 1000:
            self.sync_history = self.sync_history[-500:]
        
        self.logger.info("Sync operation created", 
                       operation_id=operation_id,
                       source=source_session_id,
                       targets=len(target_sessions))
        
        return operation_id
    
    async def execute_sync_operation(self, operation_id: str) -> bool:
        """执行同步操作"""
        operation = self.sync_operations.get(operation_id)
        if not operation:
            self.logger.warning("Sync operation not found", operation_id=operation_id)
            return False
        
        try:
            operation.status = SyncStatus.SYNCING
            
            # 获取源会话
            source_session = await self.store.get_session(operation.source_session)
            if not source_session:
                operation.status = SyncStatus.FAILED
                operation.error_message = "Source session not found"
                return False
            
            success_count = 0
            
            # 执行同步到目标会话
            for target_session_id in operation.target_sessions:
                try:
                    target_session = await self.store.get_session(target_session_id)
                    if target_session:
                        if await self._apply_sync_operation(operation, source_session, target_session):
                            success_count += 1
                            
                except Exception as e:
                    self.logger.error("Failed to sync to target", 
                                    operation_id=operation_id,
                                    target=target_session_id,
                                    error=str(e))
            
            # 更新操作状态
            if success_count == len(operation.target_sessions):
                operation.status = SyncStatus.COMPLETED
                self.logger.info("Sync operation completed", 
                               operation_id=operation_id,
                               success_count=success_count)
                return True
            elif success_count > 0:
                operation.status = SyncStatus.COMPLETED
                self.logger.warning("Sync operation partially completed", 
                                  operation_id=operation_id,
                                  success_count=success_count,
                                  total=len(operation.target_sessions))
                return True
            else:
                operation.status = SyncStatus.FAILED
                operation.error_message = "No targets synced successfully"
                return False
                
        except Exception as e:
            operation.status = SyncStatus.FAILED
            operation.error_message = str(e)
            self.logger.error("Sync operation failed", 
                            operation_id=operation_id, 
                            error=str(e))
            return False
    
    async def resolve_session_conflicts(
        self,
        session_ids: List[str],
        resolution_strategy: Optional[str] = None
    ) -> Optional[str]:
        """解决会话冲突"""
        if len(session_ids) < 2:
            return session_ids[0] if session_ids else None
        
        strategy = resolution_strategy or self.config.conflict_resolution
        
        if strategy == "latest_wins":
            # 最新的会话获胜
            latest_session = None
            latest_time = datetime.min
            
            for session_id in session_ids:
                session = await self.store.get_session(session_id)
                if session and session.last_activity > latest_time:
                    latest_time = session.last_activity
                    latest_session = session_id
            
            return latest_session
            
        elif strategy == "source_priority":
            # 优先级源获胜
            priority_source = self.config.priority_source
            
            for session_id in session_ids:
                session = await self.store.get_session(session_id)
                if session and str(session.platform) == priority_source:
                    return session_id
            
            # 如果没有匹配的，返回第一个
            return session_ids[0]
        
        elif strategy == "manual":
            # 手动解决（返回第一个，标记需要人工干预）
            self.logger.warning("Manual conflict resolution required", 
                              sessions=session_ids)
            return session_ids[0]
        
        else:
            # 默认返回最新的
            return await self.resolve_session_conflicts(session_ids, "latest_wins")
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        active_operations = sum(
            1 for op in self.sync_operations.values() 
            if op.status == SyncStatus.SYNCING
        )
        
        pending_operations = sum(
            1 for op in self.sync_operations.values() 
            if op.status == SyncStatus.PENDING
        )
        
        failed_operations = sum(
            1 for op in self.sync_operations.values() 
            if op.status == SyncStatus.FAILED
        )
        
        return {
            "running": self._running,
            "strategy": self.config.strategy.value,
            "identity_count": len(self.identity_map),
            "session_mappings": len(self.session_to_identity),
            "active_operations": active_operations,
            "pending_operations": pending_operations,
            "failed_operations": failed_operations,
            "total_operations": len(self.sync_operations),
            "recent_syncs": len([
                op for op in self.sync_history 
                if op.timestamp > datetime.now() - timedelta(hours=24)
            ])
        }
    
    async def _periodic_sync(self) -> None:
        """定期同步任务"""
        while self._running:
            try:
                await asyncio.sleep(self.config.sync_interval)
                
                if not self._running:
                    break
                
                # 执行待处理的同步操作
                pending_ops = [
                    op_id for op_id, op in self.sync_operations.items()
                    if op.status == SyncStatus.PENDING
                ]
                
                for operation_id in pending_ops:
                    await self.execute_sync_operation(operation_id)
                
                # 清理过期的同步记录
                await self._cleanup_sync_history()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in periodic sync", error=str(e))
                await asyncio.sleep(self.config.sync_interval * 2)
    
    async def _sync_session_data(
        self, 
        source: SessionContext, 
        target: SessionContext
    ) -> bool:
        """同步会话数据"""
        try:
            # 合并对话历史
            source_messages = source.conversation_history
            target_messages = target.conversation_history
            
            # 查找需要同步的消息（去重）
            source_message_ids = {msg.get("id") for msg in source_messages}
            new_messages = [
                msg for msg in source_messages 
                if msg.get("id") not in source_message_ids.intersection(
                    {msg.get("id") for msg in target_messages}
                )
            ]
            
            # 添加新消息到目标会话
            for message in new_messages:
                target.add_message(message)
            
            # 同步会话数据
            for key, value in source.data.items():
                if key not in target.data or target.data[key] != value:
                    target.set_data(key, value)
            
            # 更新时间戳
            if source.last_activity > target.last_activity:
                target.last_activity = source.last_activity
            
            # 保存目标会话
            await self.store.update_session(target)
            
            return len(new_messages) > 0
            
        except Exception as e:
            self.logger.error("Failed to sync session data", 
                            source=source.session_id,
                            target=target.session_id,
                            error=str(e))
            return False
    
    async def _apply_sync_operation(
        self,
        operation: SyncOperation,
        source: SessionContext,
        target: SessionContext
    ) -> bool:
        """应用同步操作"""
        try:
            if operation.operation_type == "merge":
                return await self._sync_session_data(source, target)
            elif operation.operation_type == "create":
                # 创建新的目标会话（基于源会话）
                pass
            elif operation.operation_type == "update":
                return await self._sync_session_data(source, target)
            elif operation.operation_type == "delete":
                # 删除目标会话
                await self.store.delete_session(target.session_id)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error("Failed to apply sync operation", 
                            operation_id=operation.operation_id,
                            error=str(e))
            return False
    
    async def _load_identity_mappings(self) -> None:
        """加载身份映射"""
        try:
            # 从存储中加载身份映射
            # 这里应该实现从数据库或文件系统加载
            pass
        except Exception as e:
            self.logger.error("Failed to load identity mappings", error=str(e))
    
    async def _save_identity_mappings(self) -> None:
        """保存身份映射"""
        try:
            # 保存身份映射到存储
            # 这里应该实现保存到数据库或文件系统
            pass
        except Exception as e:
            self.logger.error("Failed to save identity mappings", error=str(e))
    
    async def _cleanup_sync_history(self) -> None:
        """清理同步历史"""
        try:
            # 清理超过7天的同步记录
            cutoff_time = datetime.now() - timedelta(days=7)
            
            old_operations = [
                op_id for op_id, op in self.sync_operations.items()
                if op.timestamp < cutoff_time
            ]
            
            for op_id in old_operations:
                del self.sync_operations[op_id]
            
            if old_operations:
                self.logger.debug("Cleaned up sync history", count=len(old_operations))
                
        except Exception as e:
            self.logger.error("Failed to cleanup sync history", error=str(e))


# 便捷函数
async def create_session_sync(
    session_store: SessionStore,
    sync_config: Optional[SessionSyncConfig] = None
) -> SessionSynchronizer:
    """创建会话同步器"""
    synchronizer = SessionSynchronizer(session_store, sync_config)
    await synchronizer.start()
    return synchronizer


# 身份映射工具
class IdentityMapper:
    """身份映射器"""
    
    @staticmethod
    def generate_identity_key(
        platform: Union[str, Platform],
        user_id: str,
        account_id: Optional[str] = None
    ) -> str:
        """生成身份键"""
        platform_str = platform.value if hasattr(platform, 'value') else str(platform)
        
        if account_id:
            return f"{platform_str}:{account_id}:{user_id}"
        else:
            return f"{platform_str}:{user_id}"
    
    @staticmethod
    def parse_identity_key(identity_key: str) -> Dict[str, str]:
        """解析身份键"""
        parts = identity_key.split(":")
        
        if len(parts) == 2:
            return {"platform": parts[0], "user_id": parts[1]}
        elif len(parts) == 3:
            return {
                "platform": parts[0], 
                "account_id": parts[1], 
                "user_id": parts[2]
            }
        else:
            return {"platform": "unknown", "user_id": identity_key}