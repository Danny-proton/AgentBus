"""
Agent 状态管理
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

from api.schemas.message import Message, MessageType, MessageRole


logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Agent 状态"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING_TOOLS = "executing_tools"
    WAITING_APPROVAL = "waiting_approval"
    STREAMING = "streaming"
    ERROR = "error"
    INTERRUPTED = "interrupted"


@dataclass
class ToolCallInfo:
    """工具调用信息"""
    id: str
    name: str
    arguments: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    approved: Optional[bool] = None
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class AgentStatus:
    """Agent 状态信息"""
    state: AgentState = AgentState.IDLE
    current_model: str = "default"
    tool_calls: List[ToolCallInfo] = field(default_factory=list)
    last_error: Optional[str] = None
    interrupted: bool = False
    started_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "current_model": self.current_model,
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "approved": tc.approved,
                    "result": tc.result[:100] if tc.result else None
                }
                for tc in self.tool_calls
            ],
            "last_error": self.last_error,
            "interrupted": self.interrupted,
            "started_at": self.started_at.isoformat() if self.started_at else None
        }


class AgentStateManager:
    """
    Agent 状态管理器
    管理 Agent 的运行状态和状态转换
    """
    
    def __init__(self):
        self._state = AgentState.IDLE
        self._status = AgentStatus()
        self._lock = asyncio.Lock()
        self._interrupt_event = asyncio.Event()
    
    @property
    def state(self) -> AgentState:
        """获取当前状态"""
        return self._state
    
    @property
    def status(self) -> AgentStatus:
        """获取状态信息"""
        return self._status
    
    async def set_state(self, new_state: AgentState):
        """设置状态"""
        async with self._lock:
            old_state = self._state
            self._state = new_state
            self._status.state = new_state
            
            logger.debug(f"State transition: {old_state.value} -> {new_state.value}")
    
    async def start_thinking(self, model: str):
        """开始思考"""
        await self.set_state(AgentState.THINKING)
        self._status.current_model = model
        self._status.started_at = datetime.now()
        self._status.interrupted = False
        self._interrupt_event.clear()
    
    async def start_tool_execution(self):
        """开始工具执行"""
        await self.set_state(AgentState.EXECUTING_TOOLS)
    
    async def wait_for_approval(self, tool_call: ToolCallInfo):
        """等待批准"""
        await self.set_state(AgentState.WAITING_APPROVAL)
        self._status.tool_calls.append(tool_call)
    
    async def streaming(self):
        """流式输出"""
        await self.set_state(AgentState.STREAMING)
    
    async def idle(self):
        """回到空闲状态"""
        await self.set_state(AgentState.IDLE)
        self._status.tool_calls.clear()
        self._status.started_at = None
    
    async def error(self, error_message: str):
        """错误状态"""
        await self.set_state(AgentState.ERROR)
        self._status.last_error = error_message
        logger.error(f"Agent error: {error_message}")
    
    async def interrupt(self):
        """中断执行"""
        self._status.interrupted = True
        self._interrupt_event.set()
        await self.set_state(AgentState.INTERRUPTED)
        logger.info("Agent execution interrupted")
    
    def add_tool_call(self, call: ToolCallInfo):
        """添加工具调用"""
        self._status.tool_calls.append(call)
    
    def update_tool_result(self, call_id: str, result: str, error: Optional[str] = None):
        """更新工具调用结果"""
        for tc in self._status.tool_calls:
            if tc.id == call_id:
                tc.result = result
                tc.error = error
                break
    
    def is_interrupted(self) -> bool:
        """检查是否被中断"""
        return self._interrupt_event.is_set()
    
    async def wait_for_interrupt(self, timeout: Optional[float] = None) -> bool:
        """等待中断信号"""
        try:
            await asyncio.wait_for(
                self._interrupt_event.wait(),
                timeout=timeout
            )
            return True
        except asyncio.TimeoutError:
            return False
    
    def reset(self):
        """重置状态"""
        self._state = AgentState.IDLE
        self._status = AgentStatus()
        self._interrupt_event.clear()
