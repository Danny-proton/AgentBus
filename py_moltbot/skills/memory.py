#!/usr/bin/env python3
"""
本地MD长期记忆系统
Local Markdown Long-term Memory System

基于Markdown文件的长期记忆存储系统，支持7*24小时运行
"""

import asyncio
import os
import json
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from ..core.logger import get_logger
from ..core.config import settings

logger = get_logger(__name__)


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    tags: Set[str] = field(default_factory=set)
    importance: int = 1  # 1-10，重要程度
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    source: str = "unknown"  # 来源
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryQuery:
    """记忆查询"""
    keywords: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    date_range: Optional[tuple] = None
    importance_threshold: int = 1
    limit: int = 10
    sort_by: str = "relevance"  # "relevance", "date", "importance", "access_count"


class MarkdownMemoryStore:
    """
    Markdown记忆存储系统
    
    特点：
    - 基于文件系统的持久化存储
    - 支持标签分类
    - 重要程度权重
    - 自动清理机制
    - 搜索和检索
    """
    
    def __init__(self, storage_path: str = None):
        self.storage_path = Path(storage_path or settings.get_storage_paths().get("data", Path.cwd() / "data") / "memory")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 索引文件
        self.index_file = self.storage_path / "memory_index.json"
        self.usage_stats_file = self.storage_path / "usage_stats.json"
        
        # 内存缓存
        self.memory_cache: Dict[str, MemoryEntry] = {}
        self.tag_index: Dict[str, Set[str]] = {}  # tag -> memory_ids
        self.search_cache: Dict[str, List[str]] = {}  # keyword -> memory_ids
        
        # 使用统计
        self.usage_stats = {
            "total_memories": 0,
            "total_accesses": 0,
            "last_cleanup": datetime.now(),
            "cleanup_count": 0
        }
        
        # 自动清理配置
        self.max_memories = 10000  # 最大记忆条目数
        self.auto_cleanup_interval = timedelta(hours=24)  # 24小时清理一次
        self.cleanup_task: Optional[asyncio.Task] = None
        
        logger.info("MarkdownMemoryStore initialized", storage_path=str(self.storage_path))
    
    async def start(self) -> None:
        """启动记忆系统"""
        await self._load_index()
        await self._load_usage_stats()
        await self._start_auto_cleanup()
        logger.info("Memory system started")
    
    async def stop(self) -> None:
        """停止记忆系统"""
        await self._save_index()
        await self._save_usage_stats()
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
        logger.info("Memory system stopped")
    
    async def store_memory(
        self, 
        content: str, 
        tags: Set[str] = None, 
        importance: int = 1,
        source: str = "unknown",
        metadata: Dict[str, Any] = None
    ) -> str:
        """存储记忆"""
        # 生成唯一ID
        memory_id = hashlib.md5(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()
        
        # 创建记忆条目
        memory_entry = MemoryEntry(
            id=memory_id,
            content=content,
            tags=tags or set(),
            importance=max(1, min(10, importance)),
            source=source,
            metadata=metadata or {}
        )
        
        # 保存到文件
        await self._save_memory_to_file(memory_entry)
        
        # 更新索引
        await self._update_index(memory_entry)
        
        # 添加到缓存
        self.memory_cache[memory_id] = memory_entry
        
        # 更新统计
        self.usage_stats["total_memories"] += 1
        
        logger.debug("Memory stored", 
                    memory_id=memory_id, 
                    tags=list(memory_entry.tags), 
                    importance=memory_entry.importance)
        
        return memory_id
    
    async def query_memories(self, query: MemoryQuery) -> List[MemoryEntry]:
        """查询记忆"""
        matched_memories = []
        
        # 基础筛选
        for memory in self.memory_cache.values():
            # 重要程度筛选
            if memory.importance < query.importance_threshold:
                continue
            
            # 标签筛选
            if query.tags and not query.tags.intersection(memory.tags):
                continue
            
            # 日期筛选
            if query.date_range:
                start_date, end_date = query.date_range
                if not (start_date <= memory.created_at <= end_date):
                    continue
            
            # 关键词匹配
            if query.keywords:
                content_lower = memory.content.lower()
                keyword_matches = sum(1 for keyword in query.keywords if keyword.lower() in content_lower)
                if keyword_matches == 0:
                    continue
            
            matched_memories.append(memory)
        
        # 排序
        if query.sort_by == "date":
            matched_memories.sort(key=lambda m: m.created_at, reverse=True)
        elif query.sort_by == "importance":
            matched_memories.sort(key=lambda m: m.importance, reverse=True)
        elif query.sort_by == "access_count":
            matched_memories.sort(key=lambda m: m.access_count, reverse=True)
        else:  # relevance
            matched_memories.sort(key=lambda m: (m.importance, m.access_count, m.created_at), reverse=True)
        
        # 更新访问统计
        for memory in matched_memories[:query.limit]:
            memory.access_count += 1
            memory.last_accessed = datetime.now()
            self.usage_stats["total_accesses"] += 1
        
        logger.debug("Memory query completed", 
                    query=query.__dict__, 
                    results=len(matched_memories[:query.limit]))
        
        return matched_memories[:query.limit]
    
    async def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        """获取特定记忆"""
        memory = self.memory_cache.get(memory_id)
        if memory:
            memory.access_count += 1
            memory.last_accessed = datetime.now()
            self.usage_stats["total_accesses"] += 1
        return memory
    
    async def update_memory(
        self, 
        memory_id: str, 
        content: str = None, 
        tags: Set[str] = None,
        importance: int = None
    ) -> bool:
        """更新记忆"""
        memory = self.memory_cache.get(memory_id)
        if not memory:
            return False
        
        updated = False
        
        if content is not None:
            memory.content = content
            updated = True
        
        if tags is not None:
            memory.tags = tags
            updated = True
        
        if importance is not None:
            memory.importance = max(1, min(10, importance))
            updated = True
        
        if updated:
            memory.updated_at = datetime.now()
            await self._save_memory_to_file(memory)
            await self._update_index(memory)
        
        return updated
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        if memory_id not in self.memory_cache:
            return False
        
        # 从缓存中删除
        memory = self.memory_cache.pop(memory_id)
        
        # 删除文件
        memory_file = self.storage_path / f"{memory_id}.md"
        if memory_file.exists():
            memory_file.unlink()
        
        # 更新索引
        await self._remove_from_index(memory)
        
        # 更新统计
        self.usage_stats["total_memories"] -= 1
        
        logger.debug("Memory deleted", memory_id=memory_id)
        return True
    
    async def get_memories_by_tag(self, tag: str) -> List[MemoryEntry]:
        """根据标签获取记忆"""
        memory_ids = self.tag_index.get(tag, set())
        memories = []
        for memory_id in memory_ids:
            memory = self.memory_cache.get(memory_id)
            if memory:
                memories.append(memory)
        return sorted(memories, key=lambda m: m.importance, reverse=True)
    
    async def get_all_tags(self) -> List[str]:
        """获取所有标签"""
        return list(self.tag_index.keys())
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_memories": len(self.memory_cache),
            "total_accesses": self.usage_stats["total_accesses"],
            "total_tags": len(self.tag_index),
            "storage_path": str(self.storage_path),
            "last_cleanup": self.usage_stats["last_cleanup"].isoformat(),
            "cleanup_count": self.usage_stats["cleanup_count"]
        }
    
    async def _save_memory_to_file(self, memory: MemoryEntry) -> None:
        """保存记忆到Markdown文件"""
        memory_file = self.storage_path / f"{memory.id}.md"
        
        # 创建Markdown内容
        md_content = f"""# 记忆条目 {memory.id}

**创建时间**: {memory.created_at.strftime('%Y-%m-%d %H:%M:%S')}
**更新时间**: {memory.updated_at.strftime('%Y-%m-%d %H:%M:%S')}
**重要程度**: {memory.importance}/10
**访问次数**: {memory.access_count}
**来源**: {memory.source}
**标签**: {', '.join(memory.tags) if memory.tags else '无'}

---

## 内容

{memory.content}

---

## 元数据

```json
{json.dumps(memory.metadata, ensure_ascii=False, indent=2)}
```

---

*此文件由Python记忆系统自动生成和更新*
"""
        
        # 写入文件
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: memory_file.write_text(md_content, encoding='utf-8'))
    
    async def _load_index(self) -> None:
        """加载索引"""
        if not self.index_file.exists():
            return
        
        try:
            async with open(self.index_file, 'r', encoding='utf-8') as f:
                index_data = json.loads(await f.read())
            
            # 加载记忆缓存
            self.memory_cache.clear()
            for memory_id, memory_data in index_data.get("memories", {}).items():
                memory = MemoryEntry(**memory_data)
                memory.created_at = datetime.fromisoformat(memory.created_at)
                memory.updated_at = datetime.fromisoformat(memory.updated_at)
                memory.last_accessed = datetime.fromisoformat(memory.last_accessed)
                memory.tags = set(memory.tags)
                self.memory_cache[memory_id] = memory
            
            # 加载标签索引
            self.tag_index.clear()
            for tag, memory_ids in index_data.get("tag_index", {}).items():
                self.tag_index[tag] = set(memory_ids)
            
            # 加载搜索缓存
            self.search_cache.clear()
            for keyword, memory_ids in index_data.get("search_cache", {}).items():
                self.search_cache[keyword] = memory_ids
            
            logger.info("Memory index loaded", 
                       memories=len(self.memory_cache),
                       tags=len(self.tag_index))
        
        except Exception as e:
            logger.error("Failed to load memory index", error=str(e))
    
    async def _save_index(self) -> None:
        """保存索引"""
        try:
            # 准备索引数据
            index_data = {
                "memories": {},
                "tag_index": {},
                "search_cache": {},
                "last_updated": datetime.now().isoformat()
            }
            
            # 记忆数据
            for memory_id, memory in self.memory_cache.items():
                memory_data = {
                    "id": memory.id,
                    "content": memory.content,
                    "tags": list(memory.tags),
                    "importance": memory.importance,
                    "created_at": memory.created_at.isoformat(),
                    "updated_at": memory.updated_at.isoformat(),
                    "access_count": memory.access_count,
                    "last_accessed": memory.last_accessed.isoformat(),
                    "source": memory.source,
                    "metadata": memory.metadata
                }
                index_data["memories"][memory_id] = memory_data
            
            # 标签索引
            for tag, memory_ids in self.tag_index.items():
                index_data["tag_index"][tag] = list(memory_ids)
            
            # 搜索缓存
            for keyword, memory_ids in self.search_cache.items():
                index_data["search_cache"][keyword] = memory_ids
            
            # 保存文件
            async with open(self.index_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(index_data, ensure_ascii=False, indent=2))
            
            logger.debug("Memory index saved")
        
        except Exception as e:
            logger.error("Failed to save memory index", error=str(e))
    
    async def _load_usage_stats(self) -> None:
        """加载使用统计"""
        if not self.usage_stats_file.exists():
            return
        
        try:
            async with open(self.usage_stats_file, 'r', encoding='utf-8') as f:
                stats_data = json.loads(await f.read())
            
            self.usage_stats.update(stats_data)
            if "last_cleanup" in stats_data:
                self.usage_stats["last_cleanup"] = datetime.fromisoformat(stats_data["last_cleanup"])
            
            logger.debug("Usage stats loaded")
        
        except Exception as e:
            logger.error("Failed to load usage stats", error=str(e))
    
    async def _save_usage_stats(self) -> None:
        """保存使用统计"""
        try:
            stats_data = self.usage_stats.copy()
            stats_data["last_cleanup"] = stats_data["last_cleanup"].isoformat()
            
            async with open(self.usage_stats_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(stats_data, ensure_ascii=False, indent=2))
            
            logger.debug("Usage stats saved")
        
        except Exception as e:
            logger.error("Failed to save usage stats", error=str(e))
    
    async def _update_index(self, memory: MemoryEntry) -> None:
        """更新索引"""
        # 更新标签索引
        for tag in memory.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(memory.id)
        
        # 更新搜索缓存
        keywords = re.findall(r'\b\w+\b', memory.content.lower())
        for keyword in keywords[:10]:  # 只缓存前10个关键词
            if keyword not in self.search_cache:
                self.search_cache[keyword] = []
            if memory.id not in self.search_cache[keyword]:
                self.search_cache[keyword].append(memory.id)
    
    async def _remove_from_index(self, memory: MemoryEntry) -> None:
        """从索引中移除"""
        # 从标签索引中移除
        for tag in memory.tags:
            if tag in self.tag_index:
                self.tag_index[tag].discard(memory.id)
                if not self.tag_index[tag]:
                    del self.tag_index[tag]
        
        # 从搜索缓存中移除
        for keyword in self.search_cache:
            if memory.id in self.search_cache[keyword]:
                self.search_cache[keyword].remove(memory.id)
    
    async def _start_auto_cleanup(self) -> None:
        """启动自动清理"""
        async def cleanup_task():
            while True:
                try:
                    await asyncio.sleep(self.auto_cleanup_interval.total_seconds())
                    await self._perform_cleanup()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Auto cleanup task error", error=str(e))
        
        self.cleanup_task = asyncio.create_task(cleanup_task())
        logger.info("Auto cleanup started", interval=str(self.auto_cleanup_interval))
    
    async def _perform_cleanup(self) -> None:
        """执行清理"""
        logger.info("Starting memory cleanup")
        
        # 清理低重要度、低访问次数的记忆
        low_value_memories = []
        for memory in self.memory_cache.values():
            # 计算价值分数
            value_score = memory.importance + (memory.access_count / 10)
            
            # 如果价值分数很低且创建时间超过7天
            if (value_score < 2 and 
                datetime.now() - memory.created_at > timedelta(days=7)):
                low_value_memories.append(memory.id)
        
        # 删除低价值记忆
        deleted_count = 0
        for memory_id in low_value_memories:
            if await self.delete_memory(memory_id):
                deleted_count += 1
        
        # 限制总记忆数量
        if len(self.memory_cache) > self.max_memories:
            # 按重要度和访问次数排序，删除最低的
            sorted_memories = sorted(
                self.memory_cache.values(),
                key=lambda m: (m.importance, m.access_count, m.created_at)
            )
            
            excess_count = len(self.memory_cache) - self.max_memories
            for memory in sorted_memories[:excess_count]:
                if await self.delete_memory(memory.id):
                    deleted_count += 1
        
        # 更新清理统计
        self.usage_stats["last_cleanup"] = datetime.now()
        self.usage_stats["cleanup_count"] += 1
        
        await self._save_index()
        await self._save_usage_stats()
        
        logger.info("Memory cleanup completed", 
                   deleted_memories=deleted_count,
                   remaining_memories=len(self.memory_cache))


# 全局记忆存储实例
_memory_store: Optional[MarkdownMemoryStore] = None


async def get_memory_store() -> MarkdownMemoryStore:
    """获取全局记忆存储实例"""
    global _memory_store
    if _memory_store is None:
        _memory_store = MarkdownMemoryStore()
        await _memory_store.start()
    return _memory_store


async def start_memory_system() -> MarkdownMemoryStore:
    """启动记忆系统"""
    store = await get_memory_store()
    await store.start()
    return store


async def stop_memory_system() -> None:
    """停止记忆系统"""
    global _memory_store
    if _memory_store:
        await _memory_store.stop()
        _memory_store = None


@asynccontextmanager
async def memory_context():
    """记忆系统上下文管理器"""
    store = await get_memory_store()
    try:
        yield store
    finally:
        # 清理工作由系统定期处理，这里不需要特殊操作
        pass
