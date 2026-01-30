---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 3044022043420c9e63bef5086bca3cd6e42c4f56ad11181d1711b83721cc8d59b0d25e0602202889efba6ca1de7dedc87ef76ff29290ecbd57dbb1b997668dcba2df7500272c
    ReservedCode2: 304502203450ae944233366ea86df05281110d40e226926bd128a72e4627626883bcb0850221009d23810503da7fe69b243946deaebfa3ba653fb5d1d3f2df8f90ff1d30f00672
---

# AgentBus 插件框架

AgentBus插件框架提供了完整的插件系统，支持动态加载、注册工具、钩子、渠道等功能。框架采用模块化设计，允许开发者创建自定义插件来扩展AgentBus的功能。

## 🎯 主要特性

- **动态插件加载**: 支持运行时加载和卸载插件
- **工具注册**: 插件可以注册自定义工具供系统使用
- **事件钩子**: 支持事件驱动的插件通信
- **命令系统**: 插件可以注册CLI命令
- **生命周期管理**: 完整的插件激活/停用管理
- **类型安全**: 完整的类型提示和类型检查
- **异步支持**: 原生支持异步编程模式

## 🏗️ 核心组件

### PluginContext
插件上下文类，为插件提供运行时环境：

```python
@dataclass
class PluginContext:
    config: Dict[str, Any]      # 插件配置
    logger: logging.Logger       # 日志记录器
    runtime: Dict[str, Any]     # 运行时环境
```

### AgentBusPlugin
所有插件的基类，提供了插件的基本功能：

```python
class AgentBusPlugin(ABC):
    def __init__(self, plugin_id: str, context: PluginContext)
    
    # 必须实现的方法
    def get_info(self) -> Dict[str, Any]
    
    # 可选重写的方法
    async def activate(self) -> bool
    async def deactivate(self) -> bool
    
    # 资源注册方法
    def register_tool(self, name: str, description: str, function: Callable)
    def register_hook(self, event: str, handler: Callable, priority: int = 0)
    def register_command(self, command: str, handler: Callable, description: str = "")
```

### PluginManager
插件管理器，负责插件的整个生命周期：

```python
class PluginManager:
    def __init__(self, context: Optional[PluginContext] = None)
    
    # 核心管理方法
    async def discover_plugins(self) -> List[PluginInfo]
    async def load_plugin(self, plugin_id: str, module_path: str) -> AgentBusPlugin
    async def activate_plugin(self, plugin_id: str) -> bool
    async def deactivate_plugin(self, plugin_id: str) -> bool
    async def unload_plugin(self, plugin_id: str) -> bool
    
    # 资源访问方法
    async def execute_tool(self, tool_name: str, *args, **kwargs) -> PluginResult
    async def execute_hook(self, event: str, *args, **kwargs) -> List[Any]
```

## 🚀 快速开始

### 1. 创建插件

继承`AgentBusPlugin`基类创建自定义插件：

```python
from agentbus.plugins import AgentBusPlugin, PluginContext
from typing import Dict, Any
import asyncio

class MyPlugin(AgentBusPlugin):
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        self.counter = 0
    
    def get_info(self) -> Dict[str, Any]:
        return {
            'id': self.plugin_id,
            'name': 'My Plugin',
            'version': '1.0.0',
            'description': '我的自定义插件',
            'author': 'Your Name',
            'dependencies': []
        }
    
    async def activate(self):
        """激活插件时注册工具、钩子和命令"""
        await super().activate()
        
        # 注册工具
        self.register_tool(
            name='count',
            description='获取计数器值',
            function=self.get_counter
        )
        
        self.register_tool(
            name='increment',
            description='增加计数器',
            function=self.increment_counter
        )
        
        # 注册事件钩子
        self.register_hook(
            event='message_received',
            handler=self.on_message_received
        )
        
        # 注册命令
        self.register_command(
            command='/counter',
            handler=self.handle_counter_command,
            description='显示当前计数器值'
        )
    
    def get_counter(self) -> int:
        """获取当前计数器值"""
        return self.counter
    
    def increment_counter(self, amount: int = 1) -> int:
        """增加计数器"""
        self.counter += amount
        return self.counter
    
    async def on_message_received(self, message: str, sender: str):
        """处理接收到的消息"""
        self.counter += 1
        self.context.logger.info(f"Received message from {sender}")
    
    async def handle_counter_command(self, args: str) -> str:
        """处理/counter命令"""
        return f"当前计数器值: {self.counter}"
```

### 2. 使用插件管理器

```python
import asyncio
from agentbus.plugins import PluginManager, PluginContext
import logging

async def main():
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建插件上下文
    context = PluginContext(
        config={'my_plugin': {'debug': True}},
        logger=logging.getLogger('my_app'),
        runtime={'version': '1.0.0'}
    )
    
    # 创建插件管理器
    manager = PluginManager(context)
    
    # 加载插件
    plugin = await manager.load_plugin(
        'my_plugin', 
        '/path/to/my_plugin.py'
    )
    
    # 激活插件
    await manager.activate_plugin('my_plugin')
    
    # 使用插件工具
    result = await manager.execute_tool('count')
    print(f"计数器值: {result}")
    
    # 执行事件钩子
    await manager.execute_hook('message_received', 'Hello!', 'user123')
    
    # 获取统计信息
    stats = await manager.get_plugin_stats()
    print(f"插件统计: {stats}")

if __name__ == '__main__':
    asyncio.run(main())
```

