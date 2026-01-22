import asyncio
import os
import subprocess
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from .base import BaseTool, ToolResult

class AbstractShellExecutor(ABC):
    @abstractmethod
    async def execute(self, command: str, cwd: str, timeout: Optional[float] = None) -> ToolResult:
        pass

class LocalShellExecutor(AbstractShellExecutor):
    async def execute(self, command: str, cwd: str, timeout: Optional[float] = None) -> ToolResult:
        try:
            # 如果需要，可以在执行器层面处理 cd 特殊情况，但通常由调用者/会话处理
            # 但是子进程中的 "cd" 不会持久化。所以如果命令以 "cd " 开头，对子进程来说是无效的
            # 调用者应该处理状态更新。
            
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
                return ToolResult(
                    output=stdout.decode().strip(),
                    error=stderr.decode().strip() if stderr else None,
                    metadata={"exit_code": process.returncode}
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(output="", error="命令超时")
                
        except Exception as e:
            return ToolResult(output="", error=str(e))

class BashTool(BaseTool):
    name = "Bash"
    
    def __init__(self, executor: AbstractShellExecutor):
        self.executor = executor

    async def run(self, command: str, cwd: str, timeout: Optional[float] = None) -> ToolResult:
        # 简单的 cd 处理逻辑检查 - 虽然 Session 理想情况下应该处理 "cd" 对状态的影响，
        # 但工具可能会接收到 "cd /path && ls"。
        # 对于这个实现，我们假设 Agent/Session 处理 "cd" 命令来更新其状态，
        # 并将当前有效的 CWD 传递给此工具。
        # 如果命令仅仅是 "cd path"，我们将其解释为目录检查。
        
        return await self.executor.execute(command, cwd, timeout)
