"""
技能系统基类
Base Skill System

技能模块的基础架构，用于扩展AI助手功能
Base architecture for skill modules to extend AI assistant functionality
"""

from abc import ABC, abstractmethod
from typing import (
    Any, Dict, List, Optional, Union, Callable, 
    AsyncIterator, Awaitable, TypeVar
)
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
import asyncio
import json
from contextlib import asynccontextmanager

from ..core.logger import get_logger
from ..adapters.base import Message, User, AdapterType

# 类型定义
T = TypeVar('T')
SkillInput = Union[str, Dict[str, Any], Message]
SkillOutput = Union[str, Dict[str, Any], List[str], None]


class SkillType(Enum):
    """技能类型枚举"""
    COMMAND = "command"  # 命令技能
    AI_RESPONSE = "ai_response"  # AI响应技能
    CONTENT_PROCESSING = "content_processing"  # 内容处理技能
    MEDIA_HANDLING = "media_handling"  # 媒体处理技能
    SYSTEM_TOOL = "system_tool"  # 系统工具技能
    WEBHOOK = "webhook"  # Webhook技能
    SCHEDULED = "scheduled"  # 定时任务技能
    CUSTOM = "custom"  # 自定义技能


class SkillStatus(Enum):
    """技能状态枚举"""
    INACTIVE = "inactive"
    LOADING = "loading"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class SkillMetadata:
    """技能元数据"""
    name: str
    version: str
    description: str
    author: str
    skill_type: SkillType
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    
    # 运行配置
    timeout: int = 30  # 秒
    max_concurrent: int = 5
    memory_limit: int = 128  # MB
    
    # AI配置
    ai_model: Optional[str] = None
    ai_prompt: Optional[str] = None
    ai_temperature: float = 0.7
    
    # UI配置
    icon: Optional[str] = None
    color: Optional[str] = None
    category: Optional[str] = None


@dataclass
class SkillContext:
    """技能执行上下文"""
    user: User
    message: Message
    chat_id: str
    platform: AdapterType
    session_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 扩展数据
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 引用其他技能的结果
    references: Dict[str, Any] = field(default_factory=dict)
    
    def get_user_input(self) -> str:
        """获取用户输入文本"""
        if isinstance(self.message.content, str):
            return self.message.content
        elif isinstance(self.message.content, dict):
            return self.message.content.get('text', '')
        return str(self.message.content)
    
    def set_result(self, key: str, value: Any) -> None:
        """设置结果"""
        self.references[key] = value
    
    def get_result(self, key: str, default: Any = None) -> Any:
        """获取结果"""
        return self.references.get(key, default)


@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool
    output: SkillOutput = None
    execution_time: float = 0.0
    error: Optional[str] = None
    token_count: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def success(cls, output: SkillOutput, **kwargs) -> 'SkillResult':
        """创建成功结果"""
        return cls(success=True, output=output, **kwargs)
    
    @classmethod
    def error(cls, error: str, **kwargs) -> 'SkillResult':
        """创建错误结果"""
        return cls(success=False, output=None, error=error, **kwargs)


