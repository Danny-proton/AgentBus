"""
AgentBus 配置监听器
Configuration File Watcher for AgentBus

提供配置文件监听和热重载功能，基于watchdog库实现。
"""

import os
import time
import threading
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Set
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import logging

# 可选的热重载支持
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
    HAS_WATCHDOG = True
except ImportError:
    Observer = None
    FileSystemEventHandler = None
    FileModifiedEvent = None
    FileCreatedEvent = None
    HAS_WATCHDOG = False

from .config_types import WatchEvent, ConfigEvent, ConfigCallback


logger = logging.getLogger(__name__)


class WatchEventType(str, Enum):
    """监听事件类型"""
    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"
    MOVED = "moved"


@dataclass
class FileChangeInfo:
    """文件变更信息"""
    path: Path
    event_type: WatchEventType
    timestamp: float
    file_hash: Optional[str] = None
    size: Optional[int] = None


class ConfigFileHandler(FileSystemEventHandler if HAS_WATCHDOG else object):
    """配置文件事件处理器"""
    
    def __init__(self, watcher: 'ConfigWatcher'):
        self.watcher = watcher
        self._last_modified_times: Dict[Path, float] = {}
        self._file_hashes: Dict[Path, str] = {}
    
    def on_modified(self, event):
        """文件修改事件处理"""
        if not HAS_WATCHDOG:
            return
            
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        self._handle_file_change(file_path, WatchEventType.MODIFIED)
    
    def on_created(self, event):
        """文件创建事件处理"""
        if not HAS_WATCHDOG:
            return
            
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        self._handle_file_change(file_path, WatchEventType.CREATED)
    
    def on_deleted(self, event):
        """文件删除事件处理"""
        if not HAS_WATCHDOG:
            return
            
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        self._handle_file_change(file_path, WatchEventType.DELETED)
    
    def on_moved(self, event):
        """文件移动事件处理"""
        if not HAS_WATCHDOG:
            return
            
        if event.is_directory:
            return
            
        dest_path = Path(event.dest_path)
        self._handle_file_change(dest_path, WatchEventType.MOVED)
    
    def _handle_file_change(self, file_path: Path, event_type: WatchEventType):
        """处理文件变更"""
        # 检查是否为配置文件
        if not self._is_config_file(file_path):
            return
        
        # 防抖处理
        current_time = time.time()
        last_modified = self._last_modified_times.get(file_path, 0)
        
        if current_time - last_modified < 1.0:  # 1秒内忽略重复事件
            return
        
        self._last_modified_times[file_path] = current_time
        
        # 计算文件哈希
        file_hash = None
        file_size = None
        
        if file_path.exists() and file_path.is_file():
            try:
                file_size = file_path.stat().st_size
                with open(file_path, 'rb') as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
            except Exception as e:
                logger.error(f"读取文件失败 {file_path}: {e}")
                return
        
        # 检查是否真的发生了变化
        if event_type == WatchEventType.MODIFIED:
            old_hash = self._file_hashes.get(file_path)
            if old_hash and old_hash == file_hash:
                return  # 内容没有变化
        
        # 更新哈希记录
        self._file_hashes[file_path] = file_hash
        
        # 创建变更信息
        change_info = FileChangeInfo(
            path=file_path,
            event_type=event_type,
            timestamp=current_time,
            file_hash=file_hash,
            size=file_size
        )
        
        # 添加到变更队列
        self.watcher._add_change(change_info)
    
    def _is_config_file(self, file_path: Path) -> bool:
        """检查是否为配置文件"""
        if not file_path.is_file():
            return False
        
        config_extensions = {'.yaml', '.yml', '.json', '.toml', '.env'}
        return file_path.suffix.lower() in config_extensions


