"""
AgentBus 配置管理器
Configuration Manager for AgentBus

基于Moltbot的配置管理系统，提供完整的配置加载、验证、管理功能。
"""

import os
import json
import yaml
import shutil
import hashlib
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable, Set
from datetime import datetime, timedelta
from dataclasses import asdict
from enum import Enum
import logging

# 可选的热重载支持
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    Observer = None
    FileSystemEventHandler = None
    HAS_WATCHDOG = False

from .config_types import (
    EnvironmentType, ConfigProfile, ConfigSection, ValidationResult,
    WatchEvent, ConfigEvent, ConfigSnapshot, ConfigHistory, ConfigChange,
    ConfigFormat, ConfigSource, ConfigCallback
)
from .settings import ExtendedSettings
from .env_loader import EnvironmentLoader, get_env_loader
from .security import ConfigEncryption, ConfigValidator
from .watcher import ConfigWatcher
from .backup_manager import ConfigBackupManager
from .file_manager import ConfigFileManager


logger = logging.getLogger(__name__)


class ConfigManagerState(Enum):
    """配置管理器状态"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    READY = "ready"
    LOADING = "loading"
    ERROR = "error"


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        self.config_dir = Path(config_dir) if config_dir else Path("./config")
        self.state = ConfigManagerState.UNINITIALIZED
        self._lock = threading.RLock()
        self._callbacks: List[ConfigCallback] = []
        
        # 配置数据
        self._profiles: Dict[str, ConfigProfile] = {}
        self._current_profile: Optional[str] = None
        self._environment: EnvironmentType = "development"
        self._config_data: Dict[str, Any] = {}
        self._settings: Optional[ExtendedSettings] = None
        
        # 依赖组件
        self._env_loader = EnvironmentLoader()
        self._validator = ConfigValidator()
        self._encryption = ConfigEncryption()
        self._watcher: Optional[ConfigWatcher] = None
        self._backup_manager = ConfigBackupManager(self.config_dir)
        self._file_manager = ConfigFileManager(self.config_dir)
        
        # 快照和历史
        self._snapshots: Dict[str, ConfigSnapshot] = {}
        self._history: List[ConfigHistory] = []
        self._changes: List[ConfigChange] = []
        
        # 验证结果缓存
        self._validation_cache: Dict[str, ValidationResult] = {}
        self._last_validation_time: Optional[datetime] = None
        
        # 初始化默认配置
        self._setup_default_profiles()
    
    def _setup_default_profiles(self):
        """设置默认配置"""
        # 开发环境配置
        self.register_profile(ConfigProfile(
            name="development",
            environment="development",
            file_path=self.config_dir / "development.yaml",
            env_prefix="AGENTBUS_DEV_",
            priority=1,
            variables={"debug": True, "log_level": "DEBUG"}
        ))
        
        # 测试环境配置
        self.register_profile(ConfigProfile(
            name="testing",
            environment="testing",
            file_path=self.config_dir / "testing.yaml",
            env_prefix="AGENTBUS_TEST_",
            priority=1,
            variables={"debug": True, "log_level": "DEBUG"}
        ))
        
        # 生产环境配置
        self.register_profile(ConfigProfile(
            name="production",
            environment="production",
            file_path=self.config_dir / "production.yaml",
            env_prefix="AGENTBUS_PROD_",
            priority=1,
            variables={"debug": False, "log_level": "WARNING"}
        ))
        
        # 默认配置
        self.register_profile(ConfigProfile(
            name="default",
            environment="development",
            file_path=self.config_dir / "config.yaml",
            env_prefix="AGENTBUS_",
            priority=0,
            variables={}
        ))
    
    def initialize(self, environment: Optional[EnvironmentType] = None, 
                  profile: Optional[str] = None) -> bool:
        """初始化配置管理器"""
        with self._lock:
            try:
                self.state = ConfigManagerState.INITIALIZING
                logger.info("初始化配置管理器...")
                
                # 设置环境
                if environment:
                    self._environment = environment
                
                # 创建配置目录
                self._create_config_directories()
                
                # 加载配置
                self._load_configurations()
                
                # 应用配置
                self._apply_configuration()
                
                # 启动监听
                self._start_watching()
                
                # 生成初始快照
                self._create_snapshot("initial")
                
                self.state = ConfigManagerState.READY
                logger.info("配置管理器初始化完成")
                return True
                
            except Exception as e:
                self.state = ConfigManagerState.ERROR
                logger.error(f"配置管理器初始化失败: {e}")
                return False
    
    def reload(self) -> bool:
        """重新加载配置"""
        with self._lock:
            try:
                self.state = ConfigManagerState.LOADING
                logger.info("重新加载配置...")
                
                # 保存当前快照
                self._create_snapshot(f"before_reload_{int(time.time())}")
                
                # 重新加载配置
                self._load_configurations()
                
                # 应用配置
                self._apply_configuration()
                
                # 重新验证
                self._validate_configuration()
                
                # 发送重载事件
                self._emit_event(ConfigEvent.RELOADED, Path.cwd())
                
                self.state = ConfigManagerState.READY
                logger.info("配置重新加载完成")
                return True
                
            except Exception as e:
                self.state = ConfigManagerState.ERROR
                logger.error(f"配置重新加载失败: {e}")
                return False
    
    def register_profile(self, profile: ConfigProfile):
        """注册配置"""
        self._profiles[profile.name] = profile
        logger.debug(f"注册配置: {profile.name}")
    
    def unregister_profile(self, name: str) -> bool:
        """注销配置"""
        if name in self._profiles:
            del self._profiles[name]
            logger.debug(f"注销配置: {name}")
            return True
        return False
    
    def get_profile(self, name: str) -> Optional[ConfigProfile]:
        """获取配置"""
        return self._profiles.get(name)
    
    def list_profiles(self) -> List[ConfigProfile]:
        """列出所有配置"""
        return list(self._profiles.values())
    
    def switch_profile(self, name: str) -> bool:
        """切换配置"""
        if name not in self._profiles:
            logger.error(f"配置不存在: {name}")
            return False
        
        self._current_profile = name
        self._environment = self._profiles[name].environment
        
        logger.info(f"切换配置: {name}")
        return self.reload()
    
    def get_current_profile(self) -> Optional[str]:
        """获取当前配置"""
        return self._current_profile
    
    def get_environment(self) -> EnvironmentType:
        """获取当前环境"""
        return self._environment
    
    def get_settings(self) -> Optional[ExtendedSettings]:
        """获取设置实例"""
        return self._settings
    
    def get_config(self) -> Dict[str, Any]:
        """获取当前配置数据"""
        with self._lock:
            return self._config_data.copy()
    
    def set_config_value(self, path: str, value: Any, source: ConfigSource = ConfigSource.MANUAL):
        """设置配置值"""
        with self._lock:
            # 记录变更
            old_value = self._get_nested_value(self._config_data, path)
            change = ConfigChange(
                timestamp=time.time(),
                path=Path.cwd(),
                field=path,
                old_value=old_value,
                new_value=value,
                source=source,
                metadata={"source": source.value}
            )
            self._changes.append(change)
            
            # 设置新值
            self._set_nested_value(self._config_data, path, value)
            
            # 验证配置
            if self._settings:
                self._settings = self._settings.model_copy(update={path: value})
            
            # 发送更新事件
            self._emit_event(ConfigEvent.UPDATED, Path.cwd(), {
                "path": path,
                "old_value": old_value,
                "new_value": value
            })
            
            logger.debug(f"配置值已更新: {path} = {value}")
    
    def get_config_value(self, path: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._get_nested_value(self._config_data, path, default)
    
    def validate(self) -> ValidationResult:
        """验证当前配置"""
        with self._lock:
            # 检查缓存
            cache_key = self._get_validation_cache_key()
            if (self._last_validation_time and 
                datetime.now() - self._last_validation_time < timedelta(minutes=5)):
                cached_result = self._validation_cache.get(cache_key)
                if cached_result:
                    return cached_result
            
            # 执行验证
            result = self._validator.validate_config(self._config_data, self._settings)
            
            # 缓存结果
            self._validation_cache[cache_key] = result
            self._last_validation_time = datetime.now()
            
            return result
    
    def get_watcher(self) -> ConfigWatcher:
        """获取配置监听器"""
        if not self._watcher:
            self._watcher = ConfigWatcher(self.config_dir)
        return self._watcher
    
    def add_callback(self, callback: ConfigCallback):
        """添加配置变更回调"""
        with self._lock:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback: ConfigCallback):
        """移除配置变更回调"""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def export_config(self, file_path: Union[str, Path], 
                     format: ConfigFormat = ConfigFormat.YAML,
                     include_secrets: bool = False) -> bool:
        """导出配置"""
        try:
            file_path = Path(file_path)
            
            # 准备导出数据
            export_data = self._prepare_export_data(include_secrets)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                if format == ConfigFormat.YAML:
                    yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
                elif format == ConfigFormat.JSON:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                else:
                    raise ValueError(f"不支持的导出格式: {format}")
            
            logger.info(f"配置已导出到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return False
    
    def import_config(self, file_path: Union[str, Path], 
                    format: ConfigFormat = ConfigFormat.YAML) -> bool:
        """导入配置"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {file_path}")
            
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                if format == ConfigFormat.YAML:
                    config_data = yaml.safe_load(f)
                elif format == ConfigFormat.JSON:
                    config_data = json.load(f)
                else:
                    raise ValueError(f"不支持的导入格式: {format}")
            
            # 应用配置
            self._config_data.update(config_data)
            
            # 重新应用设置
            self._apply_configuration()
            
            # 发送更新事件
            self._emit_event(ConfigEvent.UPDATED, file_path, {"source": "import"})
            
            logger.info(f"配置已从 {file_path} 导入")
            return True
            
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return False
    
    def create_snapshot(self, name: str) -> bool:
        """创建配置快照"""
        return self._create_snapshot(name)
    
    def restore_snapshot(self, name: str) -> bool:
        """恢复配置快照"""
        snapshot = self._snapshots.get(name)
        if not snapshot:
            logger.error(f"快照不存在: {name}")
            return False
        
        try:
            # 保存当前状态
            self._create_snapshot(f"before_restore_{int(time.time())}")
            
            # 恢复配置
            self._config_data = snapshot.data.copy()
            
            # 重新应用设置
            self._apply_configuration()
            
            # 发送恢复事件
            self._emit_event(ConfigEvent.UPDATED, Path.cwd(), {
                "action": "restore",
                "snapshot": name
            })
            
            logger.info(f"配置快照已恢复: {name}")
            return True
            
        except Exception as e:
            logger.error(f"恢复配置快照失败: {e}")
            return False
    
    def list_snapshots(self) -> List[ConfigSnapshot]:
        """列出所有快照"""
        return list(self._snapshots.values())
    
    def delete_snapshot(self, name: str) -> bool:
        """删除快照"""
        if name in self._snapshots:
            del self._snapshots[name]
            logger.info(f"快照已删除: {name}")
            return True
        return False
    
    def get_history(self, limit: Optional[int] = None) -> List[ConfigHistory]:
        """获取配置历史"""
        history = sorted(self._history, key=lambda x: x.timestamp, reverse=True)
        return history[:limit] if limit else history
    
    def get_changes(self, limit: Optional[int] = None) -> List[ConfigChange]:
        """获取配置变更记录"""
        changes = sorted(self._changes, key=lambda x: x.timestamp, reverse=True)
        return changes[:limit] if limit else changes
    
    def encrypt_sensitive_data(self, data: Dict[str, Any]) -> bool:
        """加密敏感数据"""
        try:
            encrypted_data = self._encryption.encrypt_config(data)
            
            # 保存加密数据
            encrypted_file = self.config_dir / "encrypted_config.enc"
            with open(encrypted_file, 'w') as f:
                f.write(encrypted_data.model_dump_json())
            
            logger.info("敏感数据已加密并保存")
            return True
            
        except Exception as e:
            logger.error(f"加密敏感数据失败: {e}")
            return False
    
    def decrypt_sensitive_data(self) -> bool:
        """解密敏感数据"""
        try:
            encrypted_file = self.config_dir / "encrypted_config.enc"
            
            if not encrypted_file.exists():
                logger.warning("未找到加密配置文件")
                return False
            
            with open(encrypted_file, 'r') as f:
                encrypted_data = json.load(f)
            
            decrypted_data = self._encryption.decrypt_config(encrypted_data)
            
            # 应用解密后的数据
            self._config_data.update(decrypted_data.data)
            
            logger.info("敏感数据已解密")
            return True
            
        except Exception as e:
            logger.error(f"解密敏感数据失败: {e}")
            return False
    
    # ================================
    # 备份管理功能
    # ================================
    
    def create_backup(self, tag: Optional[str] = None) -> str:
        """创建配置备份"""
        try:
            return self._backup_manager.create_backup(tag)
        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return ""
    
    def restore_backup(self, backup_name: str) -> bool:
        """恢复配置备份"""
        try:
            if self._backup_manager.restore_backup(backup_name):
                # 重新加载配置
                self.reload()
                logger.info(f"备份已恢复: {backup_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        try:
            return self._backup_manager.list_backups()
        except Exception as e:
            logger.error(f"列出备份失败: {e}")
            return []
    
    def delete_backup(self, backup_name: str) -> bool:
        """删除备份"""
        try:
            return self._backup_manager.delete_backup(backup_name)
        except Exception as e:
            logger.error(f"删除备份失败: {e}")
            return False
    
    def cleanup_old_backups(self, days: int = 30) -> int:
        """清理旧备份"""
        try:
            return self._backup_manager.cleanup_old_backups(days)
        except Exception as e:
            logger.error(f"清理备份失败: {e}")
            return 0
    
    # ================================
    # 文件管理功能
    # ================================
    
    def read_config_file(self, file_name: str) -> Dict[str, Any]:
        """读取配置文件"""
        try:
            return self._file_manager.read_config_file(file_name)
        except Exception as e:
            logger.error(f"读取配置文件失败 {file_name}: {e}")
            return {}
    
    def write_config_file(self, file_name: str, data: Dict[str, Any], overwrite: bool = False) -> bool:
        """写入配置文件"""
        try:
            if self._file_manager.write_config_file(file_name, data, overwrite):
                logger.info(f"配置文件已写入: {file_name}")
                # 重新加载配置
                self.reload()
                return True
            return False
        except Exception as e:
            logger.error(f"写入配置文件失败 {file_name}: {e}")
            return False
    
    def delete_config_file(self, file_name: str) -> bool:
        """删除配置文件"""
        try:
            if self._file_manager.delete_config_file(file_name):
                logger.info(f"配置文件已删除: {file_name}")
                # 重新加载配置
                self.reload()
                return True
            return False
        except Exception as e:
            logger.error(f"删除配置文件失败 {file_name}: {e}")
            return False
    
    def validate_config_file(self, file_name: str) -> ValidationResult:
        """验证配置文件"""
        try:
            # 读取文件
            config_data = self._file_manager.read_config_file(file_name)
            if not config_data:
                return ValidationResult(
                    is_valid=False,
                    errors=[f"无法读取配置文件: {file_name}"],
                    warnings=[]
                )
            
            # 验证配置
            temp_settings = ExtendedSettings(**config_data)
            return self._validator.validate_config(config_data, temp_settings)
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"验证配置文件失败 {file_name}: {str(e)}"],
                warnings=[]
            )
    
    def list_config_files(self) -> List[str]:
        """列出所有配置文件"""
        try:
            return self._file_manager.list_config_files()
        except Exception as e:
            logger.error(f"列出配置文件失败: {e}")
            return []
    
    def create_template(self, template_name: str, template_data: Dict[str, Any]) -> bool:
        """创建配置模板"""
        try:
            return self._file_manager.create_template(template_name, template_data)
        except Exception as e:
            logger.error(f"创建模板失败 {template_name}: {e}")
            return False
    
    def apply_template(self, template_name: str, output_file: str, variables: Dict[str, str] = None) -> bool:
        """应用配置模板"""
        try:
            return self._file_manager.apply_template(template_name, output_file, variables)
        except Exception as e:
            logger.error(f"应用模板失败 {template_name}: {e}")
            return False
    
    # ================================
    # 私有方法
    # ================================
    
    def _create_config_directories(self):
        """创建配置目录"""
        directories = [
            self.config_dir,
            self.config_dir / "profiles",
            self.config_dir / "backups",
            self.config_dir / "snapshots",
            self.config_dir / "encrypted"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_configurations(self):
        """加载配置"""
        self._config_data = {}
        
        # 按优先级加载配置
        profiles = sorted(self._profiles.values(), key=lambda x: x.priority)
        
        for profile in profiles:
            if not profile.enabled:
                continue
            
            self._load_profile(profile)
    
    def _load_profile(self, profile: ConfigProfile):
        """加载单个配置"""
        try:
            # 加载配置文件
            if profile.file_path and profile.file_path.exists():
                config_data = self._load_config_file(profile.file_path)
                self._merge_config(config_data, ConfigSource.FILE)
            
            # 加载环境变量
            env_data = self._load_environment_vars(profile)
            self._merge_config(env_data, ConfigSource.ENVIRONMENT)
            
            # 加载profile变量
            if profile.variables:
                self._merge_config(profile.variables, ConfigSource.REMOTE)
            
            logger.debug(f"已加载配置: {profile.name}")
            
        except Exception as e:
            logger.error(f"加载配置失败 {profile.name}: {e}")
    
    def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """加载配置文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix.lower() == '.yaml' or file_path.suffix.lower() == '.yml':
                return yaml.safe_load(f)
            elif file_path.suffix.lower() == '.json':
                return json.load(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {file_path.suffix}")
    
    def _load_environment_vars(self, profile: ConfigProfile) -> Dict[str, Any]:
        """加载环境变量"""
        env_vars = {}
        
        # 从全局环境变量加载器获取
        global_vars = self._env_loader.get_variables()
        
        # 过滤profile相关的环境变量
        for key, value in global_vars.items():
            if key.startswith(profile.env_prefix):
                config_key = key[len(profile.env_prefix):]
                env_vars[config_key] = value
        
        return env_vars
    
    def _merge_config(self, new_data: Dict[str, Any], source: ConfigSource):
        """合并配置数据"""
        def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
            result = base.copy()
            
            for key, value in update.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            
            return result
        
        # 执行深度合并
        self._config_data = deep_merge(self._config_data, new_data)
    
    def _apply_configuration(self):
        """应用配置到设置"""
        try:
            # 从配置数据创建设置实例
            self._settings = ExtendedSettings(**self._config_data)
            
            logger.debug("配置已应用到设置实例")
            
        except Exception as e:
            logger.error(f"应用配置失败: {e}")
            raise
    
    def _validate_configuration(self):
        """验证配置"""
        result = self.validate()
        
        if not result.is_valid:
            logger.error("配置验证失败:")
            for error in result.errors:
                logger.error(f"  - {error}")
            
            # 发送验证失败事件
            self._emit_event(ConfigEvent.ERROR, Path.cwd(), {
                "type": "validation",
                "errors": result.errors
            })
        
        if result.warnings:
            logger.warning("配置验证警告:")
            for warning in result.warnings:
                logger.warning(f"  - {warning}")
        
        return result.is_valid
    
    def _start_watching(self):
        """启动配置监听"""
        self._watcher = ConfigWatcher(self.config_dir)
        self._watcher.add_callback(self._on_config_change)
        self._watcher.start()
    
    def _on_config_change(self, event: WatchEvent):
        """配置变更回调"""
        logger.info(f"检测到配置变更: {event.path}")
        
        # 重新加载配置
        self.reload()
    
    def _emit_event(self, event_type: ConfigEvent, path: Path, data: Optional[Dict[str, Any]] = None):
        """发送配置事件"""
        event = WatchEvent(
            event_type=event_type,
            path=path,
            timestamp=time.time(),
            data=data
        )
        
        # 调用回调函数
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"配置事件回调执行失败: {e}")
    
    def _create_snapshot(self, name: str) -> bool:
        """创建配置快照"""
        try:
            snapshot_data = self._config_data.copy()
            
            # 计算校验和
            checksum = hashlib.sha256(
                json.dumps(snapshot_data, sort_keys=True).encode()
            ).hexdigest()
            
            snapshot = ConfigSnapshot(
                id=name,
                timestamp=time.time(),
                environment=self._environment,
                profile=self._current_profile or "default",
                data=snapshot_data,
                checksum=checksum,
                metadata={
                    "version": self._settings.app_version if self._settings else "unknown",
                    "created_by": "config_manager"
                }
            )
            
            self._snapshots[name] = snapshot
            
            # 保存快照文件
            snapshot_file = self.config_dir / "snapshots" / f"{name}.json"
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                # 兼容 Pydantic v1 和 v2
                if hasattr(snapshot, "model_dump_json"):
                    f.write(snapshot.model_dump_json())
                elif hasattr(snapshot, "json"):
                    f.write(snapshot.json())
                else:
                    # 最后的回退方案
                    import json as json_lib
                    f.write(json_lib.dumps(snapshot.dict() if hasattr(snapshot, "dict") else snapshot.__dict__, indent=2))
            
            logger.debug(f"配置快照已创建: {name}")
            return True
            
        except Exception as e:
            logger.error(f"创建配置快照失败: {e}")
            return False
    
    def _prepare_export_data(self, include_secrets: bool) -> Dict[str, Any]:
        """准备导出数据"""
        export_data = self._config_data.copy()
        
        if not include_secrets:
            # 隐藏敏感信息
            sensitive_keys = ["secret_key", "jwt_secret", "password", "api_key", "token"]
            
            def mask_sensitive(data: Dict[str, Any]) -> Dict[str, Any]:
                result = {}
                for key, value in data.items():
                    if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                        result[key] = "***"
                    elif isinstance(value, dict):
                        result[key] = mask_sensitive(value)
                    else:
                        result[key] = value
                return result
            
            export_data = mask_sensitive(export_data)
        
        return export_data
    
    def _get_nested_value(self, data: Dict[str, Any], path: str, default: Any = None) -> Any:
        """获取嵌套配置值"""
        keys = path.split('.')
        current = data
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any):
        """设置嵌套配置值"""
        keys = path.split('.')
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _get_validation_cache_key(self) -> str:
        """获取验证缓存键"""
        config_str = json.dumps(self._config_data, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        if self._watcher:
            self._watcher.stop()
        
        # 清理资源
        if hasattr(self, '_backup_manager'):
            self._backup_manager.cleanup()
        
        if hasattr(self, '_file_manager'):
            self._file_manager.cleanup()
        
        if self.state == ConfigManagerState.READY:
            logger.info("配置管理器已关闭")


# 便捷函数
def create_config_manager(config_dir: Optional[Union[str, Path]] = None) -> ConfigManager:
    """创建配置管理器"""
    return ConfigManager(config_dir)


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    from . import get_config_manager as _get_manager
    return _get_manager()