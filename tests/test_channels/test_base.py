"""
AgentBus渠道基础功能测试

测试渠道系统的基础类和数据结构，包括：
- 消息类型和枚举
- 消息格式和元数据
- 渠道配置和能力
- 渠道适配器抽象类
- 渠道注册表
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
import json
import uuid

from agentbus.channels.base import (
    MessageType,
    ChatType, 
    ConnectionStatus,
    ChannelState,
    MessageMetadata,
    Message,
    ChannelCapabilities,
    ChannelAccountConfig,
    ChannelConfig,
    ChannelStatus,
    ChannelAdapter,
    ChannelRegistry,
)


class TestMessageTypes:
    """测试消息类型枚举"""
    
    def test_message_type_values(self):
        """测试消息类型枚举值"""
        assert MessageType.TEXT == "text"
        assert MessageType.MEDIA == "media"
        assert MessageType.POLL == "poll"
        assert MessageType.COMMAND == "command"
        assert MessageType.SYSTEM == "system"
        assert MessageType.REPLY == "reply"
        assert MessageType.REACTION == "reaction"
    
    def test_message_type_from_string(self):
        """测试从字符串创建消息类型"""
        assert MessageType("text") == MessageType.TEXT
        assert MessageType("media") == MessageType.MEDIA
        
        with pytest.raises(ValueError):
            MessageType("invalid_type")


class TestChatTypes:
    """测试聊天类型枚举"""
    
    def test_chat_type_values(self):
        """测试聊天类型枚举值"""
        assert ChatType.DIRECT == "direct"
        assert ChatType.GROUP == "group"
        assert ChatType.CHANNEL == "channel"
        assert ChatType.THREAD == "thread"
    
    def test_chat_type_from_string(self):
        """测试从字符串创建聊天类型"""
        assert ChatType("direct") == ChatType.DIRECT
        assert ChatType("group") == ChatType.GROUP
        
        with pytest.raises(ValueError):
            ChatType("invalid_type")


class TestConnectionStatus:
    """测试连接状态枚举"""
    
    def test_connection_status_values(self):
        """测试连接状态枚举值"""
        assert ConnectionStatus.DISCONNECTED == "disconnected"
        assert ConnectionStatus.CONNECTING == "connecting"
        assert ConnectionStatus.CONNECTED == "connected"
        assert ConnectionStatus.RECONNECTING == "reconnecting"
        assert ConnectionStatus.ERROR == "error"


class TestChannelState:
    """测试渠道状态枚举"""
    
    def test_channel_state_values(self):
        """测试渠道状态枚举值"""
        assert ChannelState.UNCONFIGURED == "unconfigured"
        assert ChannelState.CONFIGURED == "configured"
        assert ChannelState.ENABLED == "enabled"
        assert ChannelState.DISABLED == "disabled"
        assert ChannelState.RUNNING == "running"
        assert ChannelState.STOPPED == "stopped"


class TestMessageMetadata:
    """测试消息元数据"""
    
    def test_default_metadata(self):
        """测试默认元数据"""
        metadata = MessageMetadata()
        
        assert metadata.id is not None
        assert isinstance(metadata.timestamp, datetime)
        assert metadata.sender_id is None
        assert metadata.sender_name is None
        assert metadata.sender_username is None
        assert metadata.channel_id is None
        assert metadata.channel_name is None
        assert metadata.reply_to_id is None
        assert metadata.thread_id is None
        assert metadata.chat_type is None
        assert metadata.media_urls == []
        assert metadata.reactions == {}
        assert metadata.edited is False
        assert metadata.edited_at is None
        assert metadata.mentions == []
        assert metadata.tags == []
        assert metadata.custom_data == {}
    
    def test_custom_metadata(self):
        """测试自定义元数据"""
        metadata = MessageMetadata(
            sender_id="user123",
            sender_name="Test User",
            channel_id="channel456",
            chat_type=ChatType.GROUP,
            mentions=["@user1", "@user2"],
            tags=["important", "urgent"]
        )
        
        assert metadata.sender_id == "user123"
        assert metadata.sender_name == "Test User"
        assert metadata.channel_id == "channel456"
        assert metadata.chat_type == ChatType.GROUP
        assert metadata.mentions == ["@user1", "@user2"]
        assert metadata.tags == ["important", "urgent"]
    
    def test_to_dict(self):
        """测试转换为字典"""
        metadata = MessageMetadata(
            id="test_id",
            sender_id="user123",
            channel_id="channel456",
            chat_type=ChatType.DIRECT,
            mentions=["@user1"]
        )
        
        result = metadata.to_dict()
        
        assert result["id"] == "test_id"
        assert result["sender_id"] == "user123"
        assert result["channel_id"] == "channel456"
        assert result["chat_type"] == "direct"
        assert result["mentions"] == ["@user1"]
        assert "timestamp" in result
        assert result["media_urls"] == []
        assert result["reactions"] == {}
        assert result["edited"] is False
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "id": "test_id",
            "sender_id": "user123",
            "channel_id": "channel456",
            "chat_type": "direct",
            "mentions": ["@user1"],
            "media_urls": ["http://example.com/image.jpg"],
            "reactions": {"👍": 5},
            "edited": True
        }
        
        metadata = MessageMetadata.from_dict(data)
        
        assert metadata.id == "test_id"
        assert metadata.sender_id == "user123"
        assert metadata.channel_id == "channel456"
        assert metadata.chat_type == ChatType.DIRECT
        assert metadata.mentions == ["@user1"]
        assert metadata.media_urls == ["http://example.com/image.jpg"]
        assert metadata.reactions == {"👍": 5}
        assert metadata.edited is True
        assert isinstance(metadata.timestamp, datetime)
    
    def test_serialization_roundtrip(self):
        """测试序列化往返"""
        original = MessageMetadata(
            id="test_id",
            sender_id="user123",
            channel_id="channel456",
            chat_type=ChatType.GROUP,
            mentions=["@user1"],
            tags=["test"],
            custom_data={"key": "value"}
        )
        
        # 转换为字典然后再转回来
        dict_data = original.to_dict()
        restored = MessageMetadata.from_dict(dict_data)
        
        # 比较关键字段
        assert restored.id == original.id
        assert restored.sender_id == original.sender_id
        assert restored.channel_id == original.channel_id
        assert restored.chat_type == original.chat_type
        assert restored.mentions == original.mentions
        assert restored.tags == original.tags
        assert restored.custom_data == original.custom_data
        assert isinstance(restored.timestamp, datetime)


class TestMessage:
    """测试标准化消息格式"""
    
    def test_text_message(self):
        """测试文本消息"""
        message = Message(
            type=MessageType.TEXT,
            content="Hello, World!"
        )
        
        assert message.type == MessageType.TEXT
        assert message.content == "Hello, World!"
        assert isinstance(message.metadata, MessageMetadata)
        assert message.raw_data is None
    
    def test_message_with_metadata(self):
        """测试带元数据的消息"""
        metadata = MessageMetadata(
            sender_id="user123",
            channel_id="channel456"
        )
        
        message = Message(
            type=MessageType.COMMAND,
            content="/help",
            metadata=metadata,
            raw_data={"command": "help"}
        )
        
        assert message.type == MessageType.COMMAND
        assert message.content == "/help"
        assert message.metadata.sender_id == "user123"
        assert message.metadata.channel_id == "channel456"
        assert message.raw_data == {"command": "help"}
    
    def test_to_dict(self):
        """测试消息转换为字典"""
        metadata = MessageMetadata(sender_id="user123")
        message = Message(
            type=MessageType.TEXT,
            content="test message",
            metadata=metadata,
            raw_data={"raw": "data"}
        )
        
        result = message.to_dict()
        
        assert result["type"] == "text"
        assert result["content"] == "test message"
        assert result["metadata"]["sender_id"] == "user123"
        assert result["raw_data"] == {"raw": "data"}
    
    def test_from_dict(self):
        """测试从字典创建消息"""
        data = {
            "type": "text",
            "content": "test message",
            "metadata": {
                "sender_id": "user123",
                "chat_type": "direct"
            },
            "raw_data": {"raw": "data"}
        }
        
        message = Message.from_dict(data)
        
        assert message.type == MessageType.TEXT
        assert message.content == "test message"
        assert message.metadata.sender_id == "user123"
        assert message.metadata.chat_type == ChatType.DIRECT
        assert message.raw_data == {"raw": "data"}
    
    def test_serialization_roundtrip(self):
        """测试消息序列化往返"""
        original = Message(
            type=MessageType.REPLY,
            content="reply content",
            metadata=MessageMetadata(
                sender_id="user123",
                channel_id="channel456",
                reply_to_id="original_msg_id"
            ),
            raw_data={"reply_to": "original"}
        )
        
        # 转换为字典然后再转回来
        dict_data = original.to_dict()
        restored = Message.from_dict(dict_data)
        
        assert restored.type == original.type
        assert restored.content == original.content
        assert restored.metadata.sender_id == original.metadata.sender_id
        assert restored.metadata.channel_id == original.metadata.channel_id
        assert restored.metadata.reply_to_id == original.metadata.reply_to_id
        assert restored.raw_data == original.raw_data


class TestChannelCapabilities:
    """测试渠道能力配置"""
    
    def test_default_capabilities(self):
        """测试默认能力配置"""
        capabilities = ChannelCapabilities()
        
        assert capabilities.chat_types == [ChatType.DIRECT]
        assert capabilities.polls is False
        assert capabilities.reactions is False
        assert capabilities.edit is False
        assert capabilities.unsend is False
        assert capabilities.reply is False
        assert capabilities.effects is False
        assert capabilities.group_management is False
        assert capabilities.threads is False
        assert capabilities.media is False
        assert capabilities.native_commands is False
        assert capabilities.block_streaming is False
    
    def test_custom_capabilities(self):
        """测试自定义能力配置"""
        capabilities = ChannelCapabilities(
            chat_types=[ChatType.DIRECT, ChatType.GROUP],
            polls=True,
            reactions=True,
            reply=True,
            media=True,
            group_management=True
        )
        
        assert capabilities.chat_types == [ChatType.DIRECT, ChatType.GROUP]
        assert capabilities.polls is True
        assert capabilities.reactions is True
        assert capabilities.reply is True
        assert capabilities.media is True
        assert capabilities.group_management is True
        assert capabilities.edit is False  # 默认值


class TestChannelAccountConfig:
    """测试渠道账户配置"""
    
    def test_default_account_config(self):
        """测试默认账户配置"""
        config = ChannelAccountConfig(account_id="test123")
        
        assert config.account_id == "test123"
        assert config.name is None
        assert config.enabled is True
        assert config.configured is False
        assert config.token is None
        assert config.token_source is None
        assert config.custom_settings == {}
        assert config.media_limits == {}
        assert config.security_settings == {}
    
    def test_custom_account_config(self):
        """测试自定义账户配置"""
        config = ChannelAccountConfig(
            account_id="test123",
            name="Test Account",
            enabled=False,
            configured=True,
            token="secret_token",
            token_source="environment",
            custom_settings={"theme": "dark"},
            media_limits={"max_size": 10485760},
            security_settings={"2fa_enabled": True}
        )
        
        assert config.account_id == "test123"
        assert config.name == "Test Account"
        assert config.enabled is False
        assert config.configured is True
        assert config.token == "secret_token"
        assert config.token_source == "environment"
        assert config.custom_settings == {"theme": "dark"}
        assert config.media_limits == {"max_size": 10485760}
        assert config.security_settings == {"2fa_enabled": True}
    
    def test_to_dict(self):
        """测试转换为字典"""
        config = ChannelAccountConfig(
            account_id="test123",
            name="Test Account",
            token="secret"
        )
        
        result = config.to_dict()
        
        assert result["account_id"] == "test123"
        assert result["name"] == "Test Account"
        assert result["enabled"] is True
        assert result["configured"] is False
        assert result["token"] == "secret"
        assert result["custom_settings"] == {}
        assert result["media_limits"] == {}
        assert result["security_settings"] == {}
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "account_id": "test123",
            "name": "Test Account",
            "enabled": False,
            "configured": True,
            "token": "secret",
            "custom_settings": {"key": "value"}
        }
        
        config = ChannelAccountConfig.from_dict(data)
        
        assert config.account_id == "test123"
        assert config.name == "Test Account"
        assert config.enabled is False
        assert config.configured is True
        assert config.token == "secret"
        assert config.custom_settings == {"key": "value"}


class TestChannelConfig:
    """测试渠道配置"""
    
    def test_default_channel_config(self):
        """测试默认渠道配置"""
        config = ChannelConfig(
            channel_id="test123",
            channel_name="Test Channel",
            channel_type="test"
        )
        
        assert config.channel_id == "test123"
        assert config.channel_name == "Test Channel"
        assert config.channel_type == "test"
        assert config.accounts == {}
        assert config.default_account_id is None
        assert isinstance(config.capabilities, ChannelCapabilities)
        assert config.settings == {}
        assert config.enabled is True
    
    def test_full_channel_config(self):
        """测试完整渠道配置"""
        account_config = ChannelAccountConfig(
            account_id="account123",
            name="Test Account",
            configured=True
        )
        
        capabilities = ChannelCapabilities(
            chat_types=[ChatType.DIRECT, ChatType.GROUP],
            polls=True,
            media=True
        )
        
        config = ChannelConfig(
            channel_id="channel123",
            channel_name="Test Channel",
            channel_type="test",
            accounts={"account123": account_config},
            default_account_id="account123",
            capabilities=capabilities,
            settings={"auto_reconnect": True},
            enabled=False
        )
        
        assert config.channel_id == "channel123"
        assert config.channel_name == "Test Channel"
        assert config.channel_type == "test"
        assert "account123" in config.accounts
        assert config.default_account_id == "account123"
        assert config.capabilities.polls is True
        assert config.capabilities.media is True
        assert config.settings == {"auto_reconnect": True}
        assert config.enabled is False
    
    def test_to_dict(self):
        """测试转换为字典"""
        account_config = ChannelAccountConfig(account_id="account123")
        config = ChannelConfig(
            channel_id="channel123",
            channel_name="Test Channel",
            channel_type="test",
            accounts={"account123": account_config},
            default_account_id="account123",
            settings={"key": "value"}
        )
        
        result = config.to_dict()
        
        assert result["channel_id"] == "channel123"
        assert result["channel_name"] == "Test Channel"
        assert result["channel_type"] == "test"
        assert "account123" in result["accounts"]
        assert result["default_account_id"] == "account123"
        assert result["settings"] == {"key": "value"}
        assert result["enabled"] is True
        
        # 检查capabilities序列化
        assert "capabilities" in result
        assert result["capabilities"]["chat_types"] == ["direct"]
        assert result["capabilities"]["polls"] is False
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "channel_id": "channel123",
            "channel_name": "Test Channel",
            "channel_type": "test",
            "accounts": {
                "account123": {
                    "account_id": "account123",
                    "name": "Test Account",
                    "enabled": True
                }
            },
            "default_account_id": "account123",
            "capabilities": {
                "chat_types": ["direct", "group"],
                "polls": True,
                "reactions": True
            },
            "settings": {"key": "value"},
            "enabled": False
        }
        
        config = ChannelConfig.from_dict(data)
        
        assert config.channel_id == "channel123"
        assert config.channel_name == "Test Channel"
        assert config.channel_type == "test"
        assert "account123" in config.accounts
        assert config.default_account_id == "account123"
        assert config.capabilities.polls is True
        assert config.capabilities.reactions is True
        assert config.settings == {"key": "value"}
        assert config.enabled is False


class TestChannelStatus:
    """测试渠道状态"""
    
    def test_default_status(self):
        """测试默认状态"""
        status = ChannelStatus(account_id="test123")
        
        assert status.account_id == "test123"
        assert status.state == ChannelState.UNCONFIGURED
        assert status.connection_status == ConnectionStatus.DISCONNECTED
        assert status.connected is False
        assert status.running is False
        assert status.last_connected_at is None
        assert status.last_disconnected_at is None
        assert status.last_error is None
        assert status.reconnect_attempts == 0
        assert status.last_message_at is None
        assert status.last_event_at is None
        assert status.runtime_data == {}
    
    def test_custom_status(self):
        """测试自定义状态"""
        now = datetime.now()
        status = ChannelStatus(
            account_id="test123",
            state=ChannelState.RUNNING,
            connection_status=ConnectionStatus.CONNECTED,
            connected=True,
            running=True,
            last_connected_at=now,
            last_error="Previous error",
            reconnect_attempts=3
        )
        
        assert status.account_id == "test123"
        assert status.state == ChannelState.RUNNING
        assert status.connection_status == ConnectionStatus.CONNECTED
        assert status.connected is True
        assert status.running is True
        assert status.last_connected_at == now
        assert status.last_error == "Previous error"
        assert status.reconnect_attempts == 3
    
    def test_to_dict(self):
        """测试转换为字典"""
        now = datetime.now()
        status = ChannelStatus(
            account_id="test123",
            state=ChannelState.ENABLED,
            connection_status=ConnectionStatus.CONNECTED,
            last_connected_at=now
        )
        
        result = status.to_dict()
        
        assert result["account_id"] == "test123"
        assert result["state"] == "enabled"
        assert result["connection_status"] == "connected"
        assert result["connected"] is False
        assert result["running"] is False
        assert "last_connected_at" in result
        assert result["reconnect_attempts"] == 0
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "account_id": "test123",
            "state": "running",
            "connection_status": "connected",
            "connected": True,
            "running": True,
            "last_connected_at": "2023-01-01T00:00:00",
            "reconnect_attempts": 2
        }
        
        status = ChannelStatus.from_dict(data)
        
        assert status.account_id == "test123"
        assert status.state == ChannelState.RUNNING
        assert status.connection_status == ConnectionStatus.CONNECTED
        assert status.connected is True
        assert status.running is True
        assert status.reconnect_attempts == 2
        assert isinstance(status.last_connected_at, datetime)


class TestChannelAdapter:
    """测试渠道适配器抽象基类"""
    
    def test_abstract_methods(self):
        """测试抽象方法"""
        from abc import ABC
        from agentbus.channels.base import ChannelAdapter
        
        # 验证ChannelAdapter是抽象基类
        assert issubclass(ChannelAdapter, ABC)
        
        # 验证不能直接实例化
        with pytest.raises(TypeError):
            ChannelAdapter(MagicMock())
    
    def test_adapter_interface(self):
        """测试适配器接口"""
        # 创建一个具体的适配器实现来测试接口
        config = ChannelConfig(
            channel_id="test123",
            channel_name="Test Channel",
            channel_type="test"
        )
        
        class TestAdapter(ChannelAdapter):
            def __init__(self, config):
                super().__init__(config)
            
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
                return True
            
            async def disconnect(self, account_id):
                return True
            
            async def is_connected(self, account_id):
                return True
            
            async def send_message(self, message, account_id=None):
                return True
            
            async def send_media(self, message, media_url, account_id=None):
                return True
            
            async def send_poll(self, question, options, account_id=None):
                return True
            
            async def get_status(self, account_id):
                return ChannelStatus(account_id=account_id)
            
            async def configure_account(self, account_config):
                return True
        
        adapter = TestAdapter(config)
        
        # 测试基本属性
        assert adapter.channel_id == "test123"
        assert adapter.channel_name == "Test Channel"
        assert isinstance(adapter.capabilities, ChannelCapabilities)
        
        # 测试消息处理器管理
        def test_handler(message):
            pass
        
        adapter.add_message_handler(test_handler)
        assert test_handler in adapter._message_handlers
        
        adapter.remove_message_handler(test_handler)
        assert test_handler not in adapter._message_handlers
        
        # 测试事件处理器管理
        def test_event_handler(event_type, data):
            pass
        
        adapter.add_event_handler(test_event_handler)
        assert test_event_handler in adapter._event_handlers
        
        adapter.remove_event_handler(test_event_handler)
        assert test_event_handler not in adapter._event_handlers
        
        # 测试字符串表示
        assert str(adapter) == "TestAdapter(test123:Test Channel)"
    
    @pytest.mark.asyncio
    async def test_message_notification(self):
        """测试消息通知机制"""
        config = ChannelConfig(
            channel_id="test123",
            channel_name="Test Channel",
            channel_type="test"
        )
        
        class TestAdapter(ChannelAdapter):
            def __init__(self, config):
                super().__init__(config)
                self.messages_received = []
            
            @property
            def channel_id(self):
                return "test123"
            
            @property
            def channel_name(self):
                return "Test Channel"
            
            @property
            def capabilities(self):
                return ChannelCapabilities()
            
            async def connect(self, account_id):
                return True
            
            async def disconnect(self, account_id):
                return True
            
            async def is_connected(self, account_id):
                return True
            
            async def send_message(self, message, account_id=None):
                return True
            
            async def send_media(self, message, media_url, account_id=None):
                return True
            
            async def send_poll(self, question, options, account_id=None):
                return True
            
            async def get_status(self, account_id):
                return ChannelStatus(account_id=account_id)
            
            async def configure_account(self, account_config):
                return True
        
        adapter = TestAdapter(config)
        
        # 添加消息处理器
        def message_handler(message):
            adapter.messages_received.append(message)
        
        adapter.add_message_handler(message_handler)
        
        # 创建测试消息
        test_message = Message(
            type=MessageType.TEXT,
            content="test message"
        )
        
        # 触发消息通知
        adapter._notify_message_handlers(test_message)
        
        # 验证消息被接收
        assert len(adapter.messages_received) == 1
        assert adapter.messages_received[0] == test_message
        
        # 测试事件通知
        events_received = []
        def event_handler(event_type, data):
            events_received.append((event_type, data))
        
        adapter.add_event_handler(event_handler)
        
        # 触发事件通知
        adapter._notify_event_handlers("test_event", {"data": "test"})
        
        # 验证事件被接收
        assert len(events_received) == 1
        assert events_received[0] == ("test_event", {"data": "test"})
    
    def test_optional_methods(self):
        """测试可选方法实现"""
        config = ChannelConfig(
            channel_id="test123",
            channel_name="Test Channel",
            channel_type="test"
        )
        
        class MinimalAdapter(ChannelAdapter):
            def __init__(self, config):
                super().__init__(config)
            
            @property
            def channel_id(self):
                return "test123"
            
            @property
            def channel_name(self):
                return "Test Channel"
            
            @property
            def capabilities(self):
                return ChannelCapabilities()
            
            async def connect(self, account_id):
                return True
            
            async def disconnect(self, account_id):
                return True
            
            async def is_connected(self, account_id):
                return True
            
            async def send_message(self, message, account_id=None):
                return True
            
            async def send_media(self, message, media_url, account_id=None):
                return True
            
            async def send_poll(self, question, options, account_id=None):
                return True
            
            async def get_status(self, account_id):
                return ChannelStatus(account_id=account_id)
            
            async def configure_account(self, account_config):
                return True
        
        adapter = MinimalAdapter(config)
        
        # 测试可选方法
        assert asyncio.run(adapter.authenticate("test_account")) is True
        
        assert asyncio.run(adapter.validate_config(
            ChannelAccountConfig(account_id="test")
        )) == []
        
        assert asyncio.run(adapter.get_directory_info("test_account")) == {}
        
        assert asyncio.run(adapter.resolve_target("test_target", "test_account")) == "test_target"


class TestChannelRegistry:
    """测试渠道注册表"""
    
    def test_registry_creation(self):
        """测试注册表创建"""
        registry = ChannelRegistry()
        
        assert registry._adapters == {}
        assert registry._factories == {}
    
    def test_factory_registration(self):
        """测试工厂注册"""
        registry = ChannelRegistry()
        
        def test_factory(config):
            return MagicMock()
        
        registry.register_factory("test_type", test_factory)
        
        assert "test_type" in registry._factories
        assert registry._factories["test_type"] == test_factory
    
    def test_adapter_creation(self):
        """测试适配器创建"""
        registry = ChannelRegistry()
        
        def test_factory(config):
            mock_adapter = MagicMock()
            mock_adapter.channel_id = config.channel_id
            return mock_adapter
        
        registry.register_factory("test_type", test_factory)
        
        config = ChannelConfig(
            channel_id="test123",
            channel_name="Test Channel",
            channel_type="test_type"
        )
        
        adapter = registry.create_adapter(config)
        
        assert adapter.channel_id == "test123"
    
    def test_create_adapter_unknown_type(self):
        """测试创建未知类型适配器"""
        registry = ChannelRegistry()
        
        config = ChannelConfig(
            channel_id="test123",
            channel_name="Test Channel",
            channel_type="unknown_type"
        )
        
        with pytest.raises(ValueError, match="未知的渠道类型"):
            registry.create_adapter(config)
    
    def test_adapter_registration(self):
        """测试适配器注册"""
        registry = ChannelRegistry()
        
        adapter = MagicMock()
        adapter.channel_id = "test123"
        
        registry.register_adapter(adapter)
        
        assert "test123" in registry._adapters
        assert registry._adapters["test123"] == adapter
    
    def test_get_adapter(self):
        """测试获取适配器"""
        registry = ChannelRegistry()
        
        adapter = MagicMock()
        adapter.channel_id = "test123"
        registry._adapters["test123"] = adapter
        
        result = registry.get_adapter("test123")
        assert result == adapter
        
        result = registry.get_adapter("nonexistent")
        assert result is None
    
    def test_list_adapters(self):
        """测试列出适配器"""
        registry = ChannelRegistry()
        
        adapter1 = MagicMock()
        adapter1.channel_id = "test123"
        
        adapter2 = MagicMock()
        adapter2.channel_id = "test456"
        
        registry._adapters["test123"] = adapter1
        registry._adapters["test456"] = adapter2
        
        adapters = registry.list_adapters()
        
        assert len(adapters) == 2
        assert adapter1 in adapters
        assert adapter2 in adapters
    
    def test_unregister_adapter(self):
        """测试注销适配器"""
        registry = ChannelRegistry()
        
        adapter = MagicMock()
        adapter.channel_id = "test123"
        registry._adapters["test123"] = adapter
        
        registry.unregister_adapter("test123")
        
        assert "test123" not in registry._adapters
    
    def test_unregister_nonexistent_adapter(self):
        """测试注销不存在的适配器"""
        registry = ChannelRegistry()
        
        # 不应该抛出异常
        registry.unregister_adapter("nonexistent")


class TestMessageSerialization:
    """测试消息序列化功能"""
    
    def test_json_serialization(self):
        """测试JSON序列化"""
        metadata = MessageMetadata(
            sender_id="user123",
            channel_id="channel456",
            chat_type=ChatType.DIRECT
        )
        
        message = Message(
            type=MessageType.TEXT,
            content="Hello World",
            metadata=metadata,
            raw_data={"raw": "data"}
        )
        
        # 转换为字典
        message_dict = message.to_dict()
        
        # 测试JSON序列化
        json_str = json.dumps(message_dict, ensure_ascii=False, indent=2)
        
        # 验证JSON格式正确
        parsed_data = json.loads(json_str)
        assert parsed_data["type"] == "text"
        assert parsed_data["content"] == "Hello World"
        assert parsed_data["metadata"]["sender_id"] == "user123"
    
    def test_complex_metadata_serialization(self):
        """测试复杂元数据序列化"""
        metadata = MessageMetadata(
            sender_id="user123",
            channel_id="channel456",
            chat_type=ChatType.GROUP,
            mentions=["@user1", "@user2"],
            tags=["important", "urgent"],
            reactions={"👍": 5, "❤️": 3},
            custom_data={
                "priority": "high",
                "category": "alert",
                "nested_data": {"level": 1, "enabled": True}
            }
        )
        
        message = Message(
            type=MessageType.SYSTEM,
            content="System notification",
            metadata=metadata
        )
        
        # 序列化
        message_dict = message.to_dict()
        json_str = json.dumps(message_dict)
        restored_dict = json.loads(json_str)
        
        # 反序列化
        restored_message = Message.from_dict(restored_dict)
        
        # 验证复杂数据结构
        assert restored_message.metadata.mentions == ["@user1", "@user2"]
        assert restored_message.metadata.tags == ["important", "urgent"]
        assert restored_message.metadata.reactions == {"👍": 5, "❤️": 3}
        assert restored_message.metadata.custom_data["priority"] == "high"
        assert restored_message.metadata.custom_data["nested_data"]["level"] == 1
        assert restored_message.metadata.custom_data["nested_data"]["enabled"] is True


class TestErrorHandling:
    """测试错误处理"""
    
    def test_invalid_chat_type(self):
        """测试无效聊天类型"""
        with pytest.raises(ValueError):
            ChatType("invalid_type")
    
    def test_invalid_message_type(self):
        """测试无效消息类型"""
        with pytest.raises(ValueError):
            MessageType("invalid_type")
    
    def test_invalid_connection_status(self):
        """测试无效连接状态"""
        with pytest.raises(ValueError):
            ConnectionStatus("invalid_status")
    
    def test_invalid_channel_state(self):
        """测试无效渠道状态"""
        with pytest.raises(ValueError):
            ChannelState("invalid_state")
    
    def test_malformed_metadata_dict(self):
        """测试格式错误的元数据字典"""
        # 缺少必需字段但有有效的timestamp
        malformed_data = {
            "timestamp": datetime.now().isoformat(),
            "sender_id": "user123"
            # 缺少id字段
        }
        
        # 应该能处理并提供默认值
        metadata = MessageMetadata.from_dict(malformed_data)
        assert metadata.id is not None  # 应该生成默认ID
        assert metadata.sender_id == "user123"
    
    def test_invalid_datetime_format(self):
        """测试无效日期时间格式"""
        data = {
            "id": "test123",
            "timestamp": "invalid_datetime_format",
            "sender_id": "user123"
        }
        
        # 应该抛出异常或处理错误格式
        with pytest.raises(ValueError):
            MessageMetadata.from_dict(data)


# 集成测试
class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_message_workflow(self):
        """测试完整消息工作流"""
        # 1. 创建消息
        metadata = MessageMetadata(
            sender_id="user123",
            channel_id="channel456",
            chat_type=ChatType.DIRECT
        )
        
        message = Message(
            type=MessageType.TEXT,
            content="Hello World",
            metadata=metadata
        )
        
        # 2. 序列化
        message_dict = message.to_dict()
        
        # 3. 传输（模拟）
        json_str = json.dumps(message_dict)
        
        # 4. 反序列化
        received_dict = json.loads(json_str)
        received_message = Message.from_dict(received_dict)
        
        # 5. 验证
        assert received_message.type == MessageType.TEXT
        assert received_message.content == "Hello World"
        assert received_message.metadata.sender_id == "user123"
        assert received_message.metadata.channel_id == "channel456"
        assert received_message.metadata.chat_type == ChatType.DIRECT
    
    def test_channel_config_workflow(self):
        """测试渠道配置工作流"""
        # 1. 创建账户配置
        account_config = ChannelAccountConfig(
            account_id="account123",
            name="Test Account",
            token="secret_token"
        )
        
        # 2. 创建能力配置
        capabilities = ChannelCapabilities(
            chat_types=[ChatType.DIRECT, ChatType.GROUP],
            polls=True,
            reactions=True,
            media=True
        )
        
        # 3. 创建渠道配置
        channel_config = ChannelConfig(
            channel_id="channel123",
            channel_name="Test Channel",
            channel_type="test",
            accounts={"account123": account_config},
            default_account_id="account123",
            capabilities=capabilities
        )
        
        # 4. 序列化
        config_dict = channel_config.to_dict()
        
        # 5. 传输（模拟）
        json_str = json.dumps(config_dict, indent=2)
        
        # 6. 反序列化
        received_dict = json.loads(json_str)
        received_config = ChannelConfig.from_dict(received_dict)
        
        # 7. 验证
        assert received_config.channel_id == "channel123"
        assert received_config.channel_name == "Test Channel"
        assert received_config.channel_type == "test"
        assert "account123" in received_config.accounts
        assert received_config.default_account_id == "account123"
        assert received_config.capabilities.polls is True
        assert received_config.capabilities.reactions is True
        assert received_config.capabilities.media is True
        assert ChatType.GROUP in received_config.capabilities.chat_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])