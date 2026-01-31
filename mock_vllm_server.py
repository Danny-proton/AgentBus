#!/usr/bin/env python3
"""
Mock vLLM/Ollama 服务器
用于测试 AgentBus 本地模型集成,无需真实安装 vLLM 或 Ollama
"""
import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="Mock vLLM Server", version="1.0.0")

# 模拟的模型列表
MOCK_MODELS = [
    "qwen3_32B",
    "tinyllama",
    "phi-2",
    "gemma-2b"
]

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    stream: Optional[bool] = False

class CompletionRequest(BaseModel):
    model: str
    prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    stream: Optional[bool] = False

# Mock 响应生成器
def generate_mock_response(prompt: str, model: str) -> str:
    """生成模拟的 AI 响应"""
    responses = {
        "你好": f"你好!我是 {model} 模型。很高兴为您服务!",
        "1+1": "1+1等于2。这是一个简单的数学问题。",
        "介绍": f"我是 {model},一个运行在本地的大语言模型。我可以帮助您完成各种任务,包括回答问题、编写代码、翻译文本等。",
        "default": f"[Mock {model}] 我收到了您的消息: {prompt[:50]}... 这是一个模拟响应,用于测试本地模型集成。"
    }
    
    # 简单的关键词匹配
    for key, response in responses.items():
        if key in prompt.lower():
            return response
    
    return responses["default"]

async def stream_response(text: str):
    """流式返回响应"""
    words = text.split()
    for i, word in enumerate(words):
        chunk = {
            "id": f"chatcmpl-mock-{i}",
            "object": "chat.completion.chunk",
            "created": int(datetime.now().timestamp()),
            "model": "mock-model",
            "choices": [{
                "index": 0,
                "delta": {"content": word + " "},
                "finish_reason": None if i < len(words) - 1 else "stop"
            }]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0.05)  # 模拟生成延迟
    
    yield "data: [DONE]\n\n"

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Mock vLLM/Ollama Server",
        "status": "running",
        "models": MOCK_MODELS
    }

@app.get("/v1/models")
async def list_models():
    """列出可用模型 (OpenAI 兼容)"""
    return {
        "object": "list",
        "data": [
            {
                "id": model,
                "object": "model",
                "created": int(datetime.now().timestamp()),
                "owned_by": "mock-vllm"
            }
            for model in MOCK_MODELS
        ]
    }

@app.get("/api/tags")
async def ollama_list_models():
    """列出可用模型 (Ollama 兼容)"""
    return {
        "models": [
            {
                "name": model,
                "modified_at": datetime.now().isoformat(),
                "size": 1000000000,  # 1GB
                "digest": "mock-digest",
                "details": {
                    "format": "gguf",
                    "family": "llama",
                    "parameter_size": "7B"
                }
            }
            for model in MOCK_MODELS
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """聊天补全 (OpenAI 兼容)"""
    # 获取最后一条用户消息
    user_message = next(
        (msg.content for msg in reversed(request.messages) if msg.role == "user"),
        "Hello"
    )
    
    response_text = generate_mock_response(user_message, request.model)
    
    if request.stream:
        return StreamingResponse(
            stream_response(response_text),
            media_type="text/event-stream"
        )
    
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": request.model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response_text
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": len(user_message.split()),
            "completion_tokens": len(response_text.split()),
            "total_tokens": len(user_message.split()) + len(response_text.split())
        }
    }

