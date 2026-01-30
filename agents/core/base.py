"""
AgentBus Agent Base Classes
Agent系统核心基类
"""

from typing import Dict, List, Optional, Any, Set, Callable, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import asyncio
import uuid
import json

from .types import (
    AgentType, AgentStatus, AgentState, AgentCapability, AgentMetadata,
    AgentConfig, AgentMetrics, AgentHealth, SystemMetrics, ResourceQuota,
    MessageType, Priority, AgentMessage, HealthStatus, AlertLevel
)


class BaseAgent(ABC):
    """
    基础Agent抽象类
    
    所有Agent都必须继承此类并实现必要的方法
    """
    
    def __init__(self, config: AgentConfig, metadata: AgentMetadata):
        self.config = config
        self.metadata = metadata
        self.agent_id = config.agent_id
        
        # 状态管理
        self.status = AgentStatus.INITIALIZING
        self.state = AgentState.CREATED
        self.health = AgentHealth(agent_id=self.agent_id)
        
        # 能力管理
        self.capabilities: List[AgentCapability] = []
        self._enabled_capabilities: Set[str] = set()
        
        # 指标管理
        self.metrics = AgentMetrics()
        
        # 任务管理
        self.current_tasks: Dict[str, asyncio.Task] = {}
        self.task_history: List[Dict[str, Any]] = []
        
        # 资源管理
        self.resource_usage: Dict[str, float] = {}
        
        # 事件处理
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # 生命周期
        self._lifecycle_started = False
        self._shutdown_event = asyncio.Event()
        
        # 子类初始化
        self._initialize()
    
    def _initialize(self):
        """子类初始化钩子"""
        pass
    
    # === 生命周期管理 ===
    
    async def initialize(self) -> bool:
        """初始化Agent"""
        try:
            self.status = AgentStatus.INITIALIZING
            self.state = AgentState.CREATED
            
            # 验证配置
            if not await self._validate_config():
                return False
            
            # 初始化能力
            await self._initialize_capabilities()
            
            # 验证连接
            if not await self._validate_connection():
                return False
            
            self.status = AgentStatus.IDLE
            self.state = AgentState.RUNNING
            self.health.status = HealthStatus.HEALTHY
            
            # 启动生命周期
            await self._start_lifecycle()
            
            return True
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            self.state = AgentState.FAILED
            self.health.update_health(False, error_msg=str(e))
            await self._handle_error("initialize", e)
            return False
    
    async def start(self) -> bool:
        """启动Agent"""
        try:
            if self.state != AgentState.RUNNING:
                return False
            
            self.status = AgentStatus.IDLE
            self.state = AgentState.RUNNING
            
            # 触发启动事件
            await self._emit_event("started")
            
            return True
            
        except Exception as e:
            await self._handle_error("start", e)
            return False
    
    async def pause(self) -> bool:
        """暂停Agent"""
        try:
            if self.state != AgentState.RUNNING:
                return False
            
            self.status = AgentStatus.SUSPENDED
            self.state = AgentState.PAUSED
            
            # 取消所有当前任务
            for task_id, task in self.current_tasks.items():
                if not task.done():
                    task.cancel()
            
            # 触发暂停事件
            await self._emit_event("paused")
            
            return True
            
        except Exception as e:
            await self._handle_error("pause", e)
            return False
    
    async def resume(self) -> bool:
        """恢复Agent"""
        try:
            if self.state != AgentState.PAUSED:
                return False
            
            self.status = AgentStatus.IDLE
            self.state = AgentState.RUNNING
            
            # 触发恢复事件
            await self._emit_event("resumed")
            
            return True
            
        except Exception as e:
            await self._handle_error("resume", e)
            return False
    
    async def stop(self) -> bool:
        """停止Agent"""
        try:
            if self.state == AgentState.STOPPED:
                return True
            
            self.status = AgentStatus.TERMINATING
            self.state = AgentState.STOPPING
            
            # 触发停止事件
            await self._emit_event("stopping")
            
            # 取消所有任务
            for task_id, task in self.current_tasks.items():
                if not task.done():
                    task.cancel()
            
            # 等待任务完成
            if self.current_tasks:
                await asyncio.gather(*self.current_tasks.values(), return_exceptions=True)
            
            self.status = AgentStatus.OFFLINE
            self.state = AgentState.STOPPED
            
            # 触发停止事件
            await self._emit_event("stopped")
            
            # 关闭生命周期
            await self._shutdown_lifecycle()
            
            return True
            
        except Exception as e:
            await self._handle_error("stop", e)
            return False
    
    async def shutdown(self):
        """关闭Agent"""
        await self.stop()
        self._shutdown_event.set()
    
    # === 任务执行 ===
    
    async def execute_task(self, task_type: str, parameters: Dict[str, Any], 
                         timeout: Optional[float] = None) -> Dict[str, Any]:
        """执行任务"""
        if self.state != AgentState.RUNNING:
            raise RuntimeError(f"Agent is not running: {self.state}")
        
        timeout = timeout or self.config.timeout
        task_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            # 创建任务
            self.status = AgentStatus.BUSY
            task = asyncio.create_task(self._execute_task_internal(
                task_id, task_type, parameters, timeout
            ))
            self.current_tasks[task_id] = task
            
            # 执行任务
            result = await asyncio.wait_for(task, timeout=timeout)
            
            # 更新指标
            response_time = (datetime.now() - start_time).total_seconds()
            self.metrics.update_metrics(
                success=True,
                response_time=response_time
            )
            
            return {
                "task_id": task_id,
                "success": True,
                "result": result,
                "response_time": response_time
            }
            
        except asyncio.TimeoutError:
            self.metrics.update_metrics(
                success=False,
                response_time=timeout
            )
            raise TimeoutError(f"Task {task_id} timed out after {timeout} seconds")
            
        except Exception as e:
            self.metrics.update_metrics(
                success=False,
                response_time=(datetime.now() - start_time).total_seconds()
            )
            await self._handle_error("execute_task", e)
            raise
            
        finally:
            self.status = AgentStatus.IDLE if self.state == AgentState.RUNNING else self.status
            self.current_tasks.pop(task_id, None)
    
    async def _execute_task_internal(self, task_id: str, task_type: str, 
                                   parameters: Dict[str, Any], timeout: float) -> Any:
        """内部任务执行"""
        # 根据任务类型分发
        if task_type == "text_generation":
            return await self.generate_text(
                prompt=parameters.get("prompt", ""),
                system_prompt=parameters.get("system_prompt"),
                context=parameters.get("context")
            )
        elif task_type == "code_generation":
            return await self.generate_code(
                prompt=parameters.get("prompt", ""),
                language=parameters.get("language", "python")
            )
        elif task_type == "image_analysis":
            return await self.analyze_image(
                image_url=parameters.get("image_url", ""),
                prompt=parameters.get("prompt", "Analyze this image")
            )
        elif task_type == "reasoning":
            return await self.reason(
                prompt=parameters.get("prompt", "")
            )
        else:
            # 自定义任务处理
            return await self._handle_custom_task(task_type, parameters)
    
    async def _handle_custom_task(self, task_type: str, parameters: Dict[str, Any]) -> Any:
        """处理自定义任务"""
        # 子类可以重写此方法处理自定义任务类型
        raise NotImplementedError(f"Unknown task type: {task_type}")
    
    # === 抽象方法（子类必须实现） ===
    
    @abstractmethod
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None,
                          context: Optional[List[Dict[str, Any]]] = None) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    async def _validate_config(self) -> bool:
        """验证配置"""
        pass
    
    @abstractmethod
    async def _validate_connection(self) -> bool:
        """验证连接"""
        pass
    
    @abstractmethod
    async def _initialize_capabilities(self) -> None:
        """初始化能力"""
        pass
    
    # === 可选方法 ===
    
    async def generate_code(self, prompt: str, language: str = "python") -> str:
        """生成代码"""
        code_prompt = f"Generate {language} code for the following task:\n{prompt}"
        return await self.generate_text(code_prompt)
    
    async def analyze_image(self, image_url: str, prompt: str = "Analyze this image") -> str:
        """分析图像"""
        analysis_prompt = f"{prompt}\n\nImage URL: {image_url}"
        return await self.generate_text(analysis_prompt)
    
    async def reason(self, prompt: str) -> str:
        """推理"""
        reasoning_prompt = f"Analyze and reason about the following:\n{prompt}"
        return await self.generate_text(reasoning_prompt)
    
    # === 事件处理 ===
    
    def on_event(self, event_name: str, handler: Callable):
        """注册事件处理器"""
        if event_name not in self.event_handlers:
            self.event_handlers[event_name] = []
        self.event_handlers[event_name].append(handler)
    
    def off_event(self, event_name: str, handler: Callable):
        """注销事件处理器"""
        if event_name in self.event_handlers:
            try:
                self.event_handlers[event_name].remove(handler)
            except ValueError:
                pass
    
    async def _emit_event(self, event_name: str, data: Any = None):
        """触发事件"""
        if event_name in self.event_handlers:
            handlers = self.event_handlers[event_name].copy()
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    await self._handle_error(f"event_handler_{event_name}", e)
    
    async def _handle_error(self, operation: str, error: Exception):
        """处理错误"""
        error_msg = f"Error in {operation}: {str(error)}"
        print(f"[{self.agent_id}] {error_msg}")
        
        # 更新健康状态
        self.health.update_health(False, error_msg=error_msg)
        
        # 触发错误事件
        await self._emit_event("error", {
            "operation": operation,
            "error": str(error),
            "timestamp": datetime.now()
        })
    
    # === 生命周期管理 ===
    
    async def _start_lifecycle(self):
        """启动生命周期"""
        if not self._lifecycle_started:
            self._lifecycle_started = True
            asyncio.create_task(self._lifecycle_loop())
    
    async def _shutdown_lifecycle(self):
        """关闭生命周期"""
        self._lifecycle_started = False
        await self._emit_event("lifecycle_shutdown")
    
    async def _lifecycle_loop(self):
        """生命周期循环"""
        while self._lifecycle_started:
            try:
                # 健康检查
                await self._perform_health_check()
                
                # 性能监控
                await self._monitor_performance()
                
                # 资源监控
                await self._monitor_resources()
                
                await asyncio.sleep(10)  # 每10秒检查一次
                
            except Exception as e:
                await self._handle_error("lifecycle_loop", e)
                await asyncio.sleep(30)  # 错误后等待更长时间
    
    async def _perform_health_check(self):
        """执行健康检查"""
        try:
            # 检查基本状态
            if self.state == AgentState.FAILED:
                self.health.status = HealthStatus.CRITICAL
            elif self.state == AgentState.STOPPED:
                self.health.status = HealthStatus.UNHEALTHY
            elif len(self.current_tasks) > self.config.max_concurrent_tasks:
                self.health.status = HealthStatus.DEGRADED
            else:
                self.health.status = HealthStatus.HEALTHY
            
            # 更新指标
            self.health.last_check = datetime.now()
            
        except Exception as e:
            self.health.status = HealthStatus.CRITICAL
            self.health.last_error = str(e)
    
    async def _monitor_performance(self):
        """监控性能"""
        # 子类可以重写此方法添加自定义性能监控
        pass
    
    async def _monitor_resources(self):
        """监控资源"""
        # 子类可以重写此方法添加自定义资源监控
        pass
    
    # === 信息获取 ===
    
    def get_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        return {
            "agent_id": self.agent_id,
            "name": self.metadata.name,
            "type": self.config.agent_type.value,
            "version": self.metadata.version,
            "status": self.status.value,
            "state": self.state.value,
            "health": {
                "status": self.health.status.value,
                "last_check": self.health.last_check.isoformat(),
                "response_time": self.health.response_time,
                "error_count": self.health.error_count,
                "consecutive_failures": self.health.consecutive_failures,
                "last_error": self.health.last_error
            },
            "capabilities": [cap.name for cap in self.capabilities],
            "metrics": self.metrics.to_dict(),
            "current_tasks": len(self.current_tasks),
            "resource_usage": self.resource_usage,
            "created_at": self.metadata.created_at.isoformat(),
            "uptime": self.metrics.uptime
        }
    
    def get_capability(self, name: str) -> Optional[AgentCapability]:
        """获取指定能力"""
        for cap in self.capabilities:
            if cap.name == name and name in self._enabled_capabilities:
                return cap
        return None
    
    def is_capability_enabled(self, name: str) -> bool:
        """检查能力是否启用"""
        return name in self._enabled_capabilities
    
    def enable_capability(self, name: str):
        """启用能力"""
        self._enabled_capabilities.add(name)
    
    def disable_capability(self, name: str):
        """禁用能力"""
        self._enabled_capabilities.discard(name)


