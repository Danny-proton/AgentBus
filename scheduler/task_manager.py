"""
任务管理器

负责管理AgentBus中的所有任务，包括：
- 任务创建、删除、更新
- 任务状态跟踪和管理
- 任务调度和执行
- 失败重试和超时处理
- 任务依赖管理
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union
import logging
from dataclasses import dataclass, asdict
import threading
import time


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    RETRYING = "retrying"
    TIMEOUT = "timeout"


class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskConfig:
    """任务配置"""
    max_retries: int = 3
    retry_delay: float = 60.0  # 重试延迟（秒）
    timeout: Optional[float] = None  # 超时时间（秒）
    dependencies: List[str] = None  # 依赖的任务ID列表
    priority: TaskPriority = TaskPriority.NORMAL
    auto_retry: bool = True
    retry_backoff: float = 2.0  # 重试退避倍数
    description: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Task:
    """任务数据类"""
    id: str
    name: str
    func: Callable
    args: tuple = None
    kwargs: dict = None
    status: TaskStatus = TaskStatus.PENDING
    config: TaskConfig = None
    created_at: datetime = None
    updated_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_error: Optional[str] = None
    retry_count: int = 0
    result: Optional[TaskResult] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.args is None:
            self.args = ()
        if self.kwargs is None:
            self.kwargs = {}
        if self.config is None:
            self.config = TaskConfig()
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = self.created_at
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data['status'] = self.status.value
        data['priority'] = self.config.priority.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        if self.result:
            data['result'] = asdict(self.result)
            data['result']['timestamp'] = self.result.timestamp.isoformat()
        return data


class TaskManager:
    """任务管理器"""
    
    def __init__(self, storage_path: Optional[str] = None, max_workers: int = 5):
        self.storage_path = Path(storage_path) if storage_path else Path("./data/tasks")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Set[str] = set()
        self.task_lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # 线程池执行器
        self.max_workers = max_workers
        self.executor = None
        
        # 任务事件回调
        self.task_callbacks: Dict[str, List[Callable]] = {
            'created': [],
            'started': [],
            'completed': [],
            'failed': [],
            'cancelled': [],
            'paused': [],
            'resumed': []
        }
        
        # 加载持久化任务
        self._load_tasks()
        
    async def start(self):
        """启动任务管理器"""
        # 创建线程池执行器
        self.executor = asyncio.get_event_loop().run_in_executor
        
        # 恢复运行中的任务
        await self._recover_running_tasks()
        
        self.logger.info(f"TaskManager started with {len(self.tasks)} tasks")
    
    async def stop(self):
        """停止任务管理器"""
        # 取消所有运行中的任务
        running_task_ids = list(self.running_tasks)
        for task_id in running_task_ids:
            await self.cancel_task(task_id)
        
        self.logger.info("TaskManager stopped")
    
    def create_task(
        self,
        name: str,
        func: Callable,
        args: tuple = None,
        kwargs: dict = None,
        config: TaskConfig = None,
        task_id: Optional[str] = None
    ) -> str:
        """创建任务"""
        if task_id is None:
            task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            name=name,
            func=func,
            args=args or (),
            kwargs=kwargs or {},
            config=config or TaskConfig()
        )
        
        with self.task_lock:
            self.tasks[task_id] = task
        
        self._save_task(task)
        self._emit_callback('created', task)
        
        self.logger.info(f"Task created: {task_id} - {name}")
        return task_id
    
    async def start_task(self, task_id: str, force: bool = False) -> bool:
        """启动任务"""
        with self.task_lock:
            if task_id not in self.tasks:
                self.logger.error(f"Task not found: {task_id}")
                return False
            
            task = self.tasks[task_id]
            
            # 检查任务状态
            if not force and task.status in [TaskStatus.RUNNING, TaskStatus.COMPLETED]:
                self.logger.warning(f"Task cannot start: {task_id} - current status: {task.status.value}")
                return False
            
            # 检查依赖任务
            if not self._check_dependencies(task):
                self.logger.warning(f"Task dependencies not satisfied: {task_id}")
                return False
            
            # 更新任务状态
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now()
            task.updated_at = task.started_at
            task.retry_count = 0
            self.running_tasks.add(task_id)
        
        self._emit_callback('started', task)
        
        # 异步执行任务
        asyncio.create_task(self._execute_task(task))
        
        self.logger.info(f"Task started: {task_id}")
        return True
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self.task_lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                return False
            
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            task.updated_at = task.completed_at
            self.running_tasks.discard(task_id)
        
        self._emit_callback('cancelled', task)
        self._save_task(task)
        
        self.logger.info(f"Task cancelled: {task_id}")
        return True
    
    async def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        with self.task_lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status != TaskStatus.RUNNING:
                return False
            
            task.status = TaskStatus.PAUSED
            task.updated_at = datetime.now()
            self.running_tasks.discard(task_id)
        
        self._emit_callback('paused', task)
        self._save_task(task)
        
        self.logger.info(f"Task paused: {task_id}")
        return True
    
    async def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        with self.task_lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status != TaskStatus.PAUSED:
                return False
            
            task.status = TaskStatus.RUNNING
            self.running_tasks.add(task_id)
            task.updated_at = datetime.now()
        
        # 重新执行任务
        asyncio.create_task(self._execute_task(task))
        
        self._emit_callback('resumed', task)
        self._save_task(task)
        
        self.logger.info(f"Task resumed: {task_id}")
        return True
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None
    ) -> List[Task]:
        """获取任务列表"""
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        if priority:
            tasks = [t for t in tasks if t.config.priority == priority]
        
        # 按优先级和创建时间排序
        tasks.sort(key=lambda t: (t.config.priority.value, t.created_at))
        
        return tasks
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        with self.task_lock:
            if task_id not in self.tasks:
                return False
            
            # 如果任务正在运行，先取消
            if task_id in self.running_tasks:
                asyncio.create_task(self.cancel_task(task_id))
            
            del self.tasks[task_id]
        
        # 删除持久化文件
        task_file = self.storage_path / f"{task_id}.json"
        if task_file.exists():
            task_file.unlink()
        
        self.logger.info(f"Task deleted: {task_id}")
        return True
    
    def update_task_config(self, task_id: str, config: TaskConfig) -> bool:
        """更新任务配置"""
        with self.task_lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.config = config
            task.updated_at = datetime.now()
        
        self._save_task(task)
        return True
    
    def add_callback(self, event: str, callback: Callable):
        """添加任务事件回调"""
        if event in self.task_callbacks:
            self.task_callbacks[event].append(callback)
    
    def remove_callback(self, event: str, callback: Callable):
        """移除任务事件回调"""
        if event in self.task_callbacks:
            try:
                self.task_callbacks[event].remove(callback)
            except ValueError:
                pass
    
    def get_task_stats(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        stats = {
            'total': len(self.tasks),
            'pending': 0,
            'running': 0,
            'completed': 0,
            'failed': 0,
            'cancelled': 0,
            'paused': 0
        }
        
        for task in self.tasks.values():
            stats[task.status.value] += 1
        
        return stats
    
    async def _execute_task(self, task: Task):
        """执行任务"""
        try:
            start_time = time.time()
            
            # 检查超时
            if task.config.timeout:
                # 这里应该使用asyncio.wait_for来设置超时
                pass
            
            # 执行任务函数
            if asyncio.iscoroutinefunction(task.func):
                result_data = await task.func(*task.args, **task.kwargs)
            else:
                result_data = task.func(*task.args, **task.kwargs)
            
            execution_time = time.time() - start_time
            
            # 创建成功结果
            result = TaskResult(
                success=True,
                data=result_data,
                execution_time=execution_time,
                retry_count=task.retry_count
            )
            
            await self._complete_task(task, result)
            
        except asyncio.TimeoutError:
            error_msg = f"Task timeout after {task.config.timeout} seconds"
            await self._fail_task(task, error_msg, is_timeout=True)
            
        except Exception as e:
            error_msg = str(e)
            await self._fail_task(task, error_msg)
    
    async def _complete_task(self, task: Task, result: TaskResult):
        """完成任务"""
        with self.task_lock:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.updated_at = task.completed_at
            task.result = result
            task.progress = 1.0
            self.running_tasks.discard(task.id)
        
        self._emit_callback('completed', task)
        self._save_task(task)
        
        self.logger.info(f"Task completed: {task.id} in {result.execution_time:.2f}s")
    
    async def _fail_task(self, task: Task, error_msg: str, is_timeout: bool = False):
        """任务失败处理"""
        with self.task_lock:
            task.last_error = error_msg
            task.updated_at = datetime.now()
            self.running_tasks.discard(task.id)
            
            # 检查是否需要重试
            if task.config.auto_retry and task.retry_count < task.config.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                
                # 计算重试延迟
                delay = task.config.retry_delay * (task.config.retry_backoff ** (task.retry_count - 1))
                
                self.logger.warning(f"Task failed, retrying in {delay:.1f}s: {task.id} - {error_msg}")
                
                # 安排重试
                asyncio.create_task(self._schedule_retry(task, delay))
                return
            
            # 设置最终状态
            if is_timeout:
                task.status = TaskStatus.TIMEOUT
            else:
                task.status = TaskStatus.FAILED
            
            result = TaskResult(
                success=False,
                error=error_msg,
                retry_count=task.retry_count
            )
            task.result = result
        
        self._emit_callback('failed', task)
        self._save_task(task)
        
        self.logger.error(f"Task failed permanently: {task.id} - {error_msg}")
    
    async def _schedule_retry(self, task: Task, delay: float):
        """安排任务重试"""
        await asyncio.sleep(delay)
        
        with self.task_lock:
            if task.id not in self.tasks:
                return
            
            # 重新检查依赖
            if not self._check_dependencies(task):
                self.logger.warning(f"Task dependencies still not satisfied for retry: {task.id}")
                task.status = TaskStatus.FAILED
                self._save_task(task)
                return
            
            task.status = TaskStatus.RUNNING
            task.updated_at = datetime.now()
            self.running_tasks.add(task.id)
        
        # 重新执行任务
        asyncio.create_task(self._execute_task(task))
    
    def _check_dependencies(self, task: Task) -> bool:
        """检查任务依赖"""
        if not task.config.dependencies:
            return True
        
        for dep_id in task.config.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    def _emit_callback(self, event: str, task: Task):
        """触发事件回调"""
        if event in self.task_callbacks:
            for callback in self.task_callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(task))
                    else:
                        callback(task)
                except Exception as e:
                    self.logger.error(f"Callback error for event {event}: {e}")
    
    def _save_task(self, task: Task):
        """保存任务到持久化存储"""
        try:
            task_file = self.storage_path / f"{task.id}.json"
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save task {task.id}: {e}")
    
    def _load_tasks(self):
        """从持久化存储加载任务"""
        try:
            for task_file in self.storage_path.glob("*.json"):
                with open(task_file, 'r', encoding='utf-8') as f:
                    task_data = json.load(f)
                
                # 重建Task对象
                task_id = task_data['id']
                # 这里需要更复杂的重建逻辑，包括datetime和枚举的转换
                # 简化版本：只加载状态为PENDING或PAUSED的任务
                
                if task_data['status'] in ['pending', 'paused']:
                    # 重新创建任务对象（这里简化处理）
                    pass
                    
        except Exception as e:
            self.logger.error(f"Failed to load tasks: {e}")
    
    async def _recover_running_tasks(self):
        """恢复运行中的任务"""
        # 简化处理：假设所有非最终状态的任务都需要恢复
        for task in self.tasks.values():
            if task.status in [TaskStatus.RUNNING, TaskStatus.RETRYING]:
                task.status = TaskStatus.PENDING
                task.updated_at = datetime.now()
                self._save_task(task)
    
    def cleanup_completed_tasks(self, max_age_days: int = 7):
        """清理已完成的任务"""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        tasks_to_remove = []
        for task in self.tasks.values():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] 
                and task.completed_at and task.completed_at < cutoff_date):
                tasks_to_remove.append(task.id)
        
        for task_id in tasks_to_remove:
            self.delete_task(task_id)
        
        if tasks_to_remove:
            self.logger.info(f"Cleaned up {len(tasks_to_remove)} completed tasks")