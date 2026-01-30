---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 3046022100a7f6b95210b10da56faf4dfb08fa3da3851ba4763e20ad20032c887ca9a4aaed022100abf5546589e8bcd00976850205a9ac839180f1e09968f1382ba175a137220c30
    ReservedCode2: 30440220104d519192806907fa62d5b345224143b3cef0f2ecaf209678e619ec68f8365202207379a16d75780c21e386f2c27b74c5d467d0823cde5e1f92ce3eae11315cb858
---

# Agentbus 自动回复系统

基于Moltbot自动回复系统的完整Python实现，提供完整的命令检测、消息分发、群组激活控制、媒体处理和回复策略管理功能。

## 系统架构

### 核心模块

1. **命令检测器** (`command_detection.py`)
   - 检测文本中的控制命令 (`/command`)
   - 识别内联命令令牌 (`/command`, `!command`)
   - 判断命令授权需求
   - 支持命令标准化和别名匹配

2. **命令注册表** (`commands_registry.py`)
   - 管理系统中所有可用命令
   - 支持命令参数解析和验证
   - 提供命令查找和匹配功能
   - 支持动态命令注册和注销

3. **命令分发系统** (`dispatch.py`)
   - 将接收的消息分发到相应处理器
   - 支持多种调度器模式（基础调度器、带输入指示调度器）
   - 提供命令处理器注册和管理
   - 处理分发结果和错误

4. **群组激活控制** (`group_activation.py`)
   - 管理群组的激活模式（mention/always）
   - 处理激活命令解析和执行
   - 支持群组级别的配置管理
   - 提供激活状态查询和管理

5. **媒体处理** (`media_processor.py`)
   - 检测和识别媒体文件类型
   - 格式化媒体附件信息
   - 处理媒体理解结果
   - 支持多种媒体格式（图片、视频、音频、文档）

6. **回复策略管理** (`reply_strategy.py`)
   - 定义和管理多种回复策略
   - 控制响应时机和行为
   - 支持用户和群组偏好设置
   - 提供智能回复决策

## 主要特性

### 🔍 智能命令检测
- 自动检测 `/command` 格式的命令
- 支持内联命令令牌识别
- 命令别名和标准化处理
- 上下文感知的命令解析

### 📋 灵活命令管理
- 动态命令注册和注销
- 支持命令参数验证
- 内置常用命令（status、help、config等）
- 可扩展的命令处理器架构

### 💬 多模式群组控制
- **mention模式**: 仅在@提及时响应
- **always模式**: 总是响应群组消息
- **智能模式**: 基于上下文自动决策
- 群组级别的配置管理

### 📎 全面媒体支持
- 自动检测媒体文件类型
- 格式化媒体附件信息
- 支持多文件批量处理
- 媒体理解结果集成

### 🎯 智能回复策略
- 多种响应模式（立即、延迟、计划）
- 思考模式控制（基础、高级、详细）
- 用户偏好学习
- 对话上下文管理

## 快速开始

### 基本使用

```python
import asyncio
from auto_reply import (
    has_control_command,
    dispatch_inbound_message,
    DispatchContext,
    get_group_activation_manager
)

async def handle_message(message_data):
    # 1. 检查是否是命令
    if has_control_command(message_data["text"]):
        # 2. 创建分发上下文
        context = DispatchContext(
            message_id=message_data["id"],
            sender_id=message_data["from"]["id"],
            chat_id=message_data["chat"]["id"],
            chat_type=message_data["chat"]["type"],
            text=message_data["text"]
        )
        
        # 3. 分发消息
        result = await dispatch_inbound_message(context, your_dispatcher)
        
        # 4. 发送回复
        if result.response:
            await send_message(result.response)
    
    # 4. 处理群组激活
    activation_response = handle_group_activation(
        message_data["chat"]["id"],
        message_data["chat"]["type"],
        message_data["text"]
    )
    
    if activation_response:
        await send_message(activation_response)
```

### 高级配置

```python
from auto_reply import (
    ReplyStrategy,
    ReplyStrategyManager,
    GroupActivationMode
)

# 配置回复策略
manager = ReplyStrategyManager()
manager.set_active_strategy("smart")

# 配置群组激活
activation_manager = get_group_activation_manager()
activation_manager.set_group_mode(
    "group_123", 
    GroupActivationMode.ALWAYS
)

# 注册自定义命令
from auto_reply.commands_registry import ChatCommandDefinition

custom_command = ChatCommandDefinition(
    key="weather",
    description="查看天气信息",
    text_aliases=["/weather", "/天气"],
    accepts_args=True,
    args=[...]
)

# 注册命令处理器
dispatcher.register_handler("weather", handle_weather_command)
```

