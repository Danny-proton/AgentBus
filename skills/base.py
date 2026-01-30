"""
AgentBus技能系统基类和接口定义

基于Moltbot的SKILL.md概念设计，提供技能系统的核心抽象和接口。
"""

import abc
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime


class SkillStatus(Enum):
    """技能状态枚举"""
    UNLOADED = "unloaded"
    LOADING = "loading"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"


class SkillType(Enum):
    """技能类型枚举"""
    TOOL = "tool"
    COMMAND = "command"
    INTEGRATION = "integration"
    UTILITY = "utility"
    WORKFLOW = "workflow"


@dataclass
class SkillMetadata:
    """技能元数据类，类似于SKILL.md的frontmatter"""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    homepage: str = ""
    license: str = ""
    tags: List[str] = field(default_factory=list)
    category: SkillType = SkillType.TOOL
    
    # 技能配置
    enabled: bool = True
    auto_activate: bool = True
    priority: int = 0
    
    # 依赖和前置条件
    requires: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    
    # 权限和配置
    permissions: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    
    # 安装信息
    install_info: Dict[str, Any] = field(default_factory=dict)
    
    # 统计信息
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "homepage": self.homepage,
            "license": self.license,
            "tags": self.tags,
            "category": self.category.value,
            "enabled": self.enabled,
            "auto_activate": self.auto_activate,
            "priority": self.priority,
            "requires": self.requires,
            "dependencies": self.dependencies,
            "conflicts": self.conflicts,
            "permissions": self.permissions,
            "config_schema": self.config_schema,
            "install_info": self.install_info,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "usage_count": self.usage_count,
        }


@dataclass
class SkillContext:
    """技能执行上下文"""
    workspace_dir: Path
    config_dir: Path
    data_dir: Path
    temp_dir: Path
    env_vars: Dict[str, str] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    logger_name: str = ""
    
    def get_path(self, name: str) -> Path:
        """获取指定名称的路径"""
        path_map = {
            "workspace": self.workspace_dir,
            "config": self.config_dir,
            "data": self.data_dir,
            "temp": self.temp_dir,
        }
        return path_map.get(name, self.workspace_dir)
    
    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取环境变量"""
        return self.env_vars.get(key, default)
    
    def get_config(self, key: str, default: Optional[Any] = None) -> Any:
        """获取配置值"""
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


class BaseSkill(abc.ABC):
    """技能基类"""
    
    def __init__(self, metadata: SkillMetadata):
        self.metadata = metadata
        self.status = SkillStatus.UNLOADED
        self.context: Optional[SkillContext] = None
        self.logger = None
        self._initialized = False
    
    @property
    def name(self) -> str:
        """技能名称"""
        return self.metadata.name
    
    @property
    def is_active(self) -> bool:
        """是否激活"""
        return self.status == SkillStatus.ACTIVE
    
    @property
    def is_loaded(self) -> bool:
        """是否已加载"""
        return self.status in [SkillStatus.ACTIVE, SkillStatus.INACTIVE]
    
    @abc.abstractmethod
    async def initialize(self, context: SkillContext) -> None:
        """初始化技能"""
        pass
    
    @abc.abstractmethod
    async def activate(self) -> None:
        """激活技能"""
        pass
    
    @abc.abstractmethod
    async def deactivate(self) -> None:
        """停用技能"""
        pass
    
    @abc.abstractmethod
    async def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """执行技能操作"""
        pass
    
    @abc.abstractmethod
    def get_capabilities(self) -> List[str]:
        """获取技能能力列表"""
        pass
    
    @abc.abstractmethod
    def get_commands(self) -> List[Dict[str, Any]]:
        """获取技能命令列表"""
        pass
    
    async def cleanup(self) -> None:
        """清理资源"""
        pass
    
    async def health_check(self) -> bool:
        """健康检查"""
        return True
    
    def update_metadata(self, **kwargs) -> None:
        """更新元数据"""
        for key, value in kwargs.items():
            if hasattr(self.metadata, key):
                setattr(self.metadata, key, value)
        self.metadata.updated_at = datetime.now()
    
    def increment_usage(self) -> None:
        """增加使用计数"""
        self.metadata.usage_count += 1
    
    def __str__(self) -> str:
        return f"Skill({self.name}, {self.status.value})"
    
    def __repr__(self) -> str:
        return f"BaseSkill(name='{self.name}', status='{self.status.value}')"


class SkillFactory:
    """技能工厂基类"""
    
    @staticmethod
    def create_skill(metadata: SkillMetadata) -> BaseSkill:
        """创建技能实例"""
        raise NotImplementedError("Subclasses must implement create_skill")
    
    @staticmethod
    def validate_metadata(metadata: SkillMetadata) -> bool:
        """验证技能元数据"""
        return bool(metadata.name and metadata.description)


class SkillInterface:
    """技能接口定义，定义了技能系统的核心方法"""
    
    @abc.abstractmethod
    async def discover_skills(self, paths: List[Path]) -> List[SkillMetadata]:
        """发现技能"""
        pass
    
    @abc.abstractmethod
    async def load_skill(self, metadata: SkillMetadata) -> BaseSkill:
        """加载技能"""
        pass
    
    @abc.abstractmethod
    async def unload_skill(self, skill_name: str) -> bool:
        """卸载技能"""
        pass
    
    @abc.abstractmethod
    async def activate_skill(self, skill_name: str) -> bool:
        """激活技能"""
        pass
    
    @abc.abstractmethod
    async def deactivate_skill(self, skill_name: str) -> bool:
        """停用技能"""
        pass
    
    @abc.abstractmethod
    async def execute_skill(self, skill_name: str, action: str, params: Dict[str, Any]) -> Any:
        """执行技能"""
        pass
    
    @abc.abstractmethod
    def get_skill_status(self, skill_name: str) -> Optional[SkillStatus]:
        """获取技能状态"""
        pass
    
    @abc.abstractmethod
    def list_skills(self, status_filter: Optional[Set[SkillStatus]] = None) -> List[str]:
        """列出技能"""
        pass


class SkillValidationError(Exception):
    """技能验证错误"""
    pass


class SkillLoadError(Exception):
    """技能加载错误"""
    pass


class SkillExecutionError(Exception):
    """技能执行错误"""
    pass


class SkillDependencyError(Exception):
    """技能依赖错误"""
    pass