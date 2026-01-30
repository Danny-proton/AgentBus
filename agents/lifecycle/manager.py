"""
AgentBus Lifecycle Management
Agent生命周期管理系统
"""

from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import asyncio
import uuid
import json

from ..core.types import (
    AgentType, AgentStatus, AgentState, LifecycleEvent, LifecycleState,
    AgentMetadata, AgentConfig, AgentMetrics, HealthStatus, AlertLevel
)


class LifecycleManager:
    """Agent生命周期管理器"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.logger = self._get_logger()
        
        # 生命周期状态
        self.current_state = LifecycleState.CREATED
        self.previous_state = None
        self.state_history: List[Dict[str, Any]] = []
        
        # 事件处理
        self.event_handlers: Dict[LifecycleEvent, List[Callable]] = {}
        self.event_queue = asyncio.Queue()
        
        # 状态转换规则
        self.transition_rules = self._initialize_transition_rules()
        
        # 监控和告警
        self.state_monitors: List[Callable] = []
        self.alert_callbacks: List[Callable] = []
        
        # 生命周期任务
        self.lifecycle_task: Optional[asyncio.Task] = None
        self.running = False
        
        # 超时配置
        self.state_timeouts = {
            LifecycleState.INITIALIZING: 300,      # 5分钟
            LifecycleState.STARTING: 60,           # 1分钟
            LifecycleState.STOPPING: 60,           # 1分钟
            LifecycleState.TERMINATING: 120,       # 2分钟
            LifecycleState.ERROR_RECOVERY: 300    # 5分钟
        }
    
    def _get_logger(self):
        """获取日志记录器"""
        return f"lifecycle.{self.agent_id}"
    
    def _initialize_transition_rules(self) -> Dict[LifecycleState, Dict[str, LifecycleState]]:
        """初始化状态转换规则"""
        return {
            LifecycleState.CREATED: {
                "initialize": LifecycleState.INITIALIZING,
                "terminate": LifecycleState.TERMINATED
            },
            LifecycleState.INITIALIZING: {
                "initialized": LifecycleState.STOPPED,
                "error": LifecycleState.ERROR,
                "timeout": LifecycleState.ERROR
            },
            LifecycleState.STOPPED: {
                "start": LifecycleState.STARTING,
                "terminate": LifecycleState.TERMINATING
            },
            LifecycleState.STARTING: {
                "started": LifecycleState.RUNNING,
                "error": LifecycleState.ERROR_RECOVERY,
                "timeout": LifecycleState.ERROR
            },
            LifecycleState.RUNNING: {
                "pause": LifecycleState.PAUSED,
                "stop": LifecycleState.STOPPING,
                "error": LifecycleState.ERROR_RECOVERY,
                "timeout": LifecycleState.ERROR
            },
            LifecycleState.PAUSED: {
                "resume": LifecycleState.RUNNING,
                "stop": LifecycleState.STOPPING,
                "error": LifecycleState.ERROR
            },
            LifecycleState.STOPPING: {
                "stopped": LifecycleState.STOPPED,
                "error": LifecycleState.ERROR,
                "timeout": LifecycleState.ERROR
            },
            LifecycleState.ERROR_RECOVERY: {
                "recovered": LifecycleState.RUNNING,
                "failed": LifecycleState.ERROR,
                "timeout": LifecycleState.ERROR
            },
            LifecycleState.ERROR: {
                "reset": LifecycleState.STOPPED,
                "terminate": LifecycleState.TERMINATING
            },
            LifecycleState.TERMINATING: {
                "terminated": LifecycleState.TERMINATED,
                "error": LifecycleState.ERROR,
                "timeout": LifecycleState.ERROR
            },
            LifecycleState.TERMINATED: {}  # 终态，无转换
        }
    
    async def start(self):
        """启动生命周期管理器"""
        if self.running:
            return
        
        self.running = True
        self.lifecycle_task = asyncio.create_task(self._lifecycle_loop())
        self.logger.info("Lifecycle manager started")
    
    async def stop(self):
        """停止生命周期管理器"""
        if not self.running:
            return
        
        self.running = False
        
        # 取消生命周期任务
        if self.lifecycle_task:
            self.lifecycle_task.cancel()
            try:
                await self.lifecycle_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Lifecycle manager stopped")
    
    async def initialize(self, config: AgentConfig, metadata: AgentMetadata) -> bool:
        """初始化Agent"""
        try:
            await self._transition_to_state(LifecycleState.INITIALIZING)
            
            # 执行初始化逻辑
            success = await self._perform_initialization(config, metadata)
            
            if success:
                await self._emit_event(LifecycleEvent.INITIALIZE, {"success": True})
                await self._transition_to_state(LifecycleState.STOPPED)
            else:
                await self._emit_event(LifecycleEvent.INITIALIZE, {"success": False})
                await self._transition_to_state(LifecycleState.ERROR)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            await self._emit_event(LifecycleEvent.ERROR, {"error": str(e)})
            await self._transition_to_state(LifecycleState.ERROR)
            return False
    
    async def start_agent(self) -> bool:
        """启动Agent"""
        try:
            await self._transition_to_state(LifecycleState.STARTING)
            
            # 执行启动逻辑
            success = await self._perform_startup()
            
            if success:
                await self._emit_event(LifecycleEvent.START, {"success": True})
                await self._transition_to_state(LifecycleState.RUNNING)
            else:
                await self._emit_event(LifecycleEvent.START, {"success": False})
                await self._transition_to_state(LifecycleState.ERROR)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Startup failed: {e}")
            await self._emit_event(LifecycleEvent.ERROR, {"error": str(e)})
            await self._transition_to_state(LifecycleState.ERROR)
            return False
    
    async def pause_agent(self) -> bool:
        """暂停Agent"""
        try:
            if self.current_state != LifecycleState.RUNNING:
                return False
            
            await self._emit_event(LifecycleEvent.PAUSE)
            await self._transition_to_state(LifecycleState.PAUSED)
            return True
            
        except Exception as e:
            self.logger.error(f"Pause failed: {e}")
            await self._emit_event(LifecycleEvent.ERROR, {"error": str(e)})
            return False
    
    async def resume_agent(self) -> bool:
        """恢复Agent"""
        try:
            if self.current_state != LifecycleState.PAUSED:
                return False
            
            await self._emit_event(LifecycleEvent.RESUME)
            await self._transition_to_state(LifecycleState.RUNNING)
            return True
            
        except Exception as e:
            self.logger.error(f"Resume failed: {e}")
            await self._emit_event(LifecycleEvent.ERROR, {"error": str(e)})
            return False
    
    async def stop_agent(self) -> bool:
        """停止Agent"""
        try:
            if self.current_state in [LifecycleState.STOPPING, LifecycleState.TERMINATING, LifecycleState.TERMINATED]:
                return True
            
            await self._transition_to_state(LifecycleState.STOPPING)
            
            # 执行停止逻辑
            await self._perform_shutdown()
            
            await self._emit_event(LifecycleEvent.STOP, {"success": True})
            await self._transition_to_state(LifecycleState.STOPPED)
            return True
            
        except Exception as e:
            self.logger.error(f"Stop failed: {e}")
            await self._emit_event(LifecycleEvent.ERROR, {"error": str(e)})
            return False
    
    async def terminate_agent(self) -> bool:
        """终止Agent"""
        try:
            if self.current_state == LifecycleState.TERMINATED:
                return True
            
            await self._transition_to_state(LifecycleState.TERMINATING)
            
            # 执行终止逻辑
            await self._perform_termination()
            
            await self._emit_event(LifecycleEvent.TERMINATE, {"success": True})
            await self._transition_to_state(LifecycleState.TERMINATED)
            return True
            
        except Exception as e:
            self.logger.error(f"Termination failed: {e}")
            await self._emit_event(LifecycleEvent.ERROR, {"error": str(e)})
            return False
    
    async def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> bool:
        """处理错误"""
        try:
            context = context or {}
            context["error"] = str(error)
            context["timestamp"] = datetime.now().isoformat()
            
            if self.current_state == LifecycleState.RUNNING:
                # 运行状态下，进入错误恢复状态
                await self._emit_event(LifecycleEvent.ERROR, context)
                await self._transition_to_state(LifecycleState.ERROR_RECOVERY)
                
                # 尝试自动恢复
                return await self._attempt_recovery(error, context)
            else:
                # 非运行状态下，直接进入错误状态
                await self._emit_event(LifecycleEvent.ERROR, context)
                await self._transition_to_state(LifecycleState.ERROR)
                return False
            
        except Exception as e:
            self.logger.error(f"Error handling failed: {e}")
            return False
    
    def add_event_handler(self, event: LifecycleEvent, handler: Callable):
        """添加事件处理器"""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)
    
    def remove_event_handler(self, event: LifecycleEvent, handler: Callable):
        """移除事件处理器"""
        if event in self.event_handlers:
            try:
                self.event_handlers[event].remove(handler)
            except ValueError:
                pass
    
    def add_state_monitor(self, monitor: Callable):
        """添加状态监控器"""
        self.state_monitors.append(monitor)
    
    def add_alert_callback(self, callback: Callable):
        """添加告警回调"""
        self.alert_callbacks.append(callback)
    
    async def _transition_to_state(self, new_state: LifecycleState):
        """转换状态"""
        if new_state == self.current_state:
            return
        
        # 检查转换规则
        if self.current_state in self.transition_rules:
            allowed_transitions = self.transition_rules[self.current_state]
            if new_state not in allowed_transitions.values():
                raise ValueError(f"Invalid state transition from {self.current_state} to {new_state}")
        
        # 记录状态转换
        old_state = self.current_state
        self.previous_state = old_state
        self.current_state = new_state
        
        transition_record = {
            "from_state": old_state.value,
            "to_state": new_state.value,
            "timestamp": datetime.now().isoformat()
        }
        self.state_history.append(transition_record)
        
        self.logger.info(f"State transition: {old_state.value} -> {new_state.value}")
        
        # 执行状态转换钩子
        await self._on_state_transition(old_state, new_state)
        
        # 触发状态转换事件
        await self._emit_event(LifecycleEvent.INITIALIZE if new_state == LifecycleState.INITIALIZING else
                              LifecycleEvent.START if new_state == LifecycleState.STARTING else
                              LifecycleEvent.PAUSE if new_state == LifecycleState.PAUSED else
                              LifecycleEvent.RESUME if new_state == LifecycleState.RUNNING else
                              LifecycleEvent.STOP if new_state == LifecycleState.STOPPED else
                              LifecycleEvent.TERMINATE if new_state == LifecycleState.TERMINATED else
                              LifecycleEvent.ERROR, {
                                  "old_state": old_state.value,
                                  "new_state": new_state.value
                              })
        
        # 检查超时
        if new_state in self.state_timeouts:
            asyncio.create_task(self._check_state_timeout(new_state, self.state_timeouts[new_state]))
    
    async def _perform_initialization(self, config: AgentConfig, metadata: AgentMetadata) -> bool:
        """执行初始化逻辑"""
        # 子类可以重写此方法实现自定义初始化逻辑
        await asyncio.sleep(1)  # 模拟初始化过程
        return True
    
    async def _perform_startup(self) -> bool:
        """执行启动逻辑"""
        # 子类可以重写此方法实现自定义启动逻辑
        await asyncio.sleep(1)  # 模拟启动过程
        return True
    
    async def _perform_shutdown(self):
        """执行停止逻辑"""
        # 子类可以重写此方法实现自定义停止逻辑
        await asyncio.sleep(0.5)  # 模拟停止过程
    
    async def _perform_termination(self):
        """执行终止逻辑"""
        # 子类可以重写此方法实现自定义终止逻辑
        await asyncio.sleep(0.5)  # 模拟终止过程
    
    async def _attempt_recovery(self, error: Exception, context: Dict[str, Any]) -> bool:
        """尝试错误恢复"""
        try:
            # 等待一段时间后重试
            await asyncio.sleep(5)
            
            # 执行恢复逻辑
            recovery_success = await self._perform_recovery(error, context)
            
            if recovery_success:
                await self._transition_to_state(LifecycleState.RUNNING)
                return True
            else:
                await self._transition_to_state(LifecycleState.ERROR)
                return False
            
        except Exception as e:
            self.logger.error(f"Recovery attempt failed: {e}")
            await self._transition_to_state(LifecycleState.ERROR)
            return False
    
    async def _perform_recovery(self, error: Exception, context: Dict[str, Any]) -> bool:
        """执行恢复逻辑"""
        # 子类可以重写此方法实现自定义恢复逻辑
        await asyncio.sleep(2)  # 模拟恢复过程
        return True
    
    async def _on_state_transition(self, old_state: LifecycleState, new_state: LifecycleState):
        """状态转换钩子"""
        # 执行状态监控器
        for monitor in self.state_monitors:
            try:
                if asyncio.iscoroutinefunction(monitor):
                    await monitor(old_state, new_state)
                else:
                    monitor(old_state, new_state)
            except Exception as e:
                self.logger.error(f"State monitor failed: {e}")
        
        # 检查是否需要告警
        if new_state in [LifecycleState.ERROR, LifecycleState.ERROR_RECOVERY]:
            await self._trigger_alert(AlertLevel.ERROR, f"Agent entered error state: {new_state.value}")
    
    async def _emit_event(self, event: LifecycleEvent, data: Dict[str, Any] = None):
        """触发事件"""
        data = data or {}
        data["event"] = event.value
        data["timestamp"] = datetime.now().isoformat()
        data["agent_id"] = self.agent_id
        data["current_state"] = self.current_state.value
        
        # 发送到事件队列
        await self.event_queue.put({
            "event": event,
            "data": data
        })
        
        # 调用事件处理器
        handlers = self.event_handlers.get(event, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event, data)
                else:
                    handler(event, data)
            except Exception as e:
                self.logger.error(f"Event handler failed: {e}")
    
    async def _check_state_timeout(self, state: LifecycleState, timeout: int):
        """检查状态超时"""
        await asyncio.sleep(timeout)
        
        if self.current_state == state and self.running:
            self.logger.warning(f"State {state.value} timed out after {timeout} seconds")
            await self._emit_event(LifecycleEvent.ERROR, {
                "error": f"State {state.value} timed out",
                "timeout": timeout
            })
            await self._transition_to_state(LifecycleState.ERROR)
    
    async def _trigger_alert(self, level: AlertLevel, message: str):
        """触发告警"""
        alert_data = {
            "level": level.value,
            "message": message,
            "agent_id": self.agent_id,
            "timestamp": datetime.now().isoformat(),
            "current_state": self.current_state.value
        }
        
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data)
                else:
                    callback(alert_data)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")
    
    async def _lifecycle_loop(self):
        """生命周期循环"""
        while self.running:
            try:
                # 处理事件队列
                try:
                    event_data = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                    # 事件已在_emit_event中处理
                except asyncio.TimeoutError:
                    pass
                
                # 执行定期检查
                await self._periodic_checks()
                
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Lifecycle loop error: {e}")
                await asyncio.sleep(5)
    
    async def _periodic_checks(self):
        """定期检查"""
        # 子类可以重写此方法实现自定义定期检查
        pass
    
    def get_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "agent_id": self.agent_id,
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "state_history": self.state_history[-10:],  # 最近10次转换
            "running": self.running,
            "uptime": (datetime.now() - self.state_history[0]["timestamp"]).total_seconds() 
                     if self.state_history else 0
        }


def create_lifecycle_manager(agent_id: str) -> LifecycleManager:
    """创建生命周期管理器"""
    return LifecycleManager(agent_id)


def get_lifecycle_manager(agent_id: str) -> LifecycleManager:
    """获取生命周期管理器（单例）"""
    # 这里可以实现单例模式
    return LifecycleManager(agent_id)