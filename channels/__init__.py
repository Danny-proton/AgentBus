"""
AgentBus渠道系统

提供统一的渠道适配器框架，支持多种消息类型和渠道配置接口。
"""

from typing import List
from .base import (
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

__version__ = "1.0.0"
__all__ = [
    "MessageType",
    "ChatType", 
    "ConnectionStatus",
    "ChannelState",
    "MessageMetadata",
    "Message",
    "ChannelCapabilities",
    "ChannelAccountConfig", 
    "ChannelConfig",
    "ChannelStatus",
    "ChannelAdapter",
    "ChannelRegistry",
]

# 全局渠道注册表实例
channel_registry = ChannelRegistry()


def register_channel_type(channel_type: str):
    """渠道类型装饰器"""
    def decorator(factory):
        channel_registry.register_factory(channel_type, factory)
        return factory
    return decorator


def create_channel_adapter(config: ChannelConfig) -> ChannelAdapter:
    """创建渠道适配器"""
    return channel_registry.create_adapter(config)


def get_channel_adapter(channel_id: str) -> ChannelAdapter:
    """获取渠道适配器"""
    adapter = channel_registry.get_adapter(channel_id)
    if not adapter:
        raise ValueError(f"渠道适配器未找到: {channel_id}")
    return adapter


def list_channel_adapters() -> List[ChannelAdapter]:
    """列出所有渠道适配器"""
    return channel_registry.list_adapters()


# 导入常用枚举和类型
from .base import (
    MessageType,
    ChatType,
    ConnectionStatus,
    ChannelState,
)

# 导入消息和配置类
from .base import (
    MessageMetadata,
    Message,
    ChannelCapabilities,
    ChannelAccountConfig,
    ChannelConfig,
    ChannelStatus,
)

# 导入核心适配器和注册表
from .base import (
    ChannelAdapter,
    ChannelRegistry,
)