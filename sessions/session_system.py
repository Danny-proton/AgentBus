"""
完整会话管理系统
Complete Session Management System

整合会话管理、会话同步、持久化、状态跟踪和过期处理的完整系统
提供统一的接口和配置管理
"""

from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
import asyncio
import logging
from pathlib import Path
import json

from .context_manager import SessionContext, SessionType, SessionStatus, Message, Platform
from .session_storage import SessionStore, create_session_store, StorageType
from .session_manager import SessionManager
from .session_sync import SessionSynchronizer, SessionSyncConfig, SyncStrategy
from .session_persistence import SessionPersistence, BackupFormat, CompressionLevel
from .session_state_tracker import SessionStateTracker, EventType
from .session_expiry import SessionExpiryManager, ExpiryRule, ExpiryStrategy, CleanupAction

logger = logging.getLogger(__name__)


class SystemStatus(Enum):
    """系统状态枚举"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class SessionSystemConfig:
    """会话系统配置"""
    # 基础配置
    storage_type: StorageType = StorageType.MEMORY
    storage_config: Dict[str, Any] = field(default_factory=dict)
    
    # 清理配置
    enable_cleanup: bool = True
    cleanup_interval: int = 300  # 5分钟
    
    # 同步配置
    enable_sync: bool = False
    sync_config: Optional[SessionSyncConfig] = None
    
    # 持久化配置
    enable_persistence: bool = False
    backup_dir: Optional[Path] = None
    max_backups: int = 10
    auto_backup_interval: int = 3600  # 1小时
    
    # 状态跟踪配置
    enable_tracking: bool = False
    history_retention_days: int = 30
    max_events_per_session: int = 1000
    enable_prediction: bool = False
    
    # 过期管理配置
    enable_expiry: bool = True
    archive_dir: Optional[Path] = None
    auto_cleanup_interval: int = 1800  # 30分钟
    
    # 通知配置
    notification_callbacks: List[Callable] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemMetrics:
    """系统指标"""
    status: SystemStatus = SystemStatus.STOPPED
    uptime_seconds: float = 0.0
    total_sessions: int = 0
    active_sessions: int = 0
    expired_sessions: int = 0
    sync_operations: int = 0
    backup_count: int = 0
    state_transitions: int = 0
    cleanup_operations: int = 0
    last_activity: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.last_activity:
            data["last_activity"] = self.last_activity.isoformat()
        return data


class SessionSystem:
    """完整会话管理系统"""
    
    def __init__(self, config: Optional[SessionSystemConfig] = None):
        self.config = config or SessionSystemConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 系统状态
        self.status = SystemStatus.STOPPED
        self.start_time: Optional[datetime] = None
        self.metrics = SystemMetrics()
        
        # 核心组件
        self.session_store: Optional[SessionStore] = None
        self.session_manager: Optional[SessionManager] = None
        self.session_synchronizer: Optional[SessionSynchronizer] = None
        self.session_persistence: Optional[SessionPersistence] = None
        self.session_tracker: Optional[SessionStateTracker] = None
        self.session_expiry: Optional[SessionExpiryManager] = None
        
        # 组件状态
        self._components_started: Dict[str, bool] = {}
        
        # 事件处理
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # 健康检查
        self._health_check_interval = 60  # 1分钟
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """启动会话管理系统"""
        if self.status != SystemStatus.STOPPED:
            raise RuntimeError(f"System is already running with status: {self.status}")
        
        try:
            self.status = SystemStatus.STARTING
            self.start_time = datetime.now()
            
            self.logger.info("Starting session management system...")
            
            # 1. 创建存储
            await self._setup_storage()
            
            # 2. 启动核心会话管理器
            await self._setup_session_manager()
            
            # 3. 设置组件
            await self._setup_components()
            
            # 4. 启动健康检查
            await self._start_health_check()
            
            # 5. 启动系统
            self.status = SystemStatus.RUNNING
            
            self.logger.info("Session management system started successfully")
            
        except Exception as e:
            self.status = SystemStatus.ERROR
            self.logger.error("Failed to start session management system", error=str(e))
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """停止会话管理系统"""
        if self.status == SystemStatus.STOPPED:
            return
        
        try:
            self.status = SystemStatus.STOPPING
            
            self.logger.info("Stopping session management system...")
            
            # 停止健康检查
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass
            
            # 停止组件
            components = [
                ("session_expiry", self.session_expiry),
                ("session_tracker", self.session_tracker),
                ("session_persistence", self.session_persistence),
                ("session_synchronizer", self.session_synchronizer),
                ("session_manager", self.session_manager),
                ("session_store", self.session_store),
            ]
            
            for name, component in components:
                if component and self._components_started.get(name, False):
                    try:
                        if hasattr(component, 'stop'):
                            await component.stop()
                        self._components_started[name] = False
                        self.logger.debug(f"Stopped component: {name}")
                    except Exception as e:
                        self.logger.error(f"Error stopping component {name}", error=str(e))
            
            self.status = SystemStatus.STOPPED
            
            self.logger.info("Session management system stopped")
            
        except Exception as e:
            self.logger.error("Error during system shutdown", error=str(e))
            self.status = SystemStatus.ERROR
    
    async def restart(self) -> None:
        """重启系统"""
        await self.stop()
        await asyncio.sleep(1)  # 短暂延迟
        await self.start()
    
    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """获取会话"""
        if self.session_manager:
            return await self.session_manager.get_session(session_id)
        return None
    
    async def create_session(self, **kwargs) -> SessionContext:
        """创建会话"""
        if not self.session_manager:
            raise RuntimeError("Session manager not initialized")
        
        session = await self.session_manager.create_session(**kwargs)
        
        # 记录事件
        if self.session_tracker:
            await self.session_tracker.track_event(
                session.session_id,
                EventType.MESSAGE_RECEIVED,
                {"action": "session_created"}
            )
        
        return session
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if not self.session_manager:
            return False
        
        success = await self.session_manager.delete_session(session_id)
        
        # 记录事件
        if success and self.session_tracker:
            await self.session_tracker.track_event(
                session_id,
                EventType.STATE_CHANGE,
                {"action": "session_deleted"}
            )
        
        return success
    
    async def sync_sessions(self, source_session_id: str) -> List[str]:
        """同步会话"""
        if not self.session_synchronizer:
            return []
        
        synced_ids = await self.session_synchronizer.sync_sessions(source_session_id)
        
        # 更新统计
        self.metrics.sync_operations += 1
        
        return synced_ids
    
    async def create_backup(self, **kwargs) -> Optional[str]:
        """创建备份"""
        if not self.session_persistence:
            return None
        
        backup_id = await self.session_persistence.create_backup(**kwargs)
        
        # 更新统计
        self.metrics.backup_count += 1
        
        return backup_id
    
    async def restore_backup(self, backup_id: str, **kwargs) -> Dict[str, Any]:
        """恢复备份"""
        if not self.session_persistence:
            raise RuntimeError("Persistence not enabled")
        
        return await self.session_persistence.restore_backup(backup_id, **kwargs)
    
    async def track_event(
        self,
        session_id: str,
        event_type: Union[EventType, str],
        **event_data
    ) -> bool:
        """跟踪事件"""
        if not self.session_tracker:
            return False
        
        # 转换为EventType枚举
        if isinstance(event_type, str):
            try:
                event_type = EventType(event_type)
            except ValueError:
                self.logger.warning("Unknown event type", event_type=event_type)
                return False
        
        success = await self.session_tracker.track_event(session_id, event_type, event_data)
        
        # 更新统计
        if success:
            self.metrics.state_transitions += 1
        
        return success
    
    async def cleanup_expired_sessions(self, dry_run: bool = False) -> List[Dict[str, Any]]:
        """清理过期会话"""
        if not self.session_expiry:
            return []
        
        results = await self.session_expiry.cleanup_expired_sessions(dry_run)
        
        # 更新统计
        self.metrics.cleanup_operations += 1
        
        return [result.to_dict() for result in results]
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        # 更新运行时指标
        if self.start_time:
            self.metrics.uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        # 收集各组件状态
        component_status = {}
        
        for name, component in [
            ("session_manager", self.session_manager),
            ("session_synchronizer", self.session_synchronizer),
            ("session_persistence", self.session_persistence),
            ("session_tracker", self.session_tracker),
            ("session_expiry", self.session_expiry),
        ]:
            if component:
                try:
                    if hasattr(component, 'get_sync_status'):
                        component_status[name] = await component.get_sync_status()
                    elif hasattr(component, 'get_system_status'):
                        component_status[name] = await component.get_system_status()
                    else:
                        component_status[name] = {"status": "active"}
                except Exception as e:
                    component_status[name] = {"status": "error", "error": str(e)}
        
        return {
            "system": {
                "status": self.status.value,
                "uptime_seconds": self.metrics.uptime_seconds,
                "config": self.config.to_dict()
            },
            "metrics": self.metrics.to_dict(),
            "components": component_status,
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        try:
            # 检查各组件健康状态
            checks = health_status["checks"]
            
            # 检查存储
            if self.session_store:
                checks["storage"] = {"status": "healthy"}
            else:
                checks["storage"] = {"status": "unhealthy", "error": "Storage not initialized"}
            
            # 检查会话管理器
            if self.session_manager:
                checks["session_manager"] = {"status": "healthy"}
            else:
                checks["session_manager"] = {"status": "unhealthy", "error": "Manager not initialized"}
            
            # 检查同步器
            if self.session_synchronizer:
                try:
                    sync_status = await self.session_synchronizer.get_sync_status()
                    checks["synchronizer"] = {"status": "healthy", "details": sync_status}
                except Exception as e:
                    checks["synchronizer"] = {"status": "unhealthy", "error": str(e)}
            
            # 检查持久化
            if self.session_persistence:
                try:
                    backup_list = await self.session_persistence.list_backups()
                    checks["persistence"] = {"status": "healthy", "backup_count": len(backup_list)}
                except Exception as e:
                    checks["persistence"] = {"status": "unhealthy", "error": str(e)}
            
            # 检查状态跟踪器
            if self.session_tracker:
                try:
                    stats = await self.session_tracker.get_state_statistics()
                    checks["tracker"] = {"status": "healthy", "statistics": stats}
                except Exception as e:
                    checks["tracker"] = {"status": "unhealthy", "error": str(e)}
            
            # 检查过期管理器
            if self.session_expiry:
                try:
                    expiry_stats = await self.session_expiry.get_expiry_statistics()
                    checks["expiry"] = {"status": "healthy", "statistics": expiry_stats}
                except Exception as e:
                    checks["expiry"] = {"status": "unhealthy", "error": str(e)}
            
            # 确定整体健康状态
            unhealthy_checks = [name for name, check in checks.items() 
                              if check.get("status") != "healthy"]
            
            if unhealthy_checks:
                health_status["status"] = "unhealthy"
                health_status["unhealthy_components"] = unhealthy_checks
            
        except Exception as e:
            health_status["status"] = "error"
            health_status["error"] = str(e)
        
        return health_status
    
    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """添加事件处理器"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    async def _setup_storage(self) -> None:
        """设置存储"""
        self.session_store = create_session_store(self.config.storage_type, self.config.storage_config)
        self.logger.info("Storage initialized", type=self.config.storage_type.value)
    
    async def _setup_session_manager(self) -> None:
        """设置会话管理器"""
        if not self.session_store:
            raise RuntimeError("Storage not initialized")
        
        self.session_manager = SessionManager(
            session_store=self.session_store,
            enable_cleanup=self.config.enable_cleanup,
            cleanup_interval=self.config.cleanup_interval
        )
        
        await self.session_manager.start()
        self._components_started["session_manager"] = True
        
        self.logger.info("Session manager initialized")
    
    async def _setup_components(self) -> None:
        """设置组件"""
        if not self.session_store:
            raise RuntimeError("Storage not initialized")
        
        # 设置同步器
        if self.config.enable_sync:
            await self._setup_synchronizer()
        
        # 设置持久化
        if self.config.enable_persistence:
            await self._setup_persistence()
        
        # 设置状态跟踪
        if self.config.enable_tracking:
            await self._setup_tracker()
        
        # 设置过期管理
        if self.config.enable_expiry:
            await self._setup_expiry()
    
    async def _setup_synchronizer(self) -> None:
        """设置同步器"""
        if not self.session_store:
            return
        
        sync_config = self.config.sync_config or SessionSyncConfig()
        self.session_synchronizer = SessionSynchronizer(self.session_store, sync_config)
        await self.session_synchronizer.start()
        self._components_started["session_synchronizer"] = True
        
        self.logger.info("Session synchronizer initialized")
    
    async def _setup_persistence(self) -> None:
        """设置持久化"""
        if not self.session_store:
            return
        
        self.session_persistence = SessionPersistence(
            self.session_store,
            self.config.backup_dir,
            self.config.max_backups,
            self.config.auto_backup_interval
        )
        await self.session_persistence.start()
        self._components_started["session_persistence"] = True
        
        self.logger.info("Session persistence initialized")
    
    async def _setup_tracker(self) -> None:
        """设置状态跟踪"""
        if not self.session_store:
            return
        
        self.session_tracker = SessionStateTracker(
            self.session_store,
            self.config.history_retention_days,
            self.config.max_events_per_session,
            self.config.enable_prediction
        )
        await self.session_tracker.start()
        self._components_started["session_tracker"] = True
        
        self.logger.info("Session tracker initialized")
    
    async def _setup_expiry(self) -> None:
        """设置过期管理"""
        if not self.session_store:
            return
        
        # 添加默认通知回调
        notification_callbacks = self.config.notification_callbacks.copy()
        if notification_callbacks:
            self.session_expiry = SessionExpiryManager(
                self.session_store,
                self.config.archive_dir,
                self.config.auto_cleanup_interval
            )
            
            # 添加通知回调
            for callback in notification_callbacks:
                await self.session_expiry.add_notification_callback(callback)
            
            await self.session_expiry.start()
            self._components_started["session_expiry"] = True
            
            self.logger.info("Session expiry manager initialized")
    
    async def _start_health_check(self) -> None:
        """启动健康检查"""
        self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self.status == SystemStatus.RUNNING:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                if self.status != SystemStatus.RUNNING:
                    break
                
                # 执行健康检查
                health = await self.get_health_check()
                
                if health["status"] != "healthy":
                    self.logger.warning("Health check failed", health=health)
                
                # 更新最后活动时间
                self.metrics.last_activity = datetime.now()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in health check loop", error=str(e))
                await asyncio.sleep(self._health_check_interval * 2)


