"""
基础适配器接口
Base Adapter Interface

适配器模式实现，用于支持多种消息平台的统一接入
Adapter pattern implementation for unified access to multiple message platforms
"""

from abc import ABC, abstractmethod
from typing import (
    Any, Dict, List, Optional, Union, Callable, 
    AsyncIterator, Awaitable, TypeVar
)
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager

from ..core.logger import get_logger
from ..core.config import settings

# 类型定义
T = TypeVar('T')
MessageType = Union[str, Dict[str, Any], bytes]
CallbackType = Callable[[MessageType], Awaitable[None]]


class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"
    LOCATION = "location"
    CONTACT = "contact"
    STICKER = "sticker"
    SYSTEM = "system"


class AdapterType(Enum):
    """适配器类型枚举"""
    DISCORD = "discord"
    TELEGRAM = "telegram"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    SIGNAL = "signal"
    IMESSAGE = "imessage"
    WEB = "web"
    TERMINAL = "terminal"
    CUSTOM = "custom"


class AdapterStatus(Enum):
    """适配器状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


@dataclass
class Message:
    """消息数据类"""
    id: str
    platform: AdapterType
    chat_id: str
    user_id: str
    content: MessageType
    message_type: MessageType
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    reply_to: Optional[str] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def is_group(self) -> bool:
        """是否为群组消息"""
        return self.chat_id != self.user_id
    
    @property
    def text_content(self) -> str:
        """获取文本内容"""
        if isinstance(self.content, str):
            return self.content
        elif isinstance(self.content, dict):
            return self.content.get('text', '')
        return str(self.content)


@dataclass
class User:
    """用户数据类"""
    id: str
    platform: AdapterType
    username: str
    display_name: str
    avatar_url: Optional[str] = None
    is_bot: bool = False
    is_admin: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Chat:
    """聊天数据类"""
    id: str
    platform: AdapterType
    name: str
    type: str  # "private", "group", "channel"
    members: List[User] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdapterConfig:
    """适配器配置"""
    name: str
    adapter_type: AdapterType
    enabled: bool = True
    webhook_url: Optional[str] = None
    credentials: Dict[str, str] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    
    def get_credential(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取凭据"""
        return self.credentials.get(key, default)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """获取设置"""
        return self.settings.get(key, default)


