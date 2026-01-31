"""
AgentBus Discord渠道插件

此插件提供了完整的Discord Bot API集成功能，包括：
- 文本消息发送和接收
- 媒体消息支持
- 频道和服务器管理
- 角色和权限管理
- Webhook集成
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import aiohttp
from urllib.parse import urljoin

from plugins.core import AgentBusPlugin, PluginContext, PluginTool, PluginHook


class DiscordChannelPlugin(AgentBusPlugin):
    """
    Discord渠道插件
    
    提供Discord Bot API的完整集成，支持消息、媒体、服务器管理等功能。
    """
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        self._sessions = {}
        self.message_count = 0
        self.last_message_time = None
        self._guild_cache = {}
        
    def get_info(self) -> Dict[str, Any]:
        """返回插件信息"""
        return {
            'id': self.plugin_id,
            'name': 'Discord Channel Plugin',
            'version': '1.0.0',
            'description': '提供完整的Discord Bot API集成，支持消息、媒体、服务器管理等功能',
            'author': 'AgentBus Team',
            'dependencies': ['aiohttp'],
            'capabilities': [
                'send_messages', 'send_media', 'manage_guilds', 
                'manage_channels', 'webhooks', 'slash_commands'
            ]
        }
    
    async def activate(self):
        """激活插件并注册工具和钩子"""
        await super().activate()
        
        # 注册工具
        self.register_tool('send_message', '发送Discord消息', self.send_message)
        self.register_tool('send_embed', '发送Embed消息', self.send_embed)
        self.register_tool('send_media', '发送媒体消息', self.send_media)
        self.register_tool('create_webhook', '创建Webhook', self.create_webhook)
        self.register_tool('send_webhook', '通过Webhook发送消息', self.send_webhook)
        self.register_tool('get_guild_info', '获取服务器信息', self.get_guild_info)
        self.register_tool('create_channel', '创建频道', self.create_channel)
        self.register_tool('manage_role', '管理角色', self.manage_role)
        self.register_tool('get_user_info', '获取用户信息', self.get_user_info)
        self.register_tool('add_reaction', '添加反应', self.add_reaction)
        
        # 注册钩子
        self.register_hook('discord_message', self.on_discord_message, 10)
        self.register_hook('discord_guild_member_add', self.on_guild_member_add, 5)
        self.register_hook('discord_reaction_add', self.on_reaction_add, 5)
        
        # 注册命令
        self.register_command('/discord_status', self.handle_status_command, '显示Discord插件状态')
        self.register_command('/discord_servers', self.handle_servers_command, '列出已连接的服务器')
        
        self.context.logger.info(f"Discord channel plugin {self.plugin_id} activated")
    
    def _get_api_url(self, bot_token: str, endpoint: str) -> str:
        """获取Discord API URL"""
        return urljoin("https://discord.com/api/v10/", endpoint)
    
    async def _make_request(self, bot_token: str, method: str, endpoint: str, 
                           data: Dict[str, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """发起Discord API请求"""
        if headers is None:
            headers = {}
        
        headers.update({
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json"
        })
        
        # 获取或创建session
        if bot_token not in self._sessions:
            self._sessions[bot_token] = aiohttp.ClientSession()
        
        session = self._sessions[bot_token]
        url = self._get_api_url(bot_token, endpoint)
        
        try:
            async with session.request(method, url, json=data, headers=headers) as response:
                result = await response.json()
                
                if response.status == 200:
                    return {"success": True, "data": result}
                elif response.status == 429:
                    retry_after = result.get("retry_after", 1)
                    await asyncio.sleep(retry_after)
                    return await self._make_request(bot_token, method, endpoint, data, headers)
                else:
                    return {"success": False, "error": result.get("message", "Unknown error")}
                    
        except aiohttp.ClientError as e:
            return {"success": False, "error": str(e)}
    
    async def send_message(self, bot_token: str, channel_id: str, content: str, 
                          embed_data: Dict[str, Any] = None, reply_to: str = None) -> Dict[str, Any]:
        """发送Discord消息"""
        try:
            data = {"content": content}
            
            if embed_data:
                data["embeds"] = [embed_data]
            
            if reply_to:
                data["message_reference"] = {"message_id": reply_to}
            
            endpoint = f"channels/{channel_id}/messages"
            result = await self._make_request(bot_token, "POST", endpoint, data)
            
            if result["success"]:
                self.message_count += 1
                self.last_message_time = datetime.now()
                self.context.logger.info(f"Message sent to channel {channel_id}")
                return {
                    "success": True, 
                    "message_id": result["data"]["id"],
                    "timestamp": result["data"]["timestamp"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            self.context.logger.error(f"Error sending message: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_embed(self, bot_token: str, channel_id: str, title: str, 
                        description: str, color: int = 0x00ff00, 
                        fields: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """发送Embed消息"""
        try:
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.now().isoformat()
            }
            
            if fields:
                embed["fields"] = fields
            
            data = {"embeds": [embed]}
            endpoint = f"channels/{channel_id}/messages"
            result = await self._make_request(bot_token, "POST", endpoint, data)
            
            if result["success"]:
                self.message_count += 1
                return {"success": True, "message_id": result["data"]["id"]}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            self.context.logger.error(f"Error sending embed: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_media(self, bot_token: str, channel_id: str, file_path: str, 
                        caption: str = None) -> Dict[str, Any]:
        """发送媒体消息"""
        try:
            files = {}
            filename = file_path.split("/")[-1]
            
            with open(file_path, 'rb') as f:
                files['file'] = (filename, f.read())
            
            data = {'content': caption} if caption else {}
            
            headers = {"Authorization": f"Bot {bot_token}"}
            
            if bot_token not in self._sessions:
                self._sessions[bot_token] = aiohttp.ClientSession()
            
            session = self._sessions[bot_token]
            url = self._get_api_url(bot_token, f"channels/{channel_id}/messages")
            
            async with session.post(url, data=data, files=files, headers=headers) as response:
                result = await response.json()
                
                if response.status == 200:
                    self.message_count += 1
                    return {"success": True, "message_id": result["id"]}
                else:
                    return {"success": False, "error": result.get("message", "Upload failed")}
                    
        except Exception as e:
            self.context.logger.error(f"Error sending media: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_webhook(self, bot_token: str, channel_id: str, name: str) -> Dict[str, Any]:
        """创建Webhook"""
        try:
            data = {"name": name}
            endpoint = f"channels/{channel_id}/webhooks"
            result = await self._make_request(bot_token, "POST", endpoint, data)
            
            if result["success"]:
                webhook_info = result["data"]
                return {
                    "success": True,
                    "webhook": {
                        "id": webhook_info["id"],
                        "token": webhook_info["token"],
                        "url": f"https://discord.com/api/webhooks/{webhook_info['id']}/{webhook_info['token']}"
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            self.context.logger.error(f"Error creating webhook: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_webhook(self, webhook_url: str, content: str, username: str = None) -> Dict[str, Any]:
        """通过Webhook发送消息"""
        try:
            data = {"content": content}
            if username:
                data["username"] = username
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=data) as response:
                    if response.status == 204:
                        self.message_count += 1
                        return {"success": True}
                    else:
                        return {"success": False, "error": f"HTTP {response.status}"}
                        
        except Exception as e:
            self.context.logger.error(f"Error sending webhook: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_guild_info(self, bot_token: str, guild_id: str) -> Dict[str, Any]:
        """获取服务器信息"""
        try:
            endpoint = f"guilds/{guild_id}"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                guild_data = result["data"]
                return {
                    "success": True,
                    "guild_info": {
                        "id": guild_data["id"],
                        "name": guild_data["name"],
                        "member_count": guild_data.get("member_count"),
                        "channels": len(guild_data.get("channels", [])),
                        "roles": len(guild_data.get("roles", [])),
                        "features": guild_data.get("features", [])
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            self.context.logger.error(f"Error getting guild info: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_channel(self, bot_token: str, guild_id: str, name: str, 
                           channel_type: int = 0) -> Dict[str, Any]:
        """创建频道"""
        try:
            data = {"name": name, "type": channel_type}
            endpoint = f"guilds/{guild_id}/channels"
            result = await self._make_request(bot_token, "POST", endpoint, data)
            
            if result["success"]:
                channel_data = result["data"]
                return {
                    "success": True,
                    "channel": {
                        "id": channel_data["id"],
                        "name": channel_data["name"],
                        "type": channel_data["type"]
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            self.context.logger.error(f"Error creating channel: {e}")
            return {"success": False, "error": str(e)}
    
    async def manage_role(self, bot_token: str, guild_id: str, role_id: str, 
                         action: str, **kwargs) -> Dict[str, Any]:
        """管理角色"""
        try:
            allowed_actions = ["create", "modify", "delete"]
            if action not in allowed_actions:
                return {"success": False, "error": f"Invalid action. Must be one of: {allowed_actions}"}
            
            endpoint = f"guilds/{guild_id}/roles"
            
            if action == "create":
                result = await self._make_request(bot_token, "POST", endpoint, kwargs)
            elif action == "modify":
                if not role_id:
                    return {"success": False, "error": "Role ID required for modify action"}
                result = await self._make_request(bot_token, "PATCH", f"guilds/{guild_id}/roles/{role_id}", kwargs)
            elif action == "delete":
                if not role_id:
                    return {"success": False, "error": "Role ID required for delete action"}
                result = await self._make_request(bot_token, "DELETE", f"guilds/{guild_id}/roles/{role_id}")
            
            if result["success"]:
                return {"success": True, "role_data": result["data"]} if action != "delete" else {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            self.context.logger.error(f"Error managing role: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_info(self, bot_token: str, user_id: str) -> Dict[str, Any]:
        """获取用户信息"""
        try:
            endpoint = f"users/{user_id}"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                user_data = result["data"]
                return {
                    "success": True,
                    "user_info": {
                        "id": user_data["id"],
                        "username": user_data["username"],
                        "discriminator": user_data.get("discriminator"),
                        "global_name": user_data.get("global_name"),
                        "avatar": user_data.get("avatar"),
                        "bot": user_data.get("bot", False)
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            self.context.logger.error(f"Error getting user info: {e}")
            return {"success": False, "error": str(e)}
    
    async def add_reaction(self, bot_token: str, channel_id: str, 
                          message_id: str, emoji: str) -> Dict[str, Any]:
        """添加反应"""
        try:
            import urllib.parse
            encoded_emoji = urllib.parse.quote(emoji.encode('utf-8'))
            endpoint = f"channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me"
            result = await self._make_request(bot_token, "PUT", endpoint)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            self.context.logger.error(f"Error adding reaction: {e}")
            return {"success": False, "error": str(e)}
    
    async def on_discord_message(self, message_data: Dict[str, Any]):
        """Discord消息接收钩子"""
        try:
            self.context.logger.debug(f"Received Discord message: {message_data.get('id', 'unknown')}")
        except Exception as e:
            self.context.logger.error(f"Error handling Discord message: {e}")
    
    async def on_guild_member_add(self, member_data: Dict[str, Any]):
        """服务器成员加入钩子"""
        try:
            self.context.logger.debug(f"Member joined: {member_data.get('user', {}).get('username', 'unknown')}")
        except Exception as e:
            self.context.logger.error(f"Error handling guild member add: {e}")
    
    async def on_reaction_add(self, reaction_data: Dict[str, Any]):
        """反应添加钩子"""
        try:
            self.context.logger.debug(f"Reaction added: {reaction_data.get('emoji', {}).get('name', 'unknown')}")
        except Exception as e:
            self.context.logger.error(f"Error handling reaction add: {e}")
    
    async def handle_status_command(self, args: str) -> str:
        """处理状态命令"""
        try:
            status_info = {
                'plugin_id': self.plugin_id,
                'status': self.status.value,
                'message_count': self.message_count,
                'last_message_time': self.last_message_time.isoformat() if self.last_message_time else None,
                'active_sessions': len(self._sessions),
                'cached_guilds': len(self._guild_cache),
                'tools': len(self.get_tools()),
                'hooks': sum(len(hooks) for hooks in self.get_hooks().values()),
                'commands': len(self.get_commands())
            }
            
            return f"Discord插件状态:\n{json.dumps(status_info, indent=2, ensure_ascii=False)}"
        except Exception as e:
            return f"获取状态失败: {str(e)}"
    
    async def handle_servers_command(self, args: str) -> str:
        """处理服务器列表命令"""
        try:
            if not self._guild_cache:
                return "暂无缓存的服务器信息"
            
            guild_list = []
            for guild_id, guild_data in self._guild_cache.items():
                guild_list.append(f"- {guild_data.get('name', 'Unknown')} ({guild_id})")
            
            return f"已缓存的服务器:\n" + "\n".join(guild_list)
        except Exception as e:
            return f"获取服务器列表失败: {str(e)}"
    
    async def deactivate(self):
        """停用插件时的清理"""
        try:
            for session in self._sessions.values():
                await session.close()
            self._sessions.clear()
            self._guild_cache.clear()
            await super().deactivate()
        except Exception as e:
            self.context.logger.error(f"Error during Discord plugin cleanup: {e}")