"""
消息通道 (Message Channel) 服务
Message Channel service for AgentBus

本模块实现统一的消息通道系统，支持HITL消息与普通消息的融合，
提供跨平台的消息发送和接收功能。
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from loguru import logger

from ..core.settings import settings


class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    VIDEO = "video"
    HITL_REQUEST = "hitl_request"
    HITL_RESPONSE = "hitl_response"
    HITL_NOTIFICATION = "hitl_notification"
    SYSTEM = "system"
    BROADCAST = "broadcast"


class MessagePriority(Enum):
    """消息优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Message:
    """消息数据结构"""
    id: str
    type: MessageType
    content: str
    sender_id: str
    sender_type: str  # "agent", "user", "system", "hitl"
    recipients: List[str]
    timestamp: datetime
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: Dict[str, Any] = None
    attachments: List[Dict[str, Any]] = None
    thread_id: Optional[str] = None
    reply_to: Optional[str] = None
    is_hitl: bool = False
    hitl_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.attachments is None:
            self.attachments = []
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MessageHandler(ABC):
    """消息处理器抽象基类"""
    
    @abstractmethod
    async def send_message(self, message: Message) -> bool:
        """发送消息"""
        pass
    
    @abstractmethod
    async def get_message_history(self, user_id: str, limit: int = 50) -> List[Message]:
        """获取消息历史"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化处理器"""
        pass
    
    @abstractmethod
    async def close(self):
        """关闭处理器"""
        pass


class WebMessageHandler(MessageHandler):
    """Web界面消息处理器"""
    
    def __init__(self):
        self.connected_clients: Dict[str, asyncio.Queue] = {}
        self.message_history: List[Message] = []
    
    async def send_message(self, message: Message) -> bool:
        """发送消息到Web客户端"""
        try:
            # 存储到历史记录
            self.message_history.append(message)
            
            # 发送给特定客户端
            for recipient in message.recipients:
                if recipient in self.connected_clients:
                    await self.connected_clients[recipient].put(message)
            
            # 广播消息
            if MessageType.BROADCAST in message.type:
                for queue in self.connected_clients.values():
                    await queue.put(message)
            
            logger.debug(f"Web消息发送成功: {message.id}")
            return True
            
        except Exception as e:
            logger.error(f"Web消息发送失败: {e}")
            return False
    
    async def get_message_history(self, user_id: str, limit: int = 50) -> List[Message]:
        """获取指定用户的消息历史"""
        user_messages = [
            msg for msg in self.message_history
            if user_id in msg.recipients or msg.sender_id == user_id
        ]
        return user_messages[-limit:]
    
    async def register_client(self, client_id: str) -> asyncio.Queue:
        """注册Web客户端"""
        queue = asyncio.Queue()
        self.connected_clients[client_id] = queue
        logger.info(f"Web客户端已注册: {client_id}")
        return queue
    
    async def unregister_client(self, client_id: str):
        """注销Web客户端"""
        if client_id in self.connected_clients:
            del self.connected_clients[client_id]
            logger.info(f"Web客户端已注销: {client_id}")
    
    async def initialize(self) -> bool:
        """初始化Web处理器"""
        logger.info("Web消息处理器初始化完成")
        return True
    
    async def close(self):
        """关闭Web处理器"""
        self.connected_clients.clear()
        self.message_history.clear()
        logger.info("Web消息处理器已关闭")


