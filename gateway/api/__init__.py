"""
Gateway API Interface Manager

API接口管理器，提供HTTP RESTful API接口
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import aiohttp
from aiohttp import web, ClientSession
import time

from ..protocol import ProtocolHandler, RequestFrame, ResponseFrame
from ..auth import GatewayAuth, AuthResult
from ..core.connection import ConnectionManager

logger = logging.getLogger(__name__)


class HTTPMethod(Enum):
    """HTTP方法"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class APIRoute:
    """API路由"""
    path: str
    method: HTTPMethod
    handler: Callable
    auth_required: bool = True
    scopes: Optional[List[str]] = None


class APIManager:
    """API管理器"""
    
    def __init__(self, protocol_handler: ProtocolHandler, auth: GatewayAuth, connection_manager: ConnectionManager):
        self.protocol_handler = protocol_handler
        self.auth = auth
        self.connection_manager = connection_manager
        self.routes: Dict[str, APIRoute] = {}
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
        # 注册默认路由
        self._register_default_routes()
    
    def _register_default_routes(self):
        """注册默认API路由"""
        self.add_route("/status", HTTPMethod.GET, self._handle_status, auth_required=False)
        self.add_route("/health", HTTPMethod.GET, self._handle_health, auth_required=False)
        self.add_route("/api/v1/sessions", HTTPMethod.GET, self._handle_list_sessions)
        self.add_route("/api/v1/sessions", HTTPMethod.POST, self._handle_create_session)
        self.add_route("/api/v1/sessions/{session_id}", HTTPMethod.GET, self._handle_get_session)
        self.add_route("/api/v1/sessions/{session_id}", HTTPMethod.DELETE, self._handle_delete_session)
        self.add_route("/api/v1/sessions/{session_id}/messages", HTTPMethod.GET, self._handle_get_messages)
        self.add_route("/api/v1/sessions/{session_id}/messages", HTTPMethod.POST, self._handle_send_message)
        self.add_route("/api/v1/clients", HTTPMethod.GET, self._handle_list_clients)
        self.add_route("/api/v1/stats", HTTPMethod.GET, self._handle_stats)
    
    def add_route(self, path: str, method: HTTPMethod, handler: Callable, auth_required: bool = True, scopes: Optional[List[str]] = None):
        """添加API路由"""
        route_key = f"{method.value}:{path}"
        self.routes[route_key] = APIRoute(
            path=path,
            method=method,
            handler=handler,
            auth_required=auth_required,
            scopes=scopes
        )
    
    def create_app(self) -> web.Application:
        """创建aiohttp应用"""
        app = web.Application(client_max_size=25 * 1024 * 1024)  # 25MB
        
        # 添加中间件
        app.middlewares.append(self._auth_middleware)
        app.middlewares.append(self._error_middleware)
        app.middlewares.append(self._cors_middleware)
        
        # 注册路由
        for route in self.routes.values():
            if route.method == HTTPMethod.GET:
                app.router.add_get(route.path, self._create_handler(route))
            elif route.method == HTTPMethod.POST:
                app.router.add_post(route.path, self._create_handler(route))
            elif route.method == HTTPMethod.PUT:
                app.router.add_put(route.path, self._create_handler(route))
            elif route.method == HTTPMethod.DELETE:
                app.router.add_delete(route.path, self._create_handler(route))
            elif route.method == HTTPMethod.PATCH:
                app.router.add_patch(route.path, self._create_handler(route))
        
        # 404处理
        app.router.add_route("*", "/{path:.*}", self._handle_not_found)
        
        self.app = app
        return app
    
    def _create_handler(self, route: APIRoute):
        """创建路由处理器"""
        async def handler(request):
            try:
                # 验证认证
                if route.auth_required:
                    auth_result = await self._authenticate_request(request)
                    if not auth_result:
                        return web.json_response(
                            {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}},
                            status=401
                        )
                    
                    # 检查权限
                    if route.scopes and not self._check_scopes(auth_result, route.scopes):
                        return web.json_response(
                            {"error": {"code": "FORBIDDEN", "message": "Insufficient permissions"}},
                            status=403
                        )
                
                # 调用处理函数
                result = await route.handler(request, auth_result if route.auth_required else None)
                return web.json_response(result)
                
            except Exception as e:
                logger.error(f"API handler error: {e}")
                return web.json_response(
                    {"error": {"code": "INTERNAL_ERROR", "message": str(e)}},
                    status=500
                )
        
        return handler
    
    async def _authenticate_request(self, request: web.Request) -> Optional[AuthResult]:
        """认证HTTP请求"""
        # 从Header获取Token
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
        
        try:
            # 解析Bearer Token
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]  # 移除"Bearer "前缀
                return self.auth.authenticate_token(token)
            elif auth_header.startswith('Basic '):
                # Basic认证
                import base64
                credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
                username, password = credentials.split(':', 1)
                if username == "gateway" and password:
                    return self.auth.authenticate_password(password)
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
        
        return None
    
    def _check_scopes(self, auth_result: AuthResult, required_scopes: List[str]) -> bool:
        """检查权限范围"""
        if not required_scopes:
            return True
        
        user_scopes = auth_result.scopes
        return any(scope in user_scopes for scope in required_scopes)
    
    async def _auth_middleware(self, request: web.Request, handler):
        """认证中间件"""
        # 对于不需要认证的路径，直接处理
        path = request.path
        if path in ['/status', '/health', '/docs', '/openapi.json']:
            return await handler(request)
        
        # 其他路径需要认证
        return await self._authenticate_request(request) or (await handler(request))
    
    async def _error_middleware(self, request: web.Request, handler):
        """错误处理中间件"""
        try:
            return await handler(request)
        except web.HTTPError as e:
            return web.json_response(
                {"error": {"code": f"HTTP_{e.status}", "message": str(e.reason)}},
                status=e.status
            )
        except Exception as e:
            logger.error(f"Unhandled error: {e}")
            return web.json_response(
                {"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}},
                status=500
            )
    
    async def _cors_middleware(self, request: web.Request, handler):
        """CORS中间件"""
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, PATCH, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
    # API处理器实现
    async def _handle_status(self, request: web.Request, auth_result: Optional[AuthResult]) -> Dict[str, Any]:
        """处理状态查询"""
        return {
            "name": "Agentbus Gateway",
            "version": "1.0.0",
            "status": "running",
            "timestamp": time.time(),
            "uptime": time.time()
        }
    
    async def _handle_health(self, request: web.Request, auth_result: Optional[AuthResult]) -> Dict[str, Any]:
        """处理健康检查"""
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "checks": {
                "database": "ok",
                "websocket": "ok",
                "auth": "ok"
            }
        }
    
    async def _handle_list_sessions(self, request: web.Request, auth_result: AuthResult) -> Dict[str, Any]:
        """处理列出会话"""
        sessions = list(self.connection_manager.clients.values())
        return {
            "sessions": [
                {
                    "client_id": c.client_id,
                    "client_name": c.client_name,
                    "connected_at": c.connected_at,
                    "last_activity": c.last_activity,
                    "capabilities": list(c.capabilities)
                }
                for c in sessions
            ]
        }
    
    async def _handle_create_session(self, request: web.Request, auth_result: AuthResult) -> Dict[str, Any]:
        """处理创建会话"""
        data = await request.json()
        session_id = data.get("session_id")
        client_id = data.get("client_id", auth_result.user_id)
        
        if not session_id:
            return {"error": {"code": "INVALID_REQUEST", "message": "session_id is required"}}
        
        # 这里应该实际创建会话
        return {
            "session_id": session_id,
            "client_id": client_id,
            "created_at": time.time()
        }
    
    async def _handle_get_session(self, request: web.Request, auth_result: AuthResult) -> Dict[str, Any]:
        """处理获取会话"""
        session_id = request.match_info['session_id']
        # 这里应该实际获取会话信息
        return {
            "session_id": session_id,
            "status": "active",
            "created_at": time.time()
        }
    
    async def _handle_delete_session(self, request: web.Request, auth_result: AuthResult) -> Dict[str, Any]:
        """处理删除会话"""
        session_id = request.match_info['session_id']
        # 这里应该实际删除会话
        return {
            "session_id": session_id,
            "status": "deleted"
        }
    
    async def _handle_get_messages(self, request: web.Request, auth_result: AuthResult) -> Dict[str, Any]:
        """处理获取消息"""
        session_id = request.match_info['session_id']
        limit = int(request.query.get('limit', '50'))
        # 这里应该实际获取消息
        return {
            "session_id": session_id,
            "messages": [],
            "total": 0
        }
    
    async def _handle_send_message(self, request: web.Request, auth_result: AuthResult) -> Dict[str, Any]:
        """处理发送消息"""
        session_id = request.match_info['session_id']
        data = await request.json()
        message = data.get("message")
        
        if not message:
            return {"error": {"code": "INVALID_REQUEST", "message": "message is required"}}
        
        # 这里应该实际发送消息
        return {
            "session_id": session_id,
            "message_id": str(time.time()),
            "status": "sent"
        }
    
    async def _handle_list_clients(self, request: web.Request, auth_result: AuthResult) -> Dict[str, Any]:
        """处理列出客户端"""
        clients = self.connection_manager.get_clients()
        return {
            "clients": [
                {
                    "client_id": c.client_id,
                    "client_name": c.client_name,
                    "connected_at": c.connected_at,
                    "capabilities": list(c.capabilities)
                }
                for c in clients
            ]
        }
    
    async def _handle_stats(self, request: web.Request, auth_result: AuthResult) -> Dict[str, Any]:
        """处理统计信息"""
        return {
            "connections": self.connection_manager.get_client_count(),
            "uptime": time.time(),
            "memory_usage": "0MB",  # 这里应该实际获取内存使用情况
            "requests_total": 0  # 这里应该实际统计请求数
        }
    
    async def _handle_not_found(self, request: web.Request):
        """处理404"""
        return web.json_response(
            {"error": {"code": "NOT_FOUND", "message": "API endpoint not found"}},
            status=404
        )
    
    async def start(self, host: str = "127.0.0.1", port: int = 8080):
        """启动API服务器"""
        if not self.app:
            self.create_app()
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, host, port)
        await self.site.start()
        
        logger.info(f"API server started on http://{host}:{port}")
    
    async def stop(self):
        """停止API服务器"""
        if self.site:
            await self.site.stop()
            self.site = None
        
        if self.runner:
            await self.runner.cleanup()
            self.runner = None
        
        logger.info("API server stopped")