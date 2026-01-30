"""
AgentBus 环境变量加载器
Environment Variable Loader for AgentBus

基于Moltbot的环境变量处理系统，支持多环境配置和变量替换。
"""

import os
import re
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Set
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

from .config_types import EnvironmentType


logger = logging.getLogger(__name__)


class EnvVarType(str, Enum):
    """环境变量类型"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    JSON = "json"
    YAML = "yaml"
    PATH = "path"
    URL = "url"
    EMAIL = "email"


@dataclass
class EnvVarDefinition:
    """环境变量定义"""
    name: str
    type: EnvVarType
    required: bool = False
    default: Any = None
    description: str = ""
    choices: Optional[List[Any]] = None
    pattern: Optional[str] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    env_prefix: str = "AGENTBUS_"
    sensitive: bool = False
    deprecated: bool = False
    deprecation_message: str = ""


class EnvironmentLoader:
    """环境变量加载器"""
    
    def __init__(self, env_prefix: str = "AGENTBUS_", env_file: str = ".env"):
        self.env_prefix = env_prefix
        self.env_file = env_file
        self._definitions: Dict[str, EnvVarDefinition] = {}
        self._variables: Dict[str, Any] = {}
        self._sensitive_vars: Set[str] = set()
        self._load_default_definitions()
    
    def _load_default_definitions(self):
        """加载默认环境变量定义"""
        definitions = [
            # 基础配置
            EnvVarDefinition("ENVIRONMENT", EnvVarType.STRING, default="development",
                           description="运行环境"),
            EnvVarDefinition("DEBUG", EnvVarType.BOOLEAN, default=False,
                           description="调试模式"),
            EnvVarDefinition("LOG_LEVEL", EnvVarType.STRING, default="INFO",
                           choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                           description="日志级别"),
            
            # 服务器配置
            EnvVarDefinition("HOST", EnvVarType.STRING, default="127.0.0.1",
                           description="服务器主机"),
            EnvVarDefinition("PORT", EnvVarType.INTEGER, default=8000, min_value=1, max_value=65535,
                           description="服务器端口"),
            EnvVarDefinition("WORKERS", EnvVarType.INTEGER, default=1, min_value=1, max_value=32,
                           description="工作进程数"),
            
            # 数据库配置
            EnvVarDefinition("DATABASE_URL", EnvVarType.STRING,
                           description="数据库连接URL"),
            EnvVarDefinition("DATABASE_POOL_SIZE", EnvVarType.INTEGER, default=5, min_value=1, max_value=100,
                           description="数据库连接池大小"),
            EnvVarDefinition("DATABASE_TIMEOUT", EnvVarType.INTEGER, default=30, min_value=1,
                           description="数据库超时时间"),
            
            # Redis配置
            EnvVarDefinition("REDIS_URL", EnvVarType.STRING,
                           description="Redis连接URL"),
            EnvVarDefinition("REDIS_HOST", EnvVarType.STRING, default="localhost",
                           description="Redis主机"),
            EnvVarDefinition("REDIS_PORT", EnvVarType.INTEGER, default=6379, min_value=1, max_value=65535,
                           description="Redis端口"),
            EnvVarDefinition("REDIS_PASSWORD", EnvVarType.STRING, sensitive=True,
                           description="Redis密码"),
            
            # 安全配置
            EnvVarDefinition("SECRET_KEY", EnvVarType.STRING, required=True, sensitive=True,
                           min_length=32, description="应用密钥"),
            EnvVarDefinition("JWT_SECRET", EnvVarType.STRING, required=True, sensitive=True,
                           min_length=32, description="JWT密钥"),
            EnvVarDefinition("ENCRYPTION_ENABLED", EnvVarType.BOOLEAN, default=True,
                           description="启用加密"),
            
            # API配置
            EnvVarDefinition("API_KEY", EnvVarType.STRING, sensitive=True,
                           description="API密钥"),
            EnvVarDefinition("API_SECRET", EnvVarType.STRING, sensitive=True,
                           description="API密钥"),
            EnvVarDefinition("RATE_LIMIT_ENABLED", EnvVarType.BOOLEAN, default=True,
                           description="启用API限流"),
            
            # 外部服务
            EnvVarDefinition("OPENAI_API_KEY", EnvVarType.STRING, sensitive=True,
                           description="OpenAI API密钥"),
            EnvVarDefinition("ANTHROPIC_API_KEY", EnvVarType.STRING, sensitive=True,
                           description="Anthropic API密钥"),
            EnvVarDefinition("GOOGLE_API_KEY", EnvVarType.STRING, sensitive=True,
                           description="Google API密钥"),
            EnvVarDefinition("MINIMAX_API_KEY", EnvVarType.STRING, sensitive=True,
                           description="Minimax API密钥"),
            
            # 邮件配置
            EnvVarDefinition("SMTP_HOST", EnvVarType.STRING,
                           description="SMTP主机"),
            EnvVarDefinition("SMTP_PORT", EnvVarType.INTEGER, default=587, min_value=1, max_value=65535,
                           description="SMTP端口"),
            EnvVarDefinition("SMTP_USERNAME", EnvVarType.STRING,
                           description="SMTP用户名"),
            EnvVarDefinition("SMTP_PASSWORD", EnvVarType.STRING, sensitive=True,
                           description="SMTP密码"),
            EnvVarDefinition("SMTP_USE_TLS", EnvVarType.BOOLEAN, default=True,
                           description="使用TLS"),
            
            # Webhook配置
            EnvVarDefinition("WEBHOOK_URL", EnvVarType.URL,
                           description="Webhook URL"),
            EnvVarDefinition("WEBHOOK_SECRET", EnvVarType.STRING, sensitive=True,
                           description="Webhook密钥"),
            
            # 文件路径配置
            EnvVarDefinition("WORKSPACE_PATH", EnvVarType.PATH, default="./workspace",
                           description="工作空间路径"),
            EnvVarDefinition("DATA_PATH", EnvVarType.PATH, default="./data",
                           description="数据文件路径"),
            EnvVarDefinition("TEMP_PATH", EnvVarType.PATH, default="./temp",
                           description="临时文件路径"),
            EnvVarDefinition("CONFIG_PATH", EnvVarType.PATH, default="./config",
                           description="配置文件路径"),
            EnvVarDefinition("LOGS_PATH", EnvVarType.PATH, default="./logs",
                           description="日志文件路径"),
            
            # 监控配置
            EnvVarDefinition("MONITORING_ENABLED", EnvVarType.BOOLEAN, default=False,
                           description="启用监控"),
            EnvVarDefinition("METRICS_ENABLED", EnvVarType.BOOLEAN, default=False,
                           description="启用指标"),
            EnvVarDefinition("METRICS_PORT", EnvVarType.INTEGER, default=9090, min_value=1, max_value=65535,
                           description="指标端口"),
            
            # 插件配置
            EnvVarDefinition("PLUGINS_ENABLED", EnvVarType.BOOLEAN, default=True,
                           description="启用插件系统"),
            EnvVarDefinition("PLUGINS_AUTO_LOAD", EnvVarType.BOOLEAN, default=True,
                           description="自动加载插件"),
            EnvVarDefinition("PLUGINS_SCAN_DIRECTORIES", EnvVarType.LIST, default=["./plugins", "./extensions"],
                           description="插件扫描目录"),
            
            # 技能配置
            EnvVarDefinition("SKILLS_ENABLED", EnvVarType.BOOLEAN, default=True,
                           description="启用技能系统"),
            EnvVarDefinition("SKILLS_AUTO_REGISTER", EnvVarType.BOOLEAN, default=True,
                           description="自动注册技能"),
            
            # 缓存配置
            EnvVarDefinition("CACHE_ENABLED", EnvVarType.BOOLEAN, default=True,
                           description="启用缓存"),
            EnvVarDefinition("CACHE_TTL", EnvVarType.INTEGER, default=3600, min_value=0,
                           description="缓存TTL"),
            EnvVarDefinition("CACHE_MAX_SIZE", EnvVarType.INTEGER, default=1000, min_value=1,
                           description="缓存最大大小"),
            
            # 备份配置
            EnvVarDefinition("BACKUP_ENABLED", EnvVarType.BOOLEAN, default=True,
                           description="启用备份"),
            EnvVarDefinition("BACKUP_PATH", EnvVarType.PATH, default="./backups",
                           description="备份路径"),
            EnvVarDefinition("BACKUP_INTERVAL_HOURS", EnvVarType.INTEGER, default=24, min_value=1,
                           description="备份间隔（小时）"),
            
            # 开发配置
            EnvVarDefinition("DEVELOPMENT_HOT_RELOAD", EnvVarType.BOOLEAN, default=False,
                           description="热重载"),
            EnvVarDefinition("DEVELOPMENT_DEBUG_TOOLBAR", EnvVarType.BOOLEAN, default=False,
                           description="调试工具栏"),
            EnvVarDefinition("DEVELOPMENT_TEST_MODE", EnvVarType.BOOLEAN, default=False,
                           description="测试模式"),
        ]
        
        for definition in definitions:
            self.register_definition(definition)
    
    def register_definition(self, definition: EnvVarDefinition):
        """注册环境变量定义"""
        self._definitions[definition.name] = definition
        if definition.sensitive:
            self._sensitive_vars.add(definition.name)
    
    def register_definitions(self, definitions: List[EnvVarDefinition]):
        """批量注册环境变量定义"""
        for definition in definitions:
            self.register_definition(definition)
    
    def get_definition(self, name: str) -> Optional[EnvVarDefinition]:
        """获取环境变量定义"""
        return self._definitions.get(name)
    
    def list_definitions(self) -> Dict[str, EnvVarDefinition]:
        """列出所有环境变量定义"""
        return self._definitions.copy()
    
    def load_from_process_env(self) -> Dict[str, Any]:
        """从进程环境变量加载"""
        variables = {}
        
        for name, definition in self._definitions.items():
            # 获取带前缀的环境变量名
            env_name = f"{definition.env_prefix}{name}"
            
            # 获取环境变量值
            value = os.getenv(env_name)
            
            # 如果没有找到，尝试不带前缀的变量名
            if value is None:
                value = os.getenv(name)
            
            # 如果仍然没有找到，使用默认值
            if value is None:
                value = definition.default
            else:
                # 解析类型
                try:
                    value = self._parse_value(value, definition.type)
                except ValueError as e:
                    raise ValueError(f"环境变量 {env_name} 解析失败: {e}")
            
            # 验证值
            self._validate_value(value, definition)
            
            variables[name] = value
        
        self._variables = variables
        return variables
    
    def load_from_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """从环境文件加载"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"环境文件不存在: {file_path}")
            return {}
        
        variables = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析环境文件
            lines = content.split('\n')
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                
                # 解析 KEY=VALUE 格式
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    
                    # 移除前缀进行比较
                    clean_key = key
                    if key.startswith(self.env_prefix):
                        clean_key = key[len(self.env_prefix):]
                    
                    if clean_key in self._definitions:
                        definition = self._definitions[clean_key]
                        
                        # 解析类型
                        try:
                            parsed_value = self._parse_value(value, definition.type)
                            self._validate_value(parsed_value, definition)
                            variables[clean_key] = parsed_value
                        except ValueError as e:
                            logger.error(f"环境文件 {file_path}:{line_num} 解析失败: {e}")
                            continue
                else:
                    logger.warning(f"环境文件 {file_path}:{line_num} 格式无效: {line}")
        
        except Exception as e:
            logger.error(f"读取环境文件失败: {e}")
            raise
        
        self._variables.update(variables)
        return variables
    
    def _parse_value(self, value: str, var_type: EnvVarType) -> Any:
        """解析环境变量值"""
        if value is None:
            return None
        
        # 移除引号
        if isinstance(value, str):
            value = value.strip().strip('"\'')
        
        if var_type == EnvVarType.STRING:
            return str(value)
        
        elif var_type == EnvVarType.INTEGER:
            return int(value)
        
        elif var_type == EnvVarType.FLOAT:
            return float(value)
        
        elif var_type == EnvVarType.BOOOLEAN:
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        
        elif var_type == EnvVarType.LIST:
            if isinstance(value, str):
                # 逗号分隔的列表
                return [item.strip() for item in value.split(',') if item.strip()]
            return list(value)
        
        elif var_type == EnvVarType.DICT:
            if isinstance(value, str):
                # JSON格式的字典
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    # 尝试YAML格式
                    try:
                        return yaml.safe_load(value)
                    except yaml.YAMLError:
                        raise ValueError(f"无法解析字典值: {value}")
            return dict(value)
        
        elif var_type == EnvVarType.JSON:
            if isinstance(value, str):
                return json.loads(value)
            return value
        
        elif var_type == EnvVarType.YAML:
            if isinstance(value, str):
                return yaml.safe_load(value)
            return value
        
        elif var_type == EnvVarType.PATH:
            return str(Path(value).expanduser().resolve())
        
        elif var_type == EnvVarType.URL:
            url = str(value)
            if not (url.startswith('http://') or url.startswith('https://')):
                raise ValueError(f"无效的URL格式: {url}")
            return url
        
        elif var_type == EnvVarType.EMAIL:
            email = str(value)
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                raise ValueError(f"无效的邮箱格式: {email}")
            return email
        
        else:
            return value
    
    def _validate_value(self, value: Any, definition: EnvVarDefinition):
        """验证环境变量值"""
        if value is None:
            if definition.required:
                raise ValueError(f"必需的环境变量 {definition.name} 未设置")
            return
        
        # 检查choices
        if definition.choices is not None and value not in definition.choices:
            raise ValueError(f"环境变量 {definition.name} 的值必须在 {definition.choices} 中，当前值: {value}")
        
        # 检查类型
        if definition.type == EnvVarType.INTEGER:
            if not isinstance(value, int):
                raise ValueError(f"环境变量 {definition.name} 必须是整数")
            
            if definition.min_value is not None and value < definition.min_value:
                raise ValueError(f"环境变量 {definition.name} 不能小于 {definition.min_value}")
            
            if definition.max_value is not None and value > definition.max_value:
                raise ValueError(f"环境变量 {definition.name} 不能大于 {definition.max_value}")
        
        elif definition.type == EnvVarType.FLOAT:
            if not isinstance(value, (int, float)):
                raise ValueError(f"环境变量 {definition.name} 必须是数字")
            
            if definition.min_value is not None and value < definition.min_value:
                raise ValueError(f"环境变量 {definition.name} 不能小于 {definition.min_value}")
            
            if definition.max_value is not None and value > definition.max_value:
                raise ValueError(f"环境变量 {definition.name} 不能大于 {definition.max_value}")
        
        elif definition.type in (EnvVarType.STRING, EnvVarType.PATH, EnvVarType.URL, EnvVarType.EMAIL):
            str_value = str(value)
            
            if definition.min_length is not None and len(str_value) < definition.min_length:
                raise ValueError(f"环境变量 {definition.name} 长度不能小于 {definition.min_length}")
            
            if definition.max_length is not None and len(str_value) > definition.max_length:
                raise ValueError(f"环境变量 {definition.name} 长度不能大于 {definition.max_length}")
            
            if definition.pattern is not None and not re.match(definition.pattern, str_value):
                raise ValueError(f"环境变量 {definition.name} 不符合模式: {definition.pattern}")
        
        # 检查已弃用的变量
        if definition.deprecated:
            logger.warning(f"环境变量 {definition.name} 已弃用: {definition.deprecation_message}")
    
    def substitute_variables(self, text: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """替换文本中的变量引用"""
        if variables is None:
            variables = self._variables
        
        # ${VAR} 格式的变量替换
        def replace_var(match):
            var_name = match.group(1)
            
            # 支持嵌套变量
            nested_keys = var_name.split('.')
            value = variables
            
            for key in nested_keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    # 尝试从环境变量获取
                    env_var = f"{self.env_prefix}{var_name}"
                    env_value = os.getenv(env_var)
                    if env_value is not None:
                        return env_value
                    return match.group(0)  # 返回原始字符串
            
            return str(value)
        
        # 替换 ${VAR} 格式
        result = re.sub(r'\$\{([^}]+)\}', replace_var, text)
        
        # 替换 $VAR 格式
        def replace_simple_var(match):
            var_name = match.group(1)
            
            if var_name in variables:
                return str(variables[var_name])
            
            # 尝试从环境变量获取
            env_var = f"{self.env_prefix}{var_name}"
            env_value = os.getenv(env_var)
            if env_value is not None:
                return env_value
            
            return match.group(0)
        
        result = re.sub(r'\$([A-Z_][A-Z0-9_]*)', replace_simple_var, result)
        
        return result
    
    def get_variables(self) -> Dict[str, Any]:
        """获取所有变量"""
        return self._variables.copy()
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取单个变量"""
        return self._variables.get(name, default)
    
    def set_variable(self, name: str, value: Any):
        """设置变量"""
        if name in self._definitions:
            self._validate_value(value, self._definitions[name])
        
        self._variables[name] = value
    
    def is_sensitive(self, name: str) -> bool:
        """检查变量是否为敏感信息"""
        return name in self._sensitive_vars
    
    def get_sensitive_names(self) -> Set[str]:
        """获取所有敏感变量名"""
        return self._sensitive_vars.copy()
    
    def mask_sensitive_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """隐藏敏感值"""
        masked_data = data.copy()
        
        for name, value in masked_data.items():
            if name in self._sensitive_vars:
                masked_data[name] = "***"
        
        return masked_data
    
    def validate_all(self) -> List[str]:
        """验证所有变量"""
        errors = []
        
        for name, definition in self._definitions.items():
            value = self._variables.get(name)
            
            try:
                self._validate_value(value, definition)
            except ValueError as e:
                errors.append(str(e))
        
        return errors
    
    def export_to_env_format(self, include_sensitive: bool = False) -> str:
        """导出为环境文件格式"""
        lines = []
        
        for name, definition in sorted(self._definitions.items()):
            value = self._variables.get(name)
            
            if value is None:
                continue
            
            # 跳过敏感变量
            if definition.sensitive and not include_sensitive:
                lines.append(f"# {name}=*** # 敏感信息已隐藏")
                continue
            
            env_var_name = f"{definition.env_prefix}{name}"
            
            # 格式化值
            if isinstance(value, bool):
                str_value = "true" if value else "false"
            elif isinstance(value, (list, dict)):
                str_value = json.dumps(value)
            else:
                str_value = str(value)
            
            # 添加引号如果需要
            if ' ' in str_value or '"' in str_value:
                str_value = f'"{str_value}"'
            
            lines.append(f"{env_var_name}={str_value}")
        
        return '\n'.join(lines)
    
    def generate_env_file(self, file_path: Union[str, Path], include_sensitive: bool = False):
        """生成环境文件"""
        content = self.export_to_env_format(include_sensitive=include_sensitive)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"# AgentBus 环境配置文件\n")
            f.write(f"# 生成时间: {datetime.now().isoformat()}\n")
            f.write(f"# 环境: {self.get_variable('ENVIRONMENT', 'development')}\n")
            f.write("\n")
            f.write(content)
        
        logger.info(f"环境文件已生成: {file_path}")


# 全局环境变量加载器实例
_global_env_loader = None


def get_env_loader() -> EnvironmentLoader:
    """获取全局环境变量加载器"""
    global _global_env_loader
    if _global_env_loader is None:
        _global_env_loader = EnvironmentLoader()
    return _global_env_loader


def load_environment(env_file: Optional[str] = None) -> Dict[str, Any]:
    """加载环境变量"""
    loader = get_env_loader()
    
    # 从环境文件加载
    if env_file:
        loader.load_from_file(env_file)
    
    # 从进程环境变量加载
    return loader.load_from_process_env()


def substitute_env_vars(text: str) -> str:
    """替换环境变量（便捷函数）"""
    loader = get_env_loader()
    return loader.substitute_variables(text)


def get_env_var(name: str, default: Any = None) -> Any:
    """获取环境变量（便捷函数）"""
    loader = get_env_loader()
    return loader.get_variable(name, default)


def is_env_var_sensitive(name: str) -> bool:
    """检查环境变量是否为敏感信息（便捷函数）"""
    loader = get_env_loader()
    return loader.is_sensitive(name)