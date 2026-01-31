"""
流式响应处理 (Stream Response Processing) 服务
Stream Response Processing service for AgentBus

本模块实现流式响应处理系统，支持AI模型响应的实时流式传输，
提供更好的用户体验和实时交互能力。
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, AsyncGenerator, Callable, Union
from enum import Enum
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from loguru import logger

from core.settings import settings


class StreamEventType(Enum):
    """流事件类型"""
    START = "start"
    TOKEN = "token"
    PROGRESS = "progress"
    COMPLETE = "complete"
    ERROR = "error"
    CANCEL = "cancel"
    HEARTBEAT = "heartbeat"


class StreamStatus(Enum):
    """流状态"""
    PENDING = "pending"
    STREAMING = "streaming"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class StreamChunk:
    """流数据块"""
    stream_id: str
    event_type: StreamEventType
    content: str = ""
    token_count: int = 0
    progress: float = 0.0
    timestamp: datetime = None
    metadata: Dict[str, Any] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class StreamRequest:
    """流请求"""
    stream_id: str
    task_id: Optional[str] = None
    content: str = ""
    stream_type: str = "text"  # text, code, analysis, etc.
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    chunk_size: int = 10  # 每次发送的token数量
    delay_ms: int = 50  # 发送间隔(毫秒)
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StreamHandler(ABC):
    """流处理器抽象基类"""
    
    @abstractmethod
    async def start_stream(self, request: StreamRequest) -> str:
        """开始流式传输"""
        pass
    
    @abstractmethod
    async def send_chunk(self, stream_id: str, chunk: StreamChunk) -> bool:
        """发送数据块"""
        pass
    
    @abstractmethod
    async def complete_stream(self, stream_id: str) -> bool:
        """完成流式传输"""
        pass
    
    @abstractmethod
    async def cancel_stream(self, stream_id: str) -> bool:
        """取消流式传输"""
        pass


class WebSocketStreamHandler(StreamHandler):
    """WebSocket流处理器"""
    
    def __init__(self):
        self.active_streams: Dict[str, asyncio.Queue] = {}
        self.stream_metadata: Dict[str, StreamRequest] = {}
        self.stream_status: Dict[str, StreamStatus] = {}
        self.subscribers: Dict[str, List[Callable]] = {}  # stream_id -> callbacks
        
    async def start_stream(self, request: StreamRequest) -> str:
        """开始WebSocket流式传输"""
        stream_id = request.stream_id
        
        # 创建流队列
        queue = asyncio.Queue()
        self.active_streams[stream_id] = queue
        self.stream_metadata[stream_id] = request
        self.stream_status[stream_id] = StreamStatus.PENDING
        
        logger.info(f"WebSocket流已创建: {stream_id}")
        return stream_id
    
    async def send_chunk(self, stream_id: str, chunk: StreamChunk) -> bool:
        """发送数据块到WebSocket"""
        if stream_id not in self.active_streams:
            logger.warning(f"流不存在: {stream_id}")
            return False
        
        try:
            queue = self.active_streams[stream_id]
            await queue.put(chunk)
            
            # 更新状态
            if chunk.event_type == StreamEventType.START:
                self.stream_status[stream_id] = StreamStatus.STREAMING
            
            logger.debug(f"WebSocket流数据块已发送: {stream_id} - {chunk.event_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"发送WebSocket流数据块失败: {e}")
            return False
    
    async def complete_stream(self, stream_id: str) -> bool:
        """完成WebSocket流式传输"""
        if stream_id not in self.active_streams:
            return False
        
        try:
            # 发送完成事件
            complete_chunk = StreamChunk(
                stream_id=stream_id,
                event_type=StreamEventType.COMPLETE,
                content="",
                token_count=0,
                progress=1.0
            )
            
            queue = self.active_streams[stream_id]
            await queue.put(complete_chunk)
            
            # 更新状态
            self.stream_status[stream_id] = StreamStatus.COMPLETED
            
            logger.info(f"WebSocket流已完成: {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"完成WebSocket流失败: {e}")
            return False
    
    async def cancel_stream(self, stream_id: str) -> bool:
        """取消WebSocket流式传输"""
        if stream_id not in self.active_streams:
            return False
        
        try:
            # 发送取消事件
            cancel_chunk = StreamChunk(
                stream_id=stream_id,
                event_type=StreamEventType.CANCEL,
                content="",
                token_count=0,
                progress=0.0
            )
            
            queue = self.active_streams[stream_id]
            await queue.put(cancel_chunk)
            
            # 更新状态
            self.stream_status[stream_id] = StreamStatus.CANCELLED
            
            # 清理资源
            del self.active_streams[stream_id]
            if stream_id in self.stream_metadata:
                del self.stream_metadata[stream_id]
            if stream_id in self.subscribers:
                del self.subscribers[stream_id]
            
            logger.info(f"WebSocket流已取消: {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消WebSocket流失败: {e}")
            return False
    
    async def get_stream_queue(self, stream_id: str) -> Optional[asyncio.Queue]:
        """获取流队列（用于WebSocket连接）"""
        return self.active_streams.get(stream_id)
    
    async def subscribe_stream(self, stream_id: str, callback: Callable):
        """订阅流事件"""
        if stream_id not in self.subscribers:
            self.subscribers[stream_id] = []
        self.subscribers[stream_id].append(callback)
    
    async def unsubscribe_stream(self, stream_id: str, callback: Callable):
        """取消订阅"""
        if stream_id in self.subscribers and callback in self.subscribers[stream_id]:
            self.subscribers[stream_id].remove(callback)


class HTTPStreamHandler(StreamHandler):
    """HTTP流处理器 (Server-Sent Events)"""
    
    def __init__(self):
        self.active_streams: Dict[str, asyncio.Queue] = {}
        self.stream_metadata: Dict[str, StreamRequest] = {}
        self.stream_status: Dict[str, StreamStatus] = {}
        
    async def start_stream(self, request: StreamRequest) -> str:
        """开始HTTP流式传输"""
        stream_id = request.stream_id
        
        # 创建流队列
        queue = asyncio.Queue()
        self.active_streams[stream_id] = queue
        self.stream_metadata[stream_id] = request
        self.stream_status[stream_id] = StreamStatus.PENDING
        
        logger.info(f"HTTP流已创建: {stream_id}")
        return stream_id
    
    async def send_chunk(self, stream_id: str, chunk: StreamChunk) -> bool:
        """发送数据块到HTTP流"""
        if stream_id not in self.active_streams:
            logger.warning(f"流不存在: {stream_id}")
            return False
        
        try:
            queue = self.active_streams[stream_id]
            await queue.put(chunk)
            
            # 更新状态
            if chunk.event_type == StreamEventType.START:
                self.stream_status[stream_id] = StreamStatus.STREAMING
            
            logger.debug(f"HTTP流数据块已发送: {stream_id} - {chunk.event_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"发送HTTP流数据块失败: {e}")
            return False
    
    async def complete_stream(self, stream_id: str) -> bool:
        """完成HTTP流式传输"""
        if stream_id not in self.active_streams:
            return False
        
        try:
            # 发送完成事件
            complete_chunk = StreamChunk(
                stream_id=stream_id,
                event_type=StreamEventType.COMPLETE,
                content="",
                token_count=0,
                progress=1.0
            )
            
            queue = self.active_streams[stream_id]
            await queue.put(complete_chunk)
            
            # 更新状态
            self.stream_status[stream_id] = StreamStatus.COMPLETED
            
            logger.info(f"HTTP流已完成: {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"完成HTTP流失败: {e}")
            return False
    
    async def cancel_stream(self, stream_id: str) -> bool:
        """取消HTTP流式传输"""
        if stream_id not in self.active_streams:
            return False
        
        try:
            # 发送取消事件
            cancel_chunk = StreamChunk(
                stream_id=stream_id,
                event_type=StreamEventType.CANCEL,
                content="",
                token_count=0,
                progress=0.0
            )
            
            queue = self.active_streams[stream_id]
            await queue.put(cancel_chunk)
            
            # 更新状态
            self.stream_status[stream_id] = StreamStatus.CANCELLED
            
            # 清理资源
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
            if stream_id in self.stream_metadata:
                del self.stream_metadata[stream_id]
            
            logger.info(f"HTTP流已取消: {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消HTTP流失败: {e}")
            return False


class StreamResponseProcessor:
    """流式响应处理器核心服务"""
    
    def __init__(self):
        self.handlers: Dict[str, StreamHandler] = {}
        self.active_streams: Dict[str, StreamRequest] = {}
        self.stream_status: Dict[str, StreamStatus] = {}
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        
        # 注册默认处理器
        self._register_default_handlers()
        
        logger.info("流式响应处理器初始化完成")
    
    def _register_default_handlers(self):
        """注册默认流处理器"""
        self.handlers["websocket"] = WebSocketStreamHandler()
        self.handlers["http"] = HTTPStreamHandler()
        logger.info("默认流处理器已注册")
    
    async def initialize(self):
        """初始化流式响应处理器"""
        try:
            logger.info("流式响应处理器初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"流式响应处理器初始化失败: {e}")
            return False
    
    async def shutdown(self):
        """关闭流式响应处理器"""
        # 取消所有活跃流
        for stream_id in list(self.active_streams.keys()):
            await self.cancel_stream(stream_id)
        
        logger.info("流式响应处理器已关闭")
    
    async def create_stream(
        self,
        request: StreamRequest,
        handler_type: str = "websocket"
    ) -> str:
        """创建流式传输"""
        try:
            if handler_type not in self.handlers:
                raise ValueError(f"不支持的处理器类型: {handler_type}")
            
            handler = self.handlers[handler_type]
            stream_id = await handler.start_stream(request)
            
            self.active_streams[stream_id] = request
            self.stream_status[stream_id] = StreamStatus.PENDING
            
            logger.info(f"流式传输已创建: {stream_id} (处理器: {handler_type})")
            return stream_id
            
        except Exception as e:
            logger.error(f"创建流式传输失败: {e}")
            raise
    
    async def start_stream_processing(
        self,
        stream_id: str,
        generator_func: Callable[[StreamRequest], AsyncGenerator[str, None]]
    ) -> bool:
        """开始流式处理"""
        try:
            if stream_id not in self.active_streams:
                logger.error(f"流不存在: {stream_id}")
                return False
            
            request = self.active_streams[stream_id]
            
            # 创建处理任务
            task = asyncio.create_task(
                self._process_stream_content(stream_id, request, generator_func)
            )
            self.processing_tasks[stream_id] = task
            
            logger.info(f"流式处理已开始: {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"开始流式处理失败: {e}")
            return False
    
    async def _process_stream_content(
        self,
        stream_id: str,
        request: StreamRequest,
        generator_func: Callable[[StreamRequest], AsyncGenerator[str, None]]
    ):
        """处理流式内容"""
        try:
            handler_type = "websocket" if stream_id in self.handlers["websocket"].active_streams else "http"
            handler = self.handlers[handler_type]
            
            # 发送开始事件
            start_chunk = StreamChunk(
                stream_id=stream_id,
                event_type=StreamEventType.START,
                content="",
                token_count=0,
                progress=0.0,
                metadata={"request": asdict(request)}
            )
            await handler.send_chunk(stream_id, start_chunk)
            
            total_tokens = 0
            chunk_buffer = ""
            
            # 流式处理内容
            async for content_chunk in generator_func(request):
                if stream_id not in self.active_streams:
                    # 流已被取消
                    break
                
                chunk_buffer += content_chunk
                total_tokens += 1
                
                # 按chunk_size发送
                if len(chunk_buffer) >= request.chunk_size or total_tokens % request.chunk_size == 0:
                    token_chunk = StreamChunk(
                        stream_id=stream_id,
                        event_type=StreamEventType.TOKEN,
                        content=chunk_buffer,
                        token_count=total_tokens,
                        progress=min(total_tokens / (request.max_tokens or 1000), 1.0)
                    )
                    
                    await handler.send_chunk(stream_id, token_chunk)
                    
                    # 重置缓冲区
                    chunk_buffer = ""
                    
                    # 添加延迟（模拟实时流）
                    if request.delay_ms > 0:
                        await asyncio.sleep(request.delay_ms / 1000)
            
            # 发送剩余内容
            if chunk_buffer:
                final_chunk = StreamChunk(
                    stream_id=stream_id,
                    event_type=StreamEventType.TOKEN,
                    content=chunk_buffer,
                    token_count=total_tokens,
                    progress=1.0
                )
                await handler.send_chunk(stream_id, final_chunk)
            
            # 发送完成事件
            await handler.complete_stream(stream_id)
            
            logger.info(f"流式处理已完成: {stream_id}")
            
        except asyncio.CancelledError:
            logger.info(f"流式处理已取消: {stream_id}")
            await self._handle_stream_error(stream_id, "流式处理被取消")
            
        except Exception as e:
            logger.error(f"流式处理错误: {stream_id} - {e}")
            await self._handle_stream_error(stream_id, str(e))
            
        finally:
            # 清理任务
            if stream_id in self.processing_tasks:
                del self.processing_tasks[stream_id]
    
    async def _handle_stream_error(self, stream_id: str, error_message: str):
        """处理流错误"""
        try:
            handler_type = "websocket" if stream_id in self.handlers["websocket"].active_streams else "http"
            handler = self.handlers[handler_type]
            
            error_chunk = StreamChunk(
                stream_id=stream_id,
                event_type=StreamEventType.ERROR,
                content="",
                token_count=0,
                progress=0.0,
                error=error_message
            )
            
            await handler.send_chunk(stream_id, error_chunk)
            
            # 更新状态
            self.stream_status[stream_id] = StreamStatus.ERROR
            
        except Exception as e:
            logger.error(f"处理流错误失败: {e}")
    
    async def cancel_stream(self, stream_id: str) -> bool:
        """取消流式传输"""
        try:
            # 取消处理任务
            if stream_id in self.processing_tasks:
                self.processing_tasks[stream_id].cancel()
                del self.processing_tasks[stream_id]
            
            # 取消流
            handler_type = "websocket" if stream_id in self.handlers["websocket"].active_streams else "http"
            handler = self.handlers[handler_type]
            success = await handler.cancel_stream(stream_id)
            
            # 清理状态
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
            if stream_id in self.stream_status:
                del self.stream_status[stream_id]
            
            logger.info(f"流式传输已取消: {stream_id}")
            return success
            
        except Exception as e:
            logger.error(f"取消流式传输失败: {e}")
            return False
    
    async def get_stream_status(self, stream_id: str) -> Optional[StreamStatus]:
        """获取流状态"""
        return self.stream_status.get(stream_id)
    
    async def get_stream_queue(self, stream_id: str) -> Optional[asyncio.Queue]:
        """获取流队列"""
        # 首先检查WebSocket处理器
        if stream_id in self.handlers["websocket"].active_streams:
            return await self.handlers["websocket"].get_stream_queue(stream_id)
        
        # 然后检查HTTP处理器
        return self.handlers["http"].active_streams.get(stream_id)
    
    async def list_active_streams(self) -> List[str]:
        """列出活跃流"""
        return list(self.active_streams.keys())
    
    async def get_stream_stats(self) -> Dict[str, Any]:
        """获取流统计信息"""
        stats = {
            "active_streams": len(self.active_streams),
            "total_streams": len(self.stream_status),
            "by_status": {},
            "processing_tasks": len(self.processing_tasks)
        }
        
        # 按状态统计
        for status in StreamStatus:
            count = sum(1 for s in self.stream_status.values() if s == status)
            stats["by_status"][status.value] = count
        
        return stats
    
    # 辅助方法：创建模拟AI响应生成器
    async def simulate_ai_response(self, request: StreamRequest) -> AsyncGenerator[str, None]:
        """模拟AI响应生成器（用于测试）"""
        responses = {
            "text": [
                "这是一个模拟的AI响应。",
                "AI正在思考中...",
                "让我继续分析这个问题。",
                "根据我的理解，",
                "我认为最佳的解决方案是：",
                "首先，我们需要考虑多个因素。",
                "这包括技术可行性、成本效益，",
                "以及用户的实际需求。",
                "综合考虑后，",
                "我建议采用渐进式的实施策略。"
            ],
            "code": [
                "def solution():",
                "    # 这是一个示例代码",
                "    result = []",
                "    for i in range(10):",
                "        if i % 2 == 0:",
                "            result.append(i)",
                "    return result"
            ]
        }
        
        response_list = responses.get(request.stream_type, responses["text"])
        
        for response_part in response_list:
            yield response_part
            await asyncio.sleep(0.1)  # 模拟处理延迟
        
        yield "\n\n以上是我的分析和建议。"


# 插件兼容性扩展
# Plugin Compatibility Extensions

def create_stream_plugin_manager():
    """
    创建流式响应插件管理器
    
    用于插件系统集成，提供插件化的流式响应处理服务。
    """
    from plugins.stream_plugin import StreamPlugin
    from plugins.core import PluginContext
    import logging
    
    # 创建默认上下文
    logger = logging.getLogger(__name__)
    context = PluginContext(
        config={
            "stream_chunk_size": 10,
            "stream_delay_ms": 50,
            "max_concurrent_streams": 100
        },
        logger=logger,
        runtime={}
    )
    
    # 创建插件实例
    plugin = StreamPlugin("default_stream_plugin", context)
    
    return plugin


async def initialize_stream_plugin(config=None):
    """
    初始化流式响应插件
    
    Args:
        config: 可选的配置字典
        
    Returns:
        初始化的StreamPlugin实例
    """
    from plugins.stream_plugin import StreamPlugin
    from plugins.core import PluginContext
    import logging
    
    logger = logging.getLogger(__name__)
    
    # 合并配置
    plugin_config = {
        "stream_chunk_size": 10,
        "stream_delay_ms": 50,
        "max_concurrent_streams": 100
    }
    
    if config:
        plugin_config.update(config)
    
    # 创建上下文和插件
    context = PluginContext(
        config=plugin_config,
        logger=logger,
        runtime={"standalone_mode": True}
    )
    
    plugin = StreamPlugin("initialized_stream_plugin", context)
    
    # 激活插件
    try:
        success = await plugin.activate()
        # 如果插件状态是ACTIVE，即使activate返回False，我们也认为成功
        if plugin.status.value not in ['active', 'ACTIVATED']:
            raise RuntimeError(f"Failed to activate stream plugin. Status: {plugin.status}")
    except Exception as e:
        raise RuntimeError(f"Failed to initialize stream plugin: {str(e)}")
    
    return plugin


# 向后兼容性函数
# Backward Compatibility Functions

async def create_standalone_stream_processor():
    """
    创建独立的流式响应处理器
    
    用于向后兼容，提供与原有代码相同的接口。
    
    Returns:
        StreamResponseProcessor实例
    """
    processor = StreamResponseProcessor()
    await processor.initialize()
    return processor


def get_stream_plugin_info():
    """
    获取流式响应插件信息
    
    Returns:
        插件信息字典
    """
    from plugins.stream_plugin import StreamPlugin
    from plugins.core import PluginContext
    import logging
    
    logger = logging.getLogger(__name__)
    context = PluginContext(
        config={},
        logger=logger,
        runtime={}
    )
    
    plugin = StreamPlugin("info_plugin", context)
    return plugin.get_info()


# 工厂函数
# Factory Functions

def stream_factory(use_plugin_mode=True, config=None):
    """
    流式响应处理器工厂函数
    
    Args:
        use_plugin_mode: 是否使用插件模式
        config: 配置选项
        
    Returns:
        StreamResponseProcessor或StreamPlugin实例
    """
    if use_plugin_mode:
        # 同步创建插件（需要异步初始化）
        def create_plugin():
            return initialize_stream_plugin(config)
        return create_plugin
    else:
        # 返回传统的处理器
        processor = StreamResponseProcessor()
        return processor


# 事件监听器适配器
# Event Listener Adapters

class PluginEventAdapter:
    """
    插件事件适配器
    
    用于将传统的事件监听器适配到插件系统的事件钩子。
    """
    
    def __init__(self, plugin_instance):
        self.plugin = plugin_instance
        self.event_listeners = {}
    
    def add_listener(self, event_type, listener_func):
        """
        添加事件监听器
        
        Args:
            event_type: 事件类型
            listener_func: 监听器函数
        """
        if event_type not in self.event_listeners:
            self.event_listeners[event_type] = []
        
        self.event_listeners[event_type].append(listener_func)
        
        # 注册为插件钩子
        self.plugin.register_hook(event_type, listener_func)
    
    def remove_listener(self, event_type, listener_func):
        """
        移除事件监听器
        
        Args:
            event_type: 事件类型
            listener_func: 监听器函数
        """
        if event_type in self.event_listeners:
            listeners = self.event_listeners[event_type]
            if listener_func in listeners:
                listeners.remove(listener_func)
    
    def trigger_event(self, event_type, event_data):
        """
        触发事件
        
        Args:
            event_type: 事件类型
            event_data: 事件数据
        """
        if event_type in self.event_listeners:
            for listener in self.event_listeners[event_type]:
                try:
                    if asyncio.iscoroutinefunction(listener):
                        asyncio.create_task(listener(event_data))
                    else:
                        listener(event_data)
                except Exception as e:
                    self.plugin.context.logger.error(f"Event listener error: {e}")


# 配置管理
# Configuration Management

class StreamConfig:
    """
    流式响应配置管理
    """
    
    DEFAULT_CONFIG = {
        "chunk_size": 10,
        "delay_ms": 50,
        "max_tokens": None,
        "temperature": 0.7,
        "max_concurrent_streams": 100,
        "heartbeat_interval": 30,
        "timeout": 300
    }
    
    def __init__(self, config_dict=None):
        self.config = self.DEFAULT_CONFIG.copy()
        if config_dict:
            self.config.update(config_dict)
    
    def get(self, key, default=None):
        """获取配置值"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置值"""
        self.config[key] = value
    
    def to_dict(self):
        """转换为字典"""
        return self.config.copy()
    
    @classmethod
    def from_env(cls, prefix="STREAM_"):
        """
        从环境变量创建配置
        
        Args:
            prefix: 环境变量前缀
            
        Returns:
            StreamConfig实例
        """
        import os
        
        config_dict = {}
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                
                # 类型转换
                if value.lower() in ('true', 'false'):
                    config_dict[config_key] = value.lower() == 'true'
                elif value.isdigit():
                    config_dict[config_key] = int(value)
                else:
                    try:
                        config_dict[config_key] = float(value)
                    except ValueError:
                        config_dict[config_key] = value
        
        return cls(config_dict)


