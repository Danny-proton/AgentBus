"""
Gateway Protocol Handler

基于Moltbot的协议系统，处理客户端-服务器通信协议
"""

import json
import time
import uuid
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型"""
    REQUEST = "req"
    RESPONSE = "res"
    EVENT = "event"


class EventType(Enum):
    """事件类型"""
    CONNECT_CHALLENGE = "connect.challenge"
    CONNECT_OK = "connect.ok"
    CHAT_MESSAGE = "chat.message"
    CHAT_ERROR = "chat.error"
    SESSION_UPDATE = "session.update"
    PRESENCE_UPDATE = "presence.update"
    HEARTBEAT = "heartbeat"
    SHUTDOWN = "shutdown"


class ErrorCode(Enum):
    """错误代码"""
    INVALID_REQUEST = 4000
    UNAUTHORIZED = 4001
    FORBIDDEN = 4003
    NOT_FOUND = 4004
    TIMEOUT = 4008
    CONFLICT = 4009
    INTERNAL_ERROR = 5000
    SERVICE_UNAVAILABLE = 5003


@dataclass
class RequestFrame:
    """请求帧"""
    type: MessageType = MessageType.REQUEST
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ResponseFrame:
    """响应帧"""
    type: MessageType = MessageType.RESPONSE
    id: str = ""
    ok: bool = True
    payload: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class EventFrame:
    """事件帧"""
    type: MessageType = MessageType.EVENT
    event: str = ""
    payload: Optional[Dict[str, Any]] = None
    seq: Optional[int] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class HelloParams:
    """连接参数"""
    client_id: str
    client_name: str
    version: str = "1.0.0"
    platform: str = "python"
    capabilities: List[str] = field(default_factory=list)
    auth_token: Optional[str] = None
    device_id: Optional[str] = None


@dataclass
class HelloOk:
    """连接成功响应"""
    server_info: Dict[str, Any]
    capabilities: List[str]
    policy: Dict[str, Any]
    auth_info: Optional[Dict[str, Any]] = None


@dataclass
class ChatMessage:
    """聊天消息"""
    session_id: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = "user"  # user, assistant, system
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    """聊天响应"""
    session_id: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "started"  # started, streaming, completed, error
    message: Optional[ChatMessage] = None
    error: Optional[str] = None


class ProtocolError(Exception):
    """协议错误"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"Protocol Error {code.value}: {message}")


class MessageHandler(ABC):
    """消息处理器抽象基类"""
    
    @abstractmethod
    async def handle_request(self, frame: RequestFrame) -> ResponseFrame:
        """处理请求"""
        pass
    
    @abstractmethod
    async def handle_event(self, frame: EventFrame) -> Optional[EventFrame]:
        """处理事件"""
        pass


