# AgentBus 会话管理系统

AgentBus 会话管理系统为 AgentBus 提供了完整的会话管理功能，包括会话创建、保存、恢复、清理等核心功能，支持多用户会话和并发管理，实现了会话过期和自动清理机制。

## 🆕 新增功能特性

### 🚀 完整会话管理系统
- **统一接口**: 整合所有会话管理功能的统一系统
- **模块化设计**: 支持按需启用不同功能模块
- **配置管理**: 灵活的配置系统和预设配置
- **健康监控**: 完整的系统健康检查和状态监控

### 🔄 会话同步系统
- **跨通道同步**: 支持多平台、多通道的会话关联和同步
- **身份映射**: 智能的用户身份识别和映射
- **冲突解决**: 多种会话冲突解决策略
- **自动同步**: 支持手动、自动、延迟和批量同步

### 💾 会话持久化
- **多格式备份**: 支持JSON、压缩JSON、Pickle等多种格式
- **自动备份**: 可配置的自动备份机制
- **增量备份**: 智能的增量备份和恢复
- **完整性验证**: 备份文件的校验和完整性检查

### 📊 会话状态跟踪
- **状态机**: 可配置的状态转换规则
- **事件跟踪**: 全面的会话事件记录和分析
- **模式分析**: 自动识别使用模式和趋势
- **预测功能**: 智能的生命周期预测

### ⏰ 会话过期管理
- **多策略过期**: 时间、活动、使用量、混合等多种过期策略
- **智能清理**: 可配置的清理操作和通知机制
- **渐进式过期**: 基于优先级的渐进式过期处理
- **归档功能**: 自动归档和恢复功能

## 🎯 核心功能

### 💼 基础功能
- **会话生命周期管理**: 创建、保存、恢复、删除会话
- **多用户支持**: 支持多用户会话和并发管理
- **自动清理**: 会话过期和自动清理机制
- **消息历史**: 完整的对话历史记录和管理
- **父子会话**: 支持会话的层级关系管理

### 💾 存储支持
- **内存存储**: 快速访问，适合开发和测试
- **文件存储**: 基于文件系统的持久化存储
- **数据库存储**: SQLite数据库存储，支持复杂查询
- **可扩展**: 易于添加新的存储后端

### 🛠 管理工具
- **上下文管理器**: 高效的上下文缓存和管理
- **会话装饰器**: 便捷的会话上下文管理器
- **健康检查**: 系统状态监控和诊断
- **统计信息**: 详细的会话统计和分析

## 📁 文件结构

```
agentbus/sessions/
├── __init__.py                    # 模块初始化和公共接口
├── session_manager.py            # 会话管理器核心实现
├── session_storage.py            # 会话存储抽象和实现
├── context_manager.py            # 上下文管理器
├── test_sessions.py            # 功能测试脚本
├── README.md                   # 使用文档

# 🆕 新增扩展模块
├── session_sync.py              # 跨通道会话同步
├── session_persistence.py      # 会话持久化和恢复
├── session_state_tracker.py     # 会话状态跟踪
├── session_expiry.py           # 会话过期处理
├── session_system.py          # 完整会话管理系统
└── demo_complete_system.py    # 完整系统演示脚本
```

## 🚀 快速开始

### 基础使用

```python
import asyncio
from agentbus.sessions import (
    initialize_sessions, create_session, get_session, add_message,
    Platform, SessionType, Message, MessageType
)

async def main():
    # 1. 初始化会话管理系统
    system = await initialize_sessions()
    
    # 2. 创建会话
    session = await create_session(
        chat_id="chat_123",
        user_id="user_456", 
        platform=Platform.TELEGRAM,
        session_type=SessionType.PRIVATE
    )
    
    # 3. 添加消息
    message = Message(
        id="msg_001",
        content="你好！这是一条测试消息",
        user_id="user_456",
        timestamp=datetime.now(),
        message_type=MessageType.TEXT,
        platform=Platform.TELEGRAM,
        chat_id="chat_123"
    )
    
    await add_message(session.session_id, message)
    
    # 4. 获取会话
    retrieved_session = await get_session(session.session_id)
    print(f"会话包含 {len(retrieved_session.conversation_history)} 条消息")

asyncio.run(main())
```

### 🆕 完整会话管理系统

