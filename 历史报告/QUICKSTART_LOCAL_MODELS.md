---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 304402206ee9fe24f6886238aab794da922783611185daafe26068bf3a42dd573e5297910220088977dfd255d9c2a98563626cf1935266721500ebc84a6260f16717fd0704ed
    ReservedCode2: 304502203995bfa021231c68d6602741b8a99d74a9d419655dce9bffe85b8680a6271c74022100edb911ecefe83f5784290259855d8306effad78c41067a01ccdd400d6d0dad8e
---

# AgentBus 本地模型配置快速开始 - 2026年1月更新
## 行业解决方案集成与验证部（行解）出品

## 🎉 重大更新 (2026-01-29)

### ✨ 新增功能
1. **vLLM OpenAI格式完整支持** - 新增一个完整的vLLM章节（200+行）
2. **2024-2025最新模型支持** - 添加Qwen2.5、Llama3.1、Phi3等最新模型
3. **完整测试套件** - 提供Ollama、vLLM、性能对比测试脚本
4. **智能选择指南** - 根据不同需求自动推荐最佳配置

### 🔧 优化改进
- 增强vLLM配置说明，支持多GPU和性能优化
- 添加详细的OpenAI兼容API配置示例
- 完善故障排除和监控指南
- 优化文档结构，添加快速导航表

### 📈 文档规模
- **总行数**: 1010行（新增350+行）
- **vLLM章节**: 200+行完整指南
- **测试脚本**: 150+行代码示例
- **配置示例**: 50+个完整配置

## 🚀 5分钟快速配置本地AI模型

### 推荐方案：Ollama（最简单）

#### 1. 安装Ollama
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows (使用WSL或直接下载安装包)
# 下载地址: https://ollama.ai/download
```

#### 2. 启动Ollama服务
```bash
# 后台运行Ollama服务
ollama serve &

# 或者前台运行
ollama serve
```

#### 3. 下载推荐的模型
```bash
# 代码生成模型（推荐）
ollama pull codellama:7b

# 对话模型
ollama pull llama2:7b

# 轻量级模型（适合低配置）
ollama pull phi:2.7b

# 中文模型
ollama pull qwen:7b
ollama pull qwen2.5:7b    # Qwen2.5最新版本
ollama pull baichuan:7b   # 百川7B
ollama pull chatglm3:6b   # ChatGLM3

# 查看已安装的模型
ollama list
```

#### 4. 测试模型
```bash
# 测试代码生成
ollama run codellama:7b "写一个Python的Hello World程序"

# 测试对话
ollama run llama2:7b "你好，请介绍一下自己"
```

#### 5. 配置AgentBus
创建配置文件 `config/local_models.toml`：

```toml
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
    top_p = 0.9,
    description = "代码生成专用模型"
}
llama2 = { 
    model = "llama2:7b", 
    context_length = 4096,
    temperature = 0.7,
    description = "通用对话模型"
}
phi = { 
    model = "phi:2.7b", 
    context_length = 2048,
    temperature = 0.8,
    description = "轻量级模型，适合低配置"
}
```

## 🛠️ 其他本地模型方案

### 方案2：LM Studio（图形界面）

#### 安装和设置
```bash
# 1. 下载LM Studio
# https://lmstudio.ai/

# 2. 打开LM Studio
# 3. 点击"Discover"搜索模型
# 4. 下载推荐模型：
#    - Llama 2 7B Chat
#    - Code Llama 7B
#    - Mistral 7B

# 5. 在本地服务器中启动API服务
#    默认端口：1234
```

#### 配置AgentBus
```toml
[models.lmstudio]
provider = "openai"
base_url = "http://localhost:1234/v1"
api_key = "sk-lmstudio"  # 任意字符串

[models.lmstudio.models]
local_llama = { model = "local-model" }
```

### 方案3：GPT4All（完全离线）

#### 安装
```bash
# Python包
pip install gpt4all

# 图形界面（可选）
# 下载地址: https://gpt4all.io/
```

#### 下载模型
```python
from gpt4all import GPT4All

