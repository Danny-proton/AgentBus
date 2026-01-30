#!/usr/bin/env python3
"""
知识总线插件化重构测试脚本
Knowledge Bus Plugin Refactoring Test Script

此脚本测试知识总线重构后的功能，确保插件化后的功能与原来完全兼容。
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# 添加项目路径到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from agentbus.services.knowledge_bus import (
    KnowledgeBus,
    KnowledgeBusWithPluginSupport,
    KnowledgeType, 
    KnowledgeSource, 
    KnowledgeStatus,
    KnowledgeQuery
)
from agentbus.plugins import PluginContext
from agentbus.plugins.knowledge_plugin import KnowledgeBusPlugin
from agentbus.core.settings import settings


async def test_original_knowledge_bus():
    """测试原有的知识总线功能"""
    print("\n🧪 测试原有知识总线功能...")
    print("=" * 60)
    
    # 使用原有知识总线
    kb = KnowledgeBus()
    await kb.initialize()
    
    # 测试添加知识
    fact_id = await kb.add_knowledge(
        content="原有知识总线测试知识",
        knowledge_type=KnowledgeType.FACT,
        source=KnowledgeSource.USER_INPUT,
        created_by="test_user",
        tags={"测试", "原有"},
        confidence=1.0
    )
    
    # 测试搜索
    query = KnowledgeQuery(query="原有", limit=10)
    results = await kb.search_knowledge(query)
    
    # 测试统计
    stats = await kb.get_knowledge_stats()
    
    await kb.shutdown()
    
    print(f"✅ 原有知识总线测试完成")
    print(f"   - 添加知识ID: {fact_id}")
    print(f"   - 搜索结果: {len(results)} 条")
    print(f"   - 统计信息: {stats['total_knowledge']} 条知识")
    
    return fact_id


async def test_plugin_knowledge_bus():
    """测试插件化的知识总线功能"""
    print("\n🧪 测试插件化知识总线功能...")
    print("=" * 60)
    
    # 创建插件上下文
    import logging
    
    # 使用标准logging.Logger
    logger = logging.getLogger("test_plugin")
    logger.setLevel(logging.INFO)
    
    context = PluginContext(
        config={"test": True},
        logger=logger,
        runtime={"test_mode": True}
    )
    
    # 创建并激活插件
    plugin = KnowledgeBusPlugin("test_plugin", context)
    await plugin.activate()
    
    # 测试插件工具
    fact_id = await plugin.add_knowledge_tool(
        content="插件化知识总线测试知识",
        knowledge_type="fact",
        source="user_input",
        created_by="plugin_test",
        tags={"测试", "插件"},
        confidence=0.9
    )
    
    # 测试搜索
    search_results = await plugin.search_knowledge_tool(
        query="插件化",
        limit=10
    )
    
    # 测试统计
    stats = await plugin.get_knowledge_stats_tool()
    
    # 测试兼容性方法
    compatibility_results = await plugin.search_knowledge(KnowledgeQuery(query="插件化", limit=10))
    
    await plugin.deactivate()
    
    print(f"✅ 插件化知识总线测试完成")
    print(f"   - 添加知识ID: {fact_id}")
    print(f"   - 搜索结果: {len(search_results)} 条")
    print(f"   - 兼容性搜索: {len(compatibility_results)} 条")
    print(f"   - 统计信息: {stats['total_knowledge']} 条知识")
    
    return fact_id


async def test_plugin_support_knowledge_bus():
    """测试支持插件的知识总线"""
    print("\n🧪 测试支持插件的知识总线...")
    print("=" * 60)
    
    # 使用支持插件的知识总线
    kb = KnowledgeBusWithPluginSupport()
    await kb.initialize()
    
    # 注册插件钩子
    async def test_hook(knowledge_id, content):
        print(f"🔗 钩子被触发: 知识 {knowledge_id} - {content}")
    
    kb.register_plugin_hook("knowledge_added", test_hook)
    
    # 测试添加知识（会触发钩子）
    await kb.add_knowledge(
        content="支持插件的知识总线测试",
        knowledge_type=KnowledgeType.FACT,
        source=KnowledgeSource.USER_INPUT,
        created_by="plugin_support_test",
        tags={"支持", "插件"},
        confidence=0.95
    )
    
    # 测试工具注册
    def test_tool():
        return "插件工具测试"
    
    kb.register_plugin_tool("test_tool", test_tool, "测试工具")
    
    # 测试命令注册
    def test_command():
        return "插件命令测试"
    
    kb.register_plugin_command("/test", test_command, "测试命令")
    
    # 获取注册的钩子、工具和命令
    hooks = kb.get_plugin_hooks()
    tools = kb.get_plugin_tools()
    commands = kb.get_plugin_commands()
    
    await kb.shutdown()
    
    print(f"✅ 支持插件的知识总线测试完成")
    print(f"   - 注册钩子: {len(hooks)} 个")
    print(f"   - 注册工具: {len(tools)} 个")
    print(f"   - 注册命令: {len(commands)} 个")
    
    return True


async def test_compatibility():
    """测试向后兼容性"""
    print("\n🧪 测试向后兼容性...")
    print("=" * 60)
    
    # 测试原有代码是否仍然工作
    kb = KnowledgeBus()
    await kb.initialize()
    
    # 模拟原有测试代码
    test_cases = [
        {
            "content": "兼容性测试1",
            "knowledge_type": KnowledgeType.FACT,
            "source": KnowledgeSource.USER_INPUT,
            "created_by": "compat_test",
            "tags": {"兼容", "测试1"}
        },
        {
            "content": "兼容性测试2",
            "knowledge_type": KnowledgeType.PROCEDURE,
            "source": KnowledgeSource.MANUAL_ENTRY,
            "created_by": "compat_test",
            "tags": {"兼容", "测试2"}
        }
    ]
    
    knowledge_ids = []
    for case in test_cases:
        k_id = await kb.add_knowledge(**case)
        knowledge_ids.append(k_id)
    
    # 测试各种查询
    query = KnowledgeQuery(query="兼容性", limit=10)
    results = await kb.search_knowledge(query)
    
    # 测试统计
    stats = await kb.get_knowledge_stats()
    
    # 测试获取
    knowledge = await kb.get_knowledge(knowledge_ids[0])
    
    # 测试更新
    success = await kb.update_knowledge(
        knowledge_ids[0],
        confidence=0.8
    )
    
    # 测试按类型获取
    facts = await kb.get_knowledge_by_type(KnowledgeType.FACT)
    procedures = await kb.get_knowledge_by_type(KnowledgeType.PROCEDURE)
    
    await kb.shutdown()
    
    print(f"✅ 向后兼容性测试完成")
    print(f"   - 创建知识: {len(knowledge_ids)} 条")
    print(f"   - 搜索结果: {len(results)} 条")
    print(f"   - 按类型获取 - 事实: {len(facts)} 条, 程序: {len(procedures)} 条")
    print(f"   - 更新成功: {success}")
    print(f"   - 获取知识: {knowledge.content if knowledge else 'None'}")
    
    return True


async def test_plugin_integration():
    """测试插件集成"""
    print("\n🧪 测试插件集成...")
    print("=" * 60)
    
    import logging
    
    # 使用标准logging.Logger
    logger = logging.getLogger("integration_test")
    logger.setLevel(logging.INFO)
    
    context = PluginContext(
        config={
            "knowledge_bus": {
                "file_path": "./integration_test.json",
                "auto_save": True
            }
        },
        logger=logger,
        runtime={"test_mode": True}
    )
    
    # 创建插件
    plugin = KnowledgeBusPlugin("integration_test", context)
    
    # 激活插件
    try:
        success = await plugin.activate()
        if not success:
            print(f"❌ 插件激活失败")
            return False
        print("✅ 插件激活成功")
    except Exception as e:
        print(f"❌ 插件激活异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 执行完整的知识管理流程
    print("📝 执行完整知识管理流程...")
    
    # 1. 添加多种类型的知识
    knowledge_ids = []
    
    # 事实知识
    fact_id = await plugin.add_knowledge_tool(
        content="AgentBus是一个智能协作平台",
        knowledge_type="fact",
        source="user_input",
        created_by="integration_test",
        tags={"AgentBus", "平台", "智能"},
        confidence=0.95
    )
    knowledge_ids.append(fact_id)
    
    # 程序知识
    proc_id = await plugin.add_knowledge_tool(
        content="启动AgentBus: python cli.py --reload",
        knowledge_type="procedure",
        source="manual_entry", 
        created_by="integration_test",
        tags={"启动", "命令", "CLI"},
        confidence=1.0
    )
    knowledge_ids.append(proc_id)
    
    # 规则知识
    rule_id = await plugin.add_knowledge_tool(
        content="创建HITL请求时应提供清晰描述",
        knowledge_type="rule",
        source="user_input",
        created_by="integration_test", 
        tags={"HITL", "规则", "最佳实践"},
        confidence=0.9
    )
    knowledge_ids.append(rule_id)
    
    print(f"✅ 添加了 {len(knowledge_ids)} 条知识")
    
    # 2. 搜索测试
    search_tests = [
        ("AgentBus", 1),
        ("启动", 1),
        ("HITL", 1),
        ("智能", 1)
    ]
    
    for query_text, expected_min in search_tests:
        results = await plugin.search_knowledge_tool(query=query_text, limit=10)
        print(f"   搜索'{query_text}': {len(results)} 条结果")
        assert len(results) >= expected_min, f"搜索 '{query_text}' 结果不足"
    
    # 3. 统计测试
    stats = await plugin.get_knowledge_stats_tool()
    print(f"✅ 统计信息: {stats['total_knowledge']} 条知识")
    assert stats['total_knowledge'] >= 3
    
    # 4. 分类测试
    facts = await plugin.get_knowledge_by_type_tool("fact")
    procedures = await plugin.get_knowledge_by_type_tool("procedure")
    rules = await plugin.get_knowledge_by_type_tool("rule")
    
    print(f"✅ 分类统计 - 事实: {len(facts)}, 程序: {len(procedures)}, 规则: {len(rules)}")
    
    # 5. 标签测试
    agentbus_knowledge = await plugin.get_knowledge_by_tags_tool(["AgentBus"])
    hitl_knowledge = await plugin.get_knowledge_by_tags_tool(["HITL"])
    
    print(f"✅ 标签查询 - AgentBus: {len(agentbus_knowledge)}, HITL: {len(hitl_knowledge)}")
    
    # 6. 使用统计测试
    await plugin.record_knowledge_usage_tool(fact_id)
    await plugin.record_knowledge_usage_tool(fact_id)
    
    most_used = await plugin.get_most_used_knowledge_tool(5)
    print(f"✅ 热门知识: {len(most_used)} 条")
    
    # 7. 更新测试
    success = await plugin.update_knowledge_tool(
        knowledge_id=fact_id,
        content="AgentBus是一个强大的智能协作平台",
        confidence=0.98
    )
    assert success is True
    print("✅ 知识更新成功")
    
    # 8. 命令测试
    help_result = await plugin.handle_kb_help_command("")
    assert "知识总线插件帮助" in help_result
    print("✅ 帮助命令测试成功")
    
    stats_result = await plugin.handle_kb_stats_command("")
    assert "知识总线统计信息" in stats_result
    print("✅ 统计命令测试成功")
    
    # 停用插件
    await plugin.deactivate()
    
    # 清理测试文件
    if os.path.exists("./integration_test.json"):
        os.remove("./integration_test.json")
    
    print(f"✅ 插件集成测试完成")
    return True


async def main():
    """主测试函数"""
    print("🚀 知识总线插件化重构测试开始")
    print("=" * 80)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = {}
    
    try:
        # 1. 测试原有功能
        test_results["原有知识总线"] = await test_original_knowledge_bus()
        
        # 2. 测试插件化功能
        test_results["插件化知识总线"] = await test_plugin_knowledge_bus()
        
        # 3. 测试插件支持
        test_results["插件支持总线"] = await test_plugin_support_knowledge_bus()
        
        # 4. 测试兼容性
        test_results["向后兼容性"] = await test_compatibility()
        
        # 5. 测试集成
        test_results["插件集成"] = await test_plugin_integration()
        
        print("\n" + "=" * 80)
        print("🎉 所有测试完成！")
        print("\n📊 测试结果总结:")
        for test_name, result in test_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {test_name}: {status}")
        
        if all(test_results.values()):
            print("\n🎊 所有测试都通过了！知识总线插件化重构成功！")
        else:
            print("\n⚠️  有测试失败，请检查实现")
            
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return all(test_results.values())


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)