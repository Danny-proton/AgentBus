"""
设备管理模块 - 提供设备发现、配对和管理功能
"""

import asyncio
import json
import platform
import socket
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from .device_identity import DeviceIdentity, DeviceIdentityManager


class DeviceType(Enum):
    """设备类型"""
    SERVER = "server"
    CLIENT = "client"
    GATEWAY = "gateway"
    AGENT = "agent"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    UNKNOWN = "unknown"


class DeviceStatus(Enum):
    """设备状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    MAINTENANCE = "maintenance"
    UNKNOWN = "unknown"


class PairingStatus(Enum):
    """配对状态"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class DeviceInfo:
    """设备信息"""
    device_id: str
    device_name: str
    device_type: DeviceType
    status: DeviceStatus
    ip_address: str
    port: int
    last_seen: datetime
    capabilities: List[str]
    metadata: Dict[str, Any]
    pairing_status: Optional[PairingStatus] = None
    pairing_code: Optional[str] = None
    pairing_expires: Optional[datetime] = None
    trusted: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'device_type': self.device_type.value,
            'status': self.status.value,
            'last_seen': self.last_seen.isoformat(),
            'pairing_status': self.pairing_status.value if self.pairing_status else None,
            'pairing_expires': self.pairing_expires.isoformat() if self.pairing_expires else None
        }


@dataclass
class PairingRequest:
    """配对请求"""
    request_id: str
    device_id: str
    device_name: str
    public_key: str
    timestamp: datetime
    expires_at: datetime
    status: PairingStatus
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'status': self.status.value
        }


