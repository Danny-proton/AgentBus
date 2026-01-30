"""
会话持久化和恢复模块
Session Persistence and Recovery Module

负责会话数据的持久化存储、自动恢复、备份和迁移功能
支持多种存储格式和压缩算法
"""

from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum, auto
import asyncio
import json
import gzip
import pickle
import hashlib
import logging
from pathlib import Path
import shutil
from contextlib import asynccontextmanager

from .context_manager import SessionContext, SessionStatus
from .session_storage import SessionStore

logger = logging.getLogger(__name__)


class BackupFormat(Enum):
    """备份格式枚举"""
    JSON = "json"              # JSON格式
    JSON_GZ = "json.gz"       # 压缩JSON格式
    PICKLE = "pickle"          # Python pickle格式
    PICKLE_GZ = "pickle.gz"   # 压缩pickle格式


class CompressionLevel(Enum):
    """压缩级别枚举"""
    NONE = 0       # 无压缩
    FAST = 1       # 快速压缩
    NORMAL = 6     # 标准压缩
    MAXIMUM = 9    # 最大压缩


class RecoveryStrategy(Enum):
    """恢复策略枚举"""
    MERGE = "merge"           # 合并策略
    REPLACE = "replace"       # 替换策略
    SKIP_EXISTING = "skip"    # 跳过现有
    INTERACTIVE = "interactive" # 交互式


@dataclass
class BackupMetadata:
    """备份元数据"""
    backup_id: str
    timestamp: datetime
    format: BackupFormat
    compression_level: CompressionLevel
    session_count: int
    total_size: int
    checksum: str
    description: Optional[str] = None
    tags: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class RecoveryOptions:
    """恢复选项"""
    strategy: RecoveryStrategy = RecoveryStrategy.MERGE
    backup_id: Optional[str] = None
    session_filter: Optional[Callable[[SessionContext], bool]] = None
    preserve_metadata: bool = True
    overwrite_existing: bool = False
    create_backup_before_recovery: bool = True
    interactive: bool = False


