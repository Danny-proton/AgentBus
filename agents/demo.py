#!/usr/bin/env python3
"""
AgentBus Agent System Demo
Agent系统框架演示

演示如何使用新创建的Agent系统框架的所有功能：
1. Agent生命周期管理
2. Agent通信机制  
3. Agent状态监控
4. Agent资源管理
5. Agent插件系统
"""

import asyncio
import json
from typing import Dict, Any, List
from datetime import datetime

# 导入Agent系统组件
from . import (
    # 核心组件
    AgentType, AgentStatus, AgentState, ResourceType,
    AgentCapability, AgentMetadata, AgentConfig, AgentMetrics,
    BaseAgent, AgentFactory, AgentManager, AgentRegistry,
    
    # 生命周期管理
    LifecycleManager, LifecycleEvent, LifecycleState,
    create_lifecycle_manager, get_lifecycle_manager,
    
    # 通信机制
    CommunicationBus, MessageType, Priority,
    AgentMessage, BroadcastMessage, DirectMessage,
    create_communication_bus, get_communication_bus,
    
    # 状态监控
    MonitoringSystem, HealthStatus, AlertLevel,
    AgentHealth, SystemMetrics, Alert,
    create_monitoring_system, get_monitoring_system,
    
    # 资源管理
    ResourceManager, ResourceQuota, ResourcePool,
    ResourceUsage, create_resource_manager, get_resource_manager,
    
    # 插件系统
    PluginSystem, PluginType, PluginManifest,
    PluginManager, PluginInstance,
    create_plugin_system, get_plugin_system,
    
    # 便利函数
    get_agent_system, initialize_agent_system,
    shutdown_agent_system, create_agent_instance,
    agent_system
)