```python
import asyncio
from agentbus.sessions import (
    initialize_sessions, 
    get_development_config,
    EventType,
    default_notification_callback
)

async def main():
    # 1. 创建开发环境配置
    config = get_development_config()
    config.update({
        "enable_sync": True,           # 启用会话同步
        "enable_persistence": True,    # 启用持久化
        "enable_tracking": True,       # 启用状态跟踪
        "enable_expiry": True,         # 启用过期管理
    })
    
    # 2. 初始化完整会话系统
    system = await initialize_sessions(
        storage_type="DATABASE",
        storage_config={"db_path": "./agentbus.db"},
        enable_all_features=True,
        **config.__dict__
    )
    
    try:
        # 3. 创建会话
        session = await system.create_session(
            chat_id="chat_123",
            user_id="user_456",
            platform=Platform.TELEGRAM,
            session_type=SessionType.PRIVATE,
            ai_model="gpt-3.5-turbo"
        )
        
        # 4. 跟踪事件
        await system.track_event(
            session.session_id,
            EventType.MESSAGE_RECEIVED,
            content="你好！这是一条测试消息",
            user_id="user_456"
        )
        
        # 5. 创建备份
        backup_id = await system.create_backup(
            description="重要备份",
            tags=["important", "test"]
        )
        
        # 6. 获取系统状态
        status = await system.get_system_status()
        print(f"系统状态: {status['system']['status']}")
        print(f"活跃会话: {status['metrics']['active_sessions']}")
        
    finally:
        await system.stop()

asyncio.run(main())
```

### 生产环境配置

```python
import asyncio
from pathlib import Path
from agentbus.sessions import (
    initialize_sessions,
    get_production_config,
    create_email_notification_callback,
    ExpiryRule,
    ExpiryStrategy,
    CleanupAction
)

async def main():
    # 1. 创建生产环境配置
    config = get_production_config(
        storage_config={"db_path": "/var/lib/agentbus/sessions.db"},
        backup_dir=Path("/var/backups/agentbus"),
        archive_dir=Path("/var/archive/agentbus")
    )
    
    # 2. 添加自定义过期规则
    expiry_rule = ExpiryRule(
        rule_id="production_archive",
        name="生产环境归档规则",
        strategy=ExpiryStrategy.TIME_BASED,
        conditions={"default_hours": 24},
        actions=[CleanupAction.ARCHIVE],
        priority=1
    )
    
    # 3. 添加通知回调
    email_callback = create_email_notification_callback({
        "smtp_server": "smtp.company.com",
        "recipients": ["admin@company.com"]
    })
    
    config.notification_callbacks = [email_callback]
    
    # 4. 初始化系统
    system = await initialize_sessions(**config.__dict__)
    
    try:
        # 5. 业务逻辑...
        pass
    finally:
        await system.stop()

asyncio.run(main())
```

### 使用不同存储类型

```python
# 内存存储（默认）
manager = await initialize_sessions()

# 文件存储
manager = await initialize_sessions(
    storage_type=StorageType.FILE,
    storage_config={"storage_dir": "./sessions_data"}
)

# 数据库存储
manager = await initialize_sessions(
    storage_type=StorageType.DATABASE,
    storage_config={"db_path": "./agentbus_sessions.db"}
)
```

### 使用会话上下文管理器

```python
from agentbus.sessions import session_context, get_session_manager

async def handle_user_message():
    manager = get_session_manager()
    
    async with session_context(
        manager,
        chat_id="chat_123",
        user_id="user_456",
        platform=Platform.TELEGRAM
    ) as session:
        # 在这个上下文中，会话会被自动创建或获取
        print(f"处理会话: {session.session_id}")
        
        # 添加一些数据到会话
        session.set_data("user_preferences", {"theme": "dark"})
        
        # 你的业务逻辑...
        
        return session.session_id
```

## 🔧 API 参考

### 核心类

#### SessionContext
会话上下文类，包含会话的所有信息。

