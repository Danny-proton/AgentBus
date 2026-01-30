"""
高级命令解析器
Advanced Command Parser

基于Moltbot的命令解析系统，提供更强大的CLI命令解析和执行能力。
"""

import re
import shlex
import json
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """令牌类型"""
    COMMAND = "command"
    OPTION = "option"
    ARGUMENT = "argument"
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    IDENTIFIER = "identifier"


@dataclass
class Token:
    """命令令牌"""
    type: TokenType
    value: str
    position: int
    line: int
    column: int


@dataclass
class ParsedCommand:
    """解析后的命令"""
    command: str
    subcommand: Optional[str] = None
    options: Dict[str, Any] = None
    arguments: List[Any] = None
    flags: List[str] = None
    raw_tokens: List[Token] = None


class CommandParseError(Exception):
    """命令解析错误"""
    pass


class AdvancedCommandParser:
    """高级命令解析器"""
    
    def __init__(self):
        self._command_registry: Dict[str, Dict] = {}
        self._option_patterns: Dict[str, re.Pattern] = {}
        self._option_aliases: Dict[str, str] = {}
        self._init_default_patterns()
    
    def _init_default_patterns(self):
        """初始化默认模式"""
        # 选项模式
        self._option_patterns.update({
            'short': re.compile(r'^-([a-zA-Z])$'),
            'long': re.compile(r'^--([a-zA-Z][a-zA-Z0-9_-]*)$'),
            'windows': re.compile(r'^/([a-zA-Z][a-zA-Z0-9_-]*)$')
        })
        
        # 常用别名
        self._option_aliases.update({
            'h': 'help',
            'v': 'verbose',
            'q': 'quiet',
            'o': 'output',
            'f': 'format',
            'd': 'debug',
            'c': 'config',
            'p': 'profile'
        })
    
    def register_command(self, command: str, schema: Dict[str, Any]):
        """注册命令模式"""
        self._command_registry[command] = schema
    
    def parse_command_line(self, command_line: str) -> ParsedCommand:
        """解析命令行"""
        try:
            tokens = self._tokenize(command_line)
            return self._build_command(tokens)
        except Exception as e:
            raise CommandParseError(f"命令解析失败: {e}")
    
    def _tokenize(self, command_line: str) -> List[Token]:
        """分词处理"""
        tokens = []
        lines = command_line.split('\n')
        
        for line_num, line in enumerate(lines):
            if not line.strip():
                continue
                
            try:
                # 使用shlex进行基本分词，保留引号内的内容
                lexer_tokens = shlex.split(line)
            except ValueError as e:
                raise CommandParseError(f"引号不匹配: {line}")
            
            position = 0
            for token_text in lexer_tokens:
                token_type = self._determine_token_type(token_text)
                tokens.append(Token(
                    type=token_type,
                    value=token_text,
                    position=position,
                    line=line_num,
                    column=line.find(token_text)
                ))
                position += len(token_text) + 1
        
        return tokens
    
    def _determine_token_type(self, token: str) -> TokenType:
        """确定令牌类型"""
        # 检查是否为选项
        if self._is_option(token):
            return TokenType.OPTION
        
        # 检查是否为字符串
        if token.startswith('"') and token.endswith('"'):
            return TokenType.STRING
        
        # 检查是否为数字
        if re.match(r'^-?\d+\.?\d*$', token):
            return TokenType.NUMBER
        
        # 检查是否为布尔值
        if token.lower() in ['true', 'false', 'yes', 'no', 'on', 'off']:
            return TokenType.BOOLEAN
        
        # 默认标识符
        return TokenType.IDENTIFIER
    
    def _is_option(self, token: str) -> bool:
        """检查是否为选项"""
        for pattern in self._option_patterns.values():
            if pattern.match(token):
                return True
        return False
    
    def _build_command(self, tokens: List[Token]) -> ParsedCommand:
        """构建命令对象"""
        if not tokens:
            raise CommandParseError("空命令")
        
        # 第一个令牌必须是命令
        first_token = tokens[0]
        if first_token.type != TokenType.IDENTIFIER:
            raise CommandParseError(f"无效命令: {first_token.value}")
        
        command_parts = first_token.value.split('.')
        command = command_parts[0]
        subcommand = command_parts[1] if len(command_parts) > 1 else None
        
        # 解析选项和参数
        options = {}
        arguments = []
        flags = []
        i = 1
        
        while i < len(tokens):
            token = tokens[i]
            
            if token.type == TokenType.OPTION:
                option_name = self._normalize_option_name(token.value)
                option_value = True  # 默认布尔值选项
                
                # 检查是否有值
                if i + 1 < len(tokens):
                    next_token = tokens[i + 1]
                    if next_token.type in [TokenType.STRING, TokenType.NUMBER, 
                                         TokenType.IDENTIFIER, TokenType.BOOLEAN]:
                        option_value = self._parse_value(next_token.value, next_token.type)
                        i += 1
                
                options[option_name] = option_value
            
            elif token.type in [TokenType.STRING, TokenType.NUMBER, 
                              TokenType.BOOLEAN, TokenType.IDENTIFIER]:
                # 检查是否为标志（简单布尔标志）
                if token.value.startswith('-') and len(token.value) > 1:
                    flags.append(token.value)
                else:
                    arguments.append(self._parse_value(token.value, token.type))
            
            i += 1
        
        return ParsedCommand(
            command=command,
            subcommand=subcommand,
            options=options,
            arguments=arguments,
            flags=flags,
            raw_tokens=tokens
        )
    
    def _normalize_option_name(self, option: str) -> str:
        """标准化选项名"""
        # 移除选项前缀
        for prefix in ['--', '-', '/']:
            if option.startswith(prefix):
                option = option[len(prefix):]
                break
        
        # 应用别名
        if option in self._option_aliases:
            option = self._option_aliases[option]
        
        return option
    
    def _parse_value(self, value: str, token_type: TokenType) -> Any:
        """解析值"""
        if token_type == TokenType.NUMBER:
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    return value
        elif token_type == TokenType.BOOLEAN:
            return value.lower() in ['true', 'yes', 'on', '1']
        elif token_type == TokenType.STRING:
            return value.strip('"')
        else:
            return value
    
    def validate_command(self, parsed: ParsedCommand) -> Tuple[bool, List[str]]:
        """验证命令"""
        errors = []
        
        # 检查命令是否存在
        if parsed.command not in self._command_registry:
            errors.append(f"未知命令: {parsed.command}")
            return False, errors
        
        schema = self._command_registry[parsed.command]
        
        # 验证必需选项
        if 'required_options' in schema:
            for required_option in schema['required_options']:
                if required_option not in parsed.options:
                    errors.append(f"缺少必需选项: {required_option}")
        
        # 验证参数数量
        if 'max_arguments' in schema and len(parsed.arguments) > schema['max_arguments']:
            errors.append(f"参数过多: 最多允许 {schema['max_arguments']} 个参数")
        
        if 'min_arguments' in schema and len(parsed.arguments) < schema['min_arguments']:
            errors.append(f"参数不足: 至少需要 {schema['min_arguments']} 个参数")
        
        # 验证选项值
        if 'option_schemas' in schema:
            for option_name, option_schema in schema['option_schemas'].items():
                if option_name in parsed.options:
                    value = parsed.options[option_name]
                    
                    # 验证类型
                    if 'type' in option_schema:
                        expected_type = option_schema['type']
                        if not isinstance(value, expected_type):
                            errors.append(f"选项 {option_name} 类型错误: 期望 {expected_type.__name__}")
                    
                    # 验证范围
                    if 'choices' in option_schema:
                        if value not in option_schema['choices']:
                            errors.append(f"选项 {option_name} 值无效: {value} 不在允许的范围内")
        
        return len(errors) == 0, errors
    
    def autocomplete(self, partial_command: str, position: Optional[int] = None) -> List[str]:
        """自动补全"""
        suggestions = []
        
        # 按位置分割
        if position is None:
            position = len(partial_command)
        
        # 获取光标前的文本
        before_cursor = partial_command[:position]
        after_cursor = partial_command[position:]
        
        # 分析上下文
        tokens = self._tokenize(before_cursor)
        
        if not tokens:
            # 无令牌，显示所有命令
            suggestions.extend(self._command_registry.keys())
        else:
            last_token = tokens[-1]
            
            if last_token.type == TokenType.IDENTIFIER and last_token.position == position - len(last_token.value):
                # 正在输入命令或子命令
                partial = last_token.value
                
                # 查找匹配的命令
                for command in self._command_registry.keys():
                    if command.startswith(partial):
                        suggestions.append(command)
                    elif '.' in command:
                        parts = command.split('.')
                        if len(parts) > 1 and parts[0].startswith(partial):
                            suggestions.append(command)
        
        return suggestions


