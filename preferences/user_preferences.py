"""
User Preferences Management Module

This module provides comprehensive user preferences management including:
- General user settings and preferences
- Interface and behavior customization
- Privacy and security preferences
- Notification and communication settings
- Preference validation and defaults
"""

import asyncio
import json
import sqlite3
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)


class PreferenceCategory(Enum):
    """Categories of user preferences"""
    GENERAL = "general"
    INTERFACE = "interface"
    PRIVACY = "privacy"
    NOTIFICATIONS = "notifications"
    COMMUNICATION = "communication"
    ACCESSIBILITY = "accessibility"
    PERFORMANCE = "performance"
    SECURITY = "security"
    CUSTOM = "custom"


class PreferenceType(Enum):
    """Types of preference values"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    DATETIME = "datetime"


@dataclass
class PreferenceDefinition:
    """Definition of a preference setting"""
    key: str
    name: str
    description: str
    category: PreferenceCategory
    value_type: PreferenceType
    default_value: Any
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    options: Optional[List[Any]] = None
    required: bool = False
    deprecated: bool = False
    validation_rules: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if isinstance(self.category, str):
            self.category = PreferenceCategory(self.category)
        if isinstance(self.value_type, str):
            self.value_type = PreferenceType(self.value_type)
        self.metadata = self.metadata or {}
        self.validation_rules = self.validation_rules or {}


@dataclass
class UserPreference:
    """Individual user preference value"""
    user_id: str
    key: str
    value: Any
    updated_at: datetime
    source: str = "user"  # user, system, inherited
    validated: bool = False
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        self.metadata = self.metadata or {}


class UserPreferences:
    """
    Comprehensive user preferences management system
    
    Features:
    - Structured preference categories and definitions
    - Type validation and constraints
    - Default value management
    - Preference inheritance and overrides
    - Bulk operations and migration support
    - Analytics and usage tracking
    """
    
    def __init__(self, storage_path: str = "data/user_preferences.db"):
        """Initialize user preferences system
        
        Args:
            storage_path: Path to SQLite database file
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Preference definitions registry
        self.preference_definitions = {}
        self._init_default_preferences()
        
        # Database initialization
        self._init_database()
        
        # Cache for user preferences
        self._preferences_cache = {}
        self._cache_ttl = 300  # 5 minutes
        
    def _init_default_preferences(self):
        """Initialize default preference definitions"""
        default_preferences = [
            # General preferences
            PreferenceDefinition(
                key="language",
                name="Language",
                description="Preferred interface language",
                category=PreferenceCategory.GENERAL,
                value_type=PreferenceType.STRING,
                default_value="en",
                options=["en", "zh", "es", "fr", "de", "ja", "ko"]
            ),
            PreferenceDefinition(
                key="timezone",
                name="Timezone",
                description="User's timezone",
                category=PreferenceCategory.GENERAL,
                value_type=PreferenceType.STRING,
                default_value="UTC"
            ),
            PreferenceDefinition(
                key="theme",
                name="Theme",
                description="Interface theme preference",
                category=PreferenceCategory.INTERFACE,
                value_type=PreferenceType.STRING,
                default_value="light",
                options=["light", "dark", "auto"]
            ),
            PreferenceDefinition(
                key="font_size",
                name="Font Size",
                description="Interface font size",
                category=PreferenceCategory.ACCESSIBILITY,
                value_type=PreferenceType.INTEGER,
                default_value=14,
                min_value=10,
                max_value=24
            ),
            PreferenceDefinition(
                key="auto_save",
                name="Auto Save",
                description="Automatically save user data",
                category=PreferenceCategory.GENERAL,
                value_type=PreferenceType.BOOLEAN,
                default_value=True
            ),
            
            # Privacy preferences
            PreferenceDefinition(
                key="data_sharing",
                name="Data Sharing",
                description="Allow anonymous data sharing",
                category=PreferenceCategory.PRIVACY,
                value_type=PreferenceType.BOOLEAN,
                default_value=False
            ),
            PreferenceDefinition(
                key="analytics_enabled",
                name="Analytics",
                description="Enable usage analytics",
                category=PreferenceCategory.PRIVACY,
                value_type=PreferenceType.BOOLEAN,
                default_value=False
            ),
            
            # Notification preferences
            PreferenceDefinition(
                key="notifications_enabled",
                name="Notifications",
                description="Enable all notifications",
                category=PreferenceCategory.NOTIFICATIONS,
                value_type=PreferenceType.BOOLEAN,
                default_value=True
            ),
            PreferenceDefinition(
                key="email_notifications",
                name="Email Notifications",
                description="Receive notifications via email",
                category=PreferenceCategory.NOTIFICATIONS,
                value_type=PreferenceType.BOOLEAN,
                default_value=True
            ),
            PreferenceDefinition(
                key="notification_sound",
                name="Notification Sound",
                description="Play sound for notifications",
                category=PreferenceCategory.NOTIFICATIONS,
                value_type=PreferenceType.BOOLEAN,
                default_value=True
            ),
            
            # Communication preferences
            PreferenceDefinition(
                key="response_style",
                name="Response Style",
                description="Preferred AI response style",
                category=PreferenceCategory.COMMUNICATION,
                value_type=PreferenceType.STRING,
                default_value="balanced",
                options=["concise", "balanced", "detailed", "creative"]
            ),
            PreferenceDefinition(
                key="response_language",
                name="Response Language",
                description="Language for AI responses",
                category=PreferenceCategory.COMMUNICATION,
                value_type=PreferenceType.STRING,
                default_value="en",
                options=["en", "zh", "es", "fr", "de", "ja", "ko"]
            ),
            
            # Performance preferences
            PreferenceDefinition(
                key="max_concurrent_tasks",
                name="Max Concurrent Tasks",
                description="Maximum number of concurrent tasks",
                category=PreferenceCategory.PERFORMANCE,
                value_type=PreferenceType.INTEGER,
                default_value=3,
                min_value=1,
                max_value=10
            ),
            PreferenceDefinition(
                key="cache_enabled",
                name="Cache Enabled",
                description="Enable response caching",
                category=PreferenceCategory.PERFORMANCE,
                value_type=PreferenceType.BOOLEAN,
                default_value=True
            ),
            PreferenceDefinition(
                key="cache_size_mb",
                name="Cache Size",
                description="Maximum cache size in MB",
                category=PreferenceCategory.PERFORMANCE,
                value_type=PreferenceType.INTEGER,
                default_value=256,
                min_value=64,
                max_value=2048
            ),
            
            # Security preferences
            PreferenceDefinition(
                key="session_timeout_minutes",
                name="Session Timeout",
                description="Session timeout in minutes",
                category=PreferenceCategory.SECURITY,
                value_type=PreferenceType.INTEGER,
                default_value=60,
                min_value=15,
                max_value=1440
            ),
            PreferenceDefinition(
                key="two_factor_enabled",
                name="Two-Factor Auth",
                description="Enable two-factor authentication",
                category=PreferenceCategory.SECURITY,
                value_type=PreferenceType.BOOLEAN,
                default_value=False
            )
        ]
        
        # Register all default preferences
        for pref in default_preferences:
            self.preference_definitions[pref.key] = pref
    
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.storage_path) as conn:
            # User preferences table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT NOT NULL,
                    preference_key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source TEXT DEFAULT 'user',
                    validated INTEGER DEFAULT 0,
                    metadata TEXT,
                    PRIMARY KEY (user_id, preference_key),
                    FOREIGN KEY (preference_key) REFERENCES preference_definitions (key)
                )
            """)
            
            # Preference definitions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preference_definitions (
                    key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    value_type TEXT NOT NULL,
                    default_value TEXT NOT NULL,
                    min_value REAL,
                    max_value REAL,
                    options TEXT,
                    required INTEGER DEFAULT 0,
                    deprecated INTEGER DEFAULT 0,
                    validation_rules TEXT,
                    metadata TEXT
                )
            """)
            
            # Insert default definitions if they don't exist
            for key, definition in self.preference_definitions.items():
                conn.execute("""
                    INSERT OR IGNORE INTO preference_definitions (
                        key, name, description, category, value_type, default_value,
                        min_value, max_value, options, required, deprecated, 
                        validation_rules, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    definition.key,
                    definition.name,
                    definition.description,
                    definition.category.value,
                    definition.value_type.value,
                    json.dumps(definition.default_value),
                    definition.min_value,
                    definition.max_value,
                    json.dumps(definition.options) if definition.options else None,
                    definition.required,
                    definition.deprecated,
                    json.dumps(definition.validation_rules),
                    json.dumps(definition.metadata)
                ))
            
            conn.commit()
            
        logger.info(f"User preferences database initialized at {self.storage_path}")
    
    async def get_preference(
        self,
        user_id: str,
        key: str,
        use_cache: bool = True
    ) -> Optional[Any]:
        """
        Get a specific user preference value
        
        Args:
            user_id: User identifier
            key: Preference key
            use_cache: Whether to use cached values
            
        Returns:
            Preference value if found, None otherwise
        """
        # Check cache first
        if use_cache and user_id in self._preferences_cache:
            cache_entry = self._preferences_cache[user_id]
            if (datetime.now() - cache_entry['timestamp']).seconds < self._cache_ttl:
                if key in cache_entry['preferences']:
                    return cache_entry['preferences'][key]['value']
        
        # Load from database
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("""
                SELECT value FROM user_preferences 
                WHERE user_id = ? AND preference_key = ?
            """, (user_id, key))
            
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return row[0]
        
        # Return default value if no user preference found
        if key in self.preference_definitions:
            return self.preference_definitions[key].default_value
        
        return None
    
    async def set_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
        source: str = "user",
        validate: bool = True
    ) -> bool:
        """
        Set a user preference value
        
        Args:
            user_id: User identifier
            key: Preference key
            value: Preference value
            source: Source of the preference (user, system, etc.)
            validate: Whether to validate the value
            
        Returns:
            True if set successfully
        """
        # Validate if requested
        if validate and not await self.validate_preference(key, value):
            logger.warning(f"Invalid preference value for {key}: {value}")
            return False
        
        # Convert value to JSON string
        try:
            value_str = json.dumps(value)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize preference value: {e}")
            return False
        
        with sqlite3.connect(self.storage_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_preferences (
                    user_id, preference_key, value, updated_at, source, validated
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                key,
                value_str,
                datetime.now().isoformat(),
                source,
                1 if validate else 0
            ))
            conn.commit()
        
        # Invalidate cache
        if user_id in self._preferences_cache:
            del self._preferences_cache[user_id]
        
        logger.info(f"Set preference {key} for user {user_id}")
        return True
    
    async def get_all_preferences(
        self,
        user_id: str,
        include_defaults: bool = True,
        include_deprecated: bool = False
    ) -> Dict[str, Any]:
        """
        Get all preferences for a user
        
        Args:
            user_id: User identifier
            include_defaults: Include default values for unset preferences
            include_deprecated: Include deprecated preferences
            
        Returns:
            Dictionary of all user preferences
        """
        preferences = {}
        
        with sqlite3.connect(self.storage_path) as conn:
            # Get user preferences
            cursor = conn.execute("""
                SELECT preference_key, value FROM user_preferences 
                WHERE user_id = ?
            """, (user_id,))
            
            for row in cursor.fetchall():
                key, value_str = row
                try:
                    preferences[key] = json.loads(value_str)
                except json.JSONDecodeError:
                    preferences[key] = value_str
        
        # Add default values for missing preferences
        if include_defaults:
            for key, definition in self.preference_definitions.items():
                if key not in preferences and not definition.deprecated:
                    preferences[key] = definition.default_value
                elif key in preferences and definition.deprecated and not include_deprecated:
                    # Remove deprecated preferences if not requested
                    preferences.pop(key, None)
        
        return preferences
    
    async def get_preferences_by_category(
        self,
        user_id: str,
        category: PreferenceCategory,
        include_defaults: bool = True
    ) -> Dict[str, Any]:
        """
        Get preferences for a specific category
        
        Args:
            user_id: User identifier
            category: Preference category
            include_defaults: Include default values
            
        Returns:
            Dictionary of category preferences
        """
        all_preferences = await self.get_all_preferences(user_id, include_defaults)
        
        category_preferences = {}
        for key, definition in self.preference_definitions.items():
            if (definition.category == category and 
                (key in all_preferences or include_defaults)):
                
                if include_defaults:
                    category_preferences[key] = all_preferences.get(key, definition.default_value)
                else:
                    category_preferences[key] = all_preferences.get(key)
        
        return category_preferences
    
    async def validate_preference(self, key: str, value: Any) -> bool:
        """
        Validate a preference value against its definition
        
        Args:
            key: Preference key
            value: Value to validate
            
        Returns:
            True if valid, False otherwise
        """
        if key not in self.preference_definitions:
            logger.warning(f"Unknown preference key: {key}")
            return False
        
        definition = self.preference_definitions[key]
        
        # Check if deprecated
        if definition.deprecated:
            logger.warning(f"Preference {key} is deprecated")
            return False
        
        # Type validation
        if definition.value_type == PreferenceType.STRING and not isinstance(value, str):
            return False
        elif definition.value_type == PreferenceType.INTEGER and not isinstance(value, int):
            return False
        elif definition.value_type == PreferenceType.FLOAT and not isinstance(value, (int, float)):
            return False
        elif definition.value_type == PreferenceType.BOOLEAN and not isinstance(value, bool):
            return False
        elif definition.value_type == PreferenceType.LIST and not isinstance(value, list):
            return False
        elif definition.value_type == PreferenceType.DICT and not isinstance(value, dict):
            return False
        
        # Range validation
        if definition.min_value is not None and value < definition.min_value:
            return False
        if definition.max_value is not None and value > definition.max_value:
            return False
        
        # Options validation
        if definition.options is not None and value not in definition.options:
            return False
        
        # Custom validation rules
        if definition.validation_rules:
            # This could be extended to support more complex validation
            pass
        
        return True
    
    async def reset_preference(self, user_id: str, key: str) -> bool:
        """
        Reset a preference to its default value
        
        Args:
            user_id: User identifier
            key: Preference key
            
        Returns:
            True if reset successfully
        """
        if key not in self.preference_definitions:
            return False
        
        default_value = self.preference_definitions[key].default_value
        return await self.set_preference(user_id, key, default_value, "system")
    
    async def reset_all_preferences(self, user_id: str) -> int:
        """
        Reset all user preferences to defaults
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of preferences reset
        """
        reset_count = 0
        
        # Get all user preferences
        user_preferences = await self.get_all_preferences(user_id, include_defaults=False)
        
        # Reset each preference to default
        for key in user_preferences.keys():
            if await self.reset_preference(user_id, key):
                reset_count += 1
        
        logger.info(f"Reset {reset_count} preferences for user {user_id}")
        return reset_count
    
    async def bulk_set_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any],
        source: str = "user",
        validate: bool = True
    ) -> Tuple[int, int]:
        """
        Set multiple preferences at once
        
        Args:
            user_id: User identifier
            preferences: Dictionary of preferences to set
            source: Source of the preferences
            validate: Whether to validate values
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        successful = 0
        failed = 0
        
        for key, value in preferences.items():
            if await self.set_preference(user_id, key, value, source, validate):
                successful += 1
            else:
                failed += 1
        
        logger.info(f"Bulk set preferences for user {user_id}: {successful} successful, {failed} failed")
        return successful, failed
    
    async def export_preferences(
        self,
        user_id: str,
        format: str = "json",
        include_metadata: bool = True
    ) -> str:
        """
        Export user preferences
        
        Args:
            user_id: User identifier
            format: Export format (json, csv, yaml)
            include_metadata: Whether to include metadata
            
        Returns:
            Exported preferences as string
        """
        preferences = await self.get_all_preferences(user_id)
        definitions = {}
        
        if include_metadata:
            for key, definition in self.preference_definitions.items():
                definitions[key] = {
                    "name": definition.name,
                    "description": definition.description,
                    "category": definition.category.value,
                    "value_type": definition.value_type.value,
                    "default_value": definition.default_value,
                    "deprecated": definition.deprecated
                }
        
        export_data = {
            "user_id": user_id,
            "exported_at": datetime.now().isoformat(),
            "preferences": preferences,
            "definitions": definitions if include_metadata else None,
            "format": format
        }
        
        if format == "json":
            return json.dumps(export_data, indent=2, default=str)
        elif format == "csv":
            # Simple CSV export
            lines = ["key,value,category"]
            for key, value in preferences.items():
                if key in self.preference_definitions:
                    category = self.preference_definitions[key].category.value
                    lines.append(f"{key},{value},{category}")
            return "\n".join(lines)
        elif format == "yaml":
            # This would require PyYAML, for now return JSON
            return json.dumps(export_data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def get_preference_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics about user preferences
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing preference statistics
        """
        preferences = await self.get_all_preferences(user_id)
        stats = {
            "total_preferences": len(preferences),
            "categories": {},
            "types": {},
            "last_updated": None,
            "sources": {}
        }
        
        # Analyze preferences by category and type
        for key, value in preferences.items():
            if key in self.preference_definitions:
                definition = self.preference_definitions[key]
                
                # Category stats
                category = definition.category.value
                stats["categories"][category] = stats["categories"].get(category, 0) + 1
                
                # Type stats
                value_type = definition.value_type.value
                stats["types"][value_type] = stats["types"].get(value_type, 0) + 1
        
        # Get last updated timestamp
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("""
                SELECT MAX(updated_at) FROM user_preferences WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            if row and row[0]:
                stats["last_updated"] = row[0]
        
        return stats
    
    async def add_preference_definition(self, definition: PreferenceDefinition) -> bool:
        """
        Add a new preference definition
        
        Args:
            definition: Preference definition to add
            
        Returns:
            True if added successfully
        """
        try:
            # Add to registry
            self.preference_definitions[definition.key] = definition
            
            # Add to database
            with sqlite3.connect(self.storage_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO preference_definitions (
                        key, name, description, category, value_type, default_value,
                        min_value, max_value, options, required, deprecated,
                        validation_rules, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    definition.key,
                    definition.name,
                    definition.description,
                    definition.category.value,
                    definition.value_type.value,
                    json.dumps(definition.default_value),
                    definition.min_value,
                    definition.max_value,
                    json.dumps(definition.options) if definition.options else None,
                    definition.required,
                    definition.deprecated,
                    json.dumps(definition.validation_rules),
                    json.dumps(definition.metadata)
                ))
                conn.commit()
            
            logger.info(f"Added preference definition: {definition.key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add preference definition: {e}")
            return False
    
    def get_preference_definitions(self) -> Dict[str, PreferenceDefinition]:
        """Get all preference definitions"""
        return self.preference_definitions.copy()
    
    async def close(self):
        """Close the preferences system and cleanup resources"""
        self._preferences_cache.clear()
        logger.info("User preferences system closed")