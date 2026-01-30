"""
命令分发系统

负责将接收到的消息分发到相应的处理器：
- 入站消息分发
- 回复调度器
- 分发结果处理
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable, List, Union
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class DispatchStatus(Enum):
    """分发状态"""
    SUCCESS = "success"
    FAILED = "failed"
    IGNORED = "ignored"
    NOT_FOUND = "not_found"


@dataclass
class DispatchResult:
    """分发结果"""
    status: DispatchStatus
    command_key: Optional[str] = None
    args: Optional[str] = None
    response: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DispatchContext:
    """分发上下文"""
    message_id: str
    sender_id: str
    chat_id: str
    chat_type: str  # "private", "group", "channel"
    text: Optional[str] = None
    media_paths: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None
    media_types: Optional[List[str]] = None
    timestamp: float = field(default_factory=asyncio.get_event_loop().time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReplyDispatcher:
    """回复调度器基类"""
    
    def __init__(self):
        self.pending_replies: Dict[str, asyncio.Future] = {}
    
    async def send_reply(self, chat_id: str, text: str, **kwargs) -> str:
        """发送回复"""
        raise NotImplementedError("子类必须实现send_reply方法")
    
    async def wait_for_reply(self, message_id: str, timeout: float = 30.0) -> str:
        """等待回复"""
        if message_id not in self.pending_replies:
            future = asyncio.Future()
            self.pending_replies[message_id] = future
        
        try:
            return await asyncio.wait_for(self.pending_replies[message_id], timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"等待回复超时: {message_id}")
            raise
        finally:
            self.pending_replies.pop(message_id, None)
    
    def resolve_reply(self, message_id: str, response: str):
        """解析回复"""
        if message_id in self.pending_replies:
            future = self.pending_replies[message_id]
            future.set_result(response)
    
    def reject_reply(self, message_id: str, error: str):
        """拒绝回复"""
        if message_id in self.pending_replies:
            future = self.pending_replies[message_id]
            future.set_exception(Exception(error))


class TypingDispatcher(ReplyDispatcher):
    """带输入指示的调度器"""
    
    def __init__(self, base_dispatcher: ReplyDispatcher, typing_interval: float = 2.0):
        super().__init__()
        self.base_dispatcher = base_dispatcher
        self.typing_interval = typing_interval
        self.active_typing_chats: set = set()
    
    async def start_typing(self, chat_id: str):
        """开始输入指示"""
        self.active_typing_chats.add(chat_id)
        # 这里应该调用实际的输入指示API
        logger.debug(f"开始输入指示: {chat_id}")
    
    def stop_typing(self, chat_id: str):
        """停止输入指示"""
        self.active_typing_chats.discard(chat_id)
        logger.debug(f"停止输入指示: {chat_id}")
    
    async def send_reply(self, chat_id: str, text: str, **kwargs) -> str:
        """发送带输入指示的回复"""
        if chat_id in self.active_typing_chats:
            self.stop_typing(chat_id)
        
        return await self.base_dispatcher.send_reply(chat_id, text, **kwargs)


class CommandHandler:
    """命令处理器"""
    
    def __init__(self):
        self.handlers: Dict[str, Callable] = {}
    
    def register_handler(self, command_key: str, handler: Callable):
        """注册命令处理器"""
        self.handlers[command_key] = handler
    
    def unregister_handler(self, command_key: str):
        """注销命令处理器"""
        self.handlers.pop(command_key, None)
    
    async def handle_command(
        self,
        command_key: str,
        args: Optional[str],
        context: DispatchContext,
        dispatcher: ReplyDispatcher,
    ) -> str:
        """处理命令"""
        if command_key not in self.handlers:
            raise ValueError(f"未找到命令处理器: {command_key}")
        
        handler = self.handlers[command_key]
        
        try:
            if asyncio.iscoroutinefunction(handler):
                return await handler(args, context, dispatcher)
            else:
                return handler(args, context, dispatcher)
        except Exception as e:
            logger.error(f"命令处理器错误 {command_key}: {e}")
            raise


# 内置命令处理器
async def _handle_status(args: Optional[str], context: DispatchContext, dispatcher: ReplyDispatcher) -> str:
    """处理状态命令"""
    return "🤖 Agentbus 机器人状态正常"


async def _handle_help(args: Optional[str], context: DispatchContext, dispatcher: ReplyDispatcher) -> str:
    """处理帮助命令"""
    help_text = """🤖 Agentbus 机器人帮助

可用命令：
• /status - 查看机器人状态
• /help - 显示此帮助信息
• /config <key> [value] - 配置管理
• /debug [on|off] - 切换调试模式
• /echo <message> - 回显消息
• /activation [mention|always] - 设置激活模式

