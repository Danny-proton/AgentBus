"""
记忆管理系统
Memory Management System

为AI代理提供长期和短期记忆存储、检索和管理功能
"""

from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import asyncio
import json
import uuid
import hashlib
import re
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager

from ..core.logger import get_logger
from ..core.config import settings

logger = get_logger(__name__)


class MemoryType(Enum):
    """记忆类型枚举"""
    SHORT_TERM = "short_term"        # 短期记忆
    LONG_TERM = "long_term"          # 长期记忆
    EPISODIC = "episodic"            # 情节记忆
    SEMANTIC = "semantic"            # 语义记忆
    PROCEDURAL = "procedural"        # 程序性记忆
    WORKING = "working"              # 工作记忆
    EMOTIONAL = "emotional"          # 情感记忆
    CONTEXTUAL = "contextual"        # 上下文记忆


class MemoryPriority(Enum):
    """记忆优先级枚举"""
    CRITICAL = 5     # 关键记忆
    HIGH = 4         # 高优先级
    MEDIUM = 3       # 中等优先级
    LOW = 2          # 低优先级
    MINIMAL = 1      # 最小优先级


class MemoryStatus(Enum):
    """记忆状态枚举"""
    ACTIVE = "active"           # 活跃
    ARCHIVED = "archived"       # 归档
    EXPIRED = "expired"         # 过期
    CONSOLIDATING = "consolidating"  # 合并中
    FORGOTTEN = "forgotten"     # 遗忘


@dataclass
class MemoryContent:
    """记忆内容"""
    content: str
    content_type: str = "text"  # text, image, audio, video, code, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_text_content(self) -> str:
        """获取文本内容"""
        if self.content_type == "text":
            return self.content
        elif self.content_type == "json":
            try:
                data = json.loads(self.content)
                return json.dumps(data, indent=2)
            except:
                return str(self.content)
        else:
            return str(self.content)


@dataclass
class Memory:
    """记忆对象"""
    id: str
    memory_type: MemoryType
    content: MemoryContent
    user_id: str
    session_id: Optional[str] = None
    context_id: Optional[str] = None
    
    # 记忆属性
    priority: MemoryPriority = MemoryPriority.MEDIUM
    importance_score: float = 0.5  # 0-1之间，重要性评分
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    # 关联信息
    tags: Set[str] = field(default_factory=set)
    related_memories: Set[str] = field(default_factory=set)
    embeddings: Optional[List[float]] = None  # 向量嵌入
    
    # 状态和统计
    status: MemoryStatus = MemoryStatus.ACTIVE
    access_count: int = 0
    
    # 扩展数据
    source: Optional[str] = None  # 记忆来源
    emotions: List[str] = field(default_factory=list)  # 情感标签
    
    def get_age(self) -> timedelta:
        """获取记忆年龄"""
        return datetime.now() - self.created_at
    
    def get_access_frequency(self) -> float:
        """获取访问频率（次/天）"""
        age_days = max(1, self.get_age().total_seconds() / 86400)
        return self.access_count / age_days
    
    def should_consolidate(self) -> bool:
        """判断是否应该合并到长期记忆"""
        if self.memory_type == MemoryType.LONG_TERM:
            return False
        
        # 基于年龄和访问频率判断
        age_hours = self.get_age().total_seconds() / 3600
        frequency = self.get_access_frequency()
        
        # 短期记忆超过24小时或频繁访问
        return age_hours > 24 or frequency > 0.5
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    def update_access(self) -> None:
        """更新访问信息"""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def calculate_decay(self) -> float:
        """计算记忆衰减"""
        # 简单的记忆衰减模型
        age_days = self.get_age().total_seconds() / 86400
        base_decay = 0.1  # 每天衰减10%
        
        # 访问频率减缓衰减
        frequency_factor = min(1.0, self.get_access_frequency() * 0.2)
        
        decay_rate = base_decay * (1 - frequency_factor)
        total_decay = 1 - (decay_rate ** age_days)
        
        return max(0.0, min(1.0, total_decay))
    
    def get_relevance_score(self, query: str, query_embedding: Optional[List[float]] = None) -> float:
        """计算与查询的相关性分数"""
        score = 0.0
        
        # 标签匹配
        query_tags = set(tag.lower() for tag in query.lower().split() if len(tag) > 2)
        if self.tags:
            tag_match = len(query_tags.intersection(self.tags)) / max(1, len(query_tags))
            score += tag_match * 0.3
        
        # 内容匹配
        content_text = self.content.get_text_content().lower()
        query_words = set(word.lower() for word in re.findall(r'\w+', query))
        content_words = set(word.lower() for word in re.findall(r'\w+', content_text))
        
        if query_words and content_words:
            word_match = len(query_words.intersection(content_words)) / max(1, len(query_words))
            score += word_match * 0.4
        
        # 重要性评分
        score += self.importance_score * 0.2
        
        # 访问频率
        score += min(0.1, self.get_access_frequency() * 0.1)
        
        return min(1.0, score)


