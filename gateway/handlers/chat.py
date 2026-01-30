"""
Gateway Chat Handler

基于Moltbot的聊天处理模块，实现完整的聊天功能
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
from collections import defaultdict, deque

from ..protocol import ProtocolHandler, RequestFrame, ResponseFrame, EventFrame, ErrorCode
from .base import BaseHandler

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatState(Enum):
    """聊天状态"""
    IDLE = "idle"
    PROCESSING = "processing"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"
    ABORTED = "aborted"


@dataclass
class ChatMessage:
    """聊天消息"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: str = MessageRole.USER.value
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    tokens: Optional[int] = None
    model: Optional[str] = None


@dataclass
class ChatSession:
    """聊天会话"""
    session_id: str
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    state: ChatState = ChatState.IDLE
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatRun:
    """聊天运行"""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    status: ChatState = ChatState.PROCESSING
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    current_message: Optional[ChatMessage] = None
    response_stream: Optional[asyncio.Queue] = None
    abort_event: Optional[asyncio.Event] = None


class ChatManager:
    """聊天管理器"""
    
    def __init__(self, protocol_handler: ProtocolHandler):
        self.protocol_handler = protocol_handler
        self.sessions: Dict[str, ChatSession] = {}
        self.active_runs: Dict[str, ChatRun] = {}
        self.session_limits = {
            "max_messages": 1000,
            "max_tokens": 100000,
            "max_sessions_per_client": 100
        }
        self.message_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.lock = threading.RLock()
    
    def create_session(self, session_id: str, client_id: str) -> ChatSession:
        """创建聊天会话"""
        with self.lock:
            # 检查会话数量限制
            client_sessions = [s for s in self.sessions.values() 
                             if s.metadata.get("client_id") == client_id]
            if len(client_sessions) >= self.session_limits["max_sessions_per_client"]:
                # 清理最旧的会话
                oldest_session = min(client_sessions, key=lambda s: s.updated_at)
                self.delete_session(oldest_session.session_id)
            
            session = ChatSession(
                session_id=session_id,
                metadata={"client_id": client_id}
            )
            self.sessions[session_id] = session
            return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取聊天会话"""
        return self.sessions.get(session_id)
    
    def delete_session(self, session_id: str):
        """删除聊天会话"""
        with self.lock:
            # 取消活跃的运行
            active_runs = [r for r in self.active_runs.values() if r.session_id == session_id]
            for run in active_runs:
                if run.abort_event:
                    run.abort_event.set()
                run.status = ChatState.ABORTED
            
            # 删除会话
            self.sessions.pop(session_id, None)
            self.message_history.pop(session_id, None)
    
    def add_message(self, session_id: str, message: ChatMessage):
        """添加消息到会话"""
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")
            
            session.messages.append(message)
            session.updated_at = time.time()
            
            # 记录到历史
            self.message_history[session_id].append(message)
            
            # 检查消息限制
            if len(session.messages) > self.session_limits["max_messages"]:
                # 移除旧消息但保留系统消息
                system_messages = [m for m in session.messages if m.role == MessageRole.SYSTEM.value]
                session.messages = system_messages + session.messages[-self.session_limits["max_messages"]+len(system_messages):]
    
    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        """获取会话消息"""
        session = self.sessions.get(session_id)
        if not session:
            return []
        
        messages = session.messages
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def create_run(self, session_id: str) -> ChatRun:
        """创建聊天运行"""
        run = ChatRun(session_id=session_id)
        self.active_runs[run.run_id] = run
        return run
    
    def complete_run(self, run_id: str, status: ChatState = ChatState.COMPLETED):
        """完成聊天运行"""
        run = self.active_runs.pop(run_id, None)
        if run:
            run.status = status
            run.end_time = time.time()
    
    def abort_run(self, run_id: str):
        """中止聊天运行"""
        run = self.active_runs.get(run_id)
        if run and run.abort_event:
            run.abort_event.set()
            run.status = ChatState.ABORTED
    
    def get_active_run(self, session_id: str) -> Optional[ChatRun]:
        """获取会话的活跃运行"""
        for run in self.active_runs.values():
            if run.session_id == session_id:
                return run
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取聊天统计"""
        with self.lock:
            return {
                "total_sessions": len(self.sessions),
                "active_runs": len(self.active_runs),
                "sessions": [
                    {
                        "session_id": s.session_id,
                        "message_count": len(s.messages),
                        "created_at": s.created_at,
                        "updated_at": s.updated_at,
                        "state": s.state.value
                    }
                    for s in self.sessions.values()
                ]
            }


