"""
Channel Preferences Management Module

This module provides comprehensive channel-specific preferences including:
- Channel configuration and behavior settings
- Channel-specific user preferences
- Communication style and formatting preferences
- Channel performance and reliability settings
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ChannelType(Enum):
    """Types of communication channels"""
    TEXT = "text"
    VOICE = "voice"
    VIDEO = "video"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"
    API = "api"


class ChannelStatus(Enum):
    """Channel status states"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    SUSPENDED = "suspended"
    ERROR = "error"


class MessageFormat(Enum):
    """Message formatting preferences"""
    PLAIN = "plain"
    MARKDOWN = "markdown"
    HTML = "html"
    RICH = "rich"
    CUSTOM = "custom"


class NotificationLevel(Enum):
    """Notification delivery levels"""
    NONE = "none"
    MENTIONS = "mentions"
    IMPORTANT = "important"
    ALL = "all"


@dataclass
class ChannelConfiguration:
    """Channel configuration settings"""
    channel_id: str
    name: str
    channel_type: ChannelType
    description: str
    enabled: bool = True
    status: ChannelStatus = ChannelStatus.ACTIVE
    endpoint_url: Optional[str] = None
    credentials: Dict[str, Any] = None
    settings: Dict[str, Any] = None
    rate_limits: Dict[str, int] = None
    retry_config: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        self.credentials = self.credentials or {}
        self.settings = self.settings or {}
        self.rate_limits = self.rate_limits or {}
        self.retry_config = self.retry_config or {}
        self.metadata = self.metadata or {}


@dataclass
class ChannelUserPreferences:
    """User-specific channel preferences"""
    user_id: str
    channel_id: str
    enabled: bool = True
    notification_level: NotificationLevel = NotificationLevel.ALL
    message_format: MessageFormat = MessageFormat.PLAIN
    auto_responses: bool = True
    custom_settings: Dict[str, Any] = None
    display_preferences: Dict[str, Any] = None
    privacy_settings: Dict[str, Any] = None
    performance_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        self.custom_settings = self.custom_settings or {}
        self.display_preferences = self.display_preferences or {}
        self.privacy_settings = self.privacy_settings or {}
        self.performance_settings = self.performance_settings or {}


