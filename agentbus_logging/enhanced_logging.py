"""
AgentBus增强日志监控系统

集成所有日志功能的高级监控系统：分级记录、远程传输、查询分析、存储管理、告警系统
"""

import os
import json
import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

# 导入所有模块
from .log_manager import LogManager, LogLevel, LogRecord, Logger, get_logger
from .metrics import MetricsCollector, get_metrics_collector
from .alerting import AlertManager, AlertRule, AlertLevel, AlertRuleType, get_alert_manager
from .remote_transport import (
    RemoteTransport, HTTPLogTransport, WebSocketLogTransport, TCPLogTransport,
    LogForwarder, CentralizedLogServer, create_http_transport
)
from .log_query import (
    LogQuery, LogQueryEngine, LogAnalyzer, LogStreamReader,
    create_query_engine, analyze_logs, create_visualizer
)
from .log_storage import (
    LogStorage, StorageConfig, StorageStrategy, CompressionType,
    create_storage, create_archive_manager
)


class EnhancedLogLevel(Enum):
    """增强的日志级别"""
    TRACE = "TRACE"  # 更详细的调试信息
    SECURITY = "SECURITY"  # 安全相关事件
    AUDIT = "AUDIT"  # 审计日志
    PERFORMANCE = "PERFORMANCE"  # 性能日志
    BUSINESS = "BUSINESS"  # 业务日志
    
    @classmethod
    def from_log_level(cls, log_level):
        """从基础日志级别转换为增强级别"""
        return cls.TRACE if log_level == "DEBUG" else log_level


class MonitoringEventType(Enum):
    """监控事件类型"""
    LOG_GENERATED = "log_generated"
    METRIC_COLLECTED = "metric_collected"
    ALERT_TRIGGERED = "alert_triggered"
    LOG_QUERIED = "log_queried"
    STORAGE_ROTATED = "storage_rotated"
    REMOTE_SENT = "remote_sent"


@dataclass
class MonitoringEvent:
    """监控事件"""
    event_type: MonitoringEventType
    timestamp: str
    source: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None


class EnhancedLogger(Logger):
    """增强的日志记录器"""
    
    def __init__(self, name: str, level: LogLevel = LogLevel.INFO):
        super().__init__(name, level)
        self.correlation_id: Optional[str] = None
        self.event_callbacks: List[Callable] = []
        
    def set_correlation_id(self, correlation_id: str) -> None:
        """设置关联ID"""
        self.correlation_id = correlation_id
        
    def add_event_callback(self, callback: Callable) -> None:
        """添加事件回调"""
        self.event_callbacks.append(callback)
        
    def _log_with_correlation(self, level: LogLevel, message: str, **kwargs) -> None:
        """带关联ID的日志记录"""
        if self.correlation_id:
            kwargs['correlation_id'] = self.correlation_id
            
        self._log(level, message, **kwargs)
        
        # 触发监控事件
        event = MonitoringEvent(
            event_type=MonitoringEventType.LOG_GENERATED,
            timestamp=datetime.utcnow().isoformat(),
            source=self.name,
            data={
                "level": level.value,
                "message": message,
                "extra_fields": kwargs
            },
            correlation_id=self.correlation_id
        )
        
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Event callback failed: {e}")
                
    def trace(self, message: str, **kwargs) -> None:
        """跟踪日志"""
        self._log_with_correlation(EnhancedLogLevel.TRACE, message, **kwargs)
        
    def security(self, message: str, **kwargs) -> None:
        """安全日志"""
        self._log_with_correlation(EnhancedLogLevel.SECURITY, message, **kwargs)
        
    def audit(self, message: str, **kwargs) -> None:
        """审计日志"""
        self._log_with_correlation(EnhancedLogLevel.AUDIT, message, **kwargs)
        
    def performance(self, message: str, duration: float = None, **kwargs) -> None:
        """性能日志"""
        if duration is not None:
            kwargs['duration'] = duration
        self._log_with_correlation(EnhancedLogLevel.PERFORMANCE, message, **kwargs)
        
    def business(self, message: str, **kwargs) -> None:
        """业务日志"""
        self._log_with_correlation(EnhancedLogLevel.BUSINESS, message, **kwargs)


