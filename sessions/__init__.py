"""
AgentBus 会话管理系统
AgentBus Session Management System

提供完整的会话管理功能，包括：
- 会话创建、保存、恢复、清理
- 多用户会话和并发管理
- 会话过期和自动清理机制
- 多种存储后端支持
"""

from .context_manager import (
    # 核心类和枚举
    SessionContext,
    SessionType,
    SessionStatus,
    Message,
    MessageType,
    Platform,
    
    # 上下文管理器
    ContextManager,
    get_context_manager,
    init_context_manager,
    shutdown_context_manager,
)

from .session_storage import (
    # 存储接口和实现
    SessionStore,
    MemorySessionStore,
    FileSessionStore,
    DatabaseSessionStore,
    StorageType,
    
    # 存储工厂函数
    create_session_store,
    get_default_session_store,
    set_default_session_store,
)

from .session_manager import (
    # 会话管理器
    SessionManager,
    get_session_manager,
    init_session_manager,
    shutdown_session_manager,
    
    # 上下文管理器装饰器
    session_context,
    
    # 便捷函数
    create_session,
    get_session,
    add_message,
)

# 新增的扩展功能模块
from .session_sync import (
    # 会话同步
    SessionSynchronizer,
    SessionSyncConfig,
    SyncStrategy,
    SyncStatus,
    SessionIdentity,
    SyncOperation,
    create_session_sync,
    IdentityMapper,
)

from .session_persistence import (
    # 会话持久化
    SessionPersistence,
    BackupFormat,
    CompressionLevel,
    RecoveryStrategy,
    RecoveryOptions,
    BackupMetadata,
    create_session_persistence,
    session_backup_context,
)

from .session_state_tracker import (
    # 会话状态跟踪
    SessionStateTracker,
    StateTransitionType,
    EventType,
    StateTransition,
    SessionEvent,
    SessionMetrics,
    StateMachine,
    PatternAnalyzer,
    StatePredictor,
    create_session_state_tracker,
)

from .session_expiry import (
    # 会话过期管理
    SessionExpiryManager,
    ExpiryStrategy,
    CleanupAction,
    RetentionPolicy,
    ExpiryRule,
    ExpiryResult,
    ExpiryStatistics,
    create_expiry_manager,
    default_notification_callback,
    create_email_notification_callback,
    create_webhook_notification_callback,
)

from .session_system import (
    # 完整会话管理系统
    SessionSystem,
    SessionSystemConfig,
    SystemStatus,
    SystemMetrics,
    create_session_system,
    create_default_session_system,
    get_development_config,
    get_production_config,
    get_global_session_system,
    set_global_session_system,
    ConfigManager,
)

# 版本信息
__version__ = "1.0.0"
__author__ = "AgentBus Development Team"

# 导出所有公共接口
__all__ = [
    # 核心类
    "SessionContext",
    "SessionType", 
    "SessionStatus",
    "Message",
    "MessageType",
    "Platform",
    
    # 上下文管理
    "ContextManager",
    "get_context_manager",
    "init_context_manager", 
    "shutdown_context_manager",
    
    # 存储系统
    "SessionStore",
    "MemorySessionStore",
    "FileSessionStore", 
    "DatabaseSessionStore",
    "StorageType",
    "create_session_store",
    "get_default_session_store",
    "set_default_session_store",
    
    # 会话管理
    "SessionManager",
    "get_session_manager",
    "init_session_manager",
    "shutdown_session_manager",
    
    # 装饰器和工具
    "session_context",
    "create_session",
    "get_session", 
    "add_message",
    
    # 会话同步
    "SessionSynchronizer",
    "SessionSyncConfig",
    "SyncStrategy",
    "SyncStatus",
    "SessionIdentity",
    "SyncOperation",
    "create_session_sync",
    "IdentityMapper",
    
    # 会话持久化
    "SessionPersistence",
    "BackupFormat",
    "CompressionLevel",
    "RecoveryStrategy",
    "RecoveryOptions",
    "BackupMetadata",
    "create_session_persistence",
    "session_backup_context",
    
    # 会话状态跟踪
    "SessionStateTracker",
    "StateTransitionType",
    "EventType",
    "StateTransition",
    "SessionEvent",
    "SessionMetrics",
    "StateMachine",
    "PatternAnalyzer",
    "StatePredictor",
    "create_session_state_tracker",
    
    # 会话过期管理
    "SessionExpiryManager",
    "ExpiryStrategy",
    "CleanupAction",
    "RetentionPolicy",
    "ExpiryRule",
    "ExpiryResult",
    "ExpiryStatistics",
    "create_expiry_manager",
    "default_notification_callback",
    "create_email_notification_callback",
    "create_webhook_notification_callback",
    
    # 完整会话管理系统
    "SessionSystem",
    "SessionSystemConfig",
    "SystemStatus",
    "SystemMetrics",
    "create_session_system",
    "create_default_session_system",
    "get_development_config",
    "get_production_config",
    "get_global_session_system",
    "set_global_session_system",
    "ConfigManager",
]

# 初始化日志
import logging
logger = logging.getLogger(__name__)

