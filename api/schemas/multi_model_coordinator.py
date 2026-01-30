"""
多模型协调器 API schemas
Multi-Model Coordinator API schemas for AgentBus

本模块定义多模型协调器相关的API数据模型，
包括任务请求、模型配置、结果等数据结构。
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# 枚举类型定义
class ModelType(str, Enum):
    """AI模型类型"""
    TEXT_GENERATION = "text_generation"
    TEXT_UNDERSTANDING = "text_understanding"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    CREATIVE = "creative"
    TRANSLATION = "translation"
    CLASSIFICATION = "classification"
    EMBEDDING = "embedding"
    MULTIMODAL = "multimodal"


class TaskType(str, Enum):
    """任务类型"""
    QUESTION_ANSWERING = "question_answering"
    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    TEXT_ANALYSIS = "text_analysis"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"
    CLASSIFICATION = "classification"
    REASONING = "reasoning"
    CREATIVE_WRITING = "creative_writing"
    TECHNICAL_DOCUMENTATION = "technical_documentation"
    DATA_ANALYSIS = "data_analysis"


class TaskPriority(str, Enum):
    """任务优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


# 数据模型
class ModelConfigBase(BaseModel):
    """模型配置基础模型"""
    model_name: str = Field(..., description="模型名称")
    model_type: ModelType = Field(..., description="模型类型")
    provider: str = Field(..., description="模型提供者")
    max_tokens: int = Field(default=4096, description="最大令牌数")
    temperature: float = Field(default=0.7, description="温度参数")
    timeout: int = Field(default=60, description="超时时间(秒)")
    rate_limit: int = Field(default=100, description="速率限制(每分钟请求数)")
    capabilities: List[TaskType] = Field(default=[], description="模型能力列表")
    is_active: bool = Field(default=True, description="是否激活")
    cost_per_token: float = Field(default=0.0, description="每令牌成本")
    quality_score: float = Field(default=1.0, description="质量评分(0-1)")


class ModelConfigCreate(ModelConfigBase):
    """创建模型配置"""
    model_id: Optional[str] = Field(None, description="模型ID(可选)")


class ModelConfigUpdate(BaseModel):
    """更新模型配置"""
    model_name: Optional[str] = None
    model_type: Optional[ModelType] = None
    provider: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    timeout: Optional[int] = None
    rate_limit: Optional[int] = None
    capabilities: Optional[List[TaskType]] = None
    is_active: Optional[bool] = None
    cost_per_token: Optional[float] = None
    quality_score: Optional[float] = None


class ModelConfigResponse(ModelConfigBase):
    """模型配置响应"""
    model_id: str = Field(..., description="模型ID")