# 下载模型（首次运行）
model = GPT4All("ggml-model-gpt4all-falcon.bin")
```

#### 配置
```python
# config/gpt4all_config.py
from agentbus.integrations.gpt4all import GPT4AllModel

config = {
    'model_path': './models/ggml-model-gpt4all-falcon.bin',
    'device': 'cpu',  # 使用CPU，'cuda'使用GPU
    'n_threads': 4,   # CPU线程数
    'n_ctx': 2048,   # 上下文长度
    'temperature': 0.7,
    'max_tokens': 512
}

model = GPT4AllModel(config)
```

### 方案4：vLLM（高性能 + OpenAI兼容）

#### vLLM简介
vLLM是一个高性能的LLM推理服务引擎，提供OpenAI兼容的API接口，支持张量并行、批处理推理等高级功能。非常适合生产环境的本地模型部署。

#### 安装要求
```bash
# Python 3.8+
# CUDA 12.1+ (推荐) 或 CPU模式

# 安装vLLM
pip install vllm

# 如果使用GPU，安装CUDA版本
# pip install vllm[cu121]  # CUDA 12.1
# pip install vllm[cu118]  # CUDA 11.8
```

#### 启动vLLM服务器（OpenAI兼容格式）

**基本启动命令：**
```bash
# 启动OpenAI兼容服务器
python -m vllm.entrypoints.openai.api_server \
    --model microsoft/DialoGPT-medium \
    --host 0.0.0.0 \
    --port 8001 \
    --tensor-parallel-size 1 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.8
```

**高级配置启动：**
```bash
# 多GPU张量并行
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf \
    --host 0.0.0.0 \
    --port 8001 \
    --tensor-parallel-size 2 \
    --max-model-len 4096 \
    --max-num-seqs 32 \
    --max-num-batched-tokens 8192 \
    --gpu-memory-utilization 0.9 \
    --served-model-name "llama2-7b-chat" \
    --response-role role \
    --disable-log-stats

# CPU模式（无GPU）
python -m vllm.entrypoints.openai.api_server \
    --model microsoft/DialoGPT-medium \
    --host 0.0.0.0 \
    --port 8001 \
    --tensor-parallel-size 1 \
    --device cpu
```

#### 支持的模型类型

**推荐的代码生成模型：**
```bash
# Code Llama系列
--model codellama/CodeLlama-7b-Instruct-hf
--model codellama/CodeLlama-13b-Instruct-hf

# DeepSeek Coder
--model deepseek-ai/deepseek-coder-6.7b-instruct

# StarCoder
--model bigcode/starcoder2-7b
```

**对话模型：**
```bash
# Llama 2系列
--model meta-llama/Llama-2-7b-chat-hf
--model meta-llama/Llama-2-13b-chat-hf

# Mistral系列
--model mistralai/Mistral-7B-Instruct-v0.1
--model mistralai/Mistral-7B-Instruct-v0.2

# Qwen系列
--model Qwen/Qwen2.5-7B-Instruct
--model Qwen/Qwen2.5-14B-Instruct
```

**中文优化模型：**
```bash
# ChatGLM系列
--model THUDM/chatglm3-6b

# Baichuan系列
--model baichuan-inc/Baichuan2-7B-Chat

# InternLM系列
--model internlm/internlm2-chat-7b
```

#### AgentBus配置（OpenAI兼容）

```toml
[models.vllm_openai]
provider = "openai"
base_url = "http://localhost:8001/v1"
api_key = "sk-vllm-local"
timeout = 300
max_retries = 3

[models.vllm_openai.models]
# 通用对话模型
llama2_chat = { 
    model = "llama2-7b-chat", 
    context_length = 4096,
    temperature = 0.7,
    max_tokens = 2048,
    top_p = 0.9,
    description = "Llama 2 7B聊天模型"
}

# 代码生成模型
codellama = { 
    model = "codellama-7b-instruct", 
    context_length = 16384,
    temperature = 0.1,
    max_tokens = 2048,
    top_p = 0.9,
    description = "代码生成专用模型"
}

