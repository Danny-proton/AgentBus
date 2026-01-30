"""
音频理解模块

提供音频转录和理解功能
"""

import asyncio
import aiohttp
import base64
import io
import wave
import json
import time
from typing import Dict, List, Optional, Any, Tuple
import speech_recognition as sr
import tempfile
import os

from .types import (
    AudioTranscriptionRequest, 
    AudioTranscriptionResult,
    MediaUnderstandingProvider,
    MediaUnderstandingCapability,
)


class BaseAudioUnderstandingProvider(MediaUnderstandingProvider):
    """音频理解Provider基类"""
    
    def __init__(self, provider_id: str):
        super().__init__(provider_id)
    
    def get_capabilities(self) -> List[MediaUnderstandingCapability]:
        """返回支持的媒体理解能力"""
        return [MediaUnderstandingCapability.AUDIO]
    
    async def describe_image(self, request):
        """图像描述功能由子类实现"""
        raise NotImplementedError(f"{self.id} provider does not support image description")
    
    async def describe_video(self, request):
        """视频描述功能由子类实现"""
        raise NotImplementedError(f"{self.id} provider does not support video description")


class OpenAIAudioProvider(BaseAudioUnderstandingProvider):
    """OpenAI音频转录Provider"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__("openai")
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = "whisper-1"
    
    async def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        """使用OpenAI Whisper API转录音频"""
        start_time = time.time()
        
        # 准备API请求
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 准备音频数据
        audio_data = request.buffer
        files = {
            'file': ('audio.wav', io.BytesIO(audio_data), request.mime or 'audio/wav')
        }
        
        # 构建请求数据
        data = {
            'model': request.model or self.model,
            'language': request.language,
            'response_format': 'verbose_json',
            'temperature': request.temperature
        }
        
        if request.prompt:
            data['prompt'] = request.prompt
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=aiohttp.ClientTimeout(total=request.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    
                    # 解析响应
                    text = result.get("text", "")
                    language = result.get("language", request.language)
                    duration = result.get("duration", 0.0)
                    
                    # 解析分段信息
                    segments = result.get("segments", [])
                    
                    return AudioTranscriptionResult(
                        text=text,
                        model=request.model or self.model,
                        language=language,
                        segments=segments
                    )
                    
        except asyncio.TimeoutError:
            raise Exception(f"OpenAI API timeout after {request.timeout} seconds")
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")


class GoogleAudioProvider(BaseAudioUnderstandingProvider):
    """Google音频转录Provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("google")
        self.api_key = api_key
        self.model = "google_speech_to_text"
    
    async def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        """使用Google Speech-to-Text API转录音频"""
        start_time = time.time()
        
        # Google Cloud Speech-to-Text API
        # 注意：这里需要实际的Google Cloud服务实现
        # 这里提供的是一个示例框架
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 将音频编码为base64
        audio_base64 = base64.b64encode(request.buffer).decode('utf-8')
        
        payload = {
            "config": {
                "encoding": "LINEAR16",  # 或根据实际音频格式调整
                "sampleRateHertz": 16000,  # 需要根据实际音频调整
                "languageCode": request.language or "zh-CN",
                "enableAutomaticPunctuation": True,
                "model": "latest_long"
            },
            "audio": {
                "content": audio_base64
            }
        }
        
        try:
            # 这里需要实际的Google Cloud API调用
            # async with aiohttp.ClientSession() as session:
            #     async with session.post(
            #         f"https://speech.googleapis.com/v1/speech:recognize",
            #         headers=headers,
            #         json=payload,
            #         timeout=aiohttp.ClientTimeout(total=request.timeout)
            #     ) as response:
            #         ...
            
            # 临时返回示例结果
            return AudioTranscriptionResult(
                text="Google API integration placeholder",
                model=self.model,
                language=request.language or "zh-CN"
            )
            
        except Exception as e:
            raise Exception(f"Google API error: {str(e)}")


