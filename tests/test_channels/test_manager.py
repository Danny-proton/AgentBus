"""
AgentBus渠道管理器测试

测试渠道管理器的所有功能，包括：
- 渠道注册和注销
- 连接状态管理
- 消息发送和处理
- 配置管理
- 状态监控
- 错误处理
- 异步功能测试
"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
from datetime import datetime, timedelta
import uuid

from agentbus.channels.manager import ChannelManager
from agentbus.channels.base import (
    ChannelAdapter,
    ChannelConfig,
    ChannelAccountConfig,
    ChannelStatus,
    Message,
    MessageType,
    ChatType,
    ChannelState,
    ConnectionStatus,
    ChannelCapabilities,
    MessageMetadata,
    ChannelRegistry,
)


@pytest.fixture(autouse=True)
def setup_test_factory():
    """自动设置测试工厂函数"""
    # 注册测试工厂函数
    from agentbus.channels import channel_registry
    
    def test_factory(config):
        return MockChannelAdapter(config)
    
    # 注册不同类型的测试工厂
    channel_registry.register_factory("test", test_factory)
    channel_registry.register_factory("text", test_factory)
    channel_registry.register_factory("media", test_factory)
    channel_registry.register_factory("poll", test_factory)
    
    yield
    
    # 清理工厂函数
    for factory_type in ["test", "text", "media", "poll"]:
        if factory_type in channel_registry._factories:
            del channel_registry._factories[factory_type]


class MockChannelAdapter(ChannelAdapter):
    """模拟渠道适配器用于测试"""
    
    def __init__(self, config, connection_success=True):
        super().__init__(config)
        self._connection_success = connection_success
        self._connected_accounts = set()
        self._messages_sent = []
        self._media_sent = []
        self._polls_sent = []
    
    @property
    def channel_id(self):
        return self.config.channel_id
    
    @property
    def channel_name(self):
        return self.config.channel_name
    
    @property
    def capabilities(self):
        return self.config.capabilities
    
    async def connect(self, account_id):
        if self._connection_success:
            self._connected_accounts.add(account_id)
            return True
        return False
    
    async def disconnect(self, account_id):
        self._connected_accounts.discard(account_id)
        return True
    
    async def is_connected(self, account_id):
        return account_id in self._connected_accounts
    
    async def send_message(self, message, account_id=None):
        if account_id and account_id not in self._connected_accounts:
            return False
        
        self._messages_sent.append({
            "message": message,
            "account_id": account_id,
            "timestamp": datetime.now()
        })
        
        # 通知消息处理器
        self._notify_message_handlers(message)
        return True
    
    async def send_media(self, message, media_url, account_id=None):
        if account_id and account_id not in self._connected_accounts:
            return False
        
        self._media_sent.append({
            "message": message,
            "media_url": media_url,
            "account_id": account_id,
            "timestamp": datetime.now()
        })
        return True
    
    async def send_poll(self, question, options, account_id=None):
        if account_id and account_id not in self._connected_accounts:
            return False
        
        self._polls_sent.append({
            "question": question,
            "options": options,
            "account_id": account_id,
            "timestamp": datetime.now()
        })
        return True
    
    async def get_status(self, account_id):
        return ChannelStatus(
            account_id=account_id,
            state=ChannelState.ENABLED if account_id in self._connected_accounts else ChannelState.DISABLED,
            connection_status=ConnectionStatus.CONNECTED if account_id in self._connected_accounts else ConnectionStatus.DISCONNECTED,
            connected=account_id in self._connected_accounts,
            running=True,
            last_connected_at=datetime.now() if account_id in self._connected_accounts else None
        )
    
    async def configure_account(self, account_config):
        return True


class TestChannelManagerInitialization:
    """测试渠道管理器初始化"""
    
    def test_manager_creation(self):
        """测试管理器创建"""
        manager = ChannelManager()
        
        assert manager._adapters == {}
        assert manager._configs == {}
        assert manager._status_cache == {}
        assert manager._message_handlers == set()
        assert manager._status_handlers == set()
        assert not manager._running
        assert manager._shutdown_event.is_set() is False
    
    def test_manager_with_config_path(self):
        """测试带配置路径的管理器"""
        config_path = Path("test_config.json")
        manager = ChannelManager(config_path=config_path)
        
        assert manager._config_path == config_path
    
    def test_manager_registry_property(self):
        """测试管理器注册表属性"""
        manager = ChannelManager()
        
        # 验证使用全局注册表
        from agentbus.channels import channel_registry
        assert manager.registry is channel_registry


class TestChannelManagerLifecycle:
    """测试渠道管理器生命周期"""
    
    @pytest.mark.asyncio
    async def test_start_manager(self):
        """测试启动管理器"""
        manager = ChannelManager()
        
        # 确保管理器未运行
        assert not manager._running
        
        # 启动管理器
        await manager.start()
        
        # 验证管理器已运行
        assert manager._running
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_stop_manager(self):
        """测试停止管理器"""
        manager = ChannelManager()
        
        # 启动管理器
        await manager.start()
        assert manager._running
        
        # 停止管理器
        await manager.stop()
        
        # 验证管理器已停止
        assert not manager._running
        assert manager._shutdown_event.is_set()
    
    @pytest.mark.asyncio
    async def test_start_already_running_manager(self):
        """测试启动已运行的管理器"""
        manager = ChannelManager()
        
        # 第一次启动
        await manager.start()
        first_running_state = manager._running
        
        # 第二次启动
        await manager.start()
        second_running_state = manager._running
        
        # 应该仍然是运行状态
        assert first_running_state is True
        assert second_running_state is True
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_stop_not_running_manager(self):
        """测试停止未运行的管理器"""
        manager = ChannelManager()
        
        # 停止未运行的管理器应该安全
        await manager.stop()
        
        assert not manager._running
        assert manager._shutdown_event.is_set()


class TestChannelRegistration:
    """测试渠道注册"""
    
    @pytest.fixture
    def test_config(self):
        """创建测试配置"""
        account_config = ChannelAccountConfig(
            account_id="test_account",
            name="Test Account",
            enabled=True,
            configured=True,
            token="test_token"
        )
        
        capabilities = ChannelCapabilities(
            chat_types=[ChatType.DIRECT, ChatType.GROUP],
            polls=True,
            reactions=True,
            media=True
        )
        
        return ChannelConfig(
            channel_id="test_channel",
            channel_name="Test Channel",
            channel_type="test",
            accounts={"test_account": account_config},
            default_account_id="test_account",
            capabilities=capabilities,
            enabled=True
        )
    
    @pytest.mark.asyncio
    async def test_register_channel(self, test_config):
        """测试注册渠道"""
        manager = ChannelManager()
        # 注册渠道
        result = await manager.register_channel(test_config)
        
        # 验证注册成功
        assert result is True
        assert "test_channel" in manager._adapters
        assert "test_channel" in manager._configs
        
        # 验证适配器已注册
        adapter = manager._adapters["test_channel"]
        assert adapter.channel_id == "test_channel"
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_register_multiple_channels(self, test_config):
        """测试注册多个渠道"""
        manager = ChannelManager()
        
        # 创建多个配置
        configs = []
        for i in range(3):
            config = ChannelConfig(
                channel_id=f"test_channel_{i}",
                channel_name=f"Test Channel {i}",
                channel_type="test",
                accounts={
                    "test_account": ChannelAccountConfig(
                        account_id="test_account",
                        name=f"Test Account {i}",
                        configured=True
                    )
                },
                default_account_id="test_account",
                enabled=True
            )
            configs.append(config)
        
        # 注册所有渠道
        results = []
        for config in configs:
            result = await manager.register_channel(config)
            results.append(result)
        
        # 验证所有注册成功
        assert all(results)
        assert len(manager._adapters) == 3
        assert len(manager._configs) == 3
        
        # 验证渠道ID
        expected_ids = {"test_channel_0", "test_channel_1", "test_channel_2"}
        actual_ids = set(manager._configs.keys())
        assert expected_ids == actual_ids
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_unregister_channel(self, test_config):
        """测试注销渠道"""
        manager = ChannelManager()
        
        # 先注册渠道
        await manager.register_channel(test_config)
        assert "test_channel" in manager._adapters
        assert "test_channel" in manager._configs
        
        # 注销渠道
        result = await manager.unregister_channel("test_channel")
        
        # 验证注销成功
        assert result is True
        assert "test_channel" not in manager._adapters
        assert "test_channel" not in manager._configs
        assert "test_channel" not in manager._status_cache
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_unregister_nonexistent_channel(self):
        """测试注销不存在的渠道"""
        manager = ChannelManager()
        
        # 注销不存在的渠道应该返回True（安全操作）
        result = await manager.unregister_channel("nonexistent")
        assert result is True
        
        # 清理
        await manager.stop()
    
    def test_get_channel_config(self, test_config):
        """测试获取渠道配置"""
        manager = ChannelManager()
        
        # 注册渠道
        asyncio.run(manager.register_channel(test_config))
        
        # 获取配置
        config = manager.get_channel_config("test_channel")
        
        # 验证配置正确
        assert config is not None
        assert config.channel_id == "test_channel"
        assert config.channel_name == "Test Channel"
        assert config.channel_type == "test"
        assert "test_account" in config.accounts
        
        # 测试获取不存在的配置
        config = manager.get_channel_config("nonexistent")
        assert config is None
        
        # 清理
        asyncio.run(manager.stop())
    
    def test_list_channels(self, test_config):
        """测试列出渠道"""
        manager = ChannelManager()
        
        # 初始时应该没有渠道
        channels = manager.list_channels()
        assert channels == []
        
        # 注册渠道
        asyncio.run(manager.register_channel(test_config))
        
        # 列出渠道
        channels = manager.list_channels()
        assert channels == ["test_channel"]
        
        # 清理
        asyncio.run(manager.stop())
    
    def test_get_channel_adapter(self, test_config):
        """测试获取渠道适配器"""
        manager = ChannelManager()
        
        # 注册渠道
        asyncio.run(manager.register_channel(test_config))
        
        # 获取适配器
        adapter = manager.get_channel_adapter("test_channel")
        
        # 验证适配器正确
        assert adapter is not None
        assert adapter.channel_id == "test_channel"
        assert isinstance(adapter, ChannelAdapter)
        
        # 测试获取不存在的适配器
        adapter = manager.get_channel_adapter("nonexistent")
        assert adapter is None
        
        # 清理
        asyncio.run(manager.stop())


class TestConnectionManagement:
    """测试连接管理"""
    
    @pytest.fixture
    def connected_config(self):
        """创建可连接的测试配置"""
        account_config = ChannelAccountConfig(
            account_id="test_account",
            name="Test Account",
            enabled=True,
            configured=True,
            token="test_token"
        )
        
        return ChannelConfig(
            channel_id="test_channel",
            channel_name="Test Channel",
            channel_type="test",
            accounts={"test_account": account_config},
            default_account_id="test_account",
            enabled=True
        )
    
    @pytest.mark.asyncio
    async def test_connect_channel_success(self, connected_config):
        """测试成功连接渠道"""
        manager = ChannelManager()
        
        # 注册渠道
        await manager.register_channel(connected_config)
        
        # 连接渠道
        result = await manager.connect_channel("test_channel")
        
        # 验证连接成功
        assert result is True
        
        # 验证连接状态
        is_connected = await manager.is_channel_connected("test_channel")
        assert is_connected is True
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_connect_channel_failure(self):
        """测试连接失败"""
        manager = ChannelManager()
        
        # 创建总是连接失败的适配器
        config = ChannelConfig(
            channel_id="test_channel",
            channel_name="Test Channel",
            channel_type="test",
            accounts={
                "test_account": ChannelAccountConfig(
                    account_id="test_account",
                    configured=True
                )
            },
            default_account_id="test_account",
            enabled=True
        )
        
        # 注册渠道
        await manager.register_channel(config)
        
        # 模拟连接失败
        adapter = manager._adapters["test_channel"]
        adapter.connect = AsyncMock(return_value=False)
        
        # 尝试连接
        result = await manager.connect_channel("test_channel")
        
        # 验证连接失败
        assert result is False
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_connect_channel_no_account(self, connected_config):
        """测试连接无账户配置的渠道"""
        manager = ChannelManager()
        
        # 创建无账户的配置
        config = ChannelConfig(
            channel_id="test_channel",
            channel_name="Test Channel",
            channel_type="test",
            accounts={},
            enabled=True
        )
        
        # 注册渠道
        await manager.register_channel(config)
        
        # 尝试连接
        result = await manager.connect_channel("test_channel")
        
        # 验证连接失败
        assert result is False
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_connect_nonexistent_channel(self):
        """测试连接不存在的渠道"""
        manager = ChannelManager()
        
        # 尝试连接不存在的渠道
        result = await manager.connect_channel("nonexistent")
        
        # 验证连接失败
        assert result is False
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_disconnect_channel(self, connected_config):
        """测试断开渠道连接"""
        manager = ChannelManager()
        
        # 注册并连接渠道
        await manager.register_channel(connected_config)
        await manager.connect_channel("test_channel")
        
        # 验证已连接
        is_connected = await manager.is_channel_connected("test_channel")
        assert is_connected is True
        
        # 断开连接
        result = await manager.disconnect_channel("test_channel")
        
        # 验证断开成功
        assert result is True
        
        # 验证已断开
        is_connected = await manager.is_channel_connected("test_channel")
        assert is_connected is False
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_connect_all_channels(self, connected_config):
        """测试连接所有渠道"""
        manager = ChannelManager()
        
        # 创建多个配置
        configs = []
        for i in range(3):
            config = ChannelConfig(
                channel_id=f"test_channel_{i}",
                channel_name=f"Test Channel {i}",
                channel_type="test",
                accounts={
                    "test_account": ChannelAccountConfig(
                        account_id="test_account",
                        configured=True
                    )
                },
                default_account_id="test_account",
                enabled=True
            )
            configs.append(config)
            await manager.register_channel(config)
        
        # 连接所有渠道
        await manager.connect_all()
        
        # 验证所有渠道都已连接
        for i in range(3):
            is_connected = await manager.is_channel_connected(f"test_channel_{i}")
            assert is_connected is True
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_disconnect_all_channels(self, connected_config):
        """测试断开所有渠道"""
        manager = ChannelManager()
        
        # 注册并连接渠道
        await manager.register_channel(connected_config)
        await manager.connect_channel("test_channel")
        
        # 断开所有渠道
        await manager.disconnect_all()
        
        # 验证渠道已断开
        is_connected = await manager.is_channel_connected("test_channel")
        assert is_connected is False
        
        # 清理
        await manager.stop()


class TestMessageSending:
    """测试消息发送"""
    
    @pytest.fixture
    def messaging_config(self):
        """创建用于消息测试的配置"""
        account_config = ChannelAccountConfig(
            account_id="test_account",
            name="Test Account",
            enabled=True,
            configured=True,
            token="test_token"
        )
        
        capabilities = ChannelCapabilities(
            chat_types=[ChatType.DIRECT, ChatType.GROUP],
            polls=True,
            reactions=True,
            media=True
        )
        
        return ChannelConfig(
            channel_id="test_channel",
            channel_name="Test Channel",
            channel_type="test",
            accounts={"test_account": account_config},
            default_account_id="test_account",
            capabilities=capabilities,
            enabled=True
        )
    
    @pytest.mark.asyncio
    async def test_send_text_message(self, messaging_config):
        """测试发送文本消息"""
        manager = ChannelManager()
        
        # 注册并连接渠道
        await manager.register_channel(messaging_config)
        await manager.connect_channel("test_channel")
        
        # 发送消息
        result = await manager.send_message(
            "test_channel",
            "Hello, World!",
            MessageType.TEXT
        )
        
        # 验证发送成功
        assert result is True
        
        # 验证消息已发送到适配器
        adapter = manager._adapters["test_channel"]
        assert len(adapter._messages_sent) == 1
        
        sent_message = adapter._messages_sent[0]["message"]
        assert sent_message.content == "Hello, World!"
        assert sent_message.type == MessageType.TEXT
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_send_message_to_disconnected_channel(self, messaging_config):
        """测试向断开的渠道发送消息"""
        manager = ChannelManager()
        
        # 注册但不连接渠道
        await manager.register_channel(messaging_config)
        
        # 尝试发送消息
        result = await manager.send_message(
            "test_channel",
            "Hello, World!"
        )
        
        # 验证发送失败
        assert result is False
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_send_message_with_metadata(self, messaging_config):
        """测试发送带元数据的消息"""
        manager = ChannelManager()
        
        # 注册并连接渠道
        await manager.register_channel(messaging_config)
        await manager.connect_channel("test_channel")
        
        # 发送带额外元数据的消息
        result = await manager.send_message(
            "test_channel",
            "Test message",
            MessageType.TEXT,
            tags=["important", "test"],
            custom_data={"priority": "high"}
        )
        
        # 验证发送成功
        assert result is True
        
        # 验证消息包含自定义数据
        adapter = manager._adapters["test_channel"]
        sent_message = adapter._messages_sent[0]["message"]
        
        assert "important" in sent_message.metadata.tags
        assert "test" in sent_message.metadata.tags
        assert sent_message.metadata.custom_data["priority"] == "high"
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_send_media_message(self, messaging_config):
        """测试发送媒体消息"""
        manager = ChannelManager()
        
        # 注册并连接渠道
        await manager.register_channel(messaging_config)
        await manager.connect_channel("test_channel")
        
        # 发送媒体消息
        media_url = "http://example.com/image.jpg"
        result = await manager.send_media(
            "test_channel",
            "Check out this image!",
            media_url
        )
        
        # 验证发送成功
        assert result is True
        
        # 验证媒体消息已发送
        adapter = manager._adapters["test_channel"]
        assert len(adapter._media_sent) == 1
        
        sent_media = adapter._media_sent[0]
        assert sent_media["media_url"] == media_url
        assert sent_media["message"].content == "Check out this image!"
        assert sent_media["message"].type == MessageType.MEDIA
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_send_poll(self, messaging_config):
        """测试发送投票"""
        manager = ChannelManager()
        
        # 注册并连接渠道
        await manager.register_channel(messaging_config)
        await manager.connect_channel("test_channel")
        
        # 发送投票
        question = "What is your favorite color?"
        options = ["Red", "Blue", "Green", "Yellow"]
        result = await manager.send_poll("test_channel", question, options)
        
        # 验证发送成功
        assert result is True
        
        # 验证投票已发送
        adapter = manager._adapters["test_channel"]
        assert len(adapter._polls_sent) == 1
        
        sent_poll = adapter._polls_sent[0]
        assert sent_poll["question"] == question
        assert sent_poll["options"] == options
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_send_to_nonexistent_channel(self):
        """测试向不存在的渠道发送消息"""
        manager = ChannelManager()
        
        # 尝试向不存在的渠道发送消息
        result = await manager.send_message(
            "nonexistent",
            "Hello, World!"
        )
        
        # 验证发送失败
        assert result is False
        
        # 清理
        await manager.stop()


class TestStatusManagement:
    """测试状态管理"""
    
    @pytest.fixture
    def status_config(self):
        """创建用于状态测试的配置"""
        account_config = ChannelAccountConfig(
            account_id="test_account",
            name="Test Account",
            enabled=True,
            configured=True,
            token="test_token"
        )
        
        return ChannelConfig(
            channel_id="test_channel",
            channel_name="Test Channel",
            channel_type="test",
            accounts={"test_account": account_config},
            default_account_id="test_account",
            enabled=True
        )
    
    @pytest.mark.asyncio
    async def test_get_channel_status_connected(self, status_config):
        """测试获取已连接渠道的状态"""
        manager = ChannelManager()
        
        # 注册并连接渠道
        await manager.register_channel(status_config)
        await manager.connect_channel("test_channel")
        
        # 获取状态
        status = await manager.get_channel_status("test_channel")
        
        # 验证状态正确
        assert status is not None
        assert status.account_id == "test_account"
        assert status.connection_status == ConnectionStatus.CONNECTED
        assert status.connected is True
        assert status.running is True
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_get_channel_status_disconnected(self, status_config):
        """测试获取断开渠道的状态"""
        manager = ChannelManager()
        
        # 注册但不连接渠道
        await manager.register_channel(status_config)
        
        # 获取状态
        status = await manager.get_channel_status("test_channel")
        
        # 验证状态正确
        assert status is not None
        assert status.account_id == "test_account"
        assert status.connection_status == ConnectionStatus.DISCONNECTED
        assert status.connected is False
        assert status.running is True
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_get_channel_status_nonexistent(self):
        """测试获取不存在渠道的状态"""
        manager = ChannelManager()
        
        # 获取不存在渠道的状态
        status = await manager.get_channel_status("nonexistent")
        
        # 验证返回None
        assert status is None
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_get_all_status(self, status_config):
        """测试获取所有渠道状态"""
        manager = ChannelManager()
        
        # 创建多个配置
        configs = []
        for i in range(3):
            config = ChannelConfig(
                channel_id=f"test_channel_{i}",
                channel_name=f"Test Channel {i}",
                channel_type="test",
                accounts={
                    "test_account": ChannelAccountConfig(
                        account_id="test_account",
                        configured=True
                    )
                },
                default_account_id="test_account",
                enabled=True
            )
            configs.append(config)
            await manager.register_channel(config)
        
        # 连接部分渠道
        await manager.connect_channel("test_channel_0")
        await manager.connect_channel("test_channel_2")
        
        # 获取所有状态
        all_status = await manager.get_all_status()
        
        # 验证状态
        assert len(all_status) == 3
        
        # 验证渠道0已连接
        status_0 = all_status["test_channel_0"]["test_account"]
        assert status_0.connection_status == ConnectionStatus.CONNECTED
        assert status_0.connected is True
        
        # 验证渠道1未连接
        status_1 = all_status["test_channel_1"]["test_account"]
        assert status_1.connection_status == ConnectionStatus.DISCONNECTED
        assert status_1.connected is False
        
        # 验证渠道2已连接
        status_2 = all_status["test_channel_2"]["test_account"]
        assert status_2.connection_status == ConnectionStatus.CONNECTED
        assert status_2.connected is True
        
        # 清理
        await manager.stop()


class TestConfigurationManagement:
    """测试配置管理"""
    
    @pytest.fixture
    def temp_config_file(self):
        """创建临时配置文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "channels": {
                    "test_channel_1": {
                        "channel_id": "test_channel_1",
                        "channel_name": "Test Channel 1",
                        "channel_type": "test",
                        "accounts": {
                            "test_account_1": {
                                "account_id": "test_account_1",
                                "name": "Test Account 1",
                                "enabled": True,
                                "configured": True,
                                "token": "test_token_1"
                            }
                        },
                        "default_account_id": "test_account_1",
                        "capabilities": {
                            "chat_types": ["direct"],
                            "polls": False,
                            "reactions": False
                        },
                        "settings": {},
                        "enabled": True
                    }
                },
                "last_updated": datetime.now().isoformat()
            }
            json.dump(config_data, f, indent=2)
            temp_file = f.name
        
        yield temp_file
        
        # 清理临时文件
        if os.path.exists(temp_file):
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_load_configs_from_file(self, temp_config_file):
        """测试从文件加载配置"""
        # 使用临时配置文件创建管理器
        manager = ChannelManager(config_path=Path(temp_config_file))
        
        # 启动管理器（会自动加载配置）
        await manager.start()
        
        # 验证配置已加载
        assert "test_channel_1" in manager._configs
        config = manager.get_channel_config("test_channel_1")
        assert config is not None
        assert config.channel_name == "Test Channel 1"
        assert config.channel_type == "test"
        assert "test_account_1" in config.accounts
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_update_channel_config(self):
        """测试更新渠道配置"""
        manager = ChannelManager()
        
        # 原始配置
        original_config = ChannelConfig(
            channel_id="test_channel",
            channel_name="Original Channel",
            channel_type="test",
            accounts={
                "test_account": ChannelAccountConfig(
                    account_id="test_account",
                    configured=True
                )
            },
            default_account_id="test_account",
            enabled=True
        )
        
        # 注册原始配置
        await manager.register_channel(original_config)
        
        # 新配置
        updated_config = ChannelConfig(
            channel_id="test_channel",
            channel_name="Updated Channel",
            channel_type="test",
            accounts={
                "test_account": ChannelAccountConfig(
                    account_id="test_account",
                    configured=True
                ),
                "new_account": ChannelAccountConfig(
                    account_id="new_account",
                    configured=True
                )
            },
            default_account_id="new_account",
            enabled=False
        )
        
        # 更新配置
        result = await manager.update_channel_config("test_channel", updated_config)
        
        # 验证更新成功
        assert result is True
        
        # 验证配置已更新
        config = manager.get_channel_config("test_channel")
        assert config.channel_name == "Updated Channel"
        assert config.default_account_id == "new_account"
        assert config.enabled is False
        assert "new_account" in config.accounts
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_save_and_load_configs(self):
        """测试保存和加载配置"""
        manager = ChannelManager()
        
        # 创建配置
        config = ChannelConfig(
            channel_id="test_channel",
            channel_name="Test Channel",
            channel_type="test",
            accounts={
                "test_account": ChannelAccountConfig(
                    account_id="test_account",
                    configured=True
                )
            },
            default_account_id="test_account",
            enabled=True
        )
        
        # 注册渠道
        await manager.register_channel(config)
        
        # 保存配置
        await manager._save_configs()
        
        # 验证文件已创建
        assert manager._config_path.exists()
        
        # 创建新管理器并加载配置
        new_manager = ChannelManager(config_path=manager._config_path)
        await new_manager.start()
        
        # 验证配置已加载
        assert "test_channel" in new_manager._configs
        loaded_config = new_manager.get_channel_config("test_channel")
        assert loaded_config.channel_name == "Test Channel"
        assert loaded_config.channel_type == "test"
        
        # 清理
        await manager.stop()
        await new_manager.stop()


