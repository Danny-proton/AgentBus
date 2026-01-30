"""
网关WebSocket服务
Gateway WebSocket Service

提供WebSocket连接管理和消息路由功能
"""

from typing import Dict, List, Optional, Set, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import asyncio
import json
import uuid
from contextlib import asynccontextmanager

import websockets
from websockets.exceptions import ConnectionClosed

# 处理WebSocket废弃警告
try:
    from websockets.server import WebSocketServerProtocol
except ImportError:
    # 新版本websockets中的废弃API
    WebSocketServerProtocol = websockets.WebSocketServerProtocol

from ..core.logger import get_logger
from ..core.config import settings
from ..adapters.base import Message, MessageType, AdapterType

logger = get_logger(__name__)


class ConnectionState(Enum):
    """连接状态枚举"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


class MessagePriority(Enum):
    """消息优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class WebSocketConnection:
    """WebSocket连接"""
    id: str
    websocket: WebSocketServerProtocol
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    client_info: Dict[str, Any] = field(default_factory=dict)
    state: ConnectionState = ConnectionState.CONNECTING
    connected_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    subscriptions: Set[str] = field(default_factory=set)  # 订阅的频道
    
    def update_activity(self) -> None:
        """更新最后活动时间"""
        self.last_activity = datetime.now()
    
    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return self.state == ConnectionState.AUTHENTICATED and self.user_id is not None


@dataclass
class GatewayMessage:
    """网关消息"""
    id: str
    type: str  # 消息类型：auth, subscribe, message, broadcast, error等
    data: Dict[str, Any]
    connection_id: Optional[str] = None
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    reply_to: Optional[str] = None
    
    @classmethod
    def create(cls, msg_type: str, data: Dict[str, Any], **kwargs) -> 'GatewayMessage':
        """创建消息"""
        return cls(
            id=str(uuid.uuid4()),
            type=msg_type,
            data=data,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "reply_to": self.reply_to
        }


