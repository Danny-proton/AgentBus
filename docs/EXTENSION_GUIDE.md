"""
扩展系统开发文档
Extension System Development Guide

本文档说明如何为py-moltbot开发适配器、工具和技能扩展
This document explains how to develop adapters, tools, and skill extensions for py-moltbot
"""

# =============================================================================
# 适配器开发 (Adapter Development)
# =============================================================================

"""
适配器开发指南
================

适配器用于将py-moltbot连接到各种消息平台（如Discord、Telegram等）

适配器开发步骤：
1. 继承BaseAdapter类
2. 实现必需的抽象方法
3. 使用@adapter装饰器注册
4. 编写测试
"""

from py_moltbot.adapters.base import (
    BaseAdapter, AdapterConfig, AdapterType, 
    Message, MessageType, User, Chat
)
from py_moltbot.core.logger import get_logger
import asyncio

# 示例：Discord适配器实现
class DiscordAdapter(BaseAdapter):
    """
    Discord消息平台适配器
    
    这个适配器展示了如何实现一个完整的消息平台适配器
    """
    
    def __init__(self, config: AdapterConfig):
        super().__init__(config)
        self.client = None  # Discord客户端实例
        
    async def connect(self) -> None:
        """
        连接到Discord
        
        实现步骤：
        1. 验证配置
        2. 初始化Discord客户端
        3. 设置事件处理器
        4. 启动连接
        """
        if not self.config.get_credential('bot_token'):
            raise ValueError("Discord bot token is required")
            
        try:
            # 初始化Discord客户端
            # 注意：这里使用discord.py库
            # import discord
            # self.client = discord.Client(intents=discord.Intents.default())
            
            self.logger.info("Connecting to Discord...", bot_token=self.config.get_credential('bot_token')[:10])
            
            # 模拟连接过程
            await asyncio.sleep(0.1)
            
            # 设置消息事件处理器
            # self.client.event(self.on_message)
            
            # 启动客户端
            # await self.client.start(self.config.get_credential('bot_token'))
            
        except Exception as e:
            self.logger.error("Failed to connect to Discord", error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """断开Discord连接"""
        if self.client:
            self.logger.info("Disconnecting from Discord...")
            # await self.client.close()
            self.client = None
    
    async def send_message(self, chat_id: str, content, **kwargs) -> str:
        """
        发送Discord消息
        
        Args:
            chat_id: Discord频道ID
            content: 消息内容
            **kwargs: 其他参数（如reply_to, embed等）
            
        Returns:
            发送的消息ID
        """
        try:
            # 获取频道
            # channel = self.client.get_channel(int(chat_id))
            # if not channel:
            #     raise ValueError(f"Channel {chat_id} not found")
            
            # 发送消息
            # message = await channel.send(content, **kwargs)
            # return str(message.id)
            
            # 模拟发送
            message_id = f"discord_msg_{hash(chat_id + str(content))}"
            self.logger.debug("Sent Discord message", 
                            channel_id=chat_id, 
                            message_id=message_id,
                            content_type=type(content).__name__)
            
            return message_id
            
        except Exception as e:
            self.logger.error("Failed to send Discord message", 
                            error=str(e), 
                            channel_id=chat_id)
            raise
    
    async def get_user_info(self, user_id: str) -> User:
        """
        获取Discord用户信息
        
        Args:
            user_id: Discord用户ID
            
        Returns:
            User对象
        """
        try:
            # 从Discord获取用户信息
            # user = await self.client.fetch_user(int(user_id))
            
            # 模拟用户信息
            user_data = {
                "id": user_id,
                "username": f"user_{user_id}",
                "display_name": f"User {user_id}",
                "avatar_url": f"https://cdn.discordapp.com/avatars/{user_id}/avatar.png",
                "is_bot": False
            }
            
            return User(
                id=user_data["id"],
                platform=self.config.adapter_type,
                username=user_data["username"],
                display_name=user_data["display_name"],
                avatar_url=user_data["avatar_url"],
                is_bot=user_data["is_bot"]
            )
            
        except Exception as e:
            self.logger.error("Failed to get Discord user info", 
                            error=str(e), 
                            user_id=user_id)
            raise
    
    async def get_chat_info(self, chat_id: str) -> Chat:
        """
        获取Discord频道信息
        
        Args:
            chat_id: Discord频道ID
            
        Returns:
            Chat对象
        """
        try:
            # 获取频道信息
            # channel = await self.client.fetch_channel(int(chat_id))
            
            # 模拟频道信息
            chat_data = {
                "id": chat_id,
                "name": f"Channel {chat_id}",
                "type": "text"
            }
            
            return Chat(
                id=chat_data["id"],
                platform=self.config.adapter_type,
                name=chat_data["name"],
                type=chat_data["type"]
            )
            
        except Exception as e:
            self.logger.error("Failed to get Discord chat info", 
                            error=str(e), 
                            chat_id=chat_id)
            raise
    
    # Discord特定的事件处理器
    async def on_message(self, message):
        """处理收到的Discord消息"""
        # 转换Discord消息为统一格式
        unified_message = Message(
            id=str(message.id),
            platform=self.config.adapter_type,
            chat_id=str(message.channel.id),
            user_id=str(message.author.id),
            content=message.content,
            message_type=MessageType.TEXT,
            timestamp=message.created_at,
            metadata={
                "discord_guild_id": str(message.guild.id) if message.guild else None,
                "discord_mentions": [str(m.id) for m in message.mentions],
                "discord_attachments": [att.filename for att in message.attachments]
            }
        )
        
        # 调用消息处理器
        await self._handle_message(unified_message)


# 注册Discord适配器
from py_moltbot.adapters.base import adapter, AdapterRegistry

@adapter("discord")
class DiscordAdapterRegistered(DiscordAdapter):
    """已注册的Discord适配器"""
    pass


# =============================================================================
# 技能开发 (Skill Development)
# =============================================================================

"""
技能开发指南
=============

技能用于扩展AI助手的功能，可以处理命令、AI响应、内容处理等

技能开发步骤：
1. 继承BaseSkill类
2. 实现execute方法
3. 定义技能元数据
4. 使用@skill装饰器注册
5. 编写测试
"""

from py_moltbot.skills.base import (
    BaseSkill, SkillContext, SkillResult, SkillType, SkillMetadata
)
import aiohttp
import json

class WeatherSkill(BaseSkill):
    """
    天气查询技能
    
    展示如何实现一个API集成的技能
    """
    
    def _get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="weather",
            version="1.0.0",
            description="Get weather information for a location",
            author="WeatherBot",
            skill_type=SkillType.COMMAND,
            tags=["weather", "api", "utility"],
            dependencies=[],  # 依赖其他技能
            permissions=["network_access"],
            timeout=10,
            max_concurrent=5
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """
        执行天气查询
        
        预期输入格式：
        - "weather Beijing"
        - "天气 上海"
        - {"location": "Beijing", "unit": "celsius"}
        """
        try:
            # 解析输入
            location = self._extract_location(context)
            if not location:
                return SkillResult.error(
                    "Please provide a location. Usage: weather <city_name>"
                )
            
            # 调用天气API（这里使用模拟数据）
            weather_data = await self._get_weather_data(location)
            if not weather_data:
                return SkillResult.error(f"Weather data not available for {location}")
            
            # 格式化响应
            response = self._format_weather_response(weather_data)
            
            return SkillResult.success(response)
            
        except Exception as e:
            self.logger.error("Weather skill execution failed", error=str(e))
            return SkillResult.error(f"Weather service error: {str(e)}")
    
    def _extract_location(self, context: SkillContext) -> str:
        """从上下文中提取位置信息"""
        user_input = context.get_user_input()
        
        # 简单解析：移除"weather"或"天气"关键词
        words = user_input.split()
        if len(words) > 1:
            return " ".join(words[1:])  # 获取第一个参数作为位置
        
        # 检查数据中是否有位置信息
        if "location" in context.data:
            return context.data["location"]
        
        return ""
    
    async def _get_weather_data(self, location: str) -> dict:
        """获取天气数据（模拟实现）"""
        try:
            # 模拟API调用
            # 实际实现中可以使用openweathermap、weatherapi等API
            await asyncio.sleep(0.1)  # 模拟网络延迟
            
            # 返回模拟数据
            return {
                "location": location,
                "temperature": 22,
                "unit": "celsius",
                "condition": "Sunny",
                "humidity": 65,
                "wind_speed": 15,
                "wind_direction": "NW"
            }
            
        except Exception as e:
            self.logger.error("Failed to fetch weather data", error=str(e))
            return {}
    
    def _format_weather_response(self, weather_data: dict) -> str:
        """格式化天气响应"""
        location = weather_data["location"]
        temp = weather_data["temperature"]
        condition = weather_data["condition"]
        humidity = weather_data["humidity"]
        wind = weather_data["wind_speed"]
        
        return f"""
🌤️  Weather for {location}:
   Temperature: {temp}°C
   Condition: {condition}
   Humidity: {humidity}%
   Wind: {wind} km/h
        """.strip()


class AISummarizerSkill(BaseSkill):
    """
    AI文本摘要技能
    
    展示如何集成AI模型的技能
    """
    
    def _get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="summarize",
            version="1.0.0",
            description="Summarize long text using AI",
            author="AISummarizer",
            skill_type=SkillType.AI_RESPONSE,
            tags=["ai", "summarization", "text"],
            ai_model="gpt-4",
            ai_prompt="Please summarize the following text concisely:",
            ai_temperature=0.3
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行AI摘要"""
        try:
            text = context.get_user_input()
            
            if len(text) < 50:
                return SkillResult.error("Text too short to summarize (minimum 50 characters)")
            
            # 调用AI模型进行摘要
            summary = await self._summarize_text(text)
            
            return SkillResult.success(summary)
            
        except Exception as e:
            self.logger.error("AI summarization failed", error=str(e))
            return SkillResult.error(f"AI service error: {str(e)}")
    
    async def _summarize_text(self, text: str) -> str:
        """调用AI模型摘要文本（模拟实现）"""
        # 实际实现中这里会调用OpenAI、Claude等API
        await asyncio.sleep(0.1)
        
        # 简单模拟：返回文本的前100个字符作为摘要
        if len(text) > 100:
            return text[:100] + "..."
        return text


# 注册技能
from py_moltbot.skills.base import skill, SkillRegistry

@skill("weather")
class WeatherSkillRegistered(WeatherSkill):
    """已注册的天气技能"""
    pass

@skill("summarize", dependencies=["weather"])
class AISummarizerSkillRegistered(AISummarizerSkill):
    """已注册的AI摘要技能"""
    pass


# =============================================================================
# 工具类扩展 (Tool Extensions)
# =============================================================================

"""
工具扩展开发指南
===============

工具用于提供系统级的功能，如文件操作、网络请求、数据库访问等

工具可以是：
1. 独立的Python模块
2. 外部API的封装
3. 系统命令的包装
4. 第三方服务的集成
"""

import aiofiles
import aiohttp
from pathlib import Path

class FileTool:
    """文件操作工具"""
    
    @staticmethod
    async def read_file(file_path: str) -> str:
        """异步读取文件"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    
    @staticmethod
    async def write_file(file_path: str, content: str) -> None:
        """异步写入文件"""
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
    
    @staticmethod
    async def list_directory(dir_path: str) -> list:
        """列出目录内容"""
        path = Path(dir_path)
        if not path.exists():
            return []
        
        items = []
        for item in path.iterdir():
            items.append({
                "name": item.name,
                "path": str(item),
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else None
            })
        return items


class HttpTool:
    """HTTP请求工具"""
    
    @staticmethod
    async def get(url: str, headers: dict = None, timeout: int = 30) -> dict:
        """异步GET请求"""
        timeout_config = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async with session.get(url, headers=headers) as response:
                return {
                    "status": response.status,
                    "text": await response.text(),
                    "json": await response.json() if response.headers.get('content-type', '').startswith('application/json') else None,
                    "headers": dict(response.headers)
                }
    
    @staticmethod
    async def post(url: str, data: dict = None, json_data: dict = None, headers: dict = None) -> dict:
        """异步POST请求"""
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, json=json_data, headers=headers) as response:
                return {
                    "status": response.status,
                    "text": await response.text(),
                    "json": await response.json() if response.headers.get('content-type', '').startswith('application/json') else None,
                    "headers": dict(response.headers)
                }


