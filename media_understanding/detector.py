"""
媒体类型检测模块

检测媒体文件的类型，包括图像、音频、视频和文档类型
"""

import mimetypes
import magic
import os
from pathlib import Path
from typing import Optional, Dict, Any
import hashlib
import json

from .types import MediaType, MediaAttachment


class MediaDetector:
    """媒体类型检测器"""
    
    # 支持的MIME类型映射
    SUPPORTED_MIMES = {
        # 图像类型
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 
        'image/webp', 'image/bmp', 'image/tiff', 'image/svg+xml',
        
        # 音频类型
        'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg',
        'audio/aac', 'audio/flac', 'audio/m4a', 'audio/webm',
        
        # 视频类型
        'video/mp4', 'video/avi', 'video/mov', 'video/wmv',
        'video/flv', 'video/webm', 'video/mkv', 'video/m4v',
        
        # 文档类型
        'application/pdf', 'text/plain', 'text/markdown',
        'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/json', 'text/csv', 'text/xml', 'application/xml',
    }
    
    # 文件扩展名映射
    EXTENSION_MIMES = {
        # 图像扩展名
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
        '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp',
        '.tiff': 'image/tiff', '.tif': 'image/tiff', '.svg': 'image/svg+xml',
        
        # 音频扩展名
        '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg',
        '.aac': 'audio/aac', '.flac': 'audio/flac', '.m4a': 'audio/mp4',
        '.webm': 'audio/webm',
        
        # 视频扩展名
        '.mp4': 'video/mp4', '.avi': 'video/avi', '.mov': 'video/quicktime',
        '.wmv': 'video/x-ms-wmv', '.flv': 'video/x-flv', '.webm': 'video/webm',
        '.mkv': 'video/x-matroska', '.m4v': 'video/x-m4v',
        
        # 文档扩展名
        '.pdf': 'application/pdf', '.txt': 'text/plain', '.md': 'text/markdown',
        '.doc': 'application/msword', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel', '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint', '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.json': 'application/json', '.csv': 'text/csv', '.xml': 'text/xml',
    }
    
    # 图像文件签名
    IMAGE_SIGNATURES = {
        b'\xff\xd8\xff': 'image/jpeg',  # JPEG
        b'\x89PNG\r\n\x1a\n': 'image/png',  # PNG
        b'GIF87a': 'image/gif',  # GIF87a
        b'GIF89a': 'image/gif',  # GIF89a
        b'RIFF': 'image/webp',   # WEBP
        b'BM': 'image/bmp',      # BMP
        b'II*\x00': 'image/tiff', # TIFF little-endian
        b'MM\x00*': 'image/tiff', # TIFF big-endian
    }
    
    # 音频文件签名
    AUDIO_SIGNATURES = {
        b'ID3': 'audio/mpeg',  # MP3 with ID3
        b'RIFF': 'audio/wav',  # WAV
        b'OggS': 'audio/ogg',  # OGG
        b'fLaC': 'audio/flac', # FLAC
        b'ftypM4A': 'audio/mp4', # M4A
    }
    
    # 视频文件签名
    VIDEO_SIGNATURES = {
        b'ftypmp4': 'video/mp4',  # MP4
        b'ftypM4A': 'video/mp4',  # MP4
        b'RIFF': 'video/avi',      # AVI
        b'ftypisom': 'video/mp4', # MP4
    }
    
    def __init__(self):
        """初始化检测器"""
        self._magic = None
        self._init_magic()
    
    def _init_magic(self):
        """初始化python-magic库"""
        try:
            self._magic = magic.Magic(mime=True)
        except Exception:
            # 如果无法加载magic，使用mimetypes作为fallback
            self._magic = None
    
    def detect_media_type(self, attachment: MediaAttachment) -> MediaType:
        """检测媒体类型
        
        Args:
            attachment: 媒体附件
            
        Returns:
            MediaType: 检测到的媒体类型
        """
        # 首先尝试从MIME类型判断
        mime_type = self._detect_mime_type(attachment)
        if mime_type:
            return self._mime_to_media_type(mime_type)
        
        # 如果无法检测MIME类型，尝试从扩展名判断
        file_extension = self._get_file_extension(attachment)
        if file_extension:
            mime_type = self.EXTENSION_MIMES.get(file_extension.lower())
            if mime_type:
                return self._mime_to_media_type(mime_type)
        
        # 默认返回未知类型
        return MediaType.UNKNOWN
    
    def _detect_mime_type(self, attachment: MediaAttachment) -> Optional[str]:
        """检测MIME类型"""
        # 1. 优先使用attachment中提供的mime类型
        if attachment.mime:
            return attachment.mime
        
        # 2. 尝试从URL检测
        if attachment.url:
            return self._detect_mime_from_url(attachment.url)
        
        # 3. 尝试从路径检测
        if attachment.path:
            return self._detect_mime_from_path(attachment.path)
        
        return None
    
    def _detect_mime_from_url(self, url: str) -> Optional[str]:
        """从URL检测MIME类型"""
        try:
            # 尝试从URL路径提取扩展名
            parsed_url = url.split('?')[0]  # 移除查询参数
            path = Path(parsed_url)
            extension = path.suffix.lower()
            return self.EXTENSION_MIMES.get(extension)
        except Exception:
            return None
    
    def _detect_mime_from_path(self, file_path: str) -> Optional[str]:
        """从文件路径检测MIME类型"""
        try:
            # 首先尝试使用python-magic
            if self._magic:
                mime_type = self._magic.from_file(file_path)
                return mime_type
            
            # 使用mimetypes模块
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type:
                return mime_type
            
            # 从扩展名推断
            extension = Path(file_path).suffix.lower()
            return self.EXTENSION_MIMES.get(extension)
            
        except Exception:
            return None
    
    def _get_file_extension(self, attachment: MediaAttachment) -> Optional[str]:
        """获取文件扩展名"""
        if attachment.path:
            return Path(attachment.path).suffix
        elif attachment.url:
            url_path = attachment.url.split('?')[0]  # 移除查询参数
            return Path(url_path).suffix
        return None
    
    def _mime_to_media_type(self, mime_type: str) -> MediaType:
        """将MIME类型转换为媒体类型"""
        if mime_type.startswith('image/'):
            return MediaType.IMAGE
        elif mime_type.startswith('audio/'):
            return MediaType.AUDIO
        elif mime_type.startswith('video/'):
            return MediaType.VIDEO
        elif mime_type in ['application/pdf', 'text/plain', 'text/markdown'] or \
             mime_type.startswith('application/msword') or \
             mime_type.startswith('application/vnd.openxmlformats-officedocument') or \
             mime_type.startswith('application/vnd.ms-') or \
             mime_type in ['application/json', 'text/csv', 'text/xml']:
            return MediaType.DOCUMENT
        else:
            return MediaType.UNKNOWN
    
    def is_supported_media(self, attachment: MediaAttachment) -> bool:
        """检查是否支持该媒体类型"""
        media_type = self.detect_media_type(attachment)
        return media_type != MediaType.UNKNOWN
    
    def get_supported_mime_types(self) -> Dict[str, MediaType]:
        """获取支持的MIME类型映射"""
        mime_map = {}
        for mime in self.SUPPORTED_MIMES:
            media_type = self._mime_to_media_type(mime)
            if media_type != MediaType.UNKNOWN:
                mime_map[mime] = media_type
        return mime_map
    
    def detect_media_signature(self, buffer: bytes) -> Optional[str]:
        """通过文件签名检测MIME类型"""
        # 检查图像签名
        for signature, mime_type in self.IMAGE_SIGNATURES.items():
            if buffer.startswith(signature):
                return mime_type
        
        # 检查音频签名
        for signature, mime_type in self.AUDIO_SIGNATURES.items():
            if buffer.startswith(signature):
                return mime_type
        
        # 检查视频签名
        for signature, mime_type in self.VIDEO_SIGNATURES.items():
            if buffer.startswith(signature):
                return mime_type
        
        return None
    
    def get_media_info(self, attachment: MediaAttachment) -> Dict[str, Any]:
        """获取媒体文件详细信息"""
        info = {
            'type': self.detect_media_type(attachment),
            'mime_type': self._detect_mime_type(attachment),
            'file_extension': self._get_file_extension(attachment),
            'is_supported': self.is_supported_media(attachment),
            'file_hash': None,
            'file_size': None,
        }
        
        # 如果有路径，尝试获取文件信息
        if attachment.path and os.path.exists(attachment.path):
            try:
                stat = os.stat(attachment.path)
                info['file_size'] = stat.st_size
                info['file_hash'] = self._calculate_file_hash(attachment.path)
            except Exception:
                pass
        
        return info
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件MD5哈希值"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return None


# 全局检测器实例
_detector = MediaDetector()


def detect_media_type(attachment: MediaAttachment) -> MediaType:
    """检测媒体类型"""
    return _detector.detect_media_type(attachment)


def is_supported_media(attachment: MediaAttachment) -> bool:
    """检查是否支持该媒体类型"""
    return _detector.is_supported_media(attachment)


def get_media_info(attachment: MediaAttachment) -> Dict[str, Any]:
    """获取媒体文件详细信息"""
    return _detector.get_media_info(attachment)


def get_supported_mime_types() -> Dict[str, MediaType]:
    """获取支持的MIME类型映射"""
    return _detector.get_supported_mime_types()