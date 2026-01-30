"""
Discord Skill for AgentBus

Migrated from Moltbot Discord Actions skill definition.
Provides Discord bot integration for message management, reactions, threads, polls, and moderation.

Features:
- Message management (send, edit, delete, fetch)
- Reaction management (add, list reactions)
- Thread management (create, reply, list)
- Poll creation and management
- Sticker and emoji handling
- Channel and permission management
- Member and role information
- Media upload support
- Moderation tools

Usage:
    # Send message
    skill.send_message(channel_id="123", content="Hello from AgentBus")
    
    # Add reaction
    skill.add_reaction(channel_id="123", message_id="456", emoji="✅")
    
    # Create poll
    skill.create_poll(channel_id="123", question="Lunch?", answers=["Pizza", "Sushi", "Salad"])
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import aiohttp
from urllib.parse import urljoin

from ..plugins.core import AgentBusPlugin, PluginContext


class DiscordSkill(AgentBusPlugin):
    """
    Discord Skill - Provides Discord bot integration
    
    Implements Moltbot's Discord Actions functionality with support for
    message management, reactions, threads, polls, and moderation tools.
    """
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        self._sessions = {}
        self._guild_cache = {}
        self.message_count = 0
        self.action_history = []
        
        # Action gating configuration
        self.action_groups = {
            'reactions': True,
            'stickers': True, 
            'polls': True,
            'permissions': True,
            'messages': True,
            'threads': True,
            'pins': True,
            'search': True,
            'emojiUploads': True,
            'stickerUploads': True,
            'memberInfo': True,
            'roleInfo': True,
            'channelInfo': True,
            'voiceStatus': True,
            'events': True,
            'roles': False,  # Disabled by default
            'channels': False,  # Disabled by default
            'moderation': False  # Disabled by default
        }
        
    def get_info(self) -> Dict[str, Any]:
        """Return plugin information"""
        return {
            'id': self.plugin_id,
            'name': 'Discord Skill',
            'version': '1.0.0',
            'description': 'Discord bot integration for message management, reactions, threads, polls, and moderation',
            'author': 'AgentBus Team',
            'dependencies': ['aiohttp'],
            'capabilities': [
                'message_management',
                'reaction_management',
                'thread_management', 
                'poll_management',
                'sticker_emoji_handling',
                'channel_management',
                'member_info',
                'moderation'
            ],
            'action_groups': list(self.action_groups.keys())
        }
    
    async def activate(self):
        """Activate plugin and register tools"""
        await super().activate()
        
        # Register Discord tools
        self.register_tool('send_message', 'Send Discord message', self.send_message)
        self.register_tool('edit_message', 'Edit Discord message', self.edit_message)
        self.register_tool('delete_message', 'Delete Discord message', self.delete_message)
        self.register_tool('fetch_message', 'Fetch Discord message', self.fetch_message)
        self.register_tool('read_messages', 'Read recent messages', self.read_messages)
        self.register_tool('add_reaction', 'Add reaction to message', self.add_reaction)
        self.register_tool('list_reactions', 'List message reactions', self.list_reactions)
        self.register_tool('create_thread', 'Create thread', self.create_thread)
        self.register_tool('thread_reply', 'Reply in thread', self.thread_reply)
        self.register_tool('list_threads', 'List guild threads', self.list_threads)
        self.register_tool('pin_message', 'Pin message', self.pin_message)
        self.register_tool('unpin_message', 'Unpin message', self.unpin_message)
        self.register_tool('list_pins', 'List pinned messages', self.list_pins)
        self.register_tool('create_poll', 'Create poll', self.create_poll)
        self.register_tool('send_sticker', 'Send sticker', self.send_sticker)
        self.register_tool('upload_emoji', 'Upload custom emoji', self.upload_emoji)
        self.register_tool('upload_sticker', 'Upload sticker', self.upload_sticker)
        self.register_tool('search_messages', 'Search messages', self.search_messages)
        self.register_tool('get_member_info', 'Get member info', self.get_member_info)
        self.register_tool('get_role_info', 'Get role info', self.get_role_info)
        self.register_tool('list_emojis', 'List custom emojis', self.list_emojis)
        self.register_tool('check_permissions', 'Check channel permissions', self.check_permissions)
        self.register_tool('get_channel_info', 'Get channel info', self.get_channel_info)
        self.register_tool('list_channels', 'List guild channels', self.list_channels)
        self.register_tool('create_channel', 'Create channel', self.create_channel)
        self.register_tool('create_category', 'Create category', self.create_category)
        self.register_tool('edit_channel', 'Edit channel', self.edit_channel)
        self.register_tool('move_channel', 'Move channel', self.move_channel)
        self.register_tool('delete_channel', 'Delete channel', self.delete_channel)
        self.register_tool('get_voice_status', 'Get voice status', self.get_voice_status)
        self.register_tool('list_events', 'List scheduled events', self.list_events)
        self.register_tool('timeout_user', 'Timeout user', self.timeout_user)
        
        # Register commands
        self.register_command('/discord_status', self.handle_status_command, 'Show Discord skill status')
        self.register_command('/discord_actions', self.handle_actions_command, 'Show action groups status')
        self.register_command('/discord_channels', self.handle_channels_command, 'List guild channels')
        
        self.context.logger.info(f"Discord skill {self.plugin_id} activated")
    
    def _is_action_enabled(self, action_group: str) -> bool:
        """Check if action group is enabled"""
        return self.action_groups.get(action_group, False)
    
    def _get_api_url(self, bot_token: str, endpoint: str) -> str:
        """Get Discord API URL"""
        return urljoin("https://discord.com/api/v10/", endpoint)
    
    async def _make_request(self, bot_token: str, method: str, endpoint: str, 
                           data: Dict[str, Any] = None, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Make Discord API request"""
        if headers is None:
            headers = {}
        
        headers.update({
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json"
        })
        
        # Get or create session
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
                    return {"success": False, "error": result.get("message", "Unknown error"), "status": response.status}
                    
        except aiohttp.ClientError as e:
            return {"success": False, "error": str(e)}
    
    async def send_message(self, bot_token: str, channel_id: str, content: str, 
                          media_url: str = None, reply_to: str = None) -> Dict[str, Any]:
        """Send Discord message"""
        if not self._is_action_enabled('messages'):
            return {"success": False, "error": "Message actions are disabled"}
        
        try:
            data = {"content": content}
            
            if reply_to:
                data["message_reference"] = {"message_id": reply_to}
            
            if media_url:
                # Handle media upload
                return await self._send_media_message(bot_token, channel_id, content, media_url, reply_to)
            
            endpoint = f"channels/{channel_id}/messages"
            result = await self._make_request(bot_token, "POST", endpoint, data)
            
            if result["success"]:
                self.message_count += 1
                self.action_history.append({
                    'action': 'send_message',
                    'timestamp': datetime.now(),
                    'channel_id': channel_id,
                    'success': True
                })
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
    
    async def _send_media_message(self, bot_token: str, channel_id: str, content: str, 
                                 media_url: str, reply_to: str = None) -> Dict[str, Any]:
        """Send media message"""
        try:
            files = {}
            filename = media_url.split("/")[-1]
            
            # For remote URLs, we need to download first
            if media_url.startswith('http'):
                async with aiohttp.ClientSession() as session:
                    async with session.get(media_url) as response:
                        if response.status == 200:
                            files['file'] = (filename, await response.read())
                        else:
                            return {"success": False, "error": f"Failed to download media: {response.status}"}
            else:
                # Local file
                with open(media_url, 'rb') as f:
                    files['file'] = (filename, f.read())
            
            data = {'content': content} if content else {}
            
            if reply_to:
                data["message_reference"] = {"message_id": reply_to}
            
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
    
    async def edit_message(self, bot_token: str, channel_id: str, message_id: str, 
                          content: str) -> Dict[str, Any]:
        """Edit Discord message"""
        if not self._is_action_enabled('messages'):
            return {"success": False, "error": "Message actions are disabled"}
        
        try:
            data = {"content": content}
            endpoint = f"channels/{channel_id}/messages/{message_id}"
            result = await self._make_request(bot_token, "PATCH", endpoint, data)
            
            if result["success"]:
                self.action_history.append({
                    'action': 'edit_message',
                    'timestamp': datetime.now(),
                    'channel_id': channel_id,
                    'message_id': message_id,
                    'success': True
                })
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def delete_message(self, bot_token: str, channel_id: str, message_id: str) -> Dict[str, Any]:
        """Delete Discord message"""
        if not self._is_action_enabled('messages'):
            return {"success": False, "error": "Message actions are disabled"}
        
        try:
            endpoint = f"channels/{channel_id}/messages/{message_id}"
            result = await self._make_request(bot_token, "DELETE", endpoint)
            
            if result["success"]:
                self.action_history.append({
                    'action': 'delete_message',
                    'timestamp': datetime.now(),
                    'channel_id': channel_id,
                    'message_id': message_id,
                    'success': True
                })
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def fetch_message(self, bot_token: str, guild_id: str = None, channel_id: str = None, 
                          message_id: str = None, message_link: str = None) -> Dict[str, Any]:
        """Fetch single Discord message"""
        if not self._is_action_enabled('messages'):
            return {"success": False, "error": "Message actions are disabled"}
        
        try:
            if message_link:
                # Parse message link: https://discord.com/channels/<guild_id>/<channel_id>/<message_id>
                parts = message_link.split('/')
                if len(parts) >= 2:
                    guild_id = parts[-3]
                    channel_id = parts[-2]
                    message_id = parts[-1]
            
            if not all([guild_id, channel_id, message_id]):
                return {"success": False, "error": "Missing required parameters"}
            
            endpoint = f"channels/{channel_id}/messages/{message_id}"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                message_data = result["data"]
                return {
                    "success": True,
                    "message": {
                        "id": message_data["id"],
                        "content": message_data.get("content", ""),
                        "author": message_data.get("author", {}),
                        "timestamp": message_data["timestamp"],
                        "channel_id": channel_id,
                        "guild_id": guild_id
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def read_messages(self, bot_token: str, channel_id: str, limit: int = 20) -> Dict[str, Any]:
        """Read recent Discord messages"""
        if not self._is_action_enabled('messages'):
            return {"success": False, "error": "Message actions are disabled"}
        
        try:
            endpoint = f"channels/{channel_id}/messages?limit={limit}"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                messages = result["data"]
                return {
                    "success": True,
                    "channel_id": channel_id,
                    "messages": messages,
                    "count": len(messages)
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def add_reaction(self, bot_token: str, channel_id: str, message_id: str, emoji: str) -> Dict[str, Any]:
        """Add reaction to Discord message"""
        if not self._is_action_enabled('reactions'):
            return {"success": False, "error": "Reaction actions are disabled"}
        
        try:
            import urllib.parse
            encoded_emoji = urllib.parse.quote(emoji.encode('utf-8'))
            endpoint = f"channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me"
            result = await self._make_request(bot_token, "PUT", endpoint)
            
            if result["success"]:
                self.action_history.append({
                    'action': 'add_reaction',
                    'timestamp': datetime.now(),
                    'channel_id': channel_id,
                    'message_id': message_id,
                    'emoji': emoji,
                    'success': True
                })
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def list_reactions(self, bot_token: str, channel_id: str, message_id: str, 
                           limit: int = 100) -> Dict[str, Any]:
        """List reactions on Discord message"""
        if not self._is_action_enabled('reactions'):
            return {"success": False, "error": "Reaction actions are disabled"}
        
        try:
            endpoint = f"channels/{channel_id}/messages/{message_id}/reactions?limit={limit}"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                reactions = result["data"]
                return {
                    "success": True,
                    "channel_id": channel_id,
                    "message_id": message_id,
                    "reactions": reactions,
                    "count": len(reactions)
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_thread(self, bot_token: str, channel_id: str, name: str, 
                          message_id: str = None) -> Dict[str, Any]:
        """Create Discord thread"""
        if not self._is_action_enabled('threads'):
            return {"success": False, "error": "Thread actions are disabled"}
        
        try:
            data = {"name": name}
            if message_id:
                data["message_id"] = message_id
            
            endpoint = f"channels/{channel_id}/threads"
            result = await self._make_request(bot_token, "POST", endpoint, data)
            
            if result["success"]:
                thread_data = result["data"]
                return {
                    "success": True,
                    "thread": {
                        "id": thread_data["id"],
                        "name": thread_data["name"],
                        "channel_id": channel_id
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def thread_reply(self, bot_token: str, channel_id: str, content: str) -> Dict[str, Any]:
        """Reply in Discord thread"""
        if not self._is_action_enabled('threads'):
            return {"success": False, "error": "Thread actions are disabled"}
        
        try:
            data = {"content": content}
            endpoint = f"channels/{channel_id}/messages"
            result = await self._make_request(bot_token, "POST", endpoint, data)
            
            if result["success"]:
                return {
                    "success": True,
                    "message_id": result["data"]["id"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def list_threads(self, bot_token: str, guild_id: str) -> Dict[str, Any]:
        """List guild threads"""
        if not self._is_action_enabled('threads'):
            return {"success": False, "error": "Thread actions are disabled"}
        
        try:
            endpoint = f"guilds/{guild_id}/threads"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                threads = result["data"]
                return {
                    "success": True,
                    "guild_id": guild_id,
                    "threads": threads,
                    "count": len(threads)
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def pin_message(self, bot_token: str, channel_id: str, message_id: str) -> Dict[str, Any]:
        """Pin Discord message"""
        if not self._is_action_enabled('pins'):
            return {"success": False, "error": "Pin actions are disabled"}
        
        try:
            endpoint = f"channels/{channel_id}/pins/{message_id}"
            result = await self._make_request(bot_token, "PUT", endpoint)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def unpin_message(self, bot_token: str, channel_id: str, message_id: str) -> Dict[str, Any]:
        """Unpin Discord message"""
        if not self._is_action_enabled('pins'):
            return {"success": False, "error": "Pin actions are disabled"}
        
        try:
            endpoint = f"channels/{channel_id}/pins/{message_id}"
            result = await self._make_request(bot_token, "DELETE", endpoint)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def list_pins(self, bot_token: str, channel_id: str) -> Dict[str, Any]:
        """List pinned Discord messages"""
        if not self._is_action_enabled('pins'):
            return {"success": False, "error": "Pin actions are disabled"}
        
        try:
            endpoint = f"channels/{channel_id}/pins"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                pins = result["data"]
                return {
                    "success": True,
                    "channel_id": channel_id,
                    "pins": pins,
                    "count": len(pins)
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_poll(self, bot_token: str, channel_id: str, question: str, 
                         answers: List[str], allow_multiselect: bool = False,
                         duration_hours: int = 24, content: str = None) -> Dict[str, Any]:
        """Create Discord poll"""
        if not self._is_action_enabled('polls'):
            return {"success": False, "error": "Poll actions are disabled"}
        
        try:
            if not 2 <= len(answers) <= 10:
                return {"success": False, "error": "Poll must have 2-10 answers"}
            
            if not 1 <= duration_hours <= 768:  # Max 32 days
                return {"success": False, "error": "Duration must be between 1 and 768 hours"}
            
            data = {
                "name": question,
                "duration": duration_hours * 60,  # Convert to minutes
                "allow_multiselect": allow_multiselect,
                "answers": [{"answer_text": answer} for answer in answers]
            }
            
            if content:
                data["explain_message"] = {"content": content}
            
            endpoint = f"channels/{channel_id}/messages"
            result = await self._make_request(bot_token, "POST", endpoint, data)
            
            if result["success"]:
                self.action_history.append({
                    'action': 'create_poll',
                    'timestamp': datetime.now(),
                    'channel_id': channel_id,
                    'question': question,
                    'answers_count': len(answers),
                    'success': True
                })
                return {
                    "success": True,
                    "message_id": result["data"]["id"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_sticker(self, bot_token: str, to: str, sticker_ids: List[str], 
                          content: str = None) -> Dict[str, Any]:
        """Send Discord sticker"""
        if not self._is_action_enabled('stickers'):
            return {"success": False, "error": "Sticker actions are disabled"}
        
        try:
            if len(sticker_ids) > 3:
                return {"success": False, "error": "Maximum 3 stickers per message"}
            
            data = {"sticker_ids": sticker_ids}
            if content:
                data["content"] = content
            
            endpoint = f"channels/{to.split(':')[1]}/messages"
            result = await self._make_request(bot_token, "POST", endpoint, data)
            
            if result["success"]:
                return {
                    "success": True,
                    "message_id": result["data"]["id"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def upload_emoji(self, bot_token: str, guild_id: str, name: str, 
                          media_url: str, role_ids: List[str] = None) -> Dict[str, Any]:
        """Upload custom Discord emoji"""
        if not self._is_action_enabled('emojiUploads'):
            return {"success": False, "error": "Emoji upload actions are disabled"}
        
        try:
            # Download emoji image
            async with aiohttp.ClientSession() as session:
                async with session.get(media_url) as response:
                    if response.status != 200:
                        return {"success": False, "error": "Failed to download emoji image"}
                    
                    image_data = await response.read()
                    
                    # Check size (256KB limit)
                    if len(image_data) > 256 * 1024:
                        return {"success": False, "error": "Emoji image must be <= 256KB"}
                    
                    # Prepare data
                    data = {
                        "name": name,
                        "image": image_data
                    }
                    if role_ids:
                        data["roles"] = role_ids
                    
                    # Create emoji
                    endpoint = f"guilds/{guild_id}/emojis"
                    headers = {"Authorization": f"Bot {bot_token}"}
                    
                    if bot_token not in self._sessions:
                        self._sessions[bot_token] = aiohttp.ClientSession()
                    
                    session = self._sessions[bot_token]
                    url = self._get_api_url(bot_token, endpoint)
                    
                    async with session.post(url, data=data, headers=headers) as response:
                        result = await response.json()
                        
                        if response.status == 201:
                            return {
                                "success": True,
                                "emoji": {
                                    "id": result["id"],
                                    "name": result["name"]
                                }
                            }
                        else:
                            return {"success": False, "error": result.get("message", "Upload failed")}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def upload_sticker(self, bot_token: str, guild_id: str, name: str, description: str,
                           tags: str, media_url: str) -> Dict[str, Any]:
        """Upload Discord sticker"""
        if not self._is_action_enabled('stickerUploads'):
            return {"success": False, "error": "Sticker upload actions are disabled"}
        
        try:
            # Download sticker image
            async with aiohttp.ClientSession() as session:
                async with session.get(media_url) as response:
                    if response.status != 200:
                        return {"success": False, "error": "Failed to download sticker image"}
                    
                    image_data = await response.read()
                    
                    # Check size (512KB limit)
                    if len(image_data) > 512 * 1024:
                        return {"success": False, "error": "Sticker image must be <= 512KB"}
                    
                    # Prepare data
                    data = {
                        "name": name,
                        "description": description,
                        "tags": tags,
                        "file": image_data
                    }
                    
                    # Create sticker
                    endpoint = f"guilds/{guild_id}/stickers"
                    headers = {"Authorization": f"Bot {bot_token}"}
                    
                    if bot_token not in self._sessions:
                        self._sessions[bot_token] = aiohttp.ClientSession()
                    
                    session = self._sessions[bot_token]
                    url = self._get_api_url(bot_token, endpoint)
                    
                    async with session.post(url, data=data, headers=headers) as response:
                        result = await response.json()
                        
                        if response.status == 201:
                            return {
                                "success": True,
                                "sticker": {
                                    "id": result["id"],
                                    "name": result["name"],
                                    "description": result["description"]
                                }
                            }
                        else:
                            return {"success": False, "error": result.get("message", "Upload failed")}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def search_messages(self, bot_token: str, guild_id: str, content: str,
                            channel_ids: List[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Search Discord messages"""
        if not self._is_action_enabled('search'):
            return {"success": False, "error": "Search actions are disabled"}
        
        try:
            data = {
                "content": content,
                "limit": limit
            }
            if channel_ids:
                data["channel_id"] = channel_ids
            
            endpoint = f"guilds/{guild_id}/messages/search"
            result = await self._make_request(bot_token, "GET", endpoint, data)
            
            if result["success"]:
                messages = result["data"]["messages"]
                return {
                    "success": True,
                    "guild_id": guild_id,
                    "query": content,
                    "messages": messages,
                    "count": len(messages)
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_member_info(self, bot_token: str, guild_id: str, user_id: str) -> Dict[str, Any]:
        """Get Discord member info"""
        if not self._is_action_enabled('memberInfo'):
            return {"success": False, "error": "Member info actions are disabled"}
        
        try:
            endpoint = f"guilds/{guild_id}/members/{user_id}"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                member_data = result["data"]
                return {
                    "success": True,
                    "member": {
                        "user": member_data.get("user", {}),
                        "nick": member_data.get("nick"),
                        "roles": member_data.get("roles", []),
                        "joined_at": member_data.get("joined_at"),
                        "premium_since": member_data.get("premium_since"),
                        "pending": member_data.get("pending", False)
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_role_info(self, bot_token: str, guild_id: str) -> Dict[str, Any]:
        """Get Discord role info"""
        if not self._is_action_enabled('roleInfo'):
            return {"success": False, "error": "Role info actions are disabled"}
        
        try:
            endpoint = f"guilds/{guild_id}/roles"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                roles = result["data"]
                return {
                    "success": True,
                    "guild_id": guild_id,
                    "roles": roles,
                    "count": len(roles)
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def list_emojis(self, bot_token: str, guild_id: str) -> Dict[str, Any]:
        """List Discord custom emojis"""
        if not self._is_action_enabled('emojiUploads'):
            return {"success": False, "error": "Emoji actions are disabled"}
        
        try:
            endpoint = f"guilds/{guild_id}/emojis"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                emojis = result["data"]
                return {
                    "success": True,
                    "guild_id": guild_id,
                    "emojis": emojis,
                    "count": len(emojis)
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def check_permissions(self, bot_token: str, channel_id: str) -> Dict[str, Any]:
        """Check Discord bot permissions for channel"""
        if not self._is_action_enabled('permissions'):
            return {"success": False, "error": "Permission check actions are disabled"}
        
        try:
            endpoint = f"channels/{channel_id}/permissions"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                permissions = result["data"]
                return {
                    "success": True,
                    "channel_id": channel_id,
                    "permissions": permissions
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_channel_info(self, bot_token: str, channel_id: str) -> Dict[str, Any]:
        """Get Discord channel info"""
        if not self._is_action_enabled('channelInfo'):
            return {"success": False, "error": "Channel info actions are disabled"}
        
        try:
            endpoint = f"channels/{channel_id}"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                channel_data = result["data"]
                return {
                    "success": True,
                    "channel": {
                        "id": channel_data["id"],
                        "name": channel_data.get("name"),
                        "type": channel_data["type"],
                        "topic": channel_data.get("topic"),
                        "parent_id": channel_data.get("parent_id"),
                        "position": channel_data.get("position"),
                        "nsfw": channel_data.get("nsfw", False)
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def list_channels(self, bot_token: str, guild_id: str) -> Dict[str, Any]:
        """List Discord guild channels"""
        if not self._is_action_enabled('channelInfo'):
            return {"success": False, "error": "Channel info actions are disabled"}
        
        try:
            endpoint = f"guilds/{guild_id}/channels"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                channels = result["data"]
                return {
                    "success": True,
                    "guild_id": guild_id,
                    "channels": channels,
                    "count": len(channels)
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_channel(self, bot_token: str, guild_id: str, name: str, 
                           channel_type: int = 0, parent_id: str = None, 
                           topic: str = None) -> Dict[str, Any]:
        """Create Discord channel"""
        if not self._is_action_enabled('channels'):
            return {"success": False, "error": "Channel management actions are disabled"}
        
        try:
            data = {
                "name": name,
                "type": channel_type
            }
            if parent_id:
                data["parent_id"] = parent_id
            if topic:
                data["topic"] = topic
            
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
            return {"success": False, "error": str(e)}
    
    async def create_category(self, bot_token: str, guild_id: str, name: str) -> Dict[str, Any]:
        """Create Discord category"""
        return await self.create_channel(bot_token, guild_id, name, channel_type=4)
    
    async def edit_channel(self, bot_token: str, channel_id: str, **kwargs) -> Dict[str, Any]:
        """Edit Discord channel"""
        if not self._is_action_enabled('channels'):
            return {"success": False, "error": "Channel management actions are disabled"}
        
        try:
            allowed_fields = ["name", "topic", "position", "parent_id", "nsfw", "rate_limit_per_user"]
            data = {k: v for k, v in kwargs.items() if k in allowed_fields}
            
            endpoint = f"channels/{channel_id}"
            result = await self._make_request(bot_token, "PATCH", endpoint, data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def move_channel(self, bot_token: str, guild_id: str, channel_id: str, 
                          parent_id: str = None, position: int = None) -> Dict[str, Any]:
        """Move Discord channel"""
        if not self._is_action_enabled('channels'):
            return {"success": False, "error": "Channel management actions are disabled"}
        
        try:
            data = {}
            if parent_id is not None:
                data["parent_id"] = parent_id
            if position is not None:
                data["position"] = position
            
            endpoint = f"guilds/{guild_id}/channels/{channel_id}"
            result = await self._make_request(bot_token, "PATCH", endpoint, data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def delete_channel(self, bot_token: str, channel_id: str) -> Dict[str, Any]:
        """Delete Discord channel"""
        if not self._is_action_enabled('channels'):
            return {"success": False, "error": "Channel management actions are disabled"}
        
        try:
            endpoint = f"channels/{channel_id}"
            result = await self._make_request(bot_token, "DELETE", endpoint)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_voice_status(self, bot_token: str, guild_id: str, user_id: str) -> Dict[str, Any]:
        """Get Discord voice status"""
        if not self._is_action_enabled('voiceStatus'):
            return {"success": False, "error": "Voice status actions are disabled"}
        
        try:
            endpoint = f"guilds/{guild_id}/members/{user_id}"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                member_data = result["data"]
                voice_state = member_data.get("voice_state", {})
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "voice_state": {
                        "channel_id": voice_state.get("channel_id"),
                        "self_mute": voice_state.get("self_mute", False),
                        "self_deaf": voice_state.get("self_deaf", False),
                        "mute": voice_state.get("mute", False),
                        "deaf": voice_state.get("deaf", False)
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def list_events(self, bot_token: str, guild_id: str) -> Dict[str, Any]:
        """List Discord scheduled events"""
        if not self._is_action_enabled('events'):
            return {"success": False, "error": "Event actions are disabled"}
        
        try:
            endpoint = f"guilds/{guild_id}/scheduled-events"
            result = await self._make_request(bot_token, "GET", endpoint)
            
            if result["success"]:
                events = result["data"]
                return {
                    "success": True,
                    "guild_id": guild_id,
                    "events": events,
                    "count": len(events)
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def timeout_user(self, bot_token: str, guild_id: str, user_id: str, 
                          duration_minutes: int) -> Dict[str, Any]:
        """Timeout Discord user"""
        if not self._is_action_enabled('moderation'):
            return {"success": False, "error": "Moderation actions are disabled"}
        
        try:
            data = {"communication_disabled_until": duration_minutes * 60}
            endpoint = f"guilds/{guild_id}/members/{user_id}"
            result = await self._make_request(bot_token, "PATCH", endpoint, data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_status_command(self, args: str) -> str:
        """Handle Discord status command"""
        try:
            status_info = {
                'skill_id': self.plugin_id,
                'message_count': self.message_count,
                'action_history_count': len(self.action_history),
                'active_sessions': len(self._sessions),
                'cached_guilds': len(self._guild_cache),
                'action_groups': self.action_groups
            }
            
            return f"Discord Skill Status:\n{json.dumps(status_info, indent=2, ensure_ascii=False)}"
        except Exception as e:
            return f"获取Discord状态失败: {str(e)}"
    
    async def handle_actions_command(self, args: str) -> str:
        """Handle action groups status command"""
        try:
            enabled_actions = [k for k, v in self.action_groups.items() if v]
            disabled_actions = [k for k, v in self.action_groups.items() if not v]
            
            result = f"Discord Action Groups Status:\n\n"
            result += f"Enabled ({len(enabled_actions)}):\n"
            for action in enabled_actions:
                result += f"  ✅ {action}\n"
            
            result += f"\nDisabled ({len(disabled_actions)}):\n"
            for action in disabled_actions:
                result += f"  ❌ {action}\n"
            
            return result
        except Exception as e:
            return f"获取动作组状态失败: {str(e)}"
    
    async def handle_channels_command(self, args: str) -> str:
        """Handle channels list command"""
        try:
            if not self._guild_cache:
                return "暂无缓存的服务器信息，请先使用具体功能获取频道列表"
            
            result = f"缓存的服务器频道:\n"
            for guild_id, channels in self._guild_cache.items():
                result += f"\n服务器 {guild_id}:\n"
                for channel in channels[:5]:  # Limit to first 5
                    result += f"  - {channel.get('name', 'Unknown')} (ID: {channel.get('id')})\n"
                if len(channels) > 5:
                    result += f"  ... 还有 {len(channels) - 5} 个频道\n"
            
            return result
        except Exception as e:
            return f"获取频道列表失败: {str(e)}"
    
    async def deactivate(self):
        """Cleanup when deactivating"""
        try:
            for session in self._sessions.values():
                await session.close()
            self._sessions.clear()
            self._guild_cache.clear()
            self.action_history.clear()
            await super().deactivate()
        except Exception as e:
            self.context.logger.error(f"Error during Discord skill cleanup: {e}")