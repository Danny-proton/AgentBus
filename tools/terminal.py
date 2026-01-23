"""
终端命令工具
"""

import asyncio
import logging
from typing import Optional

from tools.base import (
    BaseTool,
    ToolResult,
    DEFAULT_EXECUTE_PARAMS
)
from runtime.abstract import CommandApproval


logger = logging.getLogger(__name__)


class TerminalExecuteTool(BaseTool):
    """终端命令执行工具"""
    
    name = "terminal"
    description = "Execute a shell command and return the output"
    parameters = DEFAULT_EXECUTE_PARAMS
    
    def __init__(self, environment, safe_mode: bool = False):
        super().__init__(environment)
        self.safe_mode = safe_mode
        self._approval_callback = None
        self._dangerous_commands = [
            "rm -rf",
            "format",
            "mkfs",
            "dd",
            "> /dev/",
            "| sh",
            "| bash"
        ]
    
    def set_approval_callback(self, callback):
        """设置批准回调"""
        self._approval_callback = callback
    
    async def execute(
        self,
        command: str,
        timeout: int = 60
    ) -> ToolResult:
        """执行命令"""
        # 安全检查
        if self.safe_mode or self._requires_approval(command):
            approved = await self._request_approval(command)
            
            if not approved:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Command not approved: {command}"
                )
        
        # 执行命令
        result = await self.environment.execute_command(command, timeout)
        
        # 格式化输出
        output = self._format_output(result)
        
        return ToolResult(
            success=result.success,
            content=output,
            error=None if result.success else result.stderr
        )
    
    def _requires_approval(self, command: str) -> bool:
        """检查是否需要批准"""
        command_lower = command.lower()
        
        for dangerous in self._dangerous_commands:
            if dangerous in command_lower:
                return True
        
        return False
    
    async def _request_approval(self, command: str) -> bool:
        """请求用户批准"""
        approval = CommandApproval(command, self.name, "Potentially dangerous command")
        
        if self._approval_callback:
            return await self._approval_callback(approval)
        
        # 如果没有回调，默认拒绝
        return False
    
    def _format_output(self, result) -> str:
        """格式化输出"""
        output = ""
        
        if result.stdout:
            output += f"[STDOUT]\n{result.stdout}"
        
        if result.stderr:
            if output:
                output += "\n"
            output += f"[STDERR]\n{result.stderr}"
        
        if not output:
            output = "(no output)"
        
        output += f"\n[Exit code: {result.exit_code}]"
        
        return output


class TerminalStreamTool(BaseTool):
    """终端命令流式执行工具"""
    
    name = "terminal_stream"
    description = "Execute a shell command with streaming output"
    parameters = DEFAULT_EXECUTE_PARAMS
    
    async def execute(
        self,
        command: str,
        timeout: int = 60
    ) -> ToolResult:
        """流式执行命令"""
        output_lines = []
        
        try:
            async for line in self.environment.execute_command_stream(command):
                output_lines.append(line)
            
            output = "".join(output_lines) if output_lines else "(no output)"
            
            return ToolResult(
                success=True,
                content=output
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )


class PythonExecuteTool(BaseTool):
    """Python 代码执行工具"""
    
    name = "python"
    description = "Execute Python code and return the output"
    parameters = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 30
            }
        },
        "required": ["code"]
    }
    
    async def execute(self, code: str, timeout: int = 30) -> ToolResult:
        """执行 Python 代码"""
        # 构建命令
        wrapped_code = f'''
import sys
import json

try:
    result = []
    exec('''
        '''{code}''' + ''', {{"result": result, "print": lambda x: result.append(str(x))}})
    print("\\n".join(result))
except Exception as e:
    print(f"Error: {{e}}", file=sys.stderr)
    sys.exit(1)
'''
        
        result = await self.environment.execute_command(
            f"python3 -c {wrapped_code!r}",
            timeout=timeout
        )
        
        return ToolResult(
            success=result.success,
            content=result.stdout or result.stderr
        )


class GitTool(BaseTool):
    """Git 操作工具"""
    
    name = "git"
    description = "Execute git commands"
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Git command (e.g., 'status', 'log', 'diff')"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
                "default": 30
            }
        },
        "required": ["command"]
    }
    
    async def execute(self, command: str, timeout: int = 30) -> ToolResult:
        """执行 Git 命令"""
        full_command = f"git {command}"
        
        result = await self.environment.execute_command(
            full_command,
            timeout=timeout
        )
        
        output = result.stdout or result.stderr
        
        if not output.strip():
            output = f"Git command '{command}' executed (exit code: {result.exit_code})"
        
        return ToolResult(
            success=result.success,
            content=output,
            error=None if result.success else result.stderr
        )


async def register_terminal_tools(registry, environment, safe_mode: bool = False):
    """注册所有终端工具"""
    
    terminal_tool = TerminalExecuteTool(environment, safe_mode=safe_mode)
    stream_tool = TerminalStreamTool(environment)
    python_tool = PythonExecuteTool(environment)
    git_tool = GitTool(environment)
    
    await registry.register(terminal_tool, category="terminal")
    await registry.register(stream_tool, category="terminal")
    await registry.register(python_tool, category="terminal")
    await registry.register(git_tool, category="terminal")
