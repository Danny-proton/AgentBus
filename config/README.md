---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 304502201e3e28de43249b90b72cbaab13898bd6e4bf33cf047e9b6e40b3452447e34a33022100faf813292c0048d4b9eeab40d2c434d118cfc83f7bb2da4f9251423b3e006d0e
    ReservedCode2: 30450221008c2fe9fae3d3858752bfe3f1f4ac34a19761092ad5021cbf5cbc390c053203ee0220651874b11cb9cf64fed5864f5270a1d1248172bfbe56f0917b94956256069777
---

# AgentBus 配置管理系统

基于 Moltbot 配置系统设计的 AgentBus 配置管理解决方案。

## 功能特性

- ✅ **多环境支持**: 开发、测试、生产环境配置
- ✅ **配置验证**: 基于 Pydantic 的类型安全验证
- ✅ **配置合并**: 多源配置智能合并与优先级管理
- ✅ **加密存储**: 敏感配置信息加密保护
- ✅ **热重载**: 配置变更实时重载（框架已就绪）
- ✅ **环境变量**: 灵活的环境变量覆盖机制
- ✅ **配置文件**: TOML 格式的配置管理

## 目录结构

```
agentbus/config/
├── __init__.py              # 模块初始化与导出
├── types.py                 # Pydantic 配置模型定义
├── settings.py              # 主配置类与验证
├── config_manager.py        # 配置管理器核心
├── profile_manager.py       # 配置文件管理
├── env_loader.py           # 环境变量加载器
├── security.py             # 配置加密/解密
├── base.toml               # 基础配置文件
├── development.toml        # 开发环境配置
├── production.toml         # 生产环境配置
└── example_usage.py        # 使用示例代码
```

## 快速开始

### 1. 基本使用

```python
from agentbus.config import get_settings

# 获取默认配置
settings = get_settings()
print(f"应用名称: {settings.app.name}")
print(f"调试模式: {settings.app.debug}")
```

### 2. 环境特定配置

```python
import os
from agentbus.config import ConfigManager

# 设置环境变量
os.environ["APP_ENV"] = "development"

# 加载特定环境配置
config_manager = ConfigManager()
settings = await config_manager.load_config()
```

### 3. 配置验证

所有配置都经过 Pydantic 验证，确保类型安全和数据完整性：

```python
from agentbus.config import get_settings

try:
    settings = get_settings()
    # 配置验证通过，可以安全使用
    host = settings.app.host
    port = settings.app.port
except Exception as e:
    print(f"配置验证失败: {e}")
```

### 4. 敏感数据加密

```python
from agentbus.config import SecurityManager

security = SecurityManager()

# 加密敏感数据
encrypted = await security.encrypt_value("secret_password")

# 解密数据
decrypted = await security.decrypt_value(encrypted)
```

## 配置层级

配置按以下优先级合并（从低到高）：

1. **代码默认值**: Pydantic 模型中的默认字段值
2. **基础配置**: `base.toml` 文件
3. **环境配置**: `{APP_ENV}.toml` 文件（如 `development.toml`）
4. **环境变量**: `AGENTBUS_*` 前缀的环境变量

## 环境变量覆盖

可以使用环境变量覆盖任何配置项：

```bash
# 覆盖应用配置
export AGENTBUS_APP_DEBUG=true
export AGENTBUS_DATABASE_URL="postgresql://..."

# 覆盖日志配置
export AGENTBUS_LOGGING_LEVEL=DEBUG
```

## 文件格式

配置文件使用 TOML 格式：

```toml
[app]
name = "AgentBus"
debug = false
host = "localhost"
port = 8000

[logging]
level = "INFO"
format = "json"
file_path = "logs/agentbus.log"

[database]
url = "sqlite:///./data/agentbus.db"
pool_size = 5
```

## 扩展配置模型

要添加新的配置项，修改 `types.py` 中的 Pydantic 模型：

```python
from pydantic import BaseModel, Field
from typing import Optional

class NewFeatureConfig(BaseModel):
    enabled: bool = False
    api_key: Optional[str] = None
    timeout_seconds: int = 30

class Settings(BaseSettings):
    # 现有配置...
    new_feature: NewFeatureConfig = Field(default_factory=NewFeatureConfig)
```

## 安全注意事项

- 敏感配置（如密码、API 密钥）应使用 `SecurityManager` 加密存储
- 生产环境中应设置 `APP_ENV=production`
- 定期轮换加密密钥
- 避免在代码中硬编码敏感信息

## 热重载

配置系统支持热重载功能：

```python
from agentbus.config import ConfigManager

config_manager = ConfigManager()

# 监听配置变化并重载
await config_manager.reload_config()
```

## 故障排除

### 常见问题

1. **配置验证失败**
   - 检查配置文件语法
   - 确认必填字段已提供
   - 验证数据类型正确

2. **环境变量不生效**
   - 确认变量名前缀为 `AGENTBUS_`
   - 检查环境变量是否正确设置
   - 验证变量名与配置字段匹配

3. **配置文件找不到**
   - 确认配置文件存在于正确路径
   - 检查文件权限
   - 验证 APP_ENV 环境变量设置

### 调试技巧

```python
import logging
from agentbus.config import get_settings

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)

# 获取当前配置详情
settings = get_settings()
print(settings.model_dump_json(indent=2))
```

## 性能优化

- 配置在应用启动时一次性加载并缓存
- 环境变量变化时仅重新验证相关配置段
- 加密操作使用内存缓存减少重复计算

## 贡献指南

添加新配置功能时：

1. 在 `types.py` 中定义新的 Pydantic 模型
2. 更新 `settings.py` 中的主配置类
3. 创建对应的配置文件模板
4. 添加使用示例到 `example_usage.py`
5. 更新此 README 文档

## 许可证

本配置管理系统遵循 AgentBus 项目的开源许可证。