---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 3045022100d9e84a938f6dc895c7cd00a4e9e51cffbb791b34e7a4fc67badd4079e7ba1b570220369b73456d2003b332d63611f550b11614fb0ea2e356a303c1a5e9ad72c30672
    ReservedCode2: 3046022100ed04fdd044c1425579c3ea94f73f9e8ac705f18e294603d95547b070f4a598bb022100b02760df60381e9f8f252de4b7fb4322b8b5d87d55e24c506f4ed389fbc57499
---

# AgentBus渠道系统

基于Moltbot的渠道适配器模式，为AgentBus提供统一的多渠道消息处理框架。

## 功能特性

- 🎯 **标准化消息格式** - 统一的Message类和元数据结构
- 🔧 **灵活配置接口** - 支持多种渠道类型和自定义配置
- 🔌 **插件化架构** - 通过装饰器轻松注册新渠道类型
- 📊 **状态管理** - 实时监控渠道连接状态和健康状况
- 💾 **持久化配置** - 自动保存和加载渠道配置
- 📨 **多消息类型** - 支持文本、媒体、投票等多种消息类型
- 🔄 **异步操作** - 完全异步的连接、消息发送等操作
- 📈 **事件驱动** - 消息和状态变化的事件处理器机制

## 核心组件

### 1. 基础类型 (base.py)

#### 消息相关
- `Message` - 标准化消息格式
- `MessageMetadata` - 消息元数据
- `MessageType` - 消息类型枚举 (TEXT, MEDIA, POLL, 等)
- `ChatType` - 聊天类型枚举 (DIRECT, GROUP, CHANNEL, THREAD)

#### 渠道相关
- `ChannelConfig` - 渠道配置
- `ChannelAccountConfig` - 渠道账户配置
- `ChannelCapabilities` - 渠道能力配置
- `ChannelStatus` - 渠道状态信息
- `ChannelAdapter` - 渠道适配器抽象基类

#### 状态相关
- `ConnectionStatus` - 连接状态枚举
- `ChannelState` - 渠道状态枚举

### 2. 渠道管理器 (manager.py)

`ChannelManager` 类提供统一的渠道管理功能：

```python
from agentbus.channels.manager import ChannelManager
from agentbus.channels.base import ChannelConfig, ChannelAccountConfig

# 创建管理器
manager = ChannelManager(Path("channels_config.json"))

# 启动管理器
await manager.start()

# 注册渠道
await manager.register_channel(channel_config)

# 连接渠道
await manager.connect_channel("channel_id")

# 发送消息
await manager.send_message("channel_id", "Hello World!")

# 发送媒体
await manager.send_media("channel_id", "查看图片", "https://example.com/image.jpg")

# 发送投票
await manager.send_poll("channel_id", "你更喜欢哪个？", ["选项A", "选项B"])
```

### 3. 渠道注册系统

使用装饰器注册新的渠道类型：

```python
from agentbus.channels import register_channel_type
from agentbus.channels.base import ChannelAdapter, ChannelConfig

@register_channel_type("my_channel")
def create_my_channel_adapter(config: ChannelConfig) -> ChannelAdapter:
    return MyChannelAdapter(config)
```

## 使用示例

### 创建自定义渠道适配器