## 🛠️ 插件开发指南

### 工具开发

工具是插件提供的可调用功能，可以是同步或异步的：

```python
# 同步工具
def sync_tool(self, text: str) -> str:
    return text.upper()

# 异步工具  
async def async_tool(self, delay: int) -> str:
    await asyncio.sleep(delay)
    return f"Waited {delay} seconds"

# 参数化工具
def math_tool(self, a: int, b: int, operation: str = 'add') -> int:
    if operation == 'add':
        return a + b
    elif operation == 'multiply':
        return a * b
    else:
        raise ValueError(f"Unknown operation: {operation}")
```

### 钩子开发

钩子用于响应系统事件，可以设置优先级：

```python
# 普通钩子
async def on_message(self, message: str):
    self.context.logger.info(f"Processing message: {message}")

# 高优先级钩子
async def on_message_priority(self, message: str):
    if "urgent" in message:
        await self.handle_urgent_message(message)

# 注册钩子（高优先级先执行）
self.register_hook('message_received', self.on_message, priority=5)
self.register_hook('message_received', self.on_message_priority, priority=10)
```

### 命令开发

命令为插件提供CLI接口：

```python
# 简单命令
async def simple_command(self, args: str) -> str:
    return f"简单命令，参数: {args}"

# 复杂命令
async def complex_command(self, args: str) -> str:
    parts = args.split()
    if len(parts) < 2:
        return "需要至少2个参数"
    
    action = parts[0]
    value = parts[1]
    
    if action == 'set':
        self.set_value(value)
        return f"设置值为: {value}"
    else:
        return f"未知操作: {action}"

# 注册命令
self.register_command('/simple', self.simple_command, '简单命令示例')
self.register_command('/complex', self.complex_command, '复杂命令示例')
```

### 配置管理

插件可以通过上下文访问配置：

```python
# 获取配置
debug_mode = self.get_config('debug', False)
max_retries = self.get_config('max_retries', 3)

# 设置配置
self.set_config('last_run', datetime.now())

# 获取运行时变量
api_key = self.get_runtime('api_key')
if not api_key:
    api_key = self.load_api_key()
    self.set_runtime('api_key', api_key)
```

## 📁 插件目录结构

插件可以按以下结构组织：

```
plugins/
├── __init__.py
├── my_plugin/
│   ├── __init__.py
│   ├── main.py          # 主插件文件
│   ├── tools.py         # 工具定义
│   ├── hooks.py         # 钩子定义
│   └── config.py        # 配置定义
└── another_plugin/
    └── plugin.py
```

## 🔧 高级功能

### 插件依赖

在插件信息中声明依赖：

```python
def get_info(self) -> Dict[str, Any]:
    return {
        'id': self.plugin_id,
        'name': 'Advanced Plugin',
        'version': '1.0.0',
        'description': '高级插件',
        'author': 'Your Name',
        'dependencies': ['basic_plugin', 'utils_plugin']  # 依赖列表
    }
```

### 插件发现

管理器可以自动发现插件目录中的插件：

```python
# 设置插件搜索目录
plugin_dirs = [
    '/path/to/plugins',
    '~/.agentbus/plugins',
    './extensions'
]

manager = PluginManager(context, plugin_dirs)

# 发现插件
discovered = await manager.discover_plugins()
for plugin_info in discovered:
    print(f"发现插件: {plugin_info.name} v{plugin_info.version}")
```

### 插件重新加载

支持热重载插件：

```python
# 重新加载插件（保持激活状态）
success = await manager.reload_plugin('my_plugin')
```

### 事件调度

系统可以调度事件给所有插件：

```python
# 发送事件给所有注册的钩子
results = await manager.execute_hook(
    'user_connected', 
    user_id='user123',
    timestamp=datetime.now()
)
```

## 🧪 测试插件

使用提供的测试脚本验证插件：

```bash
cd /workspace/agentbus
python test_plugins.py
```

## 📋 最佳实践

1. **错误处理**: 在插件中添加适当的错误处理和日志记录
2. **资源管理**: 在`deactivate()`方法中清理资源
3. **异步编程**: 优先使用异步方法以提高性能
4. **类型提示**: 添加完整的类型提示以提高代码质量
5. **文档字符串**: 为所有公共方法添加文档字符串
6. **配置管理**: 合理使用插件配置和运行时变量
7. **优先级设置**: 合理设置钩子优先级避免冲突

## 🤝 贡献指南

欢迎贡献插件和功能！请遵循以下步骤：

1. Fork项目
2. 创建功能分支
3. 添加测试和文档
4. 提交Pull Request

## 📄 许可证

本项目采用MIT许可证。详情请查看LICENSE文件。

---

**AgentBus插件框架** - 让扩展AgentBus功能变得简单而强大！