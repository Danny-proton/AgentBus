"""
媒体理解系统核心模块

整合所有媒体理解能力，提供统一的媒体分析接口
"""

import asyncio
import time
import traceback
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import io

from .types import (
    MediaType,
    MediaUnderstandingCapability,
    MediaAttachment,
    MediaUnderstandingContext,
    MediaUnderstandingResult,
    MediaUnderstandingOutput,
    MediaUnderstandingKind,
    MediaUnderstandingDecision,
    MediaUnderstandingOutcome,
    AudioTranscriptionRequest,
    ImageDescriptionRequest,
    VideoDescriptionRequest,
    DocumentExtractionRequest,
)

from .detector import detect_media_type, get_media_info, is_supported_media
from .image_understanding import (
    describe_image,
    register_image_provider,
    get_available_image_providers
)
from .audio_understanding import (
    transcribe_audio,
    register_audio_provider,
    get_available_audio_providers
)
from .video_understanding import (
    describe_video,
    register_video_provider,
    get_available_video_providers
)
from .document_understanding import (
    extract_document_content,
    register_document_provider,
    get_available_document_providers
)


class MediaUnderstandingSystem:
    """媒体理解系统主类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化媒体理解系统
        
        Args:
            config: 系统配置
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.timeout = self.config.get("timeout", 30.0)
        self.max_file_size = self.config.get("max_file_size", 10 * 1024 * 1024)  # 10MB
        self.max_concurrent = self.config.get("max_concurrent", 3)
        
        # 能力处理顺序
        self.capability_order = [
            MediaUnderstandingCapability.IMAGE,
            MediaUnderstandingCapability.AUDIO,
            MediaUnderstandingCapability.VIDEO,
            MediaUnderstandingCapability.DOCUMENT
        ]
        
        # 统计信息
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "by_type": {
                MediaType.IMAGE.value: 0,
                MediaType.AUDIO.value: 0,
                MediaType.VIDEO.value: 0,
                MediaType.DOCUMENT.value: 0,
                MediaType.UNKNOWN.value: 0
            },
            "by_capability": {
                capability.value: 0 for capability in MediaUnderstandingCapability
            }
        }
    
    def register_provider(self, provider_type: str, provider):
        """注册Provider
        
        Args:
            provider_type: Provider类型 ("image", "audio", "video", "document")
            provider: Provider实例
        """
        if provider_type == "image":
            register_image_provider(provider)
        elif provider_type == "audio":
            register_audio_provider(provider)
        elif provider_type == "video":
            register_video_provider(provider)
        elif provider_type == "document":
            register_document_provider(provider)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "enabled": self.enabled,
            "timeout": self.timeout,
            "max_file_size": self.max_file_size,
            "max_concurrent": self.max_concurrent,
            "available_providers": {
                "image": get_available_image_providers(),
                "audio": get_available_audio_providers(),
                "video": get_available_video_providers(),
                "document": get_available_document_providers()
            },
            "stats": self.stats
        }
    
    async def understand_media(
        self,
        context: MediaUnderstandingContext,
        preferred_providers: Optional[Dict[str, str]] = None
    ) -> MediaUnderstandingResult:
        """理解媒体内容
        
        Args:
            context: 媒体理解上下文
            preferred_providers: 首选Provider映射
            
        Returns:
            MediaUnderstandingResult: 理解结果
        """
        start_time = time.time()
        
        if not self.enabled:
            return MediaUnderstandingResult(
                success=False,
                outputs=[],
                decisions=[],
                applied_capabilities=[],
                total_processing_time=0.0,
                error="Media understanding system is disabled"
            )
        
        # 检查附件
        if not context.attachments:
            return MediaUnderstandingResult(
                success=False,
                outputs=[],
                decisions=[],
                applied_capabilities=[],
                total_processing_time=time.time() - start_time,
                error="No attachments provided"
            )
        
        # 更新统计
        self.stats["total_processed"] += 1
        
        try:
            outputs = []
            decisions = []
            applied_capabilities = []
            
            # 并发处理不同的媒体类型
            tasks = []
            for capability in self.capability_order:
                task = self._process_capability(
                    capability, context, preferred_providers
                )
                tasks.append(task)
            
            # 执行所有任务
            capability_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 收集结果
            for capability, result in zip(self.capability_order, capability_results):
                if isinstance(result, Exception):
                    print(f"Capability {capability.value} failed: {result}")
                    continue
                
                if result:
                    outputs.extend(result.get("outputs", []))
                    decisions.extend(result.get("decisions", []))
                    applied_capabilities.append(capability)
                    self.stats["by_capability"][capability.value] += 1
            
            success = len(outputs) > 0
            processing_time = time.time() - start_time
            
            if success:
                self.stats["successful"] += 1
            else:
                self.stats["failed"] += 1
            
            return MediaUnderstandingResult(
                success=success,
                outputs=outputs,
                decisions=decisions,
                applied_capabilities=applied_capabilities,
                total_processing_time=processing_time,
                error=None if success else "No successful understanding results"
            )
            
        except Exception as e:
            error_msg = f"Media understanding failed: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            
            self.stats["failed"] += 1
            
            return MediaUnderstandingResult(
                success=False,
                outputs=[],
                decisions=[],
                applied_capabilities=[],
                total_processing_time=time.time() - start_time,
                error=error_msg
            )
    
    async def _process_capability(
        self,
        capability: MediaUnderstandingCapability,
        context: MediaUnderstandingContext,
        preferred_providers: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, Any]]:
        """处理特定能力的媒体理解"""
        
        # 筛选对应类型的附件
        matching_attachments = self._filter_attachments_by_capability(
            context.attachments, capability
        )
        
        if not matching_attachments:
            return {
                "outputs": [],
                "decisions": [MediaUnderstandingDecision(
                    capability=capability,
                    outcome=MediaUnderstandingOutcome.NO_ATTACHMENT,
                    attachments=[]
                )]
            }
        
        # 检查能力是否被禁用
        if not self._is_capability_enabled(capability, context):
            return {
                "outputs": [],
                "decisions": [MediaUnderstandingDecision(
                    capability=capability,
                    outcome=MediaUnderstandingOutcome.DISABLED,
                    attachments=[]
                )]
            }
        
        # 获取首选Provider
        preferred_provider = None
        if preferred_providers:
            preferred_provider = preferred_providers.get(capability.value)
        
        # 处理每个匹配的附件
        outputs = []
        attachment_decisions = []
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_single_attachment(attachment: MediaAttachment):
            async with semaphore:
                return await self._process_single_attachment(
                    attachment, capability, context, preferred_provider
                )
        
        # 并发处理附件
        tasks = [
            process_single_attachment(attachment) 
            for attachment in matching_attachments
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集结果
        for attachment, result in zip(matching_attachments, results):
            if isinstance(result, Exception):
                print(f"Attachment {attachment.index} failed: {result}")
                attachment_decisions.append({
                    "attachment_index": attachment.index,
                    "attempts": [],
                    "chosen": None
                })
            elif result:
                outputs.extend(result.get("outputs", []))
                attachment_decisions.extend(result.get("decisions", []))
        
        # 构建最终决策
        decision = MediaUnderstandingDecision(
            capability=capability,
            outcome=MediaUnderstandingOutcome.SUCCESS if outputs else MediaUnderstandingOutcome.SKIPPED,
            attachments=attachment_decisions
        )
        
        return {
            "outputs": outputs,
            "decisions": [decision]
        }
    
    async def _process_single_attachment(
        self,
        attachment: MediaAttachment,
        capability: MediaUnderstandingCapability,
        context: MediaUnderstandingContext,
        preferred_provider: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """处理单个附件"""
        
        try:
            # 读取文件数据
            buffer = await self._read_attachment_buffer(attachment)
            
            if not buffer:
                return None
            
            # 检查文件大小
            if len(buffer) > self.max_file_size:
                raise Exception(f"File too large: {len(buffer)} bytes (max: {self.max_file_size})")
            
            outputs = []
            attempts = []
            
            # 根据能力类型处理
            if capability == MediaUnderstandingCapability.IMAGE:
                result = await self._process_image(
                    buffer, attachment, context, preferred_provider
                )
                if result:
                    outputs.append(result)
                    attempts.append({
                        "provider": preferred_provider or "unknown",
                        "outcome": "success"
                    })
            
            elif capability == MediaUnderstandingCapability.AUDIO:
                result = await self._process_audio(
                    buffer, attachment, context, preferred_provider
                )
                if result:
                    outputs.append(result)
                    attempts.append({
                        "provider": preferred_provider or "unknown",
                        "outcome": "success"
                    })
            
            elif capability == MediaUnderstandingCapability.VIDEO:
                result = await self._process_video(
                    buffer, attachment, context, preferred_provider
                )
                if result:
                    outputs.append(result)
                    attempts.append({
                        "provider": preferred_provider or "unknown",
                        "outcome": "success"
                    })
            
            elif capability == MediaUnderstandingCapability.DOCUMENT:
                result = await self._process_document(
                    buffer, attachment, context, preferred_provider
                )
                if result:
                    outputs.append(result)
                    attempts.append({
                        "provider": preferred_provider or "unknown",
                        "outcome": "success"
                    })
            
            decision = {
                "attachment_index": attachment.index,
                "attempts": attempts,
                "chosen": attempts[0] if attempts else None
            }
            
            return {
                "outputs": outputs,
                "decisions": [decision]
            }
            
        except Exception as e:
            print(f"Processing attachment {attachment.index} failed: {e}")
            return None
    
    async def _process_image(
        self,
        buffer: bytes,
        attachment: MediaAttachment,
        context: MediaUnderstandingContext,
        preferred_provider: Optional[str]
    ) -> Optional[MediaUnderstandingOutput]:
        """处理图像"""
        try:
            request = ImageDescriptionRequest(
                buffer=buffer,
                file_name=attachment.path or f"image_{attachment.index}",
                mime=attachment.mime,
                model="gpt-4-vision-preview",  # 默认模型
                provider=preferred_provider or "openai",
                prompt=context.config.image_config.get("prompt")
            )
            
            result = await describe_image(request, preferred_provider)
            
            return MediaUnderstandingOutput(
                kind=MediaUnderstandingKind.IMAGE_DESCRIPTION,
                attachment_index=attachment.index,
                text=result.text,
                provider=result.model or "image_provider",
                model=result.model,
                confidence=result.confidence
            )
            
        except Exception as e:
            print(f"Image processing failed: {e}")
            return None
    
    async def _process_audio(
        self,
        buffer: bytes,
        attachment: MediaAttachment,
        context: MediaUnderstandingContext,
        preferred_provider: Optional[str]
    ) -> Optional[MediaUnderstandingOutput]:
        """处理音频"""
        try:
            request = AudioTranscriptionRequest(
                buffer=buffer,
                file_name=attachment.path or f"audio_{attachment.index}",
                mime=attachment.mime,
                model="whisper-1",
                prompt=context.config.audio_config.get("prompt"),
                language=context.config.audio_config.get("language")
            )
            
            result = await transcribe_audio(request, preferred_provider)
            
            return MediaUnderstandingOutput(
                kind=MediaUnderstandingKind.AUDIO_TRANSCRIPTION,
                attachment_index=attachment.index,
                text=result.text,
                provider="audio_provider",
                model=result.model,
                confidence=result.confidence
            )
            
        except Exception as e:
            print(f"Audio processing failed: {e}")
            return None
    
    async def _process_video(
        self,
        buffer: bytes,
        attachment: MediaAttachment,
        context: MediaUnderstandingContext,
        preferred_provider: Optional[str]
    ) -> Optional[MediaUnderstandingOutput]:
        """处理视频"""
        try:
            request = VideoDescriptionRequest(
                buffer=buffer,
                file_name=attachment.path or f"video_{attachment.index}",
                mime=attachment.mime,
                model="gemini-pro-vision",
                prompt=context.config.video_config.get("prompt")
            )
            
            result = await describe_video(request, preferred_provider)
            
            return MediaUnderstandingOutput(
                kind=MediaUnderstandingKind.VIDEO_DESCRIPTION,
                attachment_index=attachment.index,
                text=result.text,
                provider="video_provider",
                model=result.model
            )
            
        except Exception as e:
            print(f"Video processing failed: {e}")
            return None
    
    async def _process_document(
        self,
        buffer: bytes,
        attachment: MediaAttachment,
        context: MediaUnderstandingContext,
        preferred_provider: Optional[str]
    ) -> Optional[MediaUnderstandingOutput]:
        """处理文档"""
        try:
            request = DocumentExtractionRequest(
                buffer=buffer,
                file_name=attachment.path or f"document_{attachment.index}",
                mime=attachment.mime,
                extract_text=True,
                extract_tables=context.config.document_config.get("extract_tables", True),
                extract_images=context.config.document_config.get("extract_images", False)
            )
            
            result = await extract_document_content(request, preferred_provider)
            
            return MediaUnderstandingOutput(
                kind=MediaUnderstandingKind.DOCUMENT_EXTRACTION,
                attachment_index=attachment.index,
                text=result.text,
                provider="document_provider",
                model="local_extractor"
            )
            
        except Exception as e:
            print(f"Document processing failed: {e}")
            return None
    
    def _filter_attachments_by_capability(
        self,
        attachments: List[MediaAttachment],
        capability: MediaUnderstandingCapability
    ) -> List[MediaAttachment]:
        """根据能力筛选附件"""
        filtered = []
        
        for attachment in attachments:
            media_type = detect_media_type(attachment)
            
            # 更新统计
            self.stats["by_type"][media_type.value] += 1
            
            # 检查媒体类型是否匹配
            if capability == MediaUnderstandingCapability.IMAGE and media_type == MediaType.IMAGE:
                filtered.append(attachment)
            elif capability == MediaUnderstandingCapability.AUDIO and media_type == MediaType.AUDIO:
                filtered.append(attachment)
            elif capability == MediaUnderstandingCapability.VIDEO and media_type == MediaType.VIDEO:
                filtered.append(attachment)
            elif capability == MediaUnderstandingCapability.DOCUMENT and media_type == MediaType.DOCUMENT:
                filtered.append(attachment)
        
        return filtered
    
    def _is_capability_enabled(
        self,
        capability: MediaUnderstandingCapability,
        context: MediaUnderstandingContext
    ) -> bool:
        """检查能力是否启用"""
        config = context.config
        
        if capability == MediaUnderstandingCapability.IMAGE:
            return config.image_config.get("enabled", True)
        elif capability == MediaUnderstandingCapability.AUDIO:
            return config.audio_config.get("enabled", True)
        elif capability == MediaUnderstandingCapability.VIDEO:
            return config.video_config.get("enabled", True)
        elif capability == MediaUnderstandingCapability.DOCUMENT:
            return config.document_config.get("enabled", True)
        
        return True
    
    async def _read_attachment_buffer(self, attachment: MediaAttachment) -> Optional[bytes]:
        """读取附件数据"""
        try:
            if attachment.path:
                # 从文件路径读取
                with open(attachment.path, 'rb') as f:
                    return f.read()
            elif attachment.url:
                # 从URL读取（需要实现）
                # 这里应该实现HTTP请求逻辑
                return None
            else:
                return None
                
        except Exception as e:
            print(f"Failed to read attachment {attachment.index}: {e}")
            return None
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "by_type": {
                MediaType.IMAGE.value: 0,
                MediaType.AUDIO.value: 0,
                MediaType.VIDEO.value: 0,
                MediaType.DOCUMENT.value: 0,
                MediaType.UNKNOWN.value: 0
            },
            "by_capability": {
                capability.value: 0 for capability in MediaUnderstandingCapability
            }
        }


# 全局系统实例
_media_system = MediaUnderstandingSystem()


def get_media_understanding_system() -> MediaUnderstandingSystem:
    """获取全局媒体理解系统实例"""
    return _media_system


async def understand_media(
    context: MediaUnderstandingContext,
    preferred_providers: Optional[Dict[str, str]] = None
) -> MediaUnderstandingResult:
    """理解媒体内容（便捷函数）"""
    return await _media_system.understand_media(context, preferred_providers)


def register_provider(provider_type: str, provider):
    """注册Provider（便捷函数）"""
    _media_system.register_provider(provider_type, provider)


def get_system_info() -> Dict[str, Any]:
    """获取系统信息（便捷函数）"""
    return _media_system.get_system_info()