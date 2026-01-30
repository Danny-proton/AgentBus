"""
知识总线插件
Knowledge Bus Plugin for AgentBus

此插件将知识总线服务以插件形式提供，为AgentBus提供统一的知识管理服务。
插件包含知识存储、检索、共享、更新等功能，通过插件API对外提供服务。
"""

import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from agentbus.plugins import AgentBusPlugin, PluginContext
from agentbus.services.knowledge_bus import (
    KnowledgeBus,
    KnowledgeBusWithPluginSupport,
    KnowledgeType, 
    KnowledgeSource, 
    KnowledgeStatus,
    KnowledgeQuery,
    KnowledgeResult
)


class KnowledgeBusPlugin(AgentBusPlugin):
    """
    知识总线插件
    
    将知识总线服务包装为AgentBus插件，提供以下功能：
    - 知识存储和管理
    - 知识搜索和检索
    - 知识统计和分析
    - 知识关系管理
    - 插件工具和钩子
    """
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        self.knowledge_bus: Optional[KnowledgeBus] = None
        self.plugin_stats = {
            "total_queries": 0,
            "total_knowledge_items": 0,
            "total_searches": 0,
            "last_activity": None
        }
    
    def get_info(self) -> Dict[str, Any]:
        """
        返回插件信息
        """
        return {
            'id': self.plugin_id,
            'name': 'Knowledge Bus Plugin',
            'version': '1.0.0',
            'description': '知识总线插件，提供知识存储、检索、共享和管理功能',
            'author': 'AgentBus Team',
            'dependencies': [],
            'capabilities': [
                'knowledge_storage',
                'knowledge_search', 
                'knowledge_management',
                'knowledge_statistics',
                'knowledge_relationships'
            ]
        }
    
    async def activate(self):
        """
        激活插件时初始化知识总线服务并注册工具、钩子和命令
        """
        # 先调用父类方法
        await super().activate()
        
        # 初始化支持插件的知识总线
        self.knowledge_bus = KnowledgeBusWithPluginSupport()
        await self.knowledge_bus.initialize()
        
        # 注册工具
        await self._register_tools()
        
        # 注册钩子
        self._register_hooks()
        
        # 注册命令
        self._register_commands()
        
        self.context.logger.info(f"Knowledge Bus plugin {self.plugin_id} activated")
        return True
    
    async def deactivate(self):
        """
        停用插件时关闭知识总线服务
        """
        if self.knowledge_bus:
            await self.knowledge_bus.shutdown()
            self.knowledge_bus = None
        
        await super().deactivate()
    
    async def _register_tools(self):
        """注册知识总线相关的工具"""
        
        # 知识添加工具
        self.register_tool(
            name='knowledge_add',
            description='添加新知识到知识总线',
            function=self.add_knowledge_tool
        )
        
        # 知识搜索工具
        self.register_tool(
            name='knowledge_search',
            description='搜索知识总线中的知识',
            function=self.search_knowledge_tool
        )
        
        # 知识更新工具
        self.register_tool(
            name='knowledge_update',
            description='更新现有知识',
            function=self.update_knowledge_tool
        )
        
        # 知识删除工具
        self.register_tool(
            name='knowledge_delete',
            description='删除知识',
            function=self.delete_knowledge_tool
        )
        
        # 知识获取工具
        self.register_tool(
            name='knowledge_get',
            description='获取指定知识项',
            function=self.get_knowledge_tool
        )
        
        # 知识统计工具
        self.register_tool(
            name='knowledge_stats',
            description='获取知识统计信息',
            function=self.get_knowledge_stats_tool
        )
        
        # 按类型获取知识工具
        self.register_tool(
            name='knowledge_by_type',
            description='按类型获取知识列表',
            function=self.get_knowledge_by_type_tool
        )
        
        # 按标签获取知识工具
        self.register_tool(
            name='knowledge_by_tags',
            description='按标签获取知识列表',
            function=self.get_knowledge_by_tags_tool
        )
        
        # 获取热门知识工具
        self.register_tool(
            name='knowledge_most_used',
            description='获取使用次数最多的知识',
            function=self.get_most_used_knowledge_tool
        )
        
        # 记录知识使用工具
        self.register_tool(
            name='knowledge_usage_record',
            description='记录知识使用',
            function=self.record_knowledge_usage_tool
        )
    
    def _register_hooks(self):
        """注册事件钩子"""
        
        # 知识更新钩子
        self.register_hook(
            event='knowledge_updated',
            handler=self.on_knowledge_updated,
            priority=10
        )
        
        # 知识搜索钩子
        self.register_hook(
            event='knowledge_searched',
            handler=self.on_knowledge_searched,
            priority=5
        )
        
        # 知识创建钩子
        self.register_hook(
            event='knowledge_created',
            handler=self.on_knowledge_created,
            priority=8
        )
        
        # 知识删除钩子
        self.register_hook(
            event='knowledge_deleted',
            handler=self.on_knowledge_deleted,
            priority=8
        )
        
        # 系统初始化钩子
        self.register_hook(
            event='system_initialized',
            handler=self.on_system_initialized,
            priority=1
        )
    
    def _register_commands(self):
        """注册命令"""
        
        self.register_command(
            command='/kb-add',
            handler=self.handle_kb_add_command,
            description='添加知识到知识总线'
        )
        
        self.register_command(
            command='/kb-search',
            handler=self.handle_kb_search_command,
            description='搜索知识'
        )
        
        self.register_command(
            command='/kb-stats',
            handler=self.handle_kb_stats_command,
            description='显示知识统计'
        )
        
        self.register_command(
            command='/kb-help',
            handler=self.handle_kb_help_command,
            description='显示知识总线帮助'
        )
    
    # ===== 工具实现 =====
    
    async def add_knowledge_tool(self, content: str, knowledge_type: str, 
                                source: str, created_by: str,
                                tags: List[str] = None,
                                confidence: float = 1.0,
                                metadata: Dict[str, Any] = None,
                                context: Dict[str, Any] = None) -> str:
        """
        添加知识工具
        
        Args:
            content: 知识内容
            knowledge_type: 知识类型
            source: 知识来源
            created_by: 创建者
            tags: 标签列表
            confidence: 置信度
            metadata: 元数据
            context: 上下文
            
        Returns:
            知识ID
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        # 转换枚举值
        ktype = KnowledgeType(knowledge_type)
        ksource = KnowledgeSource(source)
        
        knowledge_id = await self.knowledge_bus.add_knowledge(
            content=content,
            knowledge_type=ktype,
            source=ksource,
            created_by=created_by,
            tags=set(tags) if tags else set(),
            confidence=confidence,
            metadata=metadata or {},
            context=context or {}
        )
        
        self.plugin_stats["total_knowledge_items"] += 1
        self.plugin_stats["last_activity"] = datetime.now()
        
        self.context.logger.info(f"Knowledge added: {knowledge_id}")
        return knowledge_id
    
    async def search_knowledge_tool(self, query: str, 
                                   knowledge_types: List[str] = None,
                                   tags: List[str] = None,
                                   confidence_threshold: float = 0.0,
                                   limit: int = 10,
                                   include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        搜索知识工具
        
        Args:
            query: 查询内容
            knowledge_types: 知识类型列表
            tags: 标签列表
            confidence_threshold: 置信度阈值
            limit: 结果数量限制
            include_inactive: 是否包含不活跃知识
            
        Returns:
            搜索结果列表
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        # 转换枚举值
        ktypes = None
        if knowledge_types:
            ktypes = [KnowledgeType(ktype) for ktype in knowledge_types]
        
        # 创建查询对象
        kquery = KnowledgeQuery(
            query=query,
            knowledge_types=ktypes,
            tags=tags,
            confidence_threshold=confidence_threshold,
            limit=limit,
            include_inactive=include_inactive
        )
        
        # 执行搜索
        results = await self.knowledge_bus.search_knowledge(kquery)
        
        # 转换为可序列化的格式
        search_results = []
        for result in results:
            search_results.append({
                'knowledge_id': result.knowledge.id,
                'content': result.knowledge.content,
                'knowledge_type': result.knowledge.knowledge_type.value,
                'source': result.knowledge.source.value,
                'created_by': result.knowledge.created_by,
                'tags': list(result.knowledge.tags),
                'confidence': result.knowledge.confidence,
                'relevance_score': result.relevance_score,
                'match_reasons': result.match_reasons,
                'created_at': result.knowledge.created_at.isoformat(),
                'updated_at': result.knowledge.updated_at.isoformat()
            })
        
        self.plugin_stats["total_searches"] += 1
        self.plugin_stats["last_activity"] = datetime.now()
        
        self.context.logger.info(f"Knowledge search performed: {len(results)} results")
        return search_results
    
    async def update_knowledge_tool(self, knowledge_id: str, 
                                   content: str = None,
                                   tags: List[str] = None,
                                   confidence: float = None,
                                   metadata: Dict[str, Any] = None,
                                   status: str = None) -> bool:
        """
        更新知识工具
        
        Args:
            knowledge_id: 知识ID
            content: 新内容
            tags: 新标签
            confidence: 新置信度
            metadata: 新元数据
            status: 新状态
            
        Returns:
            更新是否成功
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        # 转换状态枚举
        kstatus = None
        if status:
            kstatus = KnowledgeStatus(status)
        
        success = await self.knowledge_bus.update_knowledge(
            knowledge_id=knowledge_id,
            content=content,
            tags=set(tags) if tags else None,
            confidence=confidence,
            metadata=metadata,
            status=kstatus
        )
        
        if success:
            self.plugin_stats["last_activity"] = datetime.now()
            self.context.logger.info(f"Knowledge updated: {knowledge_id}")
        
        return success
    
    async def delete_knowledge_tool(self, knowledge_id: str) -> bool:
        """
        删除知识工具
        
        Args:
            knowledge_id: 知识ID
            
        Returns:
            删除是否成功
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        success = await self.knowledge_bus.delete_knowledge(knowledge_id)
        
        if success:
            self.plugin_stats["total_knowledge_items"] -= 1
            self.plugin_stats["last_activity"] = datetime.now()
            self.context.logger.info(f"Knowledge deleted: {knowledge_id}")
        
        return success
    
    async def get_knowledge_tool(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """
        获取知识工具
        
        Args:
            knowledge_id: 知识ID
            
        Returns:
            知识数据或None
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        knowledge = await self.knowledge_bus.get_knowledge(knowledge_id)
        
        if knowledge:
            return {
                'id': knowledge.id,
                'content': knowledge.content,
                'knowledge_type': knowledge.knowledge_type.value,
                'source': knowledge.source.value,
                'created_by': knowledge.created_by,
                'tags': list(knowledge.tags),
                'confidence': knowledge.confidence,
                'usage_count': knowledge.usage_count,
                'status': knowledge.status.value,
                'related_knowledge': list(knowledge.related_knowledge),
                'metadata': knowledge.metadata,
                'context': knowledge.context,
                'created_at': knowledge.created_at.isoformat(),
                'updated_at': knowledge.updated_at.isoformat()
            }
        
        return None
    
    async def get_knowledge_stats_tool(self) -> Dict[str, Any]:
        """
        获取知识统计工具
        
        Returns:
            统计信息
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        stats = await self.knowledge_bus.get_knowledge_stats()
        stats['plugin_stats'] = self.plugin_stats.copy()
        
        return stats
    
    async def get_knowledge_by_type_tool(self, knowledge_type: str) -> List[Dict[str, Any]]:
        """
        按类型获取知识工具
        
        Args:
            knowledge_type: 知识类型
            
        Returns:
            知识列表
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        ktype = KnowledgeType(knowledge_type)
        knowledge_list = await self.knowledge_bus.get_knowledge_by_type(ktype)
        
        result = []
        for knowledge in knowledge_list:
            result.append({
                'id': knowledge.id,
                'content': knowledge.content,
                'knowledge_type': knowledge.knowledge_type.value,
                'created_by': knowledge.created_by,
                'tags': list(knowledge.tags),
                'confidence': knowledge.confidence,
                'created_at': knowledge.created_at.isoformat()
            })
        
        return result
    
    async def get_knowledge_by_tags_tool(self, tags: List[str]) -> List[Dict[str, Any]]:
        """
        按标签获取知识工具
        
        Args:
            tags: 标签列表
            
        Returns:
            知识列表
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        knowledge_list = await self.knowledge_bus.get_knowledge_by_tags(tags)
        
        result = []
        for knowledge in knowledge_list:
            result.append({
                'id': knowledge.id,
                'content': knowledge.content,
                'knowledge_type': knowledge.knowledge_type.value,
                'created_by': knowledge.created_by,
                'tags': list(knowledge.tags),
                'confidence': knowledge.confidence,
                'created_at': knowledge.created_at.isoformat()
            })
        
        return result
    
    async def get_most_used_knowledge_tool(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取使用次数最多的知识工具
        
        Args:
            limit: 返回数量限制
            
        Returns:
            知识列表
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        most_used = await self.knowledge_bus.get_most_used_knowledge(limit)
        
        result = []
        for knowledge, usage_count in most_used:
            result.append({
                'id': knowledge.id,
                'content': knowledge.content,
                'knowledge_type': knowledge.knowledge_type.value,
                'created_by': knowledge.created_by,
                'tags': list(knowledge.tags),
                'confidence': knowledge.confidence,
                'usage_count': usage_count,
                'created_at': knowledge.created_at.isoformat()
            })
        
        return result
    
    async def record_knowledge_usage_tool(self, knowledge_id: str) -> bool:
        """
        记录知识使用工具
        
        Args:
            knowledge_id: 知识ID
            
        Returns:
            是否成功
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        await self.knowledge_bus.record_knowledge_usage(knowledge_id)
        
        self.plugin_stats["total_queries"] += 1
        self.plugin_stats["last_activity"] = datetime.now()
        
        return True
    
    # ===== 钩子处理函数 =====
    
    async def on_knowledge_updated(self, knowledge_id: str, changes: Dict[str, Any]):
        """知识更新钩子"""
        self.context.logger.info(f"Knowledge updated via hook: {knowledge_id}")
        
        # 可以在这里添加自定义逻辑，比如：
        # - 通知其他系统
        # - 触发相关知识更新
        # - 记录审计日志等
    
    async def on_knowledge_searched(self, query: str, results_count: int):
        """知识搜索钩子"""
        self.context.logger.info(f"Knowledge searched via hook: '{query}' returned {results_count} results")
    
    async def on_knowledge_created(self, knowledge_id: str, knowledge_data: Dict[str, Any]):
        """知识创建钩子"""
        self.context.logger.info(f"Knowledge created via hook: {knowledge_id}")
    
    async def on_knowledge_deleted(self, knowledge_id: str):
        """知识删除钩子"""
        self.context.logger.info(f"Knowledge deleted via hook: {knowledge_id}")
    
    async def on_system_initialized(self):
        """系统初始化钩子"""
        self.context.logger.info("System initialized - Knowledge Bus Plugin ready")
    
    # ===== 命令处理函数 =====
    
    async def handle_kb_add_command(self, args: str) -> str:
        """处理 /kb-add 命令"""
        return "Usage: /kb-add <content> <type> <source> <created_by> [tags] - Add knowledge to the bus"
    
    async def handle_kb_search_command(self, args: str) -> str:
        """处理 /kb-search 命令"""
        return "Usage: /kb-search <query> - Search knowledge in the bus"
    
    async def handle_kb_stats_command(self, args: str) -> str:
        """处理 /kb-stats 命令"""
        if not self.knowledge_bus:
            return "Knowledge bus not initialized"
        
        stats = await self.get_knowledge_stats_tool()
        
        stats_text = f"""📊 知识总线统计信息:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 总知识数: {stats['total_knowledge']}
🔍 总搜索次数: {stats['plugin_stats']['total_searches']}
📈 总查询次数: {stats['plugin_stats']['total_queries']}
⭐ 平均置信度: {stats['average_confidence']}

📂 按类型分布:
"""
        
        for ktype, count in stats['by_type'].items():
            stats_text += f"   • {ktype}: {count} 条\n"
        
        stats_text += f"""
📊 按来源分布:
"""
        for source, count in stats['by_source'].items():
            stats_text += f"   • {source}: {count} 条\n"
        
        stats_text += f"""
🕒 最后活动: {stats['plugin_stats']['last_activity'] or '无'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        return stats_text
    
    async def handle_kb_help_command(self, args: str) -> str:
        """处理 /kb-help 命令"""
        return """🧠 知识总线插件帮助
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 可用命令:
• /kb-stats - 显示知识统计信息
• /kb-search <query> - 搜索知识
• /kb-add - 添加知识
• /kb-help - 显示此帮助信息