class ChatHandler(BaseHandler):
    """聊天处理器"""
    
    def __init__(self, protocol_handler: ProtocolHandler):
        super().__init__(protocol_handler)
        self.chat_manager = ChatManager(protocol_handler)
    
    async def handle_request(self, frame: RequestFrame) -> ResponseFrame:
        """处理聊天请求"""
        if frame.method == "chat.send":
            return await self._handle_chat_send(frame)
        elif frame.method == "chat.history":
            return await self._handle_chat_history(frame)
        elif frame.method == "chat.abort":
            return await self._handle_chat_abort(frame)
        elif frame.method == "chat.sessions.list":
            return await self._handle_list_sessions(frame)
        elif frame.method == "chat.sessions.create":
            return await self._handle_create_session(frame)
        elif frame.method == "chat.sessions.delete":
            return await self._handle_delete_session(frame)
        else:
            return await super().handle_request(frame)
    
    async def _handle_chat_send(self, frame: RequestFrame) -> ResponseFrame:
        """处理聊天发送"""
        params = frame.params or {}
        session_id = params.get("session_id")
        message_content = params.get("message", "")
        message_type = params.get("type", "text")
        
        if not session_id:
            return self.protocol_handler.create_error_response(
                frame.id,
                ErrorCode.INVALID_REQUEST,
                "session_id is required"
            )
        
        if not message_content:
            return self.protocol_handler.create_error_response(
                frame.id,
                ErrorCode.INVALID_REQUEST,
                "message is required"
            )
        
        try:
            # 创建或获取会话
            session = self.chat_manager.get_session(session_id)
            if not session:
                # 假设客户端ID从上下文中获取
                client_id = params.get("client_id", "unknown")
                session = self.chat_manager.create_session(session_id, client_id)
            
            # 检查是否有活跃的运行
            active_run = self.chat_manager.get_active_run(session_id)
            if active_run:
                return self.protocol_handler.create_error_response(
                    frame.id,
                    ErrorCode.CONFLICT,
                    "Session is already processing a message"
                )
            
            # 创建用户消息
            user_message = ChatMessage(
                role=MessageRole.USER.value,
                content=message_content,
                metadata={"type": message_type}
            )
            
            # 添加消息到会话
            self.chat_manager.add_message(session_id, user_message)
            
            # 创建运行
            run = self.chat_manager.create_run(session_id)
            run.response_stream = asyncio.Queue()
            run.abort_event = asyncio.Event()
            
            # 启动异步处理
            asyncio.create_task(self._process_chat_message(session_id, run.run_id, user_message))
            
            # 返回运行ID
            return self.protocol_handler.create_response(
                frame.id,
                payload={
                    "run_id": run.run_id,
                    "status": "started",
                    "message_id": user_message.message_id
                }
            )
            
        except Exception as e:
            logger.error(f"Chat send error: {e}")
            return self.protocol_handler.create_error_response(
                frame.id,
                ErrorCode.INTERNAL_ERROR,
                f"Internal error: {str(e)}"
            )
    
    async def _process_chat_message(self, session_id: str, run_id: str, user_message: ChatMessage):
        """异步处理聊天消息"""
        try:
            run = self.chat_manager.active_runs.get(run_id)
            if not run:
                return
            
            # 模拟AI处理延迟
            await asyncio.sleep(1)
            
            # 创建助手回复
            assistant_message = ChatMessage(
                role=MessageRole.ASSISTANT.value,
                content=f"Echo: {user_message.content}",
                metadata={"model": "echo-model"}
            )
            
            # 添加助手消息
            self.chat_manager.add_message(session_id, assistant_message)
            run.current_message = assistant_message
            
            # 发送流式响应（模拟）
            await self._send_streaming_response(session_id, run_id, assistant_message)
            
            # 完成运行
            self.chat_manager.complete_run(run_id, ChatState.COMPLETED)
            
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            self.chat_manager.complete_run(run_id, ChatState.ERROR)
    
    async def _send_streaming_response(self, session_id: str, run_id: str, message: ChatMessage):
        """发送流式响应"""
        # 模拟流式发送
        content = message.content
        words = content.split()
        
        for i, word in enumerate(words):
            if run_id not in self.chat_manager.active_runs:
                break  # 运行已被中止
            
            # 发送部分内容
            partial_content = " ".join(words[:i+1])
            
            # 发送流式事件
            stream_event = self.protocol_handler.create_event(
                "chat.stream",
                {
                    "run_id": run_id,
                    "session_id": session_id,
                    "content": partial_content,
                    "delta": word + (" " if i < len(words) - 1 else ""),
                    "done": i == len(words) - 1
                }
            )
            
            # 这里应该发送到实际的客户端
            # 在实际实现中，需要通过连接管理器广播
            logger.debug(f"Streaming to {session_id}: {partial_content}")
            
            await asyncio.sleep(0.1)  # 模拟流式延迟
    
    async def _handle_chat_history(self, frame: RequestFrame) -> ResponseFrame:
        """处理聊天历史"""
        params = frame.params or {}
        session_id = params.get("session_id")
        limit = params.get("limit")
        
        if not session_id:
            return self.protocol_handler.create_error_response(
                frame.id,
                ErrorCode.INVALID_REQUEST,
                "session_id is required"
            )
        
        try:
            messages = self.chat_manager.get_messages(session_id, limit)
            
            # 转换为协议格式
            protocol_messages = [
                {
                    "message_id": msg.message_id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "metadata": msg.metadata
                }
                for msg in messages
            ]
            
            return self.protocol_handler.create_response(
                frame.id,
                payload={
                    "session_id": session_id,
                    "messages": protocol_messages,
                    "total": len(messages)
                }
            )
            
        except Exception as e:
            logger.error(f"Chat history error: {e}")
            return self.protocol_handler.create_error_response(
                frame.id,
                ErrorCode.INTERNAL_ERROR,
                f"Internal error: {str(e)}"
            )
    
    async def _handle_chat_abort(self, frame: RequestFrame) -> ResponseFrame:
        """处理聊天中止"""
        params = frame.params or {}
        run_id = params.get("run_id")
        
        if not run_id:
            return self.protocol_handler.create_error_response(
                frame.id,
                ErrorCode.INVALID_REQUEST,
                "run_id is required"
            )
        
        try:
            self.chat_manager.abort_run(run_id)
            
            return self.protocol_handler.create_response(
                frame.id,
                payload={
                    "run_id": run_id,
                    "status": "aborted"
                }
            )
            
        except Exception as e:
            logger.error(f"Chat abort error: {e}")
            return self.protocol_handler.create_error_response(
                frame.id,
                ErrorCode.INTERNAL_ERROR,
                f"Internal error: {str(e)}"
            )
    
    async def _handle_list_sessions(self, frame: RequestFrame) -> ResponseFrame:
        """处理列出会话"""
        try:
            stats = self.chat_manager.get_stats()
            
            return self.protocol_handler.create_response(
                frame.id,
                payload=stats
            )
            
        except Exception as e:
            logger.error(f"List sessions error: {e}")
            return self.protocol_handler.create_error_response(
                frame.id,
                ErrorCode.INTERNAL_ERROR,
                f"Internal error: {str(e)}"
            )
    
    async def _handle_create_session(self, frame: RequestFrame) -> ResponseFrame:
        """处理创建会话"""
        params = frame.params or {}
        session_id = params.get("session_id")
        client_id = params.get("client_id", "unknown")
        
        if not session_id:
            return self.protocol_handler.create_error_response(
                frame.id,
                ErrorCode.INVALID_REQUEST,
                "session_id is required"
            )
        
        try:
            session = self.chat_manager.create_session(session_id, client_id)
            
            return self.protocol_handler.create_response(
                frame.id,
                payload={
                    "session_id": session.session_id,
                    "created_at": session.created_at
                }
            )
            
        except Exception as e:
            logger.error(f"Create session error: {e}")
            return self.protocol_handler.create_error_response(
                frame.id,
                ErrorCode.INTERNAL_ERROR,
                f"Internal error: {str(e)}"
            )
    
    async def _handle_delete_session(self, frame: RequestFrame) -> ResponseFrame:
        """处理删除会话"""
        params = frame.params or {}
        session_id = params.get("session_id")
        
        if not session_id:
            return self.protocol_handler.create_error_response(
                frame.id,
                ErrorCode.INVALID_REQUEST,
                "session_id is required"
            )
        
        try:
            self.chat_manager.delete_session(session_id)
            
            return self.protocol_handler.create_response(
                frame.id,
                payload={
                    "session_id": session_id,
                    "status": "deleted"
                }
            )
            
        except Exception as e:
            logger.error(f"Delete session error: {e}")
            return self.protocol_handler.create_error_response(
                frame.id,
                ErrorCode.INTERNAL_ERROR,
                f"Internal error: {str(e)}"
            )