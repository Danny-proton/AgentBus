"""
多模型协调器
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime
from uuid import uuid4

from api.schemas.message import (
    Message, 
    MessageType, 
    MessageRole,
    ToolCall,
    ToolResult,
    StreamChunk
)
from core.agent.loop import AgentLoop
from core.memory.short_term import ShortTermMemory
from core.llm.client import LLMClient
from core.llm.manager import ModelManager
from tools.registry import ToolRegistry
from runtime.abstract import Environment


logger = logging.getLogger(__name__)


class SubAgent:
    """子代理"""
    
    def __init__(
        self,
        name: str,
        model: str,
        task: str,
        loop: AgentLoop
    ):
        self.name = name
        self.model = model
        self.task = task
        self.loop = loop
        self.results: List[Message] = []
        self.status = "pending"


class ModelOrchestrator:
    """
    多模型协调器
    协调多个模型的协同工作
    """
    
    def __init__(
        self,
        memory: ShortTermMemory,
        llm_client: LLMClient,
        model_manager: ModelManager,
        tool_registry: ToolRegistry,
        environment: Environment
    ):
        self.memory = memory
        self.llm_client = llm_client
        self.model_manager = model_manager
        self.tool_registry = tool_registry
        self.environment = environment
        
        self._sub_agents: Dict[str, SubAgent] = {}
    
    async def execute_with_model(
        self,
        message: str,
        model_name: Optional[str] = None,
        sub_agents: Optional[List[Dict[str, Any]]] = None,
        stream: bool = True
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        使用指定模型执行任务
        
        Args:
            message: 用户消息
            model_name: 模型名称
            sub_agents: 子代理配置列表
            stream: 是否流式输出
        """
        model = model_name or self.model_manager.get_current_model()
        
        # 创建 AgentLoop
        loop = AgentLoop(
            session_id=str(uuid4()),
            memory=self.memory,
            llm_client=self.llm_client,
            model_manager=self.model_manager,
            tool_registry=self.tool_registry,
            workspace=str(self.environment.workspace) if self.environment else None
        )
        
        # 执行子代理任务
        if sub_agents:
            async for chunk in self._execute_sub_agents(
                loop=loop,
                message=message,
                sub_agents=sub_agents,
                stream=stream
            ):
                yield chunk
        else:
            async for chunk in loop.process(message, model, stream):
                yield chunk
    
    async def _execute_sub_agents(
        self,
        loop: AgentLoop,
        message: str,
        sub_agents: List[Dict[str, Any]],
        stream: bool
    ) -> AsyncGenerator[StreamChunk, None]:
        """执行子代理任务"""
        # 并行执行子代理
        tasks = []
        
        for i, agent_config in enumerate(sub_agents):
            agent_name = agent_config.get("name", f"agent_{i}")
            agent_model = agent_config.get("model")
            agent_task = agent_config.get("task", message)
            
            sub_loop = AgentLoop(
                session_id=f"{loop.session_id}_{agent_name}",
                memory=self.memory,
                llm_client=self.llm_client,
                model_manager=self.model_manager,
                tool_registry=self.tool_registry,
                workspace=str(self.environment.workspace) if self.environment else None
            )
            
            task = asyncio.create_task(
                self._run_sub_agent(
                    sub_loop,
                    agent_name,
                    agent_model or self.model_manager.get_model_for_task("task"),
                    agent_task
                )
            )
            tasks.append((agent_name, task))
        
        # 收集结果
        results = []
        for agent_name, task in tasks:
            try:
                result = await asyncio.wait_for(task, timeout=300)
                results.append((agent_name, result))
                
                yield StreamChunk(
                    chunk=f"\n[{agent_name}] 完成: {result[:100]}...",
                    done=False,
                    session_id=loop.session_id
                )
            except asyncio.TimeoutError:
                yield StreamChunk(
                    chunk=f"\n[{agent_name}] 超时",
                    done=False,
                    session_id=loop.session_id
                )
            except Exception as e:
                yield StreamChunk(
                    chunk=f"\n[{agent_name}] 错误: {str(e)}",
                    done=False,
                    session_id=loop.session_id
                )
        
        # 生成综合结果
        combined_result = self._combine_results(message, results)
        
        async for chunk in loop.process(combined_result, stream=stream):
            yield chunk
    
    async def _run_sub_agent(
        self,
        loop: AgentLoop,
        name: str,
        model: str,
        task: str
    ) -> str:
        """运行子代理"""
        sub_agent = SubAgent(
            name=name,
            model=model,
            task=task,
            loop=loop
        )
        
        self._sub_agents[name] = sub_agent
        sub_agent.status = "running"
        
        try:
            # 收集响应
            responses = []
            async for chunk in loop.process(task, model, stream=False):
                if chunk.done:
                    responses.append(chunk.chunk)
            
            result = " ".join(responses)
            sub_agent.results.append(Message(
                id=str(uuid4()),
                content=result,
                role=MessageRole.ASSISTANT,
                type=MessageType.ASSISTANT,
                timestamp=datetime.now()
            ))
            sub_agent.status = "completed"
            
            return result
        
        except Exception as e:
            sub_agent.status = "failed"
            raise
    
    def _combine_results(
        self,
        original_task: str,
        results: List[tuple[str, str]]
    ) -> str:
        """组合子代理结果"""
        combined = f"Original task: {original_task}\n\n"
        combined += "Sub-agent results:\n"
        
        for name, result in results:
            combined += f"- {name}: {result[:500]}\n"
        
        combined += "\nPlease synthesize these results into a comprehensive answer."
        
        return combined
    
    async def ask_expert(
        self,
        question: str,
        expert_model: str,
        context: Optional[str] = None,
        stream: bool = True
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        咨询专家模型
        临时调用特定专家模型解决疑难问题
        """
        # 构建消息
        messages = [{"role": "user", "content": question}]
        
        if context:
            messages.insert(0, {
                "role": "system",
                "content": f"Context: {context}"
            })
        
        # 调用专家模型
        async for chunk in self.llm_client.stream_complete(
            messages=messages,
            model=expert_model,
            stream=stream
        ):
            yield chunk
    
    def get_active_sub_agents(self) -> List[Dict[str, Any]]:
        """获取活跃的子代理"""
        return [
            {
                "name": name,
                "model": agent.model,
                "status": agent.status,
                "task": agent.task
            }
            for name, agent in self._sub_agents.items()
            if agent.status in ["pending", "running"]
        ]
    
    async def cleanup(self):
        """清理资源"""
        for agent in self._sub_agents.values():
            if agent.status == "running":
                await agent.loop.interrupt()
        
        self._sub_agents.clear()
