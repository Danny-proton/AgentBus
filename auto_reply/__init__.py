"""
Agentbus自动回复系统

基于Moltbot自动回复系统的完整实现，包含：
- 命令检测器
- 命令分发系统
- 回复策略管理
- 群组激活控制
- 媒体处理
"""

from .command_detection import (
    has_control_command,
    is_control_command_message,
    has_inline_command_tokens,
    should_compute_command_authorized,
    CommandDetection,
    CommandDetectionOptions,
)

from .commands_registry import (
    ChatCommandDefinition,
    CommandArgDefinition,
    CommandArgs,
    CommandDetection,
    CommandNormalizeOptions,
    CommandScope,
    CommandArgsParsing,
    list_chat_commands,
    list_chat_commands_for_config,
    find_command_by_native_name,
    resolve_text_command,
    normalize_command_body,
    is_command_message,
    parse_command_args,
    serialize_command_args,
)

from .dispatch import (
    DispatchResult,
    DispatchContext,
    DispatchStatus,
    dispatch_inbound_message,
    dispatch_inbound_message_with_dispatcher,
    dispatch_inbound_message_with_buffered_dispatcher,
)

from .group_activation import (
    GroupActivationMode,
    normalize_group_activation,
    parse_activation_command,
)

from .media_processor import (
    MediaProcessor,
    build_inbound_media_note,
)

from .reply_strategy import (
    ReplyStrategy,
    ReplyStrategyManager,
    ReplyOptions,
)

__all__ = [
    # 命令检测
    "has_control_command",
    "is_control_command_message", 
    "has_inline_command_tokens",
    "should_compute_command_authorized",
    "CommandDetection",
    "CommandDetectionOptions",
    
    # 命令注册表
    "ChatCommandDefinition",
    "CommandArgDefinition", 
    "CommandArgs",
    "CommandDetection",
    "CommandNormalizeOptions",
    "list_chat_commands",
    "list_chat_commands_for_config",
    "find_command_by_native_name",
    "resolve_text_command",
    "normalize_command_body",
    "is_command_message",
    "parse_command_args",
    "serialize_command_args",
    
    # 分发系统
    "DispatchResult",
    "dispatch_inbound_message",
    "dispatch_inbound_message_with_dispatcher",
    "dispatch_inbound_message_with_buffered_dispatcher",
    
    # 群组激活
    "GroupActivationMode",
    "normalize_group_activation",
    "parse_activation_command",
    
    # 媒体处理
    "MediaProcessor",
    "build_inbound_media_note",
    
    # 回复策略
    "ReplyStrategy",
    "ReplyStrategyManager",
    "ReplyOptions",
]