发送 /help <command> 查看具体命令用法。"""
    return help_text


async def _handle_config(args: Optional[str], context: DispatchContext, dispatcher: ReplyDispatcher) -> str:
    """处理配置命令"""
    if not args:
        return "❌ 请提供配置键名。使用 /help config 查看用法。"
    
    parts = args.split(None, 1)
    key = parts[0]
    value = parts[1] if len(parts) > 1 else None
    
    # 这里应该实现实际的配置管理逻辑
    if value is None:
        return f"🔧 当前 {key} 配置值"
    else:
        return f"✅ 已设置 {key} = {value}"


async def _handle_debug(args: Optional[str], context: DispatchContext, dispatcher: ReplyDispatcher) -> str:
    """处理调试命令"""
    if not args:
        return "🔧 当前调试模式状态"
    
    mode = args.strip().lower()
    if mode in ["on", "true", "1"]:
        return "✅ 调试模式已启用"
    elif mode in ["off", "false", "0"]:
        return "❌ 调试模式已禁用"
    else:
        return "❌ 无效的调试模式值，请使用 on/off"


async def _handle_echo(args: Optional[str], context: DispatchContext, dispatcher: ReplyDispatcher) -> str:
    """处理回显命令"""
    if not args:
        return "❌ 请提供要回显的消息"
    return args


async def _handle_activation(args: Optional[str], context: DispatchContext, dispatcher: ReplyDispatcher) -> str:
    """处理激活命令"""
    if not args:
        return "🔧 当前群组激活模式"
    
    mode = args.strip().lower()
    if mode in ["mention", "always"]:
        return f"✅ 群组激活模式已设置为: {mode}"
    else:
        return "❌ 无效的激活模式，请使用 mention/always"


class Dispatcher:
    """主分发器"""
    
    def __init__(self):
        self.command_handler = CommandHandler()
        self._register_builtin_handlers()
    
    def _register_builtin_handlers(self):
        """注册内置命令处理器"""
        self.command_handler.register_handler("status", _handle_status)
        self.command_handler.register_handler("help", _handle_help)
        self.command_handler.register_handler("config", _handle_config)
        self.command_handler.register_handler("debug", _handle_debug)
        self.command_handler.register_handler("echo", _handle_echo)
        self.command_handler.register_handler("activation", _handle_activation)
    
    async def dispatch_command(
        self,
        command_key: str,
        args: Optional[str],
        context: DispatchContext,
        dispatcher: ReplyDispatcher,
    ) -> DispatchResult:
        """分发命令"""
        import time
        start_time = time.time()
        
        try:
            response = await self.command_handler.handle_command(
                command_key, args, context, dispatcher
            )
            execution_time = time.time() - start_time
            
            return DispatchResult(
                status=DispatchStatus.SUCCESS,
                command_key=command_key,
                args=args,
                response=response,
                execution_time=execution_time,
            )
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"命令分发错误 {command_key}: {e}")
            
            return DispatchResult(
                status=DispatchStatus.FAILED,
                command_key=command_key,
                args=args,
                error=str(e),
                execution_time=execution_time,
            )


# 全局分发器实例
_dispatcher = Dispatcher()


async def dispatch_inbound_message(
    ctx: DispatchContext,
    dispatcher: ReplyDispatcher,
) -> DispatchResult:
    """分发入站消息"""
    from .command_detection import resolve_text_command, has_control_command
    
    if not ctx.text:
        return DispatchResult(status=DispatchStatus.IGNORED)
    
    # 检查是否是控制命令
    if not has_control_command(ctx.text):
        return DispatchResult(status=DispatchStatus.IGNORED)
    
    # 解析命令
    result = resolve_text_command(ctx.text)
    if not result:
        return DispatchResult(status=DispatchStatus.NOT_FOUND)
    
    command, args = result
    
    # 分发命令
    return await _dispatcher.dispatch_command(command["key"], args, ctx, dispatcher)


async def dispatch_inbound_message_with_dispatcher(
    ctx: DispatchContext,
    dispatcher_options: Optional[Dict[str, Any]] = None,
) -> DispatchResult:
    """使用指定调度器分发入站消息"""
    # 创建调度器
    dispatcher = ReplyDispatcher()
    
    # 执行分发
    result = await dispatch_inbound_message(ctx, dispatcher)
    
    # 等待调度器空闲
    if hasattr(dispatcher, 'wait_for_idle'):
        await dispatcher.wait_for_idle()
    
    return result


async def dispatch_inbound_message_with_buffered_dispatcher(
    ctx: DispatchContext,
    typing_interval: float = 2.0,
) -> DispatchResult:
    """使用缓冲调度器分发入站消息"""
    base_dispatcher = ReplyDispatcher()
    dispatcher = TypingDispatcher(base_dispatcher, typing_interval)
    
    result = await dispatch_inbound_message(ctx, dispatcher)
    
    # 标记调度器空闲
    if hasattr(dispatcher, 'mark_idle'):
        dispatcher.mark_idle()
    
    return result