class DemoAgent(BaseAgent):
    """演示Agent类"""
    
    def __init__(self, config: AgentConfig, metadata: AgentMetadata):
        super().__init__(config, metadata)
        self.logger = f"demo.agent.{config.agent_id}"
        self.processed_tasks = []
    
    async def initialize(self) -> bool:
        """初始化Agent"""
        print(f"[{self.logger}] Initializing demo agent...")
        
        # 模拟初始化过程
        await asyncio.sleep(0.1)
        
        print(f"[{self.logger}] Demo agent initialized successfully")
        return True
    
    async def start(self) -> bool:
        """启动Agent"""
        print(f"[{self.logger}] Starting demo agent...")
        
        # 模拟启动过程
        await asyncio.sleep(0.1)
        
        print(f"[{self.logger}] Demo agent started successfully")
        return True
    
    async def stop(self):
        """停止Agent"""
        print(f"[{self.logger}] Stopping demo agent...")
        
        # 模拟停止过程
        await asyncio.sleep(0.1)
        
        print(f"[{self.logger}] Demo agent stopped")
    
    async def execute_task(self, task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        print(f"[{self.logger}] Executing task: {task_type} with parameters: {parameters}")
        
        # 模拟任务执行
        await asyncio.sleep(0.5)
        
        # 记录任务
        task_result = {
            "task_id": str(uuid.uuid4()),
            "task_type": task_type,
            "parameters": parameters,
            "result": f"Task {task_type} completed successfully",
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.config.agent_id
        }
        
        self.processed_tasks.append(task_result)
        
        # 更新指标
        self.metrics.update_metrics(
            success=True,
            tokens=100,  # 模拟令牌数
            cost=0.01,   # 模拟成本
            response_time=0.5,  # 模拟响应时间
            memory=50.0,  # 模拟内存使用
            cpu=20.0     # 模拟CPU使用
        )
        
        print(f"[{self.logger}] Task {task_type} completed successfully")
        return task_result
    
    def get_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        return {
            "agent_id": self.config.agent_id,
            "name": self.metadata.name,
            "type": self.config.agent_type.value,
            "status": self.status.value,
            "state": self.state.value,
            "metrics": self.metrics.to_dict(),
            "processed_tasks_count": len(self.processed_tasks),
            "last_task": self.processed_tasks[-1] if self.processed_tasks else None
        }


async def demo_agent_lifecycle():
    """演示Agent生命周期管理"""
    print("\n=== Agent生命周期管理演示 ===")
    
    async with agent_system() as system:
        # 创建Agent配置
        agent_config = AgentConfig(
            agent_id="demo_agent_1",
            agent_type=AgentType.CONVERSATION,
            resource_limits={
                "cpu": 1.0,
                "memory": 512.0,
                "concurrent_tasks": 2
            },
            max_concurrent_tasks=2
        )
        
        # 创建Agent元数据
        agent_metadata = AgentMetadata(
            agent_id="demo_agent_1",
            name="Demo Conversation Agent",
            description="A demo agent for conversation tasks",
            author="AgentBus Team"
        )
        
        # 创建Agent
        agent = await system.create_agent(agent_config, agent_metadata)
        if not agent:
            print("❌ Failed to create agent")
            return
        
        # 启动Agent
        success = await system.start_agent("demo_agent_1")
        if success:
            print("✅ Agent created and started successfully")
        else:
            print("❌ Failed to start agent")
            return
        
        # 获取Agent状态
        status = system.get_agent_status("demo_agent_1")
        print(f"Agent status: {json.dumps(status, indent=2)}")
        
        # 停止Agent
        await system.stop_agent("demo_agent_1")
        print("✅ Agent stopped successfully")


async def demo_agent_communication():
    """演示Agent通信机制"""
    print("\n=== Agent通信机制演示 ===")
    
    async with agent_system() as system:
        # 创建两个Agent用于通信演示
        agent_configs = [
            AgentConfig(
                agent_id="sender_agent",
                agent_type=AgentType.TASK_EXECUTION,
                max_concurrent_tasks=1
            ),
            AgentConfig(
                agent_id="receiver_agent", 
                agent_type=AgentType.CONVERSATION,
                max_concurrent_tasks=1
            )
        ]
        
        agent_metadata_list = [
            AgentMetadata(agent_id="sender_agent", name="Sender Agent"),
            AgentMetadata(agent_id="receiver_agent", name="Receiver Agent")
        ]
        
        # 创建并启动Agents
        agents = []
        for config, metadata in zip(agent_configs, agent_metadata_list):
            agent = await system.create_agent(config, metadata)
            if agent:
                await system.start_agent(config.agent_id)
                agents.append(agent)
        
        print(f"✅ Created {len(agents)} agents for communication demo")
        
        # 演示直接消息
        print("\n📤 Sending direct message...")
        success = await system.send_agent_message(
            sender_id="sender_agent",
            receiver_id="receiver_agent",
            content={"message": "Hello from sender agent!", "action": "greet"},
            message_type=MessageType.DIRECT
        )
        
        if success:
            print("✅ Direct message sent successfully")
        else:
            print("❌ Failed to send direct message")
        
        # 演示广播消息
        print("\n📢 Broadcasting message...")
        broadcast_message = AgentMessage(
            message_type=MessageType.BROADCAST,
            sender_id="sender_agent",
            receiver_id="all",
            content={"message": "This is a broadcast message", "timestamp": datetime.now().isoformat()},
            priority=Priority.HIGH
        )
        
        # 发送到通信总线
        if system.communication_bus:
            await system.communication_bus.send_message(broadcast_message)
            print("✅ Broadcast message sent successfully")
        
        # 清理
        for config in agent_configs:
            await system.stop_agent(config.agent_id)


async def demo_agent_monitoring():
    """演示Agent状态监控"""
    print("\n=== Agent状态监控演示 ===")
    
    async with agent_system() as system:
        # 创建Agent
        agent_config = AgentConfig(
            agent_id="monitoring_demo_agent",
            agent_type=AgentType.REASONING,
            resource_limits={
                "cpu": 0.5,
                "memory": 256.0
            }
        )
        
        agent_metadata = AgentMetadata(
            agent_id="monitoring_demo_agent",
            name="Monitoring Demo Agent"
        )
        
        agent = await system.create_agent(agent_config, agent_metadata)
        if not agent:
            print("❌ Failed to create agent for monitoring demo")
            return
        
        await system.start_agent("monitoring_demo_agent")
        print("✅ Agent created and started for monitoring demo")
        
        # 演示监控功能
        if system.monitoring_system:
            # 注册监控
            system.monitoring_system.register_agent("monitoring_demo_agent", agent)
            
            # 模拟执行一些任务来生成监控数据
            print("\n🔄 Executing tasks to generate monitoring data...")
            
            for i in range(3):
                await system.execute_agent_task(
                    "monitoring_demo_agent",
                    "analyze_data",
                    {"data": list(range(10)), "iteration": i}
                )
                await asyncio.sleep(0.2)
            
            # 获取健康状态
            health = system.monitoring_system.get_agent_health("monitoring_demo_agent")
            if health:
                print(f"\n📊 Agent health status:")
                print(f"  Status: {health.status.value}")
                print(f"  Response time: {health.response_time:.2f}s")
                print(f"  Error count: {health.error_count}")
                print(f"  Consecutive failures: {health.consecutive_failures}")
            
            # 获取系统指标
            metrics = system.get_system_metrics()
            print(f"\n📈 System metrics:")
            print(f"  Total agents: {metrics.total_agents}")
            print(f"  Active agents: {metrics.active_agents}")
            print(f"  System CPU: {metrics.system_cpu_usage:.1f}%")
            print(f"  System Memory: {metrics.system_memory_usage:.1f}%")
        
        # 清理
        await system.stop_agent("monitoring_demo_agent")


async def demo_resource_management():
    """演示Agent资源管理"""
    print("\n=== Agent资源管理演示 ===")
    
    async with agent_system() as system:
        if not system.resource_manager:
            print("❌ Resource manager not available")
            return
        
        print("✅ Resource manager initialized")
        
        # 演示资源配额查询
        print("\n📋 System resource quotas:")
        quotas = system.resource_manager.get_system_quotas()
        for resource_type, quota in quotas.items():
            print(f"  {resource_type.value}: {quota.limit} {quota.unit} (used: {quota.used}, available: {quota.available})")
        
        # 创建需要资源的Agent
        agent_config = AgentConfig(
            agent_id="resource_demo_agent",
            agent_type=AgentType.CODE_GENERATION,
            resource_limits={
                "cpu": 2.0,
                "memory": 1024.0,
                "concurrent_tasks": 3
            },
            max_concurrent_tasks=3
        )
        
        agent_metadata = AgentMetadata(
            agent_id="resource_demo_agent",
            name="Resource Demo Agent"
        )
        
        agent = await system.create_agent(agent_config, agent_metadata)
        if not agent:
            print("❌ Failed to create agent for resource demo")
            return
        
        await system.start_agent("resource_demo_agent")
        print("✅ Agent created with resource allocation")
        
        # 查看资源使用情况
        print("\n💾 Resource usage after agent start:")
        usage = system.resource_manager.get_agent_usage("resource_demo_agent")
        if usage:
            for resource_type, amount in usage.items():
                print(f"  {resource_type.value}: {amount}")
        
        # 获取系统资源利用率
        utilization = system.resource_manager.get_system_utilization()
        print(f"\n📊 System resource utilization:")
        for resource_type, rate in utilization.get("resource_utilization", {}).items():
            print(f"  {resource_type}: {rate:.1%}")
        
        # 清理
        await system.stop_agent("resource_demo_agent")


async def demo_plugin_system():
    """演示Agent插件系统"""
    print("\n=== Agent插件系统演示 ===")
    
    async with agent_system() as system:
        if not system.plugin_system:
            print("❌ Plugin system not available")
            return
        
        # 演示插件加载
        from .plugins.examples import (
            EXAMPLE_PLUGIN_MANIFEST,
            create_example_capability_plugin
        )
        
        print("✅ Plugin system initialized")
        
        # 模拟加载插件
        plugin_manifest = PluginManifest(
            plugin_id="demo_capability_plugin",
            name="Demo Capability Plugin",
            version="1.0.0",
            description="A demo plugin for capability extension",
            plugin_type=PluginType.CAPABILITY,
            capabilities=["custom_processing", "data_analysis"]
        )
        
        # 手动创建插件实例（演示目的）
        plugin_instance = create_example_capability_plugin(plugin_manifest.__dict__, {})
        
        # 加载插件
        await plugin_instance.on_load()
        await plugin_instance.on_enable()
        
        print("✅ Demo plugin loaded and enabled")
        
        # 测试插件功能
        print("\n🔧 Testing plugin capabilities:")
        
        # 测试文本处理
        test_message = AgentMessage(
            message_type=MessageType.DIRECT,
            sender_id="test_agent",
            receiver_id="demo_capability_plugin",
            content={
                "action": "custom_text_processing",
                "text": "hello world"
            }
        )
        
        await plugin_instance.on_message(test_message)
        print("  ✅ Custom text processing tested")
        
        # 测试数据分析
        test_message.content = {
            "action": "data_analysis",
            "data": [1, 2, 3, 4, 5]
        }
        
        await plugin_instance.on_message(test_message)
        print("  ✅ Data analysis tested")
        
        # 获取插件统计
        stats = system.plugin_system.get_plugin_stats()
        print(f"\n📈 Plugin statistics:")
        print(f"  Total plugins: {stats.get('total_plugins', 0)}")
        print(f"  Loaded plugins: {stats.get('loaded_plugins', 0)}")
        
        # 清理
        await plugin_instance.on_disable()
        await plugin_instance.on_unload()


async def demo_complete_workflow():
    """演示完整的Agent工作流"""
    print("\n=== 完整Agent工作流演示 ===")
    
    async with agent_system() as system:
        print("✅ Agent system initialized")
        
        # 1. 创建多个不同类型的Agent
        print("\n🏗️  Creating multiple agents...")
        
        agents_to_create = [
            (AgentType.CONVERSATION, "conversation_agent"),
            (AgentType.TASK_EXECUTION, "task_agent"),
            (AgentType.REASONING, "reasoning_agent")
        ]
        
        created_agents = []
        
        for agent_type, agent_id in agents_to_create:
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
                print(f"  ✅ Created {agent_type.value} agent: {agent_id}")
        
        # 2. 演示Agent间的通信
        print("\n💬 Demonstrating agent communication...")
        
        for i, sender in enumerate(created_agents):
            receiver = created_[(i + 1) % len(created_agents)]
            
            await system.send_agent_message(
                sender_id=sender,
                receiver_id=receiver,
                content={
                    "message": f"Message from {sender} to {receiver}",
                    "task": "collaboration_test"
                }
            )
            print(f"  📤 {sender} -> {receiver}")
        
        # 3. 执行任务并收集监控数据
        print("\n🎯 Executing tasks and collecting monitoring data...")
        
        for agent_id in created_agents:
            result = await system.execute_agent_task(
                agent_id=agent_id,
                task_type="process_request",
                parameters={
                    "request_id": f"req_{agent_id}",
                    "data": {"test": True, "timestamp": datetime.now().isoformat()}
                }
            )
            print(f"  ✅ {agent_id}: Task completed")
        
        # 4. 获取完整的系统状态
        print("\n📊 Complete system status:")
        
        system_status = system.get_system_status()
        print(f"  System ID: {system_status['system_id']}")
        print(f"  Running: {system_status['running']}")
        print(f"  Uptime: {system_status['uptime']:.1f}s")
        print(f"  Total agents: {system_status['agents']['total']}")
        
        # Agent状态分布
        status_counts = system_status['agents']['by_status']
        print(f"  Agent status distribution:")
        for status, count in status_counts.items():
            print(f"    {status}: {count}")
        
        # 系统统计
        stats = system_status['stats']
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Success rate: {stats['successful_requests']}/{stats['total_requests']}")
        
        # 5. 清理所有Agent
        print("\n🧹 Cleaning up all agents...")
        
        for agent_id in created_agents:
            await system.stop_agent(agent_id)
            print(f"  ✅ Stopped {agent_id}")
        
        print("\n🎉 Complete workflow demonstration finished!")


async def main():
    """主演示函数"""
    print("🚀 AgentBus Agent System Framework Demo")
    print("=" * 50)
    
    try:
        # 演示各个组件
        await demo_agent_lifecycle()
        await demo_agent_communication()
        await demo_agent_monitoring()
        await demo_resource_management()
        await demo_plugin_system()
        
        # 演示完整工作流
        await demo_complete_workflow()
        
        print("\n🎊 All demonstrations completed successfully!")
        print("\nAgent系统框架功能:")
        print("✅ Agent生命周期管理")
        print("✅ Agent通信机制")
        print("✅ Agent状态监控")
        print("✅ Agent资源管理")
        print("✅ Agent插件系统")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 添加必要的导入
    import uuid
    
    # 运行演示
    asyncio.run(main())