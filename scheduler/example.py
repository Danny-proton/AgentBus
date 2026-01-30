"""
AgentBus任务调度系统使用示例

展示如何使用任务调度系统：
1. 基础任务管理
2. 定时任务调度
3. 工作流执行
4. 任务依赖和重试
"""

import asyncio
import logging
from datetime import datetime

# 导入调度系统组件
from task_manager import TaskManager, TaskConfig, TaskPriority
from cron_handler import CronHandler
from workflow import WorkflowEngine, WorkflowContext, WorkflowStep

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# 示例任务函数
async def sample_task(name: str, duration: int = 2):
    """示例任务函数"""
    logger.info(f"Starting task: {name}")
    await asyncio.sleep(duration)
    logger.info(f"Completed task: {name}")
    return f"Result from {name}"


def sync_task(name: str, value: int):
    """同步任务示例"""
    logger.info(f"Running sync task: {name} with value {value}")
    return value * 2


async def condition_task(condition: bool):
    """条件任务示例"""
    if condition:
        logger.info("Condition is true, proceeding...")
        return "Condition passed"
    else:
        logger.info("Condition is false, skipping...")
        raise Exception("Condition not met")


async def main():
    """主函数示例"""
    
    # 1. 基础任务管理
    print("=== 基础任务管理示例 ===")
    
    task_manager = TaskManager(storage_path="./data/tasks_example")
    await task_manager.start()
    
    # 创建任务
    config = TaskConfig(
        max_retries=3,
        timeout=30.0,
        auto_retry=True,
        priority=TaskPriority.HIGH
    )
    
    task_id1 = task_manager.create_task(
        name="示例任务1",
        func=sample_task,
        args=("任务1", 3),
        config=config
    )
    
    task_id2 = task_manager.create_task(
        name="同步任务",
        func=sync_task,
        args=("同步", 5),
        config=TaskConfig()
    )
    
    print(f"创建了任务: {task_id1}, {task_id2}")
    
    # 启动任务
    await task_manager.start_task(task_id1)
    await task_manager.start_task(task_id2)
    
    # 等待任务完成
    await asyncio.sleep(5)
    
    # 查看任务状态
    tasks = task_manager.get_tasks()
    for task in tasks:
        print(f"任务状态: {task.name} - {task.status.value}")
    
    # 2. 定时任务示例
    print("\n=== 定时任务示例 ===")
    
    cron_handler = CronHandler(task_manager)
    
    async def scheduled_task():
        """定时执行的任务"""
        logger.info("定时任务执行中...")
        return "定时任务完成"
    
    # 添加每5秒执行一次的任务（测试用）
    task_id = cron_handler.add_scheduled_task(
        name="定时任务示例",
        cron_expression="*/5 * * * * *",  # 每5秒
        func=scheduled_task,
        max_runs=3  # 只执行3次用于演示
    )
    
    await cron_handler.start()
    
    # 运行15秒定时任务演示
    print("定时任务运行15秒...")
    await asyncio.sleep(15)
    
    await cron_handler.stop()
    
    # 3. 工作流示例
    print("\n=== 工作流示例 ===")
    
    workflow_engine = WorkflowEngine(task_manager)
    
    # 创建工作流
    workflow_id = workflow_engine.create_workflow(
        name="示例工作流",
        description="展示工作流功能"
    )
    
    # 添加工作流步骤
    step1_id = workflow_engine.add_task_step(
        workflow_id=workflow_id,
        name="初始化步骤",
        func=sample_task,
        args=("工作流步骤1", 2)
    )
    
    step2_id = workflow_engine.add_task_step(
        workflow_id=workflow_id,
        name="处理步骤",
        func=sample_task,
        args=("工作流步骤2", 1)
    )
    
    step3_id = workflow_engine.add_task_step(
        workflow_id=workflow_id,
        name="条件步骤",
        func=condition_task,
        args=(True,)  # 设置条件为True
    )
    
    # 设置依赖关系
    workflow_engine.set_dependencies(workflow_id, {
        step2_id: [step1_id],  # step2 依赖于 step1
        step3_id: [step2_id]   # step3 依赖于 step2
    })
    
    # 创建执行上下文
    context = WorkflowContext(workflow_id=workflow_id)
    context.set_variable("user_id", "12345")
    context.set_variable("action", "process")
    
    # 执行工作流
    success = await workflow_engine.execute_workflow(workflow_id, context)
    print(f"工作流执行结果: {'成功' if success else '失败'}")
    
    # 4. 高级功能示例
    print("\n=== 高级功能示例 ===")
    
    # 任务统计
    task_stats = task_manager.get_task_stats()
    print(f"任务统计: {task_stats}")
    
    # 工作流统计
    workflow_stats = workflow_engine.get_workflow_statistics()
    print(f"工作流统计: {workflow_stats}")
    
    # 定时任务统计
    cron_stats = cron_handler.get_statistics()
    print(f"定时任务统计: {cron_stats}")
    
    # 5. 清理资源
    await task_manager.stop()
    
    print("\n=== 示例完成 ===")


async def advanced_workflow_example():
    """高级工作流示例"""
    print("\n=== 高级工作流示例 ===")
    
    workflow_engine = WorkflowEngine()
    
    # 创建复杂工作流
    workflow_id = workflow_engine.create_workflow(
        name="复杂数据处理工作流",
        description="包含并行处理、错误处理和数据传递"
    )
    
    # 步骤1: 数据准备
    async def prepare_data():
        await asyncio.sleep(1)
        return {"data": [1, 2, 3, 4, 5]}
    
    # 步骤2: 并行处理数据
    async def process_chunk(chunk_data):
        await asyncio.sleep(0.5)
        return sum(chunk_data)
    
    # 步骤3: 汇总结果
    async def aggregate_results(results):
        return sum(results)
    
    # 添加步骤
    step1_id = workflow_engine.add_task_step(
        workflow_id=workflow_id,
        name="准备数据",
        func=prepare_data
    )
    
    # 创建并行步骤
    parallel_steps = []
    for i in range(3):
        step = WorkflowStep(
            id=f"parallel_{i}",
            name=f"并行处理{i}",
            type="parallel",
            func=process_chunk,
            args=([i * 2 + 1, i * 2 + 2],)
        )
        parallel_steps.append(step)
    
    parallel_step_ids = workflow_engine.add_parallel_steps(
        workflow_id=workflow_id,
        steps=parallel_steps,
        group_name="数据处理"
    )
    
    step3_id = workflow_engine.add_task_step(
        workflow_id=workflow_id,
        name="汇总结果",
        func=aggregate_results
    )
    
    # 设置依赖
    workflow_engine.set_dependencies(workflow_id, {
        parallel_step_ids[0]: [step1_id],
        parallel_step_ids[1]: [step1_id], 
        parallel_step_ids[2]: [step1_id],
        step3_id: parallel_step_ids
    })
    
    # 添加回调函数
    async def on_step_completed(workflow, step):
        logger.info(f"步骤完成: {step.name}")
    
    async def on_workflow_completed(workflow):
        logger.info(f"工作流完成: {workflow.name}")
    
    workflow_engine.add_callback('step_completed', on_step_completed)
    workflow_engine.add_callback('workflow_completed', on_workflow_completed)
    
    # 执行工作流
    context = WorkflowContext(workflow_id=workflow_id)
    success = await workflow_engine.execute_workflow(workflow_id, context)
    
    print(f"高级工作流执行结果: {'成功' if success else '失败'}")


if __name__ == "__main__":
    # 运行基础示例
    asyncio.run(main())
    
    # 运行高级示例
    asyncio.run(advanced_workflow_example())