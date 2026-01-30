"""
AgentBus 配置备份与恢复系统
Configuration Backup and Recovery System for AgentBus

提供配置文件的自动备份、手动备份、恢复和版本管理功能。
"""

import os
import json
import yaml
import shutil
import zipfile
import tarfile
import gzip
import hashlib
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import schedule

from .config_types import ConfigSnapshot, ConfigHistory, EnvironmentType
from .security import ConfigEncryption


logger = logging.getLogger(__name__)


class BackupType(str, Enum):
    """备份类型"""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    SCHEDULED = "scheduled"
    PRE_UPDATE = "pre_update"
    PRE_DEPLOYMENT = "pre_deployment"


class BackupFormat(str, Enum):
    """备份格式"""
    JSON = "json"
    YAML = "yaml"
    ZIP = "zip"
    TAR = "tar"
    TAR_GZ = "tar.gz"


class BackupCompression(str, Enum):
    """备份压缩"""
    NONE = "none"
    GZIP = "gzip"
    BZIP2 = "bzip2"
    LZMA = "lzma"


@dataclass
class BackupMetadata:
    """备份元数据"""
    id: str
    name: str
    description: str
    backup_type: BackupType
    format: BackupFormat
    compression: BackupCompression
    created_at: datetime
    created_by: str
    environment: EnvironmentType
    profile: str
    file_count: int
    total_size: int
    checksum: str
    encrypted: bool
    retention_days: Optional[int] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RecoveryResult:
    """恢复结果"""
    success: bool
    backup_id: str
    restored_files: List[Path]
    errors: List[str]
    warnings: List[str]
    restored_at: datetime


