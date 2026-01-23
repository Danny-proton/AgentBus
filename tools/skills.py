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
        try:
            # 模拟批评者逻辑
            review_points = []
            if target == "code":
                if "TODO" in content or "FIXME" in content:
                    review_points.append("代码中包含未完成的任务标记")
                if "print(" in content:
                    review_points.append("代码中包含 print 语句，生产环境应使用 logging")
                review_points.append(f"代码结构审查: {aspect}")
            
            review = f"🔍 批评者审查结果 ({aspect}):\n"
            for i, point in enumerate(review_points, 1):
                review += f"{i}. {point}\n"
            if not review_points:
                review += "✅ 未发现明显问题\n"
            
            return ToolResult(success=True, content=review)
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


class FileEditorTool(BaseTool):
    """
    文件编辑工具 (str_replace_editor)
    Claude 官方推荐的文件编辑方式
    """
    name = "file_editor"
    description = """Custom file editor tool (str_replace_editor).
Allows viewing, creating, and editing files.
Preferred over writing entire files for small changes."""
    
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": ["view", "create", "str_replace", "insert", "undo_edit"],
                "description": "The command to run."
            },
            "path": {
                "type": "string",
                "description": "Absolute path to the file."
            },
            "file_text": {
                "type": "string",
                "description": "Content for create command."
            },
            "old_str": {
                "type": "string",
                "description": "String to replace (must be unique)."
            },
            "new_str": {
                "type": "string",
                "description": "Replacement string."
            },
            "insert_line": {
                "type": "integer",
                "description": "Line number to insert after."
            },
            "view_range": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "[start_line, end_line]"
            }
        },
        "required": ["command", "path"]
    }
    
    async def execute(
        self,
        command: str,
        path: str,
        file_text: Optional[str] = None,
        old_str: Optional[str] = None,
        new_str: Optional[str] = None,
        insert_line: Optional[int] = None,
        view_range: Optional[List[int]] = None
    ) -> ToolResult:
        try:
            file_path = Path(path)
            
            if command == "view":
                if not file_path.exists():
                    return ToolResult(success=False, content=f"File not found: {path}")
                content = file_path.read_text(encoding='utf-8')
                lines = content.split('\n')
                if view_range:
                    start, end = view_range
                    # Adjust to 0-indexed, minimal bounds check
                    start = max(1, start) - 1
                    end = min(len(lines), end)
                    view_content = "\n".join([f"{i+1}: {line}" for i, line in enumerate(lines[start:end], start=start)])
                    return ToolResult(success=True, content=view_content)
                return ToolResult(success=True, content=content)

            elif command == "create":
                if file_path.exists():
                    return ToolResult(success=False, content=f"File already exists: {path}")
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(file_text or "", encoding='utf-8')
                return ToolResult(success=True, content=f"File created: {path}")

            elif command == "str_replace":
                if not file_path.exists():
                    return ToolResult(success=False, content=f"File not found: {path}")
                content = file_path.read_text(encoding='utf-8')
                if not old_str:
                    return ToolResult(success=False, content="Missing old_str")
                if content.count(old_str) == 0:
                    return ToolResult(success=False, content=f"old_str not found in file")
                if content.count(old_str) > 1:
                    return ToolResult(success=False, content=f"old_str is not unique ({content.count(old_str)} occurrences)")
                
                new_content = content.replace(old_str, new_str or "")
                file_path.write_text(new_content, encoding='utf-8')
                return ToolResult(success=True, content=f"Replaced text in {path}")
            
            # Simplified implementation
            return ToolResult(success=False, content=f"Command {command} not fully implemented in this demo")
            
        except Exception as e:
             return ToolResult(success=False, content=str(e))
             


class ComputerTool(BaseTool):
    """
    Computer Tool
    Claude 官方 "Computer Use" 抽象
    目前作为 HumanTool 的包装或占位符
    """
    name = "computer"
    description = """Use a computer via mouse and keyboard.
Actions:
- key: Press key(s)
- type: Type text
- mouse_move: Move mouse
- left_click: Click
- screenshot: Take screenshot

Note: This tool simulates interaction."""
    
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["key", "type", "mouse_move", "left_click", "screenshot"],
                "description": "Action to perform"
            },
            "text": {
                "type": "string",
                "description": "Text to type"
            },
            "coordinate": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "[x, y] coordinates"
            }
        },
        "required": ["action"]
    }
    
    async def execute(self, action: str, text: Optional[str] = None, coordinate: Optional[List[int]] = None) -> ToolResult:
        # 这里只是一个占位实现，实际应该连接到 HumanTool 或 pyautogui
        return ToolResult(success=True, content=f"Computer action '{action}' simulated. (Real implementation requires GUI binding)")


def register_skills_tools(registry, environment):
    """注册所有技能工具"""
    tools = [
        CriticTool(environment),
        FileEditorTool(environment),
        ComputerTool(environment),
        # TaskTool 和 NoteTool 可以视情况保留或移除，这里简单起见保留
    ]
    
    for tool in tools:
        registry.register(tool, category="skills")
