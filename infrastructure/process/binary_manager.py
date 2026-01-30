"""
二进制文件管理模块 - 提供二进制文件检测、依赖管理和版本控制功能
"""

import os
import shutil
import hashlib
import subprocess
import platform
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from .process_types import BinaryInfo


class BinaryManager:
    """二进制文件管理器"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self._binary_cache: Dict[str, BinaryInfo] = {}
        self._required_binaries = set()
    
    def add_required_binary(self, binary_name: str):
        """添加必需的二进制文件"""
        self._required_binaries.add(binary_name)
    
    def remove_required_binary(self, binary_name: str):
        """移除必需的二进制文件"""
        self._required_binaries.discard(binary_name)
    
    async def find_binary(self, binary_name: str) -> Optional[str]:
        """查找二进制文件路径"""
        # 首先检查缓存
        if binary_name in self._binary_cache:
            cached_path = self._binary_cache[binary_name].path
            if Path(cached_path).exists():
                return cached_path
        
        # 在系统PATH中查找
        try:
            result = await self._run_command("which", [binary_name])
            if result.returncode == 0:
                binary_path = result.stdout.strip()
                # 缓存结果
                info = await self._get_binary_info(binary_path)
                if info:
                    self._binary_cache[binary_name] = info
                return binary_path
        except Exception:
            pass
        
        # Windows下尝试不同扩展名
        if self.system == "windows":
            for ext in ['.exe', '.bat', '.cmd', '.ps1']:
                try:
                    result = await self._run_command("where", [f"{binary_name}{ext}"])
                    if result.returncode == 0:
                        binary_path = result.stdout.strip()
                        info = await self._get_binary_info(binary_path)
                        if info:
                            self._binary_cache[binary_name] = info
                        return binary_path
                except Exception:
                    continue
        
        return None
    
    async def _get_binary_info(self, binary_path: str) -> Optional[BinaryInfo]:
        """获取二进制文件信息"""
        try:
            path_obj = Path(binary_path)
            if not path_obj.exists():
                return None
            
            # 基础信息
            name = path_obj.name
            size = path_obj.stat().st_size
            permissions = oct(path_obj.stat().st_mode)[-3:] if self.system != "windows" else None
            is_executable = os.access(binary_path, os.X_OK)
            
            # 尝试获取版本信息
            version = None
            description = None
            vendor = None
            
            try:
                if self.system == "windows":
                    # Windows版本信息
                    import winreg
                    try:
                        version_info = subprocess.check_output(
                            ["wmic", "datafile", "where", f"Name='{binary_path.replace(chr(92), chr(92)+chr(92))}'", "get", "Version"],
                            stderr=subprocess.DEVNULL,
                            universal_newlines=True
                        ).strip()
                        if version_info and version_info != "No Instance(s) Available.":
                            version = version_info
                    except Exception:
                        pass
                else:
                    # Unix/Linux版本信息
                    try:
                        result = await self._run_command(binary_path, ["--version"])
                        if result.returncode == 0:
                            version_lines = result.stdout.split('\n')
                            for line in version_lines[:3]:  # 只检查前几行
                                if line.strip():
                                    version = line.strip()
                                    break
                    except Exception:
                        pass
            except Exception:
                pass
            
            # 计算校验和
            checksum = await self._calculate_checksum(binary_path)
            
            return BinaryInfo(
                name=name,
                path=binary_path,
                version=version,
                size=size,
                checksum=checksum,
                permissions=permissions,
                is_executable=is_executable,
                description=description,
                vendor=vendor
            )
        except Exception:
            return None
    
    async def _calculate_checksum(self, file_path: str) -> str:
        """计算文件校验和"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return None
    
    async def check_required_binaries(self) -> Dict[str, bool]:
        """检查必需的二进制文件"""
        results = {}
        for binary in self._required_binaries:
            binary_path = await self.find_binary(binary)
            results[binary] = binary_path is not None
        return results
    
    async def install_binary(self, binary_name: str, source_path: str = None) -> bool:
        """安装二进制文件（仅适用于特定系统）"""
        if self.system == "linux":
            return await self._install_linux_binary(binary_name, source_path)
        elif self.system == "darwin":  # macOS
            return await self._install_macos_binary(binary_name, source_path)
        elif self.system == "windows":
            return await self._install_windows_binary(binary_name, source_path)
        else:
            return False
    
    async def _install_linux_binary(self, binary_name: str, source_path: str = None) -> bool:
        """Linux二进制文件安装"""
        try:
            # 尝试使用包管理器
            package_managers = [
                ("apt", ["install", "-y", binary_name]),
                ("yum", ["install", "-y", binary_name]),
                ("dnf", ["install", "-y", binary_name]),
                ("pacman", ["-S", "--noconfirm", binary_name]),
                ("apk", ["add", binary_name])
            ]
            
            for pm, args in package_managers:
                try:
                    result = await self._run_command(pm, args)
                    if result.returncode == 0:
                        return True
                except Exception:
                    continue
            
            # 如果包管理器失败，尝试手动安装
            if source_path:
                dest_path = f"/usr/local/bin/{binary_name}"
                try:
                    shutil.copy2(source_path, dest_path)
                    os.chmod(dest_path, 0o755)
                    return True
                except Exception:
                    pass
            
            return False
        except Exception:
            return False
    
    async def _install_macos_binary(self, binary_name: str, source_path: str = None) -> bool:
        """macOS二进制文件安装"""
        try:
            # 尝试使用Homebrew
            try:
                result = await self._run_command("brew", ["install", binary_name])
                if result.returncode == 0:
                    return True
            except Exception:
                pass
            
            # 手动安装
            if source_path:
                dest_path = f"/usr/local/bin/{binary_name}"
                try:
                    shutil.copy2(source_path, dest_path)
                    os.chmod(dest_path, 0o755)
                    return True
                except Exception:
                    pass
            
            return False
        except Exception:
            return False
    
    async def _install_windows_binary(self, binary_name: str, source_path: str = None) -> bool:
        """Windows二进制文件安装"""
        try:
            # Windows下通常使用MSI安装程序或exe文件
            # 这里提供基本的复制功能
            if source_path:
                import shutil
                dest_path = os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), binary_name)
                try:
                    shutil.copy2(source_path, dest_path)
                    return True
                except Exception:
                    pass
            
            return False
        except Exception:
            return False
    
    async def get_binary_dependencies(self, binary_path: str) -> List[str]:
        """获取二进制文件依赖"""
        try:
            if self.system == "linux":
                return await self._get_linux_dependencies(binary_path)
            elif self.system == "darwin":  # macOS
                return await self._get_macos_dependencies(binary_path)
            elif self.system == "windows":
                return await self._get_windows_dependencies(binary_path)
            else:
                return []
        except Exception:
            return []
    
    async def _get_linux_dependencies(self, binary_path: str) -> List[str]:
        """获取Linux二进制文件依赖"""
        try:
            result = await self._run_command("ldd", [binary_path])
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                dependencies = []
                for line in lines:
                    line = line.strip()
                    if '=>' in line and '(' in line:
                        lib_name = line.split('=>')[0].strip()
                        dependencies.append(lib_name)
                return dependencies
        except Exception:
            pass
        return []
    
    async def _get_macos_dependencies(self, binary_path: str) -> List[str]:
        """获取macOS二进制文件依赖"""
        try:
            result = await self._run_command("otool", ["-L", binary_path])
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                dependencies = []
                for line in lines[1:]:  # 跳过第一行
                    line = line.strip()
                    if line and '(' in line:
                        lib_path = line.split('(')[0].strip()
                        dependencies.append(lib_path)
                return dependencies
        except Exception:
            pass
        return []
    
    async def _get_windows_dependencies(self, binary_path: str) -> List[str]:
        """获取Windows二进制文件依赖"""
        # Windows DLL依赖检测比较复杂，通常需要特殊工具
        # 这里返回空列表，实际实现可以使用Dependency Walker等工具
        return []
    
    async def verify_binary_integrity(self, binary_path: str) -> Dict[str, Any]:
        """验证二进制文件完整性"""
        try:
            info = await self._get_binary_info(binary_path)
            if not info:
                return {"valid": False, "error": "Binary not found"}
            
            # 检查文件是否存在且可执行
            path_obj = Path(binary_path)
            if not path_obj.exists():
                return {"valid": False, "error": "Binary file not found"}
            
            if not os.access(binary_path, os.R_OK):
                return {"valid": False, "error": "Binary file not readable"}
            
            # 计算当前校验和
            current_checksum = await self._calculate_checksum(binary_path)
            
            # 如果有缓存的校验和，进行比较
            cached_checksum = info.checksum
            checksum_match = current_checksum == cached_checksum if cached_checksum else None
            
            return {
                "valid": True,
                "info": {
                    "name": info.name,
                    "size": info.size,
                    "is_executable": info.is_executable,
                    "checksum": current_checksum,
                    "checksum_match": checksum_match,
                    "cached_checksum": cached_checksum
                }
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def _run_command(self, command: str, args: List[str]) -> subprocess.CompletedProcess:
        """运行命令"""
        try:
            return await asyncio.create_subprocess_exec(
                command, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            ).wait()
        except Exception:
            raise
    
    async def get_binary_version(self, binary_path: str) -> Optional[str]:
        """获取二进制文件版本"""
        try:
            result = await self._run_command(binary_path, ["--version"])
            if result.returncode == 0:
                version_lines = result.stdout.split('\n')
                for line in version_lines[:3]:  # 只检查前几行
                    if line.strip():
                        return line.strip()
        except Exception:
            pass
        return None
    
    def clear_cache(self):
        """清空缓存"""
        self._binary_cache.clear()
    
    def get_cached_binaries(self) -> Dict[str, BinaryInfo]:
        """获取缓存的二进制文件信息"""
        return self._binary_cache.copy()
    
    async def scan_directory_for_binaries(self, directory: str) -> List[BinaryInfo]:
        """扫描目录中的二进制文件"""
        binaries = []
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return binaries
            
            for item in dir_path.iterdir():
                if item.is_file():
                    # 检查文件是否为可执行文件
                    if os.access(str(item), os.X_OK):
                        info = await self._get_binary_info(str(item))
                        if info:
                            binaries.append(info)
        except Exception:
            pass
        
        return binaries