"""
Gateway Authentication Module

基于Moltbot的认证系统，支持多种认证方式：
- Token认证
- 密码认证  
- 设备认证
- Tailscale集成
"""

import hashlib
import secrets
import time
from enum import Enum
from typing import Dict, Optional, Set, Any, Callable
from dataclasses import dataclass, field
import hmac
import logging

logger = logging.getLogger(__name__)


class AuthMode(Enum):
    """认证模式枚举"""
    TOKEN = "token"
    PASSWORD = "password" 
    DEVICE = "device"
    TAILSCALE = "tailscale"
    MULTI = "multi"


@dataclass
class AuthConfig:
    """认证配置"""
    mode: AuthMode = AuthMode.TOKEN
    token: Optional[str] = None
    password: Optional[str] = None
    device_tokens: Dict[str, str] = field(default_factory=dict)
    allow_tailscale: bool = False
    trusted_proxies: Set[str] = field(default_factory=set)
    max_failed_attempts: int = 5
    lockout_duration: int = 300  # 5分钟


@dataclass
class AuthResult:
    """认证结果"""
    success: bool
    method: Optional[AuthMode] = None
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    scopes: Set[str] = field(default_factory=set)
    reason: Optional[str] = None
    expires_at: Optional[float] = None


@dataclass
class DeviceIdentity:
    """设备身份标识"""
    device_id: str
    public_key: str
    signature: str
    created_at: float = field(default_factory=time.time)


