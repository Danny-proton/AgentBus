"""
工作流引擎

提供复杂工作流的执行和管理功能，支持：
- 任务依赖图
- 顺序、并行、条件执行
- 工作流状态跟踪
- 错误处理和回滚
- 工作流模板和复用
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
import logging
from dataclasses import dataclass, field
from collections import defaultdict, deque
import json


class WorkflowStatus(Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class StepType(Enum):
    """步骤类型"""
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    LOOP = "loop"
    WAIT = "wait"
    CUSTOM = "custom"


@dataclass
class WorkflowStep:
    """工作流步骤"""
    id: str
    name: str
    type: StepType
    func: Optional[Callable] = None
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    conditions: List[Callable] = field(default_factory=list)
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'dependencies': self.dependencies,
            'status': self.status.value,
            'result': self.result,
            'error': self.error,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'metadata': self.metadata
        }


@dataclass
class WorkflowContext:
    """工作流执行上下文"""
    workflow_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    shared_data: Dict[str, Any] = field(default_factory=dict)
    step_results: Dict[str, Any] = field(default_factory=dict)
    execution_path: List[str] = field(default_factory=list)
    current_step: Optional[str] = None
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(name, default)
    
    def set_variable(self, name: str, value: Any):
        """设置变量"""
        self.variables[name] = value
    
    def get_step_result(self, step_id: str, default: Any = None) -> Any:
        """获取步骤结果"""
        return self.step_results.get(step_id, default)
    
    def set_step_result(self, step_id: str, result: Any):
        """设置步骤结果"""
        self.step_results[step_id] = result


@dataclass
class Workflow:
    """工作流定义"""
    id: str
    name: str
    description: str = ""
    steps: Dict[str, WorkflowStep] = field(default_factory=dict)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    context: Optional[WorkflowContext] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_step(self, step: WorkflowStep):
        """添加步骤"""
        self.steps[step.id] = step
    
    def add_dependency(self, step_id: str, depends_on: List[str]):
        """添加依赖关系"""
        self.dependencies[step_id] = depends_on
    
    def get_ready_steps(self) -> List[str]:
        """获取准备就绪的步骤"""
        ready_steps = []
        for step_id, step in self.steps.items():
            if step.status != StepStatus.PENDING:
                continue
            
            # 检查依赖是否满足
            if step_id in self.dependencies:
                deps = self.dependencies[step_id]
                if all(self.steps[dep].status == StepStatus.COMPLETED for dep in deps):
                    ready_steps.append(step_id)
            else:
                ready_steps.append(step_id)
        
        return ready_steps
    
    def is_completed(self) -> bool:
        """检查工作流是否完成"""
        return all(step.status == StepStatus.COMPLETED for step in self.steps.values())
    
    def has_failed(self) -> bool:
        """检查是否有失败的步骤"""
        return any(step.status == StepStatus.FAILED for step in self.steps.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'steps': {step_id: step.to_dict() for step_id, step in self.steps.items()},
            'dependencies': self.dependencies,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error,
            'metadata': self.metadata
        }


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self, task_manager=None):
        self.workflows: Dict[str, Workflow] = {}
        self.running_workflows: Set[str] = set()
        self.task_manager = task_manager
        self.logger = logging.getLogger(__name__)
        
        # 工作流事件回调
        self.callbacks = {
            'workflow_started': [],
            'workflow_completed': [],
            'workflow_failed': [],
            'step_started': [],
            'step_completed': [],
            'step_failed': []
        }
    
    def create_workflow(
        self,
        name: str,
        description: str = "",
        metadata: Dict[str, Any] = None
    ) -> str:
        """创建工作流"""
        workflow_id = str(uuid.uuid4())
        
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            metadata=metadata or {}
        )
        
        self.workflows[workflow_id] = workflow
        
        self.logger.info(f"Workflow created: {workflow_id} - {name}")
        return workflow_id
    
    def add_task_step(
        self,
        workflow_id: str,
        name: str,
        func: Callable,
        args: tuple = None,
        kwargs: dict = None,
        dependencies: List[str] = None,
        timeout: float = None,
        max_retries: int = 3,
        step_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """添加任务步骤"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        if step_id is None:
            step_id = str(uuid.uuid4())
        
        step = WorkflowStep(
            id=step_id,
            name=name,
            type=StepType.TASK,
            func=func,
            args=args or (),
            kwargs=kwargs or {},
            dependencies=dependencies or [],
            timeout=timeout,
            max_retries=max_retries,
            metadata=metadata or {}
        )
        
        self.workflows[workflow_id].add_step(step)
        
        self.logger.info(f"Task step added: {step_id} to workflow {workflow_id}")
        return step_id
    
    def add_condition_step(
        self,
        workflow_id: str,
        name: str,
        condition_func: Callable,
        dependencies: List[str] = None,
        step_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """添加条件步骤"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        if step_id is None:
            step_id = str(uuid.uuid4())
        
        step = WorkflowStep(
            id=step_id,
            name=name,
            type=StepType.CONDITION,
            func=condition_func,
            dependencies=dependencies or [],
            metadata=metadata or {}
        )
        
        self.workflows[workflow_id].add_step(step)
        
        self.logger.info(f"Condition step added: {step_id} to workflow {workflow_id}")
        return step_id
    
    def add_parallel_steps(
        self,
        workflow_id: str,
        steps: List[WorkflowStep],
        group_name: str = "parallel_group"
    ) -> List[str]:
        """添加并行步骤"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        step_ids = []
        for step in steps:
            step.id = str(uuid.uuid4())
            step.type = StepType.PARALLEL
            self.workflows[workflow_id].add_step(step)
            step_ids.append(step.id)
        
        self.logger.info(f"Parallel steps added: {step_ids} to workflow {workflow_id}")
        return step_ids
    
    def add_wait_step(
        self,
        workflow_id: str,
        name: str,
        duration: float,
        dependencies: List[str] = None,
        step_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """添加等待步骤"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        if step_id is None:
            step_id = str(uuid.uuid4())
        
        async def wait_func(duration: float):
            await asyncio.sleep(duration)
            return f"Waited {duration} seconds"
        
        step = WorkflowStep(
            id=step_id,
            name=name,
            type=StepType.WAIT,
            func=wait_func,
            args=(duration,),
            dependencies=dependencies or [],
            metadata=metadata or {}
        )
        
        self.workflows[workflow_id].add_step(step)
        
        self.logger.info(f"Wait step added: {step_id} to workflow {workflow_id}")
        return step_id
    
    def set_dependencies(self, workflow_id: str, dependencies: Dict[str, List[str]]):
        """设置步骤依赖关系"""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        self.workflows[workflow_id].dependencies = dependencies
        
        # 更新步骤的依赖列表
        for step_id, deps in dependencies.items():
            if step_id in self.workflows[workflow_id].steps:
                self.workflows[workflow_id].steps[step_id].dependencies = deps
    
    async def execute_workflow(self, workflow_id: str, context: WorkflowContext = None) -> bool:
        """执行工作流"""
        if workflow_id not in self.workflows:
            self.logger.error(f"Workflow not found: {workflow_id}")
            return False
        
        workflow = self.workflows[workflow_id]
        
        if workflow.status != WorkflowStatus.PENDING:
            self.logger.warning(f"Workflow {workflow_id} is not in pending status")
            return False
        
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now()
        workflow.context = context or WorkflowContext(workflow_id=workflow_id)
        
        self.running_workflows.add(workflow_id)
        
        # 触发工作流开始事件
        self._emit_callback('workflow_started', workflow)
        
        try:
            success = await self._execute_workflow_steps(workflow)
            
            if success:
                workflow.status = WorkflowStatus.COMPLETED
                workflow.completed_at = datetime.now()
                self._emit_callback('workflow_completed', workflow)
            else:
                workflow.status = WorkflowStatus.FAILED
                workflow.error = "Workflow execution failed"
                self._emit_callback('workflow_failed', workflow)
            
            return success
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.error = str(e)
            workflow.completed_at = datetime.now()
            self.logger.error(f"Workflow {workflow_id} failed with error: {e}")
            self._emit_callback('workflow_failed', workflow)
            return False
        
        finally:
            self.running_workflows.discard(workflow_id)
    
    async def _execute_workflow_steps(self, workflow: Workflow) -> bool:
        """执行工作流步骤"""
        completed_steps = set()
        
        while True:
            # 获取准备就绪的步骤
            ready_steps = workflow.get_ready_steps()
            
            if not ready_steps:
                break
            
            # 执行准备就绪的步骤
            for step_id in ready_steps:
                if step_id not in completed_steps:
                    success = await self._execute_step(workflow, step_id)
                    completed_steps.add(step_id)
                    
                    if not success:
                        return False
            
            # 检查工作流是否完成
            if workflow.is_completed():
                return True
            
            # 如果没有可执行的步骤但还有未完成的步骤，说明有循环依赖或条件阻塞
            pending_steps = [sid for sid, step in workflow.steps.items() 
                           if step.status == StepStatus.PENDING]
            
            if not pending_steps:
                break
        
        return workflow.is_completed()
    
    async def _execute_step(self, workflow: Workflow, step_id: str) -> bool:
        """执行单个步骤"""
        step = workflow.steps[step_id]
        workflow.context.current_step = step_id
        
        # 更新步骤状态
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()
        
        # 触发步骤开始事件
        self._emit_callback('step_started', workflow, step)
        
        try:
            # 执行步骤函数
            if asyncio.iscoroutinefunction(step.func):
                result = await self._execute_step_with_retry(step, workflow.context, workflow)
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, self._execute_step_with_retry, step, workflow.context, workflow
                )
            
            # 设置步骤结果
            step.result = result
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now()
            
            # 保存到上下文
            workflow.context.set_step_result(step_id, result)
            
            # 触发步骤完成事件
            self._emit_callback('step_completed', workflow, step)
            
            return True
            
        except Exception as e:
            step.error = str(e)
            step.status = StepStatus.FAILED
            step.completed_at = datetime.now()
            
            self.logger.error(f"Step {step_id} failed: {e}")
            self._emit_callback('step_failed', workflow, step)
            
            return False
    
    async def _execute_step_with_retry(self, step: WorkflowStep, context: WorkflowContext, workflow: Workflow) -> Any:
        """执行步骤（带重试和依赖处理）"""
        last_error = None
        
        for attempt in range(step.max_retries + 1):
            try:
                # 获取依赖步骤的结果作为参数
                args = list(step.args)
                
                # 如果步骤有依赖关系，获取依赖步骤的结果
                if step.id in workflow.dependencies:
                    dependencies = workflow.dependencies[step.id]
                    
                    for dep_id in dependencies:
                        dep_result = context.get_step_result(dep_id)
                        
                        # 尝试从依赖结果中提取数据
                        if hasattr(dep_result, 'data'):
                            dep_data = dep_result.data
                        elif isinstance(dep_result, dict) and 'data' in dep_result:
                            dep_data = dep_result['data']
                        else:
                            dep_data = dep_result
                        
                        # 将依赖结果作为位置参数传递
                        args.append(dep_data)
                
                # 如果有超时设置，使用超时执行
                if step.timeout:
                    if asyncio.iscoroutinefunction(step.func):
                        result = await asyncio.wait_for(
                            step.func(*args, **step.kwargs),
                            timeout=step.timeout
                        )
                    else:
                        result = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None, step.func, *args, **step.kwargs
                            ),
                            timeout=step.timeout
                        )
                else:
                    # 正常执行
                    if asyncio.iscoroutinefunction(step.func):
                        result = await step.func(*args, **step.kwargs)
                    else:
                        result = step.func(*args, **step.kwargs)
                
                return result
                
            except Exception as e:
                last_error = e
                step.retry_count += 1
                
                if attempt < step.max_retries:
                    # 等待后重试
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                else:
                    break
        
        raise last_error
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """取消工作流"""
        if workflow_id not in self.workflows:
            return False
        
        workflow = self.workflows[workflow_id]
        
        if workflow.status not in [WorkflowStatus.RUNNING, WorkflowStatus.PAUSED]:
            return False
        
        workflow.status = WorkflowStatus.CANCELLED
        workflow.completed_at = datetime.now()
        
        # 取消所有运行中的步骤
        for step in workflow.steps.values():
            if step.status == StepStatus.RUNNING:
                step.status = StepStatus.CANCELLED
        
        self.running_workflows.discard(workflow_id)
        
        self.logger.info(f"Workflow cancelled: {workflow_id}")
        return True
    
    def pause_workflow(self, workflow_id: str) -> bool:
        """暂停工作流"""
        if workflow_id not in self.workflows:
            return False
        
        workflow = self.workflows[workflow_id]
        
        if workflow.status != WorkflowStatus.RUNNING:
            return False
        
        workflow.status = WorkflowStatus.PAUSED
        
        self.logger.info(f"Workflow paused: {workflow_id}")
        return True
    
    def resume_workflow(self, workflow_id: str) -> bool:
        """恢复工作流"""
        if workflow_id not in self.workflows:
            return False
        
        workflow = self.workflows[workflow_id]
        
        if workflow.status != WorkflowStatus.PAUSED:
            return False
        
        workflow.status = WorkflowStatus.RUNNING
        
        # 重新执行工作流
        asyncio.create_task(self.execute_workflow(workflow_id, workflow.context))
        
        self.logger.info(f"Workflow resumed: {workflow_id}")
        return True
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """获取工作流"""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self, status: Optional[WorkflowStatus] = None) -> List[Workflow]:
        """列出工作流"""
        workflows = list(self.workflows.values())
        
        if status:
            workflows = [w for w in workflows if w.status == status]
        
        return workflows
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """获取工作流统计信息"""
        stats = {
            'total': len(self.workflows),
            'pending': 0,
            'running': 0,
            'completed': 0,
            'failed': 0,
            'cancelled': 0,
            'paused': 0
        }
        
        for workflow in self.workflows.values():
            stats[workflow.status.value] += 1
        
        return stats
    
    def add_callback(self, event: str, callback: Callable):
        """添加事件回调"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def remove_callback(self, event: str, callback: Callable):
        """移除事件回调"""
        if event in self.callbacks:
            try:
                self.callbacks[event].remove(callback)
            except ValueError:
                pass
    
    def _emit_callback(self, event: str, *args):
        """触发事件回调"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(*args))
                    else:
                        callback(*args)
                except Exception as e:
                    self.logger.error(f"Callback error for event {event}: {e}")
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """删除工作流"""
        if workflow_id not in self.workflows:
            return False
        
        # 如果工作流正在运行，先取消
        if workflow_id in self.running_workflows:
            self.cancel_workflow(workflow_id)
        
        del self.workflows[workflow_id]
        
        self.logger.info(f"Workflow deleted: {workflow_id}")
        return True
    
    def cleanup_completed_workflows(self, max_age_hours: int = 24):
        """清理已完成的工作流"""
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        workflows_to_remove = []
        for workflow_id, workflow in self.workflows.items():
            if (workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED] 
                and workflow.completed_at 
                and workflow.completed_at < cutoff_time):
                workflows_to_remove.append(workflow_id)
        
        for workflow_id in workflows_to_remove:
            self.delete_workflow(workflow_id)
        
        self.logger.info(f"Cleaned up {len(workflows_to_remove)} completed workflows")
        
        return len(workflows_to_remove)