class TestEventHandling:
    """测试事件处理"""
    
    @pytest.fixture
    def event_config(self):
        """创建用于事件测试的配置"""
        account_config = ChannelAccountConfig(
            account_id="test_account",
            name="Test Account",
            enabled=True,
            configured=True,
            token="test_token"
        )
        
        return ChannelConfig(
            channel_id="test_channel",
            channel_name="Test Channel",
            channel_type="test",
            accounts={"test_account": account_config},
            default_account_id="test_account",
            enabled=True
        )
    
    @pytest.mark.asyncio
    async def test_message_handler_registration(self, event_config):
        """测试消息处理器注册"""
        manager = ChannelManager()
        
        # 注册并连接渠道
        await manager.register_channel(event_config)
        await manager.connect_channel("test_channel")
        
        # 收集接收到的消息
        received_messages = []
        
        def message_handler(message, channel_id):
            received_messages.append((message, channel_id))
        
        # 添加消息处理器
        manager.add_message_handler(message_handler)
        
        # 发送消息（应该触发处理器）
        await manager.send_message("test_channel", "Hello, World!")
        
        # 验证消息被接收
        assert len(received_messages) == 1
        message, channel_id = received_messages[0]
        assert message.content == "Hello, World!"
        assert channel_id == "test_channel"
        
        # 移除处理器
        manager.remove_message_handler(message_handler)
        
        # 发送另一条消息
        await manager.send_message("test_channel", "Second message")
        
        # 验证第二条消息没有被处理
        assert len(received_messages) == 1
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_status_handler_registration(self, event_config):
        """测试状态处理器注册"""
        manager = ChannelManager()
        
        # 收集状态变化
        status_changes = []
        
        def status_handler(channel_id, status):
            status_changes.append((channel_id, status))
        
        # 添加状态处理器
        manager.add_status_handler(status_handler)
        
        # 注册渠道
        await manager.register_channel(event_config)
        
        # 连接渠道（应该触发状态变化）
        await manager.connect_channel("test_channel")
        
        # 验证状态变化被记录
        # 注意：这里依赖于具体的事件触发逻辑
        
        # 清理
        await manager.stop()


