#!/usr/bin/env python3
"""
多模型协调器测试脚本
Multi-Model Coordinator Test Script

测试多模型协调器的各项功能，包括模型注册、任务提交、结果查询等。
"""

import asyncio
import json
import time
from datetime import datetime
from agentbus.services.multi_model_coordinator import (
    MultiModelCoordinator,
    ModelConfig,
    TaskRequest,
    TaskType,
    TaskPriority,
    ModelType,
)
from agentbus.core.settings import settings


async def test_multi_model_coordinator():
    """测试多模型协调器功能"""
    
    print("🚀 AgentBus 多模型协调器测试")
    print("=" * 50)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 初始化协调器
    print("📋 步骤 1: 初始化多模型协调器")
    coordinator = MultiModelCoordinator()
    await coordinator.initialize()
    print("✅ 多模型协调器初始化完成")
    
    # 2. 获取默认模型
    print("\n📋 步骤 2: 查看默认注册模型")
    available_models = coordinator.get_available_models()
    print(f"✅ 默认注册了 {len(available_models)} 个模型:")
    for model in available_models:
        print(f"   - {model.model_id} ({model.model_name}) - {model.provider}")
    
    # 3. 注册自定义模型
    print("\n📋 步骤 3: 注册自定义模型")
    custom_model = ModelConfig(
        model_id="gpt-3.5-turbo",
        model_name="GPT-3.5 Turbo",
        model_type=ModelType.TEXT_GENERATION,
        provider="openai",
        capabilities=[TaskType.TEXT_GENERATION, TaskType.QUESTION_ANSWERING],
        cost_per_token=0.000002,
        quality_score=0.88,
        max_tokens=4096,
        temperature=0.7
    )
    coordinator.register_model(custom_model)
    print("✅ 自定义模型注册完成")
    
    # 4. 提交任务
    print("\n📋 步骤 4: 提交各种类型任务")
    
    # 文本生成任务
    text_gen_task = TaskRequest(
        task_id="text_gen_001",
        task_type=TaskType.TEXT_GENERATION,
        content="请写一段关于人工智能的介绍",
        priority=TaskPriority.NORMAL,
        required_capabilities=[TaskType.TEXT_GENERATION],
        max_cost=0.01
    )
    task_id_1 = await coordinator.submit_task(text_gen_task)
    print(f"✅ 文本生成任务已提交: {task_id_1}")
    
    # 代码生成任务
    code_gen_task = TaskRequest(
        task_id="code_gen_001", 
        task_type=TaskType.CODE_GENERATION,
        content="请写一个Python的Hello World程序",
        priority=TaskPriority.HIGH,
        required_capabilities=[TaskType.CODE_GENERATION],
        max_cost=0.005
    )
    task_id_2 = await coordinator.submit_task(code_gen_task)
    print(f"✅ 代码生成任务已提交: {task_id_2}")
    
    # 问答任务
    qa_task = TaskRequest(
        task_id="qa_001",
        task_type=TaskType.QUESTION_ANSWERING,
        content="什么是机器学习？",
        priority=TaskPriority.NORMAL,
        required_capabilities=[TaskType.QUESTION_ANSWERING],
        max_cost=0.003
    )
    task_id_3 = await coordinator.submit_task(qa_task)
    print(f"✅ 问答任务已提交: {task_id_3}")
    
    # 5. 等待任务完成
    print("\n📋 步骤 5: 等待任务处理完成")
    
    tasks_to_check = [task_id_1, task_id_2, task_id_3]
    max_wait_time = 30  # 最多等待30秒
    start_time = time.time()
    
    while tasks_to_check and (time.time() - start_time) < max_wait_time:
        completed_tasks = []
        
        for task_id in tasks_to_check:
            result = await coordinator.get_task_result(task_id)
            if result:
                if result.status.value == "completed":
                    completed_tasks.append(task_id)
                    print(f"✅ 任务 {task_id} 已完成")
                    print(f"   结果: {result.final_content[:100]}...")
                    print(f"   使用模型: {[r.model_id for r in result.model_results]}")
                    print(f"   处理时间: {result.total_time:.2f}s")
                    print(f"   成本: ${result.total_cost:.6f}")
                elif result.status.value == "failed":
                    completed_tasks.append(task_id)
                    print(f"❌ 任务 {task_id} 失败: {result.error}")
        
        # 移除已完成的任务
        for task_id in completed_tasks:
            tasks_to_check.remove(task_id)
        
        if tasks_to_check:
            print(f"⏳ 还有 {len(tasks_to_check)} 个任务在处理中...")
            await asyncio.sleep(2)
    
    if tasks_to_check:
        print("⚠️  部分任务可能仍在处理中或超时")
    
    # 6. 测试统计信息
    print("\n📋 步骤 6: 查看协调器统计信息")
    stats = await coordinator.get_coordinator_stats()
    print("✅ 协调器统计:")
    print(f"   活跃任务: {stats['active_tasks']}")
    print(f"   总任务数: {stats['total_tasks']}")
    print(f"   成功率: {stats['success_rate']:.2%}")
    print(f"   平均处理时间: {stats['avg_processing_time']:.2f}s")
    print(f"   平均成本: ${stats['avg_cost']:.6f}")
    print(f"   注册模型数: {stats['registered_models']}")
    print(f"   活跃模型数: {stats['active_models']}")
    
    # 7. 测试模型推荐
    print("\n📋 步骤 7: 测试模型推荐")
    recommended_models = coordinator.get_available_models(TaskType.TEXT_GENERATION)
    print(f"✅ 文本生成任务推荐模型:")
    for model in recommended_models[:3]:  # 显示前3个
        print(f"   - {model.model_id}: 质量 {model.quality_score:.2f}, 成本 ${model.cost_per_token:.6f}/token")
    
    # 8. 清理
    print("\n📋 步骤 8: 清理资源")
    await coordinator.shutdown()
    print("✅ 协调器已关闭")
    
    print("\n🎉 多模型协调器测试完成！")
    print("=" * 50)


