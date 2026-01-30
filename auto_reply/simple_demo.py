#!/usr/bin/env python3
"""
Agentbus自动回复系统 - 简化演示

直接测试系统各个组件的功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 直接导入各个模块
from command_detection import (
    has_control_command,
    is_control_command_message,
    has_inline_command_tokens,
    should_compute_command_authorized
)

from commands_registry import (
    list_chat_commands,
    resolve_text_command,
    normalize_command_body,
    ChatCommandDefinition
)

from dispatch import (
    DispatchContext,
    DispatchResult,
    DispatchStatus
)

from group_activation import (
    GroupActivationMode,
    get_group_activation_manager,
    is_message_processable,
    handle_group_activation
)

from media_processor import (
    MediaProcessor,
    MediaType,
    build_inbound_media_note
)

from reply_strategy import (
    ReplyStrategy,
    ReplyStrategyManager,
    should_respond_to_message,
    create_reply_context
)


def test_command_detection():
    """测试命令检测功能"""
    print("🔍 测试命令检测")
    test_messages = ["/status", "/help", "Hello bot!", "普通消息"]
    
    for msg in test_messages:
        has_cmd = has_control_command(msg)
        is_cmd_msg = is_control_command_message(msg)
        print(f"  '{msg}' -> 控制命令:{has_cmd}, 命令消息:{is_cmd_msg}")


def test_commands_registry():
    """测试命令注册表"""
    print("\n📋 测试命令注册表")
    commands = list_chat_commands()
    print(f"  注册命令数量: {len(commands)}")
    
    # 测试命令解析
    result = resolve_text_command("/status")
    if result:
        cmd, args = result
        print(f"  解析 '/status' -> 命令:{cmd['key']}, 参数:{args}")


def test_group_activation():
    """测试群组激活"""
    print("\n👥 测试群组激活")
    manager = get_group_activation_manager()
    
    # 测试消息处理
    can_process = is_message_processable("group123", "group", "/status")
    print(f"  群组消息可处理: {can_process}")
    
    # 处理激活命令
    response = handle_group_activation("group123", "group", "/activation")
    print(f"  激活命令响应: {response or '无'}")


def test_media_processing():
    """测试媒体处理"""
    print("\n🎬 测试媒体处理")
    processor = MediaProcessor()
    
    # 检测媒体类型
    media_type = processor.detect_media_type("image.jpg")
    print(f"  'image.jpg' 类型: {media_type.value}")
    
    # 构建媒体备注
    note = build_inbound_media_note(media_paths=["img1.jpg", "img2.png"])
    print(f"  媒体备注: {note}")


def test_reply_strategy():
    """测试回复策略"""
    print("\n🎯 测试回复策略")
    
    # 测试响应决策
    should_resp = should_respond_to_message(
        message_type="command",
        has_command=True,
        chat_type="private"
    )
    print(f"  应该响应命令: {should_resp}")
    
    # 创建回复上下文
    context = create_reply_context(
        message_id="msg1",
        sender_id="user1",
        chat_id="chat1", 
        chat_type="private",
        text="Hello!"
    )
    print(f"  上下文创建: 成功")


def test_complete_workflow():
    """测试完整工作流程"""
    print("\n🚀 测试完整工作流程")
    
    # 模拟接收命令消息
    message = {
        "message_id": "demo_001",
        "sender_id": "user_123",
        "chat_id": "group_456", 
        "chat_type": "group",
        "text": "/status",
        "has_mention": True,
        "has_command": True,
    }
    
    print(f"  接收消息: '{message['text']}'")
    
    # 1. 检查是否应该处理
    should_process = is_message_processable(
        message["chat_id"], 
        message["chat_type"], 
        message["text"],
        message["has_mention"]
    )
    print(f"  1. 应该处理: {should_process}")
    
    # 2. 检查是否应该响应
    should_respond = should_respond_to_message(
        message_type="command",
        has_command=message["has_command"],
        chat_type=message["chat_type"],
        sender_id=message["sender_id"]
    )
    print(f"  2. 应该响应: {should_respond}")
    
    # 3. 解析命令
    result = resolve_text_command(message["text"])
    if result:
        cmd, args = result
        print(f"  3. 解析命令: {cmd['key']} (参数: {args})")
    
    print("  4. 工作流程测试完成 ✅")


def main():
    """主函数"""
    print("🤖 Agentbus 自动回复系统演示")
    print("=" * 50)
    
    try:
        test_command_detection()
        test_commands_registry()
        test_group_activation()
        test_media_processing()
        test_reply_strategy()
        test_complete_workflow()
        
        print("\n✅ 演示完成！自动回复系统功能正常")
        
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()