"""
知识总线功能测试
Knowledge Bus Feature Test Suite
"""

import asyncio
from datetime import datetime

from agentbus.services.knowledge_bus import (
    KnowledgeBus, 
    KnowledgeType, 
    KnowledgeSource, 
    KnowledgeStatus,
    KnowledgeQuery
)

async def test_knowledge_bus():
    """测试知识总线系统"""
    
    print("🧪 开始测试 Knowledge Bus 系统...")
    print("=" * 60)
    
    # 1. 初始化知识总线
    print("\n📋 步骤 1: 初始化知识总线")
    
    kb = KnowledgeBus()
    await kb.initialize()
    print("✅ 知识总线初始化完成")
    
    # 2. 创建测试知识
    print("\n📋 步骤 2: 创建测试知识")
    
    # 创建事实知识
    fact_id = await kb.add_knowledge(
        content="AgentBus是一个智能协作平台，提供多智能体协作、工具调用、记忆管理和API接口的综合解决方案。",
        knowledge_type=KnowledgeType.FACT,
        source=KnowledgeSource.MANUAL_ENTRY,
        created_by="test_user",
        tags={"系统介绍", "平台特性"},
        confidence=1.0,
        metadata={"category": "介绍", "importance": "high"}
    )
    print(f"✅ 创建事实知识: {fact_id}")
    
    # 创建程序知识
    procedure_id = await kb.add_knowledge(
        content="要启动AgentBus服务，请使用命令：python cli.py --reload 或 python cli.py --host 0.0.0.0 --port 8000",
        knowledge_type=KnowledgeType.PROCEDURE,
        source=KnowledgeSource.MANUAL_ENTRY,
        created_by="system",
        tags={"启动", "CLI", "命令"},
        confidence=1.0,
        metadata={"category": "操作指南", "target": "用户"}
    )
    print(f"✅ 创建程序知识: {procedure_id}")
    
    # 创建规则知识
    rule_id = await kb.add_knowledge(
        content="在创建HITL请求时，应该提供清晰的标题和描述，包含必要的上下文信息，以便更好地匹配合适的联系人。",
        knowledge_type=KnowledgeType.RULE,
        source=KnowledgeSource.MANUAL_ENTRY,
        created_by="expert",
        tags={"HITL", "最佳实践", "请求"},
        confidence=0.9,
        metadata={"category": "最佳实践", "applicability": "HITL"}
    )
    print(f"✅ 创建规则知识: {rule_id}")
    
    # 3. 测试知识搜索
    print("\n📋 步骤 3: 测试知识搜索")
    
    # 搜索包含"启动"的知识
    from agentbus.services.knowledge_bus import KnowledgeQuery
    query = KnowledgeQuery(
        query="启动",
        limit=10
    )
    results = await kb.search_knowledge(query)
    print(f"✅ 搜索'启动'关键词，找到 {len(results)} 条知识")
    
    for result in results:
        print(f"   - {result.knowledge.content[:50]}... (相关性: {result.relevance_score:.2f})")
    
    # 4. 测试知识更新
    print("\n📋 步骤 4: 测试知识更新")
    
    success = await kb.update_knowledge(
        knowledge_id=procedure_id,
        confidence=0.95,
        metadata={"updated": True, "update_time": datetime.now().isoformat()}
    )
    
    if success:
        print("✅ 知识更新成功")
        
        # 验证更新
        updated_knowledge = await kb.get_knowledge(procedure_id)
        print(f"✅ 更新后的置信度: {updated_knowledge.confidence}")
    else:
        print("❌ 知识更新失败")
    
    # 5. 测试知识关系
    print("\n📋 步骤 5: 测试知识关系")
    
    # 建立知识之间的关联
    fact_knowledge = await kb.get_knowledge(fact_id)
    procedure_knowledge = await kb.get_knowledge(procedure_id)
    
    if fact_knowledge and procedure_knowledge:
        fact_knowledge.related_knowledge.add(procedure_id)
        procedure_knowledge.related_knowledge.add(fact_id)
        
        await kb.update_knowledge(fact_id)
        await kb.update_knowledge(procedure_id)
        
        print("✅ 知识关系建立成功")
    
    # 6. 测试统计信息
    print("\n📋 步骤 6: 获取统计信息")
    
    stats = await kb.get_knowledge_stats()
    print(f"✅ 知识统计:")
    print(f"   - 总知识数: {stats['total_knowledge']}")
    print(f"   - 按类型统计: {stats['by_type']}")
    print(f"   - 按来源统计: {stats['by_source']}")
    print(f"   - 总使用次数: {stats['total_usage']}")
    print(f"   - 平均置信度: {stats['average_confidence']}")
    
    # 7. 测试使用记录
    print("\n📋 步骤 7: 测试使用记录")
    
    await kb.record_knowledge_usage(fact_id)
    await kb.record_knowledge_usage(fact_id)
    await kb.record_knowledge_usage(procedure_id)
    
    # 获取使用最多的知识
    most_used = await kb.get_most_used_knowledge(5)
    print(f"✅ 使用最多的知识:")
    for knowledge, usage_count in most_used:
        print(f"   - {knowledge.content[:30]}... (使用 {usage_count} 次)")
    
    # 8. 测试知识过滤
    print("\n📋 步骤 8: 测试知识过滤")
    
    # 按类型获取知识
    facts = await kb.get_knowledge_by_type(KnowledgeType.FACT)
    procedures = await kb.get_knowledge_by_type(KnowledgeType.PROCEDURE)
    
    print(f"✅ 按类型过滤:")
    print(f"   - 事实知识: {len(facts)} 条")
    print(f"   - 程序知识: {len(procedures)} 条")
    
    # 按标签获取知识
    hitl_knowledge = await kb.get_knowledge_by_tags(["HITL"])
    print(f"   - HITL相关知识: {len(hitl_knowledge)} 条")
    
    # 9. 清理和关闭
    print("\n📋 步骤 9: 清理资源")
    
    await kb.shutdown()
    print("✅ 知识总线已关闭")
    
    print("\n🎉 Knowledge Bus 系统测试完成！")
    print("=" * 60)