class AdvancedMonitoringSystem:
    """高级监控系统"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._running = False
        
        # 核心组件
        self.log_manager: LogManager = LogManager()
        self.metrics_collector: MetricsCollector = MetricsCollector()
        self.alert_manager: AlertManager = AlertManager(self.metrics_collector)
        
        # 增强组件
        self.log_forwarder: Optional[LogForwarder] = None
        self.query_engine: Optional[LogQueryEngine] = None
        self.storage: Optional[LogStorage] = None
        self.stream_reader: Optional[LogStreamReader] = None
        self.centralized_server: Optional[CentralizedLogServer] = None
        
        # 事件回调
        self._event_callbacks: List[Callable] = []
        
        # 线程池
        self._executor = ThreadPoolExecutor(max_workers=6)
        
    def initialize(self) -> None:
        """初始化监控系统"""
        # 配置基础日志管理
        self._configure_logging()
        
        # 配置远程传输
        if self.config.get('remote_transports'):
            self._configure_remote_transports()
            
        # 配置查询引擎
        if self.config.get('log_dirs'):
            self._configure_query_engine()
            
        # 配置存储系统
        if self.config.get('storage'):
            self._configure_storage()
            
        # 配置实时监控
        if self.config.get('stream_monitoring'):
            self._configure_stream_monitoring()
            
        # 配置集中式服务器
        if self.config.get('centralized_server'):
            self._configure_centralized_server()
            
        # 配置告警规则
        self._configure_alert_rules()
        
        # 启动监控
        self.start()
        
    def _configure_logging(self) -> None:
        """配置日志系统"""
        log_config = self.config.get('logging', {})
        self.log_manager.configure(**log_config)
        
        # 注册增强的事件回调
        for logger_name in self.log_manager.loggers:
            logger = self.log_manager.get_logger(logger_name)
            if hasattr(logger, 'add_event_callback'):
                logger.add_event_callback(self._handle_log_event)
                
    def _configure_remote_transports(self) -> None:
        """配置远程传输"""
        transports_config = self.config.get('remote_transports', [])
        transports = []
        
        for transport_config in transports_config:
            transport_type = transport_config.get('type', 'http')
            
            if transport_type == 'http':
                transport = create_http_transport(
                    name=transport_config['name'],
                    url=transport_config['url'],
                    **transport_config.get('options', {})
                )
                transports.append(transport)
            elif transport_type == 'websocket':
                # WebSocket传输
                from .remote_transport import WebSocketLogTransport
                transport = WebSocketLogTransport(
                    name=transport_config['name'],
                    ws_url=transport_config['url'],
                    **transport_config.get('options', {})
                )
                transports.append(transport)
            elif transport_type == 'tcp':
                from .remote_transport import TCPLogTransport
                transport = TCPLogTransport(
                    name=transport_config['name'],
                    host=transport_config['host'],
                    port=transport_config['port'],
                    **transport_config.get('options', {})
                )
                transports.append(transport)
                
        if transports:
            self.log_forwarder = LogForwarder(transports)
            
    def _configure_query_engine(self) -> None:
        """配置查询引擎"""
        log_dirs = self.config.get('log_dirs', [])
        index_path = self.config.get('index_path', '/tmp/agentbus/logs/index')
        
        if log_dirs:
            self.query_engine = create_query_engine(log_dirs, index_path)
            
    def _configure_storage(self) -> None:
        """配置存储系统"""
        storage_config = self.config.get('storage', {})
        config_obj = StorageConfig(**storage_config)
        self.storage = create_storage(config_obj)
        
    def _configure_stream_monitoring(self) -> None:
        """配置流式监控"""
        stream_config = self.config.get('stream_monitoring', {})
        log_files = stream_config.get('log_files', [])
        
        if log_files:
            self.stream_reader = LogStreamReader(log_files)
            self.stream_reader.add_callback(self._handle_stream_event)
            
    def _configure_centralized_server(self) -> None:
        """配置集中式服务器"""
        server_config = self.config.get('centralized_server', {})
        
        self.centralized_server = CentralizedLogServer(
            port=server_config.get('port', 9999),
            enable_ssl=server_config.get('enable_ssl', False),
            cert_file=server_config.get('cert_file'),
            key_file=server_config.get('key_file')
        )
        
        # 添加日志处理回调
        self.centralized_server.add_log_handler(self._handle_server_logs)
        
    def _configure_alert_rules(self) -> None:
        """配置告警规则"""
        alert_rules = self.config.get('alert_rules', [])
        
        for rule_config in alert_rules:
            rule = AlertRule(**rule_config)
            self.alert_manager.add_rule(rule)
            
        # 启动监控
        self.alert_manager.start_monitoring()
        
    def start(self) -> None:
        """启动监控系统"""
        self._running = True
        
        # 启动指标收集
        self.metrics_collector.start_collection()
        
        # 启动流式监控
        if self.stream_reader:
            self.stream_reader.start()
            
        # 启动后台任务
        self._start_background_tasks()
        
    def _start_background_tasks(self) -> None:
        """启动后台任务"""
        def maintenance_task():
            """维护任务"""
            while self._running:
                try:
                    # 更新日志索引
                    if self.query_engine:
                        self.query_engine.index_logs()
                        
                    # 触发指标收集回调
                    metrics_data = self.metrics_collector.get_metrics_snapshot()
                    event = MonitoringEvent(
                        event_type=MonitoringEventType.METRIC_COLLECTED,
                        timestamp=datetime.utcnow().isoformat(),
                        source="metrics",
                        data=metrics_data
                    )
                    self._trigger_event(event)
                    
                    time.sleep(60)  # 每分钟执行一次
                    
                except Exception as e:
                    print(f"Maintenance task error: {e}")
                    time.sleep(60)
                    
        self._executor.submit(maintenance_task)
        
    def _handle_log_event(self, event: MonitoringEvent) -> None:
        """处理日志事件"""
        # 转发到远程传输
        if self.log_forwarder:
            # 将事件转换为日志记录
            record = LogRecord(**event.data)
            self.log_forwarder.forward_record(record)
            
        # 触发指标收集
        self.metrics_collector.increment_counter("logs_generated", 1, {
            "level": event.data.get("level"),
            "logger": event.source
        })
        
        self._trigger_event(event)
        
    def _handle_stream_event(self, record: LogRecord) -> None:
        """处理流式事件"""
        # 记录流式日志事件
        event = MonitoringEvent(
            event_type=MonitoringEventType.LOG_GENERATED,
            timestamp=datetime.utcnow().isoformat(),
            source="stream",
            data=record.to_dict()
        )
        
        self._trigger_event(event)
        
    def _handle_server_logs(self, records: List[LogRecord]) -> None:
        """处理服务器接收的日志"""
        event = MonitoringEvent(
            event_type=MonitoringEventType.LOG_GENERATED,
            timestamp=datetime.utcnow().isoformat(),
            source="server",
            data={"records": [r.to_dict() for r in records]}
        )
        
        self._trigger_event(event)
        
    def _trigger_event(self, event: MonitoringEvent) -> None:
        """触发监控事件"""
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Event callback failed: {e}")
                
    def add_event_callback(self, callback: Callable) -> None:
        """添加事件回调"""
        self._event_callbacks.append(callback)
        
    def search_logs(self, query: LogQuery) -> List[LogRecord]:
        """搜索日志"""
        if not self.query_engine:
            return []
            
        records = self.query_engine.query(query)
        
        # 记录查询事件
        event = MonitoringEvent(
            event_type=MonitoringEventType.LOG_QUERIED,
            timestamp=datetime.utcnow().isoformat(),
            source="query",
            data={
                "query": asdict(query),
                "result_count": len(records)
            }
        )
        self._trigger_event(event)
        
        return records
        
    def analyze_logs(self, records: List[LogRecord]) -> Any:
        """分析日志"""
        result = analyze_logs(records)
        
        # 记录分析事件
        event = MonitoringEvent(
            event_type=MonitoringEventType.LOG_QUERIED,
            timestamp=datetime.utcnow().isoformat(),
            source="analyzer",
            data={
                "input_count": len(records),
                "analysis": asdict(result)
            }
        )
        self._trigger_event(event)
        
        return result
        
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        status = {
            "timestamp": datetime.utcnow().isoformat(),
            "running": self._running,
            "components": {
                "log_manager": True,
                "metrics_collector": self.metrics_collector._running,
                "alert_manager": self._running,
                "log_forwarder": self.log_forwarder is not None,
                "query_engine": self.query_engine is not None,
                "storage": self.storage is not None,
                "stream_reader": self.stream_reader is not None,
                "centralized_server": self.centralized_server is not None
            }
        }
        
        # 添加指标快照
        if self.metrics_collector:
            status["metrics"] = self.metrics_collector.get_metrics_snapshot()
            
        # 添加活跃告警
        if self.alert_manager:
            status["active_alerts"] = len(self.alert_manager.get_active_alerts())
            
        # 添加存储统计
        if self.storage:
            status["storage_stats"] = self.storage.get_storage_stats()
            
        return status
        
    def trigger_custom_alert(self, name: str, message: str, level: AlertLevel = AlertLevel.INFO,
                          extra_data: Optional[Dict[str, Any]] = None) -> None:
        """触发自定义告警"""
        self.alert_manager.trigger_alert(
            rule_name=name,
            message=message,
            metric_name="custom_metric",
            metric_value=1.0,
            labels=extra_data or {}
        )
        
    def export_logs(self, start_time: datetime, end_time: datetime,
                   output_path: str, format_type: str = "json") -> None:
        """导出日志"""
        if self.storage:
            self.storage.export_data(start_time, end_time, output_path, format_type)
            
    def stop(self) -> None:
        """停止监控系统"""
        self._running = False
        
        # 停止组件
        if self.stream_reader:
            self.stream_reader.stop()
            
        if self.metrics_collector:
            self.metrics_collector.stop_collection()
            
        if self.alert_manager:
            self.alert_manager.stop_monitoring()
            
        if self.storage:
            self.storage.close()
            
        # 关闭线程池
        self._executor.shutdown(wait=True)


class LogCorrelationTracker:
    """日志关联跟踪器"""
    
    def __init__(self, monitoring_system: AdvancedMonitoringSystem):
        self.monitoring_system = monitoring_system
        self._active_correlations: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        
        # 添加事件回调
        monitoring_system.add_event_callback(self._track_correlation_events)
        
    def start_correlation(self, correlation_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """开始关联跟踪"""
        with self._lock:
            self._active_correlations[correlation_id] = {
                "start_time": datetime.utcnow(),
                "metadata": metadata or {},
                "events": [],
                "logs": [],
                "metrics": []
            }
            
        return correlation_id
        
    def end_correlation(self, correlation_id: str, status: str = "completed") -> Dict[str, Any]:
        """结束关联跟踪"""
        with self._lock:
            correlation_data = self._active_correlations.pop(correlation_id, None)
            
        if not correlation_data:
            return {}
            
        # 计算统计信息
        end_time = datetime.utcnow()
        duration = (end_time - correlation_data["start_time"]).total_seconds()
        
        result = {
            "correlation_id": correlation_id,
            "status": status,
            "start_time": correlation_data["start_time"].isoformat(),
            "end_time": end_time.isoformat(),
            "duration": duration,
            "event_count": len(correlation_data["events"]),
            "log_count": len(correlation_data["logs"]),
            "metric_count": len(correlation_data["metrics"]),
            "metadata": correlation_data["metadata"]
        }
        
        return result
        
    def _track_correlation_events(self, event: MonitoringEvent) -> None:
        """跟踪关联事件"""
        correlation_id = event.correlation_id
        if not correlation_id:
            return
            
        with self._lock:
            if correlation_id in self._active_correlations:
                self._active_correlations[correlation_id]["events"].append(event)


# 全局监控系统实例
_monitoring_system: Optional[AdvancedMonitoringSystem] = None


def get_enhanced_monitoring_system(config: Optional[Dict[str, Any]] = None) -> AdvancedMonitoringSystem:
    """获取增强监控系统实例"""
    global _monitoring_system
    
    if _monitoring_system is None and config:
        _monitoring_system = AdvancedMonitoringSystem(config)
        _monitoring_system.initialize()
        
    return _monitoring_system


def initialize_enhanced_logging(config: Dict[str, Any]) -> AdvancedMonitoringSystem:
    """初始化增强日志系统"""
    monitoring_system = get_enhanced_monitoring_system(config)
    return monitoring_system


def get_enhanced_logger(name: str, correlation_id: Optional[str] = None) -> EnhancedLogger:
    """获取增强日志记录器"""
    monitoring_system = get_enhanced_monitoring_system()
    
    if monitoring_system:
        logger = EnhancedLogger(name)
        if correlation_id:
            logger.set_correlation_id(correlation_id)
        return logger
    else:
        # 回退到基础日志记录器
        return EnhancedLogger(name)


# 便捷函数和装饰器
def performance_monitor(name: str, correlation_id: Optional[str] = None):
    """性能监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger = get_enhanced_logger("performance", correlation_id)
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.performance(f"{name} completed", duration=duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.performance(f"{name} failed", duration=duration)
                raise
                
        return wrapper
    return decorator


def audit_log(action: str, resource: str, result: str = "success"):
    """审计日志装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_enhanced_logger("audit")
            try:
                result = func(*args, **kwargs)
                logger.audit(f"Action: {action}, Resource: {resource}, Result: {result}")
                return result
            except Exception as e:
                logger.audit(f"Action: {action}, Resource: {resource}, Result: failed, Error: {str(e)}")
                raise
                
        return wrapper
    return decorator


def security_monitor(event_type: str):
    """安全监控装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_enhanced_logger("security")
            logger.security(f"Security event: {event_type}")
            return func(*args, **kwargs)
        return wrapper
    return decorator