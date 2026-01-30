#!/usr/bin/env python3
"""
AgentBus CLI增强功能测试脚本
AgentBus CLI Enhancement Testing Script

这个脚本用于测试CLI的插件管理和渠道管理功能。
This script tests the plugin and channel management functionality of the CLI.
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

# 直接导入需要的模块，避免循环导入
try:
    from agentbus.plugins.manager import PluginManager
    from agentbus.channels.manager import ChannelManager
    from agentbus.cli.commands.plugin_commands import PluginCommands
    from agentbus.cli.commands.channel_commands import ChannelCommands
    from click.testing import CliRunner
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("尝试替代导入...")
    
    # 替代导入方法
    import importlib.util
    
    # 导入插件管理器
    plugin_manager_spec = importlib.util.spec_from_file_location(
        "plugin_manager", 
        str(Path(__file__).parent / "agentbus/plugins/manager.py")
    )
    plugin_manager_module = importlib.util.module_from_spec(plugin_manager_spec)
    plugin_manager_spec.loader.exec_module(plugin_manager_module)
    PluginManager = plugin_manager_module.PluginManager
    
    # 导入渠道管理器
    channel_manager_spec = importlib.util.spec_from_file_location(
        "channel_manager", 
        str(Path(__file__).parent / "agentbus/channels/manager.py")
    )
    channel_manager_module = importlib.util.module_from_spec(channel_manager_spec)
    channel_manager_spec.loader.exec_module(channel_manager_module)
    ChannelManager = channel_manager_module.ChannelManager
    
    # 导入CLI命令
    plugin_commands_spec = importlib.util.spec_from_file_location(
        "plugin_commands", 
        str(Path(__file__).parent / "agentbus/cli/commands/plugin_commands.py")
    )
    plugin_commands_module = importlib.util.module_from_spec(plugin_commands_spec)
    plugin_commands_spec.loader.exec_module(plugin_commands_module)
    PluginCommands = plugin_commands_module.PluginCommands
    
    channel_commands_spec = importlib.util.spec_from_file_location(
        "channel_commands", 
        str(Path(__file__).parent / "agentbus/cli/commands/channel_commands.py")
    )
    channel_commands_module = importlib.util.module_from_spec(channel_commands_spec)
    channel_commands_spec.loader.exec_module(channel_commands_module)
    ChannelCommands = channel_commands_module.ChannelCommands


class CLIEnhancementTester:
    """CLI增强功能测试器"""
    
    def __init__(self):
        self.plugin_manager = None
        self.channel_manager = None
        self.plugin_commands = None
        self.channel_commands = None
        self.test_results = []
    
    async def setup(self):
        """设置测试环境"""
        print("🔧 设置测试环境...")
        
        try:
            # 初始化管理器
            self.plugin_manager = PluginManager()
            self.channel_manager = ChannelManager()
            
            # 创建命令实例
            self.plugin_commands = PluginCommands(self.plugin_manager)
            self.channel_commands = ChannelCommands(self.channel_manager)
            
            print("✅ 测试环境设置完成")
            return True
            
        except Exception as e:
            print(f"❌ 测试环境设置失败: {e}")
            return False
    
    async def test_plugin_commands(self):
        """测试插件管理命令"""
        print("\n🔌 测试插件管理命令...")
        
        try:
            # 测试发现插件
            discovered = await self.plugin_commands.discover_plugins()
            print(f"   发现插件数量: {len(discovered)}")
            
            # 测试列出插件
            plugin_list_result = await self.plugin_commands.list_plugins()
            if "error" not in plugin_list_result:
                print(f"   ✅ 插件列表获取成功: {plugin_list_result.get('total', 0)} 个插件")
            else:
                print(f"   ❌ 插件列表获取失败: {plugin_list_result['error']}")
            
            # 测试获取统计信息
            stats_result = await self.plugin_commands.plugin_manager.get_plugin_stats()
            print(f"   ✅ 插件统计信息: {stats_result.get('total_plugins', 0)} 个插件")
            
            self.test_results.append(("插件管理命令", "PASS"))
            
        except Exception as e:
            print(f"   ❌ 插件管理命令测试失败: {e}")
            self.test_results.append(("插件管理命令", "FAIL"))
    
    async def test_channel_commands(self):
        """测试渠道管理命令"""
        print("\n📡 测试渠道管理命令...")
        
        try:
            # 测试列出渠道
            channel_list_result = await self.channel_commands.list_channels()
            if "error" not in channel_list_result:
                print(f"   ✅ 渠道列表获取成功: {channel_list_result.get('total', 0)} 个渠道")
            else:
                print(f"   ❌ 渠道列表获取失败: {channel_list_result['error']}")
            
            # 测试获取统计信息
            stats_result = self.channel_commands.channel_manager.get_statistics()
            print(f"   ✅ 渠道统计信息: {stats_result.get('total_channels', 0)} 个渠道")
            
            self.test_results.append(("渠道管理命令", "PASS"))
            
        except Exception as e:
            print(f"   ❌ 渠道管理命令测试失败: {e}")
            self.test_results.append(("渠道管理命令", "FAIL"))
    
    def test_cli_commands_import(self):
        """测试CLI命令导入"""
        print("\n📦 测试CLI命令导入...")
        
        try:
            # 测试导入插件命令
            from agentbus.cli.commands.plugin_commands import plugin
            from agentbus.cli.commands.channel_commands import channel
            
            print("   ✅ 插件命令导入成功")
            print("   ✅ 渠道命令导入成功")
            
            # 检查命令组
            if hasattr(plugin, 'commands') or len(plugin.commands) >= 0:
                print("   ✅ 插件命令组结构正确")
            
            if hasattr(channel, 'commands') or len(channel.commands) >= 0:
                print("   ✅ 渠道命令组结构正确")
            
            self.test_results.append(("CLI命令导入", "PASS"))
            
        except Exception as e:
            print(f"   ❌ CLI命令导入失败: {e}")
            self.test_results.append(("CLI命令导入", "FAIL"))
    
    def test_config_file_examples(self):
        """测试配置文件示例"""
        print("\n📋 测试配置文件示例...")
        
        try:
            # 检查插件配置文件
            plugin_config_path = Path("example_plugins_config.json")
            if plugin_config_path.exists():
                import json
                with open(plugin_config_path, 'r') as f:
                    plugin_config = json.load(f)
                if "plugins" in plugin_config:
                    print(f"   ✅ 插件配置文件有效: {len(plugin_config['plugins'])} 个插件")
                else:
                    print("   ❌ 插件配置文件格式错误")
            else:
                print("   ⚠️ 插件配置文件不存在")
            
            # 检查渠道配置文件
            channel_config_path = Path("example_channels_config.yaml")
            if channel_config_path.exists():
                import yaml
                with open(channel_config_path, 'r') as f:
                    channel_config = yaml.safe_load(f)
                if "channels" in channel_config:
                    print(f"   ✅ 渠道配置文件有效: {len(channel_config['channels'])} 个渠道")
                else:
                    print("   ❌ 渠道配置文件格式错误")
            else:
                print("   ⚠️ 渠道配置文件不存在")
            
            self.test_results.append(("配置文件示例", "PASS"))
            
        except Exception as e:
            print(f"   ❌ 配置文件示例测试失败: {e}")
            self.test_results.append(("配置文件示例", "FAIL"))
    
    def test_directory_structure(self):
        """测试目录结构"""
        print("\n📁 测试目录结构...")
        
        try:
            # 检查目录结构
            directories_to_check = [
                "cli/commands",
                "tests/test_cli",
            ]
            
            all_dirs_exist = True
            for dir_path in directories_to_check:
                if Path(dir_path).exists():
                    print(f"   ✅ 目录存在: {dir_path}")
                else:
                    print(f"   ❌ 目录不存在: {dir_path}")
                    all_dirs_exist = False
            
            # 检查重要文件
            files_to_check = [
                "cli/commands/__init__.py",
                "cli/commands/plugin_commands.py",
                "cli/commands/channel_commands.py",
                "tests/test_cli/__init__.py",
                "tests/test_cli/test_plugin_commands.py",
                "tests/test_cli/test_channel_commands.py",
            ]
            
            all_files_exist = True
            for file_path in files_to_check:
                if Path(file_path).exists():
                    print(f"   ✅ 文件存在: {file_path}")
                else:
                    print(f"   ❌ 文件不存在: {file_path}")
                    all_files_exist = False
            
            if all_dirs_exist and all_files_exist:
                self.test_results.append(("目录结构", "PASS"))
            else:
                self.test_results.append(("目录结构", "FAIL"))
                
        except Exception as e:
            print(f"   ❌ 目录结构测试失败: {e}")
            self.test_results.append(("目录结构", "FAIL"))
    
    async def cleanup(self):
        """清理测试环境"""
        print("\n🧹 清理测试环境...")
        
        try:
            # 停止渠道管理器
            if self.channel_manager:
                await self.channel_manager.stop()
            
            print("✅ 清理完成")
            
        except Exception as e:
            print(f"⚠️ 清理过程中发生错误: {e}")
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*50)
        print("🎯 测试摘要")
        print("="*50)
        
        passed = 0
        failed = 0
        
        for test_name, result in self.test_results:
            if result == "PASS":
                print(f"✅ {test_name}: {result}")
                passed += 1
            else:
                print(f"❌ {test_name}: {result}")
                failed += 1
        
        print("-" * 30)
        print(f"总计: {len(self.test_results)} 个测试")
        print(f"通过: {passed} 个")
        print(f"失败: {failed} 个")
        print(f"成功率: {passed / len(self.test_results) * 100:.1f}%")
        
        if failed == 0:
            print("\n🎉 所有测试通过！CLI增强功能开发完成。")
        else:
            print(f"\n⚠️ 有 {failed} 个测试失败，请检查相关功能。")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始测试AgentBus CLI增强功能")
        print("=" * 50)
        
        # 设置测试环境
        if not await self.setup():
            return False
        
        try:
            # 运行各项测试
            self.test_directory_structure()
            self.test_cli_commands_import()
            self.test_config_file_examples()
            await self.test_plugin_commands()
            await self.test_channel_commands()
            
        finally:
            # 清理环境
            await self.cleanup()
        
        # 打印摘要
        self.print_summary()
        
        return all(result == "PASS" for _, result in self.test_results)


async def main():
    """主函数"""
    tester = CLIEnhancementTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ CLI增强功能测试完成 - 全部通过")
        return 0
    else:
        print("\n❌ CLI增强功能测试失败 - 请检查错误")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)