class SessionPersistence:
    """会话持久化管理器"""
    
    def __init__(
        self,
        session_store: SessionStore,
        backup_dir: Optional[Path] = None,
        max_backups: int = 10,
        auto_backup_interval: int = 3600  # 1小时
    ):
        self.session_store = session_store
        self.backup_dir = backup_dir or Path("backups")
        self.max_backups = max_backups
        self.auto_backup_interval = auto_backup_interval
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 创建备份目录
        self.backup_dir.mkdir(exist_ok=True)
        
        # 备份任务
        self._backup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # 备份记录
        self.backup_metadata: Dict[str, BackupMetadata] = {}
    
    async def start(self) -> None:
        """启动持久化管理器"""
        self._running = True
        
        # 加载备份元数据
        await self._load_backup_metadata()
        
        # 启动自动备份任务
        self._backup_task = asyncio.create_task(self._auto_backup_loop())
        
        self.logger.info("Session persistence started", 
                        backup_dir=str(self.backup_dir),
                        interval=self.auto_backup_interval)
    
    async def stop(self) -> None:
        """停止持久化管理器"""
        self._running = False
        
        if self._backup_task:
            self._backup_task.cancel()
            try:
                await self._backup_task
            except asyncio.CancelledError:
                pass
        
        # 保存备份元数据
        await self._save_backup_metadata()
        
        self.logger.info("Session persistence stopped")
    
    async def create_backup(
        self,
        backup_format: BackupFormat = BackupFormat.JSON_GZ,
        compression_level: CompressionLevel = CompressionLevel.NORMAL,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        session_filter: Optional[Callable[[SessionContext], bool]] = None
    ) -> str:
        """创建备份"""
        try:
            backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(datetime.now()) % 10000}"
            
            # 获取所有会话
            all_sessions = await self._get_all_sessions(session_filter)
            
            if not all_sessions:
                self.logger.warning("No sessions to backup")
                return ""
            
            # 准备备份数据
            backup_data = {
                "backup_info": {
                    "backup_id": backup_id,
                    "timestamp": datetime.now().isoformat(),
                    "format": backup_format.value,
                    "session_count": len(all_sessions)
                },
                "sessions": []
            }
            
            # 序列化会话数据
            for session in all_sessions:
                session_data = await self._serialize_session(session)
                backup_data["sessions"].append(session_data)
            
            # 写入备份文件
            backup_path = await self._write_backup_file(
                backup_id, backup_data, backup_format, compression_level
            )
            
            # 计算校验和
            checksum = await self._calculate_checksum(backup_path)
            
            # 创建元数据
            metadata = BackupMetadata(
                backup_id=backup_id,
                timestamp=datetime.now(),
                format=backup_format,
                compression_level=compression_level,
                session_count=len(all_sessions),
                total_size=backup_path.stat().st_size,
                checksum=checksum,
                description=description,
                tags=tags or []
            )
            
            self.backup_metadata[backup_id] = metadata
            
            # 清理旧备份
            await self._cleanup_old_backups()
            
            self.logger.info("Backup created successfully", 
                           backup_id=backup_id,
                           sessions=len(all_sessions),
                           size=metadata.total_size)
            
            return backup_id
            
        except Exception as e:
            self.logger.error("Failed to create backup", error=str(e))
            raise
    
    async def restore_backup(
        self,
        backup_id: Optional[str] = None,
        options: Optional[RecoveryOptions] = None
    ) -> Dict[str, Any]:
        """恢复备份"""
        try:
            if not options:
                options = RecoveryOptions()
            
            if not backup_id and not options.backup_id:
                # 使用最新的备份
                backup_id = await self._get_latest_backup_id()
            else:
                backup_id = backup_id or options.backup_id
            
            if not backup_id or backup_id not in self.backup_metadata:
                raise ValueError(f"Backup not found: {backup_id}")
            
            metadata = self.backup_metadata[backup_id]
            
            # 创建恢复前备份
            if options.create_backup_before_recovery:
                await self.create_backup(
                    description=f"Auto backup before recovery of {backup_id}",
                    tags=["pre_recovery", "auto"]
                )
            
            # 读取备份数据
            backup_data = await self._read_backup_file(backup_id, metadata.format)
            
            # 验证校验和
            if not await self._verify_checksum(backup_id, metadata):
                self.logger.warning("Backup checksum verification failed", backup_id=backup_id)
            
            # 恢复会话
            recovery_result = await self._restore_sessions(
                backup_data["sessions"], 
                options
            )
            
            self.logger.info("Backup restored successfully", 
                           backup_id=backup_id,
                           restored=recovery_result["restored_count"],
                           skipped=recovery_result["skipped_count"],
                           errors=recovery_result["error_count"])
            
            return {
                "backup_id": backup_id,
                "restored_count": recovery_result["restored_count"],
                "skipped_count": recovery_result["skipped_count"],
                "error_count": recovery_result["error_count"],
                "errors": recovery_result["errors"]
            }
            
        except Exception as e:
            self.logger.error("Failed to restore backup", 
                            backup_id=backup_id, 
                            error=str(e))
            raise
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backup_list = []
        
        for metadata in self.backup_metadata.values():
            backup_info = metadata.to_dict()
            backup_info["path"] = str(self._get_backup_path(metadata.backup_id, metadata.format))
            backup_list.append(backup_info)
        
        # 按时间戳排序
        backup_list.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return backup_list
    
    async def delete_backup(self, backup_id: str) -> bool:
        """删除备份"""
        try:
            if backup_id not in self.backup_metadata:
                self.logger.warning("Backup not found", backup_id=backup_id)
                return False
            
            metadata = self.backup_metadata[backup_id]
            
            # 删除备份文件
            backup_path = self._get_backup_path(backup_id, metadata.format)
            if backup_path.exists():
                backup_path.unlink()
            
            # 删除元数据
            del self.backup_metadata[backup_id]
            
            self.logger.info("Backup deleted", backup_id=backup_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to delete backup", 
                            backup_id=backup_id, 
                            error=str(e))
            return False
    
    async def export_session(
        self,
        session_id: str,
        export_format: BackupFormat = BackupFormat.JSON,
        include_metadata: bool = True,
        compression_level: CompressionLevel = CompressionLevel.NONE
    ) -> Path:
        """导出单个会话"""
        try:
            session = await self.session_store.get_session(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")
            
            # 准备导出数据
            export_data = await self._serialize_session(session, include_metadata)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"session_{session_id}_{timestamp}.{export_format.value}"
            export_path = self.backup_dir / filename
            
            # 写入文件
            await self._write_data_to_file(export_data, export_path, export_format, compression_level)
            
            self.logger.info("Session exported", 
                           session_id=session_id,
                           path=str(export_path))
            
            return export_path
            
        except Exception as e:
            self.logger.error("Failed to export session", 
                            session_id=session_id, 
                            error=str(e))
            raise
    
    async def import_session(
        self,
        file_path: Path,
        import_format: Optional[BackupFormat] = None,
        options: Optional[RecoveryOptions] = None
    ) -> str:
        """导入单个会话"""
        try:
            if not options:
                options = RecoveryOptions(strategy=RecoveryStrategy.REPLACE)
            
            # 检测格式
            if not import_format:
                import_format = self._detect_format(file_path)
            
            # 读取数据
            session_data = await self._read_backup_file_from_path(file_path, import_format)
            
            # 反序列化会话
            session = await self._deserialize_session(session_data)
            
            # 应用恢复策略
            if options.strategy == RecoveryStrategy.REPLACE or options.overwrite_existing:
                # 直接保存
                await self.session_store.create_session(session)
            elif options.strategy == RecoveryStrategy.SKIP_EXISTING:
                # 检查是否已存在
                existing = await self.session_store.get_session(session.session_id)
                if existing:
                    self.logger.info("Session import skipped (already exists)", 
                                   session_id=session.session_id)
                    return session.session_id
                await self.session_store.create_session(session)
            elif options.strategy == RecoveryStrategy.MERGE:
                # 合并策略
                existing = await self.session_store.get_session(session.session_id)
                if existing:
                    merged_session = await self._merge_sessions(existing, session)
                    await self.session_store.update_session(merged_session)
                else:
                    await self.session_store.create_session(session)
            
            self.logger.info("Session imported", session_id=session.session_id)
            return session.session_id
            
        except Exception as e:
            self.logger.error("Failed to import session", 
                            path=str(file_path), 
                            error=str(e))
            raise
    
    async def migrate_session_format(
        self,
        session_id: str,
        target_format: BackupFormat,
        compression_level: CompressionLevel = CompressionLevel.NORMAL
    ) -> Path:
        """迁移会话格式"""
        try:
            # 导出为当前格式
            export_path = await self.export_session(session_id, target_format, compression_level=compression_level)
            
            self.logger.info("Session format migrated", 
                           session_id=session_id,
                           format=target_format.value)
            
            return export_path
            
        except Exception as e:
            self.logger.error("Failed to migrate session format", 
                            session_id=session_id, 
                            error=str(e))
            raise
    
    async def verify_backup_integrity(self, backup_id: str) -> Dict[str, Any]:
        """验证备份完整性"""
        try:
            if backup_id not in self.backup_metadata:
                return {"valid": False, "error": "Backup not found"}
            
            metadata = self.backup_metadata[backup_id]
            backup_path = self._get_backup_path(backup_id, metadata.format)
            
            if not backup_path.exists():
                return {"valid": False, "error": "Backup file not found"}
            
            # 检查文件大小
            actual_size = backup_path.stat().st_size
            if actual_size != metadata.total_size:
                return {"valid": False, "error": "File size mismatch"}
            
            # 验证校验和
            checksum_valid = await self._verify_checksum(backup_id, metadata)
            
            # 尝试读取和解析
            try:
                backup_data = await self._read_backup_file(backup_id, metadata.format)
                session_count = len(backup_data.get("sessions", []))
                format_valid = session_count == metadata.session_count
            except Exception:
                format_valid = False
            
            return {
                "valid": checksum_valid and format_valid,
                "checksum_valid": checksum_valid,
                "format_valid": format_valid,
                "expected_size": metadata.total_size,
                "actual_size": actual_size,
                "expected_sessions": metadata.session_count,
                "actual_sessions": session_count if 'session_count' in locals() else 0
            }
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def _auto_backup_loop(self) -> None:
        """自动备份循环"""
        while self._running:
            try:
                await asyncio.sleep(self.auto_backup_interval)
                
                if not self._running:
                    break
                
                # 创建自动备份
                await self.create_backup(
                    description="Auto backup",
                    tags=["auto", "scheduled"]
                )
                
                self.logger.debug("Auto backup completed")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in auto backup loop", error=str(e))
                await asyncio.sleep(self.auto_backup_interval * 2)
    
    async def _get_all_sessions(
        self,
        session_filter: Optional[Callable[[SessionContext], bool]] = None
    ) -> List[SessionContext]:
        """获取所有会话"""
        # 这里应该实现获取所有会话的逻辑
        # 由于SessionStore接口限制，我们暂时返回空列表
        # 实际实现时需要扩展SessionStore接口
        sessions = []
        
        # 模拟获取会话的逻辑
        # sessions = await self.session_store.get_all_sessions()
        
        if session_filter:
            sessions = [s for s in sessions if session_filter(s)]
        
        return sessions
    
    async def _serialize_session(
        self,
        session: SessionContext,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """序列化会话"""
        data = session.to_dict()
        
        if not include_metadata:
            # 移除一些元数据
            data.pop("metadata", None)
            data.pop("conversation_history", None)
        
        return data
    
    async def _deserialize_session(self, data: Dict[str, Any]) -> SessionContext:
        """反序列化会话"""
        return SessionContext.from_dict(data)
    
    async def _write_backup_file(
        self,
        backup_id: str,
        data: Dict[str, Any],
        format: BackupFormat,
        compression_level: CompressionLevel
    ) -> Path:
        """写入备份文件"""
        backup_path = self._get_backup_path(backup_id, format)
        await self._write_data_to_file(data, backup_path, format, compression_level)
        return backup_path
    
    async def _write_data_to_file(
        self,
        data: Any,
        file_path: Path,
        format: BackupFormat,
        compression_level: CompressionLevel
    ) -> None:
        """写入数据到文件"""
        if format == BackupFormat.JSON:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        elif format == BackupFormat.JSON_GZ:
            with gzip.open(file_path, 'wt', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        elif format == BackupFormat.PICKLE:
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)
        
        elif format == BackupFormat.PICKLE_GZ:
            with gzip.open(file_path, 'wb') as f:
                pickle.dump(data, f)
    
    async def _read_backup_file(
        self,
        backup_id: str,
        format: BackupFormat
    ) -> Dict[str, Any]:
        """读取备份文件"""
        backup_path = self._get_backup_path(backup_id, format)
        return await self._read_backup_file_from_path(backup_path, format)
    
    async def _read_backup_file_from_path(
        self,
        file_path: Path,
        format: BackupFormat
    ) -> Dict[str, Any]:
        """从文件路径读取备份数据"""
        if format == BackupFormat.JSON:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        elif format == BackupFormat.JSON_GZ:
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                return json.load(f)
        
        elif format == BackupFormat.PICKLE:
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        
        elif format == BackupFormat.PICKLE_GZ:
            with gzip.open(file_path, 'rb') as f:
                return pickle.load(f)
    
    def _get_backup_path(self, backup_id: str, format: BackupFormat) -> Path:
        """获取备份文件路径"""
        filename = f"{backup_id}.{format.value}"
        return self.backup_dir / filename
    
    def _detect_format(self, file_path: Path) -> BackupFormat:
        """检测文件格式"""
        suffix = file_path.suffix.lower()
        
        if suffix == ".json":
            return BackupFormat.JSON
        elif suffix == ".gz":
            # 检查是否是压缩文件
            if file_path.stem.endswith(".json"):
                return BackupFormat.JSON_GZ
            else:
                return BackupFormat.PICKLE_GZ
        elif suffix == ".pickle":
            return BackupFormat.PICKLE
        else:
            # 默认返回JSON
            return BackupFormat.JSON
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    async def _verify_checksum(self, backup_id: str, metadata: BackupMetadata) -> bool:
        """验证校验和"""
        try:
            backup_path = self._get_backup_path(backup_id, metadata.format)
            if not backup_path.exists():
                return False
            
            actual_checksum = await self._calculate_checksum(backup_path)
            return actual_checksum == metadata.checksum
            
        except Exception:
            return False
    
    async def _restore_sessions(
        self,
        sessions_data: List[Dict[str, Any]],
        options: RecoveryOptions
    ) -> Dict[str, Any]:
        """恢复会话数据"""
        restored_count = 0
        skipped_count = 0
        error_count = 0
        errors = []
        
        for session_data in sessions_data:
            try:
                # 应用会话过滤器
                if options.session_filter:
                    session = await self._deserialize_session(session_data)
                    if not options.session_filter(session):
                        skipped_count += 1
                        continue
                
                session = await self._deserialize_session(session_data)
                
                # 检查是否已存在
                existing = await self.session_store.get_session(session.session_id)
                
                if existing and options.strategy == RecoveryStrategy.SKIP_EXISTING:
                    skipped_count += 1
                    continue
                
                if existing and options.strategy == RecoveryStrategy.MERGE:
                    # 合并会话
                    merged_session = await self._merge_sessions(existing, session)
                    await self.session_store.update_session(merged_session)
                    restored_count += 1
                
                elif existing and not options.overwrite_existing:
                    # 跳过已存在的会话
                    skipped_count += 1
                    continue
                
                else:
                    # 创建或替换会话
                    await self.session_store.create_session(session)
                    restored_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(str(e))
                self.logger.error("Failed to restore session", 
                                session_id=session_data.get("session_id", "unknown"), 
                                error=str(e))
        
        return {
            "restored_count": restored_count,
            "skipped_count": skipped_count,
            "error_count": error_count,
            "errors": errors
        }
    
    async def _merge_sessions(self, existing: SessionContext, new: SessionContext) -> SessionContext:
        """合并两个会话"""
        # 合并对话历史
        existing_message_ids = {msg.get("id") for msg in existing.conversation_history}
        new_messages = [
            msg for msg in new.conversation_history 
            if msg.get("id") not in existing_message_ids
        ]
        
        for message in new_messages:
            existing.add_message(message)
        
        # 合并数据
        existing.data.update(new.data)
        
        # 合并元数据
        if existing.metadata.get("preserve_metadata") and new.metadata:
            # 如果设置了保留元数据，合并但不覆盖
            for key, value in new.metadata.items():
                if key not in existing.metadata:
                    existing.metadata[key] = value
        
        # 更新活动时间
        if new.last_activity > existing.last_activity:
            existing.last_activity = new.last_activity
        
        return existing
    
    async def _cleanup_old_backups(self) -> None:
        """清理旧备份"""
        if len(self.backup_metadata) <= self.max_backups:
            return
        
        # 按时间戳排序，删除最旧的
        sorted_backups = sorted(
            self.backup_metadata.items(),
            key=lambda x: x[1].timestamp
        )
        
        backups_to_delete = sorted_backups[:len(self.backup_metadata) - self.max_backups]
        
        for backup_id, metadata in backups_to_delete:
            await self.delete_backup(backup_id)
    
    async def _get_latest_backup_id(self) -> Optional[str]:
        """获取最新备份ID"""
        if not self.backup_metadata:
            return None
        
        latest_backup = max(
            self.backup_metadata.items(),
            key=lambda x: x[1].timestamp
        )
        
        return latest_backup[0]
    
    async def _load_backup_metadata(self) -> None:
        """加载备份元数据"""
        try:
            # 从备份目录加载元数据文件
            metadata_file = self.backup_dir / "backup_metadata.json"
            
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_dict = json.load(f)
                
                for backup_id, data in metadata_dict.items():
                    data["timestamp"] = datetime.fromisoformat(data["timestamp"])
                    self.backup_metadata[backup_id] = BackupMetadata(**data)
                
                self.logger.info("Backup metadata loaded", count=len(self.backup_metadata))
            
        except Exception as e:
            self.logger.error("Failed to load backup metadata", error=str(e))
    
    async def _save_backup_metadata(self) -> None:
        """保存备份元数据"""
        try:
            metadata_file = self.backup_dir / "backup_metadata.json"
            
            metadata_dict = {
                backup_id: metadata.to_dict()
                for backup_id, metadata in self.backup_metadata.items()
            }
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.debug("Backup metadata saved")
            
        except Exception as e:
            self.logger.error("Failed to save backup metadata", error=str(e))


# 便捷函数
async def create_session_persistence(
    session_store: SessionStore,
    backup_dir: Optional[Path] = None,
    **config
) -> SessionPersistence:
    """创建会话持久化管理器"""
    persistence = SessionPersistence(session_store, backup_dir, **config)
    await persistence.start()
    return persistence


@asynccontextmanager
async def session_backup_context(
    session_persistence: SessionPersistence,
    backup_name: str,
    **backup_kwargs
):
    """会话备份上下文管理器"""
    backup_id = None
    try:
        # 创建备份
        backup_id = await session_persistence.create_backup(
            description=f"Backup for {backup_name}",
            **backup_kwargs
        )
        
        yield backup_id
        
    except Exception as e:
        if backup_id:
            # 如果操作失败，删除备份
            await session_persistence.delete_backup(backup_id)
        raise
    finally:
        # 清理任务可以在这里添加
        pass