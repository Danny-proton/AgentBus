# AgentBus Hook System

一个完整的钩子系统，为AgentBus提供可扩展的、事件驱动的功能扩展。

## 🚀 特性

- **事件驱动架构** - 基于事件的钩子系统，支持多种事件类型
- **优先级执行** - 智能的优先级管理，确保钩子按正确顺序执行
- **内置钩子** - 提供日志记录、指标收集、会话管理等内置功能
- **第三方钩子支持** - 支持从多种来源加载钩子（内置、工作区、管理、第三方）
- **配置管理** - 完整的配置管理和验证系统
- **健康监控** - 内置健康检查和性能监控
- **安全特性** - 数据清理、权限控制和安全钩子
- **高性能** - 异步执行、并发控制和优化设计

## 📁 目录结构

```
agentbus/hooks/
├── __init__.py              # 主模块入口
├── types.py                 # 类型定义
├── core.py                  # 核心钩子系统
├── manager.py               # 钩子管理器
├── loader.py                # 钩子加载器
├── config.py                # 配置管理
├── priority.py              # 优先级管理
├── internal_hooks.py         # 内置钩子实现
├── examples/                # 示例钩子
│   ├── welcome_hook.py      # 欢迎钩子
│   ├── analytics_hooks.py   # 分析钩子
│   └── utility_hooks.py     # 实用工具钩子
└── bundled/                 # 内置钩子实现
    ├── session-memory/      # 会话内存钩子
    │   ├── HOOK.md
    │   └── handler.py
    └── command-logger/      # 命令日志钩子
        ├── HOOK.md
        └── handler.py
```

## 🛠️ 快速开始

### 基本使用

```python
import asyncio
from agentbus.hooks import (
    initialize_system, trigger_command,
    HookExecutionContext, HookPriority
)

async def main():
    # 初始化钩子系统
    system = await initialize_system()
    
    # 创建执行上下文
    context = HookExecutionContext(
        session_key="session_123",
        agent_id="my_agent",
        channel_id="discord_456",
        user_id="user_789"
    )
    
    # 触发命令事件
    results = await trigger_command(
        command="analyze",
        session_key="session_123",
        context=context,
        args=["data.json"],
        success=True,
        duration=2.5
    )
    
    # 处理结果
    for result in results:
        print(f"Hook executed: {result.success}")
        if result.messages:
            print(f"Message: {result.messages[0]}")
    
    # 关闭系统
    await system.shutdown()

# 运行
asyncio.run(main())
```

### 创建自定义钩子

```python
from agentbus.hooks import register_hook
from agentbus.hooks.types import HookEvent, HookResult

async def my_custom_hook(event: HookEvent) -> HookResult:
    """自定义钩子处理器"""
    print(f"处理事件: {event.type.value}:{event.action}")
    
    # 业务逻辑
    if event.type.value == "command":
        command = event.data.get('command', '')
        
        return HookResult(
            success=True,
            messages=[f"处理命令: {command}"],
            data={'processed': True}
        )
    
    return HookResult(success=True)

# 注册钩子
register_hook(
    event_key="command:*",  # 监听所有命令事件
    handler=my_custom_hook,
    priority=HookPriority.HIGH
)
```

## 🔧 配置

### 基本配置

```python
from agentbus.hooks import HookConfig

config = HookConfig(
    enabled=True,
    debug=True,
    load_bundled_hooks=True,
    load_workspace_hooks=True,
    execution_timeout=30,
    max_concurrent=10
)

system = await initialize_system(config)
```

### YAML 配置文件

```yaml
# ~/.agentbus/config/hooks.yaml
enabled: true
debug: false

# 加载设置
load_bundled_hooks: true
load_workspace_hooks: true
load_managed_hooks: true

# 执行设置
execution:
  timeout: 30
  retry_count: 0
  max_concurrent: 10
  fail_silent: false

# 钩子配置
hooks:
  session-memory:
    enabled: true
    priority: 200
    timeout: 30
    max_memory_files: 100
  
  command-logger:
    enabled: true
    priority: -500
    log_level: "INFO"
    include_args: true
    sanitize_sensitive: true

# 优先级覆盖
priority_overrides:
  my_custom_hook: 300
```

