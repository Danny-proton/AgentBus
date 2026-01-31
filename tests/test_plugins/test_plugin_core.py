"""
AgentBus插件框架核心功能测试

此模块测试插件系统的核心组件：
- PluginContext: 插件上下文
- AgentBusPlugin: 插件基类
- PluginTool: 工具定义
- PluginHook: 钩子定义
- PluginStatus: 插件状态枚举

测试内容：
- 组件初始化和验证
- 插件生命周期管理
- 工具注册和管理
- 钩子注册和事件处理
- 配置和运行时变量管理
- 错误处理和边界情况
"""

import pytest
import asyncio
import logging
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from plugins.core import (
    PluginContext,
    AgentBusPlugin, 
    PluginTool,
    PluginHook,
    PluginStatus,
    PluginResult
)


class TestPluginContext:
    """测试PluginContext类"""
    
    def test_plugin_context_initialization(self, mock_logger):
        """测试插件上下文初始化"""
        config = {"key": "value"}
        runtime = {"runtime_key": "runtime_value"}
        
        context = PluginContext(config=config, logger=mock_logger, runtime=runtime)
        
        assert context.config == config
        assert context.logger == mock_logger
        assert context.runtime == runtime
    
    def test_plugin_context_validation(self, mock_logger):
        """测试插件上下文验证"""
        # 测试无效配置类型
        with pytest.raises(TypeError, match="Config must be a dictionary"):
            PluginContext(config="invalid", logger=mock_logger, runtime={})
        
        # 测试无效日志器类型
        with pytest.raises(TypeError, match="Logger must be a logging.Logger instance"):
            PluginContext(config={}, logger="invalid", runtime={})
        
        # 测试无效运行时类型
        with pytest.raises(TypeError, match="Runtime must be a dictionary"):
            PluginContext(config={}, logger=mock_logger, runtime="invalid")


class TestPluginTool:
    """测试PluginTool类"""
    
    def test_plugin_tool_creation(self):
        """测试插件工具创建"""
        def test_func(x: int, y: str = "default") -> str:
            return f"{y}_{x}"
        
        tool = PluginTool(
            name="test_tool",
            description="Test tool description",
            function=test_func,
            parameters={},
            async_func=False
        )
        
        assert tool.name == "test_tool"
        assert tool.description == "Test tool description"
        assert tool.function == test_func
        assert tool.async_func == False
    
    def test_plugin_tool_validation(self):
        """测试插件工具验证"""
        # 测试不可调用的函数
        with pytest.raises(TypeError, match="Tool function must be callable"):
            PluginTool(
                name="test_tool",
                description="Test tool",
                function="not_callable",
                parameters={}
            )
    
    def test_plugin_tool_signature_analysis(self):
        """测试插件工具函数签名分析"""
        def test_func(x: int, y: str = "default", z: bool = True) -> str:
            return f"{y}_{x}_{z}"
        
        tool = PluginTool(
            name="test_tool",
            description="Test tool",
            function=test_func,
            parameters={}
        )
        
        # 检查参数分析
        assert "x" in tool.parameters
        assert "y" in tool.parameters
        assert "z" in tool.parameters
        
        # 检查参数属性
        assert tool.parameters["x"]["type"] == "int"
        assert tool.parameters["x"]["required"] == True
        
        assert tool.parameters["y"]["type"] == "str"
        assert tool.parameters["y"]["default"] == "default"
        assert tool.parameters["y"]["required"] == False
        
        assert tool.parameters["z"]["type"] == "bool"
        assert tool.parameters["z"]["default"] == True
        assert tool.parameters["z"]["required"] == False


class TestPluginHook:
    """测试PluginHook类"""
    
    def test_plugin_hook_creation(self):
        """测试插件钩子创建"""
        def test_handler(message: str) -> None:
            pass
        
        hook = PluginHook(
            event="test_event",
            handler=test_handler,
            priority=5,
            async_func=False
        )
        
        assert hook.event == "test_event"
        assert hook.handler == test_handler
        assert hook.priority == 5
        assert hook.async_func == False
    
    def test_plugin_hook_validation(self):
        """测试插件钩子验证"""
        # 测试不可调用的处理函数
        with pytest.raises(TypeError, match="Hook handler must be callable"):
            PluginHook(
                event="test_event",
                handler="not_callable"
            )
    
    def test_async_hook_detection(self):
        """测试异步钩子检测"""
        async def async_handler(message: str) -> None:
            pass
        
        def sync_handler(message: str) -> None:
            pass
        
        async_hook = PluginHook(event="test", handler=async_handler)
        sync_hook = PluginHook(event="test", handler=sync_handler)
        
        assert async_hook.async_func == True
        assert sync_hook.async_func == False


