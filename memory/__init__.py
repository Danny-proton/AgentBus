"""
AgentBus Memory System

This package provides comprehensive memory management capabilities including:
- User memory management
- Conversation history tracking  
- Context caching
- Vector database support
- Embedding generation and management
- Hybrid search capabilities
- Batch processing operations
- Memory indexing and search
- Enhanced memory management (Moltbot-inspired)

Based on the Moltbot memory system architecture with the following enhancements:
1. Vector database support for semantic search
2. Hybrid memory storage combining multiple approaches
3. Batch processing capabilities for performance
4. Embedding generation with multiple provider support
5. Memory indexing with automatic cleanup and optimization
"""

from .user_memory import UserMemory, MemoryType, MemoryPriority
from .conversation_history import ConversationHistory
from .context_cache import ContextCache

# Enhanced memory management components
from .vector_store import VectorStore, VectorEntry
from .embedding_manager import (
    EmbeddingManager, 
    EmbeddingConfig, 
    EmbeddingProvider,
    EmbeddingResult
)
from .hybrid_search import (
    HybridSearchEngine,
    SearchQuery,
    SearchResult,
    SearchStrategy,
    WeightingScheme
)
from .batch_processor import (
    BatchProcessor,
    BatchConfig,
    BatchResult,
    OperationType,
    AsyncBatchProcessor
)
from .memory_index import (
    MemoryIndexer,
    IndexConfig,
    SearchFilters,
    MemorySource,
    IndexedMemory
)
from .enhanced_memory_manager import (
    EnhancedMemoryManager,
    EnhancedMemoryConfig
)

__all__ = [
    # Original components
    'UserMemory', 
    'ConversationHistory', 
    'ContextCache',
    'MemoryType',
    'MemoryPriority',
    
    # Enhanced components
    'VectorStore',
    'VectorEntry',
    'EmbeddingManager',
    'EmbeddingConfig',
    'EmbeddingProvider',
    'EmbeddingResult',
    'HybridSearchEngine',
    'SearchQuery',
    'SearchResult',
    'SearchStrategy',
    'WeightingScheme',
    'BatchProcessor',
    'BatchConfig',
    'BatchResult',
    'OperationType',
    'AsyncBatchProcessor',
    'MemoryIndexer',
    'IndexConfig',
    'SearchFilters',
    'MemorySource',
    'IndexedMemory',
    'EnhancedMemoryManager',
    'EnhancedMemoryConfig'
]

__version__ = '2.0.0'