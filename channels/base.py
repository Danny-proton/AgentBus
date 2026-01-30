"""
AgentBus渠道适配器基础框架

基于Moltbot的渠道适配器模式，提供标准化的渠道抽象层。
支持多种消息类型、配置接口和渠道管理功能。
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Set
from uuid import uuid4
import json
import logging
from pathlib import Path


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"
    MEDIA = "media"
    POLL = "poll"
    COMMAND = "command"
    SYSTEM = "system"
    REPLY = "reply"
    REACTION = "reaction"


class ChatType(str, Enum):
    """聊天类型枚举"""
    DIRECT = "direct"
    GROUP = "group"
    CHANNEL = "channel"
    THREAD = "thread"


class ConnectionStatus(str, Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class ChannelState(str, Enum):
    """渠道状态枚举"""
    UNCONFIGURED = "unconfigured"
    CONFIGURED = "configured"
    ENABLED = "enabled"
    DISABLED = "disabled"
    RUNNING = "running"
    STOPPED = "stopped"


@dataclass
class MessageMetadata:
    """消息元数据"""
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    sender_username: Optional[str] = None
    channel_id: Optional[str] = None
    channel_name: Optional[str] = None
    reply_to_id: Optional[str] = None
    thread_id: Optional[str] = None
    chat_type: Optional[ChatType] = None
    media_urls: List[str] = field(default_factory=list)
    reactions: Dict[str, int] = field(default_factory=dict)
    edited: bool = False
    edited_at: Optional[datetime] = None
    mentions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    custom_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "sender_username": self.sender_username,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "reply_to_id": self.reply_to_id,
            "thread_id": self.thread_id,
            "chat_type": self.chat_type.value if self.chat_type else None,
            "media_urls": self.media_urls,
            "reactions": self.reactions,
            "edited": self.edited,
            "edited_at": self.edited_at.isoformat() if self.edited_at else None,
            "mentions": self.mentions,
            "tags": self.tags,
            "custom_data": self.custom_data,
        }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MessageMetadata':
        """从字典创建实例"""
        return cls(
            id=data.get("id", str(uuid4())),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            sender_id=data.get("sender_id"),
            sender_name=data.get("sender_name"),
            sender_username=data.get("sender_username"),
            channel_id=data.get("channel_id"),
            channel_name=data.get("channel_name"),
            reply_to_id=data.get("reply_to_id"),
            thread_id=data.get("thread_id"),
            chat_type=ChatType(data["chat_type"]) if data.get("chat_type") else None,
            media_urls=data.get("media_urls", []),
            reactions=data.get("reactions", {}),
            edited=data.get("edited", False),
            edited_at=datetime.fromisoformat(data["edited_at"]) if data.get("edited_at") else None,
            mentions=data.get("mentions", []),
            tags=data.get("tags", []),
            custom_data=data.get("custom_data", {}),
        )


@dataclass
class Message:
    """标准化消息格式"""
    type: MessageType
    content: str
    metadata: MessageMetadata = field(default_factory=MessageMetadata)
    raw_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "type": self.type.value,
            "content": self.content,
            "metadata": self.metadata.to_dict(),
            "raw_data": self.raw_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """从字典创建实例"""
        return cls(
            type=MessageType(data["type"]),
            content=data["content"],
            metadata=MessageMetadata.from_dict(data["metadata"]),
            raw_data=data.get("raw_data"),
        )


@dataclass
class ChannelCapabilities:
    """渠道能力配置"""
    chat_types: List[ChatType] = field(default_factory=lambda: [ChatType.DIRECT])
    polls: bool = False
    reactions: bool = False
    edit: bool = False
    unsend: bool = False
    reply: bool = False
    effects: bool = False
    group_management: bool = False
    threads: bool = False
    media: bool = False
    native_commands: bool = False
    block_streaming: bool = False


@dataclass
class ChannelAccountConfig:
    """渠道账户配置"""
    account_id: str
    name: Optional[str] = None
    enabled: bool = True
    configured: bool = False
    token: Optional[str] = None
    token_source: Optional[str] = None
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    media_limits: Dict[str, Any] = field(default_factory=dict)
    security_settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "account_id": self.account_id,
            "name": self.name,
            "enabled": self.enabled,
            "configured": self.configured,
            "token": self.token,
            "token_source": self.token_source,
            "custom_settings": self.custom_settings,
            "media_limits": self.media_limits,
            "security_settings": self.security_settings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChannelAccountConfig':
        """从字典创建实例"""
        return cls(
            account_id=data["account_id"],
            name=data.get("name"),
            enabled=data.get("enabled", True),
            configured=data.get("configured", False),
            token=data.get("token"),
            token_source=data.get("token_source"),
            custom_settings=data.get("custom_settings", {}),
            media_limits=data.get("media_limits", {}),
            security_settings=data.get("security_settings", {}),
        )


@dataclass
class ChannelConfig:
    """渠道配置"""
    channel_id: str
    channel_name: str
    channel_type: str
    accounts: Dict[str, ChannelAccountConfig] = field(default_factory=dict)
    default_account_id: Optional[str] = None
    capabilities: ChannelCapabilities = field(default_factory=ChannelCapabilities)
    settings: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "channel_type": self.channel_type,
            "accounts": {k: v.to_dict() for k, v in self.accounts.items()},
            "default_account_id": self.default_account_id,
            "capabilities": {
                "chat_types": [ct.value for ct in self.capabilities.chat_types],
                "polls": self.capabilities.polls,
                "reactions": self.capabilities.reactions,
                "edit": self.capabilities.edit,
                "unsend": self.capabilities.unsend,
                "reply": self.capabilities.reply,
                "effects": self.capabilities.effects,
                "group_management": self.capabilities.group_management,
                "threads": self.capabilities.threads,
                "media": self.capabilities.media,
                "native_commands": self.capabilities.native_commands,
                "block_streaming": self.capabilities.block_streaming,
            },
            "settings": self.settings,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChannelConfig':
        """从字典创建实例"""
        capabilities_data = data.get("capabilities", {})
        capabilities = ChannelCapabilities(
            chat_types=[ChatType(ct) for ct in capabilities_data.get("chat_types", [ChatType.DIRECT.value])],
            polls=capabilities_data.get("polls", False),
            reactions=capabilities_data.get("reactions", False),
            edit=capabilities_data.get("edit", False),
            unsend=capabilities_data.get("unsend", False),
            reply=capabilities_data.get("reply", False),
            effects=capabilities_data.get("effects", False),
            group_management=capabilities_data.get("group_management", False),
            threads=capabilities_data.get("threads", False),
            media=capabilities_data.get("media", False),
            native_commands=capabilities_data.get("native_commands", False),
            block_streaming=capabilities_data.get("block_streaming", False),
        )

        return cls(
            channel_id=data["channel_id"],
            channel_name=data["channel_name"],
            channel_type=data["channel_type"],
            accounts={k: ChannelAccountConfig.from_dict(v) for k, v in data.get("accounts", {}).items()},
            default_account_id=data.get("default_account_id"),
            capabilities=capabilities,
            settings=data.get("settings", {}),
            enabled=data.get("enabled", True),
        )


@dataclass
class ChannelStatus:
    """渠道状态信息"""
    account_id: str
    state: ChannelState = ChannelState.UNCONFIGURED
    connection_status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    connected: bool = False
    running: bool = False
    last_connected_at: Optional[datetime] = None
    last_disconnected_at: Optional[datetime] = None
    last_error: Optional[str] = None
    reconnect_attempts: int = 0
    last_message_at: Optional[datetime] = None
    last_event_at: Optional[datetime] = None
    runtime_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "account_id": self.account_id,
            "state": self.state.value,
            "connection_status": self.connection_status.value,
            "connected": self.connected,
            "running": self.running,
            "last_connected_at": self.last_connected_at.isoformat() if self.last_connected_at else None,
            "last_disconnected_at": self.last_disconnected_at.isoformat() if self.last_disconnected_at else None,
            "last_error": self.last_error,
            "reconnect_attempts": self.reconnect_attempts,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "last_event_at": self.last_event_at.isoformat() if self.last_event_at else None,
            "runtime_data": self.runtime_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChannelStatus':
        """从字典创建实例"""
        return cls(
            account_id=data["account_id"],
            state=ChannelState(data.get("state", ChannelState.UNCONFIGURED.value)),
            connection_status=ConnectionStatus(data.get("connection_status", ConnectionStatus.DISCONNECTED.value)),
            connected=data.get("connected", False),
            running=data.get("running", False),
            last_connected_at=datetime.fromisoformat(data["last_connected_at"]) if data.get("last_connected_at") else None,
            last_disconnected_at=datetime.fromisoformat(data["last_disconnected_at"]) if data.get("last_disconnected_at") else None,
            last_error=data.get("last_error"),
            reconnect_attempts=data.get("reconnect_attempts", 0),
            last_message_at=datetime.fromisoformat(data["last_message_at"]) if data.get("last_message_at") else None,
            last_event_at=datetime.fromisoformat(data["last_event_at"]) if data.get("last_event_at") else None,
            runtime_data=data.get("runtime_data", {}),
        )


class ChannelAdapter(ABC):
    """渠道适配器抽象基类"""
    
    def __init__(self, config: ChannelConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._status_cache: Dict[str, ChannelStatus] = {}
        self._message_handlers: Set[Callable] = set()
        self._event_handlers: Set[Callable] = set()
    
    @property
    @abstractmethod
    def channel_id(self) -> str:
        """获取渠道ID"""
        pass
    
    @property
    @abstractmethod
    def channel_name(self) -> str:
        """获取渠道名称"""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> ChannelCapabilities:
        """获取渠道能力"""
        pass
    
    @abstractmethod
    async def connect(self, account_id: str) -> bool:
        """连接到渠道"""
        pass
    
    @abstractmethod
    async def disconnect(self, account_id: str) -> bool:
        """断开渠道连接"""
        pass
    
    @abstractmethod
    async def is_connected(self, account_id: str) -> bool:
        """检查连接状态"""
        pass
    
    @abstractmethod
    async def send_message(self, message: Message, account_id: Optional[str] = None) -> bool:
        """发送消息"""
        pass
    
    @abstractmethod
    async def send_media(self, message: Message, media_url: str, account_id: Optional[str] = None) -> bool:
        """发送媒体消息"""
        pass
    
    @abstractmethod
    async def send_poll(self, question: str, options: List[str], account_id: Optional[str] = None) -> bool:
        """发送投票"""
        pass
    
    @abstractmethod
    async def get_status(self, account_id: str) -> ChannelStatus:
        """获取渠道状态"""
        pass
    
    @abstractmethod
    async def configure_account(self, account_config: ChannelAccountConfig) -> bool:
        """配置渠道账户"""
        pass
    
    async def authenticate(self, account_id: str) -> bool:
        """认证渠道账户（可选实现）"""
        return True
    
    async def validate_config(self, account_config: ChannelAccountConfig) -> List[str]:
        """验证配置（返回错误信息列表）"""
        return []
    
    async def get_directory_info(self, account_id: str) -> Dict[str, Any]:
        """获取目录信息（用户列表、群组列表等）"""
        return {}
    
    async def resolve_target(self, target: str, account_id: str) -> Optional[str]:
        """解析目标（将显示名称解析为ID）"""
        return target
    
    def add_message_handler(self, handler: Callable[[Message], None]):
        """添加消息处理器"""
        self._message_handlers.add(handler)
    
    def remove_message_handler(self, handler: Callable[[Message], None]):
        """移除消息处理器"""
        self._message_handlers.discard(handler)
    
    def add_event_handler(self, handler: Callable[[str, Any], None]):
        """添加事件处理器"""
        self._event_handlers.add(handler)
    
    def remove_event_handler(self, handler: Callable[[str, Any], None]):
        """移除事件处理器"""
        self._event_handlers.discard(handler)
    
    def _notify_message_handlers(self, message: Message):
        """通知消息处理器"""
        for handler in self._message_handlers:
            try:
                handler(message)
            except Exception as e:
                self.logger.error(f"消息处理器错误: {e}")
    
    def _notify_event_handlers(self, event_type: str, data: Any):
        """通知事件处理器"""
        for handler in self._event_handlers:
            try:
                handler(event_type, data)
            except Exception as e:
                self.logger.error(f"事件处理器错误: {e}")
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.channel_id}:{self.channel_name})"
    
    def __repr__(self) -> str:
        return self.__str__()


class ChannelRegistry:
    """渠道注册表"""
    
    def __init__(self):
        self._adapters: Dict[str, ChannelAdapter] = {}
        self._factories: Dict[str, Callable[[ChannelConfig], ChannelAdapter]] = {}
    
    def register_factory(self, channel_type: str, factory: Callable[[ChannelConfig], ChannelAdapter]):
        """注册渠道工厂"""
        self._factories[channel_type] = factory
    
    def create_adapter(self, config: ChannelConfig) -> ChannelAdapter:
        """创建渠道适配器"""
        factory = self._factories.get(config.channel_type)
        if not factory:
            raise ValueError(f"未知的渠道类型: {config.channel_type}")
        return factory(config)
    
    def register_adapter(self, adapter: ChannelAdapter):
        """注册渠道适配器"""
        self._adapters[adapter.channel_id] = adapter
    
    def get_adapter(self, channel_id: str) -> Optional[ChannelAdapter]:
        """获取渠道适配器"""
        return self._adapters.get(channel_id)
    
    def list_adapters(self) -> List[ChannelAdapter]:
        """列出所有渠道适配器"""
        return list(self._adapters.values())
    
    def unregister_adapter(self, channel_id: str):
        """注销渠道适配器"""
        if channel_id in self._adapters:
            del self._adapters[channel_id]