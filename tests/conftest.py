"""
AgentBus插件框架测试配置

此文件定义全局fixtures和测试配置,供所有插件测试使用。
"""

import logging
import asyncio
import pytest
import subprocess
import time
import requests
import os
from typing import Generator
# Add project root to sys.path
import sys
from pathlib import Path
project_root = str(Path(__file__).resolve().parent.parent)

if project_root not in sys.path:
    sys.path.insert(0, project_root)
elif sys.path[0] != project_root:
    sys.path.remove(project_root)
    sys.path.insert(0, project_root)


@pytest.fixture
def mock_logger():
    """创建模拟日志器"""
    return logging.getLogger("test_plugin")


@pytest.fixture
def plugin_context(mock_logger):
    """创建插件上下文fixture"""
    try:
        from plugins.core import PluginContext
    except ImportError:
        # 尝试相对导入或从 sys.modules 获取
        import sys
        if 'plugins.core' in sys.modules:
            PluginContext = sys.modules['plugins.core'].PluginContext
        else:
            raise
    
    return PluginContext(
        config={"test_config": "test_value"},
        logger=mock_logger,
        runtime={"test_runtime": "runtime_value"}
    )


@pytest.fixture
def sample_plugin_info():
    """创建示例插件信息"""
    return {
        'id': 'test_plugin',
        'name': 'Test Plugin',
        'version': '1.0.0',
        'description': 'A test plugin',
        'author': 'Test Author',
        'dependencies': []
    }


# ============================================================================
# vLLM Mock Server Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def mock_vllm_server():
    """启动 mock vLLM 服务器用于测试"""
    server_script = Path(project_root) / "mock_vllm_server.py"
    
    # 启动服务器进程
    process = subprocess.Popen(
        [sys.executable, str(server_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_root
    )
    
    # 等待服务器启动
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get("http://localhost:8030/health", timeout=1)
            if response.status_code == 200:
                print("\n✅ Mock vLLM 服务器已启动")
                break
        except requests.exceptions.RequestException:
            time.sleep(0.5)
    else:
        process.kill()
        raise RuntimeError("无法启动 mock vLLM 服务器")
    
    yield process
    
    # 清理:停止服务器
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    print("\n🛑 Mock vLLM 服务器已停止")


@pytest.fixture
def vllm_base_url():
    """vLLM 服务器基础 URL"""
    return "http://localhost:8030"


@pytest.fixture
def vllm_settings(monkeypatch):
    """配置 vLLM 测试环境变量"""
    monkeypatch.setenv("AGENTBUS_LOCAL_MODEL_ID", "qwen3_32B")
    monkeypatch.setenv("AGENTBUS_LOCAL_MODEL_BASE_URL", "http://127.0.0.1:8030/v1")
    monkeypatch.setenv("AGENTBUS_LOCAL_MODEL_API_KEY", "empty")
    return {
        "model_id": "qwen3_32B",
        "base_url": "http://127.0.0.1:8030/v1",
        "api_key": "empty"
    }


@pytest.fixture
def vllm_client(vllm_base_url):
    """创建配置好的 HTTP 客户端"""
    import httpx
    return httpx.Client(base_url=vllm_base_url, timeout=10.0)


@pytest.fixture
async def async_vllm_client(vllm_base_url):
    """创建异步 HTTP 客户端"""
    import httpx
    async with httpx.AsyncClient(base_url=vllm_base_url, timeout=10.0) as client:
        yield client