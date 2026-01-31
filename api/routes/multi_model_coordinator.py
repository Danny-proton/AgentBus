"""
多模型协调器 API 路由
Multi-Model Coordinator API routes for AgentBus

本模块提供多模型协调器的REST API接口，
包括模型管理、任务提交、结果查询等功能。
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from loguru import logger
import uuid

from api.schemas.multi_model_coordinator import (
    # 枚举类型
    ModelType, TaskType, TaskPriority, TaskStatus, FusionStrategy,
    # 数据模型
    ModelConfigCreate, ModelConfigUpdate, ModelConfigResponse,
    TaskRequestCreate, TaskResponse, TaskResultResponse,
    ModelResult, CoordinatorStats, HealthCheck,
    BatchTaskRequest, BatchTaskResponse, TaskComparison,
    ModelRecommendation, ErrorResponse, ValidationErrorResponse,
    ModelListResponse, TaskListResponse,
    # 依赖注入
)
from core.dependencies import get_multi_model_coordinator
from services.multi_model_coordinator import (
    MultiModelCoordinator, ModelConfig, TaskRequest, TaskResult,
    TaskPriority as ServiceTaskPriority, TaskType as ServiceTaskType,
    TaskStatus as ServiceTaskStatus
)


# 创建路由器
router = APIRouter(prefix="/multi-model", tags=["multi-model-coordinator"])


# 辅助函数：转换API模型到服务模型
def api_to_service_model_config(api_config: ModelConfigCreate) -> ModelConfig:
    """API模型配置转换为服务模型配置"""
    return ModelConfig(
        model_id=api_config.model_id or f"{api_config.provider}_{api_config.model_name}",
        model_name=api_config.model_name,
        model_type=ModelType(api_config.model_type.value),
        provider=api_config.provider,
        max_tokens=api_config.max_tokens,
        temperature=api_config.temperature,
        timeout=api_config.timeout,
        rate_limit=api_config.rate_limit,
        capabilities=[TaskType(ct.value) for ct in api_config.capabilities],
        is_active=api_config.is_active,
        cost_per_token=api_config.cost_per_token,
        quality_score=api_config.quality_score
    )


def service_to_api_model_config(service_config: ModelConfig) -> ModelConfigResponse:
    """服务模型配置转换为API模型配置"""
    return ModelConfigResponse(
        model_id=service_config.model_id,
        model_name=service_config.model_name,
        model_type=ModelType(service_config.model_type.value),
        provider=service_config.provider,
        max_tokens=service_config.max_tokens,
        temperature=service_config.temperature,
        timeout=service_config.timeout,
        rate_limit=service_config.rate_limit,
        capabilities=[TaskType(ct.value) for ct in service_config.capabilities],
        is_active=service_config.is_active,
        cost_per_token=service_config.cost_per_token,
        quality_score=service_config.quality_score
    )


def api_to_service_task_request(api_request: TaskRequestCreate) -> TaskRequest:
    """API任务请求转换为服务任务请求"""
    return TaskRequest(
        task_id=api_request.task_id or str(uuid.uuid4()),
        task_type=TaskType(api_request.task_type.value),
        content=api_request.content,
        context=api_request.context,
        priority=ServiceTaskPriority(api_request.priority.value),
        required_capabilities=[TaskType(ct.value) for ct in api_request.required_capabilities],
        max_cost=api_request.max_cost,
        max_time=api_request.max_time,
        preferred_models=api_request.preferred_models,
        exclude_models=api_request.exclude_models,
        metadata=api_request.metadata
    )


def service_to_api_task_result(service_result: TaskResult) -> TaskResultResponse:
    """服务任务结果转换为API任务结果"""
    return TaskResultResponse(
        task_id=service_result.task_id,
        status=TaskStatus(service_result.status.value),
        final_content=service_result.final_content,
        model_results=[
            ModelResult(
                model_id=result.model_id,
                content=result.content,
                confidence=result.confidence,
                processing_time=result.processing_time,
                cost=result.cost,
                tokens_used=result.tokens_used,
                quality_score=result.quality_score,
                metadata=result.metadata,
                error=result.error
            )
            for result in service_result.model_results
        ],
        fusion_method=service_result.fusion_method,
        total_cost=service_result.total_cost,
        total_time=service_result.total_time,
        processing_log=service_result.processing_log,
        error=service_result.error,
        metadata=service_result.metadata,
        created_at=datetime.now(),  # 这里应该从服务中获取实际时间
        completed_at=datetime.now() if service_result.status == ServiceTaskStatus.COMPLETED else None
    )


# 健康检查端点
@router.get("/health", response_model=HealthCheck)
async def health_check(coordinator: MultiModelCoordinator = Depends(get_multi_model_coordinator)):
    """健康检查"""
    try:
        stats = await coordinator.get_coordinator_stats()
        
        return HealthCheck(
            status="healthy",
            version="1.0.0",
            uptime=stats.get("uptime", 0),  # 这里应该从服务中获取实际运行时间
            memory_usage={"rss": 0, "vms": 0}  # 这里应该获取实际的内存使用情况
        )
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail="健康检查失败")


# 模型管理端点
@router.post("/models", response_model=ModelConfigResponse, status_code=201)
async def register_model(
    model_config: ModelConfigCreate,
    coordinator: MultiModelCoordinator = Depends(get_multi_model_coordinator)
):
    """注册AI模型"""
    try:
        service_config = api_to_service_model_config(model_config)
        success = coordinator.register_model(service_config)
        
        if not success:
            raise HTTPException(status_code=400, detail="模型注册失败")
        
        logger.info(f"模型注册成功: {service_config.model_id}")
        return service_to_api_model_config(service_config)
        
    except Exception as e:
        logger.error(f"模型注册异常: {e}")
        raise HTTPException(status_code=500, detail=f"模型注册失败: {str(e)}")


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=100, description="每页数量"),
    model_type: Optional[ModelType] = Query(None, description="模型类型过滤"),
    provider: Optional[str] = Query(None, description="提供者过滤"),
    active_only: bool = Query(True, description="仅显示活跃模型"),
    coordinator: MultiModelCoordinator = Depends(get_multi_model_coordinator)
):
    """获取模型列表"""
    try:
        all_models = list(coordinator.models.values())
        
        # 应用过滤条件
        if model_type:
            all_models = [m for m in all_models if m.model_type == model_type]
        
        if provider:
            all_models = [m for m in all_models if m.provider == provider]
        
        if active_only:
            all_models = [m for m in all_models if m.is_active]
        
        # 分页
        total = len(all_models)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_models = all_models[start_idx:end_idx]
        
        # 转换为API格式
        api_models = [service_to_api_model_config(m) for m in page_models]
        
        return ModelListResponse(
            page=page,
            per_page=per_page,
            total=total,
            pages=(total + per_page - 1) // per_page,
            models=api_models
        )
        
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取模型列表失败")


@router.get("/models/{model_id}", response_model=ModelConfigResponse)
async def get_model(
    model_id: str,
    coordinator: MultiModelCoordinator = Depends(get_multi_model_coordinator)
):
    """获取指定模型详情"""
    if model_id not in coordinator.models:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    return service_to_api_model_config(coordinator.models[model_id])


@router.put("/models/{model_id}", response_model=ModelConfigResponse)
async def update_model(
    model_id: str,
    model_update: ModelConfigUpdate,
    coordinator: MultiModelCoordinator = Depends(get_multi_model_coordinator)
):
    """更新模型配置"""
    if model_id not in coordinator.models:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    try:
        # 更新模型配置
        model_config = coordinator.models[model_id]
        
        if model_update.model_name is not None:
            model_config.model_name = model_update.model_name
        if model_update.model_type is not None:
            model_config.model_type = ModelType(model_update.model_type.value)
        if model_update.provider is not None:
            model_config.provider = model_update.provider
        if model_update.max_tokens is not None:
            model_config.max_tokens = model_update.max_tokens
        if model_update.temperature is not None:
            model_config.temperature = model_update.temperature
        if model_update.timeout is not None:
            model_config.timeout = model_update.timeout
        if model_update.rate_limit is not None:
            model_config.rate_limit = model_update.rate_limit
        if model_update.capabilities is not None:
            model_config.capabilities = [TaskType(ct.value) for ct in model_update.capabilities]
        if model_update.is_active is not None:
            model_config.is_active = model_update.is_active
        if model_update.cost_per_token is not None:
            model_config.cost_per_token = model_update.cost_per_token
        if model_update.quality_score is not None:
            model_config.quality_score = model_update.quality_score
        
        logger.info(f"模型配置已更新: {model_id}")
        return service_to_api_model_config(model_config)
        
    except Exception as e:
        logger.error(f"更新模型配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新模型配置失败: {str(e)}")


@router.delete("/models/{model_id}")
async def unregister_model(
    model_id: str,
    coordinator: MultiModelCoordinator = Depends(get_multi_model_coordinator)
):
    """注销AI模型"""
    success = coordinator.unregister_model(model_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="模型不存在")
    
    return {"message": f"模型 {model_id} 已注销"}


# 任务管理端点
@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def submit_task(
    task_request: TaskRequestCreate,
    background_tasks: BackgroundTasks,
    coordinator: MultiModelCoordinator = Depends(get_multi_model_coordinator)
):
    """提交任务"""
    try:
        service_request = api_to_service_task_request(task_request)
        task_id = await coordinator.submit_task(service_request)
        
        logger.info(f"任务已提交: {task_id}")
        
        return TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="任务已成功提交"
        )
        
    except Exception as e:
        logger.error(f"任务提交失败: {e}")
        raise HTTPException(status_code=500, detail=f"任务提交失败: {str(e)}")


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=100, description="每页数量"),
    status: Optional[TaskStatus] = Query(None, description="状态过滤"),
    task_type: Optional[TaskType] = Query(None, description="任务类型过滤"),
    coordinator: MultiModelCoordinator = Depends(get_multi_model_coordinator)
):
    """获取任务列表"""
    try:
        all_results = list(coordinator.task_results.values())
        
        # 应用过滤条件
        if status:
            all_results = [r for r in all_results if r.status == ServiceTaskStatus(status.value)]
        
        if task_type:
            # 这里需要从任务中获取任务类型信息
            # 简化处理，实际应该存储任务类型信息
            pass
        
        # 按时间排序（最新的在前）
        all_results.sort(key=lambda r: r.task_id, reverse=True)
        
        # 分页
        total = len(all_results)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_results = all_results[start_idx:end_idx]
        
        # 转换为API格式
        api_results = [service_to_api_task_result(r) for r in page_results]
        
        return TaskListResponse(
            page=page,
            per_page=per_page,
            total=total,
            pages=(total + per_page - 1) // per_page,
            tasks=api_results
        )
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务列表失败")


@router.get("/tasks/{task_id}", response_model=TaskResultResponse)
async def get_task_result(
    task_id: str,
    coordinator: MultiModelCoordinator = Depends(get_multi_model_coordinator)
):
    """获取任务结果"""
    result = await coordinator.get_task_result(task_id)
    
    if result is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return service_to_api_task_result(result)


@router.delete("/tasks/{task_id}")
async def cancel_task(
    task_id: str,
    coordinator: MultiModelCoordinator = Depends(get_multi_model_coordinator)
):
    """取消任务"""
    success = await coordinator.cancel_task(task_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在或无法取消")
    
    return {"message": f"任务 {task_id} 已取消"}


# 批量任务端点
@router.post("/tasks/batch", response_model=BatchTaskResponse, status_code=201)
async def submit_batch_tasks(
    batch_request: BatchTaskRequest,
    coordinator: MultiModelCoordinator = Depends(get_multi_model_coordinator)
):
    """提交批量任务"""
    try:
        batch_id = str(uuid.uuid4())
        task_ids = []
        
        for task_request in batch_request.tasks:
            service_request = api_to_service_task_request(task_request)
            task_id = await coordinator.submit_task(service_request)
            task_ids.append(task_id)
        
        logger.info(f"批量任务已提交: {batch_id}, {len(task_ids)} 个任务")
        
        return BatchTaskResponse(
            batch_id=batch_id,
            task_count=len(task_ids),
            status=TaskStatus.PENDING,
            task_ids=task_ids
        )
        
    except Exception as e:
        logger.error(f"批量任务提交失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量任务提交失败: {str(e)}")


# 辅助端点
@router.get("/stats", response_model=CoordinatorStats)
async def get_coordinator_stats(
    coordinator: MultiModelCoordinator = Depends(get_multi_model_coordinator)
):
    """获取协调器统计信息"""
    try:
        stats = await coordinator.get_coordinator_stats()
        return CoordinatorStats(**stats)
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")


@router.get("/recommendations", response_model=List[ModelRecommendation])
async def get_model_recommendations(
    task_type: TaskType = Query(..., description="任务类型"),
    max_cost: Optional[float] = Query(None, description="最大成本"),
    coordinator: MultiModelCoordinator = Depends(get_multi_model_coordinator)
):
    """获取模型推荐"""
    try:
        # 获取支持该任务类型的模型
        available_models = coordinator.get_available_models(TaskType(task_type.value))
        
        # 过滤符合成本要求的模型
        if max_cost:
            available_models = [m for m in available_models if m.cost_per_token <= max_cost]
        
        # 按质量评分排序
        available_models.sort(key=lambda m: m.quality_score, reverse=True)
        
        # 生成推荐
        recommendations = []
        for model in available_models[:3]:  # 推荐前3个模型
            api_config = service_to_api_model_config(model)
            recommendations.append(ModelRecommendation(
                task_type=task_type,
                recommended_models=[api_config],
                reasoning=f"基于质量评分 {model.quality_score} 和成本效率",
                expected_cost=model.cost_per_token * 1000,  # 假设1000个令牌
                expected_quality=model.quality_score
            ))
        
        return recommendations
        
    except Exception as e:
        logger.error(f"获取模型推荐失败: {e}")
        raise HTTPException(status_code=500, detail="获取模型推荐失败")


@router.get("/capabilities", response_model=Dict[str, List[str]])
async def get_supported_capabilities(
    coordinator: MultiModelCoordinator = Depends(get_multi_model_coordinator)
):
    """获取支持的能力列表"""
    capabilities = {}
    
    for task_type in TaskType:
        models = coordinator.get_available_models(TaskType(task_type.value))
        capabilities[task_type.value] = [m.model_id for m in models]
    
    return capabilities


# 错误处理函数（已注释，因为应该通过应用实例注册）
# async def http_exception_handler(request, exc):
#     """HTTP异常处理器"""
#     logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "timestamp": datetime.now().isoformat()
        }
    )


# 通用异常处理器（已注释，因为应该通过应用实例注册）
# async def general_exception_handler(request, exc):
#     """通用异常处理器"""
#     logger.error(f"未处理的异常: {exc}")
#     return JSONResponse(
#         status_code=500,
#         content={
#             "error": "内部服务器错误",
#             "error_code": "INTERNAL_ERROR",
#             "timestamp": datetime.now().isoformat()
#         }
#     )