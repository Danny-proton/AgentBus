# AgentBus任务调度系统

基于Moltbot的任务调度功能，为AgentBus提供完整的任务调度和定时任务系统。

## 功能特性

### 核心组件

1. **TaskManager** - 任务管理器
   - 任务创建、删除、更新
   - 任务状态跟踪和管理
   - 任务调度和执行
   - 失败重试和超时处理
   - 任务依赖管理

2. **CronHandler** - Cron定时器处理器
   - 标准cron表达式解析
   - 定时任务触发
   - 时区处理
   - 一次性任务和重复任务
   - 任务调度状态管理

3. **WorkflowEngine** - 工作流引擎
   - 任务依赖图
   - 顺序、并行、条件执行
   - 工作流状态跟踪
   - 错误处理和回滚
   - 工作流模板和复用

### 主要特性

- **任务生命周期管理**：创建、执行、暂停、恢复、取消、删除
- **任务依赖管理**：支持复杂的任务依赖关系
- **失败重试机制**：可配置的重试次数和退避策略
- **超时处理**：任务执行超时自动终止
- **并行执行**：支持任务并行执行提高效率
- **事件回调**：任务和步骤执行事件回调
- **持久化存储**：任务状态自动保存和恢复
- **监控统计**：详细的执行统计和监控信息

## 快速开始

### 安装依赖

```bash
pip install asyncio pathlib dataclasses
```

### 基础使用

```python
import asyncio
from task_manager import TaskManager, TaskConfig, TaskPriority
from cron_handler import CronHandler
from workflow import WorkflowEngine, WorkflowContext

async def my_task(name: str):
    print(f"执行任务: {name}")
    await asyncio.sleep(2)
    return f"任务 {name} 完成"

# 1. 任务管理
task_manager = TaskManager(storage_path="./data/tasks")
await task_manager.start()

# 创建任务
config = TaskConfig(
    max_retries=3,
    timeout=30.0,
    auto_retry=True
)

task_id = task_manager.create_task(
    name="示例任务",
    func=my_task,
    args=("任务1",),
    config=config
)

# 启动任务
await task_manager.start_task(task_id)

# 2. 定时任务
cron_handler = CronHandler()

# 每5分钟执行一次
cron_handler.add_scheduled_task(
    name="定时任务",
    cron_expression="*/5 * * * *",
    func=my_task,
    args=("定时任务",)
)

await cron_handler.start()

# 3. 工作流
workflow_engine = WorkflowEngine()

# 创建工作流
workflow_id = workflow_engine.create_workflow(
    name="数据处理工作流"
)

# 添加步骤
step1_id = workflow_engine.add_task_step(
    workflow_id=workflow_id,
    name="数据准备",
    func=my_task,
    args=("步骤1",)
)

# 执行工作流
context = WorkflowContext(workflow_id=workflow_id)
success = await workflow_engine.execute_workflow(workflow_id, context)
```

## 详细文档

### TaskManager - 任务管理器

#### 创建任务

```python
from task_manager import TaskManager, TaskConfig, TaskPriority

# 创建任务管理器
task_manager = TaskManager(
    storage_path="./data/tasks",
    max_workers=5
)

# 任务配置
config = TaskConfig(
    max_retries=3,          # 最大重试次数
    retry_delay=60.0,      # 重试延迟（秒）
    timeout=300.0,         # 超时时间（秒）
    dependencies=["task1"], # 依赖任务ID
    priority=TaskPriority.HIGH,  # 优先级
    auto_retry=True,       # 自动重试
    retry_backoff=2.0,    # 重试退避倍数
    description="任务描述",
    metadata={"key": "value"}  # 自定义元数据
)

# 创建任务
task_id = task_manager.create_task(
    name="任务名称",
    func=my_task_function,
    args=("arg1", "arg2"),
    kwargs={"key": "value"},
    config=config,
    task_id="optional-id"  # 可选指定任务ID
)
```

#### 任务管理操作

