"""
流式响应处理 API 路由
Stream Response Processing API routes for AgentBus

本模块提供流式响应处理的REST API接口，
包括流创建、管理、状态查询等功能。
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import asyncio
import json
import uuid

from api.schemas.stream_response import (
    # 枚举类型
    StreamEventType, StreamStatus, StreamHandlerType,
    # 数据模型
    StreamRequestCreate, StreamRequestResponse, StreamChunk,
    StreamStatusResponse, StreamStatistics, StreamEventResponse,
    HealthCheck, WebSocketMessage, WebSocketStreamStart,
    WebSocketStreamChunk, WebSocketStreamControl, StreamErrorResponse,
    BatchStreamRequest, BatchStreamResponse, StreamConfig,
    StreamConfigUpdate, PaginatedStreamsResponse, StreamFilter,
    StreamPerformanceMetrics, StreamAnalytics,
    # 依赖注入
)
from core.dependencies import get_stream_response_processor
from services.stream_response import (
    StreamResponseProcessor, StreamRequest, StreamChunk as ServiceStreamChunk,
    StreamEventType as ServiceStreamEventType, StreamStatus as ServiceStreamStatus
)


# 创建路由器
router = APIRouter(prefix="/stream", tags=["stream-response"])


# 辅助函数：转换API模型到服务模型
def api_to_service_stream_request(api_request: StreamRequestCreate) -> StreamRequest:
    """API流请求转换为服务流请求"""
    return StreamRequest(
        stream_id=api_request.stream_id or str(uuid.uuid4()),
        task_id=api_request.task_id,
        content=api_request.content,
        stream_type=api_request.stream_type,
        max_tokens=api_request.max_tokens,
        temperature=api_request.temperature,
        chunk_size=api_request.chunk_size,
        delay_ms=api_request.delay_ms,
        metadata=api_request.metadata
    )


def service_to_api_stream_status(service_status: ServiceStreamStatus) -> StreamStatus:
    """服务流状态转换为API流状态"""
    return StreamStatus(service_status.value)


# 健康检查端点
@router.get("/health", response_model=HealthCheck)
async def health_check(processor: StreamResponseProcessor = Depends(get_stream_response_processor)):
    """健康检查"""
    try:
        stats = await processor.get_stream_stats()
        
        return HealthCheck(
            status="healthy",
            active_streams=stats["active_streams"],
            handlers=list(processor.handlers.keys())
        )
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail="健康检查失败")


# 流管理端点
@router.post("/create", response_model=StreamRequestResponse)
async def create_stream(
    request: StreamRequestCreate,
    processor: StreamResponseProcessor = Depends(get_stream_response_processor)
):
    """创建流式传输"""
    try:
        service_request = api_to_service_stream_request(request)
        stream_id = await processor.create_stream(service_request, request.handler_type.value)
        
        return StreamRequestResponse(
            stream_id=stream_id,
            status=StreamStatus.PENDING,
            message="流已成功创建"
        )
        
    except Exception as e:
        logger.error(f"创建流失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建流失败: {str(e)}")


@router.post("/start/{stream_id}")
async def start_stream(
    stream_id: str,
    processor: StreamResponseProcessor = Depends(get_stream_response_processor)
):
    """开始流式处理"""
    try:
        if stream_id not in processor.active_streams:
            raise HTTPException(status_code=404, detail="流不存在")
        
        # 开始流式处理（使用模拟AI响应）
        success = await processor.start_stream_processing(
            stream_id,
            processor.simulate_ai_response
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="开始流式处理失败")
        
        return {"message": f"流 {stream_id} 的流式处理已开始"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"开始流式处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"开始流式处理失败: {str(e)}")


@router.delete("/cancel/{stream_id}")
async def cancel_stream(
    stream_id: str,
    processor: StreamResponseProcessor = Depends(get_stream_response_processor)
):
    """取消流式传输"""
    success = await processor.cancel_stream(stream_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="流不存在")
    
    return {"message": f"流 {stream_id} 已取消"}


@router.get("/status/{stream_id}", response_model=StreamStatusResponse)
async def get_stream_status(
    stream_id: str,
    processor: StreamResponseProcessor = Depends(get_stream_response_processor)
):
    """获取流状态"""
    status = await processor.get_stream_status(stream_id)
    
    if status is None:
        raise HTTPException(status_code=404, detail="流不存在")
    
    return StreamStatusResponse(
        stream_id=stream_id,
        status=service_to_api_stream_status(status),
        created_at=datetime.now(),  # 这里应该从服务中获取实际时间
        updated_at=datetime.now(),
        token_count=0,  # 这里应该从服务中获取实际令牌数
        progress=0.0    # 这里应该从服务中获取实际进度
    )


@router.get("/list", response_model=PaginatedStreamsResponse)
async def list_streams(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=100, description="每页数量"),
    status: Optional[StreamStatus] = Query(None, description="状态过滤"),
    stream_type: Optional[str] = Query(None, description="流类型过滤"),
    processor: StreamResponseProcessor = Depends(get_stream_response_processor)
):
    """获取流列表"""
    try:
        # 获取所有活跃流
        all_stream_ids = await processor.list_active_streams()
        
        # 应用过滤条件（简化实现）
        filtered_ids = all_stream_ids
        if status:
            # 这里需要从服务中获取实际的流状态进行过滤
            pass
        
        if stream_type:
            # 这里需要从服务中获取实际的流类型进行过滤
            pass
        
        # 按时间排序（最新的在前）
        filtered_ids.sort(reverse=True)
        
        # 分页
        total = len(filtered_ids)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_ids = filtered_ids[start_idx:end_idx]
        
        # 转换为API格式
        streams = []
        for stream_id in page_ids:
            status = await processor.get_stream_status(stream_id)
            if status:
                streams.append(StreamStatusResponse(
                    stream_id=stream_id,
                    status=service_to_api_stream_status(status),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    token_count=0,
                    progress=0.0
                ))
        
        return PaginatedStreamsResponse(
            page=page,
            per_page=per_page,
            total=total,
            pages=(total + per_page - 1) // per_page,
            streams=streams
        )
        
    except Exception as e:
        logger.error(f"获取流列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取流列表失败")


# 批量流操作端点
@router.post("/batch", response_model=BatchStreamResponse)
async def create_batch_streams(
    batch_request: BatchStreamRequest,
    processor: StreamResponseProcessor = Depends(get_stream_response_processor)
):
    """创建批量流"""
    try:
        batch_id = str(uuid.uuid4())
        stream_ids = []
        
        for stream_request in batch_request.streams:
            service_request = api_to_service_stream_request(stream_request)
            stream_id = await processor.create_stream(service_request, "websocket")
            stream_ids.append(stream_id)
        
        return BatchStreamResponse(
            batch_id=batch_id,
            stream_count=len(stream_ids),
            status=StreamStatus.PENDING,
            stream_ids=stream_ids
        )
        
    except Exception as e:
        logger.error(f"创建批量流失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建批量流失败: {str(e)}")


# Server-Sent Events端点
@router.get("/sse/{stream_id}")
async def stream_sse(
    stream_id: str,
    processor: StreamResponseProcessor = Depends(get_stream_response_processor)
):
    """Server-Sent Events流端点"""
    
    async def event_generator():
        """事件生成器"""
        try:
            queue = await processor.get_stream_queue(stream_id)
            if queue is None:
                yield f"data: {json.dumps({'error': 'Stream not found'})}\n\n"
                return
            
            while True:
                try:
                    # 等待数据块
                    chunk = await asyncio.wait_for(queue.get(), timeout=30)
                    
                    # 转换为SSE格式
                    event_data = {
                        "stream_id": chunk.stream_id,
                        "event": chunk.event_type.value,
                        "data": {
                            "content": chunk.content,
                            "token_count": chunk.token_count,
                            "progress": chunk.progress,
                            "timestamp": chunk.timestamp.isoformat(),
                            "metadata": chunk.metadata,
                            "error": chunk.error
                        }
                    }
                    
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    
                    # 如果是完成或错误事件，结束流
                    if chunk.event_type in [StreamEventType.COMPLETE, StreamEventType.ERROR, StreamEventType.CANCEL]:
                        break
                        
                except asyncio.TimeoutError:
                    # 发送心跳
                    yield f"data: {json.dumps({'event': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
                    
        except Exception as e:
            logger.error(f"SSE流错误: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )


# WebSocket端点（通过HTTP升级模拟）
@router.websocket("/ws/{stream_id}")
async def websocket_stream_endpoint(websocket):
    """WebSocket流式传输端点"""
    await websocket.accept()
    
    try:
        # 发送连接确认
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "message": "WebSocket流式传输已建立"
        })
        
        # 处理消息
        while True:
            # 接收消息
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "ping":
                await websocket.send_json({"type": "pong"})
                
            elif message_type == "start_stream":
                # 开始流式传输
                stream_data = data.get("data", {})
                # 这里应该调用实际的流开始逻辑
                await websocket.send_json({
                    "type": "stream_started",
                    "stream_id": stream_data.get("stream_id")
                })
                
            elif message_type == "stream_chunk":
                # 发送流数据块
                chunk_data = data.get("data", {})
                await websocket.send_json({
                    "type": "stream_chunk",
                    "data": chunk_data
                })
                
            elif message_type == "control":
                # 流控制消息
                control_data = data.get("data", {})
                action = control_data.get("action")
                
                if action == "cancel":
                    await websocket.send_json({
                        "type": "stream_cancelled",
                        "stream_id": control_data.get("stream_id")
                    })
                    
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"未知消息类型: {message_type}"
                })
    
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        await websocket.close()


# 统计和分析端点
@router.get("/stats", response_model=StreamStatistics)
async def get_stream_stats(
    processor: StreamResponseProcessor = Depends(get_stream_response_processor)
):
    """获取流统计信息"""
    try:
        stats = await processor.get_stream_stats()
        return StreamStatistics(**stats)
        
    except Exception as e:
        logger.error(f"获取流统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取流统计失败")


@router.get("/analytics", response_model=StreamAnalytics)
async def get_stream_analytics(
    processor: StreamResponseProcessor = Depends(get_stream_response_processor)
):
    """获取流分析数据"""
    try:
        # 这里是简化的分析数据
        # 实际实现中应该从数据库或存储中获取真实数据
        stats = await processor.get_stream_stats()
        
        return StreamAnalytics(
            total_streams=stats["total_streams"],
            success_rate=0.85,  # 模拟成功率
            avg_processing_time=2.5,  # 模拟平均处理时间
            avg_tokens_per_second=15.2,  # 模拟平均令牌数/秒
            popular_stream_types={"text": 60, "code": 25, "analysis": 15},  # 模拟数据
            handler_performance={  # 模拟处理器性能
                "websocket": {"avg_latency": 0.05, "throughput": 100},
                "http": {"avg_latency": 0.08, "throughput": 80}
            }
        )
        
    except Exception as e:
        logger.error(f"获取流分析失败: {e}")
        raise HTTPException(status_code=500, detail="获取流分析失败")


# 性能监控端点
@router.get("/performance/{stream_id}", response_model=StreamPerformanceMetrics)
async def get_stream_performance(
    stream_id: str,
    processor: StreamResponseProcessor = Depends(get_stream_response_processor)
):
    """获取流性能指标"""
    try:
        # 这里是模拟的性能数据
        # 实际实现中应该从监控系统中获取真实数据
        return StreamPerformanceMetrics(
            stream_id=stream_id,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_tokens=150,
            processing_time=10.2,
            tokens_per_second=14.7,
            avg_chunk_delay=0.05,
            success=True
        )
        
    except Exception as e:
        logger.error(f"获取流性能失败: {e}")
        raise HTTPException(status_code=500, detail="获取流性能失败")


# 配置管理端点
@router.get("/config", response_model=StreamConfig)
async def get_stream_config():
    """获取流配置"""
    # 返回默认配置
    return StreamConfig()


@router.put("/config", response_model=StreamConfig)
async def update_stream_config(
    config: StreamConfigUpdate
):
    """更新流配置"""
    # 这里应该将配置更新到实际的配置存储中
    # 目前返回更新后的配置
    current_config = StreamConfig()
    
    if config.max_concurrent_streams is not None:
        current_config.max_concurrent_streams = config.max_concurrent_streams
    if config.default_chunk_size is not None:
        current_config.default_chunk_size = config.default_chunk_size
    if config.default_delay_ms is not None:
        current_config.default_delay_ms = config.default_delay_ms
    if config.heartbeat_interval is not None:
        current_config.heartbeat_interval = config.heartbeat_interval
    if config.stream_timeout is not None:
        current_config.stream_timeout = config.stream_timeout
    
    return current_config


# 错误处理函数（已注释，因为应该通过应用实例注册）
# @router.exception_handler(HTTPException)
# async def http_exception_handler(request, exc):
#     """HTTP异常处理器"""
#     logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={
#             "error": exc.detail,
#             "error_code": f"HTTP_{exc.status_code}",
#             "timestamp": datetime.now().isoformat()
#         }
#     )


# @router.exception_handler(Exception)
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