# 中文对话模型
qwen_chat = { 
    model = "qwen2.5-7b-instruct", 
    context_length = 32768,
    temperature = 0.7,
    max_tokens = 2048,
    description = "中文优化对话模型"
}

# 轻量级模型
mistral_small = { 
    model = "mistral-7b-instruct-v0.1", 
    context_length = 4096,
    temperature = 0.8,
    max_tokens = 1024,
    description = "轻量级对话模型"
}
```

#### 测试vLLM服务

**1. 健康检查：**
```bash
curl http://localhost:8001/v1/models

# 预期响应：
{
  "object": "list",
  "data": [
    {
      "id": "llama2-7b-chat",
      "object": "model",
      "created": 1677610602,
      "owned_by": "vllm"
    }
  ]
}
```

**2. 聊天完成测试：**
```bash
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2-7b-chat",
    "messages": [
      {"role": "user", "content": "写一个Python的Hello World程序"}
    ],
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

**3. 流式响应测试：**
```bash
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2-7b-chat",
    "messages": [
      {"role": "user", "content": "解释一下什么是人工智能"}
    ],
    "stream": true
  }'
```

#### 性能优化配置

**GPU内存优化：**
```bash
# 设置GPU内存使用率
--gpu-memory-utilization 0.8  # 使用80%的GPU内存

# 限制最大序列数
--max-num-seqs 32  # 最大并发序列数

# 限制批处理大小
--max-num-batched-tokens 8192  # 最大批处理token数
```

**多GPU配置：**
```bash
# 4卡配置示例
--tensor-parallel-size 4 \
--pipeline-parallel-size 1 \
--ray-workers-per-node 4
```

**推理参数优化：**
```bash
# 针对代码生成优化
--max-model-len 16384 \
--enable-chunked-prefill \
--max-num-batched-tokens 8192 \
--swap-space 16
```

#### 与其他模型平台对比

| 特性 | vLLM | Ollama | LM Studio |
|------|------|--------|-----------|
| **OpenAI兼容API** | ✅ | ❌ | ✅ |
| **张量并行** | ✅ | ❌ | ❌ |
| **批处理推理** | ✅ | ❌ | ❌ |
| **KV缓存优化** | ✅ | ❌ | ❌ |
| **安装复杂度** | 中等 | 简单 | 简单 |
| **GPU优化** | 优秀 | 一般 | 一般 |
| **模型切换** | 热重载 | 需重启 | 需重启 |

#### 常见问题解决

**1. CUDA版本不匹配：**
```bash
# 检查CUDA版本
nvcc --version

# 安装对应版本的vLLM
pip install vllm[cu121]  # 如果CUDA 12.1
```

**2. GPU内存不足：**
```bash
# 使用CPU模式
--device cpu

# 降低内存使用率
--gpu-memory-utilization 0.5

# 使用量化模型
--model meta-llama/Llama-2-7b-chat-hf
# 使用4bit量化模型：--model TheBloke/Llama-2-7B-Chat-GPTQ
```

**3. 模型加载失败：**
```bash
# 检查模型名称是否正确
curl http://localhost:8001/v1/models

# 下载到本地缓存
export HF_HOME=/path/to/cache
huggingface-cli download meta-llama/Llama-2-7b-chat-hf
```

#### 监控和管理

**1. 性能监控：**
```bash
# 查看vLLM进程
ps aux | grep vllm

# 监控GPU使用
nvidia-smi -l 1

# 查看服务日志
tail -f /var/log/vllm.log
```

**2. 负载测试：**
```bash
# 使用ab进行压力测试
ab -n 100 -c 10 -H "Content-Type: application/json" \
   -p test_data.json http://localhost:8001/v1/chat/completions
```

#### 最佳实践建议

1. **生产环境配置：**
   - 使用systemd或docker运行vLLM服务
   - 配置负载均衡和健康检查
   - 设置适当的超时和重试机制

