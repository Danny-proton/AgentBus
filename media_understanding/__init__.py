"""
AgentBus 媒体理解系统

基于Moltbot架构的完整媒体理解功能，包括：
- 媒体类型检测
- 图像理解 
- 音频理解
- 视频理解
- 文档理解
"""

from .core import MediaUnderstandingSystem, MediaUnderstandingResult
from .types import (
    MediaType,
    MediaUnderstandingCapability,
    MediaAttachment,
    MediaUnderstandingOutput,
    MediaUnderstandingProvider,
    AudioTranscriptionRequest,
    AudioTranscriptionResult,
    ImageDescriptionRequest,
    ImageDescriptionResult,
    VideoDescriptionRequest,
    VideoDescriptionResult,
)

__version__ = "1.0.0"
__all__ = [
    "MediaUnderstandingSystem",
    "MediaUnderstandingResult", 
    "MediaType",
    "MediaUnderstandingCapability",
    "MediaAttachment",
    "MediaUnderstandingOutput",
    "MediaUnderstandingProvider",
    "AudioTranscriptionRequest",
    "AudioTranscriptionResult",
    "ImageDescriptionRequest", 
    "ImageDescriptionResult",
    "VideoDescriptionRequest",
    "VideoDescriptionResult",
]