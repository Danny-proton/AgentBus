# AgentBus技能系统框架使用指南

## 概述

AgentBus技能系统基于Moltbot的SKILL.md概念设计，提供了完整的技能发现、加载、管理和生命周期控制功能。本指南将详细介绍如何使用该框架。

## 核心组件

### 1. BaseSkill - 技能基类

所有技能必须继承`BaseSkill`基类并实现以下抽象方法：

```python
from agentbus.skills import BaseSkill, SkillMetadata, SkillContext

class MySkill(BaseSkill):
    def __init__(self, metadata: SkillMetadata):
        super().__init__(metadata)
        # 初始化代码
    
    async def initialize(self, context: SkillContext) -> None:
        """初始化技能"""
        # 资源加载、配置读取等
    
    async def activate(self) -> None:
        """激活技能"""
        # 启动服务、注册事件等
    
    async def deactivate(self) -> None:
        """停用技能"""
        # 清理资源、停止服务等
    
    async def execute(self, action: str, params: dict) -> Any:
        """执行技能操作"""
        # 具体业务逻辑
    
    def get_capabilities(self) -> List[str]:
        """获取技能能力列表"""
        return ["action1", "action2"]
    
    def get_commands(self) -> List[Dict[str, Any]]:
        """获取技能命令列表"""
        return [
            {"name": "action1", "description": "操作1", "usage": "action1 [params]"},
            {"name": "action2", "description": "操作2", "usage": "action2 [params]"}
        ]
```

### 2. SkillMetadata - 技能元数据

技能元数据定义技能的基本信息和配置：

```python
from agentbus.skills import SkillMetadata, SkillType

metadata = SkillMetadata(
    name="my_skill",
    description="我的自定义技能",
    version="1.0.0",
    author="Author Name",
    category=SkillType.UTILITY,
    enabled=True,
    auto_activate=True,
    dependencies=["other_skill"],
    config_schema={
        "api_key": {"type": "string", "required": True},
        "timeout": {"type": "integer", "default": 30}
    }
)
```

### 3. SkillFactory - 技能工厂

使用工厂模式创建技能实例：

```python
from agentbus.skills import SkillFactory

class MySkillFactory(SkillFactory):
    @staticmethod
    def create_skill(metadata: SkillMetadata) -> BaseSkill:
        return MySkill(metadata)
    
    @staticmethod
    def validate_metadata(metadata: SkillMetadata) -> bool:
        return bool(metadata.name and metadata.description)
```

## 基本使用流程

### 1. 创建技能管理器

```python
from agentbus.skills import SkillManager
from pathlib import Path

# 创建技能管理器
manager = SkillManager(
    workspace_dir=Path("/path/to/workspace"),
    config_dir=Path("/path/to/config")
)
```

### 2. 发现技能

```python
# 从目录发现技能
skills = await manager.discover_skills([
    Path("/path/to/skills/directory")
])

# 从标准位置扫描技能
skills = await manager.discovery.scan_standard_locations()

print(f"发现 {len(skills)} 个技能:")
for skill in skills:
    print(f"- {skill.name} v{skill.version}: {skill.description}")
```

### 3. 注册技能

```python
from agentbus.skills import SkillRegistry

registry = manager.registry

# 注册技能
await registry.register_skill(metadata, MySkillFactory)

# 检查注册状态
registered_skills = registry.get_registered_skills()
print(f"已注册 {len(registered_skills)} 个技能")
```

### 4. 加载和激活技能

```python
# 加载单个技能
skill_instance = await manager.load_skill(metadata)

# 激活技能
success = await manager.activate_skill(skill_instance.name)

# 批量加载所有启用的技能
load_results = await manager.load_all_skills()

# 批量激活自动激活的技能
activate_results = await manager.activate_auto_skills()
```

### 5. 执行技能操作

```python
# 执行技能操作
result = await manager.execute_skill(
    skill_name="my_skill",
    action="process_data",
    params={"input": "hello world", "mode": "uppercase"}
)

print(f"执行结果: {result}")
```

### 6. 管理技能状态

```python
# 获取技能状态
status = manager.get_skill_status("my_skill")
print(f"技能状态: {status.value}")

# 列出所有技能
all_skills = manager.list_skills()
active_skills = manager.list_skills({SkillStatus.ACTIVE})

# 获取技能详细信息
skill_info = manager.get_skill_info("my_skill")
print(f"技能信息: {skill_info}")
```

## 高级功能

### 1. 生命周期管理

```python
from agentbus.skills import SkillLifecycleManager, LifecycleConfig

# 创建生命周期配置
config = LifecycleConfig(
    health_check_interval=60,
    auto_restart_enabled=True,
    max_restart_attempts=3
)

# 创建生命周期管理器
lifecycle_manager = SkillLifecycleManager(manager, config)

# 启动生命周期管理
await lifecycle_manager.start()

# 获取生命周期信息
info = lifecycle_manager.get_lifecycle_info()
print(f"生命周期状态: {info}")
```

### 2. 健康检查和监控

```python
# 强制健康检查
health_status = await lifecycle_manager.force_health_check("my_skill")

# 获取所有技能的健康状态
all_health = lifecycle_manager.get_health_status()

# 获取技能指标
metrics = lifecycle_manager.get_skill_metrics("my_skill")
```

### 3. 技能依赖管理

