"""
媒体处理

处理消息中的媒体附件，包括：
- 媒体文件格式化
- 媒体类型识别
- 媒体路径处理
- 媒体理解结果处理
"""

from typing import Optional, List, Dict, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import mimetypes
import os.path


class MediaType(Enum):
    """媒体类型"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


@dataclass
class MediaAttachment:
    """媒体附件"""
    path: str
    url: Optional[str] = None
    media_type: Optional[MediaType] = None
    mime_type: Optional[str] = None
    size: Optional[int] = None
    filename: Optional[str] = None
    index: Optional[int] = None


@dataclass
class MediaUnderstanding:
    """媒体理解结果"""
    attachment_index: int
    outcome: str  # "success", "failed", "skipped"
    description: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = None


@dataclass
class MediaUnderstandingDecision:
    """媒体理解决策"""
    outcome: str
    attachments: List[Dict[str, Any]]


class MediaProcessor:
    """媒体处理器"""
    
    def __init__(self):
        self.supported_types = {
            "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
            "video": [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"],
            "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"],
            "document": [".pdf", ".doc", ".docx", ".txt", ".md", ".json", ".csv"],
        }
    
    def detect_media_type(self, file_path: str) -> MediaType:
        """
        检测媒体类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            媒体类型
        """
        if not file_path:
            return MediaType.UNKNOWN
        
        extension = os.path.splitext(file_path.lower())[1]
        
        for media_type, extensions in self.supported_types.items():
            if extension in extensions:
                return MediaType(media_type)
        
        # 基于MIME类型检测
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            if mime_type.startswith("image/"):
                return MediaType.IMAGE
            elif mime_type.startswith("video/"):
                return MediaType.VIDEO
            elif mime_type.startswith("audio/"):
                return MediaType.AUDIO
            elif mime_type.startswith("application/"):
                return MediaType.DOCUMENT
        
        return MediaType.UNKNOWN
    
    def format_media_attached_line(self, attachment: MediaAttachment) -> str:
        """
        格式化媒体附件行
        
        Args:
            attachment: 媒体附件
            
        Returns:
            格式化的附件行
        """
        parts = ["[media attached"]
        
        if attachment.index is not None:
            parts.append(f"{attachment.index}")
        
        parts.append(":")
        parts.append(attachment.path or "")
        
        if attachment.media_type:
            parts.append(f"({attachment.media_type.value})")
        
        if attachment.url:
            parts.append(f"| {attachment.url}")
        
        parts.append("]")
        
        return " ".join(parts)
    
    def process_media_attachments(
        self,
        media_paths: Optional[List[str]] = None,
        media_urls: Optional[List[str]] = None,
        media_types: Optional[List[str]] = None,
        single_media_path: Optional[str] = None,
        single_media_url: Optional[str] = None,
        single_media_type: Optional[str] = None,
    ) -> List[MediaAttachment]:
        """
        处理媒体附件列表
        
        Args:
            media_paths: 媒体路径列表
            media_urls: 媒体URL列表
            media_types: 媒体类型列表
            single_media_path: 单个媒体路径
            single_media_url: 单个媒体URL
            single_media_type: 单个媒体类型
            
        Returns:
            媒体附件列表
        """
        attachments: List[MediaAttachment] = []
        
        # 处理列表形式的媒体
        if media_paths:
            for index, path in enumerate(media_paths):
                attachment = MediaAttachment(
                    path=path or "",
                    url=media_urls[index] if media_urls and index < len(media_urls) else None,
                    media_type=MediaType(media_types[index]) if media_types and index < len(media_types) and media_types[index] else self.detect_media_type(path),
                    index=index,
                )
                attachments.append(attachment)
        
        # 处理单个媒体
        elif single_media_path:
            attachment = MediaAttachment(
                path=single_media_path or "",
                url=single_media_url,
                media_type=MediaType(single_media_type) if single_media_type else self.detect_media_type(single_media_path),
            )
            attachments.append(attachment)
        
        return attachments
    
    def filter_suppressed_attachments(
        self,
        attachments: List[MediaAttachment],
        suppressed_indices: Optional[List[int]] = None,
    ) -> List[MediaAttachment]:
        """
        过滤被抑制的附件
        
        Args:
            attachments: 媒体附件列表
            suppressed_indices: 被抑制的附件索引列表
            
        Returns:
            过滤后的附件列表
        """
        if not suppressed_indices:
            return attachments
        
        suppressed_set = set(suppressed_indices)
        return [
            attachment for attachment in attachments
            if attachment.index is None or attachment.index not in suppressed_set
        ]


def build_inbound_media_note(
    media_paths: Optional[List[str]] = None,
    media_urls: Optional[List[str]] = None,
    media_types: Optional[List[str]] = None,
    media_path: Optional[str] = None,
    media_url: Optional[str] = None,
    media_type: Optional[str] = None,
    media_understanding: Optional[List[Dict[str, Any]]] = None,
    media_understanding_decisions: Optional[List[Dict[str, Any]]] = None,
) -> Optional[str]:
    """
    构建入站媒体备注
    
    Args:
        media_paths: 媒体路径列表
        media_urls: 媒体URL列表
        media_types: 媒体类型列表
        media_path: 单个媒体路径
        media_url: 单个媒体URL
        media_type: 单个媒体类型
        media_understanding: 媒体理解结果列表
        media_understanding_decisions: 媒体理解决策列表
        
    Returns:
        格式化的媒体备注
    """
    processor = MediaProcessor()
    
    # 处理媒体附件
    attachments = processor.process_media_attachments(
        media_paths=media_paths,
        media_urls=media_urls,
        media_types=media_types,
        single_media_path=media_path,
        single_media_url=media_url,
        single_media_type=media_type,
    )
    
    if not attachments:
        return None
    
    # 确定被抑制的附件索引
    suppressed_indices = set()
    
    if media_understanding:
        for understanding in media_understanding:
            if "attachment_index" in understanding:
                suppressed_indices.add(understanding["attachment_index"])
    
    if media_understanding_decisions:
        for decision in media_understanding_decisions:
            if decision.get("outcome") != "success":
                continue
            
            for attachment in decision.get("attachments", []):
                if attachment.get("chosen", {}).get("outcome") != "success":
                    continue
                
                if "attachment_index" in attachment:
                    suppressed_indices.add(attachment["attachment_index"])
    
    # 过滤被抑制的附件
    filtered_attachments = processor.filter_suppressed_attachments(attachments, list(suppressed_indices))
    
    if not filtered_attachments:
        return None
    
    # 格式化附件
    if len(filtered_attachments) == 1:
        attachment = filtered_attachments[0]
        return processor.format_media_attached_line(attachment)
    
    # 多个附件的格式化
    lines = [f"[media attached: {len(filtered_attachments)} files]"]
    
    for index, attachment in enumerate(filtered_attachments):
        attachment.index = index + 1
        attachment_line = processor.format_media_attached_line(attachment)
        lines.append(attachment_line)
    
    return "\n".join(lines)


def extract_media_info(file_path: str) -> Dict[str, Any]:
    """
    提取媒体文件信息
    
    Args:
        file_path: 文件路径
        
    Returns:
        媒体信息字典
    """
    processor = MediaProcessor()
    media_type = processor.detect_media_type(file_path)
    
    info = {
        "path": file_path,
        "media_type": media_type.value,
        "size": None,
        "filename": os.path.basename(file_path) if file_path else None,
        "extension": os.path.splitext(file_path)[1] if file_path else None,
    }
    
    try:
        if file_path and os.path.exists(file_path):
            info["size"] = os.path.getsize(file_path)
    except (OSError, TypeError):
        pass
    
    return info


def is_media_file(file_path: str) -> bool:
    """
    检查是否是媒体文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        是否是媒体文件
    """
    processor = MediaProcessor()
    media_type = processor.detect_media_type(file_path)
    return media_type != MediaType.UNKNOWN


def get_media_summary(attachments: List[MediaAttachment]) -> Dict[str, Any]:
    """
    获取媒体附件摘要
    
    Args:
        attachments: 媒体附件列表
        
    Returns:
        媒体摘要信息
    """
    summary = {
        "total_count": len(attachments),
        "by_type": {},
        "total_size": 0,
        "has_url": False,
    }
    
    for attachment in attachments:
        # 按类型统计
        media_type = attachment.media_type or MediaType.UNKNOWN
        type_name = media_type.value
        summary["by_type"][type_name] = summary["by_type"].get(type_name, 0) + 1
        
        # 统计大小
        if attachment.size:
            summary["total_size"] += attachment.size
        
        # 检查是否有URL
        if attachment.url:
            summary["has_url"] = True
    
    return summary