## 📚 API 参考

### 核心类

#### `HookEngine`
钩子执行引擎，负责事件触发和钩子执行。

```python
from agentbus.hooks import hook_engine

# 注册钩子
hook_engine.registry.register(
    event_key="command:new",
    handler=my_handler,
    priority=100
)

# 触发事件
results = await hook_engine.trigger(event)
```

#### `HookManager`
高级钩子管理器，提供生命周期管理和监控。

```python
from agentbus.hooks import get_hook_manager

manager = get_hook_manager()

# 获取状态
status = manager.get_hook_status()
print(f"已加载钩子: {status['total_loaded']}")
print(f"健康钩子: {status['healthy_hooks']}")
```

#### `HookLoader`
钩子加载器，从各种来源加载钩子。

```python
from agentbus.hooks import HookLoader

loader = HookLoader("/path/to/workspace")

# 加载所有钩子
entries = await loader.load_all_hooks(config)
print(f"加载了 {len(entries)} 个钩子")
```

### 事件类型

```python
from agentbus.hooks.types import HookEventType

# 支持的事件类型
event_types = [
    HookEventType.COMMAND,    # 命令事件
    HookEventType.SESSION,    # 会话事件
    HookEventType.MESSAGE,    # 消息事件
    HookEventType.ERROR,      # 错误事件
    HookEventType.LIFECYCLE,  # 生命周期事件
    HookEventType.SECURITY,   # 安全事件
    HookEventType.AGENT,      # 代理事件
    HookEventType.GATEWAY     # 网关事件
]
```

### 钩子元数据

```python
from agentbus.hooks.types import HookMetadata, HookRequirements

metadata = HookMetadata(
    always=False,
    hook_key="my-hook",
    emoji="🔧",
    events=["command:*", "session:start"],
    priority=100,
    timeout=30,
    retry_count=1,
    requires=HookRequirements(
        bins=["python", "git"],
        env=["HOME", "USER"],
        config=["workspace.dir"]
    ),
    tags=["utility", "automation"]
)
```

## 🎯 内置钩子

### 会话内存钩子 (`session-memory`)

自动将会话上下文保存到内存文件。

```python
# 触发会话结束事件
await trigger_session_event(
    action="end",
    session_key="session_123",
    context=HookExecutionContext(
        session_key="session_123",
        workspace_dir="/workspace"
    ),
    events=[...],  # 会话事件列表
    duration=120
)
```

### 命令日志钩子 (`command-logger`)

记录所有命令事件用于分析和调试。

```python
# 自动记录命令
await trigger_command(
    command="analyze",
    session_key="session_123",
    args=["data.json"],
    success=True,
    duration=2.5
)
```

### 欢迎钩子 (`welcome`)

为新用户发送欢迎消息。

```python
# 触发会话开始事件
await trigger_session_event(
    action="start",
    session_key="session_123",
    context=HookExecutionContext(
        session_key="session_123",
        user_id="new_user"
    )
)
```

### 健康检查钩子 (`health-check`)

执行系统健康检查。

```python
# 触发健康检查
await trigger_session_event(
    action="check",
    session_key="session_123",
    context=HookExecutionContext(session_key="session_123"),
    check_type="system"
)
```

## 📊 监控和统计

### 获取系统统计

```python
from agentbus.hooks import get_system_info

info = get_system_info()

print("系统状态:", info['system']['status'])
print("钩子统计:", info['statistics']['registry'])
print("性能统计:", info['statistics']['engine'])
```

### 健康检查

```python
manager = get_hook_manager()

# 执行健康检查
health = await manager.health_check()

print(f"整体健康: {health['overall_health']}")
print(f"检查详情: {health['checks']}")
```

### 执行历史

```python
# 获取执行历史
history = manager.get_execution_history(limit=50)

for record in history:
    print(f"{record['timestamp']}: {record['event_type']}:{record['action']}")
    print(f"  执行了 {record['hooks_executed']} 个钩子")
    print(f"  成功: {record['successful_hooks']}, 失败: {record['failed_hooks']}")
```

