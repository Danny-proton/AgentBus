"""
AgentBus 配置文件管理系统
Configuration File Management System for AgentBus

提供配置文件的创建、编辑、验证、模板管理等功能。
"""

import os
import json
import yaml
import shutil
import difflib
import hashlib
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple, Callable, Set
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import re
import jsonschema
from jsonschema import ValidationError, Draft7Validator

from .config_types import ConfigFormat, ConfigScope, ConfigSchema, ValidationResult
from .security import ConfigValidator
from .env_loader import EnvironmentLoader


logger = logging.getLogger(__name__)


class FileOperation(str, Enum):
    """文件操作类型"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"
    COPY = "copy"
    VALIDATE = "validate"
    MERGE = "merge"


class ValidationLevel(str, Enum):
    """验证级别"""
    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"
    DISABLED = "disabled"


@dataclass
class FileChange:
    """文件变更记录"""
    operation: FileOperation
    file_path: Path
    timestamp: float
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    changes: Optional[List[str]] = None
    user: Optional[str] = None
    reason: Optional[str] = None
    checksum_before: Optional[str] = None
    checksum_after: Optional[str] = None


@dataclass
class TemplateInfo:
    """配置模板信息"""
    name: str
    description: str
    version: str
    scope: ConfigScope
    variables: Dict[str, Any]
    schema: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class FileValidationResult:
    """文件验证结果"""
    file_path: Path
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    schema_compliant: bool
    content_hash: str
    size: int
    last_modified: datetime


class ConfigFileManager:
    """配置文件管理器"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self._lock = threading.RLock()
        self._change_history: List[FileChange] = []
        self._templates: Dict[str, TemplateInfo] = {}
        self._schemas: Dict[str, ConfigSchema] = {}
        self._validator = ConfigValidator()
        self._env_loader = EnvironmentLoader()
        
        # 验证配置
        self._validation_config = {
            "level": ValidationLevel.MODERATE,
            "auto_validate": True,
            "check_permissions": True,
            "backup_on_change": True,
            "max_file_size": 10 * 1024 * 1024,  # 10MB
            "allowed_extensions": {'.yaml', '.yml', '.json', '.toml', '.env'},
            "forbidden_patterns": [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']',
                r'api_key\s*=\s*["\'][^"\']+["\']'
            ]
        }
        
        # 创建必要目录
        self._create_directories()
        
        # 加载模板和模式
        self._load_templates()
        self._load_schemas()
    
    def _create_directories(self):
        """创建必要的目录"""
        directories = [
            self.config_dir / "templates",
            self.config_dir / "schemas",
            self.config_dir / "backup",
            self.config_dir / "temp",
            self.config_dir / "exports"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_templates(self):
        """加载配置模板"""
        templates_dir = self.config_dir / "templates"
        
        if templates_dir.exists():
            for template_file in templates_dir.glob("*.yaml"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        template_data = yaml.safe_load(f)
                    
                    template = TemplateInfo(
                        name=template_data.get('name', template_file.stem),
                        description=template_data.get('description', ''),
                        version=template_data.get('version', '1.0.0'),
                        scope=ConfigScope(template_data.get('scope', 'application')),
                        variables=template_data.get('variables', {}),
                        schema=template_data.get('schema'),
                        tags=template_data.get('tags', [])
                    )
                    
                    self._templates[template.name] = template
                    
                except Exception as e:
                    logger.error(f"加载模板失败 {template_file}: {e}")
    
    def _load_schemas(self):
        """加载配置模式"""
        schemas_dir = self.config_dir / "schemas"
        
        if schemas_dir.exists():
            for schema_file in schemas_dir.glob("*.json"):
                try:
                    with open(schema_file, 'r', encoding='utf-8') as f:
                        schema_data = json.load(f)
                    
                    schema = ConfigSchema(
                        name=schema_data.get('name', schema_file.stem),
                        version=schema_data.get('version', '1.0'),
                        schema=schema_data.get('schema', {}),
                        required=schema_data.get('required', []),
                        defaults=schema_data.get('defaults', {}),
                        validators=schema_data.get('validators', {})
                    )
                    
                    self._schemas[schema.name] = schema
                    
                except Exception as e:
                    logger.error(f"加载模式失败 {schema_file}: {e}")
    
    def create_file(self, 
                   file_path: Union[str, Path],
                   content: str,
                   format: ConfigFormat = ConfigFormat.YAML,
                   validate: bool = True,
                   backup: bool = True,
                   user: Optional[str] = None) -> Tuple[bool, List[str]]:
        """创建配置文件"""
        
        file_path = Path(file_path)
        errors = []
        
        with self._lock:
            try:
                # 检查文件是否存在
                if file_path.exists():
                    errors.append(f"文件已存在: {file_path}")
                    return False, errors
                
                # 验证文件名
                if not self._validate_file_extension(file_path):
                    errors.append(f"不支持的文件扩展名: {file_path.suffix}")
                    return False, errors
                
                # 创建目录
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 验证内容
                if validate:
                    validation_result = self.validate_content(content, format)
                    if not validation_result.is_valid:
                        errors.extend(validation_result.errors)
                        return False, errors
                
                # 备份现有文件
                if backup and file_path.exists():
                    self._create_backup(file_path)
                
                # 写入文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # 记录变更
                self._record_change(
                    FileOperation.CREATE,
                    file_path,
                    new_content=content,
                    user=user
                )
                
                logger.info(f"配置文件已创建: {file_path}")
                return True, []
                
            except Exception as e:
                error_msg = f"创建配置文件失败: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                return False, errors
    
    def update_file(self, 
                   file_path: Union[str, Path],
                   content: str,
                   format: ConfigFormat = ConfigFormat.YAML,
                   validate: bool = True,
                   backup: bool = True,
                   user: Optional[str] = None,
                   reason: Optional[str] = None) -> Tuple[bool, List[str]]:
        """更新配置文件"""
        
        file_path = Path(file_path)
        errors = []
        
        with self._lock:
            try:
                # 检查文件是否存在
                if not file_path.exists():
                    errors.append(f"文件不存在: {file_path}")
                    return False, errors
                
                # 读取旧内容
                old_content = ""
                if backup:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        old_content = f.read()
                
                # 验证新内容
                if validate:
                    validation_result = self.validate_content(content, format)
                    if not validation_result.is_valid:
                        errors.extend(validation_result.errors)
                        return False, errors
                
                # 备份现有文件
                if backup:
                    self._create_backup(file_path)
                
                # 写入新内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # 记录变更
                changes = self._generate_diff(old_content, content)
                self._record_change(
                    FileOperation.UPDATE,
                    file_path,
                    old_content=old_content,
                    new_content=content,
                    changes=changes,
                    user=user,
                    reason=reason
                )
                
                logger.info(f"配置文件已更新: {file_path}")
                return True, []
                
            except Exception as e:
                error_msg = f"更新配置文件失败: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                return False, errors
    
    def delete_file(self, 
                   file_path: Union[str, Path],
                   backup: bool = True,
                   user: Optional[str] = None,
                   reason: Optional[str] = None) -> Tuple[bool, List[str]]:
        """删除配置文件"""
        
        file_path = Path(file_path)
        errors = []
        
        with self._lock:
            try:
                # 检查文件是否存在
                if not file_path.exists():
                    errors.append(f"文件不存在: {file_path}")
                    return False, errors
                
                # 读取文件内容（用于备份）
                old_content = ""
                if backup:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        old_content = f.read()
                    
                    # 创建备份
                    self._create_backup(file_path)
                
                # 删除文件
                file_path.unlink()
                
                # 记录变更
                self._record_change(
                    FileOperation.DELETE,
                    file_path,
                    old_content=old_content,
                    user=user,
                    reason=reason
                )
                
                logger.info(f"配置文件已删除: {file_path}")
                return True, []
                
            except Exception as e:
                error_msg = f"删除配置文件失败: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                return False, errors
    
    def move_file(self, 
                 source_path: Union[str, Path],
                 target_path: Union[str, Path],
                 backup: bool = True,
                 user: Optional[str] = None,
                 reason: Optional[str] = None) -> Tuple[bool, List[str]]:
        """移动配置文件"""
        
        source_path = Path(source_path)
        target_path = Path(target_path)
        errors = []
        
        with self._lock:
            try:
                # 检查源文件是否存在
                if not source_path.exists():
                    errors.append(f"源文件不存在: {source_path}")
                    return False, errors
                
                # 检查目标文件是否已存在
                if target_path.exists():
                    errors.append(f"目标文件已存在: {target_path}")
                    return False, errors
                
                # 创建目标目录
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 读取文件内容
                with open(source_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 备份源文件
                if backup:
                    self._create_backup(source_path)
                
                # 移动文件
                shutil.move(str(source_path), str(target_path))
                
                # 记录变更
                self._record_change(
                    FileOperation.MOVE,
                    source_path,
                    new_content=str(target_path),
                    user=user,
                    reason=reason
                )
                
                logger.info(f"配置文件已移动: {source_path} -> {target_path}")
                return True, []
                
            except Exception as e:
                error_msg = f"移动配置文件失败: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                return False, errors
    
    def copy_file(self, 
                 source_path: Union[str, Path],
                 target_path: Union[str, Path],
                 user: Optional[str] = None) -> Tuple[bool, List[str]]:
        """复制配置文件"""
        
        source_path = Path(source_path)
        target_path = Path(target_path)
        errors = []
        
        with self._lock:
            try:
                # 检查源文件是否存在
                if not source_path.exists():
                    errors.append(f"源文件不存在: {source_path}")
                    return False, errors
                
                # 创建目标目录
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 复制文件
                shutil.copy2(str(source_path), str(target_path))
                
                # 记录变更
                self._record_change(
                    FileOperation.COPY,
                    source_path,
                    new_content=str(target_path),
                    user=user
                )
                
                logger.info(f"配置文件已复制: {source_path} -> {target_path}")
                return True, []
                
            except Exception as e:
                error_msg = f"复制配置文件失败: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                return False, errors
    
    def validate_file(self, file_path: Union[str, Path]) -> FileValidationResult:
        """验证配置文件"""
        
        file_path = Path(file_path)
        
        try:
            # 检查文件是否存在
            if not file_path.exists():
                return FileValidationResult(
                    file_path=file_path,
                    is_valid=False,
                    errors=[f"文件不存在: {file_path}"],
                    warnings=[],
                    suggestions=[],
                    schema_compliant=False,
                    content_hash="",
                    size=0,
                    last_modified=datetime.now()
                )
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 获取文件信息
            stat = file_path.stat()
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # 确定文件格式
            format = self._detect_format(file_path)
            
            # 验证内容
            validation_result = self.validate_content(content, format)
            
            # 检查文件大小
            warnings = []
            if stat.st_size > self._validation_config.get("max_file_size", 10 * 1024 * 1024):
                warnings.append(f"文件大小超过限制: {stat.st_size} 字节")
            
            # 检查权限
            if self._validation_config.get("check_permissions", True):
                if not os.access(file_path, os.R_OK):
                    warnings.append("文件不可读")
                if not os.access(file_path, os.W_OK):
                    warnings.append("文件不可写")
            
            return FileValidationResult(
                file_path=file_path,
                is_valid=validation_result.is_valid and len(validation_result.errors) == 0,
                errors=validation_result.errors,
                warnings=warnings + validation_result.warnings,
                suggestions=validation_result.suggestions,
                schema_compliant=self._check_schema_compliance(content, format),
                content_hash=content_hash,
                size=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime)
            )
            
        except Exception as e:
            return FileValidationResult(
                file_path=file_path,
                is_valid=False,
                errors=[f"验证文件失败: {e}"],
                warnings=[],
                suggestions=[],
                schema_compliant=False,
                content_hash="",
                size=0,
                last_modified=datetime.now()
            )
    
    def validate_content(self, content: str, format: ConfigFormat) -> ValidationResult:
        """验证配置内容"""
        
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # 解析内容
            parsed_data = self._parse_content(content, format)
            
            # 基本验证
            if not isinstance(parsed_data, dict):
                errors.append("配置内容必须是字典格式")
                return ValidationResult(False, errors, warnings, suggestions)
            
            # 验证级别
            level = ValidationLevel(self._validation_config.get("level", "moderate"))
            
            if level != ValidationLevel.DISABLED:
                # 运行验证器
                result = self._validator.validate_config(parsed_data)
                errors.extend(result.errors)
                warnings.extend(result.warnings)
                suggestions.extend(result.suggestions)
            
            if level == ValidationLevel.STRICT:
                # 严格验证
                self._strict_validation(parsed_data, errors, warnings)
            
            # 检查敏感信息
            self._check_sensitive_info(content, warnings)
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
            
        except Exception as e:
            errors.append(f"内容验证失败: {e}")
            return ValidationResult(False, errors, warnings, suggestions)
    
    def create_template(self, 
                      name: str,
                      description: str,
                      scope: ConfigScope,
                      variables: Dict[str, Any],
                      content: str,
                      schema: Optional[Dict[str, Any]] = None,
                      tags: Optional[List[str]] = None) -> bool:
        """创建配置模板"""
        
        try:
            template = TemplateInfo(
                name=name,
                description=description,
                version="1.0.0",
                scope=scope,
                variables=variables,
                schema=schema,
                tags=tags or []
            )
            
            # 保存模板文件
            template_file = self.config_dir / "templates" / f"{name}.yaml"
            
            template_data = {
                "name": name,
                "description": description,
                "version": "1.0.0",
                "scope": scope.value,
                "variables": variables,
                "content": content,
                "schema": schema,
                "tags": tags or []
            }
            
            with open(template_file, 'w', encoding='utf-8') as f:
                yaml.dump(template_data, f, default_flow_style=False, allow_unicode=True)
            
            # 添加到内存
            self._templates[name] = template
            
            logger.info(f"配置模板已创建: {name}")
            return True
            
        except Exception as e:
            logger.error(f"创建配置模板失败: {e}")
            return False
    
    def generate_from_template(self, 
                           template_name: str,
                           variables: Dict[str, Any],
                           output_path: Union[str, Path],
                           validate: bool = True) -> Tuple[bool, List[str]]:
        """从模板生成配置"""
        
        errors = []
        
        try:
            # 获取模板
            template = self._templates.get(template_name)
            if not template:
                errors.append(f"模板不存在: {template_name}")
                return False, errors
            
            # 变量替换
            content = self._substitute_variables(template.variables | variables)
            
            # 验证生成的内容
            if validate:
                format = self._detect_format_from_path(output_path)
                validation_result = self.validate_content(content, format)
                if not validation_result.is_valid:
                    errors.extend(validation_result.errors)
                    return False, errors
            
            # 创建文件
            return self.create_file(output_path, content, validate=validate)
            
        except Exception as e:
            error_msg = f"从模板生成配置失败: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return False, errors
    
    def merge_files(self, 
                   source_paths: List[Union[str, Path]],
                   target_path: Union[str, Path],
                   strategy: str = "overwrite",
                   validate: bool = True) -> Tuple[bool, List[str]]:
        """合并配置文件"""
        
        source_paths = [Path(p) for p in source_paths]
        target_path = Path(target_path)
        errors = []
        
        try:
            merged_data = {}
            
            # 读取并合并所有源文件
            for source_path in source_paths:
                if not source_path.exists():
                    errors.append(f"源文件不存在: {source_path}")
                    continue
                
                format = self._detect_format(source_path)
                
                with open(source_path, 'r', encoding='utf-8') as f:
                    if format == ConfigFormat.JSON:
                        source_data = json.load(f)
                    elif format in [ConfigFormat.YAML, ConfigFormat.TOML]:
                        source_data = yaml.safe_load(f)
                    else:
                        errors.append(f"不支持的文件格式: {format}")
                        continue
                
                # 合并数据
                if strategy == "overwrite":
                    merged_data.update(source_data)
                elif strategy == "merge":
                    merged_data = self._deep_merge(merged_data, source_data)
            
            if errors and len(errors) == len(source_paths):
                return False, errors
            
            # 序列化为目标格式
            format = self._detect_format_from_path(target_path)
            content = self._serialize_content(merged_data, format)
            
            # 创建目标文件
            return self.create_file(target_path, content, validate=validate)
            
        except Exception as e:
            error_msg = f"合并配置文件失败: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return False, errors
    
    def compare_files(self, 
                    file1_path: Union[str, Path],
                    file2_path: Union[str, Path]) -> Tuple[bool, List[str]]:
        """比较两个配置文件"""
        
        file1_path = Path(file1_path)
        file2_path = Path(file2_path)
        errors = []
        
        try:
            # 检查文件是否存在
            if not file1_path.exists():
                errors.append(f"文件1不存在: {file1_path}")
                return False, errors
            
            if not file2_path.exists():
                errors.append(f"文件2不存在: {file2_path}")
                return False, errors
            
            # 读取文件内容
            with open(file1_path, 'r', encoding='utf-8') as f:
                content1 = f.read()
            
            with open(file2_path, 'r', encoding='utf-8') as f:
                content2 = f.read()
            
            # 生成差异
            diff = list(difflib.unified_diff(
                content1.splitlines(keepends=True),
                content2.splitlines(keepends=True),
                fromfile=str(file1_path),
                tofile=str(file2_path),
                lineterm=''
            ))
            
            if not diff:
                print("文件内容相同")
            else:
                print("文件差异:")
                for line in diff:
                    print(line.rstrip())
            
            return True, []
            
        except Exception as e:
            error_msg = f"比较配置文件失败: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return False, errors
    
    def list_files(self, pattern: Optional[str] = None, recursive: bool = True) -> List[Path]:
        """列出配置文件"""
        
        files = []
        
        try:
            if pattern:
                # 使用模式匹配
                if recursive:
                    files = list(self.config_dir.rglob(pattern))
                else:
                    files = list(self.config_dir.glob(pattern))
            else:
                # 默认所有配置文件
                extensions = self._validation_config.get("allowed_extensions", {'.yaml', '.yml', '.json', '.toml'})
                
                if recursive:
                    for ext in extensions:
                        files.extend(self.config_dir.rglob(f"*{ext}"))
                else:
                    for ext in extensions:
                        files.extend(self.config_dir.glob(f"*{ext}"))
            
            # 过滤只返回文件
            files = [f for f in files if f.is_file()]
            
            return sorted(files)
            
        except Exception as e:
            logger.error(f"列出配置文件失败: {e}")
            return []
    
    def get_file_info(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        
        file_path = Path(file_path)
        
        try:
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "path": str(file_path),
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "created": datetime.fromtimestamp(stat.st_ctime),
                "hash": hashlib.md5(content.encode()).hexdigest(),
                "format": self._detect_format(file_path).value,
                "readable": os.access(file_path, os.R_OK),
                "writable": os.access(file_path, os.W_OK)
            }
            
        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return None
    
    def get_change_history(self, limit: Optional[int] = None) -> List[FileChange]:
        """获取变更历史"""
        
        history = sorted(self._change_history, key=lambda x: x.timestamp, reverse=True)
        
        if limit:
            history = history[:limit]
        
        return history
    
    def export_config(self, 
                     output_path: Union[str, Path],
                     files: Optional[List[Union[str, Path]]] = None,
                     format: ConfigFormat = ConfigFormat.ZIP) -> bool:
        """导出配置"""
        
        output_path = Path(output_path)
        
        try:
            # 获取要导出的文件
            if files is None:
                files = self.list_files()
            else:
                files = [Path(f) for f in files]
            
            if not files:
                logger.warning("没有找到要导出的文件")
                return False
            
            if format == ConfigFormat.ZIP:
                return self._export_as_zip(files, output_path)
            elif format == ConfigFormat.TAR:
                return self._export_as_tar(files, output_path)
            else:
                return self._export_as_single_file(files, output_path, format)
                
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return False
    
    def import_config(self, 
                     input_path: Union[str, Path],
                     target_dir: Optional[Path] = None,
                     validate: bool = True,
                     backup: bool = True) -> Tuple[bool, List[str]]:
        """导入配置"""
        
        input_path = Path(input_path)
        target_dir = target_dir or self.config_dir
        errors = []
        
        try:
            if not input_path.exists():
                errors.append(f"导入文件不存在: {input_path}")
                return False, errors
            
            if input_path.is_file():
                # 单文件导入
                if input_path.suffix.lower() in ['.zip', '.tar', '.tar.gz']:
                    return self._import_archive(input_path, target_dir, validate, backup)
                else:
                    return self._import_single_file(input_path, target_dir, validate, backup)
            else:
                errors.append(f"不支持的导入路径类型: {input_path}")
                return False, errors
                
        except Exception as e:
            error_msg = f"导入配置失败: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return False, errors
    
    # ================================
    # 私有方法
    # ================================
    
    def _validate_file_extension(self, file_path: Path) -> bool:
        """验证文件扩展名"""
        allowed_extensions = self._validation_config.get("allowed_extensions", set())
        return file_path.suffix.lower() in allowed_extensions
    
    def _detect_format(self, file_path: Path) -> ConfigFormat:
        """检测文件格式"""
        suffix = file_path.suffix.lower()
        
        if suffix in ['.yaml', '.yml']:
            return ConfigFormat.YAML
        elif suffix == '.json':
            return ConfigFormat.JSON
        elif suffix == '.toml':
            return ConfigFormat.TOML
        elif suffix == '.env':
            return ConfigFormat.ENV
        else:
            return ConfigFormat.YAML  # 默认格式
    
    def _detect_format_from_path(self, file_path: Union[str, Path]) -> ConfigFormat:
        """从文件路径检测格式"""
        return self._detect_format(Path(file_path))
    
    def _parse_content(self, content: str, format: ConfigFormat) -> Any:
        """解析配置内容"""
        if format == ConfigFormat.JSON:
            return json.loads(content)
        elif format in [ConfigFormat.YAML, ConfigFormat.TOML]:
            return yaml.safe_load(content)
        elif format == ConfigFormat.ENV:
            # 简单的环境变量解析
            result = {}
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    result[key.strip()] = value.strip().strip('"\'')
            return result
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    def _serialize_content(self, data: Any, format: ConfigFormat) -> str:
        """序列化配置内容"""
        if format == ConfigFormat.JSON:
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif format in [ConfigFormat.YAML, ConfigFormat.TOML]:
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)
        elif format == ConfigFormat.ENV:
            lines = []
            for key, value in data.items():
                lines.append(f"{key}={value}")
            return '\n'.join(lines)
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    def _strict_validation(self, data: Dict[str, Any], errors: List[str], warnings: List[str]):
        """严格验证"""
        # 检查必需字段
        required_fields = ['app_name', 'environment']
        for field in required_fields:
            if field not in data:
                errors.append(f"缺少必需字段: {field}")
        
        # 检查数据类型
        type_checks = {
            'port': int,
            'debug': bool,
            'workers': int
        }
        
        for field, expected_type in type_checks.items():
            if field in data and not isinstance(data[field], expected_type):
                errors.append(f"字段 {field} 类型错误，期望 {expected_type.__name__}")
    
    def _check_sensitive_info(self, content: str, warnings: List[str]):
        """检查敏感信息"""
        forbidden_patterns = self._validation_config.get("forbidden_patterns", [])
        
        for pattern in forbidden_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append("可能包含敏感信息，请检查")
                break
    
    def _check_schema_compliance(self, content: str, format: ConfigFormat) -> bool:
        """检查模式符合性"""
        try:
            data = self._parse_content(content, format)
            
            # 这里可以添加具体的模式验证逻辑
            # 比如使用JSON Schema等
            
            return True
        except:
            return False
    
    def _substitute_variables(self, variables: Dict[str, Any]) -> str:
        """变量替换"""
        # 简单的变量替换逻辑
        result = ""
        
        for key, value in variables.items():
            result += f"{key}={value}\n"
        
        return result
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并字典"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _generate_diff(self, old_content: str, new_content: str) -> List[str]:
        """生成差异"""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile="old",
            tofile="new",
            lineterm=''
        ))
        
        return diff
    
    def _record_change(self, 
                      operation: FileOperation,
                      file_path: Path,
                      old_content: Optional[str] = None,
                      new_content: Optional[str] = None,
                      changes: Optional[List[str]] = None,
                      user: Optional[str] = None,
                      reason: Optional[str] = None):
        """记录变更"""
        
        change = FileChange(
            operation=operation,
            file_path=file_path,
            timestamp=time.time(),
            old_content=old_content,
            new_content=new_content,
            changes=changes,
            user=user,
            reason=reason,
            checksum_before=hashlib.md5(old_content.encode()).hexdigest() if old_content else None,
            checksum_after=hashlib.md5(new_content.encode()).hexdigest() if new_content else None
        )
        
        self._change_history.append(change)
        
        # 限制历史记录数量
        max_history = 1000
        if len(self._change_history) > max_history:
            self._change_history = self._change_history[-max_history:]
    
    def _create_backup(self, file_path: Path):
        """创建备份"""
        try:
            backup_dir = self.config_dir / "backup"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
            backup_path = backup_dir / backup_name
            
            shutil.copy2(file_path, backup_path)
            
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
    
    def _export_as_zip(self, files: List[Path], output_path: Path) -> bool:
        """导出为ZIP文件"""
        import zipfile
        
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in files:
                    if file_path.exists():
                        arcname = file_path.relative_to(self.config_dir)
                        zf.write(file_path, arcname)
            
            return True
            
        except Exception as e:
            logger.error(f"导出ZIP失败: {e}")
            return False
    
    def _export_as_tar(self, files: List[Path], output_path: Path) -> bool:
        """导出为TAR文件"""
        import tarfile
        
        try:
            with tarfile.open(output_path, 'w:gz') as tf:
                for file_path in files:
                    if file_path.exists():
                        arcname = file_path.relative_to(self.config_dir)
                        tf.add(file_path, arcname=arcname)
            
            return True
            
        except Exception as e:
            logger.error(f"导出TAR失败: {e}")
            return False
    
    def _export_as_single_file(self, files: List[Path], output_path: Path, format: ConfigFormat) -> bool:
        """导出为单个文件"""
        try:
            merged_data = {}
            
            for file_path in files:
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    data = self._parse_content(content, self._detect_format(file_path))
                    merged_data[file_path.stem] = data
            
            output_content = self._serialize_content(merged_data, format)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)
            
            return True
            
        except Exception as e:
            logger.error(f"导出单个文件失败: {e}")
            return False
    
    def _import_single_file(self, 
                          input_path: Path,
                          target_dir: Path,
                          validate: bool,
                          backup: bool) -> Tuple[bool, List[str]]:
        """导入单个文件"""
        errors = []
        
        try:
            target_path = target_dir / input_path.name
            
            # 读取并验证内容
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            format = self._detect_format(input_path)
            
            if validate:
                validation_result = self.validate_content(content, format)
                if not validation_result.is_valid:
                    errors.extend(validation_result.errors)
                    return False, errors
            
            # 创建文件
            return self.create_file(target_path, content, format=format, validate=False, backup=backup)
            
        except Exception as e:
            error_msg = f"导入单个文件失败: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return False, errors
    
    def _import_archive(self, 
                      input_path: Path,
                      target_dir: Path,
                      validate: bool,
                      backup: bool) -> Tuple[bool, List[str]]:
        """导入归档文件"""
        errors = []
        
        try:
            if input_path.suffix.lower() == '.zip':
                import zipfile
                with zipfile.ZipFile(input_path, 'r') as zf:
                    for file_info in zf.infolist():
                        if file_info.is_dir():
                            continue
                        
                        # 提取文件内容
                        content = zf.read(file_info).decode('utf-8')
                        
                        # 确定目标路径
                        target_path = target_dir / file_info.filename
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # 验证内容
                        if validate:
                            format = self._detect_format_from_path(target_path)
                            validation_result = self.validate_content(content, format)
                            if not validation_result.is_valid:
                                errors.append(f"文件 {file_info.filename} 验证失败: {validation_result.errors}")
                                continue
                        
                        # 创建文件
                        self.create_file(target_path, content, validate=False, backup=backup)
            
            elif input_path.suffix.lower() in ['.tar', '.tar.gz']:
                import tarfile
                with tarfile.open(input_path, 'r:*') as tf:
                    for member in tf.getmembers():
                        if member.isdir():
                            continue
                        
                        # 提取文件内容
                        content = tf.extractfile(member).read().decode('utf-8')
                        
                        # 确定目标路径
                        target_path = target_dir / member.name
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # 验证内容
                        if validate:
                            format = self._detect_format_from_path(target_path)
                            validation_result = self.validate_content(content, format)
                            if not validation_result.is_valid:
                                errors.append(f"文件 {member.name} 验证失败: {validation_result.errors}")
                                continue
                        
                        # 创建文件
                        self.create_file(target_path, content, validate=False, backup=backup)
            
            return len(errors) == 0, errors
            
        except Exception as e:
            error_msg = f"导入归档失败: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            return False, errors
    
    def cleanup(self):
        """清理资源"""
        try:
            # 清理临时文件
            temp_dir = self.config_dir / "temp"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                temp_dir.mkdir(exist_ok=True)
            
            # 限制变更历史记录数量
            max_history = 1000
            if len(self._change_history) > max_history:
                self._change_history = self._change_history[-max_history:]
            
            logger.info("文件管理器已清理")
            
        except Exception as e:
            logger.error(f"清理文件管理器失败: {e}")
    
    # ================================
    # 便利方法
    # ================================
    
    def read_config_file(self, file_name: str) -> Dict[str, Any]:
        """读取配置文件"""
        file_path = self.config_dir / file_name
        
        if not file_path.exists():
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            format = self._detect_format(file_path)
            return self._parse_content(content, format)
            
        except Exception as e:
            logger.error(f"读取配置文件失败 {file_name}: {e}")
            return {}
    
    def write_config_file(self, file_name: str, data: Dict[str, Any], overwrite: bool = False) -> bool:
        """写入配置文件"""
        file_path = self.config_dir / file_name
        
        try:
            if file_path.exists() and not overwrite:
                logger.error(f"文件已存在: {file_name}")
                return False
            
            format = self._detect_format_from_path(file_path)
            content = self._serialize_content(data, format)
            
            return self.create_file(file_path, content, validate=True, backup=True)[0]
            
        except Exception as e:
            logger.error(f"写入配置文件失败 {file_name}: {e}")
            return False
    
    def delete_config_file(self, file_name: str) -> bool:
        """删除配置文件"""
        file_path = self.config_dir / file_name
        
        if not file_path.exists():
            return False
        
        try:
            return self.delete_file(file_path, backup=True)[0]
            
        except Exception as e:
            logger.error(f"删除配置文件失败 {file_name}: {e}")
            return False
    
    def list_config_files(self) -> List[str]:
        """列出所有配置文件"""
        files = self.list_files()
        return [str(f.relative_to(self.config_dir)) for f in files]
    
    def create_template(self, template_name: str, template_data: Dict[str, Any]) -> bool:
        """创建配置模板"""
        try:
            content = template_data.get('content', '')
            description = template_data.get('description', '')
            scope = ConfigScope(template_data.get('scope', 'application'))
            variables = template_data.get('variables', {})
            schema = template_data.get('schema')
            tags = template_data.get('tags', [])
            
            return self._create_template(
                name=template_name,
                description=description,
                scope=scope,
                variables=variables,
                content=content,
                schema=schema,
                tags=tags
            )
            
        except Exception as e:
            logger.error(f"创建模板失败 {template_name}: {e}")
            return False
    
    def _create_template(self, 
                      name: str,
                      description: str,
                      scope: ConfigScope,
                      variables: Dict[str, Any],
                      content: str,
                      schema: Optional[Dict[str, Any]] = None,
                      tags: Optional[List[str]] = None) -> bool:
    
    def apply_template(self, template_name: str, output_file: str, variables: Dict[str, str] = None) -> bool:
        """应用配置模板"""
        try:
            output_path = self.config_dir / output_file
            success, errors = self.generate_from_template(template_name, variables or {}, output_path)
            
            if not success:
                logger.error(f"应用模板失败: {errors}")
            
            return success
            
        except Exception as e:
            logger.error(f"应用模板失败 {template_name}: {e}")
            return False


# 便捷函数
def create_file_manager(config_dir: Path) -> ConfigFileManager:
    """创建配置文件管理器"""
    return ConfigFileManager(config_dir)


def quick_validate(file_path: Path) -> bool:
    """快速验证文件"""
    manager = ConfigFileManager(file_path.parent)
    result = manager.validate_file(file_path)
    return result.is_valid


def create_from_template(template_name: str, variables: Dict[str, Any], output_path: Path) -> bool:
    """从模板快速创建"""
    manager = ConfigFileManager(output_path.parent)
    success, errors = manager.generate_from_template(template_name, variables, output_path)
    return success