# 便捷函数和工厂函数
def create_session_system(config: Optional[SessionSystemConfig] = None) -> SessionSystem:
    """创建会话系统"""
    return SessionSystem(config)


async def create_default_session_system(
    storage_type: StorageType = StorageType.MEMORY,
    storage_config: Optional[Dict[str, Any]] = None,
    enable_all_features: bool = False,
    **config_kwargs
) -> SessionSystem:
    """创建默认配置的会话系统"""
    
    # 基础配置
    config = SessionSystemConfig(
        storage_type=storage_type,
        storage_config=storage_config or {},
        enable_cleanup=True,
        cleanup_interval=300,
    )
    
    # 根据需求启用功能
    if enable_all_features:
        config.update({
            "enable_sync": True,
            "enable_persistence": True,
            "enable_tracking": True,
            "enable_expiry": True,
        })
    
    # 更新其他配置
    config.update(config_kwargs)
    
    # 创建系统
    system = SessionSystem(config)
    await system.start()
    
    return system


# 预定义配置
def get_development_config() -> SessionSystemConfig:
    """开发环境配置"""
    return SessionSystemConfig(
        storage_type=StorageType.MEMORY,
        enable_cleanup=True,
        cleanup_interval=60,  # 更频繁的清理
        enable_tracking=True,
        enable_expiry=True,
        history_retention_days=7,
        max_events_per_session=500,
    )