class MemoryStore(ABC):
    """记忆存储抽象接口"""
    
    @abstractmethod
    async def store_memory(self, memory: Memory) -> bool:
        """存储记忆"""
        pass
    
    @abstractmethod
    async def retrieve_memory(self, memory_id: str) -> Optional[Memory]:
        """检索记忆"""
        pass
    
    @abstractmethod
    async def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Memory]:
        """搜索记忆"""
        pass
    
    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        pass
    
    @abstractmethod
    async def update_memory(self, memory: Memory) -> bool:
        """更新记忆"""
        pass
    
    @abstractmethod
    async def get_memories_by_context(
        self,
        context_id: str,
        memory_type: Optional[MemoryType] = None
    ) -> List[Memory]:
        """按上下文获取记忆"""
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """清理过期记忆"""
        pass


class InMemoryStore(MemoryStore):
    """内存记忆存储（用于开发和测试）"""
    
    def __init__(self):
        self.memories: Dict[str, Memory] = {}
        self.user_memories: Dict[str, Set[str]] = {}  # user_id -> memory_ids
        self.context_memories: Dict[str, Set[str]] = {}  # context_id -> memory_ids
        self.logger = get_logger(self.__class__.__name__)
    
    async def store_memory(self, memory: Memory) -> bool:
        """存储记忆"""
        try:
            self.memories[memory.id] = memory
            
            # 更新索引
            if memory.user_id not in self.user_memories:
                self.user_memories[memory.user_id] = set()
            self.user_memories[memory.user_id].add(memory.id)
            
            if memory.context_id:
                if memory.context_id not in self.context_memories:
                    self.context_memories[memory.context_id] = set()
                self.context_memories[memory.context_id].add(memory.id)
            
            self.logger.debug("Memory stored", 
                            memory_id=memory.id,
                            memory_type=memory.memory_type.value,
                            user_id=memory.user_id)
            return True
            
        except Exception as e:
            self.logger.error("Failed to store memory", 
                            memory_id=memory.id,
                            error=str(e))
            return False
    
    async def retrieve_memory(self, memory_id: str) -> Optional[Memory]:
        """检索记忆"""
        memory = self.memories.get(memory_id)
        if memory:
            memory.update_access()
        return memory
    
    async def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Memory]:
        """搜索记忆"""
        results = []
        
        for memory in self.memories.values():
            # 过滤条件
            if memory_type and memory.memory_type != memory_type:
                continue
            
            if user_id and memory.user_id != user_id:
                continue
            
            if memory.is_expired():
                continue
            
            # 计算相关性
            relevance = memory.get_relevance_score(query)
            if relevance > 0.1:  # 最小相关性阈值
                results.append((memory, relevance))
        
        # 按相关性排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前N个结果
        return [memory for memory, _ in results[:limit]]
    
    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        memory = self.memories.pop(memory_id, None)
        if memory:
            # 清理索引
            self.user_memories[memory.user_id].discard(memory_id)
            if memory.context_id:
                self.context_memories[memory.context_id].discard(memory_id)
            
            self.logger.debug("Memory deleted", memory_id=memory_id)
            return True
        return False
    
    async def update_memory(self, memory: Memory) -> bool:
        """更新记忆"""
        if memory.id in self.memories:
            self.memories[memory.id] = memory
            return True
        return False
    
    async def get_memories_by_context(
        self,
        context_id: str,
        memory_type: Optional[MemoryType] = None
    ) -> List[Memory]:
        """按上下文获取记忆"""
        memory_ids = self.context_memories.get(context_id, set())
        results = []
        
        for memory_id in memory_ids:
            memory = self.memories.get(memory_id)
            if memory and (not memory_type or memory.memory_type == memory_type):
                results.append(memory)
        
        return results
    
    async def cleanup_expired(self) -> int:
        """清理过期记忆"""
        expired_count = 0
        
        expired_ids = [
            memory_id for memory_id, memory in self.memories.items()
            if memory.is_expired()
        ]
        
        for memory_id in expired_ids:
            await self.delete_memory(memory_id)
            expired_count += 1
        
        if expired_count > 0:
            self.logger.info("Cleaned up expired memories", count=expired_count)
        
        return expired_count


