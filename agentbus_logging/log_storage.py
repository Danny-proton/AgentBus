"""
AgentBus日志存储管理系统

提供高级日志存储、压缩、索引和管理功能
"""

import os
import json
import sqlite3
import threading
import time
import shutil
import gzip
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union, Iterator
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import hashlib
import re
import tempfile
import subprocess
import mmap
import bisect

from .log_manager import LogRecord, LogLevel


class StorageStrategy(Enum):
    """存储策略枚举"""
    TEXT = "text"           # 纯文本
    JSON = "json"          # JSON格式
    BINARY = "binary"      # 二进制格式
    COMPRESSED = "compressed"  # 压缩格式
    MIXED = "mixed"        # 混合格式


class CompressionType(Enum):
    """压缩类型枚举"""
    NONE = "none"
    GZIP = "gzip"
    ZSTD = "zstd"
    LZ4 = "lz4"


@dataclass
class StorageConfig:
    """存储配置"""
    base_path: str
    strategy: StorageStrategy = StorageStrategy.JSON
    compression: CompressionType = CompressionType.GZIP
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    max_files_per_day: int = 24  # 每天最多24个文件（每小时1个）
    retention_days: int = 30
    enable_indexing: bool = True
    enable_partitioning: bool = True
    partition_interval: str = "hour"  # hour, day, week
    encrypt_sensitive: bool = False


@dataclass
class LogSegment:
    """日志段"""
    file_path: str
    start_time: datetime
    end_time: datetime
    record_count: int
    file_size: int
    compressed: bool
    checksum: str
    metadata: Dict[str, Any]


