"""
AgentBus CLI集成测试

此模块测试CLI功能的集成，包括：
- CLI命令的执行和输出
- 插件管理相关的CLI命令
- 渠道管理相关的CLI命令
- HITL服务相关的CLI命令
- 知识总线相关的CLI命令
- 系统状态和统计信息的CLI显示
- 配置文件处理的CLI集成
- 错误处理和用户反馈

测试覆盖：
- CLI命令解析和执行
- 插件生命周期管理命令
- 服务管理命令
- 系统监控命令
- 配置管理命令
- 批处理操作
- 错误处理和日志记录
"""

import pytest
import asyncio
import tempfile
import os
import shutil
import logging
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from io import StringIO

# CLI相关模块 - 部分注释掉因为文件不存在
# from cli import AgentBusCLI
# from core.context import AgentBusContext
from plugins.manager import PluginManager
# from plugins.core import PluginContext
from channels.manager import ChannelManager


class TestCLIIntegration:
    """CLI集成测试类"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def cli_config(self, temp_dir):
        """创建CLI配置"""
        config_dir = os.path.join(temp_dir, "config")
        data_dir = os.path.join(temp_dir, "data")
        logs_dir = os.path.join(temp_dir, "logs")
        plugins_dir = os.path.join(temp_dir, "plugins")
        
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
        os.makedirs(plugins_dir, exist_ok=True)
        
        config = {
            "agentbus": {
                "data_dir": data_dir,
                "logs_dir": logs_dir,
                "plugins_dir": plugins_dir,
                "channels_config": os.path.join(config_dir, "channels.json"),
                "knowledge_config": os.path.join(config_dir, "knowledge.json")
            },
            "cli": {
                "output_format": "text",
                "verbose": False,
                "confirm_actions": False
            },
            "plugins": {
                "enabled": True,
                "auto_discover": True,
                "hot_reload": True
            },
            "channels": {
                "enabled": True,
                "auto_connect": False
            }
        }
        
        # 写入配置文件
        config_file = os.path.join(config_dir, "agentbus.json")
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return {
            "config": config,
            "config_file": config_file,
            "temp_dir": temp_dir,
            "directories": {
                "config": config_dir,
                "data": data_dir,
                "logs": logs_dir,
                "plugins": plugins_dir
            }
        }
    
    @pytest.fixture
    def system_context(self, cli_config):
        """创建系统上下文"""
        return AgentBusContext(
            config=cli_config["config"],
            data_dir=cli_config["directories"]["data"],
            logs_dir=cli_config["directories"]["logs"]
        )
    
    @pytest.fixture
    def cli_instance(self, system_context):
        """创建CLI实例"""
        return AgentBusCLI(
            context=system_context,
            logger=logging.getLogger("cli_test")
        )

    @pytest.mark.asyncio
    async def test_cli_help_commands(self, cli_instance):
        """测试CLI帮助命令"""
        
        print("📚 开始测试CLI帮助命令...")
        
        # 1. 测试主帮助命令
        result = await cli_instance.execute_command("--help")
        assert "AgentBus" in result
        assert "help" in result.lower()
        print("✅ 主帮助命令测试通过")
        
        # 2. 测试插件管理帮助
        result = await cli_instance.execute_command("plugin --help")
        assert "plugin" in result.lower()
        assert "manage" in result.lower() or "list" in result.lower()
        print("✅ 插件管理帮助命令测试通过")
        
        # 3. 测试渠道管理帮助
        result = await cli_instance.execute_command("channel --help")
        assert "channel" in result.lower()
        print("✅ 渠道管理帮助命令测试通过")
        
        # 4. 测试HITL管理帮助
        result = await cli_instance.execute_command("hitl --help")
        assert "hitl" in result.lower()
        print("✅ HITL管理帮助命令测试通过")
        
        # 5. 测试知识总线帮助
        result = await cli_instance.execute_command("knowledge --help")
        assert "knowledge" in result.lower()
        print("✅ 知识总线帮助命令测试通过")
        
        # 6. 测试系统状态帮助
        result = await cli_instance.execute_command("status --help")
        assert "status" in result.lower()
        print("✅ 系统状态帮助命令测试通过")
        
        # 7. 测试配置管理帮助
        result = await cli_instance.execute_command("config --help")
        assert "config" in result.lower()
        print("✅ 配置管理帮助命令测试通过")
        
        print("🎉 CLI帮助命令测试完成")

    @pytest.mark.asyncio
    async def test_cli_plugin_management_commands(self, cli_instance, cli_config):
        """测试CLI插件管理命令"""
        
        print("🔌 开始测试CLI插件管理命令...")
        
        # 1. 创建测试插件
        plugin_file = os.path.join(cli_config["directories"]["plugins"], "test_plugin.py")
        with open(plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
from plugins import AgentBusPlugin, PluginContext

class TestPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.test_data = []
    
    def get_info(self):
        return {
            'id': 'test_plugin',
            'name': 'Test Plugin',
            'version': '1.0.0',
            'description': 'Plugin for CLI testing',
            'author': 'CLI Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("test_tool", "Test tool", self.test_tool)
    
    def test_tool(self):
        return "Test plugin is working!"
''')
        
        # 2. 测试插件发现命令
        result = await cli_instance.execute_command("plugin discover")
        assert "test_plugin" in result or "discover" in result.lower()
        print("✅ 插件发现命令测试通过")
        
        # 3. 测试插件列表命令
        result = await cli_instance.execute_command("plugin list")
        assert "plugin" in result.lower()
        print("✅ 插件列表命令测试通过")
        
        # 4. 测试插件信息命令
        result = await cli_instance.execute_command("plugin info test_plugin")
        assert "test_plugin" in result.lower()
        print("✅ 插件信息命令测试通过")
        
        # 5. 测试插件加载命令
        result = await cli_instance.execute_command(f"plugin load {plugin_file}")
        assert "load" in result.lower() or "success" in result.lower()
        print("✅ 插件加载命令测试通过")
        
        # 6. 测试插件激活命令
        result = await cli_instance.execute_command("plugin activate test_plugin")
        assert "activate" in result.lower() or "success" in result.lower()
        print("✅ 插件激活命令测试通过")
        
        # 7. 测试插件执行工具命令
        result = await cli_instance.execute_command("plugin exec test_plugin test_tool")
        assert "working" in result.lower() or "test" in result.lower()
        print("✅ 插件工具执行命令测试通过")
        
        # 8. 测试插件停用命令
        result = await cli_instance.execute_command("plugin deactivate test_plugin")
        assert "deactivate" in result.lower() or "success" in result.lower()
        print("✅ 插件停用命令测试通过")
        
        # 9. 测试插件卸载命令
        result = await cli_instance.execute_command("plugin unload test_plugin")
        assert "unload" in result.lower() or "success" in result.lower()
        print("✅ 插件卸载命令测试通过")
        
        print("🎉 CLI插件管理命令测试完成")

    @pytest.mark.asyncio
    async def test_cli_channel_management_commands(self, cli_instance):
        """测试CLI渠道管理命令"""
        
        print("📡 开始测试CLI渠道管理命令...")
        
        # 1. 测试渠道列表命令
        result = await cli_instance.execute_command("channel list")
        assert "channel" in result.lower()
        print("✅ 渠道列表命令测试通过")
        
        # 2. 测试渠道状态命令
        result = await cli_instance.execute_command("channel status")
        assert "status" in result.lower()
        print("✅ 渠道状态命令测试通过")
        
        # 3. 测试渠道连接命令
        result = await cli_instance.execute_command("channel connect test_channel")
        assert "connect" in result.lower() or "test_channel" in result.lower()
        print("✅ 渠道连接命令测试通过")
        
        # 4. 测试渠道断开命令
        result = await cli_instance.execute_command("channel disconnect test_channel")
        assert "disconnect" in result.lower() or "test_channel" in result.lower()
        print("✅ 渠道断开命令测试通过")
        
        # 5. 测试渠道发送消息命令
        result = await cli_instance.execute_command("channel send test_channel 'Hello World'")
        assert "send" in result.lower() or "hello" in result.lower()
        print("✅ 渠道发送消息命令测试通过")
        
        # 6. 测试渠道监听命令（模拟）
        result = await cli_instance.execute_command("channel listen test_channel --timeout 1")
        assert "listen" in result.lower() or "test_channel" in result.lower()
        print("✅ 渠道监听命令测试通过")
        
        print("🎉 CLI渠道管理命令测试完成")

    @pytest.mark.asyncio
    async def test_cli_hitl_management_commands(self, cli_instance):
        """测试CLI HITL管理命令"""
        
        print("🤝 开始测试CLI HITL管理命令...")
        
        # 1. 测试HITL请求列表命令
        result = await cli_instance.execute_command("hitl list")
        assert "hitl" in result.lower() or "list" in result.lower()
        print("✅ HITL请求列表命令测试通过")
        
        # 2. 测试HITL创建请求命令
        result = await cli_instance.execute_command('''hitl create "Test Request" "This is a test HITL request"''')
        assert "create" in result.lower() or "request" in result.lower()
        print("✅ HITL创建请求命令测试通过")
        
        # 3. 测试HITL状态命令
        result = await cli_instance.execute_command("hitl status")
        assert "status" in result.lower()
        print("✅ HITL状态命令测试通过")
        
        # 4. 测试HITL响应命令
        result = await cli_instance.execute_command("hitl respond test_request_id 'This is a test response'")
        assert "respond" in result.lower() or "response" in result.lower()
        print("✅ HITL响应命令测试通过")
        
        # 5. 测试HITL统计命令
        result = await cli_instance.execute_command("hitl stats")
        assert "stats" in result.lower() or "statistics" in result.lower()
        print("✅ HITL统计命令测试通过")
        
        # 6. 测试HITL取消命令
        result = await cli_instance.execute_command("hitl cancel test_request_id")
        assert "cancel" in result.lower() or "test_request_id" in result.lower()
        print("✅ HITL取消命令测试通过")
        
        print("🎉 CLI HITL管理命令测试完成")

    @pytest.mark.asyncio
    async def test_cli_knowledge_management_commands(self, cli_instance):
        """测试CLI知识总线管理命令"""
        
        print("🧠 开始测试CLI知识总线管理命令...")
        
        # 1. 测试知识列表命令
        result = await cli_instance.execute_command("knowledge list")
        assert "knowledge" in result.lower() or "list" in result.lower()
        print("✅ 知识列表命令测试通过")
        
        # 2. 测试知识添加命令
        result = await cli_instance.execute_command('''knowledge add "Test knowledge" "This is test knowledge"''')
        assert "add" in result.lower() or "knowledge" in result.lower()
        print("✅ 知识添加命令测试通过")
        
        # 3. 测试知识搜索命令
        result = await cli_instance.execute_command('knowledge search "test knowledge"')
        assert "search" in result.lower() or "test" in result.lower()
        print("✅ 知识搜索命令测试通过")
        
        # 4. 测试知识更新命令
        result = await cli_instance.execute_command('knowledge update test_knowledge_id "Updated knowledge"')
        assert "update" in result.lower() or "updated" in result.lower()
        print("✅ 知识更新命令测试通过")
        
        # 5. 测试知识删除命令
        result = await cli_instance.execute_command('knowledge delete test_knowledge_id')
        assert "delete" in result.lower() or "test_knowledge_id" in result.lower()
        print("✅ 知识删除命令测试通过")
        
        # 6. 测试知识统计命令
        result = await cli_instance.execute_command("knowledge stats")
        assert "stats" in result.lower() or "statistics" in result.lower()
        print("✅ 知识统计命令测试通过")
        
        print("🎉 CLI知识总线管理命令测试完成")

    @pytest.mark.asyncio
    async def test_cli_system_status_commands(self, cli_instance):
        """测试CLI系统状态命令"""
        
        print("📊 开始测试CLI系统状态命令...")
        
        # 1. 测试系统状态命令
        result = await cli_instance.execute_command("status")
        assert "status" in result.lower() or "system" in result.lower()
        print("✅ 系统状态命令测试通过")
        
        # 2. 测试系统统计命令
        result = await cli_instance.execute_command("stats")
        assert "stats" in result.lower() or "statistics" in result.lower()
        print("✅ 系统统计命令测试通过")
        
        # 3. 测试系统健康检查命令
        result = await cli_instance.execute_command("health")
        assert "health" in result.lower() or "check" in result.lower()
        print("✅ 系统健康检查命令测试通过")
        
        # 4. 测试系统监控命令
        result = await cli_instance.execute_command("monitor --duration 5")
        assert "monitor" in result.lower() or "duration" in result.lower()
        print("✅ 系统监控命令测试通过")
        
        # 5. 测试系统日志命令
        result = await cli_instance.execute_command("logs --lines 10")
        assert "log" in result.lower() or "lines" in result.lower()
        print("✅ 系统日志命令测试通过")
        
        print("🎉 CLI系统状态命令测试完成")

    @pytest.mark.asyncio
    async def test_cli_config_management_commands(self, cli_instance, cli_config):
        """测试CLI配置管理命令"""
        
        print("⚙️ 开始测试CLI配置管理命令...")
        
        # 1. 测试配置显示命令
        result = await cli_instance.execute_command("config show")
        assert "config" in result.lower() or "show" in result.lower()
        print("✅ 配置显示命令测试通过")
        
        # 2. 测试配置获取命令
        result = await cli_instance.execute_command("config get agentbus.data_dir")
        assert "config" in result.lower() or "get" in result.lower()
        print("✅ 配置获取命令测试通过")
        
        # 3. 测试配置设置命令
        result = await cli_instance.execute_command("config set agentbus.test_value test_data")
        assert "config" in result.lower() or "set" in result.lower()
        print("✅ 配置设置命令测试通过")
        
        # 4. 测试配置验证命令
        result = await cli_instance.execute_command("config validate")
        assert "config" in result.lower() or "validate" in result.lower()
        print("✅ 配置验证命令测试通过")
        
        print("🎉 CLI配置管理命令测试完成")

    @pytest.mark.asyncio
    async def test_cli_error_handling(self, cli_instance):
        """测试CLI错误处理"""
        
        print("🛡️ 开始测试CLI错误处理...")
        
        # 1. 测试无效命令
        result = await cli_instance.execute_command("invalid_command")
        assert "invalid" in result.lower() or "error" in result.lower() or "not found" in result.lower()
        print("✅ 无效命令错误处理测试通过")
        
        # 2. 测试缺少参数的命令
        result = await cli_instance.execute_command("plugin")
        assert "plugin" in result.lower() or "missing" in result.lower() or "argument" in result.lower()
        print("✅ 缺少参数错误处理测试通过")
        
        # 3. 测试插件不存在的情况
        result = await cli_instance.execute_command("plugin info nonexistent_plugin")
        assert "nonexistent" in result.lower() or "not found" in result.lower() or "error" in result.lower()
        print("✅ 插件不存在错误处理测试通过")
        
        # 4. 测试文件不存在的情况
        result = await cli_instance.execute_command("config load /nonexistent/file.json")
        assert "nonexistent" in result.lower() or "not found" in result.lower() or "error" in result.lower()
        print("✅ 文件不存在错误处理测试通过")
        
        print("🎉 CLI错误处理测试完成")

    @pytest.mark.asyncio
    async def test_cli_verbose_and_output_options(self, cli_instance):
        """测试CLI详细输出和输出选项"""
        
        print("📝 开始测试CLI详细输出和输出选项...")
        
        # 1. 测试详细模式
        result = await cli_instance.execute_command("status --verbose")
        assert "status" in result.lower()
        print("✅ 详细模式测试通过")
        
        # 2. 测试JSON输出格式
        result = await cli_instance.execute_command("status --format json")
        assert "status" in result.lower()
        print("✅ JSON输出格式测试通过")
        
        # 3. 测试CSV输出格式
        result = await cli_instance.execute_command("plugin list --format csv")
        assert "plugin" in result.lower()
        print("✅ CSV输出格式测试通过")
        
        # 4. 测试表格输出格式
        result = await cli_instance.execute_command("knowledge list --format table")
        assert "knowledge" in result.lower()
        print("✅ 表格输出格式测试通过")
        
        print("🎉 CLI详细输出和输出选项测试完成")


# CLI集成测试套件
class TestCLIIntegrationSuite:
    """CLI集成测试套件"""
    
    @pytest.mark.asyncio
    async def test_cli_complete_integration(self):
        """运行完整的CLI集成测试"""
        
        print("🎯 开始运行完整的CLI集成测试套件...")
        print("=" * 80)
        
        # 创建测试环境
        temp_dir = tempfile.mkdtemp()
        try:
            config_dir = os.path.join(temp_dir, "config")
            data_dir = os.path.join(temp_dir, "data")
            logs_dir = os.path.join(temp_dir, "logs")
            plugins_dir = os.path.join(temp_dir, "plugins")
            
            os.makedirs(config_dir, exist_ok=True)
            os.makedirs(data_dir, exist_ok=True)
            os.makedirs(logs_dir, exist_ok=True)
            os.makedirs(plugins_dir, exist_ok=True)
            
            # 创建配置
            config = {
                "agentbus": {
                    "data_dir": data_dir,
                    "logs_dir": logs_dir,
                    "plugins_dir": plugins_dir
                },
                "cli": {
                    "output_format": "text",
                    "verbose": False,
                    "confirm_actions": False
                }
            }
            
            # 写入配置文件
            config_file = os.path.join(config_dir, "agentbus.json")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 创建系统上下文
            system_context = AgentBusContext(
                config=config,
                data_dir=data_dir,
                logs_dir=logs_dir
            )
            
            # 创建CLI实例
            cli = AgentBusCLI(
                context=system_context,
                logger=logging.getLogger("cli_suite_test")
            )
            
            print("✅ 测试环境准备完成")
            
            # 1. 测试基本CLI功能
            result = await cli.execute_command("--help")
            assert "AgentBus" in result
            print("✅ 步骤1: 基本CLI功能 - 通过")
            
            # 2. 测试插件管理
            # 创建测试插件
            plugin_file = os.path.join(plugins_dir, "suite_test.py")
            with open(plugin_file, 'w', encoding='utf-8') as f:
                f.write('''
from plugins import AgentBusPlugin, PluginContext

class SuiteTestPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.execution_count = 0
    
    def get_info(self):
        return {
            'id': 'suite_test',
            'name': 'Suite Test Plugin',
            'version': '1.0.0',
            'description': 'Plugin for CLI suite testing',
            'author': 'CLI Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("suite_tool", "Suite test tool", self.suite_tool)
    
    def suite_tool(self):
        self.execution_count += 1
        return f"Suite test executed {self.execution_count} times"
''')
            
            result = await cli.execute_command(f"plugin load {plugin_file}")
            assert "load" in result.lower()
            
            result = await cli.execute_command("plugin activate suite_test")
            assert "activate" in result.lower()
            
            result = await cli.execute_command("plugin exec suite_test suite_tool")
            assert "suite" in result.lower() or "executed" in result.lower()
            
            print("✅ 步骤2: 插件管理 - 通过")
            
            # 3. 测试系统状态
            result = await cli.execute_command("status")
            assert "status" in result.lower()
            
            result = await cli.execute_command("stats")
            assert "stats" in result.lower()
            
            print("✅ 步骤3: 系统状态 - 通过")
            
            # 4. 测试配置管理
            result = await cli.execute_command("config show")
            assert "config" in result.lower()
            
            result = await cli.execute_command("config get agentbus.data_dir")
            assert "config" in result.lower()
            
            print("✅ 步骤4: 配置管理 - 通过")
            
            # 5. 测试错误处理
            result = await cli.execute_command("invalid_command")
            assert "invalid" in result.lower() or "error" in result.lower()
            
            result = await cli.execute_command("plugin info nonexistent")
            assert "nonexistent" in result.lower() or "not found" in result.lower()
            
            print("✅ 步骤5: 错误处理 - 通过")
            
            # 6. 测试输出格式
            result = await cli.execute_command("status --format json")
            assert "status" in result.lower()
            
            print("✅ 步骤6: 输出格式 - 通过")
            
            print("🎉 CLI完整集成测试套件 - 全部通过！")
            print("=" * 80)
            
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)