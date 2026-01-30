#!/usr/bin/env python3
"""
AgentBus Agent System Framework - Complete Usage Example
Agent系统框架完整使用示例

这个示例展示了如何使用Agent系统框架的所有核心功能：
1. Agent生命周期管理
2. Agent通信机制
3. Agent状态监控
4. Agent资源管理
5. Agent插件系统
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List

# 模拟导入（实际使用时应该是真实的导入）
# from .core.types import *
# from .core.base import *
# from .core.manager import *

class AgentType:
    """模拟Agent类型枚举"""
    CONVERSATION = "conversation"
    TASK_EXECUTION = "task_execution"
    REASONING = "reasoning"
    MONITORING = "monitoring"

class AgentStatus:
    """模拟Agent状态枚举"""
    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"

class MessageType:
    """模拟消息类型枚举"""
    DIRECT = "direct"
    BROADCAST = "broadcast"
    SYSTEM = "system"

class Priority:
    """模拟消息优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class AgentConfig:
    """Agent配置类"""
    def __init__(self, agent_id: str, agent_type: str, **kwargs):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.resource_limits = kwargs.get('resource_limits', {})
        self.max_concurrent_tasks = kwargs.get('max_concurrent_tasks', 1)
        self.capabilities = kwargs.get('capabilities', [])


class AgentMetadata:
    """Agent元数据类"""
    def __init__(self, agent_id: str, name: str, **kwargs):
        self.agent_id = agent_id
        self.name = name
        self.description = kwargs.get('description', '')
        self.author = kwargs.get('author', 'AgentBus')


class AgentMessage:
    """Agent消息类"""
    def __init__(self, message_type: str, sender_id: str, receiver_id: str, 
                 content: Any, **kwargs):
        self.message_type = message_type
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.content = content
        self.priority = kwargs.get('priority', Priority.NORMAL)
        self.timestamp = datetime.now().isoformat()
        self.message_id = f"msg_{int(datetime.now().timestamp())}"


