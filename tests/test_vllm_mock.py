#!/usr/bin/env python3
"""
vLLM Mock 服务器单元测试

测试 mock vLLM 服务器的所有 API 端点和功能
"""
import pytest
import json
import httpx
from typing import List, Dict, Any


class TestVLLMAPIEndpoints:
    """测试 vLLM API 端点"""
    
    def test_health_check(self, mock_vllm_server, vllm_base_url):
        """测试健康检查端点"""
        response = httpx.get(f"{vllm_base_url}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "mock-vllm"
        assert "models_loaded" in data
        assert data["models_loaded"] > 0
    
    def test_root_endpoint(self, mock_vllm_server, vllm_base_url):
        """测试根端点"""
        response = httpx.get(f"{vllm_base_url}/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "running"
        assert "models" in data
        assert len(data["models"]) > 0
    
    def test_list_models(self, mock_vllm_server, vllm_base_url):
        """测试列出模型端点"""
        response = httpx.get(f"{vllm_base_url}/v1/models")
        assert response.status_code == 200
        
        data = response.json()
        assert data["object"] == "list"
        assert "data" in data
        assert len(data["data"]) > 0
        
        # 验证模型格式
        model = data["data"][0]
        assert "id" in model
        assert "object" in model
        assert model["object"] == "model"
        assert "created" in model
        assert "owned_by" in model
        
        # 验证包含预期的模型
        model_ids = [m["id"] for m in data["data"]]
        assert "qwen3_32B" in model_ids


class TestChatCompletions:
    """测试聊天补全 API"""
    
    def test_chat_completion_non_streaming(self, mock_vllm_server, vllm_base_url):
        """测试非流式聊天补全"""
        response = httpx.post(
            f"{vllm_base_url}/v1/chat/completions",
            json={
                "model": "qwen3_32B",
                "messages": [
                    {"role": "user", "content": "你好,请介绍一下你自己"}
                ],
                "stream": False
            },
            timeout=10.0
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["object"] == "chat.completion"
        assert data["model"] == "qwen3_32B"
        assert "choices" in data
        assert len(data["choices"]) > 0
        
        choice = data["choices"][0]
        assert choice["index"] == 0
        assert "message" in choice
        assert choice["message"]["role"] == "assistant"
        assert len(choice["message"]["content"]) > 0
        assert choice["finish_reason"] == "stop"
        
        # 验证 usage 信息
        assert "usage" in data
        assert "prompt_tokens" in data["usage"]
        assert "completion_tokens" in data["usage"]
        assert "total_tokens" in data["usage"]
    
    def test_chat_completion_streaming(self, mock_vllm_server, vllm_base_url):
        """测试流式聊天补全"""
        with httpx.stream(
            "POST",
            f"{vllm_base_url}/v1/chat/completions",
            json={
                "model": "qwen3_32B",
                "messages": [
                    {"role": "user", "content": "1+1等于几?"}
                ],
                "stream": True
            },
            timeout=10.0
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
            
            chunks = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    
                    chunk = json.loads(data_str)
                    chunks.append(chunk)
                    
                    # 验证 chunk 格式
                    assert "id" in chunk
                    assert "object" in chunk
                    assert chunk["object"] == "chat.completion.chunk"
                    assert "choices" in chunk
                    assert len(chunk["choices"]) > 0
            
            assert len(chunks) > 0
            
            # 验证最后一个 chunk 有 finish_reason
            last_chunk = chunks[-1]
            assert last_chunk["choices"][0]["finish_reason"] == "stop"
    
    def test_chat_completion_with_different_models(self, mock_vllm_server, vllm_base_url):
        """测试不同模型的聊天补全"""
        models = ["qwen3_32B", "tinyllama", "phi-2"]
        
        for model in models:
            response = httpx.post(
                f"{vllm_base_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": "你好"}
                    ],
                    "stream": False
                },
                timeout=10.0
            )
            assert response.status_code == 200
            data = response.json()
            assert data["model"] == model
            assert model in data["choices"][0]["message"]["content"]
    
    def test_chat_completion_with_parameters(self, mock_vllm_server, vllm_base_url):
        """测试带参数的聊天补全"""
        response = httpx.post(
            f"{vllm_base_url}/v1/chat/completions",
            json={
                "model": "qwen3_32B",
                "messages": [
                    {"role": "user", "content": "测试"}
                ],
                "temperature": 0.5,
                "max_tokens": 100,
                "stream": False
            },
            timeout=10.0
        )
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data


class TestTextCompletions:
    """测试文本补全 API"""
    
    def test_text_completion_non_streaming(self, mock_vllm_server, vllm_base_url):
        """测试非流式文本补全"""
        response = httpx.post(
            f"{vllm_base_url}/v1/completions",
            json={
                "model": "qwen3_32B",
                "prompt": "你好,请介绍一下你自己",
                "stream": False
            },
            timeout=10.0
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["object"] == "text_completion"
        assert data["model"] == "qwen3_32B"
        assert "choices" in data
        assert len(data["choices"]) > 0
        
        choice = data["choices"][0]
        assert "text" in choice
        assert len(choice["text"]) > 0
        assert choice["finish_reason"] == "stop"
    
    def test_text_completion_streaming(self, mock_vllm_server, vllm_base_url):
        """测试流式文本补全"""
        with httpx.stream(
            "POST",
            f"{vllm_base_url}/v1/completions",
            json={
                "model": "qwen3_32B",
                "prompt": "1+1等于",
                "stream": True
            },
            timeout=10.0
        ) as response:
            assert response.status_code == 200
            
            chunks = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    chunks.append(json.loads(data_str))
            
            assert len(chunks) > 0


class TestResponseFormat:
    """测试响应格式"""
    
    def test_response_contains_required_fields(self, mock_vllm_server, vllm_base_url):
        """验证响应包含所有必需字段"""
        response = httpx.post(
            f"{vllm_base_url}/v1/chat/completions",
            json={
                "model": "qwen3_32B",
                "messages": [{"role": "user", "content": "测试"}],
                "stream": False
            },
            timeout=10.0
        )
        
        data = response.json()
        required_fields = ["id", "object", "created", "model", "choices", "usage"]
        for field in required_fields:
            assert field in data, f"缺少必需字段: {field}"
    
    def test_token_counting(self, mock_vllm_server, vllm_base_url):
        """验证 token 计数"""
        response = httpx.post(
            f"{vllm_base_url}/v1/chat/completions",
            json={
                "model": "qwen3_32B",
                "messages": [{"role": "user", "content": "你好 世界"}],
                "stream": False
            },
            timeout=10.0
        )
        
        data = response.json()
        usage = data["usage"]
        
        assert usage["prompt_tokens"] > 0
        assert usage["completion_tokens"] > 0
        assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]


class TestErrorHandling:
    """测试错误处理"""
    
    def test_malformed_request(self, mock_vllm_server, vllm_base_url):
        """测试格式错误的请求"""
        # 缺少必需字段
        response = httpx.post(
            f"{vllm_base_url}/v1/chat/completions",
            json={
                "model": "qwen3_32B"
                # 缺少 messages 字段
            },
            timeout=10.0
        )
        # FastAPI 会返回 422 验证错误
        assert response.status_code == 422
    
    def test_empty_messages(self, mock_vllm_server, vllm_base_url):
        """测试空消息列表"""
        response = httpx.post(
            f"{vllm_base_url}/v1/chat/completions",
            json={
                "model": "qwen3_32B",
                "messages": [],
                "stream": False
            },
            timeout=10.0
        )
        # 应该能处理空消息
        assert response.status_code in [200, 422]


class TestMockResponseGeneration:
    """测试 mock 响应生成"""
    
    def test_keyword_matching(self, mock_vllm_server, vllm_base_url):
        """测试关键词匹配响应"""
        test_cases = [
            ("你好", "你好"),
            ("1+1", "1+1等于2"),
            ("介绍", "大语言模型"),
        ]
        
        for prompt, expected_keyword in test_cases:
            response = httpx.post(
                f"{vllm_base_url}/v1/chat/completions",
                json={
                    "model": "qwen3_32B",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False
                },
                timeout=10.0
            )
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            assert expected_keyword in content, f"响应中未找到关键词 '{expected_keyword}': {content}"
    
    def test_default_response(self, mock_vllm_server, vllm_base_url):
        """测试默认响应"""
        response = httpx.post(
            f"{vllm_base_url}/v1/chat/completions",
            json={
                "model": "qwen3_32B",
                "messages": [{"role": "user", "content": "这是一个随机的测试消息"}],
                "stream": False
            },
            timeout=10.0
        )
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        assert "Mock" in content or "模拟" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
