"""
LLM 客户端封装
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional, Dict, Any
from dataclasses import dataclass

from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.chat.chat_completion import Choice

from config.settings import get_settings, get_model_config
from core.memory.short_term import ShortTermMemory


logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float


@dataclass  
class TokenUsage:
    """Token 使用统计"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMClient:
    """
    LLM 客户端
    封装 OpenAI API 调用
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._sync_client: Optional[OpenAI] = None
        self._async_client: Optional[AsyncOpenAI] = None
    
    def _get_client(self, model_name: str) -> AsyncOpenAI:
        """获取异步客户端"""
        if self._async_client:
            return self._async_client
        
        model_config = get_model_config(model_name)
        
        client_kwargs = {
            "api_key": model_config.api_key or self.settings.llm.api_key,
            "timeout": self.settings.llm.timeout,
            "max_retries": self.settings.llm.max_retries
        }
        
        if model_config.base_url:
            client_kwargs["base_url"] = model_config.base_url
        
        self._async_client = AsyncOpenAI(**client_kwargs)
        
        return self._async_client
    
    async def complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        stream: bool = True,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7
    ) -> LLMResponse:
        """
        发送完成请求
        
        Args:
            messages: 消息列表
            model: 模型名称
            stream: 是否流式响应
            tools: 可用工具定义
            tool_choice: 工具选择策略
            max_tokens: 最大输出 token
            temperature: 温度参数
        
        Returns:
            LLMResponse: 响应结果
        """
        model = model or self.settings.llm.default_model
        model_config = get_model_config(model)
        
        if not model_config:
            raise ValueError(f"Model not found: {model}")
        
        client = self._get_client(model)
        
        request_kwargs = {
            "model": model_config.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        if max_tokens:
            request_kwargs["max_tokens"] = min(
                max_tokens, 
                model_config.max_output_tokens
            )
        
        if tools:
            request_kwargs["tools"] = tools
            request_kwargs["tool_choice"] = tool_choice or "auto"
        
        try:
            if stream:
                response = await client.chat.completions.create(
                    **request_kwargs
                )
                
                # 收集流式响应
                content = ""
                async for chunk in self._stream_response(response):
                    content += chunk
                
                # 计算 token 使用
                # 注意: 流式响应需要特殊处理 token 计数
                usage = await self._get_usage_from_response(response, content)
            
            else:
                response: ChatCompletion = await client.chat.completions.create(
                    **request_kwargs
                )
                
                content = response.choices[0].message.content or ""
                usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
                )
            
            # 计算成本
            cost = self._calculate_cost(model, usage)
            
            return LLMResponse(
                content=content,
                model=model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                cost=cost
            )
        
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            raise
    
    async def stream_complete(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式完成请求
        
        Yields:
            str: 内容块
        """
        response = await self.complete(
            messages=messages,
            model=model,
            stream=True,
            tools=tools,
            tool_choice=tool_choice
        )
        
        # 返回内容（流式已在 complete 中处理）
        yield response.content
    
    async def _stream_response(
        self, 
        response
    ) -> AsyncGenerator[str, None]:
        """处理流式响应"""
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def _get_usage_from_response(
        self, 
        response, 
        content: str
    ) -> TokenUsage:
        """从响应获取 token 使用情况"""
        # 流式响应中 usage 可能为空
        # 估算: 英文约 4 字符/token, 中文约 2 字符/token
        if response.usage:
            return TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )
        
        # 估算
        estimated_tokens = max(1, len(content) // 4)
        
        return TokenUsage(
            prompt_tokens=0,
            completion_tokens=estimated_tokens,
            total_tokens=estimated_tokens
        )
    
    def _calculate_cost(self, model_name: str, usage: TokenUsage) -> float:
        """计算请求成本"""
        model_config = get_model_config(model_name)
        
        if not model_config:
            return 0.0
        
        input_cost = usage.prompt_tokens * model_config.cost_per_input
        output_cost = usage.completion_tokens * model_config.cost_per_output
        
        return input_cost + output_cost
    
    async def count_tokens(self, text: str) -> int:
        """计算文本 token 数量"""
        # 简化版本: 使用字符估算
        # 实际应使用 tiktoken
        return max(1, len(text) // 4)
    
    async def truncate_messages(
        self,
        messages: list[dict[str, str]],
        max_tokens: int,
        system_prompt: Optional[str] = None
    ) -> list[dict[str, str]]:
        """截断消息以适应上下文窗口"""
        total_tokens = 0
        truncated = []
        
        # 从后向前处理（保留最近的消息）
        for message in reversed(messages):
            message_tokens = await self.count_tokens(str(message))
            
            if total_tokens + message_tokens > max_tokens:
                break
            
            truncated.insert(0, message)
            total_tokens += message_tokens
        
        # 如果系统提示词太大，也需要截断
        if system_prompt:
            system_tokens = await self.count_tokens(system_prompt)
            if total_tokens + system_tokens > max_tokens:
                # 截断系统提示词
                remaining = max_tokens - total_tokens
                truncated_system = system_prompt[:remaining * 4]  # 反向估算
                truncated.insert(0, {"role": "system", "content": truncated_system})
        
        return truncated