## 内置命令

系统提供以下内置命令：

| 命令 | 别名 | 描述 | 参数 |
|------|------|------|------|
| `/status` | `/状态` | 查看机器人状态 | 无 |
| `/help` | `/帮助` | 显示帮助信息 | 无 |
| `/config` | `/配置` | 配置管理 | `key [value]` |
| `/debug` | `/调试` | 调试模式控制 | `[on/off]` |
| `/echo` | `/回显` | 回显消息 | `message` |
| `/activation` | `/激活` | 设置群组激活模式 | `[mention/always]` |

## 架构优势

### 🔧 模块化设计
- 各模块职责清晰，相互独立
- 支持独立测试和调试
- 易于扩展和定制

### 🚀 高性能
- 异步处理架构
- 智能缓存机制
- 优化的命令检测算法

### 🛡️ 稳定性
- 完善的错误处理
- 失败恢复机制
- 详细的日志记录

### 🔄 可扩展性
- 插件化命令注册
- 策略模式设计
- 灵活的配置系统

## 部署建议

### 集成到现有项目

1. **作为独立服务部署**
   ```python
   from auto_reply import AutoReplyService
   
   service = AutoReplyService(
       strategies=["smart", "mention_only"],
       commands=["status", "help", "weather"],
       media_processing=True
   )
   
   await service.start()
   ```

2. **集成到消息处理管道**
   ```python
   async def process_message_pipeline(message):
       # 1. 预处理
       processed = await preprocess_message(message)
       
       # 2. 自动回复处理
       if should_respond_to_message(**processed):
           response = await handle_auto_reply(processed)
           if response:
               return response
       
       # 3. 继续原有处理流程
       return await normal_processing(message)
   ```

### 配置优化

```python
# 生产环境配置
production_config = {
    "reply_strategy": ReplyStrategy.SMART,
    "response_mode": ResponseMode.IMMEDIATE,
    "max_retries": 3,
    "timeout": 30.0,
    "context_window": 4096,
    "enable_thinking": True,
    "stream_response": False
}

# 开发环境配置
development_config = {
    "reply_strategy": ReplyStrategy.ALWAYS,
    "response_mode": ResponseMode.IMMEDIATE,
    "debug_mode": True,
    "verbose_logging": True
}
```

## 监控和调试

### 日志配置

```python
import logging

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 启用模块特定日志
auto_reply_logger = logging.getLogger('auto_reply')
auto_reply_logger.setLevel(logging.INFO)
```

### 性能监控

```python
# 监控命令执行时间
result = await dispatch_inbound_message(context, dispatcher)
print(f"执行时间: {result.execution_time:.3f}s")

# 监控消息处理量
stats = manager.get_processing_stats()
print(f"处理消息数: {stats['processed_messages']}")
print(f"成功率: {stats['success_rate']:.2%}")
```

## 故障排除

### 常见问题

1. **命令检测失败**
   - 检查命令格式是否正确
   - 确认命令已在注册表中
   - 查看命令别名配置

2. **消息分发异常**
   - 验证上下文参数完整性
   - 检查命令处理器是否注册
   - 查看分发结果日志

3. **群组激活失效**
   - 确认群组ID正确性
   - 检查激活模式配置
   - 验证权限设置

4. **媒体处理错误**
   - 检查文件路径有效性
   - 确认媒体类型支持
   - 验证文件大小限制

## 贡献指南

### 开发环境设置

```bash
# 克隆项目
git clone <repository>
cd agentbus/auto_reply

# 安装依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/

# 运行演示
python demo.py
```

### 代码规范

- 遵循PEP 8代码风格
- 添加适当的文档字符串
- 编写单元测试
- 使用类型注解

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 更新日志

### v1.0.0 (2024-12-28)
- 初始版本发布
- 实现基础命令检测和分发
- 添加群组激活控制
- 支持媒体处理
- 提供智能回复策略

---

**🤖 Agentbus 自动回复系统** - 让智能对话更简单！