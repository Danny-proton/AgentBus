"""
AgentBus主应用程序

统一的应用程序入口点，负责初始化和协调所有服务。
包括插件系统、渠道系统、各种AI服务等。
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..plugins.manager import PluginManager
from ..plugins.core import PluginContext
from ..channels.manager import ChannelManager
from ..services.hitl import HITLService
from ..services.communication_map import CommunicationMap
from ..services.message_channel import MessageChannel
from ..services.knowledge_bus import KnowledgeBus
from ..services.multi_model_coordinator import MultiModelCoordinator
from ..services.stream_response import StreamResponseProcessor
from ..core.settings import settings


class AgentBusApplication:
    """
    AgentBus主应用程序类
    
    负责协调和统一管理所有服务组件：
    - 插件系统 (PluginManager)
    - 渠道系统 (ChannelManager)
    - HITL服务 (HITLService)
    - 沟通地图 (CommunicationMap)
    - 消息通道 (MessageChannel)
    - 知识总线 (KnowledgeBus)
    - 多模型协调器 (MultiModelCoordinator)
    - 流式响应处理器 (StreamResponseProcessor)
    """
    
    def __init__(self, 
                 plugin_dirs: Optional[List[str]] = None,
                 channel_config_path: Optional[Path] = None,
                 auto_connect_channels: bool = True,
                 auto_load_plugins: bool = True):
        """
        初始化主应用程序
        
        Args:
            plugin_dirs: 插件搜索目录列表
            channel_config_path: 渠道配置文件路径
            auto_connect_channels: 是否自动连接渠道
            auto_load_plugins: 是否自动加载插件
        """
        # 基础设置
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # 服务组件
        self.plugin_manager: Optional[PluginManager] = None
        self.channel_manager: Optional[ChannelManager] = None
        self.hitl_service: Optional[HITLService] = None
        self.communication_map: Optional[CommunicationMap] = None
        self.message_channel: Optional[MessageChannel] = None
        self.knowledge_bus: Optional[KnowledgeBus] = None
        self.multi_model_coordinator: Optional[MultiModelCoordinator] = None
        self.stream_response_processor: Optional[StreamResponseProcessor] = None
        
        # 配置
        self.plugin_dirs = plugin_dirs
        self.channel_config_path = channel_config_path
        self.auto_connect_channels = auto_connect_channels
        self.auto_load_plugins = auto_load_plugins
        
        # 事件回调
        self.startup_callbacks: List[callable] = []
        self.shutdown_callbacks: List[callable] = []
        
        # 健康检查
        self.health_status = {
            "overall": "stopped",
            "components": {}
        }
    
    async def initialize(self):
        """初始化所有服务组件"""
        if self.running:
            self.logger.warning("应用程序已在运行中")
            return
        
        self.logger.info("🚀 初始化AgentBus主应用程序")
        
        try:
            # 1. 初始化插件系统
            await self._initialize_plugin_system()
            
            # 2. 初始化渠道系统
            await self._initialize_channel_system()
            
            # 3. 初始化核心服务
            await self._initialize_core_services()
            
            # 4. 执行启动回调
            await self._execute_startup_callbacks()
            
            # 5. 设置信号处理
            self._setup_signal_handlers()
            
            # 6. 更新健康状态
            await self._update_health_status()
            
            self.running = True
            self.logger.info("✅ AgentBus主应用程序初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 应用程序初始化失败: {e}")
            await self.cleanup()
            raise
    
    async def _initialize_plugin_system(self):
        """初始化插件系统"""
        self.logger.info("🔌 初始化插件系统")
        
        try:
            # 创建插件上下文
            plugin_context = PluginContext(
                config={},
                logger=logging.getLogger("agentbus.plugins"),
                runtime={
                    "channel_manager": lambda: self.channel_manager,
                    "hitl_service": lambda: self.hitl_service,
                    "knowledge_bus": lambda: self.knowledge_bus,
                    "multi_model_coordinator": lambda: self.multi_model_coordinator,
                }
            )
            
            # 创建插件管理器
            self.plugin_manager = PluginManager(
                context=plugin_context,
                plugin_dirs=self.plugin_dirs
            )
            
            # 自动发现并加载插件
            if self.auto_load_plugins:
                await self._auto_load_plugins()
            
            self.logger.info("✅ 插件系统初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 插件系统初始化失败: {e}")
            raise
    
    async def _auto_load_plugins(self):
        """自动加载插件"""
        try:
            self.logger.info("🔍 发现可用插件")
            
            # 发现插件
            discovered_plugins = await self.plugin_manager.discover_plugins()
            self.logger.info(f"发现 {len(discovered_plugins)} 个可用插件")
            
            # 自动激活核心插件
            for plugin_info in discovered_plugins:
                if plugin_info.plugin_id in ["knowledge", "hitl", "stream"]:
                    try:
                        self.logger.info(f"激活插件: {plugin_info.plugin_id}")
                        await self.plugin_manager.load_plugin(
                            plugin_info.plugin_id,
                            plugin_info.module_path,
                            plugin_info.class_name
                        )
                        await self.plugin_manager.activate_plugin(plugin_info.plugin_id)
                        self.logger.info(f"✅ 插件 {plugin_info.plugin_id} 激活成功")
                    except Exception as e:
                        self.logger.error(f"❌ 插件 {plugin_info.plugin_id} 激活失败: {e}")
            
        except Exception as e:
            self.logger.error(f"自动加载插件失败: {e}")
    
    async def _initialize_channel_system(self):
        """初始化渠道系统"""
        self.logger.info("📡 初始化渠道系统")
        
        try:
            # 创建渠道管理器
            self.channel_manager = ChannelManager(config_path=self.channel_config_path)
            
            # 启动渠道管理器
            await self.channel_manager.start()
            
            # 自动连接渠道
            if self.auto_connect_channels:
                self.logger.info("🔗 自动连接所有渠道")
                await self.channel_manager.connect_all()
            
            self.logger.info("✅ 渠道系统初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 渠道系统初始化失败: {e}")
            raise
    
    async def _initialize_core_services(self):
        """初始化核心服务"""
        self.logger.info("⚙️ 初始化核心服务")
        
        try:
            # 1. HITL服务
            self.logger.info("启动HITL服务")
            self.hitl_service = HITLService()
            await self.hitl_service.start()
            
            # 2. 沟通地图
            self.logger.info("加载沟通地图")
            self.communication_map = CommunicationMap()
            await self.communication_map.load()
            
            # 3. 消息通道
            self.logger.info("初始化消息通道")
            self.message_channel = MessageChannel()
            await self.message_channel.initialize()
            
            # 4. 知识总线
            self.logger.info("初始化知识总线")
            self.knowledge_bus = KnowledgeBus()
            await self.knowledge_bus.initialize()
            
            # 5. 多模型协调器
            self.logger.info("初始化多模型协调器")
            self.multi_model_coordinator = MultiModelCoordinator()
            await self.multi_model_coordinator.initialize()
            
            # 6. 流式响应处理器
            self.logger.info("初始化流式响应处理器")
            self.stream_response_processor = StreamResponseProcessor()
            await self.stream_response_processor.initialize()
            
            self.logger.info("✅ 核心服务初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 核心服务初始化失败: {e}")
            raise
    
    async def _execute_startup_callbacks(self):
        """执行启动回调"""
        for callback in self.startup_callbacks:
            try:
                await callback()
            except Exception as e:
                self.logger.error(f"启动回调执行失败: {e}")
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def signal_handler(signum, frame):
            self.logger.info(f"接收到信号 {signum}，开始优雅关闭")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def _update_health_status(self):
        """更新健康状态"""
        self.health_status = {
            "overall": "healthy" if self.running else "stopped",
            "components": {
                "plugin_manager": self.plugin_manager is not None,
                "channel_manager": self.channel_manager is not None,
                "hitl_service": self.hitl_service is not None,
                "communication_map": self.communication_map is not None,
                "message_channel": self.message_channel is not None,
                "knowledge_bus": self.knowledge_bus is not None,
                "multi_model_coordinator": self.multi_model_coordinator is not None,
                "stream_response_processor": self.stream_response_processor is not None,
            },
            "timestamp": asyncio.get_event_loop().time()
        }
    
    async def run(self):
        """运行应用程序主循环"""
        await self.initialize()
        
        self.logger.info("🎯 AgentBus应用程序运行中...")
        
        try:
            # 等待关闭事件
            await self.shutdown_event.wait()
        except KeyboardInterrupt:
            self.logger.info("接收到中断信号")
        finally:
            await self.cleanup()
    
    async def shutdown(self):
        """关闭应用程序"""
        if not self.running:
            return
        
        self.logger.info("🛑 开始关闭AgentBus应用程序")
        
        try:
            # 设置关闭标志
            self.running = False
            
            # 执行关闭回调
            await self._execute_shutdown_callbacks()
            
            # 1. 关闭插件系统
            await self._shutdown_plugin_system()
            
            # 2. 关闭渠道系统
            await self._shutdown_channel_system()
            
            # 3. 关闭核心服务
            await self._shutdown_core_services()
            
            # 设置关闭事件
            self.shutdown_event.set()
            
            # 更新健康状态
            self.health_status["overall"] = "stopped"
            
            self.logger.info("✅ AgentBus应用程序已关闭")
            
        except Exception as e:
            self.logger.error(f"❌ 应用程序关闭过程中出错: {e}")
    
    async def _execute_shutdown_callbacks(self):
        """执行关闭回调"""
        for callback in self.shutdown_callbacks:
            try:
                await callback()
            except Exception as e:
                self.logger.error(f"关闭回调执行失败: {e}")
    
    async def _shutdown_plugin_system(self):
        """关闭插件系统"""
        if self.plugin_manager:
            self.logger.info("🔌 关闭插件系统")
            try:
                # 停用所有插件
                plugin_ids = list(self.plugin_manager.list_plugins())
                for plugin_id in plugin_ids:
                    try:
                        await self.plugin_manager.deactivate_plugin(plugin_id)
                        self.logger.debug(f"插件 {plugin_id} 已停用")
                    except Exception as e:
                        self.logger.error(f"停用插件 {plugin_id} 失败: {e}")
                
                self.plugin_manager = None
                self.logger.info("✅ 插件系统已关闭")
            except Exception as e:
                self.logger.error(f"❌ 插件系统关闭失败: {e}")
    
    async def _shutdown_channel_system(self):
        """关闭渠道系统"""
        if self.channel_manager:
            self.logger.info("📡 关闭渠道系统")
            try:
                # 断开所有渠道
                await self.channel_manager.disconnect_all()
                
                # 停止渠道管理器
                await self.channel_manager.stop()
                
                self.channel_manager = None
                self.logger.info("✅ 渠道系统已关闭")
            except Exception as e:
                self.logger.error(f"❌ 渠道系统关闭失败: {e}")
    
    async def _shutdown_core_services(self):
        """关闭核心服务"""
        self.logger.info("⚙️ 关闭核心服务")
        
        services = [
            ("HITL服务", self.hitl_service, "stop"),
            ("沟通地图", self.communication_map, "save"),
            ("消息通道", self.message_channel, "close"),
            ("知识总线", self.knowledge_bus, "shutdown"),
            ("多模型协调器", self.multi_model_coordinator, "shutdown"),
            ("流式响应处理器", self.stream_response_processor, "shutdown"),
        ]
        
        for service_name, service_instance, method_name in services:
            if service_instance:
                try:
                    method = getattr(service_instance, method_name)
                    if asyncio.iscoroutinefunction(method):
                        await method()
                    else:
                        method()
                    self.logger.debug(f"{service_name} 已关闭")
                except Exception as e:
                    self.logger.error(f"关闭{service_name}失败: {e}")
        
        # 清空引用
        self.hitl_service = None
        self.communication_map = None
        self.message_channel = None
        self.knowledge_bus = None
        self.multi_model_coordinator = None
        self.stream_response_processor = None
        
        self.logger.info("✅ 核心服务已关闭")
    
    async def cleanup(self):
        """清理资源"""
        if self.running:
            await self.shutdown()
        
        # 强制垃圾回收
        import gc
        gc.collect()
    
    def add_startup_callback(self, callback):
        """添加启动回调"""
        self.startup_callbacks.append(callback)
    
    def add_shutdown_callback(self, callback):
        """添加关闭回调"""
        self.shutdown_callbacks.append(callback)
    
    async def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        await self._update_health_status()
        
        # 收集详细状态信息
        if self.channel_manager:
            channel_health = await self.channel_manager.health_check()
        else:
            channel_health = {"error": "channel_manager not initialized"}
        
        if self.plugin_manager:
            plugin_stats = await self.plugin_manager.get_plugin_stats()
        else:
            plugin_stats = {"error": "plugin_manager not initialized"}
        
        return {
            "overall": self.health_status,
            "channel_system": channel_health,
            "plugin_system": plugin_stats,
            "services": {
                "hitl_service": bool(self.hitl_service),
                "communication_map": bool(self.communication_map),
                "message_channel": bool(self.message_channel),
                "knowledge_bus": bool(self.knowledge_bus),
                "multi_model_coordinator": bool(self.multi_model_coordinator),
                "stream_response_processor": bool(self.stream_response_processor),
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "application": {
                "running": self.running,
                "uptime": 0  # 可以添加运行时间统计
            },
            "components": {}
        }
        
        if self.channel_manager:
            stats["components"]["channels"] = self.channel_manager.get_statistics()
        
        if self.plugin_manager:
            stats["components"]["plugins"] = {
                "total": len(self.plugin_manager.list_plugins()),
                "tools": len(self.plugin_manager.get_tools()),
                "commands": len(self.plugin_manager.get_commands()),
            }
        
        return stats


# 全局应用程序实例
_app_instance: Optional[AgentBusApplication] = None


def get_application() -> AgentBusApplication:
    """获取全局应用程序实例"""
    global _app_instance
    if _app_instance is None:
        raise RuntimeError("应用程序未初始化")
    return _app_instance


async def create_application(
    plugin_dirs: Optional[List[str]] = None,
    channel_config_path: Optional[Path] = None,
    auto_connect_channels: bool = True,
    auto_load_plugins: bool = True
) -> AgentBusApplication:
    """创建应用程序实例"""
    global _app_instance
    
    if _app_instance is not None:
        raise RuntimeError("应用程序实例已存在")
    
    _app_instance = AgentBusApplication(
        plugin_dirs=plugin_dirs,
        channel_config_path=channel_config_path,
        auto_connect_channels=auto_connect_channels,
        auto_load_plugins=auto_load_plugins
    )
    
    return _app_instance


async def destroy_application():
    """销毁应用程序实例"""
    global _app_instance
    
    if _app_instance:
        await _app_instance.cleanup()
        _app_instance = None


if __name__ == "__main__":
    # 用于测试的主函数
    async def main():
        app = await create_application()
        await app.run()
    
    asyncio.run(main())