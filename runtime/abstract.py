"""
运行时抽象层
定义环境操作的抽象接口
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncGenerator, Optional, Dict, Any, List
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """命令执行结果"""
    stdout: str
    stderr: str
    exit_code: int
    success: bool


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    name: str
    is_directory: bool
    size: int
    modified: Optional[str] = None


@dataclass
class EnvironmentInfo:
    """环境信息"""
    type: str  # local, remote
    host: Optional[str] = None
    workspace: str = ""
    os: Optional[str] = None
    python_version: Optional[str] = None
    cpu_count: Optional[int] = None
    memory: Optional[str] = None


class Environment(ABC):
    """
    环境抽象基类
    定义文件操作和命令执行的统一接口
    """
    
    def __init__(self, workspace: str = "/workspace"):
        self.workspace = Path(workspace)
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化环境"""
        pass
    
    @abstractmethod
    async def get_info(self) -> EnvironmentInfo:
        """获取环境信息"""
        pass
    
    @abstractmethod
    async def execute_command(
        self,
        command: str,
        timeout: int = 60,
        working_dir: Optional[str] = None
    ) -> CommandResult:
        """
        执行命令
        
        Args:
            command: 命令
            timeout: 超时时间（秒）
            working_dir: 工作目录
        
        Returns:
            CommandResult: 执行结果
        """
        pass
    
    @abstractmethod
    async def execute_command_stream(
        self,
        command: str,
        working_dir: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式执行命令
        
        Yields:
            str: 输出行
        """
        pass
    
    @abstractmethod
    async def read_file(self, path: str) -> Optional[str]:
        """读取文件内容"""
        pass
    
    @abstractmethod
    async def write_file(self, path: str, content: str) -> bool:
        """写入文件"""
        pass
    
    @abstractmethod
    async def edit_file(
        self,
        path: str,
        old_text: str,
        new_text: str
    ) -> bool:
        """
        编辑文件（文本替换）
        
        Args:
            path: 文件路径
            old_text: 要替换的文本
            new_text: 新文本
        
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """删除文件"""
        pass
    
    @abstractmethod
    async def list_dir(self, path: str) -> List[FileInfo]:
        """列出目录内容"""
        pass
    
    @abstractmethod
    async def glob(self, pattern: str) -> List[str]:
        """查找匹配的文件"""
        pass
    
    @abstractmethod
    async def exists(self, path: str) -> bool:
        """检查路径是否存在"""
        pass
    
    @abstractmethod
    async def is_directory(self, path: str) -> bool:
        """是否为目录"""
        pass
    
    @abstractmethod
    async def mkdir(self, path: str, parents: bool = True) -> bool:
        """创建目录"""
        pass
    
    @abstractmethod
    async def copy_file(self, src: str, dst: str) -> bool:
        """复制文件"""
        pass
    
    @abstractmethod
    async def move_file(self, src: str, dst: str) -> bool:
        """移动文件"""
        pass
    
    @abstractmethod
    async def search_files(
        self,
        path: str,
        pattern: str,
        content_search: bool = False
    ) -> List[str]:
        """搜索文件"""
        pass
    
    @abstractmethod
    async def get_file_hash(self, path: str) -> Optional[str]:
        """获取文件哈希"""
        pass
    
    @abstractmethod
    async def close(self):
        """关闭连接/清理资源"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass


class EnvironmentFactory:
    """环境工厂"""
    
    _environment: Optional[Environment] = None
    _local_env: Optional[Environment] = None
    _remote_env: Optional[Environment] = None
    
    @classmethod
    def get_environment(cls) -> Environment:
        """获取当前环境"""
        if cls._environment:
            return cls._environment
        
        # 默认返回本地环境
        if cls._local_env is None:
            from runtime.local.environment import LocalEnvironment
            cls._local_env = LocalEnvironment()
        
        return cls._local_env
    
    @classmethod
    def set_environment(cls, env: Environment):
        """设置环境"""
        cls._environment = env
        logger.info(f"Environment set to: {type(env).__name__}")
    
    @classmethod
    def create_local(cls, workspace: str = "/workspace") -> Environment:
        """创建本地环境"""
        from runtime.local.environment import LocalEnvironment
        return LocalEnvironment(workspace)
    
    @classmethod
    async def create_remote(
        cls,
        host: str,
        username: str,
        password: Optional[str] = None,
        private_key_path: Optional[str] = None,
        workspace: str = "/workspace"
    ) -> Environment:
        """创建远程环境（SSH）"""
        from runtime.remote.environment import RemoteEnvironment
        
        return RemoteEnvironment(
            host=host,
            username=username,
            password=password,
            private_key_path=private_key_path,
            workspace=workspace
        )
    
    @classmethod
    def reset(cls):
        """重置环境"""
        cls._environment = None
        cls._local_env = None
        cls._remote_env = None


class CommandApproval:
    """命令批准请求"""
    
    def __init__(
        self,
        command: str,
        tool_name: str,
        reason: Optional[str] = None
    ):
        self.id = f"approval_{id(self)}"
        self.command = command
        self.tool_name = tool_name
        self.reason = reason
        self.approved = False
        self.timestamp = None
        self.event = asyncio.Event()
    
    async def wait(self, timeout: Optional[float] = None) -> bool:
        """等待批准"""
        try:
            await asyncio.wait_for(self.event.wait(), timeout=timeout)
            return self.approved
        except asyncio.TimeoutError:
            return False
    
    def approve(self):
        """批准"""
        self.approved = True
        self.timestamp = asyncio.get_event_loop().time()
        self.event.set()
    
    def reject(self):
        """拒绝"""
        self.approved = False
        self.timestamp = asyncio.get_event_loop().time()
        self.event.set()