class ConfigBackupManager:
    """配置备份管理器"""
    
    def __init__(self, config_dir: Path, backup_dir: Optional[Path] = None):
        self.config_dir = Path(config_dir)
        self.backup_dir = Path(backup_dir) if backup_dir else self.config_dir / "backups"
        self._metadata_file = self.backup_dir / "backup_metadata.json"
        self._lock = threading.RLock()
        self._backup_schedules: Dict[str, Any] = {}
        self._auto_backup_enabled = False
        
        # 加密器
        self._encryption = ConfigEncryption()
        
        # 备份配置
        self._backup_config = {
            "max_backups": 50,
            "auto_backup": True,
            "backup_interval_hours": 24,
            "compression_enabled": True,
            "encryption_enabled": False,
            "cleanup_enabled": True,
            "retention_days": 30
        }
        
        # 创建备份目录
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self._load_backup_config()
    
    def _load_backup_config(self):
        """加载备份配置"""
        config_file = self.config_dir / "backup_config.yaml"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    self._backup_config.update(config_data)
            except Exception as e:
                logger.warning(f"加载备份配置失败: {e}")
    
    def _save_backup_config(self):
        """保存备份配置"""
        config_file = self.config_dir / "backup_config.yaml"
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self._backup_config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            logger.error(f"保存备份配置失败: {e}")
    
    def create_backup(self, 
                     name: str,
                     description: str = "",
                     backup_type: BackupType = BackupType.MANUAL,
                     format: BackupFormat = BackupFormat.ZIP,
                     compression: BackupCompression = BackupCompression.GZIP,
                     include_encryption: bool = False,
                     tags: Optional[List[str]] = None) -> str:
        """创建备份"""
        
        with self._lock:
            try:
                # 生成备份ID
                backup_id = f"{name}_{int(time.time())}"
                
                # 创建备份目录
                backup_path = self.backup_dir / backup_id
                backup_path.mkdir(exist_ok=True)
                
                # 收集配置文件
                config_files = self._collect_config_files()
                
                if not config_files:
                    raise ValueError("没有找到可备份的配置文件")
                
                # 创建备份
                backup_file = self._create_backup_archive(
                    backup_id, config_files, backup_path, format, compression
                )
                
                # 创建元数据
                metadata = BackupMetadata(
                    id=backup_id,
                    name=name,
                    description=description,
                    backup_type=backup_type,
                    format=format,
                    compression=compression,
                    created_at=datetime.now(),
                    created_by="system",
                    environment="development",  # 应该从当前配置获取
                    profile="default",
                    file_count=len(config_files),
                    total_size=backup_file.stat().st_size if backup_file.exists() else 0,
                    checksum=self._calculate_checksum(backup_file),
                    encrypted=include_encryption,
                    tags=tags or []
                )
                
                # 保存元数据
                self._save_backup_metadata(metadata)
                
                # 如果启用了加密，备份元数据
                if include_encryption:
                    self._encrypt_backup_metadata(metadata, backup_path)
                
                # 清理旧备份
                if self._backup_config.get("cleanup_enabled", True):
                    self._cleanup_old_backups()
                
                logger.info(f"备份已创建: {backup_id}")
                return backup_id
                
            except Exception as e:
                logger.error(f"创建备份失败: {e}")
                raise
    
    def restore_backup(self, 
                      backup_id: str,
                      target_dir: Optional[Path] = None,
                      overwrite: bool = False,
                      validate_only: bool = False) -> RecoveryResult:
        """恢复备份"""
        
        target_dir = target_dir or self.config_dir
        
        try:
            # 获取备份元数据
            metadata = self._get_backup_metadata(backup_id)
            if not metadata:
                return RecoveryResult(
                    success=False,
                    backup_id=backup_id,
                    restored_files=[],
                    errors=[f"备份不存在: {backup_id}"],
                    warnings=[],
                    restored_at=datetime.now()
                )
            
            # 解压备份
            backup_files = self._extract_backup_archive(backup_id, metadata, target_dir)
            
            if validate_only:
                return RecoveryResult(
                    success=True,
                    backup_id=backup_id,
                    restored_files=backup_files,
                    errors=[],
                    warnings=[],
                    restored_at=datetime.now()
                )
            
            # 验证文件
            if not self._validate_restored_files(backup_files, metadata):
                return RecoveryResult(
                    success=False,
                    backup_id=backup_id,
                    restored_files=[],
                    errors=["文件验证失败"],
                    warnings=[],
                    restored_at=datetime.now()
                )
            
            # 移动文件到目标目录
            restored_files = []
            errors = []
            
            for temp_file in backup_files:
                try:
                    target_file = target_dir / temp_file.name
                    
                    if target_file.exists() and not overwrite:
                        errors.append(f"文件已存在: {target_file}")
                        continue
                    
                    # 确保目标目录存在
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 移动文件
                    shutil.move(str(temp_file), str(target_file))
                    restored_files.append(target_file)
                    
                except Exception as e:
                    errors.append(f"恢复文件失败 {temp_file}: {e}")
            
            # 清理临时文件
            self._cleanup_temp_files(backup_id)
            
            result = RecoveryResult(
                success=len(errors) == 0,
                backup_id=backup_id,
                restored_files=restored_files,
                errors=errors,
                warnings=[],
                restored_at=datetime.now()
            )
            
            if result.success:
                logger.info(f"备份恢复成功: {backup_id}")
            else:
                logger.error(f"备份恢复失败: {backup_id}, 错误: {errors}")
            
            return result
            
        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return RecoveryResult(
                success=False,
                backup_id=backup_id,
                restored_files=[],
                errors=[str(e)],
                warnings=[],
                restored_at=datetime.now()
            )
    
    def list_backups(self, 
                    limit: Optional[int] = None,
                    backup_type: Optional[BackupType] = None,
                    tags: Optional[List[str]] = None) -> List[BackupMetadata]:
        """列出备份"""
        
        try:
            backups = []
            
            # 读取所有备份元数据
            for metadata_file in self.backup_dir.glob("*/metadata.json"):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # 转换日期时间
                    data['created_at'] = datetime.fromisoformat(data['created_at'])
                    
                    metadata = BackupMetadata(**data)
                    
                    # 过滤
                    if backup_type and metadata.backup_type != backup_type:
                        continue
                    
                    if tags and not any(tag in metadata.tags for tag in tags):
                        continue
                    
                    backups.append(metadata)
                    
                except Exception as e:
                    logger.warning(f"读取备份元数据失败 {metadata_file}: {e}")
            
            # 按创建时间排序
            backups.sort(key=lambda x: x.created_at, reverse=True)
            
            # 限制数量
            if limit:
                backups = backups[:limit]
            
            return backups
            
        except Exception as e:
            logger.error(f"列出备份失败: {e}")
            return []
    
    def delete_backup(self, backup_id: str) -> bool:
        """删除备份"""
        
        try:
            backup_path = self.backup_dir / backup_id
            
            if not backup_path.exists():
                logger.warning(f"备份不存在: {backup_id}")
                return False
            
            # 删除备份目录
            shutil.rmtree(backup_path)
            
            logger.info(f"备份已删除: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除备份失败: {e}")
            return False
    
    def cleanup_old_backups(self) -> int:
        """清理旧备份"""
        
        try:
            retention_days = self._backup_config.get("retention_days", 30)
            max_backups = self._backup_config.get("max_backups", 50)
            
            # 按创建时间清理
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # 获取所有备份
            backups = self.list_backups()
            
            deleted_count = 0
            
            # 删除超过保留期的备份
            for backup in backups:
                if backup.created_at < cutoff_date:
                    if self.delete_backup(backup.id):
                        deleted_count += 1
            
            # 如果备份数量超过限制，删除最旧的
            if len(backups) > max_backups:
                sorted_backups = sorted(backups, key=lambda x: x.created_at)
                excess_count = len(backups) - max_backups
                
                for backup in sorted_backups[:excess_count]:
                    if self.delete_backup(backup.id):
                        deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"清理了 {deleted_count} 个旧备份")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}")
            return 0
    
    def schedule_backup(self, 
                       name: str,
                       interval_hours: int,
                       description: str = "",
                       backup_type: BackupType = BackupType.SCHEDULED,
                       **kwargs) -> bool:
        """调度自动备份"""
        
        try:
            job_id = f"backup_{name}_{int(time.time())}"
            
            # 设置调度任务
            job = schedule.every(interval_hours).hours.do(
                lambda: self.create_backup(
                    name=f"{name}_auto",
                    description=f"自动备份: {description}",
                    backup_type=backup_type,
                    **kwargs
                )
            )
            
            self._backup_schedules[job_id] = job
            
            logger.info(f"已调度自动备份: {name}, 间隔: {interval_hours}小时")
            return True
            
        except Exception as e:
            logger.error(f"调度自动备份失败: {e}")
            return False
    
    def start_auto_backup(self):
        """启动自动备份"""
        if self._auto_backup_enabled:
            return
        
        self._auto_backup_enabled = True
        
        # 启动调度器线程
        scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("自动备份已启动")
    
    def stop_auto_backup(self):
        """停止自动备份"""
        self._auto_backup_enabled = False
        schedule.clear()
        self._backup_schedules.clear()
        
        logger.info("自动备份已停止")
    
    def verify_backup(self, backup_id: str) -> Tuple[bool, List[str]]:
        """验证备份完整性"""
        
        try:
            metadata = self._get_backup_metadata(backup_id)
            if not metadata:
                return False, [f"备份不存在: {backup_id}"]
            
            errors = []
            
            # 检查备份文件是否存在
            backup_file = self.backup_dir / f"{backup_id}.{metadata.format.value}"
            if not backup_file.exists():
                errors.append(f"备份文件不存在: {backup_file}")
            
            # 验证校验和
            if backup_file.exists():
                current_checksum = self._calculate_checksum(backup_file)
                if current_checksum != metadata.checksum:
                    errors.append("备份文件校验和不匹配")
            
            # 尝试解压验证
            try:
                temp_dir = self.backup_dir / f"verify_{backup_id}"
                temp_dir.mkdir(exist_ok=True)
                
                test_files = self._extract_backup_archive(backup_id, metadata, temp_dir)
                
                if not test_files:
                    errors.append("备份文件解压失败")
                
                # 清理临时文件
                shutil.rmtree(temp_dir)
                
            except Exception as e:
                errors.append(f"备份文件验证失败: {e}")
            
            is_valid = len(errors) == 0
            
            if is_valid:
                logger.info(f"备份验证成功: {backup_id}")
            else:
                logger.warning(f"备份验证失败: {backup_id}, 错误: {errors}")
            
            return is_valid, errors
            
        except Exception as e:
            logger.error(f"验证备份失败: {e}")
            return False, [str(e)]
    
    def export_backup_info(self, backup_id: str, output_file: Path) -> bool:
        """导出备份信息"""
        
        try:
            metadata = self._get_backup_metadata(backup_id)
            if not metadata:
                return False
            
            # 验证备份
            is_valid, errors = self.verify_backup(backup_id)
            
            # 创建导出数据
            export_data = {
                "backup_info": asdict(metadata),
                "validation": {
                    "is_valid": is_valid,
                    "errors": errors
                },
                "exported_at": datetime.now().isoformat()
            }
            
            # 保存到文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"备份信息已导出: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"导出备份信息失败: {e}")
            return False
    
    # ================================
    # 私有方法
    # ================================
    
    def _collect_config_files(self) -> List[Path]:
        """收集配置文件"""
        config_files = []
        
        # 配置文件扩展名
        config_extensions = {'.yaml', '.yml', '.json', '.toml', '.env'}
        
        try:
            # 递归搜索配置文件
            for file_path in self.config_dir.rglob('*'):
                if (file_path.is_file() and 
                    file_path.suffix.lower() in config_extensions and
                    not any(part.startswith('.') for part in file_path.parts)):
                    config_files.append(file_path)
            
        except Exception as e:
            logger.error(f"收集配置文件失败: {e}")
        
        return config_files
    
    def _create_backup_archive(self, 
                             backup_id: str,
                             config_files: List[Path],
                             backup_path: Path,
                             format: BackupFormat,
                             compression: BackupCompression) -> Path:
        """创建备份归档"""
        
        if format == BackupFormat.ZIP:
            return self._create_zip_backup(backup_id, config_files, backup_path, compression)
        elif format in [BackupFormat.TAR, BackupFormat.TAR_GZ]:
            return self._create_tar_backup(backup_id, config_files, backup_path, format, compression)
        else:
            return self._create_json_backup(backup_id, config_files, backup_path)
    
    def _create_zip_backup(self, 
                          backup_id: str,
                          config_files: List[Path],
                          backup_path: Path,
                          compression: BackupCompression) -> Path:
        """创建ZIP备份"""
        
        archive_path = backup_path / f"{backup_id}.zip"
        
        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for config_file in config_files:
                    # 计算相对路径
                    relative_path = config_file.relative_to(self.config_dir)
                    
                    # 添加文件到归档
                    zf.write(config_file, relative_path)
                
                # 添加元数据
                metadata = {
                    "backup_id": backup_id,
                    "created_at": datetime.now().isoformat(),
                    "files": [str(f.relative_to(self.config_dir)) for f in config_files],
                    "format": "zip"
                }
                
                zf.writestr("backup_info.json", json.dumps(metadata, indent=2))
            
            return archive_path
            
        except Exception as e:
            logger.error(f"创建ZIP备份失败: {e}")
            raise
    
    def _create_tar_backup(self, 
                          backup_id: str,
                          config_files: List[Path],
                          backup_path: Path,
                          format: BackupFormat,
                          compression: BackupCompression) -> Path:
        """创建TAR备份"""
        
        archive_name = f"{backup_id}.tar"
        if compression == BackupCompression.GZIP:
            archive_name += ".gz"
        
        archive_path = backup_path / archive_name
        
        try:
            # 确定文件打开模式
            mode = 'w:gz' if compression == BackupCompression.GZIP else 'w'
            
            with tarfile.open(archive_path, mode) as tf:
                for config_file in config_files:
                    # 计算相对路径
                    relative_path = config_file.relative_to(self.config_dir)
                    
                    # 添加文件到归档
                    tf.add(config_file, arcname=str(relative_path))
                
                # 添加元数据
                metadata = {
                    "backup_id": backup_id,
                    "created_at": datetime.now().isoformat(),
                    "files": [str(f.relative_to(self.config_dir)) for f in config_files],
                    "format": "tar"
                }
                
                # 创建元数据文件
                metadata_content = json.dumps(metadata, indent=2)
                metadata_info = tarfile.TarInfo(name="backup_info.json")
                metadata_info.size = len(metadata_content.encode())
                
                tf.addfile(metadata_info, fileobj=type('FileObj', (), {
                    'read': lambda: metadata_content.encode(),
                    'seek': lambda pos: None
                })())
            
            return archive_path
            
        except Exception as e:
            logger.error(f"创建TAR备份失败: {e}")
            raise
    
    def _create_json_backup(self, 
                           backup_id: str,
                           config_files: List[Path],
                           backup_path: Path) -> Path:
        """创建JSON备份"""
        
        backup_data = {}
        
        try:
            for config_file in config_files:
                # 计算相对路径作为键
                relative_path = config_file.relative_to(self.config_dir)
                key = str(relative_path).replace('/', '_').replace('\\', '_')
                
                # 读取文件内容
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    backup_data[key] = {
                        "path": str(relative_path),
                        "content": content,
                        "modified": config_file.stat().st_mtime
                    }
            
            # 保存为JSON文件
            backup_file = backup_path / f"{backup_id}.json"
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            return backup_file
            
        except Exception as e:
            logger.error(f"创建JSON备份失败: {e}")
            raise
    
    def _extract_backup_archive(self, 
                               backup_id: str,
                               metadata: BackupMetadata,
                               target_dir: Path) -> List[Path]:
        """解压备份归档"""
        
        backup_path = self.backup_dir / backup_id
        temp_dir = backup_path / "temp"
        temp_dir.mkdir(exist_ok=True)
        
        try:
            if metadata.format == BackupFormat.ZIP:
                archive_file = self.backup_dir / f"{backup_id}.zip"
                return self._extract_zip_backup(archive_file, temp_dir)
            elif metadata.format in [BackupFormat.TAR, BackupFormat.TAR_GZ]:
                archive_file = self.backup_dir / f"{backup_id}.tar"
                if metadata.compression == BackupCompression.GZIP:
                    archive_file = self.backup_dir / f"{backup_id}.tar.gz"
                return self._extract_tar_backup(archive_file, temp_dir)
            else:
                return self._extract_json_backup(backup_path / f"{backup_id}.json", temp_dir)
                
        except Exception as e:
            logger.error(f"解压备份失败: {e}")
            # 清理临时文件
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            raise
    
    def _extract_zip_backup(self, archive_file: Path, target_dir: Path) -> List[Path]:
        """解压ZIP备份"""
        extracted_files = []
        
        with zipfile.ZipFile(archive_file, 'r') as zf:
            for file_info in zf.infolist():
                if file_info.is_dir():
                    continue
                
                # 提取文件
                target_file = target_dir / file_info.filename
                target_file.parent.mkdir(parents=True, exist_ok=True)
                
                with zf.open(file_info) as source, open(target_file, 'wb') as target:
                    shutil.copyfileobj(source, target)
                
                extracted_files.append(target_file)
        
        return extracted_files
    
    def _extract_tar_backup(self, archive_file: Path, target_dir: Path) -> List[Path]:
        """解压TAR备份"""
        extracted_files = []
        
        with tarfile.open(archive_file, 'r:*') as tf:
            for member in tf.getmembers():
                if member.isdir():
                    continue
                
                # 提取文件
                target_file = target_dir / member.name
                target_file.parent.mkdir(parents=True, exist_ok=True)
                
                tf.extract(member, target_dir)
                extracted_files.append(target_file)
        
        return extracted_files
    
    def _extract_json_backup(self, backup_file: Path, target_dir: Path) -> List[Path]:
        """解压JSON备份"""
        extracted_files = []
        
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        for key, file_data in backup_data.items():
            # 创建文件
            file_path = target_dir / key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_data['content'])
            
            extracted_files.append(file_path)
        
        return extracted_files
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        if not file_path.exists():
            return ""
        
        hash_md5 = hashlib.md5()
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def _save_backup_metadata(self, metadata: BackupMetadata):
        """保存备份元数据"""
        backup_path = self.backup_dir / metadata.id
        
        # 保存元数据文件
        metadata_file = backup_path / "metadata.json"
        
        # 转换datetime为字符串
        metadata_dict = asdict(metadata)
        metadata_dict['created_at'] = metadata.created_at.isoformat()
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata_dict, f, indent=2, ensure_ascii=False, default=str)
    
    def _get_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """获取备份元数据"""
        metadata_file = self.backup_dir / backup_id / "metadata.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 转换日期时间
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            
            return BackupMetadata(**data)
            
        except Exception as e:
            logger.error(f"读取备份元数据失败: {e}")
            return None
    
    def _encrypt_backup_metadata(self, metadata: BackupMetadata, backup_path: Path):
        """加密备份元数据"""
        try:
            encrypted_data = self._encryption.encrypt_config(asdict(metadata))
            
            # 保存加密的元数据
            encrypted_file = backup_path / "metadata.enc"
            with open(encrypted_file, 'w') as f:
                f.write(encrypted_data.model_dump_json())
            
            logger.debug(f"备份元数据已加密: {backup_path}")
            
        except Exception as e:
            logger.error(f"加密备份元数据失败: {e}")
    
    def _validate_restored_files(self, files: List[Path], metadata: BackupMetadata) -> bool:
        """验证恢复的文件"""
        # 这里可以添加具体的验证逻辑
        # 比如检查文件完整性、格式等
        return len(files) > 0
    
    def _cleanup_temp_files(self, backup_id: str):
        """清理临时文件"""
        temp_dir = self.backup_dir / backup_id / "temp"
        
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
    
    def _run_scheduler(self):
        """运行调度器"""
        while self._auto_backup_enabled:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"调度器运行错误: {e}")
                time.sleep(60)
    
    def cleanup(self):
        """清理资源"""
        try:
            # 停止自动备份
            if self._auto_backup_enabled:
                self.stop_auto_backup()
            
            # 清理调度器
            schedule.clear()
            self._backup_schedules.clear()
            
            logger.info("备份管理器已清理")
            
        except Exception as e:
            logger.error(f"清理备份管理器失败: {e}")


# 便捷函数
def create_backup_manager(config_dir: Path, backup_dir: Optional[Path] = None) -> ConfigBackupManager:
    """创建备份管理器"""
    return ConfigBackupManager(config_dir, backup_dir)


def quick_backup(config_dir: Path, name: str = "quick_backup") -> str:
    """快速备份"""
    manager = ConfigBackupManager(config_dir)
    return manager.create_backup(name, "快速备份", BackupType.MANUAL)


def restore_from_backup(config_dir: Path, backup_id: str) -> bool:
    """从备份恢复"""
    manager = ConfigBackupManager(config_dir)
    result = manager.restore_backup(backup_id)
    return result.success