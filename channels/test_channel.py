"""
AgentBus 测试渠道适配器
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from .base import (
    Message, MessageType, ChatType,
    ChannelConfig, ChannelAccountConfig, ChannelCapabilities,
    ChannelAdapter, ChannelStatus, ChannelState, ConnectionStatus
)
from . import register_channel_type

logger = logging.getLogger(__name__)

class TestAdapter(ChannelAdapter):
    """用于测试和演示的渠道适配器"""
    
    def __init__(self, config: ChannelConfig):
        super().__init__(config)
        self._connected_accounts = set()
        self.logger = logging.getLogger(f"{__name__}.Test")
        self.logger.info(f"TestAdapter 初始化完成: {config.channel_id}")
    
    @property
    def channel_id(self) -> str:
        return self.config.channel_id
    
    @property
    def channel_name(self) -> str:
        return self.config.channel_name
    
    @property
    def capabilities(self) -> ChannelCapabilities:
        return self.config.capabilities
    
    async def connect(self, account_id: str) -> bool:
        """模拟连接逻辑"""
        self.logger.info(f"正在连接测试账户: {account_id}")
        await asyncio.sleep(0.1)
        self._connected_accounts.add(account_id)
        
        self._notify_event_handlers("status_changed", {
            "channel_id": self.channel_id,
            "account_id": account_id,
            "status": "connected"
        })
        return True
    
    async def disconnect(self, account_id: str) -> bool:
        """模拟断开连接"""
        if account_id in self._connected_accounts:
            self._connected_accounts.discard(account_id)
            self._notify_event_handlers("status_changed", {
                "channel_id": self.channel_id,
                "account_id": account_id,
                "status": "disconnected"
            })
        return True
    
    async def is_connected(self, account_id: str) -> bool:
        return account_id in self._connected_accounts
    
    async def send_message(self, message: Message, account_id=None) -> bool:
        self.logger.info(f"发送测试消息: {message.content[:50]}")
        return True
    
    async def send_media(self, message: Message, media_url: str, account_id=None) -> bool:
        self.logger.info(f"发送测试媒体: {media_url}")
        return True
    
    async def send_poll(self, question: str, options: list, account_id=None) -> bool:
        self.logger.info(f"发送测试投票: {question}")
        return True
    
    async def get_status(self, account_id: str) -> ChannelStatus:
        is_conn = account_id in self._connected_accounts
        return ChannelStatus(
            account_id=account_id,
            state=ChannelState.RUNNING if is_conn else ChannelState.STOPPED,
            connection_status=ConnectionStatus.CONNECTED if is_conn else ConnectionStatus.DISCONNECTED,
            connected=is_conn,
            running=is_conn
        )
    
    async def configure_account(self, account_config: ChannelAccountConfig) -> bool:
        self.config.accounts[account_config.account_id] = account_config
        return True

@register_channel_type("test")
def create_test_adapter(config: ChannelConfig) -> ChannelAdapter:
    """创建测试适配器工厂函数"""
    return TestAdapter(config)
