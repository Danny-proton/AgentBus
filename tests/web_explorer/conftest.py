"""
pytest 配置和共享 fixtures

为 WebExplorer Agent 测试提供共享的测试配置和 fixtures。
"""

import pytest
import asyncio
import subprocess
import time
from pathlib import Path
import httpx
import json


@pytest.fixture
def mock_server_url():
    """Mock server URL"""
    return "http://127.0.0.1:8080"


@pytest.fixture
def test_config():
    """测试配置"""
    return {
        "mock_server_url": "http://127.0.0.1:8080",
        "max_depth": 5,
        "max_nodes": 20,
        "timeout": 60,
        "headless": True
    }


@pytest.fixture
def project_memory_path(tmp_path):
    """临时项目内存路径"""
    memory_path = tmp_path / "project_memory"
    memory_path.mkdir(exist_ok=True)
    return memory_path


@pytest.fixture(scope="session")
def mock_server():
    """
    启动 mock server 作为 session fixture
    在所有测试开始前启动,所有测试结束后关闭
    """
    # 启动 mock server
    server_path = Path(__file__).parent / "mock_server.py"
    process = subprocess.Popen(
        ["python", str(server_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # 等待服务器启动
    max_retries = 30
    for i in range(max_retries):
        try:
            response = httpx.get("http://127.0.0.1:8080/health", timeout=1.0)
            if response.status_code == 200:
                print(f"\n✓ Mock server started successfully")
                break
        except:
            if i == max_retries - 1:
                process.kill()
                raise RuntimeError("Failed to start mock server")
            time.sleep(0.5)
    
    yield "http://127.0.0.1:8080"
    
    # 关闭服务器
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
    print(f"\n✓ Mock server stopped")


@pytest.fixture
async def http_client():
    """异步 HTTP 客户端"""
    async with httpx.AsyncClient() as client:
        yield client


def load_index(index_path: Path) -> dict:
    """加载 index.json"""
    if not index_path.exists():
        return {"nodes": {}, "edges": []}
    return json.loads(index_path.read_text(encoding="utf-8"))


def save_index(index_path: Path, data: dict):
    """保存 index.json"""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def index_helper():
    """Index 文件辅助工具"""
    return {
        "load": load_index,
        "save": save_index
    }
