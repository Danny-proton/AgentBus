#!/usr/bin/env python3
"""
技能管理器
Skill Manager

负责技能的生命周期管理、执行调度、7*24小时运行
"""

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
import inspect
import importlib
import importlib.util

from ..core.logger import get_logger
from ..core.config import settings
from .base import BaseSkill, SkillType, SkillStatus, SkillContext, SkillResult
from .memory import get_memory_store, MemoryQuery

logger = get_logger(__name__)


class SkillExecutionMode(Enum):
    """技能执行模式"""
    IMMEDIATE = "immediate"        # 立即执行
    QUEUED = "queued"            # 排队执行
    SCHEDULED = "scheduled"      # 定时执行
    BACKGROUND = "background"     # 后台执行
    CONTINUOUS = "continuous"     # 持续执行（7*24小时）


@dataclass
class ScheduledSkill:
    """定时技能配置"""
    skill_name: str
    interval: timedelta  # 执行间隔
    next_execution: datetime
    enabled: bool = True
    max_runs: Optional[int] = None  # 最大运行次数，None表示无限制
    runs_so_far: int = 0
    parameters: Dict[str, Any] = field(default_factory=dict)
    last_result: Optional[SkillResult] = None


class SkillManager:
    """
    技能管理器
    
    功能：
    - 技能注册和管理
    - 技能执行调度
    - 定时任务（7*24小时运行）
    - 记忆系统集成
    - 技能生命周期管理
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        
        # 技能注册表
        self.skills: Dict[str, BaseSkill] = {}
        self.skill_metadata: Dict[str, Any] = {}
        
        # 执行调度
        self.execution_queue: asyncio.Queue = asyncio.Queue()
        self.execution_tasks: Dict[str, asyncio.Task] = {}
        self.scheduled_skills: Dict[str, ScheduledSkill] = {}
        
        # 状态管理
        self.is_running = False
        self.main_loop_task: Optional[asyncio.Task] = None
        self.scheduler_task: Optional[asyncio.Task] = None
        
        # 统计信息
        self.stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "last_execution": None,
            "active_schedules": 0,
            "running_skills": set()
        }
        
        # 记忆系统集成
        self.memory_store = None
        
        logger.info("SkillManager initialized")
    
    async def start(self) -> None:
        """启动技能管理器"""
        if self.is_running:
            return
        
        self.is_running = True
        self.logger.info("Starting SkillManager...")
        
        # 初始化记忆系统
        self.memory_store = await get_memory_store()
        
        # 启动主执行循环
        self.main_loop_task = asyncio.create_task(self._main_execution_loop())
        
        # 启动调度器
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        # 自动加载内置技能
        await self._load_builtin_skills()
        
        # 加载配置中的技能
        await self._load_configured_skills()
        
        self.logger.info("SkillManager started successfully")
    
    async def stop(self) -> None:
        """停止技能管理器"""
        if not self.is_running:
            return
        
        self.logger.info("Stopping SkillManager...")
        self.is_running = False
        
        # 取消主执行循环
        if self.main_loop_task and not self.main_loop_task.done():
            self.main_loop_task.cancel()
        
        # 取消调度器
        if self.scheduler_task and not self.scheduler_task.done():
            self.scheduler_task.cancel()
        
        # 取消所有执行任务
        for task in self.execution_tasks.values():
            if not task.done():
                task.cancel()
        
        # 等待任务完成
        if self.main_loop_task:
            try:
                await self.main_loop_task
            except asyncio.CancelledError:
                pass
        
        if self.scheduler_task:
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("SkillManager stopped")
    
    async def register_skill(self, skill: BaseSkill, metadata: Dict[str, Any] = None) -> None:
        """注册技能"""
        skill_name = skill.metadata.name
        
        if skill_name in self.skills:
            self.logger.warning("Skill already registered", skill=skill_name)
            return
        
        self.skills[skill_name] = skill
        self.skill_metadata[skill_name] = metadata or {}
        
        # 初始化技能
        await skill.initialize()
        
        self.logger.info("Skill registered", 
                        skill=skill_name,
                        skill_type=skill.metadata.skill_type.value,
                        status=skill.status.value)
    
    async def unregister_skill(self, skill_name: str) -> bool:
        """取消注册技能"""
        if skill_name not in self.skills:
            return False
        
        skill = self.skills[skill_name]
        
        # 清理技能
        await skill.cleanup()
        
        # 从注册表中移除
        del self.skills[skill_name]
        del self.skill_metadata[skill_name]
        
        # 取消相关定时任务
        if skill_name in self.scheduled_skills:
            del self.scheduled_skills[skill_name]
        
        self.logger.info("Skill unregistered", skill=skill_name)
        return True
    
    async def execute_skill(
        self, 
        skill_name: str, 
        context: SkillContext,
        mode: SkillExecutionMode = SkillExecutionMode.IMMEDIATE,
        **kwargs
    ) -> SkillResult:
        """执行技能"""
        if skill_name not in self.skills:
            return SkillResult.error(f"Skill '{skill_name}' not found")
        
        skill = self.skills[skill_name]
        
        if not skill.is_active:
            return SkillResult.error(f"Skill '{skill_name}' is not active")
        
        # 记录开始执行
        self.stats["running_skills"].add(skill_name)
        
        try:
            if mode == SkillExecutionMode.QUEUED:
                # 添加到执行队列
                task_data = {
                    "skill_name": skill_name,
                    "context": context,
                    "kwargs": kwargs
                }
                await self.execution_queue.put(task_data)
                return SkillResult.success("Task queued for execution")
            
            elif mode == SkillExecutionMode.BACKGROUND:
                # 后台执行，不等待结果
                task = asyncio.create_task(self._execute_skill_async(skill_name, context, **kwargs))
                return SkillResult.success("Task started in background")
            
            else:
                # 立即执行或调度执行
                result = await self._execute_skill_async(skill_name, context, **kwargs)
                return result
        
        except Exception as e:
            self.logger.error("Skill execution failed", 
                           skill=skill_name, 
                           error=str(e))
            return SkillResult.error(f"Execution failed: {str(e)}")
        
        finally:
            self.stats["running_skills"].discard(skill_name)
    
    async def schedule_skill(
        self,
        skill_name: str,
        interval: timedelta,
        max_runs: Optional[int] = None,
        parameters: Dict[str, Any] = None,
        start_now: bool = True
    ) -> bool:
        """调度技能（实现7*24小时运行）"""
        if skill_name not in self.skills:
            return False
        
        scheduled_skill = ScheduledSkill(
            skill_name=skill_name,
            interval=interval,
            next_execution=datetime.now() if start_now else datetime.now() + interval,
            max_runs=max_runs,
            parameters=parameters or {}
        )
        
        self.scheduled_skills[skill_name] = scheduled_skill
        self.stats["active_schedules"] = len(self.scheduled_skills)
        
        self.logger.info("Skill scheduled", 
                        skill=skill_name,
                        interval=str(interval),
                        max_runs=max_runs)
        
        return True
    
    async def cancel_schedule(self, skill_name: str) -> bool:
        """取消技能调度"""
        if skill_name not in self.scheduled_skills:
            return False
        
        del self.scheduled_skills[skill_name]
        self.stats["active_schedules"] = len(self.scheduled_skills)
        
        self.logger.info("Skill schedule cancelled", skill=skill_name)
        return True
    
    async def get_skill_status(self, skill_name: str) -> Dict[str, Any]:
        """获取技能状态"""
        if skill_name not in self.skills:
            return {"error": "Skill not found"}
        
        skill = self.skills[skill_name]
        
        return {
            "name": skill_name,
            "status": skill.status.value,
            "type": skill.metadata.skill_type.value,
            "description": skill.metadata.description,
            "is_active": skill.is_active,
            "scheduled": skill_name in self.scheduled_skills,
            "metadata": self.skill_metadata.get(skill_name, {})
        }
    
    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有技能"""
        skill_list = []
        for skill_name, skill in self.skills.items():
            skill_info = {
                "name": skill_name,
                "type": skill.metadata.skill_type.value,
                "status": skill.status.value,
                "description": skill.metadata.description,
                "is_active": skill.is_active,
                "scheduled": skill_name in self.scheduled_skills
            }
            skill_list.append(skill_info)
        return skill_list
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "total_skills": len(self.skills),
            "active_schedules": len(self.scheduled_skills),
            "running_skills": list(self.stats["running_skills"])
        }
    
    async def _execute_skill_async(self, skill_name: str, context: SkillContext, **kwargs) -> SkillResult:
        """异步执行技能"""
        skill = self.skills[skill_name]
        
        start_time = datetime.now()
        self.stats["total_executions"] += 1
        
        try:
            # 集成记忆系统
            if self.memory_store:
                context.data["memory_store"] = self.memory_store
            
            # 执行技能
            result = await skill.execute(context)
            
            # 更新统计
            if result.success:
                self.stats["successful_executions"] += 1
            else:
                self.stats["failed_executions"] += 1
            
            self.stats["last_execution"] = datetime.now().isoformat()
            
            # 记录到记忆系统
            if self.memory_store and result.success:
                await self._store_execution_memory(skill_name, context, result)
            
            self.logger.debug("Skill executed successfully", 
                            skill=skill_name,
                            execution_time=(datetime.now() - start_time).total_seconds())
            
            return result
        
        except Exception as e:
            self.stats["failed_executions"] += 1
            self.logger.error("Skill execution error", 
                            skill=skill_name, 
                            error=str(e))
            return SkillResult.error(f"Execution error: {str(e)}")
    
    async def _main_execution_loop(self) -> None:
        """主执行循环"""
        self.logger.info("Main execution loop started")
        
        while self.is_running:
            try:
                # 从队列获取任务
                task_data = await asyncio.wait_for(
                    self.execution_queue.get(), 
                    timeout=1.0
                )
                
                skill_name = task_data["skill_name"]
                context = task_data["context"]
                kwargs = task_data.get("kwargs", {})
                
                # 创建执行任务
                task = asyncio.create_task(
                    self._execute_skill_async(skill_name, context, **kwargs)
                )
                
                # 保存任务引用
                task_id = f"queue_{datetime.now().timestamp()}"
                self.execution_tasks[task_id] = task
                
                # 清理已完成的任务
                completed_tasks = [
                    tid for tid, t in self.execution_tasks.items() 
                    if t.done()
                ]
                for tid in completed_tasks:
                    del self.execution_tasks[tid]
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error("Execution loop error", error=str(e))
    
    async def _scheduler_loop(self) -> None:
        """调度器循环（实现7*24小时运行）"""
        self.logger.info("Scheduler loop started for 24/7 operation")
        
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # 检查需要执行的定时技能
                for skill_name, scheduled in self.scheduled_skills.items():
                    if (scheduled.enabled and 
                        scheduled.next_execution <= current_time):
                        
                        # 检查运行次数限制
                        if (scheduled.max_runs is not None and 
                            scheduled.runs_so_far >= scheduled.max_runs):
                            continue
                        
                        # 创建执行上下文
                        context = self._create_schedule_context(skill_name, scheduled)
                        
                        # 执行技能
                        result = await self._execute_skill_async(skill_name, context, **scheduled.parameters)
                        
                        # 更新调度信息
                        scheduled.runs_so_far += 1
                        scheduled.last_result = result
                        scheduled.next_execution = current_time + scheduled.interval
                        
                        # 如果达到最大运行次数，禁用调度
                        if (scheduled.max_runs is not None and 
                            scheduled.runs_so_far >= scheduled.max_runs):
                            scheduled.enabled = False
                            self.logger.info("Scheduled skill completed max runs", 
                                          skill=skill_name,
                                          runs=scheduled.runs_so_far)
                
                # 每分钟检查一次
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error("Scheduler loop error", error=str(e))
                await asyncio.sleep(60)
    
    async def _load_builtin_skills(self) -> None:
        """加载内置技能"""
        try:
            from ..skills.base import SkillRegistry, SkillStatus
            
            # 从 SkillRegistry 获取所有注册的技能
            for skill_name, skill_class in SkillRegistry.get_all_skills().items():
                try:
                    # 动态创建技能实例
                    skill_instance = skill_class()
                    
                    # 激活技能
                    skill_instance.status = SkillStatus.ACTIVE
                    
                    # 注册到管理器
                    self.skills[skill_name] = skill_instance
                    self.logger.info(f"Loaded built-in skill: {skill_name}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to load built-in skill {skill_name}: {e}")
                    
            self.logger.info(f"Loaded {len(self.skills)} built-in skills")
            
        except ImportError as e:
            self.logger.error(f"Failed to import SkillRegistry: {e}")
    
    async def _load_configured_skills(self) -> None:
        """加载配置中的技能"""
        # 暂时跳过配置技能加载，在测试阶段只使用内置技能
        self.logger.info("Configured skills loading skipped for testing")
    
    def _create_schedule_context(self, skill_name: str, scheduled: ScheduledSkill) -> SkillContext:
        """创建定时执行的上下文"""
        # 创建虚拟用户和消息（用于定时任务）
        from ..adapters.base import User, Message, AdapterType
        
        user = User(
            id="system",
            platform=AdapterType.WEB,
            username="system",
            display_name="System",
            is_bot=True,
            is_admin=True
        )
        
        message = Message(
            id=f"schedule_{skill_name}_{datetime.now().timestamp()}",
            platform=AdapterType.WEB,
            chat_id="schedule",
            user_id="system",
            content=f"Scheduled execution of {skill_name}",
            message_type="text"
        )
        
        return SkillContext(
            user=user,
            message=message,
            chat_id="schedule",
            platform=AdapterType.WEB,
            session_id="schedule",
            data={
                "scheduled_execution": True,
                "run_count": scheduled.runs_so_far,
                "max_runs": scheduled.max_runs
            }
        )
    
    async def _store_execution_memory(self, skill_name: str, context: SkillContext, result: SkillResult) -> None:
        """存储执行记忆"""
        try:
            memory_content = f"""
技能执行记录：
- 技能名称：{skill_name}
- 执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 用户：{context.user.username}
- 平台：{context.platform.value}
- 输入：{context.get_user_input()[:200]}...
- 结果：{'成功' if result.success else '失败'}
- 执行时间：{result.execution_time:.2f}秒
"""
            
            tags = {"skill_execution", skill_name, context.platform.value}
            
            await self.memory_store.store_memory(
                content=memory_content,
                tags=tags,
                importance=2 if result.success else 3,  # 失败的记录更重要
                source="skill_manager",
                metadata={
                    "skill_name": skill_name,
                    "execution_time": result.execution_time,
                    "success": result.success
                }
            )
        
        except Exception as e:
            self.logger.error("Failed to store execution memory", error=str(e))


# 全局技能管理器实例
_skill_manager: Optional[SkillManager] = None


async def get_skill_manager() -> SkillManager:
    """获取全局技能管理器实例"""
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
        await _skill_manager.start()
    return _skill_manager


async def start_skill_system() -> SkillManager:
    """启动技能系统"""
    manager = await get_skill_manager()
    await manager.start()
    return manager


async def stop_skill_system() -> None:
    """停止技能系统"""
    global _skill_manager
    if _skill_manager:
        await _skill_manager.stop()
        _skill_manager = None