# 初始化函数
async def initialize_sessions(
    storage_type: StorageType = StorageType.MEMORY,
    storage_config: dict = None,
    enable_cleanup: bool = True,
    cleanup_interval: int = 300,
    enable_all_features: bool = False,
    **system_config
) -> SessionSystem:
    """
    初始化完整会话管理系统
    
    Args:
        storage_type: 存储类型 (MEMORY, FILE, DATABASE)
        storage_config: 存储配置字典
        enable_cleanup: 是否启用自动清理
        cleanup_interval: 清理间隔（秒）
        enable_all_features: 是否启用所有功能模块
        **system_config: 传递给完整系统的其他配置参数
    
    Returns:
        SessionSystem: 完整会话管理系统实例
    
    Examples:
        # 使用基本功能
        system = await initialize_sessions()
        
        # 启用所有功能
        system = await initialize_sessions(
            storage_type=StorageType.DATABASE,
            storage_config={"db_path": "./agentbus.db"},
            enable_all_features=True,
            enable_sync=True,
            enable_persistence=True,
            backup_dir="./backups",
            enable_tracking=True,
            enable_expiry=True,
            archive_dir="./archive"
        )
    """
    try:
        # 配置存储
        storage_config = storage_config or {}
        
        # 创建系统配置
        config = SessionSystemConfig(
            storage_type=storage_type,
            storage_config=storage_config,
            enable_cleanup=enable_cleanup,
            cleanup_interval=cleanup_interval,
            **system_config
        )
        
        # 如果启用所有功能，设置相关配置
        if enable_all_features:
            config.update({
                "enable_sync": True,
                "enable_persistence": True,
                "enable_tracking": True,
                "enable_expiry": True,
            })
        
        # 创建并启动系统
        session_system = SessionSystem(config)
        await session_system.start()
        
        # 设置为全局系统
        await set_global_session_system(session_system)
        
        logger.info("Complete session management system initialized", 
                   storage_type=storage_type.value,
                   features_enabled={
                       "cleanup": config.enable_cleanup,
                       "sync": config.enable_sync,
                       "persistence": config.enable_persistence,
                       "tracking": config.enable_tracking,
                       "expiry": config.enable_expiry
                   },
                   cleanup_interval=cleanup_interval)
        
        return session_system
        
    except Exception as e:
        logger.error("Failed to initialize session management system", error=str(e))
        raise


# 向后兼容的初始化函数
async def initialize_basic_sessions(
    storage_type: StorageType = StorageType.MEMORY,
    storage_config: dict = None,
    enable_cleanup: bool = True,
    cleanup_interval: int = 300
) -> SessionManager:
    """
    初始化基础会话管理系统（向后兼容）
    
    Args:
        storage_type: 存储类型 (MEMORY, FILE, DATABASE)
        storage_config: 存储配置字典
        enable_cleanup: 是否启用自动清理
        cleanup_interval: 清理间隔（秒）
    
    Returns:
        SessionManager: 基础会话管理器实例
    
    Examples:
        # 使用基础功能
        manager = await initialize_basic_sessions()
        
        # 使用文件存储
        manager = await initialize_basic_sessions(
            storage_type=StorageType.FILE,
            storage_config={"storage_dir": "./sessions"}
        )
    """
    try:
        # 配置存储
        storage_config = storage_config or {}
        
        # 创建存储实例
        if storage_type == StorageType.MEMORY:
            session_store = MemorySessionStore()
        elif storage_type == StorageType.FILE:
            storage_dir = storage_config.get("storage_dir", "sessions_data")
            session_store = FileSessionStore(storage_dir)
        elif storage_type == StorageType.DATABASE:
            db_path = storage_config.get("db_path", "agentbus_sessions.db")
            session_store = DatabaseSessionStore(db_path)
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")
        
        # 创建会话管理器
        session_manager = SessionManager(
            session_store=session_store,
            enable_cleanup=enable_cleanup,
            cleanup_interval=cleanup_interval
        )
        
        # 启动管理器
        await session_manager.start()
        
        # 设置为全局默认
        await set_default_session_store(session_store)
        
        logger.info("Basic session management system initialized", 
                   storage_type=storage_type.value,
                   enable_cleanup=enable_cleanup,
                   cleanup_interval=cleanup_interval)
        
        return session_manager
        
    except Exception as e:
        logger.error("Failed to initialize basic session management system", error=str(e))
        raise


async def shutdown_sessions() -> None:
    """关闭会话管理系统"""
    try:
        # 首先关闭完整会话系统
        global_system = get_global_session_system()
        if global_system:
            await global_system.stop()
        
        # 然后关闭基础管理器
        await shutdown_session_manager()
        await shutdown_context_manager()
        
        logger.info("Session management system shutdown completed")
    except Exception as e:
        logger.error("Error during session system shutdown", error=str(e))
        raise


# 健康检查
async def health_check() -> dict:
    """
    检查会话管理系统的健康状态
    
    Returns:
        dict: 健康状态信息
    """
    try:
        session_manager = get_session_manager()
        health_info = await session_manager.health_check()
        
        return {
            "status": "healthy",
            "system": "session_management",
            "version": __version__,
            "details": health_info,
            "timestamp": "2024-01-01T00:00:00Z"  # 可以用datetime.now().isoformat()替换
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "system": "session_management",
            "version": __version__,
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        }


# 便捷的配置函数
def configure_logging(level: str = "INFO", format_string: str = None) -> None:
    """
    配置会话管理系统的日志
    
    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: 日志格式字符串
    """
    import logging
    
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    logger.info("Session management logging configured", level=level)


# 导出主要类作为模块级接口
Session = SessionContext  # 别名，便于使用

# 设置默认配置
DEFAULT_CONFIG = {
    "storage_type": StorageType.MEMORY,
    "enable_cleanup": True,
    "cleanup_interval": 300,  # 5分钟
    "max_history_per_session": 50,
    "idle_timeout": 3600,  # 1小时
    "enable_parent_child_sessions": True,
    "enable_session_search": True,
}

def get_default_config() -> dict:
    """获取默认配置"""
    return DEFAULT_CONFIG.copy()


def update_default_config(**kwargs) -> None:
    """更新默认配置"""
    DEFAULT_CONFIG.update(kwargs)
    logger.info("Default config updated", new_config=DEFAULT_CONFIG)


# 初始化时自动配置日志
try:
    configure_logging()
except Exception:
    pass  # 忽略日志配置错误