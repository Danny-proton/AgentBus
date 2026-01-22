from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from ..core.session import create_session, get_session
from ..core.agent import Agent
import asyncio

router = APIRouter()

class CreateSessionRequest(BaseModel):
    cwd: str = None

class ChatRequest(BaseModel):
    message: str
    session_id: str

@router.post("/session")
async def start_session(req: CreateSessionRequest):
    session = create_session(req.cwd)
    return {"session_id": session.session_id, "cwd": session.cwd}

@router.post("/chat")
async def chat(req: ChatRequest):
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="未找到会话")
    
    agent = Agent(session)
    
    async def event_generator():
        async for chunk in agent.process_message(req.message):
            yield {"data": chunk}
            
    return EventSourceResponse(event_generator())