```python
from agentbus.channels.base import ChannelAdapter, Message, ChannelConfig, ChannelAccountConfig

class MyCustomAdapter(ChannelAdapter):
    def __init__(self, config: ChannelConfig):
        super().__init__(config)
        self._connected = False
    
    @property
    def channel_id(self) -> str:
        return self.config.channel_id
    
    @property
    def channel_name(self) -> str:
        return self.config.channel_name
    
    @property
    def capabilities(self) -> ChannelCapabilities:
        return self.config.capabilities
    
    async def connect(self, account_id: str) -> bool:
        # 实现连接逻辑
        self._connected = True
        return True
    
    async def disconnect(self, account_id: str) -> bool:
        # 实现断开逻辑
        self._connected = False
        return True
    
    async def is_connected(self, account_id: str) -> bool:
        return self._connected
    
    async def send_message(self, message: Message, account_id=None) -> bool:
        # 实现消息发送
        print(f"发送消息到 {self.channel_id}: {message.content}")
        return True
    
    async def send_media(self, message: Message, media_url: str, account_id=None) -> bool:
        # 实现媒体发送
        return True
    
    async def send_poll(self, question: str, options: list, account_id=None) -> bool:
        # 实现投票发送
        return True
    
    async def get_status(self, account_id: str):
        from agentbus.channels.base import ChannelStatus, ChannelState, ConnectionStatus
        return ChannelStatus(
            account_id=account_id,
            state=ChannelState.RUNNING if self._connected else ChannelState.STOPPED,
            connection_status=ConnectionStatus.CONNECTED if self._connected else ConnectionStatus.DISCONNECTED,
            connected=self._connected,
            running=self._connected,
        )
    
    async def configure_account(self, account_config: ChannelAccountConfig) -> bool:
        # 实现账户配置
        self.config.accounts[account_config.account_id] = account_config
        return True
```

### 配置渠道

```python
from agentbus.channels.base import (
    ChannelConfig, ChannelAccountConfig, ChannelCapabilities, ChatType
)

# 创建账户配置
account_config = ChannelAccountConfig(
    account_id="bot_account",
    name="My Bot",
    token="your_token_here",
    configured=True
)

# 创建渠道能力配置
capabilities = ChannelCapabilities(
    chat_types=[ChatType.DIRECT, ChatType.GROUP],
    polls=True,
    media=True,
    reactions=True
)

# 创建渠道配置
channel_config = ChannelConfig(
    channel_id="my_channel",
    channel_name="我的渠道",
    channel_type="my_channel",
    accounts={"bot_account": account_config},
    default_account_id="bot_account",
    capabilities=capabilities
)
```

### 事件处理

```python
def on_message(message: Message, channel_id: str):
    print(f"收到消息 [{channel_id}]: {message.content}")

def on_status_change(channel_id: str, status):
    print(f"渠道 {channel_id} 状态变化: {status.state.value}")

# 添加处理器
manager.add_message_handler(on_message)
manager.add_status_handler(on_status_change)
```

## 测试

运行测试以验证功能：

```bash
cd agentbus
python test_channels.py
```

测试包括：
- ✅ 消息元数据功能测试
- ✅ 渠道配置功能测试
- ✅ 渠道管理器基础功能测试

## 配置文件

渠道配置会自动保存为JSON格式：

```json
{
  "channels": {
    "discord_main": {
      "channel_id": "discord_main",
      "channel_name": "Discord主渠道",
      "channel_type": "discord",
      "accounts": {
        "default": {
          "account_id": "default",
          "name": "AgentBot",
          "configured": true,
          "token": "your_discord_token"
        }
      },
      "capabilities": {
        "chat_types": ["direct", "group", "channel"],
        "polls": true,
        "media": true
      }
    }
  },
  "last_updated": "2024-01-29T13:00:00.000000"
}
```

## 架构优势

1. **插件化设计** - 新渠道类型可以通过装饰器轻松注册
2. **统一接口** - 所有渠道都实现相同的抽象接口
3. **状态管理** - 统一的连接状态和健康监控
4. **配置持久化** - 自动保存和恢复配置
5. **事件驱动** - 支持消息和状态变化的事件处理
6. **异步操作** - 全异步设计，支持高并发
7. **类型安全** - 完整的类型注解和枚举定义

## 扩展指南

要添加新的渠道类型：

1. 创建继承自 `ChannelAdapter` 的适配器类
2. 实现所有抽象方法
3. 使用 `@register_channel_type("your_type")` 装饰器注册
4. 在 `ChannelCapabilities` 中定义支持的功能
5. 添加适当的测试

这个设计使得添加新渠道类型变得简单，同时保持了代码的一致性和可维护性。