class ProtocolHandler:
    """协议处理器"""
    
    def __init__(self):
        self.handlers: Dict[str, MessageHandler] = {}
        self.request_callbacks: Dict[str, Callable] = {}
        self.event_subscribers: Dict[str, List[Callable]] = {}
        self.message_seq = 0
        
    def register_handler(self, method: str, handler: MessageHandler):
        """注册处理器"""
        self.handlers[method] = handler
        logger.info(f"Registered handler for method: {method}")
    
    def register_request_callback(self, request_id: str, callback: Callable):
        """注册请求回调"""
        self.request_callbacks[request_id] = callback
    
    def subscribe_event(self, event_type: str, callback: Callable):
        """订阅事件"""
        if event_type not in self.event_subscribers:
            self.event_subscribers[event_type] = []
        self.event_subscribers[event_type].append(callback)
    
    def create_request(self, method: str, params: Optional[Dict] = None) -> RequestFrame:
        """创建请求帧"""
        return RequestFrame(
            method=method,
            params=params
        )
    
    def create_response(self, request_id: str, ok: bool = True, 
                       payload: Optional[Dict] = None, 
                       error: Optional[Dict] = None) -> ResponseFrame:
        """创建响应帧"""
        return ResponseFrame(
            id=request_id,
            ok=ok,
            payload=payload,
            error=error
        )
    
    def create_event(self, event_type: str, payload: Optional[Dict] = None, 
                    seq: Optional[int] = None) -> EventFrame:
        """创建事件帧"""
        if seq is None:
            self.message_seq += 1
            seq = self.message_seq
            
        return EventFrame(
            event=event_type,
            payload=payload,
            seq=seq
        )
    
    def create_error_response(self, request_id: str, code: ErrorCode, 
                            message: str, details: Optional[Dict] = None) -> ResponseFrame:
        """创建错误响应"""
        error = {
            "code": code.value,
            "message": message,
            "details": details or {}
        }
        return self.create_response(request_id, ok=False, error=error)
    
    async def handle_message(self, message: Union[RequestFrame, EventFrame]) -> Optional[Union[ResponseFrame, EventFrame]]:
        """处理消息"""
        try:
            if isinstance(message, RequestFrame):
                return await self._handle_request(message)
            elif isinstance(message, EventFrame):
                return await self._handle_event(message)
            else:
                raise ProtocolError(ErrorCode.INVALID_REQUEST, f"Unknown message type: {type(message)}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            if isinstance(message, RequestFrame):
                return self.create_error_response(
                    message.id, 
                    ErrorCode.INTERNAL_ERROR, 
                    f"Internal error: {str(e)}"
                )
            return None
    
    async def _handle_request(self, request: RequestFrame) -> ResponseFrame:
        """处理请求"""
        handler = self.handlers.get(request.method)
        if not handler:
            return self.create_error_response(
                request.id,
                ErrorCode.NOT_FOUND,
                f"Method not found: {request.method}"
            )
        
        try:
            return await handler.handle_request(request)
        except Exception as e:
            logger.error(f"Handler error for {request.method}: {e}")
            return self.create_error_response(
                request.id,
                ErrorCode.INTERNAL_ERROR,
                f"Handler error: {str(e)}"
            )
    
    async def _handle_event(self, event: EventFrame) -> Optional[EventFrame]:
        """处理事件"""
        # 通知订阅者
        subscribers = self.event_subscribers.get(event.event, [])
        for callback in subscribers:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Event subscriber error: {e}")
        
        # 通知处理器
        handler = self.handlers.get(event.event)
        if handler:
            try:
                return await handler.handle_event(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
        
        return None
    
    def broadcast_event(self, event_type: str, payload: Optional[Dict] = None):
        """广播事件"""
        event = self.create_event(event_type, payload)
        # 这里应该实际发送到所有连接的客户端
        logger.info(f"Broadcasting event: {event_type}")
    
    def validate_frame(self, data: Dict[str, Any]) -> Optional[Union[RequestFrame, EventFrame]]:
        """验证和解析帧数据"""
        try:
            msg_type = data.get("type")
            
            if msg_type == MessageType.REQUEST.value:
                return RequestFrame(**data)
            elif msg_type == MessageType.EVENT.value:
                return EventFrame(**data)
            elif msg_type == MessageType.RESPONSE.value:
                return ResponseFrame(**data)
            else:
                return None
        except Exception as e:
            logger.error(f"Frame validation error: {e}")
            return None
    
    def serialize_frame(self, frame: Union[RequestFrame, ResponseFrame, EventFrame]) -> str:
        """序列化帧为JSON字符串"""
        return json.dumps(frame.__dict__, default=str)
    
    def deserialize_frame(self, data: str) -> Optional[Union[RequestFrame, ResponseFrame, EventFrame]]:
        """从JSON反序列化帧"""
        try:
            parsed = json.loads(data)
            return self.validate_frame(parsed)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None


class BaseHandler(MessageHandler):
    """基础处理器"""
    
    def __init__(self, protocol_handler: ProtocolHandler):
        self.protocol_handler = protocol_handler
    
    async def handle_request(self, frame: RequestFrame) -> ResponseFrame:
        """默认请求处理"""
        return self.protocol_handler.create_error_response(
            frame.id,
            ErrorCode.NOT_IMPLEMENTED,
            f"Handler not implemented for method: {frame.method}"
        )
    
    async def handle_event(self, frame: EventFrame) -> Optional[EventFrame]:
        """默认事件处理"""
        return None


class ChatHandler(BaseHandler):
    """聊天处理器"""
    
    async def handle_request(self, frame: RequestFrame) -> ResponseFrame:
        """处理聊天请求"""
        if frame.method == "chat.send":
            return await self._handle_chat_send(frame)
        elif frame.method == "chat.history":
            return await self._handle_chat_history(frame)
        elif frame.method == "chat.abort":
            return await self._handle_chat_abort(frame)
        else:
            return await super().handle_request(frame)
    
    async def _handle_chat_send(self, frame: RequestFrame) -> ResponseFrame:
        """处理聊天发送"""
        params = frame.params or {}
        session_id = params.get("session_id")
        message = params.get("message", "")
        
        if not session_id or not message:
            return self.protocol_handler.create_error_response(
                frame.id,
                ErrorCode.INVALID_REQUEST,
                "Session ID and message are required"
            )
        
        # 创建聊天响应
        chat_response = ChatResponse(
            session_id=session_id,
            status="started"
        )
        
        return self.protocol_handler.create_response(
            frame.id,
            payload={
                "run_id": chat_response.run_id,
                "status": chat_response.status
            }
        )
    
    async def _handle_chat_history(self, frame: RequestFrame) -> ResponseFrame:
        """处理聊天历史"""
        params = frame.params or {}
        session_id = params.get("session_id")
        
        if not session_id:
            return self.protocol_handler.create_error_response(
                frame.id,
                ErrorCode.INVALID_REQUEST,
                "Session ID is required"
            )
        
        # 返回空历史记录
        return self.protocol_handler.create_response(
            frame.id,
            payload={
                "session_id": session_id,
                "messages": []
            }
        )
    
    async def _handle_chat_abort(self, frame: RequestFrame) -> ResponseFrame:
        """处理聊天中止"""
        params = frame.params or {}
        run_id = params.get("run_id")
        
        return self.protocol_handler.create_response(
            frame.id,
            payload={
                "run_id": run_id,
                "status": "aborted"
            }
        )


class SystemHandler(BaseHandler):
    """系统处理器"""
    
    async def handle_request(self, frame: RequestFrame) -> ResponseFrame:
        """处理系统请求"""
        if frame.method == "system.info":
            return await self._handle_system_info(frame)
        elif frame.method == "system.status":
            return await self._handle_system_status(frame)
        else:
            return await super().handle_request(frame)
    
    async def _handle_system_info(self, frame: RequestFrame) -> ResponseFrame:
        """处理系统信息"""
        return self.protocol_handler.create_response(
            frame.id,
            payload={
                "name": "Agentbus Gateway",
                "version": "1.0.0",
                "protocol_version": "1.0",
                "capabilities": [
                    "chat",
                    "sessions", 
                    "presence",
                    "heartbeat"
                ]
            }
        )
    
    async def _handle_system_status(self, frame: RequestFrame) -> ResponseFrame:
        """处理系统状态"""
        return self.protocol_handler.create_response(
            frame.id,
            payload={
                "status": "healthy",
                "uptime": time.time(),
                "connections": 0,
                "memory_usage": "0MB"
            }
        )