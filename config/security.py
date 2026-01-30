"""
AgentBus 配置安全模块
Configuration Security Module for AgentBus

提供配置验证、加密解密等安全功能。
"""

import os
import json
import base64
import hashlib
import hmac
import secrets
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import re
import jinja2
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import pydantic
from pydantic import ValidationError

from .config_types import ValidationResult, EncryptedConfig


logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """验证严重程度"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationRule:
    """验证规则"""
    field: str
    rule_type: str
    parameters: Dict[str, Any]
    severity: ValidationSeverity
    message: str


@dataclass
class SecurityConfig:
    """安全配置"""
    encryption_enabled: bool = True
    key_rotation_days: int = 90
    max_password_age_days: int = 365
    password_min_length: int = 8
    require_special_chars: bool = False
    require_numbers: bool = True
    require_uppercase: bool = True
    require_lowercase: bool = True
    forbidden_passwords: Set[str] = None
    secret_rotation_enabled: bool = True
    audit_logging: bool = True
    
    def __post_init__(self):
        if self.forbidden_passwords is None:
            self.forbidden_passwords = set()


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self, security_config: Optional[SecurityConfig] = None):
        self.security_config = security_config or SecurityConfig()
        self._validation_rules: List[ValidationRule] = []
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        self._load_default_rules()
    
    def _load_default_rules(self):
        """加载默认验证规则"""
        # 安全相关验证
        self._validation_rules.extend([
            ValidationRule(
                field="secret_key",
                rule_type="min_length",
                parameters={"min_length": 32},
                severity=ValidationSeverity.ERROR,
                message="密钥长度至少需要32个字符"
            ),
            ValidationRule(
                field="jwt_secret",
                rule_type="min_length",
                parameters={"min_length": 32},
                severity=ValidationSeverity.ERROR,
                message="JWT密钥长度至少需要32个字符"
            ),
            ValidationRule(
                field="secret_key",
                rule_type="not_common_password",
                parameters={},
                severity=ValidationSeverity.ERROR,
                message="不能使用常见密码"
            ),
            ValidationRule(
                field="database_url",
                rule_type="url_format",
                parameters={},
                severity=ValidationSeverity.ERROR,
                message="数据库URL格式无效"
            ),
            ValidationRule(
                field="redis_url",
                rule_type="redis_url_format",
                parameters={},
                severity=ValidationSeverity.WARNING,
                message="Redis URL格式无效"
            ),
            ValidationRule(
                field="port",
                rule_type="port_range",
                parameters={"min": 1, "max": 65535},
                severity=ValidationSeverity.ERROR,
                message="端口号必须在1-65535范围内"
            ),
            ValidationRule(
                field="log_level",
                rule_type="enum",
                parameters={"values": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
                severity=ValidationSeverity.WARNING,
                message="日志级别值无效"
            ),
            ValidationRule(
                field="cors_origins",
                rule_type="cors_origins_format",
                parameters={},
                severity=ValidationSeverity.WARNING,
                message="CORS配置可能不安全"
            ),
            ValidationRule(
                field="openai_api_key",
                rule_type="api_key_format",
                parameters={"prefix": "sk-"},
                severity=ValidationSeverity.ERROR,
                message="OpenAI API密钥格式无效"
            ),
            ValidationRule(
                field="anthropic_api_key",
                rule_type="api_key_format",
                parameters={"prefix": "sk-ant-"},
                severity=ValidationSeverity.ERROR,
                message="Anthropic API密钥格式无效"
            ),
        ])
    
    def validate_config(self, config: Dict[str, Any], 
                       settings: Optional[Any] = None) -> ValidationResult:
        """验证配置"""
        errors = []
        warnings = []
        suggestions = []
        
        # 执行规则验证
        for rule in self._validation_rules:
            try:
                field_value = self._get_nested_value(config, rule.field)
                if field_value is not None:
                    rule_result = self._validate_field(rule, field_value)
                    
                    if rule_result:
                        if rule.severity == ValidationSeverity.ERROR:
                            errors.append(f"{rule.field}: {rule.message}")
                        elif rule.severity == ValidationSeverity.WARNING:
                            warnings.append(f"{rule.field}: {rule.message}")
                        else:
                            suggestions.append(f"{rule.rule_type}: {rule.message}")
                            
            except Exception as e:
                logger.error(f"验证规则执行失败 {rule.field}: {e}")
                errors.append(f"{rule.field}: 验证规则执行失败")
        
        # 执行模式验证
        schema_errors = self._validate_with_schema(config)
        errors.extend(schema_errors)
        
        # 执行安全验证
        security_errors = self._validate_security(config)
        errors.extend(security_errors)
        
        # 执行依赖验证
        dependency_errors = self._validate_dependencies(config)
        errors.extend(dependency_errors)
        
        # 生成建议
        suggestions.extend(self._generate_suggestions(config))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def _validate_field(self, rule: ValidationRule, value: Any) -> bool:
        """验证单个字段"""
        if rule.rule_type == "min_length":
            return len(str(value)) >= rule.parameters.get("min_length", 0)
        
        elif rule.rule_type == "max_length":
            return len(str(value)) <= rule.parameters.get("max_length", float('inf'))
        
        elif rule.rule_type == "enum":
            return value in rule.parameters.get("values", [])
        
        elif rule.rule_type == "pattern":
            pattern = rule.parameters.get("pattern", "")
            return bool(re.match(pattern, str(value)))
        
        elif rule.rule_type == "url_format":
            return self._is_valid_url(str(value))
        
        elif rule.rule_type == "redis_url_format":
            return self._is_valid_redis_url(str(value))
        
        elif rule.rule_type == "port_range":
            return (isinstance(value, int) and 
                   rule.parameters.get("min", 1) <= value <= rule.parameters.get("max", 65535))
        
        elif rule.rule_type == "api_key_format":
            return str(value).startswith(rule.parameters.get("prefix", ""))
        
        elif rule.rule_type == "not_common_password":
            return self._is_not_common_password(str(value))
        
        elif rule.rule_type == "cors_origins_format":
            return self._is_secure_cors_config(value)
        
        elif rule.rule_type == "email_format":
            return self._is_valid_email(str(value))
        
        elif rule.rule_type == "ip_address":
            return self._is_valid_ip_address(str(value))
        
        else:
            logger.warning(f"未知的验证规则类型: {rule.rule_type}")
            return True
    
    def _validate_with_schema(self, config: Dict[str, Any]) -> List[str]:
        """使用模式验证配置"""
        errors = []
        
        # 基础配置验证
        required_fields = ["app_name", "environment", "host"]
        for field in required_fields:
            if not self._get_nested_value(config, field):
                errors.append(f"必需字段缺失: {field}")
        
        # 类型验证
        type_validations = {
            "port": int,
            "workers": int,
            "debug": bool,
            "log_level": str,
            "secret_key": str
        }
        
        for field, expected_type in type_validations.items():
            value = self._get_nested_value(config, field)
            if value is not None and not isinstance(value, expected_type):
                errors.append(f"{field} 类型错误，期望 {expected_type.__name__}，实际 {type(value).__name__}")
        
        return errors
    
    def _validate_security(self, config: Dict[str, Any]) -> List[str]:
        """安全验证"""
        errors = []
        
        # 生产环境特殊验证
        environment = self._get_nested_value(config, "environment")
        if environment == "production":
            # 生产环境安全检查
            secret_key = self._get_nested_value(config, "secret_key")
            if secret_key and len(secret_key) < 32:
                errors.append("生产环境中密钥长度必须至少32个字符")
            
            # 检查是否启用了调试
            debug = self._get_nested_value(config, "debug")
            if debug:
                errors.append("生产环境中不应启用调试模式")
            
            # 检查CORS配置
            cors_origins = self._get_nested_value(config, "cors_origins")
            if cors_origins == "*":
                errors.append("生产环境中CORS不应设置为'*'")
        
        # API密钥验证
        api_keys = ["openai_api_key", "anthropic_api_key", "google_api_key"]
        for key in api_keys:
            api_key = self._get_nested_value(config, key)
            if api_key and not self._is_valid_api_key(key, api_key):
                errors.append(f"API密钥格式无效: {key}")
        
        return errors
    
    def _validate_dependencies(self, config: Dict[str, Any]) -> List[str]:
        """依赖验证"""
        errors = []
        
        # 数据库配置验证
        database_url = self._get_nested_value(config, "database_url")
        database_type = self._get_nested_value(config, "database_type")
        
        if database_url and database_type:
            if database_type == "postgresql" and "postgresql" not in database_url:
                errors.append("数据库类型与URL不匹配")
            elif database_type == "mysql" and "mysql" not in database_url:
                errors.append("数据库类型与URL不匹配")
            elif database_type == "sqlite" and "sqlite" not in database_url:
                errors.append("数据库类型与URL不匹配")
        
        # Redis配置验证
        redis_url = self._get_nested_value(config, "redis_url")
        redis_enabled = self._get_nested_value(config, "cache_enabled") and \
                       self._get_nested_value(config, "cache_backend") == "redis"
        
        if redis_enabled and not redis_url:
            errors.append("启用Redis缓存但未配置Redis URL")
        
        return errors
    
    def _generate_suggestions(self, config: Dict[str, Any]) -> List[str]:
        """生成建议"""
        suggestions = []
        
        # 性能建议
        if self._get_nested_value(config, "workers", 1) == 1:
            suggestions.append("考虑增加工作进程数以提高性能")
        
        if self._get_nested_value(config, "database_pool_size", 5) < 10:
            suggestions.append("考虑增加数据库连接池大小")
        
        # 安全建议
        if not self._get_nested_value(config, "encryption_enabled"):
            suggestions.append("建议启用配置加密")
        
        if not self._get_nested_value(config, "monitoring_enabled"):
            suggestions.append("建议启用监控功能")
        
        # 运维建议
        if not self._get_nested_value(config, "backup_enabled"):
            suggestions.append("建议启用配置备份")
        
        return suggestions
    
    def _get_nested_value(self, data: Dict[str, Any], path: str, default: Any = None) -> Any:
        """获取嵌套值"""
        keys = path.split('.')
        current = data
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def _is_valid_url(self, url: str) -> bool:
        """验证URL格式"""
        pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(pattern.match(url))
    
    def _is_valid_redis_url(self, url: str) -> bool:
        """验证Redis URL格式"""
        if not url:
            return True
        
        pattern = re.compile(
            r'^redis://'  # redis://
            r'(:?[^@]+@)?'  # optional password
            r'[^:/]+'  # hostname
            r'(?::\d+)?'  # optional port
            r'(?:\/\d+)?$', re.IGNORECASE)
        return bool(pattern.match(url))
    
    def _is_not_common_password(self, password: str) -> bool:
        """检查是否为常见密码"""
        common_passwords = {
            "password", "123456", "123456789", "qwerty", "abc123",
            "password123", "admin", "letmein", "welcome", "monkey",
            "1234567890", "password1", "12345", "qwerty123",
            "1q2w3e4r", "password123", "admin123", "root123",
            "123456", "111111", "123123", "000000", "1234"
        }
        
        return password.lower() not in common_passwords
    
    def _is_secure_cors_config(self, cors_origins: Any) -> bool:
        """检查CORS配置是否安全"""
        if cors_origins == "*":
            return False
        
        if isinstance(cors_origins, list):
            return "*" not in cors_origins
        
        if isinstance(cors_origins, str):
            return cors_origins != "*"
        
        return True
    
    def _is_valid_email(self, email: str) -> bool:
        """验证邮箱格式"""
        pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        return bool(pattern.match(email))
    
    def _is_valid_ip_address(self, ip: str) -> bool:
        """验证IP地址格式"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False
            return True
        except ValueError:
            return False
    
    def _is_valid_api_key(self, key_type: str, api_key: str) -> bool:
        """验证API密钥格式"""
        key = str(api_key)
        
        if key_type == "openai_api_key":
            return key.startswith("sk-")
        elif key_type == "anthropic_api_key":
            return key.startswith("sk-ant-")
        elif key_type == "google_api_key":
            return len(key) > 20  # Google API密钥通常较长
        elif key_type == "minimax_api_key":
            return len(key) > 10  # Minimax API密钥
        
        return True  # 其他类型默认通过
    
    def add_validation_rule(self, rule: ValidationRule):
        """添加验证规则"""
        self._validation_rules.append(rule)
    
    def remove_validation_rule(self, field: str, rule_type: str):
        """移除验证规则"""
        self._validation_rules = [
            rule for rule in self._validation_rules
            if not (rule.field == field and rule.rule_type == rule_type)
        ]


