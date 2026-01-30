"""
AgentBus Preferences System

This package provides comprehensive user preferences management including:
- User preferences and settings
- Skill-specific preferences
- Channel-specific preferences
- Preference validation and migration
"""

from .user_preferences import UserPreferences
from .skill_preferences import SkillPreferences  
from .channel_preferences import ChannelPreferences

__all__ = ['UserPreferences', 'SkillPreferences', 'ChannelPreferences']
__version__ = '1.0.0'