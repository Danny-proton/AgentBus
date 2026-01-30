"""
Conversation History Management Module

This module provides comprehensive conversation history tracking including:
- Session-based conversation storage
- Message threading and context
- Conversation analytics and insights
- Historical data retrieval and search
- Conversation export and import
"""

import asyncio
import json
import sqlite3
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple, Generator
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types of messages in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    ERROR = "error"
    NOTIFICATION = "notification"


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class ConversationStatus(Enum):
    """Conversation status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    SUSPENDED = "suspended"


@dataclass
class Message:
    """Individual message structure"""
    id: str
    conversation_id: str
    message_type: MessageType
    content: str
    metadata: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    thread_id: Optional[str] = None
    priority: MessagePriority = MessagePriority.NORMAL
    token_count: Optional[int] = None
    processing_time: Optional[float] = None
    
    def __post_init__(self):
        if isinstance(self.message_type, str):
            self.message_type = MessageType(self.message_type)
        if isinstance(self.priority, int):
            self.priority = MessagePriority(self.priority)
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class Conversation:
    """Conversation session structure"""
    id: str
    user_id: str
    title: Optional[str]
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    last_activity: datetime
    message_count: int = 0
    metadata: Dict[str, Any] = None
    tags: List[str] = None
    context_summary: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = ConversationStatus(self.status)
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        if isinstance(self.last_activity, str):
            self.last_activity = datetime.fromisoformat(self.last_activity)
        self.metadata = self.metadata or {}
        self.tags = self.tags or []


class ConversationHistory:
    """
    Comprehensive conversation history management system
    
    Features:
    - Session-based conversation tracking
    - Message threading and context preservation
    - Full-text search across conversations
    - Conversation analytics and insights
    - Data export and import capabilities
    - Automatic cleanup and archival
    """
    
    def __init__(self, storage_path: str = "data/conversation_history.db"):
        """Initialize conversation history system
        
        Args:
            storage_path: Path to SQLite database file
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        self._active_conversations = {}  # Cache for active conversations
        self._message_cache = deque(maxlen=1000)  # LRU cache for recent messages
        
    def _init_database(self):
        """Initialize the SQLite database with required tables"""
        with sqlite3.connect(self.storage_path) as conn:
            # Conversations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    metadata TEXT,
                    tags TEXT,
                    context_summary TEXT,
                    INDEX idx_user_id (user_id),
                    INDEX idx_status (status),
                    INDEX idx_last_activity (last_activity),
                    INDEX idx_created_at (created_at)
                )
            """)
            
            # Messages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    parent_message_id TEXT,
                    thread_id TEXT,
                    priority INTEGER DEFAULT 2,
                    token_count INTEGER,
                    processing_time REAL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id),
                    INDEX idx_conversation_id (conversation_id),
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_user_id (user_id),
                    INDEX idx_message_type (message_type),
                    INDEX idx_thread_id (thread_id)
                )
            """)
            
            # Full-text search index for messages
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS message_search 
                USING fts5(content, content='messages', content_rowid='rowid')
            """)
            
            # Conversation analytics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    analytics_date TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    user_messages INTEGER DEFAULT 0,
                    assistant_messages INTEGER DEFAULT 0,
                    avg_response_time REAL,
                    total_tokens INTEGER,
                    topics TEXT,
                    sentiment_score REAL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            """)
            
            conn.commit()
            
        logger.info(f"Conversation history database initialized at {self.storage_path}")
    
    async def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Create a new conversation session
        
        Args:
            user_id: User identifier
            title: Optional conversation title
            metadata: Optional conversation metadata
            tags: Optional conversation tags
            
        Returns:
            Conversation ID
        """
        conversation_id = self._generate_conversation_id(user_id)
        now = datetime.now()
        
        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            title=title,
            status=ConversationStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            last_activity=now,
            metadata=metadata or {},
            tags=tags or []
        )
        
        with sqlite3.connect(self.storage_path) as conn:
            conn.execute("""
                INSERT INTO conversations (
                    id, user_id, title, status, created_at, updated_at,
                    last_activity, metadata, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation.id,
                conversation.user_id,
                conversation.title,
                conversation.status.value,
                conversation.created_at.isoformat(),
                conversation.updated_at.isoformat(),
                conversation.last_activity.isoformat(),
                json.dumps(conversation.metadata),
                json.dumps(conversation.tags)
            ))
            conn.commit()
        
        # Cache the conversation
        self._active_conversations[conversation_id] = conversation
        
        logger.info(f"Created conversation {conversation_id} for user {user_id}")
        return conversation_id
    
    async def add_message(
        self,
        conversation_id: str,
        message_type: MessageType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        parent_message_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        token_count: Optional[int] = None,
        processing_time: Optional[float] = None
    ) -> str:
        """
        Add a message to a conversation
        
        Args:
            conversation_id: Conversation identifier
            message_type: Type of message
            content: Message content
            metadata: Optional message metadata
            user_id: User identifier
            parent_message_id: Optional parent message for threading
            thread_id: Optional thread identifier
            priority: Message priority
            token_count: Optional token count
            processing_time: Optional processing time
            
        Returns:
            Message ID
        """
        message_id = self._generate_message_id(conversation_id, content)
        timestamp = datetime.now()
        
        message = Message(
            id=message_id,
            conversation_id=conversation_id,
            message_type=message_type,
            content=content,
            metadata=metadata or {},
            timestamp=timestamp,
            user_id=user_id,
            parent_message_id=parent_message_id,
            thread_id=thread_id,
            priority=priority,
            token_count=token_count,
            processing_time=processing_time
        )
        
        with sqlite3.connect(self.storage_path) as conn:
            # Insert message
            conn.execute("""
                INSERT INTO messages (
                    id, conversation_id, message_type, content, metadata,
                    timestamp, user_id, parent_message_id, thread_id,
                    priority, token_count, processing_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id,
                message.conversation_id,
                message.message_type.value,
                message.content,
                json.dumps(message.metadata),
                message.timestamp.isoformat(),
                message.user_id,
                message.parent_message_id,
                message.thread_id,
                message.priority.value,
                message.token_count,
                message.processing_time
            ))
            
            # Update conversation stats
            conn.execute("""
                UPDATE conversations 
                SET message_count = message_count + 1,
                    last_activity = ?,
                    updated_at = ?
                WHERE id = ?
            """, (timestamp.isoformat(), timestamp.isoformat(), conversation_id))
            
            # Add to full-text search index
            conn.execute("""
                INSERT INTO message_search (rowid, content)
                SELECT rowid, content FROM messages WHERE id = ?
            """, (message_id,))
            
            conn.commit()
        
        # Update cached conversation
        if conversation_id in self._active_conversations:
            conv = self._active_conversations[conversation_id]
            conv.message_count += 1
            conv.last_activity = timestamp
            conv.updated_at = timestamp
        
        # Cache the message
        self._message_cache.append(message)
        
        logger.info(f"Added message {message_id} to conversation {conversation_id}")
        return message_id
    
    async def get_conversation(
        self,
        conversation_id: str,
        include_messages: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Optional[Conversation]:
        """
        Retrieve a conversation with its messages
        
        Args:
            conversation_id: Conversation identifier
            include_messages: Whether to include messages
            limit: Maximum number of messages to retrieve
            offset: Message offset for pagination
            
        Returns:
            Conversation object with messages if requested
        """
        with sqlite3.connect(self.storage_path) as conn:
            # Get conversation
            cursor = conn.execute("""
                SELECT * FROM conversations WHERE id = ?
            """, (conversation_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            conversation = self._row_to_conversation(row)
            
            # Get messages if requested
            if include_messages:
                messages = await self.get_conversation_messages(
                    conversation_id, limit, offset
                )
                return conversation, messages
            
            return conversation
    
    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        message_type: Optional[MessageType] = None
    ) -> List[Message]:
        """
        Get messages for a conversation
        
        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages
            offset: Message offset for pagination
            message_type: Filter by message type
            
        Returns:
            List of messages
        """
        sql_conditions = ["conversation_id = ?"]
        params = [conversation_id]
        
        if message_type:
            sql_conditions.append("message_type = ?")
            params.append(message_type.value)
        
        where_clause = " AND ".join(sql_conditions)
        limit_clause = f" LIMIT {limit}" if limit else ""
        offset_clause = f" OFFSET {offset}" if offset else ""
        
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT * FROM messages 
                WHERE {where_clause}
                ORDER BY timestamp ASC
                {limit_clause} {offset_clause}
            """, params)
            
            return [self._row_to_message(row) for row in cursor.fetchall()]
    
    async def search_conversations(
        self,
        user_id: str,
        query: Optional[str] = None,
        status: Optional[ConversationStatus] = None,
        tags: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Conversation]:
        """
        Search conversations based on criteria
        
        Args:
            user_id: User identifier
            query: Text search in conversation content
            status: Filter by conversation status
            tags: Filter by conversation tags
            date_from: Start date filter
            date_to: End date filter
            limit: Maximum number of results
            
        Returns:
            List of matching conversations
        """
        sql_conditions = ["user_id = ?"]
        params = [user_id]
        
        # Add text search using full-text index
        if query:
            # Search in conversation titles and message content
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT conversation_id FROM message_search 
                    WHERE message_search MATCH ?
                """, (query,))
                
                conversation_ids = [row[0] for row in cursor.fetchall()]
                if conversation_ids:
                    sql_conditions.append(f"id IN ({','.join(['?' for _ in conversation_ids])})")
                    params.extend(conversation_ids)
                else:
                    return []  # No matches found
        
        # Add status filter
        if status:
            sql_conditions.append("status = ?")
            params.append(status.value)
        
        # Add date filters
        if date_from:
            sql_conditions.append("created_at >= ?")
            params.append(date_from.isoformat())
        
        if date_to:
            sql_conditions.append("created_at <= ?")
            params.append(date_to.isoformat())
        
        # Add tags filter
        if tags:
            for tag in tags:
                sql_conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")
        
        where_clause = " AND ".join(sql_conditions)
        
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute(f"""
                SELECT * FROM conversations 
                WHERE {where_clause}
                ORDER BY last_activity DESC
                LIMIT ?
            """, (*params, limit))
            
            return [self._row_to_conversation(row) for row in cursor.fetchall()]
    
    async def search_messages(
        self,
        user_id: str,
        query: str,
        conversation_id: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Tuple[Message, Conversation]]:
        """
        Search messages across conversations
        
        Args:
            user_id: User identifier
            query: Search query
            conversation_id: Optional specific conversation
            message_type: Filter by message type
            date_from: Start date filter
            date_to: End date filter
            limit: Maximum number of results
            
        Returns:
            List of (message, conversation) tuples
        """
        with sqlite3.connect(self.storage_path) as conn:
            if query:
                # Use full-text search
                cursor = conn.execute("""
                    SELECT m.*, c.* FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.user_id = ? AND message_search MATCH ?
                    {conversation_filter}
                    {type_filter}
                    {date_from_filter}
                    {date_to_filter}
                    ORDER BY m.timestamp DESC
                    LIMIT ?
                """.format(
                    conversation_filter=f"AND m.conversation_id = '{conversation_id}'" if conversation_id else "",
                    type_filter=f"AND m.message_type = '{message_type.value}'" if message_type else "",
                    date_from_filter=f"AND m.timestamp >= '{date_from.isoformat()}'" if date_from else "",
                    date_to_filter=f"AND m.timestamp <= '{date_to.isoformat()}'" if date_to else ""
                ), (user_id, query, limit))
            else:
                # Fallback to regular search
                conditions = ["c.user_id = ?"]
                params = [user_id]
                
                if conversation_id:
                    conditions.append("m.conversation_id = ?")
                    params.append(conversation_id)
                
                if message_type:
                    conditions.append("m.message_type = ?")
                    params.append(message_type.value)
                
                if date_from:
                    conditions.append("m.timestamp >= ?")
                    params.append(date_from.isoformat())
                
                if date_to:
                    conditions.append("m.timestamp <= ?")
                    params.append(date_to.isoformat())
                
                where_clause = " AND ".join(conditions)
                
                cursor = conn.execute(f"""
                    SELECT m.*, c.* FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE {where_clause}
                    ORDER BY m.timestamp DESC
                    LIMIT ?
                """, (*params, limit))
            
            results = []
            for row in cursor.fetchall():
                message = self._row_to_message(row[:12])  # First 12 columns are message
                conversation = self._row_to_conversation(row[12:])  # Rest are conversation
                results.append((message, conversation))
            
            return results
    
    async def get_conversation_statistics(
        self,
        user_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get conversation statistics for a user
        
        Args:
            user_id: User identifier
            date_from: Start date for statistics
            date_to: End date for statistics
            
        Returns:
            Dictionary containing conversation statistics
        """
        date_filter = ""
        params = [user_id]
        
        if date_from and date_to:
            date_filter = "AND created_at >= ? AND created_at <= ?"
            params.extend([date_from.isoformat(), date_to.isoformat()])
        elif date_from:
            date_filter = "AND created_at >= ?"
            params.append(date_from.isoformat())
        elif date_to:
            date_filter = "AND created_at <= ?"
            params.append(date_to.isoformat())
        
        with sqlite3.connect(self.storage_path) as conn:
            # Total conversations
            cursor = conn.execute(f"""
                SELECT COUNT(*) FROM conversations 
                WHERE user_id = ? {date_filter}
            """, params)
            total_conversations = cursor.fetchone()[0]
            
            # Total messages
            cursor = conn.execute(f"""
                SELECT COUNT(*) FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.user_id = ? {date_filter}
            """, params)
            total_messages = cursor.fetchone()[0]
            
            # Message types breakdown
            cursor = conn.execute(f"""
                SELECT message_type, COUNT(*) as count 
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.user_id = ? {date_filter}
                GROUP BY message_type
            """, params)
            message_types = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Average conversation length
            cursor = conn.execute(f"""
                SELECT AVG(message_count) FROM conversations 
                WHERE user_id = ? {date_filter}
            """, params)
            avg_conversation_length = cursor.fetchone()[0] or 0
            
            # Most active hours
            cursor = conn.execute(f""
                SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.user_id = ? {date_filter}
                GROUP BY hour
                ORDER BY count DESC
                LIMIT 5
            """, params)
            most_active_hours = [dict(hour=row[0], count=row[1]) for row in cursor.fetchall()]
            
            # Recent activity
            week_ago = datetime.now() - timedelta(days=7)
            cursor = conn.execute(f"""
                SELECT COUNT(*) FROM conversations 
                WHERE user_id = ? AND last_activity >= ?
            """, (user_id, week_ago.isoformat()))
            recent_conversations = cursor.fetchone()[0]
            
            cursor = conn.execute(f"""
                SELECT COUNT(*) FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.user_id = ? AND m.timestamp >= ?
            """, (user_id, week_ago.isoformat()))
            recent_messages = cursor.fetchone()[0]
        
        return {
            "user_id": user_id,
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "message_types": message_types,
            "average_conversation_length": round(avg_conversation_length, 2),
            "most_active_hours": most_active_hours,
            "recent_conversations": recent_conversations,
            "recent_messages": recent_messages,
            "date_range": {
                "from": date_from.isoformat() if date_from else None,
                "to": date_to.isoformat() if date_to else None
            },
            "generated_at": datetime.now().isoformat()
        }
    
    async def export_conversation_data(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        format: str = "json",
        include_metadata: bool = True
    ) -> str:
        """
        Export conversation data
        
        Args:
            user_id: User identifier
            conversation_id: Optional specific conversation
            format: Export format (json, csv, txt)
            include_metadata: Whether to include metadata
            
        Returns:
            Exported data as string
        """
        with sqlite3.connect(self.storage_path) as conn:
            if conversation_id:
                # Export specific conversation
                conversation = await self.get_conversation(conversation_id)
                if not conversation or conversation.user_id != user_id:
                    raise ValueError("Conversation not found or access denied")
                
                messages = await self.get_conversation_messages(conversation_id)
                
                export_data = {
                    "conversation": asdict(conversation) if hasattr(asdict, '__self__') else conversation.__dict__,
                    "messages": [asdict(msg) if hasattr(asdict, '__self__') else msg.__dict__ for msg in messages],
                    "export_info": {
                        "exported_at": datetime.now().isoformat(),
                        "format": format,
                        "include_metadata": include_metadata
                    }
                }
            else:
                # Export all user conversations
                conversations = await self.search_conversations(user_id, limit=1000)
                conversations_data = []
                total_messages = 0
                
                for conv in conversations:
                    messages = await self.get_conversation_messages(conv.id)
                    conversations_data.append({
                        "conversation": asdict(conv) if hasattr(asdict, '__self__') else conv.__dict__,
                        "messages": [asdict(msg) if hasattr(asdict, '__self__') else msg.__dict__ for msg in messages]
                    })
                    total_messages += len(messages)
                
                export_data = {
                    "user_id": user_id,
                    "total_conversations": len(conversations),
                    "total_messages": total_messages,
                    "conversations": conversations_data,
                    "export_info": {
                        "exported_at": datetime.now().isoformat(),
                        "format": format,
                        "include_metadata": include_metadata
                    }
                }
            
            if format == "json":
                return json.dumps(export_data, indent=2, default=str)
            elif format == "csv":
                # Simple CSV export of messages
                lines = ["conversation_id,message_type,content,timestamp"]
                for conv_data in export_data.get("conversations", []):
                    for msg in conv_data["messages"]:
                        content = msg["content"].replace('"', '""')  # Escape quotes
                        lines.append(f'{msg["conversation_id"]},{msg["message_type"]},"{content}",{msg["timestamp"]}')
                return "\n".join(lines)
            elif format == "txt":
                # Plain text export
                lines = []
                for conv_data in export_data.get("conversations", []):
                    conv = conv_data["conversation"]
                    lines.append(f"\n=== Conversation: {conv.get('title', conv['id'])} ===")
                    lines.append(f"Created: {conv['created_at']}")
                    lines.append(f"Messages: {len(conv_data['messages'])}")
                    lines.append("-" * 50)
                    
                    for msg in conv_data["messages"]:
                        lines.append(f"[{msg['timestamp']}] {msg['message_type'].upper()}: {msg['content']}")
                
                return "\n".join(lines)
            else:
                raise ValueError(f"Unsupported export format: {format}")
    
    async def archive_conversation(self, conversation_id: str, user_id: str) -> bool:
        """
        Archive a conversation
        
        Args:
            conversation_id: Conversation identifier
            user_id: User identifier
            
        Returns:
            True if archived successfully
        """
        with sqlite3.connect(self.storage_path) as conn:
            cursor = conn.execute("""
                UPDATE conversations 
                SET status = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
            """, (ConversationStatus.ARCHIVED.value, datetime.now().isoformat(), conversation_id, user_id))
            
            if cursor.rowcount > 0:
                # Remove from active cache
                self._active_conversations.pop(conversation_id, None)
                logger.info(f"Archived conversation {conversation_id}")
                return True
            
            return False
    
    async def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """
        Delete a conversation and all its messages
        
        Args:
            conversation_id: Conversation identifier
            user_id: User identifier
            
        Returns:
            True if deleted successfully
        """
        with sqlite3.connect(self.storage_path) as conn:
            # Check if conversation belongs to user
            cursor = conn.execute("""
                SELECT id FROM conversations WHERE id = ? AND user_id = ?
            """, (conversation_id, user_id))
            
            if not cursor.fetchone():
                return False
            
            # Delete messages (cascade delete via foreign key constraint)
            conn.execute("""
                DELETE FROM messages WHERE conversation_id = ?
            """, (conversation_id,))
            
            # Delete conversation
            conn.execute("""
                DELETE FROM conversations WHERE id = ?
            """, (conversation_id,))
            
            # Remove from search index
            conn.execute("""
                DELETE FROM message_search WHERE content LIKE ?
            """, (f"%{conversation_id}%",))
            
            conn.commit()
            
            # Remove from active cache
            self._active_conversations.pop(conversation_id, None)
            
            logger.info(f"Deleted conversation {conversation_id}")
            return True
    
    def _generate_conversation_id(self, user_id: str) -> str:
        """Generate unique conversation ID"""
        timestamp = str(time.time())
        hash_input = f"{user_id}:{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _generate_message_id(self, conversation_id: str, content: str) -> str:
        """Generate unique message ID"""
        timestamp = str(time.time())
        hash_input = f"{conversation_id}:{content}:{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def _row_to_conversation(self, row) -> Conversation:
        """Convert database row to Conversation object"""
        return Conversation(
            id=row[0],
            user_id=row[1],
            title=row[2],
            status=ConversationStatus(row[3]),
            created_at=datetime.fromisoformat(row[4]),
            updated_at=datetime.fromisoformat(row[5]),
            last_activity=datetime.fromisoformat(row[6]),
            message_count=row[7],
            metadata=json.loads(row[8]) if row[8] else {},
            tags=json.loads(row[9]) if row[9] else [],
            context_summary=row[10]
        )
    
    def _row_to_message(self, row) -> Message:
        """Convert database row to Message object"""
        return Message(
            id=row[0],
            conversation_id=row[1],
            message_type=MessageType(row[2]),
            content=row[3],
            metadata=json.loads(row[4]) if row[4] else {},
            timestamp=datetime.fromisoformat(row[5]),
            user_id=row[6],
            parent_message_id=row[7],
            thread_id=row[8],
            priority=MessagePriority(row[9]) if row[9] else MessagePriority.NORMAL,
            token_count=row[10],
            processing_time=row[11]
        )
    
    async def close(self):
        """Close the conversation history system"""
        self._active_conversations.clear()
        self._message_cache.clear()
        logger.info("Conversation history system closed")
    async def close(self):
        """Close the conversation history system"""
        self._active_conversations.clear()
        self._message_cache.clear()
        logger.info("Conversation history system closed")

