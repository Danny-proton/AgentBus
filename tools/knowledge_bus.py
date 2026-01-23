"""
Knowledge Bus 工具
作为所有 Agent 的必备工具，提供长期记忆的"小黑板"功能
使用 Markdown 文件作为存储后端，方便人类阅读和编辑
"""

import asyncio
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from uuid import uuid4
import hashlib

from tools.base import BaseTool, ToolResult


logger = logging.getLogger(__name__)


class KnowledgeBus:
    """
    知识总线
    简洁的长期记忆"小黑板"，用于存储关键信息
    存储格式为 Markdown
    """
    
    def __init__(self, bus_file_path: str):
        self.bus_file = Path(bus_file_path)
        self._lock = asyncio.Lock()
        self._cache: Dict[str, Dict] = {}
        
        # 初始化
        self._load()
    
    def _load(self):
        """加载知识总线 (Markdown 解析)"""
        if self.bus_file.exists():
            try:
                content = self.bus_file.read_text(encoding='utf-8')
                self._parse_markdown(content)
            except Exception as e:
                logger.error(f"Failed to load knowledge bus: {e}")
                self._cache = {}
        else:
            self._cache = {}
            self._save()  # 创建初始文件

    def _parse_markdown(self, content: str):
        """解析 Markdown 内容到缓存"""
        self._cache = {}
        
        # 正则匹配：## [id] key
        # 然后是元数据块，然后是内容，直到下一个 ## 或结束
        pattern = re.compile(
            r'^## \[(?P<id>[a-f0-9]+)\] (?P<key>.+?)\n'  # header
            r'(?P<body>.*?)'                             # body (lazy)
            r'(?=\n## \[|\Z)',                           # lookahead for next entry or EOF
            re.MULTILINE | re.DOTALL
        )
        
        for match in pattern.finditer(content):
            entry_id = match.group("id")
            key = match.group("key").strip()
            body = match.group("body").strip()
            
            # 解析元数据和值
            category = "general"
            updated_at = datetime.now().isoformat()
            value = body
            
            # 尝试提取 metadata 行 (简单做法：查找 **Key**: Value 格式)
            meta_pattern = re.compile(r'^\*\*(.+?)\*\*: (.*)$', re.MULTILINE)
            
            # 分离元数据和实际内容
            lines = body.split('\n')
            content_lines = []
            
            metadata = {}
            for line in lines:
                m = meta_pattern.match(line)
                if m:
                    meta_key = m.group(1).lower()
                    meta_val = m.group(2).strip()
                    if meta_key == "category":
                        category = meta_val
                    elif meta_key == "updated":
                        updated_at = meta_val
                    else:
                        metadata[meta_key] = meta_val
                else:
                    if line.strip(): # 只需要保留非空行，或者全部保留？
                        # 这里简单处理，如果遇到空行且还没开始内容，跳过
                        pass
                    content_lines.append(line)
            
            # 重新组合值，去除开头的元数据行造成的空行
            # 简单策略：找到第一个不匹配 metadata 的行作为内容开始
            real_content = []
            is_content = False
            for line in lines:
                if not is_content:
                    if meta_pattern.match(line) or not line.strip():
                        continue
                    is_content = True
                
                real_content.append(line)
            
            value = "\n".join(real_content).strip()

            self._cache[entry_id] = {
                "id": entry_id,
                "key": key,
                "value": value,
                "category": category,
                "updated_at": updated_at,
                "metadata": metadata
            }

    def _save(self):
        """保存知识总线 (Markdown 生成)"""
        try:
            content = "# Knowledge Bus\n\n"
            content += f"> Last Updated: {datetime.now().isoformat()}\n\n"
            
            # 按类别分组排序
            sorted_entries = sorted(
                self._cache.values(), 
                key=lambda x: (x.get("category", "general"), x.get("updated_at", ""))
            )
            
            current_category = None
            
            for entry in sorted_entries:
                # 写入条目
                content += f"## [{entry['id']}] {entry['key']}\n"
                content += f"**Category**: {entry.get('category', 'general')}\n"
                content += f"**Updated**: {entry.get('updated_at')}\n"
                
                # 写入额外元数据
                if entry.get("metadata"):
                    for k, v in entry["metadata"].items():
                        content += f"**{k.capitalize()}**: {v}\n"
                
                content += "\n"
                content += f"{entry['value']}\n\n"
            
            self.bus_file.write_text(content, encoding='utf-8')
            
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
        """存储信息"""
        async with self._lock:
            # 检查 key 是否已存在，如果存在复用 ID
            entry_id = self._generate_id(key) # 默认 ID 策略
            
            # 查找是否已有同名 key 但 ID 不同（防止冲突，或者更新逻辑）
            # 这里简化逻辑：ID 由 key 哈希决定，所以 key 相同 ID 相同，覆盖更新
            
            entry = {
                "id": entry_id,
                "key": key,
                "value": value,
                "category": category,
                "updated_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            self._cache[entry_id] = entry
            self._save()
            
            return entry_id
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """获取信息"""
        async with self._lock:
            # 需要遍历查找 key
            for entry in self._cache.values():
                if entry["key"] == key:
                    return entry
            return None
    
    async def get_by_id(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """通过 ID 获取"""
        async with self._lock:
            return self._cache.get(entry_id)
    
    async def get_all(self) -> List[Dict[str, Any]]:
        """获取所有"""
        async with self._lock:
            return list(self._cache.values())

    async def get_by_category(self, category: str) -> List[Dict[str, Any]]:
         async with self._lock:
            return [e for e in self._cache.values() if e.get("category") == category]

    async def delete(self, key: str) -> bool:
        async with self._lock:
            target_id = None
            for eid, entry in self._cache.items():
                if entry["key"] == key:
                    target_id = eid
                    break
            
            if target_id:
                del self._cache[target_id]
                self._save()
                return True
            return False

    async def clear(self):
        async with self._lock:
            self._cache = {}
            self._save()

    def get_path(self) -> str:
        return str(self.bus_file)


class KnowledgeBusTool(BaseTool):
    """
    Knowledge Bus 工具
    """
    
    name = "knowledge_bus"
    description = """Store and retrieve long-term memory information (Knowledge Bus).
Entries are stored in a Markdown file for readability.
Use this tool when:
- You want to save context or key findings
- You need to share information across agents
- You need to remember things for later

All stored information is referenced by ID and Key."""
    
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["put", "get", "get_all", "delete"],
                "description": "Operation: put (store), get (retrieve by key), get_all (list keys), delete (remove)"
            },
            "key": {
                "type": "string",
                "description": "Topic or Key for the information"
            },
            "value": {
                "type": "string",
                "description": "Content to store (for put action)"
            },
            "category": {
                "type": "string",
                "description": "Category (default: general)",
                "default": "general"
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
        category: str = "general"
    ) -> ToolResult:
        try:
            if action == "put":
                if not key or not value:
                    return ToolResult(success=False, content="Missing key or value")
                eid = await self.knowledge_bus.put(key, value, category)
                return ToolResult(success=True, content=f"Stored [{eid}] {key}")
            
            elif action == "get":
                if not key:
                    return ToolResult(success=False, content="Missing key")
                entry = await self.knowledge_bus.get(key)
                if entry:
                    return ToolResult(success=True, content=f"[{entry['id']}] {entry['key']}:\n{entry['value']}")
                else:
                    return ToolResult(success=True, content="Not found")
            
            elif action == "get_all":
                entries = await self.knowledge_bus.get_all()
                summary = "\n".join([f"- [{e['id']}] {e['key']} ({e.get('category')})" for e in entries])
                return ToolResult(success=True, content=f"Knowledge Bus Entries:\n{summary}")
            
            elif action == "delete":
                if not key:
                    return ToolResult(success=False, content="Missing key")
                success = await self.knowledge_bus.delete(key)
                return ToolResult(success=True, content="Deleted" if success else "Not found")
            
            else:
                return ToolResult(success=False, content=f"Unknown action: {action}")
                
        except Exception as e:
            return ToolResult(success=False, content=str(e))


# 全局 Knowledge Bus 实例
_knowledge_bus: Optional[KnowledgeBus] = None


def get_knowledge_bus() -> KnowledgeBus:
    """获取全局 Knowledge Bus 实例"""
    global _knowledge_bus
    if _knowledge_bus is None:
        raise RuntimeError("KnowledgeBus not initialized.")
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
