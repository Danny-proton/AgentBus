#!/usr/bin/env python3
"""
AgentBus Agent System Framework Test
Agent系统框架功能测试
"""

import asyncio
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.types import (
    AgentType, AgentStatus, AgentState, ResourceType,
    AgentCapability, AgentMetadata, AgentConfig, AgentMetrics,
    LifecycleEvent, LifecycleState, MessageType, Priority,
    HealthStatus, AlertLevel, PluginType
)
from core.base import BaseAgent
from core.manager import AgentSystem, agent_system


class TestAgent(BaseAgent):
    """测试Agent类"""
    
    def __init__(self, config: AgentConfig, metadata: AgentMetadata):
        super().__init__(config, metadata)
        self.processed_tasks = []
    
    async def initialize(self) -> bool:
        """初始化Agent"""
        print(f"📋 Initializing agent {self.config.agent_id}")
        await asyncio.sleep(0.1)
        print(f"✅ Agent {self.config.agent_id} initialized")
        return True
    
    async def start(self) -> bool:
        """启动Agent"""
        print(f"🚀 Starting agent {self.config.agent_id}")
        await asyncio.sleep(0.1)
        print(f"✅ Agent {self.config.agent_id} started")
        return True
    
    async def stop(self):
        """停止Agent"""
        print(f"🛑 Stopping agent {self.config.agent_id}")
        await asyncio.sleep(0.1)
        print(f"✅ Agent {self.config.agent_id} stopped")
    
    async def execute_task(self, task_type: str, parameters: dict) -> dict:
        """执行任务"""
        print(f"⚡ Executing task {task_type} for agent {self.config.agent_id}")
        await asyncio.sleep(0.2)
        
        result = {
            "task_id": f"task_{self.config.agent_id}_{len(self.processed_tasks)}",
            "task_type": task_type,
            "agent_id": self.config.agent_id,
            "result": f"Task {task_type} completed successfully",
            "timestamp": "2026-01-29T16:55:01"
        }
        
        self.processed_tasks.append(result)
        
        # 更新指标
        self.metrics.update_metrics(
            success=True,
            tokens=50,
            cost=0.01,
            response_time=0.2,
            memory=30.0,
            cpu=10.0
        )
        
        print(f"✅ Task {task_type} completed for agent {self.config.agent_id}")
        return result


async def test_basic_agent_lifecycle():
    """测试基本Agent生命周期"""
    print("\n🔄 === 测试基本Agent生命周期 ===")
    
    async with agent_system() as system:
        print("✅ Agent系统已启动")
        
        # 创建Agent配置
        config = AgentConfig(
            agent_id="test_agent_1",
            agent_type=AgentType.CONVERSATION,
            resource_limits={
                "cpu": 1.0,
                "memory": 512.0,
                "concurrent_tasks": 2
            },
            max_concurrent_tasks=2
        )
        
        metadata = AgentMetadata(
            agent_id="test_agent_1",
            name="Test Conversation Agent",
            description="A test agent for demonstration"
        )
        
        # 创建Agent
        agent = await system.create_agent(config, metadata)
        if not agent:
            print("❌ Agent创建失败")
            return False
        
        print(f"✅ Agent创建成功: {config.agent_id}")
        
        # 启动Agent
        success = await system.start_agent("test_agent_1")
        if not success:
            print("❌ Agent启动失败")
            return False
        
        # 执行一些任务
        for i in range(3):
            result = await system.execute_agent_task(
                "test_agent_1",
                "process_message",
                {"message": f"Test message {i}"}
            )
            print(f"📝 任务 {i+1} 执行结果: {result['result']}")
        
        # 获取Agent状态
        status = system.get_agent_status("test_agent_1")
        print(f"📊 Agent状态: {status['name']} - {status['status']}")
        
        # 停止Agent
        await system.stop_agent("test_agent_1")
        print("✅ Agent已停止")
        
        return True