# =============================================================================
# 扩展配置示例 (Extension Configuration Examples)
# =============================================================================

"""
扩展配置文件示例
================

如何在.env文件中配置扩展：
"""

EXTENSION_CONFIG_EXAMPLE = """
# Discord适配器配置
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_guild_id_here

# Telegram适配器配置
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# 技能配置
WEATHER_API_KEY=your_weather_api_key_here
ENABLE_WEATHER_SKILL=true
ENABLE_SUMMARIZE_SKILL=true

# 工具配置
FILE_STORAGE_PATH=./data/files
HTTP_TIMEOUT=30
HTTP_MAX_RETRIES=3

# 插件配置
PLUGINS_PATH=./plugins
ENABLE_FILE_TOOLS=true
ENABLE_HTTP_TOOLS=true
"""

# =============================================================================
# 扩展开发最佳实践 (Extension Development Best Practices)
# =============================================================================

"""
最佳实践指南
============

1. 适配器开发：
   - 总是验证配置参数
   - 实现适当的错误处理和重试机制
   - 使用连接池管理资源
   - 遵循平台的速率限制

2. 技能开发：
   - 保持技能功能单一和专注
   - 实现超时机制避免阻塞
   - 提供有意义的错误消息
   - 使用适当的日志记录

3. 工具开发：
   - 确保线程安全（如需要）
   - 实现资源清理机制
   - 提供完整的错误信息
   - 考虑性能和内存使用

4. 通用原则：
   - 编写单元测试
   - 文档化API和使用方法
   - 遵循项目的编码规范
   - 考虑安全性和隐私保护
"""