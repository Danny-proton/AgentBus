#!/usr/bin/env python3
"""
多模型协调器插件演示
Multi-Model Coordinator Plugin Demo

演示如何使用多模型协调器插件的各项功能，包括：
- 插件激活和配置
- 模型注册和管理
- 任务提交和处理
- 钩子系统和事件处理
- 统计和监控功能
"""

import asyncio
import json
import logging
from datetime import datetime

from agentbus.plugins import PluginContext
from agentbus.plugins.multi_model_plugin import MultiModelPlugin


async def demo_plugin_basic_usage():
    """演示插件基本使用方法"""
    print("🚀 多模型协调器插件基本使用演示")
    print("=" * 50)
    
    # 1. 创建插件上下文
    config = {
        'default_models': [],
        'fusion_strategy': 'best',
        'max_concurrent_tasks': 10,
        'enable_monitoring': True
    }
    
    logger = logging.getLogger('demo_plugin')
    logger.setLevel(logging.INFO)
    
    runtime = {'demo_mode': True}
    
    context = PluginContext(
        config=config,
        logger=logger,
        runtime=runtime
    )
    
    # 2. 创建插件实例
    plugin = MultiModelPlugin("demo_multi_model_plugin", context)
    
    print("✅ 插件实例创建完成")
    print(f"   插件ID: {plugin.plugin_id}")
    
    # 3. 获取插件信息
    info = plugin.get_info()
    print(f"\n📋 插件信息:")
    print(f"   名称: {info['name']}")
    print(f"   版本: {info['version']}")
    print(f"   描述: {info['description']}")
    print(f"   能力: {', '.join(info['capabilities'])}")
    
    # 4. 激活插件
    print(f"\n🔧 激活插件...")
    success = await plugin.activate()
    
    if success:
        print("✅ 插件激活成功")
        print(f"   状态: {plugin.status.value}")
        
        # 显示已注册的工具
        tools = plugin.get_tools()
        print(f"\n🛠️  已注册工具 ({len(tools)} 个):")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")
        
        # 显示已注册的钩子
        hooks = plugin.get_hooks()
        print(f"\n🔗 已注册钩子:")
        for event, event_hooks in hooks.items():
            print(f"   - {event}: {len(event_hooks)} 个处理器")
        
        # 显示已注册的命令
        commands = plugin.get_commands()
        print(f"\n💬 已注册命令:")
        for cmd in commands:
            print(f"   - {cmd['command']}: {cmd['description']}")
    else:
        print("❌ 插件激活失败")
        return
    
    return plugin


async def demo_model_management(plugin):
    """演示模型管理功能"""
    print(f"\n📊 模型管理演示")
    print("-" * 30)
    
    # 1. 列出当前模型
    print("1. 列出当前模型:")
    result = plugin.list_models_tool()
    if result['success']:
        print(f"   ✅ 找到 {result['total_count']} 个模型")
        for model in result['models']:
            status = "🟢" if model['is_active'] else "🔴"
            print(f"   {status} {model['model_name']} ({model['model_id']}) - {model['provider']}")
    else:
        print(f"   ❌ 获取模型列表失败: {result['error']}")
    
    # 2. 注册新模型
    print(f"\n2. 注册新模型:")
    register_result = plugin.register_model_tool(
        model_id="demo-gpt-4",
        model_name="Demo GPT-4",
        model_type="text_generation",
        provider="openai",
        capabilities=["text_generation", "question_answering", "reasoning"],
        cost_per_token=0.00003,
        quality_score=0.95,
        max_tokens=4096,
        temperature=0.7
    )
    
    if register_result['success']:
        print(f"   ✅ {register_result['message']}")
    else:
        print(f"   ❌ {register_result['error']}")
    
    # 3. 注册另一个模型
    print(f"\n3. 注册Claude模型:")
    claude_result = plugin.register_model_tool(
        model_id="demo-claude-3",
        model_name="Demo Claude-3",
        model_type="text_understanding",
        provider="anthropic",
        capabilities=["text_analysis", "reasoning", "technical_documentation"],
        cost_per_token=0.000025,
        quality_score=0.92,
        max_tokens=4096,
        temperature=0.7
    )
    
    if claude_result['success']:
        print(f"   ✅ {claude_result['message']}")
    else:
        print(f"   ❌ {claude_result['error']}")
    
    # 4. 再次列出模型
    print(f"\n4. 更新后的模型列表:")
    result = plugin.list_models_tool()
    if result['success']:
        print(f"   ✅ 总计 {result['total_count']} 个模型")
        for model in result['models']:
            status = "🟢" if model['is_active'] else "🔴"
            capabilities = ", ".join(model['capabilities'])
            print(f"   {status} {model['model_name']} - {capabilities}")
    
    # 5. 模型推荐演示
    print(f"\n5. 为文本生成任务推荐模型:")
    recommend_result = plugin.recommend_models_tool(
        task_type="text_generation",
        max_models=3
    )
    
    if recommend_result['success']:
        print(f"   ✅ 推荐 {recommend_result['recommendation_count']} 个模型:")
        for model in recommend_result['recommended_models']:
            print(f"   - {model['model_name']} (质量: {model['quality_score']:.2f}, 成本: ${model['cost_per_token']:.6f}/token)")
    else:
        print(f"   ❌ 模型推荐失败: {recommend_result['error']}")