```python
# 属性
session_id: str              # 会话唯一标识
chat_id: str                 # 聊天ID
user_id: str                 # 用户ID
platform: Platform          # 平台类型
session_type: SessionType    # 会话类型
created_at: datetime         # 创建时间
last_activity: datetime      # 最后活动时间
data: Dict[str, Any]         # 会话数据
metadata: Dict[str, Any]     # 会话元数据
conversation_history: List   # 对话历史

# 方法
add_message(message)         # 添加消息
set_data(key, value)         # 设置数据
get_data(key, default)       # 获取数据
is_expired()                 # 检查是否过期
is_active()                  # 检查是否活跃
```

#### SessionManager
会话管理器，负责会话的完整生命周期管理。

```python
# 创建会话
create_session(chat_id, user_id, platform, session_type, **kwargs)

# 获取会话
get_session(session_id)
get_user_session(user_id, chat_id, platform)
get_user_sessions(user_id)

# 更新会话
update_session(context)
add_message_to_session(session_id, message)

# 删除会话
delete_session(session_id)

# 生命周期管理
extend_session_lifetime(session_id, seconds)
reset_session_history(session_id, keep_recent)
cleanup_all_expired()
```

### 🆕 完整会话管理系统

#### SessionSystem
统一会话管理系统，整合所有功能模块。

```python
# 系统管理
await system.start()                    # 启动系统
await system.stop()                     # 停止系统
await system.restart()                  # 重启系统

# 会话操作
await system.get_session(session_id)   # 获取会话
await system.create_session(**kwargs)   # 创建会话
await system.delete_session(session_id) # 删除会话

# 事件跟踪
await system.track_event(session_id, EventType.MESSAGE_RECEIVED, **data)

# 同步操作
await system.sync_sessions(source_session_id)

# 备份恢复
await system.create_backup(description="备份说明", **options)
await system.restore_backup(backup_id, **options)

# 清理操作
await system.cleanup_expired_sessions(dry_run=False)

# 系统监控
await system.get_system_status()       # 获取系统状态
await system.get_health_check()        # 健康检查
```

#### 配置管理

```python
# 获取开发环境配置
config = get_development_config()

# 获取生产环境配置
config = get_production_config(
    storage_config={"db_path": "./prod.db"},
    backup_dir=Path("./backups"),
    archive_dir=Path("./archive")
)

# 自定义配置
config = SessionSystemConfig(
    storage_type=StorageType.DATABASE,
    enable_sync=True,
    enable_persistence=True,
    enable_tracking=True,
    enable_expiry=True,
    backup_dir=Path("./backups"),
    archive_dir=Path("./archive")
)
```

### 🔄 会话同步系统

#### SessionSynchronizer
跨通道会话同步管理器。

```python
# 创建同步器
synchronizer = await create_session_sync(session_store, sync_config)

# 身份映射
await synchronizer.link_identities(
    identity_key="user_123",
    session_ids=["session_1", "session_2"],
    display_name="张三"
)

# 同步会话
await synchronizer.sync_sessions(source_session_id)

# 冲突解决
await synchronizer.resolve_session_conflicts(session_ids, "latest_wins")
```

### 💾 会话持久化

#### SessionPersistence
会话数据持久化管理器。

```python
# 创建持久化管理器
persistence = await create_session_persistence(session_store, backup_dir)

# 备份操作
backup_id = await persistence.create_backup(
    format=BackupFormat.JSON_GZ,
    description="重要数据备份",
    tags=["important", "daily"]
)

# 恢复操作
result = await persistence.restore_backup(
    backup_id,
    options=RecoveryOptions(
        strategy=RecoveryStrategy.MERGE,
        preserve_metadata=True
    )
)

# 导出导入
export_path = await persistence.export_session(session_id, BackupFormat.JSON)
await persistence.import_session(export_path)
```

### 📊 会话状态跟踪

#### SessionStateTracker
会话状态跟踪和事件记录管理器。

```python
# 创建跟踪器
tracker = await create_session_state_tracker(session_store)

# 跟踪事件
await tracker.track_event(
    session_id,
    EventType.MESSAGE_RECEIVED,
    content="消息内容",
    user_id="user_123"
)

# 状态变更
await tracker.track_session_state_change(
    session_id,
    SessionStatus.IDLE,
    StateTransitionType.AUTOMATIC,
    "idle_detected"
)

# 获取统计
stats = await tracker.get_state_statistics(timedelta(days=7))
prediction = await tracker.predict_session_lifecycle(session_id)
```

### ⏰ 会话过期管理

