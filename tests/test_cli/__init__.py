"""
CLI命令测试包
CLI Commands Test Package
"""

# 测试插件管理命令
from .test_plugin_commands import TestPluginCommands, TestPluginCommandsEdgeCases

# 测试渠道管理命令
from .test_channel_commands import TestChannelCommands, TestChannelCommandsEdgeCases

__all__ = [
    'TestPluginCommands',
    'TestPluginCommandsEdgeCases', 
    'TestChannelCommands',
    'TestChannelCommandsEdgeCases'
]