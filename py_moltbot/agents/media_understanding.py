"""
媒体理解模块
Media Understanding Module

分析和理解图像、音频、视频等多媒体内容
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import asyncio
import io
import base64
import hashlib
import mimetypes
from pathlib import Path

import aiohttp
from PIL import Image
import numpy as np

from ..core.logger import get_logger
from ..core.config import settings

logger = get_logger(__name__)


class MediaType(Enum):
    """媒体类型枚举"""
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    ANIMATION = "animation"
    UNKNOWN = "unknown"


class MediaFormat(Enum):
    """媒体格式枚举"""
    # 图像格式
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"
    BMP = "bmp"
    TIFF = "tiff"
    SVG = "svg"
    
    # 音频格式
    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    AAC = "aac"
    OGG = "ogg"
    M4A = "m4a"
    
    # 视频格式
    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    MKV = "mkv"
    WEBM = "webm"
    FLV = "flv"
    
    # 文档格式
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"
    MARKDOWN = "markdown"
    
    UNKNOWN = "unknown"


class ContentCategory(Enum):
    """内容分类枚举"""
    PERSON = "person"
    LANDSCAPE = "landscape"
    CITYSCAPE = "cityscape"
    NATURE = "nature"
    ANIMAL = "animal"
    FOOD = "food"
    TECHNOLOGY = "technology"
    ART = "art"
    SPORTS = "sports"
    VEHICLE = "vehicle"
    BUILDING = "building"
    FLOWER = "flower"
    TEXT = "text"
    GRAPHIC = "graphic"
    DOCUMENT = "document"
    MUSIC = "music"
    SPEECH = "speech"
    NEWS = "news"
    COMMERCIAL = "commercial"
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"
    UNKNOWN = "unknown"


@dataclass
class MediaMetadata:
    """媒体元数据"""
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    media_type: MediaType = MediaType.UNKNOWN
    format: MediaFormat = MediaFormat.UNKNOWN
    
    # 文件信息
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    
    # 技术信息
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None  # 秒
    frame_rate: Optional[float] = None
    bitrate: Optional[int] = None
    codec: Optional[str] = None
    
    # 质量指标
    resolution: Optional[str] = None
    quality_score: Optional[float] = None
    compression_ratio: Optional[float] = None
    
    # 颜色信息（针对图像）
    dominant_colors: List[str] = field(default_factory=list)
    color_palette: List[str] = field(default_factory=list)
    
    # 音频信息
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    bit_depth: Optional[int] = None
    
    # 文档信息
    page_count: Optional[int] = None
    language: Optional[str] = None
    
    # 自定义元数据
    custom_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentAnalysis:
    """内容分析结果"""
    media_type: MediaType
    metadata: MediaMetadata
    
    # 基础分析
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    # 内容分类
    primary_category: Optional[ContentCategory] = None
    secondary_categories: List[ContentCategory] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    
    # 对象检测（针对图像/视频）
    objects: List[Dict[str, Any]] = field(default_factory=list)
    faces: List[Dict[str, Any]] = field(default_factory=list)
    text_regions: List[Dict[str, Any]] = field(default_factory=list)
    
    # 情感分析
    sentiment: Optional[Dict[str, float]] = None
    emotions: List[str] = field(default_factory=list)
    mood: Optional[str] = None
    
    # 语义分析
    themes: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    
    # 安全分析
    safety_score: float = 1.0
    inappropriate_content: List[str] = field(default_factory=list)
    violence_score: float = 0.0
    adult_content_score: float = 0.0
    
    # 质量评估
    clarity_score: float = 0.0
    aesthetic_score: float = 0.0
    technical_quality: float = 0.0
    
    # 处理信息
    processed_at: datetime = field(default_factory=datetime.now)
    processing_time: float = 0.0
    model_used: Optional[str] = None
    confidence_level: float = 0.0


class MediaClassifier:
    """媒体分类器"""
    
    @staticmethod
    def classify_media_type(file_path: str = None, file_url: str = None, content_type: str = None) -> MediaType:
        """分类媒体类型"""
        source = file_path or file_url
        
        if not source and not content_type:
            return MediaType.UNKNOWN
        
        # 基于MIME类型
        if content_type:
            if content_type.startswith('image/'):
                return MediaType.IMAGE
            elif content_type.startswith('audio/'):
                return MediaType.AUDIO
            elif content_type.startswith('video/'):
                return MediaType.VIDEO
            elif content_type in ['application/pdf', 'text/plain', 'text/html']:
                return MediaType.DOCUMENT
            elif content_type == 'image/gif':
                return MediaType.ANIMATION
        
        # 基于文件扩展名
        if source:
            source_lower = source.lower()
            
            # 图像扩展名
            image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg']
            if any(source_lower.endswith(ext) for ext in image_exts):
                if source_lower.endswith('.gif'):
                    return MediaType.ANIMATION
                return MediaType.IMAGE
            
            # 音频扩展名
            audio_exts = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma']
            if any(source_lower.endswith(ext) for ext in audio_exts):
                return MediaType.AUDIO
            
            # 视频扩展名
            video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
            if any(source_lower.endswith(ext) for ext in video_exts):
                return MediaType.VIDEO
            
            # 文档扩展名
            doc_exts = ['.pdf', '.doc', '.docx', '.txt', '.html', '.md', '.rtf']
            if any(source_lower.endswith(ext) for ext in doc_exts):
                return MediaType.DOCUMENT
        
        return MediaType.UNKNOWN
    
    @staticmethod
    def detect_format(file_path: str = None, file_url: str = None, content_type: str = None) -> MediaFormat:
        """检测媒体格式"""
        source = file_path or file_url
        
        if not source and not content_type:
            return MediaFormat.UNKNOWN
        
        # 基于MIME类型
        if content_type:
            mime_to_format = {
                'image/jpeg': MediaFormat.JPEG,
                'image/png': MediaFormat.PNG,
                'image/gif': MediaFormat.GIF,
                'image/webp': MediaFormat.WEBP,
                'audio/mp3': MediaFormat.MP3,
                'audio/wav': MediaFormat.WAV,
                'audio/flac': MediaFormat.FLAC,
                'video/mp4': MediaFormat.MP4,
                'application/pdf': MediaFormat.PDF,
                'text/plain': MediaFormat.TXT,
                'text/html': MediaFormat.HTML
            }
            
            if content_type in mime_to_format:
                return mime_to_format[content_type]
        
        # 基于文件扩展名
        if source:
            source_lower = source.lower()
            format_mapping = {
                '.jpg': MediaFormat.JPEG,
                '.jpeg': MediaFormat.JPEG,
                '.png': MediaFormat.PNG,
                '.gif': MediaFormat.GIF,
                '.webp': MediaFormat.WEBP,
                '.bmp': MediaFormat.BMP,
                '.tiff': MediaFormat.TIFF,
                '.svg': MediaFormat.SVG,
                '.mp3': MediaFormat.MP3,
                '.wav': MediaFormat.WAV,
                '.flac': MediaFormat.FLAC,
                '.aac': MediaFormat.AAC,
                '.ogg': MediaFormat.OGG,
                '.m4a': MediaFormat.M4A,
                '.mp4': MediaFormat.MP4,
                '.avi': MediaFormat.AVI,
                '.mov': MediaFormat.MOV,
                '.mkv': MediaFormat.MKV,
                '.webm': MediaFormat.WEBM,
                '.flv': MediaFormat.FLV,
                '.pdf': MediaFormat.PDF,
                '.doc': MediaFormat.DOC,
                '.docx': MediaFormat.DOCX,
                '.txt': MediaFormat.TXT,
                '.html': MediaFormat.HTML,
                '.md': MediaFormat.MARKDOWN
            }
            
            for ext, format_enum in format_mapping.items():
                if source_lower.endswith(ext):
                    return format_enum
        
        return MediaFormat.UNKNOWN


class ImageAnalyzer:
    """图像分析器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    async def analyze_image(self, image_data: Union[bytes, str, Path]) -> ContentAnalysis:
        """分析图像"""
        start_time = datetime.now()
        
        try:
            # 加载图像
            if isinstance(image_data, str):
                if image_data.startswith(('http://', 'https://')):
                    image_data = await self._download_image(image_data)
                else:
                    image_data = image_data.encode()
            
            if isinstance(image_data, Path):
                image_data = image_data.read_bytes()
            
            # 使用PIL分析基础信息
            pil_image = Image.open(io.BytesIO(image_data))
            
            # 构建元数据
            metadata = MediaMetadata(
                media_type=MediaType.IMAGE,
                format=MediaClassifier.detect_format(content_type=f"image/{pil_image.format.lower()}"),
                width=pil_image.width,
                height=pil_image.height,
                file_size=len(image_data),
                resolution=f"{pil_image.width}x{pil_image.height}"
            )
            
            # 提取颜色信息
            colors = await self._extract_colors(pil_image)
            metadata.dominant_colors = colors['dominant']
            metadata.color_palette = colors['palette']
            
            # 内容分析
            content_analysis = await self._analyze_image_content(pil_image, metadata)
            
            # 组合结果
            analysis = ContentAnalysis(
                media_type=MediaType.IMAGE,
                metadata=metadata,
                **content_analysis
            )
            
            analysis.processing_time = (datetime.now() - start_time).total_seconds()
            
            return analysis
            
        except Exception as e:
            self.logger.error("Image analysis failed", error=str(e))
            return ContentAnalysis(
                media_type=MediaType.IMAGE,
                metadata=MediaMetadata(media_type=MediaType.IMAGE)
            )
    
    async def _download_image(self, url: str) -> bytes:
        """下载图像"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.read()
    
    async def _extract_colors(self, image: Image.Image) -> Dict[str, List[str]]:
        """提取颜色信息"""
        try:
            # 简化颜色提取
            pixels = np.array(image.convert('RGB'))
            pixels_reshaped = pixels.reshape(-1, 3)
            
            # 获取主要颜色（简单实现）
            unique_colors, counts = np.unique(pixels_reshaped, axis=0, return_counts=True)
            top_indices = np.argsort(counts)[-10:]  # 取前10个颜色
            
            colors = []
            for i in top_indices:
                color = unique_colors[i]
                colors.append(f"rgb({color[0]},{color[1]},{color[2]})")
            
            return {
                'dominant': colors[:3],
                'palette': colors
            }
            
        except Exception as e:
            self.logger.error("Color extraction failed", error=str(e))
            return {'dominant': [], 'palette': []}
    
    async def _analyze_image_content(self, image: Image.Image, metadata: MediaMetadata) -> Dict[str, Any]:
        """分析图像内容"""
        # 基础分析
        analysis = {
            'summary': await self._generate_image_summary(image, metadata),
            'description': await self._generate_image_description(image, metadata),
            'tags': await self._extract_image_tags(image, metadata),
            'primary_category': await self._classify_image_category(image, metadata),
            'confidence_scores': {'overall': 0.8}  # 简化置信度
        }
        
        # 对象检测（简化实现）
        objects = await self._detect_objects(image)
        analysis['objects'] = objects
        
        # 文本检测（简化实现）
        text_regions = await self._detect_text_regions(image)
        analysis['text_regions'] = text_regions
        
        # 情感分析
        sentiment = await self._analyze_image_sentiment(image)
        analysis['sentiment'] = sentiment
        
        # 质量评估
        quality_scores = await self._assess_image_quality(image)
        analysis.update(quality_scores)
        
        return analysis
    
    async def _generate_image_summary(self, image: Image.Image, metadata: MediaMetadata) -> str:
        """生成图像摘要"""
        # 基于尺寸和格式的简单摘要
        size_desc = f"{metadata.width}x{metadata.height}像素"
        format_desc = metadata.format.value.upper()
        
        if image.mode == 'RGB':
            color_desc = "彩色"
        elif image.mode == 'L':
            color_desc = "灰度"
        else:
            color_desc = "其他"
        
        return f"这是一张{size_desc}的{color_desc}{format_desc}格式图像"
    
    async def _generate_image_description(self, image: Image.Image, metadata: MediaMetadata) -> str:
        """生成图像描述"""
        # 这里可以集成更复杂的图像理解模型
        # 目前返回简单描述
        return "图像内容分析正在处理中..."
    
    async def _extract_image_tags(self, image: Image.Image, metadata: MediaMetadata) -> List[str]:
        """提取图像标签"""
        tags = []
        
        # 基于格式添加标签
        if metadata.format == MediaFormat.JPEG:
            tags.append('JPEG')
        elif metadata.format == MediaFormat.PNG:
            tags.append('PNG')
        elif metadata.format == MediaFormat.GIF:
            tags.append('动画')
        
        # 基于尺寸添加标签
        if metadata.width and metadata.height:
            if metadata.width > 1920 or metadata.height > 1080:
                tags.append('高分辨率')
            elif metadata.width < 300 or metadata.height < 300:
                tags.append('小尺寸')
        
        # 基于颜色模式添加标签
        if image.mode == 'RGB':
            tags.append('彩色')
        elif image.mode == 'L':
            tags.append('黑白')
        
        return tags
    
    async def _classify_image_category(self, image: Image.Image, metadata: MediaMetadata) -> ContentCategory:
        """分类图像类别"""
        # 简单的分类逻辑
        # 实际实现中应该使用机器学习模型
        
        if metadata.width and metadata.height:
            # 宽高比判断
            ratio = metadata.width / metadata.height if metadata.height > 0 else 1
            
            if ratio > 1.5:
                return ContentCategory.LANDSCAPE
            elif ratio < 0.8:
                return ContentCategory.PORTRAIT if '人' in str(metadata) else ContentCategory.DOCUMENT
            else:
                return ContentCategory.UNKNOWN
        
        return ContentCategory.UNKNOWN
    
    async def _detect_objects(self, image: Image.Image) -> List[Dict[str, Any]]:
        """检测对象"""
        # 这里应该集成目标检测模型
        # 目前返回空列表
        return []
    
    async def _detect_text_regions(self, image: Image.Image) -> List[Dict[str, Any]]:
        """检测文本区域"""
        # 这里应该集成OCR技术
        # 目前返回空列表
        return []
    
    async def _analyze_image_sentiment(self, image: Image.Image) -> Dict[str, float]:
        """分析图像情感"""
        # 简单的情感分析
        # 实际实现中应该使用专门的模型
        return {
            'positive': 0.5,
            'negative': 0.3,
            'neutral': 0.2
        }
    
    async def _assess_image_quality(self, image: Image.Image) -> Dict[str, float]:
        """评估图像质量"""
        # 基于图像属性计算质量分数
        quality = {
            'clarity_score': 0.8,  # 清晰度
            'aesthetic_score': 0.7,  # 美观度
            'technical_quality': 0.8  # 技术质量
        }
        
        # 简化计算，实际应该更复杂
        return quality


class AudioAnalyzer:
    """音频分析器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    async def analyze_audio(self, audio_data: Union[bytes, str, Path]) -> ContentAnalysis:
        """分析音频"""
        start_time = datetime.now()
        
        try:
            # 基础元数据
            metadata = MediaMetadata(
                media_type=MediaType.AUDIO,
                format=MediaClassifier.detect_format(content_type="audio/mpeg")  # 简化
            )
            
            # 内容分析
            content_analysis = await self._analyze_audio_content(audio_data, metadata)
            
            # 组合结果
            analysis = ContentAnalysis(
                media_type=MediaType.AUDIO,
                metadata=metadata,
                **content_analysis
            )
            
            analysis.processing_time = (datetime.now() - start_time).total_seconds()
            
            return analysis
            
        except Exception as e:
            self.logger.error("Audio analysis failed", error=str(e))
            return ContentAnalysis(
                media_type=MediaType.AUDIO,
                metadata=MediaMetadata(media_type=MediaType.AUDIO)
            )
    
    async def _analyze_audio_content(self, audio_data: Union[bytes, str, Path], metadata: MediaMetadata) -> Dict[str, Any]:
        """分析音频内容"""
        analysis = {
            'summary': '音频内容分析结果',
            'description': '音频描述信息',
            'tags': ['音频', '声音'],
            'primary_category': ContentCategory.MUSIC,
            'confidence_scores': {'overall': 0.7}
        }
        
        # 情感分析
        sentiment = {
            'happy': 0.4,
            'sad': 0.3,
            'energetic': 0.2,
            'calm': 0.1
        }
        analysis['sentiment'] = sentiment
        analysis['mood'] = 'mixed'
        
        return analysis


