"""
OpenAI代理实现
OpenAI Agent Implementation

基于OpenAI API的文本生成代理
"""

from typing import Dict, List, Optional, Any, AsyncIterator, Union
import asyncio
import json
from datetime import datetime

import openai
from openai import AsyncOpenAI

from .base import (
    BaseAgent, AgentRequest, AgentResponse, AgentType, ModelProvider,
    ModelConfig, AgentCapability, AgentStatus
)
from ..core.logger import get_logger
from ..core.config import settings

logger = get_logger(__name__)


class OpenAIAgent(BaseAgent):
    """
    OpenAI代理实现
    
    支持GPT系列模型的文本生成和分析功能
    """
    
    def __init__(self, agent_id: str, name: str, model_config: ModelConfig):
        super().__init__(agent_id, name, model_config)
        
        # 验证配置
        if model_config.provider != ModelProvider.OPENAI:
            raise ValueError(f"Model config provider must be {ModelProvider.OPENAI.value}")
        
        # 初始化OpenAI客户端
        self.client = AsyncOpenAI(
            api_key=model_config.api_key or settings.ai.openai_api_key,
            base_url=model_config.base_url
        )
        
        # 检测能力
        self._detect_openai_capabilities()
    
    def _detect_openai_capabilities(self) -> None:
        """检测OpenAI代理能力"""
        # 基于模型名称检测能力
        model_name = self.model_config.model_name.lower()
        
        # 基础文本生成能力
        if any(keyword in model_name for keyword in ['gpt-3.5', 'gpt-4', 'gpt-4o']):
            self.capabilities.append(AgentCapability(
                type=AgentType.TEXT_GENERATION,
                description="Generate and analyze text using OpenAI models",
                input_types={"text"},
                output_types={"text"},
                supports_streaming=True,
                supports_function_calling=True
            ))
            
            self.capabilities.append(AgentCapability(
                type=AgentType.CODE_GENERATION,
                description="Generate code using OpenAI models",
                input_types={"text", "code"},
                output_types={"code"},
                supports_streaming=True
            ))
            
            self.capabilities.append(AgentCapability(
                type=AgentType.REASONING,
                description="Perform reasoning and analysis",
                input_types={"text"},
                output_types={"text"},
                supports_streaming=True
            ))
            
            self.capabilities.append(AgentCapability(
                type=AgentType.CONVERSATION,
                description="Engage in natural language conversation",
                input_types={"text"},
                output_types={"text"},
                supports_streaming=True
            ))
        
        # 图像理解能力
        if 'gpt-4o' in model_name or 'vision' in model_name:
            self.capabilities.append(AgentCapability(
                type=AgentType.IMAGE_UNDERSTANDING,
                description="Analyze and understand images",
                input_types={"image", "text"},
                output_types={"text"},
                supports_streaming=False
            ))
        
        # 音频处理能力（通过Whisper）
        if 'whisper' in model_name:
            self.capabilities.append(AgentCapability(
                type=AgentType.AUDIO_PROCESSING,
                description="Transcribe and analyze audio",
                input_types={"audio"},
                output_types={"text"},
                supports_streaming=False
            ))
        
        # DALL-E图像生成能力
        if 'dall-e' in model_name:
            self.capabilities.append(AgentCapability(
                type=AgentType.IMAGE_GENERATION,
                description="Generate images from text descriptions",
                input_types={"text"},
                output_types={"image"},
                supports_streaming=False
            ))
        
        logger.info("OpenAI capabilities detected", 
                   agent_id=self.agent_id,
                   capabilities=[cap.type.value for cap in self.capabilities])
    
    async def validate_connection(self) -> bool:
        """验证OpenAI连接"""
        try:
            # 发送一个简单的测试请求
            response = await self.client.chat.completions.create(
                model=self.model_config.model_name,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.error("OpenAI connection validation failed", 
                       agent_id=self.agent_id,
                       error=str(e))
            return False
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
        **kwargs
    ) -> AgentResponse:
        """生成文本"""
        start_time = datetime.now()
        
        try:
            # 构建消息
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            if context:
                for msg in context:
                    messages.append(msg)
            
            messages.append({"role": "user", "content": prompt})
            
            # 构建参数
            params = {
                "model": self.model_config.model_name,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", self.model_config.max_tokens),
                "temperature": kwargs.get("temperature", self.model_config.temperature),
                "top_p": kwargs.get("top_p", self.model_config.top_p),
                "frequency_penalty": kwargs.get("frequency_penalty", self.model_config.frequency_penalty),
                "presence_penalty": kwargs.get("presence_penalty", self.model_config.presence_penalty),
                "stream": stream
            }
            
            # 添加停止序列
            if self.model_config.stop_sequences:
                params["stop"] = self.model_config.stop_sequences
            
            if stream:
                return await self._generate_text_stream(prompt, messages, params, start_time)
            else:
                return await self._generate_text_sync(prompt, messages, params, start_time)
                
        except Exception as e:
            logger.error("OpenAI text generation failed", 
                       agent_id=self.agent_id,
                       error=str(e))
            return AgentResponse.error(
                "", f"Text generation failed: {str(e)}"
            )
    
    async def _generate_text_sync(
        self,
        prompt: str,
        messages: List[Dict[str, str]],
        params: Dict[str, Any],
        start_time: datetime
    ) -> AgentResponse:
        """同步文本生成"""
        try:
            response = await self.client.chat.completions.create(**params)
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            # 计算成本（简化计算）
            cost = self._calculate_cost(tokens_used)
            
            return AgentResponse.success(
                request_id="",
                content=content,
                tokens_used=tokens_used,
                cost=cost,
                response_time=(datetime.now() - start_time).total_seconds(),
                metadata={
                    "model": response.model,
                    "finish_reason": response.choices[0].finish_reason
                }
            )
            
        except Exception as e:
            logger.error("OpenAI sync generation failed", 
                       agent_id=self.agent_id,
                       error=str(e))
            return AgentResponse.error("", f"Sync generation failed: {str(e)}")
    
    async def _generate_text_stream(
        self,
        prompt: str,
        messages: List[Dict[str, str]],
        params: Dict[str, Any],
        start_time: datetime
    ) -> AgentResponse:
        """流式文本生成"""
        try:
            content_parts = []
            tokens_used = 0
            
            async for chunk in await self.client.chat.completions.create(**params):
                if chunk.choices[0].delta.content:
                    content_parts.append(chunk.choices[0].delta.content)
                
                if chunk.usage:
                    tokens_used = chunk.usage.total_tokens
            
            content = "".join(content_parts)
            cost = self._calculate_cost(tokens_used)
            
            return AgentResponse.success(
                request_id="",
                content=content,
                tokens_used=tokens_used,
                cost=cost,
                response_time=(datetime.now() - start_time).total_seconds(),
                metadata={"streaming": True}
            )
            
        except Exception as e:
            logger.error("OpenAI stream generation failed", 
                       agent_id=self.agent_id,
                       error=str(e))
            return AgentResponse.error("", f"Stream generation failed: {str(e)}")
    
    async def analyze_image(
        self,
        image_url: str,
        prompt: str = "Analyze this image",
        **kwargs
    ) -> AgentResponse:
        """分析图像"""
        start_time = datetime.now()
        
        try:
            # 检查是否支持图像分析
            if not any(cap.type == AgentType.IMAGE_UNDERSTANDING for cap in self.capabilities):
                return AgentResponse.error("", "This model does not support image analysis")
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
            
            params = {
                "model": self.model_config.model_name,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", self.model_config.max_tokens),
                "temperature": kwargs.get("temperature", self.model_config.temperature)
            }
            
            response = await self.client.chat.completions.create(**params)
            
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            cost = self._calculate_cost(tokens_used)
            
            return AgentResponse.success(
                request_id="",
                content=content,
                tokens_used=tokens_used,
                cost=cost,
                response_time=(datetime.now() - start_time).total_seconds()
            )
            
        except Exception as e:
            logger.error("OpenAI image analysis failed", 
                       agent_id=self.agent_id,
                       error=str(e))
            return AgentResponse.error("", f"Image analysis failed: {str(e)}")
    
    async def transcribe_audio(
        self,
        audio_file_path: str,
        language: Optional[str] = None,
        **kwargs
    ) -> AgentResponse:
        """转录音频"""
        start_time = datetime.now()
        
        try:
            # 检查是否支持音频处理
            if not any(cap.type == AgentType.AUDIO_PROCESSING for cap in self.capabilities):
                return AgentResponse.error("", "This model does not support audio transcription")
            
            # 使用Whisper进行转录
            with open(audio_file_path, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language
                )
            
            tokens_used = 0  # Whisper不返回token使用量
            cost = 0.006  # Whisper固定价格
            
            return AgentResponse.success(
                request_id="",
                content=transcript.text,
                tokens_used=tokens_used,
                cost=cost,
                response_time=(datetime.now() - start_time).total_seconds(),
                metadata={"model": "whisper-1"}
            )
            
        except Exception as e:
            logger.error("OpenAI audio transcription failed", 
                       agent_id=self.agent_id,
                       error=str(e))
            return AgentResponse.error("", f"Audio transcription failed: {str(e)}")
    
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        n: int = 1,
        **kwargs
    ) -> AgentResponse:
        """生成图像"""
        start_time = datetime.now()
        
        try:
            # 检查是否支持图像生成
            if not any(cap.type == AgentType.IMAGE_GENERATION for cap in self.capabilities):
                return AgentResponse.error("", "This model does not support image generation")
            
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=n
            )
            
            images = []
            for data in response.data:
                images.append({
                    "url": data.url,
                    "revised_prompt": getattr(data, 'revised_prompt', None)
                })
            
            tokens_used = 0  # DALL-E不返回token使用量
            cost = self._calculate_dalle_cost(size, quality, n)
            
            return AgentResponse.success(
                request_id="",
                content=images,
                tokens_used=tokens_used,
                cost=cost,
                response_time=(datetime.now() - start_time).total_seconds(),
                metadata={"model": "dall-e-3"}
            )
            
        except Exception as e:
            logger.error("OpenAI image generation failed", 
                       agent_id=self.agent_id,
                       error=str(e))
            return AgentResponse.error("", f"Image generation failed: {str(e)}")
    
    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncIterator[str]:
        """流式对话完成"""
        try:
            params = {
                "model": self.model_config.model_name,
                "messages": messages,
                "stream": True,
                "max_tokens": kwargs.get("max_tokens", self.model_config.max_tokens),
                "temperature": kwargs.get("temperature", self.model_config.temperature)
            }
            
            async for chunk in await self.client.chat.completions.create(**params):
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error("OpenAI stream failed", 
                       agent_id=self.agent_id,
                       error=str(e))
            yield f"Error: {str(e)}"
    
    def _calculate_cost(self, tokens: int) -> float:
        """计算API调用成本"""
        # OpenAI价格表（简化计算）
        model_name = self.model_config.model_name.lower()
        
        if "gpt-4" in model_name:
            if "gpt-4o" in model_name:
                cost_per_token = 0.00001  # $10/1M tokens
            else:
                cost_per_token = 0.00003  # $30/1M tokens
        elif "gpt-3.5" in model_name:
            cost_per_token = 0.000001   # $1/1M tokens
        else:
            cost_per_token = 0.00001    # 默认价格
        
        return tokens * cost_per_token
    
    def _calculate_dalle_cost(self, size: str, quality: str, n: int) -> float:
        """计算DALL-E成本"""
        # DALL-E价格表
        size_prices = {
            "1024x1024": 0.040,  # $0.040 per image
            "1792x1024": 0.080,  # $0.080 per image
            "1024x1792": 0.080   # $0.080 per image
        }
        
        base_price = size_prices.get(size, 0.040)
        
        # 高质量图像额外费用
        if quality == "hd":
            base_price *= 2
        
        return base_price * n
    
    async def list_available_models(self) -> List[Dict[str, Any]]:
        """列出可用的模型"""
        try:
            models = await self.client.models.list()
            return [
                {
                    "id": model.id,
                    "object": model.object,
                    "created": model.created,
                    "owned_by": model.owned_by
                }
                for model in models.data
            ]
        except Exception as e:
            logger.error("Failed to list OpenAI models", error=str(e))
            return []
    
    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        try:
            model = await self.client.models.retrieve(model_id)
            return {
                "id": model.id,
                "object": model.object,
                "created": model.created,
                "owned_by": model.owned_by
            }
        except Exception as e:
            logger.error("Failed to get OpenAI model info", 
                       model_id=model_id,
                       error=str(e))
            return None