class TaskRequestBase(BaseModel):
    """任务请求基础模型"""
    task_type: TaskType = Field(..., description="任务类型")
    content: str = Field(..., description="任务内容")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="任务优先级")
    required_capabilities: List[TaskType] = Field(default=[], description="必需能力")
    max_cost: Optional[float] = Field(None, description="最大成本限制")
    max_time: Optional[int] = Field(None, description="最大时间限制(秒)")
    preferred_models: List[str] = Field(default=[], description="首选模型列表")
    exclude_models: List[str] = Field(default=[], description="排除模型列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class TaskRequestCreate(TaskRequestBase):
    """创建任务请求"""
    task_id: Optional[str] = Field(None, description="任务ID(可选)")


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    message: str = Field(..., description="响应消息")


class ModelResult(BaseModel):
    """模型结果"""
    model_id: str = Field(..., description="模型ID")
    content: str = Field(..., description="生成内容")
    confidence: float = Field(..., description="置信度(0-1)")
    processing_time: float = Field(..., description="处理时间(秒)")
    cost: float = Field(default=0.0, description="成本")
    tokens_used: int = Field(default=0, description="使用的令牌数")
    quality_score: float = Field(default=0.0, description="质量评分")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    error: Optional[str] = Field(None, description="错误信息")


class TaskResultResponse(BaseModel):
    """任务结果响应"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    final_content: Optional[str] = Field(None, description="最终内容")
    model_results: List[ModelResult] = Field(default=[], description="模型结果列表")
    fusion_method: Optional[str] = Field(None, description="融合方法")
    total_cost: float = Field(default=0.0, description="总成本")
    total_time: float = Field(default=0.0, description="总处理时间")
    processing_log: List[str] = Field(default=[], description="处理日志")
    error: Optional[str] = Field(None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")


class CoordinatorStats(BaseModel):
    """协调器统计信息"""
    active_tasks: int = Field(..., description="活跃任务数")
    total_tasks: int = Field(..., description="总任务数")
    completed_tasks: int = Field(..., description="已完成任务数")
    success_rate: float = Field(..., description="成功率")
    avg_processing_time: float = Field(..., description="平均处理时间")
    avg_cost: float = Field(default=0.0, description="平均成本")
    registered_models: int = Field(..., description="注册模型数")
    active_models: int = Field(..., description="活跃模型数")


class HealthCheck(BaseModel):
    """健康检查"""
    status: str = Field(..., description="健康状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="检查时间")
    version: str = Field(..., description="版本信息")
    uptime: float = Field(..., description="运行时间(秒)")
    memory_usage: Dict[str, float] = Field(default_factory=dict, description="内存使用情况")


class FusionStrategy(str, Enum):
    """融合策略"""
    BEST = "best"
    WEIGHTED = "weighted"
    MAJORITY = "majority"
    ENSEMBLE = "ensemble"


class BatchTaskRequest(BaseModel):
    """批量任务请求"""
    tasks: List[TaskRequestCreate] = Field(..., description="任务列表")
    fusion_strategy: FusionStrategy = Field(default=FusionStrategy.BEST, description="融合策略")
    parallel_execution: bool = Field(default=True, description="是否并行执行")


class BatchTaskResponse(BaseModel):
    """批量任务响应"""
    batch_id: str = Field(..., description="批次ID")
    task_count: int = Field(..., description="任务数量")
    status: TaskStatus = Field(..., description="整体状态")
    task_ids: List[str] = Field(..., description="任务ID列表")


class TaskComparison(BaseModel):
    """任务结果对比"""
    task_id: str = Field(..., description="任务ID")
    model_results: List[ModelResult] = Field(..., description="模型结果列表")
    best_result: Optional[ModelResult] = Field(None, description="最佳结果")
    consensus_score: float = Field(..., description="共识评分")
    divergence: float = Field(..., description="分歧度")


class ModelRecommendation(BaseModel):
    """模型推荐"""
    task_type: TaskType = Field(..., description="任务类型")
    recommended_models: List[ModelConfigResponse] = Field(..., description="推荐模型列表")
    reasoning: str = Field(..., description="推荐理由")
    expected_cost: float = Field(..., description="预期成本")
    expected_quality: float = Field(..., description="预期质量")


# 错误响应模型
class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误信息")
    error_code: str = Field(..., description="错误代码")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class ValidationErrorResponse(BaseModel):
    """验证错误响应"""
    error: str = Field(default="Validation Error", description="错误信息")
    error_code: str = Field(default="VALIDATION_ERROR", description="错误代码")
    validation_errors: List[Dict[str, Any]] = Field(..., description="验证错误详情")


# 请求响应模型
class PaginatedResponse(BaseModel):
    """分页响应基础模型"""
    page: int = Field(..., description="当前页码")
    per_page: int = Field(..., description="每页数量")
    total: int = Field(..., description="总数量")
    pages: int = Field(..., description="总页数")


class ModelListResponse(PaginatedResponse):
    """模型列表响应"""
    models: List[ModelConfigResponse] = Field(..., description="模型列表")


class TaskListResponse(PaginatedResponse):
    """任务列表响应"""
    tasks: List[TaskResultResponse] = Field(..., description="任务列表")