"""
AgentBus统一应用程序入口点

提供统一的启动和管理接口，支持不同的运行模式：
- Web服务器模式（FastAPI）
- CLI模式
- 开发模式
"""

import asyncio
import argparse
import logging
import signal
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import uvicorn

from .main_app import AgentBusApplication, create_application, destroy_application
from api.main import create_app as create_fastapi_app
from core.settings import settings
import logging
logger = logging.getLogger(__name__)


class AgentBusServer:
    """AgentBus服务器类
    
    统一的服务器入口点，支持多种运行模式：
    - web: Web服务器模式
    - cli: 命令行模式
    - dev: 开发模式
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.app: Optional[AgentBusApplication] = None
        self.fastapi_app = None
        self.running = False
        self.mode = "web"  # 默认模式
    
    async def initialize(
        self,
        mode: str = "web",
        plugin_dirs: Optional[List[str]] = None,
        channel_config_path: Optional[Path] = None,
        auto_connect_channels: bool = True,
        auto_load_plugins: bool = True,
        host: str = "127.0.0.1",
        port: int = 8000,
        reload: bool = False
    ):
        """初始化服务器
        
        Args:
            mode: 运行模式 (web/cli/dev)
            plugin_dirs: 插件目录列表
            channel_config_path: 渠道配置文件路径
            auto_connect_channels: 是否自动连接渠道
            auto_load_plugins: 是否自动加载插件
            host: Web服务器主机地址
            port: Web服务器端口
            reload: 是否启用热重载
        """
        self.mode = mode
        
        self.logger.info(f"🚀 初始化AgentBus服务器 (模式: {mode})")
        
        try:
            # 1. 创建并初始化主应用程序
            self.app = await create_application(
                plugin_dirs=plugin_dirs,
                channel_config_path=channel_config_path,
                auto_connect_channels=auto_connect_channels,
                auto_load_plugins=auto_load_plugins
            )
            
            # 2. 初始化应用程序
            await self.app.initialize()
            
            # 3. 根据模式初始化不同的组件
            if mode == "web":
                await self._initialize_web_server(host, port, reload)
            elif mode == "dev":
                await self._initialize_dev_mode()
            
            self.running = True
            self.logger.info("✅ AgentBus服务器初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 服务器初始化失败: {e}")
            await self.cleanup()
            raise
    
    async def _initialize_web_server(self, host: str, port: int, reload: bool):
        """初始化Web服务器"""
        self.logger.info("🌐 初始化Web服务器")
        
        try:
            # 创建FastAPI应用
            self.fastapi_app = create_fastapi_app()
            
            # 注册应用程序到FastAPI应用中（用于依赖注入）
            self.fastapi_app.state.agentbus_app = self.app
            
            self.logger.info(f"✅ Web服务器初始化完成 ({host}:{port})")
            
        except Exception as e:
            self.logger.error(f"❌ Web服务器初始化失败: {e}")
            raise
    
    async def _initialize_dev_mode(self):
        """初始化开发模式"""
        self.logger.info("🔧 初始化开发模式")
        
        # 开发模式可以添加额外的调试和监控功能
        # 例如性能分析、调试端点等
        pass
    
    async def run(self):
        """运行服务器"""
        if not self.running:
            raise RuntimeError("服务器未初始化")
        
        self.logger.info(f"🎯 开始运行AgentBus服务器 (模式: {self.mode})")
        
        try:
            if self.mode == "web":
                await self._run_web_server()
            elif self.mode == "cli":
                await self._run_cli_mode()
            elif self.mode == "dev":
                await self._run_dev_mode()
            else:
                raise ValueError(f"未知模式: {self.mode}")
                
        except KeyboardInterrupt:
            self.logger.info("接收到中断信号")
        except Exception as e:
            self.logger.error(f"服务器运行错误: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def _run_web_server(self):
        """运行Web服务器"""
        if not self.fastapi_app:
            raise RuntimeError("FastAPI应用未初始化")
        
        # 从FastAPI应用中获取配置
        config = self.fastapi_app.router.routes[0].path if self.fastapi_app.router.routes else "/"
        
        # 运行uvicorn服务器
        config = uvicorn.Config(
            self.fastapi_app,
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        
        # 设置信号处理
        def signal_handler(signum, frame):
            self.logger.info("接收到关闭信号，正在停止服务器...")
            server.should_exit = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        await server.serve()
    
    async def _run_cli_mode(self):
        """运行CLI模式"""
        self.logger.info("💻 运行CLI模式")
        
        # CLI模式提供交互式命令行界面
        while self.running:
            try:
                command = input("AgentBus> ").strip()
                
                if command.lower() in ['exit', 'quit', 'q']:
                    break
                elif command.lower() == 'status':
                    await self._show_status()
                elif command.lower() == 'health':
                    await self._show_health()
                elif command.startswith('plugin '):
                    await self._handle_plugin_command(command)
                elif command.startswith('channel '):
                    await self._handle_channel_command(command)
                elif command.startswith('help'):
                    await self._show_help()
                else:
                    print("未知命令，输入 'help' 查看可用命令")
                    
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                self.logger.error(f"CLI命令执行错误: {e}")
        
        self.logger.info("CLI模式已退出")
    
    async def _run_dev_mode(self):
        """运行开发模式"""
        self.logger.info("🔧 运行开发模式")
        
        # 开发模式提供调试和开发工具
        await self._run_cli_mode()  # 先运行CLI模式
        
        # 开发模式可以添加更多功能，如代码热重载、调试端点等
        while self.running:
            await asyncio.sleep(1)
    
    async def _show_status(self):
        """显示系统状态"""
        if not self.app:
            print("应用程序未初始化")
            return
        
        stats = self.app.get_statistics()
        
        print("\n=== AgentBus 系统状态 ===")
        print(f"运行状态: {'运行中' if self.app.running else '已停止'}")
        print(f"运行模式: {self.mode}")
        
        if "components" in stats:
            components = stats["components"]
            
            if "channels" in components:
                channel_stats = components["channels"]
                print(f"\n📡 渠道系统:")
                print(f"  总渠道数: {channel_stats.get('total_channels', 0)}")
                print(f"  活跃适配器: {channel_stats.get('active_adapters', 0)}")
                print(f"  已连接渠道: {channel_stats.get('connected_channels', 0)}")
            
            if "plugins" in components:
                plugin_stats = components["plugins"]
                print(f"\n🔌 插件系统:")
                print(f"  总插件数: {plugin_stats.get('total', 0)}")
                print(f"  工具数量: {plugin_stats.get('tools', 0)}")
                print(f"  命令数量: {plugin_stats.get('commands', 0)}")
    
    async def _show_health(self):
        """显示健康状态"""
        if not self.app:
            print("应用程序未初始化")
            return
        
        health = await self.app.get_health_status()
        
        print("\n=== AgentBus 健康状态 ===")
        print(f"整体状态: {health['overall']['overall']}")
        
        if 'channel_system' in health:
            channel_health = health['channel_system']
            print(f"\n📡 渠道系统: {channel_health.get('overall_health', 'unknown')}")
        
        if 'plugin_system' in health:
            plugin_health = health['plugin_system']
            print(f"\n🔌 插件系统: {plugin_health.get('total_plugins', 0)} 个插件")
        
        print(f"\n⚙️ 核心服务:")
        for service, status in health['services'].items():
            print(f"  {service}: {'✓' if status else '✗'}")
    
    async def _handle_plugin_command(self, command: str):
        """处理插件命令"""
        parts = command.split()
        if len(parts) < 2:
            print("用法: plugin <list|info <plugin_id>>")
            return
        
        action = parts[1]
        
        if action == "list":
            if self.app and self.app.plugin_manager:
                plugins = self.app.plugin_manager.list_plugin_info()
                print(f"\n🔌 已加载插件 ({len(plugins)} 个):")
                for plugin in plugins:
                    print(f"  {plugin.plugin_id} - {plugin.name} ({plugin.status.value})")
            else:
                print("插件管理器未初始化")
        
        elif action == "info" and len(parts) > 2:
            plugin_id = parts[2]
            if self.app and self.app.plugin_manager:
                plugin_info = self.app.plugin_manager.get_plugin_info(plugin_id)
                if plugin_info:
                    print(f"\n🔌 插件信息: {plugin_id}")
                    print(f"  名称: {plugin_info.name}")
                    print(f"  版本: {plugin_info.version}")
                    print(f"  状态: {plugin_info.status.value}")
                    print(f"  描述: {plugin_info.description}")
                    if plugin_info.error_message:
                        print(f"  错误: {plugin_info.error_message}")
                else:
                    print(f"插件 {plugin_id} 未找到")
            else:
                print("插件管理器未初始化")
        else:
            print("用法: plugin <list|info <plugin_id>>")
    
    async def _handle_channel_command(self, command: str):
        """处理渠道命令"""
        parts = command.split()
        if len(parts) < 2:
            print("用法: channel <list|status|connect <channel_id>|disconnect <channel_id>>")
            return
        
        action = parts[1]
        
        if action == "list":
            if self.app and self.app.channel_manager:
                channels = self.app.channel_manager.list_channels()
                print(f"\n📡 配置的渠道 ({len(channels)} 个):")
                for channel_id in channels:
                    print(f"  {channel_id}")
            else:
                print("渠道管理器未初始化")
        
        elif action == "status":
            if self.app and self.app.channel_manager:
                status = await self.app.channel_manager.get_all_status()
                print(f"\n📡 渠道状态:")
                for channel_id, channel_status in status.items():
                    for account_id, account_status in channel_status.items():
                        print(f"  {channel_id}:{account_id} - {account_status.connection_status.value}")
            else:
                print("渠道管理器未初始化")
        
        elif action in ["connect", "disconnect"] and len(parts) > 2:
            action_name = "连接" if action == "connect" else "断开"
            channel_id = parts[2]
            
            if self.app and self.app.channel_manager:
                if action == "connect":
                    success = await self.app.channel_manager.connect_channel(channel_id)
                else:
                    success = await self.app.channel_manager.disconnect_channel(channel_id)
                
                status = "成功" if success else "失败"
                print(f"渠道 {channel_id} {action_name}{status}")
            else:
                print("渠道管理器未初始化")
        else:
            print("用法: channel <list|status|connect <channel_id>|disconnect <channel_id>>")
    
    async def _show_help(self):
        """显示帮助信息"""
        print("\n=== AgentBus CLI 帮助 ===")
        print("可用命令:")
        print("  status              - 显示系统状态")
        print("  health              - 显示健康状态")
        print("  plugin list         - 列出所有插件")
        print("  plugin info <id>   - 显示插件信息")
        print("  channel list        - 列出所有渠道")
        print("  channel status      - 显示渠道状态")
        print("  channel connect <id> - 连接渠道")
        print("  channel disconnect <id> - 断开渠道")
        print("  exit/quit/q         - 退出")
    
    async def cleanup(self):
        """清理资源"""
        if self.app:
            await self.app.cleanup()
            await destroy_application()
            self.app = None
        
        self.fastapi_app = None
        self.running = False
        
        self.logger.info("✅ AgentBus服务器已清理")


# 全局服务器实例
_server_instance: Optional[AgentBusServer] = None


async def start_server(
    mode: str = "web",
    plugin_dirs: Optional[List[str]] = None,
    channel_config_path: Optional[Path] = None,
    auto_connect_channels: bool = True,
    auto_load_plugins: bool = True,
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False
):
    """启动AgentBus服务器"""
    global _server_instance
    
    if _server_instance:
        raise RuntimeError("服务器已在运行中")
    
    _server_instance = AgentBusServer()
    
    try:
        await _server_instance.initialize(
            mode=mode,
            plugin_dirs=plugin_dirs,
            channel_config_path=channel_config_path,
            auto_connect_channels=auto_connect_channels,
            auto_load_plugins=auto_load_plugins,
            host=host,
            port=port,
            reload=reload
        )
        
        await _server_instance.run()
        
    finally:
        await _server_instance.cleanup()
        _server_instance = None


async def stop_server():
    """停止AgentBus服务器"""
    global _server_instance
    
    if _server_instance:
        await _server_instance.cleanup()
        _server_instance = None


def create_cli():
    """创建命令行接口"""
    parser = argparse.ArgumentParser(description="AgentBus AI Programming Assistant")
    
    parser.add_argument(
        "--mode", "-m",
        choices=["web", "cli", "dev"],
        default="web",
        help="运行模式 (默认: web)"
    )
    
    parser.add_argument(
        "--host", "-H",
        default="127.0.0.1",
        help="Web服务器主机地址 (默认: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Web服务器端口 (默认: 8000)"
    )
    
    parser.add_argument(
        "--reload", "-r",
        action="store_true",
        help="启用热重载 (仅开发模式)"
    )
    
    parser.add_argument(
        "--plugin-dirs",
        nargs="*",
        help="插件搜索目录列表"
    )
    
    parser.add_argument(
        "--channel-config",
        type=Path,
        help="渠道配置文件路径"
    )
    
    parser.add_argument(
        "--no-auto-connect",
        action="store_true",
        help="禁用自动连接渠道"
    )
    
    parser.add_argument(
        "--no-auto-load-plugins",
        action="store_true",
        help="禁用自动加载插件"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default="info",
        help="日志级别 (默认: info)"
    )
    
    return parser


async def main():
    """主函数"""
    parser = create_cli()
    args = parser.parse_args()
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    
    try:
        await start_server(
            mode=args.mode,
            plugin_dirs=args.plugin_dirs,
            channel_config_path=args.channel_config,
            auto_connect_channels=not args.no_auto_connect,
            auto_load_plugins=not args.no_auto_load_plugins,
            host=args.host,
            port=args.port,
            reload=args.reload
        )
    except KeyboardInterrupt:
        print("\n👋 再见!")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())