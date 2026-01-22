"""
日志服务
记录所有 Agent 执行过程中的操作细节
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum
from uuid import uuid4


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """日志类别"""
    AGENT = "AGENT"
    TOOL = "TOOL"
    LLM = "LLM"
    SUBAGENT = "SUBAGENT"
    SESSION = "SESSION"
    SYSTEM = "SYSTEM"
    USER = "USER"
    ERROR = "ERROR"


@dataclass
class LogEntry:
    """日志条目"""
    id: str
    timestamp: str
    level: str
    category: str
    agent_id: Optional[str]
    session_id: Optional[str]
    action: str
    details: Dict[str, Any]
    result: Optional[str]
    duration_ms: Optional[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class ActionLog:
    """操作日志"""
    action_id: str
    agent_name: str
    action_type: str
    description: str
    input_params: Dict[str, Any]
    output_result: Optional[str]
    success: bool
    error_message: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def to_log_entry(self) -> LogEntry:
        return LogEntry(
            id=self.action_id,
            timestamp=self.start_time.isoformat(),
            level="ERROR" if not self.success else "INFO",
            category=self.action_type.upper(),
            agent_id=self.agent_name,
            session_id=None,
            action=self.description,
            details=self.input_params,
            result=self.output_result,
            duration_ms=self.duration_ms,
            metadata=self.metadata
        )


class LogService:
    """
    日志服务
    负责记录、存储和管理所有日志
    """
    
    def __init__(self, workspace_path: str, enabled: bool = True):
        self.workspace_path = Path(workspace_path)
        self.enabled = enabled
        
        # 日志目录
        self.logs_dir = self.workspace_path / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前日志文件
        self.current_log_file = self.logs_dir / f"agentbus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # 日志缓冲区
        self._buffer: List[LogEntry] = []
        self._buffer_lock = asyncio.Lock()
        
        # 批量写入配置
        self._batch_size = 100
        self._flush_interval = 5.0  # 秒
        
        # 异步刷新任务
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        
        # 设置 Python logging
        self._setup_python_logging()
    
    def _setup_python_logging(self):
        """配置 Python logging"""
        self.logger = logging.getLogger("agentbus")
        self.logger.setLevel(logging.DEBUG)
        
        # 文件处理器
        file_handler = logging.FileHandler(
            self.workspace_path / "logs" / "python.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式化
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    async def start(self):
        """启动日志服务"""
        if not self.enabled:
            return
        
        self._running = True
        
        # 创建日志文件头
        await self._write_header()
        
        # 启动刷新任务
        self._flush_task = asyncio.create_task(self._auto_flush())
        
        self.logger.info("LogService started")
    
    async def stop(self):
        """停止日志服务"""
        self._running = False
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # 刷新所有缓冲区
        await self.flush()
        
        # 写入尾部
        await self._write_footer()
        
        self.logger.info("LogService stopped")
    
    async def _write_header(self):
        """写入日志文件头"""
        header = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "workspace": str(self.workspace_path),
            "format": "jsonl"
        }
        
        with open(self.current_log_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(header, ensure_ascii=False) + '\n')
    
    async def _write_footer(self):
        """写入日志文件尾"""
        with open(self.current_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "closed_at": datetime.now().isoformat(),
                "total_entries": len(self._buffer)
            }, ensure_ascii=False) + '\n')
    
    async def _auto_flush(self):
        """自动刷新缓冲区"""
        while self._running:
            await asyncio.sleep(self._flush_interval)
            await self.flush()
    
    async def flush(self):
        """刷新缓冲区到文件"""
        async with self._buffer_lock:
            if not self._buffer:
                return
            
            entries = self._buffer[:self._batch_size]
            self._buffer = self._buffer[self._batch_size:]
        
        # 写入文件
        with open(self.current_log_file, 'a', encoding='utf-8') as f:
            for entry in entries:
                f.write(entry.to_json() + '\n')
    
    async def log(
        self,
        action: str,
        category: LogCategory,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
        duration_ms: Optional[float] = None,
        level: LogLevel = LogLevel.INFO,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """记录日志"""
        if not self.enabled:
            return
        
        entry = LogEntry(
            id=str(uuid4()),
            timestamp=datetime.now().isoformat(),
            level=level.value,
            category=category.value,
            agent_id=agent_id,
            session_id=session_id,
            action=action,
            details=details or {},
            result=result,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        
        async with self._buffer_lock:
            self._buffer.append(entry)
        
        # Python logging 同步
        self.logger.log(
            getattr(logging, level.value),
            f"[{category.value}] {action}: {details or ''}"
        )
    
    async def log_tool_call(
        self,
        tool_name: str,
        agent_id: str,
        arguments: Dict[str, Any],
        result: str,
        success: bool,
        duration_ms: float,
        error: Optional[str] = None
    ):
        """记录工具调用"""
        await self.log(
            action=f"Tool call: {tool_name}",
            category=LogCategory.TOOL,
            agent_id=agent_id,
            details={
                "tool_name": tool_name,
                "arguments": arguments,
                "success": success,
                "error": error
            },
            result=result,
            duration_ms=duration_ms,
            level=LogLevel.ERROR if not success else LogLevel.INFO
        )
    
    async def log_llm_call(
        self,
        model: str,
        agent_id: str,
        prompt_length: int,
        response_length: int,
        duration_ms: float,
        tokens_used: Optional[int] = None,
        cost: Optional[float] = None
    ):
        """记录 LLM 调用"""
        await self.log(
            action=f"LLM call: {model}",
            category=LogCategory.LLM,
            agent_id=agent_id,
            details={
                "model": model,
                "prompt_length": prompt_length,
                "response_length": response_length,
                "tokens_used": tokens_used,
                "cost": cost
            },
            duration_ms=duration_ms,
            level=LogLevel.DEBUG
        )
    
    async def log_subagent(
        self,
        subagent_name: str,
        parent_agent: str,
        task: str,
        status: str,
        duration_ms: Optional[float] = None
    ):
        """记录子代理执行"""
        await self.log(
            action=f"SubAgent: {subagent_name}",
            category=LogCategory.SUBAGENT,
            agent_id=parent_agent,
            details={
                "subagent_name": subagent_name,
                "task": task,
                "status": status
            },
            duration_ms=duration_ms,
            level=LogLevel.WARNING if status == "failed" else LogLevel.INFO
        )
    
    async def log_session(
        self,
        session_id: str,
        event: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录会话事件"""
        await self.log(
            action=f"Session event: {event}",
            category=LogCategory.SESSION,
            session_id=session_id,
            details=details or {}
        )
    
    async def log_agent_action(
        self,
        agent_id: str,
        action_type: str,
        description: str,
        input_data: Dict[str, Any],
        output_data: Optional[str],
        success: bool,
        duration_ms: float,
        error: Optional[str] = None
    ):
        """记录 Agent 操作"""
        action_log = ActionLog(
            action_id=str(uuid4()),
            agent_name=agent_id,
            action_type=action_type,
            description=description,
            input_params=input_data,
            output_result=output_data,
            success=success,
            error_message=error,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration_ms=duration_ms
        )
        
        await self.log(
            action=description,
            category=LogCategory.AGENT,
            agent_id=agent_id,
            details=input_data,
            result=output_data,
            duration_ms=duration_ms,
            level=LogLevel.ERROR if not success else LogLevel.INFO,
            metadata={"action_type": action_type}
        )
    
    def get_log_file_path(self) -> str:
        """获取当前日志文件路径"""
        return str(self.current_log_file)
    
    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self.enabled
    
    async def get_recent_logs(
        self,
        limit: int = 100,
        category: Optional[LogCategory] = None,
        agent_id: Optional[str] = None
    ) -> List[LogEntry]:
        """获取最近的日志"""
        async with self._buffer_lock:
            entries = self._buffer.copy()
        
        # 过滤
        if category:
            entries = [e for e in entries if e.category == category.value]
        
        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        
        return entries[-limit:]
    
    async def export_logs(
        self,
        output_path: str,
        format: str = "jsonl",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ):
        """导出日志"""
        entries = await self.get_recent_logs(limit=10000)
        
        if format == "jsonl":
            with open(output_path, 'w', encoding='utf-8') as f:
                for entry in entries:
                    f.write(entry.to_json() + '\n')
        elif format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump([e.to_dict() for e in entries], f, ensure_ascii=False, indent=2)
        
        return len(entries)


# 全局日志服务实例
_log_service: Optional[LogService] = None


def get_log_service() -> LogService:
    """获取全局日志服务实例"""
    global _log_service
    if _log_service is None:
        raise RuntimeError("LogService not initialized. Call init_log_service first.")
    return _log_service


def init_log_service(
    workspace_path: str,
    enabled: bool = True
) -> LogService:
    """初始化全局日志服务"""
    global _log_service
    _log_service = LogService(workspace_path, enabled)
    return _log_service


async def start_log_service():
    """启动日志服务"""
    if _log_service:
        await _log_service.start()


async def stop_log_service():
    """停止日志服务"""
    if _log_service:
        await _log_service.stop()
