"""
AgentBus Memory and Preferences Management System

This module provides a unified interface for managing user memory, preferences,
and all related systems including conversation history, context caching, and
skill/channel preferences.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta

from .memory import UserMemory, ConversationHistory, ContextCache, MemoryType, MemoryPriority
from .memory import MessageType, MessagePriority, ConversationStatus
from .preferences import UserPreferences, SkillPreferences, ChannelPreferences
from .preferences import PreferenceCategory, SkillStatus, SkillPriority, SkillTrigger
from .preferences import ChannelType, ChannelStatus, MessageFormat, NotificationLevel

logger = logging.getLogger(__name__)


class AgentBusManager:
    """
    Unified manager for AgentBus memory and preferences systems
    
    This manager provides a single interface to access and manage:
    - User memory and long-term storage
    - Conversation history and context
    - Context caching and optimization
    - User preferences and settings
    - Skill configurations and behavior
    - Channel preferences and management
    """
    
    def __init__(
        self,
        storage_base_path: str = "data",
        memory_config: Optional[Dict[str, Any]] = None,
        preferences_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the AgentBus management system
        
        Args:
            storage_base_path: Base path for all storage files
            memory_config: Configuration for memory systems
            preferences_config: Configuration for preference systems
        """
        self.storage_base_path = storage_base_path
        self.memory_config = memory_config or {}
        self.preferences_config = preferences_config or {}
        
        # Initialize subsystems
        self.user_memory = None
        self.conversation_history = None
        self.context_cache = None
        self.user_preferences = None
        self.skill_preferences = None
        self.channel_preferences = None
        
        # System status
        self.is_initialized = False
        self.start_time = None
        
    async def initialize(self) -> bool:
        """
        Initialize all memory and preferences systems
        
        Returns:
            True if all systems initialized successfully
        """
        try:
            # Initialize memory systems
            self.user_memory = UserMemory(
                storage_path=f"{self.storage_base_path}/user_memory.db"
            )
            
            self.conversation_history = ConversationHistory(
                storage_path=f"{self.storage_base_path}/conversation_history.db"
            )
            
            self.context_cache = ContextCache(
                storage_path=f"{self.storage_base_path}/context_cache"
            )
            
            # Initialize preference systems
            self.user_preferences = UserPreferences(
                storage_path=f"{self.storage_base_path}/user_preferences.db"
            )
            
            self.skill_preferences = SkillPreferences(
                storage_path=f"{self.storage_base_path}/skill_preferences.db"
            )
            
            self.channel_preferences = ChannelPreferences(
                storage_path=f"{self.storage_base_path}/channel_preferences.db"
            )
            
            self.is_initialized = True
            self.start_time = datetime.now()
            
            logger.info("AgentBus Memory and Preferences system initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AgentBus system: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown all systems gracefully"""
        try:
            if self.user_memory:
                await self.user_memory.close()
            if self.conversation_history:
                await self.conversation_history.close()
            if self.context_cache:
                await self.context_cache.close()
            if self.user_preferences:
                await self.user_preferences.close()
            if self.skill_preferences:
                await self.skill_preferences.close()
            if self.channel_preferences:
                await self.channel_preferences.close()
            
            self.is_initialized = False
            logger.info("AgentBus Memory and Preferences system shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during system shutdown: {e}")
    
    # Memory Management Methods
    
    async def store_user_memory(
        self,
        user_id: str,
        memory_type: MemoryType,
        content: Dict[str, Any],
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        tags: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None
    ) -> str:
        """Store user memory with comprehensive metadata"""
        if not self.user_memory:
            raise RuntimeError("User memory system not initialized")
        
        return await self.user_memory.store_memory(
            user_id, memory_type, content, priority, tags, expires_at
        )
    
    async def retrieve_user_memory(
        self,
        user_id: str,
        memory_id: str
    ) -> Optional[Any]:
        """Retrieve specific user memory"""
        if not self.user_memory:
            raise RuntimeError("User memory system not initialized")
        
        memory_entry = await self.user_memory.retrieve_memory(user_id, memory_id)
        return memory_entry.content if memory_entry else None
    
    async def search_user_memories(
        self,
        user_id: str,
        query: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search user memories with filters"""
        if not self.user_memory:
            raise RuntimeError("User memory system not initialized")
        
        memories = await self.user_memory.search_memories(
            user_id, query, memory_type, tags, limit=limit
        )
        
        return [
            {
                "id": memory.id,
                "type": memory.memory_type.value,
                "content": memory.content,
                "tags": memory.tags,
                "priority": memory.priority.value,
                "created_at": memory.created_at.isoformat(),
                "access_count": memory.access_count
            }
            for memory in memories
        ]
    
    # Conversation Management Methods
    
    async def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create new conversation session"""
        if not self.conversation_history:
            raise RuntimeError("Conversation history system not initialized")
        
        return await self.conversation_history.create_conversation(user_id, title, metadata)
    
    async def add_conversation_message(
        self,
        conversation_id: str,
        message_type: MessageType,
        content: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> str:
        """Add message to conversation"""
        if not self.conversation_history:
            raise RuntimeError("Conversation history system not initialized")
        
        return await self.conversation_history.add_message(
            conversation_id, message_type, content, metadata, user_id,
            priority=priority
        )
    
    async def get_conversation(
        self,
        conversation_id: str,
        include_messages: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get conversation with messages"""
        if not self.conversation_history:
            raise RuntimeError("Conversation history system not initialized")
        
        result = await self.conversation_history.get_conversation(
            conversation_id, include_messages
        )
        
        if isinstance(result, tuple):
            conversation, messages = result
            return {
                "conversation": {
                    "id": conversation.id,
                    "user_id": conversation.user_id,
                    "title": conversation.title,
                    "status": conversation.status.value,
                    "created_at": conversation.created_at.isoformat(),
                    "message_count": conversation.message_count
                },
                "messages": [
                    {
                        "id": msg.id,
                        "type": msg.message_type.value,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                        "user_id": msg.user_id
                    }
                    for msg in messages
                ]
            }
        elif result:
            conversation = result
            return {
                "conversation": {
                    "id": conversation.id,
                    "user_id": conversation.user_id,
                    "title": conversation.title,
                    "status": conversation.status.value,
                    "created_at": conversation.created_at.isoformat(),
                    "message_count": conversation.message_count
                }
            }
        
        return None
    
    # Context Management Methods
    
    async def cache_context(
        self,
        key: str,
        value: Any,
        context_type: str,
        ttl: Optional[timedelta] = None,
        priority: int = 5
    ) -> bool:
        """Cache context data"""
        if not self.context_cache:
            raise RuntimeError("Context cache system not initialized")
        
        from .memory.context_cache import ContextType
        context_enum = ContextType(context_type)
        
        return await self.context_cache.set(
            key, value, context_enum, ttl=ttl, priority=priority
        )
    
    async def get_cached_context(
        self,
        key: str,
        context_type: Optional[str] = None
    ) -> Optional[Any]:
        """Get cached context data"""
        if not self.context_cache:
            raise RuntimeError("Context cache system not initialized")
        
        from .memory.context_cache import ContextType
        context_enum = ContextType(context_type) if context_type else None
        
        return await self.context_cache.get(key, context_enum)
    
    async def get_optimized_context_window(
        self,
        user_id: str,
        max_tokens: int = 4000,
        context_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get optimized context window for AI processing"""
        if not self.context_cache:
            raise RuntimeError("Context cache system not initialized")
        
        from .memory.context_cache import ContextType
        context_enums = [
            ContextType(ct) for ct in (context_types or [])
        ] if context_types else None
        
        return await self.context_cache.get_context_window(
            user_id, max_tokens, context_enums
        )
    
    # Preferences Management Methods
    
    async def get_user_preference(
        self,
        user_id: str,
        key: str,
        default: Any = None
    ) -> Any:
        """Get user preference with fallback to default"""
        if not self.user_preferences:
            raise RuntimeError("User preferences system not initialized")
        
        value = await self.user_preferences.get_preference(user_id, key)
        return value if value is not None else default
    
    async def set_user_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
        validate: bool = True
    ) -> bool:
        """Set user preference"""
        if not self.user_preferences:
            raise RuntimeError("User preferences system not initialized")
        
        return await self.user_preferences.set_preference(user_id, key, value, validate=validate)
    
    async def get_all_user_preferences(
        self,
        user_id: str,
        category: Optional[PreferenceCategory] = None
    ) -> Dict[str, Any]:
        """Get all user preferences, optionally filtered by category"""
        if not self.user_preferences:
            raise RuntimeError("User preferences system not initialized")
        
        if category:
            return await self.user_preferences.get_preferences_by_category(user_id, category)
        else:
            return await self.user_preferences.get_all_preferences(user_id)
    
    # Skill Management Methods
    
    async def get_user_skill_config(
        self,
        user_id: str,
        skill_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get user-specific skill configuration"""
        if not self.skill_preferences:
            raise RuntimeError("Skill preferences system not initialized")
        
        config = await self.skill_preferences.get_user_skill_config(user_id, skill_id)
        if config:
            return {
                "skill_id": config.skill_id,
                "name": config.name,
                "version": config.version,
                "description": config.description,
                "category": config.category,
                "enabled": config.enabled,
                "priority": config.priority.value,
                "trigger_type": config.trigger_type.value,
                "parameters": config.parameters,
                "dependencies": config.dependencies
            }
        return None
    
    async def set_user_skill_preference(
        self,
        user_id: str,
        skill_id: str,
        enabled: Optional[bool] = None,
        priority: Optional[SkillPriority] = None,
        custom_parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Set user skill preferences"""
        if not self.skill_preferences:
            raise RuntimeError("Skill preferences system not initialized")
        
        return await self.skill_preferences.set_user_skill_preference(
            user_id, skill_id, enabled, priority, custom_parameters
        )
    
    async def get_user_active_skills(
        self,
        user_id: str,
        trigger_type: Optional[SkillTrigger] = None
    ) -> List[Dict[str, Any]]:
        """Get active skills for user"""
        if not self.skill_preferences:
            raise RuntimeError("Skill preferences system not initialized")
        
        skills = await self.skill_preferences.get_active_skills(user_id, trigger_type)
        
        return [
            {
                "skill_id": skill.skill_id,
                "name": skill.name,
                "category": skill.category,
                "priority": skill.priority.value,
                "trigger_type": skill.trigger_type.value,
                "parameters": skill.parameters
            }
            for skill in skills
        ]
    
    # Channel Management Methods
    
    async def get_user_channel_config(
        self,
        user_id: str,
        channel_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get user-specific channel configuration"""
        if not self.channel_preferences:
            raise RuntimeError("Channel preferences system not initialized")
        
        config, prefs = await self.channel_preferences.get_user_channels(user_id, channel_id)
        if config:
            return {
                "channel_id": config.channel_id,
                "name": config.name,
                "channel_type": config.channel_type.value,
                "description": config.description,
                "enabled": config.enabled,
                "status": config.status.value,
                "user_preferences": {
                    "enabled": prefs.enabled if prefs else True,
                    "notification_level": prefs.notification_level.value if prefs else "all",
                    "message_format": prefs.message_format.value if prefs else "plain",
                    "auto_responses": prefs.auto_responses if prefs else True
                } if prefs else None
            }
        return None
    
    async def set_user_channel_preferences(
        self,
        user_id: str,
        channel_id: str,
        enabled: Optional[bool] = None,
        notification_level: Optional[NotificationLevel] = None,
        message_format: Optional[MessageFormat] = None,
        auto_responses: Optional[bool] = None
    ) -> bool:
        """Set user channel preferences"""
        if not self.channel_preferences:
            raise RuntimeError("Channel preferences system not initialized")
        
        return await self.channel_preferences.set_user_channel_preferences(
            user_id, channel_id, enabled, notification_level, message_format, auto_responses
        )
    
    async def get_user_active_channels(
        self,
        user_id: str,
        notification_level: Optional[NotificationLevel] = None
    ) -> List[Dict[str, Any]]:
        """Get active channels for user"""
        if not self.channel_preferences:
            raise RuntimeError("Channel preferences system not initialized")
        
        channels = await self.channel_preferences.get_active_channels(user_id, notification_level)
        
        return [
            {
                "channel_id": config.channel_id,
                "name": config.name,
                "channel_type": config.channel_type.value,
                "status": config.status.value,
                "user_preferences": {
                    "enabled": prefs.enabled if prefs else True,
                    "notification_level": prefs.notification_level.value if prefs else "all",
                    "message_format": prefs.message_format.value if prefs else "plain",
                    "auto_responses": prefs.auto_responses if prefs else True
                } if prefs else None
            }
            for config, prefs in channels
        ]
    
    # Analytics and Reporting Methods
    
    async def get_user_analytics(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive analytics for a user"""
        analytics = {
            "user_id": user_id,
            "period_days": days,
            "generated_at": datetime.now().isoformat()
        }
        
        try:
            # Memory analytics
            if self.user_memory:
                memory_stats = await self.user_memory.get_user_memory_stats(user_id)
                analytics["memory"] = memory_stats
            
            # Conversation analytics
            if self.conversation_history:
                conv_stats = await self.conversation_history.get_conversation_statistics(user_id)
                analytics["conversations"] = conv_stats
            
            # Cache analytics
            if self.context_cache:
                cache_stats = await self.context_cache.get_cache_stats()
                analytics["cache"] = cache_stats
            
            # Preferences analytics
            if self.user_preferences:
                pref_stats = await self.user_preferences.get_preference_statistics(user_id)
                analytics["preferences"] = pref_stats
            
        except Exception as e:
            logger.error(f"Error generating user analytics: {e}")
            analytics["error"] = str(e)
        
        return analytics
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "system": "AgentBus Memory and Preferences",
            "initialized": self.is_initialized,
            "uptime_seconds": (
                (datetime.now() - self.start_time).total_seconds()
                if self.start_time else 0
            ),
            "components": {}
        }
        
        # Check each component
        components = {
            "user_memory": self.user_memory,
            "conversation_history": self.conversation_history,
            "context_cache": self.context_cache,
            "user_preferences": self.user_preferences,
            "skill_preferences": self.skill_preferences,
            "channel_preferences": self.channel_preferences
        }
        
        for name, component in components.items():
            status["components"][name] = {
                "available": component is not None,
                "initialized": hasattr(component, 'is_initialized') 
                            and getattr(component, 'is_initialized', True)
            }
        
        return status
    
    async def cleanup_expired_data(self) -> Dict[str, int]:
        """Cleanup expired data across all systems"""
        cleanup_stats = {
            "expired_memories": 0,
            "archived_conversations": 0,
            "cleared_cache_entries": 0,
            "total_cleaned": 0
        }
        
        try:
            # Cleanup memory system
            if self.user_memory:
                cleaned = await self.user_memory.cleanup_expired_memories()
                cleanup_stats["expired_memories"] = cleaned
            
            # Archive old conversations
            if self.conversation_history:
                # This would require additional implementation for auto-archiving
                pass
            
            # Clear old cache entries
            if self.context_cache:
                cleared = await self.context_cache.clear()
                cleanup_stats["cleared_cache_entries"] = cleared
            
            cleanup_stats["total_cleaned"] = sum(cleanup_stats.values())
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            cleanup_stats["error"] = str(e)
        
        return cleanup_stats