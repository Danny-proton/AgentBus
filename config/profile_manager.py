"""
AgentBus 配置文件管理器
Configuration Profile Manager for AgentBus

管理不同环境和配置文件的生命周期，支持配置文件切换、继承、验证等功能。
"""

import os
import json
import yaml
import shutil
import copy
import hashlib
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
from jinja2 import Template, Environment, FileSystemLoader

from .config_types import (
    EnvironmentType, ConfigProfile, ConfigSection, ValidationResult,
    ConfigFormat, ConfigSource, ConfigSchema
)
from .env_loader import EnvironmentLoader


logger = logging.getLogger(__name__)


class ProfileStatus(Enum):
    """配置状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"
    DEPRECATED = "deprecated"


class ProfileValidation(Enum):
    """配置验证状态"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    UNKNOWN = "unknown"


@dataclass
class ProfileMetadata:
    """配置元数据"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_validated: Optional[datetime] = None
    validation_status: ProfileValidation = ProfileValidation.UNKNOWN
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)


@dataclass
class ProfileTemplate:
    """配置模板"""
    name: str
    description: str
    template: str
    variables: Dict[str, Any] = field(default_factory=dict)
    required_variables: List[str] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    schema: Optional[ConfigSchema] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ProfileChange:
    """配置变更记录"""
    timestamp: datetime
    profile_name: str
    action: str  # create, update, delete, activate, deactivate
    field_path: str
    old_value: Any
    new_value: Any
    user: Optional[str] = None
    reason: Optional[str] = None


class ProfileManager:
    """配置文件管理器"""
    
    def __init__(self, profiles_dir: Optional[Union[str, Path]] = None):
        self.profiles_dir = Path(profiles_dir) if profiles_dir else Path("./config/profiles")
        self._lock = threading.RLock()
        
        # 配置存储
        self._profiles: Dict[str, ConfigProfile] = {}
        self._metadata: Dict[str, ProfileMetadata] = {}
        self._templates: Dict[str, ProfileTemplate] = {}
        self._schemas: Dict[str, ConfigSchema] = {}
        
        # 当前活动配置
        self._active_profile: Optional[str] = None
        self._profile_stack: List[str] = []
        
        # 历史记录
        self._changes: List[ProfileChange] = []
        
        # 环境变量加载器
        self._env_loader = EnvironmentLoader()
        
        # Jinja2环境（用于模板渲染）
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(self.profiles_dir)),
            autoescape=True
        )
        
        # 初始化
        self._setup_directories()
        self._load_builtin_templates()
        self._discover_profiles()
    
    def _setup_directories(self):
        """设置目录结构"""
        directories = [
            self.profiles_dir,
            self.profiles_dir / "templates",
            self.profiles_dir / "schemas",
            self.profiles_dir / "backups",
            self.profiles_dir / "exports",
            self.profiles_dir / "imports"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_builtin_templates(self):
        """加载内置模板"""
        # 开发环境模板
        self.register_template(ProfileTemplate(
            name="development",
            description="开发环境配置模板",
            template="""
# AgentBus 开发环境配置
app:
  name: "AgentBus"
  version: "{{ app_version }}"
  debug: true
  environment: "development"

server:
  host: "127.0.0.1"
  port: 8000
  workers: 1
  reload: true

logging:
  level: "DEBUG"
  format: "detailed"
  console: true
  file: true

database:
  url: "{{ database_url or 'sqlite:///./data/dev.db' }}"
  echo: true
  pool_size: 5

redis:
  enabled: false

security:
  secret_key: "{{ secret_key or 'dev-secret-key-change-in-production' }}"
  jwt_secret: "{{ jwt_secret or 'dev-jwt-secret' }}"
  encryption_enabled: false

monitoring:
  enabled: false
  metrics_enabled: false

features:
  hitl_enabled: false
  plugins_enabled: true
  skills_enabled: true
  memory_enabled: true
  knowledge_enabled: true
  multi_model_enabled: true
