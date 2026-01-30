"""
测试示例插件模块

包含对示例插件的单元测试和集成测试。
"""

# 导入所有测试模块
from .test_plugins import (
    TestTelegramChannelPlugin,
    TestDiscordChannelPlugin,
    TestExampleSkillPlugin,
    TestPluginIntegration
)

__all__ = [
    'TestTelegramChannelPlugin',
    'TestDiscordChannelPlugin', 
    'TestExampleSkillPlugin',
    'TestPluginIntegration'
]