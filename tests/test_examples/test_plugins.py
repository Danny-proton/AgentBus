"""
测试示例插件

此文件包含对示例插件的单元测试和集成测试。
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, AsyncMock, patch

# 导入要测试的插件
try:
    from agentbus.plugins.telegram_channel_plugin import TelegramChannelPlugin
    from agentbus.plugins.discord_channel_plugin import DiscordChannelPlugin
    from agentbus.plugins.example_skill import ExampleSkillPlugin
    from agentbus.plugins.core import PluginContext
except ImportError as e:
    pytest.skip(f"无法导入插件: {e}", allow_module_level=True)


@pytest.fixture
def plugin_context():
    """创建测试用的插件上下文"""
    config = {"test_mode": True}
    logger = logging.getLogger("test_plugin")
    runtime = {"event_bus": Mock()}
    
    return PluginContext(
        config=config,
        logger=logger,
        runtime=runtime
    )


class TestTelegramChannelPlugin:
    """测试Telegram渠道插件"""
    
    @pytest.fixture
    def telegram_plugin(self, plugin_context):
        """创建Telegram插件实例"""
        return TelegramChannelPlugin("test_telegram", plugin_context)
    
    def test_plugin_info(self, telegram_plugin):
        """测试插件信息"""
        info = telegram_plugin.get_info()
        
        assert info["id"] == "test_telegram"
        assert info["name"] == "Telegram Channel Plugin"
        assert info["version"] == "1.0.0"
        assert "dependencies" in info
        assert "capabilities" in info
    
    @pytest.mark.asyncio
    async def test_activate_plugin(self, telegram_plugin):
        """测试插件激活"""
        await telegram_plugin.activate()
        
        assert telegram_plugin.status.value == "active"
        
        # 检查工具是否注册
        tools = telegram_plugin.get_tools()
        tool_names = [tool.name for tool in tools]
        assert "send_message" in tool_names
        assert "send_media" in tool_names
        assert "send_poll" in tool_names
        
        # 检查钩子是否注册
        hooks = telegram_plugin.get_hooks()
        assert "telegram_message" in hooks
        assert "telegram_callback" in hooks
        
        # 检查命令是否注册
        commands = telegram_plugin.get_commands()
        command_names = [cmd['command'] for cmd in commands]
        assert "/telegram_status" in command_names
        assert "/telegram_bots" in command_names
    
    @pytest.mark.asyncio
    async def test_send_message_tool(self, telegram_plugin):
        """测试发送消息工具"""
        await telegram_plugin.activate()
        
        # 模拟API请求
        with patch.object(telegram_plugin, '_make_request') as mock_request:
            mock_request.return_value = {
                "ok": True,
                "result": {"message_id": "12345"}
            }
            
            result = await telegram_plugin.send_message(
                bot_token="test_token",
                chat_id="test_chat",
                text="Hello, World!"
            )
            
            assert result["success"] is True
            assert "message_id" in result
            assert telegram_plugin.message_count > 0
    
    @pytest.mark.asyncio
    async def test_send_message_tool_error(self, telegram_plugin):
        """测试发送消息工具错误处理"""
        await telegram_plugin.activate()
        
        with patch.object(telegram_plugin, '_make_request') as mock_request:
            mock_request.return_value = {
                "ok": False,
                "error": "Invalid token"
            }
            
            result = await telegram_plugin.send_message(
                bot_token="invalid_token",
                chat_id="test_chat",
                text="Hello, World!"
            )
            
            assert result["success"] is False
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_status_command(self, telegram_plugin):
        """测试状态命令"""
        await telegram_plugin.activate()
        
        result = await telegram_plugin.handle_status_command("")
        assert "Telegram插件状态:" in result
        assert "test_telegram" in result


class TestDiscordChannelPlugin:
    """测试Discord渠道插件"""
    
    @pytest.fixture
    def discord_plugin(self, plugin_context):
        """创建Discord插件实例"""
        return DiscordChannelPlugin("test_discord", plugin_context)
    
    def test_plugin_info(self, discord_plugin):
        """测试插件信息"""
        info = discord_plugin.get_info()
        
        assert info["id"] == "test_discord"
        assert info["name"] == "Discord Channel Plugin"
        assert info["version"] == "1.0.0"
        assert "dependencies" in info
        assert "capabilities" in info
    
    @pytest.mark.asyncio
    async def test_activate_plugin(self, discord_plugin):
        """测试插件激活"""
        await discord_plugin.activate()
        
        assert discord_plugin.status.value == "active"
        
        # 检查工具是否注册
        tools = discord_plugin.get_tools()
        tool_names = [tool.name for tool in tools]
        assert "send_message" in tool_names
        assert "send_embed" in tool_names
        assert "create_webhook" in tool_names
        
        # 检查钩子是否注册
        hooks = discord_plugin.get_hooks()
        assert "discord_message" in hooks
        assert "discord_guild_member_add" in hooks
        
        # 检查命令是否注册
        commands = discord_plugin.get_commands()
        command_names = [cmd['command'] for cmd in commands]
        assert "/discord_status" in command_names
        assert "/discord_servers" in command_names
    
    @pytest.mark.asyncio
    async def test_send_message_tool(self, discord_plugin):
        """测试发送消息工具"""
        await discord_plugin.activate()
        
        # 模拟API请求
        with patch.object(discord_plugin, '_make_request') as mock_request:
            mock_request.return_value = {
                "success": True,
                "data": {"id": "12345", "timestamp": "2024-01-01T00:00:00Z"}
            }
            
            result = await discord_plugin.send_message(
                bot_token="test_token",
                channel_id="test_channel",
                content="Hello, Discord!"
            )
            
            assert result["success"] is True
            assert "message_id" in result
            assert discord_plugin.message_count > 0
    
    @pytest.mark.asyncio
    async def test_embed_message(self, discord_plugin):
        """测试Embed消息"""
        await discord_plugin.activate()
        
        with patch.object(discord_plugin, '_make_request') as mock_request:
            mock_request.return_value = {
                "success": True,
                "data": {"id": "67890"}
            }
            
            result = await discord_plugin.send_embed(
                bot_token="test_token",
                channel_id="test_channel",
                title="测试标题",
                description="这是一个测试Embed"
            )
            
            assert result["success"] is True
            assert "message_id" in result
    
    @pytest.mark.asyncio
    async def test_status_command(self, discord_plugin):
        """测试状态命令"""
        await discord_plugin.activate()
        
        result = await discord_plugin.handle_status_command("")
        assert "Discord插件状态:" in result
        assert "test_discord" in result


class TestExampleSkillPlugin:
    """测试示例技能插件"""
    
    @pytest.fixture
    def skill_plugin(self, plugin_context):
        """创建技能插件实例"""
        return ExampleSkillPlugin("test_skill", plugin_context)
    
    def test_plugin_info(self, skill_plugin):
        """测试插件信息"""
        info = skill_plugin.get_info()
        
        assert info["id"] == "test_skill"
        assert info["name"] == "Example Skill Plugin"
        assert info["version"] == "1.0.0"
        assert "capabilities" in info
    
    @pytest.mark.asyncio
    async def test_activate_plugin(self, skill_plugin):
        """测试插件激活"""
        await skill_plugin.activate()
        
        assert skill_plugin.status.value == "active"
        
        # 检查工具是否注册
        tools = skill_plugin.get_tools()
        tool_names = [tool.name for tool in tools]
        assert "calculate" in tool_names
        assert "generate_random" in tool_names
        assert "process_text" in tool_names
        
        # 检查钩子是否注册
        hooks = skill_plugin.get_hooks()
        assert "message_received" in hooks
        assert "task_completed" in hooks
        
        # 检查命令是否注册
        commands = skill_plugin.get_commands()
        command_names = [cmd['command'] for cmd in commands]
        assert "/calc" in command_names
        assert "/random" in command_names
        assert "/stats" in command_names
    
    @pytest.mark.asyncio
    async def test_calculate_tool(self, skill_plugin):
        """测试计算工具"""
        await skill_plugin.activate()
        
        result = await skill_plugin.calculate("2 + 2")
        
        assert result.success is True
        assert "4" in result.message
        assert result.data["result"] == 4.0
    
    @pytest.mark.asyncio
    async def test_calculate_invalid_expression(self, skill_plugin):
        """测试无效计算表达式"""
        await skill_plugin.activate()
        
        result = await skill_plugin.calculate("2 + invalid")
        
        assert result.success is False
        assert "不支持的操作符" in result.message
    
    @pytest.mark.asyncio
    async def test_generate_random_numbers(self, skill_plugin):
        """测试生成随机数字"""
        await skill_plugin.activate()
        
        result = await skill_plugin.generate_random("number", 5, 1, 10)
        
        assert result.success is True
        assert len(result.data["data"]) == 5
        assert all(1 <= num <= 10 for num in result.data["data"])
    
    @pytest.mark.asyncio
    async def test_generate_random_invalid_type(self, skill_plugin):
        """测试生成无效随机类型"""
        await skill_plugin.activate()
        
        result = await skill_plugin.generate_random("invalid_type", 1)
        
        assert result.success is False
        assert "不支持的数据类型" in result.message
    
    @pytest.mark.asyncio
    async def test_process_text(self, skill_plugin):
        """测试文本处理"""
        await skill_plugin.activate()
        
        result = await skill_plugin.process_text("hello world", "uppercase")
        
        assert result.success is True
        assert result.data["processed_text"] == "HELLO WORLD"
    
    @pytest.mark.asyncio
    async def test_manage_tasks(self, skill_plugin):
        """测试任务管理"""
        await skill_plugin.activate()
        
        # 创建任务
        result = await skill_plugin.manage_tasks("create", "test_task", {"steps": 2, "delay": 0.1})
        assert result.success is True
        assert "test_task" in skill_plugin.active_tasks
        
        # 检查任务状态
        result = await skill_plugin.manage_tasks("status", "test_task")
        assert result.success is True
        
        # 列出任务
        result = await skill_plugin.manage_tasks("list")
        assert result.success is True
        assert len(result.data["tasks"]) >= 1
        
        # 取消任务
        result = await skill_plugin.manage_tasks("cancel", "test_task")
        assert result.success is True
        assert "test_task" not in skill_plugin.active_tasks
    
    @pytest.mark.asyncio
    async def test_get_timestamp(self, skill_plugin):
        """测试时间戳获取"""
        await skill_plugin.activate()
        
        result = await skill_plugin.get_timestamp("iso")
        assert result.success is True
        assert "T" in result.data["timestamp"]  # ISO格式包含T
    
    @pytest.mark.asyncio
    async def test_data_validation(self, skill_plugin):
        """测试数据验证"""
        await skill_plugin.activate()
        
        # 验证数字
        result = await skill_plugin.data_validation("123", "number")
        assert result.success is True
        assert result.data["is_valid"] is True
        
        # 验证邮箱
        result = await skill_plugin.data_validation("test@example.com", "email")
        assert result.success is True
        assert result.data["is_valid"] is True
    
    @pytest.mark.asyncio
    async def test_format_output(self, skill_plugin):
        """测试输出格式化"""
        await skill_plugin.activate()
        
        data = {"name": "测试", "value": 42}
        result = await skill_plugin.format_output(data, "json")
        
        assert result.success is True
        assert "name" in result.data["formatted_output"]
        assert "value" in result.data["formatted_output"]
    
    @pytest.mark.asyncio
    async def test_skill_stats(self, skill_plugin):
        """测试技能统计"""
        await skill_plugin.activate()
        
        # 先执行一些操作
        await skill_plugin.calculate("1 + 1")
        await skill_plugin.generate_random("number", 1)
        
        result = await skill_plugin.get_skill_stats()
        
        assert result.success is True
        assert result.data["stats"]["total_executions"] >= 2
        assert result.data["stats"]["success_rate"] > 0
    
    @pytest.mark.asyncio
    async def test_calc_command(self, skill_plugin):
        """测试计算命令"""
        await skill_plugin.activate()
        
        result = await skill_plugin.handle_calc_command("3 * 4")
        assert "12" in result
    
    @pytest.mark.asyncio
    async def test_random_command(self, skill_plugin):
        """测试随机命令"""
        await skill_plugin.activate()
        
        result = await skill_plugin.handle_random_command("number 3")
        assert "3 个随机" in result
    
    @pytest.mark.asyncio
    async def test_text_command(self, skill_plugin):
        """测试文本命令"""
        await skill_plugin.activate()
        
        result = await skill_plugin.handle_text_command("hello lowercase")
        assert "hello" in result
    
    @pytest.mark.asyncio
    async def test_stats_command(self, skill_plugin):
        """测试统计命令"""
        await skill_plugin.activate()
        
        result = await skill_plugin.handle_stats_command("")
        assert "技能统计:" in result
        assert "总执行次数:" in result


class TestPluginIntegration:
    """测试插件集成"""
    
    @pytest.mark.asyncio
    async def test_plugin_lifecycle(self, plugin_context):
        """测试插件生命周期"""
        # 创建插件
        telegram_plugin = TelegramChannelPlugin("test_telegram", plugin_context)
        skill_plugin = ExampleSkillPlugin("test_skill", plugin_context)
        
        # 测试未激活状态
        assert telegram_plugin.status.value == "unloaded"
        assert skill_plugin.status.value == "unloaded"
        
        # 激活插件
        await telegram_plugin.activate()
        await skill_plugin.activate()
        
        assert telegram_plugin.status.value == "active"
        assert skill_plugin.status.value == "active"
        
        # 停用插件
        await telegram_plugin.deactivate()
        await skill_plugin.deactivate()
        
        assert telegram_plugin.status.value == "deactivated"
        assert skill_plugin.status.value == "deactivated"
    
    @pytest.mark.asyncio
    async def test_plugin_communication(self, plugin_context):
        """测试插件间通信"""
        # 这里可以测试插件间的钩子通信
        # 暂时留空，因为需要更复杂的事件系统
        pass
    
    @pytest.mark.asyncio
    async def test_multiple_plugins(self, plugin_context):
        """测试多个插件同时工作"""
        plugins = [
            TelegramChannelPlugin("telegram1", plugin_context),
            TelegramChannelPlugin("telegram2", plugin_context),
            DiscordChannelPlugin("discord1", plugin_context),
            ExampleSkillPlugin("skill1", plugin_context)
        ]
        
        # 激活所有插件
        for plugin in plugins:
            await plugin.activate()
        
        # 检查所有插件都激活成功
        for plugin in plugins:
            assert plugin.status.value == "active"
        
        # 执行一些操作
        telegram_plugin = plugins[0]
        await telegram_plugin.send_message("token", "chat", "test")
        
        # 停用所有插件
        for plugin in plugins:
            await plugin.deactivate()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])