class BaseSkill(ABC):
    """
    基础技能抽象类
    
    所有技能模块必须继承此类并实现必要的抽象方法
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.metadata = self._get_metadata()
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.status = SkillStatus.INACTIVE
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._contexts: Dict[str, SkillContext] = {}
        
    def _get_metadata(self) -> SkillMetadata:
        """获取技能元数据"""
        # 默认实现，子类可以重写
        return SkillMetadata(
            name=self.__class__.__name__.lower().replace('skill', ''),
            version="1.0.0",
            description="A skill implementation",
            author="Unknown",
            skill_type=SkillType.CUSTOM
        )
    
    # === 抽象方法（必须实现） ===
    
    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行技能"""
        pass
    
    # === 可选方法（默认实现） ===
    
    async def initialize(self) -> None:
        """初始化技能"""
        self.status = SkillStatus.LOADING
        try:
            await self._do_initialize()
            self.status = SkillStatus.ACTIVE
            self.logger.info("Skill initialized", skill=self.metadata.name)
        except Exception as e:
            self.status = SkillStatus.ERROR
            self.logger.error("Failed to initialize skill", error=str(e))
            raise
    
    async def cleanup(self) -> None:
        """清理技能"""
        self.status = SkillStatus.DISABLED
        try:
            await self._do_cleanup()
            self.logger.info("Skill cleaned up", skill=self.metadata.name)
        except Exception as e:
            self.logger.error("Failed to cleanup skill", error=str(e))
    
    async def validate_config(self) -> bool:
        """验证配置"""
        return True
    
    async def get_help(self, context: Optional[SkillContext] = None) -> str:
        """获取帮助信息"""
        return f"{self.metadata.description}\n\nUsage: {self.metadata.name}"
    
    async def handle_command(self, context: SkillContext) -> SkillResult:
        """处理命令调用"""
        return await self.execute(context)
    
    async def handle_ai_response(self, context: SkillContext) -> SkillResult:
        """处理AI响应调用"""
        return await self.execute(context)
    
    async def handle_webhook(self, data: Dict[str, Any]) -> SkillResult:
        """处理Webhook调用"""
        return SkillResult.error("Webhook not implemented")
    
    async def handle_scheduled(self) -> SkillResult:
        """处理定时任务调用"""
        return SkillResult.error("Scheduled execution not implemented")
    
    async def handle_media(self, context: SkillContext, media_type: str) -> SkillResult:
        """处理媒体文件"""
        return SkillResult.error("Media handling not implemented")
    
    # === 事件系统 ===
    
    def on_event(self, event_name: str) -> Callable:
        """事件处理器装饰器"""
        def decorator(func: Callable) -> Callable:
            if event_name not in self._event_handlers:
                self._event_handlers[event_name] = []
            self._event_handlers[event_name].append(func)
            return func
        return decorator
    
    async def _emit_event(self, event_name: str, data: Any = None) -> None:
        """发射事件"""
        if event_name in self._event_handlers:
            for handler in self._event_handlers[event_name]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    self.logger.error("Event handler error", 
                                    event=event_name,
                                    error=str(e),
                                    handler=handler.__name__)
    
    # === 工具方法 ===
    
    async def call_other_skill(self, skill_name: str, context: SkillContext) -> Optional[SkillResult]:
        """调用其他技能"""
        # 这个方法需要在SkillManager中实现
        # 这里提供接口定义
        self.logger.warning("Skill-to-skill calling not implemented in base class")
        return None
    
    def create_response(self, text: str, **kwargs) -> SkillResult:
        """创建文本响应"""
        return SkillResult.success(text, **kwargs)
    
    def create_error_response(self, error: str, **kwargs) -> SkillResult:
        """创建错误响应"""
        return SkillResult.error(error, **kwargs)
    
    def create_media_response(self, media_type: str, url: str, **kwargs) -> SkillResult:
        """创建媒体响应"""
        content = {
            "type": media_type,
            "url": url,
            **kwargs
        }
        return SkillResult.success(content, **kwargs)
    
    def validate_input(self, context: SkillContext, required_fields: List[str]) -> bool:
        """验证输入"""
        for field in required_fields:
            if field not in context.data:
                return False
        return True
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)
    
    @property
    def is_active(self) -> bool:
        """检查是否活跃"""
        return self.status == SkillStatus.ACTIVE
    
    def get_info(self) -> Dict[str, Any]:
        """获取技能信息"""
        return {
            "name": self.metadata.name,
            "version": self.metadata.version,
            "type": self.metadata.skill_type.value,
            "status": self.status.value,
            "description": self.metadata.description,
            "tags": self.metadata.tags,
        }


class SkillRegistry:
    """技能注册表"""
    
    _skills: Dict[str, type] = {}
    _instances: Dict[str, BaseSkill] = {}
    _dependencies: Dict[str, List[str]] = {}
    
    @classmethod
    def register(cls, name: str, dependencies: List[str] = None):
        """注册技能"""
        def decorator(skill_class: type) -> type:
            if not issubclass(skill_class, BaseSkill):
                raise ValueError(f"Skill class must inherit from BaseSkill: {skill_class}")
            cls._skills[name] = skill_class
            if dependencies:
                cls._dependencies[name] = dependencies
            return skill_class
        return decorator
    
    @classmethod
    def get_skill_class(cls, name: str) -> Optional[type]:
        """获取技能类"""
        return cls._skills.get(name)
    
    @classmethod
    def create_skill(cls, name: str, config: Dict[str, Any] = None) -> BaseSkill:
        """创建技能实例"""
        skill_class = cls.get_skill_class(name)
        if not skill_class:
            raise ValueError(f"Skill '{name}' not registered")
        
        if name in cls._instances:
            return cls._instances[name]
        
        instance = skill_class(config)
        cls._instances[name] = instance
        return instance
    
    @classmethod
    def get_skill(cls, name: str) -> Optional[BaseSkill]:
        """获取技能实例"""
        return cls._instances.get(name)
    
    @classmethod
    def list_skills(cls) -> List[str]:
        """列出所有注册的技能"""
        return list(cls._skills.keys())
    
    @classmethod
    def get_all_skills(cls) -> Dict[str, type]:
        """获取所有注册的技能类"""
        return cls._skills.copy()
    
    @classmethod
    def get_dependencies(cls, skill_name: str) -> List[str]:
        """获取技能依赖"""
        return cls._dependencies.get(skill_name, [])
    
    @classmethod
    def resolve_dependencies(cls, skill_names: List[str]) -> List[str]:
        """解析依赖关系并返回排序后的技能列表"""
        # 简单的拓扑排序实现
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(skill_name: str):
            if skill_name in temp_visited:
                raise ValueError(f"Circular dependency detected: {skill_name}")
            if skill_name in visited:
                return
            
            temp_visited.add(skill_name)
            
            # 先访问依赖
            for dep in cls.get_dependencies(skill_name):
                visit(dep)
            
            temp_visited.remove(skill_name)
            visited.add(skill_name)
            result.append(skill_name)
        
        for skill_name in skill_names:
            if skill_name in cls._skills:
                visit(skill_name)
        
        return result