#### SessionExpiryManager
会话过期检测和清理管理器。

```python
# 创建过期管理器
expiry_manager = await create_expiry_manager(
    session_store,
    archive_dir=Path("./archive")
)

# 添加过期规则
rule = ExpiryRule(
    rule_id="30d_archive",
    name="30天归档",
    strategy=ExpiryStrategy.TIME_BASED,
    conditions={"default_hours": 720},  # 30天
    actions=[CleanupAction.ARCHIVE],
    priority=1
)
await expiry_manager.add_expiry_rule(rule)

# 清理过期会话
results = await expiry_manager.cleanup_expired_sessions()

# 获取统计
stats = await expiry_manager.get_expiry_statistics()
```

### 存储接口

#### SessionStore
会话存储抽象接口。

```python
# 基本操作
create_session(context)
get_session(session_id)
update_session(context)
delete_session(session_id)

# 查询
find_sessions(**filters)
cleanup_expired()
get_session_count()
```

#### 存储实现
- `MemorySessionStore`: 内存存储
- `FileSessionStore`: 文件存储
- `DatabaseSessionStore`: 数据库存储

### 便利函数

```python
# 全局函数
create_session(**kwargs)      # 创建会话
get_session(session_id)       # 获取会话
add_message(session_id, msg)  # 添加消息

# 上下文管理
session_context(manager, chat_id, user_id, platform, **kwargs)

# 系统管理
initialize_sessions(**config)    # 初始化系统
shutdown_sessions()              # 关闭系统
health_check()                   # 健康检查
```

## 配置选项

### 初始化配置

```python
config = {
    "storage_type": StorageType.MEMORY,      # 存储类型
    "storage_config": {},                     # 存储配置
    "enable_cleanup": True,                   # 启用自动清理
    "cleanup_interval": 300,                  # 清理间隔（秒）
    "max_history_per_session": 50,           # 最大历史记录数
    "idle_timeout": 3600,                    # 空闲超时（秒）
}

manager = await initialize_sessions(**config)
```

### 会话配置

```python
# 创建会话时设置配置
session = await create_session(
    chat_id="chat_123",
    user_id="user_456",
    platform=Platform.TELEGRAM,
    
    # 会话元数据
    max_history=100,           # 最大历史记录数
    idle_timeout=7200,        # 空闲超时（2小时）
    expires_in=86400,          # 过期时间（1天）
    ai_model="gpt-3.5-turbo", # AI模型
    custom_data={}            # 自定义数据
)
```

## 最佳实践

### 1. 适当的存储选择

```python
# 开发/测试：使用内存存储
manager = await initialize_sessions(StorageType.MEMORY)

# 生产环境：使用数据库存储
manager = await initialize_sessions(
    storage_type=StorageType.DATABASE,
    storage_config={"db_path": "/var/lib/agentbus/sessions.db"}
)
```

### 2. 会话生命周期管理

```python
# 自动清理
manager = await initialize_sessions(enable_cleanup=True)

# 手动清理
await manager.cleanup_all_expired()

# 批量清理旧会话
await manager.batch_cleanup(older_than_days=30)
```

### 3. 错误处理

```python
async def safe_session_operation():
    try:
        session = await create_session(...)
        # 业务逻辑...
        return True
    except Exception as e:
        logger.error(f"会话操作失败: {e}")
        return False
```

### 4. 性能优化

```python
# 启用会话上下文装饰器
async with session_context(manager, ...) as session:
    # 在单个操作中处理多个相关任务
    messages = await process_messages(session)
    await update_session(session)  # 一次性更新

# 批量操作
for message in messages:
    await add_message(session_id, message)
```

## 🧪 测试

### 运行基础测试
```bash
cd agentbus/sessions
python test_sessions.py
```

### 🆕 运行完整系统演示
```bash
cd agentbus/sessions
python demo_complete_system.py
```

测试包括：
- ✅ 基本会话操作
- ✅ 不同存储类型
- ✅ 会话生命周期管理
- ✅ 上下文管理器
- ✅ 并发会话处理
- ✅ 🆕 会话同步功能
- ✅ 🆕 会话持久化
- ✅ 🆕 状态跟踪和分析
- ✅ 🆕 过期处理和清理
- ✅ 🆕 完整系统集成

### 性能测试