def get_production_config(
    storage_config: Optional[Dict[str, Any]] = None,
    backup_dir: Optional[Path] = None,
    archive_dir: Optional[Path] = None
) -> SessionSystemConfig:
    """生产环境配置"""
    return SessionSystemConfig(
        storage_type=StorageType.DATABASE,
        storage_config=storage_config or {"db_path": "agentbus_sessions.db"},
        enable_cleanup=True,
        cleanup_interval=300,
        enable_sync=True,
        enable_persistence=True,
        backup_dir=backup_dir or Path("backups"),
        max_backups=50,
        auto_backup_interval=3600,
        enable_tracking=True,
        enable_expiry=True,
        history_retention_days=90,
        max_events_per_session=2000,
        enable_prediction=True,
        archive_dir=archive_dir or Path("archive"),
        auto_cleanup_interval=1800,
    )


# 全局系统实例
_global_system: Optional[SessionSystem] = None


def get_global_session_system() -> Optional[SessionSystem]:
    """获取全局会话系统实例"""
    return _global_system


async def set_global_session_system(system: SessionSystem) -> None:
    """设置全局会话系统实例"""
    global _global_system
    if _global_system and _global_system.status == SystemStatus.RUNNING:
        await _global_system.stop()
    
    _global_system = system


# 便捷函数
async def get_session(session_id: str) -> Optional[SessionContext]:
    """获取会话的便捷函数"""
    system = get_global_session_system()
    if system:
        return await system.get_session(session_id)
    return None


async def create_session(**kwargs) -> SessionContext:
    """创建会话的便捷函数"""
    system = get_global_session_system()
    if system:
        return await system.create_session(**kwargs)
    raise RuntimeError("Global session system not initialized")


async def sync_sessions(source_session_id: str) -> List[str]:
    """同步会话的便捷函数"""
    system = get_global_session_system()
    if system:
        return await system.sync_sessions(source_session_id)
    return []


# 配置管理
class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path("session_system_config.json")
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def save_config(self, config: SessionSystemConfig) -> None:
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
            self.logger.info("Config saved", path=str(self.config_file))
        except Exception as e:
            self.logger.error("Failed to save config", error=str(e))
            raise
    
    async def load_config(self) -> Optional[SessionSystemConfig]:
        """加载配置"""
        try:
            if not self.config_file.exists():
                return None
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            config = SessionSystemConfig(**config_dict)
            self.logger.info("Config loaded", path=str(self.config_file))
            return config
            
        except Exception as e:
            self.logger.error("Failed to load config", error=str(e))
            return None
    
    async def create_default_config(self) -> SessionSystemConfig:
        """创建默认配置"""
        config = get_development_config()
        await self.save_config(config)
        return config