"""
Skill Preferences Management Module

This module provides comprehensive skill-specific preferences including:
- Individual skill configuration and behavior
- Skill activation and priority settings
- Skill performance tuning
- Skill compatibility and dependencies
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


class SkillStatus(Enum):
    """Skill status states"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class SkillPriority(Enum):
    """Skill execution priority"""
    LOWEST = 1
    LOW = 2
    NORMAL = 3
    HIGH = 4
    HIGHEST = 5


class SkillTrigger(Enum):
    """Skill trigger types"""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    CONTEXTUAL = "contextual"
    SCHEDULED = "scheduled"


@dataclass
class SkillConfiguration:
    """Skill configuration settings"""
    skill_id: str
    name: str
    version: str
    description: str
    category: str
    enabled: bool = True
    priority: SkillPriority = SkillPriority.NORMAL
    trigger_type: SkillTrigger = SkillTrigger.MANUAL
    parameters: Dict[str, Any] = None
    dependencies: List[str] = None
    compatibility: List[str] = None
    performance_config: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        self.parameters = self.parameters or {}
        self.dependencies = self.dependencies or []
        self.compatibility = self.compatibility or []
        self.performance_config = self.performance_config or {}
        self.metadata = self.metadata or {}


@dataclass
class SkillUsage:
    """Skill usage statistics"""
    skill_id: str
    user_id: str
    last_used: datetime
    usage_count: int = 0
    success_rate: float = 0.0
    avg_execution_time: float = 0.0
    error_count: int = 0
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        self.performance_metrics = self.performance_metrics or {}


