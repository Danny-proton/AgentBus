"""
AI代理系统
AI Agent System

智能代理的Python实现，支持多模型、多任务和分布式执行
"""

from typing import Dict, List, Optional, Any, Union, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from abc import ABC, abstractmethod
import asyncio
import json
import uuid
import hashlib
from contextlib import asynccontextmanager

from ..core.logger import get_logger
from ..core.config import settings

logger = get_logger(__name__)


class AgentType(Enum):
    """代理类型枚举"""
    TEXT_GENERATION = "text_generation"      # 文本生成
    CODE_GENERATION = "code_generation"      # 代码生成
    IMAGE_GENERATION = "image_generation"    # 图像生成
    IMAGE_UNDERSTANDING = "image_understanding"  # 图像理解
    AUDIO_PROCESSING = "audio_processing"    # 音频处理
    VIDEO_PROCESSING = "video_processing"    # 视频处理
    REASONING = "reasoning"                  # 推理
    CONVERSATION = "conversation"            # 对话
    TASK_EXECUTION = "task_execution"        # 任务执行
    CUSTOM = "custom"                        # 自定义


class AgentStatus(Enum):
    """代理状态枚举"""
    IDLE = "idle"           # 空闲
    BUSY = "busy"          # 忙碌
    ERROR = "error"        # 错误
    MAINTENANCE = "maintenance"  # 维护
    OFFLINE = "offline"    # 离线


class ModelProvider(Enum):
    """模型提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """模型配置"""
    provider: ModelProvider
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: List[str] = field(default_factory=list)
    
    # 模型特定配置
    supports_streaming: bool = True
    supports_function_calling: bool = False
    max_context_length: int = 32000
    
    def get_model_id(self) -> str:
        """获取模型唯一标识"""
        return f"{self.provider.value}:{self.model_name}"


@dataclass
class AgentCapability:
    """代理能力"""
    type: AgentType
    description: str
    input_types: Set[str] = field(default_factory=set)
    output_types: Set[str] = field(default_factory=set)
    parameters: Dict[str, Any] = field(default_factory=dict)
    cost_per_request: float = 0.0
    estimated_time: float = 1.0  # 秒


@dataclass
class AgentMetrics:
    """代理指标"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    average_response_time: float = 0.0
    last_used: Optional[datetime] = None
    error_rate: float = 0.0
    
    def update_metrics(self, success: bool, tokens: int, cost: float, response_time: float):
        """更新指标"""
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        self.total_tokens += tokens
        self.total_cost += cost
        self.last_used = datetime.now()
        
        # 计算平均响应时间
        if self.total_requests > 0:
            self.average_response_time = (
                (self.average_response_time * (self.total_requests - 1) + response_time) 
                / self.total_requests
            )
        
        # 计算错误率
        if self.total_requests > 0:
            self.error_rate = self.failed_requests / self.total_requests
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests


@dataclass
class AgentRequest:
    """代理请求"""
    id: str
    agent_type: AgentType
    model_config: ModelConfig
    prompt: str
    system_prompt: Optional[str] = None
    context: Optional[List[Dict[str, Any]]] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # 优先级（数字越大优先级越高）
    timeout: float = 60.0  # 超时时间
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_request_hash(self) -> str:
        """获取请求哈希"""
        content = f"{self.prompt}:{self.agent_type.value}:{self.model_config.get_model_id()}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class AgentResponse:
    """代理响应"""
    request_id: str
    success: bool
    content: Any = None
    tokens_used: int = 0
    cost: float = 0.0
    response_time: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def success(cls, request_id: str, content: Any, **kwargs) -> 'AgentResponse':
        """创建成功响应"""
        return cls(request_id=request_id, success=True, content=content, **kwargs)
    
    @classmethod
    def error(cls, request_id: str, error: str, **kwargs) -> 'AgentResponse':
        """创建错误响应"""
        return cls(request_id=request_id, success=False, content=None, error=error, **kwargs)