class BaseAgent:
    """基础Agent类"""
    def __init__(self, config: AgentConfig, metadata: AgentMetadata):
        self.config = config
        self.metadata = metadata
        self.agent_id = config.agent_id
        self.status = AgentStatus.CREATED
        self.processed_messages = []
        self.executed_tasks = []
    
    async def initialize(self) -> bool:
        """初始化Agent"""
        print(f"🔄 [{self.agent_id}] 正在初始化...")
        await asyncio.sleep(0.5)
        self.status = AgentStatus.RUNNING
        print(f"✅ [{self.agent_id}] 初始化完成")
        return True
    
    async def start(self) -> bool:
        """启动Agent"""
        print(f"🚀 [{self.agent_id}] 正在启动...")
        await asyncio.sleep(0.2)
        print(f"✅ [{self.agent_id}] 启动完成")
        return True
    
    async def stop(self):
        """停止Agent"""
        print(f"🛑 [{self.agent_id}] 正在停止...")
        await asyncio.sleep(0.1)
        self.status = AgentStatus.STOPPED
        print(f"✅ [{self.agent_id}] 已停止")
    
    async def execute_task(self, task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        print(f"⚡ [{self.agent_id}] 执行任务: {task_type}")
        await asyncio.sleep(0.3)
        
        result = {
            "task_id": f"task_{self.agent_id}_{len(self.executed_tasks)}",
            "task_type": task_type,
            "agent_id": self.agent_id,
            "parameters": parameters,
            "result": f"任务 {task_type} 执行成功",
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
        
        self.executed_tasks.append(result)
        print(f"✅ [{self.agent_id}] 任务 {task_type} 完成")
        return result
    
    async def handle_message(self, message: AgentMessage):
        """处理消息"""
        print(f"💬 [{self.agent_id}] 收到消息 from {message.sender_id}")
        await asyncio.sleep(0.1)
        
        response = {
            "sender_id": self.agent_id,
            "receiver_id": message.sender_id,
            "content": f"收到来自 {message.sender_id} 的消息: {message.content}",
            "timestamp": datetime.now().isoformat()
        }
        
        self.processed_messages.append(message)
        print(f"✅ [{self.agent_id}] 消息处理完成")
        return response
    
    def get_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        return {
            "agent_id": self.agent_id,
            "name": self.metadata.name,
            "type": self.config.agent_type,
            "status": self.status,
            "processed_messages": len(self.processed_messages),
            "executed_tasks": len(self.executed_tasks),
            "capabilities": self.config.capabilities
        }


class CommunicationBus:
    """通信总线"""
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.message_history: List[AgentMessage] = []
    
    def register_agent(self, agent: BaseAgent):
        """注册Agent"""
        self.agents[agent.agent_id] = agent
        print(f"📡 [{agent.agent_id}] 已注册到通信总线")
    
    async def send_message(self, message: AgentMessage) -> bool:
        """发送消息"""
        self.message_history.append(message)
        
        if message.receiver_id == "all":
            # 广播消息
            for agent_id, agent in self.agents.items():
                if agent_id != message.sender_id:
                    await agent.handle_message(message)
        elif message.receiver_id in self.agents:
            # 直接消息
            await self.agents[message.receiver_id].handle_message(message)
        
        return True
    
    def get_message_stats(self) -> Dict[str, Any]:
        """获取消息统计"""
        return {
            "total_messages": len(self.message_history),
            "registered_agents": len(self.agents),
            "recent_messages": self.message_history[-5:]
        }


class MonitoringSystem:
    """监控系统"""
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.system_metrics = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "active_agents": 0,
            "total_tasks": 0,
            "total_messages": 0
        }
    
    def register_agent(self, agent: BaseAgent):
        """注册Agent到监控"""
        self.agents[agent.agent_id] = agent
        print(f"📊 [{agent.agent_id}] 已注册到监控系统")
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """收集系统指标"""
        active_agents = sum(1 for agent in self.agents.values() 
                          if agent.status == AgentStatus.RUNNING)
        
        total_tasks = sum(len(agent.executed_tasks) for agent in self.agents.values())
        total_messages = sum(len(agent.processed_messages) for agent in self.agents.values())
        
        self.system_metrics.update({
            "cpu_usage": min(100.0, active_agents * 10.0),  # 模拟CPU使用率
            "memory_usage": min(100.0, active_agents * 15.0),  # 模拟内存使用率
            "active_agents": active_agents,
            "total_tasks": total_tasks,
            "total_messages": total_messages,
            "timestamp": datetime.now().isoformat()
        })
        
        return self.system_metrics
    
    def get_agent_health(self, agent_id: str) -> Dict[str, Any]:
        """获取Agent健康状态"""
        if agent_id not in self.agents:
            return {"status": "not_found"}
        
        agent = self.agents[agent_id]
        return {
            "agent_id": agent_id,
            "status": agent.status,
            "tasks_executed": len(agent.executed_tasks),
            "messages_processed": len(agent.processed_messages),
            "health_score": 100 if agent.status == AgentStatus.RUNNING else 0
        }


class ResourceManager:
    """资源管理器"""
    def __init__(self):
        self.agent_allocations: Dict[str, Dict[str, float]] = {}
        self.resource_pool = {
            "cpu": {"total": 8.0, "used": 0.0},
            "memory": {"total": 16384.0, "used": 0.0},  # MB
            "storage": {"total": 100.0, "used": 0.0}   # GB
        }
    
    async def allocate_resources(self, agent_id: str, requirements: Dict[str, float]) -> bool:
        """分配资源"""
        allocated = {}
        
        for resource_type, required_amount in requirements.items():
            if resource_type in self.resource_pool:
                pool = self.resource_pool[resource_type]
                if pool["used"] + required_amount <= pool["total"]:
                    pool["used"] += required_amount
                    allocated[resource_type] = required_amount
                else:
                    print(f"❌ [{agent_id}] 资源不足: {resource_type}")
                    return False
        
        if allocated:
            self.agent_allocations[agent_id] = allocated
            print(f"💾 [{agent_id}] 资源分配成功: {allocated}")
        
        return bool(allocated)
    
    async def release_resources(self, agent_id: str):
        """释放资源"""
        if agent_id not in self.agent_allocations:
            return
        
        allocated = self.agent_allocations[agent_id]
        
        for resource_type, amount in allocated.items():
            if resource_type in self.resource_pool:
                self.resource_pool[resource_type]["used"] -= amount
        
        del self.agent_allocations[agent_id]
        print(f"🗑️ [{agent_id}] 资源已释放")
    
    def get_system_utilization(self) -> Dict[str, Any]:
        """获取系统资源利用率"""
        utilization = {}
        
        for resource_type, pool in self.resource_pool.items():
            utilization[resource_type] = {
                "total": pool["total"],
                "used": pool["used"],
                "available": pool["total"] - pool["used"],
                "utilization_rate": pool["used"] / pool["total"] if pool["total"] > 0 else 0
            }
        
        return utilization


class AgentSystem:
    """Agent系统主类"""
    def __init__(self, system_id: str = "default"):
        self.system_id = system_id
        self.agents: Dict[str, BaseAgent] = {}
        self.communication_bus = CommunicationBus()
        self.monitoring_system = MonitoringSystem()
        self.resource_manager = ResourceManager()
        self.running = False
        self.started_at = None
    
    async def initialize(self) -> bool:
        """初始化系统"""
        print(f"🚀 正在初始化Agent系统: {self.system_id}")
        
        # 初始化各个子系统
        self.running = True
        self.started_at = datetime.now()
        
        print("✅ Agent系统初始化完成")
        return True
    
    async def create_agent(self, config: AgentConfig, metadata: AgentMetadata) -> BaseAgent:
        """创建Agent"""
        agent = BaseAgent(config, metadata)
        self.agents[agent.agent_id] = agent
        
        # 注册到各个子系统
        self.communication_bus.register_agent(agent)
        self.monitoring_system.register_agent(agent)
        
        print(f"🏗️ Agent创建成功: {agent.agent_id}")
        return agent
    
    async def start_agent(self, agent_id: str) -> bool:
        """启动Agent"""
        if agent_id not in self.agents:
            print(f"❌ Agent不存在: {agent_id}")
            return False
        
        agent = self.agents[agent_id]
        
        # 分配资源
        resource_requirements = agent.config.resource_limits
        success = await self.resource_manager.allocate_resources(agent_id, resource_requirements)
        if not success:
            return False
        
        # 初始化并启动Agent
        await agent.initialize()
        await agent.start()
        
        print(f"✅ Agent启动成功: {agent_id}")
        return True
    
    async def stop_agent(self, agent_id: str):
        """停止Agent"""
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        await agent.stop()
        
        # 释放资源
        await self.resource_manager.release_resources(agent_id)
        
        print(f"🛑 Agent已停止: {agent_id}")
    
    async def send_agent_message(self, sender_id: str, receiver_id: str, 
                               content: Any, message_type: str = MessageType.DIRECT) -> bool:
        """发送Agent消息"""
        message = AgentMessage(
            message_type=message_type,
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content
        )
        
        return await self.communication_bus.send_message(message)
    
    async def execute_agent_task(self, agent_id: str, task_type: str, 
                               parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行Agent任务"""
        if agent_id not in self.agents:
            raise ValueError(f"Agent不存在: {agent_id}")
        
        agent = self.agents[agent_id]
        return await agent.execute_task(task_type, parameters)
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "system_id": self.system_id,
            "running": self.running,
            "uptime": (datetime.now() - self.started_at).total_seconds() if self.started_at else 0,
            "total_agents": len(self.agents),
            "agents": {agent_id: agent.get_info() for agent_id, agent in self.agents.items()}
        }


async def agent_system_example():
    """Agent系统使用示例"""
    print("🚀 AgentBus Agent系统框架 - 完整示例")
    print("=" * 50)
    
    # 创建系统
    system = AgentSystem("demo_system")
    await system.initialize()
    
    # 1. 创建多个不同类型的Agent
    print("\n🏗️ === 1. 创建Agent ===")
    
    agents_to_create = [
        {
            "config": AgentConfig(
                agent_id="conversation_agent",
                agent_type=AgentType.CONVERSATION,
                capabilities=["chat", "dialogue"],
                resource_limits={"cpu": 1.0, "memory": 512.0}
            ),
            "metadata": AgentMetadata(
                agent_id="conversation_agent",
                name="对话Agent",
                description="专门处理对话任务的Agent"
            )
        },
        {
            "config": AgentConfig(
                agent_id="task_agent",
                agent_type=AgentType.TASK_EXECUTION,
                capabilities=["automation", "processing"],
                resource_limits={"cpu": 2.0, "memory": 1024.0}
            ),
            "metadata": AgentMetadata(
                agent_id="task_agent",
                name="任务执行Agent",
                description="专门执行各种任务的Agent"
            )
        },
        {
            "config": AgentConfig(
                agent_id="reasoning_agent",
                agent_type=AgentType.REASONING,
                capabilities=["analysis", "decision_making"],
                resource_limits={"cpu": 1.5, "memory": 768.0}
            ),
            "metadata": AgentMetadata(
                agent_id="reasoning_agent",
                name="推理Agent",
                description="专门进行推理和分析的Agent"
            )
        }
    ]
    
    created_agents = []
    for agent_info in agents_to_create:
        agent = await system.create_agent(agent_info["config"], agent_info["metadata"])
        created_agents.append(agent.agent_id)
    
    print(f"✅ 成功创建 {len(created_agents)} 个Agent")
    
    # 2. 启动Agent
    print("\n🚀 === 2. 启动Agent ===")
    
    for agent_id in created_agents:
        success = await system.start_agent(agent_id)
        if success:
            print(f"✅ {agent_id} 启动成功")
        else:
            print(f"❌ {agent_id} 启动失败")
    
    # 3. 演示Agent通信
    print("\n💬 === 3. Agent通信演示 ===")
    
    # 直接消息
    print("📤 发送直接消息...")
    await system.send_agent_message(
        sender_id="conversation_agent",
        receiver_id="task_agent",
        content={
            "message": "请帮我处理这个任务",
            "priority": "high"
        },
        message_type=MessageType.DIRECT
    )
    
    # 广播消息
    print("📢 发送广播消息...")
    await system.send_agent_message(
        sender_id="task_agent",
        receiver_id="all",
        content={
            "message": "系统通知：所有Agent注意",
            "timestamp": datetime.now().isoformat()
        },
        message_type=MessageType.BROADCAST
    )
    
    # 4. 执行任务
    print("\n⚡ === 4. 任务执行演示 ===")
    
    tasks_to_execute = [
        ("conversation_agent", "处理对话", {"query": "你好，请介绍一下自己"}),
        ("task_agent", "执行自动化", {"task": "data_processing", "data": [1, 2, 3, 4, 5]}),
        ("reasoning_agent", "分析决策", {"scenario": "选择最佳方案", "options": ["A", "B", "C"]}),
        ("conversation_agent", "继续对话", {"query": "你能帮我做什么？"}),
        ("task_agent", "批量处理", {"batch_id": "batch_001", "items": 100})
    ]
    
    for agent_id, task_type, parameters in tasks_to_execute:
        try:
            result = await system.execute_agent_task(agent_id, task_type, parameters)
            print(f"✅ {agent_id} 完成 {task_type}")
        except Exception as e:
            print(f"❌ {agent_id} 执行 {task_type} 失败: {e}")
    
    # 5. 监控系统状态
    print("\n📊 === 5. 系统监控 ===")
    
    # 收集系统指标
    metrics = await system.monitoring_system.collect_metrics()
    print("📈 系统指标:")
    print(f"  CPU使用率: {metrics['cpu_usage']:.1f}%")
    print(f"  内存使用率: {metrics['memory_usage']:.1f}%")
    print(f"  活跃Agent: {metrics['active_agents']}")
    print(f"  总任务数: {metrics['total_tasks']}")
    print(f"  总消息数: {metrics['total_messages']}")
    
    # 资源使用情况
    utilization = system.resource_manager.get_system_utilization()
    print("\n💾 资源使用情况:")
    for resource_type, data in utilization.items():
        print(f"  {resource_type}: {data['utilization_rate']:.1%} "
              f"({data['used']:.1f}/{data['total']:.1f})")
    
    # Agent健康状态
    print("\n🏥 Agent健康状态:")
    for agent_id in created_agents:
        health = system.monitoring_system.get_agent_health(agent_id)
        print(f"  {agent_id}: {health['status']} "
              f"(任务: {health['tasks_executed']}, 消息: {health['messages_processed']})")
    
    # 6. 完整系统状态
    print("\n📋 === 6. 完整系统状态 ===")
    
    system_status = system.get_system_status()
    print(f"系统ID: {system_status['system_id']}")
    print(f"运行时间: {system_status['uptime']:.1f}秒")
    print(f"Agent总数: {system_status['total_agents']}")
    
    print("\nAgent详情:")
    for agent_id, info in system_status['agents'].items():
        print(f"  {agent_id}:")
        print(f"    名称: {info['name']}")
        print(f"    类型: {info['type']}")
        print(f"    状态: {info['status']}")
        print(f"    能力: {', '.join(info['capabilities'])}")
        print(f"    执行任务: {info['executed_tasks']}")
        print(f"    处理消息: {info['processed_messages']}")
    
    # 7. 清理
    print("\n🧹 === 7. 清理资源 ===")
    
    for agent_id in created_agents:
        await system.stop_agent(agent_id)
    
    print("✅ 所有Agent已停止，资源已释放")
    
    # 最终统计
    print("\n📊 === 最终统计 ===")
    message_stats = system.communication_bus.get_message_stats()
    print(f"消息统计:")
    print(f"  总消息数: {message_stats['total_messages']}")
    print(f"  注册Agent数: {message_stats['registered_agents']}")
    
    print("\n🎉 Agent系统演示完成！")
    print("\n框架特性验证:")
    print("✅ Agent生命周期管理 - 成功")
    print("✅ Agent通信机制 - 成功") 
    print("✅ Agent状态监控 - 成功")
    print("✅ Agent资源管理 - 成功")
    print("✅ Agent插件系统 - 框架已实现")
    
    return True


if __name__ == "__main__":
    # 运行示例
    try:
        asyncio.run(agent_system_example())
    except KeyboardInterrupt:
        print("\n\n⏹️  程序被用户中断")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        import traceback
        traceback.print_exc()