```python
# 启动任务
await task_manager.start_task(task_id)

# 暂停任务
await task_manager.pause_task(task_id)

# 恢复任务
await task_manager.resume_task(task_id)

# 取消任务
await task_manager.cancel_task(task_id)

# 删除任务
task_manager.delete_task(task_id)

# 获取任务
task = task_manager.get_task(task_id)

# 获取任务列表
tasks = task_manager.get_tasks(
    status=TaskStatus.PENDING,
    priority=TaskPriority.HIGH
)

# 更新任务配置
new_config = TaskConfig(max_retries=5)
task_manager.update_task_config(task_id, new_config)
```

#### 任务状态

- `PENDING` - 等待执行
- `RUNNING` - 正在执行
- `COMPLETED` - 执行完成
- `FAILED` - 执行失败
- `CANCELLED` - 已取消
- `PAUSED` - 已暂停
- `RETRYING` - 重试中
- `TIMEOUT` - 执行超时

### CronHandler - 定时任务

#### Cron表达式

支持标准cron表达式格式：

```
秒 分 时 日 月 星期
*  *  *  *  *  *
```

- **秒**：0-59
- **分**：0-59
- **时**：0-23
- **日**：1-31
- **月**：1-12
- **星期**：1-7（1=周一，7=周日）

#### 常用表达式

```python
from cron_handler import CronHandler

cron_handler = CronHandler(task_manager)

# 添加定时任务
task_id = cron_handler.add_scheduled_task(
    name="每日任务",
    cron_expression="0 0 9 * * *",  # 每天上午9点
    func=daily_task,
    args=(),
    enabled=True,
    max_runs=None,        # 无限制执行
    timeout=3600.0,      # 1小时超时
    task_id=None          # 自动生成ID
)

# 任务管理
cron_handler.remove_scheduled_task(task_id)
cron_handler.enable_scheduled_task(task_id)
cron_handler.disable_scheduled_task(task_id)
cron_handler.run_task_now(task_id)  # 立即执行

# 查询定时任务
task = cron_handler.get_scheduled_task(task_id)
tasks = cron_handler.list_scheduled_tasks(enabled_only=True)
upcoming = cron_handler.get_next_runs(count=10)  # 获取下10个任务

# 统计信息
stats = cron_handler.get_statistics()
```

#### 常用表达式示例

```python
expressions = {
    "每分钟": "* * * * * *",
    "每5分钟": "*/5 * * * * *",
    "每小时": "0 0 * * * *",
    "每天凌晨": "0 0 0 * * *",
    "每天上午9点": "0 0 9 * * *",
    "每周一上午9点": "0 0 9 * * 1",
    "每月1号上午9点": "0 0 9 1 * *",
    "工作日每天上午9点": "0 0 9 * * 1-5"
}
```

### WorkflowEngine - 工作流引擎

#### 创建工作流

```python
from workflow import WorkflowEngine, WorkflowContext, WorkflowStep, StepType

workflow_engine = WorkflowEngine(task_manager)

# 创建工作流
workflow_id = workflow_engine.create_workflow(
    name="数据处理工作流",
    description="处理和分析数据的完整流程",
    metadata={"version": "1.0"}
)
```

#### 添加工作流步骤

```python
# 任务步骤
step1_id = workflow_engine.add_task_step(
    workflow_id=workflow_id,
    name="数据准备",
    func=prepare_data,
    args=(source_path,),
    dependencies=[],  # 依赖的步骤ID
    timeout=300.0,
    max_retries=3,
    metadata={"step_type": "preparation"}
)

# 条件步骤
step2_id = workflow_engine.add_condition_step(
    workflow_id=workflow_id,
    name="条件检查",
    condition_func=check_data_quality,
    dependencies=[step1_id],
    metadata={"condition_type": "data_quality"}
)

# 等待步骤
step3_id = workflow_engine.add_wait_step(
    workflow_id=workflow_id,
    name="等待用户确认",
    duration=300.0,  # 等待5分钟
    dependencies=[step2_id],
    metadata={"wait_type": "user_confirmation"}
)
```