class TerminalMessageHandler(MessageHandler):
    """终端消息处理器"""
    
    def __init__(self):
        self.terminal_users: Dict[str, asyncio.Queue] = {}
        self.message_history: List[Message] = []
    
    async def send_message(self, message: Message) -> bool:
        """发送消息到终端用户"""
        try:
            # 存储到历史记录
            self.message_history.append(message)
            
            # 如果是HITL消息，添加特殊标记
            if message.is_hitl:
                hitl_indicator = "🚨 [HITL] "
                prefixed_content = hitl_indicator + message.content
            else:
                prefixed_content = message.content
            
            # 输出到终端
            timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {message.sender_id}: {prefixed_content}")
            
            # 发送给特定用户
            for recipient in message.recipients:
                if recipient in self.terminal_users:
                    await self.terminal_users[recipient].put(message)
            
            logger.debug(f"终端消息发送成功: {message.id}")
            return True
            
        except Exception as e:
            logger.error(f"终端消息发送失败: {e}")
            return False
    
    async def get_message_history(self, user_id: str, limit: int = 50) -> List[Message]:
        """获取指定用户的消息历史"""
        user_messages = [
            msg for msg in self.message_history
            if user_id in msg.recipients or msg.sender_id == user_id
        ]
        return user_messages[-limit:]
    
    async def register_terminal_user(self, user_id: str) -> asyncio.Queue:
        """注册终端用户"""
        queue = asyncio.Queue()
        self.terminal_users[user_id] = queue
        logger.info(f"终端用户已注册: {user_id}")
        return queue
    
    async def unregister_terminal_user(self, user_id: str):
        """注销终端用户"""
        if user_id in self.terminal_users:
            del self.terminal_users[user_id]
            logger.info(f"终端用户已注销: {user_id}")
    
    async def initialize(self) -> bool:
        """初始化终端处理器"""
        logger.info("终端消息处理器初始化完成")
        return True
    
    async def close(self):
        """关闭终端处理器"""
        self.terminal_users.clear()
        self.message_history.clear()
        logger.info("终端消息处理器已关闭")