```python
import asyncio
from agentbus.sessions import create_default_session_system

async def performance_test():
    system = await create_default_session_system(
        storage_type="MEMORY",
        enable_all_features=True
    )
    
    # 创建100个会话
    start_time = datetime.now()
    sessions = []
    for i in range(100):
        session = await system.create_session(
            chat_id=f"perf_chat_{i}",
            user_id=f"perf_user_{i}",
            platform=Platform.TELEGRAM
        )
        sessions.append(session)
    
    creation_time = (datetime.now() - start_time).total_seconds()
    print(f"创建100个会话耗时: {creation_time:.2f}秒")
    
    await system.stop()

asyncio.run(performance_test())
```

## 📋 迁移指南

### 从旧版本迁移到完整系统

#### 1. 更新导入

```python
# 旧的导入方式
from agentbus.sessions import SessionManager, SessionContext

# 新的导入方式（向后兼容）
from agentbus.sessions import SessionManager, SessionContext

# 新功能导入
from agentbus.sessions import (
    SessionSystem,           # 完整系统
    initialize_sessions,     # 初始化函数
    get_development_config,  # 预设配置
)
```

#### 2```python
#. 更新初始化

 旧的初始化
manager = SessionManager()
await manager.start()

# 新的初始化（基础模式，向后兼容）
manager = await initialize_basic_sessions()

# 新的初始化（完整模式，推荐）
system = await initialize_sessions(
    storage_type=StorageType.DATABASE,
    storage_config={"db_path": "./agentbus.db"},
    enable_all_features=True
)
```

#### 3. 启用新功能

```python
# 逐步启用新功能
system = await initialize_sessions(
    storage_type=StorageType.DATABASE,
    enable_cleanup=True,
    enable_sync=True,           # 启用会话同步
    enable_persistence=True,    # 启用持久化
    enable_tracking=True,        # 启用状态跟踪
    enable_expiry=True          # 启用过期管理
)
```

### 从Moltbot迁移会话管理功能

#### 1. 替换导入

```python
# 旧的 Moltbot 导入
from py_moltbot.core.session import SessionManager, SessionContext

# 新的 AgentBus 导入
from agentbus.sessions import SessionManager, SessionContext
```

#### 2. 更新初始化

```python
# 旧的初始化
manager = SessionManager()
await manager.start()

# 新的初始化
system = await initialize_sessions()
```

#### 3. 更新API调用

大多数API保持兼容，但需要更新一些枚举类型：

```python
# 平台类型
Platform.TELEGRAM  # 替代原来的 telegram.platform

# 会话类型  
SessionType.PRIVATE  # 替代原来的 PRIVATE
```

#### 4. 迁移到完整系统（可选）

```python
# 使用完整功能
system = await initialize_sessions(
    storage_type=StorageType.DATABASE,
    storage_config={"db_path": "./agentbus.db"},
    enable_all_features=True,
    backup_dir=Path("./backups"),
    archive_dir=Path("./archive")
)

# 保持现有API兼容性
session = await system.create_session(...)  # 旧API仍然工作
```

## 故障排除

### 常见问题

1. **存储连接失败**
   ```python
   # 检查存储配置
   health = await manager.health_check()
   print(health)
   ```

2. **内存使用过高**
   ```python
   # 调整清理间隔
   manager = await initialize_sessions(cleanup_interval=60)  # 1分钟
   
   # 定期清理
   await manager.cleanup_all_expired()
   ```

3. **会话数据丢失**
   ```python
   # 使用持久化存储
   manager = await initialize_sessions(StorageType.DATABASE)
   ```

### 监控和日志

```python
import logging

# 启用详细日志
logging.getLogger('agentbus.sessions').setLevel(logging.DEBUG)

# 健康检查
health = await health_check()
if health['status'] != 'healthy':
    print(f"系统状态异常: {health}")
