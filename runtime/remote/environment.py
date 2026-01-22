"""
远程环境实现（SSH）
"""

import asyncio
import logging
import asyncssh
import hashlib
from pathlib import Path
from typing import AsyncGenerator, Optional, List

from runtime.abstract import (
    Environment,
    CommandResult,
    FileInfo,
    EnvironmentInfo
)


logger = logging.getLogger(__name__)


class RemoteEnvironment(Environment):
    """
    远程环境实现
    通过 SSH 连接远程虚拟机执行操作
    """
    
    def __init__(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        private_key_path: Optional[str] = None,
        workspace: str = "/workspace"
    ):
        super().__init__(workspace)
        
        self.host = host
        self.username = username
        self.password = password
        self.private_key_path = private_key_path
        
        self._connection: Optional[asyncssh.SSHClientConnection] = None
        self._sftp_client: Optional[asyncssh.SFTPClient] = None
        self._os_info: Optional[dict] = None
    
    async def initialize(self) -> bool:
        """初始化 SSH 连接"""
        try:
            # 建立 SSH 连接
            connect_options = {
                "host": self.host,
                "username": self.username,
                "known_hosts": None  # 禁用主机密钥检查（仅用于开发）
            }
            
            if self.password:
                connect_options["password"] = self.password
            elif self.private_key_path:
                connect_options["client_keys"] = [self.private_key_path]
            
            self._connection = await asyncssh.connect(**connect_options)
            
            # 获取 SFTP 客户端
            self._sftp_client = await self._connection.start_sftp_client()
            
            # 确保工作目录存在
            await self._ensure_directory(self.workspace)
            
            self._initialized = True
            logger.info(f"Remote environment initialized: {self.username}@{self.host}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize remote environment: {e}")
            return False
    
    async def _ensure_directory(self, path: str):
        """确保目录存在"""
        try:
            await self._sftp_client.makedirs(path, exist_ok=True)
        except Exception:
            pass  # 目录可能已存在
    
    async def get_info(self) -> EnvironmentInfo:
        """获取远程环境信息"""
        if self._os_info is None:
            self._os_info = await self._get_remote_info()
        
        return EnvironmentInfo(
            type="remote",
            host=self.host,
            workspace=self.workspace,
            os=self._os_info.get("os"),
            python_version=self._os_info.get("python_version"),
            cpu_count=self._os_info.get("cpu_count"),
            memory=self._os_info.get("memory")
        )
    
    async def _get_remote_info(self) -> dict:
        """获取远程系统信息"""
        info = {"os": "Unknown", "python_version": "Unknown"}
        
        try:
            # 获取 OS 信息
            result = await self.execute_command("uname -a")
            if result.success:
                info["os"] = result.stdout.strip()
            
            # 获取 Python 版本
            result = await self.execute_command("python3 --version 2>&1 || python --version 2>&1")
            if result.success:
                info["python_version"] = result.stdout.strip()
            
            # 获取 CPU 信息
            result = await self.execute_command("nproc 2>&1")
            if result.success:
                info["cpu_count"] = int(result.stdout.strip())
        
        except Exception as e:
            logger.debug(f"Failed to get remote info: {e}")
        
        return info
    
    async def execute_command(
        self,
        command: str,
        timeout: int = 60,
        working_dir: Optional[str] = None
    ) -> CommandResult:
        """在远程执行命令"""
        if not self._connection:
            return CommandResult(
                stdout="",
                stderr="Not connected",
                exit_code=-1,
                success=False
            )
        
        try:
            # 构建命令（添加工作目录）
            full_command = command
            if working_dir:
                full_command = f"cd {working_dir} && {command}"
            
            # 执行命令
            result = await asyncio.wait_for(
                self._connection.run(
                    full_command,
                    timeout=timeout,
                    term_type="dumb"
                ),
                timeout=timeout + 5  # 增加额外超时时间
            )
            
            return CommandResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.exit_status,
                success=result.exit_status == 0
            )
        
        except asyncio.TimeoutError:
            return CommandResult(
                stdout="",
                stderr="Command timed out",
                exit_code=-1,
                success=False
            )
        
        except Exception as e:
            logger.error(f"Remote command failed: {e}")
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
        """流式执行远程命令"""
        if not self._connection:
            return
        
        try:
            full_command = command
            if working_dir:
                full_command = f"cd {working_dir} && {command}"
            
            async with self._connection.create_process(
                full_command,
                term_type="dumb"
            ) as process:
                while True:
                    line = await process.stdout.readline()
                    
                    if not line and process.exit_status is not None:
                        break
                    
                    if line:
                        yield line
        
        except Exception as e:
            logger.error(f"Remote stream command failed: {e}")
    
    async def read_file(self, path: str) -> Optional[str]:
        """通过 SFTP 读取文件"""
        if not self._sftp_client:
            return None
        
        try:
            async with self._sftp_client.open(path, 'r') as f:
                return await f.read()
        
        except FileNotFoundError:
            return None
        
        except Exception as e:
            logger.error(f"Failed to read remote file {path}: {e}")
            return None
    
    async def write_file(self, path: str, content: str) -> bool:
        """通过 SFTP 写入文件"""
        if not self._sftp_client:
            return False
        
        try:
            # 确保目录存在
            parent = Path(path).parent
            if str(parent) != ".":
                await self._ensure_directory(str(parent))
            
            async with self._sftp_client.open(path, 'w') as f:
                await f.write(content)
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to write remote file {path}: {e}")
            return False
    
    async def edit_file(
        self,
        path: str,
        old_text: str,
        new_text: str
    ) -> bool:
        """编辑远程文件"""
        content = await self.read_file(path)
        
        if content is None:
            return False
        
        if old_text not in content:
            logger.warning(f"Text not found in remote file: {path}")
            return False
        
        new_content = content.replace(old_text, new_text)
        
        return await self.write_file(path, new_content)
    
    async def delete_file(self, path: str) -> bool:
        """删除远程文件"""
        if not self._sftp_client:
            return False
        
        try:
            stat = await self._sftp_client.stat(path)
            
            if stat.is_dir():
                await self._sftp_client.rmdir(path)
            else:
                await self._sftp_client.remove(path)
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to delete remote file {path}: {e}")
            return False
    
    async def list_dir(self, path: str) -> List[FileInfo]:
        """列出远程目录"""
        if not self._sftp_client:
            return []
        
        files = []
        
        try:
            async for entry in self._sftp_client.scandir(path):
                if entry.filename.startswith('.'):
                    continue
                
                stat = await entry.stat()
                files.append(FileInfo(
                    path=entry.path,
                    name=entry.filename,
                    is_directory=entry.is_dir(),
                    size=stat.size,
                    modified=str(stat.mtime)
                ))
        
        except Exception as e:
            logger.error(f"Failed to list remote directory {path}: {e}")
        
        return files
    
    async def glob(self, pattern: str) -> List[str]:
        """查找远程匹配文件"""
        if not self._sftp_client:
            return []
        
        matches = []
        
        try:
            # 使用 find 命令
            search_dir = self.workspace
            result = await self.execute_command(
                f"find {search_dir} -name '{pattern}' -type f 2>/dev/null"
            )
            
            if result.success:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        matches.append(line)
        
        except Exception as e:
            logger.error(f"Remote glob failed: {e}")
        
        return matches
    
    async def exists(self, path: str) -> bool:
        """检查远程路径是否存在"""
        if not self._sftp_client:
            return False
        
        try:
            await self._sftp_client.stat(path)
            return True
        
        except FileNotFoundError:
            return False
        
        except Exception:
            return False
    
    async def is_directory(self, path: str) -> bool:
        """是否为远程目录"""
        if not self._sftp_client:
            return False
        
        try:
            stat = await self._sftp_client.stat(path)
            return stat.is_dir()
        
        except Exception:
            return False
    
    async def mkdir(self, path: str, parents: bool = True) -> bool:
        """创建远程目录"""
        if not self._sftp_client:
            return False
        
        try:
            if parents:
                await self._sftp_client.makedirs(path, exist_ok=True)
            else:
                await self._sftp_client.mkdir(path)
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to create remote directory {path}: {e}")
            return False
    
    async def copy_file(self, src: str, dst: str) -> bool:
        """复制远程文件"""
        if not self._sftp_client:
            return False
        
        try:
            await self._sftp_client.copy(src, dst)
            return True
        
        except Exception as e:
            logger.error(f"Failed to copy remote file {src} to {dst}: {e}")
            return False
    
    async def move_file(self, src: str, dst: str) -> bool:
        """移动远程文件"""
        if not self._sftp_client:
            return False
        
        try:
            await self._sftp_client.rename(src, dst)
            return True
        
        except Exception as e:
            logger.error(f"Failed to move remote file {src} to {dst}: {e}")
            return False
    
    async def search_files(
        self,
        path: str,
        pattern: str,
        content_search: bool = False
    ) -> List[str]:
        """搜索远程文件"""
        results = []
        
        try:
            if content_search:
                # 内容搜索
                result = await self.execute_command(
                    f"grep -r -l '{pattern}' {path} 2>/dev/null"
                )
                
                if result.success:
                    for line in result.stdout.strip().split('\n'):
                        if line and not line.startswith('.'):
                            results.append(line)
            else:
                # 文件名搜索
                result = await self.execute_command(
                    f"find {path} -name '*{pattern}*' -type f 2>/dev/null"
                )
                
                if result.success:
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            results.append(line)
        
        except Exception as e:
            logger.error(f"Remote search failed: {e}")
        
        return results
    
    async def get_file_hash(self, path: str) -> Optional[str]:
        """获取远程文件哈希"""
        result = await self.execute_command(f"md5sum {path} 2>/dev/null || md5 {path}")
        
        if result.success:
            hash_value = result.stdout.strip().split()[0]
            return hash_value
        
        return None
    
    async def close(self):
        """关闭 SSH 连接"""
        if self._sftp_client:
            self._sftp_client.close()
        
        if self._connection:
            self._connection.close()
        
        logger.info(f"Remote environment closed: {self.username}@{self.host}")
    
    async def health_check(self) -> bool:
        """健康检查"""
        if not self._connection:
            return False
        
        try:
            result = await self.execute_command("echo 'health'")
            return result.success
        except Exception:
            return False