2. **模型选择策略：**
   - 开发环境：使用较小的7B模型
   - 生产环境：根据硬件配置选择合适的模型大小
   - 批处理：优先选择支持批处理的模型

3. **监控要点：**
   - GPU利用率和内存使用
   - API响应时间和吞吐量
   - 错误率和系统资源使用

vLLM提供了最佳的OpenAI兼容性和生产级性能，特别适合需要高并发和低延迟的应用场景。

## 🎯 不同需求的模型推荐

### 代码生成和编程助手
```bash
# 推荐模型（按性能排序）
ollama pull codellama:7b      # 最佳代码能力
ollama pull starcoder:7b      # StarCoder模型
ollama pull deepseek-coder:6.7b  # 专门针对代码
```

### 对话和聊天
```bash
# 推荐模型
ollama pull llama2:7b         # Meta Llama2
ollama pull mistral:7b        # Mistral 7B
ollama pull qwen:7b          # 通义千问
```

### 中文支持
```bash
# 中文优化模型
ollama pull qwen:7b           # 通义千钱7B
ollama pull baichuan:7b       # 百川7B
ollama pull chatglm3:6b       # ChatGLM3
```

### 低配置设备
```bash
# 轻量级模型（适合CPU）
ollama pull phi:2.7b         # Microsoft Phi-2.7B
ollama pull gemma:2b          # Google Gemma 2B
ollama pull qwen:1.4b         # 通义千钱1.4B
```

### 特定任务
```bash
# 特定领域模型
ollama pull starcoder:7b     # 代码生成
ollama pull wizardlm:13b      # 数学和科学
ollama pull nous Hermes 2-Mixtral:8x7b  # 多任务模型

# 2024-2025 最新模型
ollama pull qwen2.5-coder:7b  # Qwen2.5代码专家
ollama pull deepseek-coder:6.7b # DeepSeek代码模型
ollama pull codestral:7b      # Mistral代码模型
ollama pull gemma2:9b         # Google Gemma2 9B
ollama pull phi3:medium       # Microsoft Phi-3 Medium
ollama pull llama3.1:8b       # Meta Llama 3.1 8B
ollama pull mistral-nemo:12b  # Mistral Nemo 12B
```

## ⚙️ 性能优化建议

### GPU配置（如果有GPU）
```bash
# 检查GPU是否可用
nvidia-smi

# 使用CUDA加速的模型
ollama pull llama2:13b-chat.Q4_0.gguf  # 大模型需要GPU
```

### CPU优化
```bash
# 设置环境变量优化CPU使用
export OMP_NUM_THREADS=8
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0

# 启动时指定CPU线程数
ollama run llama2:7b --threads 8
```

### 内存优化
```bash
# 监控内存使用
htop

# 使用量化模型（减少内存使用）
ollama pull llama2:7b.Q4_0.gguf  # 4位量化
ollama pull llama2:7b.Q8_0.gguf  # 8位量化
```

## 🔧 故障排除

### 常见问题

#### 1. 模型下载失败
```bash
# 检查网络连接
ping ollama.ai

# 使用代理（如果需要）
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port

# 手动下载模型
ollama pull codellama:7b --verbose
```

#### 2. 内存不足
```bash
# 查看内存使用
free -h

# 使用小模型
ollama pull phi:2.7b

# 设置模型参数减少内存使用
export OLLAMA_NUM_PARALLEL=1
```

#### 3. 启动失败
```bash
# 检查端口是否被占用
lsof -i :11434

# 清理Ollama缓存
ollama rm all
ollama prune

# 重新安装Ollama
curl -fsSL https://ollama.ai/install.sh | sh
```

#### 4. API连接失败
```bash
# 测试API连接
curl http://localhost:11434/api/tags

# 检查防火墙
sudo ufw status
```

### 调试命令
```bash
# 查看Ollama日志
journalctl -u ollama -f

# 查看模型信息
ollama list

# 测试特定模型
ollama run codellama:7b --verbose
```

## 📱 移动端和嵌入式

### Android设备
```bash
# Termux环境
pkg install ollama
ollama serve --host 0.0.0.0

# 小模型推荐
ollama pull phi:2.7b
```

