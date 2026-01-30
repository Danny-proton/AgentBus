"""
AgentBus远程日志传输系统

支持多种远程日志传输方式：HTTP、HTTPS、WebSocket、TCP等
"""

import asyncio
import json
import logging as py_logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import asdict
from pathlib import Path
import ssl
import websocket
import requests
import socket
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import base64

from .log_manager import LogRecord, LogTransport


class RemoteTransport(LogTransport):
    """远程日志传输基类"""
    
    def __init__(self, name: str, endpoint: str, 
                 timeout: int = 30, retry_count: int = 3,
                 enable_compression: bool = True,
                 batch_size: int = 100,
                 batch_timeout: float = 5.0):
        super().__init__(name)
        self.endpoint = endpoint
        self.timeout = timeout
        self.retry_count = retry_count
        self.enable_compression = enable_compression
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._buffer: List[LogRecord] = []
        self._buffer_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._last_flush = time.time()
        
    def _compress_data(self, data: bytes) -> bytes:
        """压缩数据"""
        if self.enable_compression:
            return gzip.compress(data)
        return data
        
    def _encode_data(self, data: bytes) -> str:
        """编码数据为字符串"""
        return base64.b64encode(data).decode('utf-8')
        
    def _flush_buffer(self) -> None:
        """刷新缓冲区"""
        with self._buffer_lock:
            if len(self._buffer) == 0:
                return
                
            records = self._buffer.copy()
            self._buffer.clear()
            self._last_flush = time.time()
            
        # 异步发送
        self._executor.submit(self._send_records, records)
        
    def _send_records(self, records: List[LogRecord]) -> None:
        """发送日志记录"""
        try:
            # 序列化记录
            data = {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "agentbus",
                "records": [record.to_dict() for record in records]
            }
            
            # 转换为JSON并压缩
            json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            compressed_data = self._compress_data(json_data)
            encoded_data = self._encode_data(compressed_data)
            
            # 发送到远程端点
            for attempt in range(self.retry_count):
                try:
                    success = self._transmit(encoded_data, len(compressed_data))
                    if success:
                        break
                except Exception as e:
                    if attempt == self.retry_count - 1:
                        print(f"Remote transport {self.name} failed after {self.retry_count} attempts: {e}")
                    time.sleep(2 ** attempt)  # 指数退避
                    
        except Exception as e:
            print(f"Failed to send records: {e}")
            
    def _transmit(self, data: str, original_size: int) -> bool:
        """传输数据 - 子类实现"""
        raise NotImplementedError
        
    def write(self, record: LogRecord) -> None:
        """写入日志记录"""
        with self._buffer_lock:
            self._buffer.append(record)
            
            # 检查是否需要刷新
            should_flush = (
                len(self._buffer) >= self.batch_size or
                time.time() - self._last_flush >= self.batch_timeout
            )
            
        if should_flush:
            self._flush_buffer()
            
    def flush(self) -> None:
        """刷新输出"""
        self._flush_buffer()
        
    def close(self) -> None:
        """关闭传输"""
        self.flush()
        self._executor.shutdown(wait=True)


class HTTPLogTransport(RemoteTransport):
    """HTTP日志传输"""
    
    def __init__(self, name: str, url: str, 
                 headers: Optional[Dict[str, str]] = None,
                 **kwargs):
        super().__init__(name, url, **kwargs)
        self.headers = headers or {}
        self.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "AgentBus-Logger/1.0"
        })
        
    def _transmit(self, data: str, original_size: int) -> bool:
        """HTTP传输"""
        payload = {
            "data": data,
            "original_size": original_size,
            "compressed": self.enable_compression
        }
        
        response = requests.post(
            self.endpoint,
            json=payload,
            headers=self.headers,
            timeout=self.timeout
        )
        response.raise_for_status()
        return True


