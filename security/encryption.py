"""
加密工具 - Encryption Utilities

提供数据加密、解密、密钥管理、安全存储等功能。
支持多种加密算法和安全标准。
"""

import base64
import hashlib
import hmac
import os
import secrets
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import padding as crypto_padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.hmac import HMAC
from ..core.settings import Settings
from ..storage.database import Database
from ..storage.memory import MemoryStorage


@dataclass
class EncryptionKey:
    """加密密钥"""
    key_id: str
    key_type: str  # 'symmetric', 'asymmetric_public', 'asymmetric_private'
    algorithm: str  # 'AES-256', 'RSA-2048', etc.
    key_data: bytes
    created_at: float
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def is_expired(self) -> bool:
        """检查密钥是否过期"""
        if not self.expires_at:
            return False
        return time.time() > self.expires_at


@dataclass
class SecureData:
    """安全数据"""
    data_id: str
    encrypted_data: bytes
    encryption_algorithm: str
    key_id: str
    iv: Optional[bytes] = None
    auth_tag: Optional[bytes] = None
    created_at: float = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
        if self.metadata is None:
            self.metadata = {}


class CryptoUtils:
    """加密工具类"""
    
    @staticmethod
    def generate_symmetric_key(algorithm: str = "AES-256") -> bytes:
        """生成对称密钥"""
        if algorithm == "AES-256":
            return Fernet.generate_key()
        elif algorithm == "AES-128":
            return os.urandom(16)
        else:
            raise ValueError(f"不支持的对称算法: {algorithm}")
    
    @staticmethod
    def generate_asymmetric_key_pair(key_size: int = 2048) -> Tuple[bytes, bytes]:
        """生成非对称密钥对"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        
        # 序列化为PEM格式
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem, public_pem
    
    @staticmethod
    def derive_key_from_password(password: str, salt: bytes = None, 
                               iterations: int = 100000) -> Tuple[bytes, bytes]:
        """从密码派生密钥"""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )
        
        key = kdf.derive(password.encode())
        return key, salt
    
    @staticmethod
    def generate_random_bytes(length: int) -> bytes:
        """生成随机字节"""
        return secrets.token_bytes(length)
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """生成安全令牌"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_password(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        """哈希密码"""
        if salt is None:
            salt = os.urandom(32)
        
        # 使用PBKDF2哈希密码
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
        return dk, salt
    
    @staticmethod
    def verify_password(password: str, hashed: bytes, salt: bytes) -> bool:
        """验证密码"""
        new_hash, _ = CryptoUtils.hash_password(password, salt)
        return hmac.compare_digest(hashed, new_hash)
    
    @staticmethod
    def compute_hash(data: bytes, algorithm: str = "sha256") -> bytes:
        """计算数据哈希"""
        if algorithm == "sha256":
            return hashlib.sha256(data).digest()
        elif algorithm == "sha512":
            return hashlib.sha512(data).digest()
        elif algorithm == "md5":
            return hashlib.md5(data).digest()
        else:
            raise ValueError(f"不支持的哈希算法: {algorithm}")
    
    @staticmethod
    def compute_hmac(data: bytes, key: bytes, algorithm: str = "sha256") -> bytes:
        """计算HMAC"""
        if algorithm == "sha256":
            return hmac.new(key, data, hashlib.sha256).digest()
        elif algorithm == "sha512":
            return hmac.new(key, data, hashlib.sha512).digest()
        else:
            raise ValueError(f"不支持的HMAC算法: {algorithm}")
    
    @staticmethod
    def base64_encode(data: bytes) -> str:
        """Base64编码"""
        return base64.b64encode(data).decode()
    
    @staticmethod
    def base64_decode(data: str) -> bytes:
        """Base64解码"""
        return base64.b64decode(data.encode())
    
    @staticmethod
    def base64url_encode(data: bytes) -> str:
        """Base64URL编码"""
        return base64.urlsafe_b64encode(data).decode().rstrip('=')
    
    @staticmethod
    def base64url_decode(data: str) -> bytes:
        """Base64URL解码"""
        # 添加填充
        padding = 4 - (len(data) % 4)
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data.encode())


class AESEncryption:
    """AES加密实现"""
    
    @staticmethod
    def encrypt(plaintext: bytes, key: bytes) -> Tuple[bytes, bytes, bytes]:
        """AES加密"""
        if len(key) not in [16, 24, 32]:
            raise ValueError("密钥长度必须为16、24或32字节")
        
        # 生成随机IV
        iv = os.urandom(16)
        
        # 创建加密器
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # 添加PKCS7填充
        padder = crypto_padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext) + padder.finalize()
        
        # 加密
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # 获取认证标签（如果使用GCM模式）
        auth_tag = encryptor.tag if hasattr(encryptor, 'tag') else None
        
        return ciphertext, iv, auth_tag
    
    @staticmethod
    def decrypt(ciphertext: bytes, key: bytes, iv: bytes, 
                auth_tag: bytes = None) -> bytes:
        """AES解密"""
        if len(key) not in [16, 24, 32]:
            raise ValueError("密钥长度必须为16、24或32字节")
        
        # 创建解密器
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        # 解密
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # 验证认证标签（如果使用GCM模式）
        if auth_tag:
            decryptor.verify(auth_tag)
        
        # 移除PKCS7填充
        unpadder = crypto_padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_data) + unpadder.finalize()
        
        return plaintext


class RSAEncryption:
    """RSA加密实现"""
    
    @staticmethod
    def encrypt(plaintext: bytes, public_key_pem: bytes) -> bytes:
        """RSA公钥加密"""
        public_key = serialization.load_pem_public_key(
            public_key_pem,
            backend=default_backend()
        )
        
        # 使用OAEP填充
        ciphertext = public_key.encrypt(
            plaintext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return ciphertext
    
    @staticmethod
    def decrypt(ciphertext: bytes, private_key_pem: bytes) -> bytes:
        """RSA私钥解密"""
        private_key = serialization.load_pem_private_key(
            private_key_pem,
            password=None,
            backend=default_backend()
        )
        
        # 解密
        plaintext = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return plaintext
    
    @staticmethod
    def sign(data: bytes, private_key_pem: bytes) -> bytes:
        """RSA数字签名"""
        private_key = serialization.load_pem_private_key(
            private_key_pem,
            password=None,
            backend=default_backend()
        )
        
        signature = private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return signature
    
    @staticmethod
    def verify(data: bytes, signature: bytes, public_key_pem: bytes) -> bool:
        """RSA签名验证"""
        public_key = serialization.load_pem_public_key(
            public_key_pem,
            backend=default_backend()
        )
        
        try:
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False


class KeyManager:
    """密钥管理器"""
    
    def __init__(self, db: Database, memory: MemoryStorage):
        self.db = db
        self.memory = memory
        self._keys_cache: Dict[str, EncryptionKey] = {}
    
    async def generate_key(self, key_id: str, key_type: str, 
                          algorithm: str, expires_at: float = None,
                          metadata: Dict[str, Any] = None) -> EncryptionKey:
        """生成新密钥"""
        # 生成密钥数据
        if key_type == "symmetric":
            if algorithm == "AES-256":
                key_data = CryptoUtils.generate_symmetric_key("AES-256")
            else:
                raise ValueError(f"不支持的对称算法: {algorithm}")
        elif key_type in ["asymmetric_public", "asymmetric_private"]:
            private_pem, public_pem = CryptoUtils.generate_asymmetric_key_pair()
            key_data = private_pem if key_type == "asymmetric_private" else public_pem
        else:
            raise ValueError(f"不支持的密钥类型: {key_type}")
        
        encryption_key = EncryptionKey(
            key_id=key_id,
            key_type=key_type,
            algorithm=algorithm,
            key_data=key_data,
            created_at=time.time(),
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        # 存储密钥
        await self.store_key(encryption_key)
        
        return encryption_key
    
    async def store_key(self, key: EncryptionKey):
        """存储密钥"""
        # 更新缓存
        self._keys_cache[key.key_id] = key
        
        # 存储到内存（用于快速访问）
        key_data = base64.b64encode(key.key_data).decode()
        key_info = {
            "key_id": key.key_id,
            "key_type": key.key_type,
            "algorithm": key.algorithm,
            "key_data": key_data,
            "created_at": key.created_at,
            "expires_at": key.expires_at,
            "metadata": key.metadata,
            "is_active": key.is_active
        }
        
        key_json = __import__('json').dumps(key_info)
        self.memory.set(f"encryption_key:{key.key_id}", key_json)
    
    async def get_key(self, key_id: str) -> Optional[EncryptionKey]:
        """获取密钥"""
        # 先检查缓存
        if key_id in self._keys_cache:
            cached_key = self._keys_cache[key_id]
            if not cached_key.is_expired:
                return cached_key
            else:
                # 移除过期密钥
                await self.revoke_key(key_id)
                return None
        
        # 从内存存储查询
        key_data = self.memory.get(f"encryption_key:{key_id}")
        if key_data:
            try:
                import json
                key_info = json.loads(key_data)
                
                # 检查是否过期
                if key_info.get("expires_at") and time.time() > key_info["expires_at"]:
                    await self.revoke_key(key_id)
                    return None
                
                # 重建密钥对象
                encryption_key = EncryptionKey(
                    key_id=key_info["key_id"],
                    key_type=key_info["key_type"],
                    algorithm=key_info["algorithm"],
                    key_data=base64.b64decode(key_info["key_data"]),
                    created_at=key_info["created_at"],
                    expires_at=key_info.get("expires_at"),
                    metadata=key_info.get("metadata", {}),
                    is_active=key_info.get("is_active", True)
                )
                
                # 更新缓存
                self._keys_cache[key_id] = encryption_key
                return encryption_key
                
            except Exception:
                pass
        
        # 从数据库查询
        # 这里应该实现具体的数据库查询逻辑
        
        return None
    
    async def revoke_key(self, key_id: str) -> bool:
        """撤销密钥"""
        # 从缓存移除
        self._keys_cache.pop(key_id, None)
        
        # 从内存移除
        self.memory.delete(f"encryption_key:{key_id}")
        
        # 从数据库删除
        # 这里应该实现具体的数据库删除逻辑
        
        return True
    
    async def list_keys(self, key_type: str = None, active_only: bool = True) -> List[EncryptionKey]:
        """列出密钥"""
        keys = []
        
        # 从缓存获取
        for key in self._keys_cache.values():
            if key_type and key.key_type != key_type:
                continue
            if active_only and not key.is_active:
                continue
            if not key.is_expired:
                keys.append(key)
        
        # 从数据库获取
        # 这里应该实现具体的数据库查询逻辑
        
        return keys
    
    async def rotate_key(self, key_id: str) -> Optional[EncryptionKey]:
        """密钥轮换"""
        old_key = await self.get_key(key_id)
        if not old_key:
            return None
        
        # 生成新密钥
        new_key_id = f"{key_id}_rotated_{int(time.time())}"
        new_key = await self.generate_key(
            new_key_id,
            old_key.key_type,
            old_key.algorithm,
            old_key.expires_at,
            old_key.metadata
        )
        
        # 撤销旧密钥
        await self.revoke_key(key_id)
        
        return new_key


class EncryptionManager:
    """加密管理器"""
    
    def __init__(self, settings: Settings, db: Database, memory: MemoryStorage):
        self.settings = settings
        self.db = db
        self.memory = memory
        self.key_manager = KeyManager(db, memory)
        
        # 默认密钥ID
        self.default_key_id = "default_symmetric_key"
    
    async def initialize(self):
        """初始化加密管理器"""
        # 检查默认密钥是否存在
        default_key = await self.key_manager.get_key(self.default_key_id)
        if not default_key:
            # 创建默认密钥
            await self.key_manager.generate_key(
                self.default_key_id,
                "symmetric",
                "AES-256",
                metadata={"description": "默认对称密钥"}
            )
    
    async def encrypt_data(self, data: Union[str, bytes], key_id: str = None) -> SecureData:
        """加密数据"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        key_id = key_id or self.default_key_id
        
        # 获取加密密钥
        encryption_key = await self.key_manager.get_key(key_id)
        if not encryption_key:
            raise ValueError(f"加密密钥 {key_id} 不存在")
        
        if encryption_key.key_type != "symmetric":
            raise ValueError(f"密钥 {key_id} 不是对称密钥")
        
        # 使用AES加密
        ciphertext, iv, auth_tag = AESEncryption.encrypt(data, encryption_key.key_data)
        
        secure_data = SecureData(
            data_id=CryptoUtils.generate_token(16),
            encrypted_data=ciphertext,
            encryption_algorithm=encryption_key.algorithm,
            key_id=key_id,
            iv=iv,
            auth_tag=auth_tag,
            metadata={"encrypted_at": time.time()}
        )
        
        return secure_data
    
    async def decrypt_data(self, secure_data: SecureData) -> bytes:
        """解密数据"""
        # 获取解密密钥
        encryption_key = await self.key_manager.get_key(secure_data.key_id)
        if not encryption_key:
            raise ValueError(f"解密密钥 {secure_data.key_id} 不存在")
        
        if encryption_key.key_type != "symmetric":
            raise ValueError(f"密钥 {secure_data.key_id} 不是对称密钥")
        
        # 使用AES解密
        plaintext = AESEncryption.decrypt(
            secure_data.encrypted_data,
            encryption_key.key_data,
            secure_data.iv,
            secure_data.auth_tag
        )
        
        return plaintext
    
    async def encrypt_with_password(self, data: Union[str, bytes], password: str) -> bytes:
        """使用密码加密数据"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # 从密码派生密钥
        derived_key, salt = CryptoUtils.derive_key_from_password(password)
        
        # 生成随机IV
        iv = os.urandom(16)
        
        # 使用AES-CBC加密
        cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # 添加PKCS7填充
        padder = crypto_padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        
        # 加密
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # 组合盐、IV和密文
        result = salt + iv + ciphertext
        return result
    
    async def decrypt_with_password(self, encrypted_data: bytes, password: str) -> bytes:
        """使用密码解密数据"""
        # 提取盐、IV和密文
        salt = encrypted_data[:16]
        iv = encrypted_data[16:32]
        ciphertext = encrypted_data[32:]
        
        # 从密码派生密钥
        derived_key, _ = CryptoUtils.derive_key_from_password(password, salt)
        
        # 使用AES-CBC解密
        cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        # 解密
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # 移除PKCS7填充
        unpadder = crypto_padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_data) + unpadder.finalize()
        
        return plaintext
    
    async def encrypt_asymmetric(self, data: Union[str, bytes], public_key_id: str) -> bytes:
        """非对称加密"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # 获取公钥
        encryption_key = await self.key_manager.get_key(public_key_id)
        if not encryption_key:
            raise ValueError(f"公钥 {public_key_id} 不存在")
        
        if encryption_key.key_type != "asymmetric_public":
            raise ValueError(f"密钥 {public_key_id} 不是公钥")
        
        # 使用RSA加密
        ciphertext = RSAEncryption.encrypt(data, encryption_key.key_data)
        
        return ciphertext
    
    async def decrypt_asymmetric(self, ciphertext: bytes, private_key_id: str) -> bytes:
        """非对称解密"""
        # 获取私钥
        encryption_key = await self.key_manager.get_key(private_key_id)
        if not encryption_key:
            raise ValueError(f"私钥 {private_key_id} 不存在")
        
        if encryption_key.key_type != "asymmetric_private":
            raise ValueError(f"密钥 {private_key_id} 不是私钥")
        
        # 使用RSA解密
        plaintext = RSAEncryption.decrypt(ciphertext, encryption_key.key_data)
        
        return plaintext
    
    async def sign_data(self, data: Union[str, bytes], private_key_id: str) -> bytes:
        """数字签名"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # 获取私钥
        encryption_key = await self.key_manager.get_key(private_key_id)
        if not encryption_key:
            raise ValueError(f"私钥 {private_key_id} 不存在")
        
        if encryption_key.key_type != "asymmetric_private":
            raise ValueError(f"密钥 {private_key_id} 不是私钥")
        
        # 计算数据哈希
        data_hash = CryptoUtils.compute_hash(data)
        
        # 签名
        signature = RSAEncryption.sign(data_hash, encryption_key.key_data)
        
        return signature
    
    async def verify_signature(self, data: Union[str, bytes], signature: bytes, 
                            public_key_id: str) -> bool:
        """验证签名"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # 获取公钥
        encryption_key = await self.key_manager.get_key(public_key_id)
        if not encryption_key:
            raise ValueError(f"公钥 {public_key_id} 不存在")
        
        if encryption_key.key_type != "asymmetric_public":
            raise ValueError(f"密钥 {public_key_id} 不是公钥")
        
        # 计算数据哈希
        data_hash = CryptoUtils.compute_hash(data)
        
        # 验证签名
        return RSAEncryption.verify(data_hash, signature, encryption_key.key_data)


