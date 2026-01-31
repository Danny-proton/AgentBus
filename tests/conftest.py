"""
AgentBus插件框架测试配置

此文件定义全局fixtures和测试配置，供所有插件测试使用。
"""

import logging
import asyncio
import pytest
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