class TestAgentBusPlugin:
    """测试AgentBusPlugin基类"""
    
    @pytest.fixture
    def test_plugin(self, plugin_context):
        """创建测试插件实例"""
        class TestPlugin(AgentBusPlugin):
            def get_info(self) -> Dict[str, Any]:
                return {
                    'id': self.plugin_id,
                    'name': 'Test Plugin',
                    'version': '1.0.0',
                    'description': 'A test plugin',
                    'author': 'Test Author',
                    'dependencies': []
                }
        
        return TestPlugin("test_plugin", plugin_context)
    
    def test_plugin_initialization(self, test_plugin):
        """测试插件初始化"""
        assert test_plugin.plugin_id == "test_plugin"
        assert test_plugin.status == PluginStatus.UNLOADED
        assert len(test_plugin._tools) == 0
        assert len(test_plugin._hooks) == 0
        assert len(test_plugin._commands) == 0
    
    def test_plugin_validation(self, plugin_context):
        """测试插件验证"""
        # 测试无效插件ID
        with pytest.raises(ValueError, match="Plugin ID must be a non-empty string"):
            class TestPlugin(AgentBusPlugin):
                def get_info(self) -> Dict[str, Any]:
                    return {}
            TestPlugin("", plugin_context)
        
        # 测试无效上下文类型
        with pytest.raises(TypeError, match="Context must be a PluginContext instance"):
            class TestPlugin(AgentBusPlugin):
                def get_info(self) -> Dict[str, Any]:
                    return {}
            TestPlugin("test", "invalid_context")
    
    @pytest.mark.asyncio
    async def test_plugin_activate(self, test_plugin):
        """测试插件激活"""
        # 模拟日志记录
        with patch.object(test_plugin.context.logger, 'info') as mock_info:
            result = await test_plugin.activate()
            
            assert result == True
            assert test_plugin.status == PluginStatus.ACTIVE
            mock_info.assert_any_call(f"Activating plugin {test_plugin.plugin_id}")
            mock_info.assert_any_call(f"Plugin {test_plugin.plugin_id} activated successfully")
    
    @pytest.mark.asyncio
    async def test_plugin_activate_failure(self, test_plugin):
        """测试插件激活失败"""
        # 模拟激活失败
        with patch.object(test_plugin, 'activate', side_effect=Exception("Activation failed")):
            with patch.object(test_plugin.context.logger, 'error') as mock_error:
                result = await test_plugin.activate()
                
                assert result == False
                assert test_plugin.status == PluginStatus.ERROR
                mock_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_plugin_deactivate(self, test_plugin):
        """测试插件停用"""
        # 先激活插件
        test_plugin.status = PluginStatus.ACTIVE
        
        with patch.object(test_plugin.context.logger, 'info') as mock_info:
            result = await test_plugin.deactivate()
            
            assert result == True
            assert test_plugin.status == PluginStatus.DEACTIVATED
            mock_info.assert_any_call(f"Deactivating plugin {test_plugin.plugin_id}")
            mock_info.assert_any_call(f"Plugin {test_plugin.plugin_id} deactivated successfully")
    
    @pytest.mark.asyncio
    async def test_plugin_deactivate_failure(self, test_plugin):
        """测试插件停用失败"""
        # 设置插件为激活状态
        test_plugin.status = PluginStatus.ACTIVE
        
        # 模拟停用失败
        with patch.object(test_plugin, 'deactivate', side_effect=Exception("Deactivation failed")):
            with patch.object(test_plugin.context.logger, 'error') as mock_error:
                result = await test_plugin.deactivate()
                
                assert result == False
                assert test_plugin.status == PluginStatus.ERROR
                mock_error.assert_called_once()
    
    def test_tool_registration(self, test_plugin):
        """测试工具注册"""
        def test_tool(x: int) -> str:
            return f"result_{x}"
        
        tool = test_plugin.register_tool(
            name="test_tool",
            description="Test tool",
            function=test_tool
        )
        
        assert len(test_plugin._tools) == 1
        assert tool.name == "test_tool"
        assert tool.description == "Test tool"
        assert tool.function == test_tool
    
    def test_tool_registration_duplicate_name(self, test_plugin):
        """测试工具名称重复注册"""
        def test_tool1(x: int) -> str:
            return "result1"
        
        def test_tool2(x: int) -> str:
            return "result2"
        
        test_plugin.register_tool("test_tool", "Test tool 1", test_tool1)
        
        with pytest.raises(ValueError, match="Tool 'test_tool' already registered"):
            test_plugin.register_tool("test_tool", "Test tool 2", test_tool2)
    
    def test_hook_registration(self, test_plugin):
        """测试钩子注册"""
        async def test_hook(message: str) -> None:
            pass
        
        hook = test_plugin.register_hook(
            event="test_event",
            handler=test_hook,
            priority=10
        )
        
        assert "test_event" in test_plugin._hooks
        assert len(test_plugin._hooks["test_event"]) == 1
        assert hook.event == "test_event"
        assert hook.priority == 10
    
    def test_hook_priority_sorting(self, test_plugin):
        """测试钩子优先级排序"""
        async def low_priority_hook(message: str) -> None:
            pass
        
        async def high_priority_hook(message: str) -> None:
            pass
        
        # 注册不同优先级的钩子
        test_plugin.register_hook("test_event", low_priority_hook, priority=5)
        test_plugin.register_hook("test_event", high_priority_hook, priority=10)
        
        hooks = test_plugin._hooks["test_event"]
        assert len(hooks) == 2
        # 优先级高的应该在前
        assert hooks[0].priority == 10
        assert hooks[1].priority == 5
    
    def test_command_registration(self, test_plugin):
        """测试命令注册"""
        async def test_command(args: str) -> str:
            return f"Command result: {args}"
        
        cmd = test_plugin.register_command(
            command="/test",
            handler=test_command,
            description="Test command"
        )
        
        assert len(test_plugin._commands) == 1
        assert cmd['command'] == "/test"
        assert cmd['description'] == "Test command"
        assert cmd['async_func'] == True
    
    def test_tool_execution(self, test_plugin):
        """测试工具执行"""
        def test_tool(x: int, y: str = "default") -> str:
            return f"{y}_{x}"
        
        test_plugin.register_tool("test_tool", "Test tool", test_tool)
        
        # 同步工具执行
        result = test_plugin.execute_tool("test_tool", 5, y="test")
        assert result == "test_5"
    
    @pytest.mark.asyncio
    async def test_async_tool_execution(self, test_plugin):
        """测试异步工具执行"""
        async def async_tool(x: int) -> str:
            await asyncio.sleep(0.01)  # 短暂延迟
            return f"async_result_{x}"
        
        test_plugin.register_tool("async_tool", "Async tool", async_tool)
        
        result = await test_plugin.execute_tool("async_tool", 3)
        assert result == "async_result_3"
    
    def test_tool_execution_not_found(self, test_plugin):
        """测试工具不存在时的执行"""
        with pytest.raises(ValueError, match="Tool 'nonexistent' not found"):
            test_plugin.execute_tool("nonexistent")
    
    def test_tool_execution_error(self, test_plugin):
        """测试工具执行错误"""
        def error_tool(x: int) -> int:
            raise ValueError("Tool error")
        
        test_plugin.register_tool("error_tool", "Error tool", error_tool)
        
        result = test_plugin.execute_tool("error_tool", 1)
        assert isinstance(result, ValueError)
        assert str(result) == "Tool error"
    
    def test_config_management(self, test_plugin):
        """测试配置管理"""
        # 设置配置
        test_plugin.set_config("test_key", "test_value")
        
        # 获取配置
        value = test_plugin.get_config("test_key")
        assert value == "test_value"
        
        # 获取默认值
        default_value = test_plugin.get_config("nonexistent", "default")
        assert default_value == "default"
    
    def test_runtime_management(self, test_plugin):
        """测试运行时变量管理"""
        # 设置运行时变量
        test_plugin.set_runtime("runtime_key", "runtime_value")
        
        # 获取运行时变量
        value = test_plugin.get_runtime("runtime_key")
        assert value == "runtime_value"
        
        # 获取默认值
        default_value = test_plugin.get_runtime("nonexistent", "default")
        assert default_value == "default"
    
    def test_plugin_string_representation(self, test_plugin):
        """测试插件字符串表示"""
        str_repr = str(test_plugin)
        assert "AgentBusPlugin(test_plugin" in str_repr
        assert "status=unloaded" in str_repr
        
        repr_str = repr(test_plugin)
        assert "AgentBusPlugin(" in repr_str
        assert "plugin_id='test_plugin'" in repr_str
        assert "status=unloaded" in repr_str
        assert "tools=0" in repr_str
        assert "hooks=0" in repr_str


