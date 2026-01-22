"""
测试模块初始化
"""

import pytest
import asyncio
from contextlib import AsyncExitStack
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def exit_stack():
    """退出栈"""
    async with AsyncExitStack() as stack:
        yield stack


@pytest.fixture
def mock_environment():
    """创建通用模拟环境"""
    env = MagicMock()
    
    # 异步方法
    env.read_file = AsyncMock(return_value="print('test')")
    env.write_file = AsyncMock(return_value=True)
    env.edit_file = AsyncMock(return_value=True)
    env.delete_file = AsyncMock(return_value=True)
    env.list_dir = AsyncMock(return_value=[])
    env.glob = AsyncMock(return_value=[])
    env.exists = AsyncMock(return_value=True)
    env.is_directory = AsyncMock(return_value=False)
    env.execute_command = AsyncMock(return_value=MagicMock(
        stdout="test output",
        stderr="",
        exit_code=0,
        success=True
    ))
    env.execute_command_stream = AsyncMock(return_value=AsyncMock())
    env.health_check = AsyncMock(return_value=True)
    
    # 属性
    env.workspace = MagicMock()
    env.workspace.__str__ = MagicMock(return_value="/test")
    
    return env


@pytest.fixture
def sample_messages():
    """示例消息列表"""
    from api.schemas.message import Message, MessageRole, MessageType
    from datetime import datetime
    from uuid import uuid4
    
    return [
        Message(
            id=str(uuid4()),
            content="Hello",
            role=MessageRole.USER,
            type=MessageType.USER,
            timestamp=datetime.now()
        ),
        Message(
            id=str(uuid4()),
            content="Hi there!",
            role=MessageRole.ASSISTANT,
            type=MessageType.ASSISTANT,
            timestamp=datetime.now()
        )
    ]
