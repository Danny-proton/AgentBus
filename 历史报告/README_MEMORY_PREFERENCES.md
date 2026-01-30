---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 30450221008b06542ce339e73fdadcccfb1fdb7a564ebc767e6a8debf0dbb39ff7a7f30eb802201853a0467aa90d46dd6f606835c91d0ef5964e3e27f8429f1176f0e8458652d0
    ReservedCode2: 3046022100a6f069dfbe93d5affa1c18ff9011ccdac8ceb01e5c1fabcc7608b40f193abad40221009e87ffa7e381dbe7ac4cb2c5edeb3d249cc4ed1951c472b2a8fdc53e82b49e55
---

# AgentBus 用户记忆和偏好系统

## 概述

AgentBus 用户记忆和偏好系统是一个全面的用户数据管理解决方案，提供了智能的记忆存储、对话历史管理、上下文缓存以及全面的用户偏好配置功能。

## 系统架构

### 核心模块

#### 记忆管理模块 (`agentbus/memory/`)
- **`user_memory.py`** - 长期用户记忆存储和管理
  - 支持多种记忆类型：个人信息、偏好、兴趣、学习内容
  - 智能标签系统和优先级管理
  - 自动持久化和清理机制
  - 记忆搜索和匹配功能

- **`conversation_history.py`** - 对话历史管理
  - 完整的会话记录和上下文维护
  - 智能对话摘要和压缩
  - Token限制管理和优化
  - 对话状态跟踪和恢复

- **`context_cache.py`** - 上下文缓存系统
  - 多级缓存架构（L1内存 + L2磁盘）
  - 智能淘汰策略（LRU、FIFO、优先级）
  - 动态TTL和自动清理
  - 上下文窗口优化构建

#### 偏好管理模块 (`agentbus/preferences/`)
- **`user_preferences.py`** - 用户通用偏好设置
  - 界面和行为定制
  - 隐私和安全设置
  - 通知和通信配置
  - 偏好验证和默认值

- **`skill_preferences.py`** - 技能偏好管理
  - 技能启用/禁用配置
  - 技能优先级和触发条件
  - 技能特定参数设置
  - 技能性能监控

- **`channel_preferences.py`** - 渠道偏好管理
  - 多渠道通知配置
  - 消息格式和样式设置
  - 通知级别和频率控制
  - 渠道特定行为定制

#### 统一管理模块 (`agentbus/manager.py`)
- **`AgentBusManager`** - 统一管理接口
  - 单一入口点访问所有功能
  - 统一的错误处理和日志记录
  - 跨模块数据同步和一致性
  - 性能监控和系统统计

## 主要功能

### 1. 智能记忆管理
- **长期存储**：持久化用户重要信息和偏好
- **分类管理**：按类型和标签组织记忆内容
- **智能检索**：基于语义和关键词的高效搜索
- **自动清理**：过期和无效记忆的自动清理

### 2. 对话上下文优化
- **历史记录**：完整的对话历史保存和检索
- **上下文压缩**：智能摘要减少token使用
- **会话恢复**：跨会话的上下文连续性
- **状态管理**：对话状态和用户情绪跟踪

### 3. 多级缓存系统
- **内存缓存**：高频访问数据的快速访问
- **磁盘缓存**：大量数据的持久化存储
- **智能淘汰**：基于使用频率的自动缓存清理
- **TTL管理**：数据过期时间的动态管理

### 4. 灵活偏好配置
- **分类管理**：按功能模块组织偏好设置
- **验证机制**：偏好值的自动验证和默认值
- **继承机制**：全局和特定偏好的层级管理
- **动态更新**：实时偏好变更和应用

### 5. 技能和渠道定制
- **技能管理**：智能技能启用、配置和优先级
- **渠道集成**：多平台通知和行为定制
- **个性化体验**：基于用户偏好的个性化响应
- **性能优化**：智能资源分配和负载均衡

## 使用方法

### 快速开始

