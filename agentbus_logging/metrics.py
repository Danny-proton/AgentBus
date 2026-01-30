"""
AgentBus性能指标监控系统

提供系统指标收集、应用指标监控和性能分析功能
"""

import os
import psutil
import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
from enum import Enum
import queue
from pathlib import Path
import statistics


class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"          # 计数器
    GAUGE = "gauge"             # 仪表盘
    HISTOGRAM = "histogram"     # 直方图
    TIMER = "timer"             # 计时器


@dataclass
class Metric:
    """指标数据类"""
    name: str
    type: MetricType
    value: Union[int, float]
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class SystemMetrics:
    """系统指标"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    thread_count: int
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApplicationMetrics:
    """应用指标"""
    # 请求相关
    requests_total: int = 0
    requests_errors: int = 0
    response_time_avg: float = 0.0
    response_time_p95: float = 0.0
    response_time_p99: float = 0.0
    
    # 错误相关
    errors_total: int = 0
    warnings_total: int = 0
    
    # 资源相关
    active_connections: int = 0
    queued_tasks: int = 0
    processing_tasks: int = 0
    
    # 自定义指标
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, collection_interval: float = 1.0):
        self.collection_interval = collection_interval
        self.metrics: Dict[str, Metric] = {}
        self.system_history: deque = deque(maxlen=3600)  # 保存1小时数据
        self.app_history: deque = deque(maxlen=3600)
        self.response_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = threading.Lock()
        self._running = False
        self._collection_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[Dict[str, Metric]], None]] = []
        
    def start_collection(self) -> None:
        """开始指标收集"""
        with self._lock:
            if not self._running:
                self._running = True
                self._collection_thread = threading.Thread(
                    target=self._collection_loop,
                    daemon=True,
                    name="MetricsCollector"
                )
                self._collection_thread.start()
                
    def stop_collection(self) -> None:
        """停止指标收集"""
        with self._lock:
            self._running = False
            if self._collection_thread:
                self._collection_thread.join(timeout=5)
                
    def register_metric(self, metric: Metric) -> None:
        """注册指标"""
        with self._lock:
            self.metrics[metric.name] = metric
            
    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """增加计数器"""
        with self._lock:
            key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
            if key not in self.metrics:
                self.metrics[key] = Metric(name, MetricType.COUNTER, 0, labels or {})
            self.metrics[key].value += value
            self.metrics[key].timestamp = datetime.utcnow().isoformat()
            
    def set_gauge(self, name: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None) -> None:
        """设置仪表盘值"""
        with self._lock:
            key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
            if key not in self.metrics:
                self.metrics[key] = Metric(name, MetricType.GAUGE, value, labels or {})
            self.metrics[key].value = value
            self.metrics[key].timestamp = datetime.utcnow().isoformat()
            
    def record_timer(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None) -> None:
        """记录计时器"""
        with self._lock:
            # 更新统计信息
            response_times = self.response_times[name]
            response_times.append(duration)
            
            # 更新指标
            key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
            self.metrics[key] = Metric(
                name=name,
                type=MetricType.TIMER,
                value=duration,
                labels=labels or {},
                timestamp=datetime.utcnow().isoformat()
            )
            
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """记录直方图"""
        with self._lock:
            key = f"{name}:{json.dumps(labels or {}, sort_keys=True)}"
            self.metrics[key] = Metric(
                name=name,
                type=MetricType.HISTOGRAM,
                value=value,
                labels=labels or {},
                timestamp=datetime.utcnow().isoformat()
            )
            
    def get_system_metrics(self) -> SystemMetrics:
        """获取系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 内存信息
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 网络信息
            network = psutil.net_io_counters()
            
            # 进程信息
            process = psutil.Process()
            process_count = len(psutil.pids())
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / 1024 / 1024,
                memory_available_mb=memory.available / 1024 / 1024,
                disk_usage_percent=disk.percent,
                disk_free_gb=disk.free / 1024 / 1024 / 1024,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                process_count=process_count,
                thread_count=process.num_threads(),
            )
        except Exception:
            # 返回默认值
            return SystemMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                network_bytes_sent=0,
                network_bytes_recv=0,
                process_count=0,
                thread_count=0,
            )
            
    def get_application_metrics(self) -> ApplicationMetrics:
        """获取应用指标"""
        # 这里可以根据实际应用情况调整
        metrics = ApplicationMetrics()
        
        # 从注册的指标中提取应用指标
        for metric in self.metrics.values():
            if metric.name == "requests_total":
                metrics.requests_total = int(metric.value)
            elif metric.name == "requests_errors":
                metrics.requests_errors = int(metric.value)
            elif metric.name == "response_time_avg":
                metrics.response_time_avg = float(metric.value)
            elif metric.name == "active_connections":
                metrics.active_connections = int(metric.value)
                
        return metrics
        
    def get_response_time_stats(self, name: str) -> Dict[str, float]:
        """获取响应时间统计"""
        response_times = self.response_times.get(name, deque())
        if not response_times:
            return {"avg": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0}
            
        values = list(response_times)
        return {
            "avg": statistics.mean(values),
            "p50": statistics.median(values),
            "p95": self._percentile(values, 95),
            "p99": self._percentile(values, 99),
            "min": min(values),
            "max": max(values)
        }
        
    def _percentile(self, data: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        return sorted_data[index]
        
    def _collection_loop(self) -> None:
        """指标收集循环"""
        while self._running:
            try:
                # 收集系统指标
                sys_metrics = self.get_system_metrics()
                self.system_history.append(sys_metrics)
                
                # 收集应用指标
                app_metrics = self.get_application_metrics()
                self.app_history.append(app_metrics)
                
                # 触发回调
                self._trigger_callbacks()
                
                time.sleep(self.collection_interval)
                
            except Exception as e:
                print(f"Metrics collection error: {e}")
                time.sleep(self.collection_interval)
                
    def _trigger_callbacks(self) -> None:
        """触发注册的回调函数"""
        try:
            metrics_dict = {name: metric.to_dict() for name, metric in self.metrics.items()}
            for callback in self._callbacks:
                callback(metrics_dict)
        except Exception as e:
            print(f"Metrics callback error: {e}")
            
    def register_callback(self, callback: Callable[[Dict[str, Metric]], None]) -> None:
        """注册指标更新回调"""
        self._callbacks.append(callback)
        
    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """获取指标快照"""
        with self._lock:
            return {
                "system": self.get_system_metrics().to_dict(),
                "application": self.get_application_metrics().to_dict(),
                "custom_metrics": {name: metric.to_dict() for name, metric in self.metrics.items()},
                "response_time_stats": {
                    name: self.get_response_time_stats(name)
                    for name in self.response_times.keys()
                }
            }
            
    def export_metrics(self, format_type: str = "json") -> str:
        """导出指标数据"""
        snapshot = self.get_metrics_snapshot()
        
        if format_type == "json":
            return json.dumps(snapshot, indent=2, ensure_ascii=False)
        elif format_type == "prometheus":
            # Prometheus格式
            lines = []
            for name, metric in self.metrics.items():
                labels_str = ""
                if metric.labels:
                    label_parts = [f'{k}="{v}"' for k, v in metric.labels.items()]
                    labels_str = "{" + ",".join(label_parts) + "}"
                lines.append(f"{metric.name}{labels_str} {metric.value}")
            return "\n".join(lines)
        else:
            return str(snapshot)
            
    def save_metrics_to_file(self, file_path: str, format_type: str = "json") -> None:
        """保存指标到文件"""
        data = self.export_metrics(format_type)
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(data)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self._active_timers: Dict[str, float] = {}
        
    def start_timer(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """开始计时"""
        timer_id = f"{name}:{time.time()}:{threading.get_ident()}"
        self._active_timers[timer_id] = time.time()
        return timer_id
        
    def stop_timer(self, timer_id: str, labels: Optional[Dict[str, str]] = None) -> float:
        """停止计时并记录"""
        if timer_id not in self._active_timers:
            return 0.0
            
        duration = time.time() - self._active_timers[timer_id]
        del self._active_timers[timer_id]
        
        # 从timer_id中提取名称
        name = timer_id.split(':')[0]
        self.metrics.record_timer(name, duration, labels)
        
        return duration
        
    def track_request(self, name: str, labels: Optional[Dict[str, str]] = None):
        """请求跟踪装饰器"""
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                timer_id = self.start_timer(f"{name}_duration", labels)
                try:
                    result = func(*args, **kwargs)
                    self.metrics.increment_counter(f"{name}_success", 1, labels)
                    return result
                except Exception as e:
                    self.metrics.increment_counter(f"{name}_error", 1, labels)
                    raise
                finally:
                    self.stop_timer(timer_id, labels)
            return wrapper
        return decorator
        
    def monitor_resource_usage(self, name: str, interval: float = 1.0):
        """资源使用监控装饰器"""
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                # 开始监控
                process = psutil.Process()
                start_cpu = process.cpu_percent()
                start_memory = process.memory_info().rss
                
                timer_id = self.start_timer(f"{name}_execution", {"resource": "execution"})
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = self.stop_timer(timer_id)
                    
                    # 记录资源使用情况
                    end_cpu = process.cpu_percent()
                    end_memory = process.memory_info().rss
                    
                    self.metrics.record_histogram(f"{name}_cpu_usage", end_cpu)
                    self.metrics.record_histogram(f"{name}_memory_usage", end_memory - start_memory)
                    
            return wrapper
        return decorator


# 全局指标收集器实例
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def create_performance_monitor() -> PerformanceMonitor:
    """创建性能监控器"""
    return PerformanceMonitor(get_metrics_collector())


# 便捷函数
def increment_metric(name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
    """增加指标值"""
    get_metrics_collector().increment_counter(name, value, labels)


def set_metric(name: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None) -> None:
    """设置指标值"""
    get_metrics_collector().set_gauge(name, value, labels)


def record_time(name: str, duration: float, labels: Optional[Dict[str, str]] = None) -> None:
    """记录时间"""
    get_metrics_collector().record_timer(name, duration, labels)


def record_value(name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
    """记录值"""
    get_metrics_collector().record_histogram(name, value, labels)