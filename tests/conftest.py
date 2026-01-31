"""
AgentBus插件框架测试配置

此文件定义全局fixtures和测试配置，供所有插件测试使用。
"""

import logging
import asyncio
import pytest
from typing import Generator
import sys
from pathlib import Path

# Add project root to sys.path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环fixture用于所有异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_logger():
    """创建模拟日志器"""
    return logging.getLogger("test_plugin")


@pytest.fixture
def plugin_context(mock_logger):
    """创建插件上下文fixture"""
    from plugins.core import PluginContext
    
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