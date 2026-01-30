"""
日志系统
Logging System
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger
from .config import settings


def setup_logging() -> None:
    """设置日志系统"""
    # 获取日志配置
    log_config = settings.logging
    
    # 移除默认的logger配置
    logger.remove()
    
    # 创建logs目录
    if log_config.file_path:
        log_path = Path(log_config.file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置控制台输出
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    if settings.is_development():
        # 开发环境使用彩色输出
        logger.add(
            sys.stdout,
            format=console_format,
            level=log_config.level.upper(),
            colorize=True,
            backtrace=True,
            diagnose=True
        )
    else:
        # 生产环境使用简洁输出
        console_format_simple = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
        logger.add(
            sys.stdout,
            format=console_format_simple,
            level="INFO",
            colorize=False,
            backtrace=False,
            diagnose=False
        )
    
    # 配置文件输出（如果配置了文件路径）
    if log_config.file_path:
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
        
        if settings.is_production():
            # 生产环境使用更详细的日志格式
            file_format = (
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{process} | "
                "{thread} | "
                "{name}:{function}:{line} | "
                "{message}"
            )
        
        logger.add(
            log_config.file_path,
            format=file_format,
            level=log_config.level.upper(),
            rotation=f"{log_config.max_file_size // (1024*1024)} MB",
            retention=f"{log_config.backup_count} files",
            encoding="utf-8",
            backtrace=True,
            diagnose=True
        )
    
    # 配置第三方库的日志级别
    logger.disable("uvicorn.access")
    logger.disable("uvicorn.error")
    logger.disable("httpx")
    logger.disable("discord")
    logger.disable("telegram")
    
    # 记录启动日志
    logger.info(
        "Logging system initialized", 
        level=log_config.level,
        file_output=bool(log_config.file_path),
        development=settings.is_development(),
        production=settings.is_production()
    )


def get_logger(name: Optional[str] = None):
    """获取日志器"""
    if name is None:
        # 获取调用者的模块名
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get('__name__', 'py_moltbot')
        else:
            name = 'py_moltbot'
    
    return logger.bind(name=name)


class LoggerMixin:
    """日志器混入类"""
    
    @property
    def logger(self):
        """获取日志器"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__module__)
        return self._logger


# 便捷函数
def debug(msg: str, **kwargs) -> None:
    """调试日志"""
    get_logger().debug(msg, **kwargs)


def info(msg: str, **kwargs) -> None:
    """信息日志"""
    get_logger().info(msg, **kwargs)


def warning(msg: str, **kwargs) -> None:
    """警告日志"""
    get_logger().warning(msg, **kwargs)


def error(msg: str, **kwargs) -> None:
    """错误日志"""
    get_logger().error(msg, **kwargs)


def critical(msg: str, **kwargs) -> None:
    """严重错误日志"""
    get_logger().critical(msg, **kwargs)


# 初始化日志系统
setup_logging()
