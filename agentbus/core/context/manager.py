"""
上下文管理器
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from core.memory.short_term import ShortTermMemory


logger = logging.getLogger(__name__)


class ContextManager:
    """
    上下文管理器
    管理代码库上下文和对话上下文
    """
    
    def __init__(
        self,
        memory: ShortTermMemory,
        workspace: Optional[str] = None
    ):
        self.memory = memory
        self.workspace = Path(workspace) if workspace else Path.cwd()
        
        # 代码库索引
        self._codebase_index: Dict[str, Any] = {}
        self._indexed_files: set = set()
    
    async def build_context(
        self,
        message: str,
        max_tokens: int = 80000
    ) -> List[Dict[str, str]]:
        """
        构建上下文
        
        Args:
            message: 用户消息
            max_tokens: 最大 token 数
        
        Returns:
            List[Dict[str, str]]: 上下文消息列表
        """
        # 获取对话历史
        history = await self.memory.get_messages(include_system=False)
        
        # 搜索相关代码
        relevant_files = await self._search_relevant_code(message)
        
        # 构建代码摘要
        code_context = await self._build_code_context(relevant_files)
        
        # 组合上下文
        context_messages = []
        
        # 添加代码库摘要
        if code_context:
            context_messages.append({
                "role": "system",
                "content": f"Relevant code context:\n\n{code_context}"
            })
        
        # 添加对话历史
        for msg in history:
            context_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        # 截断以适应 token 限制
        from core.llm.client import LLMClient
        client = LLMClient()
        
        truncated = await client.truncate_messages(
            context_messages,
            max_tokens
        )
        
        return truncated
    
    async def _search_relevant_code(self, query: str) -> List[str]:
        """
        搜索相关代码
        简化版本：基于关键词匹配
        """
        relevant = []
        
        if not self.workspace.exists():
            return relevant
        
        # 搜索文件内容
        query_words = query.lower().split()
        
        for py_file in self.workspace.rglob("*.py"):
            if py_file in self._indexed_files:
                continue
            
            try:
                content = py_file.read_text(errors="ignore")
                content_lower = content.lower()
                
                # 简单关键词匹配
                matches = sum(1 for word in query_words if word in content_lower)
                
                if matches >= 2:  # 至少匹配2个词
                    relevant.append(str(py_file))
                    self._indexed_files.add(py_file)
            
            except Exception as e:
                logger.debug(f"Error reading {py_file}: {e}")
        
        return relevant[:10]  # 最多10个文件
    
    async def _build_code_context(self, files: List[str]) -> str:
        """
        构建代码上下文
        """
        if not files:
            return ""
        
        context_parts = []
        
        for file_path in files:
            try:
                path = Path(file_path)
                
                # 读取文件
                content = path.read_text(errors="ignore")
                
                # 提取文件结构
                file_context = self._extract_file_structure(path.name, content)
                context_parts.append(file_context)
            
            except Exception as e:
                logger.debug(f"Error building context for {file_path}: {e}")
        
        return "\n\n".join(context_parts[:5])  # 最多5个文件的上下文
    
    def _extract_file_structure(self, filename: str, content: str) -> str:
        """
        提取文件结构
        """
        lines = content.split('\n')
        
        # 提取类和方法
        classes = []
        functions = []
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if stripped.startswith('class '):
                class_name = stripped.split('(')[0].replace('class ', '')
                classes.append(f"  - {class_name}")
            
            elif stripped.startswith('def ') and not stripped.startswith('    '):
                func_name = stripped.split('(')[0].replace('def ', '')
                functions.append(f"  - {func_name}")
        
        # 构建摘要
        summary = f"File: {filename}\n"
        
        if classes:
            summary += "Classes:\n" + "\n".join(classes) + "\n"
        
        if functions:
            summary += "Functions:\n" + "\n".join(functions) + "\n"
        
        # 添加前50行内容
        summary += "\nContent (first 50 lines):\n"
        summary += '\n'.join(lines[:50])
        
        return summary
    
    async def index_codebase(self, pattern: str = "**/*.py"):
        """
        索引代码库
        """
        if not self.workspace.exists():
            logger.warning(f"Workspace does not exist: {self.workspace}")
            return
        
        self._codebase_index = {}
        self._indexed_files = set()
        
        indexed_count = 0
        
        for file_path in self.workspace.glob(pattern):
            try:
                # 提取文件结构
                content = file_path.read_text(errors="ignore")
                structure = self._extract_file_structure(file_path.name, content)
                
                self._codebase_index[str(file_path)] = {
                    "structure": structure,
                    "size": len(content),
                    "modified": datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat()
                }
                
                indexed_count += 1
            
            except Exception as e:
                logger.debug(f"Error indexing {file_path}: {e}")
        
        logger.info(f"Indexed {indexed_count} files in codebase")
    
    async def get_file_content(self, file_path: str) -> Optional[str]:
        """
        获取文件内容
        """
        path = Path(file_path)
        
        if not path.exists():
            return None
        
        try:
            return path.read_text(errors="ignore")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
    
    async def get_directory_structure(self, path: str = ".") -> Dict[str, Any]:
        """
        获取目录结构
        """
        target = Path(path)
        
        if not target.exists():
            return {"error": "Path does not exist"}
        
        structure = {
            "path": str(target.absolute()),
            "name": target.name,
            "type": "directory"
        }
        
        if target.is_file():
            structure["type"] = "file"
            structure["size"] = target.stat().st_size
        else:
            structure["children"] = []
            
            try:
                for item in sorted(target.iterdir()):
                    if item.name.startswith('.'):
                        continue  # 跳过隐藏文件
                    
                    child = await self.get_directory_structure(str(item))
                    structure["children"].append(child)
            
            except PermissionError:
                structure["error"] = "Permission denied"
        
        return structure
    
    async def cleanup(self):
        """清理资源"""
        self._codebase_index.clear()
        self._indexed_files.clear()