class BaseAgent(ABC):
    """
    基础代理抽象类
    
    所有AI代理必须继承此类并实现必要的方法
    """
    
    def __init__(self, agent_id: str, name: str, model_config: ModelConfig):
        self.agent_id = agent_id
        self.name = name
        self.model_config = model_config
        self.status = AgentStatus.IDLE
        self.capabilities: List[AgentCapability] = []
        self.metrics = AgentMetrics()
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # 当前执行的任务
        self.current_tasks: Dict[str, asyncio.Task] = {}
        
        # 能力检测
        self._detect_capabilities()
    
    def _detect_capabilities(self) -> None:
        """检测代理能力"""
        # 子类可以重写此方法添加自定义能力检测
        pass
    
    # === 抽象方法（必须实现） ===
    
    @abstractmethod
    async def generate_text(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        context: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AgentResponse:
        """生成文本"""
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """验证代理连接"""
        pass
    
    # === 可选方法（默认实现） ===
    
    async def generate_code(
        self, 
        prompt: str, 
        language: str = "python",
        **kwargs
    ) -> AgentResponse:
        """生成代码"""
        code_prompt = f"Generate {language} code for the following task:\n{prompt}"
        return await self.generate_text(code_prompt, **kwargs)
    
    async def analyze_image(
        self, 
        image_url: str, 
        prompt: str = "Analyze this image",
        **kwargs
    ) -> AgentResponse:
        """分析图像"""
        if not any(cap.type == AgentType.IMAGE_UNDERSTANDING for cap in self.capabilities):
            return AgentResponse.error(
                "", "This agent does not support image analysis"
            )
        
        analysis_prompt = f"{prompt}\n\nImage URL: {image_url}"
        return await self.generate_text(analysis_prompt, **kwargs)
    
    async def process_audio(
        self, 
        audio_url: str, 
        task: str = "transcribe",
        **kwargs
    ) -> AgentResponse:
        """处理音频"""
        if not any(cap.type == AgentType.AUDIO_PROCESSING for cap in self.capabilities):
            return AgentResponse.error(
                "", "This agent does not support audio processing"
            )
        
        audio_prompt = f"Perform {task} on this audio: {audio_url}"
        return await self.generate_text(audio_prompt, **kwargs)
    
    async def generate_image(
        self, 
        prompt: str, 
        style: str = "realistic",
        **kwargs
    ) -> AgentResponse:
        """生成图像"""
        if not any(cap.type == AgentType.IMAGE_GENERATION for cap in self.capabilities):
            return AgentResponse.error(
                "", "This agent does not support image generation"
            )
        
        image_prompt = f"Generate a {style} image: {prompt}"
        return await self.generate_text(image_prompt, **kwargs)
    
    async def reason(self, prompt: str, **kwargs) -> AgentResponse:
        """推理"""
        if not any(cap.type == AgentType.REASONING for cap in self.capabilities):
            return AgentResponse.error(
                "", "This agent does not support reasoning"
            )
        
        reasoning_prompt = f"Analyze and reason about the following:\n{prompt}"
        return await self.generate_text(reasoning_prompt, **kwargs)
    
    # === 状态管理 ===
    
    async def execute_request(self, request: AgentRequest) -> AgentResponse:
        """执行代理请求"""
        start_time = datetime.now()
        
        try:
            self.status = AgentStatus.BUSY
            task_id = str(uuid.uuid4())
            
            # 创建执行任务
            task = asyncio.create_task(self._execute_with_monitoring(request))
            self.current_tasks[task_id] = task
            
            # 等待执行完成或超时
            try:
                response = await asyncio.wait_for(task, timeout=request.timeout)
                self.metrics.update_metrics(
                    success=response.success,
                    tokens=getattr(response, 'tokens_used', 0),
                    cost=getattr(response, 'cost', 0.0),
                    response_time=(datetime.now() - start_time).total_seconds()
                )
                return response
                
            except asyncio.TimeoutError:
                error_response = AgentResponse.error(
                    request.id, f"Request timed out after {request.timeout} seconds"
                )
                self.metrics.update_metrics(
                    success=False,
                    tokens=0,
                    cost=0.0,
                    response_time=request.timeout
                )
                return error_response
            
        finally:
            self.status = AgentStatus.IDLE
            # 清理任务
            if task_id in self.current_tasks:
                del self.current_tasks[task_id]
    
    async def _execute_with_monitoring(self, request: AgentRequest) -> AgentResponse:
        """带监控的执行"""
        try:
            # 根据代理类型选择执行方法
            if AgentType.TEXT_GENERATION in {cap.type for cap in self.capabilities}:
                return await self.generate_text(
                    request.prompt,
                    request.system_prompt,
                    request.context,
                    **request.parameters
                )
            elif AgentType.CODE_GENERATION in {cap.type for cap in self.capabilities}:
                return await self.generate_code(
                    request.prompt,
                    **request.parameters
                )
            else:
                # 默认使用文本生成
                return await self.generate_text(
                    request.prompt,
                    request.system_prompt,
                    request.context,
                    **request.parameters
                )
                
        except Exception as e:
            self.logger.error("Agent execution failed", 
                            agent_id=self.agent_id,
                            error=str(e))
            return AgentResponse.error(request.id, str(e))
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.current_tasks:
            task = self.current_tasks[task_id]
            if not task.done():
                task.cancel()
                del self.current_tasks[task_id]
                return True
        return False
    
    def get_info(self) -> Dict[str, Any]:
        """获取代理信息"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "model_config": {
                "provider": self.model_config.provider.value,
                "model_name": self.model_config.model_name,
                "max_tokens": self.model_config.max_tokens,
                "temperature": self.model_config.temperature
            },
            "status": self.status.value,
            "capabilities": [cap.type.value for cap in self.capabilities],
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "success_rate": self.metrics.get_success_rate(),
                "average_response_time": self.metrics.average_response_time,
                "total_cost": self.metrics.total_cost
            },
            "current_tasks": len(self.current_tasks)
        }


class AgentRegistry:
    """代理注册表"""
    
    _agents: Dict[str, BaseAgent] = {}
    _agent_factories: Dict[str, Callable] = {}
    
    @classmethod
    def register_agent(cls, agent_id: str, agent: BaseAgent) -> None:
        """注册代理"""
        cls._agents[agent_id] = agent
        logger.info("Agent registered", agent_id=agent_id, name=agent.name)
    
    @classmethod
    def register_factory(cls, agent_type: str, factory: Callable) -> None:
        """注册代理工厂"""
        cls._agent_factories[agent_type] = factory
        logger.info("Agent factory registered", agent_type=agent_type)
    
    @classmethod
    def create_agent(cls, agent_id: str, name: str, model_config: ModelConfig) -> BaseAgent:
        """创建代理"""
        # 这里可以根据模型配置创建不同类型的代理
        # 简化实现，使用通用代理
        from .agents.openai_agent import OpenAIAgent
        return OpenAIAgent(agent_id, name, model_config)
    
    @classmethod
    def get_agent(cls, agent_id: str) -> Optional[BaseAgent]:
        """获取代理"""
        return cls._agents.get(agent_id)
    
    @classmethod
    def list_agents(cls) -> List[str]:
        """列出所有代理"""
        return list(cls._agents.keys())
    
    @classmethod
    def remove_agent(cls, agent_id: str) -> bool:
        """移除代理"""
        if agent_id in cls._agents:
            del cls._agents[agent_id]
            logger.info("Agent removed", agent_id=agent_id)
            return True
        return False
    
    @classmethod
    def get_agent_by_type(cls, agent_type: AgentType) -> List[BaseAgent]:
        """根据类型获取代理"""
        return [
            agent for agent in cls._agents.values()
            if agent_type in {cap.type for cap in agent.capabilities}
        ]


class AgentManager:
    """代理管理器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.registry = AgentRegistry()
        
        # 代理池
        self.agent_pools: Dict[AgentType, List[BaseAgent]] = {}
        
        # 负载均衡
        self.round_robin_index: Dict[AgentType, int] = {}
        
        # 请求队列
        self.request_queue = asyncio.Queue()
        self.response_queue = asyncio.Queue()
        
        # 运行状态
        self.running = False
        self._worker_tasks: List[asyncio.Task] = []
    
    async def start(self) -> None:
        """启动代理管理器"""
        if self.running:
            return
        
        self.running = True
        
        # 创建工作协程
        worker_count = settings.plugins.get_setting("agent_workers", 4)
        for i in range(worker_count):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self._worker_tasks.append(task)
        
        self.logger.info("Agent manager started", workers=worker_count)
    
    async def stop(self) -> None:
        """停止代理管理器"""
        if not self.running:
            return
        
        self.running = False
        
        # 取消所有工作协程
        for task in self._worker_tasks:
            task.cancel()
        
        # 等待任务完成
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        self.logger.info("Agent manager stopped")
    
    async def register_agent(self, agent: BaseAgent) -> None:
        """注册代理"""
        self.registry.register_agent(agent.agent_id, agent)
        
        # 添加到对应的池中
        for capability in agent.capabilities:
            if capability.type not in self.agent_pools:
                self.agent_pools[capability.type] = []
            self.agent_pools[capability.type].append(agent)
        
        # 验证代理连接
        is_valid = await agent.validate_connection()
        if not is_valid:
            self.logger.warning("Agent connection validation failed", 
                              agent_id=agent.agent_id)
    
    async def create_agent(
        self,
        agent_id: str,
        name: str,
        model_config: ModelConfig
    ) -> BaseAgent:
        """创建并注册代理"""
        agent = self.registry.create_agent(agent_id, name, model_config)
        await self.register_agent(agent)
        return agent
    
    async def get_agent(
        self, 
        agent_type: AgentType,
        preferred_id: Optional[str] = None
    ) -> Optional[BaseAgent]:
        """获取代理"""
        # 优先使用指定ID的代理
        if preferred_id:
            agent = self.registry.get_agent(preferred_id)
            if agent and agent_type in {cap.type for cap in agent.capabilities}:
                return agent
        
        # 从池中选择
        if agent_type in self.agent_pools:
            agents = self.agent_pools[agent_type]
            if agents:
                # 使用轮询策略
                index = self.round_robin_index.get(agent_type, 0)
                selected_agent = agents[index % len(agents)]
                self.round_robin_index[agent_type] = (index + 1) % len(agents)
                return selected_agent
        
        return None
    
    async def execute_request(self, request: AgentRequest) -> AgentResponse:
        """执行代理请求"""
        # 获取合适的代理
        agent = await self.get_agent(request.agent_type, request.metadata.get("preferred_agent_id"))
        
        if not agent:
            return AgentResponse.error(
                request.id, 
                f"No available agent for type: {request.agent_type.value}"
            )
        
        # 执行请求
        return await agent.execute_request(request)
    
    async def batch_execute(
        self, 
        requests: List[AgentRequest]
    ) -> List[AgentResponse]:
        """批量执行请求"""
        tasks = []
        for request in requests:
            task = asyncio.create_task(self.execute_request(request))
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                processed_responses.append(
                    AgentResponse.error(requests[i].id, str(response))
                )
            else:
                processed_responses.append(response)
        
        return processed_responses
    
    async def _worker(self, worker_id: str) -> None:
        """工作协程"""
        self.logger.debug("Agent worker started", worker_id=worker_id)
        
        while self.running:
            try:
                # 处理请求队列中的任务
                request = await asyncio.wait_for(self.request_queue.get(), timeout=1.0)
                response = await self.execute_request(request)
                await self.response_queue.put(response)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error("Agent worker error", 
                                worker_id=worker_id,
                                error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_agents = len(self.registry.list_agents())
        
        agent_type_counts = {}
        for agent_type, agents in self.agent_pools.items():
            agent_type_counts[agent_type.value] = len(agents)
        
        return {
            "total_agents": total_agents,
            "agent_type_counts": agent_type_counts,
            "running": self.running,
            "worker_count": len(self._worker_tasks),
            "queue_sizes": {
                "request_queue": self.request_queue.qsize(),
                "response_queue": self.response_queue.qsize()
            }
        }


# 全局代理管理器实例
_agent_manager: Optional[AgentManager] = None


def get_agent_manager() -> AgentManager:
    """获取全局代理管理器"""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager


async def start_agent_manager() -> None:
    """启动全局代理管理器"""
    manager = get_agent_manager()
    await manager.start()


async def stop_agent_manager() -> None:
    """停止全局代理管理器"""
    global _agent_manager
    if _agent_manager:
        await _agent_manager.stop()
        _agent_manager = None


# 便利函数
async def execute_agent_request(request: AgentRequest) -> AgentResponse:
    """执行代理请求便利函数"""
    manager = get_agent_manager()
    return await manager.execute_request(request)


async def batch_execute_agent_requests(requests: List[AgentRequest]) -> List[AgentResponse]:
    """批量执行代理请求便利函数"""
    manager = get_agent_manager()
    return await manager.batch_execute(requests)