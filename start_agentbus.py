#!/usr/bin/env python3
"""
AgentBus启动脚本
演示主应用程序的完整集成

Usage:
    python start_agentbus.py [options]

Examples:
    python start_agentbus.py --mode web --port 8000
    python start_agentbus.py --mode cli
    python start_agentbus.py --mode dev --debug
"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path

# 添加当前目录到项目路径
sys.path.insert(0, str(Path(__file__).parent))

from agentbus.core.app import start_server, AgentBusServer
from agentbus.core.main_app import AgentBusApplication
from agentbus.config import get_settings, ConfigManager
from py_moltbot.core.logger import get_logger

logger = get_logger(__name__)


async def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 初始化配置管理器
    try:
        config_manager = ConfigManager()
        settings = await config_manager.load_config()
        logger.info(f"✅ 配置加载成功 - 环境: {os.getenv('APP_ENV', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ 配置加载失败: {e}")
        logger.warning("使用默认配置继续启动...")
        from agentbus.config import get_settings
        settings = get_settings()
    
    # 设置日志级别
    log_level = getattr(logging, args.log_level.upper())
    logging.getLogger().setLevel(log_level)
    
    # 配置设置
    settings.app.debug = args.debug
    settings.app.host = args.host
    settings.app.port = args.port
    
    try:
        logger.info(f"🚀 启动AgentBus (模式: {args.mode})")
        
        if args.mode == "web":
            await start_web_server(args)
        elif args.mode == "cli":
            await start_cli_mode(args)
        elif args.mode == "dev":
            await start_dev_mode(args)
        else:
            raise ValueError(f"未知模式: {args.mode}")
            
    except KeyboardInterrupt:
        logger.info("🛑 接收到中断信号，正在关闭...")
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        sys.exit(1)


def create_parser():
    """创建命令行解析器"""
    parser = argparse.ArgumentParser(
        description="AgentBus AI Programming Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s --mode web --port 8000
  %(prog)s --mode cli
  %(prog)s --mode dev --debug

支持的模式:
  web   - Web服务器模式，提供REST API和Web管理界面
  cli   - 命令行模式，提供交互式命令行界面
  dev   - 开发模式，结合Web和CLI功能
        """
    )
    
    # 基本选项
    parser.add_argument(
        "--mode", "-m",
        choices=["web", "cli", "dev"],
        default="web",
        help="运行模式 (默认: web)"
    )
    
    parser.add_argument(
        "--host",
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
        "--debug", "-d",
        action="store_true",
        help="启用调试模式"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error"],
        default="info",
        help="日志级别 (默认: info)"
    )
    
    # 插件选项
    parser.add_argument(
        "--plugin-dirs",
        nargs="*",
        help="插件搜索目录列表"
    )
    
    parser.add_argument(
        "--no-auto-load-plugins",
        action="store_true",
        help="禁用自动加载插件"
    )
    
    # 渠道选项
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
    
    # 特殊选项
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅初始化但不启动服务"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="运行基本功能测试"
    )
    
    return parser


async def start_web_server(args):
    """启动Web服务器模式"""
    logger.info("🌐 启动Web服务器模式")
    
    if args.dry_run:
        await test_initialization(args)
        return
    
    if args.test:
        await run_tests(args)
        return
    
    await start_server(
        mode="web",
        plugin_dirs=args.plugin_dirs,
        channel_config_path=args.channel_config,
        auto_connect_channels=not args.no_auto_connect,
        auto_load_plugins=not args.no_auto_load_plugins,
        host=args.host,
        port=args.port,
        reload=args.debug
    )


async def start_cli_mode(args):
    """启动CLI模式"""
    logger.info("💻 启动CLI模式")
    
    if args.dry_run:
        await test_initialization(args)
        return
    
    if args.test:
        await run_tests(args)
        return
    
    await start_server(
        mode="cli",
        plugin_dirs=args.plugin_dirs,
        channel_config_path=args.channel_config,
        auto_connect_channels=not args.no_auto_connect,
        auto_load_plugins=not args.no_auto_load_plugins
    )


