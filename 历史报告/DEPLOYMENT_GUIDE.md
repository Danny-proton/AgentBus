---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 304502204ad3933730a5f1e8e2eb9cc62cc7b0717663a71fc8e43d8f8bab41923bb4dd10022100849ce965208a78d7ec849c5c7b55b75ebc0b21791a3e52b8204c137c1ff1d501
    ReservedCode2: 30450220513a616d8f8659a43c00fab0ef04868a17085592b3a0d6185107176c4dfe3e230221008eb1d46d715b2da90364f16b87e57fd73a155168c05948748d4baa615381d716
---

# AgentBus 完整部署指南

## 📋 概述

AgentBus是由行业解决方案集成与验证部（行解）牵头打造的智能测试协作助手平台，通过插件化架构提供多渠道沟通、智能任务调度、自动化测试执行和团队协作功能。支持云端和本地AI模型集成，让团队协作更高效、测试流程更智能。本指南将详细介绍如何在各种环境中部署和配置AgentBus。

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
cd agentbus
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **安装可选依赖**
```bash
# 如果需要使用浏览器自动化
pip install playwright
playwright install

# 如果需要使用向量数据库
pip install lancedb

# 如果需要本地AI模型支持
pip install torch transformers accelerate
```

4. **初始化配置**
```bash
# 创建默认配置文件
python -c "from agentbus.config.settings import setup_default_config; setup_default_config()"

# 创建工作空间目录
mkdir -p workspace/{logs,scripts,plans,contexts,temp,memory,knowledge,agent}
```

5. **启动服务**
```bash
# Web模式（推荐）
python -m agentbus.core.app --mode web --host 0.0.0.0 --port 8000

# 开发模式
python -m agentbus.core.app --mode dev --reload

# CLI模式
python -m agentbus.core.app --mode cli
```

## 🏗️ 生产环境部署

### 使用Docker部署

1. **构建Docker镜像**
```bash
docker build -t agentbus:latest .
```

2. **运行容器**
```bash
docker run -d \
  --name agentbus \
  -p 8000:8000 \
  -v $(pwd)/workspace:/app/workspace \
  -v $(pwd)/config:/app/config \
  agentbus:latest
```

3. **使用Docker Compose**
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
      - ./data:/app/data
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - LOG_LEVEL=info
    restart: unless-stopped

  # 可选：Redis用于缓存
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

## ⚙️ 配置管理

### 环境变量配置

```bash
# .env文件
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=info

# API配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# 安全配置
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# 数据库配置
DATABASE_URL=sqlite:///./data/agentbus.db

# AI模型配置
DEFAULT_MODEL_PROVIDER=openai
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

### 配置文件

AgentBus支持TOML格式的配置文件：

```toml
# config/production.toml
[server]
host = "0.0.0.0"
port = 8000
workers = 4
reload = false

[database]
url = "sqlite:///./data/agentbus.db"
pool_size = 10
max_overflow = 20

[logging]
level = "info"
file = "logs/agentbus.log"
max_size = "100MB"
backup_count = 5

[security]
secret_key = "${SECRET_KEY}"
session_timeout = 3600
max_request_size = "10MB"

[plugins]
auto_load = true
directories = [
    "./plugins",
    "./custom_plugins"
]

[channels]
auto_connect = false
config_file = "./config/channels.yaml"
```

## 🤖 本地AI模型配置

AgentBus支持多种本地AI模型，以下是详细配置指南：

### 1. Ollama配置（推荐）

```bash
# 1. 安装Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# 2. 启动Ollama服务
ollama serve

# 3. 下载模型
ollama pull llama2
ollama pull codellama
ollama pull mistral
ollama pull phi

# 4. 配置AgentBus
```

```toml
# config/models.toml
[models.local]
provider = "ollama"
base_url = "http://localhost:11434"
timeout = 120

[models.local.models]
llama2 = { model = "llama2:7b", context_length = 4096 }
codellama = { model = "codellama:7b", context_length = 16384 }
mistral = { model = "mistral:7b", context_length = 32768 }
phi = { model = "phi:2.7b", context_length = 2048 }

