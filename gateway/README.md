# Agentbus Gateway System

基于Moltbot Gateway架构的完整网关系统，提供客户端认证、聊天处理、WebSocket通信和API接口管理功能。

## 🚀 功能特性

### 核心功能
- **Gateway服务器** - 高性能WebSocket服务器，支持多客户端连接
- **客户端认证** - 支持Token、密码、设备、Tailscale多种认证方式
- **聊天处理** - 完整的会话管理、消息处理和流式响应
- **WebSocket通信** - 实时双向通信协议
- **API接口管理** - HTTP RESTful API接口

### 安全特性
- **多模式认证** - Token、密码、设备认证
- **会话管理** - 安全的会话创建和销毁
- **权限控制** - 基于Scope的权限管理
- **连接限制** - 最大连接数和超时控制
- **TLS支持** - 安全的WebSocket连接

### 扩展性
- **模块化设计** - 插件化的处理器系统
- **协议扩展** - 可扩展的通信协议
- **负载均衡** - 支持多实例部署
- **监控统计** - 详细的连接和性能统计

## 📋 目录结构

```
agentbus/gateway/
├── __init__.py              # 包初始化
├── demo.py                  # 演示程序
├── auth/                    # 认证模块
│   └── __init__.py          # 认证系统实现
├── protocol/                # 协议模块
│   └── __init__.py          # 通信协议定义
├── core/                    # 核心模块
│   ├── __init__.py
│   ├── server.py           # 网关服务器
│   ├── client.py           # 网关客户端
│   └── connection.py       # 连接管理
├── handlers/               # 处理器模块
│   ├── __init__.py
│   ├── base.py            # 基础处理器
│   └── chat.py            # 聊天处理器
└── api/                    # API模块
    └── __init__.py         # API接口管理
```

## 🔧 安装依赖

```bash
pip install websockets aiohttp asyncio
```

## 🎯 快速开始

### 1. 运行演示程序

```bash
cd /workspace/agentbus/gateway
python demo.py
```

### 2. 启动服务器

```python
import asyncio
from gateway import GatewayServer, GatewayConfig, AuthMode

async def start_gateway():
    # 配置服务器
    config = GatewayConfig(
        host="127.0.0.1",
        port=18789,
        auth_mode=AuthMode.TOKEN,
        auth_token="your-secret-token"
    )
    
    # 创建并启动服务器
    server = GatewayServer(config)
    await server.start()

# 运行服务器
asyncio.run(start_gateway())
```

### 3. 连接客户端

```python
import asyncio
from gateway import GatewayClient, ClientConfig

async def connect_client():
    # 配置客户端
    config = ClientConfig(
        url="ws://127.0.0.1:18789",
        client_name="My Client",
        auth_token="your-secret-token"
    )
    
    # 创建客户端
    client = GatewayClient(config)
    
    # 连接
    await client.connect()
    
    # 发送请求
    result = await client.send_request("system.info")
    print(f"System info: {result}")
    
    # 断开连接
    await client.disconnect()

# 运行客户端
asyncio.run(connect_client())
```

## 📡 API文档

### WebSocket API

#### 连接握手

```javascript
// 发送连接请求
{
  "type": "req",
  "id": "uuid",
  "method": "connect",
  "params": {
    "client_id": "client-123",
    "client_name": "My Application",
    "version": "1.0.0",
    "platform": "web",
    "capabilities": ["chat", "sessions"],
    "auth_token": "your-token"
  }
}

// 服务器响应
{
  "type": "res",
  "id": "uuid",
  "ok": true,
  "payload": {
    "server_info": {...},
    "capabilities": [...],
    "policy": {...},
    "auth_info": {...}
  }
}
```

#### 聊天API

```javascript
// 发送消息
{
  "type": "req",
  "id": "uuid",
  "method": "chat.send",
  "params": {
    "session_id": "session-123",
    "message": "Hello World",
    "type": "text"
  }
}

// 获取历史
{
  "type": "req",
  "id": "uuid",
  "method": "chat.history",
  "params": {
    "session_id": "session-123",
    "limit": 50
  }
}
```

### HTTP REST API

#### 基础端点

```
GET  /status              # 服务器状态
GET  /health              # 健康检查
GET  /api/v1/sessions     # 列出会话
POST /api/v1/sessions     # 创建会话
GET  /api/v1/clients      # 列出客户端
GET  /api/v1/stats        # 统计信息
```

#### 认证

```bash
# Bearer Token认证
curl -H "Authorization: Bearer your-token" \
     http://localhost:8080/api/v1/clients

# Basic认证
curl -u gateway:password \
     http://localhost:8080/api/v1/sessions
```

## 🔐 认证系统

### Token认证

```python
from gateway.auth import GatewayAuth, AuthConfig, AuthMode

# 创建Token认证
config = AuthConfig(
    mode=AuthMode.TOKEN,
    token="your-secret-token"
)
auth = GatewayAuth(config)

# 认证Token
result = auth.authenticate_token("your-secret-token")
if result.success:
    print(f"认证成功: {result.user_id}")
```

### 设备认证

