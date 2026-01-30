#!/usr/bin/env python3
"""
AgentBus任务调度系统完整演示

展示基于Moltbot的Cron调度系统所有功能：
1. Cron表达式解析
2. 任务调度执行  
3. 任务状态管理
4. 任务失败重试
5. 任务链和依赖
"""

import asyncio
import logging
from datetime import datetime

# 配置演示日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def demo_complete_scheduler():
    """完整调度系统演示"""
    print("🚀 AgentBus任务调度系统完整演示")
    print("=" * 50)
    
    # 导入调度系统
    from integration import AgentBusScheduler, SchedulerConfig
    
    # 创建统一调度器
    config = SchedulerConfig(
        storage_path="./data/demo_scheduler",
        max_workers=3,
        enable_monitoring=True
    )
    
    scheduler = AgentBusScheduler(config)
    
    try:
        print("\n1️⃣ 启动调度器...")
        await scheduler.start()
        print("✅ 调度器启动成功")
        
        # 演示任务函数
        async def data_preparation_task():
            """数据准备任务"""
            print("  📊 正在准备数据...")
            await asyncio.sleep(1)
            return {"data": [1, 2, 3, 4, 5]}
        
        async def data_processing_task(data):
            """数据处理任务"""
            print("  ⚙️ 正在处理数据...")
            await asyncio.sleep(1)
            result = sum(data["data"])
            print(f"  📈 处理结果: {result}")
            return result
        
        async def data_storage_task(result):
            """数据存储任务"""
            print("  💾 正在存储结果...")
            await asyncio.sleep(0.5)
            return f"存储完成: {result}"
        
        async def daily_report_task():
            """每日报告任务（定时）"""
            print("  📋 生成每日报告...")
            await asyncio.sleep(0.5)
            return "报告生成完成"
        
        print("\n2️⃣ 创建工作流...")
        # 创建复杂工作流
        workflow_id = scheduler.workflow_engine.create_workflow(
            name="数据处理工作流",
            description="完整的数据处理流程"
        )
        print(f"✅ 工作流创建: {workflow_id}")
        
        # 添加工作流步骤
        step1_id = scheduler.workflow_engine.add_task_step(
            workflow_id=workflow_id,
            name="数据准备",
            func=data_preparation_task
        )
        
        step2_id = scheduler.workflow_engine.add_task_step(
            workflow_id=workflow_id,
            name="数据处理",
            func=data_processing_task
        )
        
        step3_id = scheduler.workflow_engine.add_task_step(
            workflow_id=workflow_id,
            name="数据存储",
            func=data_storage_task
        )
        
        # 设置依赖关系
        scheduler.workflow_engine.set_dependencies(workflow_id, {
            step2_id: [step1_id],  # 处理依赖准备
            step3_id: [step2_id]  # 存储依赖处理
        })
        print("✅ 工作流依赖设置完成")
        
        # 创建执行上下文
        from workflow import WorkflowContext
        context = WorkflowContext(workflow_id=workflow_id)
        context.set_variable("user_id", "demo_user")
        context.set_variable("timestamp", datetime.now().isoformat())
        
        print("\n3️⃣ 执行工作流...")
        success = await scheduler.workflow_engine.execute_workflow(workflow_id, context)
        print(f"✅ 工作流执行结果: {'成功' if success else '失败'}")
        
        print("\n4️⃣ 创建定时任务...")
        # 创建每日报告定时任务
        cron_task_id = await scheduler.create_scheduled_task(
            name="每日报告任务",
            cron_expression="*/10 * * * * *",  # 每10秒执行一次（演示用）
            func=daily_report_task,
            max_runs=3  # 只执行3次用于演示
        )
        print(f"✅ 定时任务创建: {cron_task_id}")
        
        print("\n5️⃣ 运行定时任务演示...")
        await asyncio.sleep(15)  # 等待定时任务执行
        
        print("\n6️⃣ 系统监控和统计...")
        # 获取系统状态
        status = scheduler.get_status()
        print(f"✅ 系统运行状态: {status['running']}")
        print(f"✅ 组件状态: {status['components']}")
        
        # 获取详细指标
        metrics = scheduler.get_metrics()
        print(f"✅ 任务统计: {metrics['tasks']}")
        print(f"✅ 工作流统计: {metrics['workflows']}")
        print(f"✅ 定时任务统计: {metrics['cron']}")
        
        # 健康检查
        health = await scheduler.health_check()
        print(f"✅ 系统健康状态: {health['status']}")
        print(f"✅ 组件健康: {health['components']}")
        
        print("\n7️⃣ 演示任务失败重试机制...")
        # 创建会失败的任务来演示重试
        async def failing_task():
            print("  ❌ 任务执行失败...")
            raise Exception("演示失败")
        
        async def recovering_task():
            print("  🔄 任务恢复成功...")
            return "恢复完成"
        
        # 创建带重试的任务
        from task_manager import TaskConfig
        failing_task_id = scheduler.task_manager.create_task(
            name="失败重试演示",
            func=failing_task,
            config=TaskConfig(
                max_retries=2,
                auto_retry=True,
                retry_delay=1.0
            )
        )
        
        await scheduler.task_manager.start_task(failing_task_id)
        
        # 等待重试完成
        await asyncio.sleep(5)
        
        # 检查任务状态
        task = scheduler.task_manager.get_task(failing_task_id)
        print(f"✅ 失败任务状态: {task.status.value}")
        print(f"✅ 重试次数: {task.retry_count}")
        
        print("\n8️⃣ 最终系统统计...")
        final_stats = scheduler.task_manager.get_task_stats()
        final_workflow_stats = scheduler.workflow_engine.get_workflow_statistics()
        final_cron_stats = scheduler.cron_handler.get_statistics()
        
        print(f"📊 最终任务统计: {final_stats}")
        print(f"📊 最终工作流统计: {final_workflow_stats}")
        print(f"📊 最终定时任务统计: {final_cron_stats}")
        
        print("\n🎉 完整演示完成!")
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n9️⃣ 清理资源...")
        await scheduler.stop()
        print("✅ 调度器已停止")
        print("✅ 资源清理完成")

async def main():
    """主演示函数"""
    print("🔥 AgentBus任务调度系统 - 基于Moltbot的完整实现")
    print("📋 包含所有要求的功能:")
    print("   ✅ Cron表达式解析")
    print("   ✅ 任务调度执行")
    print("   ✅ 任务状态管理")
    print("   ✅ 任务失败重试")
    print("   ✅ 任务链和依赖")
    print("\n" + "=" * 60)
    
    await demo_complete_scheduler()
    
    print("\n" + "=" * 60)
    print("🎊 AgentBus任务调度系统演示完成!")
    print("📚 详细文档请查看: README.md")
    print("🧪 单元测试请运行: python test_scheduler.py")
    print("💡 使用示例请参考: python example.py")

if __name__ == "__main__":
    asyncio.run(main())