"""
Cron定时器处理器

提供基于cron表达式的定时任务调度功能
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import logging
from dataclasses import dataclass
from enum import Enum
import uuid


class CronField(Enum):
    """Cron字段枚举"""
    MINUTE = "minute"
    HOUR = "hour"
    DAY_OF_MONTH = "day_of_month"
    MONTH = "month"
    DAY_OF_WEEK = "day_of_week"


@dataclass
class CronExpression:
    """Cron表达式类"""
    expression: str
    minute: str = "*"
    hour: str = "*"
    day_of_month: str = "*"
    month: str = "*"
    day_of_week: str = "*"
    
    def __post_init__(self):
        parts = self.expression.strip().split()
        
        # 支持5部分或6部分cron表达式（忽略秒部分）
        if len(parts) == 5:
            self.minute, self.hour, self.day_of_month, self.month, self.day_of_week = parts
        elif len(parts) == 6:
            # 6部分格式: 秒 分 时 日 月 星期，忽略秒部分
            self.minute, self.hour, self.day_of_month, self.month, self.day_of_week = parts[1:]
        else:
            raise ValueError(f"Invalid cron expression: {self.expression} (must have 5 or 6 parts)")
    
    def get_next_run(self, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """计算下次运行时间"""
        if from_time is None:
            from_time = datetime.now()
        
        # 从下一秒开始计算
        next_time = from_time + timedelta(seconds=1)
        
        # 最大尝试次数（防止无限循环）
        for _ in range(10000):
            if self._matches(next_time):
                return next_time
            next_time += timedelta(seconds=1)
        
        return None
    
    def _matches(self, dt: datetime) -> bool:
        """检查时间是否匹配cron表达式"""
        return (
            self._match_field(self.minute, dt.minute, 0, 59) and
            self._match_field(self.hour, dt.hour, 0, 23) and
            self._match_field(self.day_of_month, dt.day, 1, 31) and
            self._match_field(self.month, dt.month, 1, 12) and
            self._match_field(self.day_of_week, dt.weekday() + 1, 1, 7)  # 周一=1, 周日=7
        )
    
    def _match_field(self, pattern: str, value: int, min_val: int, max_val: int) -> bool:
        """匹配单个cron字段"""
        pattern = pattern.strip()
        
        # 通配符
        if pattern == "*":
            return True
        
        # 步长（如：*/5 表示每5个单位）
        if "/" in pattern:
            parts = pattern.split("/")
            if len(parts) != 2:
                return False
            try:
                step = int(parts[1])
                base = 0 if parts[0] == "*" else int(parts[0])
                return (value - base) % step == 0 and value >= base
            except ValueError:
                return False
        
        # 范围（如：1-5 表示1到5）
        if "-" in pattern:
            parts = pattern.split("-")
            if len(parts) != 2:
                return False
            try:
                start, end = int(parts[0]), int(parts[1])
                return start <= value <= end
            except ValueError:
                return False
        
        # 列表（如：1,3,5 表示1、3、5）
        if "," in pattern:
            for part in pattern.split(","):
                if self._match_field(part.strip(), value, min_val, max_val):
                    return True
            return False
        
        # 单个值
        try:
            return int(pattern) == value
        except ValueError:
            return False


@dataclass
class ScheduledTask:
    """定时任务"""
    id: str
    name: str
    cron_expression: CronExpression
    func: Callable
    args: tuple = None
    kwargs: dict = None
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    max_runs: Optional[int] = None
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.args is None:
            self.args = ()
        if self.kwargs is None:
            self.kwargs = {}
        if self.metadata is None:
            self.metadata = {}


class CronHandler:
    """Cron定时器处理器"""
    
    def __init__(self, task_manager=None):
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.task_manager = task_manager
        self.logger = logging.getLogger(__name__)
        self._scheduler_task: Optional[asyncio.Task] = None
        
        # 任务执行回调
        self.execution_callbacks: List[Callable] = []
        
    async def start(self):
        """启动定时器"""
        if self.running:
            return
        
        self.running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        self.logger.info("CronHandler started")
    
    async def stop(self):
        """停止定时器"""
        if not self.running:
            return
        
        self.running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("CronHandler stopped")
    
    def add_scheduled_task(
        self,
        name: str,
        cron_expression: str,
        func: Callable,
        args: tuple = None,
        kwargs: dict = None,
        enabled: bool = True,
        max_runs: Optional[int] = None,
        timeout: Optional[float] = None,
        task_id: Optional[str] = None
    ) -> str:
        """添加定时任务"""
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        try:
            cron_expr = CronExpression(cron_expression)
        except ValueError as e:
            raise ValueError(f"Invalid cron expression: {e}")
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            cron_expression=cron_expr,
            func=func,
            args=args or (),
            kwargs=kwargs or {},
            enabled=enabled,
            max_runs=max_runs,
            timeout=timeout
        )
        
        # 计算下次运行时间
        task.next_run = cron_expr.get_next_run()
        
        self.scheduled_tasks[task_id] = task
        
        self.logger.info(f"Scheduled task added: {task_id} - {name} ({cron_expression})")
        return task_id
    
    def remove_scheduled_task(self, task_id: str) -> bool:
        """移除定时任务"""
        if task_id in self.scheduled_tasks:
            del self.scheduled_tasks[task_id]
            self.logger.info(f"Scheduled task removed: {task_id}")
            return True
        return False
    
    def enable_scheduled_task(self, task_id: str) -> bool:
        """启用定时任务"""
        if task_id in self.scheduled_tasks:
            task = self.scheduled_tasks[task_id]
            task.enabled = True
            task.next_run = task.cron_expression.get_next_run()
            self.logger.info(f"Scheduled task enabled: {task_id}")
            return True
        return False
    
    def disable_scheduled_task(self, task_id: str) -> bool:
        """禁用定时任务"""
        if task_id in self.scheduled_tasks:
            task = self.scheduled_tasks[task_id]
            task.enabled = False
            task.next_run = None
            self.logger.info(f"Scheduled task disabled: {task_id}")
            return True
        return False
    
    def get_scheduled_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取定时任务"""
        return self.scheduled_tasks.get(task_id)
    
    def list_scheduled_tasks(self, enabled_only: bool = False) -> List[ScheduledTask]:
        """列出所有定时任务"""
        tasks = list(self.scheduled_tasks.values())
        if enabled_only:
            tasks = [t for t in tasks if t.enabled]
        return tasks
    
    def get_next_runs(self, count: int = 10) -> List[tuple]:
        """获取下次运行的任务"""
        upcoming = []
        
        for task in self.scheduled_tasks.values():
            if task.enabled and task.next_run:
                upcoming.append((task.id, task.name, task.next_run))
        
        # 按时间排序
        upcoming.sort(key=lambda x: x[2])
        
        return upcoming[:count]
    
    def run_task_now(self, task_id: str) -> bool:
        """立即运行任务"""
        if task_id not in self.scheduled_tasks:
            return False
        
        task = self.scheduled_tasks[task_id]
        
        # 异步执行任务
        asyncio.create_task(self._execute_scheduled_task(task))
        
        self.logger.info(f"Scheduled task run manually: {task_id}")
        return True
    
    def add_execution_callback(self, callback: Callable):
        """添加任务执行回调"""
        self.execution_callbacks.append(callback)
    
    async def _scheduler_loop(self):
        """调度器主循环"""
        while self.running:
            try:
                now = datetime.now()
                
                # 检查哪些任务需要执行
                tasks_to_run = []
                
                for task in self.scheduled_tasks.values():
                    if (task.enabled and 
                        task.next_run and 
                        now >= task.next_run):
                        
                        # 检查是否达到最大运行次数
                        if task.max_runs is not None and task.run_count >= task.max_runs:
                            task.enabled = False
                            task.next_run = None
                            continue
                        
                        tasks_to_run.append(task)
                
                # 执行到期的任务
                for task in tasks_to_run:
                    await self._execute_scheduled_task(task)
                
                # 等待下次检查
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(5)  # 出错后等待更长时间
    
    async def _execute_scheduled_task(self, task: ScheduledTask):
        """执行定时任务"""
        start_time = datetime.now()
        
        try:
            # 更新任务状态
            task.last_run = start_time
            task.run_count += 1
            
            # 执行任务函数
            if task.timeout:
                # 带超时的执行
                try:
                    if asyncio.iscoroutinefunction(task.func):
                        result = await asyncio.wait_for(
                            task.func(*task.args, **task.kwargs),
                            timeout=task.timeout
                        )
                    else:
                        result = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None, task.func, *task.args, **task.kwargs
                            ),
                            timeout=task.timeout
                        )
                except asyncio.TimeoutError:
                    raise TimeoutError(f"Task {task.id} timed out after {task.timeout} seconds")
            else:
                # 正常执行
                if asyncio.iscoroutinefunction(task.func):
                    result = await task.func(*task.args, **task.kwargs)
                else:
                    result = task.func(*task.args, **task.kwargs)
            
            # 计算下次运行时间
            if task.enabled and (task.max_runs is None or task.run_count < task.max_runs):
                task.next_run = task.cron_expression.get_next_run()
            else:
                task.enabled = False
                task.next_run = None
            
            # 触发执行回调
            for callback in self.execution_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(task, result, None)
                    else:
                        callback(task, result, None)
                except Exception as e:
                    self.logger.error(f"Execution callback error: {e}")
            
            self.logger.info(f"Scheduled task executed: {task.id} - {task.name}")
            
        except Exception as e:
            error_msg = f"Scheduled task failed: {task.id} - {e}"
            self.logger.error(error_msg)
            
            # 触发错误回调
            for callback in self.execution_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(task, None, str(e))
                    else:
                        callback(task, None, str(e))
                except Exception as cb_error:
                    self.logger.error(f"Error callback error: {cb_error}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        total_tasks = len(self.scheduled_tasks)
        enabled_tasks = sum(1 for t in self.scheduled_tasks.values() if t.enabled)
        
        total_runs = sum(t.run_count for t in self.scheduled_tasks.values())
        
        # 计算下次运行的任务
        next_runs = self.get_next_runs()
        
        return {
            'total_scheduled_tasks': total_tasks,
            'enabled_tasks': enabled_tasks,
            'disabled_tasks': total_tasks - enabled_tasks,
            'total_runs': total_runs,
            'upcoming_runs': len(next_runs),
            'next_run': next_runs[0][2] if next_runs else None
        }
    
    @staticmethod
    def validate_cron_expression(expression: str) -> bool:
        """验证cron表达式格式"""
        try:
            CronExpression(expression)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def get_common_expressions() -> Dict[str, str]:
        """获取常用cron表达式"""
        return {
            "每分钟": "* * * * *",
            "每5分钟": "*/5 * * * *",
            "每15分钟": "*/15 * * * *",
            "每小时": "0 * * * *",
            "每天凌晨": "0 0 * * *",
            "每天上午9点": "0 9 * * *",
            "每周一上午9点": "0 9 * * 1",
            "每月1号上午9点": "0 9 1 * *",
            "工作日每天上午9点": "0 9 * * 1-5",
            "每季度第一天": "0 0 1 1,4,7,10 *"
        }
    
    def cleanup_disabled_tasks(self):
        """清理已禁用的任务"""
        disabled_tasks = [
            task_id for task_id, task in self.scheduled_tasks.items()
            if not task.enabled and task.max_runs is not None and task.run_count >= task.max_runs
        ]
        
        for task_id in disabled_tasks:
            del self.scheduled_tasks[task_id]
            self.logger.info(f"Cleaned up disabled task: {task_id}")
        
        return len(disabled_tasks)