class ConfigEncryption:
    """配置加密器"""
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key
        self._cipher: Optional[Fernet] = None
        self._salt_cache: Dict[str, bytes] = {}
        self._initialize_cipher()
    
    def _initialize_cipher(self):
        """初始化加密器"""
        try:
            if self.master_key:
                # 使用用户提供的密钥
                salt = b'agentbus_config_salt_2024'  # 固定盐值用于密钥派生
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
                self._cipher = Fernet(key)
            else:
                # 生成新的主密钥
                self.master_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
                salt = b'agentbus_config_salt_2024'
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
                self._cipher = Fernet(key)
                
        except Exception as e:
            logger.error(f"初始化加密器失败: {e}")
            raise
    
    def encrypt_config(self, config: Dict[str, Any]) -> EncryptedConfig:
        """加密配置"""
        if not self._cipher:
            raise ValueError("加密器未初始化")
        
        try:
            # 序列化配置
            config_json = json.dumps(config, sort_keys=True).encode('utf-8')
            
            # 加密
            encrypted_data = self._cipher.encrypt(config_json)
            
            # 计算校验和
            checksum = hashlib.sha256(config_json).hexdigest()
            
            return EncryptedConfig(
                encrypted_data=base64.urlsafe_b64encode(encrypted_data).decode(),
                checksum=checksum,
                algorithm="Fernet",
                version="1.0.0",
                timestamp=datetime.now().timestamp()
            )
            
        except Exception as e:
            logger.error(f"配置加密失败: {e}")
            raise
    
    def decrypt_config(self, encrypted_config: Union[EncryptedConfig, Dict[str, Any]]) -> EncryptedConfig:
        """解密配置"""
        if not self._cipher:
            raise ValueError("加密器未初始化")
        
        try:
            if isinstance(encrypted_config, dict):
                encrypted_config = EncryptedConfig(**encrypted_config)
            
            # 解密
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_config.encrypted_data.encode())
            decrypted_data = self._cipher.decrypt(encrypted_bytes)
            
            # 验证校验和
            decrypted_json = decrypted_data.decode('utf-8')
            config = json.loads(decrypted_json)
            checksum = hashlib.sha256(decrypted_data).hexdigest()
            
            if checksum != encrypted_config.checksum:
                raise ValueError("校验和不匹配，数据可能已损坏")
            
            return EncryptedConfig(
                encrypted_data=config,
                checksum=checksum,
                algorithm=encrypted_config.algorithm,
                version=encrypted_config.version,
                timestamp=encrypted_config.timestamp
            )
            
        except Exception as e:
            logger.error(f"配置解密失败: {e}")
            raise
    
    def encrypt_field(self, value: str) -> str:
        """加密单个字段"""
        if not self._cipher:
            raise ValueError("加密器未初始化")
        
        try:
            encrypted_data = self._cipher.encrypt(value.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"字段加密失败: {e}")
            raise
    
    def decrypt_field(self, encrypted_value: str) -> str:
        """解密单个字段"""
        if not self._cipher:
            raise ValueError("加密器未初始化")
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted_data = self._cipher.decrypt(encrypted_bytes)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"字段解密失败: {e}")
            raise
    
    def is_encrypted(self, value: str) -> bool:
        """检查值是否已加密"""
        try:
            base64.urlsafe_b64decode(value.encode())
            return True
        except:
            return False
    
    def get_master_key(self) -> str:
        """获取主密钥（谨慎使用）"""
        return self.master_key
    
    def rotate_key(self) -> str:
        """轮换密钥"""
        # 生成新密钥
        new_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        
        # 重新初始化加密器
        old_cipher = self._cipher
        old_master_key = self.master_key
        
        try:
            self.master_key = new_key
            self._initialize_cipher()
            logger.info("密钥已轮换")
            return new_key
        except Exception as e:
            # 回滚到旧密钥
            self.master_key = old_master_key
            self._cipher = old_cipher
            logger.error(f"密钥轮换失败: {e}")
            raise
    
    def export_key(self, file_path: Union[str, Path], password: Optional[str] = None) -> bool:
        """导出主密钥"""
        try:
            file_path = Path(file_path)
            
            key_data = {
                "master_key": self.master_key,
                "timestamp": datetime.now().isoformat(),
                "algorithm": "PBKDF2-SHA256-Fernet",
                "salt": "agentbus_config_salt_2024",
                "iterations": 100000
            }
            
            if password:
                # 使用密码加密导出
                password_key = hashlib.sha256(password.encode()).digest()[:32]
                fernet_key = base64.urlsafe_b64encode(password_key)
                cipher = Fernet(fernet_key)
                encrypted_data = cipher.encrypt(json.dumps(key_data).encode())
                key_data["encrypted_data"] = base64.urlsafe_b64encode(encrypted_data).decode()
                del key_data["master_key"]
            
            with open(file_path, 'w') as f:
                json.dump(key_data, f, indent=2)
            
            # 设置权限
            os.chmod(file_path, 0o600)
            
            logger.info(f"主密钥已导出到: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出主密钥失败: {e}")
            return False
    
    def import_key(self, file_path: Union[str, Path], password: Optional[str] = None) -> bool:
        """导入主密钥"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"密钥文件不存在: {file_path}")
            
            with open(file_path, 'r') as f:
                key_data = json.load(f)
            
            if "encrypted_data" in key_data and password:
                # 解密导入
                password_key = hashlib.sha256(password.encode()).digest()[:32]
                fernet_key = base64.urlsafe_b64encode(password_key)
                cipher = Fernet(fernet_key)
                encrypted_data = base64.urlsafe_b64decode(key_data["encrypted_data"])
                decrypted_data = cipher.decrypt(encrypted_data)
                key_data = json.loads(decrypted_data.decode())
            
            master_key = key_data.get("master_key")
            if not master_key:
                raise ValueError("密钥文件中没有找到主密钥")
            
            self.master_key = master_key
            self._initialize_cipher()
            
            logger.info(f"主密钥已从 {file_path} 导入")
            return True
            
        except Exception as e:
            logger.error(f"导入主密钥失败: {e}")
            return False