class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or InMemoryStore()
        self.logger = get_logger(self.__class__.__name__)
        
        # 记忆处理配置
        self.max_short_term_memories = 100
        self.short_term_expiry_hours = 24
        self.consolidation_threshold = 0.8
        
        # 工作记忆（当前活跃的短期记忆）
        self.working_memory: Dict[str, Memory] = {}
    
    async def create_memory(
        self,
        content: str,
        memory_type: MemoryType,
        user_id: str,
        session_id: Optional[str] = None,
        context_id: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        importance: float = 0.5,
        expires_in_hours: Optional[float] = None,
        **metadata
    ) -> Memory:
        """创建新记忆"""
        memory = Memory(
            id=str(uuid.uuid4()),
            memory_type=memory_type,
            content=MemoryContent(content),
            user_id=user_id,
            session_id=session_id,
            context_id=context_id,
            importance_score=importance,
            tags=tags or set(),
            expires_at=(
                datetime.now() + timedelta(hours=expires_in_hours)
                if expires_in_hours
                else None
            ),
            metadata=metadata
        )
        
        await self.store.store_memory(memory)
        
        # 如果是短期记忆，添加到工作记忆
        if memory_type == MemoryType.SHORT_TERM:
            self.working_memory[memory.id] = memory
        
        self.logger.info("Memory created", 
                        memory_id=memory.id,
                        memory_type=memory_type.value,
                        user_id=user_id)
        
        return memory
    
    async def retrieve_memory(self, memory_id: str) -> Optional[Memory]:
        """检索记忆"""
        return await self.store.retrieve_memory(memory_id)
    
    async def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Memory]:
        """搜索记忆"""
        memories = await self.store.search_memories(
            query=query,
            memory_type=memory_type,
            user_id=user_id,
            limit=limit
        )
        
        # 更新访问统计
        for memory in memories:
            memory.update_access()
        
        return memories
    
    async def add_to_working_memory(self, memory_id: str) -> bool:
        """添加到工作记忆"""
        memory = await self.retrieve_memory(memory_id)
        if not memory:
            return False
        
        self.working_memory[memory_id] = memory
        return True
    
    async def get_working_memory(self, limit: int = 10) -> List[Memory]:
        """获取工作记忆"""
        memories = list(self.working_memory.values())
        
        # 按重要性和访问时间排序
        memories.sort(
            key=lambda m: (m.importance_score, m.last_accessed),
            reverse=True
        )
        
        return memories[:limit]
    
    async def clear_working_memory(self, memory_type: Optional[MemoryType] = None) -> int:
        """清空工作记忆"""
        if memory_type:
            # 清空特定类型的短期记忆
            keys_to_remove = [
                key for key, memory in self.working_memory.items()
                if memory.memory_type == memory_type
            ]
            for key in keys_to_remove:
                del self.working_memory[key]
            return len(keys_to_remove)
        else:
            # 清空所有工作记忆
            count = len(self.working_memory)
            self.working_memory.clear()
            return count
    
    async def consolidate_memories(self, user_id: str) -> int:
        """合并记忆到长期记忆"""
        # 获取需要合并的短期记忆
        short_term_memories = await self.store.search_memories(
            query="",
            memory_type=MemoryType.SHORT_TERM,
            user_id=user_id,
            limit=1000
        )
        
        consolidated_count = 0
        
        for memory in short_term_memories:
            if memory.should_consolidate():
                # 转换为长期记忆
                memory.memory_type = MemoryType.LONG_TERM
                memory.status = MemoryStatus.CONSOLIDATING
                
                # 从工作记忆中移除
                self.working_memory.pop(memory.id, None)
                
                await self.store.update_memory(memory)
                consolidated_count += 1
        
        self.logger.info("Memories consolidated", 
                        user_id=user_id,
                        consolidated_count=consolidated_count)
        
        return consolidated_count
    
    async def link_memories(self, memory_id1: str, memory_id2: str, relationship: str = "related") -> bool:
        """关联记忆"""
        memory1 = await self.retrieve_memory(memory_id1)
        memory2 = await self.retrieve_memory(memory_id2)
        
        if not memory1 or not memory2:
            return False
        
        # 建立双向关联
        memory1.related_memories.add(memory_id2)
        memory2.related_memories.add(memory_id1)
        
        await self.store.update_memory(memory1)
        await self.store.update_memory(memory2)
        
        self.logger.debug("Memories linked", 
                        memory_id1=memory_id1,
                        memory_id2=memory_id2,
                        relationship=relationship)
        
        return True
    
    async def get_related_memories(self, memory_id: str, limit: int = 5) -> List[Memory]:
        """获取相关记忆"""
        memory = await self.retrieve_memory(memory_id)
        if not memory:
            return []
        
        related_memories = []
        for related_id in memory.related_memories:
            related_memory = await self.retrieve_memory(related_id)
            if related_memory:
                related_memories.append(related_memory)
        
        # 按相关性排序
        related_memories.sort(
            key=lambda m: m.importance_score,
            reverse=True
        )
        
        return related_memories[:limit]
    
    async def forget_memory(self, memory_id: str, decay_factor: float = 0.1) -> bool:
        """遗忘记忆"""
        memory = await self.retrieve_memory(memory_id)
        if not memory:
            return False
        
        # 应用记忆衰减
        memory.importance_score = max(0.0, memory.importance_score * (1 - decay_factor))
        
        # 如果重要性过低，标记为遗忘
        if memory.importance_score < 0.1:
            memory.status = MemoryStatus.FORGOTTEN
            # 从工作记忆中移除
            self.working_memory.pop(memory_id, None)
        
        await self.store.update_memory(memory)
        
        self.logger.debug("Memory decay applied", 
                        memory_id=memory_id,
                        new_importance=memory.importance_score)
        
        return True
    
    async def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """获取记忆统计"""
        # 获取用户的所有记忆
        all_memories = await self.store.search_memories(
            query="",
            user_id=user_id,
            limit=10000
        )
        
        # 按类型统计
        type_counts = {}
        for memory_type in MemoryType:
            count = sum(1 for m in all_memories if m.memory_type == memory_type)
            type_counts[memory_type.value] = count
        
        # 按状态统计
        status_counts = {}
        for status in MemoryStatus:
            count = sum(1 for m in all_memories if m.status == status)
            status_counts[status.value] = count
        
        # 平均重要性
        avg_importance = sum(m.importance_score for m in all_memories) / max(1, len(all_memories))
        
        # 总访问次数
        total_accesses = sum(m.access_count for m in all_memories)
        
        # 工作记忆大小
        working_memory_size = len(self.working_memory)
        
        return {
            "total_memories": len(all_memories),
            "type_counts": type_counts,
            "status_counts": status_counts,
            "average_importance": avg_importance,
            "total_accesses": total_accesses,
            "working_memory_size": working_memory_size,
            "consolidation_needed": sum(1 for m in all_memories if m.should_consolidate())
        }
    
    async def cleanup_expired_memories(self) -> int:
        """清理过期记忆"""
        return await self.store.cleanup_expired()
    
    async def export_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        format: str = "json"
    ) -> str:
        """导出记忆"""
        memories = await self.store.search_memories(
            query="",
            memory_type=memory_type,
            user_id=user_id,
            limit=10000
        )
        
        if format == "json":
            export_data = {
                "user_id": user_id,
                "exported_at": datetime.now().isoformat(),
                "memory_count": len(memories),
                "memories": []
            }
            
            for memory in memories:
                memory_dict = {
                    "id": memory.id,
                    "type": memory.memory_type.value,
                    "content": memory.content.content,
                    "content_type": memory.content.content_type,
                    "priority": memory.priority.value,
                    "importance_score": memory.importance_score,
                    "created_at": memory.created_at.isoformat(),
                    "tags": list(memory.tags),
                    "metadata": memory.metadata
                }
                export_data["memories"].append(memory_dict)
            
            return json.dumps(export_data, indent=2, ensure_ascii=False)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")


