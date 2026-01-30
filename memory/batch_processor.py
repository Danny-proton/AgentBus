"""
Batch Processor Module

This module provides batch processing capabilities for memory operations,
including batch embedding generation, storage, and retrieval operations.
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional, Callable, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue, Empty

logger = logging.getLogger(__name__)


class BatchStatus(Enum):
    """Batch operation status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OperationType(Enum):
    """Batch operation types"""
    EMBEDDING_GENERATION = "embedding_generation"
    MEMORY_STORAGE = "memory_storage"
    MEMORY_RETRIEVAL = "memory_retrieval"
    MEMORY_UPDATE = "memory_update"
    MEMORY_DELETION = "memory_deletion"
    VECTOR_SEARCH = "vector_search"
    CUSTOM = "custom"


@dataclass
class BatchItem:
    """Individual batch item"""
    id: str
    data: Any
    metadata: Optional[Dict[str, Any]] = None
    status: BatchStatus = BatchStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    processing_time: float = 0.0
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class BatchResult:
    """Batch operation result"""
    batch_id: str
    operation_type: OperationType
    total_items: int
    successful_items: int
    failed_items: int
    results: List[Any]
    errors: List[str]
    processing_time: float
    items_per_second: float
    status: BatchStatus


@dataclass
class BatchConfig:
    """Batch processing configuration"""
    max_workers: int = 4
    batch_size: int = 100
    timeout: float = 300.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    progress_callback: Optional[Callable[[int, int], None]] = None
    error_callback: Optional[Callable[[str, Exception], None]] = None


