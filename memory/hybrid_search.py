"""
Hybrid Search Module

This module provides hybrid search capabilities combining vector similarity
and keyword-based search for comprehensive memory retrieval.
"""

import asyncio
import json
import re
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import logging
import math
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SearchStrategy(Enum):
    """Search strategy types"""
    VECTOR_ONLY = "vector_only"
    KEYWORD_ONLY = "keyword_only"
    HYBRID = "hybrid"
    RANK_FUSION = "rank_fusion"


class WeightingScheme(Enum):
    """Weighting schemes for hybrid search"""
    EQUAL = "equal"
    VECTOR_WEIGHTED = "vector_weighted"
    KEYWORD_WEIGHTED = "keyword_weighted"
    ADAPTIVE = "adaptive"


@dataclass
class SearchQuery:
    """Search query structure"""
    text: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 10
    min_score: float = 0.0
    strategy: SearchStrategy = SearchStrategy.HYBRID
    weighting: WeightingScheme = WeightingScheme.HYBRID
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    time_decay: Optional[float] = None
    boost_recent: bool = True


@dataclass
class SearchResult:
    """Individual search result"""
    id: str
    content: str
    score: float
    vector_score: Optional[float] = None
    keyword_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    source: str = "unknown"
    created_at: Optional[datetime] = None
    access_count: int = 0
    snippet: Optional[str] = None


@dataclass
class SearchStats:
    """Search performance statistics"""
    total_results: int
    vector_results: int
    keyword_results: int
    processing_time: float
    cache_hits: int
    queries_executed: int


