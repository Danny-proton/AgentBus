"""
工具测试模块
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_environment():
    """创建模拟环境"""
    env = MagicMock()
    
    # 设置异步方法
    env.read_file = AsyncMock(return_value="def hello():\n    print('Hello')")
    env.write_file = AsyncMock(return_value=True)
    env.execute_command = AsyncMock(return_value=CommandResult(
        stdout="output",
        stderr="",
        exit_code=0,
        success=True
    ))
    env.list_dir = AsyncMock(return_value=[
        FileInfo(
            path="/test/file.py",
            name="file.py",
            is_directory=False,
            size=100
        )
    ])
    env.glob = AsyncMock(return_value=["/test/file.py"])
    
    return env


@pytest.fixture
def tool_registry(mock_environment):
    """创建工具注册中心"""
    from tools.registry import ToolRegistry
    from tools.file_tools import register_file_tools
    
    registry = ToolRegistry()
    register_file_tools(registry, mock_environment)
    
    return registry


@pytest.mark.asyncio
async def test_file_read_tool(tool_registry, mock_environment):
    """测试文件读取工具"""
    tool = tool_registry.get_tool("file_read")
    
    assert tool is not None
    assert tool.name == "file_read"
    
    result = await tool.execute(path="/test/file.py")
    
    assert result.success
    assert "def hello" in result.content


@pytest.mark.asyncio
async def test_glob_tool(tool_registry, mock_environment):
    """测试文件查找工具"""
    tool = tool_registry.get_tool("glob")
    
    result = await tool.execute(pattern="**/*.py")
    
    assert result.success
    assert "file.py" in result.content


@pytest.mark.asyncio
async def test_list_dir_tool(tool_registry, mock_environment):
    """测试目录列表工具"""
    tool = tool_registry.get_tool("list_dir")
    
    result = await tool.execute(path="/test")
    
    assert result.success
    assert "file.py" in result.content


def test_tool_schemas(tool_registry):
    """测试工具 Schema 生成"""
    schemas = tool_registry.get_tool_schemas()
    
    assert len(schemas) > 0
    
    # 检查 Schema 结构
    schema = schemas[0]
    assert "type" in schema
    assert "function" in schema
    assert "name" in schema["function"]
    assert "description" in schema["function"]


def test_tool_enable_disable(tool_registry):
    """测试工具启用/禁用"""
    tool = tool_registry.get_tool("file_read")
    
    assert tool.enabled
    
    tool_registry.disable_tool("file_read")
    
    assert not tool.enabled
    
    tool_registry.enable_tool("file_read")
    
    assert tool.enabled
