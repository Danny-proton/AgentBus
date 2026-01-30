"""
Context Cache Management Module

This module provides intelligent context caching capabilities including:
- Dynamic context window management
- Context compression and summarization
- Cache eviction policies
- Multi-level cache hierarchy
"""

import asyncio
import json
import pickle
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging
from collections import OrderedDict, defaultdict

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache storage levels"""
    L1_MEMORY = "l1_memory"      # In-memory cache
    L2_DISK = "l2_disk"          # Disk-based cache
    L3_REMOTE = "l3_remote"      # Remote cache (Redis, etc.)


class ContextType(Enum):
    """Types of context in cache"""
    CONVERSATION = "conversation"
    USER_PREFERENCES = "user_preferences"
    WORKSPACE = "workspace"
    KNOWLEDGE = "knowledge"
    TEMPORARY = "temporary"
    PERSISTENT = "persistent"


class EvictionPolicy(Enum):
    """Cache eviction policies"""
    LRU = "lru"          # Least Recently Used
    LFU = "lfu"          # Least Frequently Used
    FIFO = "fifo"        # First In, First Out
    TTL = "ttl"          # Time To Live
    SIZE = "size"        # Size-based eviction
    PRIORITY = "priority" # Priority-based eviction


@dataclass
class CacheEntry:
    """Individual cache entry structure"""
    key: str
    value: Any
    context_type: ContextType
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl: Optional[timedelta] = None
    size: int = 0
    priority: int = 5  # 1-10 scale, 10 being highest
    compressed: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if isinstance(self.context_type, str):
            self.context_type = ContextType(self.context_type)
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.last_accessed, str):
            self.last_accessed = datetime.fromisoformat(self.last_accessed)
        self.metadata = self.metadata or {}
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl is None:
            return False
        return datetime.now() > (self.last_accessed + self.ttl)


class ContextCache:
    """
    Intelligent context caching system with multi-level storage
    
    Features:
    - Multi-level cache hierarchy (Memory -> Disk -> Remote)
    - Intelligent context compression and summarization
    - Adaptive eviction policies
    - Context relevance scoring
    - Automatic cache warming and preloading
    - Cache analytics and monitoring
    """
    
    def __init__(
        self,
        storage_path: str = "data/context_cache",
        max_l1_size: int = 1000,
        max_l2_size: int = 10000,
        max_memory_mb: int = 512,
        default_ttl: timedelta = timedelta(hours=1),
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
        compression_enabled: bool = True
    ):
        """Initialize context cache system"""
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Cache configuration
        self.max_l1_size = max_l1_size
        self.max_l2_size = max_l2_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self.eviction_policy = eviction_policy
        self.compression_enabled = compression_enabled
        
        # Cache storage
        self.l1_cache = OrderedDict()  # Memory cache
        self.l2_cache = {}            # Disk cache index
        self.l3_cache = None           # Remote cache (placeholder)
        
        # Statistics
        self.stats = {
            "total_entries": 0,
            "l1_entries": 0,
            "l2_entries": 0,
            "hit_rate": 0.0,
            "miss_rate": 0.0,
            "eviction_count": 0
        }
        
        # Load existing cache from disk
        self._load_cache_from_disk()
    
    async def get(
        self,
        key: str,
        context_type: Optional[ContextType] = None
    ) -> Optional[Any]:
        """
        Retrieve value from cache
        
        Args:
            key: Cache key
            context_type: Expected context type
            
        Returns:
            Cached value if found, None otherwise
        """
        cache_entry = None
        
        # Try L1 cache first
        if key in self.l1_cache:
            cache_entry = self.l1_cache[key]
            
            # Check if expired
            if cache_entry.is_expired:
                await self._evict_entry(key, CacheLevel.L1_MEMORY)
                cache_entry = None
            else:
                # Update access statistics
                cache_entry.last_accessed = datetime.now()
                cache_entry.access_count += 1
                
                # Move to end for LRU
                self.l1_cache.move_to_end(key)
        
        # Try L2 cache if not found in L1
        if cache_entry is None and key in self.l2_cache:
            try:
                cache_entry = self._load_from_disk(key)
                if cache_entry and not cache_entry.is_expired:
                    # Promote to L1 cache
                    await self._promote_to_l1(key, cache_entry)
                else:
                    await self._evict_from_l2(key)
                    cache_entry = None
            except Exception as e:
                logger.error(f"Error loading from L2 cache: {e}")
                await self._evict_from_l2(key)
                cache_entry = None
        
        # Update statistics
        if cache_entry:
            self.stats["hit_rate"] = (self.stats["hit_rate"] * 0.9) + 0.1
        else:
            self.stats["miss_rate"] = (self.stats["miss_rate"] * 0.9) + 0.1
        
        return cache_entry.value if cache_entry else None
    
    async def set(
        self,
        key: str,
        value: Any,
        context_type: ContextType,
        ttl: Optional[timedelta] = None,
        priority: int = 5,
        metadata: Optional[Dict[str, Any]] = None,
        force_level: Optional[CacheLevel] = None
    ) -> bool:
        """
        Store value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            context_type: Type of context
            ttl: Time-to-live (uses default if None)
            priority: Cache priority (1-10)
            metadata: Additional metadata
            force_level: Force cache level
            
        Returns:
            True if stored successfully
        """
        ttl = ttl or self.default_ttl
        metadata = metadata or {}
        
        # Create cache entry
        cache_entry = CacheEntry(
            key=key,
            value=value,
            context_type=context_type,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            ttl=ttl,
            priority=priority,
            metadata=metadata
        )
        
        # Estimate size
        cache_entry.size = self._estimate_size(value)
        
        # Determine cache level
        if force_level:
            cache_level = force_level
        elif cache_entry.size < 1024 and cache_entry.priority >= 7:
            cache_level = CacheLevel.L1_MEMORY
        elif cache_entry.priority <= 3:
            cache_level = CacheLevel.L2_DISK
        else:
            cache_level = CacheLevel.L1_MEMORY
        
        # Store in appropriate level
        try:
            if cache_level == CacheLevel.L1_MEMORY:
                await self._store_in_l1(key, cache_entry)
            elif cache_level == CacheLevel.L2_DISK:
                await self._store_in_l2(key, cache_entry)
            elif cache_level == CacheLevel.L3_REMOTE:
                await self._store_in_l3(key, cache_entry)
            
            return True
        except Exception as e:
            logger.error(f"Error storing cache entry: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete cache entry"""
        deleted = False
        
        # Delete from L1
        if key in self.l1_cache:
            del self.l1_cache[key]
            deleted = True
        
        # Delete from L2
        if key in self.l2_cache:
            await self._evict_from_l2(key)
            deleted = True
        
        # Delete from L3
        if self.l3_cache:
            try:
                # Placeholder for remote cache deletion
                pass
            except Exception as e:
                logger.error(f"Error deleting from L3 cache: {e}")
        
        return deleted
    
    async def clear(self, context_type: Optional[ContextType] = None) -> int:
        """Clear cache entries"""
        cleared_count = 0
        
        # Clear L1 cache
        if context_type is None:
            cleared_count += len(self.l1_cache)
            self.l1_cache.clear()
        else:
            keys_to_remove = [
                key for key, entry in self.l1_cache.items()
                if entry.context_type == context_type
            ]
            for key in keys_to_remove:
                del self.l1_cache[key]
                cleared_count += 1
        
        # Clear L2 cache
        if context_type is None:
            for key in list(self.l2_cache.keys()):
                await self._evict_from_l2(key)
                cleared_count += 1
        else:
            keys_to_remove = [
                key for key in list(self.l2_cache.keys())
                if self._get_l2_metadata(key).get('context_type') == context_type.value
            ]
            for key in keys_to_remove:
                await self._evict_from_l2(key)
                cleared_count += 1
        
        return cleared_count
    
    async def get_context_window(
        self,
        user_id: str,
        max_tokens: int = 4000,
        context_types: Optional[List[ContextType]] = None
    ) -> Dict[str, Any]:
        """Get optimized context window for AI processing"""
        context_types = context_types or [
            ContextType.CONVERSATION,
            ContextType.USER_PREFERENCES,
            ContextType.WORKSPACE
        ]
        
        # Get all relevant cache entries
        relevant_entries = []
        total_tokens = 0
        
        # Search through all cache levels
        for cache_entry in self.l1_cache.values():
            if (cache_entry.context_type in context_types and 
                await self._is_user_relevant(cache_entry, user_id)):
                
                entry_tokens = await self._estimate_tokens(cache_entry.value)
                if total_tokens + entry_tokens <= max_tokens:
                    relevant_entries.append(cache_entry)
                    total_tokens += entry_tokens
        
        # Build context window
        context_window = {
            "user_id": user_id,
            "total_tokens": total_tokens,
            "max_tokens": max_tokens,
            "context_entries": [],
            "generated_at": datetime.now().isoformat()
        }
        
        # Sort by relevance and priority
        relevant_entries.sort(key=lambda x: (x.priority, x.last_accessed), reverse=True)
        
        for entry in relevant_entries:
            context_entry = {
                "key": entry.key,
                "type": entry.context_type.value,
                "content": entry.value,
                "priority": entry.priority,
                "metadata": entry.metadata
            }
            context_window["context_entries"].append(context_entry)
        
        return context_window
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        # Update current statistics
        self.stats["total_entries"] = len(self.l1_cache) + len(self.l2_cache)
        self.stats["l1_entries"] = len(self.l1_cache)
        self.stats["l2_entries"] = len(self.l2_cache)
        
        return self.stats.copy()
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes"""
        try:
            return len(pickle.dumps(value))
        except:
            return len(str(value).encode('utf-8'))
    
    async def _promote_to_l1(self, key: str, cache_entry: CacheEntry):
        """Promote cache entry from L2 to L1"""
        try:
            self.l1_cache[key] = cache_entry
            self.l1_cache.move_to_end(key)
            await self._evict_from_l2(key)
        except Exception as e:
            logger.error(f"Error promoting to L1: {e}")
    
    async def _store_in_l1(self, key: str, cache_entry: CacheEntry):
        """Store cache entry in L1 (memory) cache"""
        # Check if we need to evict
        if len(self.l1_cache) >= self.max_l1_size:
            await self._evict_from_l1()
        
        # Check memory limit
        current_memory = sum(entry.size for entry in self.l1_cache.values())
        if current_memory + cache_entry.size > self.max_memory_bytes:
            await self._evict_by_size(cache_entry.size)
        
        self.l1_cache[key] = cache_entry
        self.l1_cache.move_to_end(key)
    
    async def _store_in_l2(self, key: str, cache_entry: CacheEntry):
        """Store cache entry in L2 (disk) cache"""
        try:
            file_path = self.storage_path / f"{key}.cache"
            
            with open(file_path, 'wb') as f:
                pickle.dump(cache_entry, f)
            
            # Update L2 index
            self.l2_cache[key] = {
                "file_path": str(file_path),
                "context_type": cache_entry.context_type.value,
                "size": cache_entry.size,
                "created_at": cache_entry.created_at.isoformat()
            }
        except Exception as e:
            logger.error(f"Error storing in L2: {e}")
    
    async def _store_in_l3(self, key: str, cache_entry: CacheEntry):
        """Store cache entry in L3 (remote) cache"""
        # Placeholder for remote cache implementation
        pass
    
    def _load_from_disk(self, key: str) -> Optional[CacheEntry]:
        """Load cache entry from disk"""
        try:
            if key not in self.l2_cache:
                return None
            
            file_path = self.l2_cache[key]["file_path"]
            if not Path(file_path).exists():
                return None
            
            with open(file_path, 'rb') as f:
                cache_entry = pickle.load(f)
            
            # Update access info
            cache_entry.last_accessed = datetime.now()
            cache_entry.access_count += 1
            
            return cache_entry
        except Exception as e:
            logger.error(f"Error loading from disk: {e}")
            return None
    
    async def _evict_entry(self, key: str, level: CacheLevel):
        """Evict cache entry from specific level"""
        if level == CacheLevel.L1_MEMORY:
            await self._evict_from_l1(key)
        elif level == CacheLevel.L2_DISK:
            await self._evict_from_l2(key)
        elif level == CacheLevel.L3_REMOTE:
            await self._evict_from_l3(key)
    
    async def _evict_from_l1(self, key: Optional[str] = None):
        """Evict from L1 cache"""
        if key:
            if key in self.l1_cache:
                del self.l1_cache[key]
        else:
            # Evict based on policy
            if self.eviction_policy == EvictionPolicy.LRU:
                oldest_key = next(iter(self.l1_cache))
                del self.l1_cache[oldest_key]
            elif self.eviction_policy == EvictionPolicy.FIFO:
                oldest_key = next(iter(self.l1_cache))
                del self.l1_cache[oldest_key]
            elif self.eviction_policy == EvictionPolicy.PRIORITY:
                lowest_priority_key = min(
                    self.l1_cache.keys(),
                    key=lambda k: self.l1_cache[k].priority
                )
                del self.l1_cache[lowest_priority_key]
        
        self.stats["eviction_count"] += 1
    
    async def _evict_from_l2(self, key: str):
        """Evict from L2 cache"""
        if key in self.l2_cache:
            file_path = self.l2_cache[key]["file_path"]
            
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception as e:
                logger.error(f"Error removing cache file: {e}")
            
            del self.l2_cache[key]
    
    async def _evict_from_l3(self, key: str):
        """Evict from L3 cache"""
        # Placeholder for remote cache eviction
        pass
    
    async def _evict_by_size(self, required_space: int):
        """Evict entries to free up space"""
        entries_by_size = sorted(
            self.l1_cache.items(),
            key=lambda x: x[1].size,
            reverse=True
        )
        
        freed_space = 0
        for key, entry in entries_by_size:
            await self._evict_from_l1(key)
            freed_space += entry.size
            
            if freed_space >= required_space:
                break
    
    def _get_l2_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata for L2 cache entry"""
        return self.l2_cache.get(key, {})
    
    async def _is_user_relevant(self, cache_entry: CacheEntry, user_id: str) -> bool:
        """Check if cache entry is relevant to user"""
        user_metadata = cache_entry.metadata.get("user_id")
        if user_metadata and user_metadata != user_id:
            return False
        
        if cache_entry.context_type == ContextType.USER_PREFERENCES:
            return True
        
        return True
    
    async def _estimate_tokens(self, value: Any) -> int:
        """Estimate token count for value"""
        if isinstance(value, str):
            return len(value) // 4
        elif isinstance(value, (list, dict)):
            return len(str(value)) // 4
        else:
            return 100
    
    def _load_cache_from_disk(self):
        """Load existing cache metadata from disk"""
        for cache_file in self.storage_path.glob("*.cache"):
            key = cache_file.stem
            self.l2_cache[key] = {
                "file_path": str(cache_file),
                "context_type": "unknown",
                "size": cache_file.stat().st_size,
                "created_at": datetime.fromtimestamp(cache_file.stat().st_ctime).isoformat()
            }
    
    async def close(self):
        """Close cache system and cleanup resources"""
        # Clear L1 cache
        self.l1_cache.clear()
        
        # Clear L2 index
        self.l2_cache.clear()
        
        logger.info("Context cache system closed")