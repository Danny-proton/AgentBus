#!/usr/bin/env python3
"""
AgentBus CLI 增强版
Enhanced AgentBus CLI

基于Moltbot CLI架构的增强版命令行界面，提供完整的系统管理功能。
"""

import asyncio
import click
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agentbus.cli.commands import (
    PluginCommands, ChannelCommands, ConfigCommands,
    BrowserCommands, SchedulerCommands, AdvancedCommandParser, CommandRegistry
)

from agentbus.plugins.manager import PluginManager
from agentbus.channels.manager import ChannelManager
from agentbus.config.config_manager import ConfigManager
from agentbus.automation.browser import BrowserAutomation
from agentbus.scheduler.task_manager import TaskManager
from agentbus.scheduler.cron_handler import CronHandler


class AgentBusCLI:
    """AgentBus CLI主类"""
    
    def __init__(self):
        # 初始化管理器
        self.config_manager = None
        self.channel_manager = None
        self.plugin_manager = None
        self.browser_automation = None
        self.task_manager = None
        self.cron_handler = None
        
        # 初始化CLI命令对象
        self.plugin_commands = None
        self.channel_commands = None
        self.config_commands = None
        self.browser_commands = None
        self.scheduler_commands = None
        
        # 初始化命令解析器
        self.command_parser = AdvancedCommandParser()
        self.command_registry = CommandRegistry()
    
    async def initialize(self, config_dir: Optional[Path] = None):
        """初始化CLI和所有管理器"""
        try:
            # 初始化配置管理器
            if not self.config_manager:
                self.config_manager = ConfigManager(config_dir)
                await self.config_manager.initialize()
            
            # 初始化渠道管理器
            if not self.channel_manager:
                self.channel_manager = ChannelManager(self.config_manager)
            
            # 初始化插件管理器
            if not self.plugin_manager:
                self.plugin_manager = PluginManager(self.config_manager)
            
            # 初始化浏览器自动化
            if not self.browser_automation:
                self.browser_automation = BrowserAutomation()
            
            # 初始化任务调度器
            if not self.task_manager:
                self.task_manager = TaskManager()
            
            if not self.cron_handler:
                self.cron_handler = CronHandler(self.task_manager)
            
            # 初始化CLI命令对象
            self.config_commands = ConfigCommands(self.config_manager)
            self.channel_commands = ChannelCommands(self.channel_manager)
            self.plugin_commands = PluginCommands(self.plugin_manager)
            self.browser_commands = BrowserCommands(self.browser_automation)
            self.scheduler_commands = SchedulerCommands(self.task_manager, self.cron_handler)
            
            logger.info("AgentBus CLI 初始化完成")
            
        except Exception as e:
            logger.error(f"AgentBus CLI 初始化失败: {e}")
            raise
    
    def setup_logging(self, verbose: bool = False):
        """设置日志"""
        # 移除默认处理器
        logger.remove()
        
        # 添加控制台输出
        level = "DEBUG" if verbose else "INFO"
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=level,
            colorize=True
        )
    
    def get_context(self) -> Dict[str, Any]:
        """获取CLI上下文"""
        return {
            'config_manager': self.config_manager,
            'channel_manager': self.channel_manager,
            'plugin_manager': self.plugin_manager,
            'browser_automation': self.browser_automation,
            'task_manager': self.task_manager,
            'cron_handler': self.cron_handler,
            'plugin_commands': self.plugin_commands,
            'channel_commands': self.channel_commands,
            'config_commands': self.config_commands,
            'browser_commands': self.browser_commands,
            'scheduler_commands': self.scheduler_commands
        }


# 创建CLI实例
cli = AgentBusCLI()


@click.group()
@click.option('--config-dir', type=Path, help='配置文件目录')
@click.option('--verbose', '-v', is_flag=True, help='详细输出')
@click.option('--debug', is_flag=True, help='调试模式')
@click.pass_context
def main(ctx, config_dir, verbose, debug):
    """AgentBus CLI - 增强版命令行界面"""
    # 设置上下文
    ctx.ensure_object(dict)
    
    # 设置日志
    cli.setup_logging(verbose or debug)
    
    # 初始化CLI
    if not hasattr(ctx, '_initialized') or not ctx._initialized:
        try:
            # 在事件循环中运行初始化
            if asyncio.get_event_loop().is_running():
                # 如果已经有运行中的事件循环，在新的任务中初始化
                asyncio.create_task(cli.initialize(config_dir))
            else:
                asyncio.run(cli.initialize(config_dir))
            ctx._initialized = True
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            if debug:
                raise
            click.echo(f"❌ 初始化失败: {e}", err=True)
            sys.exit(1)
    
    # 设置上下文对象
    for key, value in cli.get_context().items():
        ctx.obj[key] = value


# 导入所有命令组
from agentbus.cli.commands.plugin_commands import plugin
from agentbus.cli.commands.channel_commands import channel
from agentbus.cli.commands.config_commands import config
from agentbus.cli.commands.browser_commands import browser
from agentbus.cli.commands.scheduler_commands import scheduler