🔧 可用工具:
• knowledge_add - 添加知识
• knowledge_search - 搜索知识
• knowledge_update - 更新知识
• knowledge_delete - 删除知识
• knowledge_get - 获取知识
• knowledge_stats - 获取统计
• knowledge_by_type - 按类型获取
• knowledge_by_tags - 按标签获取
• knowledge_most_used - 获取热门知识
• knowledge_usage_record - 记录使用

📚 知识类型:
• fact - 事实知识
• procedure - 程序知识
• context - 上下文知识
• relation - 关系知识
• rule - 规则知识
• metadata - 元数据

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    # ===== 兼容性方法 =====
    
    async def add_knowledge(self, content: str, knowledge_type: KnowledgeType,
                           source: KnowledgeSource, created_by: str,
                           tags: Set[str] = None, confidence: float = 1.0,
                           metadata: Dict[str, Any] = None,
                           context: Dict[str, Any] = None) -> str:
        """
        兼容性方法：直接调用知识总线添加知识
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        return await self.knowledge_bus.add_knowledge(
            content=content,
            knowledge_type=knowledge_type,
            source=source,
            created_by=created_by,
            tags=tags or set(),
            confidence=confidence,
            metadata=metadata or {},
            context=context or {}
        )
    
    async def search_knowledge(self, query: KnowledgeQuery) -> List[KnowledgeResult]:
        """
        兼容性方法：直接调用知识总线搜索知识
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        return await self.knowledge_bus.search_knowledge(query)
    
    async def get_knowledge(self, knowledge_id: str) -> Optional[Any]:
        """
        兼容性方法：直接调用知识总线获取知识
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        return await self.knowledge_bus.get_knowledge(knowledge_id)
    
    async def update_knowledge(self, knowledge_id: str, **kwargs) -> bool:
        """
        兼容性方法：直接调用知识总线更新知识
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        return await self.knowledge_bus.update_knowledge(knowledge_id, **kwargs)
    
    async def delete_knowledge(self, knowledge_id: str) -> bool:
        """
        兼容性方法：直接调用知识总线删除知识
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        return await self.knowledge_bus.delete_knowledge(knowledge_id)
    
    async def get_knowledge_stats(self) -> Dict[str, Any]:
        """
        兼容性方法：直接调用知识总线获取统计
        """
        if not self.knowledge_bus:
            raise Exception("Knowledge bus not initialized")
        
        return await self.knowledge_bus.get_knowledge_stats()