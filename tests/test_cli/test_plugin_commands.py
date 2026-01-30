"""
插件管理CLI命令测试
Plugin Management CLI Commands Tests
"""

import asyncio
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from click.testing import CliRunner
from pathlib import Path
import tempfile
import yaml

from agentbus.cli.commands.plugin_commands import (
    PluginCommands, create_plugin_commands, 
    list, enable, disable, reload, unload, info, export, import_config, stats
)
from agentbus.plugins.manager import PluginManager, PluginInfo, PluginStatus
from agentbus.plugins.core import PluginContext


class TestPluginCommands:
    """插件管理命令测试类"""
    
    @pytest.fixture
    def mock_plugin_manager(self):
        """创建模拟插件管理器"""
        manager = Mock(spec=PluginManager)
        
        # 模拟插件信息
        self.plugin_info_list = [
            PluginInfo(
                plugin_id="test_plugin_1",
                name="Test Plugin 1",
                version="1.0.0",
                description="Test plugin description",
                author="Test Author",
                class_name="TestPlugin1",
                module_path="/path/to/test_plugin_1.py",
                dependencies=[],
                status=PluginStatus.ACTIVE
            ),
            PluginInfo(
                plugin_id="test_plugin_2",
                name="Test Plugin 2", 
                version="2.0.0",
                description="Another test plugin",
                author="Test Author 2",
                class_name="TestPlugin2",
                module_path="/path/to/test_plugin_2.py",
                dependencies=["test_plugin_1"],
                status=PluginStatus.INACTIVE
            )
        ]
        
        manager.list_plugin_info.return_value = self.plugin_info_list
        manager.get_plugin_info.side_effect = lambda plugin_id: next(
            (info for info in self.plugin_info_list if info.plugin_id == plugin_id), None
        )
        
        # 模拟插件实例
        mock_plugin = Mock()
        mock_plugin.get_tools.return_value = []
        mock_plugin.get_commands.return_value = []
        mock_plugin.get_hooks.return_value = {}
        
        manager.get_plugin.return_value = mock_plugin
        manager.get_plugin_stats.return_value = {
            "total_plugins": 2,
            "active_plugins": 1,
            "loaded_plugins": 2,
            "error_plugins": 0,
            "total_tools": 0,
            "total_commands": 0,
            "total_hooks": 0,
            "plugins_by_status": {
                "active": 1,
                "inactive": 1,
                "error": 0,
                "unloaded": 0
            }
        }
        
        return manager
    
    @pytest.fixture
    def plugin_commands(self, mock_plugin_manager):
        """创建插件命令实例"""
        return PluginCommands(mock_plugin_manager)
    
    @pytest.mark.asyncio
    async def test_list_plugins(self, plugin_commands):
        """测试列出插件"""
        # 测试默认格式
        result = await plugin_commands.list_plugins()
        
        assert result["total"] == 2
        assert len(result["plugins"]) == 2
        assert "status_summary" in result
        
        # 测试JSON格式
        json_result = await plugin_commands.list_plugins(format_type="json")
        assert "total" in json_result
        assert "plugins" in json_result
        
        # 测试状态过滤
        filtered_result = await plugin_commands.list_plugins(status_filter="active")
        assert filtered_result["total"] == 1
        
    @pytest.mark.asyncio
    async def test_enable_plugin(self, plugin_commands, mock_plugin_manager):
        """测试启用插件"""
        # 模拟成功启用
        mock_plugin_manager.activate_plugin.return_value = True
        mock_plugin_manager.get_plugin_info.return_value = PluginInfo(
            plugin_id="test_plugin_1",
            name="Test Plugin 1",
            version="1.0.0",
            description="Test plugin description",
            author="Test Author",
            class_name="TestPlugin1",
            module_path="/path/to/test_plugin_1.py",
            dependencies=[],
            status=PluginStatus.INACTIVE
        )
        
        result = await plugin_commands.enable_plugin("test_plugin_1")
        
        assert result["success"] is True
        assert "test_plugin_1" in result["message"]
        mock_plugin_manager.activate_plugin.assert_called_once_with("test_plugin_1")
    
    @pytest.mark.asyncio
    async def test_disable_plugin(self, plugin_commands, mock_plugin_manager):
        """测试禁用插件"""
        # 模拟成功禁用
        mock_plugin_manager.deactivate_plugin.return_value = True
        
        result = await plugin_commands.disable_plugin("test_plugin_1")
        
        assert result["success"] is True
        assert "test_plugin_1" in result["message"]
        mock_plugin_manager.deactivate_plugin.assert_called_once_with("test_plugin_1")
    
    @pytest.mark.asyncio
    async def test_reload_plugin(self, plugin_commands, mock_plugin_manager):
        """测试重新加载插件"""
        # 模拟成功重新加载
        mock_plugin_manager.reload_plugin.return_value = True
        
        result = await plugin_commands.reload_plugin("test_plugin_1")
        
        assert result["success"] is True
        assert "test_plugin_1" in result["message"]
        mock_plugin_manager.reload_plugin.assert_called_once_with("test_plugin_1")
    
    @pytest.mark.asyncio
    async def test_unload_plugin(self, plugin_commands, mock_plugin_manager):
        """测试卸载插件"""
        # 模拟成功卸载
        mock_plugin_manager.unload_plugin.return_value = True
        
        result = await plugin_commands.unload_plugin("test_plugin_1")
        
        assert result["success"] is True
        assert "test_plugin_1" in result["message"]
        mock_plugin_manager.unload_plugin.assert_called_once_with("test_plugin_1")
    
    @pytest.mark.asyncio
    async def test_get_plugin_details(self, plugin_commands, mock_plugin_manager):
        """测试获取插件详细信息"""
        result = await plugin_commands.get_plugin_details("test_plugin_1")
        
        assert "plugin_id" in result
        assert "info" in result
        assert "resources" in result
        assert "statistics" in result
        
        assert result["plugin_id"] == "test_plugin_1"
        assert result["info"]["name"] == "Test Plugin 1"
    
    @pytest.mark.asyncio
    async def test_export_config(self, plugin_commands):
        """测试导出配置"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            result = await plugin_commands.export_config(output_path, "json")
            
            assert result["success"] is True
            assert "plugin_count" in result
            
            # 检查文件是否创建
            assert output_path.exists()
            
            # 验证JSON内容
            with open(output_path, 'r') as f:
                config_data = json.load(f)
            
            assert "version" in config_data
            assert "plugins" in config_data
            assert len(config_data["plugins"]) == 2
            
        finally:
            # 清理临时文件
            if output_path.exists():
                output_path.unlink()
    
    @pytest.mark.asyncio
    async def test_import_config(self, plugin_commands, mock_plugin_manager):
        """测试导入配置"""
        # 创建临时配置文件
        config_data = {
            "version": "1.0",
            "plugins": [
                {
                    "id": "imported_plugin",
                    "name": "Imported Plugin",
                    "version": "1.0.0",
                    "description": "Imported test plugin",
                    "author": "Import Test",
                    "dependencies": [],
                    "status": "active",
                    "module_path": "/path/to/imported_plugin.py",
                    "class_name": "ImportedPlugin"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            # 模拟加载插件成功
            mock_plugin_manager.load_plugin = AsyncMock()
            mock_plugin_manager.activate_plugin = AsyncMock()
            
            result = await plugin_commands.import_config(config_path)
            
            assert result["success"] is True
            assert result["imported_count"] == 1
            assert result["total_count"] == 1
            
            # 验证调用
            mock_plugin_manager.load_plugin.assert_called_once()
            
        finally:
            # 清理临时文件
            if config_path.exists():
                config_path.unlink()
    
    def test_cli_list_command(self, mock_plugin_manager):
        """测试CLI list命令"""
        runner = CliRunner()
        
        # 设置上下文
        ctx = Mock()
        ctx.obj = {'plugin_manager': mock_plugin_manager}
        
        # 模拟异步函数
        async def mock_list(*args, **kwargs):
            return {
                "total": 2,
                "plugins": [
                    {
                        "id": "test_plugin_1",
                        "name": "Test Plugin 1",
                        "version": "1.0.0",
                        "description": "Test plugin description",
                        "author": "Test Author",
                        "status": "active",
                        "dependencies": []
                    }
                ],
                "status_summary": {"active": 1, "inactive": 1}
            }
        
        with patch('agentbus.cli.commands.plugin_commands.PluginCommands.list_plugins', mock_list):
            result = runner.invoke(list, [], obj=ctx)
            
            assert result.exit_code == 0
            assert "插件列表" in result.output
            assert "Test Plugin 1" in result.output
    
    def test_cli_enable_command(self, mock_plugin_manager):
        """测试CLI enable命令"""
        runner = CliRunner()
        
        ctx = Mock()
        ctx.obj = {'plugin_manager': mock_plugin_manager}
        
        async def mock_enable(*args, **kwargs):
            return {
                "success": True,
                "message": "插件 test_plugin_1 已成功启用",
                "plugin_id": "test_plugin_1"
            }
        
        with patch('agentbus.cli.commands.plugin_commands.PluginCommands.enable_plugin', mock_enable):
            result = runner.invoke(enable, ['test_plugin_1'], obj=ctx)
            
            assert result.exit_code == 0
            assert "已成功启用" in result.output
    
    def test_cli_disable_command(self, mock_plugin_manager):
        """测试CLI disable命令"""
        runner = CliRunner()
        
        ctx = Mock()
        ctx.obj = {'plugin_manager': mock_plugin_manager}
        
        async def mock_disable(*args, **kwargs):
            return {
                "success": True,
                "message": "插件 test_plugin_1 已成功禁用",
                "plugin_id": "test_plugin_1"
            }
        
        with patch('agentbus.cli.commands.plugin_commands.PluginCommands.disable_plugin', mock_disable):
            result = runner.invoke(disable, ['test_plugin_1'], obj=ctx)
            
            assert result.exit_code == 0
            assert "已成功禁用" in result.output
    
    def test_cli_stats_command(self, mock_plugin_manager):
        """测试CLI stats命令"""
        runner = CliRunner()
        
        ctx = Mock()
        ctx.obj = {'plugin_manager': mock_plugin_manager}
        
        # 模拟异步get_plugin_stats
        async def mock_stats():
            return {
                "total_plugins": 2,
                "active_plugins": 1,
                "loaded_plugins": 2,
                "error_plugins": 0,
                "total_tools": 0,
                "total_commands": 0,
                "total_hooks": 0,
                "plugins_by_status": {
                    "active": 1,
                    "inactive": 1
                }
            }
        
        with patch.object(mock_plugin_manager, 'get_plugin_stats', mock_stats):
            result = runner.invoke(stats, [], obj=ctx)
            
            assert result.exit_code == 0
            assert "插件系统统计" in result.output
            assert "总插件数: 2" in result.output
    
    def test_create_plugin_commands(self, mock_plugin_manager):
        """测试创建插件命令实例"""
        commands = create_plugin_commands(mock_plugin_manager)
        
        assert isinstance(commands, PluginCommands)
        assert commands.plugin_manager == mock_plugin_manager


class TestPluginCommandsEdgeCases:
    """插件管理命令边界情况测试"""
    
    @pytest.fixture
    def mock_plugin_manager(self):
        """创建模拟插件管理器"""
        return Mock(spec=PluginManager)
    
    @pytest.mark.asyncio
    async def test_list_plugins_error_handling(self, mock_plugin_manager):
        """测试列出插件时的错误处理"""
        # 模拟异常
        mock_plugin_manager.list_plugin_info.side_effect = Exception("Test error")
        
        commands = PluginCommands(mock_plugin_manager)
        result = await commands.list_plugins()
        
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_enable_nonexistent_plugin(self, mock_plugin_manager):
        """测试启用不存在的插件"""
        mock_plugin_manager.get_plugin_info.return_value = None
        mock_plugin_manager.discover_plugins.return_value = []
        
        commands = PluginCommands(mock_plugin_manager)
        result = await commands.enable_plugin("nonexistent_plugin")
        
        assert result["success"] is False
        assert "未找到" in result["error"]
    
    @pytest.mark.asyncio
    async def test_export_invalid_format(self, mock_plugin_manager):
        """测试导出不支持的格式"""
        commands = PluginCommands(mock_plugin_manager)
        
        with tempfile.NamedTemporaryFile(suffix='.txt') as f:
            result = await commands.export_config(Path(f.name), "xml")
            
            assert "error" in result
            assert "不支持的格式" in result["error"]
    
    @pytest.mark.asyncio
    async def test_import_invalid_config_file(self, mock_plugin_manager):
        """测试导入无效的配置文件"""
        commands = PluginCommands(mock_plugin_manager)
        
        # 测试不支持的文件格式
        with tempfile.NamedTemporaryFile(suffix='.txt') as f:
            result = await commands.import_config(Path(f.name))
            
            assert "error" in result
            assert "不支持的配置文件格式" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_details_nonexistent_plugin(self, mock_plugin_manager):
        """测试获取不存在的插件详情"""
        mock_plugin_manager.get_plugin_info.return_value = None
        
        commands = PluginCommands(mock_plugin_manager)
        result = await commands.get_plugin_details("nonexistent_plugin")
        
        assert "error" in result
        assert "未找到" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__])