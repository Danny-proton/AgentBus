"""
AgentBus FastAPI Application
AgentBus主应用程序
"""

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .routes import (
    session_router, agent_router, message_router, 
    tool_router, config_router, hitl_router, knowledge_bus_router,
    multi_model_coordinator_router, stream_response_router
)
from ..core.dependencies import (
    startup_event, shutdown_event, 
    get_plugin_manager, get_channel_manager,
    check_services_health
)
from ..plugins.manager import PluginManager
from ..channels.manager import ChannelManager
import logging
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    
    app = FastAPI(
        title="AgentBus",
        description="AI Programming Assistant Server - 基于AgentBus架构的AI助手系统",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应该限制具体域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(session_router)
    app.include_router(agent_router)
    app.include_router(message_router)
    app.include_router(tool_router)
    app.include_router(config_router)
    app.include_router(hitl_router)
    app.include_router(knowledge_bus_router)
    app.include_router(multi_model_coordinator_router)
    app.include_router(stream_response_router)
    
    # 注册插件和渠道管理路由
    from .routes import plugin_router, channel_router
    app.include_router(plugin_router)
    app.include_router(channel_router)
    
    # 健康检查端点
    @app.get("/health")
    async def health_check():
        """健康检查"""
        services_health = await check_services_health()
        
        return {
            "status": "healthy",
            "service": "AgentBus",
            "version": "1.0.0",
            "services": services_health,
            "timestamp": "2026-01-29T11:47:03Z"
        }
    
    # 根端点
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "message": "AgentBus AI Programming Assistant Server",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
            "api_prefix": "/api",
            "management": "/management"
        }
    
    # 管理界面端点
    @app.get("/management")
    async def management_ui():
        """Web管理界面"""
        from ..web.management import MANAGEMENT_HTML
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=MANAGEMENT_HTML)
    
    @app.get("/management.js")
    async def management_js():
        """管理界面JavaScript"""
        from ..web.management import JS_API_CLIENT
        from fastapi.responses import Response
        return Response(
            content=JS_API_CLIENT,
            media_type="application/javascript"
        )
    
    # API信息端点
    @app.get("/api/info")
    async def api_info():
        """API信息"""
        return {
            "name": "AgentBus API",
            "version": "1.0.0",
            "description": "基于AgentBus架构的AI助手系统API",
            "endpoints": {
                "sessions": "/api/sessions",
                "agents": "/api/agents", 
                "messages": "/api/messages",
                "tools": "/api/tools",
                "config": "/api/config",
                "hitl": "/api/v1/hitl",
                "knowledge": "/api/v1/knowledge",
                "multi_model": "/api/v1/multi-model",
                "stream": "/api/v1/stream",
                "plugins": "/api/v1/plugins",
                "channels": "/api/v1/channels"
            },
            "features": [
                "REST API",
                "WebSocket支持",
                "技能系统",
                "工具注册中心",
                "记忆系统",
                "人在回路",
                "知识总线",
                "工作空间管理",
                "多模型协调器",
                "流式响应处理",
                "插件系统",
                "渠道管理"
            ]
        }
    
    # WebSocket端点
    @app.websocket("/ws/agent")
    async def websocket_endpoint(websocket):
        """Agent WebSocket端点"""
        await websocket.accept()
        
        try:
            # 初始化消息
            await websocket.send_json({
                "type": "init",
                "status": "connected",
                "message": "AgentBus WebSocket连接已建立"
            })
            
            # 处理消息
            while True:
                data = await websocket.receive_json()
                
                message_type = data.get("type")
                
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif message_type == "user_message":
                    # 处理用户消息
                    response = {
                        "type": "response",
                        "message": f"收到消息: {data.get('content', '')}",
                        "timestamp": "2026-01-29T11:47:03Z"
                    }
                    await websocket.send_json(response)
                
                elif message_type == "human_request":
                    # 处理人在回路请求
                    request_id = data.get("request_id", "unknown")
                    response = {
                        "type": "human_response",
                        "request_id": request_id,
                        "status": "received",
                        "message": "人在回路请求已接收"
                    }
                    await websocket.send_json(response)
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"未知消息类型: {message_type}"
                    })
        
        except Exception as e:
            logger.error("WebSocket error", error=str(e))
            await websocket.close()
    
    # 错误处理
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        """404错误处理"""
        return JSONResponse(
            status_code=404,
            content={
                "error": "Not Found",
                "message": "请求的资源不存在",
                "path": str(request.url.path)
            }
        )
    
    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc):
        """500错误处理"""
        logger.error("Internal server error", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "服务器内部错误"
            }
        )
    
    # 启动事件
    @app.on_event("startup")
    async def startup():
        """应用启动"""
        logger.info("AgentBus server starting up")
        await startup_event()
    
    @app.on_event("shutdown")
    async def shutdown():
        """应用关闭"""
        logger.info("AgentBus server shutting down")
        await shutdown_event()
    
    return app


def run_server():
    """运行服务器（用于脚本直接调用）"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AgentBus Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    app = create_app()
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    run_server()
