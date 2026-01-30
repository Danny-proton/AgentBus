"""
AgentBus日志查询和分析系统

提供强大的日志搜索、过滤、分析和可视化功能
"""

import os
import re
import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union, Iterator
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict, Counter
import gzip
import pickle
import mmap
from concurrent.futures import ThreadPoolExecutor, as_completed
import bisect
import statistics

from .log_manager import LogRecord, LogLevel


@dataclass
class LogQuery:
    """日志查询条件"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    levels: Optional[List[str]] = None
    loggers: Optional[List[str]] = None
    message_pattern: Optional[str] = None
    regex_pattern: Optional[str] = None
    field_filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    sort_by: str = "timestamp"
    sort_order: str = "desc"  # "asc" or "desc"


@dataclass
class LogAnalysisResult:
    """日志分析结果"""
    total_count: int
    time_range: tuple
    level_distribution: Dict[str, int]
    logger_distribution: Dict[str, int]
    hourly_distribution: Dict[int, int]
    error_patterns: List[Dict[str, Any]]
    performance_stats: Dict[str, float]
    custom_analysis: Dict[str, Any]


class LogIndex:
    """日志索引管理器"""
    
    def __init__(self, index_path: str):
        self.index_path = Path(index_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._index_db = None
        self._lock = threading.Lock()
        self._init_database()
        
    def _init_database(self) -> None:
        """初始化索引数据库"""
        self._index_db = sqlite3.connect(
            str(self.index_path), 
            check_same_thread=False
        )
        self._index_db.execute("""
            CREATE TABLE IF NOT EXISTS log_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                logger TEXT NOT NULL,
                message TEXT,
                file_path TEXT NOT NULL,
                file_offset INTEGER NOT NULL,
                compressed INTEGER DEFAULT 0,
                extra_fields TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        self._index_db.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON log_index(timestamp)
        """)
        self._index_db.execute("""
            CREATE INDEX IF NOT EXISTS idx_level ON log_index(level)
        """)
        self._index_db.execute("""
            CREATE INDEX IF NOT EXISTS idx_logger ON log_index(logger)
        """)
        self._index_db.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_time ON log_index(file_path, timestamp)
        """)
        
        self._index_db.commit()
        
    def add_entry(self, timestamp: str, level: str, logger: str, 
                  message: str, file_path: str, file_offset: int,
                  compressed: bool = False, extra_fields: Optional[Dict] = None) -> None:
        """添加索引条目"""
        with self._lock:
            self._index_db.execute("""
                INSERT INTO log_index 
                (timestamp, level, logger, message, file_path, file_offset, compressed, extra_fields)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, level, logger, message, file_path, file_offset, 
                1 if compressed else 0, 
                json.dumps(extra_fields) if extra_fields else None
            ))
            self._index_db.commit()
            
    def search(self, query: LogQuery) -> List[Dict[str, Any]]:
        """搜索日志条目"""
        with self._lock:
            # 构建WHERE子句
            conditions = []
            params = []
            
            if query.start_time:
                conditions.append("timestamp >= ?")
                params.append(query.start_time.isoformat())
                
            if query.end_time:
                conditions.append("timestamp <= ?")
                params.append(query.end_time.isoformat())
                
            if query.levels:
                placeholders = ",".join("?" * len(query.levels))
                conditions.append(f"level IN ({placeholders})")
                params.extend(query.levels)
                
            if query.loggers:
                placeholders = ",".join("?" * len(query.loggers))
                conditions.append(f"logger IN ({placeholders})")
                params.extend(query.loggers)
                
            if query.message_pattern:
                conditions.append("message LIKE ?")
                params.append(f"%{query.message_pattern}%")
                
            if query.regex_pattern:
                conditions.append("message REGEXP ?")
                params.append(query.regex_pattern)
                
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 构建排序
            if query.sort_order == "desc":
                order_clause = f"{query.sort_by} DESC"
            else:
                order_clause = f"{query.sort_by} ASC"
                
            # 构建LIMIT
            limit_clause = ""
            if query.limit:
                limit_clause = f"LIMIT {query.limit}"
                if query.offset:
                    limit_clause += f" OFFSET {query.offset}"
            
            sql = f"""
                SELECT timestamp, level, logger, message, file_path, file_offset, compressed, extra_fields
                FROM log_index
                WHERE {where_clause}
                ORDER BY {order_clause}
                {limit_clause}
            """
            
            cursor = self._index_db.execute(sql, params)
            results = []
            
            for row in cursor.fetchall():
                results.append({
                    "timestamp": row[0],
                    "level": row[1],
                    "logger": row[2],
                    "message": row[3],
                    "file_path": row[4],
                    "file_offset": row[5],
                    "compressed": bool(row[6]),
                    "extra_fields": json.loads(row[7]) if row[7] else None
                })
                
            return results


class LogFileReader:
    """日志文件读取器"""
    
    def __init__(self, file_path: str, compressed: bool = False):
        self.file_path = file_path
        self.compressed = compressed
        self._file_handle = None
        
    def read_record(self, offset: int, size: int) -> Optional[LogRecord]:
        """读取指定位置的日志记录"""
        try:
            with open(self.file_path, 'rb') as f:
                f.seek(offset)
                data = f.read(size)
                
            if self.compressed:
                data = gzip.decompress(data)
                
            line = data.decode('utf-8').strip()
            return self._parse_line(line)
            
        except Exception as e:
            print(f"Failed to read log record: {e}")
            return None
            
    def _parse_line(self, line: str) -> Optional[LogRecord]:
        """解析日志行"""
        try:
            # 尝试JSON格式
            if line.startswith('{'):
                data = json.loads(line)
                return LogRecord(**data)
            else:
                # 解析文本格式
                # 格式: timestamp level logger module:function:line - message
                pattern = r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z)\s+(\w+)\s+(\S+)\s+([^:]+):([^:]+):(\d+)\s+-\s+(.*)'
                match = re.match(pattern, line)
                if match:
                    timestamp, level, logger, module, function, line_num, message = match.groups()
                    return LogRecord(
                        timestamp=timestamp,
                        level=level,
                        logger=logger,
                        message=message,
                        module=module,
                        function=function,
                        line=int(line_num)
                    )
        except Exception as e:
            print(f"Failed to parse log line: {e}")
            
        return None


class LogQueryEngine:
    """日志查询引擎"""
    
    def __init__(self, log_dirs: List[str], index_path: str):
        self.log_dirs = [Path(d) for d in log_dirs]
        self.index = LogIndex(index_path)
        self._file_readers: Dict[str, LogFileReader] = {}
        self._index_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=4)
        
    def index_logs(self, force: bool = False) -> None:
        """索引日志文件"""
        if force:
            # 重建索引
            self.index._index_db.execute("DELETE FROM log_index")
            self.index._index_db.commit()
            
        for log_dir in self.log_dirs:
            if not log_dir.exists():
                continue
                
            for log_file in log_dir.glob("**/*.log*"):
                self._index_file(log_file)
                
    def _index_file(self, file_path: Path) -> None:
        """索引单个日志文件"""
        is_compressed = file_path.suffix == '.gz'
        
        try:
            with open(file_path, 'rb') as f:
                if is_compressed:
                    f = gzip.open(f, 'rt', encoding='utf-8')
                else:
                    f = open(file_path, 'r', encoding='utf-8')
                    
                offset = 0
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # 解析日志行
                    record = self._parse_line(line)
                    if record:
                        # 计算文件偏移量
                        with open(file_path, 'rb') as bf:
                            if is_compressed:
                                # 对于压缩文件，使用字符偏移
                                bf.seek(0)
                                content = gzip.decompress(bf.read()).decode('utf-8')
                                offset = content.find(line.encode('utf-8'))
                            else:
                                offset = bf.tell() - len(line.encode('utf-8'))
                                
                        # 添加到索引
                        self.index.add_entry(
                            timestamp=record.timestamp,
                            level=record.level,
                            logger=record.logger,
                            message=record.message,
                            file_path=str(file_path),
                            file_offset=offset,
                            compressed=is_compressed,
                            extra_fields=record.extra_fields
                        )
                        
        except Exception as e:
            print(f"Failed to index file {file_path}: {e}")
            
    def _parse_line(self, line: str) -> Optional[LogRecord]:
        """解析日志行"""
        try:
            if line.startswith('{'):
                data = json.loads(line)
                return LogRecord(**data)
            else:
                # 简单的文本解析
                pattern = r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z)\s+(\w+)\s+(\S+)\s+(.+)$'
                match = re.match(pattern, line)
                if match:
                    timestamp, level, logger, message = match.groups()
                    return LogRecord(
                        timestamp=timestamp,
                        level=level,
                        logger=logger,
                        message=message,
                        module="",
                        function="",
                        line=0
                    )
        except Exception as e:
            print(f"Failed to parse line: {e}")
            
        return None
        
    def query(self, query: LogQuery) -> List[LogRecord]:
        """执行日志查询"""
        # 从索引获取匹配条目
        index_results = self.index.search(query)
        records = []
        
        # 根据文件路径读取实际日志记录
        for result in index_results:
            reader = self._file_readers.get(result["file_path"])
            if not reader:
                reader = LogFileReader(result["file_path"], result["compressed"])
                self._file_readers[result["file_path"]] = reader
                
            record = reader.read_record(result["file_offset"], 4096)  # 假设最大记录4KB
            if record:
                records.append(record)
                
        return records


class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self):
        self._error_patterns = [
            r"Exception",
            r"Error",
            r"Failed",
            r"Timeout",
            r"Connection.*refused",
            r"OutOfMemory",
            r"NullPointer"
        ]
        
    def analyze(self, records: List[LogRecord]) -> LogAnalysisResult:
        """分析日志记录"""
        if not records:
            return LogAnalysisResult(
                total_count=0,
                time_range=(None, None),
                level_distribution={},
                logger_distribution={},
                hourly_distribution={},
                error_patterns=[],
                performance_stats={},
                custom_analysis={}
            )
            
        # 基本统计
        total_count = len(records)
        timestamps = [datetime.fromisoformat(r.timestamp.replace('Z', '+00:00')) 
                     for r in records if r.timestamp]
        timestamps.sort()
        
        time_range = (
            timestamps[0] if timestamps else None,
            timestamps[-1] if timestamps else None
        )
        
        # 级别分布
        level_dist = Counter(r.level for r in records)
        
        # 日志器分布
        logger_dist = Counter(r.logger for r in records)
        
        # 按小时分布
        hourly_dist = Counter()
        for ts in timestamps:
            hourly_dist[ts.hour] += 1
            
        # 错误模式分析
        error_patterns = self._analyze_error_patterns(records)
        
        # 性能统计
        perf_stats = self._calculate_performance_stats(records)
        
        # 自定义分析
        custom_analysis = self._custom_analysis(records)
        
        return LogAnalysisResult(
            total_count=total_count,
            time_range=time_range,
            level_distribution=dict(level_dist),
            logger_distribution=dict(logger_dist),
            hourly_distribution=dict(hourly_dist),
            error_patterns=error_patterns,
            performance_stats=perf_stats,
            custom_analysis=custom_analysis
        )
        
    def _analyze_error_patterns(self, records: List[LogRecord]) -> List[Dict[str, Any]]:
        """分析错误模式"""
        patterns = []
        
        for pattern in self._error_patterns:
            matches = []
            for record in records:
                if re.search(pattern, record.message, re.IGNORECASE):
                    matches.append({
                        "timestamp": record.timestamp,
                        "logger": record.logger,
                        "message": record.message[:200] + "..." if len(record.message) > 200 else record.message
                    })
                    
            if matches:
                patterns.append({
                    "pattern": pattern,
                    "count": len(matches),
                    "examples": matches[:5]  # 只保留前5个示例
                })
                
        return sorted(patterns, key=lambda x: x["count"], reverse=True)
        
    def _calculate_performance_stats(self, records: List[LogRecord]) -> Dict[str, float]:
        """计算性能统计"""
        stats = {}
        
        # 提取响应时间相关的日志
        response_times = []
        for record in records:
            if record.extra_fields:
                duration = record.extra_fields.get('duration')
                if duration:
                    try:
                        response_times.append(float(duration))
                    except ValueError:
                        continue
                        
        if response_times:
            stats.update({
                "avg_response_time": statistics.mean(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "p95_response_time": statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max(response_times),
                "p99_response_time": statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max(response_times)
            })
            
        return stats
        
    def _custom_analysis(self, records: List[LogRecord]) -> Dict[str, Any]:
        """自定义分析"""
        analysis = {}
        
        # 用户活动分析（如果有user_id字段）
        user_activity = defaultdict(int)
        for record in records:
            if record.extra_fields:
                user_id = record.extra_fields.get('user_id')
                if user_id:
                    user_activity[user_id] += 1
                    
        if user_activity:
            analysis["top_users"] = dict(sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10])
            
        # 模块性能分析
        module_performance = defaultdict(list)
        for record in records:
            if record.extra_fields and record.extra_fields.get('duration'):
                try:
                    duration = float(record.extra_fields['duration'])
                    module_performance[record.module].append(duration)
                except ValueError:
                    continue
                    
        module_stats = {}
        for module, durations in module_performance.items():
            if durations:
                module_stats[module] = {
                    "avg_duration": statistics.mean(durations),
                    "max_duration": max(durations),
                    "call_count": len(durations)
                }
                
        analysis["module_performance"] = module_stats
        
        return analysis


class LogStreamReader:
    """实时日志流读取器"""
    
    def __init__(self, log_files: List[str]):
        self.log_files = [Path(f) for f in log_files]
        self._running = False
        self._watchers: Dict[Path, threading.Thread] = {}
        self._callbacks: List[Callable] = []
        self._last_positions: Dict[Path, int] = {}
        
    def add_callback(self, callback: Callable[[LogRecord], None]) -> None:
        """添加日志回调"""
        self._callbacks.append(callback)
        
    def start(self) -> None:
        """开始监控"""
        self._running = True
        
        for log_file in self.log_files:
            if log_file.exists():
                # 记录当前位置
                with open(log_file, 'rb') as f:
                    f.seek(0, 2)  # 移动到文件末尾
                    self._last_positions[log_file] = f.tell()
                    
                # 启动监控线程
                thread = threading.Thread(
                    target=self._watch_file,
                    args=(log_file,),
                    daemon=True
                )
                thread.start()
                self._watchers[log_file] = thread
                
    def stop(self) -> None:
        """停止监控"""
        self._running = False
        
        for thread in self._watchers.values():
            thread.join(timeout=5)
            
    def _watch_file(self, file_path: Path) -> None:
        """监控单个文件"""
        while self._running:
            try:
                if not file_path.exists():
                    time.sleep(1)
                    continue
                    
                with open(file_path, 'rb') as f:
                    f.seek(self._last_positions.get(file_path, 0))
                    
                    while True:
                        line = f.readline()
                        if not line:
                            break
                            
                        # 解析日志行
                        try:
                            line_str = line.decode('utf-8').strip()
                            if line_str:
                                # 这里需要根据实际日志格式进行解析
                                # 简化实现
                                record = self._parse_line(line_str)
                                if record:
                                    # 通知所有回调
                                    for callback in self._callbacks:
                                        callback(record)
                        except UnicodeDecodeError:
                            continue
                            
                    # 更新位置
                    self._last_positions[file_path] = f.tell()
                    
                time.sleep(0.1)  # 避免CPU占用过高
                
            except Exception as e:
                print(f"Error watching file {file_path}: {e}")
                time.sleep(1)
                
    def _parse_line(self, line: str) -> Optional[LogRecord]:
        """解析日志行"""
        try:
            if line.startswith('{'):
                data = json.loads(line)
                return LogRecord(**data)
        except:
            pass
        return None


class LogVisualizer:
    """日志可视化工具"""
    
    def __init__(self, analysis_result: LogAnalysisResult):
        self.result = analysis_result
        
    def generate_text_report(self) -> str:
        """生成文本报告"""
        report = []
        report.append("=== AgentBus 日志分析报告 ===\n")
        
        # 基本统计
        report.append(f"总日志数: {self.result.total_count}")
        if self.result.time_range[0] and self.result.time_range[1]:
            duration = self.result.time_range[1] - self.result.time_range[0]
            report.append(f"时间范围: {self.result.time_range[0]} 到 {self.result.time_range[1]}")
            report.append(f"持续时间: {duration}")
        report.append("")
        
        # 级别分布
        report.append("=== 日志级别分布 ===")
        for level, count in sorted(self.result.level_distribution.items()):
            percentage = (count / self.result.total_count * 100) if self.result.total_count > 0 else 0
            report.append(f"{level}: {count} ({percentage:.1f}%)")
        report.append("")
        
        # 日志器分布
        report.append("=== Top 10 日志器 ===")
        sorted_loggers = sorted(
            self.result.logger_distribution.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        for logger, count in sorted_loggers:
            percentage = (count / self.result.total_count * 100) if self.result.total_count > 0 else 0
            report.append(f"{logger}: {count} ({percentage:.1f}%)")
        report.append("")
        
        # 错误模式
        if self.result.error_patterns:
            report.append("=== 错误模式分析 ===")
            for pattern_info in self.result.error_patterns[:10]:
                report.append(f"模式 '{pattern_info['pattern']}': {pattern_info['count']} 次")
                if pattern_info['examples']:
                    report.append("  示例:")
                    for example in pattern_info['examples'][:3]:
                        report.append(f"    {example['timestamp']} - {example['message']}")
            report.append("")
            
        # 性能统计
        if self.result.performance_stats:
            report.append("=== 性能统计 ===")
            for stat, value in self.result.performance_stats.items():
                report.append(f"{stat}: {value:.3f}")
            report.append("")
            
        # 自定义分析
        if self.result.custom_analysis:
            report.append("=== 自定义分析 ===")
            for key, value in self.result.custom_analysis.items():
                report.append(f"{key}:")
                if isinstance(value, dict):
                    for sub_key, sub_value in list(value.items())[:5]:  # 只显示前5个
                        report.append(f"  {sub_key}: {sub_value}")
                else:
                    report.append(f"  {value}")
                    
        return "\n".join(report)


# 便捷函数
def create_query_engine(log_dirs: List[str], index_path: str) -> LogQueryEngine:
    """创建查询引擎"""
    return LogQueryEngine(log_dirs, index_path)


def analyze_logs(records: List[LogRecord]) -> LogAnalysisResult:
    """分析日志记录"""
    analyzer = LogAnalyzer()
    return analyzer.analyze(records)


def create_visualizer(analysis_result: LogAnalysisResult) -> LogVisualizer:
    """创建可视化工具"""
    return LogVisualizer(analysis_result)


def search_logs(query_engine: LogQueryEngine, query: LogQuery) -> List[LogRecord]:
    """搜索日志"""
    return query_engine.query(query)