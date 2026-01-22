# AgentBus Python 项目

## 目录结构

```
kode_core/
├── api/                    # API 接口层
│   ├── routes/             # REST API 路由
│   ├── websockets/         # WebSocket 处理器
│   └── schemas/            # Pydantic 数据模型
├── core/                   # 核心业务层
│   ├── agent/              # Agent 逻辑
│   ├── context/            # 上下文管理
│   ├── llm/                # LLM 客户端
│   └── memory/             # 记忆系统
├── runtime/                # 环境运行时层
│   ├── abstract.py         # 抽象基类
│   ├── local/              # 本地环境
│   └── remote/             # 远程 SSH 环境
├── tools/                  # 工具层
├── services/               # 服务层
├── config/                 # 配置管理
├── tests/                  # 测试文件
├── main.py                 # 应用入口
├── cli.py                  # CLI 入口
├── pyproject.toml          # 项目配置
└── requirements.txt        # 依赖列表
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境

```bash
cp .env.example .env
# 编辑 .env 文件，填入您的 API Key
```

### 启动服务

```bash
# 开发模式
python cli.py --reload --port 8000

# 生产模式
python cli.py --host 0.0.0.0 --port 8000 --workers 4
```

## API 使用

### REST API

#### 创建会话

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"workspace": "/path/to/project"}'
```

#### 发送消息

```bash
curl -X POST http://localhost:8000/api/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "分析这个代码库"}'
```

### WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/agent');

// 初始化
ws.send(JSON.stringify({
  type: 'init',
  session_id: null  // 创建新会话
}));

// 发送消息
ws.send(JSON.stringify({
  type: 'user_message',
  content: '解释这个函数',
  model: 'gpt-4'
}));

// 监听响应
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'chunk') {
    process.stdout.write(data.data);
  }
};
```

## 远程环境配置

### SSH 连接

在 `.env` 中配置：

```bash
AGENTBUS_REMOTE_ENABLED=true
AGENTBUS_REMOTE_HOST=your_server.com
AGENTBUS_REMOTE_PORT=22
AGENTBUS_REMOTE_USERNAME=your_username
AGENTBUS_REMOTE_PASSWORD=your_password
# 或使用私钥
AGENTBUS_REMOTE_PRIVATE_KEY_PATH=~/.ssh/id_rsa
```

## 开发

### 运行测试

```bash
pytest tests/ -v
```

### 代码格式化

```bash
black .
isort .
```

### 类型检查

```bash
mypy .
```

## 贡献

1. Fork 本仓库
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request
