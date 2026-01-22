"""
会话管理服务
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4
from pathlib import Path

from api.schemas.message import (
    Message,
    MessageType,
    MessageRole,
    SessionStatus
)
from core.agent.loop import AgentLoop
from core.agent.orchestrator import ModelOrchestrator
from core.memory.short_term import ShortTermMemory
from core.llm.client import LLMClient
from core.llm.manager import ModelManager
from core.context.manager import ContextManager
from core.context.compressor import ContextCompressor
from tools.registry import ToolRegistry
from tools.file_tools import register_file_tools
from tools.terminal import register_terminal_tools
from tools.search import register_search_tools
from runtime.abstract import Environment, EnvironmentFactory
from services.cost_tracker import CostTracker


logger = logging.getLogger(__name__)


class Session:
    """
    单个会话
    管理对话历史、Agent 状态和工具
    """
    
    def __init__(
        self,
        session_id: str,
        workspace: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        memory: Optional[ShortTermMemory] = None,
        cost_tracker: Optional[CostTracker] = None
    ):
        self.id = session_id
        self.workspace = workspace
        self.current_model = model or "default"
        self.system_prompt = system_prompt
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.status = SessionStatus.ACTIVE
        
        # 初始化组件
        self.memory = memory or ShortTermMemory()
        self.cost_tracker = cost_tracker
        self.messages: List[Message] = []
        
        # Agent 组件（延迟初始化）
        self._agent_loop: Optional[AgentLoop] = None
        self._orchestrator: Optional[ModelOrchestrator] = None
        self._environment: Optional[Environment] = None
        self._tool_registry: Optional[ToolRegistry] = None
        
        # 锁
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """初始化会话组件"""
        async with self._lock:
            # 初始化环境
            self._environment = EnvironmentFactory.get_environment()
            await self._environment.initialize()
            
            # 初始化工具注册中心
            self._tool_registry = ToolRegistry()
            
            # 注册工具
            from config.settings import get_settings
            settings = get_settings()
            
            register_file_tools(self._tool_registry, self._environment)
            register_terminal_tools(
                self._tool_registry,
                self._environment,
                safe_mode=settings.security.safe_mode
            )
            register_search_tools(self._tool_registry, self._environment)
            
            # 初始化 Agent 组件
            llm_client = LLMClient()
            model_manager = ModelManager()
            await model_manager.initialize()
            
            self._agent_loop = AgentLoop(
                session_id=self.id,
                memory=self.memory,
                llm_client=llm_client,
                model_manager=model_manager,
                tool_registry=self._tool_registry,
                workspace=self.workspace,
                system_prompt=self.system_prompt
            )
            
            self._orchestrator = ModelOrchestrator(
                memory=self.memory,
                llm_client=llm_client,
                model_manager=model_manager,
                tool_registry=self._tool_registry,
                environment=self._environment
            )
            
            logger.info(f"Session initialized: {self.id}")
    
    async def process_message(
        self,
        content: str,
        model: Optional[str] = None,
        stream: bool = True
    ):
        """
        处理用户消息
        
        Args:
            content: 消息内容
            model: 指定模型
            stream: 是否流式输出
        
        Yields:
            StreamChunk: 输出块
        """
        # 确保已初始化
        if not self._agent_loop:
            await self.initialize()
        
        # 更新状态
        self.status = SessionStatus.THINKING
        self.updated_at = datetime.now()
        
        try:
            # 处理消息
            async for chunk in self._agent_loop.process(
                user_message=content,
                model=model or self.current_model,
                stream=stream
            ):
                yield chunk
            
            self.status = SessionStatus.IDLE
        
        except asyncio.CancelledError:
            self.status = SessionStatus.IDLE
            raise
    
    async def switch_model(self, model_name: str):
        """切换模型"""
        self.current_model = model_name
        self.updated_at = datetime.now()
        logger.info(f"Session {self.id} switched to model: {model_name}")
    
    async def interrupt(self):
        """中断当前操作"""
        if self._agent_loop:
            await self._agent_loop.interrupt()
        self.status = SessionStatus.IDLE
    
    async def approve_tool(self, call_id: str, approved: bool):
        """批准工具调用"""
        if self._agent_loop:
            await self._agent_loop.approve_tool(call_id, approved)
    
    async def get_cost_summary(self) -> Dict[str, Any]:
        """获取成本汇总"""
        if self.cost_tracker:
            return await self.cost_tracker.get_cost_summary(self.id)
        return {"total_cost": 0.0, "by_model": {}}
    
    async def shutdown(self):
        """关闭会话"""
        if self._environment:
            await self._environment.close()
        
        logger.info(f"Session shutdown: {self.id}")


class SessionManager:
    """
    会话管理器
    管理所有活跃会话
    """
    
    def __init__(
        self,
        memory: Optional[ShortTermMemory] = None,
        cost_tracker: Optional[CostTracker] = None
    ):
        self._sessions: Dict[str, Session] = {}
        self._lock = asyncio.Lock()
        self.memory = memory or ShortTermMemory()
        self.cost_tracker = cost_tracker or CostTracker()
    
    async def create_session(
        self,
        workspace: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Session:
        """
        创建新会话
        
        Args:
            workspace: 工作目录
            model: 默认模型
            system_prompt: 系统提示词
        
        Returns:
            Session: 新会话
        """
        async with self._lock:
            session_id = str(uuid4())
            
            session = Session(
                session_id=session_id,
                workspace=workspace,
                model=model,
                system_prompt=system_prompt,
                memory=self.memory,
                cost_tracker=self.cost_tracker
            )
            
            self._sessions[session_id] = session
            
            logger.info(f"Session created: {session_id}")
            
            return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self._sessions.get(session_id)
    
    async def list_sessions(self) -> List[Session]:
        """列出会话"""
        return list(self._sessions.values())
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        async with self._lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                await session.shutdown()
                del self._sessions[session_id]
                logger.info(f"Session deleted: {session_id}")
                return True
            return False
    
    async def clear_session(self, session_id: str) -> Optional[Session]:
        """清除会话消息"""
        session = await self.get_session(session_id)
        
        if session:
            await session.memory.clear()
            session.updated_at = datetime.now()
        
        return session
    
    async def compact_session(
        self,
        session_id: str,
        threshold: float = 0.85
    ) -> bool:
        """压缩会话上下文"""
        session = await self.get_session(session_id)
        
        if not session:
            return False
        
        compressor = ContextCompressor(session.memory)
        await compressor.compress(threshold)
        
        session.updated_at = datetime.now()
        return True
    
    async def shutdown(self):
        """关闭所有会话"""
        for session in self._sessions.values():
            await session.shutdown()
        
        self._sessions.clear()
        logger.info("SessionManager shutdown")


# 依赖注入
_session_manager: Optional[SessionManager] = None


async def get_session_manager() -> SessionManager:
    """获取会话管理器（FastAPI 依赖注入）"""
    global _session_manager
    
    if _session_manager is None:
        from core.memory.short_term import ShortTermMemory
        from services.cost_tracker import CostTracker
        
        memory = ShortTermMemory()
        cost_tracker = CostTracker()
        _session_manager = SessionManager(
            memory=memory,
            cost_tracker=cost_tracker
        )
    
    return _session_manager
