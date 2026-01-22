"""
短期记忆管理
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import deque

from api.schemas.message import Message, MessageType, MessageRole


logger = logging.getLogger(__name__)


class ShortTermMemory:
    """
    短期记忆管理器
    管理当前会话的上下文消息
    """
    
    def __init__(
        self, 
        max_messages: int = 100,
        max_tokens: int = 100000
    ):
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self._messages: deque = deque(maxlen=max_messages)
        self._token_count = 0
    
    @property
    def messages(self) -> List[Message]:
        """获取所有消息"""
        return list(self._messages)
    
    @property
    def message_count(self) -> int:
        """获取消息数量"""
        return len(self._messages)
    
    async def add_message(self, message: Message):
        """添加消息到记忆"""
        self._messages.append(message)
        
        # 更新 token 计数（简化版本，实际应使用 tokenizer）
        self._token_count += self._estimate_tokens(message.content)
        
        logger.debug(f"Added message: type={message.type}, total_messages={self.message_count}")
    
    async def get_messages(
        self, 
        limit: Optional[int] = None,
        include_system: bool = True
    ) -> List[Message]:
        """获取消息"""
        messages = list(self._messages)
        
        if not include_system:
            messages = [m for m in messages if m.type != MessageType.SYSTEM]
        
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    async def clear(self):
        """清空记忆"""
        self._messages.clear()
        self._token_count = 0
        logger.info("Short-term memory cleared")
    
    async def search(
        self, 
        query: str, 
        limit: int = 5
    ) -> List[Message]:
        """搜索相关消息（简化版本）"""
        # 实际实现应使用向量嵌入进行语义搜索
        messages = list(self._messages)
        
        # 简单的关键词匹配
        relevant = []
        query_words = query.lower().split()
        
        for message in reversed(messages):
            if len(relevant) >= limit:
                break
            
            content_lower = message.content.lower()
            if any(word in content_lower for word in query_words):
                relevant.append(message)
        
        return relevant
    
    def _estimate_tokens(self, text: str) -> int:
        """估算 token 数量（简化版本）"""
        # 平均每个 token 约 4 个字符
        return max(1, len(text) // 4)
    
    def needs_compression(self, threshold: float = 0.85) -> bool:
        """检查是否需要压缩"""
        return self._token_count > (self.max_tokens * threshold)
    
    async def compress(
        self, 
        strategy: str = "summary",
        keep_recent: int = 5
    ) -> int:
        """
        压缩记忆
        返回保留的消息数量
        """
        if not self.needs_compression():
            return self.message_count
        
        # 保留最近的消息
        messages = list(self._messages)
        recent_messages = messages[-keep_recent:]
        old_messages = messages[:-keep_recent]
        
        if strategy == "summary":
            # 生成摘要
            summary = await self._generate_summary(old_messages)
            
            # 清空并重建
            await self.clear()
            
            # 添加摘要消息
            summary_message = Message(
                id=f"summary_{datetime.now().timestamp()}",
                content=f"Previous conversation summary:\n{summary}",
                role=MessageRole.SYSTEM,
                type=MessageType.SYSTEM,
                timestamp=datetime.now()
            )
            
            # 添加摘要和最近消息
            self._messages.append(summary_message)
            for msg in recent_messages:
                self._messages.append(msg)
        
        elif strategy == "prune":
            # 直接删除旧消息
            await self.clear()
            for msg in recent_messages:
                self._messages.append(msg)
        
        new_count = len(self._messages)
        logger.info(f"Memory compressed: {self.message_count} -> {new_count} messages")
        
        return new_count
    
    async def _generate_summary(self, messages: List[Message]) -> str:
        """生成对话摘要"""
        if not messages:
            return "No previous conversation."
        
        # 提取关键信息
        user_messages = [
            m.content for m in messages 
            if m.type == MessageType.USER
        ]
        
        assistant_messages = [
            m.content for m in messages 
            if m.type == MessageType.ASSISTANT
        ]
        
        topics = []
        actions = []
        
        for msg in messages:
            if "analysis" in msg.content.lower():
                topics.append("code analysis")
            if "refactor" in msg.content.lower():
                actions.append("refactoring")
            if "fix" in msg.content.lower():
                actions.append("bug fixes")
            if "implement" in msg.content.lower():
                actions.append("implementation")
        
        summary_parts = []
        
        if user_messages:
            summary_parts.append(f"User requests: {len(user_messages)} messages")
        
        if topics:
            summary_parts.append(f"Topics covered: {', '.join(set(topics))}")
        
        if actions:
            summary_parts.append(f"Actions taken: {', '.join(set(actions))}")
        
        if assistant_messages:
            last_assistant = assistant_messages[-1][:200]
            summary_parts.append(f"Last assistant response: {last_assistant}...")
        
        return "\n".join(summary_parts) if summary_parts else "Brief conversation."