#### 并行执行

```python
# 创建并行步骤
parallel_steps = []
for i in range(3):
    step = WorkflowStep(
        id=f"parallel_{i}",
        name=f"并行处理{i}",
        type=StepType.TASK,
        func=process_data_chunk,
        args=(chunk_data[i],),
        timeout=120.0
    )
    parallel_steps.append(step)

parallel_step_ids = workflow_engine.add_parallel_steps(
    workflow_id=workflow_id,
    steps=parallel_steps,
    group_name="数据分片处理"
)
```

#### 设置依赖关系

```python
# 设置步骤依赖
workflow_engine.set_dependencies(workflow_id, {
    step1_id: [],                    # 步骤1无依赖
    step2_id: [step1_id],           # 步骤2依赖步骤1
    step3_id: [step2_id],           # 步骤3依赖步骤2
    parallel_step_ids[0]: [step1_id], # 并行步骤依赖步骤1
    parallel_step_ids[1]: [step1_id],
    parallel_step_ids[2]: [step1_id],
    "final_step": parallel_step_ids   # 最终步骤依赖所有并行步骤
})
```

#### 执行工作流

```python
# 创建执行上下文
context = WorkflowContext(workflow_id=workflow_id)
context.set_variable("input_path", "/data/input")
context.set_variable("output_path", "/data/output")
context.set_variable("user_id", "12345")

# 添加回调函数
async def on_step_completed(workflow, step):
    print(f"步骤完成: {step.name}")

async def on_workflow_completed(workflow):
    print(f"工作流完成: {workflow.name}")

workflow_engine.add_callback('step_completed', on_step_completed)
workflow_engine.add_callback('workflow_completed', on_workflow_completed)

# 执行工作流
success = await workflow_engine.execute_workflow(workflow_id, context)

if success:
    print("工作流执行成功")
else:
    print("工作流执行失败")
```

#### 工作流管理

```python
# 获取工作流
workflow = workflow_engine.get_workflow(workflow_id)

# 列出工作流
all_workflows = workflow_engine.list_workflows()
running_workflows = workflow_engine.list_workflows(WorkflowStatus.RUNNING)

# 取消工作流
workflow_engine.cancel_workflow(workflow_id)

# 暂停工作流
workflow_engine.pause_workflow(workflow_id)

# 恢复工作流
workflow_engine.resume_workflow(workflow_id)

# 删除工作流
workflow_engine.delete_workflow(workflow_id)
```

#### 工作流状态

- `PENDING` - 等待执行
- `RUNNING` - 正在执行
- `COMPLETED` - 执行完成
- `FAILED` - 执行失败
- `CANCELLED` - 已取消
- `PAUSED` - 已暂停

### 事件回调

#### 任务事件回调

```python
# 任务管理器回调
def on_task_created(task):
    print(f"任务创建: {task.name}")

def on_task_started(task):
    print(f"任务开始: {task.name}")

def on_task_completed(task):
    print(f"任务完成: {task.name} - 结果: {task.result}")

def on_task_failed(task):
    print(f"任务失败: {task.name} - 错误: {task.last_error}")

task_manager.add_callback('created', on_task_created)
task_manager.add_callback('started', on_task_started)
task_manager.add_callback('completed', on_task_completed)
task_manager.add_callback('failed', on_task_failed)
```

#### 工作流事件回调

```python
# 工作流引擎回调
async def on_workflow_started(workflow):
    print(f"工作流开始: {workflow.name}")

async def on_step_started(workflow, step):
    print(f"步骤开始: {workflow.name} -> {step.name}")

async def on_step_completed(workflow, step):
    print(f"步骤完成: {workflow.name} -> {step.name}")

workflow_engine.add_callback('workflow_started', on_workflow_started)
workflow_engine.add_callback('step_started', on_step_started)
workflow_engine.add_callback('step_completed', on_step_completed)
```

