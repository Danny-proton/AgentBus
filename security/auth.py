"""
认证系统 - Authentication System

提供用户认证、令牌管理、JWT、OAuth等功能。
基于Moltbot的安全架构设计，支持多种认证方式。
"""

import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import jwt
import bcrypt
from ..core.settings import Settings
from ..storage.database import Database
from ..storage.memory import MemoryStorage


class AuthProvider(Enum):
    """认证提供商"""
    LOCAL = "local"
    OAUTH_GOOGLE = "google"
    OAUTH_GITHUB = "github"
    OAUTH_MICROSOFT = "microsoft"
    API_KEY = "api_key"
    JWT = "jwt"


class TokenType(Enum):
    """令牌类型"""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    MAGIC_LINK = "magic_link"


@dataclass
class User:
    """用户模型"""
    id: str
    username: str
    email: str
    hashed_password: str
    is_active: bool = True
    is_verified: bool = False
    roles: List[str] = None
    permissions: List[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    provider: AuthProvider = AuthProvider.LOCAL
    provider_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.permissions is None:
            self.permissions = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，排除敏感信息"""
        data = asdict(self)
        data.pop('hashed_password', None)
        return data


@dataclass
class AuthToken:
    """认证令牌"""
    token: str
    token_type: TokenType
    user_id: str
    expires_at: datetime
    created_at: datetime
    revoked: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def is_expired(self) -> bool:
        """检查令牌是否过期"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """检查令牌是否有效"""
        return not self.revoked and not self.is_expired


@dataclass
class LoginAttempt:
    """登录尝试记录"""
    id: str
    user_id: Optional[str]
    email: str
    ip_address: str
    user_agent: str
    success: bool
    timestamp: datetime
    failure_reason: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class TokenManager:
    """令牌管理器"""
    
    def __init__(self, db: Database, memory: MemoryStorage):
        self.db = db
        self.memory = memory
        self._active_tokens: Dict[str, AuthToken] = {}
    
    def generate_token(self, user_id: str, token_type: TokenType, 
                      expires_in: int = 3600, metadata: Dict[str, Any] = None) -> AuthToken:
        """生成令牌"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        auth_token = AuthToken(
            token=token,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        # 存储到数据库和内存
        self._store_token(auth_token)
        
        return auth_token
    
    def verify_token(self, token: str) -> Optional[AuthToken]:
        """验证令牌"""
        # 先检查内存缓存
        if token in self._active_tokens:
            cached_token = self._active_tokens[token]
            if cached_token.is_valid:
                return cached_token
        
        # 从数据库查询
        token_data = self.memory.get(f"token:{token}")
        if token_data:
            try:
                token_dict = json.loads(token_data)
                auth_token = AuthToken(**token_dict)
                if auth_token.is_valid:
                    # 更新缓存
                    self._active_tokens[token] = auth_token
                    return auth_token
            except (json.JSONDecodeError, TypeError):
                pass
        
        return None
    
    def revoke_token(self, token: str) -> bool:
        """撤销令牌"""
        # 从内存移除
        self._active_tokens.pop(token, None)
        
        # 从内存存储移除
        self.memory.delete(f"token:{token}")
        
        # 更新数据库状态
        # 这里应该实现数据库更新逻辑
        
        return True
    
    def revoke_all_user_tokens(self, user_id: str) -> int:
        """撤销用户所有令牌"""
        revoked_count = 0
        
        # 清理内存中的令牌
        tokens_to_remove = []
        for token, auth_token in self._active_tokens.items():
            if auth_token.user_id == user_id:
                tokens_to_remove.append(token)
        
        for token in tokens_to_remove:
            self.revoke_token(token)
            revoked_count += 1
        
        # 这里应该实现数据库批量更新逻辑
        
        return revoked_count
    
    def _store_token(self, auth_token: AuthToken):
        """存储令牌"""
        # 存储到内存缓存
        self._active_tokens[auth_token.token] = auth_token
        
        # 存储到内存存储（用于持久化）
        token_data = json.dumps(asdict(auth_token), default=str)
        self.memory.set(f"token:{auth_token.token}", token_data, 
                        ttl=int((auth_token.expires_at - datetime.utcnow()).total_seconds()))


class JWTManager:
    """JWT令牌管理器"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def encode_token(self, payload: Dict[str, Any], expires_in: int = 3600) -> str:
        """编码JWT令牌"""
        now = datetime.utcnow()
        payload.update({
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
            "nbf": now
        })
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """解码JWT令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def create_access_token(self, user_id: str, permissions: List[str] = None) -> str:
        """创建访问令牌"""
        payload = {
            "sub": user_id,
            "type": "access",
            "permissions": permissions or []
        }
        return self.encode_token(payload)
    
    def create_refresh_token(self, user_id: str) -> str:
        """创建刷新令牌"""
        payload = {
            "sub": user_id,
            "type": "refresh"
        }
        return self.encode_token(payload, expires_in=7 * 24 * 3600)  # 7天


class APIKeyManager:
    """API密钥管理器"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def generate_api_key(self, user_id: str, name: str, 
                        permissions: List[str] = None) -> str:
        """生成API密钥"""
        # 生成API密钥
        api_key = f"ab_{secrets.token_urlsafe(32)}"
        
        # 计算密钥哈希
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # 存储到数据库
        # 这里应该实现具体的数据库插入逻辑
        
        return api_key
    
    def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """验证API密钥"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # 从数据库查询
        # 这里应该实现具体的数据库查询逻辑
        
        return None
    
    def revoke_api_key(self, api_key: str) -> bool:
        """撤销API密钥"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # 从数据库删除
        # 这里应该实现具体的数据库删除逻辑
        
        return True


class OAuthManager:
    """OAuth管理器"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.providers = {
            AuthProvider.OAUTH_GOOGLE: self._google_oauth,
            AuthProvider.OAUTH_GITHUB: self._github_oauth,
            AuthProvider.OAUTH_MICROSOFT: self._microsoft_oauth,
        }
    
    async def authenticate_oauth(self, provider: AuthProvider, 
                                auth_code: str, redirect_uri: str) -> Optional[User]:
        """OAuth认证"""
        if provider not in self.providers:
            return None
        
        try:
            return await self.providers[provider](auth_code, redirect_uri)
        except Exception:
            return None
    
    async def _google_oauth(self, auth_code: str, redirect_uri: str) -> Optional[User]:
        """Google OAuth认证"""
        # 这里应该实现Google OAuth逻辑
        # 使用google-auth库进行实际认证
        pass
    
    async def _github_oauth(self, auth_code: str, redirect_uri: str) -> Optional[User]:
        """GitHub OAuth认证"""
        # 这里应该实现GitHub OAuth逻辑
        pass
    
    async def _microsoft_oauth(self, auth_code: str, redirect_uri: str) -> Optional[User]:
        """Microsoft OAuth认证"""
        # 这里应该实现Microsoft OAuth逻辑
        pass