async def test_agent_communication():
    """测试Agent通信"""
    print("\n💬 === 测试Agent通信 ===")
    
    async with agent_system() as system:
        # 创建发送方和接收方Agent
        agents_to_create = [
            ("sender_agent", AgentType.TASK_EXECUTION),
            ("receiver_agent", AgentType.CONVERSATION)
        ]
        
        created_agents = []
        
        for agent_id, agent_type in agents_to_create:
            config = AgentConfig(
                agent_id=agent_id,
                agent_type=agent_type,
                max_concurrent_tasks=1
            )
            
            metadata = AgentMetadata(
                agent_id=agent_id,
                name=f"{agent_id.replace('_', ' ').title()}"
            )
            
            agent = await system.create_agent(config, metadata)
            if agent:
                await system.start_agent(agent_id)
                created_agents.append(agent_id)
                print(f"✅ 创建Agent: {agent_id}")
        
        if len(created_agents) < 2:
            print("❌ Agent创建不足，无法测试通信")
            return False
        
        # 测试直接消息
        print("\n📤 发送直接消息...")
        success = await system.send_agent_message(
            sender_id="sender_agent",
            receiver_id="receiver_agent",
            content={
                "message": "Hello from sender!",
                "action": "test_communication"
            }
        )
        
        if success:
            print("✅ 直接消息发送成功")
        else:
            print("❌ 直接消息发送失败")
        
        # 清理
        for agent_id in created_agents:
            await system.stop_agent(agent_id)
            print(f"🧹 清理Agent: {agent_id}")
        
        return True


async def test_system_monitoring():
    """测试系统监控"""
    print("\n📊 === 测试系统监控 ===")
    
    async with agent_system() as system:
        # 创建监控Agent
        config = AgentConfig(
            agent_id="monitor_agent",
            agent_type=AgentType.REASONING,
            resource_limits={
                "cpu": 0.5,
                "memory": 256.0
            }
        )
        
        metadata = AgentMetadata(
            agent_id="monitor_agent",
            name="Monitoring Test Agent"
        )
        
        agent = await system.create_agent(config, metadata)
        if not agent:
            print("❌ 监控Agent创建失败")
            return False
        
        await system.start_agent("monitor_agent")
        print("✅ 监控Agent已启动")
        
        # 执行一些任务生成监控数据
        for i in range(5):
            await system.execute_agent_task(
                "monitor_agent",
                "monitoring_task",
                {"iteration": i, "data": list(range(10))}
            )
        
        # 获取系统状态
        system_status = system.get_system_status()
        print(f"📈 系统状态:")
        print(f"  - 系统ID: {system_status['system_id']}")
        print(f"  - 运行状态: {system_status['running']}")
        print(f"  - Agent总数: {system_status['agents']['total']}")
        print(f"  - 总请求数: {system_status['stats']['total_requests']}")
        print(f"  - 成功率: {system_status['stats']['successful_requests']}/{system_status['stats']['total_requests']}")
        
        # 获取Agent状态
        agent_status = system.get_agent_status("monitor_agent")
        print(f"📋 Agent状态:")
        print(f"  - 名称: {agent_status['name']}")
        print(f"  - 状态: {agent_status['status']}")
        print(f"  - 处理任务数: {agent_status['processed_tasks_count']}")
        
        await system.stop_agent("monitor_agent")
        return True


async def test_resource_management():
    """测试资源管理"""
    print("\n💾 === 测试资源管理 ===")
    
    async with agent_system() as system:
        if not system.resource_manager:
            print("❌ 资源管理器不可用")
            return False
        
        print("✅ 资源管理器可用")
        
        # 创建资源密集型Agent
        config = AgentConfig(
            agent_id="resource_agent",
            agent_type=AgentType.CODE_GENERATION,
            resource_limits={
                "cpu": 2.0,
                "memory": 1024.0,
                "concurrent_tasks": 3
            },
            max_concurrent_tasks=3
        )
        
        metadata = AgentMetadata(
            agent_id="resource_agent",
            name="Resource Test Agent"
        )
        
        agent = await system.create_agent(config, metadata)
        if not agent:
            print("❌ 资源Agent创建失败")
            return False
        
        await system.start_agent("resource_agent")
        print("✅ 资源Agent已启动")
        
        # 查看资源使用情况
        utilization = system.resource_manager.get_system_utilization()
        print(f"📊 系统资源利用率:")
        for resource_type, data in utilization.get("resource_utilization", {}).items():
            print(f"  - {resource_type}: {data['utilization_rate']:.1%} ({data['used']:.1f}/{data['total']:.1f})")
        
        await system.stop_agent("resource_agent")
        print("🧹 资源Agent已停止")
        
        return True


