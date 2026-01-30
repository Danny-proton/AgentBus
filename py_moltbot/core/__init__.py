"""
核心基础设施模块
Core Infrastructure Module

包含配置、日志、会话、安全、网关、路由等核心功能
"""

from .config import Settings, settings
from .logger import get_logger, setup_logging, LoggerMixin
from .session import (
    SessionManager, SessionContext, SessionType, SessionStatus,
    MemorySessionStore, SessionStore, get_session_manager,
    init_session_manager, shutdown_session_manager
)
from .security import (
    SecurityManager, AuthenticationService, AuthorizationService,
    EncryptionService, JWTService, User, SecurityToken,
    Permission, SecurityLevel, get_security_manager
)
from .gateway import (
    GatewayServer, WebSocketConnection, GatewayMessage,
    MessagePriority, ConnectionState, get_gateway_server,
    start_gateway_server, stop_gateway_server
)
from .routing import (
    MessageRouter, MessageBus, RoutingRule, RouteTarget, RoutedMessage,
    RoutingStrategy, MessageRoute, get_message_bus,
    start_message_bus, stop_message_bus
)
from .app import CoreApplication, get_core_app, initialize_core_app, shutdown_core_app

__all__ = [
    # 配置和日志
    "Settings",
    "settings", 
    "get_logger",
    "setup_logging",
    "LoggerMixin",
    
    # 会话管理
    "SessionManager",
    "SessionContext",
    "SessionType",
    "SessionStatus",
    "MemorySessionStore",
    "SessionStore",
    "get_session_manager",
    "init_session_manager", 
    "shutdown_session_manager",
    
    # 安全管理
    "SecurityManager",
    "AuthenticationService",
    "AuthorizationService", 
    "EncryptionService",
    "JWTService",
    "User",
    "SecurityToken",
    "Permission",
    "SecurityLevel",
    "get_security_manager",
    
    # 网关服务
    "GatewayServer",
    "WebSocketConnection",
    "GatewayMessage",
    "MessagePriority",
    "ConnectionState",
    "get_gateway_server",
    "start_gateway_server",
    "stop_gateway_server",
    
    # 消息路由
    "MessageRouter",
    "MessageBus",
    "RoutingRule",
    "RouteTarget", 
    "RoutedMessage",
    "RoutingStrategy",
    "MessageRoute",
    "get_message_bus",
    "start_message_bus",
    "stop_message_bus",
    
    # 核心应用
    "CoreApplication",
    "get_core_app",
    "initialize_core_app",
    "shutdown_core_app",
]