[models.local.default]
model = "llama2:7b"
temperature = 0.7
max_tokens = 2048
```

### 2. vLLM配置

```bash
# 1. 安装vLLM
pip install vllm

# 2. 启动vLLM服务器
python -m vllm.entrypoints.openai.api_server \
    --model microsoft/DialoGPT-medium \
    --host 0.0.0.0 \
    --port 8001

# 3. 配置AgentBus
```

```toml
[models.vllm]
provider = "vllm"
base_url = "http://localhost:8001/v1"
api_key = "sk-vllm"  # 虚拟API key

[models.vllm.models]
gpt = { model = "microsoft/DialoGPT-medium" }
```

### 3. LM Studio配置

```bash
# 1. 下载并启动LM Studio
# 2. 加载本地模型
# 3. 启动本地API服务器（默认端口1234）
```

```toml
[models.lmstudio]
provider = "openai"
base_url = "http://localhost:1234/v1"
api_key = "sk-lmstudio"

[models.lmstudio.models]
local = { model = "local-model" }
```

### 4. GPT4All配置

```bash
# 1. 安装GPT4All
pip install gpt4all

# 2. 下载模型
from gpt4all import GPT4All
GPT4All.download_model('ggml-model-gpt4all-falcon.bin')

# 3. 配置AgentBus
```

```python
# config/gpt4all_config.py
from agentbus.integrations.gpt4all import GPT4AllModel

config = {
    'model_path': './models/ggml-model-gpt4all-falcon.bin',
    'device': 'cpu',  # 或 'cuda'
    'n_threads': 4,
    'n_ctx': 2048,
    'temperature': 0.7,
    'max_tokens': 512
}

model = GPT4AllModel(config)
```

### 5. Hugging Face Transformers配置

```python
# config/hf_config.py
from agentbus.integrations.huggingface import HFModel

config = {
    'model_name': 'microsoft/DialoGPT-medium',
    'device': 'auto',  # 自动检测GPU
    'torch_dtype': 'auto',
    'trust_remote_code': True,
    'load_in_8bit': False,
    'load_in_4bit': False
}

model = HFModel(config)
```

### 6. 完整的本地模型配置示例

```toml
# config/local_models.toml
[models]
default_provider = "ollama"

[models.ollama]
provider = "ollama"
base_url = "http://localhost:11434"
timeout = 300

[models.ollama.models]
codellama = { 
    model = "codellama:7b", 
    context_length = 16384,
    temperature = 0.1,
    top_p = 0.9
}
llama2 = { 
    model = "llama2:7b", 
    context_length = 4096,
    temperature = 0.7
}
mistral = { 
    model = "mistral:7b", 
    context_length = 32768,
    temperature = 0.8
}

[models.fallback]
provider = "huggingface"
model_name = "microsoft/DialoGPT-medium"
device = "cpu"
```

### 模型选择建议

| 需求 | 推荐模型 | 配置要点 |
|------|----------|----------|
| 代码生成 | CodeLlama, StarCoder | 高温度，短上下文 |
| 对话系统 | Llama2, Mistral | 中等温度，长上下文 |
| 文本总结 | T5, BART | 低温度，适中上下文 |
| 创意写作 | GPT-NeoX, PaLM | 高温度，长上下文 |
| 资源受限 | Phi, Qwen | 小模型，CPU运行 |

## 🔧 高级配置

### 插件系统配置

```toml
[plugins]
auto_load = true
auto_activate = true
directories = [
    "./plugins/official",
    "./plugins/custom",
    "/usr/local/share/agentbus/plugins"
]

[plugins.github]
enabled = true
api_token = "${GITHUB_TOKEN}"
rate_limit = 5000

[plugins.browser]
enabled = true
headless = false
timeout = 30000
```

### 渠道系统配置

```yaml
# config/channels.yaml
channels:
  telegram:
    enabled: true
    bot_token: "${TELEGRAM_BOT_TOKEN}"
    webhook_url: "${TELEGRAM_WEBHOOK_URL}"
    
  discord:
    enabled: true
    bot_token: "${DISCORD_BOT_TOKEN}"
    application_id: "${DISCORD_APP_ID}"
    
  slack:
    enabled: true
    bot_token: "${SLACK_BOT_TOKEN}"
    signing_secret = "${SLACK_SIGNING_SECRET}"