### 树莓派
```bash
# ARM64优化
ollama pull llama2:7b.Q4_0.gguf

# 使用轻量级模型
ollama pull phi:2.7b
```

## 🔗 集成到AgentBus

### 完整配置文件示例

```toml
# config/production_models.toml
[models]
# 默认提供商
default_provider = "ollama"

# 模型超时设置
timeout = 300
max_retries = 3

[models.ollama]
provider = "ollama"
base_url = "http://localhost:11434"
timeout = 300

[models.ollama.models]
# 通用对话
llama2_chat = { 
    model = "llama2:7b-chat", 
    context_length = 4096,
    temperature = 0.7,
    max_tokens = 2048,
    description = "通用对话模型"
}

# 代码生成
codellama = { 
    model = "codellama:7b", 
    context_length = 16384,
    temperature = 0.1,
    top_p = 0.9,
    max_tokens = 2048,
    description = "代码生成专用模型"
}

# 轻量级（备用）
phi_small = { 
    model = "phi:2.7b", 
    context_length = 2048,
    temperature = 0.8,
    max_tokens = 512,
    description = "轻量级模型，资源受限环境"
}

# 中文支持
qwen = { 
    model = "qwen:7b", 
    context_length = 32768,
    temperature = 0.7,
    max_tokens = 2048,
    description = "中文优化模型"
}

[models.ollama.default]
model = "llama2:7b-chat"
temperature = 0.7
max_tokens = 2048

# API配置
[api]
rate_limit = 100  # 每分钟请求限制
request_timeout = 300  # 请求超时时间

# 监控配置
[monitoring]
enabled = true
metrics_endpoint = "/metrics"
health_endpoint = "/health"
```

## 🎉 测试配置

### 快速测试脚本

#### 1. Ollama测试脚本
```python
# test_local_models.py
import asyncio
from agentbus.integrations.ollama import OllamaModel

async def test_ollama():
    # 测试Ollama连接
    model = OllamaModel(base_url="http://localhost:11434")
    
    # 测试对话
    response = await model.chat(
        model="llama2:7b",
        messages=[{"role": "user", "content": "Hello! How are you?"}],
        temperature=0.7
    )
    
    print("Ollama模型响应:", response["choices"][0]["message"]["content"])

if __name__ == "__main__":
    asyncio.run(test_ollama())
```

#### 2. vLLM测试脚本（OpenAI兼容）
```python
# test_vllm_models.py
import asyncio
import openai
from openai import AsyncOpenAI

async def test_vllm():
    # 连接vLLM OpenAI兼容API
    client = AsyncOpenAI(
        base_url="http://localhost:8001/v1",
        api_key="sk-vllm-local"
    )
    
    # 测试聊天完成
    response = await client.chat.completions.create(
        model="llama2-7b-chat",
        messages=[
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": "写一个Python的Hello World程序"}
        ],
        temperature=0.7,
        max_tokens=100
    )
    
    print("vLLM模型响应:", response.choices[0].message.content)
    
    # 测试流式响应
    print("\n流式响应测试:")
    async for chunk in await client.chat.completions.create(
        model="llama2-7b-chat",
        messages=[{"role": "user", "content": "解释一下什么是人工智能"}],
        stream=True,
        temperature=0.7
    ):
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end="", flush=True)

if __name__ == "__main__":
    asyncio.run(test_vllm())
```