class CommandRegistry:
    """命令注册表"""
    
    def __init__(self):
        self._commands: Dict[str, Dict] = {}
        self._command_handlers: Dict[str, Callable] = {}
        self._init_default_commands()
    
    def _init_default_commands(self):
        """初始化默认命令"""
        # 基础命令
        self.register_command('help', {
            'description': '显示帮助信息',
            'options': {
                'command': {'type': str, 'required': False}
            }
        })
        
        self.register_command('version', {
            'description': '显示版本信息'
        })
        
        self.register_command('exit', {
            'description': '退出程序'
        })
        
        self.register_command('quit', {
            'description': '退出程序',
            'aliases': ['q']
        })
    
    def register_command(self, name: str, schema: Dict[str, Any]):
        """注册命令"""
        self._commands[name] = schema
        
        # 添加别名支持
        if 'aliases' in schema:
            for alias in schema['aliases']:
                self._commands[alias] = schema.copy()
                self._commands[alias]['alias_of'] = name
    
    def register_handler(self, name: str, handler: Callable):
        """注册命令处理器"""
        self._command_handlers[name] = handler
    
    def get_commands(self) -> Dict[str, Dict]:
        """获取所有命令"""
        return self._commands.copy()
    
    def get_command_schema(self, name: str) -> Optional[Dict]:
        """获取命令模式"""
        return self._commands.get(name)
    
    def has_command(self, name: str) -> bool:
        """检查命令是否存在"""
        return name in self._commands


