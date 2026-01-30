"""
AgentBus渠道系统使用示例

展示如何创建和使用渠道适配器。
"""

import asyncio
import logging
from pathlib import Path

from .base import (
    Message, MessageType, ChatType,
    ChannelConfig, ChannelAccountConfig, ChannelCapabilities,
    ChannelAdapter, MessageMetadata
)
from .manager import ChannelManager
from . import register_channel_type


# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 示例：Discord渠道适配器
class DiscordAdapter(ChannelAdapter):
    """Discord渠道适配器示例"""
    
    def __init__(self, config: ChannelConfig):
        super().__init__(config)
        self._connected_accounts = set()
        self.logger = logging.getLogger(f"{__name__}.Discord")
    
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
        """连接到Discord"""
        try:
            # 模拟连接过程
            self.logger.info(f"连接到Discord账户: {account_id}")
            
            # 验证token
            account_config = self.config.accounts.get(account_id)
            if not account_config or not account_config.token:
                self.logger.error(f"Discord账户 {account_id} 缺少token")
                return False
            
            # 模拟连接成功
            await asyncio.sleep(0.1)  # 模拟网络延迟
            self._connected_accounts.add(account_id)
            self._notify_event_handlers("status_changed", {
                "channel_id": self.channel_id,
                "account_id": account_id,
                "status": "connected"
            })
            
            self.logger.info(f"Discord连接成功: {account_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Discord连接失败 {account_id}: {e}")
            return False
    
    async def disconnect(self, account_id: str) -> bool:
        """断开Discord连接"""
        try:
            if account_id in self._connected_accounts:
                self.logger.info(f"断开Discord连接: {account_id}")
                self._connected_accounts.discard(account_id)
                
                self._notify_event_handlers("status_changed", {
                    "channel_id": self.channel_id,
                    "account_id": account_id,
                    "status": "disconnected"
                })
            
            return True
            
        except Exception as e:
            self.logger.error(f"Discord断开失败 {account_id}: {e}")
            return False
    
    async def is_connected(self, account_id: str) -> bool:
        """检查Discord连接状态"""
        return account_id in self._connected_accounts
    
    async def send_message(self, message: Message, account_id=None) -> bool:
        """发送Discord消息"""
        try:
            # 模拟发送消息
            self.logger.info(f"发送Discord消息: {message.content[:50]}...")
            
            # 验证连接
            if not account_id:
                account_id = self.config.default_account_id
            
            if account_id not in self._connected_accounts:
                self.logger.error(f"Discord账户未连接: {account_id}")
                return False
            
            # 模拟发送成功
            await asyncio.sleep(0.05)  # 模拟网络延迟
            
            self.logger.info(f"Discord消息发送成功: {message.metadata.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Discord消息发送失败: {e}")
            return False
    
    async def send_media(self, message: Message, media_url: str, account_id=None) -> bool:
        """发送Discord媒体消息"""
        try:
            self.logger.info(f"发送Discord媒体消息: {media_url}")
            
            # 验证连接
            if not account_id:
                account_id = self.config.default_account_id
            
            if account_id not in self._connected_accounts:
                self.logger.error(f"Discord账户未连接: {account_id}")
                return False
            
            # 模拟发送成功
            await asyncio.sleep(0.1)  # 媒体消息需要更长时间
            
            self.logger.info(f"Discord媒体消息发送成功: {media_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Discord媒体消息发送失败: {e}")
            return False
    
    async def send_poll(self, question: str, options: list, account_id=None) -> bool:
        """发送Discord投票"""
        try:
            self.logger.info(f"发送Discord投票: {question}")
            
            # 验证连接
            if not account_id:
                account_id = self.config.default_account_id
            
            if account_id not in self._connected_accounts:
                self.logger.error(f"Discord账户未连接: {account_id}")
                return False
            
            # Discord暂时不支持投票，这里模拟失败
            self.logger.warning("Discord不支持投票功能")
            return False
            
        except Exception as e:
            self.logger.error(f"Discord投票发送失败: {e}")
            return False
    
    async def get_status(self, account_id: str):
        """获取Discord状态"""
        from .base import ChannelStatus, ChannelState, ConnectionStatus
        
        return ChannelStatus(
            account_id=account_id,
            state=ChannelState.RUNNING if account_id in self._connected_accounts else ChannelState.STOPPED,
            connection_status=ConnectionStatus.CONNECTED if account_id in self._connected_accounts else ConnectionStatus.DISCONNECTED,
            connected=account_id in self._connected_accounts,
            running=account_id in self._connected_accounts,
        )
    
    async def configure_account(self, account_config: ChannelAccountConfig) -> bool:
        """配置Discord账户"""
        try:
            self.config.accounts[account_config.account_id] = account_config
            self.logger.info(f"Discord账户配置成功: {account_config.account_id}")
            return True
        except Exception as e:
            self.logger.error(f"Discord账户配置失败: {e}")
            return False


