"""
上下文压缩器
"""

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from core.memory.short_term import ShortTermMemory
from core.llm.client import LLMClient


logger = logging.getLogger(__name__)


class ContextCompressor:
    """
    上下文压缩器
    压缩对话历史以适应 token 限制
    """
    
    def __init__(self, memory: ShortTermMemory):
        self.memory = memory
        self.llm_client = LLMClient()
    
    async def compress_if_needed(
        self,
        threshold: float = 0.85,
        strategy: str = "summary"
    ) -> bool:
        """
        如果需要则压缩
        
        Args:
            threshold: 压缩阈值 (0.0-1.0)
            strategy: 压缩策略
        
        Returns:
            bool: 是否进行了压缩
        """
        if self.memory.needs_compression(threshold):
            await self.compress(strategy)
            return True
        
        return False
    
    async def compress(self, strategy: str = "summary") -> int:
        """
        执行压缩
        
        Args:
            strategy: 压缩策略 ("summary", "prune", "hybrid")
        
        Returns:
            int: 压缩后的消息数量
        """
        logger.info(f"Compressing context with strategy: {strategy}")
        
        if strategy == "summary":
            return await self._compress_with_summary()
        
        elif strategy == "prune":
            return await self._compress_with_prune()
        
        elif strategy == "hybrid":
            return await self._compress_hybrid()
        
        else:
            logger.warning(f"Unknown strategy: {strategy}, using prune")
            return await self._compress_with_prune()
    
    async def _compress_with_summary(self) -> int:
        """使用摘要压缩"""
        messages = self.memory.messages
        
        if len(messages) <= 5:
            return len(messages)
        
        # 保留最近的消息
        keep_count = 5
        messages_to_summarize = messages[:-keep_count]
        recent_messages = messages[-keep_count:]
        
        # 生成摘要
        summary = await self._generate_summary(messages_to_summarize)
        
        # 创建摘要消息
        from api.schemas.message import Message, MessageRole, MessageType
        summary_message = Message(
            id=f"summary_{datetime.now().timestamp()}",
            content=f"Previous conversation summary:\n\n{summary}",
            role=MessageRole.SYSTEM,
            type=MessageType.SYSTEM,
            timestamp=datetime.now()
        )
        
        # 清空并重建
        await self.memory.clear()
        await self.memory.add_message(summary_message)
        
        for msg in recent_messages:
            await self.memory.add_message(msg)
        
        new_count = len(self.memory.messages)
        logger.info(f"Context compressed with summary: {len(messages)} -> {new_count}")
        
        return new_count
    
    async def _compress_with_prune(self) -> int:
        """直接删除旧消息"""
        messages = self.memory.messages
        
        if len(messages) <= 10:
            return len(messages)
        
        # 保留最近的消息
        keep_count = 10
        recent_messages = messages[-keep_count:]
        
        # 清空并重建
        await self.memory.clear()
        
        for msg in recent_messages:
            await self.memory.add_message(msg)
        
        new_count = len(self.memory.messages)
        logger.info(f"Context pruned: {len(messages)} -> {new_count}")
        
        return new_count
    
    async def _compress_hybrid(self) -> int:
        """混合压缩：摘要 + 选择性保留"""
        messages = self.memory.messages
        
        if len(messages) <= 15:
            return len(messages)
        
        # 分类消息
        user_messages = [
            m for m in messages 
            if m.type.value == "user"
        ]
        assistant_messages = [
            m for m in messages 
            if m.type.value == "assistant"
        ]
        
        # 保留最近的关键消息
        keep_messages = messages[-5:]  # 最近5条
        
        # 摘要中间部分
        middle_messages = messages[5:-5]
        
        if middle_messages:
            summary = await self._generate_summary(middle_messages)
            
            from api.schemas.message import Message, MessageRole, MessageType
            summary_message = Message(
                id=f"summary_{datetime.now().timestamp()}",
                content=f"Middle conversation summary:\n\n{summary}",
                role=MessageRole.SYSTEM,
                type=MessageType.SYSTEM,
                timestamp=datetime.now()
            )
            
            keep_messages.insert(0, summary_message)
        
        # 清空并重建
        await self.memory.clear()
        
        for msg in keep_messages:
            await self.memory.add_message(msg)
        
        new_count = len(self.memory.messages)
        logger.info(f"Context hybrid compressed: {len(messages)} -> {new_count}")
        
        return new_count
    
    async def _generate_summary(self, messages: List) -> str:
        """
        生成对话摘要
        """
        if not messages:
            return "No conversation history."
        
        # 构建摘要提示
        prompt = """Please summarize the following conversation into a concise overview:

"""
        
        for i, msg in enumerate(messages):
            role = msg.type.value if hasattr(msg, 'type') else str(msg.role)
            content = msg.content[:500]  # 限制每条消息长度
            
            prompt += f"[{i+1}] {role.upper()}: {content}\n"
        
        prompt += """

Please provide a summary covering:
1. Main topics discussed
2. Key actions taken
3. Important decisions made
4. Current state of work

Summary:"""
        
        try:
            # 使用 LLM 生成摘要
            response = await self.llm_client.complete(
                messages=[{"role": "user", "content": prompt}],
                model="default",
                stream=False,
                max_tokens=500
            )
            
            return response.content
        
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            
            # 回退到简单摘要
            return self._simple_summary(messages)
    
    def _simple_summary(self, messages: List) -> str:
        """简单摘要（当 LLM 不可用时）"""
        topics = set()
        actions = set()
        
        for msg in messages:
            content_lower = msg.content.lower()
            
            # 检测主题
            if "code" in content_lower or "function" in content_lower:
                topics.add("code development")
            if "analysis" in content_lower or "review" in content_lower:
                topics.add("code analysis")
            if "test" in content_lower or "fix" in content_lower:
                actions.add("testing/fixing")
            if "implement" in content_lower or "add" in content_lower:
                actions.add("implementation")
        
        summary = f"Conversation with {len(messages)} messages.\n"
        
        if topics:
            summary += f"Topics: {', '.join(topics)}\n"
        if actions:
            summary += f"Actions: {', '.join(actions)}\n"
        
        return summary