class SkillPreferences:
    """
    Comprehensive skill preferences management system
    
    Features:
    - Skill-specific configuration and behavior settings
    - Skill activation, priority, and trigger management
    - Performance tuning and optimization settings
    - Dependency and compatibility tracking
    - Usage analytics and optimization
    """
    
    def __init__(self, storage_path: str = "data/skill_preferences.db"):
        """Initialize skill preferences system
        
        Args:
            storage_path: Path to SQLite database file
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Skill registry and cache
        self.skill_registry = {}
        self._init_database()
        
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.storage_path) as conn:
            # Skill configurations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_configurations (
                    skill_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    description TEXT,
                    category TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    priority INTEGER DEFAULT 3,
                    trigger_type TEXT DEFAULT 'manual',
                    parameters TEXT,
                    dependencies TEXT,
                    compatibility TEXT,
                    performance_config TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # User skill preferences table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_skill_preferences (
                    user_id TEXT NOT NULL,
                    skill_id TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    priority INTEGER DEFAULT 3,
                    custom_parameters TEXT,
                    usage_count INTEGER DEFAULT 0,
                    last_used TEXT,
                    success_rate REAL DEFAULT 0.0,
                    avg_execution_time REAL DEFAULT 0.0,
                    error_count INTEGER DEFAULT 0,
                    performance_metrics TEXT,
                    PRIMARY KEY (user_id, skill_id)
                )
            """)
            
            # Skill usage statistics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_usage_stats (
                    skill_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    usage_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    total_execution_time REAL DEFAULT 0.0,
                    error_count INTEGER DEFAULT 0,
                    PRIMARY KEY (skill_id, user_id, date)
                )
            """)
            
            conn.commit()
            
        logger.info(f"Skill preferences database initialized at {self.storage_path}")
    
    async def register_skill(self, config: SkillConfiguration) -> bool:
        """
        Register a new skill configuration
        
        Args:
            config: Skill configuration to register
            
        Returns:
            True if registered successfully
        """
        try:
            # Add to registry
            self.skill_registry[config.skill_id] = config
            
            # Store in database
            with sqlite3.connect(self.storage_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO skill_configurations (
                        skill_id, name, version, description, category,
                        enabled, priority, trigger_type, parameters,
                        dependencies, compatibility, performance_config,
                        metadata, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    config.skill_id,
                    config.name,
                    config.version,
                    config.description,
                    config.category,
                    config.enabled,
                    config.priority.value,
                    config.trigger_type.value,
                    json.dumps(config.parameters),
                    json.dumps(config.dependencies),
                    json.dumps(config.compatibility),
                    json.dumps(config.performance_config),
                    json.dumps(config.metadata),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            logger.info(f"Registered skill: {config.skill_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register skill {config.skill_id}: {e}")
            return False
    
    async def get_skill_config(self, skill_id: str) -> Optional[SkillConfiguration]:
        """
        Get skill configuration
        
        Args:
            skill_id: Skill identifier
            
        Returns:
            Skill configuration if found
        """
        # Check registry first
        if skill_id in self.skill_registry:
            return self.skill_registry[skill_id]
        
        # Load from database
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM skill_configurations WHERE skill_id = ?
            """, (skill_id,))
            
            row = cursor.fetchone()
            if row:
                config = SkillConfiguration(
                    skill_id=row[0],
                    name=row[1],
                    version=row[2],
                    description=row[3],
                    category=row[4],
                    enabled=bool(row[5]),
                    priority=SkillPriority(row[6]),
                    trigger_type=SkillTrigger(row[7]),
                    parameters=json.loads(row[8]) if row[8] else {},
                    dependencies=json.loads(row[9]) if row[9] else [],
                    compatibility=json.loads(row[10]) if row[10] else [],
                    performance_config=json.loads(row[11]) if row[11] else {},
                    metadata=json.loads(row[12]) if row[12] else {}
                )
                
                # Cache in registry
                self.skill_registry[skill_id] = config
                return config
        
        return None
    
    async def get_user_skill_config(
        self,
        user_id: str,
        skill_id: str
    ) -> Optional[SkillConfiguration]:
        """
        Get user-specific skill configuration
        
        Args:
            user_id: User identifier
            skill_id: Skill identifier
            
        Returns:
            Combined skill configuration with user overrides
        """
        # Get base configuration
        base_config = await self.get_skill_config(skill_id)
        if not base_config:
            return None
        
        # Get user preferences
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("""
                SELECT enabled, priority, custom_parameters 
                FROM user_skill_preferences 
                WHERE user_id = ? AND skill_id = ?
            """, (user_id, skill_id))
            
            row = cursor.fetchone()
            if row:
                # Create user-specific configuration
                user_config = SkillConfiguration(
                    skill_id=base_config.skill_id,
                    name=base_config.name,
                    version=base_config.version,
                    description=base_config.description,
                    category=base_config.category,
                    enabled=bool(row[0]),
                    priority=SkillPriority(row[1]) if row[1] else base_config.priority,
                    trigger_type=base_config.trigger_type,
                    parameters={**base_config.parameters, **json.loads(row[2]) if row[2] else {}},
                    dependencies=base_config.dependencies.copy(),
                    compatibility=base_config.compatibility.copy(),
                    performance_config=base_config.performance_config.copy(),
                    metadata=base_config.metadata.copy()
                )
                return user_config
        
        # Return base configuration if no user preferences
        return base_config
    
    async def set_user_skill_preference(
        self,
        user_id: str,
        skill_id: str,
        enabled: Optional[bool] = None,
        priority: Optional[SkillPriority] = None,
        custom_parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Set user-specific skill preferences
        
        Args:
            user_id: User identifier
            skill_id: Skill identifier
            enabled: Enable/disable skill
            priority: Skill execution priority
            custom_parameters: Custom parameter overrides
            
        Returns:
            True if set successfully
        """
        try:
            # Check if skill exists
            base_config = await self.get_skill_config(skill_id)
            if not base_config:
                logger.warning(f"Skill not found: {skill_id}")
                return False
            
            with sqlite3.connect(self.storage_path) as conn:
                # Get existing preferences
                cursor = conn.execute("""
                    SELECT enabled, priority, custom_parameters 
                    FROM user_skill_preferences 
                    WHERE user_id = ? AND skill_id = ?
                """, (user_id, skill_id))
                
                row = cursor.fetchone()
                
                if row:
                    # Update existing preferences
                    current_enabled = bool(row[0]) if row[0] is not None else base_config.enabled
                    current_priority = row[1] if row[1] is not None else base_config.priority.value
                    current_params = json.loads(row[2]) if row[2] else {}
                    
                    # Apply updates
                    new_enabled = enabled if enabled is not None else current_enabled
                    new_priority = priority.value if priority is not None else current_priority
                    new_params = {**current_params, **(custom_parameters or {})}
                    
                    conn.execute("""
                        UPDATE user_skill_preferences 
                        SET enabled = ?, priority = ?, custom_parameters = ?
                        WHERE user_id = ? AND skill_id = ?
                    """, (new_enabled, new_priority, json.dumps(new_params), user_id, skill_id))
                else:
                    # Insert new preferences
                    conn.execute("""
                        INSERT INTO user_skill_preferences (
                            user_id, skill_id, enabled, priority, custom_parameters
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        user_id,
                        skill_id,
                        enabled if enabled is not None else base_config.enabled,
                        priority.value if priority is not None else base_config.priority.value,
                        json.dumps(custom_parameters or {})
                    ))
                
                conn.commit()
            
            logger.info(f"Updated skill preferences for user {user_id}, skill {skill_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set user skill preference: {e}")
            return False
    
    async def get_user_skills(
        self,
        user_id: str,
        enabled_only: bool = False,
        category: Optional[str] = None
    ) -> List[SkillConfiguration]:
        """
        Get all skills available to a user
        
        Args:
            user_id: User identifier
            enabled_only: Only return enabled skills
            category: Filter by category
            
        Returns:
            List of skill configurations
        """
        skills = []
        
        with sqlite3.connect(self.storage_path) as conn:
            # Get all skill configurations
            cursor = conn.execute("""
                SELECT skill_id FROM skill_configurations
            """)
            
            for row in cursor.fetchall():
                skill_id = row[0]
                user_config = await self.get_user_skill_config(user_id, skill_id)
                
                if user_config:
                    # Apply filters
                    if enabled_only and not user_config.enabled:
                        continue
                    if category and user_config.category != category:
                        continue
                    
                    skills.append(user_config)
        
        # Sort by priority (highest first) then by name
        skills.sort(key=lambda x: (-x.priority.value, x.name))
        
        return skills
    
    async def get_active_skills(
        self,
        user_id: str,
        trigger_type: Optional[SkillTrigger] = None
    ) -> List[SkillConfiguration]:
        """
        Get active skills for a user
        
        Args:
            user_id: User identifier
            trigger_type: Filter by trigger type
            
        Returns:
            List of active skill configurations
        """
        all_skills = await self.get_user_skills(user_id, enabled_only=True)
        
        active_skills = []
        for skill in all_skills:
            # Check if skill is actually active based on dependencies
            if await self._check_skill_dependencies(user_id, skill):
                if trigger_type is None or skill.trigger_type == trigger_type:
                    active_skills.append(skill)
        
        return active_skills
    
    async def record_skill_usage(
        self,
        user_id: str,
        skill_id: str,
        execution_time: float,
        success: bool,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Record skill usage statistics
        
        Args:
            user_id: User identifier
            skill_id: Skill identifier
            execution_time: Time taken to execute
            success: Whether execution was successful
            error_message: Error message if failed
            
        Returns:
            True if recorded successfully
        """
        try:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            
            with sqlite3.connect(self.storage_path) as conn:
                # Update or insert usage statistics
                conn.execute("""
                    INSERT INTO user_skill_preferences (
                        user_id, skill_id, usage_count, last_used,
                        avg_execution_time, error_count
                    ) VALUES (?, ?, 1, ?, ?, ?)
                    ON CONFLICT(user_id, skill_id) DO UPDATE SET
                        usage_count = usage_count + 1,
                        last_used = excluded.last_used,
                        avg_execution_time = (
                            (avg_execution_time * (usage_count - 1) + excluded.avg_execution_time) / usage_count
                        ),
                        error_count = error_count + (1 - ?)
                """, (
                    user_id,
                    skill_id,
                    now.isoformat(),
                    execution_time,
                    1 if not success else 0,
                    1 if not success else 0
                ))
                
                # Update daily statistics
                conn.execute("""
                    INSERT INTO skill_usage_stats (
                        skill_id, user_id, date, usage_count, success_count,
                        total_execution_time, error_count
                    ) VALUES (?, ?, ?, 1, ?, ?, ?)
                    ON CONFLICT(skill_id, user_id, date) DO UPDATE SET
                        usage_count = usage_count + 1,
                        success_count = success_count + ?,
                        total_execution_time = total_execution_time + ?,
                        error_count = error_count + ?
                """, (
                    skill_id,
                    user_id,
                    date_str,
                    1 if success else 0,
                    execution_time,
                    1 if not success else 0,
                    1 if success else 0,
                    execution_time,
                    1 if not success else 0
                ))
                
                conn.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record skill usage: {e}")
            return False
    
    async def get_skill_analytics(
        self,
        user_id: str,
        skill_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get analytics for a specific skill
        
        Args:
            user_id: User identifier
            skill_id: Skill identifier
            days: Number of days to analyze
            
        Returns:
            Dictionary containing analytics data
        """
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        with sqlite3.connect(self.storage_path) as conn:
            # Get usage statistics
            cursor = conn.execute("""
                SELECT date, usage_count, success_count, total_execution_time, error_count
                FROM skill_usage_stats
                WHERE user_id = ? AND skill_id = ? AND date >= ?
                ORDER BY date ASC
            """, (user_id, skill_id, start_date))
            
            daily_stats = []
            total_usage = 0
            total_success = 0
            total_time = 0
            total_errors = 0
            
            for row in cursor.fetchall():
                date, usage, success, exec_time, errors = row
                daily_stats.append({
                    "date": date,
                    "usage_count": usage,
                    "success_count": success,
                    "error_count": errors,
                    "avg_execution_time": exec_time / usage if usage > 0 else 0,
                    "success_rate": success / usage if usage > 0 else 0
                })
                
                total_usage += usage
                total_success += success
                total_time += exec_time
                total_errors += errors
            
            # Get overall statistics
            cursor = conn.execute("""
                SELECT usage_count, last_used, success_rate, avg_execution_time, error_count
                FROM user_skill_preferences
                WHERE user_id = ? AND skill_id = ?
            """, (user_id, skill_id))
            
            row = cursor.fetchone()
            if row:
                usage_count, last_used, success_rate, avg_time, error_count = row
            else:
                usage_count = last_used = success_rate = avg_time = error_count = 0
        
        return {
            "skill_id": skill_id,
            "user_id": user_id,
            "period_days": days,
            "total_usage": total_usage,
            "total_success": total_success,
            "total_errors": total_errors,
            "overall_success_rate": total_success / total_usage if total_usage > 0 else 0,
            "average_execution_time": total_time / total_usage if total_usage > 0 else 0,
            "daily_stats": daily_stats,
            "last_used": last_used,
            "generated_at": datetime.now().isoformat()
        }
    
    async def optimize_skill_settings(
        self,
        user_id: str,
        skill_id: str
    ) -> Dict[str, Any]:
        """
        Optimize skill settings based on usage analytics
        
        Args:
            user_id: User identifier
            skill_id: Skill identifier
            
        Returns:
            Dictionary containing optimization recommendations
        """
        analytics = await self.get_skill_analytics(user_id, skill_id)
        recommendations = {}
        
        # Analyze success rate
        if analytics["overall_success_rate"] < 0.8:
            recommendations["success_rate"] = {
                "issue": "Low success rate",
                "recommendation": "Consider adjusting skill parameters or disabling",
                "current_rate": analytics["overall_success_rate"]
            }
        
        # Analyze execution time
        if analytics["average_execution_time"] > 10.0:  # > 10 seconds
            recommendations["performance"] = {
                "issue": "High execution time",
                "recommendation": "Optimize skill performance or increase timeout",
                "current_time": analytics["average_execution_time"]
            }
        
        # Analyze usage patterns
        if analytics["total_usage"] == 0:
            recommendations["usage"] = {
                "issue": "Skill never used",
                "recommendation": "Consider disabling unused skill",
                "usage_count": 0
            }
        elif analytics["total_usage"] < 5:
            recommendations["usage"] = {
                "issue": "Low usage",
                "recommendation": "Skill may not be relevant",
                "usage_count": analytics["total_usage"]
            }
        
        # Performance tuning recommendations
        config = await self.get_user_skill_config(user_id, skill_id)
        if config and config.performance_config:
            if "timeout" in config.performance_config:
                current_timeout = config.performance_config["timeout"]
                if analytics["average_execution_time"] > current_timeout * 0.8:
                    recommendations["timeout"] = {
                        "issue": "Execution time close to timeout",
                        "recommendation": f"Increase timeout from {current_timeout}",
                        "suggested_timeout": int(analytics["average_execution_time"] * 1.5)
                    }
        
        return {
            "skill_id": skill_id,
            "user_id": user_id,
            "analytics": analytics,
            "recommendations": recommendations,
            "optimized_at": datetime.now().isoformat()
        }
    
    async def _check_skill_dependencies(
        self,
        user_id: str,
        skill: SkillConfiguration
    ) -> bool:
        """
        Check if skill dependencies are satisfied
        
        Args:
            user_id: User identifier
            skill: Skill configuration
            
        Returns:
            True if dependencies are satisfied
        """
        if not skill.dependencies:
            return True
        
        # Get all user skills
        user_skills = await self.get_user_skills(user_id, enabled_only=True)
        enabled_skill_ids = {s.skill_id for s in user_skills}
        
        # Check if all dependencies are enabled
        for dependency in skill.dependencies:
            if dependency not in enabled_skill_ids:
                return False
        
        return True
    
    async def get_skill_categories(self) -> List[str]:
        """
        Get all available skill categories
        
        Returns:
            List of category names
        """
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("""
                SELECT DISTINCT category FROM skill_configurations ORDER BY category
            """)
            return [row[0] for row in cursor.fetchall()]
    
    async def search_skills(
        self,
        query: str,
        category: Optional[str] = None,
        enabled_only: bool = False
    ) -> List[SkillConfiguration]:
        """
        Search for skills by name or description
        
        Args:
            query: Search query
            category: Filter by category
            enabled_only: Only return enabled skills
            
        Returns:
            List of matching skill configurations
        """
        skills = []
        query_lower = query.lower()
        
        with sqlite3.connect(self.storage_path) as conn:
            base_query = """
                SELECT skill_id FROM skill_configurations 
                WHERE (LOWER(name) LIKE ? OR LOWER(description) LIKE ?)
            """
            params = [f"%{query_lower}%", f"%{query_lower}%"]
            
            if category:
                base_query += " AND category = ?"
                params.append(category)
            
            cursor = conn.execute(base_query, params)
            
            for row in cursor.fetchall():
                skill_id = row[0]
                config = await self.get_skill_config(skill_id)
                
                if config and (not enabled_only or config.enabled):
                    skills.append(config)
        
        return skills
    
    async def disable_skill(
        self,
        user_id: str,
        skill_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Disable a skill for a user
        
        Args:
            user_id: User identifier
            skill_id: Skill identifier
            reason: Reason for disabling
            
        Returns:
            True if disabled successfully
        """
        try:
            with sqlite3.connect(self.storage_path) as conn:
                conn.execute("""
                    UPDATE user_skill_preferences 
                    SET enabled = 0 
                    WHERE user_id = ? AND skill_id = ?
                """, (user_id, skill_id))
                
                conn.commit()
            
            logger.info(f"Disabled skill {skill_id} for user {user_id}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable skill: {e}")
            return False
    
    async def close(self):
        """Close the skill preferences system"""
        self.skill_registry.clear()
        logger.info("Skill preferences system closed")