"""
Agentbus自动回复系统演示

演示如何使用自动回复系统的各个组件：
- 命令检测
- 消息分发
- 群组激活控制
- 媒体处理
- 回复策略管理
"""

import asyncio
import logging
from typing import Optional

from . import (
    # 命令检测
    has_control_command,
    is_control_command_message,
    has_inline_command_tokens,
    should_compute_command_authorized,
    
    # 命令注册表
    list_chat_commands,
    resolve_text_command,
    normalize_command_body,
    ChatCommandDefinition,
    CommandArgDefinition,
    CommandScope,
    CommandArgsParsing,
    
    # 分发系统
    dispatch_inbound_message,
    DispatchContext,
    DispatchResult,
    DispatchStatus,
    
    # 群组激活
    GroupActivationMode,
    get_group_activation_manager,
    is_message_processable,
    handle_group_activation,
    
    # 媒体处理
    build_inbound_media_note,
    MediaProcessor,
    MediaType,
    MediaAttachment,
    
    # 回复策略
    ReplyStrategy,
    ReplyStrategyManager,
    ReplyOptions,
    should_respond_to_message,
    create_reply_context,
)


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DemoChannel:
    """演示频道类"""
    
    def __init__(self, name: str):
        self.name = name
    
    async def send_message(self, chat_id: str, text: str):
        """发送消息"""
        print(f"[{self.name}] 发送到 {chat_id}: {text}")
        return "demo_message_id"


async def demo_command_detection():
    """演示命令检测功能"""
    print("\\n=== 命令检测演示 ===")
    
    test_messages = [
        "/status",
        "/help",
        "/config key value",
        "Hello, bot!",
        "Hey @bot /status",
        "/echo Hello World",
        "普通消息",
    ]
    
    for message in test_messages:
        print(f"\\n消息: '{message}'")
        
        # 检查是否是控制命令
        has_command = has_control_command(message)
        print(f"  包含控制命令: {has_command}")
        
        # 检查是否是控制命令消息
        is_command_msg = is_control_command_message(message)
        print(f"  是控制命令消息: {is_command_msg}")
        
        # 检查内联命令令牌
        has_inline = has_inline_command_tokens(message)
        print(f"  包含内联命令令牌: {has_inline}")
        
        # 检查是否应该计算命令授权
        should_compute = should_compute_command_authorized(message)
        print(f"  应该计算命令授权: {should_compute}")


async def demo_commands_registry():
    """演示命令注册表功能"""
    print("\\n=== 命令注册表演示 ===")
    
    # 列出所有可用命令
    commands = list_chat_commands()
    print(f"\\n可用命令数量: {len(commands)}")
    
    for command in commands:
        print(f"  - {command['key']}: {command['description']}")
        print(f"    别名: {', '.join(command['text_aliases'])}")
        print(f"    接受参数: {command['accepts_args']}")
        print()
    
    # 测试命令解析
    test_commands = [
        "/status",
        "/config api_key 12345",
        "/echo Hello, World!",
    ]
    
    for cmd_text in test_commands:
        print(f"\\n解析命令: '{cmd_text}'")
        result = resolve_text_command(cmd_text)
        if result:
            command, args = result
            print(f"  命令: {command['key']}")
            print(f"  参数: {args}")


async def demo_dispatch_system():
    """演示分发系统功能"""
    print("\\n=== 分发系统演示 ===")
    
    # 创建演示频道
    channel = DemoChannel("DemoChannel")
    
    # 创建分发上下文
    context = DispatchContext(
        message_id="demo_msg_001",
        sender_id="user_123",
        chat_id="group_456",
        chat_type="group",
        text="/status"
    )
    
    print(f"\\n分发上下文:")
    print(f"  消息ID: {context.message_id}")
    print(f"  发送者: {context.sender_id}")
    print(f"  聊天ID: {context.chat_id}")
    print(f"  聊天类型: {context.chat_type}")
    print(f"  文本: {context.text}")
    
    # 执行分发
    result = await dispatch_inbound_message(context, channel)
    
    print(f"\\n分发结果:")
    print(f"  状态: {result.status}")
    print(f"  命令: {result.command_key}")
    print(f"  参数: {result.args}")
    print(f"  响应: {result.response}")
    print(f"  执行时间: {result.execution_time:.3f}s")


async def demo_group_activation():
    """演示群组激活控制功能"""
    print("\\n=== 群组激活控制演示 ===")
    
    manager = get_group_activation_manager()
    
    # 测试群组
    test_groups = [
        ("group_123", "private"),
        ("group_456", "group"),
        ("group_789", "supergroup"),
    ]
    
    for chat_id, chat_type in test_groups:
        print(f"\\n群组 {chat_id} ({chat_type}):")
        
        # 检查消息是否可处理
        processable = is_message_processable(chat_id, chat_type, "/status")
        print(f"  /status 可处理: {processable}")
        
        processable = is_message_processable(chat_id, chat_type, "Hello bot!")
        print(f"  普通消息可处理: {processable}")
        
        # 处理激活命令
        response = handle_group_activation(chat_id, chat_type, "/activation")
        if response:
            print(f"  激活命令响应: {response}")
        
        # 设置群组模式
        manager.set_group_mode(chat_id, GroupActivationMode.ALWAYS)
        print(f"  已设置为总是响应模式")
    
    # 列出所有群组信息
    print("\\n所有群组信息:")
    for chat_id, info in manager.list_all_groups().items():
        print(f"  {chat_id}: {info}")


