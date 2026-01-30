"""
AgentBus任务调度系统测试

测试各个组件的基本功能
"""

import asyncio
import tempfile
import shutil
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)

from task_manager import TaskManager, TaskConfig, TaskStatus, TaskPriority
from cron_handler import CronHandler, CronExpression
from workflow import WorkflowEngine, WorkflowContext


async def test_task_manager():
    """测试任务管理器"""
    print("=== 测试任务管理器 ===")
    
    # 使用临时目录
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        task_manager = TaskManager(storage_path=str(temp_dir / "tasks"))
        await task_manager.start()
        
        # 创建任务
        async def test_async_task(name: str, duration: int = 1):
            await asyncio.sleep(duration)
            return f"异步任务 {name} 完成"
        
        def test_sync_task(value: int):
            return value * 2
        
        # 创建异步任务
        task1_id = task_manager.create_task(
            name="异步测试任务",
            func=test_async_task,
            args=("任务1",),
            config=TaskConfig(timeout=10.0, max_retries=2)
        )
        
        # 创建同步任务
        task2_id = task_manager.create_task(
            name="同步测试任务",
            func=test_sync_task,
            args=(5,),
            config=TaskConfig()
        )
        
        print(f"创建任务: {task1_id}, {task2_id}")
        
        # 启动任务
        await task_manager.start_task(task1_id)
        await task_manager.start_task(task2_id)
        
        # 等待任务完成
        await asyncio.sleep(3)
        
        # 检查任务状态
        tasks = task_manager.get_tasks()
        for task in tasks:
            print(f"任务状态: {task.name} - {task.status.value}")
            if task.result:
                print(f"任务结果: {task.result.data}")
        
        # 测试任务统计
        stats = task_manager.get_task_stats()
        print(f"任务统计: {stats}")
        
        await task_manager.stop()
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
    
    print("任务管理器测试完成\n")


async def test_cron_handler():
    """测试Cron处理器"""
    print("=== 测试Cron处理器 ===")
    
    try:
        cron_handler = CronHandler()
        
        # 测试Cron表达式验证
        valid_expr = "0 0 9 * * *"
        invalid_expr = "invalid expression"
        
        print(f"Cron表达式验证: {valid_expr} - {CronHandler.validate_cron_expression(valid_expr)}")
        print(f"Cron表达式验证: {invalid_expr} - {CronHandler.validate_cron_expression(invalid_expr)}")
        
        # 获取常用表达式
        common_exprs = CronHandler.get_common_expressions()
        print(f"常用Cron表达式:")
        for name, expr in list(common_exprs.items())[:3]:
            print(f"  {name}: {expr}")
        
        # 创建临时任务（只执行一次用于测试）
        execution_count = 0
        
        async def test_scheduled_task():
            nonlocal execution_count
            execution_count += 1
            print(f"定时任务执行 #{execution_count}")
            return f"执行结果 #{execution_count}"
        
        # 添加一个只执行3次的测试任务
        task_id = cron_handler.add_scheduled_task(
            name="测试定时任务",
            cron_expression="*/2 * * * * *",  # 每2秒执行一次
            func=test_scheduled_task,
            max_runs=3  # 只执行3次用于测试
        )
        
        print(f"添加定时任务: {task_id}")
        
        await cron_handler.start()
        
        # 运行6秒定时任务演示
        print("运行6秒定时任务...")
        await asyncio.sleep(6)
        
        await cron_handler.stop()
        
        # 获取统计信息
        stats = cron_handler.get_statistics()
        print(f"Cron统计: {stats}")
        
        print("Cron处理器测试完成\n")
        
    except Exception as e:
        print(f"Cron处理器测试失败: {e}\n")