async def test_model_registration():
    """测试模型注册功能"""
    
    print("\n🔧 测试模型注册功能")
    print("-" * 30)
    
    coordinator = MultiModelCoordinator()
    await coordinator.initialize()
    
    # 测试注册不同类型的模型
    test_models = [
        ModelConfig(
            model_id="claude-2",
            model_name="Claude 2",
            model_type=ModelType.TEXT_UNDERSTANDING,
            provider="anthropic",
            capabilities=[TaskType.TEXT_ANALYSIS, TaskType.REASONING],
            cost_per_token=0.00001,
            quality_score=0.9
        ),
        ModelConfig(
            model_id="codex",
            model_name="OpenAI Codex",
            model_type=ModelType.CODE_GENERATION,
            provider="openai",
            capabilities=[TaskType.CODE_GENERATION, TaskType.TEXT_GENERATION],
            cost_per_token=0.000003,
            quality_score=0.85
        ),
        ModelConfig(
            model_id="local-code-llama",
            model_name="Code Llama 7B",
            model_type=ModelType.CODE_GENERATION,
            provider="local",
            capabilities=[TaskType.CODE_GENERATION],
            cost_per_token=0.0,
            quality_score=0.7
        )
    ]
    
    for model in test_models:
        success = coordinator.register_model(model)
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{status} 注册模型: {model.model_id}")
    
    # 显示所有注册模型
    all_models = list(coordinator.models.values())
    print(f"\n总计注册模型: {len(all_models)}")
    
    # 按提供者分组
    providers = {}
    for model in all_models:
        if model.provider not in providers:
            providers[model.provider] = []
        providers[model.provider].append(model)
    
    for provider, models in providers.items():
        print(f"\n{provider} 提供者 ({len(models)} 个模型):")
        for model in models:
            print(f"  - {model.model_id}: {model.model_name}")
    
    await coordinator.shutdown()


async def test_task_cancellation():
    """测试任务取消功能"""
    
    print("\n🚫 测试任务取消功能")
    print("-" * 30)
    
    coordinator = MultiModelCoordinator()
    await coordinator.initialize()
    
    # 提交一个长时间任务
    long_task = TaskRequest(
        task_id="long_task_001",
        task_type=TaskType.TEXT_ANALYSIS,
        content="请详细分析以下长文本：" + "这是一个测试文本。 " * 100,  # 模拟长文本
        priority=TaskPriority.NORMAL,
        required_capabilities=[TaskType.TEXT_ANALYSIS],
        max_time=60  # 允许60秒处理时间
    )
    
    task_id = await coordinator.submit_task(long_task)
    print(f"✅ 长时间任务已提交: {task_id}")
    
    # 立即取消任务
    await asyncio.sleep(1)  # 等待任务开始处理
    success = await coordinator.cancel_task(task_id)
    
    if success:
        print("✅ 任务取消成功")
        
        # 检查任务状态
        result = await coordinator.get_task_result(task_id)
        if result:
            print(f"   最终状态: {result.status.value}")
    else:
        print("❌ 任务取消失败")
    
    await coordinator.shutdown()


async def main():
    """主测试函数"""
    try:
        await test_multi_model_coordinator()
        await test_model_registration()
        await test_task_cancellation()
        
        print("\n🎯 所有测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())