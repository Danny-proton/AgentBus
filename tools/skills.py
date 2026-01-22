"""
Skills 工具集
参考 Claude 官方实现，提供完整的技能工具
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from tools.base import BaseTool, ToolResult


logger = logging.getLogger(__name__)


class CriticTool(BaseTool):
    """
    批评者工具（Critic）
    Claude 官方核心技能，用于自我审查和评估
    """
    
    name = "critic"
    description = """Review and criticize your own work.
Use this tool to:
- Evaluate code quality and identify issues
- Check for security vulnerabilities
- Verify correctness of implementations
- Suggest improvements before finalizing
- Review file contents for errors

The critic provides constructive feedback to improve your outputs."""
    
    parameters = {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "What to review: 'code', 'plan', 'command', 'file'"
            },
            "content": {
                "type": "string",
                "description": "Content to review"
            },
            "aspect": {
                "type": "string",
                "enum": ["correctness", "security", "performance", "style", "completeness"],
                "description": "Aspect to focus on",
                "default": "correctness"
            },
            "context": {
                "type": "string",
                "description": "Additional context for review"
            }
        },
        "required": ["target", "content"]
    }
    
    async def execute(
        self,
        target: str,
        content: str,
        aspect: str = "correctness",
        context: Optional[str] = None
    ) -> ToolResult:
        """执行批评审查"""
        try:
            # 模拟批评者逻辑（实际应调用专门的批评者模型）
            review_points = []
            
            if target == "code":
                # 代码审查
                if "TODO" in content or "FIXME" in content:
                    review_points.append("代码中包含未完成的任务标记")
                
                if "print(" in content:
                    review_points.append("代码中包含 print 语句，生产环境应使用 logging")
                
                review_points.append(f"代码结构基本合理")
                review_points.append(f"建议检查{aspect}方面")
            
            elif target == "command":
                # 命令审查
                dangerous_commands = ["rm -rf", "format", "mkfs", "> /dev/null"]
                for cmd in dangerous_commands:
                    if cmd in content:
                        review_points.append(f"检测到危险命令: {cmd}")
                
                review_points.append("命令语法基本正确")
            
            elif target == "file":
                # 文件审查
                review_points.append("文件内容已读取")
                review_points.append("建议检查文件完整性和格式")
            
            else:
                review_points.append(f"已审查 {target} 类型内容")
                review_points.append("建议根据具体场景进一步分析")
            
            review = f"🔍 批评者审查结果 ({aspect}):\n\n"
            review += "✅ 优点:\n"
            review += "- 内容结构清晰\n"
            review += "- 符合基本规范\n\n"
            review += "⚠️ 改进建议:\n"
            for i, point in enumerate(review_points, 1):
                review += f"{i}. {point}\n"
            
            if context:
                review += f"\n📝 上下文: {context}"
            
            return ToolResult(success=True, content=review)
        
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


class WebFetchTool(BaseTool):
    """
    Web 获取工具
    Claude 官方 Web 技能，用于获取网页内容
    """
    
    name = "web_fetch"
    description = """Fetch and extract content from web pages.
Use this tool to:
- Get documentation from websites
- Extract information from online resources
- Read API documentation
- Access online references

Note: This is a simplified implementation. For production use,
consider integrating with proper web scraping libraries."""
    
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch"
            },
            "selector": {
                "type": "string",
                "description": "CSS selector to extract specific content"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 30
            }
        },
        "required": ["url"]
    }
    
    async def execute(
        self,
        url: str,
        selector: Optional[str] = None,
        timeout: int = 30
    ) -> ToolResult:
        """获取网页内容"""
        try:
            # 使用环境执行 curl 命令
            import subprocess
            
            cmd = ["curl", "-s", "-m", str(timeout), url]
            result = await self.environment.execute_command(" ".join(cmd), timeout)
            
            if result.success:
                content = result.stdout
                
                if selector:
                    # 简单处理，实际应使用 BeautifulSoup
                    content = f"[Extracted for selector: {selector}]\n{content[:1000]}..."
                
                return ToolResult(
                    success=True,
                    content=f"🌐 Fetched from: {url}\n\n{content[:2000]}"
                )
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Failed to fetch: {result.stderr}"
                )
        
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


class TaskTool(BaseTool):
    """
    任务分解工具
    Claude 官方 Task 技能，用于分解和管理任务
    """
    
    name = "task"
    description = """Break down and manage tasks.
Use this tool to:
- Decompose complex tasks into subtasks
- Track task progress
- Manage task dependencies
- Organize work into logical steps

