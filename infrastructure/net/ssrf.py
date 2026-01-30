"""
SSRF (Server Side Request Forgery) 保护模块
基于Moltbot的SSRF保护功能，提供网络安全防护
"""

import socket
import ipaddress
import asyncio
import aiohttp
import json
from typing import List, Dict, Optional, Union, Any
from urllib.parse import urlparse
from dataclasses import dataclass


class SsrFBlockedError(Exception):
    """SSRF攻击被阻止的异常"""
    pass


@dataclass
class NetworkConfig:
    """网络配置"""
    blocked_hostnames: set = None
    blocked_domains: set = None
    allowed_public_only: bool = True
    
    def __post_init__(self):
        if self.blocked_hostnames is None:
            self.blocked_hostnames = {
                "localhost", 
                "metadata.google.internal",
                "127.0.0.1",
                "::1"
            }
        if self.blocked_domains is None:
            self.blocked_domains = {
                ".localhost", 
                ".local", 
                ".internal",
                ".internal.domain"
            }


class SsrFProtection:
    """SSRF保护类"""
    
    # 私有IPv6前缀
    PRIVATE_IPV6_PREFIXES = ["fe80:", "fec0:", "fc", "fd"]
    
    def __init__(self, config: NetworkConfig = None):
        self.config = config or NetworkConfig()
    
    def _normalize_hostname(self, hostname: str) -> str:
        """标准化主机名"""
        normalized = hostname.strip().lower().rstrip(".")
        if normalized.startswith("[") and normalized.endswith("]"):
            return normalized[1:-1]
        return normalized
    
    def _is_private_ipv4(self, parts: List[int]) -> bool:
        """检查是否为私有IPv4地址"""
        if len(parts) != 4:
            return False
        
        octet1, octet2 = parts[0], parts[1]
        
        # 检查各种私有IP范围
        if octet1 == 0:  # 0.0.0.0/8
            return True
        if octet1 == 10:  # 10.0.0.0/8
            return True
        if octet1 == 127:  # 127.0.0.0/8 (loopback)
            return True
        if octet1 == 169 and octet2 == 254:  # 169.254.0.0/16 (link-local)
            return True
        if octet1 == 172 and 16 <= octet2 <= 31:  # 172.16.0.0/12
            return True
        if octet1 == 192 and octet2 == 168:  # 192.168.0.0/16
            return True
        if octet1 == 100 and 64 <= octet2 <= 127:  # 100.64.0.0/10 (CGNAT)
            return True
        return False
    
    def _is_private_ipv6(self, address: str) -> bool:
        """检查是否为私有IPv6地址"""
        normalized = address.lower().strip()
        
        if normalized == "::" or normalized == "::1":  # loopback
            return True
        
        if normalized.startswith("::ffff:"):
            # IPv4-mapped IPv6 address
            mapped = normalized[7:]
            try:
                if "." in mapped:  # IPv4 format
                    ipv4_parts = [int(x) for x in mapped.split(".")]
                    return self._is_private_ipv4(ipv4_parts)
                else:  # IPv6 format
                    parts = mapped.split(":")
                    if len(parts) == 1:
                        value = int(parts[0], 16)
                        return not (0 <= value <= 0xffff_ffff)
                    elif len(parts) == 2:
                        high = int(parts[0], 16)
                        low = int(parts[1], 16)
                        return not (0 <= high <= 0xffff and 0 <= low <= 0xffff)
            except ValueError:
                return True
        
        # 检查私有IPv6前缀
        return any(normalized.startswith(prefix) for prefix in self.PRIVATE_IPV6_PREFIXES)
    
    def _is_private_ip_address(self, address: str) -> bool:
        """检查是否为私有IP地址"""
        try:
            ip = ipaddress.ip_address(address)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except ValueError:
            # 如果不是有效的IP地址，尝试作为主机名处理
            return False
    
    def _is_blocked_hostname(self, hostname: str) -> bool:
        """检查是否是被阻止的主机名"""
        normalized = self._normalize_hostname(hostname)
        
        # 检查直接被阻止的主机名
        if normalized in self.config.blocked_hostnames:
            return True
        
        # 检查被阻止的域名后缀
        return any(
            normalized.endswith(domain) 
            for domain in self.config.blocked_domains
        )
    
    def is_safe_url(self, url: str) -> bool:
        """检查URL是否安全"""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            return not self._is_blocked_hostname(hostname)
        except Exception:
            return False
    
    async def validate_hostname(self, hostname: str) -> List[str]:
        """验证主机名并返回所有解析的IP地址"""
        normalized = self._normalize_hostname(hostname)
        
        # 检查是否被阻止的主机名
        if self._is_blocked_hostname(normalized):
            raise SsrFBlockedError(f"Blocked hostname: {hostname}")
        
        # 检查IP地址
        if self._is_private_ip_address(normalized):
            raise SsrFBlockedError("Blocked: private/internal IP address")
        
        # DNS解析
        try:
            if ":" in normalized:  # IPv6
                addresses = await self._resolve_ipv6(normalized)
            else:  # IPv4
                addresses = await self._resolve_ipv4(normalized)
        except Exception as e:
            raise SsrFBlockedError(f"DNS resolution failed: {hostname}") from e
        
        # 检查所有解析的IP地址
        for addr in addresses:
            if self._is_private_ip_address(addr):
                raise SsrFBlockedError(
                    f"Blocked: resolves to private/internal IP address: {addr}"
                )
        
        return addresses
    
    async def _resolve_ipv4(self, hostname: str) -> List[str]:
        """解析IPv4地址"""
        try:
            info = await asyncio.get_event_loop().getaddrinfo(
                hostname, None, family=socket.AF_INET
            )
            return [addr[4][0] for addr in info]
        except socket.gaierror:
            return []
    
    async def _resolve_ipv6(self, hostname: str) -> List[str]:
        """解析IPv6地址"""
        try:
            info = await asyncio.get_event_loop().getaddrinfo(
                hostname, None, family=socket.AF_INET6
            )
            return [addr[4][0] for addr in info]
        except socket.gaierror:
            return []
    
    def create_secure_session(self, timeout: int = 30) -> aiohttp.ClientSession:
        """创建安全的HTTP会话"""
        timeout = aiohttp.ClientTimeout(total=timeout)
        connector = aiohttp.TCPConnector()
        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
    
    async def safe_request(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """执行安全的HTTP请求"""
        if not self.is_safe_url(url):
            raise SsrFBlockedError(f"Blocked URL: {url}")
        
        addresses = await self.validate_hostname(urlparse(url).hostname)
        if not addresses:
            raise SsrFBlockedError(f"No valid addresses for hostname: {urlparse(url).hostname}")
        
        session = self.create_secure_session()
        try:
            return await session.get(url, **kwargs)
        finally:
            await session.close()


# 全局默认实例
default_protection = SsrFProtection()


def is_safe_hostname(hostname: str) -> bool:
    """检查主机名是否安全"""
    return default_protection._is_blocked_hostname(hostname)


def validate_url_safety(url: str) -> bool:
    """验证URL安全性"""
    return default_protection.is_safe_url(url)


async def safe_http_get(url: str, **kwargs) -> aiohttp.ClientResponse:
    """安全的HTTP GET请求"""
    return await default_protection.safe_request(url, **kwargs)