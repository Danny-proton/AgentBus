"""
监控管理器 - 整合所有监控功能的管理器
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from .diagnostic_events import DiagnosticEvents, DiagnosticEventType, EventFilter
from .system_metrics import SystemMetricsCollector, SystemMetrics, AlertRule
from ..process.process_manager import ProcessManager
from ..net.network import NetworkManager
from ..net.ssrf import SsrFProtection


class MonitoringManager:
    """监控管理器 - 统一管理所有监控功能"""
    
    def __init__(self, ssrf_protection: SsrFProtection = None):
        # 初始化各个监控组件
        self.diagnostic_events = DiagnosticEvents()
        self.system_metrics = SystemMetricsCollector(self.diagnostic_events)
        self.process_manager = ProcessManager()
        self.network_manager = NetworkManager(ssrf_protection)
        self.ssrf_protection = ssrf_protection
        
        # 监控状态
        self._monitoring_active = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # 监听器
        self._event_listeners: List[Callable] = []
        self._metrics_listeners: List[Callable] = []
        
        # 整合监听器
        self._setup_integrated_listeners()
        
        # 设置默认告警
        self.system_metrics.setup_default_alerts()
    
    def _setup_integrated_listeners(self):
        """设置整合监听器"""
        # 系统指标监听器
        def on_system_metrics(metrics: SystemMetrics):
            # 当系统指标达到告警阈值时发出事件
            if metrics.cpu_percent > 80:
                self.diagnostic_events.cpu_usage_high(
                    source="monitoring_manager",
                    usage_percent=metrics.cpu_percent,
                    data={"memory_percent": metrics.memory_percent}
                )
            
            if metrics.memory_percent > 85:
                self.diagnostic_events.memory_usage_high(
                    source="monitoring_manager",
                    usage_percent=metrics.memory_percent,
                    data={"cpu_percent": metrics.cpu_percent}
                )
        
        self.system_metrics.add_metrics_callback(on_system_metrics)
        
        # 告警监听器
        def on_alert(event_type: str, alert_info: Dict[str, Any]):
            if event_type == "triggered":
                self.diagnostic_events.system_error(
                    source="monitoring_manager",
                    message=f"System alert: {alert_info['rule_name']}",
                    data=alert_info,
                    severity=alert_info['severity']
                )
            elif event_type == "resolved":
                self.diagnostic_events.emit_event(
                    DiagnosticEventType.SYSTEM_INFO,
                    source="monitoring_manager",
                    message=f"Alert resolved: {alert_info['rule_name']}",
                    data=alert_info
                )
        
        self.system_metrics.add_alert_callback(on_alert)
    
    async def start_monitoring(self, 
                             metrics_interval: float = 5.0,
                             process_monitoring: bool = True,
                             network_monitoring: bool = True):
        """开始监控"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        
        # 发出启动事件
        self.diagnostic_events.system_startup(
            source="monitoring_manager",
            data={
                "metrics_interval": metrics_interval,
                "process_monitoring": process_monitoring,
                "network_monitoring": network_monitoring
            }
        )
        
        # 启动各个监控组件
        tasks = []
        
        # 系统指标监控
        tasks.append(asyncio.create_task(
            self.system_metrics.start_collection(metrics_interval)
        ))
        
        # 进程监控
        if process_monitoring:
            tasks.append(asyncio.create_task(
                self.process_manager.start_monitoring(interval=metrics_interval)
            ))
        
        # 网络监控
        if network_monitoring:
            tasks.append(asyncio.create_task(
                self.network_manager.start_monitoring(interval=metrics_interval)
            ))
        
        # 统一监控循环
        self._monitor_task = asyncio.create_task(
            self._monitoring_loop()
        )
        
        # 等待所有任务启动
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop_monitoring(self):
        """停止监控"""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        
        # 停止各个监控组件
        await self.system_metrics.stop_collection()
        await self.process_manager.stop_monitoring()
        await self.network_manager.stop_monitoring()
        
        # 停止统一监控循环
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        
        # 发出关闭事件
        self.diagnostic_events.system_shutdown(
            source="monitoring_manager"
        )
    
    async def _monitoring_loop(self):
        """统一监控循环"""
        while self._monitoring_active:
            try:
                await asyncio.sleep(60)  # 每分钟执行一次综合检查
                
                # 综合健康检查
                await self._perform_health_check()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.diagnostic_events.system_error(
                    source="monitoring_manager",
                    message=f"Error in monitoring loop: {str(e)}",
                    data={"error": str(e)}
                )
    
    async def _perform_health_check(self):
        """执行健康检查"""
        try:
            # 获取当前系统指标
            current_metrics = self.system_metrics.get_current_metrics()
            if not current_metrics:
                return
            
            # 检查系统健康状况
            health_issues = []
            
            # CPU使用率检查
            if current_metrics.cpu_percent > 90:
                health_issues.append(f"High CPU usage: {current_metrics.cpu_percent:.1f}%")
            
            # 内存使用率检查
            if current_metrics.memory_percent > 95:
                health_issues.append(f"High memory usage: {current_metrics.memory_percent:.1f}%")
            
            # 磁盘使用率检查
            if current_metrics.disk_percent > 95:
                health_issues.append(f"High disk usage: {current_metrics.disk_percent:.1f}%")
            
            # 活跃告警检查
            active_alerts = self.system_metrics.get_active_alerts()
            if active_alerts:
                health_issues.append(f"Active alerts: {len(active_alerts)}")
            
            # 如果有问题，发出警告
            if health_issues:
                self.diagnostic_events.emit_event(
                    DiagnosticEventType.SYSTEM_WARNING,
                    source="monitoring_manager",
                    message="System health issues detected",
                    severity="WARNING",
                    data={"issues": health_issues}
                )
            else:
                # 系统健康，发出正常事件
                self.diagnostic_events.emit_event(
                    DiagnosticEventType.SYSTEM_INFO,
                    source="monitoring_manager",
                    message="System health check passed",
                    severity="INFO",
                    data={"metrics": {
                        "cpu_percent": current_metrics.cpu_percent,
                        "memory_percent": current_metrics.memory_percent,
                        "disk_percent": current_metrics.disk_percent
                    }}
                )
                
        except Exception as e:
            self.diagnostic_events.system_error(
                source="monitoring_manager",
                message=f"Health check failed: {str(e)}",
                data={"error": str(e)}
            )
    
    def add_event_listener(self, listener: Callable):
        """添加事件监听器"""
        self.diagnostic_events.add_listener(listener)
        self._event_listeners.append(listener)
    
    def remove_event_listener(self, listener: Callable):
        """移除事件监听器"""
        self.diagnostic_events.remove_listener(listener)
        if listener in self._event_listeners:
            self._event_listeners.remove(listener)
    
    def add_metrics_listener(self, listener: Callable):
        """添加指标监听器"""
        self.system_metrics.add_metrics_callback(listener)
        self._metrics_listeners.append(listener)
    
    def remove_metrics_listener(self, listener: Callable):
        """移除指标监听器"""
        self.system_metrics.remove_metrics_callback(listener)
        if listener in self._metrics_listeners:
            self._metrics_listeners.remove(listener)
    
    def add_alert_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.system_metrics.add_alert_rule(rule)
    
    def remove_alert_rule(self, rule_name: str):
        """移除告警规则"""
        self.system_metrics.remove_alert_rule(rule_name)
    
    def get_alert_rules(self) -> List[AlertRule]:
        """获取告警规则"""
        return self.system_metrics.get_alert_rules()
    
    def get_active_alerts(self) -> Dict[str, Any]:
        """获取活跃告警"""
        return self.system_metrics.get_active_alerts()
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """获取当前系统指标"""
        return self.system_metrics.get_current_metrics()
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        metrics_stats = self.system_metrics.get_metrics_statistics()
        
        return {
            "monitoring_active": self._monitoring_active,
            "system_metrics": metrics_stats,
            "process_manager": {
                "monitoring_active": self.process_manager._monitoring_active,
                "tracked_processes": len(self.process_manager._metrics_history)
            },
            "network_manager": {
                "monitoring_active": self.network_manager._monitoring_active,
                "metrics_history": len(self.network_manager._metrics_history)
            },
            "diagnostic_events": self.diagnostic_events.get_event_statistics(),
            "active_alerts": len(self.get_active_alerts())
        }
    
    def get_events(self, limit: int = 100, filter_obj: EventFilter = None) -> List:
        """获取诊断事件"""
        return self.diagnostic_events.get_events(limit=limit, filter_obj=filter_obj)
    
    def get_recent_errors(self, hours: int = 24) -> List:
        """获取最近的错误事件"""
        return self.diagnostic_events.get_error_events(hours=hours)
    
    def emit_custom_event(self, event_type: DiagnosticEventType, source: str,
                        message: str, severity: str = "INFO",
                        data: Dict[str, Any] = None, tags: List[str] = None):
        """发出自定义事件"""
        return self.diagnostic_events.emit_event(
            event_type=event_type,
            source=source,
            message=message,
            severity=severity,
            data=data,
            tags=tags
        )
    
    def export_monitoring_data(self, format: str = "json", limit: int = 1000) -> str:
        """导出监控数据"""
        if format.lower() == "json":
            import json
            
            data = {
                "system_metrics": self.system_metrics.export_metrics(format="json", limit=limit),
                "diagnostic_events": self.diagnostic_events.export_events(format="json"),
                "statistics": self.get_system_statistics(),
                "active_alerts": self.get_active_alerts(),
                "alert_rules": [rule.__dict__ for rule in self.get_alert_rules()]
            }
            
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def perform_diagnostic_scan(self) -> Dict[str, Any]:
        """执行诊断扫描"""
        scan_results = {
            "timestamp": asyncio.get_event_loop().time(),
            "scan_results": {}
        }
        
        try:
            # 系统指标
            scan_results["scan_results"]["system_metrics"] = await self.system_metrics.collect_metrics().__anext__()
        except Exception as e:
            scan_results["scan_results"]["system_metrics"] = {"error": str(e)}
        
        try:
            # 活跃连接
            scan_results["scan_results"]["network_connections"] = await self.network_manager.get_active_connections()
        except Exception as e:
            scan_results["scan_results"]["network_connections"] = {"error": str(e)}
        
        try:
            # 网络接口
            scan_results["scan_results"]["network_interfaces"] = await self.network_manager.get_network_interfaces()
        except Exception as e:
            scan_results["scan_results"]["network_interfaces"] = {"error": str(e)}
        
        try:
            # 进程信息
            scan_results["scan_results"]["processes"] = await self.process_manager.list_processes(limit=50)
        except Exception as e:
            scan_results["scan_results"]["processes"] = {"error": str(e)}
        
        try:
            # 系统资源
            scan_results["scan_results"]["system_resources"] = await self.process_manager.get_system_resources()
        except Exception as e:
            scan_results["scan_results"]["system_resources"] = {"error": str(e)}
        
        # 发出扫描完成事件
        self.emit_custom_event(
            DiagnosticEventType.SYSTEM_INFO,
            "monitoring_manager",
            "Diagnostic scan completed",
            data=scan_results
        )
        
        return scan_results