"""
会话管理路由
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from uuid import uuid4

from api.schemas.message import (
    SessionCreate,
    SessionResponse,
    SessionDetail,
    SessionStatus
)
from services.session_manager import SessionManager, get_session_manager


session_router = APIRouter(prefix="/sessions", tags=["Sessions"])


@session_router.post("", response_model=SessionResponse)
async def create_session(
    request: SessionCreate,
    manager: SessionManager = Depends(get_session_manager)
) -> SessionResponse:
    """创建新会话"""
    session = await manager.create_session(
        workspace=request.workspace,
        model=request.model,
        system_prompt=request.system_prompt
    )
    
    return SessionResponse(
        id=session.id,
        status=SessionStatus.ACTIVE,
        workspace=session.workspace,
        current_model=session.current_model,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(session.messages)
    )


@session_router.get("", response_model=List[SessionResponse])
async def list_sessions(
    manager: SessionManager = Depends(get_session_manager)
) -> List[SessionResponse]:
    """列出所有会话"""
    sessions = await manager.list_sessions()
    
    return [
        SessionResponse(
            id=s.id,
            status=s.status,
            workspace=s.workspace,
            current_model=s.current_model,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=len(s.messages)
        )
        for s in sessions
    ]


@session_router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    manager: SessionManager = Depends(get_session_manager)
) -> SessionDetail:
    """获取会话详情"""
    session = await manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionDetail(
        id=session.id,
        status=session.status,
        workspace=session.workspace,
        current_model=session.current_model,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(session.messages),
        messages=session.messages,
        system_prompt=session.system_prompt
    )


@session_router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    manager: SessionManager = Depends(get_session_manager)
) -> dict:
    """删除会话"""
    success = await manager.delete_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "deleted", "session_id": session_id}


@session_router.post("/{session_id}/clear")
async def clear_session(
    session_id: str,
    manager: SessionManager = Depends(get_session_manager)
) -> SessionDetail:
    """清除会话消息"""
    session = await manager.clear_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionDetail(
        id=session.id,
        status=session.status,
        workspace=session.workspace,
        current_model=session.current_model,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(session.messages),
        messages=session.messages,
        system_prompt=session.system_prompt
    )


@session_router.post("/{session_id}/compact")
async def compact_session(
    session_id: str,
    threshold: float = 0.85,
    manager: SessionManager = Depends(get_session_manager)
) -> dict:
    """压缩会话上下文"""
    success = await manager.compact_session(session_id, threshold)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "compacted", "session_id": session_id}