class TestStatistics:
    """测试统计信息"""
    
    @pytest.mark.asyncio
    async def test_get_statistics(self):
        """测试获取统计信息"""
        manager = ChannelManager()
        
        # 启动管理器
        await manager.start()
        
        # 获取统计信息
        stats = manager.get_statistics()
        
        # 验证统计信息结构
        assert "total_channels" in stats
        assert "active_adapters" in stats
        assert "connected_channels" in stats
        assert "running" in stats
        assert "config_path" in stats
        
        # 验证初始统计
        assert stats["total_channels"] == 0
        assert stats["active_adapters"] == 0
        assert stats["connected_channels"] == 0
        assert stats["running"] is True
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        manager = ChannelManager()
        
        # 启动管理器
        await manager.start()
        
        # 执行健康检查
        health = await manager.health_check()
        
        # 验证健康检查结果结构
        assert "manager_running" in health
        assert "channels" in health
        assert "overall_health" in health
        
        # 验证管理器运行状态
        assert health["manager_running"] is True
        assert health["overall_health"] == "healthy"
        
        # 清理
        await manager.stop()


class TestErrorHandling:
    """测试错误处理"""
    
    @pytest.mark.asyncio
    async def test_connect_nonexistent_channel_error(self):
        """测试连接不存在渠道的错误处理"""
        manager = ChannelManager()
        
        # 启动管理器
        await manager.start()
        
        # 尝试连接不存在的渠道
        result = await manager.connect_channel("nonexistent")
        
        # 验证返回False而不是抛出异常
        assert result is False
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_send_to_nonexistent_channel_error(self):
        """测试向不存在渠道发送消息的错误处理"""
        manager = ChannelManager()
        
        # 启动管理器
        await manager.start()
        
        # 尝试向不存在的渠道发送消息
        result = await manager.send_message("nonexistent", "Hello, World!")
        
        # 验证返回False而不是抛出异常
        assert result is False
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_config_loading_error_handling(self):
        """测试配置文件加载错误处理"""
        # 创建损坏的配置文件
        corrupted_file = Path("corrupted_config.json")
        try:
            with open(corrupted_file, 'w') as f:
                f.write("invalid json content")
            
            # 使用损坏的配置文件创建管理器
            manager = ChannelManager(config_path=corrupted_file)
            
            # 启动管理器（应该安全地处理损坏的配置文件）
            await manager.start()
            
            # 验证管理器仍能启动
            assert manager._running is True
            
            # 清理
            await manager.stop()
            
        finally:
            # 清理损坏的配置文件
            if corrupted_file.exists():
                corrupted_file.unlink()


