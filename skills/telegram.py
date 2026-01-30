"""
Telegram Skill for AgentBus

Migrated from Moltbot Telegram functionality.
Provides Telegram bot integration for messaging, media, polls, keyboards, and webhooks.

Features:
- Text and media message sending
- Message editing and deletion
- Poll creation and management
- Custom keyboards and inline keyboards
- Webhook management
- Chat and user information
- Message reactions
- File handling

Usage:
    # Send message
    skill.send_message(bot_token="...", chat_id="123", text="Hello from AgentBus")
    
    # Send media
    skill.send_media(bot_token="...", chat_id="123", media_type="photo", media_url="...")
    
    # Create poll
    skill.create_poll(bot_token="...", chat_id="123", question="Lunch?", options=["Pizza", "Sushi"])
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
from urllib.parse import urljoin

from ..plugins.core import AgentBusPlugin, PluginContext


class TelegramSkill(AgentBusPlugin):
    """
    Telegram Skill - Provides Telegram bot integration
    
    Implements Telegram bot functionality for messaging, media, polls,
    keyboards, and webhook management.
    """
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        self._bots = {}
        self.message_count = 0
        self.action_history = []
        
    def get_info(self) -> Dict[str, Any]:
        """Return plugin information"""
        return {
            'id': self.plugin_id,
            'name': 'Telegram Skill',
            'version': '1.0.0',
            'description': 'Telegram bot integration for messaging, media, polls, keyboards, and webhooks',
            'author': 'AgentBus Team',
            'dependencies': ['requests'],
            'capabilities': [
                'send_messages',
                'send_media',
                'send_polls',
                'handle_webhooks',
                'manage_chats',
                'custom_keyboards',
                'message_editing'
            ]
        }
    
    async def activate(self):
        """Activate plugin and register tools"""
        await super().activate()
        
        # Register Telegram tools
        self.register_tool('send_message', 'Send Telegram message', self.send_message)
        self.register_tool('send_media', 'Send media message', self.send_media)
        self.register_tool('send_poll', 'Send poll', self.send_poll)
        self.register_tool('send_keyboard', 'Send keyboard message', self.send_keyboard)
        self.register_tool('send_inline_keyboard', 'Send inline keyboard', self.send_inline_keyboard)
        self.register_tool('edit_message', 'Edit message', self.edit_message)
        self.register_tool('delete_message', 'Delete message', self.delete_message)
        self.register_tool('forward_message', 'Forward message', self.forward_message)
        self.register_tool('get_chat_info', 'Get chat information', self.get_chat_info)
        self.register_tool('get_user_info', 'Get user information', self.get_user_info)
        self.register_tool('get_message_info', 'Get message information', self.get_message_info)
        self.register_tool('set_webhook', 'Set webhook', self.set_webhook)
        self.register_tool('delete_webhook', 'Delete webhook', self.delete_webhook)
        self.register_tool('get_webhook_info', 'Get webhook info', self.get_webhook_info)
        self.register_tool('get_bot_info', 'Get bot information', self.get_bot_info)
        self.register_tool('get_updates', 'Get bot updates', self.get_updates)
        self.register_tool('answer_callback', 'Answer callback query', self.answer_callback)
        self.register_tool('send_sticker', 'Send sticker', self.send_sticker)
        self.register_tool('send_location', 'Send location', self.send_location)
        self.register_tool('send_contact', 'Send contact', self.send_contact)
        
        # Register commands
        self.register_command('/telegram_status', self.handle_status_command, 'Show Telegram skill status')
        self.register_command('/telegram_bots', self.handle_bots_command, 'List configured bots')
        self.register_command('/telegram_webhooks', self.handle_webhooks_command, 'Show webhook status')
        
        self.context.logger.info(f"Telegram skill {self.plugin_id} activated")
    
    def _get_api_url(self, bot_token: str, method: str) -> str:
        """Get Telegram API URL"""
        return urljoin(f"https://api.telegram.org/bot{bot_token}/", method)
    
    def _make_request(self, bot_token: str, method: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make Telegram API request"""
        url = self._get_api_url(bot_token, method)
        
        try:
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                return {"success": True, "data": result.get("result")}
            else:
                return {"success": False, "error": result.get("description", "Unknown error")}
                
        except requests.exceptions.RequestException as e:
            self.context.logger.error(f"Telegram API request failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_message(self, bot_token: str, chat_id: str, text: str, 
                          parse_mode: str = "HTML", reply_to_message_id: str = None,
                          reply_markup: Dict[str, Any] = None, disable_web_page_preview: bool = False) -> Dict[str, Any]:
        """Send Telegram message"""
        try:
            data = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": disable_web_page_preview
            }
            
            if reply_to_message_id:
                data["reply_to_message_id"] = reply_to_message_id
            
            if reply_markup:
                data["reply_markup"] = reply_markup
            
            result = self._make_request(bot_token, "sendMessage", data)
            
            if result["success"]:
                self.message_count += 1
                self.action_history.append({
                    'action': 'send_message',
                    'timestamp': datetime.now(),
                    'chat_id': chat_id,
                    'success': True
                })
                return {
                    "success": True, 
                    "message_id": result["data"]["message_id"],
                    "date": result["data"]["date"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            self.context.logger.error(f"Error sending message: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_media(self, bot_token: str, chat_id: str, media_type: str, 
                        media_url: str, caption: str = None, parse_mode: str = "HTML") -> Dict[str, Any]:
        """Send media message"""
        try:
            # Determine media method and field
            method_mapping = {
                "photo": ("sendPhoto", "photo"),
                "video": ("sendVideo", "video"),
                "audio": ("sendAudio", "audio"),
                "document": ("sendDocument", "document"),
                "voice": ("sendVoice", "voice"),
                "video_note": ("sendVideoNote", "video_note")
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
            
            if result["success"]:
                self.message_count += 1
                return {
                    "success": True, 
                    "message_id": result["data"]["message_id"],
                    "date": result["data"]["date"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            self.context.logger.error(f"Error sending media: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_poll(self, bot_token: str, chat_id: str, question: str, 
                       options: List[str], is_anonymous: bool = True,
                       allows_multiple_answers: bool = False,
                       correct_option_id: int = None,
                       explanation: str = None) -> Dict[str, Any]:
        """Send poll"""
        try:
            if len(options) < 2 or len(options) > 10:
                return {"success": False, "error": "Poll must have 2-10 options"}
            
            data = {
                "chat_id": chat_id,
                "question": question,
                "options": json.dumps(options),
                "is_anonymous": is_anonymous,
                "allows_multiple_answers": allows_multiple_answers
            }
            
            if correct_option_id is not None:
                data["correct_option_id"] = correct_option_id
            
            if explanation:
                data["explanation"] = explanation
            
            result = self._make_request(bot_token, "sendPoll", data)
            
            if result["success"]:
                self.message_count += 1
                return {
                    "success": True,
                    "message_id": result["data"]["message_id"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            self.context.logger.error(f"Error sending poll: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_keyboard(self, bot_token: str, chat_id: str, text: str, 
                          keyboard_data: List[List[Dict[str, str]]], 
                          resize_keyboard: bool = True,
                          one_time_keyboard: bool = False) -> Dict[str, Any]:
        """Send custom keyboard"""
        try:
            reply_markup = {
                "keyboard": keyboard_data,
                "resize_keyboard": resize_keyboard,
                "one_time_keyboard": one_time_keyboard
            }
            
            return await self.send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup
            )
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_inline_keyboard(self, bot_token: str, chat_id: str, text: str,
                                 inline_keyboard: List[List[Dict[str, str]]],
                                 parse_mode: str = "HTML") -> Dict[str, Any]:
        """Send inline keyboard"""
        try:
            reply_markup = {
                "inline_keyboard": inline_keyboard
            }
            
            return await self.send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def edit_message(self, bot_token: str, chat_id: str, message_id: str, 
                          text: str, parse_mode: str = "HTML",
                          reply_markup: Dict[str, Any] = None) -> Dict[str, Any]:
        """Edit message"""
        try:
            data = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            if reply_markup:
                data["reply_markup"] = reply_markup
            
            result = self._make_request(bot_token, "editMessageText", data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def delete_message(self, bot_token: str, chat_id: str, message_id: str) -> Dict[str, Any]:
        """Delete message"""
        try:
            data = {
                "chat_id": chat_id,
                "message_id": message_id
            }
            
            result = self._make_request(bot_token, "deleteMessage", data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def forward_message(self, bot_token: str, chat_id: str, from_chat_id: str, 
                            message_id: str, disable_notification: bool = False) -> Dict[str, Any]:
        """Forward message"""
        try:
            data = {
                "chat_id": chat_id,
                "from_chat_id": from_chat_id,
                "message_id": message_id,
                "disable_notification": disable_notification
            }
            
            result = self._make_request(bot_token, "forwardMessage", data)
            
            if result["success"]:
                return {
                    "success": True,
                    "message_id": result["data"]["message_id"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_chat_info(self, bot_token: str, chat_id: str) -> Dict[str, Any]:
        """Get chat information"""
        try:
            data = {"chat_id": chat_id}
            result = self._make_request(bot_token, "getChat", data)
            
            if result["success"]:
                chat_info = result["data"]
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
                        "invite_link": chat_info.get("invite_link"),
                        "pinned_message": chat_info.get("pinned_message"),
                        "permissions": chat_info.get("permissions"),
                        "slow_mode_delay": chat_info.get("slow_mode_delay"),
                        "message_auto_delete_time": chat_info.get("message_auto_delete_time"),
                        "sticker_set_name": chat_info.get("sticker_set_name"),
                        "can_set_sticker_set": chat_info.get("can_set_sticker_set")
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_user_info(self, bot_token: str, user_id: str) -> Dict[str, Any]:
        """Get user information"""
        try:
            data = {"user_id": user_id}
            result = self._make_request(bot_token, "getChatMember", data)
            
            if result["success"]:
                user_info = result["data"]
                return {
                    "success": True,
                    "user_info": {
                        "user": user_info.get("user", {}),
                        "status": user_info.get("status"),
                        "custom_title": user_info.get("custom_title"),
                        "until_date": user_info.get("until_date"),
                        "can_be_edited": user_info.get("can_be_edited"),
                        "can_post_messages": user_info.get("can_post_messages"),
                        "can_edit_messages": user_info.get("can_edit_messages"),
                        "can_delete_messages": user_info.get("can_delete_messages"),
                        "can_restrict_members": user_info.get("can_restrict_members"),
                        "can_promote_members": user_info.get("can_promote_members"),
                        "can_change_info": user_info.get("can_change_info"),
                        "can_invite_users": user_info.get("can_invite_users"),
                        "can_pin_messages": user_info.get("can_pin_messages"),
                        "is_anonymous": user_info.get("is_anonymous")
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_message_info(self, bot_token: str, chat_id: str, message_id: str) -> Dict[str, Any]:
        """Get message information"""
        try:
            data = {
                "chat_id": chat_id,
                "message_id": message_id
            }
            result = self._make_request(bot_token, "getChat", data)
            
            if result["success"]:
                message_info = result["data"]
                return {
                    "success": True,
                    "message_info": message_info
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def set_webhook(self, bot_token: str, webhook_url: str, 
                         allowed_updates: List[str] = None,
                         drop_pending_updates: bool = False) -> Dict[str, Any]:
        """Set webhook"""
        try:
            data = {
                "url": webhook_url,
                "drop_pending_updates": drop_pending_updates
            }
            
            if allowed_updates:
                data["allowed_updates"] = allowed_updates
            
            result = self._make_request(bot_token, "setWebhook", data)
            
            if result["success"]:
                return {
                    "success": True,
                    "result": result["data"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def delete_webhook(self, bot_token: str, drop_pending_updates: bool = False) -> Dict[str, Any]:
        """Delete webhook"""
        try:
            data = {"drop_pending_updates": drop_pending_updates}
            result = self._make_request(bot_token, "deleteWebhook", data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_webhook_info(self, bot_token: str) -> Dict[str, Any]:
        """Get webhook information"""
        try:
            result = self._make_request(bot_token, "getWebhookInfo")
            
            if result["success"]:
                webhook_info = result["data"]
                return {
                    "success": True,
                    "webhook_info": {
                        "url": webhook_info.get("url"),
                        "has_custom_certificate": webhook_info.get("has_custom_certificate"),
                        "pending_update_count": webhook_info.get("pending_update_count"),
                        "last_error_date": webhook_info.get("last_error_date"),
                        "last_error_message": webhook_info.get("last_error_message"),
                        "max_connections": webhook_info.get("max_connections"),
                        "allowed_updates": webhook_info.get("allowed_updates")
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_bot_info(self, bot_token: str) -> Dict[str, Any]:
        """Get bot information"""
        try:
            result = self._make_request(bot_token, "getMe")
            
            if result["success"]:
                bot_info = result["data"]
                return {
                    "success": True,
                    "bot_info": {
                        "id": bot_info.get("id"),
                        "first_name": bot_info.get("first_name"),
                        "username": bot_info.get("username"),
                        "can_join_groups": bot_info.get("can_join_groups"),
                        "can_read_all_group_messages": bot_info.get("can_read_all_group_messages"),
                        "supports_inline_queries": bot_info.get("supports_inline_queries"),
                        "can_connect_to_business": bot_info.get("can_connect_to_business"),
                        "has_main_web_app": bot_info.get("has_main_web_app")
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_updates(self, bot_token: str, offset: int = None, 
                         limit: int = 100, timeout: int = 0,
                         allowed_updates: List[str] = None) -> Dict[str, Any]:
        """Get bot updates"""
        try:
            data = {
                "limit": limit,
                "timeout": timeout
            }
            
            if offset:
                data["offset"] = offset
            
            if allowed_updates:
                data["allowed_updates"] = allowed_updates
            
            result = self._make_request(bot_token, "getUpdates", data)
            
            if result["success"]:
                updates = result["data"]
                return {
                    "success": True,
                    "updates": updates,
                    "count": len(updates)
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def answer_callback(self, bot_token: str, callback_query_id: str,
                            text: str = None, show_alert: bool = False,
                            url: str = None, cache_time: int = 0) -> Dict[str, Any]:
        """Answer callback query"""
        try:
            data = {
                "callback_query_id": callback_query_id,
                "show_alert": show_alert,
                "cache_time": cache_time
            }
            
            if text:
                data["text"] = text
            
            if url:
                data["url"] = url
            
            result = self._make_request(bot_token, "answerCallbackQuery", data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_sticker(self, bot_token: str, chat_id: str, sticker: str,
                          disable_notification: bool = False,
                          reply_to_message_id: str = None) -> Dict[str, Any]:
        """Send sticker"""
        try:
            data = {
                "chat_id": chat_id,
                "sticker": sticker,
                "disable_notification": disable_notification
            }
            
            if reply_to_message_id:
                data["reply_to_message_id"] = reply_to_message_id
            
            result = self._make_request(bot_token, "sendSticker", data)
            
            if result["success"]:
                self.message_count += 1
                return {
                    "success": True,
                    "message_id": result["data"]["message_id"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_location(self, bot_token: str, chat_id: str, latitude: float, 
                           longitude: float, live_period: int = None,
                           disable_notification: bool = False) -> Dict[str, Any]:
        """Send location"""
        try:
            data = {
                "chat_id": chat_id,
                "latitude": latitude,
                "longitude": longitude,
                "disable_notification": disable_notification
            }
            
            if live_period:
                data["live_period"] = live_period
            
            result = self._make_request(bot_token, "sendLocation", data)
            
            if result["success"]:
                self.message_count += 1
                return {
                    "success": True,
                    "message_id": result["data"]["message_id"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_contact(self, bot_token: str, chat_id: str, phone_number: str, 
                          first_name: str, last_name: str = None,
                          vcard: str = None, disable_notification: bool = False) -> Dict[str, Any]:
        """Send contact"""
        try:
            data = {
                "chat_id": chat_id,
                "phone_number": phone_number,
                "first_name": first_name,
                "disable_notification": disable_notification
            }
            
            if last_name:
                data["last_name"] = last_name
            
            if vcard:
                data["vcard"] = vcard
            
            result = self._make_request(bot_token, "sendContact", data)
            
            if result["success"]:
                self.message_count += 1
                return {
                    "success": True,
                    "message_id": result["data"]["message_id"]
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_status_command(self, args: str) -> str:
        """Handle Telegram status command"""
        try:
            status_info = {
                'skill_id': self.plugin_id,
                'message_count': self.message_count,
                'active_bots': len(self._bots),
                'action_history_count': len(self.action_history),
                'tools': len(self.get_tools()),
                'hooks': sum(len(hooks) for hooks in self.get_hooks().values()),
                'commands': len(self.get_commands())
            }
            
            return f"Telegram Skill Status:\n{json.dumps(status_info, indent=2, ensure_ascii=False)}"
        except Exception as e:
            return f"获取Telegram状态失败: {str(e)}"
    
    async def handle_bots_command(self, args: str) -> str:
        """Handle bots list command"""
        try:
            if not self._bots:
                return "暂无已配置的机器人"
            
            bot_list = []
            for bot_id, bot_data in self._bots.items():
                bot_list.append(f"- {bot_id}: {bot_data.get('username', 'Unknown')}")
            
            return f"已配置的机器人:\n" + "\n".join(bot_list)
        except Exception as e:
            return f"获取机器人列表失败: {str(e)}"
    
    async def handle_webhooks_command(self, args: str) -> str:
        """Handle webhooks status command"""
        try:
            result = "Webhook状态:\n"
            
            for bot_token, webhook_data in self._bots.items():
                bot_info = await self.get_bot_info(bot_token)
                if bot_info['success']:
                    username = bot_info['bot_info'].get('username', 'Unknown')
                    result += f"\nBot @{username}:\n"
                    
                    webhook_info = await self.get_webhook_info(bot_token)
                    if webhook_info['success']:
                        webhook_url = webhook_info['webhook_info'].get('url', 'Not set')
                        pending_count = webhook_info['webhook_info'].get('pending_update_count', 0)
                        result += f"  URL: {webhook_url}\n"
                        result += f"  Pending updates: {pending_count}\n"
            
            return result
        except Exception as e:
            return f"获取Webhook状态失败: {str(e)}"
    
    async def deactivate(self):
        """Cleanup when deactivating"""
        try:
            self._bots.clear()
            self.action_history.clear()
            await super().deactivate()
        except Exception as e:
            self.context.logger.error(f"Error during Telegram skill cleanup: {e}")