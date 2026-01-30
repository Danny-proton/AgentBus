"""
HITL + Knowledge Bus 集成测试
Integrated Test for HITL and Knowledge Bus
"""

import asyncio
from datetime import datetime

from agentbus.services.hitl import HITLService, HITLPriority
from agentbus.services.knowledge_bus import KnowledgeBus, KnowledgeType, KnowledgeSource

async def test_hitl_knowledge_integration():
    """测试HITL与知识总线的集成"""
    
    print("🧪 开始测试 HITL + Knowledge Bus 集成...")
    print("=" * 60)
    
    # 1. 初始化服务
    print("\n📋 步骤 1: 初始化服务")
    
    hitl_service = HITLService()
    knowledge_bus = KnowledgeBus()
    
    await hitl_service.start()
    await knowledge_bus.initialize()
    
    print("✅ HITL服务和知识总线初始化完成")
    
    # 2. 创建相关知识
    print("\n📋 步骤 2: 创建HITL相关知识")
    
    # 添加HITL最佳实践知识
    best_practice_id = await knowledge_bus.add_knowledge(
        content="HITL（人在回路）请求应该包含清晰的上下文信息和具体的任务描述，以便智能匹配最合适的联系人。",
        knowledge_type=KnowledgeType.RULE,
        source=KnowledgeSource.MANUAL_ENTRY,
        created_by="system",
        tags={"HITL", "最佳实践", "请求创建"},
        confidence=0.9
    )
    
    # 添加联系方式知识
    contact_info_id = await knowledge_bus.add_knowledge(
        content="当HITL请求包含紧急标记时，系统会优先联系具有高优先级评分的联系人。",
        knowledge_type=KnowledgeType.FACT,
        source=KnowledgeSource.MANUAL_ENTRY,
        created_by="system",
        tags={"HITL", "紧急处理", "优先级"},
        confidence=0.8
    )
    
    print(f"✅ 创建了 {2} 条HITL相关知识")
    
    # 3. 模拟HITL请求场景
    print("\n📋 步骤 3: 模拟HITL请求场景")
    
    # 创建一个复杂的HITL请求
    request_id = await hitl_service.create_hitl_request(
        agent_id="test_agent",
        title="API接口调试需要专家协助",
        description="在开发AgentBus的HITL功能时，遇到了复杂的API接口问题，需要有经验的开发专家协助调试。问题涉及HITL请求创建、知识检索和响应处理。",
        context={
            "task_type": "debugging",
            "domain": "api_development",
            "technology": "fastapi",
            "priority": "high",
            "tags": ["API", "调试", "HITL", "开发"]
        },
        priority=HITLPriority.HIGH,
        timeout_minutes=15
    )
    
    print(f"✅ HITL请求创建成功: {request_id}")
    
    # 4. 测试知识检索增强HITL
    print("\n📋 步骤 4: 测试知识检索增强")
    
    # 模拟AI代理查找相关知识来辅助HITL请求
    query = await knowledge_bus.search_knowledge(
        type("Query", (), {
            "query": "HITL 请求 创建 最佳实践",
            "knowledge_types": [KnowledgeType.RULE, KnowledgeType.FACT],
            "tags": ["HITL"],
            "confidence_threshold": 0.7,
            "limit": 5,
            "include_inactive": False
        })()
    )
    
    print(f"✅ 检索到 {len(query)} 条相关知识")
    for result in query:
        print(f"   - {result.knowledge.content[:60]}... (相关性: {result.relevance_score:.2f})")
    
    # 5. 模拟HITL响应和知识更新
    print("\n📋 步骤 5: 模拟HITL响应和知识学习")
    
    # 提交HITL响应
    await hitl_service.submit_hitl_response(
        request_id=request_id,
        responder_id="expert_developer",
        content="已解决API接口问题。问题原因是依赖注入配置错误，已通过正确的依赖管理修复。建议参考最佳实践文档中的HITL集成指南。",
        is_final=True,
        attachments=[
            {
                "type": "solution",
                "description": "API调试解决方案",
                "file_path": "fixes/api_debug_solution.md"
            }
        ]
    )
    
    # 基于HITL响应创建新知识
    solution_id = await knowledge_bus.add_knowledge(
        content="API依赖注入错误的解决方案：在AgentBus中，HITL API需要正确配置依赖注入系统，确保HITLService、CommunicationMap和KnowledgeBus服务的正确集成。",
        knowledge_type=KnowledgeType.PROCEDURE,
        source=KnowledgeSource.AGENT_LEARNING,
        created_by="expert_developer",
        tags={"API", "依赖注入", "修复", "HITL"},
        confidence=0.95,
        metadata={
            "source_request": request_id,
            "category": "troubleshooting",
            "verified": True
        }
    )
    
    print("✅ HITL响应处理完成，新知识已创建")
    
    # 6. 测试统计信息
    print("\n📋 步骤 6: 获取集成统计信息")
    
    # HITL统计
    hitl_stats = await hitl_service.get_hitl_statistics()
    print(f"✅ HITL统计:")
    print(f"   - 活跃请求: {hitl_stats['active_requests']}")
    print(f"   - 总请求: {hitl_stats['total_requests']}")
    print(f"   - 完成率: {hitl_stats['completion_rate']:.2%}")
    
    # 知识总线统计
    kb_stats = await knowledge_bus.get_knowledge_stats()
    print(f"✅ 知识统计:")
    print(f"   - 总知识数: {kb_stats['total_knowledge']}")
    print(f"   - HITL相关知识: {len(await knowledge_bus.get_knowledge_by_tags(['HITL']))}")
    print(f"   - 平均置信度: {kb_stats['average_confidence']:.2f}")
    
    # 7. 清理资源
    print("\n📋 步骤 7: 清理资源")
    
    await hitl_service.stop()
    await knowledge_bus.shutdown()
    
    print("✅ 所有服务已关闭")
    
    print("\n🎉 HITL + Knowledge Bus 集成测试完成！")
    print("=" * 60)


async def main():
    """主测试函数"""
    
    print("🚀 AgentBus HITL & Knowledge Bus 集成测试")
    print("时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    try:
        await test_hitl_knowledge_integration()
        print("\n✅ 集成测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
