"""
Gateway Client

基于Moltbot的网关客户端实现，支持WebSocket连接和消息通信
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Optional, List, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

from ..protocol import (
    ProtocolHandler, RequestFrame, ResponseFrame, EventFrame,
    MessageType, ErrorCode, HelloParams, HelloOk
)

logger = logging.getLogger(__name__)


class ClientState(Enum):
    """客户端状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


@dataclass
class ClientConfig:
    """客户端配置"""
    url: str = "ws://localhost:18789"
    client_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str = "Agentbus Client"
    version: str = "1.0.0"
    platform: str = "python"
    capabilities: List[str] = field(default_factory=lambda: ["chat", "sessions", "presence"])
    auth_token: Optional[str] = None
    device_id: Optional[str] = None
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 10
    reconnect_delay: float = 5.0
    heartbeat_interval: int = 30
    request_timeout: float = 30.0


@dataclass
class PendingRequest:
    """待处理请求"""
    request: RequestFrame
    resolve: Callable
    reject: Callable
    created_at: float = field(default_factory=time.time)


class GatewayClient:
    """网关客户端"""
    
    def __init__(self, config: ClientConfig):
        self.config = config
        self.protocol_handler = ProtocolHandler()
        self.state = ClientState.DISCONNECTED
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.pending_requests: Dict[str, PendingRequest] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.reconnect_attempts = 0
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.reconnect_task: Optional[asyncio.Task] = None
        
        # 注册默认事件处理器
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认事件处理器"""
        self.on_event("connect.challenge", self._handle_connect_challenge)
        self.on_event("heartbeat", self._handle_heartbeat)
        self.on_event("disconnect", self._handle_disconnect)
    
    def on_event(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def off_event(self, event_type: str, handler: Callable):
        """取消事件处理器"""
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
            except ValueError:
                pass
    
    async def connect(self):
        """连接到网关"""
        if self.state != ClientState.DISCONNECTED:
            logger.warning("Client is already connected or connecting")
            return
        
        logger.info(f"Connecting to gateway: {self.config.url}")
        self.state = ClientState.CONNECTING
        
        try:
            # 建立WebSocket连接
            self.websocket = await websockets.connect(
                self.config.url,
                max_size=25 * 1024 * 1024,
                max_queue=32,
                ping_interval=20,
                ping_timeout=10
            )
            
            logger.info("WebSocket connection established")
            
            # 启动消息接收任务
            receive_task = asyncio.create_task(self._receive_messages())
            
            # 启动心跳任务
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # 等待连接完成或失败
            try:
                await asyncio.gather(receive_task, return_exceptions=True)
            finally:
                if self.heartbeat_task:
                    self.heartbeat_task.cancel()
                
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            await self._handle_connection_error(e)
    
    async def disconnect(self, reason: str = "Client disconnect"):
        """断开连接"""
        if self.state == ClientState.DISCONNECTED:
            return
        
        logger.info(f"Disconnecting: {reason}")
        self.state = ClientState.DISCONNECTED
        
        # 取消任务
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None
        
        if self.reconnect_task:
            self.reconnect_task.cancel()
            self.reconnect_task = None
        
        # 关闭WebSocket
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error closing websocket: {e}")
            finally:
                self.websocket = None
        
        # 拒绝所有待处理的请求
        for pending in self.pending_requests.values():
            pending.reject(Exception("Connection closed"))
        self.pending_requests.clear()
    
    async def send_request(self, method: str, params: Optional[Dict] = None) -> Any:
        """发送请求并等待响应"""
        if self.state != ClientState.CONNECTED:
            raise Exception("Client is not connected")
        
        request = self.protocol_handler.create_request(method, params)
        
        # 创建未来对象
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        
        # 添加到待处理请求
        pending = PendingRequest(
            request=request,
            resolve=future.set_result,
            reject=future.set_exception
        )
        self.pending_requests[request.id] = pending
        
        try:
            # 发送请求
            message = self.protocol_handler.serialize_frame(request)
            await self.websocket.send(message)
            
            # 等待响应
            return await asyncio.wait_for(future, timeout=self.config.request_timeout)
            
        except asyncio.TimeoutError:
            # 移除待处理请求
            self.pending_requests.pop(request.id, None)
            raise Exception("Request timeout")
        except Exception as e:
            # 移除待处理请求
            self.pending_requests.pop(request.id, None)
            raise e
    
    async def send_event(self, event_type: str, payload: Optional[Dict] = None):
        """发送事件"""
        if self.state != ClientState.CONNECTED:
            raise Exception("Client is not connected")
        
        event = self.protocol_handler.create_event(event_type, payload)
        message = self.protocol_handler.serialize_frame(event)
        await self.websocket.send(message)
    
    async def _receive_messages(self):
        """接收消息"""
        try:
            async for message in self.websocket:
                try:
                    await self._handle_message(message)
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    
        except ConnectionClosed:
            logger.info("WebSocket connection closed")
            await self._handle_connection_closed()
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            await self._handle_connection_error(e)
    
    async def _handle_message(self, message_data: str):
        """处理接收到的消息"""
        frame = self.protocol_handler.deserialize_frame(message_data)
        if not frame:
            logger.warning("Invalid message format")
            return
        
        if isinstance(frame, ResponseFrame):
            await self._handle_response(frame)
        elif isinstance(frame, EventFrame):
            await self._handle_event(frame)
    
    async def _handle_response(self, response: ResponseFrame):
        """处理响应"""
        pending = self.pending_requests.pop(response.id, None)
        if not pending:
            logger.warning(f"Unexpected response: {response.id}")
            return
        
        if response.ok:
            pending.resolve(response.payload)
        else:
            error_msg = response.error.get("message", "Unknown error") if response.error else "Unknown error"
            pending.reject(Exception(error_msg))
    
    async def _handle_event(self, event: EventFrame):
        """处理事件"""
        # 通知注册的事件处理器
        handlers = self.event_handlers.get(event.event, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
    
    async def _handle_connect_challenge(self, event: EventFrame):
        """处理连接挑战"""
        logger.info("Received connect challenge")
        
        # 创建连接参数
        hello_params = HelloParams(
            client_id=self.config.client_id,
            client_name=self.config.client_name,
            version=self.config.version,
            platform=self.config.platform,
            capabilities=self.config.capabilities,
            auth_token=self.config.auth_token,
            device_id=self.config.device_id
        )
        
        # 发送连接请求
        try:
            response = await self.send_request("connect", hello_params.__dict__)
            logger.info("Authentication successful")
            self.state = ClientState.CONNECTED
            self.reconnect_attempts = 0  # 重置重连尝试次数
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            await self.disconnect(f"Authentication failed: {e}")
    
    async def _handle_heartbeat(self, event: EventFrame):
        """处理心跳"""
        logger.debug("Received heartbeat")
    
    async def _handle_disconnect(self, event: EventFrame):
        """处理断开事件"""
        reason = event.payload.get("reason", "Unknown") if event.payload else "Unknown"
        logger.info(f"Server disconnect: {reason}")
        await self.disconnect(reason)
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        while self.state == ClientState.CONNECTED:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                await self.send_event("heartbeat", {"timestamp": time.time()})
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break
    
    async def _handle_connection_closed(self):
        """处理连接关闭"""
        logger.info("Connection closed by server")
        self.state = ClientState.DISCONNECTED
        
        if self.config.auto_reconnect:
            await self._schedule_reconnect()
    
    async def _handle_connection_error(self, error: Exception):
        """处理连接错误"""
        logger.error(f"Connection error: {error}")
        self.state = ClientState.DISCONNECTED
        
        if self.config.auto_reconnect:
            await self._schedule_reconnect()
    
    async def _schedule_reconnect(self):
        """调度重连"""
        if self.reconnect_attempts >= self.config.max_reconnect_attempts:
            logger.error("Max reconnect attempts reached")
            return
        
        self.reconnect_attempts += 1
        self.state = ClientState.RECONNECTING
        
        delay = self.config.reconnect_delay * (2 ** (self.reconnect_attempts - 1))  # 指数退避
        logger.info(f"Reconnecting in {delay:.1f} seconds (attempt {self.reconnect_attempts}/{self.config.max_reconnect_attempts})")
        
        await asyncio.sleep(delay)
        
        if self.state == ClientState.RECONNECTING:
            await self.connect()
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.state == ClientState.CONNECTED
    
    def get_status(self) -> Dict[str, Any]:
        """获取客户端状态"""
        return {
            "state": self.state.value,
            "client_id": self.config.client_id,
            "client_name": self.config.client_name,
            "url": self.config.url,
            "reconnect_attempts": self.reconnect_attempts,
            "pending_requests": len(self.pending_requests),
            "connected": self.is_connected()
        }


# 便捷方法
async def create_client(url: str, auth_token: Optional[str] = None) -> GatewayClient:
    """创建客户端"""
    config = ClientConfig(
        url=url,
        auth_token=auth_token
    )
    client = GatewayClient(config)
    return client


class SyncGatewayClient:
    """同步网关客户端包装器"""
    
    def __init__(self, client: GatewayClient):
        self.client = client
    
    def connect(self):
        """同步连接"""
        return asyncio.run(self.client.connect())
    
    def disconnect(self, reason: str = "Client disconnect"):
        """同步断开"""
        return asyncio.run(self.client.disconnect(reason))
    
    def send_request(self, method: str, params: Optional[Dict] = None) -> Any:
        """同步发送请求"""
        return asyncio.run(self.client.send_request(method, params))
    
    def send_event(self, event_type: str, payload: Optional[Dict] = None):
        """同步发送事件"""
        return asyncio.run(self.client.send_event(event_type, payload))
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.client.is_connected()
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return self.client.get_status()