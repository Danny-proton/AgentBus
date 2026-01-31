"""
媒体理解系统类型定义

基于Moltbot架构的类型定义，定义媒体理解系统的核心数据类型和接口
"""

from typing import Dict, List, Optional, Union, Callable, Any, Protocol
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from abc import ABC, abstractmethod


class MediaType(Enum):
    """媒体类型枚举"""
    IMAGE = "image"
    AUDIO = "audio" 
    VIDEO = "video"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


class MediaUnderstandingCapability(Enum):
    """媒体理解能力枚举"""
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"


class MediaUnderstandingKind(Enum):
    """媒体理解结果类型"""
    IMAGE_DESCRIPTION = "image.description"
    AUDIO_TRANSCRIPTION = "audio.transcription"
    VIDEO_DESCRIPTION = "video.description"
    DOCUMENT_EXTRACTION = "document.extraction"


class MediaUnderstandingOutcome(Enum):
    """媒体理解决策结果"""
    SUCCESS = "success"
    SKIPPED = "skipped"
    DISABLED = "disabled"
    NO_ATTACHMENT = "no-attachment"
    SCOPE_DENY = "scope-deny"


@dataclass
class MediaAttachment:
    """媒体附件数据结构"""
    path: Optional[str] = None
    url: Optional[str] = None
    mime: Optional[str] = None
    index: int = 0
    
    def __post_init__(self):
        """后处理验证"""
        if not self.path and not self.url:
            raise ValueError("MediaAttachment must have either path or url")


@dataclass
class MediaUnderstandingDecision:
    """媒体理解决策结果"""
    capability: MediaUnderstandingCapability
    outcome: MediaUnderstandingOutcome
    attachments: List['MediaUnderstandingAttachmentDecision']
    reason: Optional[str] = None


@dataclass
class MediaUnderstandingAttachmentDecision:
    """附件级别的理解决策"""
    attachment_index: int
    attempts: List['MediaUnderstandingModelDecision']
    chosen: Optional['MediaUnderstandingModelDecision'] = None


@dataclass
class MediaUnderstandingModelDecision:
    """模型级别的理解决策"""
    provider: Optional[str] = None
    model: Optional[str] = None
    type: str = "provider"  # "provider" or "cli"
    outcome: str = "success"  # "success", "skipped", "failed"
    reason: Optional[str] = None


@dataclass
class MediaUnderstandingOutput:
    """媒体理解输出结果"""
    kind: MediaUnderstandingKind
    attachment_index: int
    text: str
    provider: str
    model: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# 音频理解请求/结果类型
@dataclass
class AudioTranscriptionRequest:
    """音频转录请求"""
    buffer: bytes
    file_name: str
    mime: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    model: Optional[str] = None
    language: Optional[str] = None
    prompt: Optional[str] = None
    timeout: float = 30.0
    temperature: float = 0.0
    

@dataclass
class AudioTranscriptionResult:
    """音频转录结果"""
    text: str
    model: Optional[str] = None
    language: Optional[str] = None
    confidence: Optional[float] = None
    segments: Optional[List[Dict]] = None


# 图像理解请求/结果类型
@dataclass
class ImageDescriptionRequest:
    """图像描述请求"""
    buffer: bytes
    file_name: str
    model: str
    provider: str
    mime: Optional[str] = None
    prompt: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.0
    timeout: float = 30.0


@dataclass
class ImageDescriptionResult:
    """图像描述结果"""
    text: str
    model: Optional[str] = None
    confidence: Optional[float] = None
    detected_objects: Optional[List[Dict]] = None


# 视频理解请求/结果类型
@dataclass
class VideoDescriptionRequest:
    """视频描述请求"""
    buffer: bytes
    file_name: str
    mime: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    prompt: Optional[str] = None
    timeout: float = 60.0
    max_duration: float = 300.0  # 最大5分钟


@dataclass
class VideoDescriptionResult:
    """视频描述结果"""
    text: str
    model: Optional[str] = None
    duration: Optional[float] = None
    scenes: Optional[List[Dict]] = None


