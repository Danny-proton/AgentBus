"""
系统指标模块 - 提供系统性能指标收集和监控功能
"""

import asyncio
import psutil
import platform
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from .diagnostic_events import DiagnosticEvents, DiagnosticEventType


@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: datetime
    cpu_percent: float
    cpu_count: int
    memory_total: int
    memory_available: int
    memory_percent: float
    disk_total: int
    disk_used: int
    disk_free: int
    disk_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    thread_count: int
    load_average: List[float]
    boot_time: datetime
    uptime_seconds: float


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    metric: str
    operator: str  # >, <, >=, <=, ==
    threshold: float
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    enabled: bool = True
    duration_seconds: int = 0  # 持续时间（秒）
    
    def evaluate(self, value: float, duration: float = 0) -> bool:
        """评估告警条件"""
        if not self.enabled:
            return False
        
        if duration < self.duration_seconds:
            return False
        
        if self.operator == ">" and value > self.threshold:
            return True
        elif self.operator == "<" and value < self.threshold:
            return True
        elif self.operator == ">=" and value >= self.threshold:
            return True
        elif self.operator == "<=" and value <= self.threshold:
            return True
        elif self.operator == "==" and abs(value - self.threshold) < 0.001:
            return True
        
        return False


class SystemMetricsCollector:
    """系统指标收集器"""
    
    def __init__(self, diagnostic_events: DiagnosticEvents = None):
        self.diagnostic_events = diagnostic_events or DiagnosticEvents()
        self._metrics_history: List[SystemMetrics] = []
        self._alert_rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Dict[str, Any]] = {}
        self._collection_active = False
        self._collection_task: Optional[asyncio.Task] = None
        self._metrics_callbacks: List[Callable[[SystemMetrics], None]] = []
        self._alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
    
    def add_metrics_callback(self, callback: Callable[[SystemMetrics], None]):
        """添加指标回调"""
        self._metrics_callbacks.append(callback)
    
    def remove_metrics_callback(self, callback: Callable[[SystemMetrics], None]):
        """移除指标回调"""
        if callback in self._metrics_callbacks:
            self._metrics_callbacks.remove(callback)
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """添加告警回调"""
        self._alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """移除告警回调"""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
    
    def add_alert_rule(self, rule: AlertRule):
        """添加告警规则"""
        self._alert_rules[rule.name] = rule
    
    def remove_alert_rule(self, rule_name: str):
        """移除告警规则"""
        if rule_name in self._alert_rules:
            del self._alert_rules[rule_name]
    
    def get_alert_rules(self) -> List[AlertRule]:
        """获取告警规则"""
        return list(self._alert_rules.values())
    
    async def collect_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            # CPU指标
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            
            # 内存指标
            memory = psutil.virtual_memory()
            memory_total = memory.total
            memory_available = memory.available
            memory_percent = memory.percent
            
            # 磁盘指标
            disk = psutil.disk_usage('/')
            disk_total = disk.total
            disk_used = disk.used
            disk_free = disk.free
            disk_percent = (disk.used / disk.total) * 100
            
            # 网络指标
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv
            
            # 进程指标
            process_count = len(psutil.pids())
            thread_count = sum(
                p.num_threads() for p in psutil.process_iter(['num_threads']) 
                if p.info['num_threads'] is not None
            )
            
            # 负载平均值（仅Linux/macOS）
            load_average = []
            try:
                load_average = list(psutil.getloadavg())
            except AttributeError:
                load_average = [0.0, 0.0, 0.0]
            
            # 启动时间和运行时间
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime_seconds = (datetime.now() - boot_time).total_seconds()
            
            metrics = SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                cpu_count=cpu_count,
                memory_total=memory_total,
                memory_available=memory_available,
                memory_percent=memory_percent,
                disk_total=disk_total,
                disk_used=disk_used,
                disk_free=disk_free,
                disk_percent=disk_percent,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv,
                process_count=process_count,
                thread_count=thread_count,
                load_average=load_average,
                boot_time=boot_time,
                uptime_seconds=uptime_seconds
            )
            
            # 存储历史数据
            self._metrics_history.append(metrics)
            
            # 保持历史数据在合理范围内
            if len(self._metrics_history) > 10000:
                self._metrics_history = self._metrics_history[-5000:]
            
            return metrics
            
        except Exception as e:
            # 发出错误事件
            self.diagnostic_events.system_error(
                source="system_metrics",
                message=f"Failed to collect system metrics: {str(e)}",
                data={"error": str(e)}
            )
            raise
    
    async def start_collection(self, interval: float = 5.0):
        """开始指标收集"""
        if self._collection_active:
            return
        
        self._collection_active = True
        self._collection_task = asyncio.create_task(
            self._collection_loop(interval)
        )
        
        self.diagnostic_events.system_startup(
            source="system_metrics",
            data={"interval": interval}
        )
    
    async def stop_collection(self):
        """停止指标收集"""
        self._collection_active = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
            self._collection_task = None
        
        self.diagnostic_events.system_shutdown(
            source="system_metrics"
        )
    
    async def _collection_loop(self, interval: float):
        """指标收集循环"""
        while self._collection_active:
            try:
                await asyncio.sleep(interval)
                
                # 收集指标
                metrics = await self.collect_metrics()
                
                # 通知回调
                for callback in self._metrics_callbacks:
                    try:
                        callback(metrics)
                    except Exception:
                        pass
                
                # 检查告警
                await self._check_alerts(metrics)
                
            except asyncio.CancelledError:
                break
            except Exception:
                # 记录错误但继续
                pass
    
    async def _check_alerts(self, metrics: SystemMetrics):
        """检查告警条件"""
        current_time = time.time()
        
        for rule_name, rule in self._alert_rules.items():
            try:
                # 获取指标值
                if rule.metric == "cpu_percent":
                    value = metrics.cpu_percent
                elif rule.metric == "memory_percent":
                    value = metrics.memory_percent
                elif rule.metric == "disk_percent":
                    value = metrics.disk_percent
                elif rule.metric == "process_count":
                    value = float(metrics.process_count)
                elif rule.metric == "thread_count":
                    value = float(metrics.thread_count)
                else:
                    continue
                
                # 检查是否触发告警
                triggered = rule.evaluate(value)
                
                if triggered:
                    if rule_name not in self._active_alerts:
                        # 新的告警
                        alert_info = {
                            "rule_name": rule_name,
                            "metric": rule.metric,
                            "value": value,
                            "threshold": rule.threshold,
                            "operator": rule.operator,
                            "severity": rule.severity,
                            "first_triggered": current_time,
                            "last_triggered": current_time,
                            "trigger_count": 1
                        }
                        self._active_alerts[rule_name] = alert_info
                        
                        # 发出告警事件
                        await self._trigger_alert(alert_info)
                    else:
                        # 更新现有告警
                        alert_info = self._active_alerts[rule_name]
                        alert_info["last_triggered"] = current_time
                        alert_info["trigger_count"] += 1
                        alert_info["value"] = value
                else:
                    # 告警条件不再满足，清除告警
                    if rule_name in self._active_alerts:
                        del self._active_alerts[rule_name]
                        
                        # 发出告警恢复事件
                        await self._resolve_alert(rule_name, metrics)
                        
            except Exception:
                continue
    
    async def _trigger_alert(self, alert_info: Dict[str, Any]):
        """触发告警"""
        # 发出诊断事件
        self.diagnostic_events.emit_event(
            DiagnosticEventType.SYSTEM_WARNING,
            source="system_metrics",
            message=f"Alert triggered: {alert_info['rule_name']} - {alert_info['metric']} {alert_info['operator']} {alert_info['threshold']} (current: {alert_info['value']:.2f})",
            severity=alert_info['severity'],
            data=alert_info,
            tags=["alert", alert_info['severity'].lower()]
        )
        
        # 通知回调
        for callback in self._alert_callbacks:
            try:
                callback("triggered", alert_info)
            except Exception:
                pass
    
    async def _resolve_alert(self, rule_name: str, metrics: SystemMetrics):
        """告警恢复"""
        # 发出诊断事件
        self.diagnostic_events.emit_event(
            DiagnosticEventType.SYSTEM_INFO,
            source="system_metrics",
            message=f"Alert resolved: {rule_name}",
            severity="INFO",
            data={"rule_name": rule_name},
            tags=["alert_resolved"]
        )
        
        # 通知回调
        for callback in self._alert_callbacks:
            try:
                callback("resolved", {"rule_name": rule_name})
            except Exception:
                pass
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """获取最新指标"""
        return self._metrics_history[-1] if self._metrics_history else None
    
    def get_metrics_history(self, limit: int = 100) -> List[SystemMetrics]:
        """获取指标历史"""
        return self._metrics_history[-limit:]
    
    def get_active_alerts(self) -> Dict[str, Dict[str, Any]]:
        """获取活跃告警"""
        return self._active_alerts.copy()
    
    def get_metrics_statistics(self) -> Dict[str, Any]:
        """获取指标统计信息"""
        if not self._metrics_history:
            return {}
        
        recent_metrics = self._metrics_history[-100:]  # 最近100条记录
        
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        disk_values = [m.disk_percent for m in recent_metrics]
        
        return {
            "total_samples": len(self._metrics_history),
            "cpu": {
                "current": cpu_values[-1],
                "min": min(cpu_values),
                "max": max(cpu_values),
                "avg": sum(cpu_values) / len(cpu_values)
            },
            "memory": {
                "current": memory_values[-1],
                "min": min(memory_values),
                "max": max(memory_values),
                "avg": sum(memory_values) / len(memory_values)
            },
            "disk": {
                "current": disk_values[-1],
                "min": min(disk_values),
                "max": max(disk_values),
                "avg": sum(disk_values) / len(disk_values)
            },
            "active_alerts": len(self._active_alerts),
            "collection_active": self._collection_active,
            "rules_count": len(self._alert_rules)
        }
    
    def export_metrics(self, format: str = "json", limit: int = 1000) -> str:
        """导出指标数据"""
        data = [asdict(metric) for metric in self._metrics_history[-limit:]]
        
        # 转换datetime对象为字符串
        for item in data:
            item['timestamp'] = item['timestamp'].isoformat()
            item['boot_time'] = item['boot_time'].isoformat()
        
        if format.lower() == "json":
            import json
            return json.dumps(data, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def setup_default_alerts(self):
        """设置默认告警规则"""
        # CPU使用率告警
        self.add_alert_rule(AlertRule(
            name="high_cpu",
            metric="cpu_percent",
            operator=">",
            threshold=80.0,
            severity="WARNING",
            duration_seconds=60
        ))
        
        # 内存使用率告警
        self.add_alert_rule(AlertRule(
            name="high_memory",
            metric="memory_percent",
            operator=">",
            threshold=85.0,
            severity="WARNING",
            duration_seconds=60
        ))
        
        # 磁盘使用率告警
        self.add_alert_rule(AlertRule(
            name="high_disk",
            metric="disk_percent",
            operator=">",
            threshold=90.0,
            severity="CRITICAL",
            duration_seconds=30
        ))
        
        # 进程数量告警
        self.add_alert_rule(AlertRule(
            name="too_many_processes",
            metric="process_count",
            operator=">",
            threshold=1000.0,
            severity="WARNING",
            duration_seconds=120
        ))