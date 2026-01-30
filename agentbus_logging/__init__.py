"""
AgentBus增强日志和监控系统

基于Moltbot日志系统设计的完整日志管理解决方案，包括：
- 结构化日志记录（分级记录）
- 性能指标监控
- 告警系统
- 日志轮转和清理
- 远程日志传输
- 日志查询和分析
- 日志存储管理
- 高级分析和可视化
- 多种输出格式支持
"""

from .log_manager import (
    LogManager,
    LogLevel,
    LogFormat,
    LogTransport,
    LogRecord,
    get_logger,
    get_child_logger,
    configure_logging,
    register_log_transport,
)
from .metrics import (
    MetricsCollector,
    SystemMetrics,
    ApplicationMetrics,
    PerformanceMonitor,
    get_metrics_collector,
    increment_metric,
    set_metric,
    record_time,
    record_value,
    create_performance_monitor,
)
from .alerting import (
    AlertManager,
    AlertLevel,
    AlertRule,
    AlertRuleType,
    AlertNotification,
    get_alert_manager,
    create_email_channel,
    create_webhook_channel,
    create_slack_channel,
    add_alert_rule,
    trigger_manual_alert,
)
from .remote_transport import (
    RemoteTransport,
    HTTPLogTransport,
    WebSocketLogTransport,
    TCPLogTransport,
    LogForwarder,
    CentralizedLogServer,
    create_http_transport,
    create_websocket_transport,
    create_tcp_transport,
)
from .log_query import (
    LogQuery,
    LogQueryEngine,
    LogAnalyzer,
    LogStreamReader,
    LogAnalysisResult,
    LogQuery,
    LogAnalysisResult,
    create_query_engine,
    analyze_logs,
    create_visualizer,
    search_logs,
)
from .log_storage import (
    LogStorage,
    StorageConfig,
    StorageStrategy,
    CompressionType,
    LogSegment,
    create_storage,
    create_archive_manager,
)
from .enhanced_logging import (
    EnhancedLogLevel,
    MonitoringEventType,
    MonitoringEvent,
    EnhancedLogger,
    AdvancedMonitoringSystem,
    LogCorrelationTracker,
    get_enhanced_monitoring_system,
    initialize_enhanced_logging,
    get_enhanced_logger,
    performance_monitor,
    audit_log,
    security_monitor,
)
from .log_analytics import (
    LogPatternAnalyzer,
    ErrorAnalyzer,
    PerformanceAnalyzer,
    LogVisualizer,
    AnomalyDetector,
    LogReporter,
    quick_log_analysis,
    detect_log_anomalies,
)

__all__ = [
    # Log Manager
    "LogManager",
    "LogLevel", 
    "LogFormat",
    "LogTransport",
    "LogRecord",
    "get_logger",
    "get_child_logger", 
    "configure_logging",
    "register_log_transport",
    
    # Metrics
    "MetricsCollector",
    "SystemMetrics",
    "ApplicationMetrics", 
    "PerformanceMonitor",
    "get_metrics_collector",
    "increment_metric",
    "set_metric",
    "record_time",
    "record_value",
    "create_performance_monitor",
    
    # Alerting
    "AlertManager",
    "AlertLevel",
    "AlertRule",
    "AlertRuleType",
    "AlertNotification",
    "get_alert_manager",
    "create_email_channel",
    "create_webhook_channel",
    "create_slack_channel",
    "add_alert_rule",
    "trigger_manual_alert",
    
    # Remote Transport
    "RemoteTransport",
    "HTTPLogTransport",
    "WebSocketLogTransport",
    "TCPLogTransport",
    "LogForwarder",
    "CentralizedLogServer",
    "create_http_transport",
    "create_websocket_transport",
    "create_tcp_transport",
    
    # Log Query
    "LogQuery",
    "LogQueryEngine",
    "LogAnalyzer",
    "LogStreamReader",
    "LogAnalysisResult",
    "create_query_engine",
    "analyze_logs",
    "create_visualizer",
    "search_logs",
    
    # Log Storage
    "LogStorage",
    "StorageConfig",
    "StorageStrategy",
    "CompressionType",
    "LogSegment",
    "create_storage",
    "create_archive_manager",
    
    # Enhanced Logging
    "EnhancedLogLevel",
    "MonitoringEventType",
    "MonitoringEvent",
    "EnhancedLogger",
    "AdvancedMonitoringSystem",
    "LogCorrelationTracker",
    "get_enhanced_monitoring_system",
    "initialize_enhanced_logging",
    "get_enhanced_logger",
    "performance_monitor",
    "audit_log",
    "security_monitor",
    
    # Analytics
    "LogPatternAnalyzer",
    "ErrorAnalyzer",
    "PerformanceAnalyzer",
    "LogVisualizer",
    "AnomalyDetector",
    "LogReporter",
    "quick_log_analysis",
    "detect_log_anomalies",
]