# 全局记忆管理器实例
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """获取全局记忆管理器"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


# 便利函数
async def create_conversation_memory(
    user_id: str,
    session_id: str,
    message: str,
    speaker: str = "user",
    context_id: Optional[str] = None
) -> Memory:
    """创建对话记忆"""
    manager = get_memory_manager()
    
    tags = {"conversation", speaker}
    if context_id:
        tags.add(f"context:{context_id}")
    
    content = f"[{speaker}]: {message}"
    
    return await manager.create_memory(
        content=content,
        memory_type=MemoryType.EPISODIC,
        user_id=user_id,
        session_id=session_id,
        context_id=context_id,
        tags=tags,
        importance=0.6,
        expires_in_hours=168,  # 7天
        metadata={
            "speaker": speaker,
            "message_type": "conversation",
            "context_id": context_id
        }
    )


async def create_fact_memory(
    user_id: str,
    fact: str,
    confidence: float = 0.8,
    source: Optional[str] = None
) -> Memory:
    """创建事实记忆"""
    manager = get_memory_manager()
    
    tags = {"fact", "knowledge"}
    if source:
        tags.add(f"source:{source}")
    
    return await manager.create_memory(
        content=fact,
        memory_type=MemoryType.SEMANTIC,
        user_id=user_id,
        tags=tags,
        importance=confidence,
        expires_in_hours=8760,  # 1年
        metadata={
            "confidence": confidence,
            "source": source,
            "fact_type": "knowledge"
        }
    )


async def create_procedure_memory(
    user_id: str,
    procedure: str,
    steps: List[str],
    context: Optional[str] = None
) -> Memory:
    """创建程序性记忆"""
    manager = get_memory_manager()
    
    tags = {"procedure", "how_to"}
    if context:
        tags.add(f"context:{context}")
    
    content = f"Procedure: {procedure}\n\nSteps:\n" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))
    
    return await manager.create_memory(
        content=content,
        memory_type=MemoryType.PROCEDURAL,
        user_id=user_id,
        tags=tags,
        importance=0.7,
        expires_in_hours=8760,  # 1年
        metadata={
            "procedure": procedure,
            "steps": steps,
            "context": context,
            "procedure_type": "instruction"
        }
    )