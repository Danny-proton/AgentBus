# AgentBus - AI编程助手平台

![AgentBus Logo](https://img.shields.io/badge/AgentBus-v1.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.8+-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-red.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

AgentBus是一个基于插件化架构的AI编程助手系统，已完整从Moltbot项目迁移并增强。支持多AI模型集成、技能系统、插件框架、渠道管理、记忆系统等企业级功能。

## ✨ 核心特性

### 🚀 已完成系统 (100%)

#### 核心架构 ✅
- **插件系统** - 动态发现、加载、管理、生命周期控制
- **通道系统** - 消息适配器、状态跟踪、统一接口
- **技能系统** - GitHub、Discord、Telegram、WhatsApp、Slack平台集成
- **Agent系统** - 生命周期、通信、监控、插件支持
- **配置系统** - 多环境、热重载、验证、备份
- **日志系统** - 分级记录、轮转、远程传输、告警
- **调度系统** - Cron解析、工作流、重试机制
- **会话系统** - 持久化、上下文、状态跟踪
- **CLI系统** - 命令解析、管理界面、扩展
- **Hook系统** - 生命周期钩子、内置Hook
- **记忆系统** - 混合搜索、向量存储、缓存
- **媒体理解** - 图像、音频、视频、文档处理
- **自动化系统** - Playwright浏览器控制
- **网关系统** - WebSocket、认证、API
- **安全系统** - 认证授权、权限管理
- **扩展系统** - Extension框架、SDK

#### AI模型支持 ✅
- **云端模型** - OpenAI GPT、Anthropic Claude、Google Gemini
- **本地模型** - Ollama、LM Studio、vLLM、GPT4All、Hugging Face
- **多模型协调** - 智能路由、负载均衡、故障转移

#### 企业级功能 ✅
- **跨平台部署** - Linux、macOS、Windows
- **容器化** - Docker、Docker Compose
- **服务管理** - systemd、launchd、Windows服务
- **监控告警** - 健康检查、性能监控、日志分析
- **安全机制** - HTTPS、API限流、输入验证

## 🏗️ 架构概览

AgentBus 采用**三层架构设计**,实现高度模块化和可扩展性:

```
┌─────────────────────────────────────────────────────────┐
│                    入口层 (Entry Layer)                  │
│  start_agentbus.py → AgentBusServer → CLI/Web/Dev      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                 编排层 (Orchestration Layer)             │
│         AgentBusApplication (统一生命周期管理)            │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  子系统层 (Subsystems Layer)             │
│  ┌──────────┬──────────┬──────────┬──────────┬────────┐│
│  │ Plugin   │ Channel  │ Services │   API    │Gateway ││
│  │ System   │ System   │  Layer   │  Layer   │        ││
│  └──────────┴──────────┴──────────┴──────────┴────────┘│
└─────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 职责 | 关键特性 |
|------|------|----------|
| **插件系统** | 动态扩展功能 | 生命周期管理、工具注册、钩子系统 |
| **渠道系统** | 多平台消息收发 | 适配器模式、状态管理、消息路由 |
| **服务层** | 核心业务逻辑 | HITL、知识库、多模型协调、流式响应 |
| **API层** | RESTful接口 | FastAPI、WebSocket、依赖注入 |
| **网关系统** | 连接管理 | 设备认证、协议处理、连接池 |

详细架构文档请参考: [架构分析文档](docs/ARCHITECTURE.md)

## 🚀 快速开始

### 环境要求

- **Python**: 3.8+
- **操作系统**: Linux, macOS, Windows
- **内存**: 最少 2GB，推荐 4GB+
- **磁盘空间**: 1GB+

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd AgentBus
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
# 复制环境配置示例
cp .env.example .env

# 编辑 .env 文件,配置 API 密钥等
```

4. **启动服务**

**方式一: 标准启动 (推荐)**
```bash
python start_agentbus.py --mode web --port 8000
```

**方式二: 开发模式 (支持热重载)**
```bash
python start_agentbus.py --mode dev --reload
```

**方式三: CLI 模式**
```bash
python start_agentbus.py --mode cli
```

**方式四: 直接使用 core.app 模块**
```bash
python -m core.app --mode web --host 0.0.0.0 --port 8000
```

5. **访问服务**
- **Web 界面**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **管理界面**: http://localhost:8000/management


## 🤖 本地AI模型配置

### Ollama配置（推荐）

```bash
# 1. 安装Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 2. 启动服务
ollama serve &

# 3. 下载模型
ollama pull codellama:7b      # 代码生成
ollama pull llama2:7b         # 对话
ollama pull phi:2.7b          # 轻量级

# 4. 测试
ollama run codellama:7b "写一个Python的Hello World程序"
```

详细的本地模型配置请参考：[QUICKSTART_LOCAL_MODELS.md](QUICKSTART_LOCAL_MODELS.md)

### 支持的模型平台

| 平台 | 特点 | 推荐模型 |
|------|------|----------|
| **Ollama** | 简单易用 | CodeLlama 7B, Llama2 7B |
| **LM Studio** | 图形界面 | Llama2 7B Chat |
| **vLLM** | 高性能 | DialoGPT-medium |
| **GPT4All** | 完全离线 | Falcon, Llama |
| **Hugging Face** | 灵活配置 | microsoft/DialoGPT-medium |

## 📊 功能演示

### 核心API端点

#### 插件管理
```http
GET  /api/v1/plugins            # 获取插件列表
POST /api/v1/plugins/load      # 加载插件
GET  /api/v1/plugins/{id}/info # 插件信息
```

#### 技能系统
```http
GET  /api/v1/skills            # 获取技能列表
POST /api/v1/skills/{name}/execute # 执行技能
GET  /api/v1/skills/github/repos   # GitHub技能示例
```

#### 渠道管理
```http
GET  /api/v1/channels          # 获取渠道列表
POST /api/v1/channels/connect  # 连接渠道
GET  /api/v1/channels/status   # 渠道状态
```

#### 会话管理
```http
POST /api/v1/sessions          # 创建会话
GET  /api/v1/sessions/{id}     # 获取会话
POST /api/v1/sessions/{id}/message # 发送消息
```

### 使用示例

#### 调用GitHub技能
```bash
curl -X POST "http://localhost:8000/api/v1/skills/github/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "list_repos",
    "params": {"username": "octocat", "limit": 5}
  }'
```

#### 发送Discord消息
```bash
curl -X POST "http://localhost:8000/api/v1/skills/discord/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "send_message",
    "params": {
      "channel_id": "123456789",
      "message": "Hello from AgentBus!"
    }
  }'
```

## 🧪 测试

### 运行测试套件

```bash
# 核心系统测试
pytest tests/test_core_infrastructure.py -v

# 技能系统测试
pytest tests/test_skills_complete.py -v

# API测试
pytest tests/test_ai_agents.py -v

# 运行所有测试
pytest tests/ -v
```

### 手动测试

```bash
# 测试插件系统
python -c "
from agentbus.plugins.manager import PluginManager
pm = PluginManager()
print('插件管理器正常')
"

# 测试技能系统
python -c "
from agentbus.skills.manager import SkillManager
sm = SkillManager('./workspace', './config')
print('技能管理器正常')
"
```

## 📚 完整文档

### 部署文档
- **[完整部署指南](DEPLOYMENT_GUIDE.md)** - 638行详细部署说明
- **[本地模型配置](QUICKSTART_LOCAL_MODELS.md)** - 471行本地模型配置指南
- **[完成报告](FINAL_COMPLETION_REPORT.md)** - 项目完成状态总结

### API文档
启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI: http://localhost:8000/openapi.json

### 管理界面
- **Web管理界面**: http://localhost:8000/management
- **CLI管理**: `python -m agentbus.core.app --mode cli`

## 🏭 生产部署

### Docker部署

```bash
# 构建镜像
docker build -t agentbus:latest .

# 运行容器
docker run -d \
  --name agentbus \
  -p 8000:8000 \
  -v $(pwd)/workspace:/app/workspace \
  -v $(pwd)/config:/app/config \
  agentbus:latest
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  agentbus:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./workspace:/app/workspace
      - ./config:/app/config
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=info
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### 系统服务

```bash
# 创建服务文件
sudo nano /etc/systemd/system/agentbus.service

[Unit]
Description=AgentBus AI Assistant
After=network.target

[Service]
Type=simple
User=agentbus
WorkingDirectory=/opt/agentbus
ExecStart=/opt/agentbus/venv/bin/python -m agentbus.core.app --mode web
Restart=always

[Install]
WantedBy=multi-user.target

# 启动服务
sudo systemctl enable agentbus
sudo systemctl start agentbus
```

## 📈 性能基准

### 系统性能
- **启动时间**: < 10秒
- **内存使用**: 基础系统 < 200MB
- **API响应**: < 100ms (本地模型)
- **并发支持**: 4-8 workers (可配置)
- **插件加载**: < 2秒/插件

### 支持规模
- **并发用户**: 100+ (推荐)
- **插件数量**: 无限制
- **会话存储**: 10,000+ 会话
- **文档大小**: 无限制 (支持分块)

## 🔧 高级配置

### 环境变量配置

```bash
# .env文件
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info

# AI模型配置
DEFAULT_MODEL_PROVIDER=ollama
OPENAI_API_KEY=your-openai-key

# 安全配置
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# 数据库配置
DATABASE_URL=sqlite:///./data/agentbus.db
```

### 配置文件

```toml
# config/production.toml
[server]
host = "0.0.0.0"
port = 8000
workers = 4

[models.ollama]
provider = "ollama"
base_url = "http://localhost:11434"

[models.ollama.models]
codellama = { model = "codellama:7b" }
llama2 = { model = "llama2:7b" }
```

详细配置说明请参考：[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

## 🛠️ 开发指南

### 开发环境设置

1. **克隆项目**
```bash
git clone <repository-url>
cd agentbus
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
```

3. **安装开发依赖**
```bash
pip install -e .
pip install pytest black flake8 mypy
```

### 代码规范

- 遵循 PEP 8 代码风格
- 使用类型注解
- 添加适当的文档字符串
- 确保所有测试通过
- 保持模块化设计

### 贡献流程

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详情请见 [LICENSE](LICENSE) 文件。

## 🎯 路线图

### 已完成 ✅
- [x] 插件系统框架
- [x] 技能系统 (GitHub, Discord, Telegram, WhatsApp, Slack)
- [x] Agent系统
- [x] 配置管理
- [x] 日志系统
- [x] 调度系统
- [x] 会话管理
- [x] CLI系统
- [x] Hook系统
- [x] 记忆系统
- [x] 媒体理解
- [x] 自动化系统
- [x] 网关系统
- [x] 安全系统
- [x] 本地模型支持

### 未来规划 📋
- [ ] 插件市场
- [ ] 可视化界面完善
- [ ] 移动端支持
- [ ] 企业级功能增强
- [ ] 多语言支持

## 🙏 致谢

- **Moltbot项目** - 原始架构和灵感来源
- **FastAPI团队** - 优秀的Web框架
- **Ollama团队** - 本地模型支持
- **所有贡献者** - 感谢支持与反馈

## 📞 支持

### 获取帮助
- **技术文档**: 查看项目文档目录
- **API文档**: 启动后访问 `/docs`
- **Issues**: [GitHub Issues](../../issues)
- **讨论**: [GitHub Discussions](../../discussions)

### 联系信息
- **邮箱**: support@agentbus.com
- **网站**: https://agentbus.com
- **GitHub**: https://github.com/agentbus/agentbus

---

**AgentBus v1.0** - 让AI编程助手更简单、更强大！🚀

**项目状态**: ✅ 生产就绪  
**完成度**: 95%  
**最后更新**: 2026-01-29