class GatewayAuth:
    """网关认证管理器"""
    
    def __init__(self, config: AuthConfig):
        self.config = config
        self.failed_attempts: Dict[str, int] = {}
        self.locked_accounts: Set[str] = set()
        self.device_tokens: Dict[str, DeviceIdentity] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
    def _is_locked(self, identifier: str) -> bool:
        """检查账户是否被锁定"""
        return identifier in self.locked_accounts
    
    def _check_failed_attempts(self, identifier: str) -> bool:
        """检查失败尝试次数"""
        attempts = self.failed_attempts.get(identifier, 0)
        if attempts >= self.config.max_failed_attempts:
            self.locked_accounts.add(identifier)
            logger.warning(f"Account {identifier} locked due to too many failed attempts")
            return True
        return False
    
    def _clear_failed_attempts(self, identifier: str):
        """清除失败尝试记录"""
        self.failed_attempts.pop(identifier, None)
        self.locked_accounts.discard(identifier)
    
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        salt = secrets.token_bytes(32)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return f"{salt.hex()}:{password_hash.hex()}"
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """验证密码"""
        try:
            salt_hex, hash_hex = hashed.split(':')
            salt = bytes.fromhex(salt_hex)
            expected_hash = bytes.fromhex(hash_hex)
            actual_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
            return hmac.compare_digest(actual_hash, expected_hash)
        except (ValueError, Exception):
            return False
    
    def authenticate_token(self, token: str, client_info: Optional[Dict] = None) -> AuthResult:
        """Token认证"""
        if self._is_locked("token"):
            return AuthResult(success=False, reason="Token authentication locked")
        
        if self.config.token and hmac.compare_digest(token, self.config.token):
            self._clear_failed_attempts("token")
            return AuthResult(
                success=True,
                method=AuthMode.TOKEN,
                user_id="gateway_token_user",
                scopes={"admin", "operator"}
            )
        else:
            self.failed_attempts["token"] = self.failed_attempts.get("token", 0) + 1
            if self._check_failed_attempts("token"):
                return AuthResult(success=False, reason="Account locked due to too many failures")
            return AuthResult(success=False, reason="Invalid token")
    
    def authenticate_password(self, password: str, client_info: Optional[Dict] = None) -> AuthResult:
        """密码认证"""
        if self._is_locked("password"):
            return AuthResult(success=False, reason="Password authentication locked")
        
        if self.config.password and self._verify_password(password, self.config.password):
            self._clear_failed_attempts("password")
            return AuthResult(
                success=True,
                method=AuthMode.PASSWORD,
                user_id="gateway_password_user",
                scopes={"admin", "operator"}
            )
        else:
            self.failed_attempts["password"] = self.failed_attempts.get("password", 0) + 1
            if self._check_failed_attempts("password"):
                return AuthResult(success=False, reason="Account locked due to too many failures")
            return AuthResult(success=False, reason="Invalid password")
    
    def authenticate_device(self, device_id: str, signature: str, nonce: str, timestamp: float) -> AuthResult:
        """设备认证"""
        # 验证时间戳（防重放攻击）
        current_time = time.time()
        if abs(current_time - timestamp) > 300:  # 5分钟窗口
            return AuthResult(success=False, reason="Authentication timestamp too old")
        
        device_identity = self.device_tokens.get(device_id)
        if not device_identity:
            return AuthResult(success=False, reason="Unknown device")
        
        # 验证签名
        message = f"{device_id}:{nonce}:{timestamp}"
        expected_signature = self._sign_message(device_identity.public_key, message)
        
        if not hmac.compare_digest(signature, expected_signature):
            return AuthResult(success=False, reason="Invalid device signature")
        
        return AuthResult(
            success=True,
            method=AuthMode.DEVICE,
            device_id=device_id,
            scopes={"device", "operator"}
        )
    
    def authenticate_tailscale(self, client_ip: str, user_info: Optional[Dict] = None) -> AuthResult:
        """Tailscale认证"""
        if not self.config.allow_tailscale:
            return AuthResult(success=False, reason="Tailscale authentication not allowed")
        
        # 这里需要实际的Tailscale WHOIS查询
        # 简化实现
        if user_info and user_info.get("login"):
            return AuthResult(
                success=True,
                method=AuthMode.TAILSCALE,
                user_id=user_info["login"],
                scopes={"tailscale_user"}
            )
        
        return AuthResult(success=False, reason="Tailscale user not found")
    
    def _sign_message(self, public_key: str, message: str) -> str:
        """消息签名（简化实现）"""
        # 这里应该使用实际的加密签名
        return hashlib.sha256(f"{public_key}:{message}".encode()).hexdigest()
    
    def register_device(self, device_id: str, public_key: str) -> DeviceIdentity:
        """注册设备"""
        signature = self._sign_message(public_key, device_id)
        device_identity = DeviceIdentity(
            device_id=device_id,
            public_key=public_key,
            signature=signature
        )
        self.device_tokens[device_id] = device_identity
        return device_identity
    
    def revoke_device(self, device_id: str):
        """撤销设备"""
        self.device_tokens.pop(device_id, None)
    
    def create_session(self, auth_result: AuthResult, client_info: Dict) -> str:
        """创建会话"""
        session_id = secrets.token_urlsafe(32)
        session_data = {
            "auth_result": auth_result,
            "client_info": client_info,
            "created_at": time.time(),
            "last_activity": time.time()
        }
        self.active_sessions[session_id] = session_data
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[AuthResult]:
        """验证会话"""
        session_data = self.active_sessions.get(session_id)
        if not session_data:
            return None
        
        # 检查会话是否过期（24小时）
        if time.time() - session_data["created_at"] > 86400:
            self.active_sessions.pop(session_id, None)
            return None
        
        # 更新最后活动时间
        session_data["last_activity"] = time.time()
        return session_data["auth_result"]
    
    def revoke_session(self, session_id: str):
        """撤销会话"""
        self.active_sessions.pop(session_id, None)
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = time.time()
        expired_sessions = [
            sid for sid, data in self.active_sessions.items()
            if current_time - data["created_at"] > 86400
        ]
        for session_id in expired_sessions:
            self.active_sessions.pop(session_id, None)


def create_default_auth() -> GatewayAuth:
    """创建默认认证配置"""
    config = AuthConfig(
        mode=AuthMode.TOKEN,
        token=secrets.token_urlsafe(32),
        allow_tailscale=False
    )
    return GatewayAuth(config)