class VideoAnalyzer:
    """视频分析器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    async def analyze_video(self, video_data: Union[bytes, str, Path]) -> ContentAnalysis:
        """分析视频"""
        start_time = datetime.now()
        
        try:
            # 基础元数据
            metadata = MediaMetadata(
                media_type=MediaType.VIDEO,
                format=MediaClassifier.detect_format(content_type="video/mp4")  # 简化
            )
            
            # 内容分析
            content_analysis = await self._analyze_video_content(video_data, metadata)
            
            # 组合结果
            analysis = ContentAnalysis(
                media_type=MediaType.VIDEO,
                metadata=metadata,
                **content_analysis
            )
            
            analysis.processing_time = (datetime.now() - start_time).total_seconds()
            
            return analysis
            
        except Exception as e:
            self.logger.error("Video analysis failed", error=str(e))
            return ContentAnalysis(
                media_type=MediaType.VIDEO,
                metadata=MediaMetadata(media_type=MediaType.VIDEO)
            )
    
    async def _analyze_video_content(self, video_data: Union[bytes, str, Path], metadata: MediaMetadata) -> Dict[str, Any]:
        """分析视频内容"""
        analysis = {
            'summary': '视频内容分析结果',
            'description': '视频描述信息',
            'tags': ['视频', '多媒体'],
            'primary_category': ContentCategory.ENTERTAINMENT,
            'confidence_scores': {'overall': 0.6}
        }
        
        # 情感分析
        sentiment = {
            'positive': 0.5,
            'negative': 0.2,
            'neutral': 0.3
        }
        analysis['sentiment'] = sentiment
        
        return analysis


class DocumentAnalyzer:
    """文档分析器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    async def analyze_document(self, document_data: Union[bytes, str, Path]) -> ContentAnalysis:
        """分析文档"""
        start_time = datetime.now()
        
        try:
            # 基础元数据
            metadata = MediaMetadata(
                media_type=MediaType.DOCUMENT,
                format=MediaClassifier.detect_format(content_type="text/plain")  # 简化
            )
            
            # 内容分析
            content_analysis = await self._analyze_document_content(document_data, metadata)
            
            # 组合结果
            analysis = ContentAnalysis(
                media_type=MediaType.DOCUMENT,
                metadata=metadata,
                **content_analysis
            )
            
            analysis.processing_time = (datetime.now() - start_time).total_seconds()
            
            return analysis
            
        except Exception as e:
            self.logger.error("Document analysis failed", error=str(e))
            return ContentAnalysis(
                media_type=MediaType.DOCUMENT,
                metadata=MediaMetadata(media_type=MediaType.DOCUMENT)
            )
    
    async def _analyze_document_content(self, document_data: Union[bytes, str, Path], metadata: MediaMetadata) -> Dict[str, Any]:
        """分析文档内容"""
        # 提取文本内容
        if isinstance(document_data, str):
            if document_data.startswith(('http://', 'https://')):
                text_content = await self._download_document(document_data)
            else:
                text_content = document_data
        elif isinstance(document_data, Path):
            text_content = document_data.read_text(encoding='utf-8')
        else:
            text_content = document_data.decode('utf-8')
        
        analysis = {
            'summary': await self._generate_document_summary(text_content),
            'description': '文档内容分析',
            'tags': await self._extract_document_tags(text_content),
            'keywords': await self._extract_keywords(text_content),
            'primary_category': ContentCategory.DOCUMENT,
            'confidence_scores': {'overall': 0.8}
        }
        
        # 情感分析
        sentiment = await self._analyze_document_sentiment(text_content)
        analysis['sentiment'] = sentiment
        
        return analysis
    
    async def _download_document(self, url: str) -> str:
        """下载文档"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()
    
    async def _generate_document_summary(self, text_content: str) -> str:
        """生成文档摘要"""
        # 简单摘要：取前200个字符
        return text_content[:200] + "..." if len(text_content) > 200 else text_content
    
    async def _extract_document_tags(self, text_content: str) -> List[str]:
        """提取文档标签"""
        # 简单的关键词提取
        tags = []
        
        # 检查常见关键词
        keywords = {
            'news': ['news', 'report', 'breaking', 'latest'],
            'technical': ['api', 'code', 'programming', 'software'],
            'business': ['business', 'market', 'finance', 'economy'],
            'education': ['education', 'learning', 'course', 'study']
        }
        
        text_lower = text_content.lower()
        for tag, tag_keywords in keywords.items():
            if any(kw in text_lower for kw in tag_keywords):
                tags.append(tag)
        
        return tags
    
    async def _extract_keywords(self, text_content: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        import re
        
        # 移除标点符号并分词
        words = re.findall(r'\b\w+\b', text_content.lower())
        
        # 过滤停用词
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        
        # 统计词频并取前10个
        from collections import Counter
        word_counts = Counter(keywords)
        return [word for word, count in word_counts.most_common(10)]
    
    async def _analyze_document_sentiment(self, text_content: str) -> Dict[str, float]:
        """分析文档情感"""
        # 简单的情感分析
        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic']
        negative_words = ['bad', 'terrible', 'awful', 'horrible', 'disgusting', 'hate']
        
        text_lower = text_content.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            return {'positive': 0.33, 'negative': 0.33, 'neutral': 0.34}
        
        return {
            'positive': positive_count / total_sentiment_words,
            'negative': negative_count / total_sentiment_words,
            'neutral': 1 - (positive_count + negative_count) / total_sentiment_words
        }


class MediaUnderstandingService:
    """媒体理解服务"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.image_analyzer = ImageAnalyzer()
        self.audio_analyzer = AudioAnalyzer()
        self.video_analyzer = VideoAnalyzer()
        self.document_analyzer = DocumentAnalyzer()
    
    async def analyze_media(self, media_data: Union[bytes, str, Path]) -> ContentAnalysis:
        """分析媒体内容"""
        try:
            # 检测媒体类型
            media_type = MediaClassifier.classify_media_type(file_path=str(media_data) if isinstance(media_data, Path) else None)
            
            # 根据类型调用相应的分析器
            if media_type == MediaType.IMAGE:
                return await self.image_analyzer.analyze_image(media_data)
            elif media_type == MediaType.AUDIO:
                return await self.audio_analyzer.analyze_audio(media_data)
            elif media_type == MediaType.VIDEO:
                return await self.video_analyzer.analyze_video(media_data)
            elif media_type == MediaType.DOCUMENT:
                return await self.document_analyzer.analyze_document(media_data)
            else:
                return ContentAnalysis(
                    media_type=MediaType.UNKNOWN,
                    metadata=MediaMetadata(media_type=MediaType.UNKNOWN)
                )
                
        except Exception as e:
            self.logger.error("Media analysis failed", error=str(e))
            return ContentAnalysis(
                media_type=MediaType.UNKNOWN,
                metadata=MediaMetadata(media_type=MediaType.UNKNOWN)
            )
    
    async def batch_analyze_media(self, media_list: List[Union[bytes, str, Path]]) -> List[ContentAnalysis]:
        """批量分析媒体"""
        tasks = [self.analyze_media(media) for media in media_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error("Batch media analysis failed", index=i, error=str(result))
                processed_results.append(ContentAnalysis(
                    media_type=MediaType.UNKNOWN,
                    metadata=MediaMetadata(media_type=MediaType.UNKNOWN)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def analyze_image_url(self, image_url: str) -> ContentAnalysis:
        """分析图像URL"""
        return await self.image_analyzer.analyze_image(image_url)
    
    async def analyze_audio_url(self, audio_url: str) -> ContentAnalysis:
        """分析音频URL"""
        return await self.audio_analyzer.analyze_audio(audio_url)
    
    async def analyze_video_url(self, video_url: str) -> ContentAnalysis:
        """分析视频URL"""
        return await self.video_analyzer.analyze_video(video_url)
    
    def extract_metadata(self, file_path: str) -> MediaMetadata:
        """提取媒体元数据"""
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            return MediaMetadata(file_path=file_path)
        
        # 基础信息
        stat = file_path_obj.stat()
        media_type = MediaClassifier.classify_media_type(file_path=file_path)
        format_type = MediaClassifier.detect_format(file_path=file_path)
        
        metadata = MediaMetadata(
            file_path=file_path,
            media_type=media_type,
            format=format_type,
            file_size=stat.st_size,
            creation_date=datetime.fromtimestamp(stat.st_ctime),
            modification_date=datetime.fromtimestamp(stat.st_mtime)
        )
        
        # 图像特定信息
        if media_type == MediaType.IMAGE:
            try:
                with Image.open(file_path) as img:
                    metadata.width = img.width
                    metadata.height = img.height
            except Exception as e:
                self.logger.error("Failed to extract image metadata", file=file_path, error=str(e))
        
        return metadata


# 全局媒体理解服务
_media_service: Optional[MediaUnderstandingService] = None


def get_media_service() -> MediaUnderstandingService:
    """获取全局媒体理解服务"""
    global _media_service
    if _media_service is None:
        _media_service = MediaUnderstandingService()
    return _media_service


# 便利函数
async def analyze_media_content(media_data: Union[bytes, str, Path]) -> ContentAnalysis:
    """分析媒体内容"""
    service = get_media_service()
    return await service.analyze_media(media_data)


async def analyze_image_content(image_data: Union[bytes, str, Path]) -> ContentAnalysis:
    """分析图像内容"""
    service = get_media_service()
    return await service.image_analyzer.analyze_image(image_data)


async def analyze_audio_content(audio_data: Union[bytes, str, Path]) -> ContentAnalysis:
    """分析音频内容"""
    service = get_media_service()
    return await service.audio_analyzer.analyze_audio(audio_data)


async def analyze_video_content(video_data: Union[bytes, str, Path]) -> ContentAnalysis:
    """分析视频内容"""
    service = get_media_service()
    return await service.video_analyzer.analyze_video(video_data)


async def batch_analyze_media_files(media_list: List[Union[bytes, str, Path]]) -> List[ContentAnalysis]:
    """批量分析媒体文件"""
    service = get_media_service()
    return await service.batch_analyze_media(media_list)