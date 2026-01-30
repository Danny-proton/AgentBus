"""
Gateway Connection Manager

基于Moltbot的连接管理系统，处理WebSocket连接、客户端管理和消息路由
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Set, Optional, List, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

from ..protocol import (
    ProtocolHandler, RequestFrame, ResponseFrame, EventFrame,
    MessageType, ErrorCode, HelloParams, HelloOk, ProtocolError
)
from ..auth import GatewayAuth, AuthResult, AuthMode

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """连接状态"""
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    CLOSING = "closing"
    CLOSED = "closed"


@dataclass
class ClientInfo:
    """客户端信息"""
    client_id: str
    client_name: str
    version: str
    platform: str
    capabilities: Set[str] = field(default_factory=set)
    connected_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    auth_result: Optional[AuthResult] = None
    session_id: Optional[str] = None


@dataclass
class Connection:
    """连接对象"""
    websocket: WebSocketServerProtocol
    client_info: Optional[ClientInfo] = None
    state: ConnectionState = ConnectionState.CONNECTING
    pending_requests: Dict[str, Callable] = field(default_factory=dict)
    subscriptions: Set[str] = field(default_factory=set)


class ConnectionManager:
    """连接管理器"""
    
    def __init__(self, protocol_handler: ProtocolHandler, auth: GatewayAuth):
        self.protocol_handler = protocol_handler
        self.auth = auth
        self.connections: Dict[str, Connection] = {}
        self.clients: Dict[str, ClientInfo] = {}
        self.heartbeat_interval = 30  # 30秒心跳
        self.connection_timeout = 300  # 5分钟连接超时
        self.max_connections = 1000
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}
        
        # 注册默认处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认处理器"""
        # 连接处理器
        self.protocol_handler.register_handler("connect", ConnectHandler(self))
        self.protocol_handler.register_handler("disconnect", DisconnectHandler(self))
        
        # 心跳处理器
        self.protocol_handler.register_handler("heartbeat", HeartbeatHandler(self))
    
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """处理新的WebSocket连接"""
        connection_id = str(uuid.uuid4())
        connection = Connection(websocket=websocket)
        self.connections[connection_id] = connection
        
        logger.info(f"New connection: {connection_id}")
        
        try:
            await self._handle_connection_lifecycle(connection_id, connection)
        except Exception as e:
            logger.error(f"Connection error {connection_id}: {e}")
        finally:
            await self._cleanup_connection(connection_id)
    
    async def _handle_connection_lifecycle(self, connection_id: str, connection: Connection):
        """处理连接生命周期"""
        try:
            # 发送连接挑战
            challenge_event = self.protocol_handler.create_event(
                "connect.challenge",
                {"nonce": str(uuid.uuid4()), "timestamp": time.time()}
            )
            await connection.websocket.send(self.protocol_handler.serialize_frame(challenge_event))
            
            # 异步接收消息
            async for message in connection.websocket:
                try:
                    await self._handle_message(connection_id, connection, message)
                except Exception as e:
                    logger.error(f"Message handling error: {e}")
                    break
                    
        except ConnectionClosed:
            logger.info(f"Connection closed: {connection_id}")
        except Exception as e:
            logger.error(f"Connection lifecycle error: {e}")
        finally:
            connection.state = ConnectionState.CLOSED
    
    async def _handle_message(self, connection_id: str, connection: Connection, message_data: str):
        """处理接收到的消息"""
        # 更新最后活动时间
        if connection.client_info:
            connection.client_info.last_activity = time.time()
        
        # 解析消息
        frame = self.protocol_handler.deserialize_frame(message_data)
        if not frame:
            logger.warning(f"Invalid message format from {connection_id}")
            return
        
        if isinstance(frame, RequestFrame):
            await self._handle_request(connection_id, connection, frame)
        elif isinstance(frame, EventFrame):
            await self._handle_event(connection_id, connection, frame)
    
    async def _handle_request(self, connection_id: str, connection: Connection, request: RequestFrame):
        """处理请求"""
        try:
            # 处理连接请求特殊逻辑
            if request.method == "connect":
                response = await self._handle_connect_request(connection_id, connection, request)
            else:
                # 检查认证状态
                if not connection.client_info or not connection.client_info.auth_result:
                    response = self.protocol_handler.create_error_response(
                        request.id,
                        ErrorCode.UNAUTHORIZED,
                        "Not authenticated"
                    )
                else:
                    # 使用协议处理器处理请求
                    response = await self.protocol_handler.handle_message(request)
            
            if response:
                await connection.websocket.send(self.protocol_handler.serialize_frame(response))
                
        except Exception as e:
            logger.error(f"Request handling error: {e}")
            error_response = self.protocol_handler.create_error_response(
                request.id,
                ErrorCode.INTERNAL_ERROR,
                f"Internal error: {str(e)}"
            )
            await connection.websocket.send(self.protocol_handler.serialize_frame(error_response))
    
    async def _handle_event(self, connection_id: str, connection: Connection, event: EventFrame):
        """处理事件"""
        try:
            # 认证完成事件
            if event.event == "auth.completed":
                await self._handle_auth_completed(connection_id, connection, event)
            else:
                # 使用协议处理器处理事件
                await self.protocol_handler.handle_message(event)
        except Exception as e:
            logger.error(f"Event handling error: {e}")
    
    async def _handle_connect_request(self, connection_id: str, connection: Connection, request: RequestFrame):
        """处理连接请求"""
        params = request.params or {}
        
        try:
            hello_params = HelloParams(**params)
        except Exception as e:
            return self.protocol_handler.create_error_response(
                request.id,
                ErrorCode.INVALID_REQUEST,
                f"Invalid connect parameters: {str(e)}"
            )
        
        # 创建客户端信息
        client_info = ClientInfo(
            client_id=hello_params.client_id,
            client_name=hello_params.client_name,
            version=hello_params.version,
            platform=hello_params.platform,
            capabilities=set(hello_params.capabilities)
        )
        
        # 执行认证
        auth_result = None
        if hello_params.auth_token:
            auth_result = self.auth.authenticate_token(hello_params.auth_token)
        elif hello_params.device_id:
            # 设备认证需要额外的签名验证
            auth_result = self.auth.authenticate_device(
                hello_params.device_id,
                "",  # 签名
                "",  # nonce
                time.time()
            )
        
        if not auth_result or not auth_result.success:
            return self.protocol_handler.create_error_response(
                request.id,
                ErrorCode.UNAUTHORIZED,
                auth_result.reason if auth_result else "Authentication required"
            )
        
        # 更新连接状态
        connection.client_info = client_info
        connection.client_info.auth_result = auth_result
        client_info.session_id = self.auth.create_session(auth_result, client_info.__dict__)
        connection.state = ConnectionState.CONNECTED
        
        # 注册客户端
        self.clients[client_info.client_id] = client_info
        
        # 发送连接成功响应
        hello_ok = HelloOk(
            server_info={
                "name": "Agentbus Gateway",
                "version": "1.0.0",
                "protocol_version": "1.0"
            },
            capabilities=["chat", "sessions", "presence", "heartbeat"],
            policy={
                "heartbeat_interval": self.heartbeat_interval,
                "connection_timeout": self.connection_timeout,
                "max_connections": self.max_connections
            },
            auth_info={
                "session_id": client_info.session_id,
                "scopes": list(auth_result.scopes)
            }
        )
        
        response = self.protocol_handler.create_response(
            request.id,
            payload={
                "server_info": hello_ok.server_info,
                "capabilities": hello_ok.capabilities,
                "policy": hello_ok.policy,
                "auth_info": hello_ok.auth_info
            }
        )
        
        # 启动心跳
        self._start_heartbeat(connection_id)
        
        logger.info(f"Client connected: {client_info.client_id}")
        return response
    
    def _start_heartbeat(self, connection_id: str):
        """启动心跳"""
        if connection_id in self._heartbeat_tasks:
            self._heartbeat_tasks[connection_id].cancel()
        
        task = asyncio.create_task(self._heartbeat_loop(connection_id))
        self._heartbeat_tasks[connection_id] = task
    
    async def _heartbeat_loop(self, connection_id: str):
        """心跳循环"""
        connection = self.connections.get(connection_id)
        if not connection or not connection.websocket:
            return
        
        try:
            while connection.state == ConnectionState.CONNECTED:
                heartbeat_event = self.protocol_handler.create_event(
                    "heartbeat",
                    {"timestamp": time.time()}
                )
                await connection.websocket.send(self.protocol_handler.serialize_frame(heartbeat_event))
                await asyncio.sleep(self.heartbeat_interval)
        except Exception as e:
            logger.error(f"Heartbeat error for {connection_id}: {e}")
    
    async def _cleanup_connection(self, connection_id: str):
        """清理连接"""
        connection = self.connections.pop(connection_id, None)
        if not connection:
            return
        
        # 取消心跳任务
        task = self._heartbeat_tasks.pop(connection_id, None)
        if task:
            task.cancel()
        
        # 清理客户端信息
        if connection.client_info:
            client_id = connection.client_info.client_id
            self.clients.pop(client_id, None)
            if connection.client_info.session_id:
                self.auth.revoke_session(connection.client_info.session_id)
        
        logger.info(f"Connection cleaned up: {connection_id}")
    
    async def broadcast_event(self, event_type: str, payload: Optional[Dict] = None):
        """广播事件到客户端"""
        event = self.protocol_handler.create_event(event_type, payload)
        message = self.protocol_handler.serialize_frame(event)
        
        disconnected = []
        for connection_id, connection in list(self.connections.items()):
            if connection.state == ConnectionState.CONNECTED:
                try:
                    await connection.websocket.send(message)
                except Exception as e:
                    logger.error(f"Broadcast error to {connection_id}: {e}")
                    disconnected.append(connection_id)
        
        # 清理断开的连接
        for connection_id in disconnected:
            await self._cleanup_connection(connection_id)
    
    def get_client_count(self) -> int:
        """获取连接客户端数量"""
        return len([c for c in self.connections.values() if c.state == ConnectionState.CONNECTED])
    
    def get_clients(self) -> List[ClientInfo]:
        """获取所有已连接客户端"""
        return [conn.client_info for conn in self.connections.values() 
                if conn.client_info and conn.state == ConnectionState.CONNECTED]
    
    async def disconnect_client(self, client_id: str, reason: str = "Server disconnect"):
        """断开指定客户端"""
        for connection_id, connection in list(self.connections.items()):
            if connection.client_info and connection.client_info.client_id == client_id:
                try:
                    disconnect_event = self.protocol_handler.create_event(
                        "disconnect",
                        {"reason": reason}
                    )
                    await connection.websocket.send(self.protocol_handler.serialize_frame(disconnect_event))
                    await connection.websocket.close()
                except Exception as e:
                    logger.error(f"Disconnect error: {e}")
                finally:
                    await self._cleanup_connection(connection_id)


# 简单的处理器类
class ConnectHandler:
    def __init__(self, connection_manager):
        self.connection_manager = connection_manager
    
    async def handle_request(self, frame: RequestFrame) -> ResponseFrame:
        return self.connection_manager.protocol_handler.create_error_response(
            frame.id,
            ErrorCode.NOT_IMPLEMENTED,
            "Connect handled by connection manager"
        )


class DisconnectHandler:
    def __init__(self, connection_manager):
        self.connection_manager = connection_manager
    
    async def handle_request(self, frame: RequestFrame) -> ResponseFrame:
        params = frame.params or {}
        client_id = params.get("client_id")
        
        if client_id:
            await self.connection_manager.disconnect_client(client_id)
        
        return self.connection_manager.protocol_handler.create_response(
            frame.id,
            payload={"status": "disconnected"}
        )


class HeartbeatHandler:
    def __init__(self, connection_manager):
        self.connection_manager = connection_manager
    
    async def handle_request(self, frame: RequestFrame) -> ResponseFrame:
        return self.connection_manager.protocol_handler.create_response(
            frame.id,
            payload={"status": "ok", "timestamp": time.time()}
        )