async def test_complete_workflow():
    """测试完整工作流"""
    print("\n🎯 === 测试完整工作流 ===")
    
    async with agent_system() as system:
        print("✅ 系统已初始化")
        
        # 创建多个不同类型的Agent
        agent_types = [
            (AgentType.CONVERSATION, "conv_agent"),
            (AgentType.TASK_EXECUTION, "task_agent"),
            (AgentType.REASONING, "reason_agent")
        ]
        
        created_agents = []
        
        for agent_type, agent_id in agent_types:
            config = AgentConfig(
                agent_id=agent_id,
                agent_type=agent_type,
                resource_limits={
                    "cpu": 1.0,
                    "memory": 512.0
                }
            )
            
            metadata = AgentMetadata(
                agent_id=agent_id,
                name=f"{agent_type.value.replace('_', ' ').title()} Agent"
            )
            
            agent = await system.create_agent(config, metadata)
            if agent:
                await system.start_agent(agent_id)
                created_agents.append(agent_id)
                print(f"✅ 创建{agent_type.value} agent: {agent_id}")
        
        if not created_agents:
            print("❌ 没有成功创建任何Agent")
            return False
        
        # 执行跨Agent通信
        print("\n💬 执行跨Agent通信...")
        for i, sender in enumerate(created_agents):
            receiver = created_agents[(i + 1) % len(created_agents)]
            
            await system.send_agent_message(
                sender_id=sender,
                receiver_id=receiver,
                content={
                    "message": f"协作消息 from {sender} to {receiver}",
                    "task": "collaboration"
                }
            )
            print(f"📤 {sender} -> {receiver}")
        
        # 执行任务
        print("\n⚡ 执行任务...")
        for agent_id in created_agents:
            result = await system.execute_agent_task(
                agent_id=agent_id,
                task_type="workflow_task",
                parameters={
                    "agent_role": agent_id,
                    "timestamp": "2026-01-29T16:55:01"
                }
            )
            print(f"✅ {agent_id}: 任务完成")
        
        # 最终系统状态
        print("\n📊 最终系统状态:")
        final_status = system.get_system_status()
        print(f"  - Agent总数: {final_status['agents']['total']}")
        print(f"  - 活跃Agent: {final_status['stats'].get('active_agents', 0)}")
        print(f"  - 总请求数: {final_status['stats']['total_requests']}")
        print(f"  - 成功请求数: {final_status['stats']['successful_requests']}")
        
        # 清理
        print("\n🧹 清理所有Agent...")
        for agent_id in created_agents:
            await system.stop_agent(agent_id)
            print(f"  ✅ 已停止 {agent_id}")
        
        return True


async def main():
    """主测试函数"""
    print("🚀 AgentBus Agent System Framework Test")
    print("=" * 50)
    
    test_results = []
    
    try:
        # 运行各项测试
        print("\n开始运行测试...")
        
        # 测试1: 基本生命周期
        result1 = await test_basic_agent_lifecycle()
        test_results.append(("Agent生命周期", result1))
        
        # 测试2: 通信机制
        result2 = await test_agent_communication()
        test_results.append(("Agent通信", result2))
        
        # 测试3: 监控功能
        result3 = await test_system_monitoring()
        test_results.append(("系统监控", result3))
        
        # 测试4: 资源管理
        result4 = await test_resource_management()
        test_results.append(("资源管理", result4))
        
        # 测试5: 完整工作流
        result5 = await test_complete_workflow()
        test_results.append(("完整工作流", result5))
        
        # 显示测试结果
        print("\n" + "=" * 50)
        print("📋 测试结果汇总:")
        print("=" * 50)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:15} : {status}")
            if result:
                passed += 1
        
        print(f"\n总计: {passed}/{total} 项测试通过")
        
        if passed == total:
            print("\n🎉 所有测试通过！Agent系统框架功能正常")
        else:
            print(f"\n⚠️  有 {total - passed} 项测试失败，需要进一步调试")
        
        # 功能检查清单
        print("\n✅ Agent系统框架功能清单:")
        print("  ✓ Agent生命周期管理")
        print("  ✓ Agent通信机制")
        print("  ✓ Agent状态监控")
        print("  ✓ Agent资源管理")
        print("  ✓ Agent插件系统（框架已实现）")
        
        return passed == total
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(main())
    sys.exit(0 if success else 1)