async def demo_task_processing(plugin):
    """演示任务处理功能"""
    print(f"\n🎯 任务处理演示")
    print("-" * 30)
    
    # 1. 提交文本生成任务
    print("1. 提交文本生成任务:")
    text_task_result = await plugin.submit_multi_model_task(
        task_type="text_generation",
        content="请写一段关于人工智能发展的介绍，重点关注机器学习和深度学习的进展。",
        priority="normal",
        max_cost=0.02
    )
    
    if text_task_result['success']:
        print(f"   ✅ {text_task_result['message']}")
        print(f"   任务ID: {text_task_result['task_id']}")
        print(f"   预计使用模型数: {text_task_result['estimated_models']}")
        
        # 等待一段时间后获取结果
        print(f"\n   ⏳ 等待任务完成...")
        await asyncio.sleep(3)
        
        # 获取任务结果
        result = await plugin.get_task_result_tool(text_task_result['task_id'])
        if result['success']:
            print(f"   ✅ 任务完成:")
            print(f"   状态: {result['status']}")
            if result.get('final_content'):
                print(f"   结果摘要: {result['final_content'][:100]}...")
            print(f"   处理时间: {result['total_time']:.2f}秒")
            print(f"   总成本: ${result['total_cost']:.6f}")
            print(f"   融合方法: {result['fusion_method']}")
            
            if result.get('model_results'):
                print(f"   使用模型:")
                for model_result in result['model_results']:
                    print(f"     - {model_result['model_id']}: 置信度 {model_result['confidence']:.2f}")
        else:
            print(f"   ❌ 获取任务结果失败: {result['error']}")
    else:
        print(f"   ❌ {text_task_result['error']}")
    
    # 2. 提交问答任务
    print(f"\n2. 提交问答任务:")
    qa_task_result = await plugin.submit_multi_model_task(
        task_type="question_answering",
        content="什么是深度学习？它与传统机器学习有什么区别？",
        priority="high",
        max_cost=0.01
    )
    
    if qa_task_result['success']:
        print(f"   ✅ {qa_task_result['message']}")
        print(f"   任务ID: {qa_task_result['task_id']}")
        
        # 等待任务完成
        print(f"   ⏳ 等待任务完成...")
        await asyncio.sleep(2)
        
        # 获取结果
        result = await plugin.get_task_result_tool(qa_task_result['task_id'])
        if result['success'] and result['status'] == 'completed':
            print(f"   ✅ 问答任务完成")
            if result.get('final_content'):
                print(f"   答案摘要: {result['final_content'][:80]}...")
        else:
            print(f"   ⏳ 任务仍在处理中...")
    else:
        print(f"   ❌ {qa_task_result['error']}")
    
    # 3. 测试任务取消功能
    print(f"\n3. 测试任务取消功能:")
    cancel_task_result = await plugin.submit_multi_model_task(
        task_type="text_analysis",
        content="这是一个很长的文本分析任务" + " 用于测试的文本。" * 100,
        priority="normal",
        max_time=60
    )
    
    if cancel_task_result['success']:
        task_id = cancel_task_result['task_id']
        print(f"   ✅ 提交了可取消的任务: {task_id}")
        
        # 立即取消任务
        print(f"   🚫 取消任务...")
        cancel_result = await plugin.cancel_task_tool(task_id)
        
        if cancel_result['success']:
            print(f"   ✅ 任务取消成功")
        else:
            print(f"   ❌ 任务取消失败: {cancel_result['error']}")
        
        # 检查任务状态
        await asyncio.sleep(1)
        result = await plugin.get_task_result_tool(task_id)
        if result['success']:
            print(f"   最终状态: {result['status']}")


