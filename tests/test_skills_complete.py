#!/usr/bin/env python3
"""
技能系统完整测试
Complete Skills System Test

测试技能系统的所有功能：
1. 记忆系统
2. 技能管理器
3. 内置技能
4. 7*24小时运行机制
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from py_moltbot.core.logger import get_logger
from py_moltbot.skills.memory import get_memory_store, MemoryQuery
from py_moltbot.skills.manager import get_skill_manager, SkillExecutionMode
from py_moltbot.skills.builtin import register_builtin_skills
from py_moltbot.skills.base import SkillContext
from py_moltbot.adapters.base import User, Message, AdapterType

logger = get_logger(__name__)

import pytest

@pytest.fixture
async def skill_manager():
    """技能管理器 fixture"""
    # 注册内置技能
    register_builtin_skills()
    
    # 获取并启动技能管理器
    manager = await get_skill_manager()
    
    yield manager
    
    # 清理资源
    await manager.stop()


async def test_memory_system():
    """测试记忆系统"""
    print("\n🧠 测试记忆系统...")
    
    # 获取记忆存储
    memory_store = await get_memory_store()
    
    # 存储测试记忆
    memory_id1 = await memory_store.store_memory(
        content="这是一个测试记忆，用于验证记忆系统功能",
        tags={"test", "memory", "demo"},
        importance=5,
        source="test_system"
    )
    
    memory_id2 = await memory_store.store_memory(
        content="另一个测试记忆，包含计算结果：2+2=4",
        tags={"calculator", "math", "test"},
        importance=3,
        source="test_calculator"
    )
    
    # 测试搜索功能
    query = MemoryQuery(keywords=["测试"], limit=5)
    results = await memory_store.query_memories(query)
    
    assert len(results) >= 1, "应该找到至少一条测试记忆"
    
    # 测试标签搜索
    math_memories = await memory_store.get_memories_by_tag("math")
    assert len(math_memories) >= 1, "应该找到数学相关记忆"
    
    # 测试统计
    stats = await memory_store.get_stats()
    assert stats['total_memories'] >= 2, "应该有至少2条记忆"
    
    print(f"✅ 记忆系统测试通过 - 存储了{stats['total_memories']}条记忆")
    
    return memory_id1, memory_id2


async def test_builtin_skills():
    """测试内置技能"""
    print("\n🔧 测试内置技能...")
    
    # 注册内置技能
    register_builtin_skills()
    
    # 获取技能管理器
    skill_manager = await get_skill_manager()
    
    # 创建测试上下文
    user = User(
        id="test_user",
        platform=AdapterType.WEB,
        username="test_user",
        display_name="测试用户"
    )
    
    message = Message(
        id="test_msg_001",
        platform=AdapterType.WEB,
        chat_id="test_chat",
        user_id="test_user",
        content="",
        message_type="text"
    )
    
    context = SkillContext(
        user=user,
        message=message,
        chat_id="test_chat",
        platform=AdapterType.WEB,
        session_id="test_session"
    )
    
    # 测试计算器技能
    print("  - 测试计算器技能...")
    message.content = "2+2"
    result = await skill_manager.execute_skill("calculator", context)
    assert result.success, f"计算器技能失败: {result.error}"
    assert "4" in result.output, "计算结果应该包含4"
    
    # 测试记忆搜索技能
    print("  - 测试记忆搜索技能...")
    message.content = "测试"
    result = await skill_manager.execute_skill("memory_search", context)
    assert result.success, f"记忆搜索技能失败: {result.error}"
    
    # 测试提醒技能
    print("  - 测试提醒技能...")
    message.content = "添加:测试提醒事项"
    result = await skill_manager.execute_skill("reminder", context)
    assert result.success, f"提醒技能失败: {result.error}"
    
    # 测试系统状态技能
    print("  - 测试系统状态技能...")
    message.content = "技能"
    result = await skill_manager.execute_skill("system_status", context)
    assert result.success, f"系统状态技能失败: {result.error}"
    
    print("✅ 内置技能测试通过")
    
    return skill_manager


async def test_scheduled_tasks(skill_manager):
    """测试定时任务（7*24小时运行机制）"""
    print("\n⏰ 测试定时任务...")
    
    # 创建定时任务
    from datetime import timedelta
    
    # 设置一个每10秒执行一次的任务
    success = await skill_manager.schedule_skill(
        skill_name="system_status",
        interval=timedelta(seconds=10),
        max_runs=3,  # 只运行3次
        parameters={"mode": "quick_check"}
    )
    
    assert success, "定时任务设置失败"
    
    # 等待任务执行
    print("  - 等待定时任务执行...")
    await asyncio.sleep(15)  # 等待15秒，应该执行至少1次
    
    # 检查状态
    status = await skill_manager.get_skill_status("system_status")
    assert status["scheduled"], "system_status应该被调度"
    
    # 取消调度
    await skill_manager.cancel_schedule("system_status")
    
    print("✅ 定时任务测试通过")


async def test_execution_modes(skill_manager):
    """测试不同执行模式"""
    print("\n🚀 测试执行模式...")
    
    # 创建测试上下文
    user = User(
        id="test_user",
        platform=AdapterType.WEB,
        username="test_user",
        display_name="测试用户"
    )
    
    message = Message(
        id="test_msg_002",
        platform=AdapterType.WEB,
        chat_id="test_chat",
        user_id="test_user",
        content="2*3",
        message_type="text"
    )
    
    context = SkillContext(
        user=user,
        message=message,
        chat_id="test_chat",
        platform=AdapterType.WEB,
        session_id="test_session"
    )
    
    # 测试立即执行
    print("  - 测试立即执行模式...")
    result = await skill_manager.execute_skill(
        "calculator", 
        context, 
        mode=SkillExecutionMode.IMMEDIATE
    )
    assert result.success, f"立即执行失败: {result.error}"
    
    # 测试队列执行
    print("  - 测试队列执行模式...")
    result = await skill_manager.execute_skill(
        "calculator", 
        context, 
        mode=SkillExecutionMode.QUEUED
    )
    assert "queued" in result.output.lower(), "队列执行应该返回队列确认"
    
    # 测试后台执行
    print("  - 测试后台执行模式...")
    result = await skill_manager.execute_skill(
        "calculator", 
        context, 
        mode=SkillExecutionMode.BACKGROUND
    )
    assert "background" in result.output.lower(), "后台执行应该返回后台确认"
    
    print("✅ 执行模式测试通过")


async def test_long_running_operations():
    """测试长时间运行操作"""
    print("\n⏳ 测试长时间运行操作...")
    
    # 创建连续运行的任务
    skill_manager = await get_skill_manager()
    
    # 设置一个长时间运行的任务（实际只运行几分钟用于测试）
    success = await skill_manager.schedule_skill(
        skill_name="system_status",
        interval=timedelta(seconds=30),
        max_runs=10,  # 运行10次
        parameters={"mode": "monitoring"}
    )
    
    assert success, "长时间任务设置失败"
    
    print("  - 运行长时间任务监控...")
    
    # 监控2分钟
    start_time = datetime.now()
    while datetime.now() - start_time < timedelta(minutes=2):
        await asyncio.sleep(30)  # 每30秒检查一次
        stats = skill_manager.get_stats()
        print(f"    - 当前执行次数: {stats['total_executions']}")
        
        # 检查是否达到最大运行次数
        if stats['total_executions'] >= 5:
            break
    
    # 获取最终统计
    final_stats = skill_manager.get_stats()
    print(f"  - 最终执行统计: {final_stats}")
    
    # 取消任务
    await skill_manager.cancel_schedule("system_status")
    
    print("✅ 长时间运行操作测试通过")


async def test_error_handling():
    """测试错误处理"""
    print("\n🚨 测试错误处理...")
    
    skill_manager = await get_skill_manager()
    
    # 创建无效的测试上下文
    user = User(
        id="test_user",
        platform=AdapterType.WEB,
        username="test_user",
        display_name="测试用户"
    )
    
    message = Message(
        id="test_msg_error",
        platform=AdapterType.WEB,
        chat_id="test_chat",
        user_id="test_user",
        content="",
        message_type="text"
    )
    
    context = SkillContext(
        user=user,
        message=message,
        chat_id="test_chat",
        platform=AdapterType.WEB,
        session_id="test_session"
    )
    
    # 测试不存在的技能
    print("  - 测试不存在的技能...")
    result = await skill_manager.execute_skill("nonexistent_skill", context)
    assert not result.success, "不存在的技能应该失败"
    assert "not found" in result.error.lower(), "错误信息应该包含'not found'"
    
    # 测试无效的计算
    print("  - 测试无效计算...")
    message.content = "1/0"
    result = await skill_manager.execute_skill("calculator", context)
    assert not result.success, "除零错误应该失败"
    
    # 测试恶意输入
    print("  - 测试恶意输入防护...")
    message.content = "import os; os.system('echo hack')"
    result = await skill_manager.execute_skill("calculator", context)
    assert not result.success, "恶意输入应该被阻止"
    
    print("✅ 错误处理测试通过")


async def run_complete_test():
    """运行完整的技能系统测试"""
    print("🎯 开始技能系统完整测试")
    print("=" * 60)
    
    test_results = []
    
    try:
        # 测试1: 记忆系统
        memory_ids = await test_memory_system()
        test_results.append("记忆系统")
        
        # 测试2: 内置技能
        skill_manager = await test_builtin_skills()
        test_results.append("内置技能")
        
        # 测试3: 执行模式
        await test_execution_modes(skill_manager)
        test_results.append("执行模式")
        
        # 测试4: 定时任务
        await test_scheduled_tasks(skill_manager)
        test_results.append("定时任务")
        
        # 测试5: 错误处理
        await test_error_handling()
        test_results.append("错误处理")
        
        # 测试6: 长时间运行
        await test_long_running_operations()
        test_results.append("长时间运行")
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！")
        print(f"✅ 成功的测试模块: {', '.join(test_results)}")
        
        # 最终统计
        final_stats = skill_manager.get_stats()
        print(f"\n📊 最终系统统计:")
        print(f"  - 总技能数: {len(skill_manager.skills)}")
        print(f"  - 总执行次数: {final_stats['total_executions']}")
        print(f"  - 成功执行: {final_stats['successful_executions']}")
        print(f"  - 失败执行: {final_stats['failed_executions']}")
        
        # 记忆系统统计
        memory_store = await get_memory_store()
        memory_stats = await memory_store.get_stats()
        print(f"\n🧠 记忆系统统计:")
        print(f"  - 总记忆数: {memory_stats['total_memories']}")
        print(f"  - 总访问次数: {memory_stats['total_accesses']}")
        print(f"  - 总标签数: {memory_stats['total_tags']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理资源
        try:
            from py_moltbot.skills.manager import stop_skill_system
            from py_moltbot.skills.memory import stop_memory_system
            await stop_skill_system()
            await stop_memory_system()
        except:
            pass


if __name__ == "__main__":
    # 设置日志级别
    import logging
    logging.getLogger().setLevel(logging.INFO)
    
    # 运行测试
    success = asyncio.run(run_complete_test())
    
    if success:
        print("\n🎊 技能系统测试完全成功！系统已准备好用于生产环境。")
    else:
        print("\n💥 技能系统测试失败，请检查错误信息。")
        sys.exit(1)
