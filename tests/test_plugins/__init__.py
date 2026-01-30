"""
AgentBus插件框架测试模块

此模块包含插件框架的完整测试套件，测试插件系统的核心功能、
生命周期管理、工具注册、钩子机制等。

测试覆盖：
- PluginContext: 插件上下文测试
- AgentBusPlugin: 插件基类测试  
- PluginTool: 工具注册测试
- PluginHook: 钩子机制测试
- PluginManager: 插件管理器测试
"""

# 设置测试配置
import logging
import asyncio
import pytest
from typing import Generator

# 配置测试日志
logging.basicConfig(level=logging.DEBUG)

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
def plugin_context(mock_logger) -> "PluginContext":
    """创建插件上下文fixture"""
    from agentbus.plugins.core import PluginContext
    
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

# pytest配置
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )