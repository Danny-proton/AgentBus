"""
知识总线 (Knowledge Bus) 服务
Knowledge Bus service for AgentBus

本模块实现知识总线系统，负责知识的存储、检索、共享和更新，
为智能代理提供统一的知识管理服务。

注意：此模块现在作为知识总线插件的基础实现。
插件应该继承或组合此模块的功能。
"""

import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import aiofiles
from loguru import logger

from core.settings import settings

# 导出所有必要的类和方法
__all__ = [
    'KnowledgeType',
    'KnowledgeStatus', 
    'KnowledgeSource',
    'Knowledge',
    'KnowledgeQuery',
    'KnowledgeResult',
    'KnowledgeIndex',
    'KnowledgeBus'
]


class KnowledgeType(Enum):
    """知识类型枚举"""
    FACT = "fact"                    # 事实知识
    PROCEDURE = "procedure"          # 程序知识
    CONTEXT = "context"             # 上下文知识
    RELATION = "relation"           # 关系知识
    RULE = "rule"                  # 规则知识
    METADATA = "metadata"           # 元数据


class KnowledgeStatus(Enum):
    """知识状态枚举"""
    ACTIVE = "active"              # 活跃
    INACTIVE = "inactive"          # 不活跃
    DEPRECATED = "deprecated"       # 已废弃
    VALIDATING = "validating"       # 验证中


class KnowledgeSource(Enum):
    """知识来源枚举"""
    USER_INPUT = "user_input"      # 用户输入
    AGENT_LEARNING = "agent_learning"  # 智能体学习
    MANUAL_ENTRY = "manual_entry"   # 手动录入
    IMPORT = "import"              # 导入
    AUTO_GENERATED = "auto_generated"  # 自动生成


@dataclass
class Knowledge:
    """知识项数据结构"""
    id: str
    content: str
    knowledge_type: KnowledgeType
    source: KnowledgeSource
    created_at: datetime
    updated_at: datetime
    created_by: str               # 创建者
    tags: Set[str]               # 标签
    confidence: float             # 置信度 (0.0-1.0)
    usage_count: int = 0         # 使用次数
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE
    
    # 关联信息
    related_knowledge: Set[str] = None  # 关联知识ID
    metadata: Dict[str, Any] = None     # 元数据
    context: Dict[str, Any] = None      # 上下文
    
    def __post_init__(self):
        if self.related_knowledge is None:
            self.related_knowledge = set()
        if self.metadata is None:
            self.metadata = {}
        if self.context is None:
            self.context = {}


@dataclass
class KnowledgeQuery:
    """知识查询条件"""
    query: str                    # 查询内容
    knowledge_types: Optional[List[KnowledgeType]] = None
    tags: Optional[List[str]] = None
    confidence_threshold: float = 0.0
    limit: int = 10
    include_inactive: bool = False


@dataclass
class KnowledgeResult:
    """知识查询结果"""
    knowledge: Knowledge
    relevance_score: float        # 相关性评分
    match_reasons: List[str]     # 匹配原因