class TestPluginStatus:
    """测试PluginStatus枚举"""
    
    def test_plugin_status_values(self):
        """测试插件状态值"""
        assert PluginStatus.UNLOADED.value == "unloaded"
        assert PluginStatus.LOADING.value == "loading"
        assert PluginStatus.LOADED.value == "loaded"
        assert PluginStatus.ACTIVATING.value == "activating"
        assert PluginStatus.ACTIVE.value == "active"
        assert PluginStatus.DEACTIVATING.value == "deactivating"
        assert PluginStatus.DEACTIVATED.value == "deactivated"
        assert PluginStatus.ERROR.value == "error"
        assert PluginStatus.DISABLED.value == "disabled"
    
    def test_plugin_status_completeness(self):
        """测试插件状态完整性"""
        expected_statuses = {
            "unloaded", "loading", "loaded", "activating", 
            "active", "deactivating", "deactivated", 
            "error", "disabled"
        }
        
        actual_statuses = {status.value for status in PluginStatus}
        assert actual_statuses == expected_statuses


# 集成测试类
class TestPluginIntegration:
    """插件集成测试"""
    
    @pytest.fixture
    def complex_plugin(self, plugin_context):
        """创建复杂插件实例"""
        class ComplexPlugin(AgentBusPlugin):
            def __init__(self, plugin_id: str, context: PluginContext):
                super().__init__(plugin_id, context)
                self.execution_log = []
            
            def get_info(self) -> Dict[str, Any]:
                return {
                    'id': self.plugin_id,
                    'name': 'Complex Plugin',
                    'version': '2.0.0',
                    'description': 'A complex test plugin',
                    'author': 'Integration Test',
                    'dependencies': []
                }
            
            async def activate(self):
                await super().activate()
                
                # 注册多个工具
                self.register_tool("sync_tool", "Sync tool", self.sync_tool)
                self.register_tool("async_tool", "Async tool", self.async_tool)
                
                # 注册多个钩子
                self.register_hook("test_event", self.event_handler1, priority=10)
                self.register_hook("test_event", self.event_handler2, priority=5)
                
                # 注册命令
                self.register_command("/complex", self.complex_command, "Complex command")
            
            def sync_tool(self, x: int) -> str:
                return f"sync_{x}"
            
            async def async_tool(self, x: int) -> str:
                await asyncio.sleep(0.01)
                return f"async_{x}"
            
            async def event_handler1(self, data: str):
                self.execution_log.append(f"handler1_{data}")
            
            async def event_handler2(self, data: str):
                self.execution_log.append(f"handler2_{data}")
            
            async def complex_command(self, args: str) -> str:
                return f"Complex: {args}"
        
        return ComplexPlugin("complex_plugin", plugin_context)
    
    @pytest.mark.asyncio
    async def test_complete_plugin_lifecycle(self, complex_plugin):
        """测试完整的插件生命周期"""
        # 初始状态
        assert complex_plugin.status == PluginStatus.UNLOADED
        
        # 激活
        success = await complex_plugin.activate()
        assert success == True
        assert complex_plugin.status == PluginStatus.ACTIVE
        
        # 检查工具注册
        tools = complex_plugin.get_tools()
        assert len(tools) == 2
        tool_names = {tool.name for tool in tools}
        assert "sync_tool" in tool_names
        assert "async_tool" in tool_names
        
        # 检查钩子注册
        hooks = complex_plugin.get_hooks()
        assert "test_event" in hooks
        assert len(hooks["test_event"]) == 2
        
        # 测试工具执行
        sync_result = complex_plugin.execute_tool("sync_tool", 5)
        assert sync_result == "sync_5"
        
        async_result = await complex_plugin.execute_tool("async_tool", 3)
        assert async_result == "async_3"
        
        # 测试钩子执行
        await complex_plugin.on_message_received("test_data", "sender")
        
        # 停用
        success = await complex_plugin.deactivate()
        assert success == True
        assert complex_plugin.status == PluginStatus.DEACTIVATED
    
    @pytest.mark.asyncio
    async def test_plugin_error_handling(self, plugin_context):
        """测试插件错误处理"""
        class ErrorPlugin(AgentBusPlugin):
            def get_info(self) -> Dict[str, Any]:
                return {
                    'id': 'error_plugin',
                    'name': 'Error Plugin',
                    'version': '1.0.0',
                    'description': 'Plugin with errors',
                    'author': 'Test',
                    'dependencies': []
                }
            
            async def activate(self):
                await super().activate()
                raise Exception("Activation error")
        
        plugin = ErrorPlugin("error_plugin", plugin_context)
        
        # 激活应该失败
        with patch.object(plugin.context.logger, 'error') as mock_error:
            result = await plugin.activate()
            assert result == False
            assert plugin.status == PluginStatus.ERROR
            mock_error.assert_called_once()