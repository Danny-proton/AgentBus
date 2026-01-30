"""
诊断事件模块 - 提供系统诊断和事件监控功能
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio


class DiagnosticEventType(Enum):
    """诊断事件类型"""
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"
    SYSTEM_INFO = "system.info"
    
    CPU_USAGE_HIGH = "cpu.usage.high"
    MEMORY_USAGE_HIGH = "memory.usage.high"
    DISK_USAGE_HIGH = "disk.usage.high"
    NETWORK_ERROR = "network.error"
    
    PROCESS_START = "process.start"
    PROCESS_STOP = "process.stop"
    PROCESS_ERROR = "process.error"
    PROCESS_HIGH_CPU = "process.high.cpu"
    PROCESS_HIGH_MEMORY = "process.high.memory"
    
    FILE_OPERATION = "file.operation"
    FILE_ERROR = "file.error"
    DIRECTORY_OPERATION = "directory.operation"
    
    SERVICE_START = "service.start"
    SERVICE_STOP = "service.stop"
    SERVICE_ERROR = "service.error"
    
    SECURITY_EVENT = "security.event"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    
    CUSTOM = "custom"


@dataclass
class DiagnosticEvent:
    """诊断事件"""
    event_id: str
    event_type: DiagnosticEventType
    timestamp: datetime
    source: str
    message: str
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    data: Dict[str, Any]
    tags: List[str]
    correlation_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            **asdict(self),
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class EventFilter:
    """事件过滤器"""
    event_types: Optional[List[DiagnosticEventType]] = None
    sources: Optional[List[str]] = None
    severities: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    correlation_id: Optional[str] = None
    search_text: Optional[str] = None


class DiagnosticEvents:
    """诊断事件管理器"""
    
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self._events: List[DiagnosticEvent] = []
        self._event_index: Dict[str, int] = {}  # event_id -> index
        self._listeners: List[Callable[[DiagnosticEvent], None]] = []
        self._filters: List[EventFilter] = []
        self._event_counter = 0
        self._start_time = datetime.now()
    
    def add_listener(self, listener: Callable[[DiagnosticEvent], None]):
        """添加事件监听器"""
        self._listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[DiagnosticEvent], None]):
        """移除事件监听器"""
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def add_filter(self, filter_obj: EventFilter):
        """添加事件过滤器"""
        self._filters.append(filter_obj)
    
    def remove_filter(self, filter_obj: EventFilter):
        """移除事件过滤器"""
        if filter_obj in self._filters:
            self._filters.remove(filter_obj)
    
    def emit_event(self, 
                  event_type: DiagnosticEventType,
                  source: str,
                  message: str,
                  severity: str = "INFO",
                  data: Dict[str, Any] = None,
                  tags: List[str] = None,
                  correlation_id: str = None,
                  parent_event_id: str = None) -> str:
        """发出事件"""
        self._event_counter += 1
        event_id = f"evt_{self._event_counter}_{int(time.time() * 1000)}"
        
        event = DiagnosticEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(),
            source=source,
            message=message,
            severity=severity,
            data=data or {},
            tags=tags or [],
            correlation_id=correlation_id,
            parent_event_id=parent_event_id
        )
        
        # 添加到事件列表
        self._events.append(event)
        self._event_index[event_id] = len(self._events) - 1
        
        # 保持事件数量在限制范围内
        if len(self._events) > self.max_events:
            removed_event = self._events.pop(0)
            del self._event_index[removed_event.event_id]
            # 更新索引
            for i, event in enumerate(self._events):
                self._event_index[event.event_id] = i
        
        # 通知监听器
        for listener in self._listeners:
            try:
                listener(event)
            except Exception:
                # 忽略监听器错误
                pass
        
        # 检查过滤器
        for filter_obj in self._filters:
            if self._matches_filter(event, filter_obj):
                try:
                    # 这里可以添加过滤后的处理逻辑
                    pass
                except Exception:
                    pass
        
        return event_id
    
    def _matches_filter(self, event: DiagnosticEvent, filter_obj: EventFilter) -> bool:
        """检查事件是否匹配过滤器"""
        if filter_obj.event_types and event.event_type not in filter_obj.event_types:
            return False
        
        if filter_obj.sources and event.source not in filter_obj.sources:
            return False
        
        if filter_obj.severities and event.severity not in filter_obj.severities:
            return False
        
        if filter_obj.tags:
            if not any(tag in event.tags for tag in filter_obj.tags):
                return False
        
        if filter_obj.start_time and event.timestamp < filter_obj.start_time:
            return False
        
        if filter_obj.end_time and event.timestamp > filter_obj.end_time:
            return False
        
        if filter_obj.correlation_id and event.correlation_id != filter_obj.correlation_id:
            return False
        
        if filter_obj.search_text:
            search_lower = filter_obj.search_text.lower()
            if (search_lower not in event.message.lower() and
                search_lower not in event.source.lower()):
                return False
        
        return True
    
    def get_events(self, 
                  limit: int = 100,
                  offset: int = 0,
                  filter_obj: EventFilter = None) -> List[DiagnosticEvent]:
        """获取事件列表"""
        events = self._events
        
        # 应用过滤器
        if filter_obj:
            events = [event for event in events if self._matches_filter(event, filter_obj)]
        
        # 分页
        return events[offset:offset + limit]
    
    def get_event_by_id(self, event_id: str) -> Optional[DiagnosticEvent]:
        """根据ID获取事件"""
        index = self._event_index.get(event_id)
        if index is not None and index < len(self._events):
            return self._events[index]
        return None
    
    def get_events_by_type(self, event_type: DiagnosticEventType) -> List[DiagnosticEvent]:
        """根据类型获取事件"""
        return [event for event in self._events if event.event_type == event_type]
    
    def get_events_by_source(self, source: str) -> List[DiagnosticEvent]:
        """根据源获取事件"""
        return [event for event in self._events if event.source == source]
    
    def get_events_by_severity(self, severity: str) -> List[DiagnosticEvent]:
        """根据严重程度获取事件"""
        return [event for event in self._events if event.severity == severity]
    
    def get_events_by_correlation(self, correlation_id: str) -> List[DiagnosticEvent]:
        """根据关联ID获取事件"""
        return [event for event in self._events if event.correlation_id == correlation_id]
    
    def get_recent_events(self, minutes: int = 60) -> List[DiagnosticEvent]:
        """获取最近的事件"""
        cutoff_time = datetime.now().timestamp() - (minutes * 60)
        return [event for event in self._events if event.timestamp.timestamp() >= cutoff_time]
    
    def get_error_events(self, hours: int = 24) -> List[DiagnosticEvent]:
        """获取错误事件"""
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        return [
            event for event in self._events 
            if event.severity in ['ERROR', 'CRITICAL'] and 
               event.timestamp.timestamp() >= cutoff_time
        ]
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """获取事件统计信息"""
        now = datetime.now()
        uptime = (now - self._start_time).total_seconds()
        
        # 按类型统计
        type_counts = {}
        for event in self._events:
            event_type = event.event_type.value
            type_counts[event_type] = type_counts.get(event_type, 0) + 1
        
        # 按严重程度统计
        severity_counts = {}
        for event in self._events:
            severity_counts[event.severity] = severity_counts.get(event.severity, 0) + 1
        
        # 按源统计
        source_counts = {}
        for event in self._events:
            source_counts[event.source] = source_counts.get(event.source, 0) + 1
        
        # 最近事件
        recent_events = self.get_recent_events(60)  # 最近1小时
        
        return {
            "total_events": len(self._events),
            "uptime_seconds": uptime,
            "events_per_minute": len(recent_events) / 60 if uptime > 60 else 0,
            "type_counts": type_counts,
            "severity_counts": severity_counts,
            "source_counts": source_counts,
            "active_listeners": len(self._listeners),
            "active_filters": len(self._filters),
            "start_time": self._start_time.isoformat(),
            "last_event_time": self._events[-1].timestamp.isoformat() if self._events else None
        }
    
    def clear_events(self):
        """清空所有事件"""
        self._events.clear()
        self._event_index.clear()
        self._event_counter = 0
    
    def export_events(self, format: str = "json", filter_obj: EventFilter = None) -> str:
        """导出事件"""
        events = self.get_events(filter_obj=filter_obj)
        
        if format.lower() == "json":
            return json.dumps([event.to_dict() for event in events], ensure_ascii=False, indent=2)
        elif format.lower() == "csv":
            # 简单的CSV导出
            if not events:
                return ""
            
            lines = ["event_id,event_type,timestamp,source,severity,message"]
            for event in events:
                lines.append(f"{event.event_id},{event.event_type.value},{event.timestamp.isoformat()},{event.source},{event.severity},\"{event.message}\"")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    # 便捷方法
    def system_startup(self, source: str, data: Dict[str, Any] = None) -> str:
        """系统启动事件"""
        return self.emit_event(
            DiagnosticEventType.SYSTEM_STARTUP,
            source,
            "System startup",
            "INFO",
            data
        )
    
    def system_shutdown(self, source: str, data: Dict[str, Any] = None) -> str:
        """系统关闭事件"""
        return self.emit_event(
            DiagnosticEventType.SYSTEM_SHUTDOWN,
            source,
            "System shutdown",
            "INFO",
            data
        )
    
    def system_error(self, source: str, message: str, data: Dict[str, Any] = None) -> str:
        """系统错误事件"""
        return self.emit_event(
            DiagnosticEventType.SYSTEM_ERROR,
            source,
            message,
            "ERROR",
            data
        )
    
    def cpu_usage_high(self, source: str, usage_percent: float, data: Dict[str, Any] = None) -> str:
        """CPU使用率过高事件"""
        return self.emit_event(
            DiagnosticEventType.CPU_USAGE_HIGH,
            source,
            f"High CPU usage: {usage_percent}%",
            "WARNING",
            {**(data or {}), "usage_percent": usage_percent}
        )
    
    def memory_usage_high(self, source: str, usage_percent: float, data: Dict[str, Any] = None) -> str:
        """内存使用率过高事件"""
        return self.emit_event(
            DiagnosticEventType.MEMORY_USAGE_HIGH,
            source,
            f"High memory usage: {usage_percent}%",
            "WARNING",
            {**(data or {}), "usage_percent": usage_percent}
        )
    
    def process_start(self, source: str, process_name: str, pid: int, data: Dict[str, Any] = None) -> str:
        """进程启动事件"""
        return self.emit_event(
            DiagnosticEventType.PROCESS_START,
            source,
            f"Process started: {process_name} (PID: {pid})",
            "INFO",
            {**(data or {}), "process_name": process_name, "pid": pid}
        )
    
    def process_stop(self, source: str, process_name: str, pid: int, exit_code: int = None, data: Dict[str, Any] = None) -> str:
        """进程停止事件"""
        return self.emit_event(
            DiagnosticEventType.PROCESS_STOP,
            source,
            f"Process stopped: {process_name} (PID: {pid})",
            "INFO",
            {**(data or {}), "process_name": process_name, "pid": pid, "exit_code": exit_code}
        )
    
    def process_error(self, source: str, process_name: str, pid: int, error_message: str, data: Dict[str, Any] = None) -> str:
        """进程错误事件"""
        return self.emit_event(
            DiagnosticEventType.PROCESS_ERROR,
            source,
            f"Process error: {process_name} (PID: {pid}) - {error_message}",
            "ERROR",
            {**(data or {}), "process_name": process_name, "pid": pid, "error": error_message}
        )
    
    def file_operation(self, source: str, operation: str, file_path: str, success: bool = True, data: Dict[str, Any] = None) -> str:
        """文件操作事件"""
        return self.emit_event(
            DiagnosticEventType.FILE_OPERATION,
            source,
            f"File {operation}: {file_path} - {'Success' if success else 'Failed'}",
            "INFO" if success else "WARNING",
            {**(data or {}), "operation": operation, "file_path": file_path, "success": success}
        )
    
    def security_event(self, source: str, event_type: str, details: str, data: Dict[str, Any] = None) -> str:
        """安全事件"""
        return self.emit_event(
            DiagnosticEventType.SECURITY_EVENT,
            source,
            f"Security event: {event_type} - {details}",
            "WARNING",
            {**(data or {}), "security_type": event_type, "details": details},
            tags=["security"]
        )