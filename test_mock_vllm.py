#!/usr/bin/env python3
"""
测试 Mock vLLM 服务器
验证 AgentBus 本地模型集成
"""
import requests
import json

def test_vllm_api():
    """测试 vLLM 兼容 API"""
    print("=" * 60)
    print("🧪 测试 vLLM API (端口 8030)")
    print("=" * 60)
    
    base_url = "http://localhost:8030"
    
    # 1. 列出模型
    print("\n1️⃣ 列出可用模型:")
    try:
        response = requests.get(f"{base_url}/v1/models")
        models = response.json()
        print(f"   ✅ 找到 {len(models['data'])} 个模型:")
        for model in models['data']:
            print(f"      - {model['id']}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    # 2. 聊天补全 (非流式)
    print("\n2️⃣ 聊天补全 (非流式):")
    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json={
                "model": "qwen3_32B",
                "messages": [
                    {"role": "user", "content": "你好,请介绍一下你自己"}
                ],
                "stream": False
            }
        )
        result = response.json()
        print(f"   ✅ 响应: {result['choices'][0]['message']['content']}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    # 3. 聊天补全 (流式)
    print("\n3️⃣ 聊天补全 (流式):")
    try:
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json={
                "model": "qwen3_32B",
                "messages": [
                    {"role": "user", "content": "1+1等于几?"}
                ],
                "stream": True
            },
            stream=True
        )
        print("   ✅ 流式响应: ", end="")
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: ') and not line_str.endswith('[DONE]'):
                    data = json.loads(line_str[6:])
                    if 'choices' in data and len(data['choices']) > 0:
                        delta = data['choices'][0].get('delta', {})
                        if 'content' in delta:
                            print(delta['content'], end="", flush=True)
        print()
    except Exception as e:
        print(f"\n   ❌ 错误: {e}")

def test_ollama_api():
    """测试 Ollama 兼容 API"""
    print("\n" + "=" * 60)
    print("🧪 测试 Ollama API (端口 11434)")
    print("=" * 60)
    
    base_url = "http://localhost:11434"
    
    # 1. 列出模型
    print("\n1️⃣ 列出可用模型:")
    try:
        response = requests.get(f"{base_url}/api/tags")
        models = response.json()
        print(f"   ✅ 找到 {len(models['models'])} 个模型:")
        for model in models['models']:
            print(f"      - {model['name']}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    # 2. 生成响应 (非流式)
    print("\n2️⃣ 生成响应 (非流式):")
    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": "tinyllama",
                "prompt": "你好,请介绍一下你自己",
                "stream": False
            }
        )
        result = response.json()
        print(f"   ✅ 响应: {result['response']}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    # 3. 聊天 (非流式)
    print("\n3️⃣ 聊天 (非流式):")
    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": "phi-2",
                "messages": [
                    {"role": "user", "content": "1+1等于几?"}
                ],
                "stream": False
            }
        )
        result = response.json()
        print(f"   ✅ 响应: {result['message']['content']}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")

def test_health():
    """测试健康检查"""
    print("\n" + "=" * 60)
    print("🏥 健康检查")
    print("=" * 60)
    
    for port, name in [(8030, "vLLM"), (11434, "Ollama")]:
        try:
            response = requests.get(f"http://localhost:{port}/health")
            health = response.json()
            print(f"\n   ✅ {name} 端口 ({port}): {health['status']}")
        except Exception as e:
            print(f"\n   ❌ {name} 端口 ({port}): 无法连接")

if __name__ == "__main__":
    print("\n🚀 开始测试 Mock vLLM/Ollama 服务器\n")
    
    # 测试健康检查
    test_health()
    
    # 测试 vLLM API
    test_vllm_api()
    
    # 测试 Ollama API
    test_ollama_api()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)
    print("\n💡 提示:")
    print("   如果所有测试通过,说明 Mock 服务器工作正常")
    print("   现在可以配置 AgentBus 连接到:")
    print("   - vLLM: http://localhost:8030")
    print("   - Ollama: http://localhost:11434")
    print()
