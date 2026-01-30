"""
知识总线 API 数据模型
Knowledge Bus API Data Models
"""

from typing import List, Optional, Dict, Any, Set
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class KnowledgeType(str, Enum):
    """知识类型枚举"""
    FACT = "fact"
    PROCEDURE = "procedure"
    CONTEXT = "context"
    RELATION = "relation"
    RULE = "rule"
    METADATA = "metadata"


class KnowledgeStatus(str, Enum):
    """知识状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    VALIDATING = "validating"


class KnowledgeSource(str, Enum):
    """知识来源枚举"""
    USER_INPUT = "user_input"
    AGENT_LEARNING = "agent_learning"
    MANUAL_ENTRY = "manual_entry"
    IMPORT = "import"
    AUTO_GENERATED = "auto_generated"


class KnowledgeCreate(BaseModel):
    """创建知识的数据模型"""
    content: str = Field(..., description="知识内容", max_length=10000)
    knowledge_type: KnowledgeType = Field(..., description="知识类型")
    source: KnowledgeSource = Field(..., description="知识来源")
    created_by: str = Field(..., description="创建者", max_length=100)
    tags: Optional[List[str]] = Field(default=None, description="标签")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="置信度")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")
    context: Optional[Dict[str, Any]] = Field(default=None, description="上下文")


class KnowledgeResponse(BaseModel):
    """知识响应数据模型"""
    id: str
    content: str
    knowledge_type: str
    source: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    tags: List[str]
    confidence: float
    usage_count: int
    status: str
    related_knowledge: List[str]
    metadata: Dict[str, Any]
    context: Dict[str, Any]
    
    class Config:
        from_attributes = True


class KnowledgeUpdate(BaseModel):
    """更新知识的数据模型"""
    content: Optional[str] = Field(default=None, max_length=10000, description="知识内容")
    tags: Optional[List[str]] = Field(default=None, description="标签")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="置信度")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")
    status: Optional[KnowledgeStatus] = Field(default=None, description="状态")


class KnowledgeQueryRequest(BaseModel):
    """知识查询请求数据模型"""
    query: str = Field(..., description="查询内容", max_length=1000)
    knowledge_types: Optional[List[KnowledgeType]] = Field(default=None, description="知识类型过滤")
    tags: Optional[List[str]] = Field(default=None, description="标签过滤")
    confidence_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="置信度阈值")
    limit: int = Field(default=10, ge=1, le=100, description="结果数量限制")
    include_inactive: bool = Field(default=False, description="包含非活跃知识")


class KnowledgeResult(BaseModel):
    """知识查询结果"""
    knowledge: KnowledgeResponse
    relevance_score: float
    match_reasons: List[str]


class KnowledgeQueryResponse(BaseModel):
    """知识查询响应数据模型"""
    results: List[KnowledgeResult]
    total_count: int
    query_info: Dict[str, Any]


class KnowledgeStats(BaseModel):
    """知识统计信息数据模型"""
    total_knowledge: int
    by_type: Dict[str, int]
    by_source: Dict[str, int]
    total_usage: int
    average_confidence: float


class KnowledgeSearchFilter(BaseModel):
    """知识搜索过滤器"""
    knowledge_type: Optional[KnowledgeType] = Field(default=None, description="按类型过滤")
    source: Optional[KnowledgeSource] = Field(default=None, description="按来源过滤")
    status: Optional[KnowledgeStatus] = Field(default=None, description="按状态过滤")
    tags: Optional[List[str]] = Field(default=None, description="按标签过滤")
    created_by: Optional[str] = Field(default=None, description="按创建者过滤")
    date_from: Optional[datetime] = Field(default=None, description="起始日期")
    date_to: Optional[datetime] = Field(default=None, description="结束日期")


class KnowledgeBatchCreate(BaseModel):
    """批量创建知识的数据模型"""
    knowledge_list: List[KnowledgeCreate] = Field(..., min_items=1, max_items=100, description="知识列表")


class KnowledgeImportRequest(BaseModel):
    """知识导入请求数据模型"""
    source_type: str = Field(..., description="导入源类型", pattern="^(json|yaml|csv)$")
    source_data: Dict[str, Any] = Field(..., description="导入源数据")
    import_options: Dict[str, Any] = Field(default={}, description="导入选项")


class KnowledgeExportRequest(BaseModel):
    """知识导出请求数据模型"""
    format: str = Field(..., description="导出格式", pattern="^(json|yaml|csv)$")
    filters: Optional[KnowledgeSearchFilter] = Field(default=None, description="过滤条件")
    include_metadata: bool = Field(default=True, description="包含元数据")


class KnowledgeRelationRequest(BaseModel):
    """知识关系请求数据模型"""
    source_knowledge_id: str = Field(..., description="源知识ID")
    target_knowledge_id: str = Field(..., description="目标知识ID")
    relation_type: str = Field(..., description="关系类型", max_length=100)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="关系元数据")


class KnowledgeValidationRequest(BaseModel):
    """知识验证请求数据模型"""
    knowledge_id: str = Field(..., description="要验证的知识ID")
    validation_criteria: Dict[str, Any] = Field(..., description="验证标准")
    validate_confidence: bool = Field(default=True, description="验证置信度")
    validate_content: bool = Field(default=True, description="验证内容")


class KnowledgeAnalytics(BaseModel):
    """知识分析数据模型"""
    most_used_knowledge: List[KnowledgeResponse]
    knowledge_growth: List[Dict[str, Any]]
    tag_distribution: Dict[str, int]
    confidence_distribution: Dict[str, int]
    usage_trends: List[Dict[str, Any]]
    quality_metrics: Dict[str, float]