#### 3. 完整测试套件
```python
# test_all_models.py
import asyncio
import time
from agentbus.integrations.ollama import OllamaModel
from openai import AsyncOpenAI

class ModelTester:
    def __init__(self):
        self.ollama_model = OllamaModel(base_url="http://localhost:11434")
        self.vllm_client = AsyncOpenAI(
            base_url="http://localhost:8001/v1",
            api_key="sk-vllm-local"
        )
    
    async def test_ollama_models(self):
        """测试Ollama模型"""
        print("=== 测试Ollama模型 ===")
        
        models = ["llama2:7b", "codellama:7b", "phi:2.7b"]
        
        for model in models:
            try:
                start_time = time.time()
                response = await self.ollama_model.chat(
                    model=model,
                    messages=[{"role": "user", "content": "简短介绍一下自己"}],
                    temperature=0.7,
                    max_tokens=50
                )
                end_time = time.time()
                
                print(f"✅ {model}: {response['choices'][0]['message']['content'][:50]}...")
                print(f"   响应时间: {end_time - start_time:.2f}秒")
            except Exception as e:
                print(f"❌ {model}: {e}")
            print()
    
    async def test_vllm_models(self):
        """测试vLLM模型"""
        print("=== 测试vLLM模型 ===")
        
        models = ["llama2-7b-chat", "codellama-7b-instruct", "mistral-7b-instruct-v0.1"]
        
        for model in models:
            try:
                start_time = time.time()
                response = await self.vllm_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "简短介绍一下自己"}],
                    temperature=0.7,
                    max_tokens=50
                )
                end_time = time.time()
                
                print(f"✅ {model}: {response.choices[0].message.content[:50]}...")
                print(f"   响应时间: {end_time - start_time:.2f}秒")
            except Exception as e:
                print(f"❌ {model}: {e}")
            print()
    
    async def test_performance(self):
        """性能测试"""
        print("=== 性能对比测试 ===")
        
        # 测试Ollama并发性能
        print("Ollama并发测试...")
        start_time = time.time()
        tasks = [
            self.ollama_model.chat(
                model="llama2:7b",
                messages=[{"role": "user", "content": f"回答第{i}个问题"}],
                temperature=0.7,
                max_tokens=20
            ) for i in range(5)
        ]
        await asyncio.gather(*tasks)
        ollama_time = time.time() - start_time
        print(f"Ollama 5个并发请求完成时间: {ollama_time:.2f}秒")
        
        # 测试vLLM并发性能
        print("vLLM并发测试...")
        start_time = time.time()
        tasks = [
            self.vllm_client.chat.completions.create(
                model="llama2-7b-chat",
                messages=[{"role": "user", "content": f"回答第{i}个问题"}],
                temperature=0.7,
                max_tokens=20
            ) for i in range(5)
        ]
        await asyncio.gather(*tasks)
        vllm_time = time.time() - start_time
        print(f"vLLM 5个并发请求完成时间: {vllm_time:.2f}秒")
        
        print(f"性能对比: vLLM比Ollama快 {((ollama_time - vllm_time) / ollama_time * 100):.1f}%")

async def main():
    tester = ModelTester()
    
    print("AgentBus 本地模型测试套件")
    print("=" * 50)
    
    # 检查服务状态
    print("检查服务状态...")
    try:
        await tester.test_ollama_models()
    except Exception as e:
        print(f"Ollama服务不可用: {e}")
    
    try:
        await tester.test_vllm_models()
    except Exception as e:
        print(f"vLLM服务不可用: {e}")
    
    # 性能对比（如果两个服务都可用）
    try:
        await tester.test_performance()
    except Exception as e:
        print(f"性能测试跳过: {e}")
    
    print("\n测试完成！")

if __name__ == "__main__":
    asyncio.run(main())
```

### 运行测试

```bash
# 测试Ollama模型
python test_local_models.py

# 测试vLLM模型
python test_vllm_models.py

# 运行完整测试套件
python test_all_models.py

# 预期输出示例：
# AgentBus 本地模型测试套件
# ==================================================
# 检查服务状态...
# === 测试Ollama模型 ===
# ✅ llama2:7b: Hello! I'm doing great, thank you for asking. How can I help you today? ...
#    响应时间: 2.34秒
# 
# ✅ codellama:7b: I'm an AI assistant designed to help with programming and coding tasks...
#    响应时间: 3.12秒
# 
# === 测试vLLM模型 ===
# ✅ llama2-7b-chat: Hello! I'm an AI assistant created by Meta. I'm here to help...
#    响应时间: 1.45秒
# 
# 性能对比: vLLM比Ollama快 38.1%
```

