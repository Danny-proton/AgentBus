"""
命令注册表

管理系统中所有可用命令，包括：
- 命令定义和注册
- 命令参数解析
- 命令文本标准化
- 命令查找和匹配
"""

import re
from typing import Optional, Dict, Any, List, Union, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum


class CommandScope(Enum):
    """命令作用域"""
    NATIVE = "native"
    TEXT = "text"
    BOTH = "both"


class CommandArgsParsing(Enum):
    """命令参数解析模式"""
    NONE = "none"
    POSITIONAL = "positional"


@dataclass
class CommandArgDefinition:
    """命令参数定义"""
    name: str
    description: str
    required: bool = True
    capture_remaining: bool = False
    choices: Optional[List[Union[str, Dict[str, str]]]] = None
    default: Optional[str] = None


@dataclass
class CommandArgs:
    """命令参数"""
    raw: Optional[str] = None
    values: Optional[Dict[str, Any]] = None


@dataclass
class ChatCommandDefinition:
    """聊天命令定义"""
    key: str
    native_name: Optional[str] = None
    description: str = ""
    text_aliases: List[str] = field(default_factory=list)
    accepts_args: bool = False
    args_parsing: CommandArgsParsing = CommandArgsParsing.NONE
    args: Optional[List[CommandArgDefinition]] = None
    scope: CommandScope = CommandScope.BOTH
    format_args: Optional[callable] = None
    enabled: bool = True


@dataclass
class CommandDetection:
    """命令检测结果"""
    exact: Set[str]
    regex: re.Pattern


@dataclass 
class CommandNormalizeOptions:
    """命令标准化选项"""
    bot_username: Optional[str] = None


# 内置命令定义
BUILTIN_COMMANDS = [
    ChatCommandDefinition(
        key="status",
        native_name="status",
        description="查看机器人状态",
        text_aliases=["/status", "/状态"],
        accepts_args=False,
        scope=CommandScope.BOTH,
    ),
    ChatCommandDefinition(
        key="help", 
        native_name="help",
        description="显示帮助信息",
        text_aliases=["/help", "/帮助"],
        accepts_args=False,
        scope=CommandScope.BOTH,
    ),
    ChatCommandDefinition(
        key="config",
        native_name="config", 
        description="配置管理",
        text_aliases=["/config", "/配置"],
        accepts_args=True,
        args=[
            CommandArgDefinition(
                name="key",
                description="配置键名",
                required=True
            ),
            CommandArgDefinition(
                name="value", 
                description="配置值",
                required=False
            ),
        ],
        scope=CommandScope.BOTH,
    ),
    ChatCommandDefinition(
        key="debug",
        native_name="debug",
        description="调试模式",
        text_aliases=["/debug", "/调试"],
        accepts_args=True,
        scope=CommandScope.BOTH,
    ),
    ChatCommandDefinition(
        key="bash",
        native_name="bash",
        description="执行shell命令",
        text_aliases=["/bash", "/shell"],
        accepts_args=True,
        args=[
            CommandArgDefinition(
                name="command",
                description="要执行的命令",
                required=True,
                capture_remaining=True
            )
        ],
        scope=CommandScope.BOTH,
    ),
    ChatCommandDefinition(
        key="echo",
        native_name="echo",
        description="回显消息",
        text_aliases=["/echo", "/回显"],
        accepts_args=True,
        args=[
            CommandArgDefinition(
                name="message",
                description="要回显的消息",
                required=True,
                capture_remaining=True
            )
        ],
        scope=CommandScope.BOTH,
    ),
    ChatCommandDefinition(
        key="activation",
        native_name="activation",
        description="设置群组激活模式",
        text_aliases=["/activation", "/激活"],
        accepts_args=True,
        args=[
            CommandArgDefinition(
                name="mode",
                description="激活模式 (mention/always)",
                required=False,
                choices=["mention", "always"]
            )
        ],
        scope=CommandScope.BOTH,
    ),
]