class WebSocketLogTransport(RemoteTransport):
    """WebSocket日志传输"""
    
    def __init__(self, name: str, ws_url: str, 
                 reconnect_interval: int = 5,
                 **kwargs):
        super().__init__(name, ws_url, **kwargs)
        self.reconnect_interval = reconnect_interval
        self.ws = None
        self._connect_lock = threading.Lock()
        self._connected = False
        
    def _ensure_connected(self) -> None:
        """确保WebSocket连接"""
        if self._connected and self.ws:
            return
            
        with self._connect_lock:
            if self._connected:
                return
                
            try:
                self.ws = websocket.create_connection(
                    self.endpoint,
                    timeout=self.timeout
                )
                self._connected = True
            except Exception as e:
                print(f"WebSocket connection failed: {e}")
                raise
                
    def _transmit(self, data: str, original_size: int) -> bool:
        """WebSocket传输"""
        self._ensure_connected()
        
        message = json.dumps({
            "type": "logs",
            "data": data,
            "original_size": original_size
        })
        
        self.ws.send(message)
        return True
        
    def close(self) -> None:
        """关闭WebSocket连接"""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        self._connected = False
        super().close()


class TCPLogTransport(RemoteTransport):
    """TCP日志传输"""
    
    def __init__(self, name: str, host: str, port: int, **kwargs):
        super().__init__(name, f"{host}:{port}", **kwargs)
        self.host = host
        self.port = port
        self._socket = None
        
    def _transmit(self, data: str, original_size: int) -> bool:
        """TCP传输"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))
                
                # 发送数据长度前缀
                length_prefix = f"{len(data):10d}"
                sock.sendall(length_prefix.encode('utf-8'))
                
                # 发送数据
                sock.sendall(data.encode('utf-8'))
                
            return True
            
        except Exception as e:
            print(f"TCP transport failed: {e}")
            return False


class RedisLogTransport(RemoteTransport):
    """Redis日志传输"""
    
    def __init__(self, name: str, redis_url: str, 
                 key_pattern: str = "agentbus:logs:{timestamp}",
                 **kwargs):
        super().__init__(name, redis_url, **kwargs)
        self.redis_url = redis_url
        self.key_pattern = key_pattern
        self._redis_client = None
        
    def _get_redis_client(self):
        """获取Redis客户端"""
        if self._redis_client is None:
            try:
                import redis
                self._redis_client = redis.from_url(self.redis_url)
            except ImportError:
                raise Exception("Redis transport requires redis-py library")
        return self._redis_client
        
    def _transmit(self, data: str, original_size: int) -> bool:
        """Redis传输"""
        try:
            client = self._get_redis_client()
            key = self.key_pattern.format(
                timestamp=int(time.time())
            )
            
            # 存储到Redis
            client.lpush(key, data)
            client.expire(key, 86400)  # 24小时过期
            
            return True
            
        except Exception as e:
            print(f"Redis transport failed: {e}")
            return False


class LogForwarder:
    """日志转发器"""
    
    def __init__(self, transports: List[RemoteTransport]):
        self.transports = transports
        self._routing_rules: Dict[str, List[str]] = {}  # 路由规则
        self._filter_rules: List[Callable] = []  # 过滤规则
        
    def add_routing_rule(self, level: str, transport_names: List[str]) -> None:
        """添加路由规则"""
        self._routing_rules[level] = transport_names
        
    def add_filter_rule(self, filter_func: Callable[[LogRecord], bool]) -> None:
        """添加过滤规则"""
        self._filter_rules.append(filter_func)
        
    def forward_record(self, record: LogRecord) -> None:
        """转发日志记录"""
        # 应用过滤规则
        for filter_func in self._filter_rules:
            if not filter_func(record):
                return
                
        # 确定目标传输
        target_transports = []
        
        # 基于级别路由
        if record.level in self._routing_rules:
            transport_names = self._routing_rules[record.level]
            target_transports = [
                t for t in self.transports 
                if t.name in transport_names
            ]
        else:
            # 默认发送到所有传输
            target_transports = self.transports
            
        # 发送到目标传输
        for transport in target_transports:
            transport.write(record)
            
    def flush_all(self) -> None:
        """刷新所有传输"""
        for transport in self.transports:
            transport.flush()
            
    def close_all(self) -> None:
        """关闭所有传输"""
        for transport in self.transports:
            transport.close()


class CentralizedLogServer:
    """集中式日志服务器"""
    
    def __init__(self, port: int = 9999, enable_ssl: bool = False,
                 cert_file: Optional[str] = None, 
                 key_file: Optional[str] = None):
        self.port = port
        self.enable_ssl = enable_ssl
        self.cert_file = cert_file
        self.key_file = key_file
        self._running = False
        self._server = None
        self._handlers: List[Callable] = []
        
    def add_log_handler(self, handler: Callable[[List[LogRecord]], None]) -> None:
        """添加日志处理器"""
        self._handlers.append(handler)
        
    def start(self) -> None:
        """启动服务器"""
        import http.server
        import socketserver
        from urllib.parse import urlparse, parse_qs
        
        class LogHandler(http.server.BaseHTTPRequestHandler):
            def __init__(self, *args, server_instance=None, **kwargs):
                self.server_instance = server_instance
                super().__init__(*args, **kwargs)
                
            def do_POST(self):
                if self.path == '/logs':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    
                    try:
                        # 解析接收到的数据
                        data = json.loads(post_data.decode('utf-8'))
                        
                        if 'data' in data:
                            # 解码和解析日志数据
                            import base64
                            import gzip
                            
                            encoded_data = data['data']
                            compressed_data = base64.b64decode(encoded_data.encode('utf-8'))
                            
                            if data.get('compressed', False):
                                decompressed_data = gzip.decompress(compressed_data)
                            else:
                                decompressed_data = compressed_data
                                
                            parsed_data = json.loads(decompressed_data.decode('utf-8'))
                            records_data = parsed_data.get('records', [])
                            
                            # 转换为LogRecord对象
                            from .log_manager import LogRecord
                            records = [
                                LogRecord(**record_data) 
                                for record_data in records_data
                            ]
                            
                            # 调用所有处理器
                            for handler in self.server_instance._handlers:
                                handler(records)
                                
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.end_headers()
                            self.wfile.write(b'{"status": "ok"}')
                            
                        else:
                            self.send_response(400)
                            self.end_headers()
                            
                    except Exception as e:
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(e)}).encode())
                        
            def log_message(self, format, *args):
                # 禁用默认日志
                pass
        
        # 创建服务器
        def handler_factory(*args, **kwargs):
            return LogHandler(*args, server_instance=self, **kwargs)
            
        if self.enable_ssl:
            # HTTPS服务器
            import ssl
            httpd = socketserver.TCPServer(("", self.port), handler_factory)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(self.cert_file, self.key_file)
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        else:
            # HTTP服务器
            httpd = socketserver.TCPServer(("", self.port), handler_factory)
            
        self._server = httpd
        self._running = True
        
        print(f"Centralized log server started on port {self.port}")
        httpd.serve_forever()
        
    def stop(self) -> None:
        """停止服务器"""
        if self._server:
            self._server.shutdown()
            self._server = None
        self._running = False


# 便捷函数
def create_http_transport(name: str, url: str, **kwargs) -> HTTPLogTransport:
    """创建HTTP传输"""
    return HTTPLogTransport(name, url, **kwargs)


def create_websocket_transport(name: str, ws_url: str, **kwargs) -> WebSocketLogTransport:
    """创建WebSocket传输"""
    return WebSocketLogTransport(name, ws_url, **kwargs)


def create_tcp_transport(name: str, host: str, port: int, **kwargs) -> TCPLogTransport:
    """创建TCP传输"""
    return TCPLogTransport(name, host, port, **kwargs)


def create_redis_transport(name: str, redis_url: str, **kwargs) -> RedisLogTransport:
    """创建Redis传输"""
    return RedisLogTransport(name, redis_url, **kwargs)