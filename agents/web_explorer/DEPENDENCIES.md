# WebExplorer Agent - 依赖说明

## 核心依赖

WebExplorer Agent 使用的所有依赖都已包含在项目的 `requirements.txt` 中,无需额外安装。

### 必需依赖

| 依赖 | 版本 | 用途 | 状态 |
|------|------|------|------|
| `playwright` | >=1.41.0 | 浏览器自动化 | ✅ 已包含 |
| `aiohttp` | >=3.9.0 | 异步HTTP客户端 | ✅ 已包含 |
| `aiofiles` | >=23.2.0 | 异步文件操作 | ✅ 已包含 |
| `pydantic` | >=2.6.0 | 数据验证 | ✅ 已包含 |

### 可选依赖 (LLM集成)

| 依赖 | 版本 | 用途 | 状态 |
|------|------|------|------|
| `openai` | >=1.12.0 | OpenAI GPT模型 | ✅ 已包含 |
| `anthropic` | >=0.18.0 | Anthropic Claude | ✅ 已包含 |
| `google-generativeai` | >=0.3.0 | Google Gemini | ✅ 已包含 |
| `zhipuai` | >=2.0.0 | 智谱AI GLM | ✅ 已包含 |

## 安装步骤

### 1. 安装Python依赖

```bash
# 安装所有依赖
pip install -r requirements.txt

# 或者只安装核心依赖
pip install fastapi uvicorn playwright aiohttp aiofiles pydantic
```

### 2. 安装Playwright浏览器

```bash
# 安装Chromium浏览器
playwright install chromium

# 或安装所有浏览器
playwright install
```

### 3. 验证安装

```python
# 测试导入
from agents.web_explorer import WebExplorerAgent, ExplorerConfig
from plugins.web_explorer import AtlasManagerPlugin, BrowserManagerPlugin
from skills.web_explorer import PageAnalysisSkill, TrajectoryLabelingSkill

print("✅ WebExplorer Agent 依赖安装成功!")
```

## 开发依赖

如果需要进行开发和测试,还需要安装开发依赖:

```bash
# 测试工具
pip install pytest pytest-asyncio pytest-cov pytest-mock

# 代码质量工具(可选)
pip install black flake8 mypy isort
```

## 环境要求

- **Python**: >= 3.9
- **操作系统**: Windows / Linux / macOS
- **内存**: >= 4GB (推荐8GB)
- **磁盘空间**: >= 2GB (用于浏览器和Atlas存储)

## 特殊说明

### Windows用户

在Windows上创建软链接可能需要管理员权限。WebExplorer已实现JSON Fallback方案,即使无法创建软链接也能正常工作。

### 无头模式

如果在服务器环境运行,需要安装额外的系统依赖:

```bash
# Ubuntu/Debian
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2

# CentOS/RHEL
sudo yum install -y \
    nss \
    nspr \
    atk \
    at-spi2-atk \
    cups-libs \
    libdrm \
    libxkbcommon \
    libXcomposite \
    libXdamage \
    libXfixes \
    libXrandr \
    mesa-libgbm \
    alsa-lib
```

## LLM配置

### OpenAI

```bash
# 设置环境变量
export OPENAI_API_KEY="your-api-key"
```

### Anthropic Claude

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

### 本地LLM (Ollama)

```bash
# 安装Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 拉取模型
ollama pull qwen2.5:32b

# 启动服务
ollama serve
```

### 本地LLM (vLLM)

```bash
# 安装vLLM
pip install vllm

# 启动服务
python -m vllm.entrypoints.openai.api_server \
    --model Qwen/Qwen2.5-32B-Instruct \
    --port 8030
```

## 故障排除

### Playwright安装失败

```bash
# 手动下载浏览器
playwright install --with-deps chromium
```

### 导入错误

```bash
# 确保在项目根目录
cd /path/to/AgentBus
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

### 权限错误 (Windows软链接)

WebExplorer会自动使用JSON Fallback,无需特殊处理。

## 依赖更新

```bash
# 更新所有依赖到最新版本
pip install --upgrade -r requirements.txt

# 更新Playwright浏览器
playwright install --upgrade chromium
```

## 最小化安装

如果只想运行WebExplorer,可以只安装核心依赖:

```bash
pip install \
    fastapi \
    uvicorn \
    playwright \
    aiohttp \
    aiofiles \
    pydantic \
    pydantic-settings \
    loguru

playwright install chromium
```

---

**总结**: 所有依赖都已包含在项目的 `requirements.txt` 中,只需运行 `pip install -r requirements.txt` 和 `playwright install chromium` 即可开始使用WebExplorer Agent!
