"""
链接理解模块
Link Understanding Module

解析和理解URL链接的内容和含义
"""

from typing import Dict, List, Optional, Any, Union, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import asyncio
import re
import json
from urllib.parse import urlparse, parse_qs
import hashlib

import aiohttp
from bs4 import BeautifulSoup

from ..core.logger import get_logger
from ..core.config import settings

logger = get_logger(__name__)


class LinkType(Enum):
    """链接类型枚举"""
    WEBPAGE = "webpage"           # 网页
    IMAGE = "image"              # 图片
    VIDEO = "video"             # 视频
    AUDIO = "audio"             # 音频
    DOCUMENT = "document"        # 文档
    API_ENDPOINT = "api_endpoint" # API端点
    SOCIAL_MEDIA = "social_media" # 社交媒体
    NEWS = "news"               # 新闻
    BLOG = "blog"               # 博客
    E_COMMERCE = "ecommerce"    # 电商
    EDUCATIONAL = "educational"  # 教育
    CODE_REPOSITORY = "code_repository" # 代码仓库
    UNKNOWN = "unknown"         # 未知


class ContentType(Enum):
    """内容类型枚举"""
    HTML = "html"
    JSON = "json"
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    PDF = "pdf"
    XML = "xml"
    RSS = "rss"
    UNKNOWN = "unknown"


@dataclass
class LinkMetadata:
    """链接元数据"""
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    author: Optional[str] = None
    publish_date: Optional[datetime] = None
    language: Optional[str] = None
    content_type: ContentType = ContentType.UNKNOWN
    link_type: LinkType = LinkType.UNKNOWN
    domain: Optional[str] = None
    favicon: Optional[str] = None
    canonical_url: Optional[str] = None
    
    # SEO和社交媒体
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    twitter_title: Optional[str] = None
    twitter_description: Optional[str] = None
    twitter_image: Optional[str] = None
    
    # 技术信息
    charset: Optional[str] = None
    content_length: Optional[int] = None
    last_modified: Optional[datetime] = None
    etag: Optional[str] = None
    
    # 提取的结构化数据
    structured_data: Dict[str, Any] = field(default_factory=dict)
    
    # 自定义元数据
    custom_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LinkContent:
    """链接内容"""
    url: str
    content: str
    content_type: ContentType
    metadata: LinkMetadata
    
    # 提取的文本
    text_content: Optional[str] = None
    
    # 提取的链接
    outgoing_links: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)
    
    # 内容分析
    word_count: int = 0
    reading_time_minutes: float = 0.0
    sentiment_score: Optional[float] = None
    
    # 质量评估
    quality_score: float = 0.0
    spam_score: float = 0.0
    freshness_score: float = 0.0
    
    # 提取的结构化信息
    entities: List[Dict[str, Any]] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    emotions: List[str] = field(default_factory=list)


@dataclass
class LinkAnalysis:
    """链接分析结果"""
    url: str
    link_type: LinkType
    content_type: ContentType
    metadata: LinkMetadata
    content: LinkContent
    
    # 分析结果
    summary: Optional[str] = None
    key_points: List[str] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    
    # 相关性分析
    relevance_score: float = 0.0
    category: Optional[str] = None
    subcategory: Optional[str] = None
    
    # 安全和可信度
    trust_score: float = 0.0
    security_flags: List[str] = field(default_factory=list)
    
    # 处理信息
    processed_at: datetime = field(default_factory=datetime.now)
    processing_time: float = 0.0
    cache_key: Optional[str] = None


