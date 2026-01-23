---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 30440220097c2b0a9c286d6229bfddd1202e80bb11318238dd74d1b6e8938768d8a28e2a02206177d0032765a4bb8cfa0aa462cce819b9ea474d03cac2efb5e78c7cd372f6e5
    ReservedCode2: 3045022100cd9dece19dbb8d52508d91f8d67f25cd92fc4a5eed1ac2f7473e447d78bf8604022009d24d11bc3e9c04cab448fa08e3fa63905d75cd3e0e7e8d640656b99252689d
---

# AgentBus 功能增强总结

本文档总结了所有新增功能及使用方法。

## 1. 完整日志系统 (LogService)

### 功能描述
记录所有 Agent 执行过程中的操作细节，支持配置开关。

### 主要特性
- ✅ 支持不同日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- ✅ 支持多个日志类别 (AGENT, TOOL, LLM, SUBAGENT, SESSION, SYSTEM)
- ✅ 异步写入，批量刷新性能优化
- ✅ 可通过配置关闭日志
- ✅ 日志导出功能 (JSONL, JSON 格式)

### 使用示例
```python
from services.log_service import init_log_service, get_log_service

# 初始化
log_service = init_log_service("./workspace/logs", enabled=True)

# 记录工具调用
await log_service.log_tool_call(
    tool_name="file_read",
    agent_id="main_agent",
    arguments={"path": "/workspace/test.py"},
    result="file content...",
    success=True,
    duration_ms=45.2
)

# 记录 LLM 调用
await log_service.log_llm_call(
    model="gpt-4",
    agent_id="main_agent",
    prompt_length=1500,
    response_length=500,
    duration_ms=1200.5,
    tokens_used=2000,
    cost=0.06
)

# 获取最近日志
logs = await log_service.get_recent_logs(limit=100, category="TOOL")
```

### 配置项
```python
# config/settings.py
class LoggingConfig(BaseSettings):
    enabled: bool = True
    level: str = "DEBUG"
    directory: str = "./workspace/logs"
    flush_interval: float = 5.0
    batch_size: int = 100
```

## 2. Knowledge Bus 知识总线

### 功能描述
简洁的长期记忆"小黑板"，用于存储关键信息，避免上下文过长。

### 设计理念
- 当 subagent 或 task 结束时，将上下文存到知识总线
- 需要上报的信息通过知识总线传输
- 共享的长期信息（IP、用户名、密码等）存储到知识总线
- 所有上下文以路径形式存在总线里
- 总线条目有 ID，可通过 ID 引用

### 使用示例
```python
from tools.knowledge_bus import init_knowledge_bus, get_knowledge_bus

# 初始化
knowledge_bus = init_knowledge_bus("./workspace")

# 存储信息
entry_id = await knowledge_bus.put(
    key="server_ip",
    value="192.168.1.100",
    category="infrastructure",
    metadata={"env": "production"}
)

# 获取信息
entry = await knowledge_bus.get(key="server_ip")

# 通过 ID 获取
entry = await knowledge_bus.get_by_id(entry_id)

# 按类别获取
entries = await knowledge_bus.get_by_category("infrastructure")

# 删除条目
await knowledge_bus.delete(key="server_ip")
```

### Knowledge Bus 工具
所有 Agent 都可以使用 knowledge_bus 工具：

```python
# 作为工具调用
tool = KnowledgeBusTool(None, knowledge_bus)

# 存储
await tool.execute(
    action="put",
    key="database_password",
    value="secret123",
    category="credentials"
)

# 获取
await tool.execute(action="get", key="database_password")

# 列出所有
await tool.execute(action="get_all")

# 按类别查询
await tool.execute(action="get_by_category", category="credentials")
```

### 知识总线文件格式
```json
{
  "updated_at": "2024-01-22T10:00:00",
  "entries": {
    "a1b2c3d4": {
      "id": "a1b2c3d4",
      "key": "server_ip",
      "value": "192.168.1.100",
      "category": "infrastructure",
      "created_at": "2024-01-22T10:00:00",
      "access_count": 5
    }
  }
}
```

## 3. Human-in-the-Loop 人在回路

### 功能描述
只有主 Agent 能使用的人机协作工具，支持在遇到问题时请求人工帮助。

### 主要特性
- ✅ 支持逐层上报问题
- ✅ 支持紧急程度分级 (low, normal, high, critical)
- ✅ 支持预设选项
- ✅ 异步响应，响应会注入到下一轮主 Agent 上下文
- ✅ WebSocket 通知前端

### 使用示例
```python
from tools.human_in_loop import create_human_loop_tool, get_human_loop

# 创建工具（仅主 Agent）
human_loop_tool = create_human_loop_tool(is_main_agent=True)

# 请求人工输入
await human_loop_tool.execute(
    action="request",
    message="无法连接到数据库，请确认是否需要重启服务？",
    urgency="high",
    options=["重启服务", "等待", "查看日志"]
)

# 检查响应（不阻塞）
await human_loop_tool.execute(
    action="check_response",
    request_id="abc123",
    timeout=300
)

# 列出待处理请求
await human_loop_tool.execute(action="list_pending")

# 取消请求
await human_loop_tool.execute(action="cancel", request_id="abc123")
```

### 人工响应处理
```python
# 后端收到前端响应后
human_loop = get_human_loop()
await human_loop.submit_response(request_id, user_response)

# Agent 在下一轮可以检查响应
response = await human_loop_tool.execute(
    action="check_response",
    request_id="abc123"
)
```

### WebSocket 通知
前端会收到如下消息：
```json
{
  "type": "human_request",
  "request_id": "abc123",
  "message": "无法连接到数据库...",
  "urgency": "high",
  "options": ["重启服务", "等待", "查看日志"],
  "context": {...}
}
```

