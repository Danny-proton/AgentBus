#!/usr/bin/env python3
"""
AgentBus Memory and Preferences System Usage Example

This example demonstrates how to use the comprehensive user memory and 
preferences management system in AgentBus.

Features demonstrated:
- User memory storage and retrieval
- Conversation history management
- Context caching
- User preferences configuration
- Skill preferences management
- Channel preferences management
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Import the unified manager
from manager import AgentBusManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Demonstrate the complete memory and preferences system"""
    
    # Initialize the unified manager
    manager = AgentBusManager(
        storage_base_path="data",
        memory_config={
            "max_memory_items": 10000,
            "cache_size_mb": 100,
            "auto_cleanup": True
        },
        preferences_config={
            "auto_backup": True,
            "backup_interval_hours": 24
        }
    )
    
    print("=== AgentBus Memory and Preferences System Demo ===\n")
    
    # 1. User Memory Management
    print("1. User Memory Management")
    print("-" * 30)
    
    # Add user memories
    await manager.add_memory(
        user_id="user123",
        content="用户喜欢喝咖啡，每天早上都要喝一杯",
        memory_type="personal_info",
        tags=["咖啡", "早晨", "习惯"],
        priority="medium"
    )
    
    await manager.add_memory(
        user_id="user123",
        content="用户正在学习Python编程语言",
        memory_type="learning",
        tags=["Python", "编程", "学习"],
        priority="high"
    )
    
    # Retrieve memories
    memories = await manager.get_memories("user123", limit=10)
    print(f"Found {len(memories)} memories for user123:")
    for memory in memories:
        print(f"  - {memory.content[:50]}...")
    
    print()
    
    # 2. Conversation History
    print("2. Conversation History Management")
    print("-" * 35)
    
    # Add conversation messages
    await manager.add_message(
        session_id="session456",
        user_id="user123",
        role="user",
        content="你好，我想了解Python的基础知识",
        timestamp=datetime.now()
    )
    
    await manager.add_message(
        session_id="session456", 
        user_id="user123",
        role="assistant",
        content="当然！Python是一种简单易学的编程语言...",
        timestamp=datetime.now()
    )
    
    # Get conversation history
    history = await manager.get_conversation_history("session456", limit=10)
    print(f"Conversation history for session456 ({len(history)} messages):")
    for msg in history:
        print(f"  [{msg.role}] {msg.content[:40]}...")
    
    print()
    
    # 3. Context Caching
    print("3. Context Caching")
    print("-" * 20)
    
    # Store context in cache
    context_data = {
        "user_preferences": {"language": "zh", "theme": "dark"},
        "recent_memories": ["coffee", "python"],
        "conversation_summary": "User interested in Python learning"
    }
    
    await manager.cache_context(
        user_id="user123",
        context_data=context_data,
        cache_type="user_session",
        ttl_hours=2
    )
    
    # Retrieve cached context
    cached = await manager.get_cached_context("user123", "user_session")
    print(f"Cached context retrieved: {cached is not None}")
    if cached:
        print(f"  - Language preference: {cached.get('user_preferences', {}).get('language')}")
    
    print()
    
    # 4. User Preferences
    print("4. User Preferences Configuration")
    print("-" * 35)
    
    # Set user preferences
    await manager.set_user_preference(
        user_id="user123",
        category="general",
        key="language",
        value="zh-CN"
    )
    
    await manager.set_user_preference(
        user_id="user123",
        category="general", 
        key="notifications",
        value=True
    )
    
    # Get user preferences
    preferences = await manager.get_user_preferences("user123")
    print(f"User preferences for user123:")
    for category, prefs in preferences.items():
        for key, value in prefs.items():
            print(f"  - {category}.{key}: {value}")
    
    print()
    
    # 5. Skill Preferences
    print("5. Skill Preferences Management")
    print("-" * 35)
    
    # Configure skill preferences
    await manager.set_skill_preference(
        user_id="user123",
        skill_name="python_tutor",
        enabled=True,
        priority="high",
        parameters={"difficulty": "beginner", "examples": True}
    )
    
    await manager.set_skill_preference(
        user_id="user123",
        skill_name="coffee_reminder",
        enabled=True,
        priority="medium",
        parameters={"time": "08:00", "type": "latte"}
    )
    
    # Get skill preferences
    skills = await manager.get_user_skills("user123")
    print(f"Enabled skills for user123 ({len(skills)}):")
    for skill in skills:
        print(f"  - {skill.skill_name}: {skill.status.value} (priority: {skill.priority.value})")
    
    print()
    
    # 6. Channel Preferences
    print("6. Channel Preferences Management")
    print("-" * 35)
    
    # Set channel preferences
    await manager.set_channel_preference(
        user_id="user123",
        channel_name="slack",
        channel_type="slack",
        enabled=True,
        message_format="markdown",
        notification_level="normal"
    )
    
    await manager.set_channel_preference(
        user_id="user123",
        channel_name="discord",
        channel_type="discord", 
        enabled=True,
        message_format="text",
        notification_level="quiet"
    )
    
    # Get channel preferences
    channels = await manager.get_user_channels("user123")
    print(f"Configured channels for user123 ({len(channels)}):")
    for channel in channels:
        print(f"  - {channel.channel_name}: {channel.channel_type.value} "
              f"({channel.message_format.value}, {channel.notification_level.value})")
    
    print()
    
    # 7. System Statistics
    print("7. System Statistics")
    print("-" * 25)
    
    stats = await manager.get_system_stats()
    print(f"System Statistics:")
    print(f"  - Total memories: {stats['memory']['total_memories']}")
    print(f"  - Total conversations: {stats['memory']['total_conversations']}")
    print(f"  - Total users: {stats['preferences']['total_users']}")
    print(f"  - Enabled skills: {stats['preferences']['enabled_skills']}")
    print(f"  - Active channels: {stats['preferences']['active_channels']}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    asyncio.run(main())