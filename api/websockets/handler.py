"""
WebSocket 消息处理器
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from api.schemas.message import WebSocketMessage, StreamChunk
from services.session_manager import SessionManager


logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """建立连接"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: session_id={session_id}")
    
    def disconnect(self, session_id: str):
        """断开连接"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: session_id={session_id}")
    
    async def send_message(self, session_id: str, message: dict):
        """发送消息到客户端"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message)
    
    async def close(self, session_id: str):
        """关闭连接"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.close()
            self.disconnect(session_id)


# 全局连接管理器
connection_manager = ConnectionManager()


async def agent_ws_handler(
    websocket: WebSocket, 
    session_manager: SessionManager
):
    """Agent WebSocket 主处理器"""
    
    session_id: Optional[str] = None
    
    try:
        # 等待初始化消息
        init_data = await websocket.receive_json()
        
        if init_data.get("type") != "init":
            await websocket.send_json({
                "type": "error",
                "content": "First message must be 'init' type"
            })
            return
        
        session_id = init_data.get("session_id")
        workspace = init_data.get("workspace")
        
        # 创建或获取会话
        if session_id:
            session = await session_manager.get_session(session_id)
            if not session:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Session not found: {session_id}"
                })
                return
        else:
            new_session = await session_manager.create_session(workspace=workspace)
            session_id = new_session.id
            await websocket.send_json({
                "type": "session_created",
                "session_id": session_id
            })
        
        # 建立连接
        await connection_manager.connect(websocket, session_id)
        
        # 主消息循环
        while True:
            try:
                # 设置接收超时
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=300  # 5分钟超时
                )
                
                await handle_message(
                    websocket=websocket,
                    session_id=session_id,
                    data=data,
                    session_manager=session_manager
                )
                
            except asyncio.TimeoutError:
                # 发送心跳
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected by client: {session_id}")
    
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "content": str(e)
        })
    
    finally:
        if session_id:
            connection_manager.disconnect(session_id)


async def handle_message(
    websocket: WebSocket,
    session_id: str,
    data: dict,
    session_manager: SessionManager
):
    """处理 WebSocket 消息"""
    
    message_type = data.get("type")
    
    if message_type == "user_message":
        # 用户消息
        content = data.get("content", "")
        model = data.get("model")
        stream = data.get("stream", True)
        
        session = await session_manager.get_session(session_id)
        
        if stream:
            # 流式响应
            async for chunk in session.process_message(
                content=content,
                model=model,
                stream=True
            ):
                await websocket.send_json({
                    "type": "chunk",
                    "data": chunk.chunk,
                    "done": chunk.done,
                    "session_id": session_id
                })
        else:
            # 非流式响应
            response = await session.process_message(
                content=content,
                model=model,
                stream=False
            )
            
            await websocket.send_json({
                "type": "response",
                "data": response.model_dump(),
                "session_id": session_id
            })
    
    elif message_type == "interrupt":
        # 中断请求
        session = await session_manager.get_session(session_id)
        await session.interrupt()
        
        await websocket.send_json({
            "type": "interrupted",
            "session_id": session_id
        })
    
    elif message_type == "heartbeat":
        # 心跳响应
        await websocket.send_json({
            "type": "heartbeat_ack",
            "timestamp": datetime.now().isoformat()
        })
    
    elif message_type == "approve_tool":
        # 工具执行批准
        call_id = data.get("call_id")
        approved = data.get("approved", True)
        
        session = await session_manager.get_session(session_id)
        await session.approve_tool(call_id, approved)
        
        await websocket.send_json({
            "type": "approval_received",
            "call_id": call_id,
            "approved": approved
        })
    
    else:
        await websocket.send_json({
            "type": "error",
            "content": f"Unknown message type: {message_type}"
        })


async def stream_handler(
    websocket: WebSocket,
    session_id: str,
    session_manager: SessionManager
):
    """专用流式响应处理器"""
    
    await connection_manager.connect(websocket, session_id)
    
    try:
        session = await session_manager.get_session(session_id)
        
        if not session:
            await websocket.send_json({
                "type": "error",
                "content": f"Session not found: {session_id}"
            })
            return
        
        # 等待用户消息
        data = await websocket.receive_json()
        
        if data.get("type") != "user_message":
            await websocket.send_json({
                "type": "error",
                "content": "Expected 'user_message' type"
            })
            return
        
        content = data.get("content", "")
        model = data.get("model")
        
        # 流式处理
        async for chunk in session.process_message(
            content=content,
            model=model,
            stream=True
        ):
            await websocket.send_json({
                "type": "chunk",
                "data": chunk.chunk,
                "done": chunk.done
            })
    
    except WebSocketDisconnect:
        logger.info(f"Stream disconnected: session_id={session_id}")
    
    finally:
        connection_manager.disconnect(session_id)
