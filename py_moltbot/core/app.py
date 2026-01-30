#!/usr/bin/env python3
"""
Moltbot核心应用程序
Moltbot Core Application

协调所有核心组件的主应用程序
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from .config import settings
from .logger import get_logger, setup_logging
from .session import SessionManager, init_session_manager, shutdown_session_manager
from .security import SecurityManager, get_security_manager
from .gateway import GatewayServer, start_gateway_server, stop_gateway_server
from .routing import MessageBus, start_message_bus, stop_message_bus

logger = get_logger(__name__)


class CoreApplication:
    """
    核心应用程序类
    
    负责初始化和协调所有核心组件
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        
        # 核心组件
        self.session_manager: Optional[SessionManager] = None
        self.security_manager: Optional[SecurityManager] = None
        self.gateway_server: Optional[GatewayServer] = None
        self.message_bus: Optional[MessageBus] = None
        
        # 应用状态
        self.running = False
        self._shutdown_event = asyncio.Event()
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """处理系统信号"""
        self.logger.info("Received shutdown signal", signal=signum)
        asyncio.create_task(self.shutdown())
    
    async def initialize(self) -> None:
        """初始化所有核心组件"""
        try:
            self.logger.info("Initializing Core Application...")
            
            # 创建必要目录
            await self._setup_directories()
            
            # 初始化会话管理
            await self._initialize_session_manager()
            
            # 初始化安全管理
            await self._initialize_security()
            
            # 初始化消息总线
            await self._initialize_message_bus()
            
            # 初始化网关服务
            await self._initialize_gateway()
            
            self.logger.info("Core Application initialized successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize Core Application", error=str(e))
            raise
    
    async def _setup_directories(self) -> None:
        """设置必要的目录"""
        storage_paths = settings.get_storage_paths()
        
        for name, path in storage_paths.items():
            path.mkdir(parents=True, exist_ok=True)
            self.logger.debug("Created directory", name=name, path=str(path))
    
    async def _initialize_session_manager(self) -> None:
        """初始化会话管理"""
        self.logger.info("Initializing Session Manager...")
        
        self.session_manager = SessionManager()
        await self.session_manager.start()
        
        self.logger.info("Session Manager initialized")
    
    async def _initialize_security(self) -> None:
        """初始化安全管理"""
        self.logger.info("Initializing Security Manager...")
        
        self.security_manager = get_security_manager()
        
        # 创建默认管理员用户（如果不存在）
        # 这里可以添加更多初始化逻辑
        
        self.logger.info("Security Manager initialized")
    
    async def _initialize_message_bus(self) -> None:
        """初始化消息总线"""
        self.logger.info("Initializing Message Bus...")
        
        self.message_bus = MessageBus()
        await self.message_bus.start()
        
        # 添加消息处理器
        self.message_bus.add_processor(self._default_message_processor)
        
        self.logger.info("Message Bus initialized")
    
    async def _initialize_gateway(self) -> None:
        """初始化网关服务"""
        self.logger.info("Initializing Gateway Server...")
        
        self.gateway_server = GatewayServer()
        
        # 注册网关消息处理器
        self._register_gateway_handlers()
        
        # 启动WebSocket服务器
        await self.gateway_server.start()
        
        self.logger.info("Gateway Server initialized")
    
    def _register_gateway_handlers(self) -> None:
        """注册网关消息处理器"""
        # 注册路由处理器
        self.gateway_server.router.register_message_handler(
            "route_message", 
            self._handle_gateway_route_message
        )
        
        # 注册会话处理器
        self.gateway_server.router.register_message_handler(
            "create_session", 
            self._handle_gateway_create_session
        )
        
        # 注册用户认证处理器
        self.gateway_server.router.register_message_handler(
            "authenticate", 
            self._handle_gateway_authenticate
        )
    
    async def _default_message_processor(self, message, context) -> None:
        """默认消息处理器"""
        self.logger.debug("Processing message", 
                         message_id=message.id,
                         message_type=message.message_type.value,
                         platform=message.platform.value)
    
    async def _handle_gateway_route_message(self, message, connection) -> None:
        """处理网关路由消息请求"""
        try:
            # 解析路由参数
            route_data = message.data
            message_content = route_data.get("content", "")
            target_type = route_data.get("target_type", "adapter")
            target_name = route_data.get("target_name")
            
            # 创建消息对象
            from ..adapters.base import Message, MessageType, AdapterType
            
            routed_message = Message(
                id=str(message.id),
                platform=AdapterType.WEB,
                chat_id=connection.id,
                user_id=connection.user_id or "anonymous",
                content=message_content,
                message_type=MessageType.TEXT
            )
            
            # 路由消息
            if self.message_bus:
                await self.message_bus.send_message(routed_message, context=None)
            
            # 发送响应
            response = {
                "status": "success",
                "message_id": routed_message.id,
                "target": target_name,
                "routed": True
            }
            
            response_msg = self.gateway_server.router.Message.create("route_response", response)
            await self.gateway_server._send_message(connection, response_msg)
            
        except Exception as e:
            self.logger.error("Gateway route message error", error=str(e))
            await self.gateway_server._send_error(connection, str(e), "route_error")
    
    async def _handle_gateway_create_session(self, message, connection) -> None:
        """处理创建会话请求"""
        try:
            if not self.session_manager:
                raise RuntimeError("Session manager not initialized")
            
            session_data = message.data
            chat_id = session_data.get("chat_id", connection.id)
            user_id = session_data.get("user_id", connection.user_id or "anonymous")
            
            # 创建会话
            session = await self.session_manager.create_session(
                chat_id=chat_id,
                user_id=user_id,
                platform=connection.client_info.get("platform", AdapterType.WEB),
                session_type=session_data.get("session_type", "private")
            )
            
            # 发送响应
            response = {
                "session_id": session.session_id,
                "chat_id": session.chat_id,
                "user_id": session.user_id,
                "created_at": session.created_at.isoformat()
            }
            
            response_msg = self.gateway_server.router.Message.create("session_created", response)
            await self.gateway_server._send_message(connection, response_msg)
            
        except Exception as e:
            self.logger.error("Gateway create session error", error=str(e))
            await self.gateway_server._send_error(connection, str(e), "session_error")
    
    async def _handle_gateway_authenticate(self, message, connection) -> None:
        """处理认证请求"""
        try:
            if not self.security_manager:
                raise RuntimeError("Security manager not initialized")
            
            auth_data = message.data
            username = auth_data.get("username")
            password = auth_data.get("password")
            
            if not username or not password:
                await self.gateway_server._send_error(
                    connection, 
                    "Username and password required", 
                    "auth_failed"
                )
                return
            
            # 认证用户
            user = await self.security_manager.auth.authenticate_user(username, password)
            
            if not user:
                await self.gateway_server._send_error(
                    connection, 
                    "Invalid credentials", 
                    "auth_failed"
                )
                return
            
            # 创建访问令牌
            token = await self.security_manager.auth.create_access_token(user)
            
            # 更新连接状态
            connection.user_id = user.id
            connection.state = self.gateway_server.router.ConnectionState.AUTHENTICATED
            
            # 发送响应
            response = {
                "user_id": user.id,
                "username": user.username,
                "token": token,
                "permissions": [p.value for p in user.permissions]
            }
            
            response_msg = self.gateway_server.router.Message.create("auth_success", response)
            await self.gateway_server._send_message(connection, response_msg)
            
        except Exception as e:
            self.logger.error("Gateway authenticate error", error=str(e))
            await self.gateway_server._send_error(connection, str(e), "auth_error")
    
    async def run(self) -> None:
        """运行应用程序"""
        if not all([self.session_manager, self.security_manager, self.message_bus, self.gateway_server]):
            raise RuntimeError("Application not fully initialized. Call initialize() first.")
        
        self.running = True
        self.logger.info("Starting Core Application...")
        
        try:
            # 发送启动通知
            await self._broadcast_startup_notification()
            
            # 等待关闭信号
            await self._shutdown_event.wait()
            
        except Exception as e:
            self.logger.error("Application runtime error", error=str(e))
            raise
        finally:
            await self.shutdown()
    
    async def _broadcast_startup_notification(self) -> None:
        """广播启动通知"""
        if self.gateway_server:
            startup_msg = {
                "event": "application_started",
                "timestamp": asyncio.get_event_loop().time(),
                "version": settings.app_version,
                "environment": settings.environment
            }
            
            await self.gateway_server.broadcast_message(startup_msg)
    
    async def shutdown(self) -> None:
        """关闭应用程序"""
        if not self.running:
            return
        
        self.logger.info("Shutting down Core Application...")
        self.running = False
        
        try:
            # 关闭网关服务
            if self.gateway_server:
                await self.gateway_server.stop()
                self.logger.info("Gateway Server stopped")
            
            # 关闭消息总线
            if self.message_bus:
                await self.message_bus.stop()
                self.logger.info("Message Bus stopped")
            
            # 关闭会话管理器
            if self.session_manager:
                await self.session_manager.stop()
                self.logger.info("Session Manager stopped")
            
            # 清理安全管理器
            # 安全管理器通常不需要特殊清理
            
            self.logger.info("Core Application shutdown completed")
            
        except Exception as e:
            self.logger.error("Error during shutdown", error=str(e))
        
        finally:
            self._shutdown_event.set()
    
    def get_status(self) -> Dict[str, Any]:
        """获取应用程序状态"""
        status = {
            "running": self.running,
            "version": settings.app_version,
            "environment": settings.environment,
            "components": {}
        }
        
        # 会话管理器状态
        if self.session_manager:
            status["components"]["session_manager"] = {
                "running": True,
                "stats": self.session_manager.get_session_stats()
            }
        
        # 消息总线状态
        if self.message_bus:
            status["components"]["message_bus"] = {
                "running": True,
                "queue_size": self.message_bus.incoming_queue.qsize(),
                "processors": len(self.message_bus.processors)
            }
        
        # 网关服务状态
        if self.gateway_server:
            status["components"]["gateway"] = {
                "running": True,
                "stats": self.gateway_server.get_connection_stats()
            }
        
        # 安全管理器状态
        if self.security_manager:
            status["components"]["security"] = {
                "running": True,
                "encryption_enabled": True,
                "jwt_enabled": True
            }
        
        return status
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health = {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "checks": {}
        }
        
        # 检查会话管理器
        if self.session_manager:
            try:
                # 简单的健康检查
                await asyncio.sleep(0.01)
                health["checks"]["session_manager"] = "ok"
            except Exception as e:
                health["checks"]["session_manager"] = f"error: {e}"
                health["status"] = "degraded"
        
        # 检查消息总线
        if self.message_bus:
            try:
                queue_size = self.message_bus.incoming_queue.qsize()
                health["checks"]["message_bus"] = f"ok (queue: {queue_size})"
            except Exception as e:
                health["checks"]["message_bus"] = f"error: {e}"
                health["status"] = "degraded"
        
        # 检查网关服务
        if self.gateway_server:
            try:
                connection_count = len(self.gateway_server.connections)
                health["checks"]["gateway"] = f"ok (connections: {connection_count})"
            except Exception as e:
                health["checks"]["gateway"] = f"error: {e}"
                health["status"] = "degraded"
        
        return health


# 全局核心应用实例
_core_app: Optional[CoreApplication] = None


def get_core_app() -> CoreApplication:
    """获取全局核心应用实例"""
    global _core_app
    if _core_app is None:
        _core_app = CoreApplication()
    return _core_app


async def initialize_core_app() -> CoreApplication:
    """初始化全局核心应用"""
    app = get_core_app()
    await app.initialize()
    return app


async def shutdown_core_app() -> None:
    """关闭全局核心应用"""
    global _core_app
    if _core_app:
        await _core_app.shutdown()
        _core_app = None


# MoltBot别名（为了向后兼容）
MoltBot = CoreApplication


# CLI入口点
async def main():
    """主函数"""
    try:
        # 初始化日志系统
        setup_logging()
        
        # 创建并初始化核心应用
        app = await initialize_core_app()
        
        # 显示状态
        status = app.get_status()
        logger.info("Core Application status", status=status)
        
        # 运行应用
        await app.run()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error("Application failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())