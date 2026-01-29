"""
搜索和查找工具
"""

import logging
from typing import Optional, List

from tools.base import (
    BaseTool,
    ToolResult,
    DEFAULT_GREP_PARAMS
)


logger = logging.getLogger(__name__)


class GrepTool(BaseTool):
    """代码搜索工具"""
    
    name = "grep"
    description = "Search for a pattern in files"
    parameters = DEFAULT_GREP_PARAMS
    
    async def execute(
        self,
        pattern: str,
        path: str = "."
    ) -> ToolResult:
        """搜索模式"""
        # 使用 grep 命令
        command = f"grep -r -n -H --include='*.py' --include='*.js' --include='*.ts' --include='*.md' --include='*.txt' '{pattern}' {path} 2>/dev/null | head -50"
        
        result = await self.environment.execute_command(command)
        
        if result.success and result.stdout:
            lines = result.stdout.strip().split('\n')
            content = f"Found {len(lines)} matches for '{pattern}':\n\n"
            content += result.stdout
            
            return ToolResult(success=True, content=content)
        
        elif result.success:
            return ToolResult(
                success=True,
                content=f"No matches found for '{pattern}' in {path}"
            )
        
        else:
            return ToolResult(
                success=False,
                content="",
                error=result.stderr or "Search failed"
            )


class FindFunctionTool(BaseTool):
    """查找函数工具"""
    
    name = "find_function"
    description = "Find function definitions in code"
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Function name pattern"
            },
            "language": {
                "type": "string",
                "description": "Programming language (python, js, etc.)",
                "default": "py"
            }
        },
        "required": ["pattern"]
    }
    
    async def execute(self, pattern: str, language: str = "py") -> ToolResult:
        """查找函数"""
        ext_map = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "java": "java",
            "cpp": "cpp",
            "c": "c"
        }
        
        ext = ext_map.get(language.lower(), language.lower())
        
        # 搜索函数定义 - 使用变量避免 f-string 中的反斜杠问题
        pattern_part = f"'def {pattern}' -o -name 'function {pattern}' -o -name 'const {pattern}'"
        command = f"grep -r -n -H --include='*.{ext}' {pattern_part} . 2>/dev/null | head -30"
        
        result = await self.environment.execute_command(command)
        
        if result.success and result.stdout:
            content = f"Found function definitions matching '{pattern}':\n\n"
            content += result.stdout
            
            return ToolResult(success=True, content=content)
        
        return ToolResult(
            success=True,
            content=f"No function definitions found for '{pattern}'"
        )


class FindClassTool(BaseTool):
    """查找类工具"""
    
    name = "find_class"
    description = "Find class definitions in code"
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Class name pattern"
            },
            "language": {
                "type": "string",
                "description": "Programming language",
                "default": "py"
            }
        },
        "required": ["pattern"]
    }
    
    async def execute(self, pattern: str, language: str = "py") -> ToolResult:
        """查找类"""
        ext_map = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "java": "java",
            "cpp": "cpp"
        }
        
        ext = ext_map.get(language.lower(), language.lower())
        
        command = f"grep -r -n -H --include='*.{ext}' 'class {pattern}' . 2>/dev/null | head -30"
        
        result = await self.environment.execute_command(command)
        
        if result.success and result.stdout:
            content = f"Found class definitions matching '{pattern}':\n\n"
            content += result.stdout
            
            return ToolResult(success=True, content=content)
        
        return ToolResult(
            success=True,
            content=f"No class definitions found for '{pattern}'"
        )


class SearchImportTool(BaseTool):
    """搜索导入工具"""
    
    name = "search_import"
    description = "Search for import/require statements"
    parameters = {
        "type": "object",
        "properties": {
            "module": {
                "type": "string",
                "description": "Module name to search for"
            }
        },
        "required": ["module"]
    }
    
    async def execute(self, module: str) -> ToolResult:
        """搜索导入"""
        # 搜索各种导入模式
        patterns = [
            f"import {module}",
            f"from {module}",
            f"require('{module}')",
            f'require("{module}")',
            f"import {module} from",
            f"require({module})"
        ]
        
        results = []
        
        for pattern in patterns:
            command = f"grep -r -n -H --include='*.py' --include='*.js' --include='*.ts' '{pattern}' . 2>/dev/null | head -20"
            
            result = await self.environment.execute_command(command)
            
            if result.success and result.stdout:
                results.append(result.stdout)
        
        if results:
            content = f"Found imports of '{module}':\n\n"
            content += "\n".join(results)
            
            return ToolResult(success=True, content=content)
        
        return ToolResult(
            success=True,
            content=f"No imports found for '{module}'"
        )


class FileTreeTool(BaseTool):
    """文件树工具"""
    
    name = "file_tree"
    description = "Show directory structure as a tree"
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path",
                "default": "."
            },
            "depth": {
                "type": "integer",
                "description": "Maximum depth",
                "default": 3
            }
        },
        "required": ["path"]
    }
    
    async def execute(self, path: str = ".", depth: int = 3) -> ToolResult:
        """显示文件树"""
        # 使用 tree 命令或递归 ls
        command = f"find {path} -maxdepth {depth} -not -path '*/.*' | sort | head -100"
        
        result = await self.environment.execute_command(command)
        
        if result.success and result.stdout:
            lines = result.stdout.strip().split('\n')
            
            # 转换为树形结构
            tree_lines = []
            for line in lines:
                if not line:
                    continue
                
                depth_indent = len(line.split('/')) - 1
                indent = "  " * depth_indent
                tree_lines.append(f"{indent}📄 {line.split('/')[-1]}")
            
            content = f"File tree of {path} (depth {depth}):\n\n"
            content += "\n".join(tree_lines)
            
            if len(lines) >= 100:
                content += f"\n... and more (showing first 100 items)"
            
            return ToolResult(success=True, content=content)
        
        return ToolResult(
            success=False,
            content="",
            error=result.stderr or "Failed to get file tree"
        )


def register_search_tools(registry, environment):
    """注册所有搜索工具"""
    
    tools = [
        GrepTool(environment),
        FindFunctionTool(environment),
        FindClassTool(environment),
        SearchImportTool(environment),
        FileTreeTool(environment)
    ]
    
    for tool in tools:
        registry.register(tool, category="search")