class AuthenticationManager:
    """认证管理器"""
    
    def __init__(self, settings: Settings, db: Database, memory: MemoryStorage):
        self.settings = settings
        self.db = db
        self.memory = memory
        self.token_manager = TokenManager(db, memory)
        self.jwt_manager = JWTManager(settings.SECRET_KEY)
        self.api_key_manager = APIKeyManager(db)
        self.oauth_manager = OAuthManager(settings)
        
        # 配置
        self.max_failed_attempts = 5
        self.lockout_duration = 900  # 15分钟
        self.password_min_length = 8
    
    async def register_user(self, username: str, email: str, password: str,
                          roles: List[str] = None) -> User:
        """注册用户"""
        # 检查用户是否已存在
        if await self.get_user_by_email(email):
            raise ValueError("用户已存在")
        
        # 验证密码强度
        self._validate_password(password)
        
        # 哈希密码
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # 创建用户
        user = User(
            id=secrets.token_urlsafe(16),
            username=username,
            email=email,
            hashed_password=hashed_password,
            roles=roles or ["user"],
            provider=AuthProvider.LOCAL
        )
        
        # 存储用户
        await self._store_user(user)
        
        return user
    
    async def authenticate_user(self, email: str, password: str, 
                               ip_address: str = None, user_agent: str = None) -> Optional[AuthToken]:
        """用户认证"""
        # 获取用户
        user = await self.get_user_by_email(email)
        if not user:
            await self._record_login_attempt(None, email, ip_address, user_agent, False, "用户不存在")
            return None
        
        # 检查用户状态
        if not user.is_active:
            await self._record_login_attempt(user.id, email, ip_address, user_agent, False, "用户已被禁用")
            return None
        
        # 检查账户锁定
        if user.locked_until and datetime.utcnow() < user.locked_until:
            await self._record_login_attempt(user.id, email, ip_address, user_agent, False, "账户已锁定")
            return None
        
        # 验证密码
        if not bcrypt.checkpw(password.encode('utf-8'), user.hashed_password.encode('utf-8')):
            await self._handle_failed_login(user, email, ip_address, user_agent)
            return None
        
        # 登录成功
        await self._handle_successful_login(user, ip_address, user_agent)
        
        # 生成访问令牌
        access_token = self.token_manager.generate_token(
            user_id=user.id,
            token_type=TokenType.ACCESS,
            expires_in=3600
        )
        
        # 生成JWT令牌
        jwt_token = self.jwt_manager.create_access_token(user.id, user.permissions)
        
        return access_token
    
    async def verify_token(self, token: str) -> Optional[AuthToken]:
        """验证令牌"""
        return self.token_manager.verify_token(token)
    
    async def refresh_token(self, refresh_token: str) -> Optional[AuthToken]:
        """刷新令牌"""
        # 验证刷新令牌
        token = self.token_manager.verify_token(refresh_token)
        if not token or token.token_type != TokenType.REFRESH:
            return None
        
        # 生成新的访问令牌
        new_access_token = self.token_manager.generate_token(
            user_id=token.user_id,
            token_type=TokenType.ACCESS,
            expires_in=3600
        )
        
        return new_access_token
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据ID获取用户"""
        user_data = self.memory.get(f"user:{user_id}")
        if user_data:
            try:
                user_dict = json.loads(user_data)
                return User(**user_dict)
            except (json.JSONDecodeError, TypeError):
                pass
        
        # 从数据库查询
        # 这里应该实现具体的数据库查询逻辑
        
        return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        # 从缓存查询
        user_id = self.memory.get(f"email:{email}")
        if user_id:
            return await self.get_user_by_id(user_id)
        
        # 从数据库查询
        # 这里应该实现具体的数据库查询逻辑
        
        return None
    
    async def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        # 验证旧密码
        if not bcrypt.checkpw(old_password.encode('utf-8'), user.hashed_password.encode('utf-8')):
            return False
        
        # 验证新密码强度
        self._validate_password(new_password)
        
        # 哈希新密码
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # 更新用户
        user.hashed_password = hashed_password
        user.updated_at = datetime.utcnow()
        
        # 撤销所有现有令牌
        self.token_manager.revoke_all_user_tokens(user_id)
        
        # 存储更新后的用户
        await self._store_user(user)
        
        return True
    
    async def reset_password(self, email: str, reset_token: str, new_password: str) -> bool:
        """重置密码"""
        # 验证重置令牌
        if not self._verify_reset_token(email, reset_token):
            return False
        
        user = await self.get_user_by_email(email)
        if not user:
            return False
        
        # 验证新密码强度
        self._validate_password(new_password)
        
        # 哈希新密码
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # 更新用户
        user.hashed_password = hashed_password
        user.updated_at = datetime.utcnow()
        
        # 撤销所有现有令牌
        self.token_manager.revoke_all_user_tokens(user_id)
        
        # 存储更新后的用户
        await self._store_user(user)
        
        # 清理重置令牌
        self._clear_reset_token(email)
        
        return True
    
    def _validate_password(self, password: str):
        """验证密码强度"""
        if len(password) < self.password_min_length:
            raise ValueError(f"密码长度至少{self.password_min_length}位")
        
        if not any(c.isupper() for c in password):
            raise ValueError("密码必须包含至少一个大写字母")
        
        if not any(c.islower() for c in password):
            raise ValueError("密码必须包含至少一个小写字母")
        
        if not any(c.isdigit() for c in password):
            raise ValueError("密码必须包含至少一个数字")
    
    async def _handle_failed_login(self, user: User, email: str, 
                                  ip_address: str, user_agent: str):
        """处理登录失败"""
        user.failed_login_attempts += 1
        
        # 检查是否需要锁定账户
        if user.failed_login_attempts >= self.max_failed_attempts:
            user.locked_until = datetime.utcnow() + timedelta(seconds=self.lockout_duration)
        
        user.updated_at = datetime.utcnow()
        
        # 存储更新后的用户
        await self._store_user(user)
        
        # 记录登录尝试
        await self._record_login_attempt(
            user.id, email, ip_address, user_agent, False, "密码错误"
        )
    
    async def _handle_successful_login(self, user: User, ip_address: str, user_agent: str):
        """处理登录成功"""
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        
        # 存储更新后的用户
        await self._store_user(user)
        
        # 记录登录尝试
        await self._record_login_attempt(
            user.id, user.email, ip_address, user_agent, True
        )
    
    async def _store_user(self, user: User):
        """存储用户"""
        # 存储到内存缓存
        user_data = json.dumps(asdict(user), default=str)
        self.memory.set(f"user:{user.id}", user_data)
        self.memory.set(f"email:{user.email}", user.id)
    
    async def _record_login_attempt(self, user_id: Optional[str], email: str,
                                   ip_address: str, user_agent: str, 
                                   success: bool, failure_reason: str = None):
        """记录登录尝试"""
        attempt = LoginAttempt(
            id=secrets.token_urlsafe(16),
            user_id=user_id,
            email=email,
            ip_address=ip_address or "unknown",
            user_agent=user_agent or "unknown",
            success=success,
            timestamp=datetime.utcnow(),
            failure_reason=failure_reason
        )
        
        # 存储到内存
        attempt_data = json.dumps(asdict(attempt), default=str)
        self.memory.set(f"login_attempt:{attempt.id}", attempt_data)
    
    def _generate_reset_token(self, email: str) -> str:
        """生成重置令牌"""
        token = secrets.token_urlsafe(32)
        self.memory.set(f"reset_token:{email}:{token}", "1", ttl=3600)  # 1小时有效
        return token
    
    def _verify_reset_token(self, email: str, token: str) -> bool:
        """验证重置令牌"""
        return self.memory.get(f"reset_token:{email}:{token}") is not None
    
    def _clear_reset_token(self, email: str):
        """清理重置令牌"""
        # 这里应该清理所有相关的重置令牌
        # 简化实现，实际应该删除所有以 reset_token:{email}: 开头的键
        pass