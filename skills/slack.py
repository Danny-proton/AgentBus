"""
Slack Skill for AgentBus

Migrated from Moltbot Slack Actions skill definition.
Provides Slack bot integration for message management, reactions, pins, and member info.

Features:
- Message management (send, edit, delete, fetch)
- Reaction management (add, list reactions)
- Pin management (pin, unpin, list pins)
- Member information
- Custom emoji listing
- Channel management

Usage:
    # Send message
    skill.send_message(channel_id="C123", content="Hello from AgentBus")
    
    # Add reaction
    skill.add_reaction(channel_id="C123", message_id="1712023032.1234", emoji="✅")
    
    # Pin message
    skill.pin_message(channel_id="C123", message_id="1712023032.1234")
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
from urllib.parse import urljoin

from ..plugins.core import AgentBusPlugin, PluginContext


class SlackSkill(AgentBusPlugin):
    """
    Slack Skill - Provides Slack bot integration
    
    Implements Moltbot's Slack Actions functionality with support for
    message management, reactions, pins, and member information.
    """
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        self._tokens = {}
        self.message_count = 0
        self.action_history = []
        
        # Action groups configuration
        self.action_groups = {
            'reactions': True,      # React + list reactions
            'messages': True,       # Read/send/edit/delete
            'pins': True,          # Pin/unpin/list
            'memberInfo': True,    # Member info
            'emojiList': True      # Custom emoji list
        }
        
    def get_info(self) -> Dict[str, Any]:
        """Return plugin information"""
        return {
            'id': self.plugin_id,
            'name': 'Slack Skill',
            'version': '1.0.0',
            'description': 'Slack bot integration for message management, reactions, pins, and member info',
            'author': 'AgentBus Team',
            'dependencies': ['requests'],
            'capabilities': [
                'message_management',
                'reaction_management',
                'pin_management',
                'member_info',
                'emoji_listing'
            ],
            'action_groups': list(self.action_groups.keys())
        }
    
    async def activate(self):
        """Activate plugin and register tools"""
        await super().activate()
        
        # Register Slack tools
        self.register_tool('send_message', 'Send Slack message', self.send_message)
        self.register_tool('edit_message', 'Edit Slack message', self.edit_message)
        self.register_tool('delete_message', 'Delete Slack message', self.delete_message)
        self.register_tool('read_messages', 'Read recent messages', self.read_messages)
        self.register_tool('add_reaction', 'Add reaction to message', self.add_reaction)
        self.register_tool('list_reactions', 'List message reactions', self.list_reactions)
        self.register_tool('pin_message', 'Pin message', self.pin_message)
        self.register_tool('unpin_message', 'Unpin message', self.unpin_message)
        self.register_tool('list_pins', 'List pinned items', self.list_pins)
        self.register_tool('get_member_info', 'Get member information', self.get_member_info)
        self.register_tool('list_emojis', 'List custom emojis', self.list_emojis)
        self.register_tool('get_channel_info', 'Get channel information', self.get_channel_info)
        self.register_tool('upload_file', 'Upload file to Slack', self.upload_file)
        self.register_tool('schedule_message', 'Schedule message', self.schedule_message)
        self.register_tool('get_user_presence', 'Get user presence', self.get_user_presence)
        self.register_tool('open_im', 'Open direct message', self.open_im)
        self.register_tool('create_channel', 'Create channel', self.create_channel)
        self.register_tool('invite_to_channel', 'Invite user to channel', self.invite_to_channel)
        self.register_tool('leave_channel', 'Leave channel', self.leave_channel)
        self.register_tool('archive_channel', 'Archive channel', self.archive_channel)
        
        # Register commands
        self.register_command('/slack_status', self.handle_status_command, 'Show Slack skill status')
        self.register_command('/slack_actions', self.handle_actions_command, 'Show action groups status')
        self.register_command('/slack_channels', self.handle_channels_command, 'List accessible channels')
        
        self.context.logger.info(f"Slack skill {self.plugin_id} activated")
    
    def _is_action_enabled(self, action_group: str) -> bool:
        """Check if action group is enabled"""
        return self.action_groups.get(action_group, False)
    
    def _get_api_url(self, token: str, endpoint: str) -> str:
        """Get Slack API URL"""
        return urljoin("https://slack.com/api/", endpoint)
    
    def _make_request(self, token: str, method: str, endpoint: str, 
                     data: Dict[str, Any] = None, files: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make Slack API request"""
        url = self._get_api_url(token, endpoint)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=data, timeout=30)
            elif method == "POST":
                if files:
                    # Remove Content-Type for file uploads
                    headers.pop("Content-Type", None)
                    response = requests.post(url, headers=headers, data=data, files=files, timeout=30)
                else:
                    response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return {"success": False, "error": f"Unsupported HTTP method: {method}"}
            
            result = response.json()
            
            if result.get("ok"):
                return {"success": True, "data": result.get("data", result)}
            else:
                return {"success": False, "error": result.get("error", "Unknown error"), "detail": result}
                
        except requests.exceptions.RequestException as e:
            self.context.logger.error(f"Slack API request failed: {e}")
            return {"success": False, "error": str(e)}
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON response"}
    
    async def send_message(self, token: str, to: str, content: str, 
                          thread_ts: str = None, attachments: List[Dict[str, Any]] = None,
                          blocks: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send Slack message"""
        if not self._is_action_enabled('messages'):
            return {"success": False, "error": "Message actions are disabled"}
        
        try:
            data = {
                "channel": to,
                "text": content
            }
            
            if thread_ts:
                data["thread_ts"] = thread_ts
            
            if attachments:
                data["attachments"] = json.dumps(attachments)
            
            if blocks:
                data["blocks"] = json.dumps(blocks)
            
            result = self._make_request(token, "POST", "chat.postMessage", data)
            
            if result["success"]:
                self.message_count += 1
                self.action_history.append({
                    'action': 'send_message',
                    'timestamp': datetime.now(),
                    'channel': to,
                    'success': True
                })
                return {
                    "success": True,
                    "message_id": result["data"]["ts"],
                    "channel": result["data"]["channel"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            self.context.logger.error(f"Error sending message: {e}")
            return {"success": False, "error": str(e)}
    
    async def edit_message(self, token: str, channel: str, message_ts: str, 
                         content: str, attachments: List[Dict[str, Any]] = None,
                         blocks: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Edit Slack message"""
        if not self._is_action_enabled('messages'):
            return {"success": False, "error": "Message actions are disabled"}
        
        try:
            data = {
                "channel": channel,
                "ts": message_ts,
                "text": content
            }
            
            if attachments:
                data["attachments"] = json.dumps(attachments)
            
            if blocks:
                data["blocks"] = json.dumps(blocks)
            
            result = self._make_request(token, "POST", "chat.update", data)
            
            if result["success"]:
                return {
                    "success": True,
                    "message_id": result["data"]["ts"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def delete_message(self, token: str, channel: str, message_ts: str) -> Dict[str, Any]:
        """Delete Slack message"""
        if not self._is_action_enabled('messages'):
            return {"success": False, "error": "Message actions are disabled"}
        
        try:
            data = {
                "channel": channel,
                "ts": message_ts
            }
            
            result = self._make_request(token, "POST", "chat.delete", data)
            
            if result["success"]:
                self.action_history.append({
                    'action': 'delete_message',
                    'timestamp': datetime.now(),
                    'channel': channel,
                    'message_ts': message_ts,
                    'success': True
                })
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def read_messages(self, token: str, channel: str, limit: int = 20, 
                          oldest: str = None, latest: str = None) -> Dict[str, Any]:
        """Read recent Slack messages"""
        if not self._is_action_enabled('messages'):
            return {"success": False, "error": "Message actions are disabled"}
        
        try:
            data = {
                "channel": channel,
                "limit": limit
            }
            
            if oldest:
                data["oldest"] = oldest
            
            if latest:
                data["latest"] = latest
            
            result = self._make_request(token, "GET", "conversations.history", data)
            
            if result["success"]:
                messages = result["data"]["messages"]
                return {
                    "success": True,
                    "channel": channel,
                    "messages": messages,
                    "count": len(messages),
                    "has_more": result["data"].get("has_more", False)
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def add_reaction(self, token: str, channel: str, message_ts: str, emoji: str) -> Dict[str, Any]:
        """Add reaction to Slack message"""
        if not self._is_action_enabled('reactions'):
            return {"success": False, "error": "Reaction actions are disabled"}
        
        try:
            data = {
                "channel": channel,
                "timestamp": message_ts,
                "name": emoji
            }
            
            result = self._make_request(token, "POST", "reactions.add", data)
            
            if result["success"]:
                self.action_history.append({
                    'action': 'add_reaction',
                    'timestamp': datetime.now(),
                    'channel': channel,
                    'message_ts': message_ts,
                    'emoji': emoji,
                    'success': True
                })
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def list_reactions(self, token: str, channel: str, message_ts: str) -> Dict[str, Any]:
        """List reactions on Slack message"""
        if not self._is_action_enabled('reactions'):
            return {"success": False, "error": "Reaction actions are disabled"}
        
        try:
            data = {
                "channel": channel,
                "timestamp": message_ts
            }
            
            result = self._make_request(token, "GET", "reactions.get", data)
            
            if result["success"]:
                reactions = result["data"].get("message", {}).get("reactions", [])
                return {
                    "success": True,
                    "channel": channel,
                    "message_ts": message_ts,
                    "reactions": reactions,
                    "count": len(reactions)
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def pin_message(self, token: str, channel: str, message_ts: str) -> Dict[str, Any]:
        """Pin Slack message"""
        if not self._is_action_enabled('pins'):
            return {"success": False, "error": "Pin actions are disabled"}
        
        try:
            data = {
                "channel": channel,
                "timestamp": message_ts
            }
            
            result = self._make_request(token, "POST", "pins.add", data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def unpin_message(self, token: str, channel: str, message_ts: str) -> Dict[str, Any]:
        """Unpin Slack message"""
        if not self._is_action_enabled('pins'):
            return {"success": False, "error": "Pin actions are disabled"}
        
        try:
            data = {
                "channel": channel,
                "timestamp": message_ts
            }
            
            result = self._make_request(token, "POST", "pins.remove", data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def list_pins(self, token: str, channel: str) -> Dict[str, Any]:
        """List pinned Slack items"""
        if not self._is_action_enabled('pins'):
            return {"success": False, "error": "Pin actions are disabled"}
        
        try:
            data = {"channel": channel}
            result = self._make_request(token, "GET", "pins.list", data)
            
            if result["success"]:
                items = result["data"].get("items", [])
                return {
                    "success": True,
                    "channel": channel,
                    "items": items,
                    "count": len(items)
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_member_info(self, token: str, user_id: str) -> Dict[str, Any]:
        """Get Slack member information"""
        if not self._is_action_enabled('memberInfo'):
            return {"success": False, "error": "Member info actions are disabled"}
        
        try:
            data = {"user": user_id}
            result = self._make_request(token, "GET", "users.info", data)
            
            if result["success"]:
                user_info = result["data"]["user"]
                return {
                    "success": True,
                    "user_info": {
                        "id": user_info["id"],
                        "name": user_info["name"],
                        "real_name": user_info.get("real_name"),
                        "display_name": user_info.get("display_name"),
                        "email": user_info.get("profile", {}).get("email"),
                        "timezone": user_info.get("tz"),
                        "is_admin": user_info.get("is_admin", False),
                        "is_owner": user_info.get("is_owner", False),
                        "is_bot": user_info.get("is_bot", False),
                        "deleted": user_info.get("deleted", False)
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def list_emojis(self, token: str) -> Dict[str, Any]:
        """List custom Slack emojis"""
        if not self._is_action_enabled('emojiList'):
            return {"success": False, "error": "Emoji list actions are disabled"}
        
        try:
            result = self._make_request(token, "GET", "emoji.list")
            
            if result["success"]:
                emojis = result["data"].get("emoji", {})
                emoji_list = [{"name": name, "url": url} for name, url in emojis.items() if url]
                
                return {
                    "success": True,
                    "emojis": emoji_list,
                    "count": len(emoji_list)
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_channel_info(self, token: str, channel: str) -> Dict[str, Any]:
        """Get Slack channel information"""
        try:
            data = {"channel": channel}
            result = self._make_request(token, "GET", "conversations.info", data)
            
            if result["success"]:
                channel_info = result["data"]["channel"]
                return {
                    "success": True,
                    "channel_info": {
                        "id": channel_info["id"],
                        "name": channel_info["name"],
                        "is_channel": channel_info.get("is_channel", False),
                        "is_group": channel_info.get("is_group", False),
                        "is_im": channel_info.get("is_im", False),
                        "is_private": channel_info.get("is_private", False),
                        "is_archived": channel_info.get("is_archived", False),
                        "is_member": channel_info.get("is_member", False),
                        "member_count": channel_info.get("num_members", 0),
                        "purpose": channel_info.get("purpose", {}),
                        "topic": channel_info.get("topic", {})
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def upload_file(self, token: str, channels: List[str], file_path: str, 
                         title: str = None, comment: str = None) -> Dict[str, Any]:
        """Upload file to Slack"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {
                    "channels": ",".join(channels)
                }
                
                if title:
                    data["title"] = title
                
                if comment:
                    data["initial_comment"] = comment
            
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.post(
                "https://slack.com/api/files.upload",
                headers=headers,
                data=data,
                files=files,
                timeout=30
            )
            
            result = response.json()
            
            if result.get("ok"):
                return {
                    "success": True,
                    "file_id": result["file"]["id"],
                    "file_name": result["file"]["name"],
                    "file_url": result["file"]["url_private"]
                }
            else:
                return {"success": False, "error": result.get("error", "Upload failed")}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def schedule_message(self, token: str, channel: str, text: str, 
                              post_at: int, thread_ts: str = None) -> Dict[str, Any]:
        """Schedule Slack message"""
        try:
            data = {
                "channel": channel,
                "text": text,
                "post_at": post_at
            }
            
            if thread_ts:
                data["thread_ts"] = thread_ts
            
            result = self._make_request(token, "POST", "chat.scheduleMessage", data)
            
            if result["success"]:
                return {
                    "success": True,
                    "scheduled_message_id": result["data"]["scheduled_message_id"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_user_presence(self, token: str, user: str) -> Dict[str, Any]:
        """Get user presence"""
        try:
            data = {"user": user}
            result = self._make_request(token, "GET", "users.getPresence", data)
            
            if result["success"]:
                presence_info = result["data"]
                return {
                    "success": True,
                    "presence": {
                        "user": user,
                        "presence": presence_info.get("presence"),
                        "online": presence_info.get("online", False),
                        "auto_away": presence_info.get("auto_away", False),
                        "manual_away": presence_info.get("manual_away", False),
                        "connection_count": presence_info.get("connection_count", 0)
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def open_im(self, token: str, users: List[str]) -> Dict[str, Any]:
        """Open direct message"""
        try:
            data = {"users": ",".join(users)}
            result = self._make_request(token, "GET", "conversations.open", data)
            
            if result["success"]:
                channel_info = result["data"]["channel"]
                return {
                    "success": True,
                    "channel": {
                        "id": channel_info["id"],
                        "is_im": True,
                        "user": channel_info.get("user")
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def create_channel(self, token: str, name: str, is_private: bool = False) -> Dict[str, Any]:
        """Create channel"""
        try:
            data = {"name": name, "is_private": is_private}
            result = self._make_request(token, "POST", "conversations.create", data)
            
            if result["success"]:
                channel_info = result["data"]["channel"]
                return {
                    "success": True,
                    "channel": {
                        "id": channel_info["id"],
                        "name": channel_info["name"],
                        "is_private": channel_info.get("is_private", False)
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def invite_to_channel(self, token: str, channel: str, users: List[str]) -> Dict[str, Any]:
        """Invite user to channel"""
        try:
            data = {"channel": channel, "users": ",".join(users)}
            result = self._make_request(token, "POST", "conversations.invite", data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def leave_channel(self, token: str, channel: str) -> Dict[str, Any]:
        """Leave channel"""
        try:
            data = {"channel": channel}
            result = self._make_request(token, "POST", "conversations.leave", data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def archive_channel(self, token: str, channel: str) -> Dict[str, Any]:
        """Archive channel"""
        try:
            data = {"channel": channel}
            result = self._make_request(token, "POST", "conversations.archive", data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_status_command(self, args: str) -> str:
        """Handle Slack status command"""
        try:
            status_info = {
                'skill_id': self.plugin_id,
                'message_count': self.message_count,
                'active_tokens': len(self._tokens),
                'action_history_count': len(self.action_history),
                'action_groups': self.action_groups,
                'tools': len(self.get_tools()),
                'hooks': sum(len(hooks) for hooks in self.get_hooks().values()),
                'commands': len(self.get_commands())
            }
            
            return f"Slack Skill Status:\n{json.dumps(status_info, indent=2, ensure_ascii=False)}"
        except Exception as e:
            return f"获取Slack状态失败: {str(e)}"
    
    async def handle_actions_command(self, args: str) -> str:
        """Handle action groups status command"""
        try:
            enabled_actions = [k for k, v in self.action_groups.items() if v]
            disabled_actions = [k for k, v in self.action_groups.items() if not v]
            
            result = f"Slack Action Groups Status:\n\n"
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
            if not self._tokens:
                return "暂无配置的Slack令牌"
            
            result = f"可访问的频道:\n"
            
            # This would require token-specific implementation
            result += "(需要具体令牌来获取频道列表)\n"
            
            return result
        except Exception as e:
            return f"获取频道列表失败: {str(e)}"
    
    async def deactivate(self):
        """Cleanup when deactivating"""
        try:
            self._tokens.clear()
            self.action_history.clear()
            await super().deactivate()
        except Exception as e:
            self.context.logger.error(f"Error during Slack skill cleanup: {e}")