class SecureStorage:
    """安全存储"""
    
    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption_manager = encryption_manager
        self.storage_key = "secure_storage"
    
    async def store_secure(self, key: str, value: Union[str, bytes], 
                          password: str = None, key_id: str = None) -> bool:
        """安全存储数据"""
        try:
            if password:
                # 使用密码加密
                encrypted_data = await self.encryption_manager.encrypt_with_password(value, password)
            else:
                # 使用密钥加密
                secure_data = await self.encryption_manager.encrypt_data(value, key_id)
                encrypted_data = __import__('json').dumps({
                    "data": CryptoUtils.base64_encode(secure_data.encrypted_data),
                    "key_id": secure_data.key_id,
                    "iv": CryptoUtils.base64_encode(secure_data.iv) if secure_data.iv else None,
                    "auth_tag": CryptoUtils.base64_encode(secure_data.auth_tag) if secure_data.auth_tag else None,
                    "algorithm": secure_data.encryption_algorithm
                }).encode()
            
            # 存储到内存
            self.encryption_manager.memory.set(
                f"{self.storage_key}:{key}", 
                encrypted_data
            )
            
            return True
            
        except Exception:
            return False
    
    async def retrieve_secure(self, key: str, password: str = None, 
                            key_id: str = None) -> Optional[bytes]:
        """检索安全存储的数据"""
        try:
            # 从内存获取
            encrypted_data = self.encryption_manager.memory.get(f"{self.storage_key}:{key}")
            if not encrypted_data:
                return None
            
            if password:
                # 使用密码解密
                plaintext = await self.encryption_manager.decrypt_with_password(encrypted_data, password)
            else:
                # 使用密钥解密
                import json
                encrypted_info = json.loads(encrypted_data.decode())
                
                secure_data = SecureData(
                    data_id="temp",
                    encrypted_data=CryptoUtils.base64_decode(encrypted_info["data"]),
                    encryption_algorithm=encrypted_info["algorithm"],
                    key_id=encrypted_info["key_id"],
                    iv=CryptoUtils.base64_decode(encrypted_info["iv"]) if encrypted_info["iv"] else None,
                    auth_tag=CryptoUtils.base64_decode(encrypted_info["auth_tag"]) if encrypted_info["auth_tag"] else None
                )
                
                plaintext = await self.encryption_manager.decrypt_data(secure_data)
            
            return plaintext
            
        except Exception:
            return None
    
    async def delete_secure(self, key: str) -> bool:
        """删除安全存储的数据"""
        try:
            self.encryption_manager.memory.delete(f"{self.storage_key}:{key}")
            return True
        except Exception:
            return False
    
    async def list_keys(self) -> List[str]:
        """列出所有存储的键"""
        # 这里应该实现键的列举逻辑
        # 简化实现
        return []