## 4. AgentWorkSpace 工作空间

### 功能描述
初始化项目时创建的工作空间目录，统一管理所有运行时文件。

### 目录结构
```
workspace/
├── logs/              # 日志文件
├── scripts/           # 运行时生成的脚本
├── plans/             # 任务计划文件
├── contexts/          # 上下文文件
├── temp/              # 临时文件
├── agent.md           # 工作空间说明
├── knowledge_bus.md   # 知识总线
└── session.json       # 会话状态
```

### 使用示例
```python
from services.workspace import init_workspace, get_workspace

# 初始化工作空间
workspace = init_workspace("./workspace")

# 获取路径
workspace.get_path()           # "./workspace"
workspace.get_logs_path()      # "./workspace/logs"
workspace.get_scripts_path()   # "./workspace/scripts"

# 写入脚本
script_path = workspace.write_script("deploy.sh", "#!/bin/bash\n...")

# 写入计划
plan_path = workspace.write_plan("task_001.md", "# 任务计划\n...")

# 写入上下文
context_path = workspace.write_context("analysis.json", "{...}")

# 列出文件
files = workspace.list_files(directory="scripts", file_type="script")

# 获取统计
stats = workspace.get_statistics()
# {
#   "workspace_path": "./workspace",
#   "directories": {
#     "logs": 5,
#     "scripts": 3,
#     "plans": 2
#   },
#   "total_size_mb": 10.5
# }

# 清理临时文件
workspace.cleanup_temp(max_age_hours=24)
```

### 自动创建内容
启动时自动创建 `agent.md`:
```markdown
# AgentBus 工作空间

## 创建时间
2024-01-22T10:00:00

## 当前会话信息
- 会话 ID: 待初始化
- 主模型: 待配置
- 工作模式: 标准

## 使用说明
...
```

## 5. Skills 工具集

### 新增的技能工具
参考 Claude 官方实现，添加了以下技能工具：

#### CriticTool - 批评者
```python
# 代码审查
await critic_tool.execute(
    target="code",
    content="print('hello')",
    aspect="correctness"
)
```

#### TaskTool - 任务管理
```python
# 创建任务
await task_tool.execute(
    action="plan",
    task_name="实现功能",
    description="实现用户认证功能",
    dependencies=["数据库设计"]
)

# 列出任务
await task_tool.execute(action="list")

# 完成任务
await task_tool.execute(action="complete", task_name="实现功能")
```

#### NoteTool - 笔记
```python
# 创建笔记
await note_tool.execute(
    action="create",
    title="设计思路",
    content="采用微服务架构..."
)

# 列出笔记
await note_tool.execute(action="list")
```

## 6. 配置系统增强

### 新增配置项
```python
# config/settings.py

class LoggingConfig(BaseSettings):
    enabled: bool = True
    level: str = "DEBUG"
    directory: str = "./workspace/logs"

class WorkspaceConfig(BaseSettings):
    path: str = "./workspace"
    create_if_not_exists: bool = True
    max_temp_age_hours: int = 24

class KnowledgeBusConfig(BaseSettings):
    enabled: bool = True
    auto_cleanup: bool = False
    max_entries: int = 1000

class HumanLoopConfig(BaseSettings):
    enabled: bool = True
    default_timeout: int = 300
    max_pending_requests: int = 10
```

### 环境变量
```bash
# 日志配置
export AGENTBUS_LOGGING_ENABLED=true
export AGENTBUS_LOGGING_LEVEL=DEBUG

# 工作空间配置
export AGENTBUS_WORKSPACE_PATH=./workspace

# 知识总线配置
export AGENTBUS_KNOWLEDGE_ENABLED=true

# 人在回路配置
export AGENTBUS_HUMAN_ENABLED=true
export AGENTBUS_HUMAN_DEFAULT_TIMEOUT=300
```

## 7. 启动流程增强

### main.py 更新
```python
async def lifespan(app: FastAPI):
    # 1. 初始化工作空间
    workspace = init_workspace(settings.workspace.path)
    
    # 2. 初始化日志服务
    log_service = init_log_service(workspace.get_logs_path())
    await start_log_service()
    
    # 3. 初始化知识总线
    knowledge_bus = init_knowledge_bus(settings.workspace.path)
    
    # 4. 初始化其他服务...
    
    yield
    
    # 清理
    await stop_log_service()
```

## 8. 使用建议

### 最佳实践
1. **日志系统**：生产环境建议启用 DEBUG 级别，便于问题排查
2. **知识总线**：频繁使用的信息（配置、凭证）存储到知识总线
3. **人在回路**：仅在真正需要人工决策时使用，避免过度打扰
4. **工作空间**：所有 Agent 生成的文件都放在工作空间，便于管理

### 性能考虑
- 日志服务使用异步写入和批量刷新
- 知识总线使用文件存储，支持快速查询
- 工作空间支持临时文件自动清理

### 与原始 kodecli 的对比
| 功能 | kodecli | AgentBus |
|------|---------|----------|
| 基础工具 | ✅ | ✅ 完整保留 |
| 日志记录 | ❌ | ✅ 完整实现 |
| 知识总线 | ❌ | ✅ 实现 |
| 人在回路 | ❌ | ✅ 实现 |
| 工作空间 | ❌ | ✅ 实现 |
| Skills 工具 | 部分 | ✅ 完整实现 |

## 9. 后续扩展建议

1. **日志分析**：添加日志分析工具，生成执行报告
2. **知识总线持久化**：支持不同存储后端（Redis, SQLite）
3. **人在回路增强**：支持多人协作、审批流程
4. **工作空间模板**：支持不同项目类型的工作空间模板
