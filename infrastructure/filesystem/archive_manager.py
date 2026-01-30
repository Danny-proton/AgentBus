"""
存档管理模块 - 提供ZIP和TAR存档的创建、提取和管理功能
"""

import os
import tarfile
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum
import asyncio


class ArchiveKind(Enum):
    """存档类型"""
    ZIP = "zip"
    TAR = "tar"
    TAR_GZ = "tar.gz"
    TAR_BZ2 = "tar.bz2"


@dataclass
class ArchiveEntry:
    """存档条目"""
    name: str
    size: int
    is_dir: bool
    modified: Optional[str] = None
    compressed_size: Optional[int] = None
    compression_type: Optional[str] = None


@dataclass
class ArchiveStats:
    """存档统计"""
    total_entries: int
    total_size: int
    compressed_size: int
    compression_ratio: float
    directories: int
    files: int


class ArchiveManager:
    """存档管理器"""
    
    def __init__(self):
        self._temp_dirs = []
    
    async def cleanup_temp_dirs(self):
        """清理临时目录"""
        for temp_dir in self._temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception:
                pass
        self._temp_dirs.clear()
    
    def _resolve_archive_kind(self, file_path: Union[str, Path]) -> ArchiveKind:
        """确定存档类型"""
        path_str = str(file_path).lower()
        
        if path_str.endswith('.zip'):
            return ArchiveKind.ZIP
        elif path_str.endswith('.tar.gz') or path_str.endswith('.tgz'):
            return ArchiveKind.TAR_GZ
        elif path_str.endswith('.tar.bz2') or path_str.endswith('.tbz2'):
            return ArchiveKind.TAR_BZ2
        elif path_str.endswith('.tar'):
            return ArchiveKind.TAR
        else:
            # 默认尝试ZIP
            return ArchiveKind.ZIP
    
    async def create_archive(self, source_path: Union[str, Path],
                           archive_path: Union[str, Path],
                           kind: ArchiveKind = None) -> bool:
        """创建存档"""
        source = Path(source_path)
        archive = Path(archive_path)
        
        if not source.exists():
            return False
        
        try:
            # 确保目标目录存在
            archive.parent.mkdir(parents=True, exist_ok=True)
            
            if kind is None:
                kind = self._resolve_archive_kind(archive)
            
            if kind == ArchiveKind.ZIP:
                return await self._create_zip(source, archive)
            elif kind == ArchiveKind.TAR:
                return await self._create_tar(source, archive, 'w')
            elif kind == ArchiveKind.TAR_GZ:
                return await self._create_tar(source, archive, 'w:gz')
            elif kind == ArchiveKind.TAR_BZ2:
                return await self._create_tar(source, archive, 'w:bz2')
            else:
                return False
                
        except Exception:
            return False
    
    async def _create_zip(self, source: Path, archive: Path) -> bool:
        """创建ZIP存档"""
        try:
            with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if source.is_dir():
                    for root, dirs, files in os.walk(source):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = file_path.relative_to(source.parent)
                            zipf.write(file_path, arcname)
                else:
                    zipf.write(source, source.name)
            return True
        except Exception:
            return False
    
    async def _create_tar(self, source: Path, archive: Path, 
                         mode: str) -> bool:
        """创建TAR存档"""
        try:
            with tarfile.open(archive, mode) as tarf:
                if source.is_dir():
                    tarf.add(source, arcname=source.name)
                else:
                    tarf.add(source, arcname=source.name)
            return True
        except Exception:
            return False
    
    async def extract_archive(self, archive_path: Union[str, Path],
                            extract_path: Union[str, Path] = None,
                            kind: ArchiveKind = None) -> bool:
        """提取存档"""
        archive = Path(archive_path)
        
        if not archive.exists():
            return False
        
        if extract_path is None:
            extract_path = archive.parent
        else:
            extract_path = Path(extract_path)
        
        try:
            if kind is None:
                kind = self._resolve_archive_kind(archive)
            
            if kind == ArchiveKind.ZIP:
                return await self._extract_zip(archive, extract_path)
            else:
                return await self._extract_tar(archive, extract_path, kind)
                
        except Exception:
            return False
    
    async def _extract_zip(self, archive: Path, extract_path: Path) -> bool:
        """提取ZIP存档"""
        try:
            with zipfile.ZipFile(archive, 'r') as zipf:
                # 确保提取路径存在
                extract_path.mkdir(parents=True, exist_ok=True)
                
                # 安全检查：防止路径遍历攻击
                for member in zipf.namelist():
                    member_path = (extract_path / member).resolve()
                    if not str(member_path).startswith(str(extract_path.resolve())):
                        return False
                
                zipf.extractall(extract_path)
            return True
        except Exception:
            return False
    
    async def _extract_tar(self, archive: Path, extract_path: Path,
                          kind: ArchiveKind) -> bool:
        """提取TAR存档"""
        try:
            mode_map = {
                ArchiveKind.TAR: 'r',
                ArchiveKind.TAR_GZ: 'r:gz',
                ArchiveKind.TAR_BZ2: 'r:bz2'
            }
            
            mode = mode_map.get(kind, 'r')
            with tarfile.open(archive, mode) as tarf:
                # 确保提取路径存在
                extract_path.mkdir(parents=True, exist_ok=True)
                
                # 安全检查
                for member in tarf.getmembers():
                    if member.name.startswith('/') or '..' in member.name:
                        continue
                    
                    member_path = (extract_path / member.name).resolve()
                    if not str(member_path).startswith(str(extract_path.resolve())):
                        continue
                
                tarf.extractall(extract_path)
            return True
        except Exception:
            return False
    
    async def list_archive_contents(self, archive_path: Union[str, Path],
                                  kind: ArchiveKind = None) -> List[ArchiveEntry]:
        """列出存档内容"""
        archive = Path(archive_path)
        
        if not archive.exists():
            return []
        
        try:
            if kind is None:
                kind = self._resolve_archive_kind(archive)
            
            if kind == ArchiveKind.ZIP:
                return await self._list_zip_contents(archive)
            else:
                return await self._list_tar_contents(archive, kind)
                
        except Exception:
            return []
    
    async def _list_zip_contents(self, archive: Path) -> List[ArchiveEntry]:
        """列出ZIP内容"""
        contents = []
        try:
            with zipfile.ZipFile(archive, 'r') as zipf:
                for info in zipf.infolist():
                    contents.append(ArchiveEntry(
                        name=info.filename,
                        size=info.file_size,
                        is_dir=info.filename.endswith('/'),
                        modified=info.date_time.isoformat() if info.date_time else None,
                        compressed_size=info.compress_size,
                        compression_type="deflated" if info.compress_type == 8 else "stored"
                    ))
        except Exception:
            pass
        
        return contents
    
    async def _list_tar_contents(self, archive: Path, 
                               kind: ArchiveKind) -> List[ArchiveEntry]:
        """列出TAR内容"""
        contents = []
        try:
            mode_map = {
                ArchiveKind.TAR: 'r',
                ArchiveKind.TAR_GZ: 'r:gz',
                ArchiveKind.TAR_BZ2: 'r:bz2'
            }
            
            mode = mode_map.get(kind, 'r')
            with tarfile.open(archive, mode) as tarf:
                for member in tarf.getmembers():
                    contents.append(ArchiveEntry(
                        name=member.name,
                        size=member.size,
                        is_dir=member.isdir(),
                        modified=member.mtime.isoformat() if member.mtime else None
                    ))
        except Exception:
            pass
        
        return contents
    
    async def get_archive_stats(self, archive_path: Union[str, Path],
                              kind: ArchiveKind = None) -> Optional[ArchiveStats]:
        """获取存档统计信息"""
        contents = await self.list_archive_contents(archive_path, kind)
        
        if not contents:
            return None
        
        total_size = sum(entry.size for entry in contents if not entry.is_dir)
        compressed_size = sum(
            entry.compressed_size for entry in contents 
            if entry.compressed_size and not entry.is_dir
        ) or total_size  # 如果没有压缩大小信息，使用原始大小
        
        directories = sum(1 for entry in contents if entry.is_dir)
        files = len(contents) - directories
        
        compression_ratio = (
            (1 - compressed_size / total_size) * 100 
            if total_size > 0 and compressed_size > 0 else 0
        )
        
        return ArchiveStats(
            total_entries=len(contents),
            total_size=total_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            directories=directories,
            files=files
        )
    
    async def verify_archive(self, archive_path: Union[str, Path],
                           kind: ArchiveKind = None) -> Dict[str, Any]:
        """验证存档完整性"""
        archive = Path(archive_path)
        
        if not archive.exists():
            return {"valid": False, "error": "Archive file does not exist"}
        
        try:
            if kind is None:
                kind = self._resolve_archive_kind(archive)
            
            if kind == ArchiveKind.ZIP:
                return await self._verify_zip(archive)
            else:
                return await self._verify_tar(archive, kind)
                
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def _verify_zip(self, archive: Path) -> Dict[str, Any]:
        """验证ZIP存档"""
        try:
            with zipfile.ZipFile(archive, 'r') as zipf:
                result = zipf.testzip()
                if result:
                    return {
                        "valid": False,
                        "error": f"Corrupted file in archive: {result}"
                    }
                return {"valid": True, "entries": len(zipf.namelist())}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def _verify_tar(self, archive: Path, kind: ArchiveKind) -> Dict[str, Any]:
        """验证TAR存档"""
        try:
            mode_map = {
                ArchiveKind.TAR: 'r',
                ArchiveKind.TAR_GZ: 'r:gz',
                ArchiveKind.TAR_BZ2: 'r:bz2'
            }
            
            mode = mode_map.get(kind, 'r')
            with tarfile.open(archive, mode) as tarf:
                # 尝试读取所有成员来验证完整性
                members = tarf.getmembers()
                return {"valid": True, "entries": len(members)}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def extract_to_temp(self, archive_path: Union[str, Path]) -> Optional[str]:
        """提取到临时目录"""
        temp_dir = tempfile.mkdtemp()
        self._temp_dirs.append(temp_dir)
        
        success = await self.extract_archive(archive_path, temp_dir)
        if success:
            return temp_dir
        else:
            # 清理失败的提取
            try:
                shutil.rmtree(temp_dir)
                self._temp_dirs.remove(temp_dir)
            except Exception:
                pass
            return None
    
    async def create_archive_from_files(self, files: List[Union[str, Path]],
                                      archive_path: Union[str, Path],
                                      kind: ArchiveKind = ArchiveKind.ZIP) -> bool:
        """从文件列表创建存档"""
        archive = Path(archive_path)
        
        try:
            # 确保目标目录存在
            archive.parent.mkdir(parents=True, exist_ok=True)
            
            if kind == ArchiveKind.ZIP:
                return await self._create_zip_from_files(files, archive)
            else:
                return await self._create_tar_from_files(files, archive, kind)
                
        except Exception:
            return False
    
    async def _create_zip_from_files(self, files: List[Path], 
                                   archive: Path) -> bool:
        """从文件列表创建ZIP"""
        try:
            with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    if file_path.exists():
                        zipf.write(file_path, file_path.name)
            return True
        except Exception:
            return False
    
    async def _create_tar_from_files(self, files: List[Path], 
                                  archive: Path, kind: ArchiveKind) -> bool:
        """从文件列表创建TAR"""
        try:
            mode_map = {
                ArchiveKind.TAR: 'w',
                ArchiveKind.TAR_GZ: 'w:gz',
                ArchiveKind.TAR_BZ2: 'w:bz2'
            }
            
            mode = mode_map.get(kind, 'w')
            with tarfile.open(archive, mode) as tarf:
                for file_path in files:
                    if file_path.exists():
                        tarf.add(file_path, arcname=file_path.name)
            return True
        except Exception:
            return False