class BaseAdapter(ABC):
    """
    基础适配器抽象类
    
    所有消息平台适配器必须继承此类并实现必要的抽象方法
    """
    
    def __init__(self, config: AdapterConfig):
        self.config = config
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        self.status = AdapterStatus.DISCONNECTED
        self._message_handlers: Dict[str, CallbackType] = {}
        self._event_handlers: Dict[str, List[CallbackType]] = {}
        self._tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        
    # === 抽象方法（必须实现） ===
    
    @abstractmethod
    async def connect(self) -> None:
        """连接到消息平台"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass
    
    @abstractmethod
    async def send_message(self, chat_id: str, content: MessageType, **kwargs) -> str:
        """
        发送消息
        
        Args:
            chat_id: 聊天ID
            content: 消息内容
            **kwargs: 其他参数
            
        Returns:
            消息ID
        """
        pass
    
    @abstractmethod
    async def get_user_info(self, user_id: str) -> Optional[User]:
        """获取用户信息"""
        pass
    
    @abstractmethod
    async def get_chat_info(self, chat_id: str) -> Optional[Chat]:
        """获取聊天信息"""
        pass
    
    # === 可选方法（默认实现） ===
    
    async def start(self) -> None:
        """启动适配器"""
        try:
            self.status = AdapterStatus.CONNECTING
            await self.connect()
            self.status = AdapterStatus.CONNECTED
            self.logger.info("Adapter started", adapter=self.config.name)
        except Exception as e:
            self.status = AdapterStatus.ERROR
            self.logger.error("Failed to start adapter", error=str(e))
            raise
    
    async def stop(self) -> None:
        """停止适配器"""
        self.status = AdapterStatus.SHUTTING_DOWN
        self.logger.info("Stopping adapter", adapter=self.config.name)
        
        # 取消所有任务
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # 等待任务完成
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        await self.disconnect()
        self.status = AdapterStatus.DISCONNECTED
        self.logger.info("Adapter stopped", adapter=self.config.name)
    
    async def restart(self) -> None:
        """重启适配器"""
        self.logger.info("Restarting adapter", adapter=self.config.name)
        await self.stop()
        await self.start()
    
    def on_message(self, message_type: Optional[MessageType] = None) -> Callable:
        """消息处理器装饰器"""
        def decorator(func: CallbackType) -> CallbackType:
            key = message_type.value if message_type else "all"
            self._message_handlers[key] = func
            return func
        return decorator
    
    def on_event(self, event_name: str) -> Callable:
        """事件处理器装饰器"""
        def decorator(func: CallbackType) -> CallbackType:
            if event_name not in self._event_handlers:
                self._event_handlers[event_name] = []
            self._event_handlers[event_name].append(func)
            return func
        return decorator
    
    async def _handle_message(self, message: Message) -> None:
        """处理收到的消息"""
        try:
            # 记录消息
            self.logger.debug("Received message", 
                           message_id=message.id,
                           platform=message.platform.value,
                           chat_id=message.chat_id,
                           message_type=message.message_type.value)
            
            # 查找合适的处理器
            handlers = []
            
            # 特定类型处理器
            if message.message_type.value in self._message_handlers:
                handlers.append(self._message_handlers[message.message_type.value])
            
            # 通用处理器
            if "all" in self._message_handlers:
                handlers.append(self._message_handlers["all"])
            
            # 执行处理器
            for handler in handlers:
                try:
                    await handler(message)
                except Exception as e:
                    self.logger.error("Message handler error", 
                                    error=str(e), 
                                    handler=handler.__name__)
        except Exception as e:
            self.logger.error("Failed to handle message", error=str(e))
    
    async def _emit_event(self, event_name: str, data: Any = None) -> None:
        """发射事件"""
        if event_name in self._event_handlers:
            for handler in self._event_handlers[event_name]:
                try:
                    await handler(data)
                except Exception as e:
                    self.logger.error("Event handler error", 
                                    event=event_name,
                                    error=str(e),
                                    handler=handler.__name__)
    
    # === 便利方法 ===
    
    async def send_text(self, chat_id: str, text: str, **kwargs) -> str:
        """发送文本消息"""
        return await self.send_message(chat_id, text, **kwargs)
    
    async def send_image(self, chat_id: str, image_url: str, caption: Optional[str] = None, **kwargs) -> str:
        """发送图片消息"""
        content = {"type": "image", "url": image_url, "caption": caption}
        return await self.send_message(chat_id, content, **kwargs)
    
    async def send_file(self, chat_id: str, file_url: str, filename: str, **kwargs) -> str:
        """发送文件消息"""
        content = {"type": "file", "url": file_url, "filename": filename}
        return await self.send_message(chat_id, content, **kwargs)
    
    async def reply(self, message_id: str, content: MessageType, **kwargs) -> str:
        """回复消息"""
        # 子类可以重写此方法实现更精确的回复逻辑
        chat_id = kwargs.get('chat_id', '')
        return await self.send_message(chat_id, content, reply_to=message_id, **kwargs)
    
    async def get_messages(self, chat_id: str, limit: int = 50) -> List[Message]:
        """获取聊天消息历史"""
        # 默认实现返回空列表，子类可以重写
        return []
    
    async def upload_file(self, file_path: str, file_type: str = "auto") -> Dict[str, str]:
        """上传文件"""
        # 默认实现返回空字典，子类可以重写
        return {}
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.status == AdapterStatus.CONNECTED
    
    @property
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self.config.enabled
    
    def get_info(self) -> Dict[str, Any]:
        """获取适配器信息"""
        return {
            "name": self.config.name,
            "type": self.config.adapter_type.value,
            "status": self.status.value,
            "enabled": self.config.enabled,
            "webhook_url": self.config.webhook_url,
        }


class AdapterRegistry:
    """适配器注册表"""
    
    _adapters: Dict[str, type] = {}
    _instances: Dict[str, BaseAdapter] = {}
    
    @classmethod
    def register(cls, name: str):
        """注册适配器"""
        def decorator(adapter_class: type) -> type:
            if not issubclass(adapter_class, BaseAdapter):
                raise ValueError(f"Adapter class must inherit from BaseAdapter: {adapter_class}")
            cls._adapters[name] = adapter_class
            return adapter_class
        return decorator
    
    @classmethod
    def get_adapter_class(cls, name: str) -> Optional[type]:
        """获取适配器类"""
        return cls._adapters.get(name)
    
    @classmethod
    def create_adapter(cls, name: str, config: AdapterConfig) -> BaseAdapter:
        """创建适配器实例"""
        adapter_class = cls.get_adapter_class(name)
        if not adapter_class:
            raise ValueError(f"Adapter '{name}' not registered")
        
        if name in cls._instances:
            return cls._instances[name]
        
        instance = adapter_class(config)
        cls._instances[name] = instance
        return instance
    
    @classmethod
    def get_adapter(cls, name: str) -> Optional[BaseAdapter]:
        """获取适配器实例"""
        return cls._instances.get(name)
    
    @classmethod
    def list_adapters(cls) -> List[str]:
        """列出所有注册的适配器"""
        return list(cls._adapters.keys())


# 自动注册装饰器
def adapter(name: str):
    """适配器注册装饰器"""
    return AdapterRegistry.register(name)