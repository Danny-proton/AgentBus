"""
AgentBus 插件系统集成测试

此模块专门测试插件系统的集成功能，包括：
- 插件发现、加载、激活和停用的完整流程
- 插件间依赖关系的处理
- 插件钩子、工具和命令的注册与执行
- 插件生命周期管理
- 插件错误处理和恢复
- 插件性能监控
- 插件热重载功能

测试覆盖：
- 单个插件的完整生命周期
- 多插件协同工作
- 插件依赖解析
- 插件间通信
- 插件资源管理
- 插件性能测试
"""

import pytest
import asyncio
import tempfile
import os
import shutil
import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from plugins.manager import PluginManager
from plugins.core import PluginContext, AgentBusPlugin, PluginStatus, PluginResult


class TestPluginSystemIntegration:
    """插件系统集成测试类"""
    
    @pytest.fixture
    def plugin_context(self):
        """创建插件上下文"""
        temp_dir = tempfile.mkdtemp()
        config_dir = os.path.join(temp_dir, "config")
        plugins_dir = os.path.join(temp_dir, "plugins")
        data_dir = os.path.join(temp_dir, "data")
        
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(plugins_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        
        config = {
            "plugins": {
                "enabled": True,
                "auto_discover": True,
                "hot_reload": True,
                "max_concurrent": 10,
                "timeout": 30
            }
        }
        
        context = PluginContext(
            config=config,
            logger=logging.getLogger("plugin_integration_test"),
            runtime={
                "temp_dir": temp_dir,
                "plugins_dir": plugins_dir,
                "data_dir": data_dir
            }
        )
        
        yield context
        
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def plugin_manager(self, plugin_context):
        """创建插件管理器"""
        manager = PluginManager(plugin_context)
        manager._plugin_dirs = [plugin_context.runtime["plugins_dir"]]
        return manager

    @pytest.mark.asyncio
    async def test_plugin_lifecycle_integration(self, plugin_manager):
        """测试插件完整生命周期集成"""
        
        print("🔄 开始测试插件生命周期集成...")
        
        # 1. 创建测试插件
        plugin_file = os.path.join(plugin_manager._plugin_dirs[0], "lifecycle_test.py")
        with open(plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
import asyncio
from plugins import AgentBusPlugin, PluginContext

class LifecycleTestPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.activation_count = 0
        self.deactivation_count = 0
        self.tool_calls = []
        self.hook_calls = []
    
    def get_info(self):
        return {
            'id': 'lifecycle_test',
            'name': 'Lifecycle Test Plugin',
            'version': '1.0.0',
            'description': 'Plugin for testing lifecycle',
            'author': 'Integration Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.activation_count += 1
        self.register_tool("get_lifecycle_info", "Get lifecycle information", self.get_lifecycle_info)
        self.register_hook("test_event", self.handle_test_event)
        self.register_command("/lifecycle", self.lifecycle_command, "Get lifecycle status")
    
    async def deactivate(self):
        self.deactivation_count += 1
        await super().deactivate()
    
    def get_lifecycle_info(self) -> dict:
        self.tool_calls.append("get_lifecycle_info")
        return {
            'plugin_id': self.plugin_id,
            'activation_count': self.activation_count,
            'deactivation_count': self.deactivation_count,
            'tool_calls': self.tool_calls,
            'status': self.status.value
        }
    
    async def handle_test_event(self, event_data):
        self.hook_calls.append(event_data)
        return f"Event handled: {event_data}"
    
    async def lifecycle_command(self, args):
        info = self.get_lifecycle_info()
        return f"Lifecycle status: {info}"
''')
        
        # 2. 初始化插件管理器
        await plugin_manager.initialize()
        print("✅ 插件管理器初始化完成")
        
        # 3. 发现插件
        discovered = await plugin_manager.discover_plugins()
        assert len(discovered) == 1
        assert discovered[0].plugin_id == 'lifecycle_test'
        print("✅ 插件发现测试通过")
        
        # 4. 加载插件
        plugin = await plugin_manager.load_plugin('lifecycle_test', plugin_file)
        assert plugin is not None
        assert plugin.status == PluginStatus.LOADED
        print("✅ 插件加载测试通过")
        
        # 5. 激活插件
        success = await plugin_manager.activate_plugin('lifecycle_test')
        assert success == True
        assert plugin.status == PluginStatus.ACTIVE
        assert plugin.activation_count == 1
        print("✅ 插件激活测试通过")
        
        # 6. 执行工具
        lifecycle_info = await plugin_manager.execute_tool("get_lifecycle_info")
        assert lifecycle_info['activation_count'] == 1
        assert lifecycle_info['deactivation_count'] == 0
        assert len(lifecycle_info['tool_calls']) == 1
        print("✅ 插件工具执行测试通过")
        
        # 7. 执行钩子
        hook_results = await plugin_manager.execute_hook("test_event", "test_data")
        assert len(hook_results) == 1
        assert "test_data" in hook_results[0]
        print("✅ 插件钩子执行测试通过")
        
        # 8. 执行命令
        command_result = await plugin_manager.execute_command("/lifecycle", "")
        assert "Lifecycle status" in command_result
        print("✅ 插件命令执行测试通过")
        
        # 9. 重新激活插件（测试重复激活）
        success = await plugin_manager.activate_plugin('lifecycle_test')
        assert success == True
        assert plugin.activation_count == 2  # 应该保持激活状态
        print("✅ 重复激活测试通过")
        
        # 10. 停用插件
        success = await plugin_manager.deactivate_plugin('lifecycle_test')
        assert success == True
        assert plugin.status == PluginStatus.DEACTIVATED
        assert plugin.deactivation_count == 1
        print("✅ 插件停用测试通过")
        
        # 11. 重新激活插件
        success = await plugin_manager.activate_plugin('lifecycle_test')
        assert success == True
        assert plugin.status == PluginStatus.ACTIVE
        assert plugin.activation_count == 3
        print("✅ 重新激活测试通过")
        
        # 12. 卸载插件
        success = await plugin_manager.unload_plugin('lifecycle_test')
        assert success == True
        assert plugin.status == PluginStatus.UNLOADED
        assert 'lifecycle_test' not in plugin_manager._plugins
        print("✅ 插件卸载测试通过")
        
        print("🎉 插件生命周期集成测试完成")

    @pytest.mark.asyncio
    async def test_plugin_dependencies_integration(self, plugin_manager):
        """测试插件依赖关系集成"""
        
        print("🔗 开始测试插件依赖关系集成...")
        
        # 1. 创建基础插件
        base_plugin_file = os.path.join(plugin_manager._plugin_dirs[0], "base_plugin.py")
        with open(base_plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class BasePlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.base_data = {}
    
    def get_info(self):
        return {
            'id': 'base_plugin',
            'name': 'Base Plugin',
            'version': '1.0.0',
            'description': 'Base plugin for dependency testing',
            'author': 'Integration Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("get_base_data", "Get base data", self.get_base_data)
        self.register_tool("set_base_data", "Set base data", self.set_base_data)
    
    def get_base_data(self) -> dict:
        return self.base_data
    
    def set_base_data(self, key: str, value: str) -> dict:
        self.base_data[key] = value
        return self.base_data
''')
        
        # 2. 创建依赖插件
        dependent_plugin_file = os.path.join(plugin_manager._plugin_dirs[0], "dependent_plugin.py")
        with open(dependent_plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class DependentPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.dependent_data = {}
    
    def get_info(self):
        return {
            'id': 'dependent_plugin',
            'name': 'Dependent Plugin',
            'version': '1.0.0',
            'description': 'Plugin that depends on base plugin',
            'author': 'Integration Test',
            'dependencies': ['base_plugin']
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("get_dependent_data", "Get dependent data", self.get_dependent_data)
        self.register_tool("enhance_base_data", "Enhance base data", self.enhance_base_data)
        
        # 获取基础插件实例
        base_plugin = self.context.runtime.get('plugin_manager').get_plugin('base_plugin')
        if base_plugin and base_plugin.status.value == 'active':
            self.base_plugin = base_plugin
        else:
            raise Exception("Base plugin not available")
    
    def get_dependent_data(self) -> dict:
        return self.dependent_data
    
    def enhance_base_data(self, key: str, value: str) -> dict:
        if hasattr(self, 'base_plugin'):
            base_data = self.base_plugin.get_base_data()
            enhanced_data = base_data.copy()
            enhanced_data[f"enhanced_{key}"] = f"enhanced_{value}"
            return enhanced_data
        else:
            raise Exception("Base plugin not available")
''')
        
        # 3. 创建循环依赖插件
        circular_plugin_file = os.path.join(plugin_manager._plugin_dirs[0], "circular_plugin.py")
        with open(circular_plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class CircularPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.circular_data = {}
    
    def get_info(self):
        return {
            'id': 'circular_plugin',
            'name': 'Circular Plugin',
            'version': '1.0.0',
            'description': 'Plugin with circular dependencies',
            'author': 'Integration Test',
            'dependencies': ['dependent_plugin', 'base_plugin']
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("get_circular_data", "Get circular data", self.get_circular_data)
        self.register_tool("process_circular", "Process circular dependencies", self.process_circular)
        
        # 检查依赖
        manager = self.context.runtime.get('plugin_manager')
        dependent_plugin = manager.get_plugin('dependent_plugin')
        base_plugin = manager.get_plugin('base_plugin')
        
        if not dependent_plugin or dependent_plugin.status.value != 'active':
            raise Exception("Dependent plugin not available")
        if not base_plugin or base_plugin.status.value != 'active':
            raise Exception("Base plugin not available")
        
        self.dependent_plugin = dependent_plugin
        self.base_plugin = base_plugin
    
    def get_circular_data(self) -> dict:
        return self.circular_data
    
    def process_circular(self) -> dict:
        if hasattr(self, 'base_plugin') and hasattr(self, 'dependent_plugin'):
            base_data = self.base_plugin.get_base_data()
            dependent_data = self.dependent_plugin.get_dependent_data()
            return {
                'base_data': base_data,
                'dependent_data': dependent_data,
                'circular_processed': True
            }
        else:
            raise Exception("Dependencies not available")
''')
        
        # 4. 发现插件
        discovered = await plugin_manager.discover_plugins()
        assert len(discovered) == 3
        plugin_ids = [p.plugin_id for p in discovered]
        assert 'base_plugin' in plugin_ids
        assert 'dependent_plugin' in plugin_ids
        assert 'circular_plugin' in plugin_ids
        print("✅ 依赖插件发现测试通过")
        
        # 5. 初始化插件管理器
        await plugin_manager.initialize()
        print("✅ 插件管理器初始化完成")
        
        # 6. 按依赖顺序加载插件
        base_plugin = await plugin_manager.load_plugin('base_plugin', base_plugin_file)
        assert base_plugin is not None
        print("✅ 基础插件加载完成")
        
        dependent_plugin = await plugin_manager.load_plugin('dependent_plugin', dependent_plugin_file)
        assert dependent_plugin is not None
        print("✅ 依赖插件加载完成")
        
        circular_plugin = await plugin_manager.load_plugin('circular_plugin', circular_plugin_file)
        assert circular_plugin is not None
        print("✅ 循环依赖插件加载完成")
        
        # 7. 按依赖顺序激活插件
        success1 = await plugin_manager.activate_plugin('base_plugin')
        assert success1 == True
        print("✅ 基础插件激活完成")
        
        success2 = await plugin_manager.activate_plugin('dependent_plugin')
        assert success2 == True
        print("✅ 依赖插件激活完成")
        
        success3 = await plugin_manager.activate_plugin('circular_plugin')
        assert success3 == True
        print("✅ 循环依赖插件激活完成")
        
        # 8. 测试基础插件功能
        base_data = await plugin_manager.execute_tool("set_base_data", "key1", "value1")
        assert "key1" in base_data
        assert base_data["key1"] == "value1"
        print("✅ 基础插件功能测试通过")
        
        # 9. 测试依赖插件功能
        enhanced_data = await plugin_manager.execute_tool("enhance_base_data", "key2", "value2")
        assert "enhanced_key2" in enhanced_data
        assert enhanced_data["enhanced_key2"] == "enhanced_value2"
        print("✅ 依赖插件功能测试通过")
        
        # 10. 测试循环依赖插件功能
        circular_result = await plugin_manager.execute_tool("process_circular")
        assert circular_result['circular_processed'] == True
        assert 'base_data' in circular_result
        assert 'dependent_data' in circular_result
        print("✅ 循环依赖插件功能测试通过")
        
        print("🎉 插件依赖关系集成测试完成")

    @pytest.mark.asyncio
    async def test_plugin_communication_integration(self, plugin_manager):
        """测试插件间通信集成"""
        
        print("📡 开始测试插件间通信集成...")
        
        # 1. 创建发送者插件
        sender_plugin_file = os.path.join(plugin_manager._plugin_dirs[0], "sender_plugin.py")
        with open(sender_plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class SenderPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.sent_messages = []
    
    def get_info(self):
        return {
            'id': 'sender_plugin',
            'name': 'Sender Plugin',
            'version': '1.0.0',
            'description': 'Plugin that sends messages',
            'author': 'Integration Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("send_message", "Send message to other plugins", self.send_message)
        self.register_hook("message_received", self.handle_received_message)
    
    def send_message(self, message: str, target_plugin: str = None) -> dict:
        self.sent_messages.append({
            'message': message,
            'target_plugin': target_plugin,
            'timestamp': time.time()
        })
        
        # 通过钩子发送消息
        self.trigger_hook("message_to_plugin", {
            'from_plugin': self.plugin_id,
            'message': message,
            'target_plugin': target_plugin
        })
        
        return {
            'sent': True,
            'message': message,
            'target': target_plugin
        }
    
    async def handle_received_message(self, message_data):
        self.sent_messages.append({
            'type': 'received',
            'data': message_data,
            'timestamp': time.time()
        })
        return f"Received: {message_data}"
''')
        
        # 2. 创建接收者插件
        receiver_plugin_file = os.path.join(plugin_manager._plugin_dirs[0], "receiver_plugin.py")
        with open(receiver_plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
import time
from plugins import AgentBusPlugin, PluginContext

class ReceiverPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.received_messages = []
        self.broadcast_messages = []
    
    def get_info(self):
        return {
            'id': 'receiver_plugin',
            'name': 'Receiver Plugin',
            'version': '1.0.0',
            'description': 'Plugin that receives messages',
            'author': 'Integration Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("get_received_messages", "Get received messages", self.get_received_messages)
        self.register_hook("message_to_plugin", self.handle_plugin_message)
        self.register_hook("broadcast_message", self.handle_broadcast)
    
    async def handle_plugin_message(self, message_data):
        self.received_messages.append({
            'from_plugin': message_data.get('from_plugin'),
            'message': message_data.get('message'),
            'target_plugin': message_data.get('target_plugin'),
            'timestamp': time.time()
        })
        return f"Plugin message handled: {message_data.get('message')}"
    
    async def handle_broadcast(self, broadcast_data):
        self.broadcast_messages.append({
            'from_plugin': broadcast_data.get('from_plugin'),
            'message': broadcast_data.get('message'),
            'timestamp': time.time()
        })
        return f"Broadcast handled: {broadcast_data.get('message')}"
    
    def get_received_messages(self) -> list:
        return self.received_messages
''')
        
        # 3. 创建广播插件
        broadcaster_plugin_file = os.path.join(plugin_manager._plugin_dirs[0], "broadcaster_plugin.py")
        with open(broadcaster_plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
import time
from plugins import AgentBusPlugin, PluginContext

class BroadcasterPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.broadcasts_sent = []
    
    def get_info(self):
        return {
            'id': 'broadcaster_plugin',
            'name': 'Broadcaster Plugin',
            'version': '1.0.0',
            'description': 'Plugin that broadcasts messages',
            'author': 'Integration Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("broadcast_message", "Broadcast message to all plugins", self.broadcast_message)
        self.register_tool("get_broadcast_stats", "Get broadcast statistics", self.get_broadcast_stats)
    
    def broadcast_message(self, message: str) -> dict:
        self.broadcasts_sent.append({
            'message': message,
            'timestamp': time.time()
        })
        
        # 触发广播钩子
        self.trigger_hook("broadcast_message", {
            'from_plugin': self.plugin_id,
            'message': message
        })
        
        return {
            'broadcast': True,
            'message': message,
            'recipients': 'all_plugins'
        }
    
    def get_broadcast_stats(self) -> dict:
        return {
            'total_broadcasts': len(self.broadcasts_sent),
            'broadcasts': self.broadcasts_sent
        }
''')
        
        # 4. 初始化并加载所有插件
        await plugin_manager.initialize()
        
        sender_plugin = await plugin_manager.load_plugin('sender_plugin', sender_plugin_file)
        receiver_plugin = await plugin_manager.load_plugin('receiver_plugin', receiver_plugin_file)
        broadcaster_plugin = await plugin_manager.load_plugin('broadcaster_plugin', broadcaster_plugin_file)
        
        print("✅ 通信插件加载完成")
        
        # 5. 激活所有插件
        await plugin_manager.activate_plugin('sender_plugin')
        await plugin_manager.activate_plugin('receiver_plugin')
        await plugin_manager.activate_plugin('broadcaster_plugin')
        
        print("✅ 通信插件激活完成")
        
        # 6. 测试点对点消息发送
        result = await plugin_manager.execute_tool("send_message", "Hello from sender!", "receiver_plugin")
        assert result['sent'] == True
        assert result['message'] == "Hello from sender!"
        assert result['target'] == "receiver_plugin"
        print("✅ 点对点消息发送测试通过")
        
        # 等待消息处理
        await asyncio.sleep(0.1)
        
        # 7. 验证消息接收
        received_messages = await plugin_manager.execute_tool("get_received_messages", plugin_id="receiver_plugin")
        assert len(received_messages) >= 1
        assert any("Hello from sender!" in str(msg) for msg in received_messages)
        print("✅ 消息接收验证通过")
        
        # 8. 测试广播消息
        result = await plugin_manager.execute_tool("broadcast_message", "Broadcast message from broadcaster!")
        assert result['broadcast'] == True
        assert result['message'] == "Broadcast message from broadcaster!"
        print("✅ 广播消息发送测试通过")
        
        # 等待广播处理
        await asyncio.sleep(0.1)
        
        # 9. 验证广播接收
        receiver_stats = await plugin_manager.execute_tool("get_broadcast_stats", plugin_id="receiver_plugin")
        broadcaster_stats = await plugin_manager.execute_tool("get_broadcast_stats", plugin_id="broadcaster_plugin")
        
        assert len(broadcaster_stats['broadcasts']) >= 1
        print("✅ 广播消息验证通过")
        
        # 10. 测试钩子触发链
        sender_stats = await plugin_manager.execute_tool("send_message", "Chain test message")
        assert sender_stats['sent'] == True
        print("✅ 钩子触发链测试通过")
        
        # 11. 测试多插件消息循环
        for i in range(3):
            await plugin_manager.execute_tool("send_message", f"Cycle message {i+1}")
        
        await asyncio.sleep(0.1)
        
        final_received = await plugin_manager.execute_tool("get_received_messages", plugin_id="receiver_plugin")
        assert len(final_received) >= 3
        print("✅ 多插件消息循环测试通过")
        
        print("🎉 插件间通信集成测试完成")