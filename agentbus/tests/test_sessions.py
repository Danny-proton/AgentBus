"""
会话管理测试模块
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
async def session_manager():
    """创建会话管理器"""
    from services.session_manager import SessionManager
    from services.cost_tracker import CostTracker
    from core.memory.short_term import ShortTermMemory
    
    memory = ShortTermMemory()
    cost_tracker = CostTracker()
    
    manager = SessionManager(memory=memory, cost_tracker=cost_tracker)
    
    yield manager
    
    await manager.shutdown()


@pytest.mark.asyncio
async def test_create_session(session_manager):
    """测试创建会话"""
    session = await session_manager.create_session(
        workspace="/test",
        model="test-model"
    )
    
    assert session is not None
    assert session.id is not None
    assert session.workspace == "/test"
    assert session.current_model == "test-model"


@pytest.mark.asyncio
async def test_get_session(session_manager):
    """测试获取会话"""
    # 创建会话
    created = await session_manager.create_session()
    
    # 获取会话
    retrieved = await session_manager.get_session(created.id)
    
    assert retrieved is not None
    assert retrieved.id == created.id


@pytest.mark.asyncio
async def test_delete_session(session_manager):
    """测试删除会话"""
    session = await session_manager.create_session()
    
    success = await session_manager.delete_session(session.id)
    
    assert success
    
    # 验证已删除
    retrieved = await session_manager.get_session(session.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_list_sessions(session_manager):
    """测试列出会话"""
    # 创建多个会话
    await session_manager.create_session()
    await session_manager.create_session()
    
    sessions = await session_manager.list_sessions()
    
    assert len(sessions) >= 2


@pytest.mark.asyncio
async def test_clear_session(session_manager):
    """测试清除会话消息"""
    session = await session_manager.create_session()
    
    # 添加一些消息
    await session.memory.add_message(MagicMock())
    await session.memory.add_message(MagicMock())
    
    # 清除
    cleared = await session_manager.clear_session(session.id)
    
    assert cleared is not None
    assert len(cleared.messages) == 0


@pytest.mark.asyncio
async def test_session_process_message(session_manager):
    """测试会话消息处理"""
    session = await session_manager.create_session()
    
    # 处理消息
    chunks = []
    async for chunk in session.process_message(
        content="Hello, test!",
        stream=False
    ):
        chunks.append(chunk)
    
    assert len(chunks) == 1