```

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 运行测试
5. 创建 Pull Request

## 许可证

本项目遵循 MIT 许可证。

## 🎉 完成总结

### ✅ 已实现功能

本次扩展实现了基于Moltbot会话管理功能的完整AgentBus会话管理系统，包括：

#### 🏗️ 核心架构
- ✅ **完整会话管理系统**: 统一的SessionSystem类，整合所有功能模块
- ✅ **模块化设计**: 支持按需启用不同功能，提供灵活的配置选项
- ✅ **向后兼容**: 保持与现有API的完全兼容，支持渐进式升级

#### 🔄 会话同步系统 (session_sync.py)
- ✅ **跨通道会话同步**: 支持多平台、多通道的会话关联和同步
- ✅ **身份映射**: 智能的用户身份识别和映射机制
- ✅ **冲突解决**: 支持latest_wins、manual、source_priority等策略
- ✅ **同步操作**: 支持create、update、delete、merge等操作类型

#### 💾 会话持久化 (session_persistence.py)
- ✅ **多格式备份**: 支持JSON、JSON_GZ、Pickle、Pickle_GZ格式
- ✅ **自动备份**: 可配置的自动备份机制和保留策略
- ✅ **恢复策略**: 支持merge、replace、skip、interactive等策略
- ✅ **完整性验证**: 备份文件的校验和完整性检查
- ✅ **导出导入**: 单个会话的导出和导入功能

#### 📊 会话状态跟踪 (session_state_tracker.py)
- ✅ **状态机**: 可配置的状态转换规则和处理器
- ✅ **事件跟踪**: 全面的会话事件记录和分析
- ✅ **模式分析**: 自动识别使用模式和趋势
- ✅ **预测功能**: 智能的生命周期预测和建议
- ✅ **统计报告**: 详细的状态统计和使用分析

#### ⏰ 会话过期管理 (session_expiry.py)
- ✅ **多策略过期**: 时间、活动、使用量、混合、自定义等策略
- ✅ **智能清理**: 支持archive、delete、merge、suspend、notify等操作
- ✅ **优先级管理**: 基于优先级的渐进式过期处理
- ✅ **通知机制**: 灵活的过期通知和回调系统
- ✅ **归档功能**: 自动归档和恢复功能

#### 🔧 系统集成 (session_system.py)
- ✅ **统一接口**: SessionSystem类提供统一的系统接口
- ✅ **配置管理**: 灵活的SessionSystemConfig和预设配置
- ✅ **健康监控**: 完整的系统健康检查和状态监控
- ✅ **组件协调**: 各模块间的协调和集成管理

### 📁 新增文件

```
agentbus/sessions/
├── session_sync.py              # 跨通道会话同步
├── session_persistence.py       # 会话持久化和恢复
├── session_state_tracker.py     # 会话状态跟踪
├── session_expiry.py           # 会话过期处理
├── session_system.py          # 完整会话管理系统
└── demo_complete_system.py    # 完整系统演示脚本
```

### 🚀 使用示例

#### 开发环境快速开始
```python
system = await initialize_sessions(enable_all_features=True)
```

#### 生产环境配置
```python
config = get_production_config(
    storage_config={"db_path": "./prod.db"},
    backup_dir=Path("./backups"),
    archive_dir=Path("./archive")
)
system = await initialize_sessions(**config.__dict__)
```

### 🔄 迁移路径

1. **向后兼容**: 现有代码无需修改即可继续工作
2. **逐步升级**: 可以逐个启用新功能模块
3. **完整迁移**: 使用完整SessionSystem获得所有功能

### 📈 性能优化

- ✅ **内存管理**: 智能的内存使用和垃圾回收
- ✅ **批量操作**: 支持批量会话处理和同步
- ✅ **缓存机制**: 多层缓存提升访问性能
- ✅ **异步处理**: 全面的异步操作支持

### 🛡️ 稳定性保证

- ✅ **错误处理**: 全面的异常处理和错误恢复
- ✅ **健康检查**: 实时系统健康状态监控
- ✅ **自动恢复**: 系统组件的自动恢复机制
- ✅ **日志记录**: 详细的操作日志和审计跟踪

## 🔮 未来扩展

### 可能的增强功能
- 🤖 **AI智能**: 集成AI进行会话质量分析和优化
- 📱 **移动端支持**: 专门的移动端会话管理
- 🌐 **分布式**: 支持多节点分布式会话管理
- 📊 **可视化**: Web界面和可视化仪表板
- 🔐 **安全增强**: 更细粒度的权限控制和安全审计

---

**AgentBus会话管理系统现在提供了企业级的完整会话管理解决方案，支持从简单的应用到复杂的企业部署的所有需求。**