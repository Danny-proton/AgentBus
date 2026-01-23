"""
文件操作工具
"""

import logging
from typing import Optional
from pathlib import Path

from tools.base import (
    BaseTool,
    ToolResult,
    DEFAULT_FILE_READ_PARAMS,
    DEFAULT_FILE_WRITE_PARAMS,
    DEFAULT_FILE_EDIT_PARAMS,
    DEFAULT_GLOB_PARAMS
)


logger = logging.getLogger(__name__)


class FileReadTool(BaseTool):
    """文件读取工具"""
    
    name = "file_read"
    description = "Read the contents of a file"
    parameters = DEFAULT_FILE_READ_PARAMS
    
    async def execute(self, path: str) -> ToolResult:
        """读取文件"""
        content = await self.environment.read_file(path)
        
        if content is None:
            return ToolResult(
                success=False,
                content="",
                error=f"File not found or cannot read: {path}"
            )
        
        return ToolResult(
            success=True,
            content=content
        )


class FileWriteTool(BaseTool):
    """文件写入工具"""
    
    name = "file_write"
    description = "Write content to a file (creates or overwrites)"
    parameters = DEFAULT_FILE_WRITE_PARAMS
    
    async def execute(self, path: str, content: str) -> ToolResult:
        """写入文件"""
        success = await self.environment.write_file(path, content)
        
        if success:
            return ToolResult(
                success=True,
                content=f"File written successfully: {path}"
            )
        else:
            return ToolResult(
                success=False,
                content="",
                error=f"Failed to write file: {path}"
            )


class FileEditTool(BaseTool):
    """文件编辑工具"""
    
    name = "file_edit"
    description = "Edit a file by replacing exact text with new text"
    parameters = DEFAULT_FILE_EDIT_PARAMS
    
    async def execute(
        self,
        path: str,
        old_text: str,
        new_text: str
    ) -> ToolResult:
        """编辑文件"""
        success = await self.environment.edit_file(path, old_text, new_text)
        
        if success:
            return ToolResult(
                success=True,
                content=f"File edited successfully: {path}"
            )
        else:
            return ToolResult(
                success=False,
                content="",
                error=f"Failed to edit file: {path}"
            )


class GlobTool(BaseTool):
    """文件查找工具"""
    
    name = "glob"
    description = "Find files matching a glob pattern"
    parameters = DEFAULT_GLOB_PARAMS
    
    async def execute(self, pattern: str) -> ToolResult:
        """查找文件"""
        files = await self.environment.glob(pattern)
        
        if files:
            content = f"Found {len(files)} files matching '{pattern}':\n\n"
            content += "\n".join(files[:50])  # 限制显示数量
            
            if len(files) > 50:
                content += f"\n... and {len(files) - 50} more"
            
            return ToolResult(success=True, content=content)
        else:
            return ToolResult(
                success=True,
                content=f"No files found matching '{pattern}'"
            )


class ListDirTool(BaseTool):
    """目录列表工具"""
    
    name = "list_dir"
    description = "List contents of a directory"
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path",
                "default": "."
            }
        },
        "required": ["path"]
    }
    
    async def execute(self, path: str = ".") -> ToolResult:
        """列出目录"""
        files = await self.environment.list_dir(path)
        
        if not files:
            return ToolResult(
                success=True,
                content=f"Directory is empty or not found: {path}"
            )
        
        content = f"Contents of {path}:\n\n"
        
        for f in sorted(files, key=lambda x: (not x.is_directory, x.name)):
            prefix = "[DIR]  " if f.is_directory else "[FILE] "
            size_str = f" ({f.size} bytes)" if not f.is_directory else ""
            content += f"{prefix}{f.name}{size_str}\n"
        
        return ToolResult(success=True, content=content)


class FileSearchTool(BaseTool):
    """文件搜索工具"""
    
    name = "file_search"
    description = "Search for files containing a pattern in their content"
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Search path",
                "default": "."
            },
            "pattern": {
                "type": "string",
                "description": "Pattern to search for"
            }
        },
        "required": ["path", "pattern"]
    }
    
    async def execute(self, path: str, pattern: str) -> ToolResult:
        """搜索文件"""
        files = await self.environment.search_files(
            path=path,
            pattern=pattern,
            content_search=True
        )
        
        if files:
            content = f"Found {len(files)} files containing '{pattern}':\n\n"
            content += "\n".join(files[:30])
            
            if len(files) > 30:
                content += f"\n... and {len(files) - 30} more"
            
            return ToolResult(success=True, content=content)
        else:
            return ToolResult(
                success=True,
                content=f"No files found containing '{pattern}' in {path}"
            )


class FileDeleteTool(BaseTool):
    """文件删除工具"""
    
    name = "file_delete"
    description = "Delete a file or directory"
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to delete"
            }
        },
        "required": ["path"]
    }
    
    async def execute(self, path: str) -> ToolResult:
        """删除文件"""
        success = await self.environment.delete_file(path)
        
        if success:
            return ToolResult(
                success=True,
                content=f"Deleted: {path}"
            )
        else:
            return ToolResult(
                success=False,
                content="",
                error=f"Failed to delete: {path}"
            )


class FileInfoTool(BaseTool):
    """文件信息工具"""
    
    name = "file_info"
    description = "Get information about a file or directory"
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File or directory path"
            }
        },
        "required": ["path"]
    }
    
    async def execute(self, path: str) -> ToolResult:
        """获取文件信息"""
        exists = await self.environment.exists(path)
        
        if not exists:
            return ToolResult(
                success=False,
                content="",
                error=f"Path does not exist: {path}"
            )
        
        is_dir = await self.environment.is_directory(path)
        
        content = f"Path: {path}\n"
        content += f"Type: {'Directory' if is_dir else 'File'}\n"
        
        if is_dir:
            files = await self.environment.list_dir(path)
            content += f"Contents: {len(files)} items"
        else:
            content += "File exists"
        
        return ToolResult(success=True, content=content)


async def register_file_tools(registry, environment):
    """注册所有文件工具"""
    
    tools = [
        FileReadTool(environment),
        FileWriteTool(environment),
        FileEditTool(environment),
        GlobTool(environment),
        ListDirTool(environment),
        FileSearchTool(environment),
        FileDeleteTool(environment),
        FileInfoTool(environment)
    ]
    
    for tool in tools:
        await registry.register(tool, category="file_operations")
