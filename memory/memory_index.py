"""
Memory Index Module

This module provides comprehensive memory indexing and search capabilities,
combining vector embeddings, metadata indexing, and efficient retrieval.
"""

import asyncio
import json
import sqlite3
import hashlib
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path
from datetime import datetime, timedelta
import re
from collections import defaultdict

logger = logging.getLogger(__name__)


class IndexStatus(Enum):
    """Index operation status"""
    CREATING = "creating"
    ACTIVE = "active"
    UPDATING = "updating"
    OPTIMIZING = "optimizing"
    ERROR = "error"


class MemorySource(Enum):
    """Memory source types"""
    USER_MEMORY = "user_memory"
    CONVERSATION_HISTORY = "conversation_history"
    CONTEXT_CACHE = "context_cache"
    VECTOR_STORE = "vector_store"
    EXTERNAL = "external"


@dataclass
class IndexedMemory:
    """Indexed memory entry structure"""
    id: str
    content: str
    source: MemorySource
    memory_type: str
    priority: int
    tags: List[str]
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    created_at: datetime = None
    updated_at: datetime = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    importance_score: float = 0.0
    chunk_id: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class IndexConfig:
    """Configuration for memory indexing"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_memory_age_days: Optional[int] = None
    min_importance_score: float = 0.0
    enable_vector_indexing: bool = True
    enable_fulltext_indexing: bool = True
    enable_metadata_indexing: bool = True
    auto_cleanup: bool = True
    cleanup_interval_hours: int = 24
    max_results: int = 100
    enable_snippets: bool = True
    snippet_length: int = 200


@dataclass
class SearchFilters:
    """Search filters for memory retrieval"""
    source_filter: Optional[List[MemorySource]] = None
    memory_type_filter: Optional[List[str]] = None
    priority_min: Optional[int] = None
    priority_max: Optional[int] = None
    tags_filter: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    importance_min: Optional[float] = None
    metadata_filter: Optional[Dict[str, Any]] = None
    include_expired: bool = False


class MemoryIndexer:
    """
    Comprehensive memory indexing and search system
    
    Features:
    - Multi-source memory indexing (user memory, conversations, etc.)
    - Automatic chunking and embedding generation
    - Full-text search with FTS support
    - Vector similarity search
    - Metadata-based filtering
    - Importance scoring and ranking
    - Automatic cleanup and optimization
    - Incremental indexing updates
    """
    
    def __init__(self, storage_path: str = "data/memory_index.db", config: Optional[IndexConfig] = None):
        """Initialize memory indexer
        
        Args:
            storage_path: Path to SQLite database file
            config: Indexing configuration
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = config or IndexConfig()
        
        # External dependencies
        self.embedding_func = None
        self.vector_store = None
        
        # Index status
        self.status = IndexStatus.CREATING
        self._init_lock = asyncio.Lock()
        
        # Statistics
        self.stats = {
            "indexed_memories": 0,
            "total_memories": 0,
            "vector_memories": 0,
            "fulltext_memories": 0,
            "last_cleanup": None,
            "last_optimization": None
        }
        
        self._init_database()
        
        # Start background tasks
        if self.config.auto_cleanup:
            self._start_cleanup_task()
        
        self.status = IndexStatus.ACTIVE
        logger.info(f"Memory indexer initialized at {self.storage_path}")
    
    def set_embedding_function(self, func: Callable[[str], List[float]]):
        """Set embedding generation function"""
        self.embedding_func = func
    
    def set_vector_store(self, vector_store):
        """Set vector store for similarity search"""
        self.vector_store = vector_store
    
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.storage_path) as conn:
            # Main memories table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    tags TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    embedding TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    importance_score REAL DEFAULT 0.0,
                    chunk_id TEXT,
                    hash TEXT UNIQUE NOT NULL
                )
            """)
            
            # Full-text search table
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    content,
                    content='memories',
                    content_rowid='rowid'
                )
            """)
            
            # Triggers for FTS synchronization
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_fts_insert AFTER INSERT ON memories
                BEGIN
                    INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_fts_update AFTER UPDATE ON memories
                BEGIN
                    UPDATE memories_fts SET content = new.content WHERE rowid = new.rowid;
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memories_fts_delete AFTER DELETE ON memories
                BEGIN
                    DELETE FROM memories_fts WHERE rowid = old.rowid;
                END
            """)
            
            # Memory chunks for large content
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_chunks (
                    id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (memory_id) REFERENCES memories (id)
                )
            """)
            
            # Index metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS index_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_source ON memories (source)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_type ON memories (memory_type)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_priority ON memories (priority)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_created ON memories (created_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories (importance_score)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_hash ON memories (hash)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_memory ON memory_chunks (memory_id)
            """)
            
            conn.commit()
        
        logger.info("Memory index database initialized")
    
    async def index_memory(
        self,
        content: str,
        source: MemorySource,
        memory_type: str,
        priority: int = 3,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        force_reindex: bool = False
    ) -> str:
        """
        Index a memory entry
        
        Args:
            content: Memory content
            source: Memory source
            memory_type: Type of memory
            priority: Priority level (1-5)
            tags: Optional tags
            metadata: Optional metadata
            force_reindex: Whether to force re-indexing
            
        Returns:
            Memory ID
        """
        if metadata is None:
            metadata = {}
        if tags is None:
            tags = []
        
        # Generate memory ID
        memory_id = self._generate_memory_id(content, source, memory_type, metadata)
        
        # Check if already indexed
        if not force_reindex and await self._memory_exists(memory_id):
            logger.debug(f"Memory {memory_id} already indexed")
            return memory_id
        
        # Generate embedding if enabled
        embedding = None
        if self.config.enable_vector_indexing and self.embedding_func:
            try:
                embedding = await self._generate_embedding_async(content)
            except Exception as e:
                logger.warning(f"Failed to generate embedding for memory {memory_id}: {e}")
        
        # Calculate importance score
        importance_score = self._calculate_importance_score(
            content, priority, tags, metadata
        )
        
        # Store memory
        await self._store_memory(
            memory_id=memory_id,
            content=content,
            source=source,
            memory_type=memory_type,
            priority=priority,
            tags=tags,
            metadata=metadata,
            embedding=embedding,
            importance_score=importance_score
        )
        
        # Chunk if necessary
        if len(content) > self.config.chunk_size:
            await self._create_chunks(memory_id, content, embedding)
        
        # Update statistics
        self.stats["indexed_memories"] += 1
        self.stats["total_memories"] += 1
        
        if embedding:
            self.stats["vector_memories"] += 1
        if self.config.enable_fulltext_indexing:
            self.stats["fulltext_memories"] += 1
        
        logger.debug(f"Indexed memory {memory_id} from {source.value}")
        return memory_id
    
    async def search_memories(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 10,
        include_snippets: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search indexed memories
        
        Args:
            query: Search query
            filters: Optional search filters
            limit: Maximum number of results
            include_snippets: Whether to include snippets
            
        Returns:
            List of search results
        """
        filters = filters or SearchFilters()
        
        # Determine search strategy
        has_embedding = self.embedding_func is not None
        has_fts = self.config.enable_fulltext_indexing
        
        if has_embedding and has_fts:
            # Hybrid search
            results = await self._hybrid_search(query, filters, limit)
        elif has_embedding:
            # Vector-only search
            results = await self._vector_search(query, filters, limit)
        elif has_fts:
            # Full-text search
            results = await self._fulltext_search(query, filters, limit)
        else:
            # Basic search
            results = await self._basic_search(query, filters, limit)
        
        # Update access statistics
        await self._update_access_stats([r['id'] for r in results])
        
        # Add snippets if requested
        if include_snippets:
            for result in results:
                result['snippet'] = self._generate_snippet(
                    result['content'], query
                )
        
        return results[:limit]
    
    async def _hybrid_search(
        self,
        query: str,
        filters: SearchFilters,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform hybrid vector + full-text search"""
        # Generate query embedding
        query_embedding = None
        try:
            query_embedding = await self._generate_embedding_async(query)
        except Exception as e:
            logger.warning(f"Failed to generate query embedding: {e}")
            return await self._fulltext_search(query, filters, limit)
        
        # Perform parallel searches
        vector_task = self._vector_search(query_embedding, filters, limit * 2)
        fts_task = self._fulltext_search(query, filters, limit * 2)
        
        vector_results, fts_results = await asyncio.gather(vector_task, fts_task)
        
        # Combine and rerank results
        return self._combine_search_results(vector_results, fts_results, limit)
    
    async def _vector_search(
        self,
        query: Union[str, List[float]],
        filters: SearchFilters,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search"""
        # Generate embedding if query is text
        if isinstance(query, str):
            try:
                query_embedding = await self._generate_embedding_async(query)
            except Exception as e:
                logger.warning(f"Failed to generate query embedding: {e}")
                return []
        else:
            query_embedding = query
        
        # Build SQL query
        sql, params = self._build_vector_search_query(filters, limit)
        
        results = []
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute(sql, params)
            
            for row in cursor.fetchall():
                try:
                    embedding = json.loads(row[7]) if row[7] else None
                    if not embedding:
                        continue
                    
                    # Calculate similarity
                    similarity = self._cosine_similarity(query_embedding, embedding)
                    
                    result = {
                        'id': row[0],
                        'content': row[1],
                        'source': row[2],
                        'memory_type': row[3],
                        'priority': row[4],
                        'tags': json.loads(row[5]),
                        'metadata': json.loads(row[6]),
                        'importance_score': row[8],
                        'created_at': datetime.fromisoformat(row[9]),
                        'access_count': row[10],
                        'score': similarity
                    }
                    
                    results.append(result)
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Error processing memory row: {e}")
                    continue
        
        # Sort by similarity and apply limit
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    async def _fulltext_search(
        self,
        query: str,
        filters: SearchFilters,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform full-text search using FTS"""
        # Build FTS query
        fts_query = self._build_fts_query(query)
        
        # Build filter conditions
        where_conditions = ["memories_fts MATCH ?"]
        params = [fts_query]
        
        self._add_filter_conditions(where_conditions, params, filters)
        
        where_clause = " AND ".join(where_conditions)
        
        sql = f"""
            SELECT memories.*, 
                   bm25(memories_fts) as rank
            FROM memories 
            JOIN memories_fts ON memories.rowid = memories_fts.rowid
            WHERE {where_clause}
            ORDER BY rank ASC
            LIMIT ?
        """
        
        params.append(limit)
        
        results = []
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute(sql, params)
            
            for row in cursor.fetchall():
                try:
                    result = {
                        'id': row[1],
                        'content': row[2],
                        'source': row[3],
                        'memory_type': row[4],
                        'priority': row[5],
                        'tags': json.loads(row[6]),
                        'metadata': json.loads(row[7]),
                        'importance_score': row[10],
                        'created_at': datetime.fromisoformat(row[11]),
                        'access_count': row[12],
                        'score': 1.0 / (1.0 + row[-1])  # Convert BM25 rank to score
                    }
                    
                    results.append(result)
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Error processing memory row: {e}")
                    continue
        
        return results
    
    async def _basic_search(
        self,
        query: str,
        filters: SearchFilters,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform basic text search without FTS or vectors"""
        where_conditions = ["content LIKE ?"]
        params = [f"%{query}%"]
        
        self._add_filter_conditions(where_conditions, params, filters)
        
        where_clause = " AND ".join(where_conditions)
        
        sql = f"""
            SELECT * FROM memories
            WHERE {where_clause}
            ORDER BY importance_score DESC, created_at DESC
            LIMIT ?
        """
        
        params.append(limit)
        
        results = []
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute(sql, params)
            
            for row in cursor.fetchall():
                try:
                    result = {
                        'id': row[1],
                        'content': row[2],
                        'source': row[3],
                        'memory_type': row[4],
                        'priority': row[5],
                        'tags': json.loads(row[6]),
                        'metadata': json.loads(row[7]),
                        'importance_score': row[10],
                        'created_at': datetime.fromisoformat(row[11]),
                        'access_count': row[12],
                        'score': 1.0
                    }
                    
                    results.append(result)
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Error processing memory row: {e}")
                    continue
        
        return results
    
    def _build_fts_query(self, query: str) -> str:
        """Build FTS query from text"""
        # Simple tokenization and boolean query building
        tokens = re.findall(r'\w+', query.lower())
        
        if not tokens:
            return ""
        
        # Build phrase query
        quoted_tokens = [f'"{token}"' for token in tokens]
        return " AND ".join(quoted_tokens)
    
    def _add_filter_conditions(
        self,
        conditions: List[str],
        params: List[Any],
        filters: SearchFilters
    ):
        """Add filter conditions to query"""
        if filters.source_filter:
            placeholders = ",".join("?" * len(filters.source_filter))
            conditions.append(f"source IN ({placeholders})")
            params.extend([s.value for s in filters.source_filter])
        
        if filters.memory_type_filter:
            placeholders = ",".join("?" * len(filters.memory_type_filter))
            conditions.append(f"memory_type IN ({placeholders})")
            params.extend(filters.memory_type_filter)
        
        if filters.priority_min is not None:
            conditions.append("priority >= ?")
            params.append(filters.priority_min)
        
        if filters.priority_max is not None:
            conditions.append("priority <= ?")
            params.append(filters.priority_max)
        
        if filters.importance_min is not None:
            conditions.append("importance_score >= ?")
            params.append(filters.importance_min)
        
        if filters.date_from:
            conditions.append("created_at >= ?")
            params.append(filters.date_from.isoformat())
        
        if filters.date_to:
            conditions.append("created_at <= ?")
            params.append(filters.date_to.isoformat())
        
        if filters.tags_filter:
            for tag in filters.tags_filter:
                conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")
    
    def _combine_search_results(
        self,
        vector_results: List[Dict[str, Any]],
        fts_results: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Combine vector and FTS search results"""
        # Create result maps
        vector_map = {r['id']: r for r in vector_results}
        fts_map = {r['id']: r for r in fts_results}
        
        # Get all unique IDs
        all_ids = set(vector_map.keys()) | set(fts_map.keys())
        
        # Combine results
        combined = []
        for result_id in all_ids:
            vector_result = vector_map.get(result_id)
            fts_result = fts_map.get(result_id)
            
            # Calculate combined score
            vector_score = vector_result['score'] if vector_result else 0.0
            fts_score = fts_result['score'] if fts_result else 0.0
            
            # Weighted combination (70% vector, 30% text)
            combined_score = 0.7 * vector_score + 0.3 * fts_score
            
            # Use the result with more complete data
            primary_result = vector_result or fts_result
            
            combined_result = primary_result.copy()
            combined_result['score'] = combined_score
            combined_result['vector_score'] = vector_score
            combined_result['text_score'] = fts_score
            
            combined.append(combined_result)
        
        # Sort by combined score
        combined.sort(key=lambda x: x['score'], reverse=True)
        
        return combined[:limit]
    
    def _generate_snippet(self, content: str, query: str, max_length: int = None) -> str:
        """Generate snippet from content based on query"""
        if max_length is None:
            max_length = self.config.snippet_length
        
        # Simple snippet generation
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Find first occurrence of query terms
        first_pos = len(content)
        for term in query_lower.split():
            pos = content_lower.find(term)
            if pos != -1 and pos < first_pos:
                first_pos = pos
        
        if first_pos == len(content):
            # No match found, return beginning
            return content[:max_length] + ("..." if len(content) > max_length else "")
        
        # Extract snippet around the match
        start = max(0, first_pos - 50)
        end = min(len(content), start + max_length)
        
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        
        return snippet
    
    def _calculate_importance_score(
        self,
        content: str,
        priority: int,
        tags: List[str],
        metadata: Dict[str, Any]
    ) -> float:
        """Calculate importance score for memory"""
        score = 0.0
        
        # Base score from priority (lower priority number = higher importance)
        score += (6 - priority) * 0.3
        
        # Content length factor
        content_length = len(content)
        if content_length > 500:
            score += 0.2
        elif content_length > 100:
            score += 0.1
        
        # Tag bonuses
        important_tags = {'important', 'critical', 'key', 'essential', 'priority'}
        tag_score = sum(0.1 for tag in tags if tag.lower() in important_tags)
        score += min(tag_score, 0.3)
        
        # Metadata bonuses
        if metadata.get('auto_important', False):
            score += 0.2
        
        if metadata.get('user_flagged', False):
            score += 0.3
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _generate_memory_id(
        self,
        content: str,
        source: MemorySource,
        memory_type: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Generate unique memory ID"""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        source_str = f"{source.value}:{memory_type}"
        
        # Include some metadata in hash for uniqueness
        meta_str = json.dumps(metadata, sort_keys=True)
        meta_hash = hashlib.sha256(meta_str.encode()).hexdigest()[:8]
        
        return f"{source_str}:{content_hash}:{meta_hash}"
    
    async def _generate_embedding_async(self, text: str) -> List[float]:
        """Generate embedding asynchronously"""
        if self.embedding_func:
            # Run embedding generation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.embedding_func, text)
        else:
            raise ValueError("No embedding function configured")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import numpy as np
        
        if len(vec1) != len(vec2):
            return 0.0
        
        vec1_array = np.array(vec1)
        vec2_array = np.array(vec2)
        
        dot_product = np.dot(vec1_array, vec2_array)
        norm1 = np.linalg.norm(vec1_array)
        norm2 = np.linalg.norm(vec2_array)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    async def _memory_exists(self, memory_id: str) -> bool:
        """Check if memory already exists"""
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("SELECT id FROM memories WHERE id = ?", (memory_id,))
            return cursor.fetchone() is not None
    
    async def _store_memory(
        self,
        memory_id: str,
        content: str,
        source: MemorySource,
        memory_type: str,
        priority: int,
        tags: List[str],
        metadata: Dict[str, Any],
        embedding: Optional[List[float]],
        importance_score: float
    ):
        """Store memory in database"""
        memory_hash = hashlib.sha256(f"{memory_id}:{content}".encode()).hexdigest()
        
        with sqlite3.connect(self.storage_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memories (
                    id, content, source, memory_type, priority, tags, metadata,
                    embedding, created_at, updated_at, importance_score, hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_id,
                content,
                source.value,
                memory_type,
                priority,
                json.dumps(tags),
                json.dumps(metadata),
                json.dumps(embedding) if embedding else None,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                importance_score,
                memory_hash
            ))
            conn.commit()
    
    async def _create_chunks(
        self,
        memory_id: str,
        content: str,
        embedding: Optional[List[float]]
    ):
        """Create memory chunks for large content"""
        chunk_size = self.config.chunk_size
        overlap = self.config.chunk_overlap
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            chunk_content = content[start:end]
            
            # Create chunk embedding if parent has embedding
            chunk_embedding = None
            if embedding:
                chunk_embedding = embedding  # Simplified - could use sliding window
            
            chunk_id = f"{memory_id}_chunk_{len(chunks)}"
            
            chunks.append({
                'id': chunk_id,
                'memory_id': memory_id,
                'chunk_index': len(chunks),
                'content': chunk_content,
                'embedding': chunk_embedding
            })
            
            start = end - overlap if overlap > 0 else end
        
        # Store chunks
        with sqlite3.connect(self.storage_path) as conn:
            for chunk in chunks:
                conn.execute("""
                    INSERT OR REPLACE INTO memory_chunks (
                        id, memory_id, chunk_index, content, embedding, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    chunk['id'],
                    chunk['memory_id'],
                    chunk['chunk_index'],
                    chunk['content'],
                    json.dumps(chunk['embedding']) if chunk['embedding'] else None,
                    datetime.now().isoformat()
                ))
            conn.commit()
    
    async def _update_access_stats(self, memory_ids: List[str]):
        """Update access statistics for memories"""
        if not memory_ids:
            return
        
        with sqlite3.connect(self.storage_path) as conn:
            placeholders = ",".join("?" * len(memory_ids))
            conn.execute(f"""
                UPDATE memories 
                SET access_count = access_count + 1, 
                    last_accessed = ?
                WHERE id IN ({placeholders})
            """, (datetime.now().isoformat(), *memory_ids))
            conn.commit()
    
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        async def cleanup_worker():
            while True:
                try:
                    await asyncio.sleep(self.config.cleanup_interval_hours * 3600)
                    await self.cleanup_old_memories()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")
        
        asyncio.create_task(cleanup_worker())
    
    async def cleanup_old_memories(self) -> int:
        """Clean up old and low-importance memories"""
        if not self.config.max_memory_age_days:
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=self.config.max_memory_age_days)
        min_importance = self.config.min_importance_score
        
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("""
                DELETE FROM memories 
                WHERE created_at < ? AND importance_score < ?
            """, (cutoff_date.isoformat(), min_importance))
            
            deleted_count = cursor.rowcount
            conn.commit()
        
        self.stats["last_cleanup"] = datetime.now()
        logger.info(f"Cleaned up {deleted_count} old memories")
        
        return deleted_count
    
    async def optimize_index(self) -> Dict[str, Any]:
        """Optimize index for better performance"""
        self.status = IndexStatus.OPTIMIZING
        
        with sqlite3.connect(self.storage_path) as conn:
            # Analyze query performance
            conn.execute("ANALYZE memories")
            conn.execute("ANALYZE memory_chunks")
            
            # Vacuum to reclaim space
            conn.execute("VACUUM")
            
            conn.commit()
        
        self.stats["last_optimization"] = datetime.now()
        self.status = IndexStatus.ACTIVE
        
        logger.info("Index optimization completed")
        
        return {
            "status": "optimized",
            "timestamp": datetime.now().isoformat(),
            "total_memories": self.stats["total_memories"],
            "vector_memories": self.stats["vector_memories"],
            "fulltext_memories": self.stats["fulltext_memories"]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        with sqlite3.connect(self.storage_path) as conn:
            # Get database size
            cursor = conn.execute("""
                SELECT page_count * page_size as size 
                FROM pragma_page_count(), pragma_page_size()
            """)
            db_size = cursor.fetchone()[0]
            
            # Get memory counts by source
            cursor = conn.execute("""
                SELECT source, COUNT(*) as count 
                FROM memories 
                GROUP BY source
            """)
            source_counts = dict(cursor.fetchall())
            
            # Get memory type counts
            cursor = conn.execute("""
                SELECT memory_type, COUNT(*) as count 
                FROM memories 
                GROUP BY memory_type
            """)
            type_counts = dict(cursor.fetchall())
            
            # Get recent activity
            week_ago = datetime.now() - timedelta(days=7)
            cursor = conn.execute("""
                SELECT COUNT(*) 
                FROM memories 
                WHERE created_at >= ?
            """, (week_ago.isoformat(),))
            recent_memories = cursor.fetchone()[0]
        
        return {
            "status": self.status.value,
            "database_size_bytes": db_size,
            "total_memories": self.stats["total_memories"],
            "indexed_memories": self.stats["indexed_memories"],
            "vector_memories": self.stats["vector_memories"],
            "fulltext_memories": self.stats["fulltext_memories"],
            "recent_memories": recent_memories,
            "source_distribution": source_counts,
            "type_distribution": type_counts,
            "last_cleanup": self.stats["last_cleanup"].isoformat() if self.stats["last_cleanup"] else None,
            "last_optimization": self.stats["last_optimization"].isoformat() if self.stats["last_optimization"] else None
        }