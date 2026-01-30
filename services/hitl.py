"""
人在回路 (HITL) 服务
Human-in-the-Loop service for AgentBus

本模块实现人在回路系统，允许AI代理在需要时向人类寻求帮助，
并与消息通道系统深度融合。

此服务现在作为插件的基础服务，可以通过HITLPlugin插件模式使用，
同时保持与原有服务的完全兼容性。
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from loguru import logger

from .communication_map import CommunicationMap
from .message_channel import MessageChannel
from ..core.settings import settings


class HITLStatus(Enum):
    """人在回路状态枚举"""
    PENDING = "pending"          # 等待人类响应
    IN_PROGRESS = "in_progress" # 人类正在处理
    COMPLETED = "completed"     # 人类已完成
    TIMEOUT = "timeout"         # 超时
    CANCELLED = "cancelled"     # 已取消


class HITLPriority(Enum):
    """人在回路优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class HITLRequest:
    """人在回路请求数据结构"""
    id: str
    agent_id: str
    title: str
    description: str
    context: Dict[str, Any]
    priority: HITLPriority
    created_at: datetime
    timeout_minutes: int = 30
    assigned_to: Optional[str] = None
    status: HITLStatus = HITLStatus.PENDING
    response: Optional[str] = None
    completed_at: Optional[datetime] = None
    tags: Set[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = set()
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class HITLResponse:
    """人在回路响应数据结构"""
    request_id: str
    responder_id: str
    content: str
    created_at: datetime
    is_final: bool = True
    attachments: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


class HITLService:
    """人在回路服务核心类"""
    
    def __init__(self):
        self.active_requests: Dict[str, HITLRequest] = {}
        self.request_history: Dict[str, HITLRequest] = {}
        self.communication_map = CommunicationMap()
        self.message_channel = MessageChannel()
        self._request_timeout_tasks: Dict[str, asyncio.Task] = {}
        
        logger.info("HITL服务初始化完成")
    
    async def create_hitl_request(
        self,
        agent_id: str,
        title: str,
        description: str,
        context: Dict[str, Any] = None,
        priority: HITLPriority = HITLPriority.MEDIUM,
        timeout_minutes: int = 30,
        assigned_to: str = None,
        tags: Set[str] = None
    ) -> str:
        """创建人在回路请求"""
        
        # 创建请求
        request = HITLRequest(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            title=title,
            description=description,
            context=context or {},
            priority=priority,
            created_at=datetime.now(),
            timeout_minutes=timeout_minutes,
            assigned_to=assigned_to,
            status=HITLStatus.PENDING,
            tags=tags or set()
        )
        
        # 存储请求
        self.active_requests[request.id] = request
        
        # 发送到消息通道
        await self._send_hitl_notification(request)
        
        # 设置超时任务
        await self._schedule_timeout(request)
        
        logger.info(f"HITL请求创建成功: {request.id} - {title}")
        return request.id
    
    async def submit_hitl_response(
        self,
        request_id: str,
        responder_id: str,
        content: str,
        is_final: bool = True,
        attachments: List[Dict[str, Any]] = None
    ) -> bool:
        """提交人在回路响应"""
        
        # 检查请求是否存在
        if request_id not in self.active_requests:
            logger.warning(f"HITL请求不存在: {request_id}")
            return False
        
        request = self.active_requests[request_id]
        
        # 创建响应
        response = HITLResponse(
            request_id=request_id,
            responder_id=responder_id,
            content=content,
            created_at=datetime.now(),
            is_final=is_final,
            attachments=attachments or []
        )
        
        # 更新请求状态
        request.status = HITLStatus.COMPLETED
        request.response = content
        request.completed_at = datetime.now()
        
        # 取消超时任务
        if request_id in self._request_timeout_tasks:
            self._request_timeout_tasks[request_id].cancel()
            del self._request_timeout_tasks[request_id]
        
        # 移动到历史记录
        self.request_history[request_id] = request
        del self.active_requests[request_id]
        
        # 发送响应通知
        await self._send_hitl_response_notification(request, response)
        
        logger.info(f"HITL响应提交成功: {request_id}")
        return True
    
    async def get_hitl_request(self, request_id: str) -> Optional[HITLRequest]:
        """获取人在回路请求详情"""
        return self.active_requests.get(request_id) or self.request_history.get(request_id)
    
    async def list_active_requests(self) -> List[HITLRequest]:
        """列出所有活跃的HITL请求"""
        return list(self.active_requests.values())
    
    async def list_user_requests(self, user_id: str) -> List[HITLRequest]:
        """列出指定用户的所有HITL请求"""
        user_requests = []
        for request in list(self.active_requests.values()) + list(self.request_history.values()):
            if request.assigned_to == user_id:
                user_requests.append(request)
        return user_requests
    
    async def cancel_hitl_request(self, request_id: str, reason: str = None) -> bool:
        """取消人在回路请求"""
        
        if request_id not in self.active_requests:
            return False
        
        request = self.active_requests[request_id]
        request.status = HITLStatus.CANCELLED
        
        # 取消超时任务
        if request_id in self._request_timeout_tasks:
            self._request_timeout_tasks[request_id].cancel()
            del self._request_timeout_tasks[request_id]
        
        # 移动到历史记录
        self.request_history[request_id] = request
        del self.active_requests[request_id]
        
        # 发送取消通知
        await self._send_hitl_cancellation_notification(request, reason)
        
        logger.info(f"HITL请求已取消: {request_id}")
        return True
    
    async def get_hitl_statistics(self) -> Dict[str, Any]:
        """获取HITL统计信息"""
        active_count = len(self.active_requests)
        total_count = len(self.request_history)
        
        completed_count = len([
            r for r in self.request_history.values()
            if r.status == HITLStatus.COMPLETED
        ])
        
        timeout_count = len([
            r for r in self.request_history.values()
            if r.status == HITLStatus.TIMEOUT
        ])
        
        return {
            "active_requests": active_count,
            "total_requests": total_count,
            "completed_requests": completed_count,
            "timeout_requests": timeout_count,
            "completion_rate": completed_count / total_count if total_count > 0 else 0
        }
    
    async def _send_hitl_notification(self, request: HITLRequest):
        """发送HITL请求通知"""
        
        # 标记为HITL调用
        enhanced_context = request.context.copy()
        enhanced_context["hitl_request"] = {
            "id": request.id,
            "title": request.title,
            "priority": request.priority.value,
            "is_hitl": True
        }
        
        # 确定接收者
        if request.assigned_to:
            recipients = [request.assigned_to]
        else:
            # 从沟通地图中获取合适的联系人
            recipients = await self.communication_map.find_contacts_by_context(
                request.context, request.priority.value
            )
        
        # 发送消息
        message_data = {
            "type": "hitl_request",
            "data": {
                "request_id": request.id,
                "agent_id": request.agent_id,
                "title": request.title,
                "description": request.description,
                "priority": request.priority.value,
                "created_at": request.created_at.isoformat(),
                "timeout_minutes": request.timeout_minutes,
                "tags": list(request.tags)
            }
        }
        
        await self.message_channel.broadcast_message(
            message_type="hitl_request",
            content=message_data,
            recipients=recipients,
            priority=request.priority.value
        )
    
    async def _send_hitl_response_notification(
        self, 
        request: HITLRequest, 
        response: HITLResponse
    ):
        """发送HITL响应通知"""
        
        message_data = {
            "type": "hitl_response",
            "data": {
                "request_id": request.id,
                "responder_id": response.responder_id,
                "content": response.content,
                "is_final": response.is_final,
                "created_at": response.created_at.isoformat(),
                "attachments": response.attachments
            }
        }
        
        await self.message_channel.send_message_to_agent(
            agent_id=request.agent_id,
            message_type="hitl_response",
            content=message_data
        )
    
    async def _send_hitl_cancellation_notification(
        self, 
        request: HITLRequest, 
        reason: str
    ):
        """发送HITL取消通知"""
        
        message_data = {
            "type": "hitl_cancellation",
            "data": {
                "request_id": request.id,
                "reason": reason,
                "cancelled_at": datetime.now().isoformat()
            }
        }
        
        await self.message_channel.send_message_to_agent(
            agent_id=request.agent_id,
            message_type="hitl_cancellation",
            content=message_data
        )
    
    async def _schedule_timeout(self, request: HITLRequest):
        """设置超时任务"""
        
        async def timeout_handler():
            await asyncio.sleep(request.timeout_minutes * 60)
            
            if request.id in self.active_requests:
                request.status = HITLStatus.TIMEOUT
                request.completed_at = datetime.now()
                
                # 移动到历史记录
                self.request_history[request.id] = request
                del self.active_requests[request.id]
                
                # 发送超时通知
                await self._send_hitl_timeout_notification(request)
                
                logger.warning(f"HITL请求已超时: {request.id}")
        
        task = asyncio.create_task(timeout_handler())
        self._request_timeout_tasks[request.id] = task
    
    async def _send_hitl_timeout_notification(self, request: HITLRequest):
        """发送超时通知"""
        
        message_data = {
            "type": "hitl_timeout",
            "data": {
                "request_id": request.id,
                "title": request.title,
                "timeout_minutes": request.timeout_minutes,
                "timed_out_at": datetime.now().isoformat()
            }
        }
        
        await self.message_channel.send_message_to_agent(
            agent_id=request.agent_id,
            message_type="hitl_timeout",
            content=message_data
        )
    
    async def start(self):
        """启动HITL服务"""
        await self.communication_map.load()
        await self.message_channel.initialize()
        logger.info("HITL服务已启动")
    
    async def stop(self):
        """停止HITL服务"""
        # 取消所有超时任务
        for task in self._request_timeout_tasks.values():
            task.cancel()
        self._request_timeout_tasks.clear()
        
        await self.message_channel.close()
        logger.info("HITL服务已停止")