class ChannelPreferences:
    """
    Comprehensive channel preferences management system
    
    Features:
    - Channel configuration and behavior management
    - User-specific channel preferences
    - Message formatting and notification settings
    - Performance and reliability tuning
    - Channel analytics and optimization
    """
    
    def __init__(self, storage_path: str = "data/channel_preferences.db"):
        """Initialize channel preferences system
        
        Args:
            storage_path: Path to SQLite database file
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Channel registry and cache
        self.channel_registry = {}
        self._init_database()
        
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.storage_path) as conn:
            # Channel configurations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS channel_configurations (
                    channel_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    channel_type TEXT NOT NULL,
                    description TEXT,
                    enabled INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'active',
                    endpoint_url TEXT,
                    credentials TEXT,
                    settings TEXT,
                    rate_limits TEXT,
                    retry_config TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # User channel preferences table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_channel_preferences (
                    user_id TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    notification_level TEXT DEFAULT 'all',
                    message_format TEXT DEFAULT 'plain',
                    auto_responses INTEGER DEFAULT 1,
                    custom_settings TEXT,
                    display_preferences TEXT,
                    privacy_settings TEXT,
                    performance_settings TEXT,
                    last_used TEXT,
                    usage_count INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, channel_id)
                )
            """)
            
            # Channel usage statistics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS channel_usage_stats (
                    channel_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    avg_response_time REAL DEFAULT 0.0,
                    PRIMARY KEY (channel_id, user_id, date)
                )
            """)
            
            # Channel health monitoring table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS channel_health (
                    channel_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_time REAL,
                    error_rate REAL,
                    uptime REAL,
                    metadata TEXT,
                    PRIMARY KEY (channel_id, timestamp)
                )
            """)
            
            conn.commit()
            
        logger.info(f"Channel preferences database initialized at {self.storage_path}")
    
    async def register_channel(self, config: ChannelConfiguration) -> bool:
        """
        Register a new channel configuration
        
        Args:
            config: Channel configuration to register
            
        Returns:
            True if registered successfully
        """
        try:
            # Add to registry
            self.channel_registry[config.channel_id] = config
            
            # Store in database
            with sqlite3.connect(self.storage_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO channel_configurations (
                        channel_id, name, channel_type, description,
                        enabled, status, endpoint_url, credentials,
                        settings, rate_limits, retry_config,
                        metadata, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    config.channel_id,
                    config.name,
                    config.channel_type.value,
                    config.description,
                    config.enabled,
                    config.status.value,
                    config.endpoint_url,
                    json.dumps(config.credentials),
                    json.dumps(config.settings),
                    json.dumps(config.rate_limits),
                    json.dumps(config.retry_config),
                    json.dumps(config.metadata),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            logger.info(f"Registered channel: {config.channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register channel {config.channel_id}: {e}")
            return False
    
    async def get_channel_config(self, channel_id: str) -> Optional[ChannelConfiguration]:
        """
        Get channel configuration
        
        Args:
            channel_id: Channel identifier
            
        Returns:
            Channel configuration if found
        """
        # Check registry first
        if channel_id in self.channel_registry:
            return self.channel_registry[channel_id]
        
        # Load from database
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM channel_configurations WHERE channel_id = ?
            """, (channel_id,))
            
            row = cursor.fetchone()
            if row:
                config = ChannelConfiguration(
                    channel_id=row[0],
                    name=row[1],
                    channel_type=ChannelType(row[2]),
                    description=row[3],
                    enabled=bool(row[4]),
                    status=ChannelStatus(row[5]),
                    endpoint_url=row[6],
                    credentials=json.loads(row[7]) if row[7] else {},
                    settings=json.loads(row[8]) if row[8] else {},
                    rate_limits=json.loads(row[9]) if row[9] else {},
                    retry_config=json.loads(row[10]) if row[10] else {},
                    metadata=json.loads(row[11]) if row[11] else {}
                )
                
                # Cache in registry
                self.channel_registry[channel_id] = config
                return config
        
        return None
    
    async def get_user_channel_preferences(
        self,
        user_id: str,
        channel_id: str
    ) -> Optional[ChannelUserPreferences]:
        """
        Get user-specific channel preferences
        
        Args:
            user_id: User identifier
            channel_id: Channel identifier
            
        Returns:
            User channel preferences if found
        """
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM user_channel_preferences 
                WHERE user_id = ? AND channel_id = ?
            """, (user_id, channel_id))
            
            row = cursor.fetchone()
            if row:
                preferences = ChannelUserPreferences(
                    user_id=row[0],
                    channel_id=row[1],
                    enabled=bool(row[2]),
                    notification_level=NotificationLevel(row[3]),
                    message_format=MessageFormat(row[4]),
                    auto_responses=bool(row[5]),
                    custom_settings=json.loads(row[6]) if row[6] else {},
                    display_preferences=json.loads(row[7]) if row[7] else {},
                    privacy_settings=json.loads(row[8]) if row[8] else {},
                    performance_settings=json.loads(row[9]) if row[9] else {}
                )
                return preferences
        
        return None
    
    async def set_user_channel_preferences(
        self,
        user_id: str,
        channel_id: str,
        enabled: Optional[bool] = None,
        notification_level: Optional[NotificationLevel] = None,
        message_format: Optional[MessageFormat] = None,
        auto_responses: Optional[bool] = None,
        custom_settings: Optional[Dict[str, Any]] = None,
        display_preferences: Optional[Dict[str, Any]] = None,
        privacy_settings: Optional[Dict[str, Any]] = None,
        performance_settings: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Set user-specific channel preferences
        
        Args:
            user_id: User identifier
            channel_id: Channel identifier
            enabled: Enable/disable channel
            notification_level: Notification level preference
            message_format: Message format preference
            auto_responses: Enable/disable auto responses
            custom_settings: Custom channel settings
            display_preferences: Display-related preferences
            privacy_settings: Privacy-related preferences
            performance_settings: Performance-related preferences
            
        Returns:
            True if set successfully
        """
        try:
            # Get existing preferences
            existing = await self.get_user_channel_preferences(user_id, channel_id)
            
            # Merge with existing or use defaults
            final_settings = {}
            if existing:
                final_settings = {
                    "enabled": enabled if enabled is not None else existing.enabled,
                    "notification_level": notification_level if notification_level is not None else existing.notification_level,
                    "message_format": message_format if message_format is not None else existing.message_format,
                    "auto_responses": auto_responses if auto_responses is not None else existing.auto_responses,
                    "custom_settings": {**existing.custom_settings, **(custom_settings or {})},
                    "display_preferences": {**existing.display_preferences, **(display_preferences or {})},
                    "privacy_settings": {**existing.privacy_settings, **(privacy_settings or {})},
                    "performance_settings": {**existing.performance_settings, **(performance_settings or {})}
                }
            else:
                # Get channel defaults
                channel_config = await self.get_channel_config(channel_id)
                defaults = channel_config.settings if channel_config else {}
                
                final_settings = {
                    "enabled": enabled if enabled is not None else True,
                    "notification_level": notification_level if notification_level is not None else NotificationLevel.ALL,
                    "message_format": message_format if message_format is not None else MessageFormat.PLAIN,
                    "auto_responses": auto_responses if auto_responses is not None else True,
                    "custom_settings": custom_settings or defaults.get("custom_settings", {}),
                    "display_preferences": display_preferences or defaults.get("display_preferences", {}),
                    "privacy_settings": privacy_settings or defaults.get("privacy_settings", {}),
                    "performance_settings": performance_settings or defaults.get("performance_settings", {})
                }
            
            with sqlite3.connect(self.storage_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO user_channel_preferences (
                        user_id, channel_id, enabled, notification_level,
                        message_format, auto_responses, custom_settings,
                        display_preferences, privacy_settings, performance_settings
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    channel_id,
                    final_settings["enabled"],
                    final_settings["notification_level"].value,
                    final_settings["message_format"].value,
                    final_settings["auto_responses"],
                    json.dumps(final_settings["custom_settings"]),
                    json.dumps(final_settings["display_preferences"]),
                    json.dumps(final_settings["privacy_settings"]),
                    json.dumps(final_settings["performance_settings"])
                ))
                conn.commit()
            
            logger.info(f"Updated channel preferences for user {user_id}, channel {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set user channel preferences: {e}")
            return False
    
    async def get_user_channels(
        self,
        user_id: str,
        enabled_only: bool = False,
        channel_type: Optional[ChannelType] = None,
        status: Optional[ChannelStatus] = None
    ) -> List[tuple]:
        """
        Get all channels available to a user with their preferences
        
        Args:
            user_id: User identifier
            enabled_only: Only return enabled channels
            channel_type: Filter by channel type
            status: Filter by channel status
            
        Returns:
            List of (channel_config, user_preferences) tuples
        """
        results = []
        
        with sqlite3.connect(self.storage_path) as conn:
            # Get all channel configurations
            cursor = conn.execute("""
                SELECT channel_id FROM channel_configurations
            """)
            
            for row in cursor.fetchall():
                channel_id = row[0]
                channel_config = await self.get_channel_config(channel_id)
                user_prefs = await self.get_user_channel_preferences(user_id, channel_id)
                
                if channel_config:
                    # Apply filters
                    if enabled_only and not (user_prefs.enabled if user_prefs else channel_config.enabled):
                        continue
                    if channel_type and channel_config.channel_type != channel_type:
                        continue
                    if status and channel_config.status != status:
                        continue
                    
                    results.append((channel_config, user_prefs))
        
        # Sort by channel type then by name
        results.sort(key=lambda x: (x[0].channel_type.value, x[0].name))
        
        return results
    
    async def get_active_channels(
        self,
        user_id: str,
        notification_level: Optional[NotificationLevel] = None
    ) -> List[tuple]:
        """
        Get active channels for a user
        
        Args:
            user_id: User identifier
            notification_level: Filter by notification level
            
        Returns:
            List of (channel_config, user_preferences) tuples for active channels
        """
        all_channels = await self.get_user_channels(user_id, enabled_only=True)
        
        active_channels = []
        for channel_config, user_prefs in all_channels:
            # Check if channel is actually active
            if channel_config.status != ChannelStatus.ACTIVE:
                continue
            
            # Check user notification preferences
            if (notification_level and user_prefs and 
                user_prefs.notification_level.value != notification_level.value and
                user_prefs.notification_level != NotificationLevel.ALL):
                continue
            
            active_channels.append((channel_config, user_prefs))
        
        return active_channels
    
    async def record_channel_usage(
        self,
        user_id: str,
        channel_id: str,
        success: bool,
        response_time: Optional[float] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Record channel usage statistics
        
        Args:
            user_id: User identifier
            channel_id: Channel identifier
            success: Whether the operation was successful
            response_time: Response time in seconds
            error_message: Error message if failed
            
        Returns:
            True if recorded successfully
        """
        try:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            
            with sqlite3.connect(self.storage_path) as conn:
                # Update user preferences with usage
                conn.execute("""
                    UPDATE user_channel_preferences 
                    SET last_used = ?, usage_count = usage_count + 1
                    WHERE user_id = ? AND channel_id = ?
                """, (now.isoformat(), user_id, channel_id))
                
                # Update daily statistics
                conn.execute("""
                    INSERT INTO channel_usage_stats (
                        channel_id, user_id, date, message_count, success_count,
                        error_count, avg_response_time
                    ) VALUES (?, ?, ?, 1, ?, ?, ?)
                    ON CONFLICT(channel_id, user_id, date) DO UPDATE SET
                        message_count = message_count + 1,
                        success_count = success_count + ?,
                        error_count = error_count + ?,
                        avg_response_time = (
                            (avg_response_time * (message_count - 1) + ?) / message_count
                        )
                """, (
                    channel_id,
                    user_id,
                    date_str,
                    1 if success else 0,
                    1 if not success else 0,
                    response_time or 0.0,
                    1 if success else 0,
                    1 if not success else 0,
                    response_time or 0.0
                ))
                
                conn.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record channel usage: {e}")
            return False
    
    async def update_channel_health(
        self,
        channel_id: str,
        status: ChannelStatus,
        response_time: Optional[float] = None,
        error_rate: Optional[float] = None,
        uptime: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update channel health monitoring data
        
        Args:
            channel_id: Channel identifier
            status: Current channel status
            response_time: Average response time
            error_rate: Current error rate
            uptime: Channel uptime percentage
            metadata: Additional health metadata
            
        Returns:
            True if updated successfully
        """
        try:
            with sqlite3.connect(self.storage_path) as conn:
                conn.execute("""
                    INSERT INTO channel_health (
                        channel_id, timestamp, status, response_time,
                        error_rate, uptime, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    channel_id,
                    datetime.now().isoformat(),
                    status.value,
                    response_time,
                    error_rate,
                    uptime,
                    json.dumps(metadata or {})
                ))
                conn.commit()
            
            # Update cached channel status
            if channel_id in self.channel_registry:
                self.channel_registry[channel_id].status = status
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update channel health: {e}")
            return False
    
    async def get_channel_analytics(
        self,
        user_id: str,
        channel_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get analytics for a specific channel
        
        Args:
            user_id: User identifier
            channel_id: Channel identifier
            days: Number of days to analyze
            
        Returns:
            Dictionary containing analytics data
        """
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        with sqlite3.connect(self.storage_path) as conn:
            # Get usage statistics
            cursor = conn.execute("""
                SELECT date, message_count, success_count, error_count, avg_response_time
                FROM channel_usage_stats
                WHERE user_id = ? AND channel_id = ? AND date >= ?
                ORDER BY date ASC
            """, (user_id, channel_id, start_date))
            
            daily_stats = []
            total_messages = 0
            total_success = 0
            total_errors = 0
            total_response_time = 0
            days_with_usage = 0
            
            for row in cursor.fetchall():
                date, messages, success, errors, avg_time = row
                daily_stats.append({
                    "date": date,
                    "message_count": messages,
                    "success_count": success,
                    "error_count": errors,
                    "avg_response_time": avg_time,
                    "success_rate": success / messages if messages > 0 else 0
                })
                
                if messages > 0:
                    total_messages += messages
                    total_success += success
                    total_errors += errors
                    total_response_time += avg_time
                    days_with_usage += 1
            
            # Get current preferences
            prefs = await self.get_user_channel_preferences(user_id, channel_id)
            
            # Get recent health data
            cursor = conn.execute("""
                SELECT status, avg(response_time), avg(error_rate), avg(uptime)
                FROM channel_health
                WHERE channel_id = ? AND timestamp >= ?
                GROUP BY status
                ORDER BY timestamp DESC
                LIMIT 5
            """, (channel_id, start_date))
            
            recent_health = []
            for row in cursor.fetchall():
                recent_health.append({
                    "status": row[0],
                    "avg_response_time": row[1],
                    "avg_error_rate": row[2],
                    "avg_uptime": row[3]
                })
        
        return {
            "channel_id": channel_id,
            "user_id": user_id,
            "period_days": days,
            "total_messages": total_messages,
            "total_success": total_success,
            "total_errors": total_errors,
            "overall_success_rate": total_success / total_messages if total_messages > 0 else 0,
            "average_response_time": total_response_time / days_with_usage if days_with_usage > 0 else 0,
            "daily_stats": daily_stats,
            "recent_health": recent_health,
            "user_preferences": {
                "enabled": prefs.enabled if prefs else True,
                "notification_level": prefs.notification_level.value if prefs else "all",
                "message_format": prefs.message_format.value if prefs else "plain",
                "auto_responses": prefs.auto_responses if prefs else True
            },
            "generated_at": datetime.now().isoformat()
        }
    
    async def optimize_channel_settings(
        self,
        user_id: str,
        channel_id: str
    ) -> Dict[str, Any]:
        """
        Optimize channel settings based on usage analytics
        
        Args:
            user_id: User identifier
            channel_id: Channel identifier
            
        Returns:
            Dictionary containing optimization recommendations
        """
        analytics = await self.get_channel_analytics(user_id, channel_id)
        recommendations = {}
        
        # Analyze success rate
        if analytics["overall_success_rate"] < 0.9:
            recommendations["reliability"] = {
                "issue": "Low success rate",
                "recommendation": "Check channel configuration and retry settings",
                "current_rate": analytics["overall_success_rate"]
            }
        
        # Analyze response time
        if analytics["average_response_time"] > 5.0:  # > 5 seconds
            recommendations["performance"] = {
                "issue": "High response time",
                "recommendation": "Consider using a different channel or optimizing settings",
                "current_time": analytics["average_response_time"]
            }
        
        # Analyze usage patterns
        if analytics["total_messages"] == 0:
            recommendations["usage"] = {
                "issue": "Channel never used",
                "recommendation": "Consider disabling unused channel",
                "message_count": 0
            }
        
        # Check for error patterns
        error_rate = analytics["total_errors"] / analytics["total_messages"] if analytics["total_messages"] > 0 else 0
        if error_rate > 0.1:  # > 10% error rate
            recommendations["errors"] = {
                "issue": "High error rate",
                "recommendation": "Review error logs and channel configuration",
                "error_rate": error_rate
            }
        
        return {
            "channel_id": channel_id,
            "user_id": user_id,
            "analytics": analytics,
            "recommendations": recommendations,
            "optimized_at": datetime.now().isoformat()
        }
    
    async def get_channel_types(self) -> List[str]:
        """
        Get all available channel types
        
        Returns:
            List of channel type names
        """
        return [channel_type.value for channel_type in ChannelType]
    
    async def search_channels(
        self,
        query: str,
        channel_type: Optional[ChannelType] = None,
        enabled_only: bool = False
    ) -> List[ChannelConfiguration]:
        """
        Search for channels by name or description
        
        Args:
            query: Search query
            channel_type: Filter by channel type
            enabled_only: Only return enabled channels
            
        Returns:
            List of matching channel configurations
        """
        channels = []
        query_lower = query.lower()
        
        with sqlite3.connect(self.storage_path) as conn:
            base_query = """
                SELECT channel_id FROM channel_configurations 
                WHERE (LOWER(name) LIKE ? OR LOWER(description) LIKE ?)
            """
            params = [f"%{query_lower}%", f"%{query_lower}%"]
            
            if channel_type:
                base_query += " AND channel_type = ?"
                params.append(channel_type.value)
            
            cursor = conn.execute(base_query, params)
            
            for row in cursor.fetchall():
                channel_id = row[0]
                config = await self.get_channel_config(channel_id)
                
                if config and (not enabled_only or config.enabled):
                    channels.append(config)
        
        return channels
    
    async def disable_channel(
        self,
        user_id: str,
        channel_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Disable a channel for a user
        
        Args:
            user_id: User identifier
            channel_id: Channel identifier
            reason: Reason for disabling
            
        Returns:
            True if disabled successfully
        """
        try:
            with sqlite3.connect(self.storage_path) as conn:
                conn.execute("""
                    UPDATE user_channel_preferences 
                    SET enabled = 0 
                    WHERE user_id = ? AND channel_id = ?
                """, (user_id, channel_id))
                
                conn.commit()
            
            logger.info(f"Disabled channel {channel_id} for user {user_id}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable channel: {e}")
            return False
    
    async def get_channel_health_summary(self, channel_id: str, hours: int = 24) -> Dict[str, Any]:
        """
        Get health summary for a channel
        
        Args:
            channel_id: Channel identifier
            hours: Number of hours to analyze
            
        Returns:
            Dictionary containing health summary
        """
        start_time = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("""
                SELECT status, avg(response_time), avg(error_rate), avg(uptime), count(*)
                FROM channel_health
                WHERE channel_id = ? AND timestamp >= ?
                GROUP BY status
            """, (channel_id, start_time.isoformat()))
            
            status_summary = {}
            total_checks = 0
            
            for row in cursor.fetchall():
                status, avg_response, avg_error_rate, avg_uptime, count = row
                status_summary[status] = {
                    "count": count,
                    "avg_response_time": avg_response,
                    "avg_error_rate": avg_error_rate,
                    "avg_uptime": avg_uptime
                }
                total_checks += count
            
            # Get current status
            cursor = conn.execute("""
                SELECT status FROM channel_health
                WHERE channel_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (channel_id,))
            
            row = cursor.fetchone()
            current_status = row[0] if row else "unknown"
        
        return {
            "channel_id": channel_id,
            "period_hours": hours,
            "current_status": current_status,
            "total_checks": total_checks,
            "status_breakdown": status_summary,
            "generated_at": datetime.now().isoformat()
        }
    
    async def close(self):
        """Close the channel preferences system"""
        self.channel_registry.clear()
        logger.info("Channel preferences system closed")