async def demo_statistics_and_monitoring(plugin):
    """演示统计和监控功能"""
    print(f"\n📈 统计和监控演示")
    print("-" * 30)
    
    # 1. 获取插件统计
    print("1. 插件统计信息:")
    plugin_stats = plugin.get_plugin_stats_tool()
    
    if plugin_stats['success']:
        stats = plugin_stats['stats']
        print(f"   提交任务数: {stats['tasks_submitted']}")
        print(f"   完成任务数: {stats['tasks_completed']}")
        print(f"   失败任务数: {stats['tasks_failed']}")
        print(f"   注册模型数: {stats['models_registered']}")
        print(f"   监控任务数: {plugin_stats['monitored_tasks']}")
        print(f"   注册工具数: {plugin_stats['registered_tools']}")
        print(f"   注册钩子数: {plugin_stats['registered_hooks']}")
        print(f"   注册命令数: {plugin_stats['registered_commands']}")
    else:
        print(f"   ❌ 获取插件统计失败: {plugin_stats['error']}")
    
    # 2. 获取协调器统计
    print(f"\n2. 协调器统计信息:")
    coord_stats = await plugin.get_coordinator_stats_tool()
    
    if coord_stats['success']:
        stats = coord_stats['stats']
        print(f"   活跃任务: {stats['active_tasks']}")
        print(f"   总任务数: {stats['total_tasks']}")
        print(f"   成功率: {stats['success_rate']:.1%}")
        print(f"   平均处理时间: {stats['avg_processing_time']:.2f}秒")
        print(f"   平均成本: ${stats['avg_cost']:.6f}")
        print(f"   注册模型数: {stats['registered_models']}")
        print(f"   活跃模型数: {stats['active_models']}")
    else:
        print(f"   ❌ 获取协调器统计失败: {coord_stats['error']}")
    
    # 3. 健康检查
    print(f"\n3. 健康检查:")
    health_result = await plugin.coordinator.health_check()
    
    print(f"   总体状态: {health_result['status']}")
    print(f"   检查时间: {health_result['timestamp']}")
    
    if 'checks' in health_result:
        checks = health_result['checks']
        print(f"   协调器运行状态: {'正常' if checks.get('coordinator_running') else '异常'}")
        
        if 'models_status' in checks:
            models_check = checks['models_status']
            print(f"   模型状态: {models_check['active']}/{models_check['total']} 活跃")
            print(f"   模型健康度: {models_check['health_ratio']:.1%}")
        
        if 'tasks_status' in checks:
            tasks_check = checks['tasks_status']
            print(f"   任务成功率: {tasks_check['success_ratio']:.1%}")


async def demo_commands(plugin):
    """演示命令功能"""
    print(f"\n💬 命令功能演示")
    print("-" * 30)
    
    # 1. /models 命令
    print("1. /models 命令:")
    models_result = await plugin.handle_models_command("")
    print(f"   {models_result}")
    
    # 2. /stats 命令
    print(f"\n2. /stats 命令:")
    stats_result = await plugin.handle_stats_command("")
    print(f"   {stats_result}")
    
    # 3. /health 命令
    print(f"\n3. /health 命令:")
    health_result = await plugin.handle_health_command("")
    print(f"   {health_result}")
    
    # 4. 带参数的 /models 命令
    print(f"\n4. /models text_generation 命令:")
    filtered_models_result = await plugin.handle_models_command("text_generation")
    print(f"   {filtered_models_result}")


async def demo_prompt_preparation(plugin):
    """演示提示词准备功能"""
    print(f"\n🔧 提示词准备演示")
    print("-" * 30)
    
    # 1. 准备不同类型的提示词
    task_types = ["text_generation", "code_generation", "summarization", "translation"]
    
    for task_type in task_types:
        print(f"\n{task_type} 提示词优化:")
        prompt_result = plugin.prepare_prompt_tool(
            task_type=task_type,
            content=f"这是一个{task_type}任务的测试内容。",
            context={"user_preference": "简洁", "language": "中文"}
        )
        
        if prompt_result['success']:
            print(f"   ✅ 原始内容: {prompt_result['original_content']}")
            print(f"   ✅ 优化后: {prompt_result['prepared_prompt']}")
            print(f"   应用优化: {'是' if prompt_result['optimization_applied'] else '否'}")
        else:
            print(f"   ❌ 提示词准备失败: {prompt_result['error']}")


async def main():
    """主演示函数"""
    try:
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        print(f"🎬 多模型协调器插件演示开始")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"=" * 60)
        
        # 1. 基本使用演示
        plugin = await demo_plugin_basic_usage()
        
        if plugin:
            # 2. 模型管理演示
            await demo_model_management(plugin)
            
            # 3. 任务处理演示
            await demo_task_processing(plugin)
            
            # 4. 统计和监控演示
            await demo_statistics_and_monitoring(plugin)
            
            # 5. 命令功能演示
            await demo_commands(plugin)
            
            # 6. 提示词准备演示
            await demo_prompt_preparation(plugin)
            
            # 7. 停用插件
            print(f"\n🔄 停用插件...")
            success = await plugin.deactivate()
            
            if success:
                print(f"✅ 插件停用成功")
            else:
                print(f"❌ 插件停用失败")
        
        print(f"\n🎉 演示完成！")
        print(f"=" * 60)
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())