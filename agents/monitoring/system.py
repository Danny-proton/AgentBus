"""
AgentBus Monitoring System
Agent状态监控系统
"""

from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import asyncio
import uuid
import json
import psutil
import statistics
from collections import defaultdict, deque

from ..core.types import (
    AgentStatus, AgentState, HealthStatus, AlertLevel, AgentHealth,
    SystemMetrics, AgentMetrics, MessageType, Priority, AgentMessage
)


class MonitoringSystem:
    """监控系统"""
    
    def __init__(self, system_id: str = "default"):
        self.system_id = system_id
        self.logger = self._get_logger()
        
        # 监控目标
        self.monitored_agents: Dict[str, 'AgentMonitor'] = {}
        self.system_monitors: List['SystemMonitor'] = []
        
        # 告警管理
        self.alert_rules: List['AlertRule'] = []
        self.active_alerts: Dict[str, 'Alert'] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_handlers: Dict[AlertLevel, List[Callable]] = defaultdict(list)
        
        # 指标存储
        self.metrics_store = MetricsStore()
        self.retention_policy = {
            "detailed": timedelta(hours=24),    # 详细指标保留24小时
            "aggregated": timedelta(days=30),    # 聚合指标保留30天
            "alerts": timedelta(days=90)         # 告警保留90天
        }
        
        # 监控配置
        self.monitoring_enabled = True
        self.collection_interval = 10  # 秒
        self.heartbeat_timeout = 30    # 秒
        self.alert_cooldown = 300      # 5分钟
        
        # 运行状态
        self.running = False
        self.monitoring_tasks: List[asyncio.Task] = []
        
        # 统计信息
        self.stats = {
            "total_collections": 0,
            "total_alerts": 0,
            "critical_alerts": 0,
            "monitored_agents": 0,
            "system_uptime": 0
        }
        
        # 初始化默认监控器
        self._initialize_default_monitors()
    
    def _get_logger(self):
        """获取日志记录器"""
        return f"monitoring.system.{self.system_id}"
    
    def _initialize_default_monitors(self):
        """初始化默认监控器"""
        # 系统资源监控
        self.add_system_monitor(SystemResourceMonitor())
        
        # Agent健康监控
        self.add_system_monitor(AgentHealthMonitor())
        
        # 网络监控
        self.add_system_monitor(NetworkMonitor())
        
        # 存储监控
        self.add_system_monitor(StorageMonitor())
    
    async def start(self):
        """启动监控系统"""
        if self.running:
            return
        
        self.running = True
        
        # 启动监控任务
        self.monitoring_tasks.extend([
            asyncio.create_task(self._collection_loop()),
            asyncio.create_task(self._alert_processing_loop()),
            asyncio.create_task(self._cleanup_loop()),
            asyncio.create_task(self._heartbeat_monitor_loop())
        ])
        
        self.logger.info("Monitoring system started")
    
    async def stop(self):
        """停止监控系统"""
        if not self.running:
            return
        
        self.running = False
        
        # 取消所有监控任务
        for task in self.monitoring_tasks:
            task.cancel()
        
        # 等待任务完成
        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        self.monitoring_tasks.clear()
        self.logger.info("Monitoring system stopped")
    
    def register_agent(self, agent_id: str, agent_instance: Any) -> bool:
        """注册Agent监控"""
        try:
            if agent_id in self.monitored_agents:
                self.logger.warning(f"Agent {agent_id} already registered")
                return False
            
            monitor = AgentMonitor(agent_id, agent_instance)
            self.monitored_agents[agent_id] = monitor
            
            self.stats["monitored_agents"] = len(self.monitored_agents)
            
            self.logger.info(f"Agent {agent_id} registered for monitoring")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_id}: {e}")
            return False
    
    def unregister_agent(self, agent_id: str):
        """注销Agent监控"""
        if agent_id in self.monitored_agents:
            del self.monitored_agents[agent_id]
            self.stats["monitored_agents"] = len(self.monitored_agents)
            self.logger.info(f"Agent {agent_id} unregistered from monitoring")
    
    def add_system_monitor(self, monitor: 'SystemMonitor'):
        """添加系统监控器"""
        self.system_monitors.append(monitor)
        self.logger.info(f"System monitor added: {monitor.name}")
    
    def add_alert_rule(self, rule: 'AlertRule'):
        """添加告警规则"""
        self.alert_rules.append(rule)
        self.logger.info(f"Alert rule added: {rule.name}")
    
    def add_alert_handler(self, level: AlertLevel, handler: Callable):
        """添加告警处理器"""
        self.alert_handlers[level].append(handler)
    
    async def collect_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        metrics = SystemMetrics()
        
        # 收集系统资源指标
        for monitor in self.system_monitors:
            try:
                if asyncio.iscoroutinefunction(monitor.collect):
                    monitor_metrics = await monitor.collect()
                else:
                    monitor_metrics = monitor.collect()
                
                # 合并指标
                metrics = self._merge_metrics(metrics, monitor_metrics)
                
            except Exception as e:
                self.logger.error(f"Monitor {monitor.name} collection failed: {e}")
        
        # 收集Agent指标
        agent_metrics = await self._collect_agent_metrics()
        metrics.total_agents = len(self.monitored_agents)
        metrics.active_agents = len([a for a in agent_metrics.values() if a.get('status') == 'active'])
        metrics.idle_agents = len([a for a in agent_metrics.values() if a.get('status') == 'idle'])
        metrics.busy_agents = len([a for a in agent_metrics.values() if a.get('status') == 'busy'])
        metrics.error_agents = len([a for a in agent_metrics.values() if a.get('status') == 'error'])
        
        # 统计请求信息
        total_requests = sum(a.get('total_requests', 0) for a in agent_metrics.values())
        successful_requests = sum(a.get('successful_requests', 0) for a in agent_metrics.values())
        failed_requests = sum(a.get('failed_requests', 0) for a in agent_metrics.values())
        
        metrics.total_requests = total_requests
        metrics.successful_requests = successful_requests
        metrics.failed_requests = failed_requests
        
        # 存储指标
        self.metrics_store.store_system_metrics(metrics)
        
        # 更新统计
        self.stats["total_collections"] += 1
        
        return metrics
    
    async def _collect_agent_metrics(self) -> Dict[str, Dict[str, Any]]:
        """收集Agent指标"""
        agent_metrics = {}
        
        for agent_id, monitor in self.monitored_agents.items():
            try:
                # 收集Agent指标
                if asyncio.iscoroutinefunction(monitor.collect_metrics):
                    metrics = await monitor.collect_metrics()
                else:
                    metrics = monitor.collect_metrics()
                
                agent_metrics[agent_id] = metrics
                
                # 评估告警规则
                await self._evaluate_alert_rules(agent_id, metrics)
                
            except Exception as e:
                self.logger.error(f"Failed to collect metrics for agent {agent_id}: {e}")
                agent_metrics[agent_id] = {"error": str(e)}
        
        return agent_metrics
    
    async def _evaluate_alert_rules(self, agent_id: str, metrics: Dict[str, Any]):
        """评估告警规则"""
        for rule in self.alert_rules:
            try:
                should_alert, alert_data = await rule.evaluate(agent_id, metrics)
                
                if should_alert:
                    await self._trigger_alert(rule, agent_id, alert_data)
                    
            except Exception as e:
                self.logger.error(f"Alert rule {rule.name} evaluation failed: {e}")
    
    async def _trigger_alert(self, rule: 'AlertRule', agent_id: str, data: Dict[str, Any]):
        """触发告警"""
        alert_id = str(uuid.uuid4())
        
        alert = Alert(
            alert_id=alert_id,
            rule_name=rule.name,
            agent_id=agent_id,
            level=rule.level,
            title=f"{rule.name} - {agent_id}",
            message=data.get("message", "Alert triggered"),
            timestamp=datetime.now(),
            data=data,
            acknowledged=False
        )
        
        # 检查冷却期
        if self._is_in_cooldown(rule.name, agent_id):
            return
        
        # 存储告警
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # 更新统计
        self.stats["total_alerts"] += 1
        if rule.level == AlertLevel.CRITICAL:
            self.stats["critical_alerts"] += 1
        
        # 调用告警处理器
        handlers = self.alert_handlers.get(rule.level, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                self.logger.error(f"Alert handler failed: {e}")
        
        self.logger.warning(f"Alert triggered: {alert.title} - {alert.message}")
    
    def _is_in_cooldown(self, rule_name: str, agent_id: str) -> bool:
        """检查是否在冷却期"""
        # 简化实现，实际应该记录每个规则的最后触发时间
        return False
    
    def _merge_metrics(self, base_metrics: SystemMetrics, new_metrics: Dict[str, Any]) -> SystemMetrics:
        """合并指标"""
        # 简化实现，根据监控器类型合并
        for key, value in new_metrics.items():
            if hasattr(base_metrics, key):
                setattr(base_metrics, key, value)
        
        return base_metrics
    
    def get_agent_health(self, agent_id: str) -> Optional[AgentHealth]:
        """获取Agent健康状态"""
        if agent_id not in self.monitored_agents:
            return None
        
        monitor = self.monitored_agents[agent_id]
        return monitor.get_health_status()
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        healthy_agents = 0
        total_agents = len(self.monitored_agents)
        
        for monitor in self.monitored_agents.values():
            health = monitor.get_health_status()
            if health and health.status == HealthStatus.HEALTHY:
                healthy_agents += 1
        
        health_ratio = healthy_agents / total_agents if total_agents > 0 else 0.0
        
        return {
            "overall_status": HealthStatus.HEALTHY.value if health_ratio >= 0.8 
                           else HealthStatus.DEGRADED.value if health_ratio >= 0.5 
                           else HealthStatus.CRITICAL.value,
            "healthy_agents": healthy_agents,
            "total_agents": total_agents,
            "health_ratio": health_ratio,
            "active_alerts": len(self.active_alerts),
            "critical_alerts": len([a for a in self.active_alerts.values() if a.level == AlertLevel.CRITICAL])
        }
    
    def get_alerts(self, level: Optional[AlertLevel] = None, 
                  agent_id: Optional[str] = None) -> List['Alert']:
        """获取告警列表"""
        alerts = list(self.active_alerts.values())
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        if agent_id:
            alerts = [a for a in alerts if a.agent_id == agent_id]
        
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """确认告警"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            return True
        return False
    
    def get_metrics(self, agent_id: Optional[str] = None, 
                   time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """获取指标数据"""
        if agent_id:
            return self.metrics_store.get_agent_metrics(agent_id, time_range)
        else:
            return self.metrics_store.get_system_metrics(time_range)
    
    async def _collection_loop(self):
        """指标收集循环"""
        while self.running:
            try:
                await self.collect_metrics()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Collection loop error: {e}")
                await asyncio.sleep(self.collection_interval * 2)
    
    async def _alert_processing_loop(self):
        """告警处理循环"""
        while self.running:
            try:
                # 处理活跃告警
                await self._process_active_alerts()
                await asyncio.sleep(30)  # 每30秒处理一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Alert processing loop error: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_loop(self):
        """清理循环"""
        while self.running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # 每小时清理一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(3600)
    
    async def _heartbeat_monitor_loop(self):
        """心跳监控循环"""
        while self.running:
            try:
                current_time = datetime.now()
                
                for agent_id, monitor in self.monitored_agents.items():
                    if current_time - monitor.last_heartbeat > timedelta(seconds=self.heartbeat_timeout):
                        # Agent心跳超时
                        monitor.update_health(False, error_msg="Heartbeat timeout")
                        await self._trigger_alert(
                            AlertRule(name="heartbeat_timeout", level=AlertLevel.ERROR),
                            agent_id,
                            {"message": f"Agent {agent_id} heartbeat timeout"}
                        )
                
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Heartbeat monitor loop error: {e}")
                await asyncio.sleep(30)
    
    async def _process_active_alerts(self):
        """处理活跃告警"""
        current_time = datetime.now()
        
        for alert_id, alert in list(self.active_alerts.items()):
            # 检查告警是否应该自动解决
            if alert.auto_resolve:
                if await self._should_resolve_alert(alert):
                    del self.active_alerts[alert_id]
                    self.logger.info(f"Alert auto-resolved: {alert.title}")
    
    async def _should_resolve_alert(self, alert: 'Alert') -> bool:
        """判断告警是否应该解决"""
        # 简化实现：检查Agent状态是否恢复正常
        if alert.agent_id in self.monitored_agents:
            monitor = self.monitored_agents[alert.agent_id]
            health = monitor.get_health_status()
            if health and health.status == HealthStatus.HEALTHY:
                return True
        return False
    
    async def _cleanup_old_data(self):
        """清理旧数据"""
        cutoff_time = datetime.now() - self.retention_policy["detailed"]
        self.metrics_store.cleanup_old_metrics(cutoff_time)


class AgentMonitor:
    """Agent监控器"""
    
    def __init__(self, agent_id: str, agent_instance: Any):
        self.agent_id = agent_id
        self.agent_instance = agent_instance
        self.health = AgentHealth(agent_id=agent_id)
        self.last_heartbeat = datetime.now()
        self.metrics_history: deque = deque(maxlen=100)
        self.error_count = 0
        self.consecutive_errors = 0
    
    def update_heartbeat(self):
        """更新心跳"""
        self.last_heartbeat = datetime.now()
    
    def update_health(self, success: bool, response_time: float = 0.0, error_msg: str = ""):
        """更新健康状态"""
        self.health.update_health(success, response_time, error_msg)
        
        if success:
            self.consecutive_errors = 0
        else:
            self.consecutive_errors += 1
            self.error_count += 1
    
    def collect_metrics(self) -> Dict[str, Any]:
        """收集指标"""
        try:
            # 从Agent实例获取指标
            if hasattr(self.agent_instance, 'get_info'):
                info = self.agent_instance.get_info()
                metrics = {
                    "agent_id": self.agent_id,
                    "status": info.get("status", "unknown"),
                    "state": info.get("state", "unknown"),
                    "total_requests": info.get("metrics", {}).get("total_requests", 0),
                    "successful_requests": info.get("metrics", {}).get("successful_requests", 0),
                    "failed_requests": info.get("metrics", {}).get("failed_requests", 0),
                    "average_response_time": info.get("metrics", {}).get("average_response_time", 0.0),
                    "cpu_usage": info.get("metrics", {}).get("cpu_usage", 0.0),
                    "memory_usage": info.get("metrics", {}).get("memory_usage", 0.0),
                    "current_tasks": info.get("current_tasks", 0),
                    "uptime": info.get("uptime", 0.0)
                }
            else:
                # 默认指标
                metrics = {
                    "agent_id": self.agent_id,
                    "status": "unknown",
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0
                }
            
            # 存储历史指标
            self.metrics_history.append({
                "timestamp": datetime.now(),
                "metrics": metrics.copy()
            })
            
            return metrics
            
        except Exception as e:
            return {
                "agent_id": self.agent_id,
                "error": str(e)
            }
    
    def get_health_status(self) -> AgentHealth:
        """获取健康状态"""
        return self.health


class SystemMonitor(ABC):
    """系统监控器基类"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """收集指标"""
        pass


class SystemResourceMonitor(SystemMonitor):
    """系统资源监控器"""
    
    def __init__(self):
        super().__init__("system_resources")
    
    def collect(self) -> Dict[str, Any]:
        """收集系统资源指标"""
        try:
            return {
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_usage": psutil.virtual_memory().percent,
                "storage_usage": psutil.disk_usage('/').percent,
                "load_average": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
            }
        except Exception:
            return {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "storage_usage": 0.0,
                "load_average": 0.0
            }


class AgentHealthMonitor(SystemMonitor):
    """Agent健康监控器"""
    
    def __init__(self):
        super().__init__("agent_health")
    
    def collect(self) -> Dict[str, Any]:
        """收集Agent健康指标"""
        # 这里应该从监控系统中获取Agent健康数据
        return {}


class NetworkMonitor(SystemMonitor):
    """网络监控器"""
    
    def __init__(self):
        super().__init__("network")
        self._last_io_stats = psutil.net_io_counters()
    
    def collect(self) -> Dict[str, Any]:
        """收集网络指标"""
        try:
            current_io = psutil.net_io_counters()
            
            if self._last_io_stats:
                bytes_sent_per_sec = current_io.bytes_sent - self._last_io_stats.bytes_sent
                bytes_recv_per_sec = current_io.bytes_recv - self._last_io_stats.bytes_recv
            else:
                bytes_sent_per_sec = 0
                bytes_recv_per_sec = 0
            
            self._last_io_stats = current_io
            
            return {
                "bytes_sent_per_sec": bytes_sent_per_sec,
                "bytes_recv_per_sec": bytes_recv_per_sec,
                "total_bytes_sent": current_io.bytes_sent,
                "total_bytes_recv": current_io.bytes_recv
            }
        except Exception:
            return {
                "bytes_sent_per_sec": 0,
                "bytes_recv_per_sec": 0,
                "total_bytes_sent": 0,
                "total_bytes_recv": 0
            }


class StorageMonitor(SystemMonitor):
    """存储监控器"""
    
    def __init__(self):
        super().__init__("storage")
    
    def collect(self) -> Dict[str, Any]:
        """收集存储指标"""
        try:
            disk_usage = psutil.disk_usage('/')
            return {
                "total_storage": disk_usage.total,
                "used_storage": disk_usage.used,
                "free_storage": disk_usage.free,
                "storage_percent": disk_usage.percent
            }
        except Exception:
            return {
                "total_storage": 0,
                "used_storage": 0,
                "free_storage": 0,
                "storage_percent": 0.0
            }


class AlertRule:
    """告警规则"""
    
    def __init__(self, name: str, level: AlertLevel, condition: Callable, 
                 description: str = "", auto_resolve: bool = False):
        self.name = name
        self.level = level
        self.condition = condition
        self.description = description
        self.auto_resolve = auto_resolve
    
    async def evaluate(self, agent_id: str, metrics: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
        """评估规则"""
        try:
            if asyncio.iscoroutinefunction(self.condition):
                result, data = await self.condition(agent_id, metrics)
            else:
                result, data = self.condition(agent_id, metrics)
            
            return result, data
            
        except Exception as e:
            return False, {"error": str(e)}


class MetricsStore:
    """指标存储"""
    
    def __init__(self):
        self.system_metrics: deque = deque(maxlen=1000)
        self.agent_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
    
    def store_system_metrics(self, metrics: SystemMetrics):
        """存储系统指标"""
        self.system_metrics.append(metrics)
    
    def store_agent_metrics(self, agent_id: str, metrics: Dict[str, Any]):
        """存储Agent指标"""
        self.agent_metrics[agent_id].append({
            "timestamp": datetime.now(),
            "metrics": metrics.copy()
        })
    
    def get_system_metrics(self, time_range: Optional[timedelta] = None) -> List[SystemMetrics]:
        """获取系统指标"""
        metrics = list(self.system_metrics)
        
        if time_range:
            cutoff_time = datetime.now() - time_range
            metrics = [m for m in metrics if m.timestamp > cutoff_time]
        
        return metrics
    
    def get_agent_metrics(self, agent_id: str, time_range: Optional[timedelta] = None) -> List[Dict[str, Any]]:
        """获取Agent指标"""
        if agent_id not in self.agent_metrics:
            return []
        
        metrics = list(self.agent_metrics[agent_id])
        
        if time_range:
            cutoff_time = datetime.now() - time_range
            metrics = [m for m in metrics if m["timestamp"] > cutoff_time]
        
        return metrics
    
    def cleanup_old_metrics(self, cutoff_time: datetime):
        """清理旧指标"""
        # 清理系统指标
        self.system_metrics = deque(
            [m for m in self.system_metrics if m.timestamp > cutoff_time],
            maxlen=1000
        )
        
        # 清理Agent指标
        for agent_id in list(self.agent_metrics.keys()):
            self.agent_metrics[agent_id] = deque(
                [m for m in self.agent_metrics[agent_id] if m["timestamp"] > cutoff_time],
                maxlen=1000
            )


@dataclass
class Alert:
    """告警"""
    alert_id: str
    rule_name: str
    agent_id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    data: Dict[str, Any]
    acknowledged: bool = False
    auto_resolve: bool = False


def create_monitoring_system(system_id: str = "default") -> MonitoringSystem:
    """创建监控系统"""
    return MonitoringSystem(system_id)


def get_monitoring_system(system_id: str = "default") -> MonitoringSystem:
    """获取监控系统（单例）"""
    # 这里可以实现单例模式
    return MonitoringSystem(system_id)