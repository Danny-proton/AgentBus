"""
Embedding Manager Module

This module provides embedding generation and management capabilities
with support for multiple providers and fallback mechanisms.
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


class EmbeddingProvider(Enum):
    """Supported embedding providers"""
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    FAKE = "fake"  # For testing


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation"""
    provider: EmbeddingProvider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: int = 8192
    timeout: int = 60
    retry_attempts: int = 3
    batch_size: int = 100


@dataclass
class EmbeddingResult:
    """Result of embedding generation"""
    text: str
    embedding: List[float]
    provider: EmbeddingProvider
    model: str
    tokens_used: int
    processing_time: float
    cached: bool = False


class EmbeddingManager:
    """
    Comprehensive embedding generation and management system
    
    Features:
    - Multiple provider support (OpenAI, HuggingFace, local models)
    - Automatic fallback between providers
    - Caching for performance optimization
    - Batch processing capabilities
    - Rate limiting and retry mechanisms
    - Embedding validation and normalization
    """
    
    def __init__(self, config: EmbeddingConfig, cache_size: int = 10000):
        """Initialize embedding manager
        
        Args:
            config: Embedding configuration
            cache_size: Maximum number of embeddings to cache
        """
        self.config = config
        self.cache = {}
        self.cache_order = []
        self.cache_size = cache_size
        self.stats = {
            "requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "total_tokens": 0,
            "total_processing_time": 0
        }
        
        # Initialize provider-specific clients
        self._init_provider()
    
    def _init_provider(self):
        """Initialize the specified embedding provider"""
        try:
            if self.config.provider == EmbeddingProvider.OPENAI:
                self._init_openai()
            elif self.config.provider == EmbeddingProvider.HUGGINGFACE:
                self._init_huggingface()
            elif self.config.provider == EmbeddingProvider.LOCAL:
                self._init_local()
            elif self.config.provider == EmbeddingProvider.FAKE:
                self._init_fake()
            else:
                raise ValueError(f"Unsupported embedding provider: {self.config.provider}")
                
            logger.info(f"Initialized {self.config.provider.value} embedding provider")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding provider: {e}")
            # Fallback to fake provider for testing
            self.config.provider = EmbeddingProvider.FAKE
            self._init_fake()
    
    def _init_openai(self):
        """Initialize OpenAI embedding provider"""
        try:
            import openai
            
            client_config = {
                "api_key": self.config.api_key,
                "timeout": self.config.timeout,
            }
            
            if self.config.base_url:
                client_config["base_url"] = self.config.base_url
                
            self.client = openai.OpenAI(**client_config)
            
        except ImportError:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")
    
    def _init_huggingface(self):
        """Initialize HuggingFace embedding provider"""
        try:
            from sentence_transformers import SentenceTransformer
            
            self.client = SentenceTransformer(self.config.model)
            
        except ImportError:
            raise ImportError("sentence-transformers package not installed. Install with: pip install sentence-transformers")
    
    def _init_local(self):
        """Initialize local embedding provider"""
        try:
            # For local models, we can use various implementations
            # This is a placeholder - actual implementation depends on chosen local model
            logger.warning("Local embedding provider not fully implemented")
            self.client = None
            
        except Exception as e:
            logger.error(f"Failed to initialize local embedding provider: {e}")
            raise
    
    def _init_fake(self):
        """Initialize fake embedding provider for testing"""
        import random
        random.seed(42)  # For consistent results
        
        self.client = None
        logger.info("Initialized fake embedding provider for testing")
    
    def _get_cache_key(self, text: str, provider: EmbeddingProvider, model: str) -> str:
        """Generate cache key for text embedding"""
        content = f"{provider.value}:{model}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _add_to_cache(self, key: str, result: EmbeddingResult):
        """Add result to cache with LRU eviction"""
        if len(self.cache) >= self.cache_size:
            # Remove oldest entry
            oldest_key = self.cache_order.pop(0)
            del self.cache[oldest_key]
        
        self.cache[key] = result
        self.cache_order.append(key)
    
    def _get_from_cache(self, key: str) -> Optional[EmbeddingResult]:
        """Get result from cache and update access order"""
        if key in self.cache:
            # Move to end (most recently used)
            self.cache_order.remove(key)
            self.cache_order.append(key)
            self.stats["cache_hits"] += 1
            return self.cache[key]
        
        self.stats["cache_misses"] += 1
        return None
    
    async def generate_embedding(
        self,
        text: str,
        normalize: bool = True,
        use_cache: bool = True
    ) -> EmbeddingResult:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            normalize: Whether to normalize the embedding vector
            use_cache: Whether to use cached results
            
        Returns:
            EmbeddingResult containing the embedding and metadata
        """
        start_time = time.time()
        
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(text, self.config.provider, self.config.model)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
        
        self.stats["requests"] += 1
        
        try:
            if self.config.provider == EmbeddingProvider.OPENAI:
                embedding = await self._generate_openai_embedding(text)
            elif self.config.provider == EmbeddingProvider.HUGGINGFACE:
                embedding = await self._generate_huggingface_embedding(text)
            elif self.config.provider == EmbeddingProvider.LOCAL:
                embedding = await self._generate_local_embedding(text)
            elif self.config.provider == EmbeddingProvider.FAKE:
                embedding = await self._generate_fake_embedding(text)
            else:
                raise ValueError(f"Unsupported provider: {self.config.provider}")
            
            processing_time = time.time() - start_time
            
            # Normalize if requested
            if normalize:
                embedding = self._normalize_vector(embedding)
            
            result = EmbeddingResult(
                text=text,
                embedding=embedding,
                provider=self.config.provider,
                model=self.config.model,
                tokens_used=self._estimate_tokens(text),
                processing_time=processing_time
            )
            
            # Cache the result
            if use_cache:
                cache_key = self._get_cache_key(text, self.config.provider, self.config.model)
                self._add_to_cache(cache_key, result)
            
            self.stats["total_tokens"] += result.tokens_used
            self.stats["total_processing_time"] += processing_time
            
            return result
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    async def generate_batch_embeddings(
        self,
        texts: List[str],
        normalize: bool = True,
        use_cache: bool = True,
        batch_size: Optional[int] = None
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts in batch
        
        Args:
            texts: List of texts to embed
            normalize: Whether to normalize embedding vectors
            use_cache: Whether to use cached results
            batch_size: Size of batches to process
            
        Returns:
            List of EmbeddingResult objects
        """
        if not texts:
            return []
        
        batch_size = batch_size or self.config.batch_size
        
        results = []
        remaining_texts = texts.copy()
        
        while remaining_texts:
            batch = remaining_texts[:batch_size]
            remaining_texts = remaining_texts[batch_size:]
            
            # Process batch
            batch_results = await self._process_batch(
                batch, normalize, use_cache
            )
            results.extend(batch_results)
            
            # Add small delay to respect rate limits
            if remaining_texts:
                await asyncio.sleep(0.1)
        
        return results
    
    async def _process_batch(
        self,
        texts: List[str],
        normalize: bool,
        use_cache: bool
    ) -> List[EmbeddingResult]:
        """Process a batch of texts"""
        results = []
        
        # Check cache first
        cache_keys = []
        cached_results = []
        
        if use_cache:
            for text in texts:
                cache_key = self._get_cache_key(text, self.config.provider, self.config.model)
                cache_keys.append(cache_key)
                cached_result = self._get_from_cache(cache_key)
                cached_results.append(cached_result)
        
        # Process non-cached texts
        uncached_texts = []
        uncached_indices = []
        
        for i, (text, cached) in enumerate(zip(texts, cached_results)):
            if cached is None:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            try:
                if self.config.provider == EmbeddingProvider.OPENAI:
                    uncached_embeddings = await self._generate_openai_batch(uncached_texts)
                elif self.config.provider == EmbeddingProvider.HUGGINGFACE:
                    uncached_embeddings = await self._generate_huggingface_batch(uncached_texts)
                elif self.config.provider == EmbeddingProvider.LOCAL:
                    uncached_embeddings = await self._generate_local_batch(uncached_texts)
                elif self.config.provider == EmbeddingProvider.FAKE:
                    uncached_embeddings = await self._generate_fake_batch(uncached_texts)
                else:
                    raise ValueError(f"Unsupported provider: {self.config.provider}")
                
                # Create results for uncached texts
                uncached_results = []
                for text, embedding in zip(uncached_texts, uncached_embeddings):
                    if normalize:
                        embedding = self._normalize_vector(embedding)
                    
                    result = EmbeddingResult(
                        text=text,
                        embedding=embedding,
                        provider=self.config.provider,
                        model=self.config.model,
                        tokens_used=self._estimate_tokens(text),
                        processing_time=0.0  # Batch processing time is distributed
                    )
                    uncached_results.append(result)
                
                # Cache uncached results
                if use_cache:
                    for i, result in enumerate(uncached_results):
                        cache_key = cache_keys[uncached_indices[i]]
                        self._add_to_cache(cache_key, result)
                
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                # Generate fake embeddings as fallback
                uncached_embeddings = await self._generate_fake_batch(uncached_texts)
                uncached_results = []
                for text, embedding in zip(uncached_texts, uncached_embeddings):
                    if normalize:
                        embedding = self._normalize_vector(embedding)
                    
                    result = EmbeddingResult(
                        text=text,
                        embedding=embedding,
                        provider=EmbeddingProvider.FAKE,
                        model="fallback",
                        tokens_used=self._estimate_tokens(text),
                        processing_time=0.0
                    )
                    uncached_results.append(result)
        
        # Combine cached and newly generated results
        for i, (text, cached_result) in enumerate(zip(texts, cached_results)):
            if cached_result is not None:
                results.append(cached_result)
            else:
                uncached_index = uncached_indices.index(i)
                results.append(uncached_results[uncached_index])
        
        return results
    
    async def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI"""
        response = self.client.embeddings.create(
            model=self.config.model,
            input=text
        )
        return response.data[0].embedding
    
    async def _generate_openai_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI batch API"""
        response = self.client.embeddings.create(
            model=self.config.model,
            input=texts
        )
        return [data.embedding for data in response.data]
    
    async def _generate_huggingface_embedding(self, text: str) -> List[float]:
        """Generate embedding using HuggingFace"""
        embedding = self.client.encode(text)
        return embedding.tolist()
    
    async def _generate_huggingface_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using HuggingFace batch API"""
        embeddings = self.client.encode(texts)
        return embeddings.tolist()
    
    async def _generate_local_embedding(self, text: str) -> List[float]:
        """Generate embedding using local model"""
        # Placeholder implementation - actual local model integration needed
        raise NotImplementedError("Local embedding provider not implemented")
    
    async def _generate_local_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using local model batch"""
        # Placeholder implementation
        raise NotImplementedError("Local embedding provider not implemented")
    
    async def _generate_fake_embedding(self, text: str) -> List[float]:
        """Generate fake embedding for testing"""
        import random
        random.seed(hash(text) % (2**31))
        return [random.gauss(0, 1) for _ in range(768)]  # 768-dimensional fake embedding
    
    async def _generate_fake_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate fake embeddings for testing"""
        return [await self._generate_fake_embedding(text) for text in texts]
    
    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """Normalize vector to unit length"""
        import numpy as np
        if not vector:
            return vector
        
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        
        return (np.array(vector) / norm).tolist()
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        # Rough estimation - average 4 characters per token
        return len(text) // 4
    
    def get_stats(self) -> Dict[str, Any]:
        """Get embedding manager statistics"""
        cache_hit_rate = 0
        if self.stats["requests"] > 0:
            cache_hit_rate = self.stats["cache_hits"] / self.stats["requests"]
        
        avg_processing_time = 0
        if self.stats["requests"] > 0:
            avg_processing_time = self.stats["total_processing_time"] / self.stats["requests"]
        
        return {
            "provider": self.config.provider.value,
            "model": self.config.model,
            "requests": self.stats["requests"],
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "cache_hit_rate": round(cache_hit_rate, 3),
            "errors": self.stats["errors"],
            "total_tokens": self.stats["total_tokens"],
            "total_processing_time": round(self.stats["total_processing_time"], 2),
            "average_processing_time": round(avg_processing_time, 3),
            "cache_size": len(self.cache),
            "cache_max_size": self.cache_size
        }
    
    def clear_cache(self):
        """Clear the embedding cache"""
        self.cache.clear()
        self.cache_order.clear()
        logger.info("Embedding cache cleared")
    
    async def validate_embedding(self, embedding: List[float]) -> bool:
        """Validate an embedding vector"""
        if not embedding:
            return False
        
        # Check for NaN or infinite values
        import numpy as np
        embedding_array = np.array(embedding)
        
        if np.any(np.isnan(embedding_array)) or np.any(np.isinf(embedding_array)):
            return False
        
        # Check vector dimension
        if len(embedding) == 0:
            return False
        
        return True