```python
# 注册设备
device = auth.register_device("device-123", "public-key")

# 设备认证
result = auth.authenticate_device(
    "device-123",
    "signature",
    "nonce",
    timestamp
)
```

### 会话管理

```python
# 创建会话
session_id = auth.create_session(auth_result, client_info)

# 验证会话
result = auth.validate_session(session_id)

# 撤销会话
auth.revoke_session(session_id)
```

## 🧠 聊天系统

### 会话管理

```python
from gateway.handlers.chat import ChatManager, ChatSession, ChatMessage

# 创建聊天管理器
chat_manager = ChatManager(protocol_handler)

# 创建会话
session = chat_manager.create_session("session-123", "client-123")

# 添加消息
message = ChatMessage(
    role="user",
    content="Hello",
    metadata={"type": "text"}
)
chat_manager.add_message("session-123", message)

# 获取历史
messages = chat_manager.get_messages("session-123", limit=50)
```

### 消息处理

```python
# 创建聊天运行
run = chat_manager.create_run("session-123")

# 异步处理
asyncio.create_task(process_chat_message(session_id, run.run_id, message))

# 中止运行
chat_manager.abort_run(run.run_id)
```

## 🌐 连接管理

### 连接状态

```python
from gateway.core.connection import ConnectionManager, ConnectionState

connection_manager = ConnectionManager(protocol_handler, auth)

# 检查连接状态
for connection_id, connection in connection_manager.connections.items():
    print(f"连接 {connection_id}: {connection.state.value}")
    if connection.client_info:
        print(f"客户端: {connection.client_info.client_name}")
```

### 事件广播

```python
# 广播事件
await connection_manager.broadcast_event(
    "notification",
    {"message": "系统通知"},
    client_filter=lambda c: "admin" in c.capabilities
)
```

## 📊 监控统计

### 服务器状态

```python
status = server.get_status()
print(f"运行时间: {status['uptime']:.2f}秒")
print(f"连接数: {status['connections']}")
print(f"客户端: {len(status['clients'])}")
```

### 聊天统计

```python
stats = chat_manager.get_stats()
print(f"总会话数: {stats['total_sessions']}")
print(f"活跃运行: {stats['active_runs']}")
```

## 🔧 配置选项

### 服务器配置

```python
from gateway.core.server import GatewayConfig

config = GatewayConfig(
    host="0.0.0.0",           # 监听地址
    port=18789,               # 监听端口
    max_connections=1000,     # 最大连接数
    connection_timeout=300,    # 连接超时(秒)
    heartbeat_interval=30,     # 心跳间隔(秒)
    auth_mode=AuthMode.TOKEN,  # 认证模式
    auth_token="secret",       # 认证令牌
    allow_tailscale=False,     # 允许Tailscale
    log_level="INFO"          # 日志级别
)
```

### 客户端配置

```python
from gateway.core.client import ClientConfig

config = ClientConfig(
    url="ws://localhost:18789",    # 服务器地址
    client_id="client-123",        # 客户端ID
    client_name="My App",         # 客户端名称
    version="1.0.0",              # 版本号
    platform="python",             # 平台
    capabilities=["chat"],         # 能力列表
    auth_token="secret",           # 认证令牌
    auto_reconnect=True,           # 自动重连
    max_reconnect_attempts=10,     # 最大重连次数
    reconnect_delay=5.0,           # 重连延迟
    heartbeat_interval=30,         # 心跳间隔
    request_timeout=30.0            # 请求超时
)
```

## 🚀 部署指南

### Docker部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 18789 8080

CMD ["python", "demo.py"]
```

### systemd服务

```ini
[Unit]
Description=Agentbus Gateway
After=network.target

[Service]
Type=simple
User=gateway
WorkingDirectory=/opt/gateway
ExecStart=/usr/bin/python3 demo.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Nginx反向代理

```nginx
upstream gateway_ws {
    server 127.0.0.1:18789;
}

upstream gateway_api {
    server 127.0.0.1:8080;
}

server {
    listen 80;
    server_name your-domain.com;

    # WebSocket代理
    location /ws/ {
        proxy_pass http://gateway_ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # HTTP API代理
    location /api/ {
        proxy_pass http://gateway_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🧪 测试

### 单元测试

```bash
python -m pytest tests/
```

### 集成测试

```bash
python demo.py
```

### 性能测试

```python
import asyncio
import websockets
import json

async def performance_test():
    uri = "ws://localhost:18789"
    async with websockets.connect(uri) as websocket:
        # 发送大量请求
        for i in range(1000):
            request = {
                "type": "req",
                "id": f"test-{i}",
                "method": "system.status"
            }
            await websocket.send(json.dumps(request))
            response = await websocket.recv()
            
asyncio.run(performance_test())
```

## 🤝 贡献指南

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- 基于 [Moltbot](https://github.com/mariozechner/moltbot) Gateway系统架构
- 使用Python asyncio进行异步处理
- WebSocket支持由websockets库提供
- HTTP API支持由aiohttp提供

## 📞 支持

如有问题或建议，请创建Issue或联系维护者。

---

**Agentbus Gateway System** - 让AI通信更简单！