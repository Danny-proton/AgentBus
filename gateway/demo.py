"""
Gateway Demo

演示完整的网关系统功能
"""

import asyncio
import logging
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from . import (
    GatewayServer, GatewayClient, GatewayAuth, AuthMode, create_default_auth,
    GatewayConfig, ClientConfig, SyncGatewayClient
)
from .api import APIManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_server():
    """演示服务器功能"""
    logger.info("=== Gateway Server Demo ===")
    
    # 创建服务器配置
    config = GatewayConfig(
        host="127.0.0.1",
        port=18789,
        auth_mode=AuthMode.TOKEN,
        log_level="INFO"
    )
    
    # 创建服务器
    server = GatewayServer(config)
    
    # 创建API管理器
    api_manager = APIManager(
        server.protocol_handler,
        server.auth,
        server.connection_manager
    )
    
    # 启动服务器
    server_task = asyncio.create_task(server.start())
    api_task = asyncio.create_task(api_manager.start(host="127.0.0.1", port=8080))
    
    try:
        logger.info("Server started. Testing connections...")
        
        # 等待服务器启动
        await asyncio.sleep(2)
        
        # 演示客户端连接
        await demo_client()
        
        # 演示API调用
        await demo_api()
        
        # 保持服务器运行
        logger.info("Server demo completed. Press Ctrl+C to stop...")
        await asyncio.Event().wait()  # 永久等待
        
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        # 停止服务器
        server_task.cancel()
        api_task.cancel()
        await server.stop()
        await api_manager.stop()


async def demo_client():
    """演示客户端功能"""
    logger.info("=== Gateway Client Demo ===")
    
    # 获取认证令牌
    auth_token = server.auth.config.token if hasattr(server, 'auth') else "demo-token"
    
    # 创建客户端配置
    client_config = ClientConfig(
        url="ws://127.0.0.1:18789",
        client_name="Demo Client",
        auth_token=auth_token,
        auto_reconnect=False
    )
    
    # 创建客户端
    client = GatewayClient(client_config)
    
    try:
        # 连接
        logger.info("Connecting to gateway...")
        connect_task = asyncio.create_task(client.connect())
        
        # 等待连接
        await asyncio.wait_for(connect_task, timeout=10)
        
        if client.is_connected():
            logger.info("Connected successfully!")
            
            # 测试系统信息
            try:
                result = await client.send_request("system.info")
                logger.info(f"System info: {result}")
            except Exception as e:
                logger.error(f"System info failed: {e}")
            
            # 测试聊天功能
            try:
                # 创建会话
                session_result = await client.send_request("chat.sessions.create", {
                    "session_id": "demo-session-1",
                    "client_id": client_config.client_id
                })
                logger.info(f"Session created: {session_result}")
                
                # 发送消息
                chat_result = await client.send_request("chat.send", {
                    "session_id": "demo-session-1",
                    "message": "Hello, Gateway!",
                    "type": "text"
                })
                logger.info(f"Chat send result: {chat_result}")
                
                # 获取历史
                history_result = await client.send_request("chat.history", {
                    "session_id": "demo-session-1"
                })
                logger.info(f"Chat history: {history_result}")
                
            except Exception as e:
                logger.error(f"Chat demo failed: {e}")
            
            # 显示客户端状态
            status = client.get_status()
            logger.info(f"Client status: {status}")
            
        else:
            logger.error("Failed to connect")
    
    except Exception as e:
        logger.error(f"Client demo failed: {e}")
    
    finally:
        # 断开连接
        await client.disconnect("Demo completed")


async def demo_api():
    """演示API功能"""
    logger.info("=== Gateway API Demo ===")
    
    try:
        import aiohttp
        
        # 测试健康检查
        async with aiohttp.ClientSession() as session:
            # 健康检查
            async with session.get("http://127.0.0.1:8080/health") as resp:
                health = await resp.json()
                logger.info(f"Health check: {health}")
            
            # 状态查询
            async with session.get("http://127.0.0.1:8080/status") as resp:
                status = await resp.json()
                logger.info(f"Status: {status}")
            
            # 获取认证令牌
            auth_token = server.auth.config.token if hasattr(server, 'auth') else "demo-token"
            
            # 列出客户端
            headers = {"Authorization": f"Bearer {auth_token}"}
            async with session.get("http://127.0.0.1:8080/api/v1/clients", headers=headers) as resp:
                clients = await resp.json()
                logger.info(f"Clients: {clients}")
    
    except Exception as e:
        logger.error(f"API demo failed: {e}")


def demo_sync_client():
    """演示同步客户端"""
    logger.info("=== Sync Gateway Client Demo ===")
    
    # 创建同步客户端
    client_config = ClientConfig(
        url="ws://127.0.0.1:18789",
        client_name="Sync Demo Client",
        auth_token="demo-token",
        auto_reconnect=False
    )
    
    client = GatewayClient(client_config)
    sync_client = SyncGatewayClient(client)
    
    try:
        # 连接
        sync_client.connect()
        
        if sync_client.is_connected():
            logger.info("Sync client connected!")
            
            # 测试系统信息
            try:
                result = sync_client.send_request("system.info")
                logger.info(f"Sync system info: {result}")
            except Exception as e:
                logger.error(f"Sync system info failed: {e}")
        
    except Exception as e:
        logger.error(f"Sync client demo failed: {e}")
    
    finally:
        sync_client.disconnect("Demo completed")


# 全局服务器实例（用于演示）
server = None


def create_demo_server():
    """创建演示服务器"""
    global server
    
    config = GatewayConfig(
        host="127.0.0.1",
        port=18789,
        auth_mode=AuthMode.TOKEN,
        log_level="INFO"
    )
    
    server = GatewayServer(config)
    return server


async def main():
    """主函数"""
    logger.info("Starting Agentbus Gateway Demo")
    
    # 创建演示服务器
    demo_server_instance = create_demo_server()
    
    try:
        # 运行演示
        await demo_server()
    except KeyboardInterrupt:
        logger.info("Demo interrupted")
    except Exception as e:
        logger.error(f"Demo failed: {e}")


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════╗
    ║      Agentbus Gateway System        ║
    ║         Demo Application            ║
    ╠══════════════════════════════════════╣
    ║ Features:                           ║
    ║ • Gateway Server (WebSocket)        ║
    ║ • Client Authentication             ║
    ║ • Chat Processing                   ║
    ║ • WebSocket Communication           ║
    ║ • HTTP REST API                     ║
    ║ • Session Management                ║
    ║ • Device Management                 ║
    ║ • Real-time Events                  ║
    ╚══════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Demo stopped by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")