class LinkClassifier:
    """链接分类器"""
    
    # URL模式匹配规则
    URL_PATTERNS = {
        LinkType.IMAGE: [
            r'\.(jpg|jpeg|png|gif|bmp|svg|webp|ico)$',
            r'/(image|img|picture|photo)/',
            r'/i\.',
            r'/img/',
            r'/\?.*(?:format=image|image=)',
            r'/(?:cdn|static|assets)/.*\.(?:jpg|jpeg|png|gif)',
        ],
        LinkType.VIDEO: [
            r'\.(mp4|avi|mkv|mov|wmv|flv|webm|m4v)$',
            r'/video|vid|clip|movie/',
            r'\.(?:youtube\.com/watch|youtu\.be|vimeo\.com|twitch\.tv)',
            r'/(?:embed|player)/.*\.(?:mp4|webm)',
        ],
        LinkType.AUDIO: [
            r'\.(mp3|wav|flac|aac|ogg|m4a|wma)$',
            r'/audio|sound|music|podcast/',
            r'\.(?:spotify\.com|soundcloud\.com)',
            r'/(?:embed|player)/.*\.(?:mp3|wav)',
        ],
        LinkType.DOCUMENT: [
            r'\.(pdf|doc|docx|xls|xlsx|ppt|pptx|txt|rtf|odt)$',
            r'/document|file|download/',
            r'/(?:docs|files)/',
            r'\.(?:google\.com.*document|office\.com)',
        ],
        LinkType.SOCIAL_MEDIA: [
            r'(?:facebook\.com|twitter\.com|x\.com|instagram\.com|tiktok\.com)',
            r'(?:linkedin\.com|reddit\.com|pinterest\.com)',
            r'/(?:post|share|tweet|status|update)',
        ],
        LinkType.NEWS: [
            r'(?:news|cnn|bbc|reuters|ap|bloomberg|wsj|nytimes)',
            r'(?:newsletter|breaking|latest|report)',
            r'/news|article|story/',
        ],
        LinkType.BLOG: [
            r'/(?:blog|post|article|story|thought|insight)',
            r'\.(?:wordpress\.com|medium\.com|substack\.com)',
        ],
        LinkType.E_COMMERCE: [
            r'(?:amazon|ebay|etsy|shopify|woocommerce)',
            r'(?:cart|checkout|product|item|buy|purchase)',
            r'/(?:shop|store|catalog|price)',
        ],
        LinkType.EDUCATIONAL: [
            r'(?:edu|coursera|udemy|edx|khan|academy)',
            r'(?:course|lesson|tutorial|guide|learn)',
            r'/(?:education|learning|training|class)',
        ],
        LinkType.CODE_REPOSITORY: [
            r'(?:github|gitlab|bitbucket|sourceforge)',
            r'(?:code|repo|repository|source|commit)',
            r'/(?:git|svn|version|branch)',
        ],
        LinkType.API_ENDPOINT: [
            r'/api/v?\d*/',
            r'/(?:rest|graphql|json|xml)/',
            r'/(?:endpoint|service|api)',
            r'/(?:auth|login|token)',
        ],
    }
    
    @classmethod
    def classify_url(cls, url: str) -> LinkType:
        """分类URL"""
        parsed = urlparse(url)
        path = parsed.path.lower()
        query = parsed.query.lower()
        
        # 特殊域名处理
        domain = parsed.netloc.lower()
        
        # 检查预定义域名
        domain_mapping = {
            'youtube.com': LinkType.VIDEO,
            'youtu.be': LinkType.VIDEO,
            'vimeo.com': LinkType.VIDEO,
            'twitch.tv': LinkType.VIDEO,
            'spotify.com': LinkType.AUDIO,
            'soundcloud.com': LinkType.AUDIO,
            'github.com': LinkType.CODE_REPOSITORY,
            'gitlab.com': LinkType.CODE_REPOSITORY,
            'bitbucket.org': LinkType.CODE_REPOSITORY,
            'arxiv.org': LinkType.DOCUMENT,
            'medium.com': LinkType.BLOG,
            'substack.com': LinkType.BLOG,
            'reddit.com': LinkType.SOCIAL_MEDIA,
            'stackoverflow.com': LinkType.EDUCATIONAL,
        }
        
        if domain in domain_mapping:
            return domain_mapping[domain]
        
        # 检查URL模式
        full_url = (path + '?' + query).lower()
        
        for link_type, patterns in cls.URL_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, full_url, re.IGNORECASE):
                    return link_type
        
        return LinkType.UNKNOWN
    
    @classmethod
    def detect_content_type(cls, url: str, content_type_header: str = None) -> ContentType:
        """检测内容类型"""
        if content_type_header:
            if 'text/html' in content_type_header:
                return ContentType.HTML
            elif 'application/json' in content_type_header:
                return ContentType.JSON
            elif 'text/plain' in content_type_header:
                return ContentType.TEXT
            elif 'image/' in content_type_header:
                return ContentType.IMAGE
            elif 'video/' in content_type_header:
                return ContentType.VIDEO
            elif 'audio/' in content_type_header:
                return ContentType.AUDIO
            elif 'application/pdf' in content_type_header:
                return ContentType.PDF
        
        # 从URL推断
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        if any(path.endswith(ext) for ext in ['.html', '.htm']):
            return ContentType.HTML
        elif path.endswith('.json'):
            return ContentType.JSON
        elif path.endswith('.txt'):
            return ContentType.TEXT
        elif any(path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']):
            return ContentType.IMAGE
        elif any(path.endswith(ext) for ext in ['.mp4', '.avi', '.mkv', '.mov']):
            return ContentType.VIDEO
        elif any(path.endswith(ext) for ext in ['.mp3', '.wav', '.flac', '.aac']):
            return ContentType.AUDIO
        elif path.endswith('.pdf'):
            return ContentType.PDF
        elif path.endswith('.xml') or 'rss' in path:
            return ContentType.RSS
        
        return ContentType.UNKNOWN


class LinkExtractor:
    """链接内容提取器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.session = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'MoltBot Link Extractor 1.0'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()
    
    async def extract_link_metadata(self, url: str) -> LinkMetadata:
        """提取链接元数据"""
        try:
            async with self.session.get(url) as response:
                content_type = response.headers.get('content-type', '')
                charset = response.headers.get('charset', 'utf-8')
                
                # 基本信息
                metadata = LinkMetadata(
                    url=url,
                    content_type=LinkClassifier.detect_content_type(url, content_type),
                    link_type=LinkClassifier.classify_url(url),
                    domain=urlparse(url).netloc,
                    charset=charset,
                    content_length=int(response.headers.get('content-length', 0)) or None,
                    etag=response.headers.get('etag')
                )
                
                # 提取HTML元数据
                if metadata.content_type == ContentType.HTML:
                    html_content = await response.text()
                    await self._extract_html_metadata(html_content, metadata)
                
                return metadata
                
        except Exception as e:
            self.logger.error("Failed to extract metadata", 
                            url=url, error=str(e))
            return LinkMetadata(url=url)
    
    async def _extract_html_metadata(self, html: str, metadata: LinkMetadata) -> None:
        """从HTML中提取元数据"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 基本元数据
            title_tag = soup.find('title')
            if title_tag:
                metadata.title = title_tag.get_text().strip()
            
            meta_description = soup.find('meta', attrs={'name': 'description'})
            if meta_description:
                metadata.description = meta_description.get('content', '').strip()
            
            # 关键词
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords:
                keywords_text = meta_keywords.get('content', '')
                metadata.keywords = [k.strip() for k in keywords_text.split(',')]
            
            # Open Graph元数据
            for property in ['og:title', 'og:description', 'og:image', 'og:type']:
                meta_tag = soup.find('meta', attrs={'property': property})
                if meta_tag:
                    value = meta_tag.get('content', '')
                    if property == 'og:title':
                        metadata.og_title = value
                    elif property == 'og:description':
                        metadata.og_description = value
                    elif property == 'og:image':
                        metadata.og_image = value
            
            # Twitter Card元数据
            for name in ['twitter:title', 'twitter:description', 'twitter:image']:
                meta_tag = soup.find('meta', attrs={'name': name})
                if meta_tag:
                    value = meta_tag.get('content', '')
                    if name == 'twitter:title':
                        metadata.twitter_title = value
                    elif name == 'twitter:description':
                        metadata.twitter_description = value
                    elif name == 'twitter:image':
                        metadata.twitter_image = value
            
            # 作者信息
            author_meta = soup.find('meta', attrs={'name': 'author'})
            if author_meta:
                metadata.author = author_meta.get('content', '')
            
            # 发布日期
            date_meta = soup.find('meta', attrs={'property': 'article:published_time'}) or \
                       soup.find('meta', attrs={'name': 'date'}) or \
                       soup.find('time')
            
            if date_meta:
                date_str = date_meta.get('content') or date_meta.get('datetime')
                if date_str:
                    try:
                        metadata.publish_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except:
                        # 尝试其他日期格式
                        from dateutil import parser
                        try:
                            metadata.publish_date = parser.parse(date_str)
                        except:
                            pass
            
            # 规范链接
            canonical_link = soup.find('link', attrs={'rel': 'canonical'})
            if canonical_link:
                metadata.canonical_url = canonical_link.get('href')
            
            # 提取结构化数据
            structured_data = soup.find_all('script', attrs={'type': 'application/ld+json'})
            for script in structured_data:
                try:
                    data = json.loads(script.string)
                    metadata.structured_data.update(data)
                except json.JSONDecodeError:
                    continue
                    
        except Exception as e:
            self.logger.error("Failed to extract HTML metadata", error=str(e))
    
    async def extract_link_content(self, url: str) -> Optional[LinkContent]:
        """提取链接内容"""
        try:
            async with self.session.get(url) as response:
                content_type = response.headers.get('content-type', '')
                metadata = await self.extract_link_metadata(url)
                
                # 根据内容类型处理
                if metadata.content_type == ContentType.HTML:
                    html = await response.text()
                    return await self._extract_html_content(url, html, metadata)
                elif metadata.content_type == ContentType.JSON:
                    json_data = await response.json()
                    return await self._extract_json_content(url, json_data, metadata)
                else:
                    content = await response.text()
                    return LinkContent(
                        url=url,
                        content=content,
                        content_type=metadata.content_type,
                        metadata=metadata,
                        text_content=content
                    )
                    
        except Exception as e:
            self.logger.error("Failed to extract content", url=url, error=str(e))
            return None
    
    async def _extract_html_content(self, url: str, html: str, metadata: LinkMetadata) -> LinkContent:
        """提取HTML内容"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 提取纯文本
        for script in soup(["script", "style"]):
            script.decompose()
        
        text_content = soup.get_text()
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # 提取链接
        outgoing_links = [a.get('href') for a in soup.find_all('a', href=True)]
        outgoing_links = [link for link in outgoing_links if link.startswith('http')]
        
        # 提取媒体
        images = [img.get('src') for img in soup.find_all('img', src=True)]
        images = [img for img in images if img.startswith('http')]
        
        videos = [video.get('src') for video in soup.find_all('video', src=True)]
        videos = [video for video in videos if video.startswith('http')]
        
        # 计算字数
        word_count = len(text_content.split())
        reading_time = word_count / 200  # 假设每分钟阅读200词
        
        return LinkContent(
            url=url,
            content=html,
            content_type=ContentType.HTML,
            metadata=metadata,
            text_content=text_content,
            outgoing_links=outgoing_links,
            images=images,
            videos=videos,
            word_count=word_count,
            reading_time_minutes=reading_time
        )
    
    async def _extract_json_content(self, url: str, json_data: Dict[str, Any], metadata: LinkMetadata) -> LinkContent:
        """提取JSON内容"""
        content_str = json.dumps(json_data, ensure_ascii=False, indent=2)
        
        return LinkContent(
            url=url,
            content=content_str,
            content_type=ContentType.JSON,
            metadata=metadata,
            text_content=content_str
        )


class LinkAnalyzer:
    """链接分析器"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    async def analyze_link(self, url: str, content: LinkContent) -> LinkAnalysis:
        """分析链接"""
        start_time = datetime.now()
        
        try:
            # 基本分类
            link_type = LinkClassifier.classify_url(url)
            
            # 质量评估
            quality_score = await self._assess_quality(content)
            spam_score = await self._assess_spam(content)
            freshness_score = await self._assess_freshness(content.metadata)
            
            # 内容分析
            summary = await self._generate_summary(content)
            key_points = await self._extract_key_points(content)
            entities = await self._extract_entities(content)
            topics = await self._extract_topics(content)
            
            # 相关性和分类
            relevance_score = await self._calculate_relevance(content)
            category, subcategory = await self._categorize_link(url, content)
            
            # 信任度和安全性
            trust_score = await self._assess_trust(content.metadata)
            security_flags = await self._check_security_flags(url, content)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            cache_key = self._generate_cache_key(url, content.metadata)
            
            return LinkAnalysis(
                url=url,
                link_type=link_type,
                content_type=content.content_type,
                metadata=content.metadata,
                content=content,
                summary=summary,
                key_points=key_points,
                entities=entities,
                topics=topics,
                relevance_score=relevance_score,
                category=category,
                subcategory=subcategory,
                trust_score=trust_score,
                security_flags=security_flags,
                quality_score=quality_score,
                spam_score=spam_score,
                freshness_score=freshness_score,
                processing_time=processing_time,
                cache_key=cache_key
            )
            
        except Exception as e:
            self.logger.error("Link analysis failed", url=url, error=str(e))
            return LinkAnalysis(
                url=url,
                link_type=LinkType.UNKNOWN,
                content_type=ContentType.UNKNOWN,
                metadata=content.metadata,
                content=content
            )
    
    async def _assess_quality(self, content: LinkContent) -> float:
        """评估内容质量"""
        score = 0.5  # 基础分
        
        # 字数评估
        if content.word_count > 100:
            score += 0.2
        elif content.word_count < 50:
            score -= 0.2
        
        # 元数据完整性
        if content.metadata.title:
            score += 0.1
        if content.metadata.description:
            score += 0.1
        if content.metadata.keywords:
            score += 0.05
        
        # 结构化数据
        if content.metadata.structured_data:
            score += 0.1
        
        return min(1.0, max(0.0, score))
    
    async def _assess_spam(self, content: LinkContent) -> float:
        """评估垃圾内容概率"""
        spam_indicators = 0
        
        # 过多广告关键词
        spam_keywords = ['click here', 'buy now', 'limited time', 'act now']
        text_lower = content.text_content.lower() if content.text_content else ''
        
        for keyword in spam_keywords:
            if keyword in text_lower:
                spam_indicators += 1
        
        # 过多链接
        if len(content.outgoing_links) > 20:
            spam_indicators += 1
        
        # 缺失重要元数据
        if not content.metadata.title:
            spam_indicators += 1
        if not content.metadata.description:
            spam_indicators += 1
        
        return min(1.0, spam_indicators / 5)
    
    async def _assess_freshness(self, metadata: LinkMetadata) -> float:
        """评估内容新鲜度"""
        if not metadata.publish_date:
            return 0.5  # 未知时间，设为中性
        
        age_days = (datetime.now() - metadata.publish_date).days
        
        if age_days < 1:
            return 1.0
        elif age_days < 7:
            return 0.8
        elif age_days < 30:
            return 0.6
        elif age_days < 365:
            return 0.4
        else:
            return 0.2
    
    async def _generate_summary(self, content: LinkContent) -> Optional[str]:
        """生成摘要"""
        if not content.text_content:
            return None
        
        # 简单的摘要生成：取前150个字符
        text = content.text_content.strip()
        if len(text) <= 150:
            return text
        
        # 在句号处截断
        sentences = text.split('.')
        summary = ''
        for sentence in sentences:
            if len(summary + sentence) <= 150:
                summary += sentence + '.'
            else:
                break
        
        return summary.strip() or text[:150] + '...'
    
    async def _extract_key_points(self, content: LinkContent) -> List[str]:
        """提取关键点"""
        if not content.text_content:
            return []
        
        # 简单的关键点提取：取每段第一句话
        paragraphs = content.text_content.split('\n\n')
        key_points = []
        
        for paragraph in paragraphs[:3]:  # 只取前3段
            sentences = paragraph.split('.')
            if sentences:
                key_point = sentences[0].strip()
                if key_point and len(key_point) > 20:
                    key_points.append(key_point)
        
        return key_points
    
    async def _extract_entities(self, content: LinkContent) -> List[Dict[str, Any]]:
        """提取实体"""
        # 简单的实体提取：人名、地名、组织名
        entities = []
        
        # 这里可以集成命名实体识别库，如spaCy
        # 暂时使用简单的正则表达式
        
        # 人名模式（简单）
        person_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'
        people = re.findall(person_pattern, content.text_content or '')
        for person in set(people):
            entities.append({'type': 'PERSON', 'text': person})
        
        # 地点模式（简单）
        location_pattern = r'\b(?:北京|上海|广州|深圳|杭州|南京|成都|武汉|西安|重庆)\b'
        locations = re.findall(location_pattern, content.text_content or '')
        for location in set(locations):
            entities.append({'type': 'LOCATION', 'text': location})
        
        return entities
    
    async def _extract_topics(self, content: LinkContent) -> List[str]:
        """提取主题"""
        if not content.metadata.keywords:
            return []
        
        # 基于关键词推断主题
        topic_keywords = {
            '科技': ['technology', 'tech', 'digital', 'ai', 'artificial intelligence'],
            '商业': ['business', 'economy', 'market', 'finance', 'investment'],
            '教育': ['education', 'learning', 'course', 'tutorial', 'study'],
            '健康': ['health', 'medical', 'medicine', 'wellness', 'fitness'],
            '娱乐': ['entertainment', 'movie', 'music', 'game', 'fun'],
            '新闻': ['news', 'breaking', 'report', 'journalist', 'media']
        }
        
        text_lower = content.text_content.lower() if content.text_content else ''
        keywords = [k.lower() for k in content.metadata.keywords]
        
        topics = []
        for topic, topic_kws in topic_keywords.items():
            if any(kw in text_lower for kw in topic_kws) or any(kw in keywords for kw in topic_kws):
                topics.append(topic)
        
        return topics
    
    async def _calculate_relevance(self, content: LinkContent) -> float:
        """计算相关性"""
        # 基于内容质量、元数据完整性等计算
        relevance = 0.5
        
        if content.metadata.title:
            relevance += 0.2
        if content.metadata.description:
            relevance += 0.1
        if content.word_count > 100:
            relevance += 0.1
        if content.metadata.keywords:
            relevance += 0.1
        
        return min(1.0, relevance)
    
    async def _categorize_link(self, url: str, content: LinkContent) -> Tuple[Optional[str], Optional[str]]:
        """分类链接"""
        link_type = LinkClassifier.classify_url(url)
        
        # 基础分类
        if link_type == LinkType.NEWS:
            return '新闻', '资讯'
        elif link_type == LinkType.BLOG:
            return '博客', '个人分享'
        elif link_type == LinkType.EDUCATIONAL:
            return '教育', '学习资源'
        elif link_type == LinkType.ECOMMERCE:
            return '电商', '购物'
        elif link_type == LinkType.SOCIAL_MEDIA:
            return '社交媒体', '社区'
        elif link_type == LinkType.VIDEO:
            return '视频', '多媒体'
        elif link_type == LinkType.CODE_REPOSITORY:
            return '代码', '开发资源'
        
        return None, None
    
    async def _assess_trust(self, metadata: LinkMetadata) -> float:
        """评估可信度"""
        trust = 0.5  # 基础可信度
        
        # 知名域名加分
        trusted_domains = [
            'wikipedia.org', 'github.com', 'stackoverflow.com',
            'medium.com', 'youtube.com', 'vimeo.com',
            'bbc.com', 'reuters.com', 'apnews.com'
        ]
        
        if metadata.domain in trusted_domains:
            trust += 0.3
        
        # 有作者信息加分
        if metadata.author:
            trust += 0.1
        
        # 有发布日期加分
        if metadata.publish_date:
            trust += 0.1
        
        # 有结构化数据加分
        if metadata.structured_data:
            trust += 0.1
        
        return min(1.0, trust)
    
    async def _check_security_flags(self, url: str, content: LinkContent) -> List[str]:
        """检查安全标志"""
        flags = []
        
        # HTTP而非HTTPS
        if url.startswith('http://'):
            flags.append('non_secure_protocol')
        
        # 短URL服务
        shorteners = ['bit.ly', 'tinyurl.com', 'goo.gl', 'ow.ly']
        if any(domain in url for domain in shorteners):
            flags.append('url_shortener')
        
        # IP地址而不是域名
        import ipaddress
        try:
            parsed = urlparse(url)
            ipaddress.ip_address(parsed.hostname)
            flags.append('ip_address_url')
        except:
            pass
        
        # 过多重定向
        # 这里需要实际请求来检查重定向次数，暂时不实现
        
        return flags
    
    def _generate_cache_key(self, url: str, metadata: LinkMetadata) -> str:
        """生成缓存键"""
        content = f"{url}:{metadata.title}:{metadata.etag}:{metadata.last_modified}"
        return hashlib.md5(content.encode()).hexdigest()


# 主要的链接理解服务
class LinkUnderstandingService:
    """链接理解服务"""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.extractor = LinkExtractor()
        self.analyzer = LinkAnalyzer()
    
    async def understand_link(self, url: str) -> Optional[LinkAnalysis]:
        """理解链接"""
        try:
            async with self.extractor:
                # 提取元数据
                metadata = await self.extractor.extract_link_metadata(url)
                
                # 提取内容
                content = await self.extractor.extract_link_content(url)
                
                if not content:
                    return None
                
                # 分析内容
                analysis = await self.analyzer.analyze_link(url, content)
                
                self.logger.info("Link understood successfully", 
                              url=url,
                              link_type=analysis.link_type.value,
                              processing_time=analysis.processing_time)
                
                return analysis
                
        except Exception as e:
            self.logger.error("Link understanding failed", url=url, error=str(e))
            return None
    
    async def batch_understand_links(self, urls: List[str]) -> List[Optional[LinkAnalysis]]:
        """批量理解链接"""
        tasks = [self.understand_link(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error("Batch link understanding failed", 
                                url=urls[i],
                                error=str(result))
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results


# 全局链接理解服务
_link_service: Optional[LinkUnderstandingService] = None


def get_link_service() -> LinkUnderstandingService:
    """获取全局链接理解服务"""
    global _link_service
    if _link_service is None:
        _link_service = LinkUnderstandingService()
    return _link_service


# 便利函数
async def understand_url(url: str) -> Optional[LinkAnalysis]:
    """理解URL"""
    service = get_link_service()
    return await service.understand_link(url)


async def batch_understand_urls(urls: List[str]) -> List[Optional[LinkAnalysis]]:
    """批量理解URL"""
    service = get_link_service()
    return await service.batch_understand_links(urls)