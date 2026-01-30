"""
HITL 功能测试
HITL Feature Test Suite
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from agentbus.services.hitl import HITLService, HITLPriority, HITLStatus
from agentbus.services.communication_map import CommunicationMap, Contact
from agentbus.services.message_channel import MessageChannel, MessageType, MessagePriority

async def test_hitl_system():
    """测试完整的HITL系统"""
    
    print("🧪 开始测试 HITL 系统...")
    print("=" * 60)
    
    # 1. 初始化服务
    print("\n📋 步骤 1: 初始化服务")
    
    hitl_service = HITLService()
    comm_map = CommunicationMap()
    msg_channel = MessageChannel()
    
    await hitl_service.start()
    await comm_map.load()
    await msg_channel.initialize()
    
    print("✅ 所有服务初始化完成")
    
    # 2. 测试沟通地图
    print("\n📋 步骤 2: 测试沟通地图")
    
    # 添加测试联系人
    test_contact = Contact(
        id="test_expert",
        name="测试专家",
        role="technical_expert",
        expertise={"testing", "debugging", "api_design"},
        availability="work_hours",
        contact_methods=[
            {"type": "email", "value": "expert@test.com"},
            {"type": "slack", "value": "@test_expert"}
        ],
        priority_score=0.9,
        response_time_estimate=15
    )
    
    await comm_map.add_contact(test_contact)
    print(f"✅ 添加联系人: {test_contact.name}")
    
    # 测试联系人匹配
    test_context = {
        "task_type": "testing",
        "domain": "api",
        "required_expertise": ["testing", "api_design"],
        "keywords": ["test", "debug"]
    }
    
    matched_contacts = await comm_map.find_contacts_by_context(test_context)
    print(f"✅ 匹配到 {len(matched_contacts)} 个联系人: {matched_contacts}")
    
    # 3. 测试HITL请求
    print("\n📋 步骤 3: 测试HITL请求创建")
    
    request_id = await hitl_service.create_hitl_request(
        agent_id="test_agent",
        title="API接口测试失败",
        description="在测试AgentBus API时遇到接口响应异常，需要专家协助调试",
        context={
            "task_type": "testing",
            "domain": "api",
            "error_details": "HTTP 500 错误",
            "affected_endpoint": "/api/v1/hitl/requests"
        },
        priority=HITLPriority.HIGH,
        timeout_minutes=10,
        assigned_to="test_expert"
    )
    
    print(f"✅ HITL请求创建成功: {request_id}")
    
    # 获取请求详情
    request = await hitl_service.get_hitl_request(request_id)
    print(f"✅ 请求详情: {request.title} - 状态: {request.status.value}")
    
    # 4. 测试HITL响应
    print("\n📋 步骤 4: 测试HITL响应")
    
    success = await hitl_service.submit_hitl_response(
        request_id=request_id,
        responder_id="test_expert",
        content="我检查了代码，发现是依赖注入的问题。已经在API路由中添加了正确的依赖管理。",
        is_final=True,
        attachments=[
            {
                "type": "file",
                "name": "fix_suggestions.md",
                "content": "详细的修复建议..."
            }
        ]
    )
    
    if success:
        print("✅ HITL响应提交成功")
        
        # 验证请求状态
        updated_request = await hitl_service.get_hitl_request(request_id)
        print(f"✅ 请求状态已更新: {updated_request.status.value}")
    else:
        print("❌ HITL响应提交失败")
    
    # 5. 测试消息通道
    print("\n📋 步骤 5: 测试消息通道")
    
    # 发送测试消息
    message_id = await msg_channel.send_message(
        sender_id="test_system",
        sender_type="system",
        content="这是一条测试消息",
        recipients=["test_user"],
        message_type=MessageType.TEXT,
        priority=MessagePriority.NORMAL
    )
    
    print(f"✅ 消息发送成功: {message_id}")
    
    # 发送HITL消息
    hitl_message_id = await msg_channel.send_message(
        sender_id="test_agent",
        sender_type="agent",
        content="🚨 需要人工协助处理重要问题",
        recipients=["test_expert"],
        message_type=MessageType.HITL_NOTIFICATION,
        priority=MessagePriority.HIGH,
        is_hitl=True,
        hitl_data={
            "request_id": request_id,
            "is_urgent": True
        }
    )
    
    print(f"✅ HITL消息发送成功: {hitl_message_id}")
    
    # 6. 测试统计信息
    print("\n📋 步骤 6: 获取统计信息")
    
    hitl_stats = await hitl_service.get_hitl_statistics()
    print(f"✅ HITL统计: 活跃请求 {hitl_stats['active_requests']}, 总请求 {hitl_stats['total_requests']}")
    
    comm_stats = await comm_map.get_contact_stats()
    print(f"✅ 沟通地图统计: 联系人 {comm_stats['total_contacts']}, 活跃 {comm_stats['active_contacts']}")
    
    # 7. 清理资源
    print("\n📋 步骤 7: 清理资源")
    
    await hitl_service.stop()
    await comm_map.save()
    await msg_channel.close()
    
    print("✅ 所有资源清理完成")
    
    print("\n🎉 HITL系统测试完成！")
    print("=" * 60)


async def test_hitl_api_integration():
    """测试HITL API集成"""
    
    print("\n🔗 测试 HITL API 集成...")
    print("=" * 60)
    
    # 导入FastAPI测试客户端
    try:
        from fastapi.testclient import TestClient
        from agentbus.api.main import create_app
        
        # 创建测试应用
        app = create_app()
        client = TestClient(app)
        
        print("✅ FastAPI测试客户端创建成功")
        
        # 测试健康检查
        response = client.get("/health")
        if response.status_code == 200:
            print("✅ 健康检查端点正常")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
        
        # 测试API信息
        response = client.get("/api/info")
        if response.status_code == 200:
            api_info = response.json()
            if "hitl" in api_info.get("endpoints", {}):
                print("✅ HITL API端点信息正常")
            else:
                print("❌ HITL API端点信息缺失")
        else:
            print(f"❌ API信息获取失败: {response.status_code}")
        
        # 注意：完整的HITL API测试需要启动服务，这里只做基础验证
        print("ℹ️  完整HITL API测试需要在运行服务后进行")
        
    except ImportError:
        print("⚠️  FastAPI测试客户端未安装，跳过API集成测试")
    
    print("🔗 HITL API集成测试完成")


async def main():
    """主测试函数"""
    
    print("🚀 AgentBus HITL 系统测试开始")
    print("时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    try:
        # 运行HITL系统测试
        await test_hitl_system()
        
        # 运行API集成测试
        await test_hitl_api_integration()
        
        print("\n✅ 所有测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