class KnowledgeIndex:
    """知识索引"""
    
    def __init__(self):
        self.content_index: Dict[str, Set[str]] = {}    # 关键词 -> 知识ID集合
        self.tag_index: Dict[str, Set[str]] = {}       # 标签 -> 知识ID集合
        self.type_index: Dict[KnowledgeType, Set[str]] = {}  # 类型 -> 知识ID集合
        self.source_index: Dict[KnowledgeSource, Set[str]] = {}  # 来源 -> 知识ID集合
        self.date_index: Dict[str, Set[str]] = {}      # 日期 -> 知识ID集合
        self.usage_index: Dict[str, int] = {}          # 知识ID -> 使用次数
    
    def add_knowledge(self, knowledge: Knowledge):
        """添加知识到索引"""
        knowledge_id = knowledge.id
        
        # 内容索引
        words = self._extract_keywords(knowledge.content)
        for word in words:
            if word not in self.content_index:
                self.content_index[word] = set()
            self.content_index[word].add(knowledge_id)
        
        # 标签索引
        for tag in knowledge.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(knowledge_id)
        
        # 类型索引
        if knowledge.knowledge_type not in self.type_index:
            self.type_index[knowledge.knowledge_type] = set()
        self.type_index[knowledge.knowledge_type].add(knowledge_id)
        
        # 来源索引
        if knowledge.source not in self.source_index:
            self.source_index[knowledge.source] = set()
        self.source_index[knowledge.source].add(knowledge_id)
        
        # 日期索引
        date_key = knowledge.created_at.strftime("%Y-%m-%d")
        if date_key not in self.date_index:
            self.date_index[date_key] = set()
        self.date_index[date_key].add(knowledge_id)
        
        # 使用次数索引
        self.usage_index[knowledge_id] = knowledge.usage_count
    
    def remove_knowledge(self, knowledge: Knowledge):
        """从索引中移除知识"""
        knowledge_id = knowledge.id
        
        # 从所有索引中移除
        for index_dict in [self.content_index, self.tag_index, self.type_index, 
                          self.source_index, self.date_index]:
            # 复制键列表以避免迭代时修改字典
            keys_to_remove = [key for key, knowledge_set in index_dict.items() 
                             if knowledge_id in knowledge_set]
            for key in keys_to_remove:
                index_dict[key].discard(knowledge_id)
                # 如果集合为空，删除该键
                if not index_dict[key]:
                    del index_dict[key]
        
        # 移除使用次数索引
        self.usage_index.pop(knowledge_id, None)
    
    def update_knowledge(self, old_knowledge: Knowledge, new_knowledge: Knowledge):
        """更新知识索引"""
        self.remove_knowledge(old_knowledge)
        self.add_knowledge(new_knowledge)
    
    def search_by_keywords(self, keywords: List[str]) -> Set[str]:
        """根据关键词搜索"""
        if not keywords:
            return set()
        
        result_sets = []
        for keyword in keywords:
            keyword_lower = keyword.lower()
            # 搜索内容索引
            content_matches = set()
            for word, knowledge_ids in self.content_index.items():
                if keyword_lower in word.lower():
                    content_matches.update(knowledge_ids)
            result_sets.append(content_matches)
        
        # 返回交集（所有关键词都匹配的知识）
        if result_sets:
            return set.intersection(*result_sets)
        return set()
    
    def search_by_tags(self, tags: List[str]) -> Set[str]:
        """根据标签搜索"""
        if not tags:
            return set()
        
        result_sets = []
        for tag in tags:
            if tag in self.tag_index:
                result_sets.append(self.tag_index[tag].copy())
        
        # 返回交集
        if result_sets:
            return set.intersection(*result_sets)
        return set()
    
    def search_by_type(self, knowledge_types: List[KnowledgeType]) -> Set[str]:
        """根据类型搜索"""
        if not knowledge_types:
            return set()
        
        result_sets = []
        for ktype in knowledge_types:
            if ktype in self.type_index:
                result_sets.append(self.type_index[ktype].copy())
        
        # 返回交集
        if result_sets:
            return set.intersection(*result_sets)
        return set()
    
    def get_most_used(self, limit: int = 10) -> List[Tuple[str, int]]:
        """获取使用次数最多的知识"""
        sorted_items = sorted(self.usage_index.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:limit]
    
    def _extract_keywords(self, content: str) -> List[str]:
        """从内容中提取关键词"""
        # 简单的关键词提取（实际应用中可以集成更复杂的NLP库）
        import re
        
        # 移除标点符号和特殊字符
        cleaned = re.sub(r'[^\w\s]', ' ', content.lower())
        
        # 分词并过滤停用词
        stop_words = {'的', '是', '在', '和', '与', '或', '及', '等', '了', '着', '过'}
        words = [word for word in cleaned.split() if len(word) > 1 and word not in stop_words]
        
        return words[:20]  # 限制关键词数量