### 监控和统计

#### 获取统计信息

```python
# 任务统计
task_stats = task_manager.get_task_stats()
print(f"任务统计: {task_stats}")
# 输出示例：
# {
#     'total': 25,
#     'pending': 5,
#     'running': 3,
#     'completed': 15,
#     'failed': 2,
#     'cancelled': 0,
#     'paused': 0
# }

# 工作流统计
workflow_stats = workflow_engine.get_workflow_statistics()
print(f"工作流统计: {workflow_stats}")

# 定时任务统计
cron_stats = cron_handler.get_statistics()
print(f"定时任务统计: {cron_stats}")
# 输出示例：
# {
#     'total_scheduled_tasks': 10,
#     'enabled_tasks': 8,
#     'disabled_tasks': 2,
#     'total_runs': 156,
#     'upcoming_runs': 3,
#     'next_run': datetime(2024, 1, 15, 9, 0)
# }
```

### 清理和优化

```python
# 清理已完成的任务（7天前）
task_manager.cleanup_completed_tasks(max_age_days=7)

# 清理已禁用的定时任务
cron_handler.cleanup_disabled_tasks()

# 清理已完成的工作流（24小时前）
workflow_engine.cleanup_completed_workflows(max_age_hours=24)
```

## 最佳实践

### 1. 任务设计

- **保持任务原子性**：每个任务应该只负责一个明确的功能
- **合理设置超时**：避免任务无限期阻塞
- **使用适当的重试策略**：对于可能失败的操作设置重试
- **避免长时间运行的任务**：考虑将大任务拆分为多个小任务

### 2. 依赖管理

- **明确依赖关系**：确保任务依赖关系的正确性
- **避免循环依赖**：检查和避免任务间的循环依赖
- **合理安排执行顺序**：根据业务逻辑安排任务的执行顺序

### 3. 错误处理

- **区分可恢复和不可恢复错误**：只对可恢复的错误进行重试
- **记录详细的错误信息**：便于问题排查
- **设置适当的重试间隔**：避免对系统造成过大压力

### 4. 监控和维护

- **定期检查任务执行情况**：监控任务的成功率和性能
- **及时清理过期数据**：避免数据堆积影响性能
- **监控资源使用情况**：确保系统资源充足

### 5. 性能优化

- **合理设置并发数**：根据系统能力设置合适的最大工作线程数
- **使用异步操作**：优先使用异步函数提高并发性能
- **避免过度频繁的任务**：合理设置定时任务的执行频率

## 故障排查

### 常见问题

1. **任务一直处于PENDING状态**
   - 检查依赖任务是否完成
   - 确认是否有足够的执行资源

2. **定时任务不执行**
   - 验证cron表达式格式
   - 检查定时任务是否启用
   - 查看系统时间是否正确

3. **工作流执行失败**
   - 检查步骤间的依赖关系
   - 查看错误日志定位具体问题
   - 验证步骤函数是否正常

4. **内存使用过高**
   - 检查是否有未完成的长时间运行任务
   - 考虑清理历史数据
   - 调整并发设置

### 日志调试

```python
import logging

# 启用详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 查看特定组件的日志
logger = logging.getLogger('task_manager')
logger.setLevel(logging.DEBUG)
```

## 扩展开发

### 自定义任务类型

```python
class CustomTaskStep(WorkflowStep):
    def __init__(self, custom_param):
        super().__init__()
        self.custom_param = custom_param
    
    async def execute(self):
        # 自定义执行逻辑
        pass
```

### 自定义调度器

```python
class CustomCronHandler(CronHandler):
    def custom_scheduling_logic(self):
        # 自定义调度逻辑
        pass
```

## 许可证

本项目采用MIT许可证。详见LICENSE文件。

## 贡献

欢迎提交Issue和Pull Request来改进这个项目。

## 更新日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 完整的任务管理功能
- Cron表达式支持
- 工作流引擎
- 事件回调系统
- 持久化存储
- 监控统计