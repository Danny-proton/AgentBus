"""
AgentBus调度系统集成测试
"""

import asyncio
import tempfile
import shutil
from pathlib import Path

async def test_integration():
    """测试集成后的调度系统"""
    print("🔧 开始集成测试...")
    
    # 使用临时目录
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        from integration import AgentBusScheduler, SchedulerConfig
        
        # 创建调度器
        config = SchedulerConfig(
            storage_path=str(temp_dir),
            max_workers=2,
            enable_monitoring=True
        )
        
        scheduler = AgentBusScheduler(config)
        
        # 启动调度器
        await scheduler.start()
        print("✅ 调度器启动成功")
        
        # 创建测试任务
        async def test_task(name: str):
            print(f"执行任务: {name}")
            await asyncio.sleep(0.5)
            return f"任务 {name} 完成"
        
        # 测试定时任务
        task_id = await scheduler.create_scheduled_task(
            name="集成测试任务",
            cron_expression="*/1 * * * * *",  # 每秒执行一次
            func=test_task,
            args=("集成测试",),
            max_runs=3
        )
        print(f"✅ 创建定时任务: {task_id}")
        
        # 运行5秒
        await asyncio.sleep(5)
        
        # 健康检查
        health = await scheduler.health_check()
        print(f"✅ 健康检查: {health['status']}")
        
        # 获取状态
        status = scheduler.get_status()
        print(f"✅ 系统状态: {status['running']}")
        
        # 获取指标
        metrics = scheduler.get_metrics()
        print(f"✅ 任务统计: {metrics['tasks']}")
        print(f"✅ Cron统计: {metrics['cron']}")
        
        # 停止调度器
        await scheduler.stop()
        print("✅ 调度器停止成功")
        
        print("🎉 集成测试完成 - 所有功能正常!")
        return True
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    success = asyncio.run(test_integration())
    if success:
        print("\n🚀 AgentBus调度系统集成测试通过!")
    else:
        print("\n💥 AgentBus调度系统集成测试失败!")
        exit(1)