# 注册所有命令组
main.add_command(plugin, name='plugin')
main.add_command(channel, name='channel')
main.add_command(config, name='config')
main.add_command(browser, name='browser')
main.add_command(scheduler, name='scheduler')


@main.command()
@click.option('--output', '-o', type=Path, help='输出文件路径')
@click.pass_context
def status(ctx, output):
    """显示系统状态"""
    async def _status():
        try:
            # 获取各组件状态
            status_info = {
                "timestamp": asyncio.get_event_loop().time(),
                "components": {}
            }
            
            # 配置管理器状态
            if ctx.obj.get('config_manager'):
                status_info["components"]["config"] = {
                    "status": "ready",
                    "current_profile": ctx.obj['config_manager'].get_current_profile(),
                    "environment": ctx.obj['config_manager'].get_environment()
                }
            
            # 渠道管理器状态
            if ctx.obj.get('channel_manager'):
                try:
                    summary = await ctx.obj['channel_commands'].get_channels_status_summary()
                    status_info["components"]["channels"] = summary
                except Exception as e:
                    status_info["components"]["channels"] = {"error": str(e)}
            
            # 插件管理器状态
            if ctx.obj.get('plugin_manager'):
                try:
                    stats = await ctx.obj['plugin_manager'].get_plugin_stats()
                    status_info["components"]["plugins"] = stats
                except Exception as e:
                    status_info["components"]["plugins"] = {"error": str(e)}
            
            # 浏览器状态
            if ctx.obj.get('browser_automation'):
                try:
                    browser_status = await ctx.obj['browser_commands'].get_browser_status()
                    status_info["components"]["browser"] = browser_status
                except Exception as e:
                    status_info["components"]["browser"] = {"error": str(e)}
            
            # 调度器状态
            if ctx.obj.get('scheduler_commands'):
                try:
                    scheduler_status = await ctx.obj['scheduler_commands'].get_scheduler_status()
                    status_info["components"]["scheduler"] = scheduler_status
                except Exception as e:
                    status_info["components"]["scheduler"] = {"error": str(e)}
            
            # 输出状态
            if output:
                import json
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(status_info, f, indent=2, ensure_ascii=False, default=str)
                click.echo(f"✅ 系统状态已保存到: {output}")
            else:
                click.echo("🔧 AgentBus 系统状态")
                click.echo("=" * 50)
                
                for component, info in status_info["components"].items():
                    click.echo(f"\n📋 {component.upper()}:")
                    if "error" in info:
                        click.echo(f"   ❌ 错误: {info['error']}")
                    else:
                        click.echo(f"   ✅ 状态: {info.get('status', 'ready')}")
                        # 显示组件特定信息
                        if component == "config":
                            click.echo(f"   当前档案: {info.get('current_profile', 'unknown')}")
                            click.echo(f"   环境: {info.get('environment', 'unknown')}")
                        elif component == "channels":
                            click.echo(f"   总渠道: {info.get('total_channels', 0)}")
                            click.echo(f"   已连接: {info.get('connected_channels', 0)}")
                        elif component == "plugins":
                            click.echo(f"   总插件: {info.get('total_plugins', 0)}")
                            click.echo(f"   活跃插件: {info.get('active_plugins', 0)}")
                        elif component == "browser":
                            click.echo(f"   浏览器: {'运行中' if info.get('running') else '未运行'}")
                        elif component == "scheduler":
                            click.echo(f"   调度器: {'运行中' if info.get('scheduler', {}).get('status') == 'running' else '已停止'}")
                            click.echo(f"   总任务: {info.get('scheduler', {}).get('total_tasks', 0)}")
        
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            click.echo(f"❌ 获取系统状态失败: {e}", err=True)
    
    asyncio.run(_status())


@main.command()
@click.pass_context
def health(ctx):
    """健康检查"""
    async def _health():
        try:
            issues = []
            
            # 检查配置管理器
            if not ctx.obj.get('config_manager'):
                issues.append("配置管理器未初始化")
            
            # 检查渠道管理器
            if not ctx.obj.get('channel_manager'):
                issues.append("渠道管理器未初始化")
            
            # 检查插件管理器
            if not ctx.obj.get('plugin_manager'):
                issues.append("插件管理器未初始化")
            
            # 检查浏览器
            if not ctx.obj.get('browser_automation'):
                issues.append("浏览器自动化未初始化")
            
            # 检查调度器
            if not ctx.obj.get('task_manager'):
                issues.append("任务调度器未初始化")
            
            if issues:
                click.echo("❌ 健康检查失败:", err=True)
                for issue in issues:
                    click.echo(f"   - {issue}", err=True)
                sys.exit(1)
            else:
                click.echo("✅ 所有组件健康状态良好")
        
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            click.echo(f"❌ 健康检查失败: {e}", err=True)
            sys.exit(1)
    
    asyncio.run(_health())


@main.command()
@click.pass_context
def version(ctx):
    """显示版本信息"""
    click.echo("AgentBus CLI 增强版 v1.0.0")
    click.echo("基于Moltbot CLI架构构建")
    click.echo("支持插件、渠道、配置、浏览器、调度器管理")


if __name__ == '__main__':
    main()