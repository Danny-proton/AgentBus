

# AgentBus Python Implementation
# AI Programming Assistant - Server Edition

## 项目结构

```
kode_core/
├── api/                    # API 接口层
│   ├── __init__.py
│   ├── routes/             # REST API 路由
│   │   ├── __init__.py
│   │   ├── session.py      # 会话管理接口
│   │   ├── agent.py        # Agent 控制接口
│   │   └── config.py       # 配置管理接口
│   ├── websockets/         # WebSocket 处理器
│   │   ├── __init__.py
│   │   └── handler.py      # WebSocket 消息处理
│   └── schemas/            # Pydantic 数据模型
│       ├── __init__.py
│       ├── message.py      # 消息格式定义
│       ├── session.py      # 会话模型
│       └── agent.py        # Agent 相关模型
├── core/                   # 核心业务层
│   ├── __init__.py
│   ├── agent/              # Agent 核心逻辑
│   │   ├── __init__.py
│   │   ├── orchestrator.py # 多模型协调器
│   │   ├── loop.py         # Agent 执行循环
│   │   └── state.py        # Agent 状态管理
│   ├── context/            # 上下文管理
│   │   ├── __init__.py
│   │   ├── manager.py      # 上下文管理器
│   │   ├── compressor.py   # 上下文压缩
│   │   └── rag.py          # RAG 相关功能
│   ├── llm/                # LLM 客户端
│   │   ├── __init__.py
│   │   ├── client.py       # OpenAI 客户端封装
│   │   ├── manager.py      # 多模型管理器
│   │   └── stream.py       # 流式响应处理
│   └── memory/             # 记忆系统
│       ├── __init__.py
│       ├── short_term.py   # 短期记忆
│       └── long_term.py    # 长期记忆
├── runtime/                # 环境运行时层
│   ├── __init__.py
│   ├── abstract.py         # 抽象基类定义
│   ├── local/              # 本地环境实现
│   │   ├── __init__.py
│   │   ├── environment.py  # 本地环境
│   │   ├── executor.py     # 命令执行器
│   │   └── file_ops.py     # 文件操作
│   └── remote/             # 远程 VM 实现
│       ├── __init__.py
│       ├── ssh.py          # SSH 连接管理
│       ├── environment.py  # 远程环境
│       └── file_transfer.py # 文件传输
├── tools/                  # 工具层
│   ├── __init__.py
│   ├── registry.py         # 工具注册中心
│   ├── base.py             # 工具基类
│   ├── file_tools.py       # 文件操作工具
│   ├── terminal.py         # 终端命令工具
│   ├── search.py           # 搜索工具
│   └── custom.py           # 自定义工具
├── services/               # 服务层
│   ├── __init__.py
│   ├── cost_tracker.py     # 成本追踪服务
│   └── session_manager.py  # 会话管理服务
├── config/                 # 配置管理
│   ├── __init__.py
│   ├── settings.py         # 配置加载
│   └── models.py           # 配置模型
├── main.py                 # 应用入口
└── requirements.txt        # 依赖列表
```

## 核心设计原则

1. **异步优先**: 所有 I/O 操作使用 asyncio
2. **接口抽象**: 运行环境通过抽象接口隔离
3. **流式处理**: 支持 LLM 流式响应
4. **可扩展性**: 工具系统支持动态注册
5. **类型安全**: 使用 Pydantic 进行数据验证

## 使用方法

### 启动服务
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### WebSocket 连接
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/agent');
ws.send(JSON.stringify({type: 'user_message', content: '分析这个项目结构'}));
```

### REST API
```bash
# 创建会话
curl -X POST http://localhost:8000/api/sessions

# 发送消息
curl -X POST http://localhost:8000/api/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "解释这段代码"}'
```