@app.post("/v1/completions")
async def completions(request: CompletionRequest):
    """文本补全 (OpenAI 兼容)"""
    response_text = generate_mock_response(request.prompt, request.model)
    
    if request.stream:
        return StreamingResponse(
            stream_response(response_text),
            media_type="text/event-stream"
        )
    
    return {
        "id": "cmpl-mock",
        "object": "text_completion",
        "created": int(datetime.now().timestamp()),
        "model": request.model,
        "choices": [{
            "text": response_text,
            "index": 0,
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": len(request.prompt.split()),
            "completion_tokens": len(response_text.split()),
            "total_tokens": len(request.prompt.split()) + len(response_text.split())
        }
    }

@app.post("/api/generate")
async def ollama_generate(request: Request):
    """生成响应 (Ollama 兼容)"""
    data = await request.json()
    model = data.get("model", "tinyllama")
    prompt = data.get("prompt", "")
    stream = data.get("stream", False)
    
    response_text = generate_mock_response(prompt, model)
    
    if stream:
        async def ollama_stream():
            words = response_text.split()
            for word in words:
                chunk = {
                    "model": model,
                    "created_at": datetime.now().isoformat(),
                    "response": word + " ",
                    "done": False
                }
                yield json.dumps(chunk) + "\n"
                await asyncio.sleep(0.05)
            
            final = {
                "model": model,
                "created_at": datetime.now().isoformat(),
                "response": "",
                "done": True,
                "total_duration": 1000000000,
                "load_duration": 100000000,
                "prompt_eval_count": len(prompt.split()),
                "eval_count": len(response_text.split())
            }
            yield json.dumps(final) + "\n"
        
        return StreamingResponse(ollama_stream(), media_type="application/x-ndjson")
    
    return {
        "model": model,
        "created_at": datetime.now().isoformat(),
        "response": response_text,
        "done": True,
        "total_duration": 1000000000,
        "load_duration": 100000000,
        "prompt_eval_count": len(prompt.split()),
        "eval_count": len(response_text.split())
    }

@app.post("/api/chat")
async def ollama_chat(request: Request):
    """聊天 (Ollama 兼容)"""
    data = await request.json()
    model = data.get("model", "tinyllama")
    messages = data.get("messages", [])
    stream = data.get("stream", False)
    
    user_message = next(
        (msg["content"] for msg in reversed(messages) if msg["role"] == "user"),
        "Hello"
    )
    
    response_text = generate_mock_response(user_message, model)
    
    if stream:
        async def ollama_chat_stream():
            words = response_text.split()
            for word in words:
                chunk = {
                    "model": model,
                    "created_at": datetime.now().isoformat(),
                    "message": {
                        "role": "assistant",
                        "content": word + " "
                    },
                    "done": False
                }
                yield json.dumps(chunk) + "\n"
                await asyncio.sleep(0.05)
            
            final = {
                "model": model,
                "created_at": datetime.now().isoformat(),
                "message": {
                    "role": "assistant",
                    "content": ""
                },
                "done": True
            }
            yield json.dumps(final) + "\n"
        
        return StreamingResponse(ollama_chat_stream(), media_type="application/x-ndjson")
    
    return {
        "model": model,
        "created_at": datetime.now().isoformat(),
        "message": {
            "role": "assistant",
            "content": response_text
        },
        "done": True
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "mock-vllm",
        "models_loaded": len(MOCK_MODELS)
    }

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Mock vLLM/Ollama 服务器启动中...")
    print("=" * 60)
    print()
    print("📍 服务地址:")
    print("   - OpenAI 兼容: http://localhost:8030/v1/chat/completions")
    print("   - Ollama 兼容: http://localhost:11434/api/generate")
    print()
    print("📋 可用模型:")
    for model in MOCK_MODELS:
        print(f"   - {model}")
    print()
    print("🧪 测试命令:")
    print("   curl http://localhost:8030/v1/models")
    print("   curl http://localhost:11434/api/tags")
    print()
    print("=" * 60)
    
    # 同时在两个端口启动
    import threading
    
    def run_vllm():
        uvicorn.run(app, host="0.0.0.0", port=8030, log_level="info")
    
    def run_ollama():
        uvicorn.run(app, host="0.0.0.0", port=11434, log_level="info")
    
    # 启动 vLLM 端口
    vllm_thread = threading.Thread(target=run_vllm, daemon=True)
    vllm_thread.start()
    
    # 主线程运行 Ollama 端口
    try:
        run_ollama()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