# 文档理解请求/结果类型
@dataclass
class DocumentExtractionRequest:
    """文档提取请求"""
    buffer: bytes
    file_name: str
    mime: Optional[str] = None
    extract_text: bool = True
    extract_tables: bool = True
    extract_images: bool = True
    max_pages: Optional[int] = None
    ocr_enabled: bool = False


@dataclass
class DocumentExtractionResult:
    """文档提取结果"""
    text: str
    pages: Optional[int] = None
    tables: Optional[List[str]] = None
    images: Optional[List[bytes]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# Provider接口定义
class MediaUnderstandingProvider(ABC):
    """媒体理解Provider基类"""
    
    def __init__(self, provider_id: str):
        self.id = provider_id
        
    @abstractmethod
    def get_capabilities(self) -> List[MediaUnderstandingCapability]:
        """获取支持的媒体理解能力"""
        pass
    
    @abstractmethod
    async def transcribe_audio(self, request: AudioTranscriptionRequest) -> AudioTranscriptionResult:
        """音频转录"""
        pass
    
    @abstractmethod
    async def describe_image(self, request: ImageDescriptionRequest) -> ImageDescriptionResult:
        """图像描述"""
        pass
    
    @abstractmethod
    async def describe_video(self, request: VideoDescriptionRequest) -> VideoDescriptionResult:
        """视频描述"""
        pass


# 配置类型
@dataclass
class MediaUnderstandingConfig:
    """媒体理解配置"""
    enabled: bool = True
    timeout: float = 30.0
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    supported_mimes: List[str] = field(default_factory=list)
    
    # 能力配置
    image_config: Dict[str, Any] = field(default_factory=dict)
    audio_config: Dict[str, Any] = field(default_factory=dict)
    video_config: Dict[str, Any] = field(default_factory=dict)
    document_config: Dict[str, Any] = field(default_factory=dict)
    
    # Provider配置
    provider_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class MediaUnderstandingContext:
    """媒体理解上下文"""
    attachments: List[MediaAttachment]
    config: MediaUnderstandingConfig
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MediaUnderstandingResult:
    """媒体理解综合结果"""
    success: bool
    outputs: List[MediaUnderstandingOutput]
    decisions: List[MediaUnderstandingDecision]
    applied_capabilities: List[MediaUnderstandingCapability]
    total_processing_time: float = 0.0
    error: Optional[str] = None
    
    @property
    def has_image_output(self) -> bool:
        """是否有图像理解输出"""
        return any(output.kind == MediaUnderstandingKind.IMAGE_DESCRIPTION for output in self.outputs)
    
    @property
    def has_audio_output(self) -> bool:
        """是否有音频理解输出"""
        return any(output.kind == MediaUnderstandingKind.AUDIO_TRANSCRIPTION for output in self.outputs)
    
    @property
    def has_video_output(self) -> bool:
        """是否有视频理解输出"""
        return any(output.kind == MediaUnderstandingKind.VIDEO_DESCRIPTION for output in self.outputs)
    
    @property
    def has_document_output(self) -> bool:
        """是否有文档理解输出"""
        return any(output.kind == MediaUnderstandingKind.DOCUMENT_EXTRACTION for output in self.outputs)
    
    def get_text_output(self) -> str:
        """获取所有文本输出"""
        return "\n".join(output.text for output in self.outputs)
    
    def get_output_by_capability(self, capability: MediaUnderstandingCapability) -> List[MediaUnderstandingOutput]:
        """根据能力获取输出"""
        kind_map = {
            MediaUnderstandingCapability.IMAGE: MediaUnderstandingKind.IMAGE_DESCRIPTION,
            MediaUnderstandingCapability.AUDIO: MediaUnderstandingKind.AUDIO_TRANSCRIPTION,
            MediaUnderstandingCapability.VIDEO: MediaUnderstandingKind.VIDEO_DESCRIPTION,
            MediaUnderstandingCapability.DOCUMENT: MediaUnderstandingKind.DOCUMENT_EXTRACTION,
        }
        target_kind = kind_map.get(capability)
        if not target_kind:
            return []
        return [output for output in self.outputs if output.kind == target_kind]