class MessageRouter:
    """消息路由器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self._routes: Dict[str, List[Callable]] = {}
        self._message_handlers: Dict[str, Callable] = {}
    
    def register_route(self, channel: str, handler: Callable) -> None:
        """注册路由"""
        if channel not in self._routes:
            self._routes[channel] = []
        self._routes[channel].append(handler)
        self.logger.debug("Route registered", channel=channel)
    
    def register_message_handler(self, message_type: str, handler: Callable) -> None:
        """注册消息处理器"""
        self._message_handlers[message_type] = handler
        self.logger.debug("Message handler registered", message_type=message_type)
    
    async def route_message(self, message: GatewayMessage, connection: WebSocketConnection) -> None:
        """路由消息"""
        channel = message.data.get("channel")
        
        if channel and channel in self._routes:
            # 广播到订阅者
            await self._broadcast_to_channel(channel, message)
        elif message.type in self._message_handlers:
            # 处理特定消息类型
            handler = self._message_handlers[message.type]
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message, connection)
                else:
                    handler(message, connection)
            except Exception as e:
                self.logger.error("Message handler error", 
                               message_type=message.type,
                               error=str(e))
        else:
            self.logger.warning("Unknown message", message_type=message.type)
    
    async def _broadcast_to_channel(self, channel: str, message: GatewayMessage) -> None:
        """向频道广播消息"""
        if channel in self._routes:
            for handler in self._routes[channel]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception as e:
                    self.logger.error("Route handler error", 
                                    channel=channel,
                                    error=str(e))


class GatewayServer:
    """网关服务器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.connections: Dict[str, WebSocketConnection] = {}
        self.router = MessageRouter()
        self._server: Optional[websockets.WebSocketServer] = None
        self._shutdown_event = asyncio.Event()
        
        # 注册默认消息处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """注册默认消息处理器"""
        self.router.register_message_handler("auth", self._handle_auth)
        self.router.register_message_handler("subscribe", self._handle_subscribe)
        self.router.register_message_handler("unsubscribe", self._handle_unsubscribe)
        self.router.register_message_handler("ping", self._handle_ping)
        self.router.register_message_handler("message", self._handle_message)
        self.router.register_message_handler("broadcast", self._handle_broadcast)
    
    async def start(self, host: str = None, port: int = None) -> None:
        """启动网关服务器"""
        host = host or settings.web.host
        port = port or settings.web.websocket_port
        
        self.logger.info("Starting gateway server", host=host, port=port)
        
        self._server = await websockets.serve(
            self._handle_connection,
            host,
            port,
            max_size=2**20,  # 1MB max message size
            ping_interval=20,
            ping_timeout=10
        )
        
        self.logger.info("Gateway server started", address=f"{host}:{port}")
    
    async def stop(self) -> None:
        """停止网关服务器"""
        self.logger.info("Stopping gateway server...")
        
        self._shutdown_event.set()
        
        # 关闭所有连接
        for connection in list(self.connections.values()):
            await self._disconnect_client(connection)
        
        # 关闭服务器
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        
        self.logger.info("Gateway server stopped")
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """处理新的WebSocket连接"""
        connection_id = str(uuid.uuid4())
        connection = WebSocketConnection(
            id=connection_id,
            websocket=websocket
        )
        
        self.connections[connection_id] = connection
        self.logger.info("Client connected", 
                        connection_id=connection_id,
                        remote=websocket.remote_address)
        
        try:
            # 处理连接生命周期
            await self._handle_connection_lifecycle(connection)
            
        except Exception as e:
            self.logger.error("Connection handler error", 
                            connection_id=connection_id,
                            error=str(e))
        finally:
            await self._disconnect_client(connection)
    
    async def _handle_connection_lifecycle(self, connection: WebSocketConnection) -> None:
        """处理连接生命周期"""
        async for message in connection.websocket:
            try:
                # 解析消息
                parsed_message = self._parse_message(message)
                if not parsed_message:
                    continue
                
                # 更新连接活动时间
                connection.update_activity()
                
                # 路由消息
                await self.router.route_message(parsed_message, connection)
                
            except json.JSONDecodeError:
                await self._send_error(connection, "Invalid JSON", "parse_error")
            except Exception as e:
                self.logger.error("Message processing error", 
                               connection_id=connection.id,
                               error=str(e))
                await self._send_error(connection, "Internal error", "server_error")
    
    def _parse_message(self, raw_message: str) -> Optional[GatewayMessage]:
        """解析原始消息"""
        try:
            data = json.loads(raw_message)
            
            # 验证必需字段
            if "type" not in data:
                return None
            
            # 创建消息对象
            message = GatewayMessage(
                id=data.get("id", str(uuid.uuid4())),
                type=data["type"],
                data=data.get("data", {}),
                connection_id=data.get("connection_id"),
                priority=MessagePriority(data.get("priority", MessagePriority.NORMAL.value)),
                reply_to=data.get("reply_to")
            )
            
            return message
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error("Message parsing failed", error=str(e))
            return None
    
    async def _disconnect_client(self, connection: WebSocketConnection) -> None:
        """断开客户端连接"""
        if connection.id in self.connections:
            del self.connections[connection.id]
        
        try:
            await connection.websocket.close()
        except Exception:
            pass  # 连接可能已经关闭
        
        self.logger.info("Client disconnected", connection_id=connection.id)
    
    # === 消息处理器 ===
    
    async def _handle_auth(self, message: GatewayMessage, connection: WebSocketConnection) -> None:
        """处理认证消息"""
        auth_data = message.data
        
        # 验证认证信息
        user_id = auth_data.get("user_id")
        token = auth_data.get("token")
        
        if not user_id or not token:
            await self._send_error(connection, "Authentication failed", "auth_failed")
            return
        
        # 模拟认证验证（实际实现中需要验证JWT等）
        # 这里简化处理，仅检查token格式
        if len(token) < 10:
            await self._send_error(connection, "Invalid token", "auth_failed")
            return
        
        # 认证成功
        connection.user_id = user_id
        connection.state = ConnectionState.AUTHENTICATED
        connection.client_info = auth_data.get("client_info", {})
        
        self.logger.info("Client authenticated", 
                        connection_id=connection.id,
                        user_id=user_id)
        
        # 发送认证成功响应
        response = GatewayMessage.create(
            "auth_success",
            {"user_id": user_id, "connection_id": connection.id}
        )
        await self._send_message(connection, response)
    
    async def _handle_subscribe(self, message: GatewayMessage, connection: WebSocketConnection) -> None:
        """处理订阅消息"""
        if not connection.is_authenticated():
            await self._send_error(connection, "Authentication required", "auth_required")
            return
        
        channel = message.data.get("channel")
        if not channel:
            await self._send_error(connection, "Channel required", "invalid_request")
            return
        
        connection.subscriptions.add(channel)
        
        self.logger.debug("Client subscribed", 
                        connection_id=connection.id,
                        channel=channel)
        
        # 发送订阅确认
        response = GatewayMessage.create(
            "subscribed",
            {"channel": channel}
        )
        await self._send_message(connection, response)
    
    async def _handle_unsubscribe(self, message: GatewayMessage, connection: WebSocketConnection) -> None:
        """处理取消订阅消息"""
        channel = message.data.get("channel")
        if not channel:
            await self._send_error(connection, "Channel required", "invalid_request")
            return
        
        connection.subscriptions.discard(channel)
        
        self.logger.debug("Client unsubscribed", 
                        connection_id=connection.id,
                        channel=channel)
    
    async def _handle_ping(self, message: GatewayMessage, connection: WebSocketConnection) -> None:
        """处理ping消息"""
        response = GatewayMessage.create("pong", {"timestamp": datetime.now().isoformat()})
        await self._send_message(connection, response)
    
    async def _handle_message(self, message: GatewayMessage, connection: WebSocketConnection) -> None:
        """处理普通消息"""
        if not connection.is_authenticated():
            await self._send_error(connection, "Authentication required", "auth_required")
            return
        
        # 处理用户消息
        self.logger.info("User message", 
                        connection_id=connection.id,
                        user_id=connection.user_id,
                        message_type=message.data.get("type"))
        
        # 这里可以集成到消息路由系统
        # await self._route_to_adapters(message)
    
    async def _handle_broadcast(self, message: GatewayMessage, connection: WebSocketConnection) -> None:
        """处理广播消息"""
        if not connection.is_authenticated():
            await self._send_error(connection, "Authentication required", "auth_required")
            return
        
        # 检查管理员权限
        # 这里简化处理，实际实现中需要验证权限
        
        # 广播消息
        await self.broadcast_message(message.data)
    
    # === 消息发送方法 ===
    
    async def _send_message(self, connection: WebSocketConnection, message: GatewayMessage) -> bool:
        """发送消息到连接"""
        try:
            await connection.websocket.send(json.dumps(message.to_dict()))
            return True
        except ConnectionClosed:
            self.logger.warning("Failed to send message - connection closed", 
                              connection_id=connection.id)
            await self._disconnect_client(connection)
            return False
        except Exception as e:
            self.logger.error("Failed to send message", 
                            connection_id=connection.id,
                            error=str(e))
            return False
    
    async def _send_error(self, connection: WebSocketConnection, error_message: str, error_code: str) -> None:
        """发送错误消息"""
        error_msg = GatewayMessage.create(
            "error",
            {
                "message": error_message,
                "code": error_code
            }
        )
        await self._send_message(connection, error_msg)
    
    async def send_to_user(self, user_id: str, message: GatewayMessage) -> int:
        """发送消息给指定用户"""
        sent_count = 0
        
        for connection in self.connections.values():
            if connection.user_id == user_id and connection.is_authenticated():
                if await self._send_message(connection, message):
                    sent_count += 1
        
        self.logger.debug("Message sent to user", 
                        user_id=user_id,
                        connection_count=sent_count)
        
        return sent_count
    
    async def broadcast_to_channel(self, channel: str, message: GatewayMessage) -> int:
        """向频道广播消息"""
        sent_count = 0
        
        for connection in self.connections.values():
            if channel in connection.subscriptions and connection.is_authenticated():
                if await self._send_message(connection, message):
                    sent_count += 1
        
        self.logger.debug("Message broadcasted", 
                        channel=channel,
                        connection_count=sent_count)
        
        return sent_count
    
    async def broadcast_message(self, data: Dict[str, Any], exclude_connection: str = None) -> int:
        """广播消息给所有连接"""
        sent_count = 0
        message = GatewayMessage.create("broadcast", data)
        
        for connection_id, connection in self.connections.items():
            if connection_id != exclude_connection and connection.is_authenticated():
                if await self._send_message(connection, message):
                    sent_count += 1
        
        self.logger.debug("Message broadcasted", 
                        total_connections=sent_count,
                        exclude=exclude_connection)
        
        return sent_count
    
    async def send_system_message(self, data: Dict[str, Any]) -> None:
        """发送系统消息"""
        message = GatewayMessage.create("system", data)
        await self.broadcast_message(message.to_dict())
    
    # === 状态管理 ===
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接统计"""
        total_connections = len(self.connections)
        authenticated_connections = sum(1 for c in self.connections.values() if c.is_authenticated())
        
        # 按状态统计
        state_stats = {}
        for connection in self.connections.values():
            state = connection.state.value
            state_stats[state] = state_stats.get(state, 0) + 1
        
        # 按订阅统计
        subscription_stats = {}
        for connection in self.connections.values():
            for channel in connection.subscriptions:
                subscription_stats[channel] = subscription_stats.get(channel, 0) + 1
        
        return {
            "total_connections": total_connections,
            "authenticated_connections": authenticated_connections,
            "state_stats": state_stats,
            "subscription_stats": subscription_stats,
            "uptime": datetime.now().isoformat()
        }


# 全局网关服务器实例
_gateway_server: Optional[GatewayServer] = None


def get_gateway_server() -> GatewayServer:
    """获取全局网关服务器"""
    global _gateway_server
    if _gateway_server is None:
        _gateway_server = GatewayServer()
    return _gateway_server


async def start_gateway_server() -> None:
    """启动全局网关服务器"""
    server = get_gateway_server()
    await server.start()


async def stop_gateway_server() -> None:
    """停止全局网关服务器"""
    global _gateway_server
    if _gateway_server:
        await _gateway_server.stop()
        _gateway_server = None


# 便利函数
async def broadcast_system_message(data: Dict[str, Any]) -> None:
    """广播系统消息便利函数"""
    server = get_gateway_server()
    await server.send_system_message(data)


async def send_to_user(user_id: str, data: Dict[str, Any]) -> int:
    """发送消息给用户便利函数"""
    server = get_gateway_server()
    message = GatewayMessage.create("notification", data)
    return await server.send_to_user(user_id, message)