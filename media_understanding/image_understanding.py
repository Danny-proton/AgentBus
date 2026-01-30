"""
图像理解模块

提供图像内容分析和描述功能
"""

import base64
import io
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from PIL import Image
import json
import time

from .types import (
    ImageDescriptionRequest, 
    ImageDescriptionResult,
    MediaUnderstandingProvider,
    MediaUnderstandingCapability,
)


class BaseImageUnderstandingProvider(MediaUnderstandingProvider):
    """图像理解Provider基类"""
    
    def __init__(self, provider_id: str):
        super().__init__(provider_id)
    
    def get_capabilities(self) -> List[MediaUnderstandingCapability]:
        """返回支持的媒体理解能力"""
        return [MediaUnderstandingCapability.IMAGE]
    
    async def describe_video(self, request):
        """视频描述功能由子类实现"""
        raise NotImplementedError(f"{self.id} provider does not support video description")
    
    def _encode_image_to_base64(self, buffer: bytes) -> str:
        """将图像编码为base64字符串"""
        return base64.b64encode(buffer).decode('utf-8')


class OpenAIImageProvider(BaseImageUnderstandingProvider):
    """OpenAI图像理解Provider"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__("openai")
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = "gpt-4-vision-preview"
    
    async def transcribe_audio(self, request):
        """音频转录功能由子类实现"""
        raise NotImplementedError(f"{self.id} provider does not support audio transcription")
    
    async def describe_image(self, request: ImageDescriptionRequest) -> ImageDescriptionResult:
        """使用OpenAI API描述图像"""
        start_time = time.time()
        
        # 准备API请求
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 构建请求数据
        payload = {
            "model": request.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": request.prompt or "请描述这张图片的内容"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{request.mime};base64,{self._encode_image_to_base64(request.buffer)}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=request.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    
                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"]
                        return ImageDescriptionResult(
                            text=content,
                            model=request.model,
                            confidence=0.9
                        )
                    else:
                        raise Exception("Invalid response format from OpenAI")
                        
        except asyncio.TimeoutError:
            raise Exception(f"OpenAI API timeout after {request.timeout} seconds")
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")


class AnthropicImageProvider(BaseImageUnderstandingProvider):
    """Anthropic图像理解Provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("anthropic")
        self.api_key = api_key
        self.model = "claude-3-haiku-20240307"
    
    async def transcribe_audio(self, request):
        """音频转录功能由子类实现"""
        raise NotImplementedError(f"{self.id} provider does not support audio transcription")
    
    async def describe_image(self, request: ImageDescriptionRequest) -> ImageDescriptionResult:
        """使用Anthropic API描述图像"""
        start_time = time.time()
        
        # 准备API请求
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        # 构建请求数据
        payload = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": request.prompt or "Please describe this image"
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": request.mime or "image/jpeg",
                                "data": self._encode_image_to_base64(request.buffer)
                            }
                        }
                    ]
                }
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=request.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Anthropic API error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    
                    if "content" in result and len(result["content"]) > 0:
                        content = result["content"][0]["text"]
                        return ImageDescriptionResult(
                            text=content,
                            model=request.model,
                            confidence=0.9
                        )
                    else:
                        raise Exception("Invalid response format from Anthropic")
                        
        except asyncio.TimeoutError:
            raise Exception(f"Anthropic API timeout after {request.timeout} seconds")
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")


class LocalImageProvider(BaseImageUnderstandingProvider):
    """本地图像理解Provider（使用PIL和简单分析）"""
    
    def __init__(self):
        super().__init__("local")
    
    async def transcribe_audio(self, request):
        """音频转录功能由子类实现"""
        raise NotImplementedError(f"{self.id} provider does not support audio transcription")
    
    async def describe_image(self, request: ImageDescriptionRequest) -> ImageDescriptionResult:
        """使用本地PIL库分析图像"""
        try:
            # 使用PIL打开图像
            image = Image.open(io.BytesIO(request.buffer))
            
            # 获取图像基本信息
            width, height = image.size
            mode = image.mode
            
            # 构建基础描述
            description_parts = [
                f"图像尺寸: {width}x{height}像素",
                f"色彩模式: {mode}"
            ]
            
            # 添加颜色分析
            if image.mode == "RGB":
                # 计算平均颜色
                import numpy as np
                img_array = np.array(image)
                avg_color = np.mean(img_array.reshape(-1, 3), axis=0)
                r, g, b = avg_color
                
                description_parts.append(
                    f"平均颜色: RGB({int(r)}, {int(g)}, {int(b)})"
                )
            
            # 添加图像格式信息
            if request.mime:
                description_parts.append(f"文件格式: {request.mime}")
            
            # 如果有自定义提示词，添加提示
            if request.prompt:
                description_parts.append(f"分析要求: {request.prompt}")
            
            description = "、".join(description_parts)
            
            return ImageDescriptionResult(
                text=description,
                model="PIL-local",
                confidence=0.7,
                metadata={
                    "width": width,
                    "height": height,
                    "mode": mode,
                    "file_size": len(request.buffer)
                }
            )
            
        except Exception as e:
            raise Exception(f"Local image analysis failed: {str(e)}")


class ImageUnderstandingEngine:
    """图像理解引擎"""
    
    def __init__(self):
        self.providers: Dict[str, BaseImageUnderstandingProvider] = {}
        self._register_default_providers()
    
    def _register_default_providers(self):
        """注册默认的图像理解Provider"""
        # 注册本地Provider（总是可用）
        self.providers["local"] = LocalImageProvider()
    
    def register_provider(self, provider: BaseImageUnderstandingProvider):
        """注册图像理解Provider"""
        self.providers[provider.id] = provider
    
    async def describe_image(
        self, 
        request: ImageDescriptionRequest,
        preferred_provider: Optional[str] = None
    ) -> ImageDescriptionResult:
        """描述图像"""
        
        # 如果指定了首选Provider，优先使用
        if preferred_provider and preferred_provider in self.providers:
            provider = self.providers[preferred_provider]
            try:
                return await provider.describe_image(request)
            except Exception as e:
                print(f"Provider {preferred_provider} failed: {e}")
        
        # 尝试所有可用的Provider
        for provider_id, provider in self.providers.items():
            try:
                return await provider.describe_image(request)
            except Exception as e:
                print(f"Provider {provider_id} failed: {e}")
                continue
        
        raise Exception("All image understanding providers failed")


# 全局图像理解引擎实例
_image_engine = ImageUnderstandingEngine()


def register_image_provider(provider: BaseImageUnderstandingProvider):
    """注册图像理解Provider"""
    _image_engine.register_provider(provider)


async def describe_image(
    request: ImageDescriptionRequest,
    preferred_provider: Optional[str] = None
) -> ImageDescriptionResult:
    """描述图像"""
    return await _image_engine.describe_image(request, preferred_provider)


def get_available_image_providers() -> List[str]:
    """获取可用的图像理解Provider列表"""
    return list(_image_engine.providers.keys())