class BatchProcessor:
    """
    Comprehensive batch processing system for memory operations
    
    Features:
    - Concurrent batch processing with configurable workers
    - Progress tracking and callbacks
    - Error handling and retry mechanisms
    - Memory-efficient streaming for large datasets
    - Support for custom operations
    - Batch result caching and statistics
    """
    
    def __init__(self, config: Optional[BatchConfig] = None):
        """Initialize batch processor
        
        Args:
            config: Batch processing configuration
        """
        self.config = config or BatchConfig()
        
        # Active batches tracking
        self.active_batches = {}
        self.batch_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "total_batches": 0,
            "successful_batches": 0,
            "failed_batches": 0,
            "total_items_processed": 0,
            "total_processing_time": 0.0
        }
        
        logger.info("Batch processor initialized")
    
    async def process_batch(
        self,
        batch_id: str,
        items: List[Any],
        operation_type: OperationType,
        processor_func: Callable,
        config: Optional[BatchConfig] = None
    ) -> BatchResult:
        """
        Process a batch of items
        
        Args:
            batch_id: Unique batch identifier
            items: List of items to process
            operation_type: Type of operation being performed
            processor_func: Function to process individual items
            config: Optional batch configuration override
            
        Returns:
            BatchResult with processing results
        """
        batch_config = config or self.config
        
        logger.info(f"Starting batch {batch_id} with {len(items)} items")
        
        start_time = time.time()
        batch_items = [
            BatchItem(
                id=f"{batch_id}_{i}",
                data=item,
                metadata={"batch_id": batch_id, "index": i}
            )
            for i, item in enumerate(items)
        ]
        
        # Track active batch
        with self.batch_lock:
            self.active_batches[batch_id] = {
                "status": BatchStatus.RUNNING,
                "total_items": len(batch_items),
                "completed_items": 0,
                "start_time": start_time
            }
        
        try:
            # Process batch
            results, errors = await self._process_batch_items(
                batch_items, processor_func, batch_config
            )
            
            # Calculate metrics
            processing_time = time.time() - start_time
            successful_count = len(results)
            failed_count = len(errors)
            items_per_second = len(batch_items) / processing_time if processing_time > 0 else 0
            
            # Create result
            batch_result = BatchResult(
                batch_id=batch_id,
                operation_type=operation_type,
                total_items=len(batch_items),
                successful_items=successful_count,
                failed_items=failed_count,
                results=results,
                errors=errors,
                processing_time=processing_time,
                items_per_second=items_per_second,
                status=BatchStatus.COMPLETED if failed_count == 0 else BatchStatus.FAILED
            )
            
            # Update statistics
            self._update_stats(batch_result)
            
            logger.info(f"Batch {batch_id} completed: {successful_count}/{len(batch_items)} successful")
            
            return batch_result
            
        except Exception as e:
            logger.error(f"Batch {batch_id} failed: {e}")
            
            # Create failed result
            processing_time = time.time() - start_time
            batch_result = BatchResult(
                batch_id=batch_id,
                operation_type=operation_type,
                total_items=len(batch_items),
                successful_items=0,
                failed_items=len(batch_items),
                results=[],
                errors=[str(e)],
                processing_time=processing_time,
                items_per_second=0,
                status=BatchStatus.FAILED
            )
            
            self._update_stats(batch_result)
            raise
            
        finally:
            # Remove from active batches
            with self.batch_lock:
                if batch_id in self.active_batches:
                    del self.active_batches[batch_id]
    
    async def _process_batch_items(
        self,
        batch_items: List[BatchItem],
        processor_func: Callable,
        config: BatchConfig
    ) -> Tuple[List[Any], List[str]]:
        """Process batch items with concurrency control"""
        results = []
        errors = []
        
        # Process items in chunks to control memory usage
        for chunk_start in range(0, len(batch_items), config.batch_size):
            chunk = batch_items[chunk_start:chunk_start + config.batch_size]
            
            # Process chunk
            chunk_results, chunk_errors = await self._process_chunk(
                chunk, processor_func, config
            )
            
            results.extend(chunk_results)
            errors.extend(chunk_errors)
            
            # Update progress
            if config.progress_callback:
                completed = len(results) + len(errors)
                config.progress_callback(completed, len(batch_items))
        
        return results, errors
    
    async def _process_chunk(
        self,
        chunk: List[BatchItem],
        processor_func: Callable,
        config: BatchConfig
    ) -> Tuple[List[Any], List[str]]:
        """Process a chunk of items concurrently"""
        results = []
        errors = []
        
        # Use ThreadPoolExecutor for CPU-bound operations
        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            # Submit all tasks
            future_to_item = {
                executor.submit(
                    self._process_item_sync,
                    item,
                    processor_func,
                    config
                ): item for item in chunk
            }
            
            # Collect results
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result(timeout=config.timeout)
                    results.append(result)
                except Exception as e:
                    error_msg = f"Item {item.id} failed: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    
                    # Call error callback if provided
                    if config.error_callback:
                        config.error_callback(item.id, e)
        
        return results, errors
    
    def _process_item_sync(
        self,
        item: BatchItem,
        processor_func: Callable,
        config: BatchConfig
    ) -> Any:
        """Process a single item synchronously"""
        item.started_at = datetime.now()
        item.status = BatchStatus.RUNNING
        
        start_time = time.time()
        
        try:
            # Retry logic
            for attempt in range(config.retry_attempts):
                try:
                    result = processor_func(item.data, item.metadata)
                    
                    item.result = result
                    item.status = BatchStatus.COMPLETED
                    item.processing_time = time.time() - start_time
                    item.completed_at = datetime.now()
                    
                    return result
                    
                except Exception as e:
                    if attempt == config.retry_attempts - 1:
                        # Final attempt failed
                        item.error = str(e)
                        item.status = BatchStatus.FAILED
                        item.processing_time = time.time() - start_time
                        item.completed_at = datetime.now()
                        raise
                    else:
                        # Retry with delay
                        logger.warning(f"Item {item.id} attempt {attempt + 1} failed, retrying...")
                        time.sleep(config.retry_delay * (2 ** attempt))  # Exponential backoff
            
        except Exception:
            # Ensure item is marked as failed
            if item.status == BatchStatus.RUNNING:
                item.status = BatchStatus.FAILED
                item.completed_at = datetime.now()
            raise
    
    async def process_streaming_batch(
        self,
        batch_id: str,
        item_generator: Callable[[], Any],
        total_items: int,
        operation_type: OperationType,
        processor_func: Callable,
        config: Optional[BatchConfig] = None
    ) -> BatchResult:
        """
        Process items from a streaming source
        
        Args:
            batch_id: Unique batch identifier
            item_generator: Generator function that yields items
            total_items: Total number of items expected
            operation_type: Type of operation being performed
            processor_func: Function to process individual items
            config: Optional batch configuration override
            
        Returns:
            BatchResult with processing results
        """
        batch_config = config or self.config
        
        logger.info(f"Starting streaming batch {batch_id} with ~{total_items} items")
        
        start_time = time.time()
        
        # Track active batch
        with self.batch_lock:
            self.active_batches[batch_id] = {
                "status": BatchStatus.RUNNING,
                "total_items": total_items,
                "completed_items": 0,
                "start_time": start_time
            }
        
        try:
            results = []
            errors = []
            processed_count = 0
            
            # Process items in batches
            while True:
                # Collect batch of items from generator
                batch = []
                try:
                    for _ in range(batch_config.batch_size):
                        item = next(item_generator)
                        batch.append(item)
                except StopIteration:
                    break
                
                if not batch:
                    break
                
                # Process batch
                batch_results, batch_errors = await self._process_batch_items(
                    [
                        BatchItem(
                            id=f"{batch_id}_{processed_count + i}",
                            data=item,
                            metadata={"batch_id": batch_id, "index": processed_count + i}
                        )
                        for i, item in enumerate(batch)
                    ],
                    processor_func,
                    batch_config
                )
                
                results.extend(batch_results)
                errors.extend(batch_errors)
                processed_count += len(batch)
                
                # Update progress
                if batch_config.progress_callback:
                    batch_config.progress_callback(processed_count, total_items)
                
                # Update active batch status
                with self.batch_lock:
                    if batch_id in self.active_batches:
                        self.active_batches[batch_id]["completed_items"] = processed_count
            
            # Calculate metrics
            processing_time = time.time() - start_time
            items_per_second = processed_count / processing_time if processing_time > 0 else 0
            
            # Create result
            batch_result = BatchResult(
                batch_id=batch_id,
                operation_type=operation_type,
                total_items=processed_count,
                successful_items=len(results),
                failed_items=len(errors),
                results=results,
                errors=errors,
                processing_time=processing_time,
                items_per_second=items_per_second,
                status=BatchStatus.COMPLETED if len(errors) == 0 else BatchStatus.FAILED
            )
            
            # Update statistics
            self._update_stats(batch_result)
            
            logger.info(f"Streaming batch {batch_id} completed: {len(results)}/{processed_count} successful")
            
            return batch_result
            
        except Exception as e:
            logger.error(f"Streaming batch {batch_id} failed: {e}")
            
            # Create failed result
            processing_time = time.time() - start_time
            batch_result = BatchResult(
                batch_id=batch_id,
                operation_type=operation_type,
                total_items=total_items,
                successful_items=0,
                failed_items=total_items,
                results=[],
                errors=[str(e)],
                processing_time=processing_time,
                items_per_second=0,
                status=BatchStatus.FAILED
            )
            
            self._update_stats(batch_result)
            raise
            
        finally:
            # Remove from active batches
            with self.batch_lock:
                if batch_id in self.active_batches:
                    del self.active_batches[batch_id]
    
    def get_batch_status(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific batch"""
        with self.batch_lock:
            return self.active_batches.get(batch_id)
    
    def list_active_batches(self) -> List[Dict[str, Any]]:
        """List all active batches"""
        with self.batch_lock:
            return list(self.active_batches.values())
    
    def cancel_batch(self, batch_id: str) -> bool:
        """Cancel an active batch"""
        with self.batch_lock:
            if batch_id in self.active_batches:
                self.active_batches[batch_id]["status"] = BatchStatus.CANCELLED
                return True
        return False
    
    def _update_stats(self, result: BatchResult):
        """Update processor statistics"""
        with self.batch_lock:
            self.stats["total_batches"] += 1
            self.stats["total_items_processed"] += result.total_items
            self.stats["total_processing_time"] += result.processing_time
            
            if result.status == BatchStatus.COMPLETED:
                self.stats["successful_batches"] += 1
            else:
                self.stats["failed_batches"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batch processor statistics"""
        with self.batch_lock:
            avg_processing_time = 0
            if self.stats["total_batches"] > 0:
                avg_processing_time = self.stats["total_processing_time"] / self.stats["total_batches"]
            
            success_rate = 0
            if self.stats["total_batches"] > 0:
                success_rate = self.stats["successful_batches"] / self.stats["total_batches"]
            
            return {
                "total_batches": self.stats["total_batches"],
                "successful_batches": self.stats["successful_batches"],
                "failed_batches": self.stats["failed_batches"],
                "success_rate": round(success_rate, 3),
                "total_items_processed": self.stats["total_items_processed"],
                "total_processing_time": round(self.stats["total_processing_time"], 2),
                "average_processing_time": round(avg_processing_time, 2),
                "active_batches": len(self.active_batches)
            }
    
    async def process_embeddings_batch(
        self,
        texts: List[str],
        embedding_func: Callable[[str], Any],
        batch_id: Optional[str] = None
    ) -> BatchResult:
        """
        Convenience method for batch embedding generation
        
        Args:
            texts: List of texts to embed
            embedding_func: Function that generates embeddings
            batch_id: Optional batch identifier
            
        Returns:
            BatchResult with embedding results
        """
        if batch_id is None:
            batch_id = f"embeddings_{int(time.time())}"
        
        def process_embedding(text, metadata):
            return embedding_func(text)
        
        return await self.process_batch(
            batch_id=batch_id,
            items=texts,
            operation_type=OperationType.EMBEDDING_GENERATION,
            processor_func=process_embedding
        )
    
    async def process_memory_operations_batch(
        self,
        operations: List[Tuple[str, Dict[str, Any], Callable]],
        batch_id: Optional[str] = None
    ) -> BatchResult:
        """
        Process a batch of memory operations
        
        Args:
            operations: List of (operation_type, data, function) tuples
            batch_id: Optional batch identifier
            
        Returns:
            BatchResult with operation results
        """
        if batch_id is None:
            batch_id = f"memory_ops_{int(time.time())}"
        
        def process_memory_op(operation_data, metadata):
            op_type, data, func = operation_data
            return func(data)
        
        return await self.process_batch(
            batch_id=batch_id,
            items=operations,
            operation_type=OperationType.CUSTOM,
            processor_func=process_memory_op
        )
    
    async def cleanup_completed_batches(self, max_age_hours: int = 24) -> int:
        """Cleanup old completed batches from statistics"""
        # This is a placeholder - in practice, you'd maintain
        # a history of completed batches and clean up old ones
        logger.info("Batch cleanup completed")
        return 0


class AsyncBatchProcessor:
    """Asynchronous batch processor for memory-intensive operations"""
    
    def __init__(self, max_concurrent_batches: int = 5):
        """Initialize async batch processor
        
        Args:
            max_concurrent_batches: Maximum number of concurrent batches
        """
        self.max_concurrent_batches = max_concurrent_batches
        self.semaphore = asyncio.Semaphore(max_concurrent_batches)
        self.active_tasks = set()
        
        logger.info("Async batch processor initialized")
    
    async def process_batch_with_semaphore(
        self,
        batch_processor: BatchProcessor,
        batch_id: str,
        items: List[Any],
        operation_type: OperationType,
        processor_func: Callable
    ) -> BatchResult:
        """Process batch with concurrency limiting"""
        async with self.semaphore:
            task = asyncio.create_task(
                batch_processor.process_batch(
                    batch_id, items, operation_type, processor_func
                )
            )
            self.active_tasks.add(task)
            
            try:
                result = await task
                return result
            finally:
                self.active_tasks.discard(task)
    
    async def cancel_all_batches(self):
        """Cancel all active batches"""
        for task in self.active_tasks:
            task.cancel()
        
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
        
        self.active_tasks.clear()
        logger.info("All batches cancelled")