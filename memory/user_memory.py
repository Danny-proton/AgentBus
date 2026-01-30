"""
User Memory Management Module

This module provides comprehensive user memory management capabilities including:
- Long-term memory storage and retrieval
- Memory categorization and tagging
- Memory persistence and cleanup
- Memory migration and version management
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

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of user memories"""
    PERSONAL_INFO = "personal_info"
    PREFERENCES = "preferences"
    INTERESTS = "interests"
    HISTORY = "history"
    CONTEXT = "context"
    LEARNED_FACTS = "learned_facts"
    INTERACTIONS = "interactions"
    CUSTOM = "custom"


class MemoryPriority(Enum):
    """Memory priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    ARCHIVED = 5


@dataclass
class MemoryEntry:
    """Individual memory entry structure"""
    id: str
    user_id: str
    memory_type: MemoryType
    priority: MemoryPriority
    content: Dict[str, Any]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    version: int = 1
    
    def __post_init__(self):
        if isinstance(self.memory_type, str):
            self.memory_type = MemoryType(self.memory_type)
        if isinstance(self.priority, int):
            self.priority = MemoryPriority(self.priority)
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        if isinstance(self.last_accessed, str):
            self.last_accessed = datetime.fromisoformat(self.last_accessed)
        if isinstance(self.expires_at, str):
            self.expires_at = datetime.fromisoformat(self.expires_at)


class UserMemory:
    """
    Comprehensive user memory management system
    
    Features:
    - Persistent storage in SQLite database
    - Memory categorization and tagging
    - Priority-based memory management
    - Automatic cleanup and expiration
    - Memory migration and versioning
    - Search and retrieval capabilities
    """
    
    def __init__(self, storage_path: str = "data/user_memory.db"):
        """Initialize user memory system
        
        Args:
            storage_path: Path to SQLite database file
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        self._cleanup_task = None
        
        # Start background cleanup task
        self._start_cleanup_task()
    
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.storage_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    expires_at TEXT,
                    version INTEGER DEFAULT 1,
                    INDEX idx_user_id (user_id),
                    INDEX idx_memory_type (memory_type),
                    INDEX idx_priority (priority),
                    INDEX idx_created_at (created_at),
                    INDEX idx_expires_at (expires_at)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_name TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    version_from INTEGER NOT NULL,
                    version_to INTEGER NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_stats (
                    user_id TEXT PRIMARY KEY,
                    total_memories INTEGER DEFAULT 0,
                    memory_types_count TEXT,
                    last_cleanup TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.commit()
            
        logger.info(f"User memory database initialized at {self.storage_path}")
    
    async def store_memory(
        self,
        user_id: str,
        memory_type: MemoryType,
        content: Dict[str, Any],
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        tags: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None
    ) -> str:
        """
        Store a new memory entry
        
        Args:
            user_id: Unique user identifier
            memory_type: Type of memory
            content: Memory content as dictionary
            priority: Memory priority level
            tags: Optional list of tags
            expires_at: Optional expiration datetime
            
        Returns:
            Memory entry ID
        """
        memory_id = self._generate_memory_id(user_id, content)
        tags = tags or []
        
        memory_entry = MemoryEntry(
            id=memory_id,
            user_id=user_id,
            memory_type=memory_type,
            priority=priority,
            content=content,
            tags=tags,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            expires_at=expires_at
        )
        
        with sqlite3.connect(self.storage_path) as conn:
            conn.execute("""
                INSERT INTO memories (
                    id, user_id, memory_type, priority, content, tags,
                    created_at, updated_at, expires_at, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_entry.id,
                memory_entry.user_id,
                memory_entry.memory_type.value,
                memory_entry.priority.value,
                json.dumps(memory_entry.content),
                json.dumps(memory_entry.tags),
                memory_entry.created_at.isoformat(),
                memory_entry.updated_at.isoformat(),
                memory_entry.expires_at.isoformat() if memory_entry.expires_at else None,
                memory_entry.version
            ))
            conn.commit()
        
        # Update user statistics
        await self._update_user_stats(user_id)
        
        logger.info(f"Stored memory {memory_id} for user {user_id}")
        return memory_id
    
    async def retrieve_memory(
        self,
        user_id: str,
        memory_id: str
    ) -> Optional[MemoryEntry]:
        """
        Retrieve a specific memory entry
        
        Args:
            user_id: User identifier
            memory_id: Memory entry ID
            
        Returns:
            Memory entry if found, None otherwise
        """
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM memories WHERE id = ? AND user_id = ?
            """, (memory_id, user_id))
            
            row = cursor.fetchone()
            if row:
                memory = self._row_to_memory_entry(row)
                await self._update_access_stats(memory_id)
                return memory
        
        return None
    
    async def search_memories(
        self,
        user_id: str,
        query: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        priority_min: Optional[MemoryPriority] = None,
        limit: int = 50,
        include_expired: bool = False
    ) -> List[MemoryEntry]:
        """
        Search for user memories based on criteria
        
        Args:
            user_id: User identifier
            query: Text search in memory content
            memory_type: Filter by memory type
            tags: Filter by tags
            priority_min: Minimum priority level
            limit: Maximum number of results
            include_expired: Whether to include expired memories
            
        Returns:
            List of matching memory entries
        """
        sql_conditions = ["user_id = ?"]
        params = [user_id]
        
        # Add text search
        if query:
            sql_conditions.append("(content LIKE ? OR tags LIKE ?)")
            search_term = f"%{query}%"
            params.extend([search_term, search_term])
        
        # Add memory type filter
        if memory_type:
            sql_conditions.append("memory_type = ?")
            params.append(memory_type.value)
        
        # Add tags filter
        if tags:
            for tag in tags:
                sql_conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")
        
        # Add priority filter
        if priority_min:
            sql_conditions.append("priority <= ?")
            params.append(priority_min.value)
        
        # Exclude expired if requested
        if not include_expired:
            sql_conditions.append("(expires_at IS NULL OR expires_at > ?)")
            params.append(datetime.now().isoformat())
        
        where_clause = " AND ".join(sql_conditions)
        
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute(f"""
                SELECT * FROM memories 
                WHERE {where_clause}
                ORDER BY priority ASC, created_at DESC
                LIMIT ?
            """, (*params, limit))
            
            memories = [self._row_to_memory_entry(row) for row in cursor.fetchall()]
            
            # Update access stats for retrieved memories
            for memory in memories:
                await self._update_access_stats(memory.id)
            
            return memories
    
    async def update_memory(
        self,
        user_id: str,
        memory_id: str,
        content: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        priority: Optional[MemoryPriority] = None,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Update an existing memory entry
        
        Args:
            user_id: User identifier
            memory_id: Memory entry ID
            content: New content (optional)
            tags: New tags (optional)
            priority: New priority (optional)
            expires_at: New expiration (optional)
            
        Returns:
            True if updated successfully, False otherwise
        """
        # Get current memory
        memory = await self.retrieve_memory(user_id, memory_id)
        if not memory:
            return False
        
        # Update fields if provided
        if content is not None:
            memory.content = content
        if tags is not None:
            memory.tags = tags
        if priority is not None:
            memory.priority = priority
        if expires_at is not None:
            memory.expires_at = expires_at
        
        memory.updated_at = datetime.now()
        memory.version += 1
        
        with sqlite3.connect(self.storage_path) as conn:
            conn.execute("""
                UPDATE memories 
                SET content = ?, tags = ?, priority = ?, expires_at = ?, 
                    updated_at = ?, version = ?
                WHERE id = ? AND user_id = ?
            """, (
                json.dumps(memory.content),
                json.dumps(memory.tags),
                memory.priority.value,
                memory.expires_at.isoformat() if memory.expires_at else None,
                memory.updated_at.isoformat(),
                memory.version,
                memory_id,
                user_id
            ))
            conn.commit()
        
        logger.info(f"Updated memory {memory_id} for user {user_id}")
        return True
    
    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        """
        Delete a memory entry
        
        Args:
            user_id: User identifier
            memory_id: Memory entry ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("""
                DELETE FROM memories WHERE id = ? AND user_id = ?
            """, (memory_id, user_id))
            conn.commit()
            
            if cursor.rowcount > 0:
                await self._update_user_stats(user_id)
                logger.info(f"Deleted memory {memory_id} for user {user_id}")
                return True
        
        return False
    
    async def cleanup_expired_memories(self, user_id: Optional[str] = None) -> int:
        """
        Clean up expired memory entries
        
        Args:
            user_id: Optional specific user, if None cleanup all users
            
        Returns:
            Number of memories cleaned up
        """
        now = datetime.now()
        
        with sqlite3.connect(self.storage_path) as conn:
            if user_id:
                cursor = conn.execute("""
                    DELETE FROM memories 
                    WHERE user_id = ? AND expires_at IS NOT NULL AND expires_at <= ?
                """, (user_id, now.isoformat()))
            else:
                cursor = conn.execute("""
                    DELETE FROM memories 
                    WHERE expires_at IS NOT NULL AND expires_at <= ?
                """, (now.isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            # Update cleanup timestamp
            if user_id:
                await self._update_user_stats(user_id)
            else:
                conn.execute("""
                    UPDATE memory_stats 
                    SET last_cleanup = ?, updated_at = ?
                """, (now.isoformat(), now.isoformat()))
                conn.commit()
        
        logger.info(f"Cleaned up {deleted_count} expired memories")
        return deleted_count
    
    async def get_user_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get memory statistics for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing memory statistics
        """
        with sqlite3.connect(self.storage_path) as conn:
            # Total memories count
            cursor = conn.execute("""
                SELECT COUNT(*) as total FROM memories WHERE user_id = ?
            """, (user_id,))
            total_memories = cursor.fetchone()[0]
            
            # Memory types breakdown
            cursor = conn.execute("""
                SELECT memory_type, COUNT(*) as count 
                FROM memories 
                WHERE user_id = ?
                GROUP BY memory_type
            """, (user_id,))
            type_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Priority breakdown
            cursor = conn.execute("""
                SELECT priority, COUNT(*) as count 
                FROM memories 
                WHERE user_id = ?
                GROUP BY priority
            """, (user_id,))
            priority_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Recent memories (last 7 days)
            week_ago = datetime.now() - timedelta(days=7)
            cursor = conn.execute("""
                SELECT COUNT(*) as recent_count 
                FROM memories 
                WHERE user_id = ? AND created_at >= ?
            """, (user_id, week_ago.isoformat()))
            recent_memories = cursor.fetchone()[0]
            
            # Most accessed memories
            cursor = conn.execute("""
                SELECT id, content, access_count 
                FROM memories 
                WHERE user_id = ?
                ORDER BY access_count DESC 
                LIMIT 5
            """, (user_id,))
            most_accessed = [
                {
                    "id": row[0],
                    "content": json.loads(row[1]),
                    "access_count": row[2]
                }
                for row in cursor.fetchall()
            ]
        
        return {
            "user_id": user_id,
            "total_memories": total_memories,
            "memory_types": type_counts,
            "priority_distribution": priority_counts,
            "recent_memories": recent_memories,
            "most_accessed": most_accessed,
            "last_updated": datetime.now().isoformat()
        }
    
    async def migrate_memories(self, from_version: int, to_version: int) -> bool:
        """
        Migrate memory database to a new version
        
        Args:
            from_version: Current version
            to_version: Target version
            
        Returns:
            True if migration successful
        """
        migration_name = f"migration_{from_version}_to_{to_version}"
        
        try:
            # Check if migration already applied
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.execute("""
                    SELECT id FROM memory_migrations WHERE migration_name = ?
                """, (migration_name,))
                if cursor.fetchone():
                    logger.info(f"Migration {migration_name} already applied")
                    return True
            
            # Apply migration based on version
            if to_version == 2:
                await self._apply_migration_v2()
            elif to_version == 3:
                await self._apply_migration_v3()
            else:
                logger.warning(f"Unknown migration target version: {to_version}")
                return False
            
            # Record migration
            with sqlite3.connect(self.storage_path) as conn:
                conn.execute("""
                    INSERT INTO memory_migrations (
                        migration_name, applied_at, version_from, version_to
                    ) VALUES (?, ?, ?, ?)
                """, (
                    migration_name,
                    datetime.now().isoformat(),
                    from_version,
                    to_version
                ))
                conn.commit()
            
            logger.info(f"Successfully applied migration {migration_name}")
            return True
            
        except Exception as e:
            logger.error(f"Migration {migration_name} failed: {e}")
            return False
    
    def _generate_memory_id(self, user_id: str, content: Dict[str, Any]) -> str:
        """Generate unique memory ID based on user and content"""
        content_str = json.dumps(content, sort_keys=True)
        hash_input = f"{user_id}:{content_str}:{time.time()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _row_to_memory_entry(self, row) -> MemoryEntry:
        """Convert database row to MemoryEntry object"""
        return MemoryEntry(
            id=row[0],
            user_id=row[1],
            memory_type=MemoryType(row[2]),
            priority=MemoryPriority(row[3]),
            content=json.loads(row[4]),
            tags=json.loads(row[5]),
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7]),
            access_count=row[8],
            last_accessed=datetime.fromisoformat(row[9]) if row[9] else None,
            expires_at=datetime.fromisoformat(row[10]) if row[10] else None,
            version=row[11]
        )
    
    async def _update_access_stats(self, memory_id: str):
        """Update access statistics for a memory entry"""
        with sqlite3.connect(self.storage_path) as conn:
            conn.execute("""
                UPDATE memories 
                SET access_count = access_count + 1, last_accessed = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), memory_id))
            conn.commit()
    
    async def _update_user_stats(self, user_id: str):
        """Update user memory statistics"""
        stats = await self.get_user_memory_stats(user_id)
        
        with sqlite3.connect(self.storage_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory_stats (
                    user_id, total_memories, memory_types_count, 
                    last_cleanup, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                stats["total_memories"],
                json.dumps(stats["memory_types"]),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def _start_cleanup_task(self):
        """Start background cleanup task for expired memories"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired memories"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self.cleanup_expired_memories()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic cleanup failed: {e}")
    
    async def _apply_migration_v2(self):
        """Apply migration to version 2 - add memory categorization"""
        with sqlite3.connect(self.storage_path) as conn:
            # Add new columns for v2
            conn.execute("""
                ALTER TABLE memories ADD COLUMN category TEXT
            """)
            conn.execute("""
                ALTER TABLE memories ADD COLUMN importance_score REAL DEFAULT 0.0
            """)
            conn.commit()
    
    async def _apply_migration_v3(self):
        """Apply migration to version 3 - add memory relationships"""
        with sqlite3.connect(self.storage_path) as conn:
            # Create memory relationships table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_memory_id TEXT NOT NULL,
                    target_memory_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    strength REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (source_memory_id) REFERENCES memories (id),
                    FOREIGN KEY (target_memory_id) REFERENCES memories (id)
                )
            """)
            conn.commit()
    
    async def close(self):
        """Close the memory system and cleanup resources"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("User memory system closed")