# 工具函数
# Utility Functions

def validate_stream_config(config):
    """
    验证流配置
    
    Args:
        config: 配置字典
        
    Raises:
        ValueError: 配置无效时抛出
    """
    required_fields = ['chunk_size', 'delay_ms']
    
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required config field: {field}")
    
    # 验证数值范围
    if config['chunk_size'] <= 0:
        raise ValueError("chunk_size must be positive")
    
    if config['delay_ms'] < 0:
        raise ValueError("delay_ms must be non-negative")
    
    if 'max_concurrent_streams' in config and config['max_concurrent_streams'] <= 0:
        raise ValueError("max_concurrent_streams must be positive")


def create_stream_request_from_dict(data):
    """
    从字典创建流请求
    
    Args:
        data: 请求数据字典
        
    Returns:
        StreamRequest实例
        
    Raises:
        ValueError: 数据格式无效时抛出
    """
    required_fields = ['content', 'stream_type']
    
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    # 设置默认值
    stream_id = data.get('stream_id') or str(uuid.uuid4())
    chunk_size = data.get('chunk_size', 10)
    delay_ms = data.get('delay_ms', 50)
    max_tokens = data.get('max_tokens')
    temperature = data.get('temperature', 0.7)
    metadata = data.get('metadata', {})
    
    return StreamRequest(
        stream_id=stream_id,
        content=data['content'],
        stream_type=data['stream_type'],
        chunk_size=chunk_size,
        delay_ms=delay_ms,
        max_tokens=max_tokens,
        temperature=temperature,
        metadata=metadata
    )


def format_stream_stats(stats):
    """
    格式化流统计信息
    
    Args:
        stats: 原始统计字典
        
    Returns:
        格式化的统计字符串
    """
    lines = [
        "📊 流统计信息:",
        f"  总流数: {stats.get('total_streams', 0)}",
        f"  活跃流数: {stats.get('active_streams', 0)}",
        f"  已完成: {stats.get('completed_streams', 0)}",
        f"  错误: {stats.get('error_streams', 0)}",
        f"  已取消: {stats.get('cancelled_streams', 0)}",
        f"  数据块: {stats.get('total_chunks_sent', 0)}",
        f"  字节数: {stats.get('total_bytes_sent', 0)}"
    ]
    
    return "\n".join(lines)