class CommandRegistry:
    """命令注册表管理器"""
    
    def __init__(self):
        self._commands: Dict[str, ChatCommandDefinition] = {}
        self._native_commands: Dict[str, ChatCommandDefinition] = {}
        self._text_alias_map: Dict[str, ChatCommandDefinition] = {}
        self._cached_detection: Optional[CommandDetection] = None
        self._register_builtin_commands()
    
    def _register_builtin_commands(self):
        """注册内置命令"""
        for command in BUILTIN_COMMANDS:
            self.register_command(command)
    
    def register_command(self, command: ChatCommandDefinition):
        """注册命令"""
        self._commands[command.key] = command
        
        # 注册原生命令
        if command.native_name:
            self._native_commands[command.native_name] = command
        
        # 注册文本别名
        for alias in command.text_aliases:
            if alias:
                self._text_alias_map[alias.lower()] = command
    
    def unregister_command(self, key: str):
        """注销命令"""
        if key in self._commands:
            command = self._commands.pop(key)
            
            # 移除原生命令
            if command.native_name and command.native_name in self._native_commands:
                del self._native_commands[command.native_name]
            
            # 移除文本别名
            for alias in command.text_aliases:
                if alias in self._text_alias_map:
                    del self._text_alias_map[alias.lower()]
            
            # 清除缓存
            self._cached_detection = None
    
    def get_command(self, key: str) -> Optional[ChatCommandDefinition]:
        """获取命令定义"""
        return self._commands.get(key)
    
    def get_commands(self) -> List[ChatCommandDefinition]:
        """获取所有命令"""
        return list(self._commands.values())
    
    def get_native_command(self, name: str) -> Optional[ChatCommandDefinition]:
        """获取原生命令"""
        return self._native_commands.get(name)
    
    def list_native_commands(self) -> List[ChatCommandDefinition]:
        """列出所有原生命令"""
        return list(self._native_commands.values())
    
    def find_command_by_text_alias(self, alias: str) -> Optional[ChatCommandDefinition]:
        """根据文本别名查找命令"""
        return self._text_alias_map.get(alias.lower())
    
    def list_commands_for_config(self, cfg: Optional[Dict[str, Any]] = None) -> List[ChatCommandDefinition]:
        """根据配置列出可用命令"""
        commands = []
        for command in self._commands.values():
            if self._is_command_enabled(cfg, command):
                commands.append(command)
        return commands
    
    def _is_command_enabled(self, cfg: Optional[Dict[str, Any]], command: ChatCommandDefinition) -> bool:
        """检查命令是否启用"""
        if not cfg or not cfg.get("commands"):
            return command.enabled
        
        commands_config = cfg.get("commands", {})
        
        # 特殊处理配置命令
        if command.key == "config":
            return commands_config.get("config", True)
        elif command.key == "debug":
            return commands_config.get("debug", False)
        elif command.key == "bash":
            return commands_config.get("bash", False)
        
        return command.enabled
    
    def build_detection(self) -> CommandDetection:
        """构建命令检测"""
        if self._cached_detection:
            return self._cached_detection
        
        exact: Set[str] = set()
        patterns: list[str] = []
        
        for command in self._commands.values():
            for alias in command.text_aliases:
                normalized = alias.strip().lower()
                if not normalized:
                    continue
                
                exact.add(normalized)
                
                # 转义正则表达式特殊字符
                escaped = re.escape(normalized)
                if not escaped:
                    continue
                
                if command.accepts_args:
                    patterns.append(f"{escaped}(?:\\s+.+|\\s*:\\s*.*)?")
                else:
                    patterns.append(f"{escaped}(?:\\s*:\\s*)?")
        
        regex = re.compile(f"^(?:{"|".join(patterns)})$", re.IGNORECASE) if patterns else re.compile(r"$^")
        
        self._cached_detection = CommandDetection(exact=exact, regex=regex)
        return self._cached_detection


# 全局命令注册表实例
_registry = CommandRegistry()


def list_chat_commands() -> List[ChatCommandDefinition]:
    """列出所有聊天命令"""
    return _registry.get_commands()


def list_chat_commands_for_config(cfg: Optional[Dict[str, Any]] = None) -> List[ChatCommandDefinition]:
    """根据配置列出聊天命令"""
    return _registry.list_commands_for_config(cfg)


def find_command_by_native_name(name: str) -> Optional[ChatCommandDefinition]:
    """根据原生名称查找命令"""
    return _registry.get_native_command(name)


def resolve_text_command(raw: str, cfg: Optional[Dict[str, Any]] = None) -> Optional[Tuple[ChatCommandDefinition, Optional[str]]]:
    """解析文本命令"""
    trimmed = normalize_command_body(raw).strip()
    alias = _maybe_resolve_text_alias(trimmed, cfg)
    
    if not alias:
        return None
    
    command = _registry.find_command_by_text_alias(alias)
    if not command:
        return None
    
    if not command.accepts_args:
        return (command, None)
    
    args = trimmed[len(alias):].strip()
    return (command, args or None)