def create_parser() -> AdvancedCommandParser:
    """创建命令解析器实例"""
    return AdvancedCommandParser()


def create_registry() -> CommandRegistry:
    """创建命令注册表实例"""
    return CommandRegistry()


# 预定义的命令模式
COMMAND_SCHEMAS = {
    'config.get': {
        'description': '获取配置值',
        'arguments': [
            {'name': 'key', 'type': str, 'required': True, 'description': '配置键'}
        ],
        'options': {
            'profile': {'type': str, 'required': False, 'description': '配置档案'},
            'format': {'type': str, 'choices': ['json', 'yaml', 'table'], 'default': 'table'}
        }
    },
    
    'config.set': {
        'description': '设置配置值',
        'arguments': [
            {'name': 'key', 'type': str, 'required': True, 'description': '配置键'},
            {'name': 'value', 'type': str, 'required': True, 'description': '配置值'}
        ],
        'options': {
            'profile': {'type': str, 'required': False, 'description': '配置档案'},
            'encrypt': {'type': bool, 'default': False, 'description': '是否加密'}
        }
    },
    
    'browser.start': {
        'description': '启动浏览器',
        'options': {
            'headless': {'type': bool, 'default': False, 'description': '无头模式'},
            'profile': {'type': str, 'required': False, 'description': '浏览器档案'},
            'proxy': {'type': str, 'required': False, 'description': '代理设置'}
        }
    },
    
    'browser.stop': {
        'description': '停止浏览器'
    },
    
    'browser.status': {
        'description': '查看浏览器状态'
    },
    
    'channel.list': {
        'description': '列出渠道',
        'options': {
            'status': {'type': str, 'choices': ['active', 'inactive', 'error'], 'required': False},
            'format': {'type': str, 'choices': ['table', 'json'], 'default': 'table'}
        }
    },
    
    'channel.start': {
        'description': '启动渠道',
        'arguments': [
            {'name': 'channel_id', 'type': str, 'required': True, 'description': '渠道ID'}
        ]
    },
    
    'scheduler.add': {
        'description': '添加定时任务',
        'arguments': [
            {'name': 'name', 'type': str, 'required': True, 'description': '任务名称'},
            {'name': 'cron', 'type': str, 'required': True, 'description': 'Cron表达式'}
        ],
        'options': {
            'description': {'type': str, 'required': False, 'description': '任务描述'},
            'command': {'type': str, 'required': True, 'description': '要执行的命令'}
        }
    },
    
    'scheduler.list': {
        'description': '列出定时任务',
        'options': {
            'status': {'type': str, 'choices': ['active', 'inactive', 'completed', 'failed'], 'required': False}
        }
    }
}