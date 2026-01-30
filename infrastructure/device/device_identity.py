"""
设备身份管理模块 - 提供设备身份认证、密钥生成和管理功能
"""

import os
import json
import secrets
import hashlib
import base64
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


@dataclass
class DeviceIdentity:
    """设备身份信息"""
    device_id: str
    device_name: str
    device_type: str
    created_at: datetime
    last_seen: datetime
    public_key: str
    fingerprint: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            **asdict(self),
            'created_at': self.created_at.isoformat(),
            'last_seen': self.last_seen.isoformat()
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class DeviceKeyPair:
    """设备密钥对"""
    private_key_pem: str
    public_key_pem: str
    private_key_encrypted: Optional[str] = None
    encryption_method: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DeviceIdentityManager:
    """设备身份管理器"""
    
    def __init__(self, storage_path: str = None):
        if storage_path is None:
            # 默认存储在用户配置目录
            config_dir = Path.home() / ".agentbus"
            self.storage_path = config_dir / "device_identity"
        else:
            self.storage_path = Path(storage_path)
        
        self.identity_file = self.storage_path / "identity.json"
        self.keys_file = self.storage_path / "keys.json"
        self._current_identity: Optional[DeviceIdentity] = None
        self._current_keys: Optional[DeviceKeyPair] = None
    
    def ensure_storage_directory(self):
        """确保存储目录存在"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def generate_device_id(self, device_name: str, device_type: str) -> str:
        """生成设备ID"""
        timestamp = datetime.now().isoformat()
        random_bytes = secrets.token_bytes(16)
        data = f"{device_name}:{device_type}:{timestamp}".encode() + random_bytes
        return hashlib.sha256(data).hexdigest()
    
    def generate_fingerprint(self, public_key_pem: str) -> str:
        """生成密钥指纹"""
        # 提取公钥的DER格式数据
        public_key = serialization.load_pem_public_key(public_key_pem.encode())
        der_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return hashlib.sha256(der_bytes).hexdigest()
    
    async def generate_key_pair(self, algorithm: str = "ed25519") -> DeviceKeyPair:
        """生成密钥对"""
        if algorithm == "ed25519":
            private_key = ed25519.Ed25519PrivateKey.generate()
        elif algorithm == "rsa":
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()
        
        public_key = private_key.public_key()
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        return DeviceKeyPair(
            private_key_pem=private_key_pem,
            public_key_pem=public_key_pem
        )
    
    async def create_device_identity(self, 
                                   device_name: str,
                                   device_type: str,
                                   metadata: Dict[str, Any] = None) -> DeviceIdentity:
        """创建设备身份"""
        self.ensure_storage_directory()
        
        # 生成密钥对
        key_pair = await self.generate_key_pair()
        
        # 生成设备ID
        device_id = self.generate_device_id(device_name, device_type)
        
        # 生成指纹
        fingerprint = self.generate_fingerprint(key_pair.public_key_pem)
        
        # 创建身份信息
        now = datetime.now()
        identity = DeviceIdentity(
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            created_at=now,
            last_seen=now,
            public_key=key_pair.public_key_pem,
            fingerprint=fingerprint,
            metadata=metadata or {}
        )
        
        # 保存身份和密钥
        await self._save_identity(identity)
        await self._save_keys(key_pair)
        
        self._current_identity = identity
        self._current_keys = key_pair
        
        return identity
    
    async def load_device_identity(self) -> Optional[DeviceIdentity]:
        """加载设备身份"""
        if not self.identity_file.exists():
            return None
        
        try:
            with open(self.identity_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            identity = DeviceIdentity(
                device_id=data['device_id'],
                device_name=data['device_name'],
                device_type=data['device_type'],
                created_at=datetime.fromisoformat(data['created_at']),
                last_seen=datetime.fromisoformat(data['last_seen']),
                public_key=data['public_key'],
                fingerprint=data['fingerprint'],
                metadata=data.get('metadata', {})
            )
            
            self._current_identity = identity
            return identity
        except Exception:
            return None
    
    async def load_keys(self) -> Optional[DeviceKeyPair]:
        """加载密钥"""
        if not self.keys_file.exists():
            return None
        
        try:
            with open(self.keys_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            key_pair = DeviceKeyPair(
                private_key_pem=data['private_key_pem'],
                public_key_pem=data['public_key_pem'],
                private_key_encrypted=data.get('private_key_encrypted'),
                encryption_method=data.get('encryption_method')
            )
            
            self._current_keys = key_pair
            return key_pair
        except Exception:
            return None
    
    async def _save_identity(self, identity: DeviceIdentity):
        """保存身份信息"""
        with open(self.identity_file, 'w', encoding='utf-8') as f:
            f.write(identity.to_json())
    
    async def _save_keys(self, key_pair: DeviceKeyPair):
        """保存密钥"""
        with open(self.keys_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(key_pair.to_dict(), ensure_ascii=False, indent=2))
    
    def get_current_identity(self) -> Optional[DeviceIdentity]:
        """获取当前身份"""
        return self._current_identity
    
    def get_current_keys(self) -> Optional[DeviceKeyPair]:
        """获取当前密钥"""
        return self._current_keys
    
    async def update_last_seen(self):
        """更新最后活动时间"""
        if self._current_identity:
            self._current_identity.last_seen = datetime.now()
            await self._save_identity(self._current_identity)
    
    async def sign_data(self, data: str) -> str:
        """使用私钥签名数据"""
        if not self._current_keys:
            raise ValueError("No keys available")
        
        private_key = serialization.load_pem_private_key(
            self._current_keys.private_key_pem.encode(),
            password=None
        )
        
        signature = private_key.sign(data.encode())
        return base64.b64encode(signature).decode()
    
    def verify_signature(self, data: str, signature: str, public_key_pem: str) -> bool:
        """验证签名"""
        try:
            public_key = serialization.load_pem_public_key(public_key_pem.encode())
            signature_bytes = base64.b64decode(signature.encode())
            
            if isinstance(public_key, ed25519.Ed25519PublicKey):
                public_key.verify(signature_bytes, data.encode())
            elif isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(signature_bytes, data.encode(), 
                                padding.PSS(
                                    mgf=padding.MGF1(hashes.SHA256()),
                                    salt_length=padding.PSS.MAX_LENGTH
                                ),
                                hashes.SHA256())
            else:
                return False
            
            return True
        except Exception:
            return False
    
    def export_identity(self, format: str = "json") -> str:
        """导出身份信息"""
        if not self._current_identity:
            raise ValueError("No identity available")
        
        if format.lower() == "json":
            return self._current_identity.to_json()
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def export_public_key(self) -> str:
        """导出公钥"""
        if not self._current_keys:
            raise ValueError("No keys available")
        return self._current_keys.public_key_pem
    
    def encrypt_private_key(self, password: str) -> bool:
        """加密私钥"""
        if not self._current_keys:
            return False
        
        try:
            # 这里实现密钥加密逻辑
            # 使用简单的对称加密作为示例
            key = hashlib.sha256(password.encode()).digest()
            
            private_key = serialization.load_pem_private_key(
                self._current_keys.private_key_pem.encode(),
                password=None
            )
            
            private_bytes = self._current_keys.private_key_pem.encode()
            
            # 生成随机IV
            iv = secrets.token_bytes(16)
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            encryptor = cipher.encryptor()
            
            # PKCS7填充
            padding_length = 16 - (len(private_bytes) % 16)
            padded_data = private_bytes + bytes([padding_length] * padding_length)
            
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # 保存加密后的密钥
            self._current_keys.private_key_encrypted = base64.b64encode(iv + encrypted_data).decode()
            self._current_keys.encryption_method = "AES-256-CBC"
            
            # 清除未加密的私钥
            self._current_keys.private_key_pem = ""
            
            return True
        except Exception:
            return False
    
    def decrypt_private_key(self, password: str) -> bool:
        """解密私钥"""
        if not self._current_keys or not self._current_keys.private_key_encrypted:
            return False
        
        try:
            # 这里实现密钥解密逻辑
            key = hashlib.sha256(password.encode()).digest()
            encrypted_data = base64.b64decode(self._current_keys.private_key_encrypted.encode())
            
            iv = encrypted_data[:16]
            cipher_data = encrypted_data[16:]
            
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            
            padded_data = decryptor.update(cipher_data) + decryptor.finalize()
            
            # 移除PKCS7填充
            padding_length = padded_data[-1]
            private_bytes = padded_data[:-padding_length]
            
            self._current_keys.private_key_pem = private_bytes.decode()
            self._current_keys.private_key_encrypted = None
            self._current_keys.encryption_method = None
            
            return True
        except Exception:
            return False
    
    async def delete_identity(self) -> bool:
        """删除身份信息"""
        try:
            if self.identity_file.exists():
                self.identity_file.unlink()
            if self.keys_file.exists():
                self.keys_file.unlink()
            
            self._current_identity = None
            self._current_keys = None
            
            return True
        except Exception:
            return False
    
    def is_identity_exists(self) -> bool:
        """检查身份是否存在"""
        return self.identity_file.exists() and self.keys_file.exists()
    
    def get_identity_info(self) -> Dict[str, Any]:
        """获取身份信息摘要"""
        if not self._current_identity:
            return {}
        
        return {
            "device_id": self._current_identity.device_id,
            "device_name": self._current_identity.device_name,
            "device_type": self._current_identity.device_type,
            "created_at": self._current_identity.created_at.isoformat(),
            "last_seen": self._current_identity.last_seen.isoformat(),
            "fingerprint": self._current_identity.fingerprint,
            "has_keys": self._current_keys is not None,
            "keys_encrypted": self._current_keys.private_key_encrypted is not None if self._current_keys else False
        }