# 注册Discord适配器
@register_channel_type("discord")
def create_discord_adapter(config: ChannelConfig) -> ChannelAdapter:
    """创建Discord适配器"""
    return DiscordAdapter(config)


# 示例：Telegram渠道适配器
class TelegramAdapter(ChannelAdapter):
    """Telegram渠道适配器示例"""
    
    def __init__(self, config: ChannelConfig):
        super().__init__(config)
        self._connected_accounts = set()
        self.logger = logging.getLogger(f"{__name__}.Telegram")
    
    @property
    def channel_id(self) -> str:
        return self.config.channel_id
    
    @property
    def channel_name(self) -> str:
        return self.config.channel_name
    
    @property
    def capabilities(self) -> ChannelCapabilities:
        capabilities = self.config.capabilities
        capabilities.polls = True  # Telegram支持投票
        capabilities.reactions = True
        return capabilities
    
    async def connect(self, account_id: str) -> bool:
        """连接到Telegram"""
        try:
            account_config = self.config.accounts.get(account_id)
            if not account_config or not account_config.token:
                self.logger.error(f"Telegram账户 {account_id} 缺少token")
                return False
            
            self.logger.info(f"连接到Telegram账户: {account_id}")
            await asyncio.sleep(0.1)
            self._connected_accounts.add(account_id)
            
            self._notify_event_handlers("status_changed", {
                "channel_id": self.channel_id,
                "account_id": account_id,
                "status": "connected"
            })
            
            return True
        except Exception as e:
            self.logger.error(f"Telegram连接失败 {account_id}: {e}")
            return False
    
    async def disconnect(self, account_id: str) -> bool:
        """断开Telegram连接"""
        try:
            if account_id in self._connected_accounts:
                self._connected_accounts.discard(account_id)
                self._notify_event_handlers("status_changed", {
                    "channel_id": self.channel_id,
                    "account_id": account_id,
                    "status": "disconnected"
                })
            return True
        except Exception as e:
            self.logger.error(f"Telegram断开失败 {account_id}: {e}")
            return False
    
    async def is_connected(self, account_id: str) -> bool:
        """检查Telegram连接状态"""
        return account_id in self._connected_accounts
    
    async def send_message(self, message: Message, account_id=None) -> bool:
        """发送Telegram消息"""
        try:
            if not account_id:
                account_id = self.config.default_account_id
            
            if account_id not in self._connected_accounts:
                return False
            
            self.logger.info(f"发送Telegram消息: {message.content[:50]}...")
            await asyncio.sleep(0.05)
            return True
        except Exception as e:
            self.logger.error(f"Telegram消息发送失败: {e}")
            return False
    
    async def send_media(self, message: Message, media_url: str, account_id=None) -> bool:
        """发送Telegram媒体消息"""
        try:
            if not account_id:
                account_id = self.config.default_account_id
            
            if account_id not in self._connected_accounts:
                return False
            
            self.logger.info(f"发送Telegram媒体消息: {media_url}")
            await asyncio.sleep(0.1)
            return True
        except Exception as e:
            self.logger.error(f"Telegram媒体消息发送失败: {e}")
            return False
    
    async def send_poll(self, question: str, options: list, account_id=None) -> bool:
        """发送Telegram投票"""
        try:
            if not account_id:
                account_id = self.config.default_account_id
            
            if account_id not in self._connected_accounts:
                return False
            
            self.logger.info(f"发送Telegram投票: {question}")
            await asyncio.sleep(0.1)
            return True
        except Exception as e:
            self.logger.error(f"Telegram投票发送失败: {e}")
            return False
    
    async def get_status(self, account_id: str):
        """获取Telegram状态"""
        from .base import ChannelStatus, ChannelState, ConnectionStatus
        
        return ChannelStatus(
            account_id=account_id,
            state=ChannelState.RUNNING if account_id in self._connected_accounts else ChannelState.STOPPED,
            connection_status=ConnectionStatus.CONNECTED if account_id in self._connected_accounts else ConnectionStatus.DISCONNECTED,
            connected=account_id in self._connected_accounts,
            running=account_id in self._connected_accounts,
        )
    
    async def configure_account(self, account_config: ChannelAccountConfig) -> bool:
        """配置Telegram账户"""
        try:
            self.config.accounts[account_config.account_id] = account_config
            self.logger.info(f"Telegram账户配置成功: {account_config.account_id}")
            return True
        except Exception as e:
            self.logger.error(f"Telegram账户配置失败: {e}")
            return False