class ConfigWatcher:
    """配置监听器"""
    
    def __init__(self, config_dir: Path, recursive: bool = True):
        self.config_dir = Path(config_dir)
        self.recursive = recursive
        self._observer: Optional[Observer] = None
        self._handler: Optional[ConfigFileHandler] = None
        self._callbacks: List[ConfigCallback] = []
        self._change_queue: List[FileChangeInfo] = []
        self._queue_lock = threading.RLock()
        self._watch_thread: Optional[threading.Thread] = None
        self._running = False
        
        # 创建必要的目录
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def start(self):
        """启动监听器"""
        if self._running:
            logger.warning("监听器已在运行")
            return
        
        if not HAS_WATCHDOG:
            logger.warning("watchdog库未安装，使用轮询模式")
            self._start_polling()
            return
        
        try:
            # 创建观察者
            self._observer = Observer()
            self._handler = ConfigFileHandler(self)
            
            # 添加监控目录
            self._observer.schedule(
                self._handler,
                str(self.config_dir),
                recursive=self.recursive
            )
            
            # 启动观察者
            self._observer.start()
            self._running = True
            
            # 启动处理线程
            self._start_processing_thread()
            
            logger.info(f"配置监听器已启动，监控目录: {self.config_dir}")
            
        except Exception as e:
            logger.error(f"启动配置监听器失败: {e}")
            raise
    
    def stop(self):
        """停止监听器"""
        if not self._running:
            return
        
        self._running = False
        
        try:
            if self._observer and HAS_WATCHDOG:
                self._observer.stop()
                self._observer.join(timeout=5)
            
            if self._watch_thread and self._watch_thread.is_alive():
                self._watch_thread.join(timeout=5)
            
            logger.info("配置监听器已停止")
            
        except Exception as e:
            logger.error(f"停止配置监听器失败: {e}")
    
    def add_callback(self, callback: ConfigCallback):
        """添加变更回调"""
        with self._queue_lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)
    
    def remove_callback(self, callback: ConfigCallback):
        """移除变更回调"""
        with self._queue_lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def is_running(self) -> bool:
        """检查是否在运行"""
        return self._running
    
    def get_watched_files(self) -> Set[Path]:
        """获取监控的文件列表"""
        if not HAS_WATCHDOG or not self._observer:
            return set()
        
        watched_files = set()
        
        try:
            for watch in self._observer.watches:
                if watch.is_recursive == self.recursive:
                    watched_files.update(self._get_files_in_watch(watch))
        except Exception as e:
            logger.error(f"获取监控文件列表失败: {e}")
        
        return watched_files
    
    def force_rescan(self):
        """强制重新扫描"""
        if not HAS_WATCHDOG:
            self._poll_for_changes()
            return
        
        # 停止并重新启动观察者
        if self._observer:
            self._observer.stop()
            self._observer.join()
            
            self._observer = Observer()
            self._observer.schedule(
                self._handler,
                str(self.config_dir),
                recursive=self.recursive
            )
            self._observer.start()
    
    def _start_processing_thread(self):
        """启动处理线程"""
        self._watch_thread = threading.Thread(target=self._process_changes, daemon=True)
        self._watch_thread.start()
    
    def _start_polling(self):
        """启动轮询模式"""
        self._running = True
        self._start_processing_thread()
    
    def _process_changes(self):
        """处理变更队列"""
        while self._running:
            try:
                # 从队列获取变更
                change_info = self._get_next_change()
                
                if change_info:
                    # 发送变更事件
                    self._emit_change_event(change_info)
                
                time.sleep(0.1)  # 避免CPU占用过高
                
            except Exception as e:
                logger.error(f"处理配置变更失败: {e}")
                time.sleep(1)
    
    def _poll_for_changes(self):
        """轮询检查文件变更"""
        try:
            for file_path in self._get_all_config_files():
                current_time = time.time()
                last_modified = self._last_modified_times.get(file_path, 0)
                
                if file_path.exists():
                    stat = file_path.stat()
                    current_mtime = stat.st_mtime
                    
                    if current_mtime > last_modified:
                        # 文件发生变化
                        change_info = FileChangeInfo(
                            path=file_path,
                            event_type=WatchEventType.MODIFIED,
                            timestamp=current_time,
                            file_hash=hashlib.md5(open(file_path, 'rb').read()).hexdigest(),
                            size=stat.st_size
                        )
                        
                        self._add_change(change_info)
                        self._last_modified_times[file_path] = current_mtime
                else:
                    # 文件被删除
                    if last_modified > 0:
                        change_info = FileChangeInfo(
                            path=file_path,
                            event_type=WatchEventType.DELETED,
                            timestamp=current_time
                        )
                        
                        self._add_change(change_info)
                        self._last_modified_times[file_path] = 0
        
        except Exception as e:
            logger.error(f"轮询文件变更失败: {e}")
    
    def _get_all_config_files(self) -> Set[Path]:
        """获取所有配置文件"""
        config_files = set()
        config_extensions = {'.yaml', '.yml', '.json', '.toml', '.env'}
        
        try:
            if self.recursive:
                for file_path in self.config_dir.rglob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in config_extensions:
                        config_files.add(file_path)
            else:
                for file_path in self.config_dir.glob('*'):
                    if file_path.is_file() and file_path.suffix.lower() in config_extensions:
                        config_files.add(file_path)
        except Exception as e:
            logger.error(f"获取配置文件列表失败: {e}")
        
        return config_files
    
    def _add_change(self, change_info: FileChangeInfo):
        """添加变更到队列"""
        with self._queue_lock:
            self._change_queue.append(change_info)
    
    def _get_next_change(self) -> Optional[FileChangeInfo]:
        """从队列获取下一个变更"""
        with self._queue_lock:
            if self._change_queue:
                return self._change_queue.pop(0)
            return None
    
    def _emit_change_event(self, change_info: FileChangeInfo):
        """发送变更事件"""
        try:
            # 确定事件类型
            if change_info.event_type == WatchEventType.MODIFIED:
                event_type = ConfigEvent.UPDATED
            elif change_info.event_type == WatchEventType.CREATED:
                event_type = ConfigEvent.LOADED
            elif change_info.event_type == WatchEventType.DELETED:
                event_type = ConfigEvent.ERROR
            else:
                event_type = ConfigEvent.RELOADED
            
            # 创建事件
            event = WatchEvent(
                event_type=event_type,
                path=change_info.path,
                timestamp=change_info.timestamp,
                data={
                    "event_type": change_info.event_type.value,
                    "file_hash": change_info.file_hash,
                    "file_size": change_info.size
                }
            )
            
            # 调用回调
            for callback in self._callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"配置变更回调执行失败: {e}")
            
            logger.debug(f"配置文件变更: {change_info.path} ({change_info.event_type.value})")
            
        except Exception as e:
            logger.error(f"发送配置变更事件失败: {e}")
    
    def _get_files_in_watch(self, watch) -> Set[Path]:
        """获取监控目录下的文件"""
        files = set()
        
        try:
            if hasattr(watch, 'path') and os.path.exists(watch.path):
                if os.path.isfile(watch.path):
                    files.add(Path(watch.path))
                elif os.path.isdir(watch.path):
                    if watch.is_recursive:
                        for file_path in Path(watch.path).rglob('*'):
                            if file_path.is_file():
                                files.add(file_path)
                    else:
                        for file_path in Path(watch.path).glob('*'):
                            if file_path.is_file():
                                files.add(file_path)
        except Exception as e:
            logger.error(f"获取监控文件失败: {e}")
        
        return files
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop()