class KnowledgeBus:
    """知识总线核心类"""
    
    def __init__(self):
        self.knowledge_store: Dict[str, Knowledge] = {}
        self.index = KnowledgeIndex()
        self.file_path = settings.knowledge_bus_file or "./data/knowledge_bus.json"
        
        # 统计信息
        self.stats = {
            "total_knowledge": 0,
            "by_type": {},
            "by_source": {},
            "total_usage": 0,
            "average_confidence": 0.0
        }
        
        logger.info("知识总线初始化完成")
    
    async def initialize(self):
        """初始化知识总线"""
        try:
            await self._load_from_file()
            logger.info(f"知识总线加载完成，共 {len(self.knowledge_store)} 条知识")
        except Exception as e:
            logger.error(f"知识总线加载失败: {e}")
            await self._create_default_knowledge()
    
    async def shutdown(self):
        """关闭知识总线"""
        try:
            await self._save_to_file()
            logger.info("知识总线已保存")
        except Exception as e:
            logger.error(f"知识总线保存失败: {e}")
    
    async def add_knowledge(
        self,
        content: str,
        knowledge_type: KnowledgeType,
        source: KnowledgeSource,
        created_by: str,
        tags: Set[str] = None,
        confidence: float = 1.0,
        metadata: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> str:
        """添加知识"""
        
        import uuid
        knowledge_id = str(uuid.uuid4())
        
        now = datetime.now()
        knowledge = Knowledge(
            id=knowledge_id,
            content=content,
            knowledge_type=knowledge_type,
            source=source,
            created_at=now,
            updated_at=now,
            created_by=created_by,
            tags=tags or set(),
            confidence=confidence,
            metadata=metadata or {},
            context=context or {}
        )
        
        # 存储知识
        self.knowledge_store[knowledge_id] = knowledge
        
        # 更新索引
        self.index.add_knowledge(knowledge)
        
        # 更新统计
        await self._update_stats()
        
        logger.info(f"知识已添加: {knowledge_id}")
        return knowledge_id
    
    async def update_knowledge(
        self,
        knowledge_id: str,
        content: str = None,
        tags: Set[str] = None,
        confidence: float = None,
        metadata: Dict[str, Any] = None,
        status: KnowledgeStatus = None
    ) -> bool:
        """更新知识"""
        
        if knowledge_id not in self.knowledge_store:
            return False
        
        knowledge = self.knowledge_store[knowledge_id]
        
        # 备份旧版本用于索引更新
        old_knowledge = Knowledge(**asdict(knowledge))
        
        # 更新字段
        if content is not None:
            knowledge.content = content
        if tags is not None:
            knowledge.tags = tags
        if confidence is not None:
            knowledge.confidence = confidence
        if metadata is not None:
            knowledge.metadata.update(metadata)
        if status is not None:
            knowledge.status = status
        
        knowledge.updated_at = datetime.now()
        
        # 更新索引
        self.index.update_knowledge(old_knowledge, knowledge)
        
        # 更新统计
        await self._update_stats()
        
        logger.info(f"知识已更新: {knowledge_id}")
        return True
    
    async def delete_knowledge(self, knowledge_id: str) -> bool:
        """删除知识"""
        
        if knowledge_id not in self.knowledge_store:
            return False
        
        knowledge = self.knowledge_store[knowledge_id]
        
        # 从索引中移除
        self.index.remove_knowledge(knowledge)
        
        # 从存储中删除
        del self.knowledge_store[knowledge_id]
        
        # 更新统计
        await self._update_stats()
        
        logger.info(f"知识已删除: {knowledge_id}")
        return True
    
    async def get_knowledge(self, knowledge_id: str) -> Optional[Knowledge]:
        """获取知识"""
        return self.knowledge_store.get(knowledge_id)
    
    async def search_knowledge(self, query: KnowledgeQuery) -> List[KnowledgeResult]:
        """搜索知识"""
        
        # 获取候选知识ID集合
        candidate_ids = set(self.knowledge_store.keys())
        
        # 应用过滤条件
        if not query.include_inactive:
            # 只包含活跃知识
            candidate_ids = {
                k_id for k_id, k in self.knowledge_store.items()
                if k.status == KnowledgeStatus.ACTIVE
            }
        
        if query.knowledge_types:
            type_matches = self.index.search_by_type(query.knowledge_types)
            candidate_ids &= type_matches
        
        if query.tags:
            tag_matches = self.index.search_by_tags(query.tags)
            candidate_ids &= tag_matches
        
        # 关键词搜索
        keywords = query.query.split()
        if keywords:
            keyword_matches = self.index.search_by_keywords(keywords)
            candidate_ids &= keyword_matches
        
        # 计算相关性评分
        results = []
        for knowledge_id in candidate_ids:
            knowledge = self.knowledge_store[knowledge_id]
            
            # 计算基础相关性
            relevance_score = await self._calculate_relevance(knowledge, query.query)
            
            # 应用置信度阈值
            if relevance_score >= query.confidence_threshold:
                results.append(KnowledgeResult(
                    knowledge=knowledge,
                    relevance_score=relevance_score,
                    match_reasons=await self._get_match_reasons(knowledge, query)
                ))
        
        # 按相关性排序并限制结果数量
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:query.limit]
    
    async def get_knowledge_stats(self) -> Dict[str, Any]:
        """获取知识统计信息"""
        await self._update_stats()
        return self.stats.copy()
    
    async def get_knowledge_by_type(self, knowledge_type: KnowledgeType) -> List[Knowledge]:
        """按类型获取知识"""
        return [
            knowledge for knowledge in self.knowledge_store.values()
            if knowledge.knowledge_type == knowledge_type
        ]
    
    async def get_knowledge_by_tags(self, tags: List[str]) -> List[Knowledge]:
        """按标签获取知识"""
        if not tags:
            return []
        
        result = []
        for knowledge in self.knowledge_store.values():
            if any(tag in knowledge.tags for tag in tags):
                result.append(knowledge)
        return result
    
    async def get_most_used_knowledge(self, limit: int = 10) -> List[Tuple[Knowledge, int]]:
        """获取使用次数最多的知识"""
        most_used = self.index.get_most_used(limit)
        return [
            (self.knowledge_store[knowledge_id], usage_count)
            for knowledge_id, usage_count in most_used
            if knowledge_id in self.knowledge_store
        ]
    
    async def record_knowledge_usage(self, knowledge_id: str):
        """记录知识使用"""
        if knowledge_id in self.knowledge_store:
            self.knowledge_store[knowledge_id].usage_count += 1
            self.index.usage_index[knowledge_id] = self.knowledge_store[knowledge_id].usage_count
    
    async def _calculate_relevance(self, knowledge: Knowledge, query: str) -> float:
        """计算知识与查询的相关性"""
        
        # 基础相关性：内容匹配度
        content_score = 0.0
        query_words = set(query.lower().split())
        content_words = set(knowledge.content.lower().split())
        
        if query_words and content_words:
            intersection = query_words & content_words
            content_score = len(intersection) / len(query_words)
        
        # 标签匹配度
        tag_score = 0.0
        if knowledge.tags:
            tag_matches = sum(1 for word in query_words if any(word in tag.lower() for tag in knowledge.tags))
            tag_score = tag_matches / len(query_words) if query_words else 0
        
        # 置信度权重
        confidence_score = knowledge.confidence
        
        # 使用频率权重
        usage_score = min(knowledge.usage_count / 100.0, 1.0)  # 归一化到[0,1]
        
        # 综合评分
        relevance_score = (
            content_score * 0.4 +      # 内容匹配 40%
            tag_score * 0.3 +         # 标签匹配 30%
            confidence_score * 0.2 +   # 置信度 20%
            usage_score * 0.1          # 使用频率 10%
        )
        
        return min(relevance_score, 1.0)
    
    async def _get_match_reasons(self, knowledge: Knowledge, query: KnowledgeQuery) -> List[str]:
        """获取匹配原因"""
        reasons = []
        query_words = set(query.query.lower().split())
        
        # 内容匹配
        content_words = set(knowledge.content.lower().split())
        content_matches = query_words & content_words
        if content_matches:
            reasons.append(f"内容匹配: {', '.join(list(content_matches)[:3])}")
        
        # 标签匹配
        if knowledge.tags:
            tag_matches = [tag for tag in knowledge.tags if any(word in tag.lower() for word in query_words)]
            if tag_matches:
                reasons.append(f"标签匹配: {', '.join(tag_matches[:3])}")
        
        # 类型匹配
        if query.knowledge_types and knowledge.knowledge_type in query.knowledge_types:
            reasons.append(f"类型匹配: {knowledge.knowledge_type.value}")
        
        return reasons
    
    async def _update_stats(self):
        """更新统计信息"""
        self.stats["total_knowledge"] = len(self.knowledge_store)
        
        # 按类型统计
        self.stats["by_type"] = {}
        for ktype in KnowledgeType:
            count = sum(1 for k in self.knowledge_store.values() if k.knowledge_type == ktype)
            self.stats["by_type"][ktype.value] = count
        
        # 按来源统计
        self.stats["by_source"] = {}
        for source in KnowledgeSource:
            count = sum(1 for k in self.knowledge_store.values() if k.source == source)
            self.stats["by_source"][source.value] = count
        
        # 总使用次数
        self.stats["total_usage"] = sum(k.usage_count for k in self.knowledge_store.values())
        
        # 平均置信度
        if self.knowledge_store:
            avg_confidence = sum(k.confidence for k in self.knowledge_store.values()) / len(self.knowledge_store)
            self.stats["average_confidence"] = round(avg_confidence, 3)
    
    async def _load_from_file(self):
        """从文件加载知识"""
        try:
            path = Path(self.file_path)
            if not path.exists():
                return
            
            async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                content = await f.read()
                data = json.loads(content)
            
            # 加载知识
            for knowledge_data in data.get('knowledge', []):
                # 转换枚举值
                knowledge_data['knowledge_type'] = KnowledgeType(knowledge_data['knowledge_type'])
                knowledge_data['source'] = KnowledgeSource(knowledge_data['source'])
                knowledge_data['status'] = KnowledgeStatus(knowledge_data['status'])
                
                # 转换集合
                knowledge_data['tags'] = set(knowledge_data['tags'])
                knowledge_data['related_knowledge'] = set(knowledge_data['related_knowledge'])
                
                # 转换时间
                knowledge_data['created_at'] = datetime.fromisoformat(knowledge_data['created_at'])
                knowledge_data['updated_at'] = datetime.fromisoformat(knowledge_data['updated_at'])
                
                knowledge = Knowledge(**knowledge_data)
                self.knowledge_store[knowledge.id] = knowledge
                self.index.add_knowledge(knowledge)
            
            logger.info(f"从文件加载了 {len(self.knowledge_store)} 条知识")
            
        except Exception as e:
            logger.error(f"从文件加载知识失败: {e}")
            raise
    
    async def _save_to_file(self):
        """保存知识到文件"""
        try:
            path = Path(self.file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # 准备序列化数据
            knowledge_data = []
            for knowledge in self.knowledge_store.values():
                data = asdict(knowledge)
                # 转换枚举值为字符串
                data['knowledge_type'] = knowledge.knowledge_type.value
                data['source'] = knowledge.source.value
                data['status'] = knowledge.status.value
                # 转换集合为列表
                data['tags'] = list(knowledge.tags)
                data['related_knowledge'] = list(knowledge.related_knowledge)
                # 转换时间为字符串
                data['created_at'] = knowledge.created_at.isoformat()
                data['updated_at'] = knowledge.updated_at.isoformat()
                knowledge_data.append(data)
            
            save_data = {
                'knowledge': knowledge_data,
                'stats': self.stats,
                'last_updated': datetime.now().isoformat()
            }
            
            async with aiofiles.open(path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(save_data, ensure_ascii=False, indent=2))
            
            logger.info(f"知识已保存到文件: {self.file_path}")
            
        except Exception as e:
            logger.error(f"保存知识到文件失败: {e}")
            raise
    
    async def _create_default_knowledge(self):
        """创建默认知识"""
        logger.info("创建默认知识")
        
        # 系统知识
        await self.add_knowledge(
            content="AgentBus是一个智能协作平台，提供多智能体协作、工具调用、记忆管理和API接口的综合解决方案。",
            knowledge_type=KnowledgeType.FACT,
            source=KnowledgeSource.MANUAL_ENTRY,
            created_by="system",
            tags={"系统介绍", "平台特性"},
            confidence=1.0
        )
        
        # 使用指南
        await self.add_knowledge(
            content="要启动AgentBus服务，请使用命令：python cli.py --reload 或 python cli.py --host 0.0.0.0 --port 8000",
            knowledge_type=KnowledgeType.PROCEDURE,
            source=KnowledgeSource.MANUAL_ENTRY,
            created_by="system",
            tags={"启动", "CLI", "命令"},
            confidence=1.0
        )
        
        # 最佳实践
        await self.add_knowledge(
            content="在创建HITL请求时，应该提供清晰的标题和描述，包含必要的上下文信息，以便更好地匹配合适的联系人。",
            knowledge_type=KnowledgeType.RULE,
            source=KnowledgeSource.MANUAL_ENTRY,
            created_by="system",
            tags={"HITL", "最佳实践", "请求"},
            confidence=0.9
        )
        
        logger.info("默认知识创建完成")


# 插件化兼容方法
class KnowledgeBusPluginMixin:
    """
    知识总线插件混合类
    
    为知识总线提供插件化兼容方法，使插件可以更容易地扩展和定制功能。
    """
    
    def __init__(self):
        super().__init__()
        self.plugin_hooks = {}
        self.plugin_tools = {}
        self.plugin_commands = {}
    
    def register_plugin_hook(self, event: str, handler: callable, priority: int = 0):
        """注册插件钩子"""
        if event not in self.plugin_hooks:
            self.plugin_hooks[event] = []
        
        hook_info = {
            'handler': handler,
            'priority': priority,
            'registered_at': datetime.now()
        }
        
        self.plugin_hooks[event].append(hook_info)
        
        # 按优先级排序
        self.plugin_hooks[event].sort(key=lambda x: x['priority'], reverse=True)
        
        logger.info(f"Registered plugin hook '{event}' with priority {priority}")
    
    def register_plugin_tool(self, name: str, function: callable, description: str = ""):
        """注册插件工具"""
        self.plugin_tools[name] = {
            'function': function,
            'description': description,
            'registered_at': datetime.now()
        }
        logger.info(f"Registered plugin tool '{name}'")
    
    def register_plugin_command(self, command: str, handler: callable, description: str = ""):
        """注册插件命令"""
        self.plugin_commands[command] = {
            'handler': handler,
            'description': description,
            'registered_at': datetime.now()
        }
        logger.info(f"Registered plugin command '{command}'")
    
    async def execute_plugin_hook(self, event: str, *args, **kwargs):
        """执行插件钩子"""
        if event in self.plugin_hooks:
            for hook_info in self.plugin_hooks[event]:
                try:
                    handler = hook_info['handler']
                    if asyncio.iscoroutinefunction(handler):
                        await handler(*args, **kwargs)
                    else:
                        handler(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Plugin hook '{event}' execution failed: {e}")
    
    def get_plugin_hooks(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有插件钩子"""
        return self.plugin_hooks.copy()
    
    def get_plugin_tools(self) -> Dict[str, Dict[str, Any]]:
        """获取所有插件工具"""
        return self.plugin_tools.copy()
    
    def get_plugin_commands(self) -> Dict[str, Dict[str, Any]]:
        """获取所有插件命令"""
        return self.plugin_commands.copy()


# 扩展 KnowledgeBus 以包含插件混合功能
class KnowledgeBusWithPluginSupport(KnowledgeBus, KnowledgeBusPluginMixin):
    """
    支持插件的知识总线类
    
    这个类结合了 KnowledgeBus 和 KnowledgeBusPluginMixin 的功能，
    为知识总线提供了完整的插件支持。
    """
    
    def __init__(self):
        KnowledgeBus.__init__(self)
        KnowledgeBusPluginMixin.__init__(self)
        logger.info("Knowledge Bus with plugin support initialized")


# 保持向后兼容性，默认导出原来的 KnowledgeBus 类
# 如果需要插件支持，请使用 KnowledgeBusWithPluginSupport
def create_knowledge_bus(plugin_support: bool = False) -> KnowledgeBus:
    """
    创建知识总线实例
    
    Args:
        plugin_support: 是否启用插件支持
        
    Returns:
        知识总线实例
    """
    if plugin_support:
        return KnowledgeBusWithPluginSupport()
    else:
        return KnowledgeBus()
