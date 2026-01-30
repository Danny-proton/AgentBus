"""
Gateway Server Core

基于Moltbot的网关服务器核心，实现完整的网关功能
"""

import asyncio
import logging
import signal
import sys
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
import websockets
from websockets.server import serve

from ..protocol import ProtocolHandler, BaseHandler, ChatHandler, SystemHandler
from ..auth import GatewayAuth, AuthConfig, AuthMode, create_default_auth
from .connection import ConnectionManager

logger = logging.getLogger(__name__)


@dataclass
class GatewayConfig:
    """网关配置"""
    host: str = "0.0.0.0"
    port: int = 18789
    max_connections: int = 1000
    connection_timeout: int = 300
    heartbeat_interval: int = 30
    auth_mode: AuthMode = AuthMode.TOKEN
    auth_token: Optional[str] = None
    allow_tailscale: bool = False
    log_level: str = "INFO"


class GatewayServer:
    """网关服务器"""
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.protocol_handler = ProtocolHandler()
        self.auth = self._setup_auth()
        self.connection_manager = ConnectionManager(self.protocol_handler, self.auth)
        self.websocket_server: Optional[websockets.WebSocketServer] = None
        self.running = False
        self.start_time: Optional[float] = None
        
        # 注册处理器
        self._register_handlers()
        
        # 设置日志
        self._setup_logging()
    
    def _setup_auth(self) -> GatewayAuth:
        """设置认证"""
        auth_config = AuthConfig(
            mode=self.config.auth_mode,
            token=self.config.auth_token,
            allow_tailscale=self.config.allow_tailscale
        )
        return GatewayAuth(auth_config)
    
    def _register_handlers(self):
        """注册请求处理器"""
        # 聊天处理器
        chat_handler = ChatHandler(self.protocol_handler)
        self.protocol_handler.register_handler("chat.send", chat_handler)
        self.protocol_handler.register_handler("chat.history", chat_handler)
        self.protocol_handler.register_handler("chat.abort", chat_handler)
        
        # 系统处理器
        system_handler = SystemHandler(self.protocol_handler)
        self.protocol_handler.register_handler("system.info", system_handler)
        self.protocol_handler.register_handler("system.status", system_handler)
        
        # 会话处理器
        self.protocol_handler.register_handler("sessions.list", SessionHandler(self.protocol_handler))
        self.protocol_handler.register_handler("sessions.get", SessionHandler(self.protocol_handler))
        self.protocol_handler.register_handler("sessions.delete", SessionHandler(self.protocol_handler))
        
        # 设备处理器
        self.protocol_handler.register_handler("devices.register", DeviceHandler(self.protocol_handler))
        self.protocol_handler.register_handler("devices.list", DeviceHandler(self.protocol_handler))
        self.protocol_handler.register_handler("devices.revoke", DeviceHandler(self.protocol_handler))
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    async def start(self):
        """启动网关服务器"""
        if self.running:
            logger.warning("Gateway server is already running")
            return
        
        self.running = True
        self.start_time = time.time()
        
        logger.info(f"Starting Agentbus Gateway Server v1.0.0")
        logger.info(f"Host: {self.config.host}:{self.config.port}")
        logger.info(f"Auth mode: {self.config.auth_mode.value}")
        logger.info(f"Max connections: {self.config.max_connections}")
        
        try:
            # 创建WebSocket服务器
            self.websocket_server = await serve(
                self.connection_manager.handle_connection,
                self.config.host,
                self.config.port,
                max_size=25 * 1024 * 1024,  # 25MB
                max_queue=32,
                ping_interval=20,
                ping_timeout=10
            )
            
            logger.info("WebSocket server started successfully")
            
            # 注册信号处理器
            self._register_signal_handlers()
            
            # 开始主循环
            await self._main_loop()
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """停止网关服务器"""
        if not self.running:
            return
        
        logger.info("Stopping Gateway Server...")
        self.running = False
        
        # 关闭WebSocket服务器
        if self.websocket_server:
            self.websocket_server.close()
            await self.websocket_server.wait_closed()
        
        # 清理连接
        for connection_id in list(self.connection_manager.connections.keys()):
            await self.connection_manager._cleanup_connection(connection_id)
        
        logger.info("Gateway Server stopped")
    
    async def _main_loop(self):
        """主循环"""
        try:
            while self.running:
                # 广播心跳
                await self.connection_manager.broadcast_event(
                    "heartbeat",
                    {"timestamp": time.time(), "uptime": self.get_uptime()}
                )
                
                # 清理过期会话
                self.auth.cleanup_expired_sessions()
                
                # 等待心跳间隔
                await asyncio.sleep(self.config.heartbeat_interval)
                
        except asyncio.CancelledError:
            logger.info("Main loop cancelled")
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            raise
    
    def _register_signal_handlers(self):
        """注册信号处理器"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def get_uptime(self) -> float:
        """获取运行时间"""
        if self.start_time:
            return time.time() - self.start_time
        return 0
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        return {
            "name": "Agentbus Gateway",
            "version": "1.0.0",
            "status": "running" if self.running else "stopped",
            "uptime": self.get_uptime(),
            "connections": self.connection_manager.get_client_count(),
            "clients": [
                {
                    "client_id": c.client_id,
                    "client_name": c.client_name,
                    "connected_at": c.connected_at,
                    "capabilities": list(c.capabilities)
                }
                for c in self.connection_manager.get_clients()
            ],
            "config": {
                "host": self.config.host,
                "port": self.config.port,
                "auth_mode": self.config.auth_mode.value,
                "max_connections": self.config.max_connections
            }
        }
    
    async def restart(self):
        """重启服务器"""
        logger.info("Restarting Gateway Server...")
        await self.stop()
        await asyncio.sleep(1)  # 等待一秒
        await self.start()


# 处理器实现
class SessionHandler:
    """会话处理器"""
    
    def __init__(self, protocol_handler: ProtocolHandler):
        self.protocol_handler = protocol_handler
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    async def handle_request(self, frame):
        """处理会话请求"""
        if frame.method == "sessions.list":
            return await self._handle_list_sessions(frame)
        elif frame.method == "sessions.get":
            return await self._handle_get_session(frame)
        elif frame.method == "sessions.delete":
            return await self._handle_delete_session(frame)
        else:
            return self.protocol_handler.create_error_response(
                frame.id,
                4004,
                f"Method not found: {frame.method}"
            )
    
    async def _handle_list_sessions(self, frame):
        """处理列出会话"""
        sessions = [
            {
                "session_id": sid,
                "created_at": data.get("created_at", 0),
                "client_id": data.get("client_id", ""),
                "last_activity": data.get("last_activity", 0)
            }
            for sid, data in self.sessions.items()
        ]
        
        return self.protocol_handler.create_response(
            frame.id,
            payload={"sessions": sessions}
        )
    
    async def _handle_get_session(self, frame):
        """处理获取会话"""
        params = frame.params or {}
        session_id = params.get("session_id")
        
        if not session_id:
            return self.protocol_handler.create_error_response(
                frame.id,
                4000,
                "session_id is required"
            )
        
        session = self.sessions.get(session_id)
        if not session:
            return self.protocol_handler.create_error_response(
                frame.id,
                404,
                f"Session not found: {session_id}"
            )
        
        return self.protocol_handler.create_response(
            frame.id,
            payload={"session": session}
        )
    
    async def _handle_delete_session(self, frame):
        """处理删除会话"""
        params = frame.params or {}
        session_id = params.get("session_id")
        
        if not session_id:
            return self.protocol_handler.create_error_response(
                frame.id,
                4000,
                "session_id is required"
            )
        
        if session_id in self.sessions:
            del self.sessions[session_id]
        
        return self.protocol_handler.create_response(
            frame.id,
            payload={"status": "deleted"}
        )


class DeviceHandler:
    """设备处理器"""
    
    def __init__(self, protocol_handler: ProtocolHandler):
        self.protocol_handler = protocol_handler
        self.devices: Dict[str, Dict[str, Any]] = {}
    
    async def handle_request(self, frame):
        """处理设备请求"""
        if frame.method == "devices.register":
            return await self._handle_register_device(frame)
        elif frame.method == "devices.list":
            return await self._handle_list_devices(frame)
        elif frame.method == "devices.revoke":
            return await self._handle_revoke_device(frame)
        else:
            return self.protocol_handler.create_error_response(
                frame.id,
                4004,
                f"Method not found: {frame.method}"
            )
    
    async def _handle_register_device(self, frame):
        """处理注册设备"""
        params = frame.params or {}
        device_id = params.get("device_id")
        public_key = params.get("public_key")
        
        if not device_id or not public_key:
            return self.protocol_handler.create_error_response(
                frame.id,
                4000,
                "device_id and public_key are required"
            )
        
        device_info = {
            "device_id": device_id,
            "public_key": public_key,
            "registered_at": time.time(),
            "status": "active"
        }
        
        self.devices[device_id] = device_info
        
        return self.protocol_handler.create_response(
            frame.id,
            payload={"device": device_info}
        )
    
    async def _handle_list_devices(self, frame):
        """处理列出设备"""
        devices = list(self.devices.values())
        
        return self.protocol_handler.create_response(
            frame.id,
            payload={"devices": devices}
        )
    
    async def _handle_revoke_device(self, frame):
        """处理撤销设备"""
        params = frame.params or {}
        device_id = params.get("device_id")
        
        if not device_id:
            return self.protocol_handler.create_error_response(
                frame.id,
                4000,
                "device_id is required"
            )
        
        if device_id in self.devices:
            self.devices[device_id]["status"] = "revoked"
            self.devices[device_id]["revoked_at"] = time.time()
        
        return self.protocol_handler.create_response(
            frame.id,
            payload={"status": "revoked"}
        )