"""
AgentBus技能系统

基于Moltbot的SKILL.md概念实现的技能系统框架，提供技能的发现、加载、管理和生命周期控制。

主要组件:
- BaseSkill: 技能基类，定义技能的基本接口
- SkillMetadata: 技能元数据类，存储技能的配置信息
- SkillRegistry: 技能注册表，管理技能的注册和发现
- SkillManager: 技能管理器，提供技能的全生命周期管理
- SkillLifecycleManager: 技能生命周期管理器，提供监控、健康检查等功能

使用示例:
```python
from skills import SkillManager, BaseSkill, SkillMetadata, SkillFactory

# 创建技能管理器
manager = SkillManager(workspace_dir="/path/to/workspace", 
                       config_dir="/path/to/config")

# 发现技能
skills = await manager.discover_skills([Path("/path/to/skills")])

# 加载技能
for skill_metadata in skills:
    await manager.load_skill(skill_metadata)
    await manager.activate_skill(skill_metadata.name)

# 执行技能
result = await manager.execute_skill("skill_name", "action", {"param": "value"})
```
"""

from .base import (
    # 基类和接口
    BaseSkill,
    SkillFactory,
    SkillInterface,
    
    # 数据类
    SkillMetadata,
    SkillContext,
    
    # 枚举
    SkillStatus,
    SkillType,
    
    # 异常类
    SkillValidationError,
    SkillLoadError,
    SkillExecutionError,
    SkillDependencyError,
)

from .registry import (
    SkillRegistry,
    SkillDiscovery,
    SkillManager,
)

from .manager import (
    SkillLifecycleManager,
    LifecycleConfig,
    LifecycleState,
    HealthStatus,
    SkillMetrics,
)

# 版本信息
__version__ = "1.0.0"
__author__ = "AgentBus Team"
__description__ = "AgentBus技能系统框架"

# 导出的公共接口
__all__ = [
    # 基类和接口
    "BaseSkill",
    "SkillFactory", 
    "SkillInterface",
    
    # 数据类
    "SkillMetadata",
    "SkillContext",
    
    # 枚举
    "SkillStatus",
    "SkillType",
    "LifecycleState",
    "HealthStatus",
    
    # 异常类
    "SkillValidationError",
    "SkillLoadError", 
    "SkillExecutionError",
    "SkillDependencyError",
    
    # 核心组件
    "SkillRegistry",
    "SkillDiscovery",
    "SkillManager",
    "SkillLifecycleManager",
    
    # 配置类
    "LifecycleConfig",
    "SkillMetrics",
]

# 工具函数
def create_skill_metadata(
    name: str,
    description: str,
    version: str = "1.0.0",
    **kwargs
) -> SkillMetadata:
    """创建技能元数据的便捷函数"""
    return SkillMetadata(
        name=name,
        description=description,
        version=version,
        **kwargs
    )


def create_lifecycle_config(**kwargs) -> LifecycleConfig:
    """创建生命周期配置的便捷函数"""
    return LifecycleConfig(**kwargs)


# 模块初始化
def _init_module():
    """模块初始化函数"""
    import logging
    
    # 设置技能系统的日志记录器
    logger = logging.getLogger("agentbus.skills")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    logger.info(f"AgentBus Skills System v{__version__} initialized")


# 自动初始化
_init_module()


# 兼容性：支持从不同路径导入
try:
    from .base import *
    from .registry import *
    from .manager import *
except ImportError as e:
    # 在某些情况下可能无法导入所有模块，记录警告但不失败
    import warnings
    warnings.warn(f"部分技能系统模块导入失败: {e}", RuntimeWarning)


# 文档生成相关的辅助函数
def get_skill_template() -> str:
    """获取技能模板字符串"""
    return """
---
name: example_skill
description: 示例技能
version: 1.0.0
author: Your Name
homepage: https://example.com
license: MIT
tags: [example, utility]
category: tool
enabled: true
auto_activate: true
priority: 0
requires:
  python_version: ">=3.8"
dependencies: []
conflicts: []
permissions: []
config_schema:
  api_key:
    type: string
    required: true
    description: API密钥
install_info:
  pip_packages:
    - requests
    - numpy
---

# 技能描述

这里是技能的详细描述文档。

## 功能

- 功能1
- 功能2

## 使用方法

```python
result = await skill.execute("action", {"param": "value"})
```

## 配置

技能需要以下配置项：

- api_key: API密钥
"""


def validate_skill_file(skill_file_path: str) -> dict:
    """验证技能文件"""
    import yaml
    import json
    from pathlib import Path
    
    skill_file = Path(skill_file_path)
    
    if not skill_file.exists():
        return {"valid": False, "error": f"File not found: {skill_file_path}"}
    
    try:
        with open(skill_file, 'r', encoding='utf-8') as f:
            if skill_file.suffix.lower() in ['.yml', '.yaml']:
                data = yaml.safe_load(f)
            elif skill_file.suffix.lower() == '.json':
                data = json.load(f)
            else:
                return {"valid": False, "error": f"Unsupported file format: {skill_file.suffix}"}
        
        # 基本验证
        required_fields = ['name', 'description']
        for field in required_fields:
            if field not in data:
                return {"valid": False, "error": f"Missing required field: {field}"}
        
        return {"valid": True, "data": data}
    
    except Exception as e:
        return {"valid": False, "error": f"Error parsing skill file: {e}"}


# 示例技能类
class ExampleSkill(BaseSkill):
    """示例技能类"""
    
    def __init__(self, metadata: SkillMetadata):
        super().__init__(metadata)
        self.logger = logging.getLogger(f"skill.{metadata.name}")
    
    async def initialize(self, context: SkillContext) -> None:
        """初始化技能"""
        self.logger.info(f"Initializing skill: {self.metadata.name}")
        self.context = context
        self._initialized = True
    
    async def activate(self) -> None:
        """激活技能"""
        self.logger.info(f"Activating skill: {self.metadata.name}")
        # 技能激活逻辑
    
    async def deactivate(self) -> None:
        """停用技能"""
        self.logger.info(f"Deactivating skill: {self.metadata.name}")
        # 技能停用逻辑
    
    async def execute(self, action: str, params: dict) -> Any:
        """执行技能操作"""
        self.logger.info(f"Executing {action} with params: {params}")
        
        if action == "hello":
            return f"Hello from {self.metadata.name}!"
        elif action == "status":
            return {
                "name": self.metadata.name,
                "status": self.status.value,
                "initialized": self._initialized
            }
        else:
            raise SkillExecutionError(f"Unknown action: {action}")
    
    def get_capabilities(self) -> list:
        """获取技能能力列表"""
        return ["hello", "status"]
    
    def get_commands(self) -> list:
        """获取技能命令列表"""
        return [
            {
                "name": "hello",
                "description": "打招呼",
                "usage": "hello"
            },
            {
                "name": "status", 
                "description": "查看技能状态",
                "usage": "status"
            }
        ]


class ExampleSkillFactory(SkillFactory):
    """示例技能工厂"""
    
    @staticmethod
    def create_skill(metadata: SkillMetadata) -> BaseSkill:
        """创建技能实例"""
        return ExampleSkill(metadata)
    
    @staticmethod
    def validate_metadata(metadata: SkillMetadata) -> bool:
        """验证技能元数据"""
        return bool(metadata.name and metadata.description)


# 为了方便使用，可以导出示例类和工厂
__all__.extend(["ExampleSkill", "ExampleSkillFactory"])