class DeviceManager:
    """设备管理器"""
    
    def __init__(self, identity_manager: DeviceIdentityManager = None, storage_path: str = None):
        self.identity_manager = identity_manager or DeviceIdentityManager(storage_path)
        self.devices_file = self.identity_manager.storage_path / "devices.json"
        self.pairing_requests_file = self.identity_manager.storage_path / "pairing.json"
        
        self._devices: Dict[str, DeviceInfo] = {}
        self._pairing_requests: Dict[str, PairingRequest] = {}
        self._listeners: List[Callable[[str, DeviceInfo], None]] = []
        self._discovery_active = False
        self._discovery_task: Optional[asyncio.Task] = None
        self._current_device: Optional[DeviceInfo] = None
        
        # 加载现有数据
        asyncio.create_task(self._load_devices())
        asyncio.create_task(self._load_pairing_requests())
    
    async def _load_devices(self):
        """加载设备列表"""
        if not self.devices_file.exists():
            return
        
        try:
            with open(self.devices_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for device_data in data.values():
                device = DeviceInfo(
                    device_id=device_data['device_id'],
                    device_name=device_data['device_name'],
                    device_type=DeviceType(device_data['device_type']),
                    status=DeviceStatus(device_data['status']),
                    ip_address=device_data['ip_address'],
                    port=device_data['port'],
                    last_seen=datetime.fromisoformat(device_data['last_seen']),
                    capabilities=device_data['capabilities'],
                    metadata=device_data.get('metadata', {}),
                    pairing_status=PairingStatus(device_data['pairing_status']) if device_data.get('pairing_status') else None,
                    pairing_code=device_data.get('pairing_code'),
                    pairing_expires=datetime.fromisoformat(device_data['pairing_expires']) if device_data.get('pairing_expires') else None,
                    trusted=device_data.get('trusted', False)
                )
                self._devices[device.device_id] = device
        except Exception:
            pass
    
    async def _save_devices(self):
        """保存设备列表"""
        self.identity_manager.ensure_storage_directory()
        data = {device_id: device.to_dict() for device_id, device in self._devices.items()}
        
        with open(self.devices_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    async def _load_pairing_requests(self):
        """加载配对请求"""
        if not self.pairing_requests_file.exists():
            return
        
        try:
            with open(self.pairing_requests_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for request_data in data.values():
                request = PairingRequest(
                    request_id=request_data['request_id'],
                    device_id=request_data['device_id'],
                    device_name=request_data['device_name'],
                    public_key=request_data['public_key'],
                    timestamp=datetime.fromisoformat(request_data['timestamp']),
                    expires_at=datetime.fromisoformat(request_data['expires_at']),
                    status=PairingStatus(request_data['status']),
                    metadata=request_data.get('metadata', {})
                )
                self._pairing_requests[request.request_id] = request
        except Exception:
            pass
    
    async def _save_pairing_requests(self):
        """保存配对请求"""
        self.identity_manager.ensure_storage_directory()
        data = {req_id: req.to_dict() for req_id, req in self._pairing_requests.items()}
        
        with open(self.pairing_requests_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def register_device_listener(self, listener: Callable[[str, DeviceInfo], None]):
        """注册设备事件监听器"""
        self._listeners.append(listener)
    
    def unregister_device_listener(self, listener: Callable[[str, DeviceInfo], None]):
        """取消设备事件监听器"""
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    async def create_device(self, device_name: str, device_type: DeviceType = DeviceType.UNKNOWN,
                          capabilities: List[str] = None, metadata: Dict[str, Any] = None) -> DeviceInfo:
        """创建设备"""
        # 确保有设备身份
        if not self.identity_manager.is_identity_exists():
            await self.identity_manager.create_device_identity(
                device_name=device_name,
                device_type=device_type.value,
                metadata=metadata or {}
            )
        
        identity = await self.identity_manager.load_device_identity()
        if not identity:
            raise ValueError("Failed to load device identity")
        
        # 获取当前IP地址
        ip_address = await self._get_local_ip_address()
        
        device = DeviceInfo(
            device_id=identity.device_id,
            device_name=device_name,
            device_type=device_type,
            status=DeviceStatus.ONLINE,
            ip_address=ip_address,
            port=8080,  # 默认端口
            last_seen=datetime.now(),
            capabilities=capabilities or [],
            metadata=metadata or {},
            trusted=True
        )
        
        self._devices[device.device_id] = device
        self._current_device = device
        
        await self._save_devices()
        
        # 通知监听器
        for listener in self._listeners:
            try:
                listener("created", device)
            except Exception:
                pass
        
        return device
    
    async def _get_local_ip_address(self) -> str:
        """获取本地IP地址"""
        try:
            # 创建一个连接到外部地址的socket来获取本地IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    async def discover_devices(self, timeout: float = 10.0) -> List[DeviceInfo]:
        """发现网络中的设备"""
        discovered = []
        
        # 这里实现设备发现逻辑
        # 实际实现可能包括：
        # 1. mDNS/Bonjour发现
        # 2. UDP广播发现
        # 3. SSDP发现
        # 4. 自定义协议发现
        
        # 简单的局域网扫描示例
        try:
            local_ip = await self._get_local_ip_address()
            network = ".".join(local_ip.split(".")[:-1])
            
            tasks = []
            for i in range(1, 255):
                if i != int(local_ip.split(".")[-1]):  # 跳过自己
                    ip = f"{network}.{i}"
                    tasks.append(self._check_device_at_ip(ip, timeout))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, DeviceInfo):
                    discovered.append(result)
        except Exception:
            pass
        
        return discovered
    
    async def _check_device_at_ip(self, ip: str, timeout: float) -> Optional[DeviceInfo]:
        """检查指定IP的设备"""
        try:
            # 简单的端口扫描
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, 8080),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            
            # 如果连接成功，认为有设备
            return DeviceInfo(
                device_id=f"discovered_{ip}",
                device_name=f"Device at {ip}",
                device_type=DeviceType.UNKNOWN,
                status=DeviceStatus.ONLINE,
                ip_address=ip,
                port=8080,
                last_seen=datetime.now(),
                capabilities=[],
                metadata={}
            )
        except Exception:
            return None
    
    async def pair_device(self, device_id: str, pairing_code: str = None) -> bool:
        """配对设备"""
        device = self._devices.get(device_id)
        if not device:
            return False
        
        # 生成配对代码（如果没有提供）
        if not pairing_code:
            pairing_code = self._generate_pairing_code()
        
        # 创建配对请求
        request_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(minutes=10)
        
        request = PairingRequest(
            request_id=request_id,
            device_id=device.device_id,
            device_name=device.device_name,
            public_key=self.identity_manager.export_public_key(),
            timestamp=datetime.now(),
            expires_at=expires_at,
            status=PairingStatus.PENDING,
            metadata={}
        )
        
        self._pairing_requests[request_id] = request
        await self._save_pairing_requests()
        
        # 更新设备配对状态
        device.pairing_status = PairingStatus.PENDING
        device.pairing_code = pairing_code
        device.pairing_expires = expires_at
        await self._save_devices()
        
        return True
    
    def _generate_pairing_code(self) -> str:
        """生成配对代码"""
        return ''.join(secrets.choice('0123456789ABCDEF') for _ in range(8))
    
    async def confirm_pairing(self, request_id: str) -> bool:
        """确认配对"""
        request = self._pairing_requests.get(request_id)
        if not request or request.status != PairingStatus.PENDING:
            return False
        
        # 检查是否过期
        if datetime.now() > request.expires_at:
            request.status = PairingStatus.EXPIRED
            await self._save_pairing_requests()
            return False
        
        # 标记为已确认
        request.status = PairingStatus.CONFIRMED
        
        # 更新设备状态
        device = self._devices.get(request.device_id)
        if device:
            device.pairing_status = PairingStatus.CONFIRMED
            device.trusted = True
            device.last_seen = datetime.now()
            await self._save_devices()
        
        await self._save_pairing_requests()
        
        # 通知监听器
        for listener in self._listeners:
            try:
                listener("paired", device)
            except Exception:
                pass
        
        return True
    
    async def reject_pairing(self, request_id: str) -> bool:
        """拒绝配对"""
        request = self._pairing_requests.get(request_id)
        if not request or request.status != PairingStatus.PENDING:
            return False
        
        request.status = PairingStatus.REJECTED
        await self._save_pairing_requests()
        
        # 更新设备状态
        device = self._devices.get(request.device_id)
        if device:
            device.pairing_status = PairingStatus.REJECTED
            await self._save_devices()
        
        return True
    
    async def start_device_discovery(self, interval: float = 30.0):
        """开始设备发现"""
        if self._discovery_active:
            return
        
        self._discovery_active = True
        self._discovery_task = asyncio.create_task(
            self._discovery_loop(interval)
        )
    
    async def stop_device_discovery(self):
        """停止设备发现"""
        self._discovery_active = False
        if self._discovery_task:
            self._discovery_task.cancel()
            try:
                await self._discovery_task
            except asyncio.CancelledError:
                pass
            self._discovery_task = None
    
    async def _discovery_loop(self, interval: float):
        """设备发现循环"""
        while self._discovery_active:
            try:
                await asyncio.sleep(interval)
                
                # 发现新设备
                discovered = await self.discover_devices(timeout=5.0)
                
                for device in discovered:
                    if device.device_id not in self._devices:
                        self._devices[device.device_id] = device
                        
                        # 通知监听器
                        for listener in self._listeners:
                            try:
                                listener("discovered", device)
                            except Exception:
                                pass
                
                # 更新设备状态
                await self._update_device_statuses()
                
                # 清理过期的配对请求
                await self._cleanup_expired_pairings()
                
                await self._save_devices()
                await self._save_pairing_requests()
                
            except asyncio.CancelledError:
                break
            except Exception:
                # 记录错误但继续
                pass
    
    async def _update_device_statuses(self):
        """更新设备状态"""
        current_time = datetime.now()
        offline_threshold = timedelta(minutes=5)
        
        for device in self._devices.values():
            if device.status == DeviceStatus.ONLINE:
                if current_time - device.last_seen > offline_threshold:
                    device.status = DeviceStatus.OFFLINE
    
    async def _cleanup_expired_pairings(self):
        """清理过期的配对"""
        current_time = datetime.now()
        expired_requests = []
        
        for request_id, request in self._pairing_requests.items():
            if (request.status == PairingStatus.PENDING and 
                current_time > request.expires_at):
                request.status = PairingStatus.EXPIRED
                expired_requests.append(request_id)
        
        return expired_requests
    
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """获取设备信息"""
        return self._devices.get(device_id)
    
    def get_all_devices(self) -> List[DeviceInfo]:
        """获取所有设备"""
        return list(self._devices.values())
    
    def get_devices_by_status(self, status: DeviceStatus) -> List[DeviceInfo]:
        """根据状态获取设备"""
        return [device for device in self._devices.values() if device.status == status]
    
    def get_devices_by_type(self, device_type: DeviceType) -> List[DeviceInfo]:
        """根据类型获取设备"""
        return [device for device in self._devices.values() if device.device_type == device_type]
    
    def get_trusted_devices(self) -> List[DeviceInfo]:
        """获取可信设备"""
        return [device for device in self._devices.values() if device.trusted]
    
    def get_pairing_requests(self, status: PairingStatus = None) -> List[PairingRequest]:
        """获取配对请求"""
        if status is None:
            return list(self._pairing_requests.values())
        return [req for req in self._pairing_requests.values() if req.status == status]
    
    def get_current_device(self) -> Optional[DeviceInfo]:
        """获取当前设备"""
        return self._current_device
    
    async def remove_device(self, device_id: str) -> bool:
        """移除设备"""
        if device_id in self._devices:
            device = self._devices.pop(device_id)
            await self._save_devices()
            
            # 通知监听器
            for listener in self._listeners:
                try:
                    listener("removed", device)
                except Exception:
                    pass
            
            return True
        return False
    
    async def update_device(self, device_id: str, **kwargs) -> bool:
        """更新设备信息"""
        device = self._devices.get(device_id)
        if not device:
            return False
        
        for key, value in kwargs.items():
            if hasattr(device, key):
                setattr(device, key, value)
        
        device.last_seen = datetime.now()
        await self._save_devices()
        
        # 通知监听器
        for listener in self._listeners:
            try:
                listener("updated", device)
            except Exception:
                pass
        
        return True
    
    def get_device_statistics(self) -> Dict[str, Any]:
        """获取设备统计信息"""
        total = len(self._devices)
        online = len(self.get_devices_by_status(DeviceStatus.ONLINE))
        trusted = len(self.get_trusted_devices())
        pending_pairings = len(self.get_pairing_requests(PairingStatus.PENDING))
        
        type_counts = {}
        for device_type in DeviceType:
            type_counts[device_type.value] = len(self.get_devices_by_type(device_type))
        
        return {
            "total_devices": total,
            "online_devices": online,
            "offline_devices": total - online,
            "trusted_devices": trusted,
            "pending_pairings": pending_pairings,
            "device_types": type_counts,
            "discovery_active": self._discovery_active,
            "current_device": self._current_device.device_id if self._current_device else None
        }
    
    def export_devices(self, format: str = "json") -> str:
        """导出设备列表"""
        if format.lower() == "json":
            data = {device_id: device.to_dict() for device_id, device in self._devices.items()}
            return json.dumps(data, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")