#!/usr/bin/env python3
"""
Moltbot Python Implementation
============================

跨平台AI助手的Python实现
Cross-platform AI assistant implementation in Python

Author: MiniMax Agent
License: MIT
"""

__version__ = "1.0.0"
__author__ = "MiniMax Agent"
__license__ = "MIT"

# 核心模块导入
from py_moltbot.core.config import Settings
from py_moltbot.core.logger import get_logger
from py_moltbot.core.app import MoltBot
from py_moltbot.adapters.base import BaseAdapter
from py_moltbot.skills.base import BaseSkill

# 版本信息
VERSION_INFO = {
    "version": __version__,
    "author": __author__,
    "license": __license__,
    "description": "跨平台AI助手的Python实现",
}

__all__ = [
    "MoltBot",
    "BaseAdapter", 
    "BaseSkill",
    "Settings",
    "get_logger",
    "VERSION_INFO",
]