# AgentBus Python 重构版文档

本项目（原 Kode-cli）已重构为基于 Python (FastAPI) 的后端服务，并配备了一个现代化的 Web 前端。

## 架构概览

本项目不再是一个 Node.js CLI 工具，而是一个 Client-Server 架构的应用程序：

1.  **后端 (Python/FastAPI)**:
    *   位于 `app/` 目录。
    *   处理 LLM 交互 (使用 `openai` Python SDK)。
    *   **核心特性**: 支持 OpenAI Function Calling (Tool Use)，Agent 可自主决策执行 Bash 命令。
    *   管理会话状态 (`Session`) 和文件系统上下文。
    *   提供 Bash 执行能力 (`BashTool`)。
    *   `POST /chat` 接口通过 SSE (Server-Sent Events) 流式传输响应。

2.  **前端 (HTML/JS)**:
    *   位于 `static/` 目录。
    *   采用 **分屏设计** (类似 Manus/MiniMax)：
        *   **左侧**: 聊天窗口，用于与 AgentBus 对话。
        *   **右侧**: 虚拟机/终端窗口，显示命令执行结果 (`stdout`/`stderr`)。

## 快速开始

### 1. 环境准备

确保已安装 Python 3.8+。

安装依赖：
```bash
pip install -r requirements.txt
```

### 2. 配置

设置 OpenAI API Key (在环境变量中或 `.env` 文件)：
```bash
export OPENAI_API_KEY="your-api-key"
# Windows PowerShell:
# $env:OPENAI_API_KEY="your-api-key"
```

### 3. 运行服务

启动 FastAPI 服务器：
```bash
uvicorn app.main:app --reload
```
服务将在 `http://localhost:8000` 启动。

### 4. 使用说明

打开浏览器访问 `http://localhost:8000`。

*   **聊天模式**: 在左侧输入框输入自然语言，AgentBus 会回答。
*   **Bash 模式**:
    *   在输入框上方的下拉菜单选择 "Bash (!)"。
    *   或者直接以 `! ` 开头输入命令（例如 `! ls -la`）。
    *   命令的执行结果将显示在**右侧终端窗口**中，而不会干扰左侧的对话流。
*   **文件上传**: 点击回形针图标模拟上传文件（会生成一个 `file://` URL 注入到对话中）。

## 开发指南

*   **API 路由**: `app/api/router.py`
*   **核心逻辑**: `app/core/agent.py` (包含对话循环和工具调用逻辑)
*   **工具实现**: `app/tools/bash.py` (包含本地 Shell 执行器)
*   **前端逻辑**: `static/app.js` (包含 SSE 解析和分屏路由逻辑)
*   **测试**: 运行 `pytest` 执行单元测试和集成测试。

## 项目文件结构说明

本次重构新增的核心文件如下：

### 后端 (Python/FastAPI)
*   **`app/main.py`**: 应用程序入口，配置 FastAPI 和静态文件服务。
*   **`app/api/router.py`**: 定义 API 路由 (`/session`, `/chat`)，处理 HTTP 请求。
*   **`app/core/agent.py`**: 核心 Agent 逻辑，负责协调 LLM 和工具调用，处理消息流。
*   **`app/core/session.py`**: 会话管理，维护内存中的对话历史和当前工作目录 (CWD)。
*   **`app/tools/bash.py`**: Bash 工具实现，包含 `LocalShellExecutor` 用于执行本地命令。
*   **`app/tools/base.py`**: 工具抽象基类。
*   **`app/services/llm.py`**: OpenAI Python SDK 的封装服务。
*   **`app/constants/prompts.py`**: 系统提示词定义。

### 前端 (Static Web)
*   **`static/index.html`**: 单页应用入口，定义了分屏布局结构。
*   **`static/style.css`**: 全局样式表，实现了 Dark Mode 和终端风格界面。
*   **`static/app.js`**: 前端核心逻辑，处理 API 通信、SSE 消息流解析和分屏路由。

### 其他
*   **`tests/`**: 包含 `test_tools.py` 和 `test_api.py` 单元/集成测试。
*   **`requirements.txt`**: Python 依赖列表。

