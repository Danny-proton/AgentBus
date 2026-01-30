"""
AgentBus Agent System Core Manager
Agent系统核心管理器
"""

from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import asyncio
import uuid
import json

from .core.base import (
    BaseAgent, AgentFactory, AgentManager, AgentRegistry,
    AgentType, AgentStatus, AgentState, AgentConfig, AgentMetadata
)
from .core.types import (
    AgentMetrics, HealthStatus, AlertLevel, ResourceType,
    MessageType, Priority, AgentMessage, SystemMetrics
)
from .lifecycle.manager import LifecycleManager, create_lifecycle_manager
from .communication.bus import CommunicationBus, create_communication_bus
from .monitoring.system import MonitoringSystem, create_monitoring_system
from .resource.manager import ResourceManager, create_resource_manager
from .plugins.system import PluginSystem, create_plugin_system


class AgentSystem:
    """Agent系统主类"""
    
    def __init__(self, system_id: str = "default"):
        self.system_id = system_id
        self.logger = self._get_logger()
        
        # 核心组件
        self.agent_manager = AgentManager()
        self.lifecycle_manager: Optional[LifecycleManager] = None
        self.communication_bus: Optional[CommunicationBus] = None
        self.monitoring_system: Optional[MonitoringSystem] = None
        self.resource_manager: Optional[ResourceManager] = None
        self.plugin_system: Optional[PluginSystem] = None
        
        # Agent实例
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_configs: Dict[str, AgentConfig] = {}
        self.agent_metadata: Dict[str, AgentMetadata] = {}
        
        # 系统状态
        self.running = False
        self.started_at: Optional[datetime] = None
        
        # 事件处理
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.agent_event_handlers: Dict[str, List[Callable]] = {}
        
        # 统计信息
        self.stats = {
            "system_uptime": 0,
            "total_agents": 0,
            "active_agents": 0,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "system_errors": 0,
            "resource_utilization": {},
            "plugin_count": 0
        }
        
        # 组件状态
        self.component_status = {
            "agent_manager": False,
            "lifecycle_manager": False,
            "communication_bus": False,
            "monitoring_system": False,
            "resource_manager": False,
            "plugin_system": False
        }
    
    def _get_logger(self):
        """获取日志记录器"""
        return f"agent.system.{self.system_id}"
    
    async def initialize(self, config: Dict[str, Any] = None) -> bool:
        """初始化Agent系统"""
        try:
            self.logger.info("Initializing Agent system...")
            
            config = config or {}
            
            # 初始化生命周期管理器
            self.lifecycle_manager = create_lifecycle_manager(f"system_{self.system_id}")
            self.component_status["lifecycle_manager"] = True
            
            # 初始化通信总线
            self.communication_bus = create_communication_bus(self.system_id)
            self.component_status["communication_bus"] = True
            
            # 初始化监控系统
            self.monitoring_system = create_monitoring_system(self.system_id)
            self.component_status["monitoring_system"] = True
            
            # 初始化资源管理器
            self.resource_manager = create_resource_manager(self.system_id)
            self.component_status["resource_manager"] = True
            
            # 初始化插件系统
            self.plugin_system = create_plugin_system(self.system_id)
            self.component_status["plugin_system"] = True
            
            # 启动各个组件
            await self._initialize_components(config)
            
            self.logger.info("Agent system initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Agent system: {e}")
            await self._cleanup_components()
            return False
    
    async def start(self) -> bool:
        """启动Agent系统"""
        if self.running:
            return True
        
        try:
            self.logger.info("Starting Agent system...")
            
            # 启动各个组件
            await self._start_components()
            
            # 启动Agent管理器
            await self.agent_manager.start()
            self.component_status["agent_manager"] = True
            
            # 设置事件处理器
            self._setup_event_handlers()
            
            # 自动加载插件
            if self.plugin_system:
                await self.plugin_system.start()
            
            self.running = True
            self.started_at = datetime.now()
            
            # 启动系统循环
            asyncio.create_task(self._system_loop())
            
            self.logger.info("Agent system started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Agent system: {e}")
            return False
    
    async def stop(self):
        """停止Agent系统"""
        if not self.running:
            return
        
        self.logger.info("Stopping Agent system...")
        
        # 停止所有Agent
        for agent_id in list(self.agents.keys()):
            await self.stop_agent(agent_id)
        
        # 停止各个组件
        await self._stop_components()
        
        self.running = False
        self.started_at = None
        
        self.logger.info("Agent system stopped")
    
    async def create_agent(self, agent_config: AgentConfig, agent_metadata: AgentMetadata) -> Optional[BaseAgent]:
        """创建Agent"""
        try:
            if agent_config.agent_id in self.agents:
                self.logger.warning(f"Agent {agent_config.agent_id} already exists")
                return None
            
            # 创建Agent实例
            agent = await self.agent_manager.create_agent(agent_config, agent_metadata)
            
            # 注册到各个系统
            await self._register_agent(agent)
            
            # 存储引用
            self.agents[agent_config.agent_id] = agent
            self.agent_configs[agent_config.agent_id] = agent_config
            self.agent_metadata[agent_config.agent_id] = agent_metadata
            
            # 更新统计
            self.stats["total_agents"] = len(self.agents)
            self.stats["active_agents"] = len([a for a in self.agents.values() if a.state == AgentState.RUNNING])
            
            self.logger.info(f"Agent created: {agent_config.agent_id}")
            return agent
            
        except Exception as e:
            self.logger.error(f"Failed to create agent {agent_config.agent_id}: {e}")
            return None
    
    async def start_agent(self, agent_id: str) -> bool:
        """启动Agent"""
        if agent_id not in self.agents:
            return False
        
        try:
            agent = self.agents[agent_id]
            
            # 初始化Agent
            success = await agent.initialize()
            if not success:
                return False
            
            # 启动Agent
            success = await agent.start()
            if not success:
                return False
            
            # 启动生命周期管理器（针对单个Agent）
            agent_lifecycle = create_lifecycle_manager(agent_id)
            await agent_lifecycle.start()
            
            # 注册到监控系统
            if self.monitoring_system:
                self.monitoring_system.register_agent(agent_id, agent)
            
            # 请求资源
            if self.resource_manager:
                resource_requests = self._get_agent_resource_requests(agent)
                await self.resource_manager.allocate_resources(agent_id, resource_requests, agent.config)
            
            # 触发启动事件
            await self._emit_agent_event("started", agent_id, {})
            
            self.logger.info(f"Agent started: {agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start agent {agent_id}: {e}")
            return False
    
    async def stop_agent(self, agent_id: str) -> bool:
        """停止Agent"""
        if agent_id not in self.agents:
            return False
        
        try:
            agent = self.agents[agent_id]
            
            # 停止Agent
            await agent.stop()
            
            # 释放资源
            if self.resource_manager:
                resource_usage = self._get_agent_resource_usage(agent)
                await self.resource_manager.release_resources(agent_id, resource_usage)
            
            # 从监控系统中移除
            if self.monitoring_system:
                self.monitoring_system.unregister_agent(agent_id)
            
            # 触发停止事件
            await self._emit_agent_event("stopped", agent_id, {})
            
            self.logger.info(f"Agent stopped: {agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop agent {agent_id}: {e}")
            return False
    
    async def execute_agent_task(self, agent_id: str, task_type: str, 
                              parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行Agent任务"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        agent = self.agents[agent_id]
        
        try:
            # 执行任务
            result = await agent.execute_task(task_type, parameters)
            
            # 更新系统统计
            self.stats["total_requests"] += 1
            if result.get("success"):
                self.stats["successful_requests"] += 1
            else:
                self.stats["failed_requests"] += 1
            
            return result
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            self.logger.error(f"Task execution failed for agent {agent_id}: {e}")
            raise
    
    async def send_agent_message(self, sender_id: str, receiver_id: str, 
                               content: Any, message_type: MessageType = MessageType.DIRECT) -> bool:
        """发送Agent消息"""
        message = AgentMessage(
            message_type=message_type,
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content
        )
        
        if self.communication_bus:
            return await self.communication_bus.send_message(message)
        
        return False
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取Agent状态"""
        if agent_id not in self.agents:
            return None
        
        agent = self.agents[agent_id]
        return agent.get_info()
    
    def list_agents(self, status_filter: Optional[AgentStatus] = None) -> List[str]:
        """列出Agent"""
        agent_ids = list(self.agents.keys())
        
        if status_filter:
            agent_ids = [
                aid for aid in agent_ids 
                if self.agents[aid].status == status_filter
            ]
        
        return agent_ids
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        uptime = (datetime.now() - self.started_at).total_seconds() if self.started_at else 0
        
        return {
            "system_id": self.system_id,
            "running": self.running,
            "uptime": uptime,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "components": self.component_status.copy(),
            "stats": self.stats.copy(),
            "agents": {
                "total": len(self.agents),
                "by_status": self._get_agent_status_counts(),
                "by_type": self._get_agent_type_counts()
            }
        }
    
    def get_system_metrics(self) -> SystemMetrics:
        """获取系统指标"""
        # 收集各个组件的指标
        metrics = SystemMetrics()
        
        if self.monitoring_system:
            system_metrics = asyncio.create_task(self.monitoring_system.collect_metrics())
            # 这里简化处理，实际应该等待结果
            # metrics = await system_metrics
        
        return metrics
    
    def add_event_handler(self, event_name: str, handler: Callable):
        """添加事件处理器"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    def add_agent_event_handler(self, agent_id: str, event_name: str, handler: Callable):
        """添加Agent事件处理器"""
        if agent_id not in self.agent_event_handlers:
            self.agent_event_handlers[agent_id] = {}
        if event_name not in self.agent_event_handlers[agent_id]:
            self.agent_event_handlers[agent_id][event_name] = []
        self.agent_event_handlers[agent_id][event_name].append(handler)
    
    # === 私有方法 ===
    
    async def _initialize_components(self, config: Dict[str, Any]):
        """初始化各个组件"""
        # 初始化Agent管理器
        await self.agent_manager.start()
        
        # 启动各个子系统
        tasks = []
        
        if self.communication_bus:
            tasks.append(self.communication_bus.start())
        
        if self.monitoring_system:
            tasks.append(self.monitoring_system.start())
        
        if self.resource_manager:
            tasks.append(self.resource_manager.start())
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def _start_components(self):
        """启动各个组件"""
        tasks = []
        
        if self.lifecycle_manager:
            tasks.append(self.lifecycle_manager.start())
        
        if self.communication_bus:
            tasks.append(self.communication_bus.start())
        
        if self.monitoring_system:
            tasks.append(self.monitoring_system.start())
        
        if self.resource_manager:
            tasks.append(self.resource_manager.start())
        
        if self.plugin_system:
            tasks.append(self.plugin_system.start())
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def _stop_components(self):
        """停止各个组件"""
        tasks = []
        
        if self.plugin_system:
            tasks.append(self.plugin_system.stop())
        
        if self.resource_manager:
            tasks.append(self.resource_manager.stop())
        
        if self.monitoring_system:
            tasks.append(self.monitoring_system.stop())
        
        if self.communication_bus:
            tasks.append(self.communication_bus.stop())
        
        if self.lifecycle_manager:
            tasks.append(self.lifecycle_manager.stop())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _cleanup_components(self):
        """清理组件"""
        self.component_status = {k: False for k in self.component_status}
    
    def _setup_event_handlers(self):
        """设置事件处理器"""
        # 设置系统事件处理器
        if self.monitoring_system:
            def handle_alert(alert):
                self.logger.warning(f"System alert: {alert.title} - {alert.message}")
            
            self.monitoring_system.add_alert_handler(AlertLevel.WARNING, handle_alert)
            self.monitoring_system.add_alert_handler(AlertLevel.ERROR, handle_alert)
            self.monitoring_system.add_alert_handler(AlertLevel.CRITICAL, handle_alert)
        
        # 设置通信事件处理器
        if self.communication_bus:
            def handle_system_message(message: AgentMessage):
                asyncio.create_task(self._handle_system_message(message))
            
            self.communication_bus.add_message_handler(MessageType.SYSTEM, handle_system_message)
    
    async def _register_agent(self, agent: BaseAgent):
        """注册Agent到各个系统"""
        agent_id = agent.agent_id
        
        # 注册到通信总线
        if self.communication_bus:
            from .communication.bus import AgentConnection
            connection = AgentConnection(agent_id)
            self.communication_bus.register_agent(agent_id, connection)
        
        # 注册到监控系统
        if self.monitoring_system:
            self.monitoring_system.register_agent(agent_id, agent)
    
    def _get_agent_resource_requests(self, agent: BaseAgent) -> Dict[ResourceType, float]:
        """获取Agent资源请求"""
        requests = {}
        
        # 基于Agent配置确定资源需求
        config = agent.config
        resource_limits = config.resource_limits
        
        for resource_type_str, amount in resource_limits.items():
            try:
                resource_type = ResourceType(resource_type_str)
                requests[resource_type] = amount
            except ValueError:
                pass
        
        # 设置默认值
        if ResourceType.CPU not in requests:
            requests[ResourceType.CPU] = 1.0
        if ResourceType.MEMORY not in requests:
            requests[ResourceType.MEMORY] = 512.0  # MB
        if ResourceType.CONCURRENT_TASKS not in requests:
            requests[ResourceType.CONCURRENT_TASKS] = float(config.max_concurrent_tasks)
        
        return requests
    
    def _get_agent_resource_usage(self, agent: BaseAgent) -> Dict[ResourceType, float]:
        """获取Agent资源使用情况"""
        usage = {}
        
        # 从Agent状态中获取资源使用情况
        for resource_type_str, amount in agent.resource_usage.items():
            try:
                resource_type = ResourceType(resource_type_str)
                usage[resource_type] = amount
            except ValueError:
                pass
        
        return usage
    
    async def _handle_system_message(self, message: AgentMessage):
        """处理系统消息"""
        message_type = message.content.get("type")
        
        if message_type == "agent_status":
            agent_id = message.content.get("agent_id")
            status = message.content.get("status")
            
            # 更新Agent状态
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                agent.status = AgentStatus(status)
                
                # 触发Agent状态事件
                await self._emit_agent_event("status_changed", agent_id, {
                    "old_status": getattr(agent, "old_status", None),
                    "new_status": status
                })
        
        elif message_type == "agent_error":
            agent_id = message.content.get("agent_id")
            error = message.content.get("error")
            
            # 更新系统统计
            self.stats["system_errors"] += 1
            
            # 触发Agent错误事件
            await self._emit_agent_event("error", agent_id, {
                "error": error
            })
    
    async def _emit_event(self, event_name: str, data: Dict[str, Any] = None):
        """触发系统事件"""
        handlers = self.event_handlers.get(event_name, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                self.logger.error(f"Event handler {event_name} failed: {e}")
    
    async def _emit_agent_event(self, event_name: str, agent_id: str, data: Dict[str, Any] = None):
        """触发Agent事件"""
        # 调用Agent特定的处理器
        if agent_id in self.agent_event_handlers:
            handlers = self.agent_event_handlers[agent_id].get(event_name, [])
            
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(agent_id, data)
                    else:
                        handler(agent_id, data)
                except Exception as e:
                    self.logger.error(f"Agent event handler {event_name} failed for {agent_id}: {e}")
        
        # 调用全局处理器
        await self._emit_event(f"agent_{event_name}", {
            "agent_id": agent_id,
            **data
        })
    
    def _get_agent_status_counts(self) -> Dict[str, int]:
        """获取Agent状态统计"""
        counts = {}
        for agent in self.agents.values():
            status = agent.status.value
            counts[status] = counts.get(status, 0) + 1
        return counts
    
    def _get_agent_type_counts(self) -> Dict[str, int]:
        """获取Agent类型统计"""
        counts = {}
        for agent in self.agents.values():
            agent_type = agent.config.agent_type.value
            counts[agent_type] = counts.get(agent_type, 0) + 1
        return counts
    
    async def _system_loop(self):
        """系统主循环"""
        while self.running:
            try:
                # 更新系统统计
                if self.started_at:
                    self.stats["system_uptime"] = (datetime.now() - self.started_at).total_seconds()
                
                self.stats["active_agents"] = len([
                    a for a in self.agents.values() if a.state == AgentState.RUNNING
                ])
                
                # 收集资源利用率
                if self.resource_manager:
                    utilization = self.resource_manager.get_system_utilization()
                    self.stats["resource_utilization"] = utilization.get("resource_utilization", {})
                
                # 收集插件数量
                if self.plugin_system:
                    plugin_stats = self.plugin_system.get_plugin_stats()
                    self.stats["plugin_count"] = plugin_stats.get("loaded_plugins", 0)
                
                await asyncio.sleep(10)  # 每10秒更新一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"System loop error: {e}")
                await asyncio.sleep(30)


# 便利函数和单例管理

_global_agent_system: Optional[AgentSystem] = None
_system_lock = asyncio.Lock()


async def get_agent_system(system_id: str = "default") -> AgentSystem:
    """获取Agent系统实例（单例）"""
    global _global_agent_system
    
    async with _system_lock:
        if _global_agent_system is None or _global_agent_system.system_id != system_id:
            _global_agent_system = AgentSystem(system_id)
    
    return _global_agent_system


async def initialize_agent_system(config: Dict[str, Any] = None) -> bool:
    """初始化Agent系统"""
    system = await get_agent_system()
    return await system.initialize(config)


async def start_agent_system() -> bool:
    """启动Agent系统"""
    system = await get_agent_system()
    return await system.start()


async def shutdown_agent_system():
    """关闭Agent系统"""
    global _global_agent_system
    
    if _global_agent_system:
        await _global_agent_system.stop()
        _global_agent_system = None


async def create_agent_instance(agent_config: AgentConfig, agent_metadata: AgentMetadata) -> Optional[BaseAgent]:
    """创建Agent实例"""
    system = await get_agent_system()
    return await system.create_agent(agent_config, agent_metadata)


# 上下文管理器

class AgentSystemContext:
    """Agent系统上下文管理器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.system: Optional[AgentSystem] = None
    
    async def __aenter__(self) -> AgentSystem:
        """进入上下文"""
        self.system = await get_agent_system()
        
        if not self.system.running:
            await self.system.initialize(self.config)
            await self.system.start()
        
        return self.system
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self.system and self.system.running:
            await self.system.stop()


def agent_system(config: Dict[str, Any] = None) -> AgentSystemContext:
    """Agent系统上下文管理器"""
    return AgentSystemContext(config)