技能系统自动处理依赖关系：

```python
# 在SkillMetadata中定义依赖
metadata = SkillMetadata(
    name="my_skill",
    description="需要其他技能的技能",
    dependencies=["dependency_skill"],
    conflicts=["conflicting_skill"]
)

# 系统会自动检查和加载依赖
```

### 4. 配置文件支持

技能配置文件支持YAML和JSON格式：

```yaml
# skills/my_skill.yaml
---
name: my_skill
description: 我的技能
version: 1.0.0
category: utility
enabled: true
dependencies: []
config_schema:
  api_key:
    type: string
    required: true
---

# 技能文档...
```

## 技能开发最佳实践

### 1. 异步编程

所有技能方法都应该是异步的：

```python
import asyncio
from agentbus.skills import BaseSkill

class AsyncSkill(BaseSkill):
    async def execute(self, action: str, params: dict) -> Any:
        if action == "long_operation":
            # 使用asyncio进行并发操作
            results = await asyncio.gather(
                self.task1(),
                self.task2(),
                self.task3()
            )
            return results
```

### 2. 错误处理

实现完善的错误处理：

```python
from agentbus.skills import SkillExecutionError

async def execute(self, action: str, params: dict) -> Any:
    try:
        if action == "risky_operation":
            result = await self.risky_operation(params)
            return result
    except ValueError as e:
        # 参数错误
        raise SkillExecutionError(f"Invalid parameters: {e}")
    except Exception as e:
        # 其他错误
        self.logger.error(f"Operation failed: {e}")
        raise SkillExecutionError(f"Operation failed: {e}")
```

### 3. 日志记录

使用适当的日志记录：

```python
import logging

class MySkill(BaseSkill):
    def __init__(self, metadata: SkillMetadata):
        super().__init__(metadata)
        self.logger = logging.getLogger(f"skill.{metadata.name}")
    
    async def execute(self, action: str, params: dict) -> Any:
        self.logger.info(f"Executing {action} with params: {params}")
        try:
            result = await self._do_work(params)
            self.logger.info(f"Operation {action} completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"Operation {action} failed: {e}")
            raise
```

### 4. 配置管理

从上下文中读取配置：

```python
async def initialize(self, context: SkillContext) -> None:
    self.context = context
    
    # 读取配置
    self.api_key = context.get_config("api_key")
    self.timeout = context.get_config("timeout", 30)
    
    # 读取环境变量
    self.env_var = context.get_env("MY_ENV_VAR")
    
    # 创建工作目录
    self.work_dir = context.get_path("data")
    self.work_dir.mkdir(parents=True, exist_ok=True)
```

## 技能配置文件格式

技能使用YAML或JSON格式的配置文件，支持以下字段：

```yaml
---
name: skill_name
description: 技能描述
version: 1.0.0
author: 作者
homepage: https://example.com
license: MIT
tags: [tag1, tag2]
category: tool|command|integration|utility|workflow
enabled: true|false
auto_activate: true|false
priority: 0

requires:
  python_version: ">=3.8"
  packages:
    - package1
    - package2

dependencies:
  - other_skill1
  - other_skill2

conflicts:
  - conflicting_skill1

permissions:
  - permission1
  - permission2

config_schema:
  param1:
    type: string|integer|boolean
    required: true|false
    default: default_value
    description: 参数描述

install_info:
  pip_packages:
    - package>=version
  system_requirements:
    - system_tool
  environment_setup:
    - name: ENV_VAR
      description: 环境变量描述
      required: true|false
---

# 技能详细文档...
```

## 故障排除

### 常见问题

1. **技能加载失败**
   - 检查配置文件格式是否正确
   - 验证依赖是否已安装
   - 查看日志获取详细错误信息

2. **技能激活失败**
   - 检查依赖技能是否已激活
   - 验证权限配置
   - 确认配置文件正确

3. **执行错误**
   - 检查参数格式和类型
   - 验证网络连接和API访问
   - 查看技能内部日志

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查技能状态
status = manager.get_skill_status("my_skill")
print(f"Skill status: {status}")

# 获取技能信息
info = manager.get_skill_info("my_skill")
print(f"Skill info: {info}")

# 检查注册表
registry_info = manager.export_registry()
print(f"Registry info: {registry_info}")
```

## 扩展和定制

### 自定义技能类型

```python
from agentbus.skills import SkillType

# 添加自定义技能类型
class CustomSkillType(SkillType):
    CUSTOM = "custom"

# 在技能元数据中使用
metadata = SkillMetadata(
    name="custom_skill",
    category=CustomSkillType.CUSTOM
)
```

### 自定义生命周期配置

```python
from agentbus.skills import LifecycleConfig

config = LifecycleConfig(
    health_check_interval=30,
    auto_restart_enabled=True,
    max_restart_attempts=5,
    restart_delay=2.0,
    timeout_shutdown=60.0
)
```

## 总结

AgentBus技能系统提供了完整的技能生命周期管理框架，包括：

- **发现**: 自动发现和扫描技能
- **注册**: 验证和注册技能
- **加载**: 按需加载技能实例
- **管理**: 激活、停用、状态管理
- **执行**: 统一的执行接口
- **监控**: 健康检查、指标收集、自动重启
- **扩展**: 灵活的扩展和定制机制

通过遵循本指南，您可以快速开发和部署高质量的AgentBus技能。