# 注册Telegram适配器
@register_channel_type("telegram")
def create_telegram_adapter(config: ChannelConfig) -> ChannelAdapter:
    """创建Telegram适配器"""
    return TelegramAdapter(config)


# 示例使用函数
async def example_usage():
    """使用示例"""
    logger.info("开始AgentBus渠道系统示例")
    
    # 创建渠道管理器
    config_path = Path("example_channels_config.json")
    manager = ChannelManager(config_path)
    
    # 定义消息和状态处理器
    def on_message(message: Message, channel_id: str):
        logger.info(f"收到消息 [{channel_id}]: {message.content[:50]}...")
    
    def on_status_change(channel_id: str, status):
        logger.info(f"状态变化 [{channel_id}]: {status.state.value} - {status.connection_status.value}")
    
    # 添加处理器
    manager.add_message_handler(on_message)
    manager.add_status_handler(on_status_change)
    
    # 启动管理器
    await manager.start()
    
    try:
        # 创建Discord渠道配置
        discord_account = ChannelAccountConfig(
            account_id="default",
            name="AgentBot",
            token="your_discord_bot_token_here",
            token_source="config",
            configured=True
        )
        
        discord_config = ChannelConfig(
            channel_id="discord_main",
            channel_name="Discord主渠道",
            channel_type="discord",
            accounts={"default": discord_account},
            default_account_id="default",
            capabilities=ChannelCapabilities(
                chat_types=[ChatType.DIRECT, ChatType.GROUP, ChatType.CHANNEL],
                polls=True,
                reactions=True,
                threads=True,
                media=True,
                native_commands=True
            ),
            enabled=True
        )
        
        # 创建Telegram渠道配置
        telegram_account = ChannelAccountConfig(
            account_id="default",
            name="AgentBot",
            token="your_telegram_bot_token_here",
            token_source="config",
            configured=True
        )
        
        telegram_config = ChannelConfig(
            channel_id="telegram_main",
            channel_name="Telegram主渠道",
            channel_type="telegram",
            accounts={"default": telegram_account},
            default_account_id="default",
            capabilities=ChannelCapabilities(
                chat_types=[ChatType.DIRECT, ChatType.GROUP],
                polls=True,
                reactions=True,
                media=True
            ),
            enabled=True
        )
        
        # 注册渠道
        logger.info("注册Discord渠道")
        success1 = await manager.register_channel(discord_config)
        logger.info(f"Discord渠道注册结果: {success1}")
        
        logger.info("注册Telegram渠道")
        success2 = await manager.register_channel(telegram_config)
        logger.info(f"Telegram渠道注册结果: {success2}")
        
        if success1 and success2:
            # 连接所有渠道
            logger.info("连接所有渠道")
            await manager.connect_all()
            
            # 等待连接稳定
            await asyncio.sleep(1)
            
            # 发送测试消息
            logger.info("发送测试消息")
            await manager.send_message("discord_main", "Hello from AgentBus Discord!", MessageType.TEXT)
            await manager.send_message("telegram_main", "Hello from AgentBus Telegram!", MessageType.TEXT)
            
            # 发送媒体消息
            await manager.send_media("discord_main", "查看这个图片", "https://example.com/image.jpg")
            
            # 发送投票
            await manager.send_poll("telegram_main", "你更喜欢哪个？", ["选项A", "选项B", "选项C"])
            
            # 等待消息发送
            await asyncio.sleep(2)
            
            # 获取状态
            logger.info("获取渠道状态")
            status = await manager.get_all_status()
            for channel_id, channel_status in status.items():
                logger.info(f"渠道 {channel_id} 状态:")
                for account_id, account_status in channel_status.items():
                    logger.info(f"  账户 {account_id}: {account_status.state.value}")
            
            # 健康检查
            health = await manager.health_check()
            logger.info(f"系统健康状态: {health['overall_health']}")
            
            # 统计信息
            stats = manager.get_statistics()
            logger.info(f"系统统计: {stats}")
        
        # 断开所有连接
        logger.info("断开所有连接")
        await manager.disconnect_all()
        
    finally:
        # 停止管理器
        await manager.stop()
        logger.info("示例完成")


if __name__ == "__main__":
    asyncio.run(example_usage())