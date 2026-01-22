"""
Knowledge Bus 工具
作为所有 Agent 的必备工具，提供长期记忆的"小黑板"功能
"""

import asyncio
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from uuid import uuid4

from tools.base import BaseTool, ToolResult


logger = logging.getLogger(__name__)


class KnowledgeBus:
    """
    知识总线
    简洁的长期记忆"小黑板"，用于存储关键信息
    """
    
    def __init__(self, bus_file_path: str):
        self.bus_file = Path(bus_file_path)
        self._lock = asyncio.Lock()
        self._cache: Dict[str, Dict] = {}
        
        # 初始化
        self._load()
    
    def _load(self):
        """加载知识总线"""
        if self.bus_file.exists():
            try:
                with open(self.bus_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._cache = data.get("entries", {})
            except Exception as e:
                logger.error(f"Failed to load knowledge bus: {e}")
                self._cache = {}
        else:
            self._cache = {}
    
    def _save(self):
        """保存知识总线"""
        try:
            data = {
                "updated_at": datetime.now().isoformat(),
                "entries": self._cache
            }
            with open(self.bus_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save knowledge bus: {e}")
    
    def _generate_id(self, key: str) -> str:
        """生成条目 ID"""
        return hashlib.md5(key.encode()).hexdigest()[:8]
    
    async def put(
        self,
        key: str,
        value: str,
        category: str = "general",
        expires_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        存储信息到知识总线
        
        Args:
            key: 键（用于检索）
            value: 值（可以是路径、信息等）
            category: 类别
            expires_at: 过期时间（ISO 格式）
            metadata: 元数据
        
        Returns:
            str: 条目 ID
        """
        async with self._lock:
            entry_id = self._generate_id(key)
            
            entry = {
                "id": entry_id,
                "key": key,
                "value": value,
                "category": category,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "expires_at": expires_at,
                "metadata": metadata or {},
                "access_count": 0
            }
            
            self._cache[entry_id] = entry
            self._save()
            
            logger.info(f"KnowledgeBus: stored {key} -> {value}")
            
            return entry_id
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        从知识总线获取信息
        
        Args:
            key: 键
        
        Returns:
            Dict: 条目信息，不存在返回 None
        """
        async with self._lock:
            entry_id = self._generate_id(key)
            
            if entry_id in self._cache:
                entry = self._cache[entry_id]
                entry["access_count"] += 1
                entry["updated_at"] = datetime.now().isoformat()
                self._save()
                return entry
            
            return None
    
    async def get_by_id(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """
        通过 ID 获取条目
        
        Args:
            entry_id: 条目 ID
        
        Returns:
            Dict: 条目信息
        """
        async with self._lock:
            return self._cache.get(entry_id)
    
    async def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        按类别获取所有条目
        
        Args:
            category: 类别
        
        Returns:
            List[Dict]: 条目列表
        """
        async with self._lock:
            return [
                entry for entry in self._cache.values()
                if entry.get("category") == category
            ]
    
    async def get_all(self) -> List[Dict[str, Any]]:
        """获取所有条目"""
        async with self._lock:
            return list(self._cache.values())
    
    async def delete(self, key: str) -> bool:
        """
        删除条目
        
        Args:
            key: 键
        
        Returns:
            bool: 是否成功删除
        """
        async with self._lock:
            entry_id = self._generate_id(key)
            
            if entry_id in self._cache:
                del self._cache[entry_id]
                self._save()
                return True
            
            return False
    
    async def delete_by_id(self, entry_id: str) -> bool:
        """
        通过 ID 删除条目
        
        Args:
            entry_id: 条目 ID
        
        Returns:
            bool: 是否成功删除
        """
        async with self._lock:
            if entry_id in self._cache:
                del self._cache[entry_id]
                self._save()
                return True
            
            return False
    
    async def clear(self):
        """清空知识总线"""
        async with self._lock:
            self._cache.clear()
            self._save()
    
    def get_path(self) -> str:
        """获取知识总线文件路径"""
        return str(self.bus_file)


class KnowledgeBusTool(BaseTool):
    """
    Knowledge Bus 工具
    作为所有 Agent 的必备工具
    """
    
    name = "knowledge_bus"
    description = """Store and retrieve long-term memory information (Knowledge Bus).
Use this tool when:
- A subagent or task completes and you want to save context
- You need to share information across agents (IPs, usernames, passwords, etc.)
- You need to remember key information for later retrieval
- You want to reference information by ID for reporting

The Knowledge Bus is a simple "blackboard" for long-term memory.
All stored information is referenced by path-like entries in the bus."""
    
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["put", "get", "get_all", "get_by_category", "delete", "clear"],
                "description": "Operation: put (store), get (retrieve by key), get_all (list all), get_by_category (filter), delete (remove), clear (empty)"
            },
            "key": {
                "type": "string",
                "description": "Key to store/retrieve (for put/get actions)"
            },
            "value": {
                "type": "string",
                "description": "Value to store (for put action)"
            },
            "category": {
                "type": "string",
                "description": "Category for organization (default: general)",
                "default": "general"
            },
            "entry_id": {
                "type": "string",
                "description": "Entry ID (for get_by_id/delete_by_id actions)"
            },
            "metadata": {
                "type": "object",
                "description": "Additional metadata (for put action)"
            }
        },
        "required": ["action"]
    }
    
    def __init__(self, environment, knowledge_bus: KnowledgeBus):
        super().__init__(environment)
        self.knowledge_bus = knowledge_bus
    
    async def execute(
        self,
        action: str,
        key: Optional[str] = None,
        value: Optional[str] = None,
        category: str = "general",
        entry_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """执行 Knowledge Bus 操作"""
        try:
            if action == "put":
                if not key or not value:
                    return ToolResult(
                        success=False,
                        content="",
                        error="key and value are required for put action"
                    )
                
                entry_id = await self.knowledge_bus.put(
                    key=key,
                    value=value,
                    category=category,
                    metadata=metadata
                )
                
                return ToolResult(
                    success=True,
                    content=f"Stored in Knowledge Bus [ID: {entry_id}]\nKey: {key}\nValue: {value}\nCategory: {category}"
                )
            
            elif action == "get":
                if not key:
                    return ToolResult(
                        success=False,
                        content="",
                        error="key is required for get action"
                    )
                
                entry = await self.knowledge_bus.get(key)
                
                if entry:
                    return ToolResult(
                        success=True,
                        content=f"Found in Knowledge Bus [ID: {entry['id']}]\nKey: {entry['key']}\nValue: {entry['value']}\nCategory: {entry['category']}\nAccess Count: {entry['access_count']}"
                    )
                else:
                    return ToolResult(
                        success=True,
                        content=f"No entry found for key: {key}"
                    )
            
            elif action == "get_by_id":
                if not entry_id:
                    return ToolResult(
                        success=False,
                        content="",
                        error="entry_id is required for get_by_id action"
                    )
                
                entry = await self.knowledge_bus.get_by_id(entry_id)
                
                if entry:
                    return ToolResult(
                        success=True,
                        content=f"Entry [ID: {entry['id']}]\nKey: {entry['key']}\nValue: {entry['value']}\nCategory: {entry['category']}"
                    )
                else:
                    return ToolResult(
                        success=True,
                        content=f"No entry found with ID: {entry_id}"
                    )
            
            elif action == "get_all":
                entries = await self.knowledge_bus.get_all()
                
                if not entries:
                    return ToolResult(
                        success=True,
                        content="Knowledge Bus is empty"
                    )
                
                content = f"Knowledge Bus contains {len(entries)} entries:\n\n"
                for entry in entries:
                    content += f"[{entry['id']}] {entry['key']} = {entry['value']} ({entry['category']})\n"
                
                return ToolResult(success=True, content=content)
            
            elif action == "get_by_category":
                entries = await self.knowledge_bus.get_by_category(category)
                
                if not entries:
                    return ToolResult(
                        success=True,
                        content=f"No entries found in category: {category}"
                    )
                
                content = f"Entries in category '{category}':\n\n"
                for entry in entries:
                    content += f"[{entry['id']}] {entry['key']} = {entry['value']}\n"
                
                return ToolResult(success=True, content=content)
            
            elif action == "delete":
                if not key:
                    return ToolResult(
                        success=False,
                        content="",
                        error="key is required for delete action"
                    )
                
                success = await self.knowledge_bus.delete(key)
                
                if success:
                    return ToolResult(
                        success=True,
                        content=f"Deleted entry with key: {key}"
                    )
                else:
                    return ToolResult(
                        success=True,
                        content=f"No entry found with key: {key}"
                    )
            
            elif action == "clear":
                await self.knowledge_bus.clear()
                
                return ToolResult(
                    success=True,
                    content="Knowledge Bus cleared"
                )
            
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Unknown action: {action}"
                )
        
        except Exception as e:
            logger.exception(f"KnowledgeBusTool error: {e}")
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )


# 全局 Knowledge Bus 实例
_knowledge_bus: Optional[KnowledgeBus] = None


def get_knowledge_bus() -> KnowledgeBus:
    """获取全局 Knowledge Bus 实例"""
    global _knowledge_bus
    if _knowledge_bus is None:
        raise RuntimeError("KnowledgeBus not initialized. Call init_knowledge_bus first.")
    return _knowledge_bus


def init_knowledge_bus(workspace_path: str) -> KnowledgeBus:
    """初始化全局 Knowledge Bus"""
    global _knowledge_bus
    bus_file = Path(workspace_path) / "knowledge_bus.md"
    _knowledge_bus = KnowledgeBus(str(bus_file))
    return _knowledge_bus


def create_knowledge_bus_tool(knowledge_bus: KnowledgeBus) -> KnowledgeBusTool:
    """创建 Knowledge Bus 工具实例"""
    return KnowledgeBusTool(None, knowledge_bus)
