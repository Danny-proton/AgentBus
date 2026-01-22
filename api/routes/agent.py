"""
Agent 控制路由
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from sse_starlette.sse import EventSourceResponse

from api.schemas.message import (
    AgentRequest,
    AgentResponse,
    Message
)
from services.session_manager import SessionManager, get_session_manager


agent_router = APIRouter(prefix="/agent", tags=["Agent"])


@agent_router.post("/request", response_model=AgentResponse)
async def agent_request(
    request: AgentRequest,
    manager: SessionManager = Depends(get_session_manager)
) -> AgentResponse:
    """发送 Agent 请求（非流式）"""
    session = await manager.get_session(request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 执行 Agent 处理
    response_message = await session.process_message(
        content=request.message,
        model=request.model,
        stream=False
    )
    
    return AgentResponse(
        session_id=request.session_id,
        message=response_message
    )


@agent_router.get("/stream/{session_id}")
async def stream_agent(
    session_id: str,
    message: str = Query(..., description="用户消息"),
    model: Optional[str] = Query(None, description="指定模型"),
    manager: SessionManager = Depends(get_session_manager)
) -> EventSourceResponse:
    """流式 Agent 响应"""
    session = await manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    async def event_generator():
        async for chunk in session.process_message(
            content=message,
            model=model,
            stream=True
        ):
            yield {
                "data": chunk.json(),
                "event": "chunk" if not chunk.done else "done"
            }
    
    return EventSourceResponse(event_generator())


@agent_router.post("/interrupt/{session_id}")
async def interrupt_agent(
    session_id: str,
    manager: SessionManager = Depends(get_session_manager)
) -> dict:
    """中断当前 Agent 操作"""
    session = await manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await session.interrupt()
    
    return {"status": "interrupted", "session_id": session_id}


@agent_router.get("/cost/{session_id}")
async def get_cost(
    session_id: str,
    manager: SessionManager = Depends(get_session_manager)
):
    """获取会话成本统计"""
    session = await manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    cost_summary = await session.get_cost_summary()
    
    return cost_summary


@agent_router.post("/model/{session_id}")
async def switch_model(
    session_id: str,
    model: str = Query(..., description="新模型名称"),
    manager: SessionManager = Depends(get_session_manager)
) -> dict:
    """切换模型"""
    session = await manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await session.switch_model(model)
    
    return {
        "status": "success",
        "session_id": session_id,
        "new_model": model
    }
