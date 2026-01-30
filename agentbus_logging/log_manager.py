"""
AgentBus日志管理器

提供结构化日志记录、多种格式支持、轮转和清理功能
"""

import os
import json
import logging as py_logging
import logging.handlers
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import gzip
import shutil
from concurrent.futures import ThreadPoolExecutor
import traceback


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """日志格式枚举"""
    JSON = "json"
    TEXT = "text"
    COLORED = "colored"
    COMPACT = "compact"


class LogTransport:
    """日志传输接口"""
    
    def __init__(self, name: str):
        self.name = name
        
    def write(self, record: "LogRecord") -> None:
        """写入日志记录"""
        raise NotImplementedError
        
    def flush(self) -> None:
        """刷新输出"""
        pass
        
    def close(self) -> None:
        """关闭传输"""
        pass


@dataclass
class LogRecord:
    """结构化日志记录"""
    timestamp: str
    level: str
    logger: str
    message: str
    module: str
    function: str
    line: int
    thread_id: Optional[int] = None
    process_id: Optional[int] = None
    extra_fields: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    def to_json(self) -> str:
        """转换为JSON格式"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    def to_text(self, format_type: LogFormat = LogFormat.TEXT) -> str:
        """转换为文本格式"""
        timestamp = self.timestamp.split('T')[1].split('.')[0]  # 只保留时间部分
        
        if format_type == LogFormat.COLORED:
            # 添加颜色代码
            level_colors = {
                'DEBUG': '\033[36m',    # 青色
                'INFO': '\033[32m',     # 绿色
                'WARNING': '\033[33m',  # 黄色
                'ERROR': '\033[31m',    # 红色
                'CRITICAL': '\033[35m', # 紫色
            }
            color = level_colors.get(self.level, '\033[0m')  # 默认白色
            reset = '\033[0m'
            
            return f"{color}{timestamp} {self.level:8} {self.logger:15} {self.module}:{self.function}:{self.line} - {self.message}{reset}"
        elif format_type == LogFormat.COMPACT:
            return f"{self.timestamp} {self.level} {self.logger} {self.message}"
        else:
            # 标准文本格式
            extra = ""
            if self.extra_fields:
                extra_fields = ", ".join(f"{k}={v}" for k, v in self.extra_fields.items())
                extra = f" [{extra_fields}]"
            
            return f"{self.timestamp} {self.level:8} {self.logger:15} {self.module}:{self.function}:{self.line} - {self.message}{extra}"


class FileTransport(LogTransport):
    """文件日志传输"""
    
    def __init__(self, name: str, file_path: str, format_type: LogFormat = LogFormat.JSON):
        super().__init__(name)
        self.file_path = Path(file_path)
        self.format_type = format_type
        self.file_handle = None
        self._lock = threading.Lock()
        
        # 确保目录存在
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        
    def write(self, record: LogRecord) -> None:
        """写入文件"""
        with self._lock:
            try:
                if self.format_type == LogFormat.JSON:
                    line = record.to_json()
                else:
                    line = record.to_text(self.format_type)
                
                with open(self.file_path, 'a', encoding='utf-8') as f:
                    f.write(line + '\n')
            except Exception as e:
                # 避免日志写入失败导致系统崩溃
                print(f"Failed to write log: {e}")
                
    def close(self) -> None:
        """关闭文件句柄"""
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None


class ConsoleTransport(LogTransport):
    """控制台日志传输"""
    
    def __init__(self, name: str, format_type: LogFormat = LogFormat.COLORED):
        super().__init__(name)
        self.format_type = format_type
        
    def write(self, record: LogRecord) -> None:
        """写入控制台"""
        try:
            line = record.to_text(self.format_type)
            level = record.level
            
            if level in ['ERROR', 'CRITICAL']:
                print(line, file=py_logging.stderr)
            else:
                print(line)
        except Exception as e:
            # 避免控制台输出失败
            print(f"Failed to write console log: {e}")


class RotatingFileHandler(logging.handlers.BaseRotatingHandler):
    """自定义轮转文件处理器"""
    
    def __init__(self, filename: str, max_bytes: int = 0, backup_count: int = 0, 
                 encoding: str = 'utf-8', compress: bool = True):
        super().__init__(filename, 'a', encoding, delay=True, errors=None)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.compress = compress
        self._lock = threading.Lock()
        
    def shouldRollover(self, record) -> bool:
        """检查是否需要轮转"""
        if self.stream is None:
            self.stream = self._open()
            
        if self.max_bytes > 0:
            if self.stream.tell() >= self.max_bytes:
                return 1
        return 0
        
    def doRollover(self) -> None:
        """执行轮转"""
        if self.stream:
            self.stream.close()
            self.stream = None
            
        if self.backup_count > 0:
            for i in range(self.backup_count - 1, 0, -1):
                sfn = f"{self.baseFilename}.{i}"
                dfn = f"{self.baseFilename}.{i+1}"
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)
                    
            dfn = self.baseFilename + ".1"
            if os.path.exists(dfn):
                if self.compress and not dfn.endswith('.gz'):
                    with open(dfn, 'rb') as f_in:
                        with gzip.open(dfn + '.gz', 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    os.remove(dfn)
                    dfn += '.gz'
            else:
                os.rename(self.baseFilename, dfn)
                
        if not self.delay:
            self.stream = self._open()


class Logger:
    """AgentBus日志记录器"""
    
    def __init__(self, name: str, level: LogLevel = LogLevel.INFO):
        self.name = name
        self.level = level
        self.transports: List[LogTransport] = []
        self._local = threading.local()
        
    def add_transport(self, transport: LogTransport) -> None:
        """添加日志传输"""
        self.transports.append(transport)
        
    def _log(self, level: LogLevel, message: str, **kwargs) -> None:
        """内部日志方法"""
        if level.value < self.level.value:
            return
            
        # 获取调用栈信息
        frame = None
        try:
            frame = kwargs.pop('_frame', None)
            if frame is None:
                frame = traceback.extract_stack()[-2]
        except:
            frame = None
            
        module = frame.filename if frame else "unknown"
        function = frame.name if frame else "unknown"  
        line = frame.lineno if frame else 0
        
        # 创建日志记录
        record = LogRecord(
            timestamp=datetime.utcnow().isoformat(),
            level=level.value,
            logger=self.name,
            message=message,
            module=module,
            function=function,
            line=line,
            thread_id=threading.get_ident(),
            process_id=os.getpid(),
            extra_fields=kwargs if kwargs else None
        )
        
        # 发送到所有传输
        for transport in self.transports:
            try:
                transport.write(record)
            except Exception as e:
                # 避免传输失败影响日志记录
                print(f"Transport {transport.name} failed: {e}")
                
    def debug(self, message: str, **kwargs) -> None:
        """调试日志"""
        self._log(LogLevel.DEBUG, message, **kwargs)
        
    def info(self, message: str, **kwargs) -> None:
        """信息日志"""
        self._log(LogLevel.INFO, message, **kwargs)
        
    def warning(self, message: str, **kwargs) -> None:
        """警告日志"""
        self._log(LogLevel.WARNING, message, **kwargs)
        
    def error(self, message: str, **kwargs) -> None:
        """错误日志"""
        self._log(LogLevel.ERROR, message, **kwargs)
        
    def critical(self, message: str, **kwargs) -> None:
        """严重错误日志"""
        self._log(LogLevel.CRITICAL, message, **kwargs)
        
    def exception(self, message: str, **kwargs) -> None:
        """异常日志"""
        kwargs['exception'] = traceback.format_exc()
        self._log(LogLevel.ERROR, message, **kwargs)


class LogManager:
    """日志管理器"""
    
    def __init__(self):
        self.loggers: Dict[str, Logger] = {}
        self.transports: List[LogTransport] = []
        self.config: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)
        
    def configure(
        self,
        log_dir: str = "/tmp/agentbus/logs",
        level: str = "INFO",
        format_type: str = "json",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        backup_count: int = 10,
        retention_days: int = 30,
        enable_console: bool = True,
        enable_file: bool = True,
        enable_compression: bool = True,
    ) -> None:
        """配置日志系统"""
        with self._lock:
            self.config = {
                'log_dir': log_dir,
                'level': level,
                'format_type': format_type,
                'max_file_size': max_file_size,
                'backup_count': backup_count,
                'retention_days': retention_days,
                'enable_console': enable_console,
                'enable_file': enable_file,
                'enable_compression': enable_compression,
            }
            
            # 清理现有传输
            for transport in self.transports:
                transport.close()
            self.transports.clear()
            
            # 添加控制台传输
            if enable_console:
                console_format = LogFormat.COLORED if format_type == "colored" else LogFormat.TEXT
                self.transports.append(ConsoleTransport("console", console_format))
                
            # 添加文件传输
            if enable_file:
                log_path = Path(log_dir) / "agentbus.log"
                file_format = LogFormat(format_type)
                self.transports.append(FileTransport("file", str(log_path), file_format))
                
            # 设置日志清理任务
            self._schedule_cleanup()
            
    def get_logger(self, name: str, level: Optional[LogLevel] = None) -> Logger:
        """获取日志记录器"""
        with self._lock:
            if name not in self.loggers:
                log_level = level or LogLevel(self.config.get('level', 'INFO'))
                logger = Logger(name, log_level)
                
                # 添加所有传输
                for transport in self.transports:
                    logger.add_transport(transport)
                    
                self.loggers[name] = logger
                
            return self.loggers[name]
            
    def _schedule_cleanup(self) -> None:
        """安排日志清理任务"""
        def cleanup_task():
            """定期清理旧日志文件"""
            try:
                log_dir = Path(self.config.get('log_dir', '/tmp/agentbus/logs'))
                retention_days = self.config.get('retention_days', 30)
                
                cutoff_date = datetime.now() - timedelta(days=retention_days)
                
                for log_file in log_dir.glob("*.log*"):
                    if log_file.stat().st_mtime < cutoff_date.timestamp():
                        log_file.unlink(missing_ok=True)
                        
            except Exception as e:
                print(f"Log cleanup failed: {e}")
                
        # 每天执行一次清理
        self._executor.submit(cleanup_task)
        
    def shutdown(self) -> None:
        """关闭日志管理器"""
        # 关闭所有传输
        for transport in self.transports:
            transport.close()
            
        # 关闭线程池
        self._executor.shutdown(wait=True)


# 全局日志管理器实例
_log_manager: Optional[LogManager] = None
_logger_cache: Dict[str, Logger] = {}


def configure_logging(**kwargs) -> None:
    """配置全局日志系统"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    _log_manager.configure(**kwargs)


def get_logger(name: str = "agentbus") -> Logger:
    """获取全局日志记录器"""
    global _log_manager, _logger_cache
    
    if name not in _logger_cache:
        if _log_manager is None:
            _log_manager = LogManager()
            _log_manager.configure()
        _logger_cache[name] = _log_manager.get_logger(name)
        
    return _logger_cache[name]


def get_child_logger(parent_name: str, child_name: str) -> Logger:
    """获取子日志记录器"""
    full_name = f"{parent_name}.{child_name}"
    return get_logger(full_name)


def register_log_transport(transport: LogTransport) -> None:
    """注册自定义日志传输"""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
        _log_manager.configure()
        
    _log_manager.transports.append(transport)
    
    # 将传输添加到现有所有logger
    for logger in _log_manager.loggers.values():
        logger.add_transport(transport)