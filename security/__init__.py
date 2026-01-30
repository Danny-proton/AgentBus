"""
AgentBus Security System

基于Moltbot安全架构的AgentBus安全系统实现。
提供认证、授权、限流、加密等安全功能。
"""

from .auth import (
    AuthenticationManager,
    TokenManager,
    JWTManager,
    OAuthManager,
    APIKeyManager,
    User,
    AuthToken,
    LoginAttempt,
)
from .permissions import (
    PermissionManager,
    RoleManager,
    UserRole,
    Permission,
    Role,
    PermissionChecker,
)
from .rate_limiter import (
    RateLimiter,
    TokenBucket,
    SlidingWindow,
    FixedWindow,
    RateLimitRule,
)
from .encryption import (
    EncryptionManager,
    KeyManager,
    SecureStorage,
    CryptoUtils,
)

__all__ = [
    # Authentication
    "AuthenticationManager",
    "TokenManager", 
    "JWTManager",
    "OAuthManager",
    "APIKeyManager",
    "User",
    "AuthToken",
    "LoginAttempt",
    
    # Permissions
    "PermissionManager",
    "RoleManager", 
    "UserRole",
    "Permission",
    "Role",
    "PermissionChecker",
    
    # Rate Limiting
    "RateLimiter",
    "TokenBucket",
    "SlidingWindow", 
    "FixedWindow",
    "RateLimitRule",
    
    # Encryption
    "EncryptionManager",
    "KeyManager",
    "SecureStorage",
    "CryptoUtils",
]

__version__ = "1.0.0"
__author__ = "AgentBus Security Team"