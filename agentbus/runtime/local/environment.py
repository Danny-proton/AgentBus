"""
本地环境实现
"""

import asyncio
import logging
import hashlib
import os
import shutil
from pathlib import Path
from typing import AsyncGenerator, Optional, List

from runtime.abstract import (
    Environment,
    CommandResult,
    FileInfo,
    EnvironmentInfo
)


logger = logging.getLogger(__name__)


class LocalEnvironment(Environment):
    """
    本地环境实现
    在本地文件系统上执行操作
    """
    
    def __init__(self, workspace: str = "/workspace"):
        super().__init__(workspace)
        self._os_info = None
    
    async def initialize(self) -> bool:
        """初始化本地环境"""
        try:
            # 确保工作目录存在
            self.workspace.mkdir(parents=True, exist_ok=True)
            self._initialized = True
            
            logger.info(f"Local environment initialized: {self.workspace}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize local environment: {e}")
            return False
    
    async def get_info(self) -> EnvironmentInfo:
        """获取环境信息"""
        if self._os_info is None:
            self._os_info = await self._get_os_info()
        
        return EnvironmentInfo(
            type="local",
            workspace=str(self.workspace),
            os=self._os_info.get("os"),
            python_version=self._os_info.get("python_version"),
            cpu_count=self._os_info.get("cpu_count"),
            memory=self._os_info.get("memory")
        )
    
    async def _get_os_info(self) -> dict:
        """获取操作系统信息"""
        import platform
        
        info = {
            "os": f"{platform.system()} {platform.release()}",
            "python_version": platform.python_version()
        }
        
        # 获取 CPU 和内存信息
        try:
            import psutil
            info["cpu_count"] = psutil.cpu_count()
            info["memory"] = f"{psutil.virtual_memory().total // (1024**3)}GB"
        except ImportError:
            pass
        
        return info
    
    async def execute_command(
        self,
        command: str,
        timeout: int = 60,
        working_dir: Optional[str] = None
    ) -> CommandResult:
        """执行命令"""
        import subprocess
        
        work_dir = working_dir or str(self.workspace)
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return CommandResult(
                    stdout="",
                    stderr="Command timed out",
                    exit_code=-1,
                    success=False
                )
            
            return CommandResult(
                stdout=stdout.decode("utf-8", errors="ignore"),
                stderr=stderr.decode("utf-8", errors="ignore"),
                exit_code=process.returncode,
                success=process.returncode == 0
            )
        
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return CommandResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                success=False
            )
    
    async def execute_command_stream(
        self,
        command: str,
        working_dir: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """流式执行命令"""
        import subprocess
        
        work_dir = working_dir or str(self.workspace)
        
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=work_dir
        )
        
        while True:
            line = await process.stdout.readline()
            
            if not line and process.returncode is not None:
                break
            
            if line:
                yield line.decode("utf-8", errors="ignore")
    
    async def read_file(self, path: str) -> Optional[str]:
        """读取文件"""
        file_path = self._resolve_path(path)
        
        if not file_path.exists() or not file_path.is_file():
            return None
        
        try:
            return file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.error(f"Failed to read file {path}: {e}")
            return None
    
    async def write_file(self, path: str, content: str) -> bool:
        """写入文件"""
        file_path = self._resolve_path(path)
        
        try:
            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_path.write_text(content, encoding="utf-8")
            return True
        
        except Exception as e:
            logger.error(f"Failed to write file {path}: {e}")
            return False
    
    async def edit_file(
        self,
        path: str,
        old_text: str,
        new_text: str
    ) -> bool:
        """编辑文件"""
        content = await self.read_file(path)
        
        if content is None:
            return False
        
        if old_text not in content:
            logger.warning(f"Text not found in file: {path}")
            return False
        
        new_content = content.replace(old_text, new_text)
        
        return await self.write_file(path, new_content)
    
    async def delete_file(self, path: str) -> bool:
        """删除文件"""
        file_path = self._resolve_path(path)
        
        if not file_path.exists():
            return True
        
        try:
            if file_path.is_dir():
                shutil.rmtree(file_path)
            else:
                file_path.unlink()
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")
            return False
    
    async def list_dir(self, path: str) -> List[FileInfo]:
        """列出目录"""
        dir_path = self._resolve_path(path)
        
        if not dir_path.exists() or not dir_path.is_dir():
            return []
        
        files = []
        
        try:
            for item in dir_path.iterdir():
                if item.name.startswith('.'):
                    continue
                
                stat = item.stat()
                files.append(FileInfo(
                    path=str(item),
                    name=item.name,
                    is_directory=item.is_dir(),
                    size=stat.st_size,
                    modified=str(stat.st_mtime)
                ))
        
        except Exception as e:
            logger.error(f"Failed to list directory {path}: {e}")
        
        return files
    
    async def glob(self, pattern: str) -> List[str]:
        """查找匹配的文件"""
        matches = []
        
        try:
            for match in self.workspace.glob(pattern):
                if not match.name.startswith('.'):
                    matches.append(str(match))
        
        except Exception as e:
            logger.error(f"Glob pattern failed: {pattern}, error: {e}")
        
        return matches
    
    async def exists(self, path: str) -> bool:
        """检查路径是否存在"""
        return self._resolve_path(path).exists()
    
    async def is_directory(self, path: str) -> bool:
        """是否为目录"""
        path_obj = self._resolve_path(path)
        return path_obj.exists() and path_obj.is_dir()
    
    async def mkdir(self, path: str, parents: bool = True) -> bool:
        """创建目录"""
        dir_path = self._resolve_path(path)
        
        try:
            if parents:
                dir_path.mkdir(parents=True, exist_ok=True)
            else:
                dir_path.mkdir(exist_ok=True)
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False
    
    async def copy_file(self, src: str, dst: str) -> bool:
        """复制文件"""
        src_path = self._resolve_path(src)
        dst_path = self._resolve_path(dst)
        
        if not src_path.exists():
            return False
        
        try:
            if src_path.is_dir():
                shutil.copytree(src_path, dst_path)
            else:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to copy {src} to {dst}: {e}")
            return False
    
    async def move_file(self, src: str, dst: str) -> bool:
        """移动文件"""
        src_path = self._resolve_path(src)
        dst_path = self._resolve_path(dst)
        
        if not src_path.exists():
            return False
        
        try:
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            return True
        
        except Exception as e:
            logger.error(f"Failed to move {src} to {dst}: {e}")
            return False
    
    async def search_files(
        self,
        path: str,
        pattern: str,
        content_search: bool = False
    ) -> List[str]:
        """搜索文件"""
        search_path = self._resolve_path(path)
        results = []
        
        try:
            if content_search:
                # 内容搜索
                for file_path in search_path.rglob("*"):
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        try:
                            content = file_path.read_text(errors="ignore")
                            if pattern in content:
                                results.append(str(file_path))
                        except Exception:
                            pass
            else:
                # 文件名搜索
                for file_path in search_path.rglob(f"*{pattern}*"):
                    if not file_path.name.startswith('.'):
                        results.append(str(file_path))
        
        except Exception as e:
            logger.error(f"Search failed in {path}: {e}")
        
        return results
    
    async def get_file_hash(self, path: str) -> Optional[str]:
        """获取文件哈希"""
        file_path = self._resolve_path(path)
        
        if not file_path.is_file():
            return None
        
        try:
            hasher = hashlib.md5()
            
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            
            return hasher.hexdigest()
        
        except Exception as e:
            logger.error(f"Failed to hash file {path}: {e}")
            return None
    
    async def close(self):
        """关闭连接"""
        # 本地环境无需特殊关闭
        logger.info("Local environment closed")
    
    async def health_check(self) -> bool:
        """健康检查"""
        return self.workspace.exists() and self.workspace.is_dir()
    
    def _resolve_path(self, path: str) -> Path:
        """解析路径"""
        if path.startswith("/"):
            return Path(path)
        else:
            return (self.workspace / path).resolve()
