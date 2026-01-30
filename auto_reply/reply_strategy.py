"""
回复策略管理

管理自动回复的策略，包括：
- 回复模式定义
- 策略配置管理
- 回复时机控制
- 响应行为管理
"""

from typing import Optional, Dict, Any, List, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class ReplyStrategy(Enum):
    """回复策略"""
    ALWAYS = "always"           # 总是回复
    MENTION_ONLY = "mention_only"  # 仅@时回复
    COMMAND_ONLY = "command_only"  # 仅命令时回复
    SMARTR = "smart"           # 智能回复
    DISABLED = "disabled"      # 禁用


class ResponseMode(Enum):
    """响应模式"""
    IMMEDIATE = "immediate"     # 立即响应
    DELAYED = "delayed"        # 延迟响应
    SCHEDULED = "scheduled"    # 计划响应


class ThinkingMode(Enum):
    """思考模式"""
    NONE = "none"              # 无思考
    BASIC = "basic"            # 基本思考
    ADVANCED = "advanced"      # 高级思考
    VERBOSE = "verbose"        # 详细思考


@dataclass
class ReplyOptions:
    """回复选项"""
    strategy: ReplyStrategy = ReplyStrategy.SMARTR
    response_mode: ResponseMode = ResponseMode.IMMEDIATE
    thinking_mode: ThinkingMode = ThinkingMode.BASIC
    max_retries: int = 3
    timeout: float = 30.0
    include_thinking: bool = False
    stream_response: bool = False
    context_window: int = 4096
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyConfig:
    """策略配置"""
    name: str
    description: str
    enabled: bool = True
    conditions: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReplyStrategyManager:
    """回复策略管理器"""
    
    def __init__(self):
        self.strategies: Dict[str, StrategyConfig] = {}
        self.active_strategy: Optional[str] = "smart"
        self.reply_options: ReplyOptions = ReplyOptions()
        self.message_history: List[Dict[str, Any]] = []
        self.user_preferences: Dict[str, Dict[str, Any]] = {}
        self.group_settings: Dict[str, Dict[str, Any]] = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """注册默认策略"""
        default_strategies = [
            StrategyConfig(
                name="always",
                description="总是回复所有消息",
                conditions=["message_received"],
                actions=["process_message"]
            ),
            StrategyConfig(
                name="mention_only",
                description="仅在@提及时回复",
                conditions=["mention_detected"],
                actions=["process_message"]
            ),
            StrategyConfig(
                name="command_only",
                description="仅在收到命令时回复",
                conditions=["command_detected"],
                actions=["execute_command"]
            ),
            StrategyConfig(
                name="smartr",
                description="智能回复模式",
                conditions=["context_aware"],
                actions=["analyze_intent", "process_message"]
            ),
        ]
        
        for strategy in default_strategies:
            self.register_strategy(strategy)
    
    def register_strategy(self, strategy: StrategyConfig):
        """注册策略"""
        self.strategies[strategy.name] = strategy
        logger.info(f"已注册回复策略: {strategy.name}")
    
    def unregister_strategy(self, name: str):
        """注销策略"""
        if name in self.strategies:
            del self.strategies[name]
            logger.info(f"已注销回复策略: {name}")
    
    def set_active_strategy(self, name: str) -> bool:
        """设置活动策略"""
        if name in self.strategies:
            self.active_strategy = name
            logger.info(f"已设置活动策略: {name}")
            return True
        return False
    
    def get_active_strategy(self) -> Optional[StrategyConfig]:
        """获取活动策略"""
        if self.active_strategy and self.active_strategy in self.strategies:
            return self.strategies[self.active_strategy]
        return None
    
    def configure_reply_options(self, options: ReplyOptions):
        """配置回复选项"""
        self.reply_options = options
        logger.info("已更新回复选项配置")
    
    def should_respond(
        self,
        message_type: str,
        has_mention: bool = False,
        has_command: bool = False,
        chat_type: str = "private",
        sender_id: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        判断是否应该响应
        
        Args:
            message_type: 消息类型
            has_mention: 是否有@提及
            has_command: 是否有命令
            chat_type: 聊天类型
            sender_id: 发送者ID
            **kwargs: 其他参数
            
        Returns:
            是否应该响应
        """
        strategy = self.get_active_strategy()
        if not strategy or not strategy.enabled:
            return False
        
        # 根据消息类型和策略判断
        if message_type == "command":
            return has_command
        
        if message_type == "mention":
            return has_mention or chat_type == "private"
        
        if message_type == "text":
            if self.active_strategy == "always":
                return True
            elif self.active_strategy == "mention_only":
                return has_mention or chat_type == "private"
            elif self.active_strategy == "command_only":
                return has_command
            elif self.active_strategy == "smartr":
                # 智能模式：基于上下文和用户偏好
                return self._should_respond_smartr(has_mention, has_command, chat_type, sender_id, **kwargs)
        
        return False
    
    def _should_respond_smartr(
        self,
        has_mention: bool,
        has_command: bool,
        chat_type: str,
        sender_id: Optional[str],
        **kwargs
    ) -> bool:
        """智能模式的响应判断"""
        # 私聊总是响应
        if chat_type == "private":
            return True
        
        # 群聊中需要@提及
        if chat_type in ["group", "supergroup"]:
            if has_mention:
                return True
            
            # 检查用户偏好
            if sender_id and self._user_prefers_responses(sender_id):
                return True
        
        return False
    
    def _user_prefers_responses(self, sender_id: str) -> bool:
        """检查用户是否偏好响应"""
        user_prefs = self.user_preferences.get(sender_id, {})
        return user_prefs.get("prefers_responses", False)
    
    def set_user_preference(self, sender_id: str, preference: str, value: Any):
        """设置用户偏好"""
        if sender_id not in self.user_preferences:
            self.user_preferences[sender_id] = {}
        self.user_preferences[sender_id][preference] = value
        logger.info(f"已设置用户 {sender_id} 的偏好: {preference} = {value}")
    
    def configure_group_settings(self, chat_id: str, settings: Dict[str, Any]):
        """配置群组设置"""
        if chat_id not in self.group_settings:
            self.group_settings[chat_id] = {}
        self.group_settings[chat_id].update(settings)
        logger.info(f"已配置群组 {chat_id} 设置")
    
    def get_group_settings(self, chat_id: str) -> Dict[str, Any]:
        """获取群组设置"""
        return self.group_settings.get(chat_id, {})
    
    def add_message_to_history(self, message: Dict[str, Any]):
        """添加消息到历史"""
        self.message_history.append(message)
        
        # 限制历史长度
        max_history = 100
        if len(self.message_history) > max_history:
            self.message_history = self.message_history[-max_history:]
    
    def get_conversation_context(self, chat_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取对话上下文"""
        return [
            msg for msg in self.message_history[-limit:]
            if msg.get("chat_id") == chat_id
        ]
    
    def create_reply_context(
        self,
        message_id: str,
        sender_id: str,
        chat_id: str,
        chat_type: str,
        text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """创建回复上下文"""
        context = {
            "message_id": message_id,
            "sender_id": sender_id,
            "chat_id": chat_id,
            "chat_type": chat_type,
            "text": text,
            "timestamp": kwargs.get("timestamp"),
            "reply_options": self.reply_options,
            "group_settings": self.get_group_settings(chat_id),
            "conversation_context": self.get_conversation_context(chat_id),
            "user_preferences": self.user_preferences.get(sender_id, {}),
            "metadata": kwargs.get("metadata", {}),
        }
        
        # 添加到历史
        self.add_message_to_history({
            "message_id": message_id,
            "sender_id": sender_id,
            "chat_id": chat_id,
            "text": text,
            "timestamp": context["timestamp"],
        })
        
        return context


# 全局策略管理器实例
_strategy_manager = ReplyStrategyManager()


def get_reply_strategy_manager() -> ReplyStrategyManager:
    """获取回复策略管理器"""
    return _strategy_manager


def should_respond_to_message(
    message_type: str,
    has_mention: bool = False,
    has_command: bool = False,
    chat_type: str = "private",
    sender_id: Optional[str] = None,
    **kwargs
) -> bool:
    """
    快速判断是否应该响应消息
    
    Args:
        message_type: 消息类型
        has_mention: 是否有@提及
        has_command: 是否有命令
        chat_type: 聊天类型
        sender_id: 发送者ID
        **kwargs: 其他参数
        
    Returns:
        是否应该响应
    """
    return _strategy_manager.should_respond(
        message_type=message_type,
        has_mention=has_mention,
        has_command=has_command,
        chat_type=chat_type,
        sender_id=sender_id,
        **kwargs
    )


def create_reply_context(
    message_id: str,
    sender_id: str,
    chat_id: str,
    chat_type: str,
    text: str,
    **kwargs
) -> Dict[str, Any]:
    """
    创建回复上下文
    
    Args:
        message_id: 消息ID
        sender_id: 发送者ID
        chat_id: 聊天ID
        chat_type: 聊天类型
        text: 消息文本
        **kwargs: 其他参数
        
    Returns:
        回复上下文
    """
    return _strategy_manager.create_reply_context(
        message_id=message_id,
        sender_id=sender_id,
        chat_id=chat_id,
        chat_type=chat_type,
        text=text,
        **kwargs
    )


def configure_default_reply_strategy(strategy: ReplyStrategy = ReplyStrategy.SMARTR):
    """配置默认回复策略"""
    strategy_name = "smartr" if strategy == ReplyStrategy.SMARTR else strategy.value
    _strategy_manager.set_active_strategy(strategy_name)
    
    # 配置相应的回复选项
    options = ReplyOptions(strategy=strategy)
    _strategy_manager.configure_reply_options(options)