async def test_workflow_engine():
    """测试工作流引擎"""
    print("=== 测试工作流引擎 ===")
    
    try:
        workflow_engine = WorkflowEngine()
        
        # 创建测试任务
        async def prepare_data():
            await asyncio.sleep(0.5)
            return {"data": [1, 2, 3, 4, 5]}
        
        async def process_data(data):
            await asyncio.sleep(0.3)
            if isinstance(data, dict) and 'data' in data:
                return sum(data["data"])
            elif isinstance(data, list):
                return sum(data)
            else:
                return 0
        
        async def save_result(result):
            await asyncio.sleep(0.2)
            return f"结果已保存: {result}"
        
        # 创建工作流
        workflow_id = workflow_engine.create_workflow(
            name="测试工作流",
            description="数据处理流程"
        )
        
        print(f"创建工作流: {workflow_id}")
        
        # 添加步骤
        step1_id = workflow_engine.add_task_step(
            workflow_id=workflow_id,
            name="数据准备",
            func=prepare_data
        )
        
        step2_id = workflow_engine.add_task_step(
            workflow_id=workflow_id,
            name="数据处理",
            func=process_data
        )
        
        step3_id = workflow_engine.add_task_step(
            workflow_id=workflow_id,
            name="保存结果",
            func=save_result
        )
        
        # 设置依赖关系
        workflow_engine.set_dependencies(workflow_id, {
            step2_id: [step1_id],
            step3_id: [step2_id]
        })
        
        # 添加回调
        execution_log = []
        
        async def on_step_completed(workflow, step):
            execution_log.append(f"步骤完成: {step.name}")
            print(f"步骤完成: {step.name}")
        
        async def on_workflow_completed(workflow):
            execution_log.append(f"工作流完成: {workflow.name}")
            print(f"工作流完成: {workflow.name}")
        
        workflow_engine.add_callback('step_completed', on_step_completed)
        workflow_engine.add_callback('workflow_completed', on_workflow_completed)
        
        # 执行工作流
        context = WorkflowContext(workflow_id=workflow_id)
        context.set_variable("version", "1.0")
        
        print("执行工作流...")
        success = await workflow_engine.execute_workflow(workflow_id, context)
        
        print(f"工作流执行结果: {'成功' if success else '失败'}")
        
        # 获取工作流统计
        stats = workflow_engine.get_workflow_statistics()
        print(f"工作流统计: {stats}")
        
        print("工作流引擎测试完成\n")
        
    except Exception as e:
        print(f"工作流引擎测试失败: {e}\n")


async def test_workflow_parallel():
    """测试工作流并行执行"""
    print("=== 测试工作流并行执行 ===")
    
    try:
        workflow_engine = WorkflowEngine()
        
        # 创建并行任务
        async def parallel_task(task_id: int):
            await asyncio.sleep(0.5)  # 模拟耗时操作
            return f"并行任务 {task_id} 完成"
        
        # 创建工作流
        workflow_id = workflow_engine.create_workflow(
            name="并行处理工作流",
            description="测试并行执行能力"
        )
        
        # 创建并行步骤
        from workflow import WorkflowStep, StepType
        
        parallel_steps = []
        for i in range(3):
            step = WorkflowStep(
                id=f"parallel_{i}",
                name=f"并行任务{i+1}",
                type=StepType.TASK,
                func=parallel_task,
                args=(i+1,)
            )
            parallel_steps.append(step)
        
        parallel_step_ids = workflow_engine.add_parallel_steps(
            workflow_id=workflow_id,
            steps=parallel_steps,
            group_name="并行处理"
        )
        
        # 添加汇总步骤
        async def aggregate_results(*args):
            await asyncio.sleep(0.1)
            return f"所有并行任务完成，共{len(args)}个结果"
        
        final_step_id = workflow_engine.add_task_step(
            workflow_id=workflow_id,
            name="结果汇总",
            func=aggregate_results
        )
        
        # 设置依赖
        workflow_engine.set_dependencies(workflow_id, {
            final_step_id: parallel_step_ids
        })
        
        # 执行工作流
        context = WorkflowContext(workflow_id=workflow_id)
        
        print("执行并行工作流...")
        success = await workflow_engine.execute_workflow(workflow_id, context)
        
        print(f"并行工作流执行结果: {'成功' if success else '失败'}")
        
        print("并行工作流测试完成\n")
        
    except Exception as e:
        print(f"并行工作流测试失败: {e}\n")


async def test_error_handling():
    """测试错误处理"""
    print("=== 测试错误处理 ===")
    
    try:
        task_manager = TaskManager()
        await task_manager.start()
        
        # 创建会失败的任务
        async def failing_task():
            await asyncio.sleep(0.5)
            raise Exception("测试错误")
        
        # 创建带重试的任务
        failing_task_id = task_manager.create_task(
            name="失败任务",
            func=failing_task,
            config=TaskConfig(max_retries=2, auto_retry=True)
        )
        
        await task_manager.start_task(failing_task_id)
        
        # 等待重试完成
        await asyncio.sleep(3)
        
        # 检查任务状态
        task = task_manager.get_task(failing_task_id)
        print(f"失败任务状态: {task.status.value}")
        print(f"重试次数: {task.retry_count}")
        print(f"错误信息: {task.last_error}")
        
        await task_manager.stop()
        
        print("错误处理测试完成\n")
        
    except Exception as e:
        print(f"错误处理测试失败: {e}\n")


async def run_all_tests():
    """运行所有测试"""
    print("AgentBus任务调度系统测试开始\n")
    
    await test_task_manager()
    await test_cron_handler()
    await test_workflow_engine()
    await test_workflow_parallel()
    await test_error_handling()
    
    print("所有测试完成")


if __name__ == "__main__":
    asyncio.run(run_all_tests())