class MessageChannel:
    """统一消息通道服务"""
    
    def __init__(self):
        self.handlers: Dict[str, MessageHandler] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_queue = asyncio.Queue()
        self.is_running = False
        
        # 注册默认处理器
        self._register_default_handlers()
        
        logger.info("消息通道初始化完成")
    
    def _register_default_handlers(self):
        """注册默认消息处理器"""
        self.handlers["web"] = WebMessageHandler()
        self.handlers["terminal"] = TerminalMessageHandler()
    
    async def initialize(self):
        """初始化消息通道"""
        try:
            # 初始化所有处理器
            for name, handler in self.handlers.items():
                success = await handler.initialize()
                if not success:
                    logger.warning(f"消息处理器初始化失败: {name}")
            
            # 启动消息处理循环
            self.is_running = True
            asyncio.create_task(self._message_processing_loop())
            
            logger.info("消息通道初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"消息通道初始化失败: {e}")
            return False
    
    async def close(self):
        """关闭消息通道"""
        self.is_running = False
        
        # 关闭所有处理器
        for handler in self.handlers.values():
            await handler.close()
        
        logger.info("消息通道已关闭")
    
    async def send_message(
        self,
        sender_id: str,
        sender_type: str,
        content: str,
        recipients: List[str],
        message_type: MessageType = MessageType.TEXT,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Dict[str, Any] = None,
        attachments: List[Dict[str, Any]] = None,
        thread_id: str = None,
        reply_to: str = None,
        is_hitl: bool = False,
        hitl_data: Dict[str, Any] = None
    ) -> str:
        """发送消息"""
        
        import uuid
        message_id = str(uuid.uuid4())
        
        message = Message(
            id=message_id,
            type=message_type,
            content=content,
            sender_id=sender_id,
            sender_type=sender_type,
            recipients=recipients,
            timestamp=datetime.now(),
            priority=priority,
            metadata=metadata or {},
            attachments=attachments or [],
            thread_id=thread_id,
            reply_to=reply_to,
            is_hitl=is_hitl,
            hitl_data=hitl_data
        )
        
        # 添加到队列
        await self.message_queue.put(message)
        
        logger.info(f"消息已创建: {message_id} (HITL: {is_hitl})")
        return message_id
    
    async def broadcast_message(
        self,
        message_type: str,
        content: Any,
        recipients: List[str] = None,
        priority: str = "normal"
    ) -> str:
        """广播消息"""
        
        if recipients is None:
            recipients = ["*"]  # 广播给所有用户
        
        return await self.send_message(
            sender_id="system",
            sender_type="system",
            content=json.dumps(content, ensure_ascii=False),
            recipients=recipients,
            message_type=MessageType.BROADCAST,
            priority=MessagePriority(priority)
        )
    
    async def send_message_to_agent(
        self,
        agent_id: str,
        message_type: str,
        content: Any,
        priority: str = "normal"
    ) -> str:
        """发送消息给特定智能体"""
        
        return await self.send_message(
            sender_id="hitl_system",
            sender_type="system",
            content=json.dumps(content, ensure_ascii=False),
            recipients=[agent_id],
            message_type=MessageType(message_type),
            priority=MessagePriority(priority),
            is_hitl=True,
            hitl_data={"message_type": message_type}
        )
    
    async def send_hitl_request(
        self,
        request_id: str,
        agent_id: str,
        title: str,
        description: str,
        recipients: List[str],
        priority: str = "medium"
    ) -> str:
        """发送HITL请求"""
        
        hitl_content = {
            "request_id": request_id,
            "title": title,
            "description": description,
            "type": "hitl_request"
        }
        
        return await self.send_message(
            sender_id=agent_id,
            sender_type="agent",
            content=json.dumps(hitl_content, ensure_ascii=False),
            recipients=recipients,
            message_type=MessageType.HITL_REQUEST,
            priority=MessagePriority(priority),
            is_hitl=True,
            hitl_data={
                "request_id": request_id,
                "title": title,
                "is_hitl_request": True
            }
        )
    
    async def send_hitl_response(
        self,
        request_id: str,
        responder_id: str,
        content: str,
        recipients: List[str],
        is_final: bool = True
    ) -> str:
        """发送HITL响应"""
        
        hitl_content = {
            "request_id": request_id,
            "responder_id": responder_id,
            "content": content,
            "is_final": is_final,
            "type": "hitl_response"
        }
        
        return await self.send_message(
            sender_id=responder_id,
            sender_type="user",
            content=content,
            recipients=recipients,
            message_type=MessageType.HITL_RESPONSE,
            priority=MessagePriority.HIGH,
            is_hitl=True,
            hitl_data={
                "request_id": request_id,
                "responder_id": responder_id,
                "is_hitl_response": True
            }
        )
    
    async def subscribe(self, event_type: str, callback: Callable):
        """订阅消息事件"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    async def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        if event_type in self.subscribers:
            if callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)
    
    async def _message_processing_loop(self):
        """消息处理循环"""
        while self.is_running:
            try:
                # 从队列获取消息
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                
                # 发送给所有处理器
                for handler in self.handlers.values():
                    await handler.send_message(message)
                
                # 通知订阅者
                await self._notify_subscribers(message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"消息处理错误: {e}")
    
    async def _notify_subscribers(self, message: Message):
        """通知订阅者"""
        event_type = f"{message.sender_type}.{message.type.value}"
        
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"订阅者回调错误: {e}")
    
    async def get_message_history(
        self, 
        user_id: str, 
        handler_name: str = None,
        limit: int = 50
    ) -> List[Message]:
        """获取消息历史"""
        
        if handler_name and handler_name in self.handlers:
            return await self.handlers[handler_name].get_message_history(user_id, limit)
        
        # 合并所有处理器的历史记录
        all_messages = []
        for handler in self.handlers.values():
            messages = await handler.get_message_history(user_id, limit)
            all_messages.extend(messages)
        
        # 按时间排序
        all_messages.sort(key=lambda x: x.timestamp, reverse=True)
        return all_messages[:limit]
    
    async def register_client(self, platform: str, client_id: str):
        """注册客户端"""
        if platform == "web":
            return await self.handlers["web"].register_client(client_id)
        elif platform == "terminal":
            return await self.handlers["terminal"].register_terminal_user(client_id)
        else:
            logger.warning(f"不支持的平台: {platform}")
            return None
    
    async def unregister_client(self, platform: str, client_id: str):
        """注销客户端"""
        if platform == "web":
            await self.handlers["web"].unregister_client(client_id)
        elif platform == "terminal":
            await self.handlers["terminal"].unregister_terminal_user(client_id)
        else:
            logger.warning(f"不支持的平台: {platform}")
