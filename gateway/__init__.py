"""
Agentbus Gateway System

A complete gateway system based on Moltbot's architecture for:
- Gateway server functionality
- Client authentication
- Chat processing
- WebSocket communication
- API interface management
"""

__version__ = "1.0.0"
__author__ = "Agentbus Team"

from .core.server import GatewayServer, GatewayConfig
from .core.client import GatewayClient, ClientConfig, SyncGatewayClient
from .auth import GatewayAuth, AuthConfig, AuthMode, create_default_auth
from .protocol import ProtocolHandler
from .core.connection import ConnectionManager

__all__ = [
    "GatewayServer",
    "GatewayConfig",
    "GatewayClient",
    "ClientConfig", 
    "SyncGatewayClient",
    "GatewayAuth",
    "AuthConfig",
    "AuthMode",
    "create_default_auth",
    "ProtocolHandler",
    "ConnectionManager",
]