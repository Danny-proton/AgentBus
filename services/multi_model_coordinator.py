"""
多模型协调器 (Multi-Model Coordinator) 服务
Multi-Model Coordinator service for AgentBus

本模块实现智能的多模型协调系统，能够根据任务类型自动选择最适合的AI模型，
处理模型间的协作、结果融合和决策，提供统一的AI服务接口。
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from loguru import logger
import openai
from openai import AsyncOpenAI

try:
    from core.settings import settings
except ImportError as e:
    print(f"Failed to import settings: {e}")
    # 如果没有配置模块，创建一个默认的settings
    class Settings:
        pass
    settings = Settings()


class ModelType(Enum):
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


class TaskType(Enum):
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


class TaskPriority(Enum):
    """任务优先级"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class ModelConfig:
    """AI模型配置"""
    model_id: str
    model_name: str
    model_type: ModelType
    provider: str  # openai, anthropic, local, etc.
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    rate_limit: int = 100  # requests per minute
    capabilities: List[TaskType] = None
    is_active: bool = True
    cost_per_token: float = 0.0
    quality_score: float = 1.0  # 0-1 quality rating
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


@dataclass
class TaskRequest:
    """任务请求"""
    task_id: str
    task_type: TaskType
    content: str
    context: Optional[Dict[str, Any]] = None
    priority: TaskPriority = TaskPriority.NORMAL
    required_capabilities: List[TaskType] = None
    max_cost: Optional[float] = None
    max_time: Optional[int] = None  # seconds
    preferred_models: List[str] = None
    exclude_models: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.required_capabilities is None:
            self.required_capabilities = []
        if self.preferred_models is None:
            self.preferred_models = []
        if self.exclude_models is None:
            self.exclude_models = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ModelResult:
    """模型结果"""
    model_id: str
    content: str
    confidence: float  # 0-1 confidence score
    processing_time: float  # seconds
    cost: float = 0.0
    tokens_used: int = 0
    quality_score: float = 0.0
    metadata: Dict[str, Any] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: TaskStatus
    final_content: Optional[str] = None
    model_results: List[ModelResult] = None
    fusion_method: Optional[str] = None
    total_cost: float = 0.0
    total_time: float = 0.0
    processing_log: List[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.model_results is None:
            self.model_results = []
        if self.processing_log is None:
            self.processing_log = []
        if self.metadata is None:
            self.metadata = {}


class ModelProvider(ABC):
    """AI模型提供者抽象基类"""
    
    @abstractmethod
    async def generate(self, config: ModelConfig, prompt: str, **kwargs) -> ModelResult:
        """生成内容"""
        pass
    
    @abstractmethod
    async def validate_config(self, config: ModelConfig) -> bool:
        """验证配置"""
        pass


class OpenAIProvider(ModelProvider):
    """OpenAI模型提供者"""
    
    async def generate(self, config: ModelConfig, prompt: str, **kwargs) -> ModelResult:
        """OpenAI API调用"""
        start_time = datetime.now()
        
        try:
            client = AsyncOpenAI(
                api_key=config.api_key,
                base_url=config.base_url
            )
            
            messages = [{"role": "user", "content": prompt}]
            
            response = await client.chat.completions.create(
                model=config.model_id,
                messages=messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature
            )
            
            content = response.choices[0].message.content
            
            return ModelResult(
                model_id=config.model_id,
                content=content,
                confidence=0.95, # OpenAI doesn't return confidence usually
                processing_time=(datetime.now() - start_time).total_seconds(),
                cost=config.cost_per_token * response.usage.total_tokens,
                tokens_used=response.usage.total_tokens,
                quality_score=config.quality_score
            )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return ModelResult(
                model_id=config.model_id,
                content="",
                confidence=0.0,
                processing_time=(datetime.now() - start_time).total_seconds(),
                error=str(e)
            )
    
    async def validate_config(self, config: ModelConfig) -> bool:
        """验证OpenAI配置"""
        return bool(config.api_key)


class AnthropicProvider(ModelProvider):
    """Anthropic模型提供者"""
    
    async def generate(self, config: ModelConfig, prompt: str, **kwargs) -> ModelResult:
        """Anthropic API调用"""
        start_time = datetime.now()
        
        try:
            # 模拟Anthropic API调用
            await asyncio.sleep(0.12)
            
            return ModelResult(
                model_id=config.model_id,
                content=f"[Anthropic Response] {prompt[:100]}...",
                confidence=0.93,
                processing_time=(datetime.now() - start_time).total_seconds(),
                cost=config.cost_per_token * len(prompt) * 0.001,
                tokens_used=len(prompt) // 4,
                quality_score=config.quality_score
            )
            
        except Exception as e:
            return ModelResult(
                model_id=config.model_id,
                content="",
                confidence=0.0,
                processing_time=(datetime.now() - start_time).total_seconds(),
                error=str(e)
            )
    
    async def validate_config(self, config: ModelConfig) -> bool:
        """验证Anthropic配置"""
        return bool(config.api_key)


class LocalProvider(ModelProvider):
    """本地模型提供者 (vLLM/Ollama compatible)"""
    
    async def generate(self, config: ModelConfig, prompt: str, **kwargs) -> ModelResult:
        """本地模型调用 (通过OpenAI兼容接口)"""
        start_time = datetime.now()
        
        try:
            # 使用OpenAI客户端连接本地API
            client = AsyncOpenAI(
                api_key=config.api_key or "empty",
                base_url=config.base_url
            )
            
            messages = [{"role": "user", "content": prompt}]
            
            response = await client.chat.completions.create(
                model=config.model_id,
                messages=messages,
                max_tokens=config.max_tokens,
                temperature=config.temperature
            )
            
            content = response.choices[0].message.content
            
            return ModelResult(
                model_id=config.model_id,
                content=content,
                confidence=0.90, # default confidence for local models
                processing_time=(datetime.now() - start_time).total_seconds(),
                cost=0.0,  # 本地模型假设无API成本
                tokens_used=response.usage.total_tokens,
                quality_score=config.quality_score
            )
            
        except Exception as e:
            logger.error(f"Local model error: {e}")
            return ModelResult(
                model_id=config.model_id,
                content="",
                confidence=0.0,
                processing_time=(datetime.now() - start_time).total_seconds(),
                error=str(e)
            )
    
    async def validate_config(self, config: ModelConfig) -> bool:
        """验证本地模型配置"""
        return bool(config.base_url)


class MultiModelCoordinator:
    """多模型协调器核心服务"""
    
    def __init__(self):
        self.models: Dict[str, ModelConfig] = {}
        self.providers: Dict[str, ModelProvider] = {}
        self.task_queue = asyncio.Queue()
        self.active_tasks: Dict[str, TaskRequest] = {}
        self.task_results: Dict[str, TaskResult] = {}
        self.rate_limits: Dict[str, asyncio.Queue] = {}  # model_id -> token bucket
        self.fusion_strategies: Dict[str, Callable] = {}
        self.is_running = False
        
        # 注册默认提供者和融合策略
        self._register_default_providers()
        self._register_default_fusion_strategies()
        
        # 注册默认模型
        self._register_default_models()
        
        logger.info("多模型协调器初始化完成")
    
    def _register_default_providers(self):
        """注册默认模型提供者"""
        self.providers["openai"] = OpenAIProvider()
        self.providers["anthropic"] = AnthropicProvider()
        self.providers["local"] = LocalProvider()
        logger.info("默认模型提供者已注册")
    
    def _register_default_fusion_strategies(self):
        """注册默认融合策略"""
        self.fusion_strategies["best"] = self._fusion_best_result
        self.fusion_strategies["weighted"] = self._fusion_weighted_average
        self.fusion_strategies["majority"] = self._fusion_majority_vote
        self.fusion_strategies["ensemble"] = self._fusion_ensemble
        logger.info("默认融合策略已注册")
    
    def _register_default_models(self):
        """注册默认模型配置"""
        default_models = [
            ModelConfig(
                model_id="glm-4-flash",
                model_name="GLM-4-Flash",
                model_type=ModelType.TEXT_GENERATION,
                provider="openai",
                api_key=settings.zhipu_api_key,
                base_url=settings.zhipu_base_url,
                capabilities=[TaskType.QUESTION_ANSWERING, TaskType.TEXT_GENERATION, TaskType.CREATIVE_WRITING],
                cost_per_token=0.0000001, # Extremely cheap
                quality_score=0.90
            ),
            ModelConfig(
                model_id="gpt-4",
                model_name="GPT-4",
                model_type=ModelType.TEXT_GENERATION,
                provider="openai",
                capabilities=[TaskType.QUESTION_ANSWERING, TaskType.REASONING, TaskType.CREATIVE_WRITING],
                cost_per_token=0.00003,
                quality_score=0.95
            ),
            ModelConfig(
                model_id="claude-3",
                model_name="Claude-3",
                model_type=ModelType.TEXT_UNDERSTANDING,
                provider="anthropic",
                capabilities=[TaskType.TEXT_ANALYSIS, TaskType.REASONING, TaskType.TECHNICAL_DOCUMENTATION],
                cost_per_token=0.000025,
                quality_score=0.92
            ),
            ModelConfig(
                model_id=getattr(settings, "local_model_id", "qwen3_32B"),
                model_name=f"{getattr(settings, 'local_model_id', 'qwen3_32B')} (Local)",
                model_type=ModelType.TEXT_GENERATION,
                provider="local",
                base_url=getattr(settings, "local_model_base_url", "http://127.0.0.1:8030/v1"),
                api_key=getattr(settings, "local_model_api_key", "empty"),
                capabilities=[TaskType.QUESTION_ANSWERING, TaskType.TEXT_GENERATION, TaskType.CODE_GENERATION, TaskType.REASONING],
                cost_per_token=0.0,
                quality_score=0.88,
                max_tokens=8192
            )

        ]
        
        
        for model in default_models:
            self.register_model(model)
    
    async def initialize(self):
        """初始化协调器"""
        try:
            # 验证所有模型配置
            for model_id, model_config in self.models.items():
                if not await self.providers[model_config.provider].validate_config(model_config):
                    logger.warning(f"模型配置验证失败: {model_id}")
                    model_config.is_active = False
            
            # 初始化速率限制器
            for model_id, model_config in self.models.items():
                self.rate_limits[model_id] = asyncio.Queue(maxsize=model_config.rate_limit)
            
            # 启动任务处理循环
            self.is_running = True
            asyncio.create_task(self._task_processing_loop())
            
            logger.info("多模型协调器初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"多模型协调器初始化失败: {e}")
            return False
    
    async def shutdown(self):
        """关闭协调器"""
        self.is_running = False
        
        # 等待所有任务完成
        timeout = 30
        start_time = datetime.now()
        
        while self.active_tasks and (datetime.now() - start_time).total_seconds() < timeout:
            await asyncio.sleep(1)
        
        logger.info("多模型协调器已关闭")
    
    def register_model(self, model_config: ModelConfig) -> bool:
        """注册AI模型"""
        try:
            self.models[model_config.model_id] = model_config
            logger.info(f"模型已注册: {model_config.model_id} ({model_config.model_name})")
            return True
            
        except Exception as e:
            logger.error(f"模型注册失败: {e}")
            return False
    
    def unregister_model(self, model_id: str) -> bool:
        """注销AI模型"""
        if model_id in self.models:
            del self.models[model_id]
            if model_id in self.rate_limits:
                del self.rate_limits[model_id]
            logger.info(f"模型已注销: {model_id}")
            return True
        return False
    
    async def submit_task(self, task_request: TaskRequest) -> str:
        """提交任务"""
        try:
            # 生成任务ID
            if not task_request.task_id:
                task_request.task_id = str(uuid.uuid4())
            
            # 存储活跃任务
            self.active_tasks[task_request.task_id] = task_request
            
            # 添加到队列
            await self.task_queue.put(task_request)
            
            logger.info(f"任务已提交: {task_request.task_id} ({task_request.task_type.value})")
            return task_request.task_id
            
        except Exception as e:
            logger.error(f"任务提交失败: {e}")
            raise
    
    async def get_task_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        return self.task_results.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].priority = TaskPriority.URGENT  # 标记为取消
            logger.info(f"任务已取消: {task_id}")
            return True
        return False
    
    def get_available_models(self, task_type: TaskType = None) -> List[ModelConfig]:
        """获取可用模型列表"""
        available_models = []
        
        for model_config in self.models.values():
            if model_config.is_active:
                if task_type is None or task_type in model_config.capabilities:
                    available_models.append(model_config)
        
        return available_models
    
    async def _task_processing_loop(self):
        """任务处理循环"""
        while self.is_running:
            try:
                # 从队列获取任务
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                # 处理任务
                asyncio.create_task(self._process_task(task))
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"任务处理循环错误: {e}")
    
    async def _process_task(self, task_request: TaskRequest):
        """处理单个任务"""
        start_time = datetime.now()
        
        try:
            logger.info(f"开始处理任务: {task_request.task_id}")
            
            # 初始化任务结果
            task_result = TaskResult(
                task_id=task_request.task_id,
                status=TaskStatus.PROCESSING
            )
            
            # 选择模型
            selected_models = self._select_models(task_request)
            
            if not selected_models:
                raise ValueError("没有找到合适的模型来处理此任务")
            
            # 并行执行模型
            model_tasks = []
            for model_config in selected_models:
                task = asyncio.create_task(
                    self._execute_model(model_config, task_request)
                )
                model_tasks.append(task)
            
            # 等待所有模型完成
            model_results = await asyncio.gather(*model_tasks, return_exceptions=True)
            
            # 处理结果
            valid_results = []
            for result in model_results:
                if isinstance(result, ModelResult):
                    valid_results.append(result)
                else:
                    logger.error(f"模型执行异常: {result}")
            
            task_result.model_results = valid_results
            
            # 融合结果
            if valid_results:
                final_content, fusion_method = await self._fuse_results(valid_results, task_request)
                task_result.final_content = final_content
                task_result.fusion_method = fusion_method
                task_result.status = TaskStatus.COMPLETED
            else:
                task_result.status = TaskStatus.FAILED
                task_result.error = "所有模型执行失败"
            
            # 计算统计信息
            task_result.total_time = (datetime.now() - start_time).total_seconds()
            task_result.total_cost = sum(r.cost for r in valid_results)
            task_result.processing_log.append(f"任务完成，使用 {len(valid_results)} 个模型")
            
            # 存储结果
            self.task_results[task_request.task_id] = task_result
            
            # 移除活跃任务
            if task_request.task_id in self.active_tasks:
                del self.active_tasks[task_request.task_id]
            
            logger.info(f"任务处理完成: {task_request.task_id}")
            
        except Exception as e:
            logger.error(f"任务处理失败: {task_request.task_id} - {e}")
            
            # 创建失败结果
            task_result = TaskResult(
                task_id=task_request.task_id,
                status=TaskStatus.FAILED,
                error=str(e),
                total_time=(datetime.now() - start_time).total_seconds()
            )
            
            self.task_results[task_request.task_id] = task_result
            
            # 移除活跃任务
            if task_request.task_id in self.active_tasks:
                del self.active_tasks[task_request.task_id]
    
    def _select_models(self, task_request: TaskRequest) -> List[ModelConfig]:
        """选择适合的模型"""
        available_models = self.get_available_models()
        
        # 过滤模型
        filtered_models = []
        for model in available_models:
            # 检查能力匹配
            if not any(cap in model.capabilities for cap in task_request.required_capabilities):
                continue
            
            # 检查排除列表
            if model.model_id in task_request.exclude_models:
                continue
            
            # 检查成本限制
            if task_request.max_cost and model.cost_per_token > task_request.max_cost:
                continue
            
            filtered_models.append(model)
        
        # 排序和选择
        if not filtered_models:
            return []
        
        # 按优先级排序：质量分数、速度、成本
        filtered_models.sort(
            key=lambda m: (m.quality_score, -m.cost_per_token, -m.max_tokens),
            reverse=True
        )
        
        # 应用首选模型
        preferred_models = []
        other_models = []
        
        for model in filtered_models:
            if model.model_id in task_request.preferred_models:
                preferred_models.append(model)
            else:
                other_models.append(model)
        
        # 合并并限制数量
        selected = preferred_models + other_models[:3]  # 最多选择3个模型
        
        return selected
    
    async def _execute_model(self, model_config: ModelConfig, task_request: TaskRequest) -> ModelResult:
        """执行单个模型"""
        start_time = datetime.now()
        
        try:
            # 检查速率限制
            await self._check_rate_limit(model_config.model_id)
            
            # 准备提示词
            prompt = self._prepare_prompt(task_request, model_config)
            
            # 调用模型
            provider = self.providers[model_config.provider]
            result = await provider.generate(model_config, prompt)
            
            logger.debug(f"模型 {model_config.model_id} 执行完成，耗时 {result.processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"模型 {model_config.model_id} 执行失败: {e}")
            
            return ModelResult(
                model_id=model_config.model_id,
                content="",
                confidence=0.0,
                processing_time=(datetime.now() - start_time).total_seconds(),
                error=str(e)
            )
    
    async def _check_rate_limit(self, model_id: str):
        """检查速率限制"""
        if model_id in self.rate_limits:
            # 简化的速率限制检查
            # 实际实现中需要更复杂的token bucket算法
            await asyncio.sleep(0.1)  # 模拟速率限制延迟
    
    def _prepare_prompt(self, task_request: TaskRequest, model_config: ModelConfig) -> str:
        """准备提示词"""
        base_prompt = task_request.content
        
        # 根据任务类型添加上下文
        if task_request.task_type == TaskType.CODE_GENERATION:
            base_prompt = f"请生成代码:\n{task_request.content}"
        elif task_request.task_type == TaskType.SUMMARIZATION:
            base_prompt = f"请总结以下内容:\n{task_request.content}"
        elif task_request.task_type == TaskType.TRANSLATION:
            base_prompt = f"请翻译以下内容:\n{task_request.content}"
        
        # 添加模型特定的后缀
        if model_config.model_type == ModelType.CREATIVE:
            base_prompt += "\n请用创意和想象力回答。"
        
        return base_prompt
    
    async def _fuse_results(self, results: List[ModelResult], task_request: TaskRequest) -> Tuple[str, str]:
        """融合多个模型的结果"""
        if len(results) == 1:
            return results[0].content, "single_model"
        
        # 尝试不同的融合策略
        fusion_methods = ["best", "weighted", "majority"]
        
        for method in fusion_methods:
            if method in self.fusion_strategies:
                try:
                    content, score = await self.fusion_strategies[method](results, task_request)
                    if content:
                        return content, method
                except Exception as e:
                    logger.warning(f"融合策略 {method} 失败: {e}")
        
        # 默认返回最佳结果
        best_result = max(results, key=lambda r: r.confidence * r.quality_score)
        return best_result.content, "best_result"
    
    async def _fusion_best_result(self, results: List[ModelResult], task_request: TaskRequest) -> Tuple[str, float]:
        """选择最佳结果"""
        if not results:
            return "", 0.0
        
        # 综合评分：置信度 × 质量分数 × 处理时间权重
        def calculate_score(result: ModelResult) -> float:
            time_score = max(0, 1 - result.processing_time / 10)  # 10秒为基准
            return result.confidence * result.quality_score * time_score
        
        best_result = max(results, key=calculate_score)
        return best_result.content, calculate_score(best_result)
    
    async def _fusion_weighted_average(self, results: List[ModelResult], task_request: TaskRequest) -> Tuple[str, float]:
        """加权平均融合"""
        if not results:
            return "", 0.0
        
        # 按质量分数加权
        total_weight = sum(r.quality_score for r in results)
        if total_weight == 0:
            return "", 0.0
        
        # 简化的文本融合：拼接前100个字符
        fused_content = []
        for result in results:
            weight = result.quality_score / total_weight
            if weight > 0.1:  # 只包含权重大于10%的结果
                content_preview = result.content[:100]
                fused_content.append(f"[{result.model_id}:{weight:.2f}] {content_preview}")
        
        return "\n".join(fused_content), total_weight / len(results)
    
    async def _fusion_majority_vote(self, results: List[ModelResult], task_request: TaskRequest) -> Tuple[str, float]:
        """多数投票融合"""
        if not results:
            return "", 0.0
        
        # 对简单答案进行投票（这里简化为选择最高置信度的结果）
        best_result = max(results, key=lambda r: r.confidence)
        return best_result.content, best_result.confidence
    
    async def _fusion_ensemble(self, results: List[ModelResult], task_request: TaskRequest) -> Tuple[str, float]:
        """集成融合"""
        if not results:
            return "", 0.0
        
        # 集成方法：结合多个结果的优势
        contents = [r.content for r in results if r.content]
        if not contents:
            return "", 0.0
        
        # 简化的集成：选择最完整的结果
        best_content = max(contents, key=len)
        avg_confidence = sum(r.confidence for r in results) / len(results)
        
        return best_content, avg_confidence
    
    async def get_coordinator_stats(self) -> Dict[str, Any]:
        """获取协调器统计信息"""
        active_tasks = len(self.active_tasks)
        total_tasks = len(self.task_results)
        completed_tasks = sum(1 for r in self.task_results.values() if r.status == TaskStatus.COMPLETED)
        
        avg_processing_time = 0
        avg_cost = 0
        
        if self.task_results:
            completed_results = [r for r in self.task_results.values() if r.status == TaskStatus.COMPLETED]
            if completed_results:
                avg_processing_time = sum(r.total_time for r in completed_results) / len(completed_results)
                avg_cost = sum(r.total_cost for r in completed_results) / len(completed_results)
        
        return {
            "active_tasks": active_tasks,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "success_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
            "avg_processing_time": avg_processing_time,
            "avg_cost": avg_cost,
            "registered_models": len(self.models),
            "active_models": sum(1 for m in self.models.values() if m.is_active)
        }
    
    # 插件友好的方法
    def get_plugin_compatible_stats(self) -> Dict[str, Any]:
        """
        获取与插件兼容的统计信息
        
        Returns:
            包含插件所需统计信息的字典
        """
        stats = {
            "coordinator_info": {
                "is_running": self.is_running,
                "total_models": len(self.models),
                "active_models": sum(1 for m in self.models.values() if m.is_active),
                "total_providers": len(self.providers),
                "total_fusion_strategies": len(self.fusion_strategies)
            },
            "task_statistics": self.get_coordinator_stats(),
            "model_summary": {
                "by_provider": {},
                "by_type": {},
                "by_capability": {}
            },
            "performance_metrics": {
                "total_processed": len(self.task_results),
                "avg_confidence": 0.0,
                "avg_quality": 0.0
            }
        }
        
        # 按提供者分组统计模型
        for model in self.models.values():
            provider = model.provider
            if provider not in stats["model_summary"]["by_provider"]:
                stats["model_summary"]["by_provider"][provider] = 0
            stats["model_summary"]["by_provider"][provider] += 1
        
        # 按类型分组统计模型
        for model in self.models.values():
            model_type = model.model_type.value
            if model_type not in stats["model_summary"]["by_type"]:
                stats["model_summary"]["by_type"][model_type] = 0
            stats["model_summary"]["by_type"][model_type] += 1
        
        # 按能力分组统计模型
        for model in self.models.values():
            for capability in model.capabilities:
                cap = capability.value
                if cap not in stats["model_summary"]["by_capability"]:
                    stats["model_summary"]["by_capability"][cap] = 0
                stats["model_summary"]["by_capability"][cap] += 1
        
        # 计算性能指标
        if self.task_results:
            completed_results = [r for r in self.task_results.values() if r.status == TaskStatus.COMPLETED]
            if completed_results:
                all_confidences = []
                all_qualities = []
                for result in completed_results:
                    for model_result in result.model_results:
                        all_confidences.append(model_result.confidence)
                        all_qualities.append(model_result.quality_score)
                
                if all_confidences:
                    stats["performance_metrics"]["avg_confidence"] = sum(all_confidences) / len(all_confidences)
                if all_qualities:
                    stats["performance_metrics"]["avg_quality"] = sum(all_qualities) / len(all_qualities)
        
        return stats
    
    def export_model_configs(self) -> List[Dict[str, Any]]:
        """
        导出所有模型配置（用于插件序列化）
        
        Returns:
            模型配置字典列表
        """
        configs = []
        for model in self.models.values():
            config_dict = asdict(model)
            config_dict["model_type"] = model.model_type.value
            config_dict["capabilities"] = [cap.value for cap in model.capabilities]
            configs.append(config_dict)
        return configs
    
    def import_model_configs(self, configs: List[Dict[str, Any]]) -> int:
        """
        导入模型配置（用于插件反序列化）
        
        Args:
            configs: 模型配置字典列表
            
        Returns:
            成功导入的模型数量
        """
        imported_count = 0
        
        for config_dict in configs:
            try:
                # 重建枚举类型
                model_type = ModelType(config_dict["model_type"])
                capabilities = [TaskType(cap) for cap in config_dict["capabilities"]]
                
                # 创建模型配置
                model_config = ModelConfig(
                    model_id=config_dict["model_id"],
                    model_name=config_dict["model_name"],
                    model_type=model_type,
                    provider=config_dict["provider"],
                    api_key=config_dict.get("api_key"),
                    base_url=config_dict.get("base_url"),
                    max_tokens=config_dict.get("max_tokens", 4096),
                    temperature=config_dict.get("temperature", 0.7),
                    timeout=config_dict.get("timeout", 60),
                    rate_limit=config_dict.get("rate_limit", 100),
                    capabilities=capabilities,
                    is_active=config_dict.get("is_active", True),
                    cost_per_token=config_dict.get("cost_per_token", 0.0),
                    quality_score=config_dict.get("quality_score", 1.0)
                )
                
                if self.register_model(model_config):
                    imported_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to import model config {config_dict.get('model_id', 'unknown')}: {e}")
        
        return imported_count
    
    def get_model_by_id(self, model_id: str) -> Optional[ModelConfig]:
        """
        根据ID获取模型配置（插件便利方法）
        
        Args:
            model_id: 模型ID
            
        Returns:
            模型配置或None
        """
        return self.models.get(model_id)
    
    def get_models_by_provider(self, provider: str) -> List[ModelConfig]:
        """
        根据提供者获取模型列表（插件便利方法）
        
        Args:
            provider: 模型提供者
            
        Returns:
            模型配置列表
        """
        return [model for model in self.models.values() if model.provider == provider]
    
    def get_models_by_capability(self, capability: TaskType) -> List[ModelConfig]:
        """
        根据能力获取模型列表（插件便利方法）
        
        Args:
            capability: 任务能力
            
        Returns:
            模型配置列表
        """
        return [model for model in self.models.values() if capability in model.capabilities]
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查（插件监控方法）
        
        Returns:
            健康状态信息
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        try:
            # 检查协调器状态
            health_status["checks"]["coordinator_running"] = self.is_running
            
            # 检查模型状态
            active_models = sum(1 for m in self.models.values() if m.is_active)
            total_models = len(self.models)
            health_status["checks"]["models_status"] = {
                "active": active_models,
                "total": total_models,
                "health_ratio": active_models / total_models if total_models > 0 else 0
            }
            
            # 检查任务状态
            failed_tasks = sum(1 for r in self.task_results.values() if r.status == TaskStatus.FAILED)
            total_tasks = len(self.task_results)
            health_status["checks"]["tasks_status"] = {
                "failed": failed_tasks,
                "total": total_tasks,
                "success_ratio": (total_tasks - failed_tasks) / total_tasks if total_tasks > 0 else 1.0
            }
            
            # 检查提供者状态
            provider_health = {}
            for provider_name, provider in self.providers.items():
                try:
                    # 简单的健康检查 - 实际实现中可能需要更复杂的检查
                    provider_health[provider_name] = {"status": "healthy", "available": True}
                except Exception as e:
                    provider_health[provider_name] = {"status": "error", "available": False, "error": str(e)}
            
            health_status["checks"]["providers_status"] = provider_health
            
            # 评估总体健康状态
            if health_status["checks"]["models_status"]["health_ratio"] < 0.5:
                health_status["status"] = "warning"
            if health_status["checks"]["tasks_status"]["success_ratio"] < 0.7:
                health_status["status"] = "critical"
            if any(p["status"] == "error" for p in provider_health.values()):
                health_status["status"] = "critical"
            
            return health_status
            
        except Exception as e:
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "checks": {}
            }
    
    def __str__(self) -> str:
        """返回协调器的字符串表示"""
        return f"MultiModelCoordinator(models={len(self.models)}, running={self.is_running})"
    
    def __repr__(self) -> str:
        """返回协调器的详细字符串表示"""
        return (f"MultiModelCoordinator("
                f"models={len(self.models)}, "
                f"active_models={sum(1 for m in self.models.values() if m.is_active)}, "
                f"providers={len(self.providers)}, "
                f"active_tasks={len(self.active_tasks)}, "
                f"total_results={len(self.task_results)})")