# 全局日志管理器实例
_log_manager: LogManager | None = None
_metrics_collector: MetricsCollector | None = None
_alert_manager: AlertManager | None = None
_enhanced_monitoring_system: AdvancedMonitoringSystem | None = None
_correlation_tracker: LogCorrelationTracker | None = None


def get_log_manager() -> LogManager:
    """获取全局日志管理器实例"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager


def get_metrics_manager() -> MetricsCollector:
    """获取全局指标收集器实例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_alerting_manager() -> AlertManager:
    """获取全局告警管理器实例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def get_enhanced_monitoring_system_instance() -> AdvancedMonitoringSystem:
    """获取全局增强监控系统实例"""
    global _enhanced_monitoring_system
    return _enhanced_monitoring_system


def get_correlation_tracker() -> LogCorrelationTracker:
    """获取全局关联跟踪器实例"""
    global _correlation_tracker
    return _correlation_tracker


def initialize_logging(
    log_dir: str = "/tmp/agentbus/logs",
    level: str = "INFO",
    format_type: str = "json",
    enable_metrics: bool = True,
    enable_alerting: bool = True,
    enable_console: bool = True,
    max_file_size: int = 100 * 1024 * 1024,  # 100MB
    backup_count: int = 10,
    retention_days: int = 30,
    enable_compression: bool = True,
) -> None:
    """
    初始化AgentBus日志系统
    
    Args:
        log_dir: 日志目录
        level: 日志级别
        format_type: 日志格式 (json, text, colored)
        enable_metrics: 是否启用指标收集
        enable_alerting: 是否启用告警系统
        enable_console: 是否启用控制台输出
        max_file_size: 最大文件大小
        backup_count: 备份文件数量
        retention_days: 保留天数
        enable_compression: 是否启用压缩
    """
    # 配置日志管理器
    from .log_manager import LogManager
    log_manager = LogManager()
    log_manager.configure(
        log_dir=log_dir,
        level=level,
        format_type=format_type,
        max_file_size=max_file_size,
        backup_count=backup_count,
        retention_days=retention_days,
        enable_console=enable_console,
        enable_file=True,
        enable_compression=enable_compression,
    )
    
    # 初始化指标收集器
    if enable_metrics:
        metrics = get_metrics_collector()
        metrics.start_collection()
    
    # 初始化告警管理器
    if enable_alerting:
        alerts = get_alert_manager()
        alerts.start_monitoring()


# 默认配置
DEFAULT_LOG_DIR = "/tmp/agentbus/logs"
DEFAULT_LOG_MAX_SIZE = 100 * 1024 * 1024  # 100MB
DEFAULT_LOG_MAX_FILES = 10
DEFAULT_LOG_RETENTION_DAYS = 30

# 支持的日志级别
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
ENHANCED_LOG_LEVELS = LOG_LEVELS + ["TRACE", "SECURITY", "AUDIT", "PERFORMANCE", "BUSINESS"]

# 支持的日志格式
LOG_FORMATS = ["json", "text", "colored", "compact"]

# 告警级别
ALERT_LEVELS = ["INFO", "WARNING", "ERROR", "CRITICAL"]

# 存储策略
STORAGE_STRATEGIES = ["text", "json", "binary", "compressed", "mixed"]

# 压缩类型
COMPRESSION_TYPES = ["none", "gzip", "zstd", "lz4"]

# 远程传输类型
REMOTE_TRANSPORT_TYPES = ["http", "websocket", "tcp", "redis"]

# 监控事件类型
MONITORING_EVENT_TYPES = ["log_generated", "metric_collected", "alert_triggered", "log_queried", "storage_rotated", "remote_sent"]

# 默认增强配置示例
DEFAULT_ENHANCED_CONFIG = {
    "logging": {
        "log_dir": "/tmp/agentbus/logs",
        "level": "INFO",
        "format_type": "json",
        "max_file_size": 100 * 1024 * 1024,
        "backup_count": 10,
        "retention_days": 30,
        "enable_console": True,
        "enable_file": True,
        "enable_compression": True,
    },
    "remote_transports": [],
    "log_dirs": ["/tmp/agentbus/logs"],
    "index_path": "/tmp/agentbus/logs/index",
    "storage": {
        "base_path": "/tmp/agentbus/storage",
        "strategy": "json",
        "compression": "gzip",
        "max_file_size": 100 * 1024 * 1024,
        "max_files_per_day": 24,
        "retention_days": 30,
        "enable_indexing": True,
        "enable_partitioning": True,
        "partition_interval": "hour",
    },
    "stream_monitoring": {
        "log_files": []
    },
    "centralized_server": {
        "port": 9999,
        "enable_ssl": False,
    },
    "alert_rules": [
        {
            "name": "high_error_rate",
            "description": "错误率过高",
            "level": "ERROR",
            "rule_type": "threshold",
            "metric_name": "errors_total",
            "condition": ">",
            "threshold": 10.0,
            "evaluation_window": 300,
            "cooldown_period": 600
        }
    ]
}