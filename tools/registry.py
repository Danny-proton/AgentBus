"""
工具注册中心
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from tools.base import BaseTool, ToolResult


logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    工具注册中心
    管理所有可用工具的注册和调用
    """
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._tool_categories: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()
    
    async def register(
        self,
        tool: BaseTool,
        category: Optional[str] = None
    ) -> bool:
        """
        注册工具
        
        Args:
            tool: 工具实例
            category: 工具类别
        
        Returns:
            bool: 是否成功
        """
        async with self._lock:
            if tool.name in self._tools:
                logger.warning(f"Tool already registered: {tool.name}")
                return False
            
            self._tools[tool.name] = tool
            
            if category:
                if category not in self._tool_categories:
                    self._tool_categories[category] = []
                
                self._tool_categories[category].append(tool.name)
            
            logger.info(f"Tool registered: {tool.name} (category: {category})")
            return True
    
    async def unregister(self, tool_name: str) -> bool:
        """
        注销工具
        
        Args:
            tool_name: 工具名称
        
        Returns:
            bool: 是否成功
        """
        async with self._lock:
            if tool_name not in self._tools:
                return False
            
            tool = self._tools.pop(tool_name)
            
            # 从类别中移除
            for category, tools in self._tool_categories.items():
                if tool_name in tools:
                    tools.remove(tool_name)
            
            logger.info(f"Tool unregistered: {tool_name}")
            return True
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(tool_name)
    
    def list_tools(self, category: Optional[str] = None) -> List[str]:
        """列出工具"""
        if category:
            return self._tool_categories.get(category, [])
        return list(self._tools.keys())
    
    def list_all_tools(self) -> List[BaseTool]:
        """列出所有工具"""
        return list(self._tools.values())
    
    def get_enabled_tools(self) -> List[BaseTool]:
        """获取所有启用的工具"""
        return [tool for tool in self._tools.values() if tool.enabled]
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        获取所有启用的工具的 OpenAI Schema
        
        Returns:
            List[Dict]: OpenAI Function Schemas
        """
        schemas = []
        
        for tool in self.get_enabled_tools():
            schema = tool.get_schema()
            
            # 检查参数定义是否完整
            if "function" in schema:
                func = schema["function"]
                
                # 确保有 parameters
                if "parameters" not in func or func["parameters"] is None:
                    func["parameters"] = {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                
                # 确保有 type
                if "type" not in schema:
                    schema["type"] = "function"
            
            schemas.append(schema)
        
        return schemas
    
    async def execute_tool(
        self,
        tool_name: str,
        **kwargs
    ) -> ToolResult:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
        
        Returns:
            ToolResult: 执行结果
        """
        tool = self.get_tool(tool_name)
        
        if not tool:
            return ToolResult(
                success=False,
                content="",
                error=f"Tool not found: {tool_name}"
            )
        
        if not tool.enabled:
            return ToolResult(
                success=False,
                content="",
                error=f"Tool disabled: {tool_name}"
            )
        
        try:
            result = await tool.execute(**kwargs)
            return result
        
        except Exception as e:
            logger.exception(f"Tool execution error: {e}")
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )
    
    async def execute_tool_by_name(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> str:
        """
        执行工具并返回字符串
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
        
        Returns:
            str: 结果字符串
        """
        result = await self.execute_tool(tool_name, **arguments)
        
        if result.success:
            return result.content
        else:
            return f"Error: {result.error}"
    
    async def enable_tool(self, tool_name: str) -> bool:
        """启用工具"""
        tool = self.get_tool(tool_name)
        
        if tool:
            tool.enabled = True
            return True
        
        return False
    
    async def disable_tool(self, tool_name: str) -> bool:
        """禁用工具"""
        tool = self.get_tool(tool_name)
        
        if tool:
            tool.enabled = False
            return True
        
        return False
    
    async def health_check_all(self) -> Dict[str, bool]:
        """所有工具健康检查"""
        results = {}
        
        for tool_name, tool in self._tools.items():
            results[tool_name] = await tool.health_check()
        
        return results
    
    def get_categories(self) -> List[str]:
        """获取所有类别"""
        return list(self._tool_categories.keys())
    
    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """获取类别下的所有工具"""
        tool_names = self._tool_categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    async def clear(self):
        """清空所有工具"""
        self._tools.clear()
        self._tool_categories.clear()
        logger.info("Tool registry cleared")
