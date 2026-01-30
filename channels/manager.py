"""
AgentBus渠道管理器

负责管理所有渠道适配器，提供统一的渠道操作接口。
支持渠道的连接、断开、认证、消息发送等基础功能。
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import asdict
import json
import uuid

from .base import (
    ChannelAdapter,
    ChannelConfig,
    ChannelAccountConfig,
    ChannelStatus,
    Message,
    MessageType,
    ChatType,
    ChannelState,
    ConnectionStatus,
    ChannelRegistry,
    MessageMetadata,
)


class ChannelManager:
    """渠道管理器
    
    统一管理所有渠道适配器，提供：
    - 渠道注册和管理
    - 连接状态管理
    - 消息路由和发送
    - 配置管理
    - 状态监控
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.logger = logging.getLogger(__name__)
        self._adapters: Dict[str, ChannelAdapter] = {}
        self._configs: Dict[str, ChannelConfig] = {}
        self._status_cache: Dict[str, Dict[str, ChannelStatus]] = {}
        self._message_handlers: Set[Callable] = set()
        self._status_handlers: Set[Callable] = set()
        self._config_path = config_path or Path("channels_config.json")
        # 使用全局注册表而不是自己的实例
        from . import channel_registry
        self._registry = channel_registry
        self._running = False
        self._shutdown_event = asyncio.Event()
        
        # 自动保存配置的任务
        self._auto_save_task: Optional[asyncio.Task] = None
    
    @property
    def registry(self) -> ChannelRegistry:
        """获取渠道注册表"""
        return self._registry
    
    async def start(self):
        """启动渠道管理器"""
        if self._running:
            return
        
        self.logger.info("启动渠道管理器")
        self._running = True
        
        # 加载配置
        await self._load_configs()
        
        # 创建所有配置的适配器
        await self._create_adapters()
        
        # 启动自动保存任务
        self._auto_save_task = asyncio.create_task(self._auto_save_loop())
        
        self.logger.info("渠道管理器启动完成")
    
    async def stop(self):
        """停止渠道管理器"""
        was_running = self._running
        
        if not self._running:
            # 即使没有运行，也设置关闭事件
            self._shutdown_event.set()
            return
        
        self.logger.info("停止渠道管理器")
        self._running = False
        
        # 停止自动保存任务
        if self._auto_save_task:
            self._auto_save_task.cancel()
            try:
                await self._auto_save_task
            except asyncio.CancelledError:
                pass
        
        # 断开所有渠道连接
        if was_running:
            await self.disconnect_all()
        
        # 通知关闭事件
        self._shutdown_event.set()
        
        self.logger.info("渠道管理器已停止")
    
    async def _auto_save_loop(self):
        """自动保存配置循环"""
        while self._running:
            try:
                await asyncio.sleep(300)  # 每5分钟保存一次
                await self._save_configs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"自动保存配置失败: {e}")
    
    # 渠道管理方法
    
    async def register_channel(self, config: ChannelConfig) -> bool:
        """注册渠道"""
        try:
            # 创建适配器
            adapter = self._registry.create_adapter(config)
            
            # 注册适配器
            self._adapters[adapter.channel_id] = adapter
            
            # 保存配置
            self._configs[config.channel_id] = config
            
            # 添加事件处理器
            adapter.add_message_handler(self._on_message_received)
            adapter.add_event_handler(self._on_channel_event)
            
            self.logger.info(f"成功注册渠道: {adapter.channel_id}")
            await self._save_configs()
            return True
            
        except Exception as e:
            self.logger.error(f"注册渠道失败 {config.channel_id}: {e}")
            return False
    
    async def unregister_channel(self, channel_id: str) -> bool:
        """注销渠道"""
        try:
            # 断开连接
            if channel_id in self._adapters:
                await self.disconnect_channel(channel_id)
                
                # 移除适配器
                del self._adapters[channel_id]
            
            # 移除配置
            if channel_id in self._configs:
                del self._configs[channel_id]
            
            # 清理状态缓存
            if channel_id in self._status_cache:
                del self._status_cache[channel_id]
            
            self.logger.info(f"成功注销渠道: {channel_id}")
            await self._save_configs()
            return True
            
        except Exception as e:
            self.logger.error(f"注销渠道失败 {channel_id}: {e}")
            return False
    
    def get_channel_config(self, channel_id: str) -> Optional[ChannelConfig]:
        """获取渠道配置"""
        return self._configs.get(channel_id)
    
    def list_channels(self) -> List[str]:
        """列出所有渠道ID"""
        return list(self._configs.keys())
    
    def get_channel_adapter(self, channel_id: str) -> Optional[ChannelAdapter]:
        """获取渠道适配器"""
        return self._adapters.get(channel_id)
    
    # 连接管理方法
    
    async def connect_channel(self, channel_id: str, account_id: Optional[str] = None) -> bool:
        """连接单个渠道"""
        try:
            adapter = self._adapters.get(channel_id)
            if not adapter:
                self.logger.error(f"渠道未找到: {channel_id}")
                return False
            
            # 确定要连接的账户ID
            config = self._configs[channel_id]
            if not account_id:
                account_id = config.default_account_id
                if not account_id and config.accounts:
                    account_id = list(config.accounts.keys())[0]
            
            if not account_id:
                self.logger.error(f"渠道 {channel_id} 没有可用的账户配置")
                return False
            
            # 连接
            success = await adapter.connect(account_id)
            if success:
                self.logger.info(f"成功连接渠道: {channel_id} (账户: {account_id})")
            else:
                self.logger.error(f"连接渠道失败: {channel_id} (账户: {account_id})")
            
            return success
            
        except Exception as e:
            self.logger.error(f"连接渠道异常 {channel_id}: {e}")
            return False
    
    async def disconnect_channel(self, channel_id: str, account_id: Optional[str] = None) -> bool:
        """断开单个渠道"""
        try:
            adapter = self._adapters.get(channel_id)
            if not adapter:
                self.logger.error(f"渠道未找到: {channel_id}")
                return False
            
            # 确定要断开的账户ID
            config = self._configs[channel_id]
            if not account_id:
                account_id = config.default_account_id
                if not account_id and config.accounts:
                    account_id = list(config.accounts.keys())[0]
            
            if not account_id:
                self.logger.warning(f"渠道 {channel_id} 没有可用的账户配置")
                return True
            
            # 断开
            success = await adapter.disconnect(account_id)
            if success:
                self.logger.info(f"成功断开渠道: {channel_id} (账户: {account_id})")
            else:
                self.logger.error(f"断开渠道失败: {channel_id} (账户: {account_id})")
            
            return success
            
        except Exception as e:
            self.logger.error(f"断开渠道异常 {channel_id}: {e}")
            return False
    
    async def connect_all(self):
        """连接所有渠道"""
        tasks = []
        for channel_id in self._configs.keys():
            tasks.append(self.connect_channel(channel_id))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            self.logger.info(f"连接完成: {success_count}/{len(tasks)} 个渠道成功")
    
    async def disconnect_all(self):
        """断开所有渠道"""
        tasks = []
        for channel_id in self._adapters.keys():
            tasks.append(self.disconnect_channel(channel_id))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            self.logger.info("已断开所有渠道")
    
    async def is_channel_connected(self, channel_id: str, account_id: Optional[str] = None) -> bool:
        """检查渠道连接状态"""
        adapter = self._adapters.get(channel_id)
        if not adapter:
            return False
        
        config = self._configs[channel_id]
        if not account_id:
            account_id = config.default_account_id
            if not account_id and config.accounts:
                account_id = list(config.accounts.keys())[0]
        
        if not account_id:
            return False
        
        return await adapter.is_connected(account_id)
    
    # 消息发送方法
    
    async def send_message(
        self, 
        channel_id: str, 
        content: str, 
        message_type: MessageType = MessageType.TEXT,
        account_id: Optional[str] = None,
        **kwargs
    ) -> bool:
        """发送消息"""
        try:
            adapter = self._adapters.get(channel_id)
            if not adapter:
                self.logger.error(f"渠道未找到: {channel_id}")
                return False
            
            # 创建消息对象
            message = Message(
                type=message_type,
                content=content,
                metadata=MessageMetadata(
                    channel_id=channel_id,
                    chat_type=ChatType.DIRECT  # 默认值，可以根据需要调整
                )
            )
            
            # 添加额外元数据
            for key, value in kwargs.items():
                if hasattr(message.metadata, key):
                    setattr(message.metadata, key, value)
                else:
                    message.metadata.custom_data[key] = value
            
            # 发送消息
            success = await adapter.send_message(message, account_id)
            if success:
                self.logger.debug(f"成功发送消息到渠道: {channel_id}")
            else:
                self.logger.error(f"发送消息失败到渠道: {channel_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"发送消息异常 {channel_id}: {e}")
            return False
    
    async def send_media(
        self,
        channel_id: str,
        content: str,
        media_url: str,
        account_id: Optional[str] = None,
        **kwargs
    ) -> bool:
        """发送媒体消息"""
        try:
            adapter = self._adapters.get(channel_id)
            if not adapter:
                self.logger.error(f"渠道未找到: {channel_id}")
                return False
            
            # 创建媒体消息
            message = Message(
                type=MessageType.MEDIA,
                content=content,
                metadata=MessageMetadata(
                    channel_id=channel_id,
                    media_urls=[media_url]
                )
            )
            
            # 添加额外元数据
            for key, value in kwargs.items():
                if hasattr(message.metadata, key):
                    setattr(message.metadata, key, value)
                else:
                    message.metadata.custom_data[key] = value
            
            # 发送媒体消息
            success = await adapter.send_media(message, media_url, account_id)
            if success:
                self.logger.debug(f"成功发送媒体消息到渠道: {channel_id}")
            else:
                self.logger.error(f"发送媒体消息失败到渠道: {channel_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"发送媒体消息异常 {channel_id}: {e}")
            return False
    
    async def send_poll(
        self,
        channel_id: str,
        question: str,
        options: List[str],
        account_id: Optional[str] = None
    ) -> bool:
        """发送投票"""
        try:
            adapter = self._adapters.get(channel_id)
            if not adapter:
                self.logger.error(f"渠道未找到: {channel_id}")
                return False
            
            success = await adapter.send_poll(question, options, account_id)
            if success:
                self.logger.debug(f"成功发送投票到渠道: {channel_id}")
            else:
                self.logger.error(f"发送投票失败到渠道: {channel_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"发送投票异常 {channel_id}: {e}")
            return False
    
    # 状态管理方法
    
    async def get_channel_status(self, channel_id: str, account_id: Optional[str] = None) -> Optional[ChannelStatus]:
        """获取渠道状态"""
        adapter = self._adapters.get(channel_id)
        if not adapter:
            return None
        
        config = self._configs[channel_id]
        if not account_id:
            account_id = config.default_account_id
            if not account_id and config.accounts:
                account_id = list(config.accounts.keys())[0]
        
        if not account_id:
            return None
        
        return await adapter.get_status(account_id)
    
    async def get_all_status(self) -> Dict[str, Dict[str, ChannelStatus]]:
        """获取所有渠道状态"""
        result = {}
        for channel_id in self._adapters.keys():
            channel_status = {}
            adapter = self._adapters[channel_id]
            config = self._configs[channel_id]
            
            for account_id in config.accounts.keys():
                try:
                    status = await adapter.get_status(account_id)
                    channel_status[account_id] = status
                except Exception as e:
                    self.logger.error(f"获取渠道状态失败 {channel_id}:{account_id}: {e}")
            
            if channel_status:
                result[channel_id] = channel_status
        
        return result
    
    # 配置管理方法
    
    async def update_channel_config(self, channel_id: str, config: ChannelConfig) -> bool:
        """更新渠道配置"""
        try:
            # 更新配置
            self._configs[channel_id] = config
            
            # 重新创建适配器
            if channel_id in self._adapters:
                await self.disconnect_channel(channel_id)
                del self._adapters[channel_id]
            
            adapter = self._registry.create_adapter(config)
            self._adapters[channel_id] = adapter
            adapter.add_message_handler(self._on_message_received)
            adapter.add_event_handler(self._on_channel_event)
            
            self.logger.info(f"成功更新渠道配置: {channel_id}")
            await self._save_configs()
            return True
            
        except Exception as e:
            self.logger.error(f"更新渠道配置失败 {channel_id}: {e}")
            return False
    
    async def _load_configs(self):
        """加载配置"""
        try:
            if self._config_path.exists():
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for channel_id, config_data in data.get("channels", {}).items():
                    try:
                        config = ChannelConfig.from_dict(config_data)
                        self._configs[channel_id] = config
                    except Exception as e:
                        self.logger.error(f"加载渠道配置失败 {channel_id}: {e}")
                
                self.logger.info(f"成功加载 {len(self._configs)} 个渠道配置")
            else:
                self.logger.info("配置文件不存在，使用空配置")
                
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
    
    async def _save_configs(self):
        """保存配置"""
        try:
            data = {
                "channels": {
                    channel_id: config.to_dict()
                    for channel_id, config in self._configs.items()
                },
                "last_updated": datetime.now().isoformat()
            }
            
            # 创建目录
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
    
    async def _create_adapters(self):
        """创建适配器"""
        for channel_id, config in self._configs.items():
            try:
                adapter = self._registry.create_adapter(config)
                self._adapters[channel_id] = adapter
                adapter.add_message_handler(self._on_message_received)
                adapter.add_event_handler(self._on_channel_event)
                self.logger.debug(f"创建渠道适配器: {channel_id}")
            except Exception as e:
                self.logger.error(f"创建渠道适配器失败 {channel_id}: {e}")
    
    # 事件处理方法
    
    def add_message_handler(self, handler: Callable[[Message, str], None]):
        """添加消息处理器"""
        self._message_handlers.add(handler)
    
    def remove_message_handler(self, handler: Callable[[Message, str], None]):
        """移除消息处理器"""
        self._message_handlers.discard(handler)
    
    def add_status_handler(self, handler: Callable[[str, ChannelStatus], None]):
        """添加状态处理器"""
        self._status_handlers.add(handler)
    
    def remove_status_handler(self, handler: Callable[[str, ChannelStatus], None]):
        """移除状态处理器"""
        self._status_handlers.discard(handler)
    
    def _on_message_received(self, message: Message):
        """消息接收处理"""
        # 通知所有注册的处理器
        for handler in self._message_handlers:
            try:
                handler(message, message.metadata.channel_id or "")
            except Exception as e:
                self.logger.error(f"消息处理器错误: {e}")
    
    def _on_channel_event(self, event_type: str, data: Any):
        """渠道事件处理"""
        if event_type == "status_changed":
            channel_id = data.get("channel_id")
            status = data.get("status")
            if channel_id and status:
                for handler in self._status_handlers:
                    try:
                        handler(channel_id, status)
                    except Exception as e:
                        self.logger.error(f"状态处理器错误: {e}")
    
    # 工具方法
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        connected_count = 0
        total_messages = 0
        
        for channel_id in self._adapters.keys():
            try:
                # 这里可以添加更详细的统计逻辑
                connected_count += 1 if self._adapters[channel_id] else 0
            except Exception:
                pass
        
        return {
            "total_channels": len(self._configs),
            "active_adapters": len(self._adapters),
            "connected_channels": connected_count,
            "running": self._running,
            "config_path": str(self._config_path),
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        status = {
            "manager_running": self._running,
            "channels": {},
            "overall_health": "healthy"
        }
        
        unhealthy_channels = 0
        for channel_id in self._adapters.keys():
            try:
                channel_status = await self.get_channel_status(channel_id)
                if channel_status:
                    is_healthy = (
                        channel_status.connection_status == ConnectionStatus.CONNECTED and
                        channel_status.state in [ChannelState.ENABLED, ChannelState.RUNNING]
                    )
                    status["channels"][channel_id] = {
                        "healthy": is_healthy,
                        "connection_status": channel_status.connection_status.value,
                        "state": channel_status.state.value
                    }
                    if not is_healthy:
                        unhealthy_channels += 1
                else:
                    status["channels"][channel_id] = {"healthy": False, "error": "status_unavailable"}
                    unhealthy_channels += 1
            except Exception as e:
                status["channels"][channel_id] = {"healthy": False, "error": str(e)}
                unhealthy_channels += 1
        
        if unhealthy_channels > 0:
            status["overall_health"] = "degraded" if unhealthy_channels < len(self._adapters) else "unhealthy"
        
        return status