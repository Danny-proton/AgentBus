---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 30450221009030f4f0e61b87e0f247b1c61daa74d12d1532544bdc278f3a97ab551097c8bf022074ca6ee6eb79d5939cffa0d9fcd3229dc72d3308fe2cef9fbc76905b9eae3af9
    ReservedCode2: 3046022100a72838b946ddb60b8b9267fb275a838bdf0e8f3ad32d48cd5750d5487657864a022100d82473a6ee7ba8d6aaa79f4d030355c5b3351837e11318242c81d16fe567464b
---

# AgentBus Agent System Framework

基于Moltbot架构的完整Agent系统框架，提供Agent生命周期管理、通信机制、状态监控、资源管理和插件系统的完整解决方案。

## 🚀 核心特性

### 1. Agent生命周期管理
- Agent创建、初始化、启动、停止、销毁
- 生命周期事件监听和处理
- 自动资源分配和回收
- 优雅关闭和错误恢复

### 2. Agent通信机制
- 基于事件驱动的消息总线
- 支持直接消息和广播消息
- 消息优先级和路由
- 异步消息处理

### 3. Agent状态监控
- 实时健康状态监控
- 性能指标收集
- 告警系统
- 系统级监控

### 4. Agent资源管理
- CPU、内存、存储等资源配额管理
- 动态资源分配和调整
- 资源使用率监控
- 资源池管理

### 5. Agent插件系统
- 可插拔的能力扩展
- 插件生命周期管理
- 插件间通信
- 安全权限控制

## 📁 目录结构

```
agentbus/agents/
├── __init__.py              # 主包初始化
├── demo.py                  # 完整演示脚本
├── core/                    # 核心组件
│   ├── base.py             # 基础类和接口
│   ├── manager.py          # 核心管理器
│   └── types.py            # 类型定义
├── lifecycle/              # 生命周期管理
│   └── manager.py          # 生命周期管理器
├── communication/          # 通信机制
│   └── bus.py              # 通信总线
├── monitoring/             # 状态监控
│   └── system.py           # 监控系统
├── resource/               # 资源管理
│   └── manager.py          # 资源管理器
└── plugins/                # 插件系统
    ├── system.py           # 插件系统
    └── examples.py         # 插件示例
```

## 🛠️ 快速开始

### 基本使用

```python
import asyncio
from agentbus.agents import agent_system, AgentConfig, AgentMetadata, AgentType

async def basic_example():
    async with agent_system() as system:
        # 创建Agent配置
        config = AgentConfig(
            agent_id="my_agent",
            agent_type=AgentType.CONVERSATION,
            resource_limits={"cpu": 1.0, "memory": 512.0}
        )
        
        metadata = AgentMetadata(
            agent_id="my_agent",
            name="My Conversation Agent"
        )
        
        # 创建并启动Agent
        agent = await system.create_agent(config, metadata)
        await system.start_agent("my_agent")
        
        # 执行任务
        result = await system.execute_agent_task(
            "my_agent",
            "process_message",
            {"message": "Hello World"}
        )
        
        # 获取状态
        status = system.get_agent_status("my_agent")
        print(status)

asyncio.run(basic_example())
```

### Agent通信

```python
# 发送直接消息
await system.send_agent_message(
    sender_id="agent1",
    receiver_id="agent2", 
    content={"message": "Hello!"},
    message_type=MessageType.DIRECT
)

# 广播消息
message = AgentMessage(
    message_type=MessageType.BROADCAST,
    sender_id="agent1",
    receiver_id="all",
    content={"announcement": "System update"}
)
await system.communication_bus.send_message(message)
```

### 插件使用

```python
from agentbus.agents.plugins.examples import (
    EXAMPLE_PLUGIN_MANIFEST,
    create_example_capability_plugin
)

# 创建插件实例
plugin = create_example_capability_plugin(
    EXAMPLE_PLUGIN_MANIFEST,
    {"config_key": "config_value"}
)

# 加载插件
await plugin.on_load()
await plugin.on_enable()
```

## 📊 监控和管理

### 获取系统状态

```python
# 完整系统状态
status = system.get_system_status()
print(f"Active agents: {status['agents']['total']}")
print(f"System uptime: {status['uptime']}s")

# 系统指标
metrics = system.get_system_metrics()
print(f"CPU usage: {metrics.system_cpu_usage}%")
print(f"Memory usage: {metrics.system_memory_usage}%")
```

### 健康检查

```python
if system.monitoring_system:
    # 获取Agent健康状态
    health = system.monitoring_system.get_agent_health("agent_id")
    print(f"Agent health: {health.status.value}")
    
    # 获取所有告警
    alerts = system.monitoring_system.get_active_alerts()
    for alert in alerts:
        print(f"Alert: {alert.title} - {alert.message}")
```

## 🔧 运行演示

要查看完整的功能演示，运行：

```bash
python -m agentbus.agents.demo
```

演示包含：
- Agent生命周期管理
- Agent通信机制
- Agent状态监控  
- Agent资源管理
- Agent插件系统
- 完整工作流演示

## 🏗️ 架构设计

### 核心组件

1. **AgentSystem**: 中央协调器，管理所有子系统
2. **AgentManager**: Agent创建和管理
3. **LifecycleManager**: Agent生命周期管理
4. **CommunicationBus**: 消息传递和路由
5. **MonitoringSystem**: 状态监控和告警
6. **ResourceManager**: 资源分配和监控
7. **PluginSystem**: 插件管理和加载

### 设计原则

- **模块化**: 每个组件独立，可单独使用
- **可扩展**: 插件系统支持功能扩展
- **可监控**: 全面的监控和指标收集
- **高性能**: 异步处理和资源优化
- **易用性**: 简洁的API和丰富的示例

## 📈 性能特性

- **异步处理**: 全异步架构，高并发支持
- **资源优化**: 智能资源分配和回收
- **监控完整**: 实时指标收集和分析
- **容错机制**: 自动故障检测和恢复
- **扩展性强**: 插件系统支持功能扩展

## 🔒 安全特性

- **权限控制**: 插件权限管理
- **资源隔离**: Agent间资源隔离
- **安全通信**: 加密消息传输
- **审计日志**: 完整的操作审计

## 🤝 贡献

欢迎贡献代码、报告问题或提出改进建议！

## 📄 许可证

MIT License

---

**AgentBus Agent System Framework** - 让Agent开发更简单、更强大！