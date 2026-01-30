"""
安全模块
Security Module

提供身份验证、授权、加密等安全功能
"""

from typing import Dict, Any, Optional, List, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import asyncio
import hashlib
import hmac
import secrets
import base64
from contextlib import asynccontextmanager

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import jwt as pyjwt
import bcrypt

from ..core.logger import get_logger
from ..core.config import settings

logger = get_logger(__name__)


class SecurityLevel(Enum):
    """安全级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Permission(Enum):
    """权限枚举"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"
    MANAGE = "manage"
    DELETE = "delete"


@dataclass
class User:
    """用户实体"""
    id: str
    username: str
    email: Optional[str] = None
    hashed_password: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    permissions: Set[Permission] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_permission(self, permission: Permission) -> bool:
        """检查用户是否有指定权限"""
        if self.is_admin:
            return True
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """检查用户是否有任意一个权限"""
        return any(self.has_permission(p) for p in permissions)
    
    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """检查用户是否有所有权限"""
        return all(self.has_permission(p) for p in permissions)
    
    def is_locked(self) -> bool:
        """检查用户是否被锁定"""
        if not self.locked_until:
            return False
        return datetime.now() < self.locked_until
    
    def increment_failed_attempts(self, max_attempts: int = 5, lock_duration: int = 1800) -> None:
        """增加失败登录次数"""
        self.failed_login_attempts += 1
        
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.now() + timedelta(seconds=lock_duration)
            logger.warning("User account locked", user_id=self.id, attempts=self.failed_login_attempts)
    
    def reset_failed_attempts(self) -> None:
        """重置失败登录次数"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login = datetime.now()


@dataclass
class SecurityToken:
    """安全令牌"""
    token: str
    user_id: str
    token_type: str  # "access", "refresh", "api"
    permissions: Set[Permission] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """检查令牌是否过期"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at
    
    def has_permission(self, permission: Permission) -> bool:
        """检查令牌是否有指定权限"""
        if Permission.ADMIN in self.permissions:
            return True
        return permission in self.permissions


