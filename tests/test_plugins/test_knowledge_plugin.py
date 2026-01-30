"""
知识总线插件测试
Knowledge Bus Plugin Test Suite

此测试套件测试知识总线插件的所有功能，包括工具注册、钩子处理、
命令注册以及插件的完整生命周期管理。
"""

import asyncio
import pytest
import tempfile
import os
import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from agentbus.plugins import PluginContext
from agentbus.plugins.knowledge_plugin import KnowledgeBusPlugin
from agentbus.services.knowledge_bus import (
    KnowledgeType, 
    KnowledgeSource, 
    KnowledgeStatus,
    KnowledgeQuery
)


class TestKnowledgeBusPlugin:
    """知识总线插件测试类"""
    
    @pytest.fixture
    def plugin_context(self):
        """创建插件上下文fixture"""
        # 创建真正的logger而不是Mock
        logger = logging.getLogger('test_knowledge_plugin')
        logger.setLevel(logging.DEBUG)
        
        # 添加处理器避免"No handlers found"警告
        if not logger.handlers:
            handler = logging.StreamHandler()
            logger.addHandler(handler)
        
        config = {
            "knowledge_bus.file_path": "./test_knowledge.json",
            "knowledge_bus.auto_save": True
        }
        
        runtime = {
            "test_mode": True,
            "temp_dir": tempfile.gettempdir()
        }
        
        return PluginContext(
            config=config,
            logger=logger,
            runtime=runtime
        )
    
    @pytest.fixture
    async def plugin(self, plugin_context):
        """创建插件fixture"""
        plugin = KnowledgeBusPlugin("test_knowledge_plugin", plugin_context)
        await plugin.activate()
        yield plugin
        await plugin.deactivate()
    
    def test_plugin_info(self, plugin):
        """测试插件信息获取"""
        info = plugin.get_info()
        
        assert "id" in info
        assert "name" in info
        assert "version" in info
        assert "description" in info
        assert "capabilities" in info
        
        assert info["id"] == "test_knowledge_plugin"
        assert info["name"] == "Knowledge Bus Plugin"
        # 描述可以是中文或英文，只要包含相关关键词
        desc_lower = info["description"].lower()
        assert any(keyword in desc_lower for keyword in ["knowledge", "知识", "storage", "检索"])
        assert "knowledge_storage" in info["capabilities"]
    
    def test_plugin_tools_registration(self, plugin):
        """测试工具注册"""
        tools = plugin.get_tools()
        
        # 检查所有工具都已注册
        tool_names = [tool.name for tool in tools]
        
        expected_tools = [
            "knowledge_add",
            "knowledge_search", 
            "knowledge_update",
            "knowledge_delete",
            "knowledge_get",
            "knowledge_stats",
            "knowledge_by_type",
            "knowledge_by_tags",
            "knowledge_most_used",
            "knowledge_usage_record"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool {expected_tool} not registered"
        
        # 检查工具属性
        for tool in tools:
            assert tool.name is not None
            assert tool.description is not None
            assert callable(tool.function)
    
    def test_plugin_hooks_registration(self, plugin):
        """测试钩子注册"""
        hooks = plugin.get_hooks()
        
        # 检查所有钩子都已注册
        expected_hooks = [
            "knowledge_updated",
            "knowledge_searched", 
            "knowledge_created",
            "knowledge_deleted",
            "system_initialized"
        ]
        
        for expected_hook in expected_hooks:
            assert expected_hook in hooks, f"Hook {expected_hook} not registered"
            assert len(hooks[expected_hook]) > 0, f"Hook {expected_hook} has no handlers"
    
    def test_plugin_commands_registration(self, plugin):
        """测试命令注册"""
        commands = plugin.get_commands()
        
        # 检查所有命令都已注册
        command_names = [cmd["command"] for cmd in commands]
        
        expected_commands = [
            "/kb-add",
            "/kb-search", 
            "/kb-stats",
            "/kb-help"
        ]
        
        for expected_command in expected_commands:
            assert expected_command in command_names, f"Command {expected_command} not registered"
    
    @pytest.mark.asyncio
    async def test_plugin_lifecycle(self, plugin_context):
        """测试插件生命周期"""
        plugin = KnowledgeBusPlugin("test_lifecycle_plugin", plugin_context)
        
        # 测试初始化
        assert plugin.status.value == "unloaded"
        
        # 测试激活
        success = await plugin.activate()
        assert success is True
        assert plugin.status.value == "active"
        assert plugin.knowledge_bus is not None
        
        # 测试停用
        success = await plugin.deactivate()
        assert success is True
        assert plugin.status.value == "deactivated"
        assert plugin.knowledge_bus is None
    
    @pytest.mark.asyncio
    async def test_add_knowledge_tool(self, plugin):
        """测试添加知识工具"""
        knowledge_id = await plugin.add_knowledge_tool(
            content="这是一个测试知识",
            knowledge_type="fact",
            source="user_input",
            created_by="test_user",
            tags=["测试", "工具"],
            confidence=0.9
        )
        
        assert knowledge_id is not None
        assert isinstance(knowledge_id, str)
        assert len(knowledge_id) > 0
        
        # 验证知识已被添加
        knowledge = await plugin.get_knowledge_tool(knowledge_id)
        assert knowledge is not None
        assert knowledge["content"] == "这是一个测试知识"
        assert knowledge["knowledge_type"] == "fact"
        assert knowledge["created_by"] == "test_user"
        assert "测试" in knowledge["tags"]
        assert knowledge["confidence"] == 0.9
    
    @pytest.mark.asyncio
    async def test_search_knowledge_tool(self, plugin):
        """测试搜索知识工具"""
        # 添加测试知识
        await plugin.add_knowledge_tool(
            content="AgentBus是一个智能协作平台",
            knowledge_type="fact",
            source="user_input",
            created_by="test_user",
            tags=["AgentBus", "平台"]
        )
        
        # 搜索知识
        results = await plugin.search_knowledge_tool(
            query="AgentBus",
            limit=10
        )
        
        assert len(results) > 0
        assert any("AgentBus" in result["content"] for result in results)
        
        # 检查结果格式
        for result in results:
            assert "knowledge_id" in result
            assert "content" in result
            assert "knowledge_type" in result
            assert "relevance_score" in result
            assert "match_reasons" in result
    
    @pytest.mark.asyncio
    async def test_update_knowledge_tool(self, plugin):
        """测试更新知识工具"""
        # 添加知识
        knowledge_id = await plugin.add_knowledge_tool(
            content="原始内容",
            knowledge_type="fact",
            source="user_input",
            created_by="test_user"
        )
        
        # 更新知识
        success = await plugin.update_knowledge_tool(
            knowledge_id=knowledge_id,
            content="更新后的内容",
            confidence=0.8
        )
        
        assert success is True
        
        # 验证更新
        knowledge = await plugin.get_knowledge_tool(knowledge_id)
        assert knowledge["content"] == "更新后的内容"
        assert knowledge["confidence"] == 0.8
    
    @pytest.mark.asyncio
    async def test_delete_knowledge_tool(self, plugin):
        """测试删除知识工具"""
        # 添加知识
        knowledge_id = await plugin.add_knowledge_tool(
            content="将被删除的知识",
            knowledge_type="fact",
            source="user_input",
            created_by="test_user"
        )
        
        # 验证知识存在
        knowledge = await plugin.get_knowledge_tool(knowledge_id)
        assert knowledge is not None
        
        # 删除知识
        success = await plugin.delete_knowledge_tool(knowledge_id)
        assert success is True
        
        # 验证知识已被删除
        knowledge = await plugin.get_knowledge_tool(knowledge_id)
        assert knowledge is None
    
    @pytest.mark.asyncio
    async def test_get_knowledge_stats_tool(self, plugin):
        """测试获取统计信息工具"""
        # 添加一些知识
        await plugin.add_knowledge_tool(
            content="知识1",
            knowledge_type="fact",
            source="user_input",
            created_by="user1"
        )
        
        await plugin.add_knowledge_tool(
            content="知识2",
            knowledge_type="procedure", 
            source="manual_entry",
            created_by="user2"
        )
        
        # 获取统计
        stats = await plugin.get_knowledge_stats_tool()
        
        assert "total_knowledge" in stats
        assert "by_type" in stats
        assert "by_source" in stats
        assert "plugin_stats" in stats
        
        assert stats["total_knowledge"] >= 2
        assert "fact" in stats["by_type"]
        assert "procedure" in stats["by_type"]
    
    @pytest.mark.asyncio
    async def test_get_knowledge_by_type_tool(self, plugin):
        """测试按类型获取知识工具"""
        # 添加不同类型的知识
        await plugin.add_knowledge_tool(
            content="事实知识",
            knowledge_type="fact",
            source="user_input",
            created_by="user1"
        )
        
        await plugin.add_knowledge_tool(
            content="程序知识",
            knowledge_type="procedure",
            source="user_input", 
            created_by="user2"
        )
        
        # 获取事实类型知识
        facts = await plugin.get_knowledge_by_type_tool("fact")
        assert len(facts) > 0
        assert all(item["knowledge_type"] == "fact" for item in facts)
        
        # 获取程序类型知识
        procedures = await plugin.get_knowledge_by_type_tool("procedure")
        assert len(procedures) > 0
        assert all(item["knowledge_type"] == "procedure" for item in procedures)
    
    @pytest.mark.asyncio
    async def test_get_knowledge_by_tags_tool(self, plugin):
        """测试按标签获取知识工具"""
        # 添加带标签的知识
        await plugin.add_knowledge_tool(
            content="AI相关知识",
            knowledge_type="fact",
            source="user_input",
            created_by="user1",
            tags=["AI", "机器学习"]
        )
        
        await plugin.add_knowledge_tool(
            content="编程相关知识", 
            knowledge_type="fact",
            source="user_input",
            created_by="user2",
            tags=["编程", "Python"]
        )
        
        # 按标签搜索
        ai_knowledge = await plugin.get_knowledge_by_tags_tool(["AI"])
        assert len(ai_knowledge) > 0
        assert any("AI" in item["tags"] for item in ai_knowledge)
        
        python_knowledge = await plugin.get_knowledge_by_tags_tool(["Python"])
        assert len(python_knowledge) > 0
        assert any("Python" in item["tags"] for item in python_knowledge)
    
    @pytest.mark.asyncio
    async def test_record_knowledge_usage_tool(self, plugin):
        """测试记录知识使用工具"""
        # 添加知识
        knowledge_id = await plugin.add_knowledge_tool(
            content="将被使用的知识",
            knowledge_type="fact",
            source="user_input",
            created_by="test_user"
        )
        
        # 记录使用
        success = await plugin.record_knowledge_usage_tool(knowledge_id)
        assert success is True
        
        # 验证使用次数增加
        knowledge = await plugin.get_knowledge_tool(knowledge_id)
        assert knowledge["usage_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_hook_handlers(self, plugin):
        """测试钩子处理函数"""
        # 这些钩子主要用于记录日志，测试其调用不会抛出异常
        
        # 测试知识更新钩子
        await plugin.on_knowledge_updated("test_id", {"field": "value"})
        
        # 测试知识搜索钩子
        await plugin.on_knowledge_searched("test query", 5)
        
        # 测试知识创建钩子
        await plugin.on_knowledge_created("test_id", {"content": "test"})
        
        # 测试知识删除钩子
        await plugin.on_knowledge_deleted("test_id")
        
        # 测试系统初始化钩子
        await plugin.on_system_initialized()
    
    @pytest.mark.asyncio
    async def test_command_handlers(self, plugin):
        """测试命令处理函数"""
        # 测试帮助命令
        help_result = await plugin.handle_kb_help_command("")
        assert "知识总线插件帮助" in help_result
        assert "/kb-stats" in help_result
        
        # 测试统计命令
        stats_result = await plugin.handle_kb_stats_command("")
        assert "知识总线统计信息" in stats_result
        
        # 测试添加命令
        add_result = await plugin.handle_kb_add_command("")
        assert "Usage:" in add_result
        
        # 测试搜索命令
        search_result = await plugin.handle_kb_search_command("")
        assert "Usage:" in search_result
    
    @pytest.mark.asyncio
    async def test_compatibility_methods(self, plugin):
        """测试兼容性方法"""
        # 测试添加知识兼容性方法
        knowledge_id = await plugin.add_knowledge(
            content="兼容性测试知识",
            knowledge_type=KnowledgeType.FACT,
            source=KnowledgeSource.USER_INPUT,
            created_by="test_user",
            tags={"兼容性", "测试"}
        )
        
        assert knowledge_id is not None
        
        # 测试搜索知识兼容性方法
        query = KnowledgeQuery(
            query="兼容性",
            limit=10
        )
        
        results = await plugin.search_knowledge(query)
        assert len(results) > 0
        
        # 测试获取知识兼容性方法
        knowledge = await plugin.get_knowledge(knowledge_id)
        assert knowledge is not None
        assert knowledge.content == "兼容性测试知识"
        
        # 测试更新知识兼容性方法
        success = await plugin.update_knowledge(
            knowledge_id=knowledge_id,
            content="更新后的兼容性测试知识"
        )
        assert success is True
        
        # 测试删除知识兼容性方法
        success = await plugin.delete_knowledge(knowledge_id)
        assert success is True
        
        # 测试获取统计兼容性方法
        stats = await plugin.get_knowledge_stats()
        assert "total_knowledge" in stats
    
    @pytest.mark.asyncio
    async def test_error_handling(self, plugin_context):
        """测试错误处理"""
        # 测试未初始化的插件
        plugin = KnowledgeBusPlugin("test_error_plugin", plugin_context)
        
        with pytest.raises(Exception, match="Knowledge bus not initialized"):
            await plugin.add_knowledge_tool("content", "fact", "user_input", "user")
        
        with pytest.raises(Exception, match="Knowledge bus not initialized"):
            await plugin.search_knowledge_tool("query")
        
        with pytest.raises(Exception, match="Knowledge bus not initialized"):
            await plugin.get_knowledge_tool("test_id")
    
    @pytest.mark.asyncio
    async def test_plugin_configuration(self, plugin):
        """测试插件配置"""
        # 测试配置获取
        file_path = plugin.get_config("knowledge_bus.file_path", "./default.json")
        assert file_path == "./test_knowledge.json"  # 来自fixture配置
        
        auto_save = plugin.get_config("knowledge_bus.auto_save", False)
        assert auto_save is True
        
        # 测试配置设置
        plugin.set_config("test_key", "test_value")
        value = plugin.get_config("test_key")
        assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_plugin_runtime_variables(self, plugin):
        """测试插件运行时变量"""
        # 测试运行时变量获取
        test_mode = plugin.get_runtime("test_mode")
        assert test_mode is True
        
        temp_dir = plugin.get_runtime("temp_dir")
        assert temp_dir is not None
        
        # 测试运行时变量设置
        plugin.set_runtime("custom_runtime_var", "custom_value")
        value = plugin.get_runtime("custom_runtime_var")
        assert value == "custom_value"
    
    @pytest.mark.asyncio
    async def test_multiple_plugin_instances(self, plugin_context):
        """测试多个插件实例"""
        # 创建多个插件实例
        plugin1 = KnowledgeBusPlugin("plugin1", plugin_context)
        plugin2 = KnowledgeBusPlugin("plugin2", plugin_context)
        
        # 激活插件
        await plugin1.activate()
        await plugin2.activate()
        
        # 每个插件应该独立工作
        knowledge_id1 = await plugin1.add_knowledge_tool(
            content="插件1的知识",
            knowledge_type="fact",
            source="user_input",
            created_by="plugin1"
        )
        
        knowledge_id2 = await plugin2.add_knowledge_tool(
            content="插件2的知识", 
            knowledge_type="fact",
            source="user_input",
            created_by="plugin2"
        )
        
        # 验证它们相互独立
        knowledge1 = await plugin1.get_knowledge_tool(knowledge_id1)
        knowledge2 = await plugin2.get_knowledge_tool(knowledge_id2)
        
        assert knowledge1["created_by"] == "plugin1"
        assert knowledge2["created_by"] == "plugin2"
        
        # 停用插件
        await plugin1.deactivate()
        await plugin2.deactivate()


# 集成测试
class TestKnowledgeBusPluginIntegration:
    """知识总线插件集成测试"""
    
    @pytest.mark.asyncio
    async def test_plugin_with_real_knowledge_bus(self):
        """测试插件与真实知识总线的集成"""
        # 创建真实的插件上下文
        logger = logging.getLogger('integration_test')
        config = {"knowledge_bus": {"file_path": "./integration_test.json"}}
        runtime = {"test_mode": True}
        
        context = PluginContext(
            config=config,
            logger=logger,
            runtime=runtime
        )
        
        # 创建并激活插件
        plugin = KnowledgeBusPlugin("integration_plugin", context)
        await plugin.activate()
        
        try:
            # 执行完整的知识管理流程
            # 1. 添加知识
            fact_id = await plugin.add_knowledge_tool(
                content="AgentBus是一个集成平台",
                knowledge_type="fact",
                source="user_input",
                created_by="integration_test",
                tags={"集成", "测试"},
                confidence=0.95
            )
            
            # 2. 搜索知识
            search_results = await plugin.search_knowledge_tool(
                query="AgentBus",
                confidence_threshold=0.5
            )
            
            assert len(search_results) > 0
            
            # 3. 获取统计信息
            stats = await plugin.get_knowledge_stats_tool()
            assert stats["total_knowledge"] >= 1
            
            # 4. 按类型获取
            facts = await plugin.get_knowledge_by_type_tool("fact")
            assert len(facts) > 0
            
            # 5. 更新知识
            success = await plugin.update_knowledge_tool(
                knowledge_id=fact_id,
                content="AgentBus是一个强大的集成平台"
            )
            assert success is True
            
            # 6. 记录使用
            await plugin.record_knowledge_usage_tool(fact_id)
            
            # 7. 获取热门知识
            most_used = await plugin.get_most_used_knowledge_tool(5)
            assert len(most_used) >= 0
            
        finally:
            # 清理
            await plugin.deactivate()
            
            # 删除测试文件
            if os.path.exists("./integration_test.json"):
                os.remove("./integration_test.json")


if __name__ == "__main__":
    # 运行基本测试
    asyncio.run(test_basic_plugin_functionality())


async def test_basic_plugin_functionality():
    """基本插件功能测试"""
    print("🧪 开始测试知识总线插件基本功能...")
    
    # 创建插件上下文
    logger = logging.getLogger('basic_test')
    
    config = {
        "knowledge_bus": {
            "file_path": "./test_basic_knowledge.json",
            "auto_save": True
        }
    }
    
    runtime = {
        "test_mode": True,
        "temp_dir": tempfile.gettempdir()
    }
    
    context = PluginContext(
        config=config,
        logger=logger,
        runtime=runtime
    )
    
    # 创建并激活插件
    plugin = KnowledgeBusPlugin("basic_test_plugin", context)
    await plugin.activate()
    
    try:
        print("✅ 插件激活成功")
        
        # 测试添加知识
        knowledge_id = await plugin.add_knowledge_tool(
            content="这是一个基本测试知识",
            knowledge_type="fact",
            source="user_input",
            created_by="basic_test",
            tags={"基本", "测试"},
            confidence=0.8
        )
        
        print(f"✅ 知识添加成功: {knowledge_id}")
        
        # 测试搜索知识
        results = await plugin.search_knowledge_tool(
            query="基本测试",
            limit=10
        )
        
        print(f"✅ 知识搜索成功，找到 {len(results)} 条结果")
        
        # 测试获取统计
        stats = await plugin.get_knowledge_stats_tool()
        print(f"✅ 统计信息获取成功，总知识数: {stats['total_knowledge']}")
        
        print("🎉 基本插件功能测试完成！")
        
    finally:
        await plugin.deactivate()
        
        # 清理测试文件
        if os.path.exists("./test_basic_knowledge.json"):
            os.remove("./test_basic_knowledge.json")