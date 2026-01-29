"""
Agent 执行循环
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional
from datetime import datetime
from uuid import uuid4

from api.schemas.message import (
    Message, 
    MessageType, 
    MessageRole, 
    ToolCall,
    StreamChunk
)
from core.agent.state import AgentStateManager, AgentState, ToolCallInfo
from core.memory.short_term import ShortTermMemory
from core.llm.client import LLMClient
from core.llm.manager import ModelManager
from tools.registry import ToolRegistry


logger = logging.getLogger(__name__)


class AgentLoop:
    """
    Agent 执行循环
    核心的思考-行动循环逻辑
    """
    
    def __init__(
        self,
        session_id: str,
        memory: ShortTermMemory,
        llm_client: LLMClient,
        model_manager: ModelManager,
        tool_registry: ToolRegistry,
        workspace: Optional[str] = None,
        system_prompt: Optional[str] = None
    ):
        self.session_id = session_id
        self.memory = memory
        self.llm_client = llm_client
        self.model_manager = model_manager
        self.tool_registry = tool_registry
        self.workspace = workspace
        self.system_prompt = system_prompt
        
        self.state_manager = AgentStateManager()
        self._pending_approvals: dict[str, asyncio.Event] = {}
    
    async def process(
        self,
        user_message: str,
        model: Optional[str] = None,
        stream: bool = True
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        处理用户消息
        
        Args:
            user_message: 用户消息
            model: 指定模型
            stream: 是否流式输出
        
        Yields:
            StreamChunk: 输出块
        """
        # 添加用户消息
        user_msg = Message(
            id=str(uuid4()),
            content=user_message,
            role=MessageRole.USER,
            type=MessageType.USER,
            timestamp=datetime.now()
        )
        await self.memory.add_message(user_msg)
        
        # 开始思考
        model = model or self.model_manager.get_current_model()
        await self.state_manager.start_thinking(model)
        
        try:
            # 执行主循环
            async for chunk in self._thinking_loop(model, stream):
                yield chunk
            
            await self.state_manager.idle()
        
        except asyncio.CancelledError:
            await self.state_manager.interrupt()
            yield StreamChunk(
                chunk="\n\n[中断] Agent 执行被中断",
                done=True,
                session_id=self.session_id
            )
        
        except Exception as e:
            await self.state_manager.error(str(e))
            yield StreamChunk(
                chunk=f"\n\n[错误] {str(e)}",
                done=True,
                session_id=self.session_id
            )
    
    async def _thinking_loop(
        self,
        model: str,
        stream: bool
    ) -> AsyncGenerator[StreamChunk, None]:
        """思考循环"""
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # 检查中断
            if self.state_manager.is_interrupted():
                return
            
            # 构建消息
            messages = await self._build_messages()
            
            # 获取可用工具
            tools = self.tool_registry.get_tool_schemas()
            
            # 调用 LLM
            response = await self.llm_client.complete(
                messages=messages,
                model=model,
                stream=stream,
                tools=tools if tools else None
            )
            
            # 处理响应
            if response.content:
                # 输出响应
                await self.state_manager.streaming()
                
                if stream:
                    async for chunk in self._stream_content(response.content):
                        yield chunk
                else:
                    yield StreamChunk(
                        chunk=response.content,
                        done=True,
                        session_id=self.session_id
                    )
                
                # 保存助手消息
                assistant_msg = Message(
                    id=str(uuid4()),
                    content=response.content,
                    role=MessageRole.ASSISTANT,
                    type=MessageType.ASSISTANT,
                    model=model,
                    tokens=response.total_tokens,
                    cost=response.cost,
                    timestamp=datetime.now()
                )
                await self.memory.add_message(assistant_msg)
                
                # 完成
                return
            
            # 处理工具调用
            if response.content is None and tools:
                # 检查是否有工具调用
                # 注意: 实际响应中会有 tool_calls 字段
                tool_calls = await self._extract_tool_calls(response)
                
                if tool_calls:
                    await self.state_manager.start_tool_execution()
                    
                    for tool_call in tool_calls:
                        result = await self._execute_tool(tool_call)
                        
                        yield StreamChunk(
                            chunk=f"\n[工具调用] {tool_call.name}\n结果: {result}\n",
                            done=False,
                            session_id=self.session_id
                        )
        
        # 达到最大迭代次数
        yield StreamChunk(
            chunk="\n[警告] 达到最大迭代次数，停止执行",
            done=True,
            session_id=self.session_id
        )
    
    async def _build_messages(self) -> list[dict]:
        """构建消息列表"""
        messages = []
        
        # 系统提示词
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        else:
            messages.append({
                "role": "system", 
                "content": self._get_default_system_prompt()
            })
        
        # 上下文消息
        context_messages = await self.memory.get_messages(include_system=False)
        
        for msg in context_messages:
            message_dict = {
                "role": msg.role.value,
                "content": msg.content
            }
            
            # 添加工具调用信息
            if msg.tool_calls:
                message_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments
                        }
                    }
                    for tc in msg.tool_calls
                ]
            
            messages.append(message_dict)
        
        return messages
    
    def _get_default_system_prompt(self) -> str:
        """获取默认系统提示词"""
        return """You are AgentBus, an AI programming assistant. You can help users with:
- Writing and editing code
- Analyzing codebases
- Running shell commands
- Debugging issues
- Explaining complex concepts

You think step by step and use tools when needed. Always be helpful and concise.
"""
    
    async def _stream_content(self, content: str) -> AsyncGenerator[StreamChunk, None]:
        """流式输出内容"""
        # 简单按字符流式输出
        for char in content:
            if self.state_manager.is_interrupted():
                break
            yield StreamChunk(
                chunk=char,
                done=False,
                session_id=self.session_id
            )
        
        yield StreamChunk(
            chunk="",
            done=True,
            session_id=self.session_id
        )
    
    async def _extract_tool_calls(self, response) -> list[ToolCall]:
        """从响应中提取工具调用"""
        tool_calls = []
        
        # 检查响应是否有工具调用
        if hasattr(response, 'tool_calls') and response.tool_calls:
            for tc in response.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=tc.function.arguments
                ))
        
        return tool_calls
    
    async def _execute_tool(self, tool_call: ToolCall) -> str:
        """执行工具调用"""
        tool_name = tool_call.name
        arguments = tool_call.arguments
        
        # 检查工具是否存在
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return f"Error: Unknown tool '{tool_name}'"
        
        # 执行工具
        try:
            result = await tool.execute(**arguments)
            return result
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"
    
    async def interrupt(self):
        """中断执行"""
        await self.state_manager.interrupt()
    
    async def approve_tool(self, call_id: str, approved: bool):
        """批准工具调用"""
        if call_id in self._pending_approvals:
            if approved:
                self._pending_approvals[call_id].set()
            else:
                # 设置事件但标记为拒绝
                self._pending_approvals[call_id].set()