class EncryptionService:
    """加密服务"""
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or settings.security.secret_key
        self._fernet = None
        self._initialize_fernet()
    
    def _initialize_fernet(self) -> None:
        """初始化Fernet实例"""
        try:
            # 从密钥生成Fernet实例
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'moltbot_salt_2024',  # 生产环境中应该使用随机盐
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.secret_key.encode()))
            self._fernet = Fernet(key)
        except Exception as e:
            logger.error("Failed to initialize encryption service", error=str(e))
            raise
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """加密数据"""
        if isinstance(data, str):
            data = data.encode()
        
        try:
            encrypted_data = self._fernet.encrypt(data)
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self._fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            raise
    
    def hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """验证密码"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error("Password verification failed", error=str(e))
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """生成安全令牌"""
        return secrets.token_urlsafe(length)
    
    def hash_data(self, data: str, salt: Optional[str] = None) -> str:
        """数据哈希"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        hasher = hashlib.pbkdf2_hmac(
            'sha256',
            data.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return f"{salt}:{hasher.hexdigest()}"
    
    def verify_hash(self, data: str, hashed: str) -> bool:
        """验证哈希"""
        try:
            salt, hash_value = hashed.split(':')
            computed_hash = hashlib.pbkdf2_hmac(
                'sha256',
                data.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return secrets.compare_digest(hash_value, computed_hash.hexdigest())
        except Exception:
            return False


class JWTService:
    """JWT令牌服务"""
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or settings.security.jwt_secret_key
        self.algorithm = settings.security.jwt_algorithm
    
    def create_token(
        self,
        user_id: str,
        permissions: List[str] = None,
        expires_in_hours: int = None,
        token_type: str = "access"
    ) -> str:
        """创建JWT令牌"""
        if expires_in_hours is None:
            expires_in_hours = settings.security.jwt_expire_hours
        
        expire_time = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        payload = {
            "user_id": user_id,
            "permissions": permissions or [],
            "token_type": token_type,
            "exp": expire_time,
            "iat": datetime.utcnow(),
            "iss": "moltbot"
        }
        
        try:
            token = pyjwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            return token
        except Exception as e:
            logger.error("JWT token creation failed", error=str(e))
            raise
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = pyjwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            return payload
        except pyjwt.ExpiredSignatureError:
            logger.warning("JWT token expired", token=token[:20])
            return None
        except pyjwt.InvalidTokenError as e:
            logger.error("Invalid JWT token", error=str(e), token=token[:20])
            return None
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解码JWT令牌（不验证过期时间）"""
        try:
            # 使用"none"算法解码，用于检查令牌结构
            payload = pyjwt.decode(
                token, 
                options={"verify_signature": False}
            )
            return payload
        except Exception as e:
            logger.error("JWT token decode failed", error=str(e))
            return None


class AuthenticationService:
    """身份认证服务"""
    
    def __init__(self, encryption_service: EncryptionService, jwt_service: JWTService):
        self.encryption = encryption_service
        self.jwt = jwt_service
        self.logger = get_logger(self.__class__.__name__)
        
        # 内存用户存储（生产环境应使用数据库）
        self.users: Dict[str, User] = {}
        self.tokens: Dict[str, SecurityToken] = {}
        
        # 创建默认管理员用户
        self._create_default_admin()
    
    def _create_default_admin(self) -> None:
        """创建默认管理员用户"""
        admin_id = "admin"
        if admin_id not in self.users:
            admin_user = User(
                id=admin_id,
                username="admin",
                email="admin@moltbot.local",
                is_admin=True,
                permissions={Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.ADMIN}
            )
            self.users[admin_id] = admin_user
            self.logger.info("Default admin user created", user_id=admin_id)
    
    async def register_user(
        self,
        username: str,
        password: str,
        email: Optional[str] = None,
        permissions: List[Permission] = None
    ) -> User:
        """注册用户"""
        user_id = f"user_{len(self.users) + 1}"
        
        # 检查用户名是否已存在
        if any(user.username == username for user in self.users.values()):
            raise ValueError("Username already exists")
        
        # 创建用户
        user = User(
            id=user_id,
            username=username,
            email=email,
            hashed_password=self.encryption.hash_password(password),
            permissions=set(permissions) if permissions else {Permission.READ}
        )
        
        self.users[user_id] = user
        self.logger.info("User registered", user_id=user_id, username=username)
        
        return user
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """用户身份认证"""
        # 查找用户
        user = next((u for u in self.users.values() if u.username == username), None)
        
        if not user:
            self.logger.warning("Login attempt with non-existent username", username=username)
            return None
        
        # 检查用户是否被锁定
        if user.is_locked():
            self.logger.warning("Login attempt with locked account", user_id=user.id)
            return None
        
        # 验证密码
        if not self.encryption.verify_password(password, user.hashed_password):
            user.increment_failed_attempts()
            self.logger.warning("Failed login attempt", 
                              user_id=user.id, 
                              attempts=user.failed_login_attempts)
            return None
        
        # 认证成功
        user.reset_failed_attempts()
        self.logger.info("User authenticated", user_id=user.id, username=username)
        
        return user
    
    async def create_access_token(self, user: User, expires_in_hours: int = 1) -> str:
        """创建访问令牌"""
        token = self.jwt.create_token(
            user_id=user.id,
            permissions=[p.value for p in user.permissions],
            expires_in_hours=expires_in_hours,
            token_type="access"
        )
        
        # 创建令牌记录
        security_token = SecurityToken(
            token=token,
            user_id=user.id,
            token_type="access",
            permissions=user.permissions,
            expires_at=datetime.now() + timedelta(hours=expires_in_hours)
        )
        
        self.tokens[token] = security_token
        return token
    
    async def verify_token(self, token: str) -> Optional[SecurityToken]:
        """验证令牌"""
        payload = self.jwt.verify_token(token)
        
        if not payload:
            return None
        
        token_record = self.tokens.get(token)
        if not token_record:
            self.logger.warning("Token not found in registry", token=token[:20])
            return None
        
        if token_record.is_expired():
            del self.tokens[token]
            self.logger.warning("Token expired", token=token[:20])
            return None
        
        return token_record
    
    async def revoke_token(self, token: str) -> bool:
        """撤销令牌"""
        if token in self.tokens:
            del self.tokens[token]
            self.logger.info("Token revoked", token=token[:20])
            return True
        return False
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户"""
        return self.users.get(user_id)
    
    async def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """获取用户权限"""
        user = await self.get_user_by_id(user_id)
        return user.permissions if user else set()
    
    async def update_user_permissions(self, user_id: str, permissions: List[Permission]) -> bool:
        """更新用户权限"""
        user = await self.get_user_by_id(user_id)
        if user:
            user.permissions = set(permissions)
            self.logger.info("User permissions updated", 
                           user_id=user_id, 
                           permissions=[p.value for p in permissions])
            return True
        return False


class AuthorizationService:
    """授权服务"""
    
    def __init__(self, auth_service: AuthenticationService):
        self.auth = auth_service
        self.logger = get_logger(self.__class__.__name__)
    
    async def check_permission(self, user_id: str, permission: Permission) -> bool:
        """检查用户权限"""
        user = await self.auth.get_user_by_id(user_id)
        return user.has_permission(permission) if user else False
    
    async def require_permission(self, user_id: str, permission: Permission) -> bool:
        """要求指定权限"""
        if not await self.check_permission(user_id, permission):
            self.logger.warning("Permission denied", 
                              user_id=user_id, 
                              permission=permission.value)
            raise PermissionError(f"Permission {permission.value} required")
        return True
    
    async def require_any_permission(self, user_id: str, permissions: List[Permission]) -> bool:
        """要求任意一个权限"""
        has_permission = await self.auth.get_user_by_id(user_id)
        if has_permission and has_permission.has_any_permission(permissions):
            return True
        
        self.logger.warning("Permission denied", 
                          user_id=user_id, 
                          required_permissions=[p.value for p in permissions])
        raise PermissionError(f"One of {', '.join(p.value for p in permissions)} required")
    
    async def require_admin(self, user_id: str) -> bool:
        """要求管理员权限"""
        user = await self.auth.get_user_by_id(user_id)
        if not user or not user.is_admin:
            self.logger.warning("Admin access denied", user_id=user_id)
            raise PermissionError("Admin access required")
        return True


class SecurityManager:
    """安全管理器"""
    
    def __init__(self):
        self.encryption = EncryptionService()
        self.jwt = JWTService()
        self.auth = AuthenticationService(self.encryption, self.jwt)
        self.authorization = AuthorizationService(self.auth)
        self.logger = get_logger(self.__class__.__name__)
    
    @asynccontextmanager
    async def secure_context(self, user_id: str):
        """安全上下文管理器"""
        token = None
        try:
            # 验证用户
            user = await self.auth.get_user_by_id(user_id)
            if not user:
                raise PermissionError("User not found")
            
            if user.is_locked():
                raise PermissionError("User account is locked")
            
            # 创建访问令牌
            token = await self.auth.create_access_token(user)
            
            yield {
                "user": user,
                "token": token,
                "auth_service": self.auth,
                "authz_service": self.authorization
            }
            
        except Exception as e:
            self.logger.error("Secure context error", user_id=user_id, error=str(e))
            raise
        finally:
            if token:
                await self.auth.revoke_token(token)


# 全局安全管理器实例
_security_manager: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    """获取全局安全管理器"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager


# 便利函数
async def authenticate_user(username: str, password: str) -> Optional[User]:
    """用户认证便利函数"""
    manager = get_security_manager()
    return await manager.auth.authenticate_user(username, password)


async def create_access_token(user: User) -> str:
    """创建访问令牌便利函数"""
    manager = get_security_manager()
    return await manager.auth.create_access_token(user)


async def verify_token(token: str) -> Optional[SecurityToken]:
    """验证令牌便利函数"""
    manager = get_security_manager()
    return await manager.auth.verify_token(token)


async def check_permission(user_id: str, permission: Permission) -> bool:
    """检查权限便利函数"""
    manager = get_security_manager()
    return await manager.authorization.check_permission(user_id, permission)