def normalize_command_body(raw: str, options: Optional[CommandNormalizeOptions] = None) -> str:
    """标准化命令体"""
    trimmed = raw.strip()
    
    if not trimmed.startswith("/"):
        return trimmed
    
    # 处理单行
    newline_index = trimmed.find("\n")
    single_line = trimmed[:newline_index] if newline_index >= 0 else trimmed
    
    # 处理冒号格式
    colon_match = single_line.match(r"^/([^\s:]+)\s*:(.*)$/")
    if colon_match:
        command, rest = colon_match.groups()
        normalized_rest = rest.strip()
        return f"/{command} {normalized_rest}" if normalized_rest else f"/{command}"
    
    # 处理@提及
    normalized_bot_username = options.bot_username.strip().lower() if options and options.bot_username else None
    if normalized_bot_username:
        mention_match = single_line.match(r"^/([^\s@]+)@([^\s]+)(.*)$/")
        if mention_match and mention_match[2].lower() == normalized_bot_username:
            return f"/{mention_match[1]}{mention_match[3] or ""}"
    
    # 查找匹配的命令
    detection = _registry.build_detection()
    lowered = single_line.lower()
    
    if lowered in detection.exact:
        return lowered
    
    token_match = single_line.match(r"^/([^\s]+)(?:\s+([\s\S]+))?$/")
    if not token_match:
        return single_line
    
    token, rest = token_match.groups()
    token_key = f"/{token.lower()}"
    token_command = _registry.find_command_by_text_alias(token_key)
    
    if not token_command:
        return single_line
    
    if rest and not token_command.accepts_args:
        return single_line
    
    normalized_rest = rest.strip_start() if rest else None
    return f"{token_command.text_aliases[0]} {normalized_rest}" if normalized_rest else token_command.text_aliases[0]


def _maybe_resolve_text_alias(raw: str, cfg: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """尝试解析文本别名"""
    trimmed = normalize_command_body(raw).strip()
    if not trimmed.startswith("/"):
        return None
    
    detection = _registry.build_detection()
    normalized = trimmed.lower()
    
    if normalized in detection.exact:
        return normalized
    
    if not detection.regex.match(normalized):
        return None
    
    token_match = re.match(r"^/([^\s:]+)(?:\s|$)", normalized)
    if not token_match:
        return None
    
    token_key = f"/{token_match[1]}"
    return token_key if token_key in _registry._text_alias_map else None


def is_command_message(raw: str) -> bool:
    """检查是否是命令消息"""
    return normalize_command_body(raw).startswith("/")


def parse_command_args(command: ChatCommandDefinition, raw: Optional[str]) -> Optional[CommandArgs]:
    """解析命令参数"""
    trimmed = raw.strip() if raw else None
    if not trimmed:
        return None
    
    if not command.args or command.args_parsing == CommandArgsParsing.NONE:
        return CommandArgs(raw=trimmed)
    
    values = _parse_positional_args(command.args, trimmed)
    return CommandArgs(raw=trimmed, values=values)


def _parse_positional_args(definitions: List[CommandArgDefinition], raw: str) -> Dict[str, Any]:
    """解析位置参数"""
    values: Dict[str, Any] = {}
    trimmed = raw.strip()
    
    if not trimmed:
        return values
    
    tokens = [token for token in trimmed.split() if token]
    index = 0
    
    for definition in definitions:
        if index >= len(tokens):
            break
        
        if definition.capture_remaining:
            values[definition.name] = " ".join(tokens[index:])
            break
        
        values[definition.name] = tokens[index]
        index += 1
    
    return values


def serialize_command_args(command: ChatCommandDefinition, args: Optional[CommandArgs]) -> Optional[str]:
    """序列化命令参数"""
    if not args:
        return None
    
    raw = args.raw.strip() if args.raw else None
    if raw:
        return raw
    
    if not args.values or not command.args:
        return None
    
    if command.format_args:
        return command.format_args(args.values)
    
    return _format_positional_args(command.args, args.values)


def _format_positional_args(definitions: List[CommandArgDefinition], values: Dict[str, Any]) -> Optional[str]:
    """格式化位置参数"""
    parts: List[str] = []
    
    for definition in definitions:
        value = values.get(definition.name)
        if value is None:
            continue
        
        rendered = value.strip() if isinstance(value, str) else str(value)
        if not rendered:
            continue
        
        parts.append(rendered)
        if definition.capture_remaining:
            break
    
    return " ".join(parts) if parts else None


def build_command_text(command_name: str, args: Optional[str] = None) -> str:
    """构建命令文本"""
    trimmed_args = args.strip() if args else None
    return f"/{command_name} {trimmed_args}" if trimmed_args else f"/{command_name}"


def build_command_text_from_args(command: ChatCommandDefinition, args: Optional[CommandArgs] = None) -> str:
    """根据参数构建命令文本"""
    command_name = command.native_name or command.key
    return build_command_text(command_name, serialize_command_args(command, args))