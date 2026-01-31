# AgentBus技能系统框架

基于Moltbot的SKILL.md概念实现的AgentBus技能系统框架，提供完整的技能发现、加载、管理和生命周期控制功能。

## 🚀 特性

- **技能发现**: 自动扫描和发现技能文件
- **技能注册**: 验证和注册技能到系统
- **生命周期管理**: 完整的技能加载、激活、停用、卸载流程
- **依赖管理**: 自动处理技能间的依赖和冲突关系
- **健康监控**: 内置健康检查、指标收集和自动重启机制
- **配置管理**: 灵活的配置架构和验证机制
- **工厂模式**: 统一的技能创建和管理接口
- **异步支持**: 完整的异步编程模型

## 📦 组件架构

```
agentbus/skills/
├── __init__.py              # 模块初始化和公共接口
├── base.py                  # 技能基类和接口定义
├── registry.py              # 技能注册和管理系统
├── manager.py               # 技能生命周期管理器
├── examples/                # 示例技能配置
│   └── example_utility_skill.yaml
├── AGENTBUS_SKILLS_GUIDE.md # 完整使用指南
└── test_skills_system.py   # 测试示例
```

## 🛠️ 核心组件

### 1. BaseSkill - 技能基类
所有技能必须继承的抽象基类，定义了技能的核心接口：

```python
from agentbus.skills import BaseSkill, SkillMetadata, SkillContext

class MySkill(BaseSkill):
    async def initialize(self, context: SkillContext) -> None:
        # 初始化技能
        
    async def activate(self) -> None:
        # 激活技能
        
    async def execute(self, action: str, params: dict) -> Any:
        # 执行技能操作
```

### 2. SkillManager - 技能管理器
提供技能的全生命周期管理：

```python
from agentbus.skills import SkillManager
from pathlib import Path

manager = SkillManager(
    workspace_dir=Path("/path/to/workspace"),
    config_dir=Path("/path/to/config")
)

# 发现技能
skills = await manager.discover_skills([Path("/skills/dir")])

# 加载和激活技能
for metadata in skills:
    await manager.load_skill(metadata)
    await manager.activate_skill(metadata.name)

# 执行技能
result = await manager.execute_skill("skill_name", "action", params)
```

### 3. SkillLifecycleManager - 生命周期管理器
提供监控、健康检查和自动重启功能：

```python
from agentbus.skills import SkillLifecycleManager, LifecycleConfig

config = LifecycleConfig(
    health_check_interval=60,
    auto_restart_enabled=True,
    max_restart_attempts=3
)

lifecycle_manager = SkillLifecycleManager(manager, config)
await lifecycle_manager.start()
```

## 📝 技能配置格式

技能使用YAML或JSON格式的配置文件：

```yaml
---
name: my_skill
description: 我的自定义技能
version: 1.0.0
author: 作者姓名
category: utility  # tool|command|integration|utility|workflow
enabled: true
auto_activate: true

# 依赖管理
dependencies:
  - other_skill

# 配置架构
config_schema:
  api_key:
    type: string
    required: true
    description: API密钥

# 安装信息
install_info:
  pip_packages:
    - requests>=2.25.0
---

# 技能详细文档
这里可以包含技能的详细说明、使用示例等。
```

## 🔧 快速开始

### 1. 安装依赖

```bash
pip install pyyaml pydantic
```

### 2. 创建技能

```python
from agentbus.skills import BaseSkill, SkillMetadata, SkillFactory

class HelloSkill(BaseSkill):
    async def execute(self, action: str, params: dict) -> str:
        if action == "hello":
            name = params.get("name", "World")
            return f"Hello, {name}!"
        return "Unknown action"

class HelloSkillFactory(SkillFactory):
    @staticmethod
    def create_skill(metadata: SkillMetadata) -> BaseSkill:
        return HelloSkill(metadata)
```

### 3. 注册和使用

```python
from agentbus.skills import SkillManager, SkillMetadata, SkillType

# 创建技能管理器
manager = SkillManager(workspace_dir="./workspace", config_dir="./config")

# 创建技能元数据
metadata = SkillMetadata(
    name="hello_skill",
    description="打招呼技能",
    category=SkillType.UTILITY
)

# 注册技能
await manager.registry.register_skill(metadata, HelloSkillFactory)

# 加载和激活
await manager.load_skill(metadata)
await manager.activate_skill("hello_skill")

# 执行技能
result = await manager.execute_skill("hello_skill", "hello", {"name": "AgentBus"})
print(result)  # Hello, AgentBus!
```

## 🧪 运行测试

```bash
cd /workspace/agentbus/skills
python test_skills_system.py
```

测试包括：
- 技能管理器基本功能
- 技能发现和注册
- 生命周期管理
- 示例技能执行
- 错误处理

## 📖 详细文档

- [完整使用指南](AGENTBUS_SKILLS_GUIDE.md) - 详细的使用说明和最佳实践
- [技能配置文件](examples/example_utility_skill.yaml) - 完整的配置示例

## 🏗️ 基于Moltbot概念

本框架基于Moltbot的SKILL.md概念设计，保持了以下核心思想：

1. **技能文档化**: 每个技能都有详细的markdown文档
2. **元数据驱动**: 通过frontmatter定义技能配置
3. **依赖管理**: 明确声明依赖和冲突关系
4. **安装自动化**: 支持自动安装依赖和系统要求
5. **分类系统**: 技能按类型分类管理
6. **权限控制**: 细粒度的权限控制机制

## 🔄 生命周期状态

技能支持完整的状态管理：

- `UNLOADED`: 未加载
- `LOADING`: 加载中
- `ACTIVE`: 已激活
- `INACTIVE`: 未激活
- `ERROR`: 错误状态
- `DISABLED`: 已禁用

## 📊 监控和健康检查

内置监控功能：

- **健康状态**: HEALTHY, WARNING, CRITICAL, UNKNOWN
- **性能指标**: 执行次数、错误率、响应时间
- **资源监控**: 内存使用、CPU使用
- **自动重启**: 错误恢复机制

## 🛡️ 安全特性

- **权限验证**: 技能执行前的权限检查
- **依赖隔离**: 技能间依赖关系的安全处理
- **配置验证**: 严格的配置参数验证
- **错误处理**: 完善的异常处理机制

## 🔌 扩展能力

框架提供丰富的扩展点：

- **自定义技能类型**: 支持扩展技能分类
- **自定义工厂**: 灵活的技能创建机制
- **事件钩子**: 生命周期事件回调
- **配置扩展**: 自定义配置架构

## 📈 性能优化

- **懒加载**: 技能按需加载
- **异步执行**: 完整的异步编程支持
- **资源管理**: 自动资源清理和回收
- **缓存机制**: 配置和元数据缓存

## 🤝 贡献指南

欢迎贡献代码和建议！请遵循以下步骤：

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 📄 许可证

MIT License - 详见LICENSE文件

## 🆘 支持

如有问题或建议，请：

1. 查看[使用指南](AGENTBUS_SKILLS_GUIDE.md)
2. 运行测试文件调试
3. 创建Issue描述问题

---

**AgentBus技能系统** - 让技能开发更简单、更高效！