""",
            variables={
                "app_version": "2.0.0",
                "database_url": None,
                "secret_key": None,
                "jwt_secret": None
            },
            required_variables=["app_version"],
            environment_variables={
                "AGENTBUS_DEV_SECRET_KEY": "secret_key",
                "AGENTBUS_DEV_JWT_SECRET": "jwt_secret"
            }
        ))
        
        # 生产环境模板
        self.register_template(ProfileTemplate(
            name="production",
            description="生产环境配置模板",
            template="""
# AgentBus 生产环境配置
app:
  name: "AgentBus"
  version: "{{ app_version }}"
  debug: false
  environment: "production"

server:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  reload: false

logging:
  level: "WARNING"
  format: "json"
  console: false
  file: true
  max_size: 104857600  # 100MB
  backup_count: 10

database:
  url: "{{ database_url }}"
  echo: false
  pool_size: 20
  max_overflow: 10
  ssl_mode: "require"

redis:
  enabled: true
  url: "{{ redis_url }}"
  ssl: true

security:
  secret_key: "{{ secret_key }}"
  jwt_secret: "{{ jwt_secret }}"
  encryption_enabled: true
  security_level: "high"

monitoring:
  enabled: true
  metrics_enabled: true
  prometheus_enabled: true
  health_endpoint: "/health"
  metrics_endpoint: "/metrics"

features:
  hitl_enabled: true
  hitl_timeout_default: 60
  plugins_enabled: true
  skills_enabled: true
  memory_enabled: true
  knowledge_enabled: true
  multi_model_enabled: true

backup:
  enabled: true
  interval_hours: 24
  retention_days: 30
  encryption: true
""",
            variables={
                "app_version": "2.0.0",
                "database_url": "postgresql://user:pass@localhost:5432/agentbus",
                "redis_url": "redis://localhost:6379/0",
                "secret_key": None,
                "jwt_secret": None
            },
            required_variables=["database_url", "redis_url", "secret_key", "jwt_secret"],
            environment_variables={
                "AGENTBUS_PROD_DATABASE_URL": "database_url",
                "AGENTBUS_PROD_REDIS_URL": "redis_url",
                "AGENTBUS_PROD_SECRET_KEY": "secret_key",
                "AGENTBUS_PROD_JWT_SECRET": "jwt_secret"
            }
        ))
        
        # 测试环境模板
        self.register_template(ProfileTemplate(
            name="testing",
            description="测试环境配置模板",
            template="""
# AgentBus 测试环境配置
app:
  name: "AgentBus"
  version: "{{ app_version }}"
  debug: true
  environment: "testing"

server:
  host: "127.0.0.1"
  port: 8001
  workers: 1
  reload: false

logging:
  level: "INFO"
  format: "simple"
  console: true
  file: false

database:
  url: "{{ database_url or 'sqlite:///./data/test.db' }}"
  echo: false
  pool_size: 5

redis:
  enabled: false

security:
  secret_key: "{{ secret_key or 'test-secret-key' }}"
  jwt_secret: "{{ jwt_secret or 'test-jwt-secret' }}"
  encryption_enabled: false

monitoring:
  enabled: false
  metrics_enabled: false

features:
  hitl_enabled: false
  plugins_enabled: false
  skills_enabled: false
  memory_enabled: false
  knowledge_enabled: false
  multi_model_enabled: false

development:
  test_mode: true
  mock_external: true
  profiling: true
