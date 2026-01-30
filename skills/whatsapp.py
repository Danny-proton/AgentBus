"""
WhatsApp Skill for AgentBus

Migrated from Moltbot WhatsApp functionality.
Provides WhatsApp messaging integration for sending messages, media, and managing contacts.

Features:
- Text message sending
- Media message support (images, documents, audio, video)
- Contact management
- Group messaging
- Message status tracking
- Media upload and sharing

Usage:
    # Send message
    skill.send_message(phone_number="+1234567890", text="Hello from AgentBus")
    
    # Send media
    skill.send_media(phone_number="+1234567890", media_type="image", media_url="...")
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests
from urllib.parse import urljoin

from ..plugins.core import AgentBusPlugin, PluginContext


class WhatsAppSkill(AgentBusPlugin):
    """
    WhatsApp Skill - Provides WhatsApp messaging integration
    
    Implements WhatsApp messaging functionality for text, media,
    and contact management.
    """
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        self._sessions = {}
        self.message_count = 0
        self.action_history = []
        
    def get_info(self) -> Dict[str, Any]:
        """Return plugin information"""
        return {
            'id': self.plugin_id,
            'name': 'WhatsApp Skill',
            'version': '1.0.0',
            'description': 'WhatsApp messaging integration for text, media, and contact management',
            'author': 'AgentBus Team',
            'dependencies': ['requests'],
            'capabilities': [
                'send_messages',
                'send_media',
                'contact_management',
                'group_messaging',
                'media_sharing'
            ]
        }
    
    async def activate(self):
        """Activate plugin and register tools"""
        await super().activate()
        
        # Register WhatsApp tools
        self.register_tool('send_message', 'Send WhatsApp message', self.send_message)
        self.register_tool('send_media', 'Send media message', self.send_media)
        self.register_tool('send_document', 'Send document', self.send_document)
        self.register_tool('send_audio', 'Send audio message', self.send_audio)
        self.register_tool('send_video', 'Send video message', self.send_video)
        self.register_tool('send_image', 'Send image message', self.send_image)
        self.register_tool('send_location', 'Send location', self.send_location)
        self.register_tool('send_contact', 'Send contact', self.send_contact)
        self.register_tool('send_sticker', 'Send sticker', self.send_sticker)
        self.register_tool('create_group', 'Create group', self.create_group)
        self.register_tool('add_participant', 'Add participant to group', self.add_participant)
        self.register_tool('remove_participant', 'Remove participant from group', self.remove_participant)
        self.register_tool('get_group_info', 'Get group information', self.get_group_info)
        self.register_tool('get_contact_info', 'Get contact information', self.get_contact_info)
        self.register_tool('get_message_status', 'Get message status', self.get_message_status)
        self.register_tool('archive_chat', 'Archive chat', self.archive_chat)
        self.register_tool('unarchive_chat', 'Unarchive chat', self.unarchive_chat)
        self.register_tool('mark_message_read', 'Mark message as read', self.mark_message_read)
        self.register_tool('get_chat_list', 'Get chat list', self.get_chat_list)
        
        # Register commands
        self.register_command('/whatsapp_status', self.handle_status_command, 'Show WhatsApp skill status')
        self.register_command('/whatsapp_sessions', self.handle_sessions_command, 'List active sessions')
        self.register_command('/whatsapp_groups', self.handle_groups_command, 'List managed groups')
        
        self.context.logger.info(f"WhatsApp skill {self.plugin_id} activated")
    
    def _get_api_url(self, base_url: str, endpoint: str) -> str:
        """Get WhatsApp API URL"""
        return urljoin(f"{base_url}/", endpoint)
    
    def _make_request(self, session_id: str, base_url: str, method: str, endpoint: str, 
                     data: Dict[str, Any] = None, files: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make WhatsApp API request"""
        url = self._get_api_url(base_url, endpoint)
        
        # Get or create session
        if session_id not in self._sessions:
            self._sessions[session_id] = requests.Session()
        
        session = self._sessions[session_id]
        
        try:
            if method == "GET":
                response = session.get(url, timeout=30)
            elif method == "POST":
                if files:
                    response = session.post(url, data=data, files=files, timeout=30)
                else:
                    response = session.post(url, json=data, timeout=30)
            elif method == "PUT":
                response = session.put(url, json=data, timeout=30)
            elif method == "DELETE":
                response = session.delete(url, timeout=30)
            else:
                return {"success": False, "error": f"Unsupported HTTP method: {method}"}
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("success", True):
                return {"success": True, "data": result.get("data", result)}
            else:
                return {"success": False, "error": result.get("error", "Unknown error")}
                
        except requests.exceptions.RequestException as e:
            self.context.logger.error(f"WhatsApp API request failed: {e}")
            return {"success": False, "error": str(e)}
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON response"}
    
    def _format_phone_number(self, phone_number: str) -> str:
        """Format phone number for WhatsApp"""
        # Remove all non-digit characters
        cleaned = ''.join(filter(str.isdigit, phone_number))
        
        # Add country code if not present (assume +1 for North America)
        if len(cleaned) == 10:
            cleaned = '1' + cleaned
        elif not cleaned.startswith('1') and len(cleaned) > 10:
            # Keep as is if it already has country code
            pass
        else:
            cleaned = '1' + cleaned
        
        return cleaned
    
    async def send_message(self, session_id: str, base_url: str, phone_number: str, 
                          text: str, message_type: str = "text") -> Dict[str, Any]:
        """Send WhatsApp message"""
        try:
            formatted_phone = self._format_phone_number(phone_number)
            
            data = {
                "phone": formatted_phone,
                "type": message_type,
                "message": text
            }
            
            if message_type == "text":
                data["message"] = {"text": text}
            elif message_type == "template":
                data["template"] = json.loads(text)  # Assume JSON template
            elif message_type == "list":
                data["list"] = json.loads(text)  # Assume JSON list
            elif message_type == "button":
                data["button"] = json.loads(text)  # Assume JSON button
            
            result = self._make_request(session_id, base_url, "POST", "send-message", data)
            
            if result["success"]:
                self.message_count += 1
                self.action_history.append({
                    'action': 'send_message',
                    'timestamp': datetime.now(),
                    'phone_number': formatted_phone,
                    'message_type': message_type,
                    'success': True
                })
                return {
                    "success": True,
                    "message_id": result["data"].get("key", {}).get("id"),
                    "status": result["data"].get("status")
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            self.context.logger.error(f"Error sending message: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_media(self, session_id: str, base_url: str, phone_number: str, 
                        media_type: str, media_url: str, caption: str = None) -> Dict[str, Any]:
        """Send media message"""
        try:
            formatted_phone = self._format_phone_number(phone_number)
            
            # Download media file first if it's a URL
            if media_url.startswith('http'):
                response = requests.get(media_url, timeout=30)
                response.raise_for_status()
                media_data = response.content
                filename = media_url.split('/')[-1]
            else:
                with open(media_url, 'rb') as f:
                    media_data = f.read()
                filename = media_url.split('/')[-1]
            
            # Determine message type based on media type
            type_mapping = {
                "image": "image",
                "video": "video", 
                "audio": "audio",
                "document": "document",
                "sticker": "sticker"
            }
            
            message_type = type_mapping.get(media_type, "document")
            
            data = {
                "phone": formatted_phone,
                "type": message_type
            }
            
            files = {
                "file": (filename, media_data)
            }
            
            if caption:
                data["caption"] = caption
            
            result = self._make_request(session_id, base_url, "POST", "send-media", data, files)
            
            if result["success"]:
                self.message_count += 1
                return {
                    "success": True,
                    "message_id": result["data"].get("key", {}).get("id"),
                    "status": result["data"].get("status")
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            self.context.logger.error(f"Error sending media: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_document(self, session_id: str, base_url: str, phone_number: str, 
                           document_url: str, filename: str = None, caption: str = None) -> Dict[str, Any]:
        """Send document"""
        try:
            formatted_phone = self._format_phone_number(phone_number)
            
            # Download document
            response = requests.get(document_url, timeout=30)
            response.raise_for_status()
            document_data = response.content
            
            if not filename:
                filename = document_url.split('/')[-1]
            
            data = {
                "phone": formatted_phone,
                "caption": caption
            }
            
            files = {
                "file": (filename, document_data)
            }
            
            result = self._make_request(session_id, base_url, "POST", "send-media", data, files)
            
            if result["success"]:
                self.message_count += 1
                return {
                    "success": True,
                    "message_id": result["data"].get("key", {}).get("id")
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_audio(self, session_id: str, base_url: str, phone_number: str, 
                        audio_url: str, caption: str = None) -> Dict[str, Any]:
        """Send audio message"""
        return await self.send_media(session_id, base_url, phone_number, "audio", audio_url, caption)
    
    async def send_video(self, session_id: str, base_url: str, phone_number: str, 
                        video_url: str, caption: str = None) -> Dict[str, Any]:
        """Send video message"""
        return await self.send_media(session_id, base_url, phone_number, "video", video_url, caption)
    
    async def send_image(self, session_id: str, base_url: str, phone_number: str, 
                        image_url: str, caption: str = None) -> Dict[str, Any]:
        """Send image message"""
        return await self.send_media(session_id, base_url, phone_number, "image", image_url, caption)
    
    async def send_location(self, session_id: str, base_url: str, phone_number: str, 
                           latitude: float, longitude: float, name: str = None,
                           address: str = None) -> Dict[str, Any]:
        """Send location"""
        try:
            formatted_phone = self._format_phone_number(phone_number)
            
            data = {
                "phone": formatted_phone,
                "type": "location",
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                }
            }
            
            if name:
                data["location"]["name"] = name
            
            if address:
                data["location"]["address"] = address
            
            result = self._make_request(session_id, base_url, "POST", "send-message", data)
            
            if result["success"]:
                self.message_count += 1
                return {
                    "success": True,
                    "message_id": result["data"].get("key", {}).get("id")
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_contact(self, session_id: str, base_url: str, phone_number: str, 
                          contact_name: str, contact_phone: str, 
                          contact_email: str = None) -> Dict[str, Any]:
        """Send contact"""
        try:
            formatted_phone = self._format_phone_number(phone_number)
            
            data = {
                "phone": formatted_phone,
                "type": "contact",
                "contact": {
                    "displayName": contact_name,
                    "contacts": [{
                        "name": {"displayName": contact_name},
                        "phones": [{"phone": contact_phone}]
                    }]
                }
            }
            
            if contact_email:
                data["contact"]["contacts"][0]["emails"] = [{"email": contact_email}]
            
            result = self._make_request(session_id, base_url, "POST", "send-message", data)
            
            if result["success"]:
                self.message_count += 1
                return {
                    "success": True,
                    "message_id": result["data"].get("key", {}).get("id")
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def send_sticker(self, session_id: str, base_url: str, phone_number: str, 
                          sticker_url: str) -> Dict[str, Any]:
        """Send sticker"""
        return await self.send_media(session_id, base_url, phone_number, "sticker", sticker_url)
    
    async def create_group(self, session_id: str, base_url: str, name: str, 
                          participants: List[str]) -> Dict[str, Any]:
        """Create group"""
        try:
            formatted_participants = [self._format_phone_number(p) for p in participants]
            
            data = {
                "name": name,
                "participants": formatted_participants
            }
            
            result = self._make_request(session_id, base_url, "POST", "create-group", data)
            
            if result["success"]:
                return {
                    "success": True,
                    "group_id": result["data"].get("gid"),
                    "participants": formatted_participants
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def add_participant(self, session_id: str, base_url: str, group_id: str, 
                             phone_number: str) -> Dict[str, Any]:
        """Add participant to group"""
        try:
            formatted_phone = self._format_phone_number(phone_number)
            
            data = {
                "group_id": group_id,
                "phone": formatted_phone
            }
            
            result = self._make_request(session_id, base_url, "POST", "add-participant", data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def remove_participant(self, session_id: str, base_url: str, group_id: str, 
                                phone_number: str) -> Dict[str, Any]:
        """Remove participant from group"""
        try:
            formatted_phone = self._format_phone_number(phone_number)
            
            data = {
                "group_id": group_id,
                "phone": formatted_phone
            }
            
            result = self._make_request(session_id, base_url, "POST", "remove-participant", data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_group_info(self, session_id: str, base_url: str, group_id: str) -> Dict[str, Any]:
        """Get group information"""
        try:
            data = {"group_id": group_id}
            result = self._make_request(session_id, base_url, "GET", "group-info", data)
            
            if result["success"]:
                group_info = result["data"]
                return {
                    "success": True,
                    "group_info": {
                        "id": group_info.get("id"),
                        "name": group_info.get("name"),
                        "participants": group_info.get("participants", []),
                        "owner": group_info.get("owner"),
                        "creation_time": group_info.get("creation"),
                        "description": group_info.get("desc"),
                        "announcement": group_info.get("announce")
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_contact_info(self, session_id: str, base_url: str, phone_number: str) -> Dict[str, Any]:
        """Get contact information"""
        try:
            formatted_phone = self._format_phone_number(phone_number)
            
            data = {"phone": formatted_phone}
            result = self._make_request(session_id, base_url, "GET", "contact-info", data)
            
            if result["success"]:
                contact_info = result["data"]
                return {
                    "success": True,
                    "contact_info": {
                        "id": contact_info.get("id"),
                        "name": contact_info.get("name", {}),
                        "pushname": contact_info.get("pushname"),
                        "verified_name": contact_info.get("verifiedName"),
                        "is_business": contact_info.get("isBusiness"),
                        "is_enterprise": contact_info.get("isEnterprise"),
                        "phone": formatted_phone
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_message_status(self, session_id: str, base_url: str, message_id: str) -> Dict[str, Any]:
        """Get message status"""
        try:
            data = {"message_id": message_id}
            result = self._make_request(session_id, base_url, "GET", "message-status", data)
            
            if result["success"]:
                status_info = result["data"]
                return {
                    "success": True,
                    "status": {
                        "message_id": message_id,
                        "status": status_info.get("status"),
                        "timestamp": status_info.get("timestamp"),
                        "receipt": status_info.get("receipt"),
                        "read": status_info.get("read")
                    }
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def archive_chat(self, session_id: str, base_url: str, chat_id: str) -> Dict[str, Any]:
        """Archive chat"""
        try:
            data = {"chat_id": chat_id, "archive": True}
            result = self._make_request(session_id, base_url, "POST", "archive-chat", data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def unarchive_chat(self, session_id: str, base_url: str, chat_id: str) -> Dict[str, Any]:
        """Unarchive chat"""
        try:
            data = {"chat_id": chat_id, "archive": False}
            result = self._make_request(session_id, base_url, "POST", "archive-chat", data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def mark_message_read(self, session_id: str, base_url: str, chat_id: str) -> Dict[str, Any]:
        """Mark message as read"""
        try:
            data = {"chat_id": chat_id}
            result = self._make_request(session_id, base_url, "POST", "mark-read", data)
            
            if result["success"]:
                return {"success": True}
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_chat_list(self, session_id: str, base_url: str, limit: int = 50) -> Dict[str, Any]:
        """Get chat list"""
        try:
            data = {"limit": limit}
            result = self._make_request(session_id, base_url, "GET", "chat-list", data)
            
            if result["success"]:
                chats = result["data"]
                return {
                    "success": True,
                    "chats": chats,
                    "count": len(chats) if isinstance(chats, list) else 1
                }
            else:
                return {"success": False, "error": result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def handle_status_command(self, args: str) -> str:
        """Handle WhatsApp status command"""
        try:
            status_info = {
                'skill_id': self.plugin_id,
                'message_count': self.message_count,
                'active_sessions': len(self._sessions),
                'action_history_count': len(self.action_history),
                'tools': len(self.get_tools()),
                'hooks': sum(len(hooks) for hooks in self.get_hooks().values()),
                'commands': len(self.get_commands())
            }
            
            return f"WhatsApp Skill Status:\n{json.dumps(status_info, indent=2, ensure_ascii=False)}"
        except Exception as e:
            return f"获取WhatsApp状态失败: {str(e)}"
    
    async def handle_sessions_command(self, args: str) -> str:
        """Handle sessions list command"""
        try:
            if not self._sessions:
                return "暂无活跃会话"
            
            session_list = []
            for session_id in self._sessions.keys():
                session_list.append(f"- {session_id}")
            
            return f"活跃会话:\n" + "\n".join(session_list)
        except Exception as e:
            return f"获取会话列表失败: {str(e)}"
    
    async def handle_groups_command(self, args: str) -> str:
        """Handle groups list command"""
        try:
            # This would need to be implemented based on actual group management
            return "群组管理功能正在开发中..."
        except Exception as e:
            return f"获取群组列表失败: {str(e)}"
    
    async def deactivate(self):
        """Cleanup when deactivating"""
        try:
            for session in self._sessions.values():
                session.close()
            self._sessions.clear()
            self.action_history.clear()
            await super().deactivate()
        except Exception as e:
            self.context.logger.error(f"Error during WhatsApp skill cleanup: {e}")