## 📚 更多资源

- [Ollama官方文档](https://ollama.ai/docs)
- [LM Studio文档](https://lmstudio.ai/docs)
- [Hugging Face模型库](https://huggingface.co/models)
- [GPT4All文档](https://docs.gpt4all.io/)
- [vLLM GitHub仓库](https://github.com/vllm-project/vllm)
- [vLLM官方文档](https://docs.vllm.ai/)

## 🎯 快速导航

| 需求 | 推荐方案 | 配置文件 | 快速命令 |
|------|----------|----------|----------|
| **最简单的本地模型** | Ollama | `config/ollama.toml` | `ollama serve` |
| **高性能生产环境** | vLLM (OpenAI格式) | `config/vllm.toml` | `python -m vllm.entrypoints.openai.api_server` |
| **图形界面管理** | LM Studio | `config/lmstudio.toml` | LM Studio GUI启动API |
| **完全离线** | GPT4All | `config/gpt4all.py` | Python API调用 |
| **代码生成专用** | Code Llama (vLLM) | `config/codellama.toml` | `--model codellama/CodeLlama-7b-Instruct-hf` |
| **中文优化** | Qwen (Ollama) | `config/qwen.toml` | `ollama pull qwen:7b` |
| **低配置设备** | Phi-2.7B (Ollama) | `config/phi.toml` | `ollama pull phi:2.7b` |

## 🏆 选择建议

### 开发环境推荐
- **首选**: Ollama + Llama2 7B（简单易用）
- **备选**: vLLM + Llama2 7B（性能更好）

### 生产环境推荐
- **首选**: vLLM + 优化模型（高性能、OpenAI兼容）
- **备选**: Ollama + 轻量级模型（稳定可靠）

### 团队协作推荐
- **首选**: vLLM（支持并发、多模型）
- **备选**: Ollama（简单部署、维护容易）

---

## ✅ 快速配置总结

### 方案1：Ollama（推荐新手）
1. 安装Ollama：`curl -fsSL https://ollama.ai/install.sh | sh`
2. 下载模型：`ollama pull codellama:7b`
3. 启动服务：`ollama serve`
4. 创建配置文件：`config/ollama.toml`
5. 测试连接：`python test_local_models.py`

### 方案2：vLLM（推荐生产）
1. 安装vLLM：`pip install vllm`
2. 启动服务：`python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-2-7b-chat-hf`
3. 创建配置文件：`config/vllm.toml`
4. 测试连接：`python test_vllm_models.py`

### 推荐模型配置
| 用途 | 模型 | 内存需求 | 特点 |
|------|------|----------|------|
| **代码生成** | `codellama:7b` | 8GB+ | 专业的代码理解能力 |
| **最新代码模型** | `qwen2.5-coder:7b` | 8GB+ | 2024年最新代码专家 |
| **通用对话** | `llama3.1:8b` | 8GB+ | Meta最新Llama 3.1 |
| **中文支持** | `qwen2.5:7b` | 8GB+ | 最新的中文理解模型 |
| **轻量级** | `phi3:medium` | 4GB+ | Microsoft最新轻量模型 |
| **高性能** | `llama3.1:70b` (vLLM) | 40GB+ | 顶级理解能力 |
| **多语言** | `mistral-nemo:12b` | 12GB+ | Mistral最新多语言模型 |

### 性能基准
| 平台 | 单请求响应时间 | 并发性能 | 内存使用 | 推荐场景 |
|------|---------------|----------|----------|----------|
| **Ollama** | 2-4秒 | 一般 | 4-8GB | 开发测试、简单部署 |
| **vLLM** | 1-2秒 | 优秀 | 6-12GB | 生产环境、高并发 |
| **LM Studio** | 3-5秒 | 一般 | 4-8GB | 图形化管理、小团队 |
| **GPT4All** | 5-10秒 | 差 | 2-4GB | 完全离线、极简需求 |

**最后更新**: 2026-01-29  
**版本**: v1.0 - 完整支持vLLM OpenAI格式