# 自动注册装饰器
def skill(name: str, dependencies: List[str] = None):
    """技能注册装饰器"""
    return SkillRegistry.register(name, dependencies)


class SkillManager:
    """技能管理器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.skills: Dict[str, BaseSkill] = {}
        self._execution_pool: Optional[asyncio.Semaphore] = None
    
    async def initialize(self, skill_configs: Dict[str, Dict[str, Any]] = None) -> None:
        """初始化所有技能"""
        configs = skill_configs or {}
        
        # 创建所有技能实例
        for skill_name in SkillRegistry.list_skills():
            try:
                skill_config = configs.get(skill_name, {})
                skill_instance = SkillRegistry.create_skill(skill_name, skill_config)
                self.skills[skill_name] = skill_instance
            except Exception as e:
                self.logger.error("Failed to create skill instance", 
                                skill=skill_name, error=str(e))
        
        # 解析依赖并按顺序初始化
        skill_names = list(self.skills.keys())
        try:
            ordered_skills = SkillRegistry.resolve_dependencies(skill_names)
        except ValueError as e:
            self.logger.error("Dependency resolution failed", error=str(e))
            ordered_skills = skill_names
        
        # 初始化技能
        for skill_name in ordered_skills:
            if skill_name in self.skills:
                skill_instance = self.skills[skill_name]
                try:
                    if await skill_instance.validate_config():
                        await skill_instance.initialize()
                    else:
                        self.logger.warning("Skill config validation failed", skill=skill_name)
                except Exception as e:
                    self.logger.error("Failed to initialize skill", 
                                    skill=skill_name, error=str(e))
        
        # 创建执行池
        max_concurrent = max((skill.metadata.max_concurrent 
                             for skill in self.skills.values()), default=10)
        self._execution_pool = asyncio.Semaphore(max_concurrent)
        
        self.logger.info("Skill manager initialized", 
                        skill_count=len(self.skills),
                        max_concurrent=max_concurrent)
    
    async def execute_skill(self, skill_name: str, context: SkillContext) -> SkillResult:
        """执行技能"""
        if skill_name not in self.skills:
            return SkillResult.error(f"Skill '{skill_name}' not found")
        
        skill_instance = self.skills[skill_name]
        if not skill_instance.is_active:
            return SkillResult.error(f"Skill '{skill_name}' is not active")
        
        async with self._execution_pool:
            start_time = datetime.now()
            try:
                result = await skill_instance.execute(context)
                execution_time = (datetime.now() - start_time).total_seconds()
                result.execution_time = execution_time
                return result
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                self.logger.error("Skill execution failed", 
                                skill=skill_name, 
                                error=str(e),
                                execution_time=execution_time)
                return SkillResult.error(str(e), execution_time=execution_time)
    
    async def get_skill_help(self, skill_name: str, context: Optional[SkillContext] = None) -> str:
        """获取技能帮助"""
        if skill_name not in self.skills:
            return f"Skill '{skill_name}' not found"
        
        skill_instance = self.skills[skill_name]
        return await skill_instance.get_help(context)
    
    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有技能"""
        return [skill.get_info() for skill in self.skills.values()]
    
    async def cleanup(self) -> None:
        """清理所有技能"""
        for skill_instance in self.skills.values():
            try:
                await skill_instance.cleanup()
            except Exception as e:
                self.logger.error("Failed to cleanup skill", 
                                skill=skill_instance.metadata.name, error=str(e))