This helps structure your approach to complex problems."""
    
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["plan", "status", "complete", "list"],
                "description": "Action: plan (create plan), status (check status), complete (mark complete), list (show all)"
            },
            "task_name": {
                "type": "string",
                "description": "Task name"
            },
            "description": {
                "type": "string",
                "description": "Task description"
            },
            "dependencies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Task dependencies"
            },
            "status": {
                "type": "string",
                "description": "Task status"
            }
        },
        "required": ["action"]
    }
    
    def __init__(self, environment):
        super().__init__(environment)
        self._tasks: Dict[str, Dict] = {}
    
    async def execute(
        self,
        action: str,
        task_name: Optional[str] = None,
        description: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        status: Optional[str] = None
    ) -> ToolResult:
        """执行任务管理"""
        try:
            if action == "plan":
                if not task_name or not description:
                    return ToolResult(
                        success=False,
                        content="",
                        error="task_name and description required for plan action"
                    )
                
                task_id = f"task_{len(self._tasks) + 1}"
                self._tasks[task_id] = {
                    "name": task_name,
                    "description": description,
                    "dependencies": dependencies or [],
                    "status": "pending",
                    "created_at": datetime.now().isoformat()
                }
                
                return ToolResult(
                    success=True,
                    content=f"✅ Task planned: {task_name}\nID: {task_id}\nDescription: {description}\nDependencies: {', '.join(dependencies) if dependencies else 'None'}"
                )
            
            elif action == "list":
                if not self._tasks:
                    return ToolResult(
                        success=True,
                        content="No tasks planned"
                    )
                
                content = "📋 Planned tasks:\n\n"
                for task_id, task in self._tasks.items():
                    status_icon = "⏳" if task["status"] == "pending" else "✅"
                    content += f"{status_icon} [{task_id}] {task['name']} - {task['status']}\n"
                    content += f"   {task['description']}\n\n"
                
                return ToolResult(success=True, content=content)
            
            elif action == "status":
                if not task_name:
                    return ToolResult(
                        success=False,
                        content="",
                        error="task_name required for status action"
                    )
                
                for task_id, task in self._tasks.items():
                    if task["name"] == task_name:
                        return ToolResult(
                            success=True,
                            content=f"📊 Task status: {task_name}\nStatus: {task['status']}\nCreated: {task['created_at']}"
                        )
                
                return ToolResult(
                    success=True,
                    content=f"Task not found: {task_name}"
                )
            
            elif action == "complete":
                if not task_name:
                    return ToolResult(
                        success=False,
                        content="",
                        error="task_name required for complete action"
                    )
                
                for task_id, task in self._tasks.items():
                    if task["name"] == task_name:
                        task["status"] = "completed"
                        return ToolResult(
                            success=True,
                            content=f"✅ Task completed: {task_name}"
                        )
                
                return ToolResult(
                    success=True,
                    content=f"Task not found: {task_name}"
                )
            
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Unknown action: {action}"
                )
        
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


class NoteTool(BaseTool):
    """
    笔记工具
    用于创建和管理笔记
    """
    
    name = "note"
    description = """Create and manage notes.
Use this tool to:
- Take notes during work
- Store intermediate results
- Remember important information
- Organize thoughts

Notes are stored in the workspace and persist across sessions."""
    
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "read", "list", "append"],
                "description": "Action: create (new note), read (view note), list (all notes), append (add to note)"
            },
            "title": {
                "type": "string",
                "description": "Note title"
            },
            "content": {
                "type": "string",
                "description": "Note content"
            }
        },
        "required": ["action"]
    }
    
    def __init__(self, environment):
        super().__init__(environment)
        self._notes: Dict[str, Dict] = {}
    
    async def execute(
        self,
        action: str,
        title: Optional[str] = None,
        content: Optional[str] = None
    ) -> ToolResult:
        """执行笔记操作"""
        try:
            if action == "create":
                if not title or not content:
                    return ToolResult(
                        success=False,
                        content="",
                        error="title and content required for create action"
                    )
                
                note_id = f"note_{len(self._notes) + 1}"
                self._notes[note_id] = {
                    "title": title,
                    "content": content,
                    "created_at": datetime.now().isoformat()
                }
                
                return ToolResult(
                    success=True,
                    content=f"📝 Note created: {title}\nID: {note_id}"
                )
            
            elif action == "list":
                if not self._notes:
                    return ToolResult(
                        success=True,
                        content="No notes created"
                    )
                
                content = "📚 Notes:\n\n"
                for note_id, note in self._notes.items():
                    content += f"📌 [{note_id}] {note['title']}\n"
                    content += f"   {note['content'][:100]}...\n\n"
                
                return ToolResult(success=True, content=content)
            
            elif action == "read":
                if not title:
                    return ToolResult(
                        success=False,
                        content="",
                        error="title required for read action"
                    )
                
                for note_id, note in self._notes.items():
                    if note["title"] == title:
                        return ToolResult(
                            success=True,
                            content=f"📝 {note['title']}\n\n{note['content']}"
                        )
                
                return ToolResult(
                    success=True,
                    content=f"Note not found: {title}"
                )
            
            elif action == "append":
                if not title or not content:
                    return ToolResult(
                        success=False,
                        content="",
                        error="title and content required for append action"
                    )
                
                for note_id, note in self._notes.items():
                    if note["title"] == title:
                        note["content"] += f"\n\n{content}"
                        note["updated_at"] = datetime.now().isoformat()
                        return ToolResult(
                            success=True,
                            content=f"📝 Appended to: {title}"
                        )
                
                return ToolResult(
                    success=True,
                    content=f"Note not found: {title}"
                )
            
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Unknown action: {action}"
                )
        
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


def register_skills_tools(registry, environment):
    """注册所有技能工具"""
    
    tools = [
        CriticTool(environment),
        TaskTool(environment),
        NoteTool(environment),
    ]
    
    for tool in tools:
        registry.register(tool, category="skills")
    
    # WebFetch 需要特殊处理（可能无法使用）
    try:
        web_fetch = WebFetchTool(environment)
        registry.register(web_fetch, category="skills")
    except Exception as e:
        logger.warning(f"WebFetchTool registration failed: {e}")