# OpenAI代理工厂
def create_openai_agent(
    agent_id: str,
    name: str,
    model_name: str = "gpt-4",
    api_key: Optional[str] = None,
    **model_config_params
) -> OpenAIAgent:
    """创建OpenAI代理"""
    model_config = ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name=model_name,
        api_key=api_key or settings.ai.openai_api_key,
        **model_config_params
    )
    
    return OpenAIAgent(agent_id, name, model_config)


# 预定义的模型配置
OPENAI_MODEL_CONFIGS = {
    "gpt-4o": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="gpt-4o",
        max_tokens=128000,
        temperature=0.7,
        supports_streaming=True,
        supports_function_calling=True
    ),
    "gpt-4o-mini": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="gpt-4o-mini",
        max_tokens=128000,
        temperature=0.7,
        supports_streaming=True,
        supports_function_calling=True
    ),
    "gpt-4-turbo": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="gpt-4-turbo",
        max_tokens=128000,
        temperature=0.7,
        supports_streaming=True,
        supports_function_calling=True
    ),
    "gpt-3.5-turbo": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="gpt-3.5-turbo",
        max_tokens=16385,
        temperature=0.7,
        supports_streaming=True,
        supports_function_calling=True
    ),
    "dall-e-3": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="dall-e-3",
        supports_streaming=False,
        supports_function_calling=False
    ),
    "whisper-1": ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="whisper-1",
        supports_streaming=False,
        supports_function_calling=False
    )
}


def create_preconfigured_openai_agent(
    agent_id: str,
    name: str,
    model_name: str = "gpt-4o",
    api_key: Optional[str] = None
) -> OpenAIAgent:
    """使用预配置创建OpenAI代理"""
    if model_name not in OPENAI_MODEL_CONFIGS:
        raise ValueError(f"Unknown OpenAI model: {model_name}")
    
    base_config = OPENAI_MODEL_CONFIGS[model_name]
    
    # 合并用户提供的配置
    final_config = ModelConfig(
        provider=base_config.provider,
        model_name=base_config.model_name,
        api_key=api_key or settings.ai.openai_api_key,
        max_tokens=base_config.max_tokens,
        temperature=base_config.temperature,
        supports_streaming=base_config.supports_streaming,
        supports_function_calling=base_config.supports_function_calling,
        max_context_length=base_config.max_context_length
    )
    
    return OpenAIAgent(agent_id, name, final_config)