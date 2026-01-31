"""
AgentBus渠道系统测试模块

提供渠道系统各组件的完整测试套件，包括：
- 基础类和消息格式测试
- 渠道适配器功能测试
- 渠道管理器测试
- 异步功能测试
- 错误处理测试
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Optional, Any

# 测试配置
pytest_plugins = ("pytest_asyncio",)

def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "unit: 单元测试标记")
    config.addinivalue_line("markers", "integration: 集成测试标记")
    config.addinivalue_line("markers", "async_test: 异步测试标记")
    config.addinivalue_line("markers", "slow: 慢速测试标记")

# 异步测试配置
@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# 常用测试夹具
@pytest.fixture
def mock_message_metadata():
    """模拟消息元数据"""
    from channels.base import MessageMetadata, ChatType
    from datetime import datetime
    
    return MessageMetadata(
        id="test_msg_123",
        timestamp=datetime.now(),
        sender_id="user_123",
        sender_name="Test User",
        sender_username="testuser",
        channel_id="channel_123",
        channel_name="Test Channel",
        chat_type=ChatType.DIRECT,
        mentions=["@other_user"],
        tags=["test", "important"]
    )

@pytest.fixture
def mock_message(mock_message_metadata):
    """模拟消息对象"""
    from channels.base import Message, MessageType
    
    return Message(
        type=MessageType.TEXT,
        content="测试消息内容",
        metadata=mock_message_metadata
    )

@pytest.fixture
def mock_channel_config():
    """模拟渠道配置"""
    from channels.base import ChannelConfig, ChannelAccountConfig, ChannelCapabilities, ChatType
    
    account_config = ChannelAccountConfig(
        account_id="test_account_123",
        name="Test Account",
        enabled=True,
        configured=True,
        token="test_token_123"
    )
    
    capabilities = ChannelCapabilities(
        chat_types=[ChatType.DIRECT, ChatType.GROUP],
        polls=True,
        reactions=True,
        reply=True,
        media=True
    )
    
    return ChannelConfig(
        channel_id="test_channel_123",
        channel_name="Test Channel",
        channel_type="test",
        accounts={"test_account_123": account_config},
        default_account_id="test_account_123",
        capabilities=capabilities,
        enabled=True
    )

@pytest.fixture
def mock_channel_status():
    """模拟渠道状态"""
    from channels.base import ChannelStatus, ChannelState, ConnectionStatus
    from datetime import datetime
    
    return ChannelStatus(
        account_id="test_account_123",
        state=ChannelState.ENABLED,
        connection_status=ConnectionStatus.CONNECTED,
        connected=True,
        running=True,
        last_connected_at=datetime.now()
    )

@pytest.fixture
def mock_channel_adapter(mock_channel_config, mock_channel_status):
    """模拟渠道适配器"""
    from channels.base import ChannelAdapter
    
    adapter = MagicMock(spec=ChannelAdapter)
    adapter.channel_id = mock_channel_config.channel_id
    adapter.channel_name = mock_channel_config.channel_name
    adapter.capabilities = mock_channel_config.capabilities
    
    # 模拟异步方法
    adapter.connect = AsyncMock(return_value=True)
    adapter.disconnect = AsyncMock(return_value=True)
    adapter.is_connected = AsyncMock(return_value=True)
    adapter.send_message = AsyncMock(return_value=True)
    adapter.send_media = AsyncMock(return_value=True)
    adapter.send_poll = AsyncMock(return_value=True)
    adapter.get_status = AsyncMock(return_value=mock_channel_status)
    adapter.configure_account = AsyncMock(return_value=True)
    adapter.authenticate = AsyncMock(return_value=True)
    adapter.validate_config = AsyncMock(return_value=[])
    
    return adapter

# 异步测试工具函数
async def wait_for_condition(condition_func, timeout=5.0, interval=0.1):
    """等待条件满足"""
    import time
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func():
            return True
        await asyncio.sleep(interval)
    
    return False

def assert_async_raises(coro, exception_type):
    """断言异步函数抛出异常"""
    import pytest
    with pytest.raises(exception_type):
        asyncio.run(coro)

# 测试数据生成器
class TestDataGenerator:
    """测试数据生成器"""
    
    @staticmethod
    def create_test_messages(count=5):
        """创建测试消息列表"""
        from channels.base import Message, MessageType, MessageMetadata, ChatType
        from datetime import datetime
        
        messages = []
        for i in range(count):
            metadata = MessageMetadata(
                id=f"test_msg_{i}",
                timestamp=datetime.now(),
                sender_id=f"user_{i}",
                sender_name=f"User {i}",
                channel_id="test_channel",
                chat_type=ChatType.DIRECT
            )
            message = Message(
                type=MessageType.TEXT,
                content=f"测试消息 {i}",
                metadata=metadata
            )
            messages.append(message)
        
        return messages
    
    @staticmethod
    def create_test_channel_configs(count=3):
        """创建测试渠道配置列表"""
        from channels.base import ChannelConfig, ChannelAccountConfig, ChannelCapabilities, ChatType
        
        configs = []
        for i in range(count):
            account_config = ChannelAccountConfig(
                account_id=f"test_account_{i}",
                name=f"Test Account {i}",
                enabled=True,
                configured=True,
                token=f"test_token_{i}"
            )
            
            capabilities = ChannelCapabilities(
                chat_types=[ChatType.DIRECT],
                polls=(i % 2 == 0),
                reactions=(i % 2 == 1),
                media=True
            )
            
            config = ChannelConfig(
                channel_id=f"test_channel_{i}",
                channel_name=f"Test Channel {i}",
                channel_type="test",
                accounts={f"test_account_{i}": account_config},
                default_account_id=f"test_account_{i}",
                capabilities=capabilities,
                enabled=True
            )
            configs.append(config)
        
        return configs

# 测试环境清理函数
async def cleanup_test_environment():
    """清理测试环境"""
    # 清理全局状态
    from agentbus.channels import channel_registry
    channel_registry._adapters.clear()
    channel_registry._factories.clear()
    
    # 清理临时文件
    import os
    import tempfile
    
    temp_files = [
        "channels_config.json",
        "test_channels_config.json"
    ]
    
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)

# 错误模拟器
class ErrorSimulator:
    """错误模拟器"""
    
    @staticmethod
    def create_connection_error():
        """创建连接错误"""
        return ConnectionError("模拟连接失败")
    
    @staticmethod
    def create_auth_error():
        """创建认证错误"""
        return PermissionError("模拟认证失败")
    
    @staticmethod
    def create_timeout_error():
        """创建超时错误"""
        return asyncio.TimeoutError("模拟操作超时")
    
    @staticmethod
    def create_validation_error(message="配置验证失败"):
        """创建验证错误"""
        return ValueError(message)

# 导出常用测试工具
__all__ = [
    "TestDataGenerator",
    "ErrorSimulator", 
    "wait_for_condition",
    "assert_async_raises",
    "cleanup_test_environment"
]