async def test_knowledge_advanced_features():
    """测试知识总线高级功能"""
    
    print("\n🚀 测试 Knowledge Bus 高级功能...")
    print("=" * 60)
    
    kb = KnowledgeBus()
    await kb.initialize()
    
    # 1. 创建复杂的查询
    print("\n📋 步骤 1: 复杂查询测试")
    
    # 添加更多测试知识
    await kb.add_knowledge(
        content="知识总线提供了强大的搜索和索引功能，支持多种查询方式和过滤条件。",
        knowledge_type=KnowledgeType.FACT,
        source=KnowledgeSource.AGENT_LEARNING,
        created_by="ai_agent",
        tags={"知识总线", "搜索", "索引"},
        confidence=0.8
    )
    
    await kb.add_knowledge(
        content="HITL（Human-in-the-Loop）是一种重要的AI协作模式，允许AI代理在遇到复杂问题时向人类求助。",
        knowledge_type=KnowledgeType.CONTEXT,
        source=KnowledgeSource.USER_INPUT,
        created_by="user",
        tags={"HITL", "协作", "人工智能"},
        confidence=0.9
    )
    
    # 执行复合查询
    query = KnowledgeQuery(
        query="AI HITL 协作",
        knowledge_types=[KnowledgeType.CONTEXT, KnowledgeType.FACT],
        tags=["HITL", "协作"],
        confidence_threshold=0.7,
        limit=10
    )
    
    results = await kb.search_knowledge(query)
    print(f"✅ 复合查询结果: {len(results)} 条知识")
    
    for result in results:
        print(f"   - {result.knowledge.content[:40]}...")
        print(f"     相关性: {result.relevance_score:.2f}")
        print(f"     匹配原因: {', '.join(result.match_reasons)}")
    
    # 2. 测试知识验证和状态管理
    print("\n📋 步骤 2: 知识状态管理")
    
    # 创建验证中的知识
    validation_id = await kb.add_knowledge(
        content="这是一个需要验证的知识项，其准确性需要进一步确认。",
        knowledge_type=KnowledgeType.METADATA,
        source=KnowledgeSource.AUTO_GENERATED,
        created_by="system",
        tags={"验证中"},
        confidence=0.5,
        metadata={"validation_required": True}
    )
    
    # 更新为不活跃状态
    await kb.update_knowledge(
        knowledge_id=validation_id,
        status=KnowledgeStatus.INACTIVE
    )
    
    print("✅ 知识状态管理测试完成")
    
    # 3. 测试元数据操作
    print("\n📋 步骤 3: 元数据操作")
    
    # 更新元数据
    await kb.update_knowledge(
        knowledge_id=validation_id,
        metadata={
            "validation_score": 0.6,
            "reviewer": "expert",
            "last_review": datetime.now().isoformat(),
            "approved": False
        }
    )
    
    knowledge = await kb.get_knowledge(validation_id)
    print(f"✅ 元数据更新完成: {knowledge.metadata}")
    
    await kb.shutdown()
    print("\n🎉 Knowledge Bus 高级功能测试完成！")


async def main():
    """主测试函数"""
    
    print("🚀 AgentBus Knowledge Bus 系统测试开始")
    print("时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    try:
        # 运行基础功能测试
        await test_knowledge_bus()
        
        # 运行高级功能测试
        await test_knowledge_advanced_features()
        
        print("\n✅ 所有测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