async def demo_media_processing():
    """演示媒体处理功能"""
    print("\\n=== 媒体处理演示 ===")
    
    processor = MediaProcessor()
    
    # 测试媒体文件
    test_files = [
        "image.jpg",
        "video.mp4",
        "audio.mp3",
        "document.pdf",
        "unknown.xyz",
    ]
    
    print("\\n媒体类型检测:")
    for file_path in test_files:
        media_type = processor.detect_media_type(file_path)
        print(f"  {file_path}: {media_type.value}")
    
    # 构建媒体备注
    media_note = build_inbound_media_note(
        media_paths=["image1.jpg", "image2.png"],
        media_urls=["https://example.com/img1.jpg", "https://example.com/img2.png"]
    )
    
    print(f"\\n媒体备注:")
    print(f"  {media_note}")
    
    # 创建媒体附件
    attachment = MediaAttachment(
        path="test_image.jpg",
        url="https://example.com/test.jpg",
        media_type=MediaType.IMAGE
    )
    
    formatted_line = processor.format_media_attached_line(attachment)
    print(f"\\n格式化附件行:")
    print(f"  {formatted_line}")


async def demo_reply_strategy():
    """演示回复策略功能"""
    print("\\n=== 回复策略演示 ===")
    
    manager = ReplyStrategyManager()
    
    # 测试不同策略
    test_scenarios = [
        ("command", False, True, "private", None),
        ("text", False, False, "private", None),
        ("text", False, False, "group", "user_123"),
        ("mention", True, False, "group", "user_123"),
        ("text", False, False, "group", "user_456"),
    ]
    
    print("\\n策略响应测试:")
    for message_type, has_mention, has_command, chat_type, sender_id in test_scenarios:
        should_respond = should_respond_to_message(
            message_type=message_type,
            has_mention=has_mention,
            has_command=has_command,
            chat_type=chat_type,
            sender_id=sender_id
        )
        
        print(f"  {message_type} | 提及:{has_mention} | 命令:{has_command} | {chat_type} | {sender_id}: {should_respond}")
    
    # 创建回复上下文
    context = create_reply_context(
        message_id="msg_001",
        sender_id="user_123",
        chat_id="group_456",
        chat_type="group",
        text="Hello bot!",
        metadata={"source": "telegram"}
    )
    
    print("\\n回复上下文:")
    for key, value in context.items():
        if key != "conversation_context":  # 简化输出
            print(f"  {key}: {value}")


async def demo_complete_workflow():
    """演示完整工作流程"""
    print("\\n=== 完整工作流程演示 ===")
    
    # 模拟接收消息
    incoming_message = {
        "message_id": "demo_001",
        "sender_id": "user_123",
        "chat_id": "group_456",
        "chat_type": "group",
        "text": "/status",
        "has_mention": True,
        "has_command": True,
    }
    
    print(f"\\n接收消息: {incoming_message['text']}")
    
    # 1. 检查是否应该处理
    should_process = is_message_processable(
        incoming_message["chat_id"],
        incoming_message["chat_type"],
        incoming_message["text"],
        incoming_message["has_mention"]
    )
    
    print(f"1. 是否应该处理: {should_process}")
    
    if not should_process:
        print("消息被忽略")
        return
    
    # 2. 处理群组激活命令
    activation_response = handle_group_activation(
        incoming_message["chat_id"],
        incoming_message["chat_type"],
        incoming_message["text"]
    )
    
    if activation_response:
        print(f"2. 激活命令响应: {activation_response}")
        return
    
    # 3. 检查是否应该响应
    should_respond = should_respond_to_message(
        message_type="command",
        has_command=incoming_message["has_command"],
        chat_type=incoming_message["chat_type"],
        sender_id=incoming_message["sender_id"]
    )
    
    print(f"3. 是否应该响应: {should_respond}")
    
    if not should_respond:
        print("消息被忽略")
        return
    
    # 4. 创建分发上下文
    context = DispatchContext(**incoming_message)
    
    # 5. 分发消息
    channel = DemoChannel("AutoReplyBot")
    result = await dispatch_inbound_message(context, channel)
    
    print(f"4. 分发结果:")
    print(f"   状态: {result.status}")
    print(f"   响应: {result.response}")


async def main():
    """主演示函数"""
    print("🤖 Agentbus 自动回复系统演示")
    print("=" * 50)
    
    try:
        await demo_command_detection()
        await demo_commands_registry()
        await demo_dispatch_system()
        await demo_group_activation()
        await demo_media_processing()
        await demo_reply_strategy()
        await demo_complete_workflow()
        
        print("\\n✅ 演示完成!")
        
    except Exception as e:
        print(f"\\n❌ 演示过程中出错: {e}")
        logger.exception("演示错误")


if __name__ == "__main__":
    asyncio.run(main())