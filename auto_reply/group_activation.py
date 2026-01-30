"""
群组激活控制

管理群组的激活模式，包括：
- 激活模式定义 (mention/always)
- 激活命令解析
- 群组激活状态管理
"""

from typing import Optional, Dict, Any, Tuple
from enum import Enum
import re


class GroupActivationMode(Enum):
    """群组激活模式"""
    MENTION = "mention"  # 需要@提及
    ALWAYS = "always"   # 总是响应


class GroupActivationStatus(Enum):
    """群组激活状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"


def normalize_group_activation(raw: Optional[str]) -> Optional[GroupActivationMode]:
    """
    标准化群组激活模式
    
    Args:
        raw: 原始激活模式字符串
        
    Returns:
        标准化的激活模式
    """
    if not raw:
        return None
    
    value = raw.strip().lower()
    
    if value == "mention":
        return GroupActivationMode.MENTION
    elif value == "always":
        return GroupActivationMode.ALWAYS
    
    return None


def parse_activation_command(raw: Optional[str]) -> Tuple[bool, Optional[GroupActivationMode]]:
    """
    解析激活命令
    
    Args:
        raw: 原始命令文本
        
    Returns:
        (是否包含激活命令, 激活模式)
    """
    if not raw:
        return (False, None)
    
    trimmed = raw.strip()
    if not trimmed:
        return (False, None)
    
    from .commands_registry import normalize_command_body
    
    normalized = normalize_command_body(trimmed)
    
    # 匹配 /activation 命令
    match = normalized.match(r"^/activation(?:\s+([a-zA-Z]+))?\s*$/i")
    if not match:
        return (False, None)
    
    mode_str = match.group(1)
    mode = normalize_group_activation(mode_str) if mode_str else None
    
    return (True, mode)


class GroupActivationManager:
    """群组激活管理器"""
    
    def __init__(self):
        self.group_modes: Dict[str, GroupActivationMode] = {}
        self.group_status: Dict[str, GroupActivationStatus] = {}
        self.default_mode = GroupActivationMode.MENTION
    
    def set_group_mode(self, chat_id: str, mode: GroupActivationMode):
        """设置群组激活模式"""
        self.group_modes[chat_id] = mode
        self.group_status[chat_id] = GroupActivationStatus.ACTIVE
        print(f"群组 {chat_id} 激活模式设置为: {mode.value}")
    
    def get_group_mode(self, chat_id: str) -> GroupActivationMode:
        """获取群组激活模式"""
        return self.group_modes.get(chat_id, self.default_mode)
    
    def get_group_status(self, chat_id: str) -> GroupActivationStatus:
        """获取群组激活状态"""
        return self.group_status.get(chat_id, GroupActivationStatus.UNKNOWN)
    
    def is_group_active(self, chat_id: str, has_mention: bool = False) -> bool:
        """检查群组是否激活"""
        mode = self.get_group_mode(chat_id)
        status = self.get_group_status(chat_id)
        
        if status != GroupActivationStatus.ACTIVE:
            return False
        
        if mode == GroupActivationMode.ALWAYS:
            return True
        elif mode == GroupActivationMode.MENTION:
            return has_mention
        
        return False
    
    def activate_group(self, chat_id: str):
        """激活群组"""
        self.group_status[chat_id] = GroupActivationStatus.ACTIVE
        print(f"群组 {chat_id} 已激活")
    
    def deactivate_group(self, chat_id: str):
        """停用群组"""
        self.group_status[chat_id] = GroupActivationStatus.INACTIVE
        print(f"群组 {chat_id} 已停用")
    
    def get_group_info(self, chat_id: str) -> Dict[str, Any]:
        """获取群组信息"""
        return {
            "chat_id": chat_id,
            "mode": self.get_group_mode(chat_id).value,
            "status": self.get_group_status(chat_id).value,
            "is_active": self.is_group_active(chat_id),
        }
    
    def list_all_groups(self) -> Dict[str, Dict[str, Any]]:
        """列出所有群组信息"""
        all_chat_ids = set(self.group_modes.keys()) | set(self.group_status.keys())
        return {
            chat_id: self.get_group_info(chat_id)
            for chat_id in all_chat_ids
        }


class ActivationContext:
    """激活上下文"""
    
    def __init__(self, chat_id: str, chat_type: str, text: Optional[str] = None):
        self.chat_id = chat_id
        self.chat_type = chat_type
        self.text = text or ""
        self.has_mention = self._detect_mention()
        self.has_activation_command = False
        self.new_mode = None
    
    def _detect_mention(self) -> bool:
        """检测是否有@提及"""
        # 这里应该实现实际的@提及检测逻辑
        # 暂时返回False
        return False
    
    def check_activation_command(self) -> bool:
        """检查是否包含激活命令"""
        has_command, new_mode = parse_activation_command(self.text)
        self.has_activation_command = has_command
        self.new_mode = new_mode
        return has_command


def should_process_message(
    context: ActivationContext,
    manager: GroupActivationManager,
) -> bool:
    """
    判断是否应该处理消息
    
    Args:
        context: 激活上下文
        manager: 群组激活管理器
        
    Returns:
        是否应该处理消息
    """
    # 私聊总是处理
    if context.chat_type == "private":
        return True
    
    # 检查是否是激活命令（总是处理激活命令）
    if context.check_activation_command():
        return True
    
    # 检查群组激活状态
    return manager.is_group_active(context.chat_id, context.has_mention)


def process_activation_command(
    context: ActivationContext,
    manager: GroupActivationManager,
) -> Optional[str]:
    """
    处理激活命令
    
    Args:
        context: 激活上下文
        manager: 群组激活管理器
        
    Returns:
        回复消息
    """
    if not context.has_activation_command:
        return None
    
    if context.new_mode:
        # 设置新模式
        manager.set_group_mode(context.chat_id, context.new_mode)
        
        if context.chat_type != "private":
            mode_desc = "总是响应" if context.new_mode == GroupActivationMode.ALWAYS else "需要@提及"
            return f"✅ 群组激活模式已设置为: {mode_desc}"
    else:
        # 显示当前模式
        group_info = manager.get_group_info(context.chat_id)
        mode_desc = {
            "mention": "需要@提及",
            "always": "总是响应"
        }.get(group_info["mode"], "未知")
        
        status_desc = {
            "active": "已激活",
            "inactive": "已停用", 
            "unknown": "未知"
        }.get(group_info["status"], "未知")
        
        return f"🔧 当前群组状态: {status_desc}\n激活模式: {mode_desc}"
    
    return None


# 全局群组激活管理器实例
_activation_manager = GroupActivationManager()


def get_group_activation_manager() -> GroupActivationManager:
    """获取群组激活管理器"""
    return _activation_manager


def is_message_processable(
    chat_id: str,
    chat_type: str,
    text: Optional[str] = None,
    has_mention: bool = False,
) -> bool:
    """
    快速检查消息是否可处理
    
    Args:
        chat_id: 聊天ID
        chat_type: 聊天类型
        text: 消息文本
        has_mention: 是否有@提及
        
    Returns:
        消息是否可处理
    """
    context = ActivationContext(chat_id, chat_type, text)
    context.has_mention = has_mention
    
    return should_process_message(context, _activation_manager)


def handle_group_activation(
    chat_id: str,
    chat_type: str,
    text: Optional[str] = None,
) -> Optional[str]:
    """
    处理群组激活
    
    Args:
        chat_id: 聊天ID
        chat_type: 聊天类型
        text: 消息文本
        
    Returns:
        回复消息
    """
    context = ActivationContext(chat_id, chat_type, text)
    
    # 处理激活命令
    if context.has_activation_command:
        return process_activation_command(context, _activation_manager)
    
    return None