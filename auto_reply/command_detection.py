"""
命令检测器

检测和解析用户输入中的命令，支持：
- 控制命令检测 (/command)
- 内联命令令牌检测 (/!, !等)
- 命令授权决策
"""

import re
from typing import Optional, Set, Dict, Any
from dataclasses import dataclass
from .commands_registry import (
    list_chat_commands,
    list_chat_commands_for_config,
    normalize_command_body,
    CommandNormalizeOptions,
)


@dataclass
class CommandDetectionOptions:
    """命令检测选项"""
    bot_username: Optional[str] = None


@dataclass
class CommandDetection:
    """命令检测结果"""
    exact: Set[str]
    regex: re.Pattern


def has_control_command(
    text: Optional[str],
    cfg: Optional[Dict[str, Any]] = None,
    options: Optional[CommandDetectionOptions] = None,
) -> bool:
    """
    检查文本是否包含控制命令
    
    Args:
        text: 要检查的文本
        cfg: 配置对象
        options: 检测选项
        
    Returns:
        是否包含控制命令
    """
    if not text:
        return False
    
    trimmed = text.strip()
    if not trimmed:
        return False
    
    normalized_body = normalize_command_body(trimmed, options)
    if not normalized_body:
        return False
    
    lowered = normalized_body.lower()
    commands = list_chat_commands_for_config(cfg) if cfg else list_chat_commands()
    
    for command in commands:
        for alias in command["text_aliases"]:
            normalized = alias.strip().lower()
            if not normalized:
                continue
            
            if lowered == normalized:
                return True
            
            if command["accepts_args"] and lowered.startswith(normalized):
                next_char = normalized_body[len(normalized):len(normalized)+1]
                if next_char and next_char.isspace():
                    return True
    
    return False


def is_control_command_message(
    text: Optional[str],
    cfg: Optional[Dict[str, Any]] = None,
    options: Optional[CommandDetectionOptions] = None,
) -> bool:
    """
    判断是否是控制命令消息
    
    Args:
        text: 要检查的文本
        cfg: 配置对象
        options: 检测选项
        
    Returns:
        是否是控制命令消息
    """
    if not text:
        return False
    
    trimmed = text.strip()
    if not trimmed:
        return False
    
    if has_control_command(trimmed, cfg, options):
        return True
    
    normalized = normalize_command_body(trimmed, options).strip().lower()
    
    # 检查是否是中止触发器
    return _is_abort_trigger(normalized)


def has_inline_command_tokens(text: Optional[str]) -> bool:
    """
    粗略检测内联指令/快捷方式 (例如 "hey /status")
    
    Args:
        text: 要检查的文本
        
    Returns:
        是否包含内联命令令牌
    """
    if not text:
        return False
    
    body = text.strip()
    if not body:
        return False
    
    # 检测 / 或 ! 开始的命令
    pattern = r'(?:^|\s)[/!][a-z]'
    return bool(re.search(pattern, body, re.IGNORECASE))


def should_compute_command_authorized(
    text: Optional[str],
    cfg: Optional[Dict[str, Any]] = None,
    options: Optional[CommandDetectionOptions] = None,
) -> bool:
    """
    判断是否应该计算命令授权
    
    Args:
        text: 要检查的文本
        cfg: 配置对象
        options: 检测选项
        
    Returns:
        是否应该计算命令授权
    """
    return is_control_command_message(text, cfg, options) or has_inline_command_tokens(text)


def _is_abort_trigger(text: str) -> bool:
    """
    检查是否是中止触发器
    
    Args:
        text: 要检查的文本
        
    Returns:
        是否是中止触发器
    """
    abort_triggers = [
        "/abort",
        "/stop", 
        "/cancel",
        "/halt",
    ]
    
    normalized = text.strip().lower()
    
    # 精确匹配
    if normalized in abort_triggers:
        return True
    
    # 检查是否是带参数的中止命令
    for trigger in abort_triggers:
        if normalized.startswith(trigger + " "):
            return True
    
    return False


def build_command_detection() -> CommandDetection:
    """
    构建命令检测器
    
    Returns:
        命令检测结果
    """
    commands = list_chat_commands()
    exact: Set[str] = set()
    patterns: list[str] = []
    
    for command in commands:
        for alias in command["text_aliases"]:
            normalized = alias.strip().lower()
            if not normalized:
                continue
            
            exact.add(normalized)
            
            # 转义正则表达式特殊字符
            escaped = re.escape(normalized)
            if not escaped:
                continue
            
            if command["accepts_args"]:
                patterns.append(f"{escaped}(?:\\s+.+|\\s*:\\s*.*)?")
            else:
                patterns.append(f"{escaped}(?:\\s*:\\s*)?")
    
    regex = re.compile(f"^(?:{"|".join(patterns)})$", re.IGNORECASE) if patterns else re.compile(r"$^")
    
    return CommandDetection(exact=exact, regex=regex)


def detect_command_in_text(text: str) -> Optional[str]:
    """
    在文本中检测命令
    
    Args:
        text: 要检测的文本
        
    Returns:
        检测到的命令名称，如果没有则返回None
    """
    detection = build_command_detection()
    normalized = text.strip().lower()
    
    # 精确匹配
    if normalized in detection.exact:
        return normalized
    
    # 正则匹配
    match = detection.regex.match(normalized)
    if match:
        # 提取命令名称
        token_match = re.match(r"^/([^\s:]+)(?:\s|$)", normalized)
        if token_match:
            token = token_match.group(1)
            return f"/{token.lower()}"
    
    return None