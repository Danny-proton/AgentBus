"""
视频理解模块

提供视频内容分析和描述功能
"""

import asyncio
import aiohttp
import base64
import io
import tempfile
import os
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from .types import (
    VideoDescriptionRequest, 
    VideoDescriptionResult,
    MediaUnderstandingProvider,
    MediaUnderstandingCapability,
)


class BaseVideoUnderstandingProvider(MediaUnderstandingProvider):
    """视频理解Provider基类"""
    
    def __init__(self, provider_id: str):
        super().__init__(provider_id)
    
    def get_capabilities(self) -> List[MediaUnderstandingCapability]:
        """返回支持的媒体理解能力"""
        return [MediaUnderstandingCapability.VIDEO]
    
    async def transcribe_audio(self, request):
        """音频转录功能由子类实现"""
        raise NotImplementedError(f"{self.id} provider does not support audio transcription")
    
    async def describe_image(self, request):
        """图像描述功能由子类实现"""
        raise NotImplementedError(f"{self.id} provider does not support image description")


class GoogleVideoProvider(BaseVideoUnderstandingProvider):
    """Google视频理解Provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("google")
        self.api_key = api_key
        self.model = "gemini-pro-vision"
    
    async def transcribe_audio(self, request):
        """音频转录功能由子类实现"""
        raise NotImplementedError(f"{self.id} provider does not support audio transcription")
    
    async def describe_video(self, request: VideoDescriptionRequest) -> VideoDescriptionResult:
        """使用Google Gemini API理解视频"""
        start_time = time.time()
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        # 构建请求数据
        # Google Gemini Pro Vision支持视频分析
        payload = {
            "contents": [{
                "parts": [
                    {
                        "text": request.prompt or "请分析这个视频的内容，包括主要场景、人物、动作和关键事件"
                    },
                    {
                        "inline_data": {
                            "mime_type": request.mime or "video/mp4",
                            "data": base64.b64encode(request.buffer).decode('utf-8')
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=request.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Google API error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    
                    if "candidates" in result and len(result["candidates"]) > 0:
                        content = result["candidates"][0]["content"]["parts"][0]["text"]
                        return VideoDescriptionResult(
                            text=content,
                            model=self.model,
                            metadata={
                                "provider": "google",
                                "analysis_type": "full_video"
                            }
                        )
                    else:
                        raise Exception("Invalid response format from Google")
                        
        except asyncio.TimeoutError:
            raise Exception(f"Google API timeout after {request.timeout} seconds")
        except Exception as e:
            raise Exception(f"Google API error: {str(e)}")


class OpenAIVideoProvider(BaseVideoUnderstandingProvider):
    """OpenAI视频理解Provider"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__("openai")
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
    
    async def transcribe_audio(self, request):
        """音频转录功能由子类实现"""
        raise NotImplementedError(f"{self.id} provider does not support audio transcription")
    
    async def describe_video(self, request: VideoDescriptionRequest) -> VideoDescriptionResult:
        """使用OpenAI GPT-4 Vision分析视频（通过关键帧）"""
        start_time = time.time()
        
        # OpenAI的GPT-4 Vision目前不直接支持视频，
        # 这里提供通过提取关键帧来分析的方案
        
        # 提取视频关键帧（这里需要实际的视频处理库）
        # 例如使用ffmpeg或moviepy提取关键帧
        keyframes = await self._extract_keyframes(request.buffer)
        
        # 如果没有提取到关键帧，返回基础信息
        if not keyframes:
            return VideoDescriptionResult(
                text=f"视频文件: {request.file_name}",
                model="openai-gpt4-vision",
                metadata={
                    "provider": "openai",
                    "analysis_type": "metadata_only",
                    "file_size": len(request.buffer)
                }
            )
        
        # 逐个分析关键帧
        frame_descriptions = []
        for i, frame in enumerate(keyframes[:3]):  # 最多分析3个关键帧
            frame_description = await self._analyze_frame_with_openai(frame, request.prompt)
            frame_descriptions.append(f"关键帧{i+1}: {frame_description}")
        
        # 合并分析结果
        combined_description = "\n".join(frame_descriptions)
        
        return VideoDescriptionResult(
            text=combined_description,
            model="openai-gpt4-vision",
            metadata={
                "provider": "openai",
                "analysis_type": "keyframes",
                "keyframes_analyzed": len(keyframes)
            }
        )
    
    async def _extract_keyframes(self, video_buffer: bytes) -> List[bytes]:
        """提取视频关键帧（需要实现）"""
        # 这里需要实际的视频处理实现
        # 可以使用moviepy、ffmpeg-python等库
        # 返回关键帧的图像数据
        
        # 临时返回空列表
        return []
    
    async def _analyze_frame_with_openai(self, frame_buffer: bytes, prompt: Optional[str]) -> str:
        """使用OpenAI分析单个帧"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt or "描述这个视频帧的内容"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64.b64encode(frame_buffer).decode('utf-8')}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300,
            "temperature": 0.1
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30.0)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "choices" in result and len(result["choices"]) > 0:
                            return result["choices"][0]["message"]["content"]
                    return "无法分析该帧"
        except Exception:
            pass
        
        return "分析失败"


class LocalVideoProvider(BaseVideoUnderstandingProvider):
    """本地视频理解Provider"""
    
    def __init__(self):
        super().__init__("local")
    
    async def transcribe_audio(self, request):
        """音频转录功能由子类实现"""
        raise NotImplementedError(f"{self.id} provider does not support audio transcription")
    
    async def describe_video(self, request: VideoDescriptionRequest) -> VideoDescriptionResult:
        """使用本地库分析视频元数据"""
        try:
            # 简单的视频元数据提取
            # 这里可以实现基于文件信息的分析
            
            metadata = {
                "file_name": request.file_name,
                "file_size": len(request.buffer),
                "mime_type": request.mime,
                "analysis_capability": "basic_metadata"
            }
            
            # 如果有提示词，添加到描述中
            if request.prompt:
                description = f"视频分析要求: {request.prompt}\n\n"
            else:
                description = ""
            
            description += f"视频文件: {request.file_name}\n"
            description += f"文件大小: {len(request.buffer)} 字节\n"
            description += f"文件类型: {request.mime or '未知'}\n"
            
            # 添加分析限制说明
            description += "\n注意: 本地Provider提供基础的视频元数据分析，"
            description += "如需深度视频内容理解，请配置云端Provider。"
            
            return VideoDescriptionResult(
                text=description,
                model="local-video-analyzer",
                metadata=metadata
            )
            
        except Exception as e:
            raise Exception(f"Local video analysis failed: {str(e)}")


class VideoUnderstandingEngine:
    """视频理解引擎"""
    
    def __init__(self):
        self.providers: Dict[str, BaseVideoUnderstandingProvider] = {}
        self._register_default_providers()
    
    def _register_default_providers(self):
        """注册默认的视频理解Provider"""
        # 注册本地Provider（总是可用）
        self.providers["local"] = LocalVideoProvider()
    
    def register_provider(self, provider: BaseVideoUnderstandingProvider):
        """注册视频理解Provider"""
        self.providers[provider.id] = provider
    
    async def describe_video(
        self, 
        request: VideoDescriptionRequest,
        preferred_provider: Optional[str] = None
    ) -> VideoDescriptionResult:
        """理解视频内容"""
        
        # 检查视频文件大小限制
        max_size = 100 * 1024 * 1024  # 100MB
        if len(request.buffer) > max_size:
            raise Exception(f"Video file too large: {len(request.buffer)} bytes (max: {max_size})")
        
        # 如果指定了首选Provider，优先使用
        if preferred_provider and preferred_provider in self.providers:
            provider = self.providers[preferred_provider]
            try:
                return await provider.describe_video(request)
            except Exception as e:
                print(f"Provider {preferred_provider} failed: {e}")
        
        # 尝试所有可用的Provider
        for provider_id, provider in self.providers.items():
            try:
                return await provider.describe_video(request)
            except Exception as e:
                print(f"Provider {provider_id} failed: {e}")
                continue
        
        raise Exception("All video understanding providers failed")
    
    async def analyze_video_scenes(
        self,
        request: VideoDescriptionRequest,
        preferred_provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """分析视频场景（如果Provider支持）"""
        result = await self.describe_video(request, preferred_provider)
        
        # 如果Provider返回了场景信息
        if hasattr(result, 'scenes') and result.scenes:
            return result.scenes
        
        # 否则基于文本描述简单分割
        text = result.text
        if "关键帧" in text:
            # 尝试从关键帧描述中提取场景信息
            scenes = []
            lines = text.split('\n')
            current_scene = {"description": "", "timestamp": 0}
            
            for line in lines:
                if line.startswith("关键帧"):
                    if current_scene["description"]:
                        scenes.append(current_scene)
                    current_scene = {"description": line, "timestamp": len(scenes) * 10}
                else:
                    current_scene["description"] += line
            
            if current_scene["description"]:
                scenes.append(current_scene)
            
            return scenes
        
        # 默认返回单个场景
        return [{"description": text, "timestamp": 0}]
    
    async def extract_video_frames(
        self,
        video_buffer: bytes,
        max_frames: int = 5
    ) -> List[Tuple[bytes, float]]:
        """提取视频关键帧"""
        # 这里需要实际的视频处理实现
        # 返回 (frame_data, timestamp) 元组列表
        
        # 临时返回空列表
        return []


# 全局视频理解引擎实例
_video_engine = VideoUnderstandingEngine()


def register_video_provider(provider: BaseVideoUnderstandingProvider):
    """注册视频理解Provider"""
    _video_engine.register_provider(provider)


async def describe_video(
    request: VideoDescriptionRequest,
    preferred_provider: Optional[str] = None
) -> VideoDescriptionResult:
    """理解视频内容"""
    return await _video_engine.describe_video(request, preferred_provider)


async def analyze_video_scenes(
    request: VideoDescriptionRequest,
    preferred_provider: Optional[str] = None
) -> List[Dict[str, Any]]:
    """分析视频场景"""
    return await _video_engine.analyze_video_scenes(request, preferred_provider)


async def extract_video_frames(
    video_buffer: bytes,
    max_frames: int = 5
) -> List[Tuple[bytes, float]]:
    """提取视频关键帧"""
    return await _video_engine.extract_video_frames(video_buffer, max_frames)


def get_available_video_providers() -> List[str]:
    """获取可用的视频理解Provider列表"""
    return list(_video_engine.providers.keys())