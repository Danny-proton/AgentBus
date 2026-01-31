"""
AgentBus插件管理器测试

此模块测试PluginManager类的所有功能，包括：
- 插件发现和加载
- 插件生命周期管理（激活、停用、卸载）
- 插件资源注册（工具、钩子、命令）
- 插件事件调度
- 错误处理和边界情况
- 插件依赖和冲突处理

测试覆盖：
- 单元测试：每个管理器方法
- 集成测试：完整的管理器功能
- 边界测试：错误情况和异常处理
- 性能测试：并发操作和大量插件
"""

import pytest
import asyncio
import tempfile
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from plugins.manager import (
    PluginManager,
    PluginInfo,
    PluginLoadError,
    PluginActivationError
)
from plugins.core import (
    PluginContext,
    AgentBusPlugin,
    PluginStatus,
    PluginResult
)


class TestPluginManager:
    """测试PluginManager类"""
    
    @pytest.fixture
    def plugin_manager(self):
        """创建插件管理器实例"""
        context = PluginContext(
            config={},
            logger=logging.getLogger("test_manager"),
            runtime={}
        )
        return PluginManager(context)
    
    @pytest.fixture
    def temp_plugin_dir(self):
        """创建临时插件目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_manager_initialization(self, plugin_manager):
        """测试管理器初始化"""
        assert plugin_manager._context is not None
        assert isinstance(plugin_manager._plugins, dict)
        assert isinstance(plugin_manager._plugin_info, dict)
        assert isinstance(plugin_manager._plugin_modules, dict)
        assert isinstance(plugin_manager._event_hooks, dict)
        assert isinstance(plugin_manager._tool_registry, dict)
        assert isinstance(plugin_manager._command_registry, dict)
        assert plugin_manager._lock is not None
    
    def test_default_plugin_dirs(self, plugin_manager):
        """测试默认插件目录设置"""
        dirs = plugin_manager._get_default_plugin_dirs()
        
        # 检查包含预期的目录
        expected_patterns = [
            "extensions",
            "plugins", 
            ".agentbus",
            "plugins"
        ]
        
        for pattern in expected_patterns:
            found = any(pattern in dir_path for dir_path in dirs)
            assert found, f"Expected pattern '{pattern}' not found in plugin directories"
    
    @pytest.mark.asyncio
    async def test_discover_plugins_empty_dir(self, plugin_manager, temp_plugin_dir):
        """测试在空目录中发现插件"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        discovered = await plugin_manager.discover_plugins()
        assert len(discovered) == 0
    
    @pytest.mark.asyncio
    async def test_discover_plugins_with_valid_plugin(self, plugin_manager, temp_plugin_dir):
        """测试发现有效插件"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        # 创建测试插件文件
        plugin_file = os.path.join(temp_plugin_dir, "test_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class TestPlugin(AgentBusPlugin):
    def get_info(self):
        return {
            'id': 'test_plugin',
            'name': 'Test Plugin',
            'version': '1.0.0',
            'description': 'A test plugin',
            'author': 'Test Author',
            'dependencies': []
        }
''')
        
        discovered = await plugin_manager.discover_plugins()
        assert len(discovered) == 1
        
        plugin_info = discovered[0]
        assert plugin_info.plugin_id == 'test_plugin'
        assert plugin_info.name == 'Test Plugin'
        assert plugin_info.version == '1.0.0'
        assert plugin_info.module_path == plugin_file
    
    @pytest.mark.asyncio
    async def test_discover_plugins_with_invalid_file(self, plugin_manager, temp_plugin_dir):
        """测试发现包含无效文件的插件"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        # 创建无效文件
        invalid_file = os.path.join(temp_plugin_dir, "invalid.py")
        with open(invalid_file, 'w') as f:
            f.write("print('not a plugin')")
        
        discovered = await plugin_manager.discover_plugins()
        assert len(discovered) == 0
    
    @pytest.mark.asyncio
    async def test_load_plugin(self, plugin_manager, temp_plugin_dir):
        """测试插件加载"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        # 创建测试插件文件
        plugin_file = os.path.join(temp_plugin_dir, "test_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class TestPlugin(AgentBusPlugin):
    def get_info(self):
        return {
            'id': 'test_plugin',
            'name': 'Test Plugin',
            'version': '1.0.0',
            'description': 'A test plugin',
            'author': 'Test Author',
            'dependencies': []
        }
''')
        
        plugin = await plugin_manager.load_plugin('test_plugin', plugin_file)
        
        assert plugin is not None
        assert plugin.plugin_id == 'test_plugin'
        assert plugin_manager._plugins['test_plugin'] == plugin
        assert plugin.status == PluginStatus.LOADED
    
    @pytest.mark.asyncio
    async def test_load_plugin_duplicate(self, plugin_manager, temp_plugin_dir):
        """测试重复加载插件"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        # 创建测试插件文件
        plugin_file = os.path.join(temp_plugin_dir, "test_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class TestPlugin(AgentBusPlugin):
    def get_info(self):
        return {
            'id': 'test_plugin',
            'name': 'Test Plugin',
            'version': '1.0.0',
            'description': 'A test plugin',
            'author': 'Test Author',
            'dependencies': []
        }
''')
        
        # 第一次加载
        plugin1 = await plugin_manager.load_plugin('test_plugin', plugin_file)
        
        # 第二次加载（应该返回已存在的实例）
        plugin2 = await plugin_manager.load_plugin('test_plugin', plugin_file)
        
        assert plugin1 is plugin2
        assert plugin_manager._plugins['test_plugin'] == plugin1
    
    @pytest.mark.asyncio
    async def test_load_plugin_nonexistent_file(self, plugin_manager):
        """测试加载不存在的插件文件"""
        with pytest.raises(PluginLoadError, match="Cannot find module"):
            await plugin_manager.load_plugin('test_plugin', '/nonexistent/file.py')
    
    @pytest.mark.asyncio
    async def test_load_plugin_invalid_class(self, plugin_manager, temp_plugin_dir):
        """测试加载无效插件类"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        # 创建不包含插件类的文件
        plugin_file = os.path.join(temp_plugin_dir, "invalid_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write('''
def some_function():
    pass
''')
        
        with pytest.raises(PluginLoadError, match="No valid plugin class found"):
            await plugin_manager.load_plugin('test_plugin', plugin_file)
    
    @pytest.mark.asyncio
    async def test_unload_plugin(self, plugin_manager, temp_plugin_dir):
        """测试插件卸载"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        # 创建并加载插件
        plugin_file = os.path.join(temp_plugin_dir, "test_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class TestPlugin(AgentBusPlugin):
    def get_info(self):
        return {
            'id': 'test_plugin',
            'name': 'Test Plugin',
            'version': '1.0.0',
            'description': 'A test plugin',
            'author': 'Test Author',
            'dependencies': []
        }
''')
        
        plugin = await plugin_manager.load_plugin('test_plugin', plugin_file)
        assert 'test_plugin' in plugin_manager._plugins
        
        # 卸载插件
        success = await plugin_manager.unload_plugin('test_plugin')
        assert success == True
        assert 'test_plugin' not in plugin_manager._plugins
        assert plugin.status == PluginStatus.UNLOADED
    
    @pytest.mark.asyncio
    async def test_unload_plugin_not_loaded(self, plugin_manager):
        """测试卸载未加载的插件"""
        success = await plugin_manager.unload_plugin('nonexistent_plugin')
        assert success == False
    
    @pytest.mark.asyncio
    async def test_activate_plugin(self, plugin_manager, temp_plugin_dir):
        """测试插件激活"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        # 创建插件
        plugin_file = os.path.join(temp_plugin_dir, "test_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class TestPlugin(AgentBusPlugin):
    def get_info(self):
        return {
            'id': 'test_plugin',
            'name': 'Test Plugin',
            'version': '1.0.0',
            'description': 'A test plugin',
            'author': 'Test Author',
            'dependencies': []
        }
''')
        
        plugin = await plugin_manager.load_plugin('test_plugin', plugin_file)
        
        success = await plugin_manager.activate_plugin('test_plugin')
        assert success == True
        assert plugin.status == PluginStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_activate_plugin_not_loaded(self, plugin_manager):
        """测试激活未加载的插件"""
        success = await plugin_manager.activate_plugin('nonexistent_plugin')
        assert success == False
    
    @pytest.mark.asyncio
    async def test_activate_plugin_failure(self, plugin_manager, temp_plugin_dir):
        """测试插件激活失败"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        # 创建激活失败的插件
        plugin_file = os.path.join(temp_plugin_dir, "test_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class TestPlugin(AgentBusPlugin):
    def get_info(self):
        return {
            'id': 'test_plugin',
            'name': 'Test Plugin',
            'version': '1.0.0',
            'description': 'A test plugin',
            'author': 'Test Author',
            'dependencies': []
        }
    
    async def activate(self):
        raise Exception("Activation failed")
''')
        
        plugin = await plugin_manager.load_plugin('test_plugin', plugin_file)
        
        success = await plugin_manager.activate_plugin('test_plugin')
        assert success == False
        assert plugin.status == PluginStatus.ERROR
    
    @pytest.mark.asyncio
    async def test_deactivate_plugin(self, plugin_manager, temp_plugin_dir):
        """测试插件停用"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        # 创建并激活插件
        plugin_file = os.path.join(temp_plugin_dir, "test_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class TestPlugin(AgentBusPlugin):
    def get_info(self):
        return {
            'id': 'test_plugin',
            'name': 'Test Plugin',
            'version': '1.0.0',
            'description': 'A test plugin',
            'author': 'Test Author',
            'dependencies': []
        }
''')
        
        plugin = await plugin_manager.load_plugin('test_plugin', plugin_file)
        await plugin_manager.activate_plugin('test_plugin')
        
        success = await plugin_manager.deactivate_plugin('test_plugin')
        assert success == True
        assert plugin.status == PluginStatus.DEACTIVATED
    
    @pytest.mark.asyncio
    async def test_reload_plugin(self, plugin_manager, temp_plugin_dir):
        """测试插件重新加载"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        # 创建插件文件
        plugin_file = os.path.join(temp_plugin_dir, "test_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class TestPlugin(AgentBusPlugin):
    def get_info(self):
        return {
            'id': 'test_plugin',
            'name': 'Test Plugin',
            'version': '1.0.0',
            'description': 'A test plugin',
            'author': 'Test Author',
            'dependencies': []
        }
''')
        
        # 首次加载并激活
        plugin1 = await plugin_manager.load_plugin('test_plugin', plugin_file)
        await plugin_manager.activate_plugin('test_plugin')
        original_plugin = plugin1
        
        # 修改插件文件
        with open(plugin_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class TestPlugin(AgentBusPlugin):
    def get_info(self):
        return {
            'id': 'test_plugin',
            'name': 'Test Plugin Reloaded',
            'version': '1.0.1',
            'description': 'A reloaded test plugin',
            'author': 'Test Author',
            'dependencies': []
        }
''')
        
        # 重新加载
        success = await plugin_manager.reload_plugin('test_plugin')
        assert success == True
        
        # 检查插件被重新加载
        plugin2 = plugin_manager.get_plugin('test_plugin')
        assert plugin2 is not original_plugin
        assert plugin2.get_info()['name'] == 'Test Plugin Reloaded'
        assert plugin2.status == PluginStatus.ACTIVE  # 保持激活状态
    
    @pytest.mark.asyncio
    async def test_execute_hook(self, plugin_manager, temp_plugin_dir):
        """测试钩子执行"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        # 创建带钩子的插件
        plugin_file = os.path.join(temp_plugin_dir, "test_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class TestPlugin(AgentBusPlugin):
    def get_info(self):
        return {
            'id': 'test_plugin',
            'name': 'Test Plugin',
            'version': '1.0.0',
            'description': 'A test plugin',
            'author': 'Test Author',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_hook("test_event", self.test_hook)
    
    async def test_hook(self, message):
        return f"Hook processed: {message}"
''')
        
        plugin = await plugin_manager.load_plugin('test_plugin', plugin_file)
        await plugin_manager.activate_plugin('test_plugin')
        
        # 执行钩子
        results = await plugin_manager.execute_hook("test_event", "Hello World")
        assert len(results) == 1
        assert results[0] == "Hook processed: Hello World"
    
    @pytest.mark.asyncio
    async def test_execute_hook_multiple_plugins(self, plugin_manager, temp_plugin_dir):
        """测试多个插件的钩子执行"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        # 创建第一个插件
        plugin1_file = os.path.join(temp_plugin_dir, "plugin1.py")
        with open(plugin1_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class Plugin1(AgentBusPlugin):
    def get_info(self):
        return {
            'id': 'plugin1',
            'name': 'Plugin 1',
            'version': '1.0.0',
            'description': 'Plugin 1',
            'author': 'Test Author',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_hook("test_event", self.hook1, priority=10)
    
    async def hook1(self, message):
        return f"Plugin1: {message}"
''')
        
        # 创建第二个插件
        plugin2_file = os.path.join(temp_plugin_dir, "plugin2.py")
        with open(plugin2_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class Plugin2(AgentBusPlugin):
    def get_info(self):
        return {
            'id': 'plugin2',
            'name': 'Plugin 2',
            'version': '1.0.0',
            'description': 'Plugin 2',
            'author': 'Test Author',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_hook("test_event", self.hook2, priority=5)
    
    async def hook2(self, message):
        return f"Plugin2: {message}"
''')
        
        # 加载并激活两个插件
        plugin1 = await plugin_manager.load_plugin('plugin1', plugin1_file)
        plugin2 = await plugin_manager.load_plugin('plugin2', plugin2_file)
        
        await plugin_manager.activate_plugin('plugin1')
        await plugin_manager.activate_plugin('plugin2')
        
        # 执行钩子（应该按优先级执行）
        results = await plugin_manager.execute_hook("test_event", "Hello")
        
        assert len(results) == 2
        # 优先级高的先执行
        assert results[0] == "Plugin1: Hello"
        assert results[1] == "Plugin2: Hello"
    
    @pytest.mark.asyncio
    async def test_execute_tool(self, plugin_manager, temp_plugin_dir):
        """测试工具执行"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        # 创建带工具的插件
        plugin_file = os.path.join(temp_plugin_dir, "test_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class TestPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.call_count = 0
    
    def get_info(self):
        return {
            'id': 'test_plugin',
            'name': 'Test Plugin',
            'version': '1.0.0',
            'description': 'A test plugin',
            'author': 'Test Author',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("test_tool", "Test tool", self.test_tool)
    
    def test_tool(self, x, y="default"):
        self.call_count += 1
        return f"Result: {x}, {y}"
''')
        
        plugin = await plugin_manager.load_plugin('test_plugin', plugin_file)
        await plugin_manager.activate_plugin('test_plugin')
        
        # 执行工具
        result = await plugin_manager.execute_tool("test_tool", 5, y="custom")
        assert result == "Result: 5, custom"
        
        # 再次执行以验证状态保持
        result = await plugin_manager.execute_tool("test_tool", 10)
        assert result == "Result: 10, default"
        assert plugin.call_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, plugin_manager):
        """测试执行不存在的工具"""
        with pytest.raises(ValueError, match="Tool 'nonexistent' not found"):
            await plugin_manager.execute_tool("nonexistent")
    
    def test_get_plugin(self, plugin_manager):
        """测试获取插件实例"""
        # 测试不存在的插件
        plugin = plugin_manager.get_plugin("nonexistent")
        assert plugin is None
    
    def test_get_plugin_info(self, plugin_manager):
        """测试获取插件信息"""
        # 测试不存在的插件信息
        info = plugin_manager.get_plugin_info("nonexistent")
        assert info is None
    
    def test_list_plugins(self, plugin_manager):
        """测试列出插件"""
        plugins = plugin_manager.list_plugins()
        assert isinstance(plugins, list)
        assert len(plugins) == 0
    
    def test_list_plugin_info(self, plugin_manager):
        """测试列出插件信息"""
        info_list = plugin_manager.list_plugin_info()
        assert isinstance(info_list, list)
        assert len(info_list) == 0
    
    def test_get_tools(self, plugin_manager):
        """测试获取工具注册信息"""
        tools = plugin_manager.get_tools()
        assert isinstance(tools, dict)
        assert len(tools) == 0
    
    def test_get_commands(self, plugin_manager):
        """测试获取命令注册信息"""
        commands = plugin_manager.get_commands()
        assert isinstance(commands, dict)
        assert len(commands) == 0
    
    def test_get_hooks(self, plugin_manager):
        """测试获取钩子注册信息"""
        hooks = plugin_manager.get_hooks()
        assert isinstance(hooks, dict)
        assert len(hooks) == 0
    
    def test_get_plugin_status(self, plugin_manager):
        """测试获取插件状态"""
        # 测试不存在的插件
        status = plugin_manager.get_plugin_status("nonexistent")
        assert status is None
    
    @pytest.mark.asyncio
    async def test_get_plugin_stats(self, plugin_manager, temp_plugin_dir):
        """测试获取插件统计信息"""
        plugin_manager._plugin_dirs = [temp_plugin_dir]
        
        # 创建插件
        plugin_file = os.path.join(temp_plugin_dir, "test_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class TestPlugin(AgentBusPlugin):
    def get_info(self):
        return {
            'id': 'test_plugin',
            'name': 'Test Plugin',
            'version': '1.0.0',
            'description': 'A test plugin',
            'author': 'Test Author',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("test_tool", "Test tool", self.test_tool)
        self.register_hook("test_event", self.test_hook)
        self.register_command("/test", self.test_command, "Test command")
    
    def test_tool(self):
        return "test"
    
    async def test_hook(self):
        pass
    
    async def test_command(self):
        return "test"
''')
        
        # 加载插件
        plugin = await plugin_manager.load_plugin('test_plugin', plugin_file)
        await plugin_manager.activate_plugin('test_plugin')
        
        # 获取统计信息
        stats = await plugin_manager.get_plugin_stats()
        
        assert stats['total_plugins'] == 1
        assert stats['active_plugins'] == 1
        assert stats['loaded_plugins'] == 0
        assert stats['error_plugins'] == 0
        assert stats['total_tools'] == 1
        assert stats['total_commands'] == 1
        assert stats['total_hooks'] == 1
        assert 'plugins_by_status' in stats


# 集成测试类
class TestPluginManagerIntegration:
    """插件管理器集成测试"""
    
    @pytest.fixture
    def integration_manager(self):
        """创建集成测试管理器"""
        context = PluginContext(
            config={},
            logger=logging.getLogger("integration_test"),
            runtime={}
        )
        return PluginManager(context)
    
    @pytest.fixture
    def plugin_dir(self):
        """创建插件测试目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_full_plugin_workflow(self, integration_manager, plugin_dir):
        """测试完整的插件工作流程"""
        integration_manager._plugin_dirs = [plugin_dir]
        
        # 1. 创建插件
        plugin_file = os.path.join(plugin_dir, "workflow_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext
import asyncio

class WorkflowPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.events_processed = []
    
    def get_info(self):
        return {
            'id': 'workflow_plugin',
            'name': 'Workflow Plugin',
            'version': '1.0.0',
            'description': 'Plugin for workflow testing',
            'author': 'Integration Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("process_data", "Process data", self.process_data)
        self.register_tool("get_status", "Get status", self.get_status)
        self.register_hook("data_received", self.handle_data)
        self.register_command("/status", self.status_command, "Get plugin status")
    
    def process_data(self, data: str) -> str:
        return f"Processed: {data.upper()}"
    
    def get_status(self) -> dict:
        return {
            'plugin_id': self.plugin_id,
            'events_processed': len(self.events_processed),
            'status': self.status.value
        }
    
    async def handle_data(self, data: str):
        self.events_processed.append(data)
        self.context.logger.info(f"Processed data: {data}")
    
    async def status_command(self, args: str) -> str:
        status = self.get_status()
        return f"Plugin Status: {status}"
''')
        
        # 2. 发现插件
        discovered = await integration_manager.discover_plugins()
        assert len(discovered) == 1
        assert discovered[0].plugin_id == 'workflow_plugin'
        
        # 3. 加载插件
        plugin = await integration_manager.load_plugin('workflow_plugin', plugin_file)
        assert plugin is not None
        assert plugin.status == PluginStatus.LOADED
        
        # 4. 激活插件
        success = await integration_manager.activate_plugin('workflow_plugin')
        assert success == True
        assert plugin.status == PluginStatus.ACTIVE
        
        # 5. 执行工具
        result = await integration_manager.execute_tool("process_data", "hello world")
        assert result == "Processed: HELLO WORLD"
        
        status_result = await integration_manager.execute_tool("get_status")
        assert status_result['plugin_id'] == 'workflow_plugin'
        assert status_result['status'] == 'active'
        
        # 6. 执行钩子
        results = await integration_manager.execute_hook("data_received", "test data")
        assert len(results) == 1
        
        # 再次检查状态
        status_result = await integration_manager.execute_tool("get_status")
        assert status_result['events_processed'] == 1
        
        # 7. 获取统计信息
        stats = await integration_manager.get_plugin_stats()
        assert stats['total_plugins'] == 1
        assert stats['active_plugins'] == 1
        assert stats['total_tools'] == 2
        assert stats['total_hooks'] == 1
        assert stats['total_commands'] == 1
        
        # 8. 停用插件
        success = await integration_manager.deactivate_plugin('workflow_plugin')
        assert success == True
        assert plugin.status == PluginStatus.DEACTIVATED
        
        # 9. 卸载插件
        success = await integration_manager.unload_plugin('workflow_plugin')
        assert success == True
        assert 'workflow_plugin' not in integration_manager._plugins
    
    @pytest.mark.asyncio
    async def test_concurrent_plugin_operations(self, integration_manager, plugin_dir):
        """测试并发插件操作"""
        integration_manager._plugin_dirs = [plugin_dir]
        
        # 创建多个插件
        for i in range(5):
            plugin_file = os.path.join(plugin_dir, f"plugin_{i}.py")
            with open(plugin_file, 'w') as f:
                f.write(f'''
from plugins import AgentBusPlugin, PluginContext

class Plugin{i}(AgentBusPlugin):
    def get_info(self):
        return {{
            'id': 'plugin_{i}',
            'name': 'Plugin {i}',
            'version': '1.0.0',
            'description': 'Plugin {i}',
            'author': 'Test',
            'dependencies': []
        }}
    
    async def activate(self):
        await super().activate()
        self.register_tool("test_tool", "Test tool", self.test_tool)
    
    def test_tool(self):
        return "result_{i}"
''')
        
        # 并发加载所有插件
        load_tasks = []
        for i in range(5):
            plugin_file = os.path.join(plugin_dir, f"plugin_{i}.py")
            task = integration_manager.load_plugin(f'plugin_{i}', plugin_file)
            load_tasks.append(task)
        
        loaded_plugins = await asyncio.gather(*load_tasks)
        assert len(loaded_plugins) == 5
        
        # 并发激活所有插件
        activate_tasks = []
        for i in range(5):
            task = integration_manager.activate_plugin(f'plugin_{i}')
            activate_tasks.append(task)
        
        activate_results = await asyncio.gather(*activate_tasks)
        assert all(activate_results)
        
        # 验证所有插件都激活成功
        for i in range(5):
            plugin = integration_manager.get_plugin(f'plugin_{i}')
            assert plugin.status == PluginStatus.ACTIVE
        
        # 并发执行工具
        execute_tasks = []
        for i in range(5):
            task = integration_manager.execute_tool(f"test_tool", plugin_id=f'plugin_{i}')
            execute_tasks.append(task)
        
        tool_results = await asyncio.gather(*execute_tasks)
        expected_results = [f"result_{i}" for i in range(5)]
        assert set(tool_results) == set(expected_results)
    
    @pytest.mark.asyncio
    async def test_plugin_error_recovery(self, integration_manager, plugin_dir):
        """测试插件错误恢复"""
        integration_manager._plugin_dirs = [plugin_dir]
        
        # 创建会出错的插件
        plugin_file = os.path.join(plugin_dir, "error_plugin.py")
        with open(plugin_file, 'w') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class ErrorPlugin(AgentBusPlugin):
    def get_info(self):
        return {
            'id': 'error_plugin',
            'name': 'Error Plugin',
            'version': '1.0.0',
            'description': 'Plugin that fails',
            'author': 'Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("error_tool", "Error tool", self.error_tool)
    
    def error_tool(self):
        raise Exception("Tool execution failed")
''')
        
        # 加载并激活插件
        plugin = await integration_manager.load_plugin('error_plugin', plugin_file)
        success = await integration_manager.activate_plugin('error_plugin')
        assert success == True
        assert plugin.status == PluginStatus.ACTIVE
        
        # 尝试执行会出错的工具
        result = await integration_manager.execute_tool("error_tool")
        assert isinstance(result, Exception)
        assert str(result) == "Tool execution failed"
        
        # 插件状态应该仍然是激活的
        assert plugin.status == PluginStatus.ACTIVE
        
        # 停用插件
        success = await integration_manager.deactivate_plugin('error_plugin')
        assert success == True
        assert plugin.status == PluginStatus.DEACTIVATED