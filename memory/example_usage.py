"""
Enhanced Memory System Usage Example

This example demonstrates how to use the enhanced memory management system
with vector database support, hybrid search, and batch processing capabilities.
"""

import asyncio
import logging
from typing import List, Dict, Any

# Import the enhanced memory management system
from memory import (
    EnhancedMemoryManager,
    EnhancedMemoryConfig,
    SearchStrategy,
    WeightingScheme,
    MemorySource,
    MemoryType,
    MemoryPriority,
    BatchProcessor,
    OperationType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_memory_operations():
    """Demonstrate basic memory operations"""
    logger.info("=== Basic Memory Operations ===")
    
    # Configure the enhanced memory manager
    config = EnhancedMemoryConfig(
        # Use fake embeddings for demonstration
        embedding_provider="fake",
        embedding_model="fake-embedding-model",
        
        # Enable all features
        enable_vector_store=True,
        enable_fulltext_indexing=True,
        
        # Configure search
        hybrid_search_weights=(0.7, 0.3),
        max_search_results=10,
        
        # Configure batch processing
        batch_size=5,
        max_concurrent_batches=2
    )
    
    # Initialize the enhanced memory manager
    memory_manager = EnhancedMemoryManager(config)
    await memory_manager.initialize()
    
    # Store some sample memories
    sample_memories = [
        {
            "content": "Python is a high-level programming language with dynamic semantics",
            "source": "programming",
            "memory_type": "technical",
            "priority": 2,
            "tags": ["python", "programming", "language"],
            "metadata": {"category": "technology", "importance": "high"}
        },
        {
            "content": "Machine learning involves training algorithms on data to make predictions",
            "source": "programming",
            "memory_type": "technical", 
            "priority": 1,
            "tags": ["machine-learning", "ai", "algorithms"],
            "metadata": {"category": "technology", "importance": "high"}
        },
        {
            "content": "The user prefers working in the morning and drinking coffee",
            "source": "user_preference",
            "memory_type": "preference",
            "priority": 3,
            "tags": ["schedule", "preference", "coffee"],
            "metadata": {"user": "persona"}
        }
    ]
    
    # Store individual memories
    memory_ids = []
    for memory_data in sample_memories:
        memory_id = await memory_manager.store_memory(
            content=memory_data["content"],
            source=memory_data["source"],
            memory_type=memory_data["memory_type"],
            priority=memory_data["priority"],
            tags=memory_data["tags"],
            metadata=memory_data["metadata"]
        )
        memory_ids.append(memory_id)
        logger.info(f"Stored memory: {memory_id}")
    
    return memory_manager, memory_ids


async def search_operations(memory_manager: EnhancedMemoryManager):
    """Demonstrate search operations"""
    logger.info("\n=== Search Operations ===")
    
    # Basic search
    search_queries = [
        "Python programming language",
        "machine learning algorithms", 
        "user preferences morning coffee"
    ]
    
    for query in search_queries:
        logger.info(f"\nSearching for: '{query}'")
        
        results = await memory_manager.search_memories(
            query=query,
            limit=5,
            strategy="hybrid"
        )
        
        logger.info(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            logger.info(f"  {i}. Score: {result['score']:.3f}")
            logger.info(f"     Content: {result['content'][:100]}...")
            logger.info(f"     Source: {result.get('source', 'unknown')}")
            if result.get('snippet'):
                logger.info(f"     Snippet: {result['snippet']}")


async def batch_operations(memory_manager: EnhancedMemoryManager):
    """Demonstrate batch operations"""
    logger.info("\n=== Batch Operations ===")
    
    # Create a batch of memories to store
    batch_memories = [
        {
            "content": f"Technical note #{i}: This is a sample technical content for batch processing",
            "source": "batch",
            "memory_type": "technical",
            "priority": 4,
            "tags": ["batch", "technical", f"note-{i}"],
            "metadata": {"batch_id": "example_batch", "index": i}
        }
        for i in range(1, 11)  # Create 10 memories
    ]
    
    # Store in batch
    logger.info("Storing memories in batch...")
    batch_result = await memory_manager.batch_store_memories(batch_memories)
    
    logger.info(f"Batch operation completed:")
    logger.info(f"  Total items: {batch_result.total_items}")
    logger.info(f"  Successful: {batch_result.successful_items}")
    logger.info(f"  Failed: {batch_result.failed_items}")
    logger.info(f"  Processing time: {batch_result.processing_time:.3f}s")
    logger.info(f"  Items per second: {batch_result.items_per_second:.1f}")


async def memory_statistics(memory_manager: EnhancedMemoryManager):
    """Demonstrate memory statistics and monitoring"""
    logger.info("\n=== Memory Statistics ===")
    
    # Get comprehensive statistics
    stats = await memory_manager.get_memory_stats()
    
    logger.info("Enhanced Memory System Statistics:")
    logger.info(f"  Memories stored: {stats['enhanced_memory']['memories_stored']}")
    logger.info(f"  Searches performed: {stats['enhanced_memory']['searches_performed']}")
    logger.info(f"  Embeddings generated: {stats['enhanced_memory']['embeddings_generated']}")
    logger.info(f"  Batch operations: {stats['enhanced_memory']['batch_operations']}")
    
    # Embedding manager stats
    if 'embedding_manager' in stats:
        embedding_stats = stats['embedding_manager']
        logger.info(f"\nEmbedding Manager:")
        logger.info(f"  Provider: {embedding_stats['provider']}")
        logger.info(f"  Model: {embedding_stats['model']}")
        logger.info(f"  Requests: {embedding_stats['requests']}")
        logger.info(f"  Cache hit rate: {embedding_stats['cache_hit_rate']:.3f}")
        logger.info(f"  Average processing time: {embedding_stats['average_processing_time']:.3f}s")
    
    # Vector store stats
    if 'vector_store' in stats:
        vector_stats = stats['vector_store']
        logger.info(f"\nVector Store:")
        logger.info(f"  Total vectors: {vector_stats['total_vectors']}")
        logger.info(f"  Average dimensions: {vector_stats['average_embedding_dimensions']}")
        logger.info(f"  Recent vectors: {vector_stats['recent_vectors']}")
    
    # Memory index stats
    if 'memory_index' in stats:
        index_stats = stats['memory_index']
        logger.info(f"\nMemory Index:")
        logger.info(f"  Status: {index_stats['status']}")
        logger.info(f"  Total memories: {index_stats['total_memories']}")
        logger.info(f"  Vector memories: {index_stats['vector_memories']}")
        logger.info(f"  Full-text memories: {index_stats['fulltext_memories']}")
    
    # Batch processor stats
    if 'batch_processor' in stats:
        batch_stats = stats['batch_processor']
        logger.info(f"\nBatch Processor:")
        logger.info(f"  Total batches: {batch_stats['total_batches']}")
        logger.info(f"  Success rate: {batch_stats['success_rate']:.3f}")
        logger.info(f"  Active batches: {batch_stats['active_batches']}")


async def advanced_features(memory_manager: EnhancedMemoryManager):
    """Demonstrate advanced features"""
    logger.info("\n=== Advanced Features ===")
    
    # Similar memory search (requires stored memories with embeddings)
    logger.info("Demonstrating similar memory search...")
    try:
        similar_results = await memory_manager.search_similar_memories(
            memory_id="example_memory_id",  # This would be a real memory ID
            limit=3
        )
        logger.info(f"Found {len(similar_results)} similar memories")
    except Exception as e:
        logger.info(f"Similar memory search not available: {e}")
    
    # Memory optimization
    logger.info("\nOptimizing memory systems...")
    optimization_results = await memory_manager.optimize_memory_systems()
    logger.info("Optimization completed:")
    for system, result in optimization_results.items():
        logger.info(f"  {system}: {result}")


async def memory_lifecycle_management(memory_manager: EnhancedMemoryManager):
    """Demonstrate memory lifecycle management"""
    logger.info("\n=== Memory Lifecycle Management ===")
    
    # Clean up old memories
    logger.info("Cleaning up old and low-importance memories...")
    cleanup_stats = await memory_manager.cleanup_old_memories()
    logger.info("Cleanup completed:")
    for system, count in cleanup_stats.items():
        logger.info(f"  {system}: {count} items cleaned")


async def main():
    """Main demonstration function"""
    logger.info("Starting Enhanced Memory System Demonstration")
    logger.info("=" * 60)
    
    try:
        # Run all demonstrations
        memory_manager, memory_ids = await basic_memory_operations()
        
        await search_operations(memory_manager)
        await batch_operations(memory_manager)
        await memory_statistics(memory_manager)
        await advanced_features(memory_manager)
        await memory_lifecycle_management(memory_manager)
        
        # Close the memory manager
        await memory_manager.close()
        
        logger.info("\n" + "=" * 60)
        logger.info("Enhanced Memory System demonstration completed successfully!")
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        raise


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())