## 🔒 安全特性

### 数据清理

```python
# 自动清理敏感数据
hook = create_utility_hooks()['hash']
# 内置敏感数据检测和清理功能
```

### 权限控制

```python
config = HookConfig(
    allowed_sources=[
        "agentbus-bundled",
        "agentbus-workspace",
        "agentbus-managed"
    ],
    require_signature=False  # 启用签名验证
)
```

### 安全监控

```python
# 注册安全钩子
register_hook(
    event_key="security:*",
    handler=security_monitor,
    priority=HookPriority.CRITICAL
)
```

## ⚡ 性能优化

### 优先级管理

```python
from agentbus.hooks import HookPriority

# 优先级级别
priority_levels = [
    HookPriority.CRITICAL,  # 1000 - 关键
    HookPriority.HIGH,      # 500  - 高
    HookPriority.NORMAL,    # 0    - 正常
    HookPriority.LOW,       # -500 - 低
    HookPriority.BACKGROUND # -1000 - 后台
]
```

### 并发控制

```python
config = HookConfig(
    execution=HookExecutionConfig(
        max_concurrent=10,      # 最大并发数
        timeout=30,             # 超时时间
        retry_count=0,         # 重试次数
        continue_on_error=True # 错误时继续
    )
)
```

### 内存管理

```python
# 自动清理旧数据
await manager.cleanup_expired_history(max_age_days=7)

# 限制历史记录大小
config.max_execution_history = 1000
```

## 🧪 测试

### 运行演示

```bash
python demo_hook_system.py
```

演示包括：
- 基本功能演示
- 事件类型演示
- 实用工具钩子演示
- 性能监控演示
- 错误处理演示
- 配置管理演示
- 健康监控演示

### 单元测试

```python
import pytest
from agentbus.hooks import register_hook, trigger_command

@pytest.mark.asyncio
async def test_custom_hook():
    """测试自定义钩子"""
    called = False
    
    async def test_hook(event):
        nonlocal called
        called = True
        return HookResult(success=True)
    
    # 注册测试钩子
    register_hook("command:test", test_hook)
    
    # 触发事件
    results = await trigger_command("test", "session_123")
    
    # 验证
    assert called
    assert len(results) > 0
    assert results[0].success
```

## 📈 扩展开发

### 创建自定义钩子

1. **创建钩子处理器**

```python
# my_custom_hook.py
from agentbus.hooks.types import HookEvent, HookResult

async def my_hook_handler(event: HookEvent) -> HookResult:
    """自定义钩子处理器"""
    
    # 处理事件
    if event.type.value == "command":
        command = event.data.get('command', '')
        
        # 业务逻辑
        result = f"处理命令: {command}"
        
        return HookResult(
            success=True,
            messages=[result],
            data={'processed': True}
        )
    
    return HookResult(success=True)
```

2. **创建钩子文档**

```markdown
---
name: my-custom-hook
description: 我的自定义钩子
metadata:
    agentbus:
        emoji: 🔧
        events:
            - command
        priority: 100
        tags:
            - custom
            - utility
---

# My Custom Hook

这是我的自定义钩子描述...

## 使用方法

```python
register_hook("command:*", my_hook_handler)
```
```

3. **注册钩子**

```python
from my_custom_hook import my_hook_handler
from agentbus.hooks import register_hook

register_hook(
    event_key="command:*",
    handler=my_hook_handler,
    priority=100
)
```

### 钩子最佳实践

1. **异步处理** - 所有钩子都应该异步执行
2. **错误处理** - 妥善处理异常，不要让钩子崩溃
3. **性能考虑** - 避免耗时操作，使用适当的超时
4. **数据安全** - 清理敏感数据，遵守隐私原则
5. **日志记录** - 适当的日志记录便于调试
6. **测试覆盖** - 为钩子编写测试用例

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 🆘 支持

如有问题或建议，请：

1. 查看文档和示例
2. 运行演示脚本
3. 创建 Issue
4. 联系维护者

---

**AgentBus Hook System** - 让您的Agent更强大！