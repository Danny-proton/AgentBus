"""
AgentBus技能生命周期管理

提供技能的全生命周期管理，包括启动、停止、健康检查、状态监控等功能。
"""

import asyncio
import logging
import signal
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import weakref

from .base import (
    BaseSkill, SkillMetadata, SkillContext, 
    SkillStatus, SkillType, SkillExecutionError
)
from .registry import SkillManager


class LifecycleState(Enum):
    """生命周期状态"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class SkillMetrics:
    """技能指标"""
    skill_name: str
    status: SkillStatus
    activation_time: Optional[datetime] = None
    last_execution: Optional[datetime] = None
    execution_count: int = 0
    error_count: int = 0
    average_execution_time: float = 0.0
    memory_usage: int = 0
    cpu_usage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "status": self.status.value,
            "activation_time": self.activation_time.isoformat() if self.activation_time else None,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "average_execution_time": self.average_execution_time,
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
        }


@dataclass
class LifecycleConfig:
    """生命周期配置"""
    health_check_interval: int = 60  # 秒
    auto_restart_enabled: bool = True
    max_restart_attempts: int = 3
    restart_delay: float = 5.0  # 秒
    timeout_shutdown: float = 30.0  # 秒
    timeout_health_check: float = 10.0  # 秒
    metrics_collection_interval: int = 30  # 秒
    max_execution_time: float = 300.0  # 秒
    memory_limit_mb: int = 512
    cpu_limit_percent: float = 80.0
    
    # 事件钩子
    on_skill_start: Optional[Callable[[str], None]] = None
    on_skill_stop: Optional[Callable[[str], None]] = None
    on_skill_error: Optional[Callable[[str, Exception], None]] = None
    on_health_check: Optional[Callable[[str, HealthStatus], None]] = None


class SkillLifecycleManager:
    """技能生命周期管理器"""
    
    def __init__(self, skill_manager: SkillManager, config: Optional[LifecycleConfig] = None):
        self.skill_manager = skill_manager
        self.config = config or LifecycleConfig()
        self.state = LifecycleState.STOPPED
        
        # 技能状态跟踪
        self._skill_metrics: Dict[str, SkillMetrics] = {}
        self._skill_health_status: Dict[str, HealthStatus] = {}
        self._skill_watchers: Dict[str, asyncio.Task] = {}
        self._execution_times: Dict[str, List[float]] = {}
        
        # 生命周期管理
        self._main_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._lock = asyncio.Lock()
        
        self.logger = logging.getLogger(__name__)
        
        # 信号处理
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """设置信号处理器"""
        try:
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig,
                    lambda: asyncio.create_task(self.shutdown())
                )
        except (OSError, NotImplementedError):
            # 在某些平台上可能不支持信号处理器
            pass
    
    async def start(self) -> None:
        """启动生命周期管理器"""
        async with self._lock:
            if self.state != LifecycleState.STOPPED:
                self.logger.warning("Lifecycle manager is already running")
                return
            
            self.state = LifecycleState.STARTING
            self.logger.info("Starting skill lifecycle manager...")
            
            try:
                # 启动所有启用的技能
                await self._start_all_skills()
                
                # 启动监控任务
                await self._start_monitoring_tasks()
                
                # 设置主任务
                self._main_task = asyncio.create_task(self._main_loop())
                
                self.state = LifecycleState.RUNNING
                self.logger.info("Skill lifecycle manager started successfully")
                
            except Exception as e:
                self.state = LifecycleState.ERROR
                self.logger.error(f"Failed to start lifecycle manager: {e}")
                raise
    
    async def stop(self) -> None:
        """停止生命周期管理器"""
        await self.shutdown()
    
    async def shutdown(self) -> None:
        """关闭生命周期管理器"""
        async with self._lock:
            if self.state == LifecycleState.STOPPED:
                return
            
            self.state = LifecycleState.STOPPING
            self.logger.info("Shutting down skill lifecycle manager...")
            
            # 设置关闭事件
            self._shutdown_event.set()
            
            # 停止所有监控任务
            await self._stop_monitoring_tasks()
            
            # 停止所有技能
            await self._stop_all_skills()
            
            # 等待主任务完成
            if self._main_task and not self._main_task.done():
                try:
                    await asyncio.wait_for(self._main_task, timeout=self.config.timeout_shutdown)
                except asyncio.TimeoutError:
                    self.logger.warning("Main task did not complete within timeout")
            
            self.state = LifecycleState.STOPPED
            self.logger.info("Skill lifecycle manager stopped")
    
    async def _start_all_skills(self) -> None:
        """启动所有启用的技能"""
        auto_load_results = await self.skill_manager.load_all_skills()
        auto_activate_results = await self.skill_manager.activate_auto_skills()
        
        # 为每个技能创建监控器
        for skill_name in self.skill_manager.list_skills():
            await self._create_skill_watcher(skill_name)
    
    async def _stop_all_skills(self) -> None:
        """停止所有技能"""
        active_skills = self.skill_manager.list_skills({SkillStatus.ACTIVE, SkillStatus.INACTIVE})
        
        # 停止所有技能
        for skill_name in active_skills:
            try:
                await self.skill_manager.deactivate_skill(skill_name)
                await self.skill_manager.unload_skill(skill_name)
            except Exception as e:
                self.logger.error(f"Error stopping skill {skill_name}: {e}")
    
    async def _start_monitoring_tasks(self) -> None:
        """启动监控任务"""
        # 健康检查任务
        asyncio.create_task(self._health_check_loop())
        
        # 指标收集任务
        asyncio.create_task(self._metrics_collection_loop())
        
        # 清理任务
        asyncio.create_task(self._cleanup_loop())
    
    async def _stop_monitoring_tasks(self) -> None:
        """停止监控任务"""
        for watcher in self._skill_watchers.values():
            if not watcher.done():
                watcher.cancel()
        
        self._skill_watchers.clear()
    
    async def _main_loop(self) -> None:
        """主循环"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(1)
                
                # 检查技能状态
                await self._check_skill_states()
                
                # 处理自动重启
                if self.config.auto_restart_enabled:
                    await self._handle_auto_restart()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while not self._shutdown_event.is_set():
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(10)
    
    async def _metrics_collection_loop(self) -> None:
        """指标收集循环"""
        while not self._shutdown_event.is_set():
            try:
                await self._collect_metrics()
                await asyncio.sleep(self.config.metrics_collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(30)
    
    async def _cleanup_loop(self) -> None:
        """清理循环"""
        while not self._shutdown_event.is_set():
            try:
                await self._perform_cleanup()
                await asyncio.sleep(300)  # 5分钟清理一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(300)
    
    async def _check_skill_states(self) -> None:
        """检查技能状态"""
        for skill_name in self.skill_manager.list_skills():
            status = self.skill_manager.get_skill_status(skill_name)
            if not status:
                continue
            
            # 检查是否需要创建监控器
            if skill_name not in self._skill_watchers:
                await self._create_skill_watcher(skill_name)
            
            # 检查是否需要重启
            if status == SkillStatus.ERROR:
                await self._handle_skill_error(skill_name)
    
    async def _perform_health_checks(self) -> None:
        """执行健康检查"""
        for skill_name in self.skill_manager.list_skills():
            await self._check_skill_health(skill_name)
    
    async def _check_skill_health(self, skill_name: str) -> None:
        """检查单个技能健康状态"""
        try:
            skill_info = self.skill_manager.get_skill_info(skill_name)
            if not skill_info:
                return
            
            # 基础状态检查
            status = skill_info["status"]
            if status == "error":
                health_status = HealthStatus.CRITICAL
            elif status == "inactive":
                health_status = HealthStatus.WARNING
            elif status == "active":
                # 详细健康检查
                health_status = await self._detailed_health_check(skill_name)
            else:
                health_status = HealthStatus.UNKNOWN
            
            self._skill_health_status[skill_name] = health_status
            
            # 调用健康检查回调
            if self.config.on_health_check:
                try:
                    self.config.on_health_check(skill_name, health_status)
                except Exception as e:
                    self.logger.error(f"Error in health check callback for {skill_name}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error checking health for skill {skill_name}: {e}")
            self._skill_health_status[skill_name] = HealthStatus.CRITICAL
    
    async def _detailed_health_check(self, skill_name: str) -> HealthStatus:
        """详细健康检查"""
        try:
            # 获取技能实例
            skills = self.skill_manager.list_skills()
            if skill_name not in skills:
                return HealthStatus.UNKNOWN
            
            # 检查指标
            metrics = self._skill_metrics.get(skill_name)
            if metrics:
                # 检查错误率
                if metrics.error_count > metrics.execution_count * 0.1:  # 10%错误率
                    return HealthStatus.WARNING
                
                # 检查响应时间
                if metrics.average_execution_time > self.config.max_execution_time:
                    return HealthStatus.WARNING
            
            # 执行技能健康检查
            skill_instance = self._get_skill_instance(skill_name)
            if skill_instance and await skill_instance.health_check():
                return HealthStatus.HEALTHY
            else:
                return HealthStatus.CRITICAL
        
        except Exception as e:
            self.logger.error(f"Error in detailed health check for {skill_name}: {e}")
            return HealthStatus.CRITICAL
    
    async def _collect_metrics(self) -> None:
        """收集指标"""
        for skill_name in self.skill_manager.list_skills():
            await self._collect_skill_metrics(skill_name)
    
    async def _collect_skill_metrics(self, skill_name: str) -> None:
        """收集单个技能指标"""
        try:
            skill_info = self.skill_manager.get_skill_info(skill_name)
            if not skill_info:
                return
            
            # 获取或创建指标对象
            if skill_name not in self._skill_metrics:
                self._skill_metrics[skill_name] = SkillMetrics(
                    skill_name=skill_name,
                    status=skill_info["status"]
                )
            
            metrics = self._skill_metrics[skill_name]
            
            # 更新指标
            metrics.status = SkillStatus(skill_info["status"])
            metrics.execution_count = skill_info["metadata"]["usage_count"]
            
            # 更新执行时间统计
            if skill_name in self._execution_times:
                times = self._execution_times[skill_name]
                if times:
                    metrics.average_execution_time = sum(times) / len(times)
        
        except Exception as e:
            self.logger.error(f"Error collecting metrics for {skill_name}: {e}")
    
    async def _perform_cleanup(self) -> None:
        """执行清理"""
        try:
            # 清理旧的执行时间记录
            cutoff_time = datetime.now() - timedelta(hours=1)
            
            for skill_name in list(self._execution_times.keys()):
                times = self._execution_times[skill_name]
                # 这里可以添加时间过滤逻辑
            
            # 清理无效的指标
            active_skills = set(self.skill_manager.list_skills())
            invalid_metrics = set(self._skill_metrics.keys()) - active_skills
            
            for skill_name in invalid_metrics:
                del self._skill_metrics[skill_name]
                del self._skill_health_status[skill_name]
                self._execution_times.pop(skill_name, None)
        
        except Exception as e:
            self.logger.error(f"Error in cleanup: {e}")
    
    async def _create_skill_watcher(self, skill_name: str) -> None:
        """为技能创建监控器"""
        if skill_name in self._skill_watchers:
            return
        
        # 创建监控任务
        watcher = asyncio.create_task(self._watch_skill(skill_name))
        self._skill_watchers[skill_name] = watcher
    
    async def _watch_skill(self, skill_name: str) -> None:
        """监控单个技能"""
        while not self._shutdown_event.is_set():
            try:
                # 检查技能状态
                status = self.skill_manager.get_skill_status(skill_name)
                if not status:
                    await asyncio.sleep(5)
                    continue
                
                # 如果技能处于错误状态，尝试重启
                if status == SkillStatus.ERROR and self.config.auto_restart_enabled:
                    await self._restart_skill(skill_name)
                
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error watching skill {skill_name}: {e}")
                await asyncio.sleep(30)
    
    async def _handle_skill_error(self, skill_name: str) -> None:
        """处理技能错误"""
        try:
            self.logger.error(f"Handling error for skill {skill_name}")
            
            # 调用错误回调
            if self.config.on_skill_error:
                try:
                    self.config.on_skill_error(skill_name, Exception("Skill error"))
                except Exception as e:
                    self.logger.error(f"Error in skill error callback: {e}")
            
            # 自动重启
            if self.config.auto_restart_enabled:
                await self._restart_skill(skill_name)
        
        except Exception as e:
            self.logger.error(f"Error handling skill error for {skill_name}: {e}")
    
    async def _restart_skill(self, skill_name: str) -> None:
        """重启技能"""
        try:
            self.logger.info(f"Attempting to restart skill {skill_name}")
            
            # 卸载技能
            await self.skill_manager.unload_skill(skill_name)
            
            # 等待重启延迟
            await asyncio.sleep(self.config.restart_delay)
            
            # 重新加载
            metadata = self.skill_manager.registry.get_skill_metadata(skill_name)
            if metadata:
                await self.skill_manager.load_skill(metadata)
                await self.skill_manager.activate_skill(skill_name)
            
            self.logger.info(f"Successfully restarted skill {skill_name}")
        
        except Exception as e:
            self.logger.error(f"Failed to restart skill {skill_name}: {e}")
    
    def _get_skill_instance(self, skill_name: str) -> Optional[BaseSkill]:
        """获取技能实例"""
        # 这里需要从SkillManager中获取实例
        # 由于SkillManager没有直接暴露实例的方法，这里需要修改
        return None
    
    async def _handle_auto_restart(self) -> None:
        """处理自动重启"""
        # 检查需要重启的技能并重启
        pass
    
    # 公共接口方法
    
    async def restart_skill(self, skill_name: str) -> bool:
        """重启技能"""
        try:
            await self._restart_skill(skill_name)
            return True
        except Exception as e:
            self.logger.error(f"Failed to restart skill {skill_name}: {e}")
            return False
    
    async def force_health_check(self, skill_name: str) -> HealthStatus:
        """强制健康检查"""
        await self._check_skill_health(skill_name)
        return self._skill_health_status.get(skill_name, HealthStatus.UNKNOWN)
    
    def get_lifecycle_state(self) -> LifecycleState:
        """获取生命周期状态"""
        return self.state
    
    def get_skill_metrics(self, skill_name: Optional[str] = None) -> Dict[str, Any]:
        """获取技能指标"""
        if skill_name:
            metrics = self._skill_metrics.get(skill_name)
            return metrics.to_dict() if metrics else {}
        
        return {
            name: metrics.to_dict()
            for name, metrics in self._skill_metrics.items()
        }
    
    def get_health_status(self, skill_name: Optional[str] = None) -> Dict[str, Any]:
        """获取健康状态"""
        if skill_name:
            status = self._skill_health_status.get(skill_name)
            return {"skill_name": skill_name, "status": status.value if status else "unknown"}
        
        return {
            name: status.value for name, status in self._skill_health_status.items()
        }
    
    def get_lifecycle_info(self) -> Dict[str, Any]:
        """获取生命周期信息"""
        return {
            "state": self.state.value,
            "active_skills": len([s for s in self.skill_manager.list_skills() 
                                if self.skill_manager.get_skill_status(s) == SkillStatus.ACTIVE]),
            "total_skills": len(self.skill_manager.list_skills()),
            "config": {
                "health_check_interval": self.config.health_check_interval,
                "auto_restart_enabled": self.config.auto_restart_enabled,
                "metrics_collection_interval": self.config.metrics_collection_interval,
            }
        }