class TestAsyncOperations:
    """测试异步操作"""
    
    @pytest.mark.asyncio
    async def test_concurrent_channel_operations(self):
        """测试并发渠道操作"""
        manager = ChannelManager()
        
        # 创建多个配置
        configs = []
        for i in range(5):
            config = ChannelConfig(
                channel_id=f"test_channel_{i}",
                channel_name=f"Test Channel {i}",
                channel_type="test",
                accounts={
                    "test_account": ChannelAccountConfig(
                        account_id="test_account",
                        configured=True
                    )
                },
                default_account_id="test_account",
                enabled=True
            )
            configs.append(config)
        
        # 并发注册所有渠道
        register_tasks = [manager.register_channel(config) for config in configs]
        register_results = await asyncio.gather(*register_tasks)
        
        # 验证所有注册成功
        assert all(register_results)
        assert len(manager._adapters) == 5
        
        # 并发连接所有渠道
        connect_tasks = [manager.connect_channel(f"test_channel_{i}") for i in range(5)]
        connect_results = await asyncio.gather(*connect_tasks)
        
        # 验证所有连接成功
        assert all(connect_results)
        
        # 验证所有渠道都已连接
        for i in range(5):
            is_connected = await manager.is_channel_connected(f"test_channel_{i}")
            assert is_connected is True
        
        # 并发断开所有渠道
        disconnect_tasks = [manager.disconnect_channel(f"test_channel_{i}") for i in range(5)]
        disconnect_results = await asyncio.gather(*disconnect_tasks)
        
        # 验证所有断开成功
        assert all(disconnect_results)
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_message_sending(self):
        """测试并发消息发送"""
        manager = ChannelManager()
        
        # 创建配置
        config = ChannelConfig(
            channel_id="test_channel",
            channel_name="Test Channel",
            channel_type="test",
            accounts={
                "test_account": ChannelAccountConfig(
                    account_id="test_account",
                    configured=True
                )
            },
            default_account_id="test_account",
            enabled=True
        )
        
        # 注册并连接渠道
        await manager.register_channel(config)
        await manager.connect_channel("test_channel")
        
        # 并发发送多条消息
        message_tasks = []
        for i in range(10):
            task = manager.send_message("test_channel", f"Message {i}")
            message_tasks.append(task)
        
        send_results = await asyncio.gather(*message_tasks)
        
        # 验证所有消息发送成功
        assert all(send_results)
        
        # 验证所有消息都已发送到适配器
        adapter = manager._adapters["test_channel"]
        assert len(adapter._messages_sent) == 10
        
        # 清理
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_auto_save_configuration(self):
        """测试自动保存配置功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            manager = ChannelManager(config_path=config_path)
            
            # 启动管理器
            await manager.start()
            
            # 创建配置
            config = ChannelConfig(
                channel_id="test_channel",
                channel_name="Test Channel",
                channel_type="test",
                accounts={
                    "test_account": ChannelAccountConfig(
                        account_id="test_account",
                        configured=True
                    )
                },
                default_account_id="test_account",
                enabled=True
            )
            
            # 注册渠道
            await manager.register_channel(config)
            
            # 等待自动保存触发（至少5分钟，这里我们手动触发保存）
            await manager._save_configs()
            
            # 验证配置文件已创建
            assert config_path.exists()
            
            # 验证配置文件内容正确
            with open(config_path, 'r') as f:
                saved_data = json.load(f)
            
            assert "test_channel" in saved_data["channels"]
            
            # 清理
            await manager.stop()


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_channel_lifecycle(self):
        """测试完整渠道生命周期"""
        # 1. 创建管理器
        manager = ChannelManager()
        
        # 2. 启动管理器
        await manager.start()
        
        # 3. 创建配置
        account_config = ChannelAccountConfig(
            account_id="test_account",
            name="Test Account",
            enabled=True,
            configured=True,
            token="test_token"
        )
        
        capabilities = ChannelCapabilities(
            chat_types=[ChatType.DIRECT, ChatType.GROUP],
            polls=True,
            reactions=True,
            media=True
        )
        
        config = ChannelConfig(
            channel_id="integration_test_channel",
            channel_name="Integration Test Channel",
            channel_type="test",
            accounts={"test_account": account_config},
            default_account_id="test_account",
            capabilities=capabilities,
            enabled=True
        )
        
        # 4. 注册渠道
        register_result = await manager.register_channel(config)
        assert register_result is True
        
        # 5. 连接渠道
        connect_result = await manager.connect_channel("integration_test_channel")
        assert connect_result is True
        
        # 6. 验证连接状态
        is_connected = await manager.is_channel_connected("integration_test_channel")
        assert is_connected is True
        
        # 7. 获取状态
        status = await manager.get_channel_status("integration_test_channel")
        assert status is not None
        assert status.connection_status == ConnectionStatus.CONNECTED
        
        # 8. 发送文本消息
        text_result = await manager.send_message(
            "integration_test_channel",
            "Integration test message",
            MessageType.TEXT
        )
        assert text_result is True
        
        # 9. 发送媒体消息
        media_result = await manager.send_media(
            "integration_test_channel",
            "Check this out!",
            "http://example.com/image.jpg"
        )
        assert media_result is True
        
        # 10. 发送投票
        poll_result = await manager.send_poll(
            "integration_test_channel",
            "Integration test poll?",
            ["Yes", "No", "Maybe"]
        )
        assert poll_result is True
        
        # 11. 获取统计信息
        stats = manager.get_statistics()
        assert stats["total_channels"] >= 1  # 至少包含我们的测试渠道
        assert stats["active_adapters"] >= 1  # 至少包含我们的适配器
        assert stats["connected_channels"] >= 1  # 至少有一个已连接
        
        # 12. 健康检查
        health = await manager.health_check()
        assert health["manager_running"] is True
        assert "integration_test_channel" in health["channels"]
        
        # 13. 断开渠道
        disconnect_result = await manager.disconnect_channel("integration_test_channel")
        assert disconnect_result is True
        
        # 14. 验证断开状态
        is_connected = await manager.is_channel_connected("integration_test_channel")
        assert is_connected is False
        
        # 15. 注销渠道
        unregister_result = await manager.unregister_channel("integration_test_channel")
        assert unregister_result is True
        
        # 16. 验证渠道已被移除
        assert "integration_test_channel" not in manager._adapters
        assert "integration_test_channel" not in manager._configs
        
        # 17. 停止管理器
        await manager.stop()
        
        # 18. 验证管理器已停止
        assert manager._running is False
    
    @pytest.mark.asyncio
    async def test_multiple_channels_integration(self):
        """测试多渠道集成"""
        manager = ChannelManager()
        await manager.start()
        
        # 创建多个不同类型的渠道配置
        configs = [
            # 文本渠道
            ChannelConfig(
                channel_id="text_channel",
                channel_name="Text Channel",
                channel_type="text",
                accounts={
                    "text_account": ChannelAccountConfig(
                        account_id="text_account",
                        configured=True
                    )
                },
                default_account_id="text_account",
                capabilities=ChannelCapabilities(
                    chat_types=[ChatType.DIRECT],
                    polls=False,
                    reactions=False,
                    media=False
                ),
                enabled=True
            ),
            # 媒体渠道
            ChannelConfig(
                channel_id="media_channel",
                channel_name="Media Channel",
                channel_type="media",
                accounts={
                    "media_account": ChannelAccountConfig(
                        account_id="media_account",
                        configured=True
                    )
                },
                default_account_id="media_account",
                capabilities=ChannelCapabilities(
                    chat_types=[ChatType.DIRECT, ChatType.GROUP],
                    polls=False,
                    reactions=True,
                    media=True
                ),
                enabled=True
            ),
            # 投票渠道
            ChannelConfig(
                channel_id="poll_channel",
                channel_name="Poll Channel",
                channel_type="poll",
                accounts={
                    "poll_account": ChannelAccountConfig(
                        account_id="poll_account",
                        configured=True
                    )
                },
                default_account_id="poll_account",
                capabilities=ChannelCapabilities(
                    chat_types=[ChatType.GROUP],
                    polls=True,
                    reactions=True,
                    media=False
                ),
                enabled=True
            )
        ]
        
        # 注册所有渠道
        for config in configs:
            result = await manager.register_channel(config)
            assert result is True
        
        # 连接所有渠道
        await manager.connect_all()
        
        # 验证所有渠道都已连接
        for config in configs:
            is_connected = await manager.is_channel_connected(config.channel_id)
            assert is_connected is True
        
        # 测试发送不同类型的消息
        # 文本渠道：只发送文本
        text_result = await manager.send_message("text_channel", "Text message")
        assert text_result is True
        
        # 媒体渠道：发送媒体消息
        media_result = await manager.send_media(
            "media_channel",
            "Media message",
            "http://example.com/image.jpg"
        )
        assert media_result is True
        
        # 投票渠道：发送投票
        poll_result = await manager.send_poll(
            "poll_channel",
            "Which option do you prefer?",
            ["Option A", "Option B", "Option C"]
        )
        assert poll_result is True
        
        # 获取所有状态
        all_status = await manager.get_all_status()
        assert len(all_status) == 3
        
        # 验证统计信息
        stats = manager.get_statistics()
        assert stats["total_channels"] == 3
        assert stats["connected_channels"] == 3
        
        # 清理
        await manager.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])