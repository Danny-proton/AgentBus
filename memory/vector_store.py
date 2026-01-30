"""
Vector Store Module

This module provides vector database support for memory storage and retrieval,
implementing vector similarity search for semantic memory lookup.
"""

import sqlite3
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass
import asyncio
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class VectorEntry:
    """Vector entry structure"""
    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]
    created_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None


class VectorStore:
    """
    Vector database implementation using SQLite with vector extensions
    
    Features:
    - Vector similarity search using cosine similarity
    - Metadata filtering and retrieval
    - Vector normalization and deduplication
    - Efficient storage with SQLite
    - Batch operations for performance
    """
    
    def __init__(self, storage_path: str = "data/vector_store.db", enable_vec_extension: bool = True):
        """Initialize vector store
        
        Args:
            storage_path: Path to SQLite database file
            enable_vec_extension: Whether to use SQLite-Vec extension if available
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.enable_vec_extension = enable_vec_extension
        self._vec_extension_loaded = False
        
        self._init_database()
        self._load_extensions()
    
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.storage_path) as conn:
            # Main vectors table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vectors (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    hash TEXT UNIQUE NOT NULL
                )
            """)
            
            # Vector similarity cache for fast lookups
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vector_similarities (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    similarity REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (source_id, target_id),
                    FOREIGN KEY (source_id) REFERENCES vectors (id),
                    FOREIGN KEY (target_id) REFERENCES vectors (id)
                )
            """)
            
            # Index for fast vector operations
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_vectors_created_at 
                ON vectors (created_at)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_vectors_access_count 
                ON vectors (access_count)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_similarities_source 
                ON vector_similarities (source_id)
            """)
            
            conn.commit()
            
        logger.info(f"Vector store database initialized at {self.storage_path}")
    
    def _load_extensions(self):
        """Load SQLite extensions for vector operations"""
        if not self.enable_vec_extension:
            return
            
        try:
            # Try to load sqlite-vicdb extension
            try:
                import sqlite_vicdb
                # Register the extension (implementation depends on the extension)
                logger.info("sqlite-vicdb extension loaded successfully")
                self._vec_extension_loaded = True
            except ImportError:
                pass
            
            # Try to load sqlite-vss extension
            try:
                import sqlite_vss
                # Register the extension
                logger.info("sqlite-vss extension loaded successfully")
                self._vec_extension_loaded = True
            except ImportError:
                pass
                
        except Exception as e:
            logger.warning(f"Failed to load vector extensions: {e}")
    
    def _compute_hash(self, content: str, embedding: List[float]) -> str:
        """Compute hash for deduplication"""
        combined = f"{content}:{':'.join(map(str, embedding))}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """Normalize vector to unit length"""
        if not vector:
            return vector
            
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        
        return (np.array(vector) / norm).tolist()
    
    async def store_vector(
        self,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        force_unique: bool = False
    ) -> str:
        """
        Store a vector entry
        
        Args:
            content: Text content
            embedding: Vector embedding
            metadata: Optional metadata dictionary
            force_unique: Whether to force unique storage (no duplicates)
            
        Returns:
            Vector entry ID
        """
        if metadata is None:
            metadata = {}
            
        # Normalize embedding
        normalized_embedding = self._normalize_vector(embedding)
        vector_hash = self._compute_hash(content, normalized_embedding)
        
        vector_id = hashlib.sha256(f"{content}:{datetime.now().isoformat()}".encode()).hexdigest()[:16]
        
        with sqlite3.connect(self.storage_path) as conn:
            if force_unique:
                # Check for existing similar vectors
                existing = conn.execute(
                    "SELECT id FROM vectors WHERE hash = ? LIMIT 1",
                    (vector_hash,)
                ).fetchone()
                if existing:
                    logger.debug(f"Vector already exists: {existing[0]}")
                    return existing[0]
            
            conn.execute("""
                INSERT INTO vectors (
                    id, content, embedding, metadata, created_at, hash
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                vector_id,
                content,
                json.dumps(normalized_embedding),
                json.dumps(metadata),
                datetime.now().isoformat(),
                vector_hash
            ))
            conn.commit()
        
        logger.debug(f"Stored vector {vector_id} with {len(normalized_embedding)} dimensions")
        return vector_id
    
    async def get_vector(self, vector_id: str) -> Optional[VectorEntry]:
        """
        Retrieve a vector entry by ID
        
        Args:
            vector_id: Vector entry ID
            
        Returns:
            VectorEntry if found, None otherwise
        """
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM vectors WHERE id = ?
            """, (vector_id,))
            
            row = cursor.fetchone()
            if row:
                # Update access stats
                conn.execute("""
                    UPDATE vectors 
                    SET access_count = access_count + 1, last_accessed = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), vector_id))
                conn.commit()
                
                return VectorEntry(
                    id=row[0],
                    content=row[1],
                    embedding=json.loads(row[2]),
                    metadata=json.loads(row[3]),
                    created_at=datetime.fromisoformat(row[4]),
                    access_count=row[5],
                    last_accessed=datetime.fromisoformat(row[6]) if row[6] else None
                )
        
        return None
    
    async def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[VectorEntry, float]]:
        """
        Search for similar vectors using cosine similarity
        
        Args:
            query_embedding: Query vector
            limit: Maximum number of results
            threshold: Minimum similarity threshold
            metadata_filter: Optional metadata filter
            
        Returns:
            List of (VectorEntry, similarity_score) tuples
        """
        normalized_query = self._normalize_vector(query_embedding)
        query_array = np.array(normalized_query)
        
        similar_vectors = []
        
        with sqlite3.connect(self.storage_path) as conn:
            # Build metadata filter if provided
            where_clause = ""
            params = []
            
            if metadata_filter:
                for key, value in metadata_filter.items():
                    where_clause += f" AND metadata LIKE ?"
                    params.append(f'%"%s":"%s"%' % (key, value))
            
            # Retrieve all vectors for similarity computation
            query = f"""
                SELECT * FROM vectors 
                WHERE 1=1 {where_clause}
            """
            
            cursor = conn.execute(query, params)
            
            for row in cursor.fetchall():
                try:
                    stored_embedding = json.loads(row[2])
                    
                    if len(stored_embedding) != len(normalized_query):
                        continue  # Skip vectors with different dimensions
                    
                    stored_array = np.array(stored_embedding)
                    
                    # Compute cosine similarity
                    similarity = self._cosine_similarity(query_array, stored_array)
                    
                    if similarity >= threshold:
                        vector_entry = VectorEntry(
                            id=row[0],
                            content=row[1],
                            embedding=stored_embedding,
                            metadata=json.loads(row[3]),
                            created_at=datetime.fromisoformat(row[4]),
                            access_count=row[5],
                            last_accessed=datetime.fromisoformat(row[6]) if row[6] else None
                        )
                        similar_vectors.append((vector_entry, similarity))
                        
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Error processing vector {row[0]}: {e}")
                    continue
        
        # Sort by similarity and limit results
        similar_vectors.sort(key=lambda x: x[1], reverse=True)
        return similar_vectors[:limit]
    
    async def batch_store(
        self,
        entries: List[Tuple[str, List[float], Optional[Dict[str, Any]]]]
    ) -> List[str]:
        """
        Store multiple vectors in batch
        
        Args:
            entries: List of (content, embedding, metadata) tuples
            
        Returns:
            List of vector IDs
        """
        vector_ids = []
        
        with sqlite3.connect(self.storage_path) as conn:
            for content, embedding, metadata in entries:
                if metadata is None:
                    metadata = {}
                    
                normalized_embedding = self._normalize_vector(embedding)
                vector_hash = self._compute_hash(content, normalized_embedding)
                vector_id = hashlib.sha256(
                    f"{content}:{datetime.now().isoformat()}".encode()
                ).hexdigest()[:16]
                
                conn.execute("""
                    INSERT OR IGNORE INTO vectors (
                        id, content, embedding, metadata, created_at, hash
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    vector_id,
                    content,
                    json.dumps(normalized_embedding),
                    json.dumps(metadata),
                    datetime.now().isoformat(),
                    vector_hash
                ))
                
                vector_ids.append(vector_id)
            
            conn.commit()
        
        logger.info(f"Batch stored {len(vector_ids)} vectors")
        return vector_ids
    
    async def delete_vector(self, vector_id: str) -> bool:
        """
        Delete a vector entry
        
        Args:
            vector_id: Vector entry ID
            
        Returns:
            True if deleted successfully
        """
        with sqlite3.connect(self.storage_path) as conn:
            # Delete vector and its similarities
            conn.execute("DELETE FROM vectors WHERE id = ?", (vector_id,))
            conn.execute("DELETE FROM vector_similarities WHERE source_id = ? OR target_id = ?", 
                         (vector_id, vector_id))
            conn.commit()
            
            return conn.total_changes > 0
    
    async def get_vector_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        with sqlite3.connect(self.storage_path) as conn:
            # Total vectors
            cursor = conn.execute("SELECT COUNT(*) FROM vectors")
            total_vectors = cursor.fetchone()[0]
            
            # Average embedding dimension
            cursor = conn.execute("""
                SELECT AVG(json_array_length(embedding)) as avg_dims 
                FROM vectors
            """)
            avg_dims = cursor.fetchone()[0] or 0
            
            # Most accessed vectors
            cursor = conn.execute("""
                SELECT id, content, access_count 
                FROM vectors 
                ORDER BY access_count DESC 
                LIMIT 5
            """)
            most_accessed = [
                {"id": row[0], "content": row[1], "access_count": row[2]}
                for row in cursor.fetchall()
            ]
            
            # Recent vectors (last 7 days)
            week_ago = datetime.now() - timedelta(days=7)
            cursor = conn.execute("""
                SELECT COUNT(*) 
                FROM vectors 
                WHERE created_at >= ?
            """, (week_ago.isoformat(),))
            recent_vectors = cursor.fetchone()[0]
        
        return {
            "total_vectors": total_vectors,
            "average_embedding_dimensions": round(avg_dims, 2),
            "most_accessed": most_accessed,
            "recent_vectors": recent_vectors,
            "extension_loaded": self._vec_extension_loaded
        }
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors"""
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        
        dot_product = np.dot(vec1, vec2)
        return float(dot_product / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
    
    async def cleanup_old_vectors(self, days: int = 30) -> int:
        """
        Clean up old, infrequently accessed vectors
        
        Args:
            days: Age threshold for cleanup
            
        Returns:
            Number of vectors cleaned up
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("""
                DELETE FROM vectors 
                WHERE created_at < ? AND access_count = 0
            """, (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
        
        logger.info(f"Cleaned up {deleted_count} old vectors")
        return deleted_count
    
    async def close(self):
        """Close the vector store and cleanup resources"""
        logger.info("Vector store closed")