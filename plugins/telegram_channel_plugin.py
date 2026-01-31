"""
AgentBus Telegram渠道插件

此插件提供了完整的Telegram Bot API集成功能，包括：
- 文本消息发送和接收
- 媒体消息支持
- 群组和频道管理
- 投票功能
- 键盘和内联键盘
- 消息编辑和删除

使用方法：
1. 插件激活后自动注册Telegram渠道适配器
2. 通过PluginManager获取工具调用
3. 支持事件钩子监听消息
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
from urllib.parse import urljoin

from plugins.core import AgentBusPlugin, PluginContext, PluginTool, PluginHook


class TelegramChannelPlugin(AgentBusPlugin):
    """
    Telegram渠道插件
    
    提供Telegram Bot API的完整集成，支持消息、媒体、投票等功能。
    """
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        self._bots = {}  # 存储bot实例
        self._webhook_handlers = []
        self.message_count = 0
        self.last_message_time = None
        
    def get_info(self) -> Dict[str, Any]:
        """返回插件信息"""
        return {
            'id': self.plugin_id,
            'name': 'Telegram Channel Plugin',
            'version': '1.0.0',
            'description': '提供完整的Telegram Bot API集成，支持消息、媒体、投票等功能',
            'author': 'AgentBus Team',
            'dependencies': ['requests'],
            'capabilities': [
                'send_messages',
                'send_media', 
                'send_polls',
                'handle_webhooks',
                'manage_chats',
                'custom_keyboards'
            ]
        }
    
    async def activate(self):
        """激活插件并注册工具和钩子"""
        await super().activate()
        
        # 注册工具
        self.register_tool(
            name='send_message',
            description='发送Telegram消息',
            function=self.send_message
        )
        
        self.register_tool(
            name='send_media',
            description='发送媒体消息',
            function=self.send_media
        )
        
        self.register_tool(
            name='send_poll',
            description='发送投票',
            function=self.send_poll
        )
        
        self.register_tool(
            name='get_chat_info',
            description='获取聊天信息',
            function=self.get_chat_info
        )
        
        self.register_tool(
            name='set_webhook',
            description='设置Webhook',
            function=self.set_webhook
        )
        
        self.register_tool(
            name='get_bot_info',
            description='获取机器人信息',
            function=self.get_bot_info
        )
        
        self.register_tool(
            name='send_keyboard',
            description='发送带键盘的消息',
            function=self.send_keyboard
        )
        
        self.register_tool(
            name='edit_message',
            description='编辑消息',
            function=self.edit_message
        )
        
        # 注册钩子
        self.register_hook(
            event='telegram_message',
            handler=self.on_telegram_message,
            priority=10
        )
        
        self.register_hook(
            event='telegram_callback',
            handler=self.on_telegram_callback,
            priority=10
        )
        
        # 注册命令
        self.register_command(
            command='/telegram_status',
            handler=self.handle_status_command,
            description='显示Telegram插件状态'
        )
        
        self.register_command(
            command='/telegram_bots',
            handler=self.handle_bots_command,
            description='列出已配置的机器人'
        )
        
        self.context.logger.info(f"Telegram channel plugin {self.plugin_id} activated")
    
    def _get_api_url(self, bot_token: str, method: str) -> str:
        """获取Telegram API URL"""
        return urljoin(f"https://api.telegram.org/bot{bot_token}/", method)
    
    def _make_request(self, bot_token: str, method: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """发起Telegram API请求"""
        url = self._get_api_url(bot_token, method)
        
        try:
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.context.logger.error(f"Telegram API request failed: {e}")
            return {"ok": False, "error": str(e)}
    
    async def send_message(self, bot_token: str, chat_id: str, text: str, 
                          parse_mode: str = "HTML", reply_to_message_id: str = None) -> Dict[str, Any]:
        """发送Telegram消息"""
        try:
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            if reply_to_message_id:
                data["reply_to_message_id"] = reply_to_message_id
            
            result = self._make_request(bot_token, "sendMessage", data)
            
            if result.get("ok"):
                self.message_count += 1
                self.last_message_time = datetime.now()
                self.context.logger.info(f"Message sent to chat {chat_id}")
                return {"success": True, "message_id": result["result"]["message_id"]}
            else:
                self.context.logger.error(f"Failed to send message: {result.get('error', 'Unknown error')}")
                return {"success": False, "error": result.get('error', 'Unknown error')}
                
        except Exception as e:
            self.context.logger.error(f"Error sending message: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_media(self, bot_token: str, chat_id: str, media_type: str, 
                        media_url: str, caption: str = None, parse_mode: str = "HTML") -> Dict[str, Any]:
        """发送媒体消息"""
        try:
            # 确定媒体方法和字段
            method_mapping = {
                "photo": ("sendPhoto", "photo"),
                "video": ("sendVideo", "video"),
                "audio": ("sendAudio", "audio"),
                "document": ("sendDocument", "document")
            }
            
            if media_type not in method_mapping:
                return {"success": False, "error": f"Unsupported media type: {media_type}"}
            
            method, field = method_mapping[media_type]
            
            data = {
                "chat_id": chat_id,
                field: media_url
            }
            
            if caption:
                data["caption"] = caption
                data["parse_mode"] = parse_mode
            
            result = self._make_request(bot_token, method, data)
            
            if result.get("ok"):
                self.message_count += 1
                self.context.logger.info(f"Media sent to chat {chat_id}")
                return {"success": True, "message_id": result["result"]["message_id"]}
            else:
                return {"success": False, "error": result.get('error', 'Unknown error')}
                
        except Exception as e:
            self.context.logger.error(f"Error sending media: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_poll(self, bot_token: str, chat_id: str, question: str, 
                       options: List[str], is_anonymous: bool = True) -> Dict[str, Any]:
        """发送投票"""
        try:
            data = {
                "chat_id": chat_id,
                "question": question,
                "options": json.dumps(options),
                "is_anonymous": is_anonymous
            }
            
            result = self._make_request(bot_token, "sendPoll", data)
            
            if result.get("ok"):
                self.message_count += 1
                self.context.logger.info(f"Poll sent to chat {chat_id}")
                return {"success": True, "message_id": result["result"]["message_id"]}
            else:
                return {"success": False, "error": result.get('error', 'Unknown error')}
                
        except Exception as e:
            self.context.logger.error(f"Error sending poll: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_chat_info(self, bot_token: str, chat_id: str) -> Dict[str, Any]:
        """获取聊天信息"""
        try:
            data = {"chat_id": chat_id}
            result = self._make_request(bot_token, "getChat", data)
            
            if result.get("ok"):
                chat_info = result["result"]
                return {
                    "success": True,
                    "chat_info": {
                        "id": chat_info.get("id"),
                        "type": chat_info.get("type"),
                        "title": chat_info.get("title"),
                        "username": chat_info.get("username"),
                        "first_name": chat_info.get("first_name"),
                        "last_name": chat_info.get("last_name"),
                        "description": chat_info.get("description"),
                        "member_count": chat_info.get("pinned_message", {}).get("message_id")  # 简化
                    }
                }
            else:
                return {"success": False, "error": result.get('error', 'Unknown error')}
                
        except Exception as e:
            self.context.logger.error(f"Error getting chat info: {e}")
            return {"success": False, "error": str(e)}
    
    async def set_webhook(self, bot_token: str, webhook_url: str, 
                         allowed_updates: List[str] = None) -> Dict[str, Any]:
        """设置Webhook"""
        try:
            data = {
                "url": webhook_url,
                "allowed_updates": json.dumps(allowed_updates or ["message", "callback_query"])
            }
            
            result = self._make_request(bot_token, "setWebhook", data)
            
            if result.get("ok"):
                self.context.logger.info(f"Webhook set to {webhook_url}")
                return {"success": True, "result": result["result"]}
            else:
                return {"success": False, "error": result.get('error', 'Unknown error')}
                
        except Exception as e:
            self.context.logger.error(f"Error setting webhook: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_bot_info(self, bot_token: str) -> Dict[str, Any]:
        """获取机器人信息"""
        try:
            result = self._make_request(bot_token, "getMe")
            
            if result.get("ok"):
                bot_info = result["result"]
                return {
                    "success": True,
                    "bot_info": {
                        "id": bot_info.get("id"),
                        "first_name": bot_info.get("first_name"),
                        "username": bot_info.get("username"),
                        "can_join_groups": bot_info.get("can_join_groups"),
                        "can_read_all_group_messages": bot_info.get("can_read_all_group_messages"),
                        "supports_inline_queries": bot_info.get("supports_inline_queries")
                    }
                }
            else:
                return {"success": False, "error": result.get('error', 'Unknown error')}
                
        except Exception as e:
            self.context.logger.error(f"Error getting bot info: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_keyboard(self, bot_token: str, chat_id: str, text: str, 
                          keyboard_data: List[List[Dict[str, str]]], 
                          resize_keyboard: bool = True) -> Dict[str, Any]:
        """发送带键盘的消息"""
        try:
            data = {
                "chat_id": chat_id,
                "text": text,
                "reply_markup": {
                    "keyboard": keyboard_data,
                    "resize_keyboard": resize_keyboard,
                    "one_time_keyboard": False
                }
            }
            
            result = self._make_request(bot_token, "sendMessage", data)
            
            if result.get("ok"):
                self.message_count += 1
                return {"success": True, "message_id": result["result"]["message_id"]}
            else:
                return {"success": False, "error": result.get('error', 'Unknown error')}
                
        except Exception as e:
            self.context.logger.error(f"Error sending keyboard: {e}")
            return {"success": False, "error": str(e)}
    
    async def edit_message(self, bot_token: str, chat_id: str, message_id: str, 
                          text: str, parse_mode: str = "HTML") -> Dict[str, Any]:
        """编辑消息"""
        try:
            data = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            result = self._make_request(bot_token, "editMessageText", data)
            
            if result.get("ok"):
                self.context.logger.info(f"Message {message_id} edited in chat {chat_id}")
                return {"success": True}
            else:
                return {"success": False, "error": result.get('error', 'Unknown error')}
                
        except Exception as e:
            self.context.logger.error(f"Error editing message: {e}")
            return {"success": False, "error": str(e)}
    
    async def on_telegram_message(self, message_data: Dict[str, Any]):
        """Telegram消息接收钩子"""
        try:
            self.context.logger.debug(f"Received Telegram message: {message_data.get('message_id', 'unknown')}")
            # 这里可以添加消息处理逻辑
            # 例如：存储消息、触发其他事件等
        except Exception as e:
            self.context.logger.error(f"Error handling Telegram message: {e}")
    
    async def on_telegram_callback(self, callback_data: Dict[str, Any]):
        """Telegram回调钩子"""
        try:
            self.context.logger.debug(f"Received Telegram callback: {callback_data.get('id', 'unknown')}")
            # 处理内联键盘回调
        except Exception as e:
            self.context.logger.error(f"Error handling Telegram callback: {e}")
    
    async def handle_status_command(self, args: str) -> str:
        """处理状态命令"""
        try:
            status_info = {
                'plugin_id': self.plugin_id,
                'status': self.status.value,
                'message_count': self.message_count,
                'last_message_time': self.last_message_time.isoformat() if self.last_message_time else None,
                'active_bots': len(self._bots),
                'tools': len(self.get_tools()),
                'hooks': sum(len(hooks) for hooks in self.get_hooks().values()),
                'commands': len(self.get_commands())
            }
            
            return f"Telegram插件状态:\n{json.dumps(status_info, indent=2, ensure_ascii=False)}"
        except Exception as e:
            return f"获取状态失败: {str(e)}"
    
    async def handle_bots_command(self, args: str) -> str:
        """处理机器人列表命令"""
        try:
            if not self._bots:
                return "暂无已配置的机器人"
            
            bot_list = []
            for bot_id, bot_data in self._bots.items():
                bot_list.append(f"- {bot_id}: {bot_data.get('username', 'Unknown')}")
            
            return f"已配置的机器人:\n" + "\n".join(bot_list)
        except Exception as e:
            return f"获取机器人列表失败: {str(e)}"