""",
            variables={
                "app_version": "2.0.0",
                "database_url": None,
                "secret_key": None,
                "jwt_secret": None
            },
            required_variables=["app_version"],
            environment_variables={
                "AGENTBUS_TEST_SECRET_KEY": "secret_key",
                "AGENTBUS_TEST_JWT_SECRET": "jwt_secret"
            }
        ))
    
    def _discover_profiles(self):
        """发现现有配置"""
        if not self.profiles_dir.exists():
            return
        
        # 扫描配置文件
        for config_file in self.profiles_dir.glob("*.yaml"):
            self._load_profile_from_file(config_file)
        
        for config_file in self.profiles_dir.glob("*.json"):
            self._load_profile_from_file(config_file)
        
        # 扫描模板目录
        for template_file in (self.profiles_dir / "templates").glob("*.yaml"):
            self._load_template_from_file(template_file)
        
        for template_file in (self.profiles_dir / "templates").glob("*.j2"):
            self._load_template_from_file(template_file)
    
    def _load_profile_from_file(self, file_path: Path):
        """从文件加载配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() == '.yaml' or file_path.suffix.lower() == '.yml':
                    data = yaml.safe_load(f)
                elif file_path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    return
            
            # 提取配置信息
            profile_name = data.get('profile', {}).get('name', file_path.stem)
            environment = data.get('profile', {}).get('environment', 'development')
            
            profile = ConfigProfile(
                name=profile_name,
                environment=environment,
                file_path=file_path,
                priority=data.get('profile', {}).get('priority', 1),
                enabled=data.get('profile', {}).get('enabled', True),
                variables=data.get('profile', {}).get('variables', {})
            )
            
            # 注册配置
            self.register_profile(profile)
            
            # 加载元数据
            metadata = ProfileMetadata(
                name=profile_name,
                version=data.get('profile', {}).get('version', '1.0.0'),
                description=data.get('profile', {}).get('description', ''),
                author=data.get('profile', {}).get('author', ''),
                tags=data.get('profile', {}).get('tags', []),
                validation_status=ProfileValidation.UNKNOWN
            )
            
            self._metadata[profile_name] = metadata
            
            logger.debug(f"已加载配置: {profile_name}")
            
        except Exception as e:
            logger.error(f"加载配置文件失败 {file_path}: {e}")
    
    def _load_template_from_file(self, file_path: Path):
        """从文件加载模板"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试解析为YAML获取元数据
            try:
                metadata = yaml.safe_load(content) or {}
            except:
                metadata = {}
            
            template_name = metadata.get('name', file_path.stem)
            
            template = ProfileTemplate(
                name=template_name,
                description=metadata.get('description', ''),
                template=content,
                variables=metadata.get('variables', {}),
                required_variables=metadata.get('required_variables', []),
                environment_variables=metadata.get('environment_variables', {})
            )
            
            self.register_template(template)
            
            logger.debug(f"已加载模板: {template_name}")
            
        except Exception as e:
            logger.error(f"加载模板文件失败 {file_path}: {e}")
    
    def register_profile(self, profile: ConfigProfile):
        """注册配置"""
        with self._lock:
            self._profiles[profile.name] = profile
            logger.debug(f"注册配置: {profile.name}")
    
    def unregister_profile(self, name: str) -> bool:
        """注销配置"""
        with self._lock:
            if name in self._profiles:
                del self._profiles[name]
                if name in self._metadata:
                    del self._metadata[name]
                
                # 从活动栈中移除
                if name in self._profile_stack:
                    self._profile_stack.remove(name)
                
                if self._active_profile == name:
                    self._active_profile = None
                
                logger.debug(f"注销配置: {name}")
                return True
            return False
    
    def get_profile(self, name: str) -> Optional[ConfigProfile]:
        """获取配置"""
        return self._profiles.get(name)
    
    def get_metadata(self, name: str) -> Optional[ProfileMetadata]:
        """获取配置元数据"""
        return self._metadata.get(name)
    
    def list_profiles(self) -> List[ConfigProfile]:
        """列出所有配置"""
        with self._lock:
            return list(self._profiles.values())
    
    def list_profiles_by_environment(self, environment: EnvironmentType) -> List[ConfigProfile]:
        """按环境列出配置"""
        with self._lock:
            return [p for p in self._profiles.values() if p.environment == environment]
    
    def activate_profile(self, name: str, push: bool = True) -> bool:
        """激活配置"""
        with self._lock:
            if name not in self._profiles:
                logger.error(f"配置不存在: {name}")
                return False
            
            profile = self._profiles[name]
            
            if push and self._active_profile:
                # 将当前配置压入栈
                self._profile_stack.append(self._active_profile)
            
            self._active_profile = name
            
            # 记录变更
            self._changes.append(ProfileChange(
                timestamp=datetime.now(),
                profile_name=name,
                action="activate",
                field_path="active_profile",
                old_value=self._active_profile if push else None,
                new_value=name
            ))
            
            logger.info(f"配置已激活: {name}")
            return True
    
    def deactivate_profile(self, name: str) -> bool:
        """停用配置"""
        with self._lock:
            if name not in self._profiles:
                return False
            
            if self._active_profile == name:
                self._active_profile = None
                
                # 恢复栈中的配置
                if self._profile_stack:
                    self._active_profile = self._profile_stack.pop()
                
                logger.info(f"配置已停用: {name}")
                return True
            
            return False
    
    def get_active_profile(self) -> Optional[str]:
        """获取当前活动配置"""
        return self._active_profile
    
    def get_profile_stack(self) -> List[str]:
        """获取配置栈"""
        return self._profile_stack.copy()
    
    def create_profile_from_template(self, template_name: str, profile_name: str,
                                   variables: Optional[Dict[str, Any]] = None,
                                   environment: Optional[EnvironmentType] = None) -> bool:
        """从模板创建配置"""
        template = self._templates.get(template_name)
        if not template:
            logger.error(f"模板不存在: {template_name}")
            return False
        
        try:
            # 准备渲染变量
            render_vars = template.variables.copy()
            if variables:
                render_vars.update(variables)
            
            # 渲染模板
            jinja_template = Template(template.template)
            rendered_content = jinja_template.render(**render_vars)
            
            # 解析渲染后的内容
            try:
                config_data = yaml.safe_load(rendered_content)
            except:
                config_data = json.loads(rendered_content)
            
            # 创建配置
            profile = ConfigProfile(
                name=profile_name,
                environment=environment or template_name,
                variables=render_vars,
                priority=1,
                enabled=True
            )
            
            # 保存配置文件
            file_path = self.profiles_dir / f"{profile_name}.yaml"
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            profile.file_path = file_path
            
            # 注册配置
            self.register_profile(profile)
            
            # 创建元数据
            metadata = ProfileMetadata(
                name=profile_name,
                version="1.0.0",
                description=f"从模板 {template_name} 创建",
                tags=["generated", template_name]
            )
            
            self._metadata[profile_name] = metadata
            
            # 记录变更
            self._changes.append(ProfileChange(
                timestamp=datetime.now(),
                profile_name=profile_name,
                action="create",
                field_path="profile",
                old_value=None,
                new_value=profile_name
            ))
            
            logger.info(f"配置已从模板创建: {profile_name}")
            return True
            
        except Exception as e:
            logger.error(f"从模板创建配置失败: {e}")
            return False
    
    def register_template(self, template: ProfileTemplate):
        """注册模板"""
        with self._lock:
            self._templates[template.name] = template
    
    def get_template(self, name: str) -> Optional[ProfileTemplate]:
        """获取模板"""
        return self._templates.get(name)
    
    def list_templates(self) -> List[ProfileTemplate]:
        """列出所有模板"""
        return list(self._templates.values())
    
    def delete_template(self, name: str) -> bool:
        """删除模板"""
        with self._lock:
            if name in self._templates:
                del self._templates[name]
                logger.debug(f"模板已删除: {name}")
                return True
            return False
    
    def export_profile(self, name: str, file_path: Union[str, Path], 
                     format: ConfigFormat = ConfigFormat.YAML) -> bool:
        """导出配置"""
        profile = self._profiles.get(name)
        if not profile:
            logger.error(f"配置不存在: {name}")
            return False
        
        try:
            file_path = Path(file_path)
            
            # 读取配置数据
            if profile.file_path and profile.file_path.exists():
                with open(profile.file_path, 'r', encoding='utf-8') as f:
                    if profile.file_path.suffix.lower() == '.yaml' or profile.file_path.suffix.lower() == '.yml':
                        data = yaml.safe_load(f)
                    else:
                        data = json.load(f)
            else:
                data = profile.variables
            
            # 添加元数据
            export_data = {
                "profile": {
                    "name": profile.name,
                    "environment": profile.environment,
                    "version": self._metadata.get(name, ProfileMetadata(name)).version,
                    "description": self._metadata.get(name, ProfileMetadata(name)).description,
                    "tags": self._metadata.get(name, ProfileMetadata(name)).tags,
                    "exported_at": datetime.now().isoformat()
                },
                "config": data
            }
            
            # 写入导出文件
            with open(file_path, 'w', encoding='utf-8') as f:
                if format == ConfigFormat.YAML:
                    yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
                elif format == ConfigFormat.JSON:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                else:
                    raise ValueError(f"不支持的导出格式: {format}")
            
            logger.info(f"配置已导出: {name} -> {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return False
    
    def import_profile(self, file_path: Union[str, Path], 
                     format: ConfigFormat = ConfigFormat.YAML) -> bool:
        """导入配置"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"导入文件不存在: {file_path}")
            
            # 读取导入文件
            with open(file_path, 'r', encoding='utf-8') as f:
                if format == ConfigFormat.YAML:
                    data = yaml.safe_load(f)
                elif format == ConfigFormat.JSON:
                    data = json.load(f)
                else:
                    raise ValueError(f"不支持的导入格式: {format}")
            
            # 提取配置信息
            profile_data = data.get('config', data)
            profile_meta = data.get('profile', {})
            
            profile_name = profile_meta.get('name', file_path.stem)
            environment = profile_meta.get('environment', 'development')
            
            # 创建配置
            profile = ConfigProfile(
                name=profile_name,
                environment=environment,
                variables=profile_data,
                priority=1,
                enabled=True
            )
            
            # 保存配置文件
            save_path = self.profiles_dir / f"{profile_name}.yaml"
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(profile_data, f, default_flow_style=False, allow_unicode=True)
            
            profile.file_path = save_path
            
            # 注册配置
            self.register_profile(profile)
            
            # 创建元数据
            metadata = ProfileMetadata(
                name=profile_name,
                version=profile_meta.get('version', '1.0.0'),
                description=profile_meta.get('description', ''),
                tags=profile_meta.get('tags', []),
                imported_at=datetime.now()
            )
            
            self._metadata[profile_name] = metadata
            
            # 记录变更
            self._changes.append(ProfileChange(
                timestamp=datetime.now(),
                profile_name=profile_name,
                action="import",
                field_path="profile",
                old_value=None,
                new_value=profile_name
            ))
            
            logger.info(f"配置已导入: {profile_name}")
            return True
            
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return False
    
    def validate_profile(self, name: str) -> ProfileValidation:
        """验证配置"""
        profile = self._profiles.get(name)
        if not profile:
            return ProfileValidation.UNKNOWN
        
        errors = []
        warnings = []
        
        try:
            # 检查必需字段
            if not profile.name:
                errors.append("配置名称为空")
            
            if not profile.environment:
                errors.append("环境类型为空")
            
            # 检查文件路径
            if profile.file_path and not profile.file_path.exists():
                errors.append(f"配置文件不存在: {profile.file_path}")
            
            # 检查变量
            if not profile.variables:
                warnings.append("配置变量为空")
            
            # 如果有文件，尝试加载和解析
            if profile.file_path and profile.file_path.exists():
                try:
                    with open(profile.file_path, 'r', encoding='utf-8') as f:
                        if profile.file_path.suffix.lower() in ['.yaml', '.yml']:
                            yaml.safe_load(f)
                        elif profile.file_path.suffix.lower() == '.json':
                            json.load(f)
                except Exception as e:
                    errors.append(f"配置文件解析失败: {e}")
            
            # 更新验证状态
            metadata = self._metadata.get(name)
            if metadata:
                metadata.validation_status = ProfileValidation.VALID if not errors else ProfileValidation.INVALID
                metadata.errors = errors
                metadata.warnings = warnings
                metadata.last_validated = datetime.now()
            
            result = ProfileValidation.VALID if not errors else ProfileValidation.INVALID
            if warnings and result == ProfileValidation.VALID:
                result = ProfileValidation.WARNING
            
            logger.debug(f"配置验证结果 {name}: {result.value}")
            return result
            
        except Exception as e:
            logger.error(f"验证配置失败 {name}: {e}")
            return ProfileValidation.UNKNOWN
    
    def get_profile_data(self, name: str) -> Optional[Dict[str, Any]]:
        """获取配置数据"""
        profile = self._profiles.get(name)
        if not profile:
            return None
        
        # 如果有配置文件，读取文件内容
        if profile.file_path and profile.file_path.exists():
            try:
                with open(profile.file_path, 'r', encoding='utf-8') as f:
                    if profile.file_path.suffix.lower() in ['.yaml', '.yml']:
                        return yaml.safe_load(f)
                    elif profile.file_path.suffix.lower() == '.json':
                        return json.load(f)
            except Exception as e:
                logger.error(f"读取配置文件失败 {name}: {e}")
        
        # 否则返回变量
        return profile.variables
    
    def update_profile_data(self, name: str, data: Dict[str, Any]) -> bool:
        """更新配置数据"""
        profile = self._profiles.get(name)
        if not profile:
            logger.error(f"配置不存在: {name}")
            return False
        
        try:
            # 如果有配置文件，更新文件
            if profile.file_path:
                with open(profile.file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            else:
                # 更新变量
                profile.variables.update(data)
            
            # 更新元数据
            metadata = self._metadata.get(name)
            if metadata:
                metadata.updated_at = datetime.now()
            
            # 记录变更
            self._changes.append(ProfileChange(
                timestamp=datetime.now(),
                profile_name=name,
                action="update",
                field_path="profile_data",
                old_value=profile.variables.copy(),
                new_value=data
            ))
            
            logger.info(f"配置数据已更新: {name}")
            return True
            
        except Exception as e:
            logger.error(f"更新配置数据失败 {name}: {e}")
            return False
    
    def get_changes(self, limit: Optional[int] = None) -> List[ProfileChange]:
        """获取变更历史"""
        changes = sorted(self._changes, key=lambda x: x.timestamp, reverse=True)
        return changes[:limit] if limit else changes
    
    def backup_profile(self, name: str) -> bool:
        """备份配置"""
        profile = self._profiles.get(name)
        if not profile or not profile.file_path:
            return False
        
        try:
            # 创建备份目录
            backup_dir = self.profiles_dir / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{name}_{timestamp}"
            
            # 复制配置文件
            if profile.file_path.exists():
                backup_path = backup_dir / f"{backup_name}{profile.file_path.suffix}"
                shutil.copy2(profile.file_path, backup_path)
            
            logger.info(f"配置已备份: {name} -> {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"备份配置失败 {name}: {e}")
            return False
    
    def restore_profile(self, backup_name: str) -> bool:
        """恢复配置"""
        try:
            backup_dir = self.profiles_dir / "backups"
            
            # 查找备份文件
            backup_files = list(backup_dir.glob(f"{backup_name}.*"))
            if not backup_files:
                logger.error(f"备份文件不存在: {backup_name}")
                return False
            
            # 恢复最新的备份文件
            backup_file = max(backup_files, key=lambda x: x.stat().st_mtime)
            
            # 提取原始配置名
            original_name = backup_name.rsplit('_', 2)[0]  # 移除时间戳
            
            if original_name in self._profiles:
                original_file = self._profiles[original_name].file_path
                if original_file:
                    shutil.copy2(backup_file, original_file)
                    
                    # 重新验证
                    self.validate_profile(original_name)
                    
                    logger.info(f"配置已恢复: {original_name}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"恢复配置失败 {backup_name}: {e}")
            return False
    
    def list_backups(self, profile_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出备份"""
        backup_dir = self.profiles_dir / "backups"
        if not backup_dir.exists():
            return []
        
        backups = []
        for backup_file in backup_dir.glob("*.yaml"):
            try:
                # 提取配置名和时间戳
                parts = backup_file.stem.rsplit('_', 2)
                if len(parts) >= 2:
                    config_name = parts[0]
                    
                    if profile_name and config_name != profile_name:
                        continue
                    
                    stat = backup_file.stat()
                    backups.append({
                        "name": backup_file.stem,
                        "config_name": config_name,
                        "file_path": backup_file,
                        "created_at": datetime.fromtimestamp(stat.st_mtime),
                        "size": stat.st_size
                    })
            except Exception as e:
                logger.warning(f"解析备份文件失败 {backup_file}: {e}")
        
        return sorted(backups, key=lambda x: x["created_at"], reverse=True)
    
    def delete_backup(self, backup_name: str) -> bool:
        """删除备份"""
        backup_dir = self.profiles_dir / "backups"
        backup_files = list(backup_dir.glob(f"{backup_name}.*"))
        
        if backup_files:
            for backup_file in backup_files:
                backup_file.unlink()
            logger.info(f"备份已删除: {backup_name}")
            return True
        
        return False
    
    def compare_profiles(self, name1: str, name2: str) -> Dict[str, Any]:
        """比较两个配置"""
        data1 = self.get_profile_data(name1) or {}
        data2 = self.get_profile_data(name2) or {}
        
        # 简单的键级别比较
        keys1 = set(data1.keys()) if isinstance(data1, dict) else set()
        keys2 = set(data2.keys()) if isinstance(data2, dict) else set()
        
        added_keys = keys2 - keys1
        removed_keys = keys1 - keys2
        common_keys = keys1 & keys2
        
        changed_keys = []
        for key in common_keys:
            if data1.get(key) != data2.get(key):
                changed_keys.append({
                    "key": key,
                    "old_value": data1.get(key),
                    "new_value": data2.get(key)
                })
        
        return {
            "profile1": name1,
            "profile2": name2,
            "added_keys": list(added_keys),
            "removed_keys": list(removed_keys),
            "changed_keys": changed_keys,
            "summary": {
                "total_keys1": len(keys1),
                "total_keys2": len(keys2),
                "added_count": len(added_keys),
                "removed_count": len(removed_keys),
                "changed_count": len(changed_keys)
            }
        }
    
    def generate_profile_diff(self, name1: str, name2: str, 
                            format: str = "yaml") -> str:
        """生成配置差异"""
        diff = self.compare_profiles(name1, name2)
        
        if format.lower() == "yaml":
            return yaml.dump(diff, default_flow_style=False, allow_unicode=True)
        elif format.lower() == "json":
            return json.dumps(diff, indent=2, ensure_ascii=False)
        else:
            # 简单文本格式
            lines = [f"配置比较: {name1} vs {name2}", "=" * 50]
            
            if diff["added_keys"]:
                lines.append("\n新增键:")
                for key in diff["added_keys"]:
                    lines.append(f"  + {key}")
            
            if diff["removed_keys"]:
                lines.append("\n删除键:")
                for key in diff["removed_keys"]:
                    lines.append(f"  - {key}")
            
            if diff["changed_keys"]:
                lines.append("\n变更键:")
                for change in diff["changed_keys"]:
                    lines.append(f"  ~ {change['key']}: {change['old_value']} -> {change['new_value']}")
            
            return "\n".join(lines)
    
    def validate_all_profiles(self) -> Dict[str, ProfileValidation]:
        """验证所有配置"""
        results = {}
        for name in self._profiles.keys():
            results[name] = self.validate_profile(name)
        return results
    
    def cleanup_old_backups(self, days: int = 30) -> int:
        """清理旧备份"""
        backup_dir = self.profiles_dir / "backups"
        if not backup_dir.exists():
            return 0
        
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for backup_file in backup_dir.glob("*"):
            try:
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_time:
                    backup_file.unlink()
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"删除备份文件失败 {backup_file}: {e}")
        
        logger.info(f"清理了 {deleted_count} 个旧备份")
        return deleted_count