```python
import asyncio
from agentbus.manager import AgentBusManager

async def example():
    # 初始化管理器
    manager = AgentBusManager(
        storage_base_path="data",
        memory_config={"max_memory_items": 10000},
        preferences_config={"auto_backup": True}
    )
    
    # 添加用户记忆
    await manager.add_memory(
        user_id="user123",
        content="用户喜欢喝咖啡",
        memory_type="preferences",
        tags=["咖啡", "饮料"],
        priority="high"
    )
    
    # 配置用户偏好
    await manager.set_user_preference(
        user_id="user123",
        category="general",
        key="language",
        value="zh-CN"
    )
    
    # 启用技能
    await manager.set_skill_preference(
        user_id="user123",
        skill_name="coffee_reminder",
        enabled=True,
        priority="medium"
    )

asyncio.run(example())
```

### 完整示例

查看 `example_memory_preferences.py` 文件获取完整的使用示例，包括：
- 用户记忆的增删改查
- 对话历史管理
- 上下文缓存操作
- 用户偏好配置
- 技能和渠道管理
- 系统统计信息

## 配置选项

### 记忆系统配置
```python
memory_config = {
    "max_memory_items": 10000,      # 最大记忆条目数
    "cache_size_mb": 100,           # 缓存大小限制(MB)
    "auto_cleanup": True,           # 自动清理开关
    "cleanup_interval_hours": 24,  # 清理间隔(小时)
    "default_ttl_hours": 168       # 默认TTL(小时)
}
```

### 偏好系统配置
```python
preferences_config = {
    "auto_backup": True,            # 自动备份开关
    "backup_interval_hours": 24,   # 备份间隔(小时)
    "max_backup_files": 10,        # 最大备份文件数
    "validation_strict": True      # 严格验证模式
}
```

## 数据存储

系统支持多种存储后端：
- **SQLite**：轻量级本地数据库（默认）
- **JSON文件**：简单的文件存储
- **PostgreSQL**：生产级关系数据库（可选）
- **Redis**：高性能缓存存储（可选）

## 性能特性

- **异步操作**：所有I/O操作支持异步执行
- **批量处理**：支持批量数据操作提升性能
- **连接池**：数据库连接复用和优化
- **监控指标**：内置性能监控和统计
- **内存优化**：智能内存管理和垃圾回收

## 扩展性

系统设计为高度可扩展：
- **插件架构**：支持自定义记忆和偏好处理器
- **存储适配器**：可插拔的存储后端
- **事件系统**：基于事件的模块间通信
- **配置驱动**：完全基于配置的行为定制

## 最佳实践

1. **记忆管理**
   - 定期清理过期记忆
   - 使用适当的优先级和标签
   - 避免重复和冗余信息

2. **缓存优化**
   - 合理设置TTL值
   - 监控缓存命中率
   - 及时清理无用缓存

3. **偏好配置**
   - 提供合理的默认值
   - 实现偏好验证机制
   - 保持配置的一致性

4. **性能优化**
   - 使用批量操作
   - 适当使用索引
   - 监控内存使用

## 故障排除

### 常见问题

1. **记忆丢失**
   - 检查存储路径权限
   - 验证数据序列化
   - 查看错误日志

2. **缓存不生效**
   - 确认缓存TTL设置
   - 检查缓存键名一致性
   - 验证存储空间

3. **偏好设置无效**
   - 验证偏好值格式
   - 检查权限设置
   - 确认数据同步

### 日志调试

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看详细操作日志
logger = logging.getLogger('agentbus.memory')
logger.setLevel(logging.DEBUG)
```

## 版本兼容性

- **Python**: 3.8+
- **异步支持**: asyncio
- **依赖库**: dataclasses, pathlib, hashlib
- **可选依赖**: sqlite3 (内置), redis, psycopg2

## 更新日志

### v1.0.0 (当前版本)
- 完整的用户记忆管理系统
- 对话历史和上下文缓存
- 全面的用户偏好配置
- 统一的管理接口
- 异步操作支持
- 多存储后端支持