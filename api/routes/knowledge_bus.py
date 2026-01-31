"""
知识总线 API 路由
Knowledge Bus API Routes
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime

from api.schemas.knowledge_bus import (
    KnowledgeCreate,
    KnowledgeResponse,
    KnowledgeUpdate,
    KnowledgeQueryRequest,
    KnowledgeQueryResponse,
    KnowledgeResult,
    KnowledgeStats,
    KnowledgeSearchFilter,
    KnowledgeBatchCreate,
    KnowledgeImportRequest,
    KnowledgeExportRequest,
    KnowledgeRelationRequest,
    KnowledgeValidationRequest,
    KnowledgeAnalytics
)
from services.knowledge_bus import KnowledgeBus, KnowledgeType, KnowledgeSource, KnowledgeStatus
from core.dependencies import get_knowledge_bus

router = APIRouter(prefix="/knowledge", tags=["Knowledge Bus - 知识总线"])


# === 知识管理 API ===

@router.post("/", response_model=KnowledgeResponse)
async def create_knowledge(
    knowledge_data: KnowledgeCreate,
    knowledge_bus: KnowledgeBus = Depends(get_knowledge_bus)
):
    """创建知识"""
    try:
        knowledge_id = await knowledge_bus.add_knowledge(
            content=knowledge_data.content,
            knowledge_type=KnowledgeType(knowledge_data.knowledge_type),
            source=KnowledgeSource(knowledge_data.source),
            created_by=knowledge_data.created_by,
            tags=set(knowledge_data.tags) if knowledge_data.tags else set(),
            confidence=knowledge_data.confidence,
            metadata=knowledge_data.metadata or {},
            context=knowledge_data.context or {}
        )
        
        knowledge = await knowledge_bus.get_knowledge(knowledge_id)
        if not knowledge:
            raise HTTPException(status_code=500, detail="知识创建失败")
        
        return KnowledgeResponse(
            id=knowledge.id,
            content=knowledge.content,
            knowledge_type=knowledge.knowledge_type.value,
            source=knowledge.source.value,
            created_at=knowledge.created_at,
            updated_at=knowledge.updated_at,
            created_by=knowledge.created_by,
            tags=list(knowledge.tags),
            confidence=knowledge.confidence,
            usage_count=knowledge.usage_count,
            status=knowledge.status.value,
            related_knowledge=list(knowledge.related_knowledge),
            metadata=knowledge.metadata,
            context=knowledge.context
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建知识失败: {str(e)}")


@router.get("/", response_model=List[KnowledgeResponse])
async def list_knowledge(
    knowledge_type: Optional[KnowledgeType] = Query(None, description="按类型过滤"),
    source: Optional[KnowledgeSource] = Query(None, description="按来源过滤"),
    status: Optional[KnowledgeStatus] = Query(None, description="按状态过滤"),
    tags: Optional[List[str]] = Query(None, description="按标签过滤"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    knowledge_bus: KnowledgeBus = Depends(get_knowledge_bus)
):
    """列出知识"""
    try:
        all_knowledge = list(knowledge_bus.knowledge_store.values())
        
        # 应用过滤条件
        if knowledge_type:
            all_knowledge = [k for k in all_knowledge if k.knowledge_type == knowledge_type]
        
        if source:
            all_knowledge = [k for k in all_knowledge if k.source == source]
        
        if status:
            all_knowledge = [k for k in all_knowledge if k.status == status]
        
        if tags:
            all_knowledge = [k for k in all_knowledge if any(tag in k.tags for tag in tags)]
        
        # 应用分页
        paginated_knowledge = all_knowledge[offset:offset + limit]
        
        return [
            KnowledgeResponse(
                id=k.id,
                content=k.content,
                knowledge_type=k.knowledge_type.value,
                source=k.source.value,
                created_at=k.created_at,
                updated_at=k.updated_at,
                created_by=k.created_by,
                tags=list(k.tags),
                confidence=k.confidence,
                usage_count=k.usage_count,
                status=k.status.value,
                related_knowledge=list(k.related_knowledge),
                metadata=k.metadata,
                context=k.context
            )
            for k in paginated_knowledge
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识列表失败: {str(e)}")


@router.get("/{knowledge_id}", response_model=KnowledgeResponse)
async def get_knowledge(
    knowledge_id: str,
    knowledge_bus: KnowledgeBus = Depends(get_knowledge_bus)
):
    """获取特定知识"""
    try:
        knowledge = await knowledge_bus.get_knowledge(knowledge_id)
        
        if not knowledge:
            raise HTTPException(status_code=404, detail="知识不存在")
        
        return KnowledgeResponse(
            id=knowledge.id,
            content=knowledge.content,
            knowledge_type=knowledge.knowledge_type.value,
            source=knowledge.source.value,
            created_at=knowledge.created_at,
            updated_at=knowledge.updated_at,
            created_by=knowledge.created_by,
            tags=list(knowledge.tags),
            confidence=knowledge.confidence,
            usage_count=knowledge.usage_count,
            status=knowledge.status.value,
            related_knowledge=list(knowledge.related_knowledge),
            metadata=knowledge.metadata,
            context=knowledge.context
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识失败: {str(e)}")


@router.put("/{knowledge_id}", response_model=KnowledgeResponse)
async def update_knowledge(
    knowledge_id: str,
    update_data: KnowledgeUpdate,
    knowledge_bus: KnowledgeBus = Depends(get_knowledge_bus)
):
    """更新知识"""
    try:
        success = await knowledge_bus.update_knowledge(
            knowledge_id=knowledge_id,
            content=update_data.content,
            tags=set(update_data.tags) if update_data.tags else None,
            confidence=update_data.confidence,
            metadata=update_data.metadata,
            status=update_data.status
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="知识不存在")
        
        knowledge = await knowledge_bus.get_knowledge(knowledge_id)
        if not knowledge:
            raise HTTPException(status_code=500, detail="知识更新失败")
        
        return KnowledgeResponse(
            id=knowledge.id,
            content=knowledge.content,
            knowledge_type=knowledge.knowledge_type.value,
            source=knowledge.source.value,
            created_at=knowledge.created_at,
            updated_at=knowledge.updated_at,
            created_by=knowledge.created_by,
            tags=list(knowledge.tags),
            confidence=knowledge.confidence,
            usage_count=knowledge.usage_count,
            status=knowledge.status.value,
            related_knowledge=list(knowledge.related_knowledge),
            metadata=knowledge.metadata,
            context=knowledge.context
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新知识失败: {str(e)}")


@router.delete("/{knowledge_id}")
async def delete_knowledge(
    knowledge_id: str,
    knowledge_bus: KnowledgeBus = Depends(get_knowledge_bus)
):
    """删除知识"""
    try:
        success = await knowledge_bus.delete_knowledge(knowledge_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="知识不存在")
        
        return {"message": "知识已删除", "knowledge_id": knowledge_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除知识失败: {str(e)}")


# === 知识搜索 API ===

@router.post("/search", response_model=KnowledgeQueryResponse)
async def search_knowledge(
    search_request: KnowledgeQueryRequest,
    knowledge_bus: KnowledgeBus = Depends(get_knowledge_bus)
):
    """搜索知识"""
    try:
        # 转换知识类型
        knowledge_types = None
        if search_request.knowledge_types:
            knowledge_types = [KnowledgeType(kt) for kt in search_request.knowledge_types]
        
        # 创建查询对象
        query = KnowledgeQueryRequest(
            query=search_request.query,
            knowledge_types=knowledge_types,
            tags=search_request.tags,
            confidence_threshold=search_request.confidence_threshold,
            limit=search_request.limit,
            include_inactive=search_request.include_inactive
        )
        
        # 执行搜索
        results = await knowledge_bus.search_knowledge(query)
        
        # 转换结果
        knowledge_results = []
        for result in results:
            knowledge_results.append(KnowledgeResult(
                knowledge=KnowledgeResponse(
                    id=result.knowledge.id,
                    content=result.knowledge.content,
                    knowledge_type=result.knowledge.knowledge_type.value,
                    source=result.knowledge.source.value,
                    created_at=result.knowledge.created_at,
                    updated_at=result.knowledge.updated_at,
                    created_by=result.knowledge.created_by,
                    tags=list(result.knowledge.tags),
                    confidence=result.knowledge.confidence,
                    usage_count=result.knowledge.usage_count,
                    status=result.knowledge.status.value,
                    related_knowledge=list(result.knowledge.related_knowledge),
                    metadata=result.knowledge.metadata,
                    context=result.knowledge.context
                ),
                relevance_score=result.relevance_score,
                match_reasons=result.match_reasons
            ))
        
        return KnowledgeQueryResponse(
            results=knowledge_results,
            total_count=len(knowledge_results),
            query_info={
                "query": search_request.query,
                "knowledge_types": search_request.knowledge_types,
                "tags": search_request.tags,
                "confidence_threshold": search_request.confidence_threshold
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索知识失败: {str(e)}")


@router.get("/stats", response_model=KnowledgeStats)
async def get_knowledge_stats(
    knowledge_bus: KnowledgeBus = Depends(get_knowledge_bus)
):
    """获取知识统计信息"""
    try:
        stats = await knowledge_bus.get_knowledge_stats()
        
        # 转换枚举值到字符串
        by_type = {kt.value: count for kt, count in stats["by_type"].items()}
        by_source = {ks.value: count for ks, count in stats["by_source"].items()}
        
        return KnowledgeStats(
            total_knowledge=stats["total_knowledge"],
            by_type=by_type,
            by_source=by_source,
            total_usage=stats["total_usage"],
            average_confidence=stats["average_confidence"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/most-used")
async def get_most_used_knowledge(
    limit: int = Query(10, ge=1, le=100, description="返回数量限制"),
    knowledge_bus: KnowledgeBus = Depends(get_knowledge_bus)
):
    """获取使用次数最多的知识"""
    try:
        most_used = await knowledge_bus.get_most_used_knowledge(limit)
        
        results = []
        for knowledge, usage_count in most_used:
            results.append({
                "knowledge": KnowledgeResponse(
                    id=knowledge.id,
                    content=knowledge.content,
                    knowledge_type=knowledge.knowledge_type.value,
                    source=knowledge.source.value,
                    created_at=knowledge.created_at,
                    updated_at=knowledge.updated_at,
                    created_by=knowledge.created_by,
                    tags=list(knowledge.tags),
                    confidence=knowledge.confidence,
                    usage_count=knowledge.usage_count,
                    status=knowledge.status.value,
                    related_knowledge=list(knowledge.related_knowledge),
                    metadata=knowledge.metadata,
                    context=knowledge.context
                ),
                "usage_count": usage_count
            })
        
        return {"results": results, "total_count": len(results)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取热门知识失败: {str(e)}")


@router.post("/{knowledge_id}/usage")
async def record_knowledge_usage(
    knowledge_id: str,
    knowledge_bus: KnowledgeBus = Depends(get_knowledge_bus)
):
    """记录知识使用"""
    try:
        await knowledge_bus.record_knowledge_usage(knowledge_id)
        return {"message": "使用记录已更新", "knowledge_id": knowledge_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录使用失败: {str(e)}")


# === 知识关系 API ===

@router.post("/relations")
async def create_knowledge_relation(
    relation_request: KnowledgeRelationRequest,
    knowledge_bus: KnowledgeBus = Depends(get_knowledge_bus)
):
    """创建知识关系"""
    try:
        # 检查两个知识是否存在
        source_knowledge = await knowledge_bus.get_knowledge(relation_request.source_knowledge_id)
        target_knowledge = await knowledge_bus.get_knowledge(relation_request.target_knowledge_id)
        
        if not source_knowledge or not target_knowledge:
            raise HTTPException(status_code=404, detail="源知识或目标知识不存在")
        
        # 添加关系
        source_knowledge.related_knowledge.add(relation_request.target_knowledge_id)
        target_knowledge.related_knowledge.add(relation_request.source_knowledge_id)
        
        # 更新知识
        await knowledge_bus.update_knowledge(
            knowledge_id=relation_request.source_knowledge_id,
            metadata=source_knowledge.metadata
        )
        await knowledge_bus.update_knowledge(
            knowledge_id=relation_request.target_knowledge_id,
            metadata=target_knowledge.metadata
        )
        
        return {
            "message": "知识关系已创建",
            "source_id": relation_request.source_knowledge_id,
            "target_id": relation_request.target_knowledge_id,
            "relation_type": relation_request.relation_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建知识关系失败: {str(e)}")


@router.get("/{knowledge_id}/relations")
async def get_knowledge_relations(
    knowledge_id: str,
    knowledge_bus: KnowledgeBus = Depends(get_knowledge_bus)
):
    """获取知识关系"""
    try:
        knowledge = await knowledge_bus.get_knowledge(knowledge_id)
        
        if not knowledge:
            raise HTTPException(status_code=404, detail="知识不存在")
        
        # 获取相关知识
        related_knowledge = []
        for related_id in knowledge.related_knowledge:
            related = await knowledge_bus.get_knowledge(related_id)
            if related:
                related_knowledge.append({
                    "id": related.id,
                    "content": related.content,
                    "knowledge_type": related.knowledge_type.value,
                    "confidence": related.confidence
                })
        
        return {
            "knowledge_id": knowledge_id,
            "related_count": len(related_knowledge),
            "related_knowledge": related_knowledge
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识关系失败: {str(e)}")


# === 批量操作 API ===

@router.post("/batch/create")
async def batch_create_knowledge(
    batch_data: KnowledgeBatchCreate,
    knowledge_bus: KnowledgeBus = Depends(get_knowledge_bus)
):
    """批量创建知识"""
    try:
        created_knowledge = []
        
        for knowledge_data in batch_data.knowledge_list:
            knowledge_id = await knowledge_bus.add_knowledge(
                content=knowledge_data.content,
                knowledge_type=KnowledgeType(knowledge_data.knowledge_type),
                source=KnowledgeSource(knowledge_data.source),
                created_by=knowledge_data.created_by,
                tags=set(knowledge_data.tags) if knowledge_data.tags else set(),
                confidence=knowledge_data.confidence,
                metadata=knowledge_data.metadata or {},
                context=knowledge_data.context or {}
            )
            created_knowledge.append(knowledge_id)
        
        return {
            "message": f"成功创建 {len(created_knowledge)} 条知识",
            "created_ids": created_knowledge,
            "total_created": len(created_knowledge)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量创建知识失败: {str(e)}")