class AgentFactory(ABC):
    """Agent工厂抽象类"""
    
    @abstractmethod
    async def create_agent(self, config: AgentConfig, metadata: AgentMetadata) -> BaseAgent:
        """创建Agent实例"""
        pass
    
    @abstractmethod
    def get_agent_type(self) -> AgentType:
        """获取Agent类型"""
        pass
    
    @abstractmethod
    def get_supported_capabilities(self) -> List[str]:
        """获取支持的能力"""
        pass


class AgentRegistry:
    """Agent注册表"""
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._factories: Dict[str, AgentFactory] = {}
        self._agent_types: Dict[str, AgentType] = {}
    
    def register_agent(self, agent_id: str, agent: BaseAgent):
        """注册Agent"""
        self._agents[agent_id] = agent
    
    def unregister_agent(self, agent_id: str):
        """注销Agent"""
        self._agents.pop(agent_id, None)
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """获取Agent"""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> List[str]:
        """列出所有Agent"""
        return list(self._agents.keys())
    
    def register_factory(self, agent_type: AgentType, factory: AgentFactory):
        """注册工厂"""
        self._factories[agent_type.value] = factory
        self._agent_types[factory.__class__.__name__] = agent_type
    
    def create_agent(self, config: AgentConfig, metadata: AgentMetadata) -> BaseAgent:
        """创建Agent"""
        factory = self._factories.get(config.agent_type.value)
        if not factory:
            raise ValueError(f"No factory found for agent type: {config.agent_type}")
        
        return asyncio.create_task(factory.create_agent(config, metadata))
    
    def get_agents_by_type(self, agent_type: AgentType) -> List[BaseAgent]:
        """根据类型获取Agent"""
        return [agent for agent in self._agents.values() 
                if agent.config.agent_type == agent_type]


class AgentManager:
    """Agent管理器"""
    
    def __init__(self):
        self.registry = AgentRegistry()
        self.running = False
    
    async def start(self):
        """启动管理器"""
        self.running = True
    
    async def stop(self):
        """停止管理器"""
        self.running = False
        
        # 停止所有Agent
        for agent in self.registry.list_agents():
            agent_instance = self.registry.get_agent(agent)
            if agent_instance:
                await agent_instance.stop()
    
    async def create_agent(self, config: AgentConfig, metadata: AgentMetadata) -> BaseAgent:
        """创建Agent"""
        agent = await self.registry.create_agent(config, metadata)
        self.registry.register_agent(config.agent_id, agent)
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """获取Agent"""
        return self.registry.get_agent(agent_id)
    
    def list_agents(self) -> List[str]:
        """列出所有Agent"""
        return self.registry.list_agents()
    
    async def stop_agent(self, agent_id: str) -> bool:
        """停止Agent"""
        agent = self.registry.get_agent(agent_id)
        if agent:
            await agent.stop()
            self.registry.unregister_agent(agent_id)
            return True
        return False