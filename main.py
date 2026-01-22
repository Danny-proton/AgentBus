"""
AgentBus Python 实现
AI Programming Assistant - Server Edition

主要入口文件，启动 FastAPI 服务
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from api.routes import session_router, agent_router, config_router
from api.websockets.handler import agent_ws_handler
from config.settings import get_settings
from core.memory.short_term import ShortTermMemory
from services.session_manager import SessionManager
from services.cost_tracker import CostTracker
from services.log_service import init_log_service, start_log_service, stop_log_service, get_log_service
from services.workspace import init_workspace, get_workspace
from tools.knowledge_bus import init_knowledge_bus, get_knowledge_bus
from tools.human_in_loop import get_human_loop

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 全局服务实例
session_manager: SessionManager = None
cost_tracker: CostTracker = None
short_term_memory: ShortTermMemory = None


async def lifespan(app: FastAPI) -> AsyncGenerator:
    """应用生命周期管理"""
    global session_manager, cost_tracker, short_term_memory
    
    logger.info("🚀 启动 AgentBus 服务...")
    
    # 初始化服务
    settings = get_settings()
    
    # 1. 初始化工作空间
    workspace = init_workspace(settings.workspace.path)
    logger.info(f"✅ 工作空间初始化: {workspace.get_path()}")
    
    # 2. 初始化日志服务
    log_service = init_log_service(
        workspace.get_logs_path(),
        enabled=settings.logging.enabled
    )
    await start_log_service()
    logger.info("✅ 日志服务已启动")
    
    # 3. 初始化知识总线
    knowledge_bus = init_knowledge_bus(settings.workspace.path)
    logger.info(f"✅ 知识总线已初始化: {knowledge_bus.get_path()}")
    
    # 4. 初始化内存
    short_term_memory = ShortTermMemory(max_messages=settings.memory.max_messages)
    
    # 5. 初始化成本跟踪
    cost_tracker = CostTracker()
    
    # 6. 初始化会话管理器
    session_manager = SessionManager(
        memory=short_term_memory,
        cost_tracker=cost_tracker,
        workspace=workspace,
        knowledge_bus=knowledge_bus,
        log_service=log_service
    )
    
    logger.info("✅ 所有服务启动完成")
    
    yield
    
    # 清理资源
    logger.info("🛑 正在关闭服务...")
    
    # 停止日志服务
    await stop_log_service()
    
    # 清理会话
    await session_manager.shutdown()
    
    logger.info("✅ 服务已关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    
    app = FastAPI(
        title="AgentBus AI Assistant API",
        description="AI 编程助手服务端 API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )
    
    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制为特定域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(session_router, prefix="/api")
    app.include_router(agent_router, prefix="/api")
    app.include_router(config_router, prefix="/api")
    
    # WebSocket 端点
    @app.websocket("/ws/agent")
    async def websocket_endpoint(websocket):
        """Agent WebSocket 处理器"""
        await agent_ws_handler(websocket, session_manager)
    
    @app.websocket("/ws/stream/{session_id}")
    async def stream_endpoint(websocket, session_id: str):
        """会话流式响应端点"""
        from api.websockets.handler import stream_handler
        await stream_handler(websocket, session_id, session_manager)
    
    # 健康检查
    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        return {"status": "healthy", "service": "agentbus-core"}
    
    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """全局异常处理器"""
        logger.exception(f"未处理的异常: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": str(exc)}
        )
    
    # 挂载静态文件目录（前端页面）
    try:
        app.mount("/", StaticFiles(directory="static", html=True), name="static")
        logger.info("✅ 静态文件服务已挂载到根路径")
    except Exception as e:
        logger.warning(f"⚠️ 静态文件目录不存在或无法访问: {e}")
    
    return app


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        log_level=settings.server.log_level
    )