# 便捷函数
def create_config_watcher(config_dir: Path, recursive: bool = True) -> ConfigWatcher:
    """创建配置监听器"""
    return ConfigWatcher(config_dir, recursive)


def start_config_watcher(config_dir: Path, callback: ConfigCallback, 
                        recursive: bool = True) -> ConfigWatcher:
    """启动配置监听器"""
    watcher = ConfigWatcher(config_dir, recursive)
    watcher.add_callback(callback)
    watcher.start()
    return watcher


# 模拟监听器（当watchdog不可用时）
class MockConfigWatcher:
    """模拟配置监听器（用于测试或watchdog不可用时）"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self._callbacks: List[ConfigCallback] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_scan = time.time()
    
    def start(self):
        """启动模拟监听器"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._simulate_changes, daemon=True)
        self._thread.start()
        
        logger.info(f"模拟配置监听器已启动: {self.config_dir}")
    
    def stop(self):
        """停止模拟监听器"""
        self._running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        logger.info("模拟配置监听器已停止")
    
    def add_callback(self, callback: ConfigCallback):
        """添加回调"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback: ConfigCallback):
        """移除回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def is_running(self) -> bool:
        """检查是否在运行"""
        return self._running
    
    def _simulate_changes(self):
        """模拟文件变更（仅用于测试）"""
        while self._running:
            try:
                time.sleep(5)  # 每5秒检查一次
                
                # 这里可以添加模拟逻辑
                # 在实际使用中，这个类主要用于测试
                
            except Exception as e:
                logger.error(f"模拟监听器错误: {e}")


# 工厂函数
def create_watcher(config_dir: Path, recursive: bool = True) -> ConfigWatcher:
    """创建合适的监听器"""
    if HAS_WATCHDOG:
        return ConfigWatcher(config_dir, recursive)
    else:
        logger.warning("watchdog不可用，使用模拟监听器")
        return MockConfigWatcher(config_dir)