async def start_dev_mode(args):
    """启动开发模式"""
    logger.info("🔧 启动开发模式")
    
    if args.dry_run:
        await test_initialization(args)
        return
    
    if args.test:
        await run_tests(args)
        return
    
    await start_server(
        mode="dev",
        plugin_dirs=args.plugin_dirs,
        channel_config_path=args.channel_config,
        auto_connect_channels=not args.no_auto_connect,
        auto_load_plugins=not args.no_auto_load_plugins,
        host=args.host,
        port=args.port,
        reload=args.debug
    )


async def test_initialization(args):
    """测试初始化"""
    logger.info("🧪 测试应用程序初始化")
    
    try:
        # 创建应用程序实例
        app = AgentBusApplication(
            plugin_dirs=args.plugin_dirs,
            channel_config_path=args.channel_config,
            auto_connect_channels=not args.no_auto_connect,
            auto_load_plugins=not args.no_auto_load_plugins
        )
        
        # 初始化
        await app.initialize()
        
        # 获取健康状态
        health = await app.get_health_status()
        
        logger.info("✅ 应用程序初始化测试通过")
        logger.info(f"整体状态: {health['overall']['overall']}")
        
        # 打印组件状态
        logger.info("组件状态:")
        for component, status in health['overall']['components'].items():
            status_str = "✅" if status else "❌"
            logger.info(f"  {status_str} {component}")
        
        # 清理
        await app.cleanup()
        
        logger.info("🎉 所有测试通过！")
        
    except Exception as e:
        logger.error(f"❌ 初始化测试失败: {e}")
        raise


async def run_tests(args):
    """运行测试"""
    logger.info("🧪 运行系统测试")
    
    try:
        # 创建应用程序实例
        app = AgentBusApplication(
            plugin_dirs=args.plugin_dirs,
            channel_config_path=args.channel_config,
            auto_connect_channels=not args.no_auto_connect,
            auto_load_plugins=not args.no_auto_load_plugins
        )
        
        # 初始化
        await app.initialize()
        
        # 测试插件系统
        if app.plugin_manager:
            logger.info("🔌 测试插件系统")
            plugins = app.plugin_manager.list_plugins()
            logger.info(f"已加载插件: {len(plugins)} 个")
            
            if plugins:
                plugin_id = plugins[0]
                logger.info(f"测试插件: {plugin_id}")
                
                # 获取插件信息
                plugin_info = app.plugin_manager.get_plugin_info(plugin_id)
                if plugin_info:
                    logger.info(f"插件状态: {plugin_info.status.value}")
        
        # 测试渠道系统
        if app.channel_manager:
            logger.info("📡 测试渠道系统")
            channels = app.channel_manager.list_channels()
            logger.info(f"配置渠道: {len(channels)} 个")
            
            if channels:
                channel_id = channels[0]
                logger.info(f"测试渠道: {channel_id}")
                
                # 获取渠道状态
                status = await app.channel_manager.get_channel_status(channel_id)
                if status:
                    logger.info(f"渠道状态: {status.connection_status.value}")
        
        # 测试核心服务
        logger.info("⚙️ 测试核心服务")
        services_to_test = [
            ("HITL服务", app.hitl_service),
            ("沟通地图", app.communication_map),
            ("消息通道", app.message_channel),
            ("知识总线", app.knowledge_bus),
            ("多模型协调器", app.multi_model_coordinator),
            ("流式响应处理器", app.stream_response_processor),
        ]
        
        for service_name, service_instance in services_to_test:
            if service_instance:
                logger.info(f"✅ {service_name} 已初始化")
            else:
                logger.warning(f"❌ {service_name} 未初始化")
        
        # 获取完整健康状态
        health = await app.get_health_status()
        logger.info("📊 完整健康状态:")
        logger.info(f"整体状态: {health['overall']['overall']}")
        
        # 清理
        await app.cleanup()
        
        logger.info("🎉 所有测试完成！")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        raise


def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    🤖 AgentBus                              ║
║              AI Programming Assistant                       ║
║                                                              ║
║  统一管理插件、渠道和AI服务的智能助手系统                    ║
║                                                              ║
║  支持模式: Web服务器 | CLI交互 | 开发调试                   ║
║  管理界面: http://localhost:8000/management                 ║
║  API文档:   http://localhost:8000/docs                     ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


if __name__ == "__main__":
    print_banner()
    asyncio.run(main())