class LocalAudioProvider(BaseAudioUnderstandingProvider):
    """本地音频转录Provider（使用speech_recognition）"""
    
    def __init__(self):
        super().__init__("local")
        self.recognizer = sr.Recognizer()
    
    async def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        """使用本地库转录音频"""
        try:
            # 将音频数据转换为AudioData对象
            # speech_recognition库需要特定的音频格式
            audio_data = sr.AudioData(
                request.buffer, 
                sample_rate=16000,  # 默认采样率
                sample_width=2      # 默认位深
            )
            
            # 使用Google Web Speech API进行识别（需要网络）
            try:
                text = self.recognizer.recognize_google(audio_data, language=request.language)
                return AudioTranscriptionResult(
                    text=text,
                    model="Google-Web-Speech",
                    confidence=0.8
                )
            except sr.UnknownValueError:
                return AudioTranscriptionResult(
                    text="无法识别音频内容",
                    model="Google-Web-Speech",
                    confidence=0.0
                )
            except sr.RequestError as e:
                # 如果Google API失败，尝试本地识别
                try:
                    text = self.recognizer.recognize_sphinx(audio_data)
                    return AudioTranscriptionResult(
                        text=text,
                        model="Sphinx",
                        confidence=0.6
                    )
                except:
                    raise Exception(f"Local speech recognition failed: {str(e)}")
                    
        except Exception as e:
            raise Exception(f"Local audio transcription failed: {str(e)}")


class DeepgramAudioProvider(BaseAudioUnderstandingProvider):
    """Deepgram音频转录Provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("deepgram")
        self.api_key = api_key
        self.model = "nova"
    
    async def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        """使用Deepgram API转录音频"""
        start_time = time.time()
        
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Deepgram API配置
        config = {
            "model": request.model or self.model,
            "language": request.language or "zh-CN",
            "smart_format": True,
            "punctuate": True,
            "diarize": False,
            "utterances": False
        }
        
        if request.prompt:
            config["context"] = request.prompt
        
        # Deepgram使用WebSocket连接，这里提供HTTP接口示例
        # 实际实现需要使用WebSocket
        try:
            # 这里需要实际的Deepgram WebSocket实现
            # 临时返回示例结果
            return AudioTranscriptionResult(
                text="Deepgram API integration placeholder",
                model=self.model,
                language=request.language or "zh-CN"
            )
            
        except Exception as e:
            raise Exception(f"Deepgram API error: {str(e)}")


class AudioUnderstandingEngine:
    """音频理解引擎"""
    
    def __init__(self):
        self.providers: Dict[str, BaseAudioUnderstandingProvider] = {}
        self._register_default_providers()
    
    def _register_default_providers(self):
        """注册默认的音频理解Provider"""
        # 注册本地Provider（总是可用）
        self.providers["local"] = LocalAudioProvider()
    
    def register_provider(self, provider: BaseAudioUnderstandingProvider):
        """注册音频理解Provider"""
        self.providers[provider.id] = provider
    
    async def transcribe_audio(
        self, 
        request: AudioTranscriptionRequest,
        preferred_provider: Optional[str] = None
    ) -> AudioTranscriptionResult:
        """转录音频"""
        
        # 如果指定了首选Provider，优先使用
        if preferred_provider and preferred_provider in self.providers:
            provider = self.providers[preferred_provider]
            try:
                return await provider.transcribe_audio(request)
            except Exception as e:
                print(f"Provider {preferred_provider} failed: {e}")
        
        # 尝试所有可用的Provider
        for provider_id, provider in self.providers.items():
            try:
                return await provider.transcribe_audio(request)
            except Exception as e:
                print(f"Provider {provider_id} failed: {e}")
                continue
        
        raise Exception("All audio understanding providers failed")
    
    async def batch_transcribe(
        self,
        requests: List[AudioTranscriptionRequest],
        preferred_provider: Optional[str] = None,
        max_concurrent: int = 3
    ) -> List[AudioTranscriptionResult]:
        """批量转录音频"""
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def transcribe_with_semaphore(request):
            async with semaphore:
                return await self.transcribe_audio(request, preferred_provider)
        
        tasks = [transcribe_with_semaphore(request) for request in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(AudioTranscriptionResult(
                    text=f"转录失败: {str(result)}",
                    model="error",
                    confidence=0.0
                ))
            else:
                processed_results.append(result)
        
        return processed_results


# 全局音频理解引擎实例
_audio_engine = AudioUnderstandingEngine()


def register_audio_provider(provider: BaseAudioUnderstandingProvider):
    """注册音频理解Provider"""
    _audio_engine.register_provider(provider)


async def transcribe_audio(
    request: AudioTranscriptionRequest,
    preferred_provider: Optional[str] = None
) -> AudioTranscriptionResult:
    """转录音频"""
    return await _audio_engine.transcribe_audio(request, preferred_provider)


async def batch_transcribe_audio(
    requests: List[AudioTranscriptionRequest],
    preferred_provider: Optional[str] = None,
    max_concurrent: int = 3
) -> List[AudioTranscriptionResult]:
    """批量转录音频"""
    return await _audio_engine.batch_transcribe(requests, preferred_provider, max_concurrent)


def get_available_audio_providers() -> List[str]:
    """获取可用的音频理解Provider列表"""
    return list(_audio_engine.providers.keys())