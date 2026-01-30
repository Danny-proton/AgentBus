"""
进程管理类型定义
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any


class ProcessState(Enum):
    """进程状态"""
    RUNNING = "running"
    SLEEPING = "sleeping"
    STOPPED = "stopped"
    ZOMBIE = "zombie"
    UNKNOWN = "unknown"


@dataclass
class ProcessInfo:
    """进程信息"""
    pid: int
    name: str
    state: ProcessState
    cpu_percent: float
    memory_percent: float
    memory_info: Dict[str, int]
    create_time: datetime
    cmdline: List[str]
    exe: Optional[str] = None
    cwd: Optional[str] = None
    parent_pid: Optional[int] = None
    num_threads: Optional[int] = None
    io_counters: Optional[Dict[str, int]] = None
    num_fds: Optional[int] = None
    context_switches: Optional[int] = None
    status: Optional[str] = None


@dataclass
class BinaryInfo:
    """二进制信息"""
    name: str
    path: str
    version: Optional[str] = None
    size: Optional[int] = None
    checksum: Optional[str] = None
    permissions: Optional[str] = None
    is_executable: bool = False
    required_by: List[str] = None
    dependencies: List[str] = None
    description: Optional[str] = None
    vendor: Optional[str] = None


@dataclass
class SystemResourceUsage:
    """系统资源使用情况"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io: Dict[str, int]
    process_count: int
    thread_count: int
    load_average: List[float]


@dataclass
class ProcessMetrics:
    """进程指标"""
    pid: int
    timestamp: datetime
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    io_read_bytes: int
    io_write_bytes: int
    num_threads: int
    num_fds: int
    context_switches_voluntary: int
    context_switches_involuntary: int