class LogStorage:
    """日志存储管理器"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.base_path = Path(config.base_path)
        self._lock = threading.RLock()
        self._current_segment: Optional[LogSegment] = None
        self._segment_file = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._metadata_db = None
        self._index_db = None
        
        # 初始化存储目录
        self._init_storage()
        
        # 启动后台任务
        self._start_background_tasks()
        
    def _init_storage(self) -> None:
        """初始化存储结构"""
        # 创建目录结构
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.base_path / "logs").mkdir(exist_ok=True)
        (self.base_path / "index").mkdir(exist_ok=True)
        (self.base_path / "metadata").mkdir(exist_ok=True)
        (self.base_path / "temp").mkdir(exist_ok=True)
        
        # 初始化数据库
        self._init_metadata_db()
        if self.config.enable_indexing:
            self._init_index_db()
            
        # 恢复当前段
        self._restore_current_segment()
        
    def _init_metadata_db(self) -> None:
        """初始化元数据数据库"""
        metadata_path = self.base_path / "metadata" / "storage.db"
        self._metadata_db = sqlite3.connect(str(metadata_path), check_same_thread=False)
        
        # 创建表
        self._metadata_db.execute("""
            CREATE TABLE IF NOT EXISTS segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                record_count INTEGER DEFAULT 0,
                file_size INTEGER DEFAULT 0,
                compressed INTEGER DEFAULT 0,
                checksum TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self._metadata_db.execute("""
            CREATE TABLE IF NOT EXISTS storage_stats (
                date TEXT PRIMARY KEY,
                total_records INTEGER DEFAULT 0,
                total_size INTEGER DEFAULT 0,
                compression_ratio REAL DEFAULT 1.0,
                avg_records_per_hour REAL DEFAULT 0
            )
        """)
        
        self._metadata_db.commit()
        
    def _init_index_db(self) -> None:
        """初始化索引数据库"""
        index_path = self.base_path / "index" / "logs.db"
        self._index_db = sqlite3.connect(str(index_path), check_same_thread=False)
        
        self._index_db.execute("""
            CREATE TABLE IF NOT EXISTS log_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                segment_id INTEGER,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                logger TEXT NOT NULL,
                position INTEGER NOT NULL,
                size INTEGER NOT NULL,
                checksum TEXT,
                FOREIGN KEY (segment_id) REFERENCES segments (id)
            )
        """)
        
        # 创建索引
        self._index_db.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON log_index(timestamp)")
        self._index_db.execute("CREATE INDEX IF NOT EXISTS idx_level ON log_index(level)")
        self._index_db.execute("CREATE INDEX IF NOT EXISTS idx_logger ON log_index(logger)")
        self._index_db.execute("CREATE INDEX IF NOT EXISTS idx_segment ON log_index(segment_id)")
        
        self._index_db.commit()
        
    def _restore_current_segment(self) -> None:
        """恢复当前日志段"""
        # 查找最近的未完成段
        cursor = self._metadata_db.execute("""
            SELECT * FROM segments 
            WHERE end_time IS NULL 
            ORDER BY created_at DESC LIMIT 1
        """)
        row = cursor.fetchone()
        
        if row:
            segment = self._segment_from_row(row)
            self._current_segment = segment
            
            # 打开文件继续写入
            if Path(segment.file_path).exists():
                self._segment_file = open(segment.file_path, 'a', encoding='utf-8')
            else:
                self._start_new_segment()
        else:
            self._start_new_segment()
            
    def _start_new_segment(self) -> None:
        """开始新的日志段"""
        timestamp = datetime.now()
        if self.config.partition_interval == "hour":
            segment_name = f"logs_{timestamp.strftime('%Y%m%d_%H')}.log"
        elif self.config.partition_interval == "day":
            segment_name = f"logs_{timestamp.strftime('%Y%m%d')}.log"
        else:
            segment_name = f"logs_{timestamp.strftime('%Y%m%d_%H%M%S')}.log"
            
        segment_path = self.base_path / "logs" / segment_name
        
        # 关闭当前段
        if self._segment_file:
            self._segment_file.close()
            self._finalize_segment()
            
        # 开始新段
        self._segment_file = open(segment_path, 'a', encoding='utf-8')
        
        # 创建段对象
        self._current_segment = LogSegment(
            file_path=str(segment_path),
            start_time=timestamp,
            end_time=None,
            record_count=0,
            file_size=0,
            compressed=False,
            checksum="",
            metadata={}
        )
        
        # 保存到数据库
        self._save_segment(self._current_segment)
        
    def _save_segment(self, segment: LogSegment) -> None:
        """保存段到数据库"""
        with self._lock:
            self._metadata_db.execute("""
                INSERT OR REPLACE INTO segments 
                (file_path, start_time, end_time, record_count, file_size, compressed, checksum, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                segment.file_path,
                segment.start_time.isoformat(),
                segment.end_time.isoformat() if segment.end_time else None,
                segment.record_count,
                segment.file_size,
                1 if segment.compressed else 0,
                segment.checksum,
                json.dumps(segment.metadata)
            ))
            self._metadata_db.commit()
            
    def _segment_from_row(self, row) -> LogSegment:
        """从数据库行创建段对象"""
        return LogSegment(
            file_path=row[1],
            start_time=datetime.fromisoformat(row[2]),
            end_time=datetime.fromisoformat(row[3]) if row[3] else None,
            record_count=row[4],
            file_size=row[5],
            compressed=bool(row[6]),
            checksum=row[7] or "",
            metadata=json.loads(row[8]) if row[8] else {}
        )
        
    def write_record(self, record: LogRecord) -> None:
        """写入日志记录"""
        with self._lock:
            # 检查是否需要轮转段
            if self._should_rotate_segment():
                self._start_new_segment()
                
            # 序列化记录
            serialized_record = self._serialize_record(record)
            
            # 写入文件
            self._segment_file.write(serialized_record + '\n')
            self._segment_file.flush()
            
            # 更新段信息
            if self._current_segment:
                self._current_segment.record_count += 1
                self._current_segment.file_size = Path(self._current_segment.file_path).stat().st_size
                
                # 更新索引
                if self.config.enable_indexing:
                    self._index_record(record)
                    
    def _serialize_record(self, record: LogRecord) -> str:
        """序列化日志记录"""
        if self.config.strategy == StorageStrategy.JSON:
            return json.dumps(record.to_dict(), ensure_ascii=False)
        elif self.config.strategy == StorageStrategy.TEXT:
            # 文本格式
            return record.to_text()
        elif self.config.strategy == StorageStrategy.BINARY:
            # 二进制格式
            return pickle.dumps(record)
        else:
            # 默认JSON
            return json.dumps(record.to_dict(), ensure_ascii=False)
            
    def _index_record(self, record: LogRecord) -> None:
        """索引日志记录"""
        if not self._index_db or not self._current_segment:
            return
            
        # 计算位置和校验和
        position = self._segment_file.tell()
        serialized = self._serialize_record(record)
        checksum = hashlib.sha256(serialized.encode()).hexdigest()
        
        # 保存到索引
        self._index_db.execute("""
            INSERT INTO log_index 
            (segment_id, timestamp, level, logger, position, size, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            self._get_current_segment_id(),
            record.timestamp,
            record.level,
            record.logger,
            position,
            len(serialized.encode()),
            checksum
        ))
        
    def _get_current_segment_id(self) -> int:
        """获取当前段ID"""
        cursor = self._metadata_db.execute("""
            SELECT id FROM segments WHERE file_path = ? LIMIT 1
        """, (self._current_segment.file_path,))
        row = cursor.fetchone()
        return row[0] if row else 0
        
    def _should_rotate_segment(self) -> bool:
        """检查是否应该轮转段"""
        if not self._current_segment:
            return True
            
        # 检查文件大小
        if self._current_segment.file_size >= self.config.max_file_size:
            return True
            
        # 检查时间间隔
        if self.config.partition_interval == "hour":
            time_diff = datetime.now() - self._current_segment.start_time
            if time_diff.total_seconds() >= 3600:  # 1小时
                return True
        elif self.config.partition_interval == "day":
            time_diff = datetime.now() - self._current_segment.start_time
            if time_diff.total_seconds() >= 86400:  # 1天
                return True
                
        return False
        
    def _finalize_segment(self) -> None:
        """完成当前段"""
        if not self._current_segment:
            return
            
        # 更新段结束时间
        self._current_segment.end_time = datetime.now()
        
        # 计算校验和
        self._current_segment.checksum = self._calculate_file_checksum(self._current_segment.file_path)
        
        # 压缩文件（如果启用）
        if self.config.compression != CompressionType.NONE:
            self._compress_segment()
            
        # 保存到数据库
        self._save_segment(self._current_segment)
        
    def _calculate_file_checksum(self, file_path: str) -> str:
        """计算文件校验和"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
        
    def _compress_segment(self) -> None:
        """压缩段文件"""
        if not self._current_segment:
            return
            
        original_path = Path(self._current_segment.file_path)
        compressed_path = Path(str(original_path) + '.gz')
        
        try:
            with open(original_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                    
            # 删除原文件
            original_path.unlink()
            
            # 更新段信息
            self._current_segment.file_path = str(compressed_path)
            self._current_segment.compressed = True
            self._current_segment.file_size = compressed_path.stat().st_size
            
        except Exception as e:
            print(f"Failed to compress segment {original_path}: {e}")
            
    def query_records(self, start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None,
                     levels: Optional[List[str]] = None,
                     loggers: Optional[List[str]] = None,
                     limit: Optional[int] = None) -> Iterator[LogRecord]:
        """查询日志记录"""
        if not self.config.enable_indexing:
            # 如果没有索引，使用全表扫描
            return self._full_scan_query(start_time, end_time, levels, loggers, limit)
        else:
            # 使用索引查询
            return self._indexed_query(start_time, end_time, levels, loggers, limit)
            
    def _indexed_query(self, start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None,
                      levels: Optional[List[str]] = None,
                      loggers: Optional[List[str]] = None,
                      limit: Optional[int] = None) -> Iterator[LogRecord]:
        """使用索引查询"""
        conditions = []
        params = []
        
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())
            
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())
            
        if levels:
            placeholders = ",".join("?" * len(levels))
            conditions.append(f"level IN ({placeholders})")
            params.extend(levels)
            
        if loggers:
            placeholders = ",".join("?" * len(loggers))
            conditions.append(f"logger IN ({placeholders})")
            params.extend(loggers)
            
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        sql = f"""
            SELECT li.*, s.file_path, s.compressed
            FROM log_index li
            JOIN segments s ON li.segment_id = s.id
            WHERE {where_clause}
            ORDER BY li.timestamp DESC
            {limit_clause}
        """
        
        cursor = self._index_db.execute(sql, params)
        
        for row in cursor.fetchall():
            yield self._record_from_index_row(row)
            
    def _full_scan_query(self, start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        levels: Optional[List[str]] = None,
                        loggers: Optional[List[str]] = None,
                        limit: Optional[int] = None) -> Iterator[LogRecord]:
        """全表扫描查询"""
        # 获取所有段文件
        cursor = self._metadata_db.execute("""
            SELECT * FROM segments 
            WHERE (start_time <= ? OR ? IS NULL)
            AND (end_time >= ? OR ? IS NULL)
            ORDER BY start_time DESC
        """, (
            end_time.isoformat() if end_time else None,
            end_time.isoformat() if end_time else None,
            start_time.isoformat() if start_time else None,
            start_time.isoformat() if start_time else None
        ))
        
        records_yielded = 0
        
        for row in cursor.fetchall():
            if limit and records_yielded >= limit:
                break
                
            segment = self._segment_from_row(row)
            
            # 读取文件记录
            records = self._read_segment_records(segment)
            
            for record in records:
                if limit and records_yielded >= limit:
                    break
                    
                # 应用过滤器
                if levels and record.level not in levels:
                    continue
                    
                if loggers and record.logger not in loggers:
                    continue
                    
                if start_time and datetime.fromisoformat(record.timestamp.replace('Z', '+00:00')) < start_time:
                    continue
                    
                if end_time and datetime.fromisoformat(record.timestamp.replace('Z', '+00:00')) > end_time:
                    continue
                    
                yield record
                records_yielded += 1
                
    def _record_from_index_row(self, row) -> LogRecord:
        """从索引行创建记录对象"""
        # 这里需要根据实际存储格式来反序列化
        # 简化实现
        return LogRecord(
            timestamp=row[2],
            level=row[3],
            logger=row[4],
            message="",
            module="",
            function="",
            line=0
        )
        
    def _read_segment_records(self, segment: LogSegment) -> List[LogRecord]:
        """读取段文件中的所有记录"""
        records = []
        file_path = Path(segment.file_path)
        
        try:
            if segment.compressed:
                file_opener = gzip.open
            else:
                file_opener = open
                
            with file_opener(file_path, 'rt', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        record = self._deserialize_record(line)
                        if record:
                            records.append(record)
                            
        except Exception as e:
            print(f"Failed to read segment {segment.file_path}: {e}")
            
        return records
        
    def _deserialize_record(self, data: str) -> Optional[LogRecord]:
        """反序列化记录"""
        try:
            if self.config.strategy == StorageStrategy.JSON:
                record_data = json.loads(data)
                return LogRecord(**record_data)
            elif self.config.strategy == StorageStrategy.TEXT:
                # 简单的文本解析
                # 这里需要根据实际文本格式进行解析
                return None
            elif self.config.strategy == StorageStrategy.BINARY:
                return pickle.loads(data.encode())
            else:
                return None
        except Exception as e:
            print(f"Failed to deserialize record: {e}")
            return None
            
    def cleanup_old_logs(self) -> None:
        """清理过期日志"""
        cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)
        
        # 查找过期段
        cursor = self._metadata_db.execute("""
            SELECT * FROM segments 
            WHERE end_time < ?
            ORDER BY end_time ASC
        """, (cutoff_date.isoformat(),))
        
        for row in cursor.fetchall():
            segment = self._segment_from_row(row)
            
            try:
                # 删除物理文件
                file_path = Path(segment.file_path)
                if file_path.exists():
                    file_path.unlink()
                    
                # 删除索引记录
                if self.config.enable_indexing:
                    self._index_db.execute("DELETE FROM log_index WHERE segment_id = ?", (row[0],))
                    
                # 删除段记录
                self._metadata_db.execute("DELETE FROM segments WHERE id = ?", (row[0],))
                
                print(f"Cleaned up old log segment: {segment.file_path}")
                
            except Exception as e:
                print(f"Failed to cleanup segment {segment.file_path}: {e}")
                
        self._metadata_db.commit()
        if self.config.enable_indexing:
            self._index_db.commit()
            
    def _start_background_tasks(self) -> None:
        """启动后台任务"""
        def cleanup_task():
            while True:
                try:
                    self.cleanup_old_logs()
                    # 每天执行一次清理
                    time.sleep(86400)
                except Exception as e:
                    print(f"Cleanup task error: {e}")
                    time.sleep(3600)  # 出错时1小时后重试
                    
        self._executor.submit(cleanup_task)
        
    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        cursor = self._metadata_db.execute("""
            SELECT 
                COUNT(*) as total_segments,
                SUM(record_count) as total_records,
                SUM(file_size) as total_size,
                AVG(file_size) as avg_file_size
            FROM segments
        """)
        
        row = cursor.fetchone()
        
        return {
            "total_segments": row[0] or 0,
            "total_records": row[1] or 0,
            "total_size": row[2] or 0,
            "avg_file_size": row[3] or 0,
            "storage_path": str(self.base_path)
        }
        
    def export_data(self, start_time: datetime, end_time: datetime, 
                   output_path: str, format_type: str = "json") -> None:
        """导出数据"""
        records = list(self.query_records(start_time, end_time))
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        if format_type == "json":
            with open(output_file, 'w', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record.to_dict(), ensure_ascii=False) + '\n')
        elif format_type == "csv":
            import csv
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "level", "logger", "message", "module", "function", "line"])
                for record in records:
                    writer.writerow([
                        record.timestamp, record.level, record.logger, record.message,
                        record.module, record.function, record.line
                    ])
                    
    def close(self) -> None:
        """关闭存储管理器"""
        with self._lock:
            if self._segment_file:
                self._segment_file.close()
                self._finalize_segment()
                
            if self._metadata_db:
                self._metadata_db.close()
                
            if self._index_db:
                self._index_db.close()
                
            self._executor.shutdown(wait=True)


class LogArchiveManager:
    """日志归档管理器"""
    
    def __init__(self, storage: LogStorage, archive_path: str):
        self.storage = storage
        self.archive_path = Path(archive_path)
        self.archive_path.mkdir(parents=True, exist_ok=True)
        
    def create_archive(self, start_time: datetime, end_time: datetime, 
                      compression: bool = True) -> str:
        """创建日志归档"""
        # 生成归档文件名
        archive_name = f"logs_{start_time.strftime('%Y%m%d_%H%M%S')}_{end_time.strftime('%Y%m%d_%H%M%S')}"
        if compression:
            archive_name += ".tar.gz"
        else:
            archive_name += ".tar"
            
        archive_file = self.archive_path / archive_name
        
        # 收集要归档的文件
        files_to_archive = []
        
        # 查询匹配的段
        cursor = self.storage._metadata_db.execute("""
            SELECT * FROM segments 
            WHERE (start_time <= ? AND end_time >= ?)
            ORDER BY start_time ASC
        """, (end_time.isoformat(), start_time.isoformat()))
        
        for row in cursor.fetchall():
            segment = self.storage._segment_from_row(row)
            if Path(segment.file_path).exists():
                files_to_archive.append(segment.file_path)
                
        # 创建归档
        if compression:
            import tarfile
            with tarfile.open(archive_file, "w:gz") as tar:
                for file_path in files_to_archive:
                    tar.add(file_path, arcname=Path(file_path).name)
        else:
            import tarfile
            with tarfile.open(archive_file, "w") as tar:
                for file_path in files_to_archive:
                    tar.add(file_path, arcname=Path(file_path).name)
                    
        return str(archive_file)
        
    def restore_archive(self, archive_path: str, restore_path: str) -> None:
        """恢复归档"""
        archive_file = Path(archive_path)
        restore_dir = Path(restore_path)
        restore_dir.mkdir(parents=True, exist_ok=True)
        
        if archive_path.endswith('.tar.gz'):
            import tarfile
            with tarfile.open(archive_file, "r:gz") as tar:
                tar.extractall(restore_dir)
        else:
            import tarfile
            with tarfile.open(archive_file, "r") as tar:
                tar.extractall(restore_dir)


# 便捷函数
def create_storage(config: StorageConfig) -> LogStorage:
    """创建日志存储"""
    return LogStorage(config)


def create_archive_manager(storage: LogStorage, archive_path: str) -> LogArchiveManager:
    """创建归档管理器"""
    return LogArchiveManager(storage, archive_path)