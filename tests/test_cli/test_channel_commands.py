"""
渠道管理CLI命令测试
Channel Management CLI Commands Tests
"""

import asyncio
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from click.testing import CliRunner
from pathlib import Path
import tempfile
import yaml

from agentbus.cli.commands.channel_commands import (
    ChannelCommands, create_channel_commands,
    list, add, remove, connect, disconnect, status, send, info,
    connect_all, disconnect_all, export, import_config, stats
)
from agentbus.channels.manager import ChannelManager
from agentbus.channels.base import (
    ChannelConfig, ChannelAccountConfig, MessageType, ChatType, 
    ChannelStatus, ConnectionStatus, ChannelState
)


class TestChannelCommands:
    """渠道管理命令测试类"""
    
    @pytest.fixture
    def mock_channel_manager(self):
        """创建模拟渠道管理器"""
        manager = Mock(spec=ChannelManager)
        
        # 模拟渠道配置
        self.mock_config = Mock(spec=ChannelConfig)
        self.mock_config.channel_id = "test_channel_1"
        self.mock_config.name = "Test Channel 1"
        self.mock_config.type = "telegram"
        self.mock_config.default_account_id = "default_account"
        self.mock_config.accounts = {"default_account": Mock()}
        
        # 模拟渠道状态
        self.mock_status = Mock(spec=ChannelStatus)
        self.mock_status.connection_status = ConnectionStatus.CONNECTED
        self.mock_status.state = ChannelState.RUNNING
        self.mock_status.last_activity = None
        self.mock_status.error_message = None
        
        # 设置模拟返回值
        manager.list_channels.return_value = ["test_channel_1", "test_channel_2"]
        manager.get_channel_config.side_effect = lambda channel_id: self.mock_config if channel_id == "test_channel_1" else None
        manager.is_channel_connected.return_value = True
        manager.get_channel_status.return_value = self.mock_status
        manager.get_channel_adapter.return_value = Mock()
        manager.get_statistics.return_value = {
            "total_channels": 2,
            "active_adapters": 2,
            "connected_channels": 1,
            "running": True,
            "config_path": "/path/to/channels_config.json"
        }
        
        return manager
    
    @pytest.fixture
    def channel_commands(self, mock_channel_manager):
        """创建渠道命令实例"""
        return ChannelCommands(mock_channel_manager)
    
    @pytest.mark.asyncio
    async def test_list_channels(self, channel_commands):
        """测试列出渠道"""
        # 测试默认格式
        result = await channel_commands.list_channels()
        
        assert result["total"] == 2
        assert "statistics" in result
        assert "channels" in result
        
        # 测试JSON格式
        json_result = await channel_commands.list_channels(format_type="json")
        assert "total" in json_result
        
        # 测试状态过滤
        filtered_result = await channel_commands.list_channels(status_filter="connected")
        assert "total" in filtered_result
    
    @pytest.mark.asyncio
    async def test_add_channel(self, channel_commands, mock_channel_manager):
        """测试添加渠道"""
        # 模拟成功添加
        mock_channel_manager.register_channel.return_value = True
        
        channel_data = {
            "channel_id": "new_channel",
            "name": "New Channel",
            "type": "discord",
            "default_account_id": "default_account",
            "accounts": {}
        }
        
        # 模拟ChannelConfig.from_dict
        with patch('agentbus.cli.commands.channel_commands.ChannelConfig.from_dict') as mock_from_dict:
            mock_config = Mock()
            mock_config.channel_id = "new_channel"
            mock_from_dict.return_value = mock_config
            
            result = await channel_commands.add_channel(channel_data)
            
            assert result["success"] is True
            assert "new_channel" in result["message"]
            mock_channel_manager.register_channel.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remove_channel(self, channel_commands, mock_channel_manager):
        """测试删除渠道"""
        # 模拟成功删除
        mock_channel_manager.unregister_channel.return_value = True
        
        result = await channel_commands.remove_channel("test_channel_1")
        
        assert result["success"] is True
        assert "test_channel_1" in result["message"]
        mock_channel_manager.unregister_channel.assert_called_once_with("test_channel_1")
    
    @pytest.mark.asyncio
    async def test_connect_channel(self, channel_commands, mock_channel_manager):
        """测试连接渠道"""
        # 模拟成功连接
        mock_channel_manager.connect_channel.return_value = True
        
        result = await channel_commands.connect_channel("test_channel_1", "default_account")
        
        assert result["success"] is True
        assert "test_channel_1" in result["message"]
        mock_channel_manager.connect_channel.assert_called_once_with("test_channel_1", "default_account")
    
    @pytest.mark.asyncio
    async def test_disconnect_channel(self, channel_commands, mock_channel_manager):
        """测试断开渠道"""
        # 模拟成功断开
        mock_channel_manager.disconnect_channel.return_value = True
        
        result = await channel_commands.disconnect_channel("test_channel_1", "default_account")
        
        assert result["success"] is True
        assert "test_channel_1" in result["message"]
        mock_channel_manager.disconnect_channel.assert_called_once_with("test_channel_1", "default_account")
    
    @pytest.mark.asyncio
    async def test_send_message(self, channel_commands, mock_channel_manager):
        """测试发送消息"""
        # 模拟成功发送
        mock_channel_manager.send_message.return_value = True
        
        result = await channel_commands.send_message_to_channel(
            "test_channel_1", "Hello, world!", "text", "default_account"
        )
        
        assert result["success"] is True
        assert "test_channel_1" in result["message"]
        mock_channel_manager.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_channel_status(self, channel_commands, mock_channel_manager):
        """测试获取渠道状态"""
        result = await channel_commands.get_channel_status("test_channel_1", "default_account")
        
        assert "channel_id" in result
        assert "connection_status" in result
        assert "state" in result
        assert result["channel_id"] == "test_channel_1"
    
    @pytest.mark.asyncio
    async def test_get_channel_details(self, channel_commands, mock_channel_manager):
        """测试获取渠道详细信息"""
        result = await channel_commands.get_channel_details("test_channel_1")
        
        assert "channel_id" in result
        assert "config" in result
        assert "status" in result
        assert "adapter_info" in result
        
        assert result["channel_id"] == "test_channel_1"
    
    @pytest.mark.asyncio
    async def test_connect_all_channels(self, channel_commands, mock_channel_manager):
        """测试连接所有渠道"""
        # 模拟连接所有渠道
        mock_channel_manager.connect_all = AsyncMock()
        mock_channel_manager.get_all_status.return_value = {
            "test_channel_1": {"default_account": self.mock_status},
            "test_channel_2": {"default_account": self.mock_status}
        }
        
        result = await channel_commands.connect_all_channels()
        
        assert result["success"] is True
        assert "status" in result
        mock_channel_manager.connect_all.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_all_channels(self, channel_commands, mock_channel_manager):
        """测试断开所有渠道"""
        # 模拟断开所有渠道
        mock_channel_manager.disconnect_all = AsyncMock()
        
        result = await channel_commands.disconnect_all_channels()
        
        assert result["success"] is True
        assert "所有渠道已断开连接" in result["message"]
        mock_channel_manager.disconnect_all.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_export_config(self, channel_commands, mock_channel_manager):
        """测试导出配置"""
        # 模拟get_channel_config返回配置
        mock_config = Mock()
        mock_config.to_dict.return_value = {
            "channel_id": "test_channel_1",
            "name": "Test Channel",
            "type": "telegram"
        }
        mock_channel_manager.get_channel_config.return_value = mock_config
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            result = await channel_commands.export_config(output_path, "json")
            
            assert result["success"] is True
            assert "channel_count" in result
            
            # 检查文件是否创建
            assert output_path.exists()
            
            # 验证JSON内容
            with open(output_path, 'r') as f:
                config_data = json.load(f)
            
            assert "version" in config_data
            assert "channels" in config_data
            
        finally:
            # 清理临时文件
            if output_path.exists():
                output_path.unlink()
    
    @pytest.mark.asyncio
    async def test_import_config(self, channel_commands, mock_channel_manager):
        """测试导入配置"""
        # 创建临时配置文件
        config_data = {
            "version": "1.0",
            "channels": {
                "imported_channel": {
                    "channel_id": "imported_channel",
                    "name": "Imported Channel",
                    "type": "discord",
                    "accounts": {}
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            # 模拟注册渠道成功
            mock_channel_manager.register_channel = AsyncMock(return_value=True)
            
            # 模拟ChannelConfig.from_dict
            with patch('agentbus.cli.commands.channel_commands.ChannelConfig.from_dict') as mock_from_dict:
                mock_config = Mock()
                mock_config.channel_id = "imported_channel"
                mock_from_dict.return_value = mock_config
                
                result = await channel_commands.import_config(config_path)
                
                assert result["success"] is True
                assert result["imported_count"] == 1
                assert result["total_count"] == 1
                
                # 验证调用
                mock_channel_manager.register_channel.assert_called_once()
                
        finally:
            # 清理临时文件
            if config_path.exists():
                config_path.unlink()
    
    @pytest.mark.asyncio
    async def test_get_channels_status_summary(self, channel_commands, mock_channel_manager):
        """测试获取渠道状态摘要"""
        # 模拟所有状态
        mock_channel_manager.get_all_status.return_value = {
            "test_channel_1": {"default_account": self.mock_status},
            "test_channel_2": {"default_account": self.mock_status}
        }
        
        result = await channel_commands.get_channels_status_summary()
        
        assert "total_channels" in result
        assert "connected_channels" in result
        assert "channels" in result
        assert result["total_channels"] == 2
    
    def test_cli_list_command(self, mock_channel_manager):
        """测试CLI list命令"""
        runner = CliRunner()
        
        # 设置上下文
        ctx = Mock()
        ctx.obj = {'channel_manager': mock_channel_manager}
        
        # 模拟异步函数
        async def mock_list(*args, **kwargs):
            return {
                "total": 2,
                "channels": [
                    {
                        "id": "test_channel_1",
                        "name": "Test Channel 1",
                        "type": "telegram",
                        "status": "connected",
                        "account_count": 1,
                        "default_account": "default_account"
                    }
                ],
                "statistics": {"connected": 1, "disconnected": 1}
            }
        
        with patch('agentbus.cli.commands.channel_commands.ChannelCommands.list_channels', mock_list):
            result = runner.invoke(list, [], obj=ctx)
            
            assert result.exit_code == 0
            assert "渠道列表" in result.output
            assert "Test Channel 1" in result.output
    
    def test_cli_connect_command(self, mock_channel_manager):
        """测试CLI connect命令"""
        runner = CliRunner()
        
        ctx = Mock()
        ctx.obj = {'channel_manager': mock_channel_manager}
        
        async def mock_connect(*args, **kwargs):
            return {
                "success": True,
                "message": "渠道 test_channel_1 连接成功",
                "channel_id": "test_channel_1",
                "account_id": "default_account"
            }
        
        with patch('agentbus.cli.commands.channel_commands.ChannelCommands.connect_channel', mock_connect):
            result = runner.invoke(connect, ['test_channel_1', '--account', 'default_account'], obj=ctx)
            
            assert result.exit_code == 0
            assert "连接成功" in result.output
    
    def test_cli_send_command(self, mock_channel_manager):
        """测试CLI send命令"""
        runner = CliRunner()
        
        ctx = Mock()
        ctx.obj = {'channel_manager': mock_channel_manager}
        
        async def mock_send(*args, **kwargs):
            return {
                "success": True,
                "message": "消息发送到渠道 test_channel_1 成功",
                "channel_id": "test_channel_1"
            }
        
        with patch('agentbus.cli.commands.channel_commands.ChannelCommands.send_message_to_channel', mock_send):
            result = runner.invoke(send, ['test_channel_1', 'Hello, world!'], obj=ctx)
            
            assert result.exit_code == 0
            assert "发送成功" in result.output
    
    def test_cli_stats_command(self, mock_channel_manager):
        """测试CLI stats命令"""
        runner = CliRunner()
        
        ctx = Mock()
        ctx.obj = {'channel_manager': mock_channel_manager}
        
        result = runner.invoke(stats, [], obj=ctx)
        
        assert result.exit_code == 0
        assert "渠道系统统计" in result.output
        assert "总渠道数: 2" in result.output
    
    def test_create_channel_commands(self, mock_channel_manager):
        """测试创建渠道命令实例"""
        commands = create_channel_commands(mock_channel_manager)
        
        assert isinstance(commands, ChannelCommands)
        assert commands.channel_manager == mock_channel_manager


class TestChannelCommandsEdgeCases:
    """渠道管理命令边界情况测试"""
    
    @pytest.fixture
    def mock_channel_manager(self):
        """创建模拟渠道管理器"""
        return Mock(spec=ChannelManager)
    
    @pytest.mark.asyncio
    async def test_list_channels_error_handling(self, mock_channel_manager):
        """测试列出渠道时的错误处理"""
        # 模拟异常
        mock_channel_manager.list_channels.side_effect = Exception("Test error")
        
        commands = ChannelCommands(mock_channel_manager)
        result = await commands.list_channels()
        
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_add_channel_error_handling(self, mock_channel_manager):
        """测试添加渠道时的错误处理"""
        # 模拟异常
        mock_channel_manager.register_channel.side_effect = Exception("Test error")
        
        commands = ChannelCommands(mock_channel_manager)
        result = await commands.add_channel({})
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_get_status_nonexistent_channel(self, mock_channel_manager):
        """测试获取不存在渠道的状态"""
        mock_channel_manager.get_channel_status.return_value = None
        
        commands = ChannelCommands(mock_channel_manager)
        result = await commands.get_channel_status("nonexistent_channel")
        
        assert "error" in result
        assert "未找到" in result["error"]
    
    @pytest.mark.asyncio
    async def test_send_message_invalid_type(self, mock_channel_manager):
        """测试发送无效类型的消息"""
        commands = ChannelCommands(mock_channel_manager)
        
        # 模拟不支持的消息类型
        with pytest.raises(ValueError):
            await commands.send_message_to_channel(
                "test_channel_1", "Hello", "invalid_type"
            )
    
    @pytest.mark.asyncio
    async def test_export_invalid_format(self, mock_channel_manager):
        """测试导出不支持的格式"""
        commands = ChannelCommands(mock_channel_manager)
        
        with tempfile.NamedTemporaryFile(suffix='.txt') as f:
            result = await commands.export_config(Path(f.name), "xml")
            
            assert "error" in result
            assert "不支持的格式" in result["error"]
    
    @pytest.mark.asyncio
    async def test_import_invalid_config_file(self, mock_channel_manager):
        """测试导入无效的配置文件"""
        commands = ChannelCommands(mock_channel_manager)
        
        # 测试不支持的文件格式
        with tempfile.NamedTemporaryFile(suffix='.txt') as f:
            result = await commands.import_config(Path(f.name))
            
            assert "error" in result
            assert "不支持的配置文件格式" in result["error"]
    
    @pytest.mark.asyncio
    async def test_connect_all_channels_error_handling(self, mock_channel_manager):
        """测试连接所有渠道时的错误处理"""
        # 模拟异常
        mock_channel_manager.connect_all.side_effect = Exception("Test error")
        
        commands = ChannelCommands(mock_channel_manager)
        result = await commands.connect_all_channels()
        
        assert result["success"] is False
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__])