class HybridSearchEngine:
    """
    Hybrid search engine combining vector and keyword search
    
    Features:
    - Vector similarity search using embeddings
    - Full-text keyword search with BM25 ranking
    - Hybrid search with configurable weighting
    - Rank fusion algorithms
    - Result deduplication and reranking
    - Query expansion and semantic matching
    - Time-decay scoring
    """
    
    def __init__(self, 
                 vector_search_func=None,
                 keyword_search_func=None,
                 default_weights: Tuple[float, float] = (0.7, 0.3)):
        """Initialize hybrid search engine
        
        Args:
            vector_search_func: Function for vector similarity search
            keyword_search_func: Function for keyword search
            default_weights: Default (vector, keyword) weights
        """
        self.vector_search_func = vector_search_func
        self.keyword_search_func = keyword_search_func
        self.default_weights = default_weights
        
        # Query processing
        self.query_cache = {}
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they', 'have'
        }
        
        # Statistics
        self.stats = SearchStats(
            total_results=0,
            vector_results=0,
            keyword_results=0,
            processing_time=0.0,
            cache_hits=0,
            queries_executed=0
        )
        
        logger.info("Hybrid search engine initialized")
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Perform hybrid search
        
        Args:
            query: Search query configuration
            
        Returns:
            List of search results ranked by relevance
        """
        start_time = datetime.now()
        
        try:
            # Check cache first
            cache_key = self._get_cache_key(query)
            if cache_key in self.query_cache:
                self.stats.cache_hits += 1
                cached_results = self.query_cache[cache_key]
                # Update access time
                self.query_cache[cache_key]['accessed_at'] = start_time
                return cached_results
            
            self.stats.queries_executed += 1
            
            # Process query
            processed_query = self._preprocess_query(query)
            
            # Execute search based on strategy
            if query.strategy == SearchStrategy.VECTOR_ONLY:
                results = await self._vector_only_search(processed_query)
            elif query.strategy == SearchStrategy.KEYWORD_ONLY:
                results = await self._keyword_only_search(processed_query)
            elif query.strategy == SearchStrategy.HYBRID:
                results = await self._hybrid_search(processed_query)
            elif query.strategy == SearchStrategy.RANK_FUSION:
                results = await self._rank_fusion_search(processed_query)
            else:
                raise ValueError(f"Unknown search strategy: {query.strategy}")
            
            # Apply post-processing
            results = await self._postprocess_results(results, processed_query)
            
            # Cache results
            self._cache_results(cache_key, results)
            
            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(results, processing_time)
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def _preprocess_query(self, query: SearchQuery) -> SearchQuery:
        """Preprocess and expand query"""
        # Tokenize and clean query
        tokens = self._tokenize_query(query.text)
        
        # Expand query with synonyms or related terms
        expanded_tokens = self._expand_query(tokens)
        
        # Reconstruct query text
        expanded_text = " ".join(expanded_tokens)
        
        # Return updated query
        return SearchQuery(
            text=expanded_text,
            filters=query.filters,
            limit=query.limit,
            min_score=query.min_score,
            strategy=query.strategy,
            weighting=query.weighting,
            vector_weight=query.vector_weight,
            keyword_weight=query.keyword_weight,
            time_decay=query.time_decay,
            boost_recent=query.boost_recent
        )
    
    def _tokenize_query(self, text: str) -> List[str]:
        """Tokenize and clean query text"""
        # Convert to lowercase and remove punctuation
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split into tokens
        tokens = text.split()
        
        # Remove stop words and short tokens
        tokens = [
            token for token in tokens 
            if token not in self.stop_words and len(token) > 2
        ]
        
        return tokens
    
    def _expand_query(self, tokens: List[str]) -> List[str]:
        """Expand query with related terms (simplified)"""
        # This is a simplified expansion - in practice, you'd use
        # word embeddings, synonym dictionaries, or LLMs for expansion
        expanded = tokens.copy()
        
        # Add some basic expansions (could be enhanced)
        expansions = {
            'ai': ['artificial intelligence', 'machine learning'],
            'ml': ['machine learning', 'artificial intelligence'],
            'python': ['programming', 'code'],
            'code': ['programming', 'software'],
            'search': ['find', 'query', 'lookup']
        }
        
        for token in tokens:
            if token in expansions:
                expanded.extend(expansions[token])
        
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for token in expanded:
            if token not in seen:
                seen.add(token)
                result.append(token)
        
        return result
    
    async def _vector_only_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform vector-only search"""
        if not self.vector_search_func:
            logger.warning("Vector search function not available")
            return []
        
        # Generate query embedding
        vector_results = await self.vector_search_func(
            query_text=query.text,
            limit=query.limit * 2,  # Get more results for filtering
            filters=query.filters
        )
        
        # Convert to SearchResult format
        results = []
        for item in vector_results:
            result = SearchResult(
                id=item.get('id', ''),
                content=item.get('content', ''),
                score=item.get('similarity', 0.0),
                vector_score=item.get('similarity', 0.0),
                metadata=item.get('metadata', {}),
                source=item.get('source', 'vector'),
                created_at=item.get('created_at'),
                access_count=item.get('access_count', 0)
            )
            results.append(result)
        
        return results
    
    async def _keyword_only_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform keyword-only search"""
        if not self.keyword_search_func:
            logger.warning("Keyword search function not available")
            return []
        
        # Execute keyword search
        keyword_results = await self.keyword_search_func(
            query_text=query.text,
            limit=query.limit * 2,
            filters=query.filters
        )
        
        # Convert to SearchResult format
        results = []
        for item in keyword_results:
            result = SearchResult(
                id=item.get('id', ''),
                content=item.get('content', ''),
                score=item.get('relevance', 0.0),
                keyword_score=item.get('relevance', 0.0),
                metadata=item.get('metadata', {}),
                source=item.get('source', 'keyword'),
                created_at=item.get('created_at'),
                access_count=item.get('access_count', 0)
            )
            results.append(result)
        
        return results
    
    async def _hybrid_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform hybrid search combining vector and keyword results"""
        # Execute both searches in parallel
        vector_task = self._vector_only_search(query) if self.vector_search_func else asyncio.create_task(asyncio.sleep(0, return_value=[]))
        keyword_task = self._keyword_only_search(query) if self.keyword_search_func else asyncio.create_task(asyncio.sleep(0, return_value=[]))
        
        vector_results, keyword_results = await asyncio.gather(vector_task, keyword_task)
        
        # Normalize scores
        vector_results = self._normalize_scores(vector_results, 'vector_score')
        keyword_results = self._normalize_scores(keyword_results, 'keyword_score')
        
        # Merge results
        return self._merge_results(
            vector_results, keyword_results, 
            query.vector_weight, query.keyword_weight
        )
    
    async def _rank_fusion_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform rank fusion search using multiple algorithms"""
        # Execute both searches
        vector_results = await self._vector_only_search(query)
        keyword_results = await self._keyword_only_search(query)
        
        # Apply different rank fusion algorithms
        fused_results = []
        
        # Reciprocal Rank Fusion (RRF)
        rrf_results = self._reciprocal_rank_fusion(vector_results, keyword_results)
        fused_results.extend(rrf_results)
        
        # Borda Count
        borda_results = self._borda_count_fusion(vector_results, keyword_results)
        fused_results.extend(borda_results)
        
        # Combine and deduplicate
        combined = self._combine_and_deduplicate(fused_results)
        
        # Re-rank using additional features
        reranked = self._rerank_results(combined, query)
        
        return reranked
    
    def _normalize_scores(self, results: List[SearchResult], score_field: str) -> List[SearchResult]:
        """Normalize scores to 0-1 range"""
        if not results:
            return results
        
        scores = [getattr(result, score_field, 0.0) or 0.0 for result in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            return results
        
        for result in results:
            score = getattr(result, score_field, 0.0) or 0.0
            normalized = (score - min_score) / (max_score - min_score)
            setattr(result, score_field, normalized)
        
        return results
    
    def _merge_results(
        self,
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult],
        vector_weight: float,
        keyword_weight: float
    ) -> List[SearchResult]:
        """Merge vector and keyword results"""
        # Create dictionaries for easy lookup
        vector_dict = {result.id: result for result in vector_results}
        keyword_dict = {result.id: result for result in keyword_results}
        
        # Get all unique IDs
        all_ids = set(vector_dict.keys()) | set(keyword_dict.keys())
        
        merged_results = []
        
        for result_id in all_ids:
            vector_result = vector_dict.get(result_id)
            keyword_result = keyword_dict.get(result_id)
            
            # Calculate combined score
            combined_score = 0.0
            source = "hybrid"
            
            if vector_result and keyword_result:
                # Both results available
                combined_score = (
                    vector_weight * (vector_result.vector_score or 0.0) +
                    keyword_weight * (keyword_result.keyword_score or 0.0)
                )
                source = "hybrid"
            elif vector_result:
                # Only vector result
                combined_score = vector_weight * (vector_result.vector_score or 0.0)
                source = "vector"
            elif keyword_result:
                # Only keyword result
                combined_score = keyword_weight * (keyword_result.keyword_score or 0.0)
                source = "keyword"
            
            # Create merged result
            merged_result = SearchResult(
                id=result_id,
                content=(vector_result or keyword_result).content,
                score=combined_score,
                vector_score=vector_result.vector_score if vector_result else None,
                keyword_score=keyword_result.keyword_score if keyword_result else None,
                metadata=(vector_result or keyword_result).metadata,
                source=source,
                created_at=(vector_result or keyword_result).created_at,
                access_count=(vector_result or keyword_result).access_count
            )
            
            merged_results.append(merged_result)
        
        # Sort by combined score
        merged_results.sort(key=lambda x: x.score, reverse=True)
        
        return merged_results
    
    def _reciprocal_rank_fusion(
        self,
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult]
    ) -> List[SearchResult]:
        """Apply Reciprocal Rank Fusion algorithm"""
        # Create rank dictionaries
        vector_ranks = {result.id: i + 1 for i, result in enumerate(vector_results)}
        keyword_ranks = {result.id: i + 1 for i, result in enumerate(keyword_results)}
        
        # Get all unique IDs
        all_ids = set(vector_ranks.keys()) | set(keyword_ranks.keys())
        
        # Calculate RRF scores
        rrf_scores = {}
        k = 60  # Fusion parameter
        
        for result_id in all_ids:
            vector_rank = vector_ranks.get(result_id, len(vector_results) + 1)
            keyword_rank = keyword_ranks.get(result_id, len(keyword_results) + 1)
            
            rrf_score = (1 / (k + vector_rank)) + (1 / (k + keyword_rank))
            rrf_scores[result_id] = rrf_score
        
        # Create results
        fused_results = []
        for result_id, score in rrf_scores.items():
            # Find the best result for this ID
            vector_result = next((r for r in vector_results if r.id == result_id), None)
            keyword_result = next((r for r in keyword_results if r.id == result_id), None)
            
            best_result = vector_result or keyword_result
            if best_result:
                fused_result = SearchResult(
                    id=result_id,
                    content=best_result.content,
                    score=score,
                    vector_score=vector_result.vector_score if vector_result else None,
                    keyword_score=keyword_result.keyword_score if keyword_result else None,
                    metadata=best_result.metadata,
                    source="rrf_fusion",
                    created_at=best_result.created_at,
                    access_count=best_result.access_count
                )
                fused_results.append(fused_result)
        
        # Sort by RRF score
        fused_results.sort(key=lambda x: x.score, reverse=True)
        
        return fused_results
    
    def _borda_count_fusion(
        self,
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult]
    ) -> List[SearchResult]:
        """Apply Borda Count fusion algorithm"""
        # Create rank dictionaries
        vector_ranks = {result.id: len(vector_results) - i for i, result in enumerate(vector_results)}
        keyword_ranks = {result.id: len(keyword_results) - i for i, result in enumerate(keyword_results)}
        
        # Get all unique IDs
        all_ids = set(vector_ranks.keys()) | set(keyword_ranks.keys())
        
        # Calculate Borda scores
        borda_scores = {}
        
        for result_id in all_ids:
            vector_score = vector_ranks.get(result_id, 0)
            keyword_score = keyword_ranks.get(result_id, 0)
            
            borda_score = vector_score + keyword_score
            borda_scores[result_id] = borda_score
        
        # Create results
        fused_results = []
        for result_id, score in borda_scores.items():
            vector_result = next((r for r in vector_results if r.id == result_id), None)
            keyword_result = next((r for r in keyword_results if r.id == result_id), None)
            
            best_result = vector_result or keyword_result
            if best_result:
                fused_result = SearchResult(
                    id=result_id,
                    content=best_result.content,
                    score=score,
                    vector_score=vector_result.vector_score if vector_result else None,
                    keyword_score=keyword_result.keyword_score if keyword_result else None,
                    metadata=best_result.metadata,
                    source="borda_fusion",
                    created_at=best_result.created_at,
                    access_count=best_result.access_count
                )
                fused_results.append(fused_result)
        
        # Sort by Borda score
        fused_results.sort(key=lambda x: x.score, reverse=True)
        
        return fused_results
    
    def _combine_and_deduplicate(self, results: List[SearchResult]) -> List[SearchResult]:
        """Combine and deduplicate results from multiple fusion algorithms"""
        seen_ids = set()
        combined = []
        
        for result in results:
            if result.id not in seen_ids:
                seen_ids.add(result.id)
                combined.append(result)
        
        return combined
    
    def _rerank_results(self, results: List[SearchResult], query: SearchQuery) -> List[SearchResult]:
        """Rerank results using additional features"""
        for result in results:
            score = result.score
            
            # Apply time decay if specified
            if query.time_decay and result.created_at:
                age_days = (datetime.now() - result.created_at).days
                time_factor = math.exp(-query.time_decay * age_days)
                score *= time_factor
            
            # Boost recent results if specified
            if query.boost_recent and result.created_at:
                recent_days = 30  # Consider results from last 30 days as recent
                age_days = (datetime.now() - result.created_at).days
                if age_days <= recent_days:
                    recency_boost = 1.0 + (1.0 - age_days / recent_days) * 0.1
                    score *= recency_boost
            
            # Boost frequently accessed results
            if result.access_count > 0:
                access_boost = 1.0 + math.log(1 + result.access_count) * 0.05
                score *= access_boost
            
            result.score = score
        
        # Sort by final score
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results
    
    async def _postprocess_results(self, results: List[SearchResult], query: SearchQuery) -> List[SearchResult]:
        """Apply post-processing to search results"""
        # Filter by minimum score
        if query.min_score > 0:
            results = [r for r in results if r.score >= query.min_score]
        
        # Limit results
        results = results[:query.limit]
        
        # Generate snippets
        for result in results:
            result.snippet = self._generate_snippet(result.content, query.text)
        
        return results
    
    def _generate_snippet(self, content: str, query: str) -> str:
        """Generate a snippet from content based on query"""
        # Simple snippet generation - find first occurrence of query terms
        content_lower = content.lower()
        query_lower = query.lower()
        
        # Find position of first query term
        first_pos = len(content)
        for term in query_lower.split():
            pos = content_lower.find(term)
            if pos != -1 and pos < first_pos:
                first_pos = pos
        
        if first_pos == len(content):
            # No match found, return beginning of content
            return content[:200] + "..." if len(content) > 200 else content
        
        # Extract snippet around the match
        start = max(0, first_pos - 50)
        end = min(len(content), first_pos + 150)
        
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        
        return snippet
    
    def _get_cache_key(self, query: SearchQuery) -> str:
        """Generate cache key for query"""
        import hashlib
        query_str = json.dumps({
            'text': query.text,
            'filters': query.filters,
            'strategy': query.strategy.value,
            'weighting': query.weighting.value,
            'vector_weight': query.vector_weight,
            'keyword_weight': query.keyword_weight
        }, sort_keys=True)
        
        return hashlib.md5(query_str.encode()).hexdigest()
    
    def _cache_results(self, cache_key: str, results: List[SearchResult]):
        """Cache search results with LRU eviction"""
        if len(self.query_cache) >= 100:  # Max 100 cached queries
            # Remove least recently used
            oldest_key = min(self.query_cache.keys(), 
                           key=lambda k: self.query_cache[k]['accessed_at'])
            del self.query_cache[oldest_key]
        
        self.query_cache[cache_key] = {
            'results': results,
            'accessed_at': datetime.now()
        }
    
    def _update_stats(self, results: List[SearchResult], processing_time: float):
        """Update search statistics"""
        self.stats.total_results += len(results)
        self.stats.processing_time += processing_time
        
        vector_count = sum(1 for r in results if r.vector_score is not None)
        keyword_count = sum(1 for r in results if r.keyword_score is not None)
        
        self.stats.vector_results += vector_count
        self.stats.keyword_results += keyword_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search statistics"""
        avg_processing_time = 0
        if self.stats.queries_executed > 0:
            avg_processing_time = self.stats.processing_time / self.stats.queries_executed
        
        return {
            "total_results": self.stats.total_results,
            "vector_results": self.stats.vector_results,
            "keyword_results": self.stats.keyword_results,
            "processing_time": round(self.stats.processing_time, 3),
            "average_processing_time": round(avg_processing_time, 3),
            "cache_hits": self.stats.cache_hits,
            "queries_executed": self.stats.queries_executed,
            "cache_size": len(self.query_cache)
        }
    
    def clear_cache(self):
        """Clear search cache"""
        self.query_cache.clear()
        logger.info("Search cache cleared")