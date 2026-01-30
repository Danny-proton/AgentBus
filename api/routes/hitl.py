"""
HITL API 路由
HITL API Routes for AgentBus
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio

from ..schemas.hitl import (
    HITLRequestCreate,
    HITLRequestResponse,
    HITLResponseCreate,
    HITLResponseResponse,
    HITLStatistics,
    ContactCreate,
    ContactResponse,
    ContactMatchRequest,
    ContactMatchResponse
)
from ...services.hitl import HITLService, HITLPriority, HITLStatus
from ...services.communication_map import CommunicationMap
from ...core.dependencies import get_hitl_service, get_communication_map

router = APIRouter(prefix="/hitl", tags=["HITL - 人在回路"])


@router.post("/requests", response_model=HITLRequestResponse)
async def create_hitl_request(
    request_data: HITLRequestCreate,
    hitl_service: HITLService = Depends(get_hitl_service)
):
    """创建人在回路请求"""
    try:
        # 转换优先级
        priority = HITLPriority(request_data.priority)
        
        # 创建HITL请求
        request_id = await hitl_service.create_hitl_request(
            agent_id=request_data.agent_id,
            title=request_data.title,
            description=request_data.description,
            context=request_data.context or {},
            priority=priority,
            timeout_minutes=request_data.timeout_minutes,
            assigned_to=request_data.assigned_to,
            tags=set(request_data.tags) if request_data.tags else set()
        )
        
        # 获取创建的请求
        request = await hitl_service.get_hitl_request(request_id)
        
        return HITLRequestResponse(
            id=request.id,
            agent_id=request.agent_id,
            title=request.title,
            description=request.description,
            context=request.context,
            priority=request.priority.value,
            status=request.status.value,
            created_at=request.created_at,
            timeout_minutes=request.timeout_minutes,
            assigned_to=request.assigned_to,
            response=request.response,
            completed_at=request.completed_at,
            tags=list(request.tags)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建HITL请求失败: {str(e)}")


@router.get("/requests", response_model=List[HITLRequestResponse])
async def list_hitl_requests(
    active_only: bool = Query(True, description="只显示活跃请求"),
    agent_id: Optional[str] = Query(None, description="过滤特定智能体的请求"),
    hitl_service: HITLService = Depends(get_hitl_service)
):
    """列出人在回路请求"""
    try:
        if active_only:
            requests = await hitl_service.list_active_requests()
        else:
            # 这里应该从历史记录中获取所有请求
            requests = await hitl_service.list_active_requests()
        
        # 如果指定了agent_id，过滤结果
        if agent_id:
            requests = [r for r in requests if r.agent_id == agent_id]
        
        return [
            HITLRequestResponse(
                id=r.id,
                agent_id=r.agent_id,
                title=r.title,
                description=r.description,
                context=r.context,
                priority=r.priority.value,
                status=r.status.value,
                created_at=r.created_at,
                timeout_minutes=r.timeout_minutes,
                assigned_to=r.assigned_to,
                response=r.response,
                completed_at=r.completed_at,
                tags=list(r.tags)
            )
            for r in requests
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取HITL请求列表失败: {str(e)}")


@router.get("/requests/{request_id}", response_model=HITLRequestResponse)
async def get_hitl_request(
    request_id: str,
    hitl_service: HITLService = Depends(get_hitl_service)
):
    """获取特定HITL请求详情"""
    try:
        request = await hitl_service.get_hitl_request(request_id)
        
        if not request:
            raise HTTPException(status_code=404, detail="HITL请求不存在")
        
        return HITLRequestResponse(
            id=request.id,
            agent_id=request.agent_id,
            title=request.title,
            description=request.description,
            context=request.context,
            priority=request.priority.value,
            status=request.status.value,
            created_at=request.created_at,
            timeout_minutes=request.timeout_minutes,
            assigned_to=request.assigned_to,
            response=request.response,
            completed_at=request.completed_at,
            tags=list(request.tags)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取HITL请求详情失败: {str(e)}")


@router.post("/requests/{request_id}/responses", response_model=HITLResponseResponse)
async def submit_hitl_response(
    request_id: str,
    response_data: HITLResponseCreate,
    hitl_service: HITLService = Depends(get_hitl_service)
):
    """提交HITL响应"""
    try:
        success = await hitl_service.submit_hitl_response(
            request_id=request_id,
            responder_id=response_data.responder_id,
            content=response_data.content,
            is_final=response_data.is_final,
            attachments=response_data.attachments or []
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="HITL请求不存在或已结束")
        
        return HITLResponseResponse(
            request_id=request_id,
            responder_id=response_data.responder_id,
            content=response_data.content,
            created_at=datetime.now(),
            is_final=response_data.is_final,
            attachments=response_data.attachments or []
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交HITL响应失败: {str(e)}")


@router.post("/requests/{request_id}/cancel")
async def cancel_hitl_request(
    request_id: str,
    reason: Optional[str] = Query(None, description="取消原因"),
    hitl_service: HITLService = Depends(get_hitl_service)
):
    """取消HITL请求"""
    try:
        success = await hitl_service.cancel_hitl_request(request_id, reason)
        
        if not success:
            raise HTTPException(status_code=404, detail="HITL请求不存在")
        
        return {"message": "HITL请求已取消", "request_id": request_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消HITL请求失败: {str(e)}")


@router.get("/statistics", response_model=HITLStatistics)
async def get_hitl_statistics(
    hitl_service: HITLService = Depends(get_hitl_service)
):
    """获取HITL统计信息"""
    try:
        stats = await hitl_service.get_hitl_statistics()
        return HITLStatistics(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取HITL统计信息失败: {str(e)}")


@router.get("/contacts", response_model=List[ContactResponse])
async def list_contacts(
    role: Optional[str] = Query(None, description="过滤特定角色的联系人"),
    expertise: Optional[str] = Query(None, description="过滤特定专业技能的联系人"),
    active_only: bool = Query(True, description="只显示活跃联系人"),
    communication_map: CommunicationMap = Depends(get_communication_map)
):
    """列出联系人"""
    try:
        contacts = await communication_map.list_contacts(
            role=role,
            expertise=expertise,
            active_only=active_only
        )
        
        return [
            ContactResponse(
                id=c.id,
                name=c.name,
                role=c.role,
                expertise=list(c.expertise),
                availability=c.availability,
                contact_methods=c.contact_methods,
                timezone=c.timezone,
                language=c.language,
                priority_score=c.priority_score,
                active=c.active,
                tags=list(c.tags),
                last_active=c.last_active,
                response_time_estimate=c.response_time_estimate
            )
            for c in contacts
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取联系人列表失败: {str(e)}")


@router.post("/contacts", response_model=ContactResponse)
async def add_contact(
    contact_data: ContactCreate,
    communication_map: CommunicationMap = Depends(get_communication_map)
):
    """添加联系人"""
    try:
        from ..services.communication_map import Contact
        
        contact = Contact(
            id=contact_data.id,
            name=contact_data.name,
            role=contact_data.role,
            expertise=set(contact_data.expertise) if contact_data.expertise else set(),
            availability=contact_data.availability,
            contact_methods=contact_data.contact_methods,
            timezone=contact_data.timezone,
            language=contact_data.language,
            priority_score=contact_data.priority_score,
            active=contact_data.active,
            tags=set(contact_data.tags) if contact_data.tags else set(),
            response_time_estimate=contact_data.response_time_estimate
        )
        
        success = await communication_map.add_contact(contact)
        
        if not success:
            raise HTTPException(status_code=400, detail="添加联系人失败")
        
        return ContactResponse(
            id=contact.id,
            name=contact.name,
            role=contact.role,
            expertise=list(contact.expertise),
            availability=contact.availability,
            contact_methods=contact.contact_methods,
            timezone=contact.timezone,
            language=contact.language,
            priority_score=contact.priority_score,
            active=contact.active,
            tags=list(contact.tags),
            last_active=contact.last_active,
            response_time_estimate=contact.response_time_estimate
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加联系人失败: {str(e)}")


@router.post("/contacts/match", response_model=ContactMatchResponse)
async def match_contacts(
    match_request: ContactMatchRequest,
    communication_map: CommunicationMap = Depends(get_communication_map)
):
    """智能匹配联系人"""
    try:
        contact_ids = await communication_map.find_contacts_by_context(
            context=match_request.context,
            priority=match_request.priority,
            max_results=match_request.max_results
        )
        
        matched_contacts = []
        for contact_id in contact_ids:
            contact = await communication_map.get_contact(contact_id)
            if contact:
                matched_contacts.append(
                    ContactResponse(
                        id=contact.id,
                        name=contact.name,
                        role=contact.role,
                        expertise=list(contact.expertise),
                        availability=contact.availability,
                        contact_methods=contact.contact_methods,
                        timezone=contact.timezone,
                        language=contact.language,
                        priority_score=contact.priority_score,
                        active=contact.active,
                        tags=list(contact.tags),
                        last_active=contact.last_active,
                        response_time_estimate=contact.response_time_estimate
                    )
                )
        
        return ContactMatchResponse(
            matches=matched_contacts,
            total_found=len(matched_contacts)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"联系人匹配失败: {str(e)}")


@router.get("/contacts/stats")
async def get_contact_statistics(
    communication_map: CommunicationMap = Depends(get_communication_map)
):
    """获取联系人统计信息"""
    try:
        stats = await communication_map.get_contact_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取联系人统计信息失败: {str(e)}")
