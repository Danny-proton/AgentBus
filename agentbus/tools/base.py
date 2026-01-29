"""
工具基类
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    content: str
    error: Optional[str] = None


class BaseTool(ABC):
    """
    工具基类
    所有工具都必须继承此类
    """
    
    name: str = "base_tool"
    description: str = "Base tool"
    parameters: Dict[str, Any] = None
    
    def __init__(self, environment):
        self.environment = environment
        self._enabled = True
    
    @property
    def enabled(self) -> bool:
        """工具是否启用"""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        """设置工具启用状态"""
        self._enabled = value
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工具
        
        Args:
            **kwargs: 工具参数
        
        Returns:
            ToolResult: 执行结果
        """
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """
        获取工具的 OpenAI Function Schema
        
        Returns:
            Dict: OpenAI Function 格式的工具定义
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    
    async def run(
        self,
        **kwargs
    ) -> str:
        """
        运行工具并返回字符串结果
        """
        try:
            result = await self.execute(**kwargs)
            
            if result.success:
                return result.content
            else:
                return f"Error: {result.error or 'Unknown error'}"
        
        except Exception as e:
            logger.exception(f"Tool {self.name} execution error: {e}")
            return f"Error: {str(e)}"
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 简单检查环境是否可用
            if hasattr(self.environment, 'health_check'):
                return await self.environment.health_check()
            return True
        except Exception:
            return False


class ToolCategory:
    """工具类别"""
    
    FILE_OPS = "file_operations"
    TERMINAL = "terminal"
    SEARCH = "search"
    CODE = "code"
    SYSTEM = "system"
    CUSTOM = "custom"


# 默认工具参数定义
DEFAULT_FILE_READ_PARAMS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "File path to read"
        }
    },
    "required": ["path"]
}

DEFAULT_FILE_WRITE_PARAMS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "File path to write"
        },
        "content": {
            "type": "string",
            "description": "Content to write"
        }
    },
    "required": ["path", "content"]
}

DEFAULT_FILE_EDIT_PARAMS = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": "File path to edit"
        },
        "old_text": {
            "type": "string",
            "description": "Text to replace"
        },
        "new_text": {
            "type": "string",
            "description": "New text"
        }
    },
    "required": ["path", "old_text", "new_text"]
}

DEFAULT_EXECUTE_PARAMS = {
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "Command to execute"
        },
        "timeout": {
            "type": "integer",
            "description": "Timeout in seconds",
            "default": 60
        }
    },
    "required": ["command"]
}

DEFAULT_GLOB_PARAMS = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "Glob pattern (e.g., '**/*.py')"
        }
    },
    "required": ["pattern"]
}

DEFAULT_GREP_PARAMS = {
    "type": "object",
    "properties": {
        "pattern": {
            "type": "string",
            "description": "Search pattern"
        },
        "path": {
            "type": "string",
            "description": "Search path",
            "default": "."
        }
    },
    "required": ["pattern"]
}
