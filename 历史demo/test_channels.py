"""
AgentBus渠道系统测试

测试渠道适配器基础框架的功能。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from agentbus.channels.base import (
    Message, MessageType, ChatType,
    ChannelConfig, ChannelAccountConfig, ChannelCapabilities,
    ChannelAdapter, MessageMetadata
)
from agentbus.channels.manager import ChannelManager
from agentbus.channels import register_channel_type


class TestAdapter(ChannelAdapter):
    """测试用渠道适配器"""
    
    def __init__(self, config: ChannelConfig):
        super().__init__(config)
        self._connected_accounts = set()
    
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
        print(f"连接渠道: {self.channel_id}, 账户: {account_id}")
        self._connected_accounts.add(account_id)
        return True
    
    async def disconnect(self, account_id: str) -> bool:
        print(f"断开渠道: {self.channel_id}, 账户: {account_id}")
        self._connected_accounts.discard(account_id)
        return True
    
    async def is_connected(self, account_id: str) -> bool:
        return account_id in self._connected_accounts
    
    async def send_message(self, message: Message, account_id=None) -> bool:
        print(f"发送消息到 {self.channel_id}: {message.content}")
        return True
    
    async def send_media(self, message: Message, media_url: str, account_id=None) -> bool:
        print(f"发送媒体到 {self.channel_id}: {media_url}")
        return True
    
    async def send_poll(self, question: str, options: list, account_id=None) -> bool:
        print(f"发送投票到 {self.channel_id}: {question}")
        return True
    
    async def get_status(self, account_id: str):
        from agentbus.channels.base import ChannelStatus, ChannelState, ConnectionStatus
        return ChannelStatus(
            account_id=account_id,
            state=ChannelState.RUNNING,
            connection_status=ConnectionStatus.CONNECTED,
            connected=account_id in self._connected_accounts,
            running=account_id in self._connected_accounts,
        )
    
    async def configure_account(self, account_config: ChannelAccountConfig) -> bool:
        self.config.accounts[account_config.account_id] = account_config
        return True


# 注册测试适配器
@register_channel_type("test")
def create_test_adapter(config: ChannelConfig) -> ChannelAdapter:
    return TestAdapter(config)


async def test_basic_functionality():
    """测试基础功能"""
    print("=== 测试AgentBus渠道系统基础功能 ===\n")
    
    # 创建渠道管理器
    manager = ChannelManager(Path("test_config.json"))
    
    # 定义事件处理器
    def on_message(message: Message, channel_id: str):
        print(f"[消息处理器] 收到消息 [{channel_id}]: {message.content}")
    
    def on_status_change(channel_id: str, status):
        print(f"[状态处理器] 状态变化 [{channel_id}]: {status.state.value}")
    
    manager.add_message_handler(on_message)
    manager.add_status_handler(on_status_change)
    
    # 启动管理器
    await manager.start()
    
    try:
        # 创建测试配置
        account_config = ChannelAccountConfig(
            account_id="test_account",
            name="Test Bot",
            token="test_token_123",
            configured=True
        )
        
        channel_config = ChannelConfig(
            channel_id="test_channel",
            channel_name="测试渠道",
            channel_type="test",
            accounts={"test_account": account_config},
            default_account_id="test_account",
            capabilities=ChannelCapabilities(
                chat_types=[ChatType.DIRECT, ChatType.GROUP],
                polls=True,
                media=True
            )
        )
        
        # 注册渠道
        print("1. 注册渠道...")
        success = await manager.register_channel(channel_config)
        print(f"   注册结果: {success}")
        
        if success:
            # 连接渠道
            print("\n2. 连接渠道...")
            await manager.connect_channel("test_channel")
            
            # 等待连接
            await asyncio.sleep(0.5)
            
            # 发送测试消息
            print("\n3. 发送测试消息...")
            await manager.send_message("test_channel", "Hello AgentBus!", MessageType.TEXT)
            await manager.send_media("test_channel", "查看图片", "https://example.com/image.jpg")
            await manager.send_poll("test_channel", "你更喜欢哪个？", ["选项A", "选项B"])
            
            # 获取状态
            print("\n4. 获取渠道状态...")
            status = await manager.get_channel_status("test_channel", "test_account")
            print(f"   渠道状态: {status.state.value}")
            print(f"   连接状态: {status.connection_status.value}")
            
            # 健康检查
            print("\n5. 健康检查...")
            health = await manager.health_check()
            print(f"   整体健康: {health['overall_health']}")
            
            # 统计信息
            print("\n6. 统计信息...")
            stats = manager.get_statistics()
            for key, value in stats.items():
                print(f"   {key}: {value}")
            
            # 断开连接
            print("\n7. 断开连接...")
            await manager.disconnect_channel("test_channel")
        
    finally:
        await manager.stop()
    
    print("\n=== 测试完成 ===")


async def test_message_metadata():
    """测试消息元数据功能"""
    print("\n=== 测试消息元数据功能 ===\n")
    
    # 创建消息元数据
    metadata = MessageMetadata(
        sender_id="user123",
        sender_name="测试用户",
        channel_id="test_channel",
        chat_type=ChatType.DIRECT,
        mentions=["@bot"],
        tags=["test", "demo"]
    )
    
    print("1. 原始元数据:")
    print(f"   ID: {metadata.id}")
    print(f"   发送者: {metadata.sender_name} ({metadata.sender_id})")
    print(f"   渠道: {metadata.channel_id}")
    print(f"   聊天类型: {metadata.chat_type.value}")
    print(f"   提及: {metadata.mentions}")
    print(f"   标签: {metadata.tags}")
    
    # 序列化为字典
    metadata_dict = metadata.to_dict()
    print("\n2. 序列化为字典:")
    print(f"   {metadata_dict}")
    
    # 从字典反序列化
    restored_metadata = MessageMetadata.from_dict(metadata_dict)
    print("\n3. 从字典恢复:")
    print(f"   ID: {restored_metadata.id}")
    print(f"   发送者: {restored_metadata.sender_name}")
    print(f"   渠道: {restored_metadata.channel_id}")
    print(f"   聊天类型: {restored_metadata.chat_type.value}")
    
    # 创建完整消息
    message = Message(
        type=MessageType.TEXT,
        content="测试消息内容",
        metadata=metadata
    )
    
    print("\n4. 完整消息:")
    print(f"   类型: {message.type.value}")
    print(f"   内容: {message.content}")
    print(f"   元数据ID: {message.metadata.id}")
    
    # 序列化和反序列化消息
    message_dict = message.to_dict()
    restored_message = Message.from_dict(message_dict)
    
    print("\n5. 消息序列化/反序列化:")
    print(f"   原始内容: {message.content}")
    print(f"   恢复内容: {restored_message.content}")
    print(f"   内容匹配: {message.content == restored_message.content}")
    
    print("\n=== 消息元数据测试完成 ===")


async def test_channel_config():
    """测试渠道配置功能"""
    print("\n=== 测试渠道配置功能 ===\n")
    
    # 创建账户配置
    account_config = ChannelAccountConfig(
        account_id="bot_account",
        name="My Bot",
        enabled=True,
        configured=True,
        token="secret_token_123",
        token_source="environment",
        custom_settings={
            "max_message_length": 2000,
            "enable_typing": True
        },
        media_limits={
            "max_file_size": 10485760,  # 10MB
            "allowed_types": ["image/*", "video/*"]
        }
    )
    
    print("1. 账户配置:")
    print(f"   账户ID: {account_config.account_id}")
    print(f"   名称: {account_config.name}")
    print(f"   已配置: {account_config.configured}")
    print(f"   Token来源: {account_config.token_source}")
    print(f"   自定义设置: {account_config.custom_settings}")
    
    # 创建渠道能力配置
    capabilities = ChannelCapabilities(
        chat_types=[ChatType.DIRECT, ChatType.GROUP, ChatType.CHANNEL],
        polls=True,
        reactions=True,
        media=True,
        threads=True
    )
    
    print("\n2. 渠道能力:")
    print(f"   支持的聊天类型: {[ct.value for ct in capabilities.chat_types]}")
    print(f"   支持投票: {capabilities.polls}")
    print(f"   支持反应: {capabilities.reactions}")
    print(f"   支持媒体: {capabilities.media}")
    print(f"   支持线程: {capabilities.threads}")
    
    # 创建完整渠道配置
    channel_config = ChannelConfig(
        channel_id="my_test_channel",
        channel_name="我的测试渠道",
        channel_type="test",
        accounts={"bot_account": account_config},
        default_account_id="bot_account",
        capabilities=capabilities,
        settings={
            "auto_reconnect": True,
            "message_queue_size": 100
        }
    )
    
    print("\n3. 渠道配置:")
    print(f"   渠道ID: {channel_config.channel_id}")
    print(f"   渠道名称: {channel_config.channel_name}")
    print(f"   渠道类型: {channel_config.channel_type}")
    print(f"   默认账户: {channel_config.default_account_id}")
    print(f"   账户数量: {len(channel_config.accounts)}")
    print(f"   设置: {channel_config.settings}")
    
    # 序列化配置
    config_dict = channel_config.to_dict()
    print("\n4. 配置序列化:")
    print(f"   配置字典键: {list(config_dict.keys())}")
    
    # 反序列化配置
    restored_config = ChannelConfig.from_dict(config_dict)
    print("\n5. 配置反序列化:")
    print(f"   恢复的渠道ID: {restored_config.channel_id}")
    print(f"   恢复的渠道名称: {restored_config.channel_name}")
    print(f"   恢复的账户数量: {len(restored_config.accounts)}")
    
    print("\n=== 渠道配置测试完成 ===")


async def main():
    """主测试函数"""
    print("AgentBus渠道系统测试开始...\n")
    
    try:
        await test_message_metadata()
        await test_channel_config()
        await test_basic_functionality()
        
        print("\n🎉 所有测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())