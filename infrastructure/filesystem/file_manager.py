"""
文件系统管理模块 - 提供文件操作、目录管理和监控功能
"""

import os
import shutil
import asyncio
import hashlib
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional, Union, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class FileType(Enum):
    """文件类型"""
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    UNKNOWN = "unknown"


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    name: str
    size: int
    type: FileType
    modified: datetime
    created: datetime
    accessed: datetime
    permissions: str
    mime_type: Optional[str] = None
    checksum: Optional[str] = None
    is_hidden: bool = False
    is_executable: bool = False


@dataclass
class DirectoryInfo:
    """目录信息"""
    path: str
    name: str
    total_size: int
    file_count: int
    directory_count: int
    modified: datetime
    permissions: str


class FileSystemManager:
    """文件系统管理器"""
    
    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self._watchers: Dict[str, Callable] = {}
        self._file_callbacks: List[Callable[[FileInfo], None]] = []
        self._dir_callbacks: List[Callable[[DirectoryInfo], None]] = []
    
    def set_base_path(self, path: Union[str, Path]):
        """设置基础路径"""
        self.base_path = Path(path)
    
    def resolve_path(self, path: Union[str, Path]) -> Path:
        """解析路径"""
        return self.base_path / Path(path)
    
    async def file_exists(self, path: Union[str, Path]) -> bool:
        """检查文件是否存在"""
        return self.resolve_path(path).exists()
    
    async def is_file(self, path: Union[str, Path]) -> bool:
        """检查是否为文件"""
        return self.resolve_path(path).is_file()
    
    async def is_directory(self, path: Union[str, Path]) -> bool:
        """检查是否为目录"""
        return self.resolve_path(path).is_dir()
    
    async def get_file_info(self, path: Union[str, Path]) -> Optional[FileInfo]:
        """获取文件信息"""
        file_path = self.resolve_path(path)
        try:
            stat = file_path.stat()
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            # 计算文件哈希
            checksum = None
            if file_path.is_file():
                checksum = await self._calculate_checksum(file_path)
            
            # 检查权限
            permissions = oct(stat.st_mode)[-3:]
            is_executable = os.access(str(file_path), os.X_OK)
            is_hidden = file_path.name.startswith('.')
            
            return FileInfo(
                path=str(file_path.absolute()),
                name=file_path.name,
                size=stat.st_size,
                type=FileType.FILE if file_path.is_file() else 
                     FileType.DIRECTORY if file_path.is_dir() else
                     FileType.SYMLINK if file_path.is_symlink() else FileType.UNKNOWN,
                modified=datetime.fromtimestamp(stat.st_mtime),
                created=datetime.fromtimestamp(stat.st_ctime),
                accessed=datetime.fromtimestamp(stat.st_atime),
                permissions=permissions,
                mime_type=mime_type,
                checksum=checksum,
                is_hidden=is_hidden,
                is_executable=is_executable
            )
        except (OSError, FileNotFoundError):
            return None
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return None
    
    async def get_directory_info(self, path: Union[str, Path]) -> Optional[DirectoryInfo]:
        """获取目录信息"""
        dir_path = self.resolve_path(path)
        try:
            if not dir_path.is_dir():
                return None
            
            stat = dir_path.stat()
            total_size = 0
            file_count = 0
            directory_count = 0
            
            # 递归计算大小和计数
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    try:
                        file_path = Path(root) / file
                        total_size += file_path.stat().st_size
                        file_count += 1
                    except OSError:
                        pass
                directory_count += len(dirs)
            
            return DirectoryInfo(
                path=str(dir_path.absolute()),
                name=dir_path.name,
                total_size=total_size,
                file_count=file_count,
                directory_count=directory_count,
                modified=datetime.fromtimestamp(stat.st_mtime),
                permissions=oct(stat.st_mode)[-3:]
            )
        except (OSError, FileNotFoundError):
            return None
    
    async def list_directory(self, path: Union[str, Path], 
                           include_hidden: bool = False,
                           recursive: bool = False) -> List[FileInfo]:
        """列出目录内容"""
        dir_path = self.resolve_path(path)
        if not dir_path.is_dir():
            return []
        
        results = []
        pattern = "*" if include_hidden else "[!.]*"
        
        if recursive:
            for file_path in dir_path.rglob(pattern):
                if file_path.is_file() or file_path.is_dir():
                    info = await self.get_file_info(file_path)
                    if info:
                        results.append(info)
        else:
            for item in dir_path.glob(pattern):
                if item.is_file() or item.is_dir():
                    info = await self.get_file_info(item)
                    if info:
                        results.append(info)
        
        return sorted(results, key=lambda x: x.name.lower())
    
    async def create_directory(self, path: Union[str, Path], 
                             parents: bool = True) -> bool:
        """创建目录"""
        dir_path = self.resolve_path(path)
        try:
            if parents:
                dir_path.mkdir(parents=True, exist_ok=True)
            else:
                dir_path.mkdir(exist_ok=False)
            return True
        except (OSError, FileExistsError):
            return False
    
    async def delete_file(self, path: Union[str, Path]) -> bool:
        """删除文件"""
        file_path = self.resolve_path(path)
        try:
            if file_path.is_file() or file_path.is_symlink():
                file_path.unlink()
                return True
            return False
        except OSError:
            return False
    
    async def delete_directory(self, path: Union[str, Path], 
                            recursive: bool = False) -> bool:
        """删除目录"""
        dir_path = self.resolve_path(path)
        try:
            if recursive:
                shutil.rmtree(dir_path)
            else:
                dir_path.rmdir()
            return True
        except OSError:
            return False
    
    async def copy_file(self, source: Union[str, Path], 
                       destination: Union[str, Path]) -> bool:
        """复制文件"""
        src_path = self.resolve_path(source)
        dst_path = self.resolve_path(destination)
        try:
            # 确保目标目录存在
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)
            return True
        except OSError:
            return False
    
    async def move_file(self, source: Union[str, Path], 
                       destination: Union[str, Path]) -> bool:
        """移动文件"""
        src_path = self.resolve_path(source)
        dst_path = self.resolve_path(destination)
        try:
            # 确保目标目录存在
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            return True
        except OSError:
            return False
    
    async def read_file(self, path: Union[str, Path], 
                       encoding: str = 'utf-8') -> Optional[str]:
        """读取文件内容"""
        file_path = self.resolve_path(path)
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except (OSError, UnicodeDecodeError):
            return None
    
    async def write_file(self, content: str, path: Union[str, Path], 
                        encoding: str = 'utf-8') -> bool:
        """写入文件内容"""
        file_path = self.resolve_path(path)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            return True
        except OSError:
            return False
    
    async def append_file(self, content: str, path: Union[str, Path], 
                         encoding: str = 'utf-8') -> bool:
        """追加文件内容"""
        file_path = self.resolve_path(path)
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'a', encoding=encoding) as f:
                f.write(content)
            return True
        except OSError:
            return False
    
    async def search_files(self, pattern: str, 
                          path: Union[str, Path] = None,
                          case_sensitive: bool = False) -> List[FileInfo]:
        """搜索文件"""
        if path is None:
            path = self.base_path
        else:
            path = self.resolve_path(path)
        
        results = []
        glob_pattern = f"**/{pattern}" if "**" not in pattern else pattern
        
        try:
            for file_path in path.rglob(glob_pattern):
                if file_path.is_file() or file_path.is_dir():
                    info = await self.get_file_info(file_path)
                    if info:
                        # 简单模式匹配
                        if not case_sensitive:
                            if pattern.lower() in info.name.lower():
                                results.append(info)
                        else:
                            if pattern in info.name:
                                results.append(info)
        except Exception:
            pass
        
        return results
    
    async def get_disk_usage(self, path: Union[str, Path] = None) -> Dict[str, Any]:
        """获取磁盘使用情况"""
        if path is None:
            path = self.base_path
        else:
            path = self.resolve_path(path)
        
        try:
            total, used, free = shutil.disk_usage(path)
            return {
                "path": str(path),
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "used_percent": (used / total * 100) if total > 0 else 0
            }
        except OSError:
            return {}
    
    async def get_file_statistics(self, path: Union[str, Path]) -> Dict[str, Any]:
        """获取文件统计信息"""
        info = await self.get_file_info(path)
        if not info:
            return {}
        
        return {
            "name": info.name,
            "path": info.path,
            "size": info.size,
            "type": info.type.value,
            "mime_type": info.mime_type,
            "checksum": info.checksum,
            "permissions": info.permissions,
            "is_hidden": info.is_hidden,
            "is_executable": info.is_executable,
            "created": info.created.isoformat(),
            "modified": info.modified.isoformat(),
            "accessed": info.accessed.isoformat()
        }