```

### 记忆系统配置

```toml
[memory]
enabled = true
backend = "hybrid"  # hybrid, sqlite, redis, lancedb

[memory.hybrid]
vector_backend = "lancedb"
text_backend = "sqlite"
relevance_threshold = 0.7

[memory.sqlite]
database_url = "sqlite:///./data/memory.db"
max_entries = 100000

[memory.lancedb]
persist_directory = "./data/vector_db"
collection_name = "agentbus_memory"
```

## 🔍 监控和日志

### 日志配置

```toml
[logging]
level = "info"
format = "json"
file = "logs/agentbus.log"
max_size = "100MB"
backup_count = 5

[logging.console]
enabled = true
format = "text"
level = "info"

[logging.remote]
enabled = false
endpoint = "http://localhost:9000"
api_key = "${LOG_API_KEY}"
```

### 监控配置

```toml
[monitoring]
enabled = true
metrics_port = 9090

[monitoring.health]
endpoint = "/health"
interval = 30

[monitoring.prometheus]
enabled = true
endpoint = "/metrics"
```

## 🛠️ 故障排除

### 常见问题

1. **端口被占用**
```bash
# 查找占用进程
lsof -i :8000

# 杀死进程
kill -9 <PID>
```

2. **权限问题**
```bash
# 创建专用用户
sudo useradd -r -s /bin/false agentbus
sudo chown -R agentbus:agentbus /opt/agentbus
```

3. **依赖问题**
```bash
# 重新安装依赖
pip install --force-reinstall -r requirements.txt
```

4. **配置问题**
```bash
# 验证配置
python -c "from agentbus.config.settings import validate_config; validate_config()"
```

### 调试模式

```bash
# 启用调试日志
export LOG_LEVEL=debug

# 启用详细错误信息
export DEBUG=true

# 启用热重载
python -m agentbus.core.app --mode dev --reload
```

## 📊 性能优化

### 生产环境优化

1. **使用Gunicorn + Uvicorn**
```bash
pip install gunicorn uvicorn

gunicorn agentbus.core.app:create_app \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 300
```

2. **数据库优化**
```sql
-- SQLite优化
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = memory;
```

3. **内存优化**
```toml
[performance]
max_memory_usage = "2GB"
gc_threshold = 700
connection_pool_size = 20
```

## 🔐 安全配置

### 安全最佳实践

1. **使用HTTPS**
```bash
# 使用Let's Encrypt
certbot --nginx -d your-domain.com

# 配置反向代理
location / {
    proxy_pass http://localhost:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

2. **防火墙配置**
```bash
# Ubuntu/Debian
sudo ufw allow 8000/tcp
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

3. **API密钥管理**
```bash
# 使用密钥管理服务
export OPENAI_API_KEY="$(vault kv get -field=api_key secret/agentbus/openai)"
export ANTHROPIC_API_KEY="$(vault kv get -field=api_key secret/agentbus/anthropic)"
```

## 🚀 升级和备份

### 版本升级

```bash
# 备份数据
cp -r ./data ./data.backup.$(date +%Y%m%d)

# 升级代码
git pull origin main

# 升级依赖
pip install --upgrade -r requirements.txt

# 运行数据库迁移
python -m agentbus.migrations.upgrade
```

### 备份策略

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/agentbus"

# 备份数据
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/data_$DATE.tar.gz ./data

# 备份配置
tar -czf $BACKUP_DIR/config_$DATE.tar.gz ./config

# 备份工作空间
tar -czf $BACKUP_DIR/workspace_$DATE.tar.gz ./workspace

# 清理旧备份（保留30天）
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

## 📞 支持和帮助

### 获取帮助

- **文档**: [项目文档链接]
- **Issues**: [GitHub Issues链接]
- **讨论**: [GitHub Discussions链接]
- **社区**: [Discord/微信群链接]

### 联系信息

- **邮箱**: support@agentbus.com
- **网站**: https://agentbus.com
- **GitHub**: https://github.com/agentbus/agentbus

---

**最后更新**: 2026-01-29  
**版本**: 1.0.0  
**作者**: AgentBus Team