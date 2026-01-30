"""
进程管理模块 - 提供进程监控、控制和管理功能
"""

import os
import signal
import asyncio
import time
import psutil
from typing import Dict, List, Optional, Any, Callable
from dataclasses import asdict
from datetime import datetime
from .process_types import ProcessInfo, ProcessState, ProcessMetrics, SystemResourceUsage


class ProcessManager:
    """进程管理器"""
    
    def __init__(self):
        self._metrics_history: Dict[int, List[ProcessMetrics]] = {}
        self._system_metrics_history: List[SystemResourceUsage] = []
        self._monitoring_active = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._process_callbacks: List[Callable[[ProcessInfo], None]] = []
        self._metrics_callbacks: List[Callable[[ProcessMetrics], None]] = []
    
    async def get_process_info(self, pid: int) -> Optional[ProcessInfo]:
        """获取进程信息"""
        try:
            process = psutil.Process(pid)
            with process.oneshot():
                cpu_percent = process.cpu_percent()
                memory_info = process.memory_info()
                create_time = datetime.fromtimestamp(process.create_time())
                
                # 获取命令行
                try:
                    cmdline = process.cmdline()
                except (psutil.AccessDenied, psutil.ZombieProcess):
                    cmdline = []
                
                # 获取其他信息
                try:
                    exe = process.exe()
                except (psutil.AccessDenied, psutil.ZombieProcess):
                    exe = None
                
                try:
                    cwd = process.cwd()
                except (psutil.AccessDenied, psutil.ZombieProcess):
                    cwd = None
                
                try:
                    num_threads = process.num_threads()
                except (psutil.AccessDenied, psutil.ZombieProcess):
                    num_threads = None
                
                try:
                    num_fds = process.num_fds() if hasattr(process, 'num_fds') else None
                except (psutil.AccessDenied, psutil.ZombieProcess):
                    num_fds = None
                
                # 获取进程状态
                try:
                    status = process.status()
                except (psutil.AccessDenied, psutil.ZombieProcess):
                    status = None
                
                return ProcessInfo(
                    pid=pid,
                    name=process.name(),
                    state=self._map_process_state(process.status()),
                    cpu_percent=cpu_percent,
                    memory_percent=process.memory_percent(),
                    memory_info={
                        "rss": memory_info.rss,
                        "vms": memory_info.vms,
                        "shared": getattr(memory_info, 'shared', 0),
                        "text": getattr(memory_info, 'text', 0),
                        "lib": getattr(memory_info, 'lib', 0),
                        "data": getattr(memory_info, 'data', 0),
                        "dirty": getattr(memory_info, 'dirty', 0)
                    },
                    create_time=create_time,
                    cmdline=cmdline,
                    exe=exe,
                    cwd=cwd,
                    parent_pid=process.ppid(),
                    num_threads=num_threads,
                    num_fds=num_fds,
                    status=status
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
    
    def _map_process_state(self, status: str) -> ProcessState:
        """映射进程状态"""
        status_mapping = {
            'running': ProcessState.RUNNING,
            'sleeping': ProcessState.SLEEPING,
            'stopped': ProcessState.STOPPED,
            'zombie': ProcessState.ZOMBIE,
        }
        return status_mapping.get(status, ProcessState.UNKNOWN)
    
    async def list_processes(self, 
                           include_system: bool = False,
                           sort_by: str = 'pid',
                           limit: int = None) -> List[ProcessInfo]:
        """列出进程"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'status']):
            try:
                # 跳过系统进程（可选）
                if not include_system and proc.info['pid'] == 0:
                    continue
                
                info = await self.get_process_info(proc.info['pid'])
                if info:
                    processes.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # 排序
        if sort_by == 'pid':
            processes.sort(key=lambda x: x.pid)
        elif sort_by == 'name':
            processes.sort(key=lambda x: x.name.lower())
        elif sort_by == 'cpu':
            processes.sort(key=lambda x: x.cpu_percent, reverse=True)
        elif sort_by == 'memory':
            processes.sort(key=lambda x: x.memory_percent, reverse=True)
        
        # 限制数量
        if limit:
            processes = processes[:limit]
        
        return processes
    
    async def find_processes_by_name(self, name: str) -> List[ProcessInfo]:
        """按名称查找进程"""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == name.lower():
                    info = await self.get_process_info(proc.info['pid'])
                    if info:
                        processes.append(info)
        except Exception:
            pass
        return processes
    
    async def terminate_process(self, pid: int, timeout: float = 5.0) -> bool:
        """终止进程"""
        try:
            process = psutil.Process(pid)
            process.terminate()
            
            # 等待进程结束
            try:
                process.wait(timeout=timeout)
                return True
            except psutil.TimeoutExpired:
                # 如果超时，强制杀死
                process.kill()
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    async def kill_process(self, pid: int) -> bool:
        """强制杀死进程"""
        try:
            process = psutil.Process(pid)
            process.kill()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    async def suspend_process(self, pid: int) -> bool:
        """暂停进程"""
        try:
            process = psutil.Process(pid)
            process.suspend()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    async def resume_process(self, pid: int) -> bool:
        """恢复进程"""
        try:
            process = psutil.Process(pid)
            process.resume()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    async def get_process_tree(self, root_pid: int = None) -> Dict[str, Any]:
        """获取进程树"""
        if root_pid is None:
            root_pid = os.getpid()
        
        def build_tree(pid: int) -> Dict[str, Any]:
            try:
                process = psutil.Process(pid)
                children = []
                
                for child in process.children(recursive=False):
                    children.append(build_tree(child.pid))
                
                return {
                    "pid": pid,
                    "name": process.name(),
                    "state": process.status(),
                    "cpu_percent": process.cpu_percent(),
                    "memory_percent": process.memory_percent(),
                    "children": children
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return {
                    "pid": pid,
                    "error": "Process not accessible"
                }
        
        return build_tree(root_pid)
    
    async def get_system_resources(self) -> SystemResourceUsage:
        """获取系统资源使用情况"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # 获取负载平均值（仅Linux/macOS）
            load_avg = []
            try:
                load_avg = list(psutil.getloadavg())
            except AttributeError:
                # Windows不支持负载平均值
                load_avg = [0.0, 0.0, 0.0]
            
            return SystemResourceUsage(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage_percent=(disk.used / disk.total) * 100,
                network_io={
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                    "errin": network.errin,
                    "errout": network.errout,
                    "dropin": network.dropin,
                    "dropout": network.dropout
                },
                process_count=len(psutil.pids()),
                thread_count=sum(p.num_threads() for p in psutil.process_iter(['num_threads']) if p.info['num_threads']),
                load_average=load_avg
            )
        except Exception:
            return SystemResourceUsage(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_usage_percent=0.0,
                network_io={},
                process_count=0,
                thread_count=0,
                load_average=[0.0, 0.0, 0.0]
            )
    
    async def start_monitoring(self, interval: float = 5.0):
        """开始进程监控"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitor_task = asyncio.create_task(
            self._monitoring_loop(interval)
        )
    
    async def stop_monitoring(self):
        """停止进程监控"""
        self._monitoring_active = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
    
    async def _monitoring_loop(self, interval: float):
        """监控循环"""
        while self._monitoring_active:
            try:
                await asyncio.sleep(interval)
                
                # 获取系统资源使用情况
                system_usage = await self.get_system_resources()
                self._system_metrics_history.append(system_usage)
                
                # 保持历史记录在合理范围内
                if len(self._system_metrics_history) > 1000:
                    self._system_metrics_history = self._system_metrics_history[-500:]
                
                # 监控重要进程（CPU或内存使用率高的进程）
                processes = await self.list_processes(sort_by='cpu', limit=10)
                for process in processes:
                    if process.cpu_percent > 5.0 or process.memory_percent > 5.0:
                        # 创建进程指标
                        metrics = ProcessMetrics(
                            pid=process.pid,
                            timestamp=datetime.now(),
                            cpu_percent=process.cpu_percent,
                            memory_mb=process.memory_info.get('rss', 0) / 1024 / 1024,
                            memory_percent=process.memory_percent,
                            io_read_bytes=0,  # 需要额外的权限
                            io_write_bytes=0,  # 需要额外的权限
                            num_threads=process.num_threads or 0,
                            num_fds=process.num_fds or 0,
                            context_switches_voluntary=0,  # 需要额外的权限
                            context_switches_involuntary=0  # 需要额外的权限
                        )
                        
                        # 添加到历史记录
                        if process.pid not in self._metrics_history:
                            self._metrics_history[process.pid] = []
                        self._metrics_history[process.pid].append(metrics)
                        
                        # 保持历史记录在合理范围内
                        if len(self._metrics_history[process.pid]) > 200:
                            self._metrics_history[process.pid] = self._metrics_history[process.pid][-100:]
                        
                        # 通知回调
                        for callback in self._metrics_callbacks:
                            try:
                                callback(metrics)
                            except Exception:
                                pass
                
            except asyncio.CancelledError:
                break
            except Exception:
                # 记录错误但继续监控
                pass
    
    def add_process_callback(self, callback: Callable[[ProcessInfo], None]):
        """添加进程回调"""
        self._process_callbacks.append(callback)
    
    def add_metrics_callback(self, callback: Callable[[ProcessMetrics], None]):
        """添加指标回调"""
        self._metrics_callbacks.append(callback)
    
    def get_process_metrics_history(self, pid: int, limit: int = 100) -> List[ProcessMetrics]:
        """获取进程指标历史"""
        return self._metrics_history.get(pid, [])[-limit:]
    
    def get_system_metrics_history(self, limit: int = 100) -> List[SystemResourceUsage]:
        """获取系统指标历史"""
        return self._system_metrics_history[-limit:]
    
    def export_metrics(self, pid: int = None, format: str = "json") -> str:
        """导出指标数据"""
        if pid:
            data = [asdict(metric) for metric in self._metrics_history.get(pid, [])]
        else:
            data = [asdict(usage) for usage in self._system_metrics_history]
        
        if format.lower() == "json":
            import json
            return json.dumps(data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")