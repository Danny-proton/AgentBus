"""
Enhanced Memory Manager Module

This module integrates all memory management capabilities including:
- Vector database support
- Hybrid memory storage
- Batch processing
- Embedding generation
- Memory indexing and search

Based on the Moltbot memory system architecture.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Union, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import time

# Import all the enhanced modules
from .vector_store import VectorStore, VectorEntry
from .embedding_manager import EmbeddingManager, EmbeddingConfig, EmbeddingProvider, EmbeddingResult
from .hybrid_search import HybridSearchEngine, SearchQuery, SearchResult, SearchStrategy, WeightingScheme
from .batch_processor import BatchProcessor, BatchConfig, BatchResult, OperationType
from .memory_index import MemoryIndexer, IndexConfig, SearchFilters, MemorySource
from .user_memory import UserMemory, MemoryType, MemoryPriority

logger = logging.getLogger(__name__)


@dataclass
class EnhancedMemoryConfig:
    """Configuration for enhanced memory manager"""
    # Storage paths
    vector_store_path: str = "data/vector_store.db"
    memory_index_path: str = "data/enhanced_memory_index.db"
    user_memory_path: str = "data/user_memory.db"
    
    # Embedding configuration
    embedding_provider: str = "fake"  # openai, huggingface, local, fake
    embedding_model: str = "text-embedding-ada-002"
    embedding_api_key: Optional[str] = None
    embedding_base_url: Optional[str] = None
    
    # Vector store configuration
    enable_vector_store: bool = True
    vector_similarity_threshold: float = 0.7
    max_vector_results: int = 100
    
    # Index configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    enable_fulltext_indexing: bool = True
    auto_cleanup: bool = True
    cleanup_interval_hours: int = 24
    
    # Batch processing configuration
    batch_size: int = 50
    max_concurrent_batches: int = 3
    batch_timeout: float = 300.0
    
    # Search configuration
    hybrid_search_weights: Tuple[float, float] = (0.7, 0.3)  # vector, keyword
    enable_query_expansion: bool = True
    max_search_results: int = 20
    
    # Memory lifecycle
    max_memory_age_days: Optional[int] = 90
    min_importance_score: float = 0.1


class EnhancedMemoryManager:
    """
    Enhanced Memory Manager integrating all memory capabilities
    
    Features:
    - Unified interface for all memory operations
    - Vector similarity search
    - Hybrid search combining multiple approaches
    - Batch processing for performance
    - Automatic memory lifecycle management
    - Multiple memory sources support
    - Embedding generation and caching
    - Memory importance scoring
    """
    
    def __init__(self, config: Optional[EnhancedMemoryConfig] = None):
        """Initialize enhanced memory manager
        
        Args:
            config: Enhanced memory configuration
        """
        self.config = config or EnhancedMemoryConfig()
        
        # Initialize components
        self.vector_store = None
        self.embedding_manager = None
        self.hybrid_search = None
        self.batch_processor = None
        self.memory_index = None
        self.user_memory = None
        
        # Status tracking
        self.initialized = False
        self.initialization_lock = asyncio.Lock()
        
        # Statistics
        self.stats = {
            "memories_stored": 0,
            "memories_retrieved": 0,
            "searches_performed": 0,
            "embeddings_generated": 0,
            "batch_operations": 0,
            "last_cleanup": None
        }
        
        logger.info("Enhanced Memory Manager created")
    
    async def initialize(self):
        """Initialize all memory management components"""
        async with self.initialization_lock:
            if self.initialized:
                return
            
            try:
                logger.info("Initializing Enhanced Memory Manager components...")
                
                # Initialize vector store
                if self.config.enable_vector_store:
                    self.vector_store = VectorStore(self.config.vector_store_path)
                    logger.info("Vector store initialized")
                
                # Initialize embedding manager
                await self._init_embedding_manager()
                
                # Initialize memory indexer
                await self._init_memory_indexer()
                
                # Initialize hybrid search engine
                await self._init_hybrid_search()
                
                # Initialize batch processor
                self.batch_processor = BatchProcessor(
                    BatchConfig(
                        batch_size=self.config.batch_size,
                        timeout=self.config.batch_timeout
                    )
                )
                logger.info("Batch processor initialized")
                
                # Initialize user memory (legacy system integration)
                self.user_memory = UserMemory(self.config.user_memory_path)
                logger.info("User memory system initialized")
                
                self.initialized = True
                logger.info("Enhanced Memory Manager fully initialized")
                
            except Exception as e:
                logger.error(f"Failed to initialize Enhanced Memory Manager: {e}")
                raise
    
    async def _init_embedding_manager(self):
        """Initialize embedding manager"""
        # Map string provider to enum
        provider_map = {
            "openai": EmbeddingProvider.OPENAI,
            "huggingface": EmbeddingProvider.HUGGINGFACE,
            "local": EmbeddingProvider.LOCAL,
            "fake": EmbeddingProvider.FAKE
        }
        
        provider = provider_map.get(self.config.embedding_provider.lower(), EmbeddingProvider.FAKE)
        
        embedding_config = EmbeddingConfig(
            provider=provider,
            model=self.config.embedding_model,
            api_key=self.config.embedding_api_key,
            base_url=self.config.embedding_base_url,
            batch_size=self.config.batch_size
        )
        
        self.embedding_manager = EmbeddingManager(embedding_config)
        
        # Set embedding function for other components
        if self.memory_index:
            self.memory_index.set_embedding_function(
                lambda text: self.embedding_manager._generate_fake_embedding(text)
                if provider == EmbeddingProvider.FAKE
                else lambda text: asyncio.run(self.embedding_manager.generate_embedding(text)).embedding
            )
        
        logger.info(f"Embedding manager initialized with {provider.value}")
    
    async def _init_memory_indexer(self):
        """Initialize memory indexer"""
        index_config = IndexConfig(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            max_memory_age_days=self.config.max_memory_age_days,
            min_importance_score=self.config.min_importance_score,
            enable_vector_indexing=self.config.enable_vector_store,
            enable_fulltext_indexing=self.config.enable_fulltext_indexing,
            auto_cleanup=self.config.auto_cleanup,
            cleanup_interval_hours=self.config.cleanup_interval_hours
        )
        
        self.memory_index = MemoryIndexer(
            self.config.memory_index_path,
            index_config
        )
        
        # Set vector store reference if available
        if self.vector_store:
            self.memory_index.set_vector_store(self.vector_store)
        
        logger.info("Memory indexer initialized")
    
    async def _init_hybrid_search(self):
        """Initialize hybrid search engine"""
        if not self.memory_index:
            return
        
        # Create search functions
        async def vector_search_func(query_text, limit, filters=None):
            # This would integrate with the vector store
            return []
        
        async def keyword_search_func(query_text, limit, filters=None):
            # This would integrate with the memory indexer FTS
            filters = filters or {}
            search_filters = SearchFilters(
                source_filter=filters.get('source_filter'),
                memory_type_filter=filters.get('memory_type_filter'),
                priority_min=filters.get('priority_min'),
                tags_filter=filters.get('tags_filter')
            )
            
            return await self.memory_index.search_memories(
                query_text,
                search_filters,
                limit
            )
        
        self.hybrid_search = HybridSearchEngine(
            vector_search_func=vector_search_func,
            keyword_search_func=keyword_search_func,
            default_weights=self.config.hybrid_search_weights
        )
        
        logger.info("Hybrid search engine initialized")
    
    async def store_memory(
        self,
        content: str,
        source: str = "user",
        memory_type: str = "general",
        priority: int = 3,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Store a memory entry across all systems
        
        Args:
            content: Memory content
            source: Memory source
            memory_type: Type of memory
            priority: Priority level (1-5)
            tags: Optional tags
            metadata: Optional metadata
            user_id: Optional user ID for user memory integration
            
        Returns:
            Memory ID
        """
        await self.initialize()
        
        start_time = time.time()
        
        try:
            memory_id = None
            
            # 1. Store in user memory system (if user_id provided)
            if user_id and self.user_memory:
                memory_type_enum = self._map_memory_type(memory_type)
                priority_enum = self._map_priority(priority)
                
                user_memory_id = await self.user_memory.store_memory(
                    user_id=user_id,
                    memory_type=memory_type_enum,
                    content={"text": content, "source": source},
                    priority=priority_enum,
                    tags=tags or [],
                    expires_at=datetime.now() + timedelta(days=self.config.max_memory_age_days or 90)
                )
                memory_id = f"user_memory:{user_memory_id}"
            
            # 2. Generate embedding
            embedding = None
            if self.embedding_manager:
                embedding_result = await self.embedding_manager.generate_embedding(content)
                embedding = embedding_result.embedding
                self.stats["embeddings_generated"] += 1
            
            # 3. Store in vector store
            if self.vector_store and embedding:
                vector_id = await self.vector_store.store_vector(
                    content=content,
                    embedding=embedding,
                    metadata={
                        "source": source,
                        "memory_type": memory_type,
                        "priority": priority,
                        "tags": tags or [],
                        **(metadata or {})
                    }
                )
                memory_id = f"vector:{vector_id}" if not memory_id else memory_id
            
            # 4. Index in memory indexer
            if self.memory_index:
                memory_source = self._map_memory_source(source)
                indexed_id = await self.memory_index.index_memory(
                    content=content,
                    source=memory_source,
                    memory_type=memory_type,
                    priority=priority,
                    tags=tags or [],
                    metadata=metadata or {}
                )
                memory_id = f"index:{indexed_id}" if not memory_id else memory_id
            
            self.stats["memories_stored"] += 1
            
            processing_time = time.time() - start_time
            logger.debug(f"Stored memory {memory_id} in {processing_time:.3f}s")
            
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise
    
    async def search_memories(
        self,
        query: str,
        source_filter: Optional[List[str]] = None,
        memory_type_filter: Optional[List[str]] = None,
        tags_filter: Optional[List[str]] = None,
        limit: int = 10,
        strategy: str = "hybrid"
    ) -> List[Dict[str, Any]]:
        """
        Search memories using hybrid approach
        
        Args:
            query: Search query
            source_filter: Optional source filter
            memory_type_filter: Optional memory type filter
            tags_filter: Optional tags filter
            limit: Maximum results
            search_strategy: Search strategy (hybrid, vector, keyword)
            
        Returns:
            List of search results
        """
        await self.initialize()
        
        start_time = time.time()
        
        try:
            # Build search filters
            filters = SearchFilters()
            
            if source_filter:
                filters.source_filter = [self._map_memory_source(s) for s in source_filter]
            
            if memory_type_filter:
                filters.memory_type_filter = memory_type_filter
            
            if tags_filter:
                filters.tags_filter = tags_filter
            
            # Choose search strategy
            if strategy == "hybrid" and self.hybrid_search:
                # Use hybrid search
                search_query = SearchQuery(
                    text=query,
                    filters=filters.__dict__,
                    limit=limit,
                    strategy=SearchStrategy.HYBRID,
                    vector_weight=self.config.hybrid_search_weights[0],
                    keyword_weight=self.config.hybrid_search_weights[1]
                )
                
                search_results = await self.hybrid_search.search(search_query)
                
                # Convert to standard format
                results = []
                for result in search_results:
                    results.append({
                        "id": result.id,
                        "content": result.content,
                        "score": result.score,
                        "source": result.source,
                        "metadata": result.metadata,
                        "snippet": result.snippet
                    })
                
            elif strategy == "vector" and self.memory_index:
                # Use vector search through memory index
                results = await self.memory_index.search_memories(
                    query, filters, limit
                )
                
            elif strategy == "keyword" and self.memory_index:
                # Use keyword search through memory index
                results = await self.memory_index.search_memories(
                    query, filters, limit
                )
                
            else:
                # Fallback to basic search
                results = await self._basic_search(query, filters, limit)
            
            self.stats["searches_performed"] += 1
            
            processing_time = time.time() - start_time
            logger.debug(f"Search completed in {processing_time:.3f}s, found {len(results)} results")
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    async def batch_store_memories(
        self,
        memories: List[Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> BatchResult:
        """
        Store multiple memories in batch
        
        Args:
            memories: List of memory dictionaries
            user_id: Optional user ID for user memory integration
            
        Returns:
            BatchResult with processing results
        """
        await self.initialize()
        
        if not self.batch_processor:
            raise ValueError("Batch processor not initialized")
        
        def process_memory_item(item_data, metadata):
            item = item_data
            return asyncio.run(
                self.store_memory(
                    content=item["content"],
                    source=item.get("source", "batch"),
                    memory_type=item.get("memory_type", "general"),
                    priority=item.get("priority", 3),
                    tags=item.get("tags"),
                    metadata=item.get("metadata"),
                    user_id=user_id
                )
            )
        
        return await self.batch_processor.process_batch(
            batch_id=f"batch_store_{int(time.time())}",
            items=memories,
            operation_type=OperationType.MEMORY_STORAGE,
            processor_func=process_memory_item
        )
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        await self.initialize()
        
        stats = {
            "enhanced_memory": self.stats.copy(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Get embedding manager stats
        if self.embedding_manager:
            stats["embedding_manager"] = self.embedding_manager.get_stats()
        
        # Get vector store stats
        if self.vector_store:
            stats["vector_store"] = await self.vector_store.get_vector_stats()
        
        # Get memory index stats
        if self.memory_index:
            stats["memory_index"] = self.memory_index.get_stats()
        
        # Get batch processor stats
        if self.batch_processor:
            stats["batch_processor"] = self.batch_processor.get_stats()
        
        # Get user memory stats (if user_id provided, could be expanded)
        if self.user_memory:
            # This would need user-specific calls
            pass
        
        return stats
    
    async def cleanup_old_memories(self) -> Dict[str, int]:
        """Clean up old and low-importance memories"""
        await self.initialize()
        
        cleanup_stats = {}
        
        # Cleanup memory indexer
        if self.memory_index:
            cleaned = await self.memory_index.cleanup_old_memories()
            cleanup_stats["memory_index"] = cleaned
        
        # Cleanup vector store
        if self.vector_store:
            cleaned = await self.vector_store.cleanup_old_vectors()
            cleanup_stats["vector_store"] = cleaned
        
        # Cleanup user memory
        if self.user_memory:
            cleaned = await self.user_memory.cleanup_expired_memories()
            cleanup_stats["user_memory"] = cleaned
        
        self.stats["last_cleanup"] = datetime.now()
        
        logger.info(f"Cleanup completed: {cleanup_stats}")
        return cleanup_stats
    
    async def optimize_memory_systems(self) -> Dict[str, Any]:
        """Optimize all memory systems for better performance"""
        await self.initialize()
        
        optimization_results = {}
        
        # Optimize memory indexer
        if self.memory_index:
            result = await self.memory_index.optimize_index()
            optimization_results["memory_index"] = result
        
        # Clear embedding cache
        if self.embedding_manager:
            self.embedding_manager.clear_cache()
            optimization_results["embedding_cache"] = "cleared"
        
        # Clear search cache
        if self.hybrid_search:
            self.hybrid_search.clear_cache()
            optimization_results["search_cache"] = "cleared"
        
        logger.info("Memory systems optimization completed")
        return optimization_results
    
    async def search_similar_memories(
        self,
        memory_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find memories similar to a specific memory"""
        await self.initialize()
        
        if not self.vector_store:
            raise ValueError("Vector store not available")
        
        try:
            # Get the original memory's embedding
            vector_entry = await self.vector_store.get_vector(memory_id)
            if not vector_entry:
                raise ValueError(f"Memory {memory_id} not found in vector store")
            
            # Search for similar vectors
            similar_results = await self.vector_store.search_similar(
                query_embedding=vector_entry.embedding,
                limit=limit,
                metadata_filter={"source": vector_entry.metadata.get("source")}
            )
            
            # Format results
            results = []
            for similar_entry, similarity in similar_results:
                results.append({
                    "id": similar_entry.id,
                    "content": similar_entry.content,
                    "similarity": similarity,
                    "metadata": similar_entry.metadata
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Similar memory search failed: {e}")
            raise
    
    async def _basic_search(
        self,
        query: str,
        filters: SearchFilters,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Basic text-based search as fallback"""
        # This is a simplified implementation
        # In practice, you'd implement a proper text search
        
        all_results = []
        
        # Search through vector store
        if self.vector_store and self.embedding_manager:
            try:
                query_embedding = await self.embedding_manager.generate_embedding(query)
                vector_results = await self.vector_store.search_similar(
                    query_embedding.embedding,
                    limit=limit,
                    threshold=0.0  # Lower threshold for basic search
                )
                
                for entry, score in vector_results:
                    all_results.append({
                        "id": entry.id,
                        "content": entry.content,
                        "score": score,
                        "source": entry.metadata.get("source", "unknown")
                    })
            except Exception as e:
                logger.warning(f"Vector search failed in basic search: {e}")
        
        return all_results[:limit]
    
    def _map_memory_type(self, memory_type: str) -> MemoryType:
        """Map string to MemoryType enum"""
        try:
            return MemoryType(memory_type)
        except ValueError:
            return MemoryType.CUSTOM
    
    def _map_priority(self, priority: int) -> MemoryPriority:
        """Map int to MemoryPriority enum"""
        try:
            return MemoryPriority(priority)
        except ValueError:
            return MemoryPriority.MEDIUM
    
    def _map_memory_source(self, source: str) -> MemorySource:
        """Map string to MemorySource enum"""
        source_map = {
            "user": MemorySource.USER_MEMORY,
            "conversation": MemorySource.CONVERSATION_HISTORY,
            "context": MemorySource.CONTEXT_CACHE,
            "vector": MemorySource.VECTOR_STORE,
            "external": MemorySource.EXTERNAL
        }
        
        return source_map.get(source.lower(), MemorySource.EXTERNAL)
    
    async def close(self):
        """Close all memory management components"""
        logger.info("Closing Enhanced Memory Manager...")
        
        # Close components in reverse order
        if self.user_memory:
            await self.user_memory.close()
        
        if self.batch_processor:
            # Batch processor doesn't have a close method currently
            pass
        
        if self.hybrid_search:
            # Hybrid search doesn't have a close method currently
            pass
        
        if self.memory_index:
            # Memory indexer doesn't have a close method currently
            pass
        
        if self.vector_store:
            await self.vector_store.close()
        
        if self.embedding_manager:
            # Embedding manager doesn't have a close method currently
            pass
        
        self.initialized = False
        logger.info("Enhanced Memory Manager closed")