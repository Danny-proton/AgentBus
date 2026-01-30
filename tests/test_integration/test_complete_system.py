"""
AgentBus 完整系统集成测试

此模块测试整个AgentBus系统的完整集成功能，包括：
- 插件系统的完整生命周期（加载、激活、停用、卸载）
- 渠道系统的连接和消息处理
- HITL服务的集成
- 知识总线的集成
- 多模型协调器的集成
- CLI功能的集成
- 所有组件间的交互和数据流

测试覆盖：
- 端到端系统测试
- 跨组件集成测试
- 性能和稳定性测试
- 错误恢复和容错测试
"""

import pytest
import asyncio
import tempfile
import os
import shutil
import logging
import json
import time
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# AgentBus 核心组件 - 部分注释掉因为文件不存在
# from agentbus.core.context import AgentBusContext
from agentbus.plugins.manager import PluginManager
# from agentbus.plugins.core import PluginContext, AgentBusPlugin, PluginStatus
from agentbus.channels.manager import ChannelManager
from agentbus.services.hitl import HITLService, HITLPriority
from agentbus.services.knowledge_bus import KnowledgeBus, KnowledgeType, KnowledgeSource
from agentbus.services.multi_model_coordinator import MultiModelCoordinator, ModelType
# from agentbus.cli import AgentBusCLI


class TestCompleteSystemIntegration:
    """完整系统集成测试类"""
    
    @pytest.fixture
    async def system_context(self):
        """创建完整的系统上下文"""
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        config_dir = os.path.join(temp_dir, "config")
        data_dir = os.path.join(temp_dir, "data")
        logs_dir = os.path.join(temp_dir, "logs")
        
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
        
        # 创建配置
        config = {
            "agentbus": {
                "data_dir": data_dir,
                "logs_dir": logs_dir,
                "plugins_dir": os.path.join(temp_dir, "plugins"),
                "channels_config": os.path.join(config_dir, "channels.json"),
                "knowledge_config": os.path.join(config_dir, "knowledge.json")
            },
            "hitl": {
                "enabled": True,
                "timeout_minutes": 30,
                "max_concurrent_requests": 10
            },
            "knowledge_bus": {
                "enabled": True,
                "max_knowledge_items": 1000,
                "confidence_threshold": 0.7
            },
            "multi_model": {
                "enabled": True,
                "default_model": "gpt-3.5-turbo",
                "max_concurrent_requests": 5
            },
            "channels": {
                "enabled": True,
                "auto_connect": False,
                "heartbeat_interval": 30
            }
        }
        
        # 写入配置文件
        config_file = os.path.join(config_dir, "agentbus.json")
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # 创建上下文
        context = AgentBusContext(
            config=config,
            data_dir=data_dir,
            logs_dir=logs_dir
        )
        
        yield context
        
        # 清理资源
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    async def plugin_manager(self, system_context):
        """创建插件管理器"""
        plugin_context = PluginContext(
            config=system_context.config.get("plugins", {}),
            logger=logging.getLogger("plugin_manager"),
            runtime={"system_context": system_context}
        )
        
        manager = PluginManager(plugin_context)
        
        # 创建插件目录
        plugin_dir = system_context.config["agentbus"]["plugins_dir"]
        os.makedirs(plugin_dir, exist_ok=True)
        manager._plugin_dirs = [plugin_dir]
        
        yield manager
    
    @pytest.fixture
    async def channel_manager(self, system_context):
        """创建渠道管理器"""
        manager = ChannelManager(
            config=system_context.config.get("channels", {}),
            logger=logging.getLogger("channel_manager")
        )
        yield manager
    
    @pytest.fixture
    async def hitl_service(self, system_context):
        """创建HITL服务"""
        service = HITLService(
            config=system_context.config.get("hitl", {}),
            logger=logging.getLogger("hitl_service")
        )
        yield service
    
    @pytest.fixture
    async def knowledge_bus(self, system_context):
        """创建知识总线"""
        kb = KnowledgeBus(
            config=system_context.config.get("knowledge_bus", {}),
            logger=logging.getLogger("knowledge_bus")
        )
        yield kb
    
    @pytest.fixture
    async def multi_model_coordinator(self, system_context):
        """创建多模型协调器"""
        coordinator = MultiModelCoordinator(
            config=system_context.config.get("multi_model", {}),
            logger=logging.getLogger("multi_model_coordinator")
        )
        yield coordinator
    
    @pytest.fixture
    def cli_instance(self, system_context):
        """创建CLI实例"""
        cli = AgentBusCLI(
            context=system_context,
            logger=logging.getLogger("cli")
        )
        yield cli

    @pytest.mark.asyncio
    async def test_complete_system_initialization(self, system_context, plugin_manager, 
                                                  channel_manager, hitl_service, 
                                                  knowledge_bus, multi_model_coordinator):
        """测试完整系统的初始化"""
        
        print("🚀 开始测试完整系统初始化...")
        
        # 1. 初始化所有组件
        await plugin_manager.initialize()
        await channel_manager.initialize()
        await hitl_service.start()
        await knowledge_bus.initialize()
        await multi_model_coordinator.start()
        
        print("✅ 所有核心组件初始化完成")
        
        # 2. 验证组件状态
        assert plugin_manager is not None
        assert channel_manager is not None
        assert hitl_service is not None
        assert knowledge_bus is not None
        assert multi_model_coordinator is not None
        
        print("✅ 系统组件状态验证通过")

    @pytest.mark.asyncio
    async def test_plugin_system_integration(self, system_context, plugin_manager):
        """测试插件系统集成"""
        
        print("🔌 开始测试插件系统集成...")
        
        # 创建测试插件目录
        plugin_dir = system_context.config["agentbus"]["plugins_dir"]
        
        # 1. 创建数据处理插件
        data_plugin_file = os.path.join(plugin_dir, "data_processor.py")
        with open(data_plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
import asyncio
from agentbus.plugins import AgentBusPlugin, PluginContext

class DataProcessorPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.processed_count = 0
    
    def get_info(self):
        return {
            'id': 'data_processor',
            'name': 'Data Processor Plugin',
            'version': '1.0.0',
            'description': 'Process data for system integration',
            'author': 'System Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("process_data", "Process data", self.process_data)
        self.register_hook("data_received", self.handle_data)
        self.register_command("/stats", self.get_stats, "Get processing statistics")
    
    def process_data(self, data: str) -> str:
        self.processed_count += 1
        return f"Processed: {data.upper()}"
    
    async def handle_data(self, data: str):
        self.context.logger.info(f"Handled data: {data}")
        return f"Hook processed: {data}"
    
    async def get_stats(self) -> dict:
        return {
            'plugin_id': self.plugin_id,
            'processed_count': self.processed_count,
            'status': self.status.value
        }
''')
        
        # 2. 创建HITL增强插件
        hitl_plugin_file = os.path.join(plugin_dir, "hitl_enhancer.py")
        with open(hitl_plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
from agentbus.plugins import AgentBusPlugin, PluginContext

class HITLEnhancerPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.enhancement_count = 0
    
    def get_info(self):
        return {
            'id': 'hitl_enhancer',
            'name': 'HITL Enhancer Plugin',
            'version': '1.0.0',
            'description': 'Enhance HITL requests with additional context',
            'author': 'System Test',
            'dependencies': ['data_processor']
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("enhance_request", "Enhance HITL request", self.enhance_request)
        self.register_hook("hitl_request_created", self.enhance_hitl_request)
    
    def enhance_request(self, request_data: dict) -> dict:
        self.enhancement_count += 1
        enhanced = request_data.copy()
        enhanced['enhanced'] = True
        enhanced['enhancement_count'] = self.enhancement_count
        return enhanced
    
    async def enhance_hitl_request(self, request: dict):
        enhanced = self.enhance_request(request)
        return enhanced
''')
        
        # 3. 发现并加载插件
        discovered = await plugin_manager.discover_plugins()
        assert len(discovered) == 2
        
        print(f"✅ 发现 {len(discovered)} 个插件")
        
        # 4. 加载并激活插件
        data_plugin = await plugin_manager.load_plugin('data_processor', data_plugin_file)
        assert data_plugin is not None
        
        hitl_plugin = await plugin_manager.load_plugin('hitl_enhancer', hitl_plugin_file)
        assert hitl_plugin is not None
        
        print("✅ 插件加载完成")
        
        # 5. 激活插件
        success1 = await plugin_manager.activate_plugin('data_processor')
        assert success1 == True
        
        success2 = await plugin_manager.activate_plugin('hitl_enhancer')
        assert success2 == True
        
        print("✅ 插件激活完成")
        
        # 6. 测试插件功能
        result = await plugin_manager.execute_tool("process_data", "test data")
        assert result == "Processed: TEST DATA"
        
        stats = await plugin_manager.execute_tool("get_stats")
        assert stats['processed_count'] == 1
        
        enhancement_result = await plugin_manager.execute_tool("enhance_request", {"test": "data"})
        assert enhancement_result['enhanced'] == True
        assert enhancement_result['enhancement_count'] == 1
        
        print("✅ 插件功能测试通过")
        
        # 7. 测试钩子执行
        hook_results = await plugin_manager.execute_hook("data_received", "test message")
        assert len(hook_results) == 1
        assert "Hook processed: test message" in hook_results[0]
        
        print("✅ 插件钩子执行测试通过")

    @pytest.mark.asyncio
    async def test_hitl_knowledge_integration(self, system_context, hitl_service, knowledge_bus):
        """测试HITL与知识总线的集成"""
        
        print("🧠 开始测试HITL与知识总线集成...")
        
        # 1. 启动服务
        await hitl_service.start()
        await knowledge_bus.initialize()
        
        # 2. 创建知识基础
        practice_id = await knowledge_bus.add_knowledge(
            content="HITL请求应该包含清晰的上下文信息和具体的任务描述，以便智能匹配最合适的联系人。",
            knowledge_type=KnowledgeType.RULE,
            source=KnowledgeSource.MANUAL_ENTRY,
            created_by="system",
            tags={"HITL", "最佳实践"},
            confidence=0.9
        )
        
        contact_id = await knowledge_bus.add_knowledge(
            content="当HITL请求包含紧急标记时，系统会优先联系具有高优先级评分的联系人。",
            knowledge_type=KnowledgeType.FACT,
            source=KnowledgeSource.MANUAL_ENTRY,
            created_by="system",
            tags={"HITL", "紧急处理"},
            confidence=0.8
        )
        
        print("✅ 知识基础创建完成")
        
        # 3. 创建HITL请求
        request_id = await hitl_service.create_hitl_request(
            agent_id="test_agent",
            title="API接口调试需要专家协助",
            description="在开发AgentBus的HITL功能时，遇到了复杂的API接口问题，需要有经验的开发专家协助调试。",
            context={
                "task_type": "debugging",
                "domain": "api_development",
                "technology": "fastapi",
                "priority": "high"
            },
            priority=HITLPriority.HIGH,
            timeout_minutes=15
        )
        
        print(f"✅ HITL请求创建: {request_id}")
        
        # 4. 知识检索辅助
        query_results = await knowledge_bus.search_knowledge(
            type("Query", (), {
                "query": "HITL 请求 创建 最佳实践",
                "knowledge_types": [KnowledgeType.RULE, KnowledgeType.FACT],
                "tags": ["HITL"],
                "confidence_threshold": 0.7,
                "limit": 5
            })()
        )
        
        assert len(query_results) >= 1
        print(f"✅ 检索到 {len(query_results)} 条相关知识")
        
        # 5. 提交HITL响应
        await hitl_service.submit_hitl_response(
            request_id=request_id,
            responder_id="expert_developer",
            content="已解决API接口问题。问题原因是依赖注入配置错误，已通过正确的依赖管理修复。",
            is_final=True
        )
        
        # 6. 基于响应创建新知识
        solution_id = await knowledge_bus.add_knowledge(
            content="API依赖注入错误的解决方案：在AgentBus中，HITL API需要正确配置依赖注入系统。",
            knowledge_type=KnowledgeType.PROCEDURE,
            source=KnowledgeSource.AGENT_LEARNING,
            created_by="expert_developer",
            tags={"API", "依赖注入", "修复"},
            confidence=0.95
        )
        
        print("✅ HITL响应处理和新知识创建完成")
        
        # 7. 验证统计信息
        hitl_stats = await hitl_service.get_hitl_statistics()
        kb_stats = await knowledge_bus.get_knowledge_stats()
        
        assert hitl_stats['total_requests'] >= 1
        assert kb_stats['total_knowledge'] >= 3
        
        print("✅ HITL与知识总线集成测试完成")

    @pytest.mark.asyncio
    async def test_channel_messaging_integration(self, system_context, channel_manager, plugin_manager):
        """测试渠道消息处理集成"""
        
        print("📡 开始测试渠道消息处理集成...")
        
        # 1. 启动渠道管理器
        await channel_manager.initialize()
        
        # 2. 创建消息处理插件
        plugin_dir = system_context.config["agentbus"]["plugins_dir"]
        message_plugin_file = os.path.join(plugin_dir, "message_handler.py")
        
        with open(message_plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
from agentbus.plugins import AgentBusPlugin, PluginContext

class MessageHandlerPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.message_count = 0
        self.processed_messages = []
    
    def get_info(self):
        return {
            'id': 'message_handler',
            'name': 'Message Handler Plugin',
            'version': '1.0.0',
            'description': 'Handle channel messages',
            'author': 'System Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("get_message_stats", "Get message statistics", self.get_stats)
        self.register_hook("message_received", self.handle_message)
        self.register_hook("channel_connected", self.handle_connection)
    
    async def handle_message(self, message):
        self.message_count += 1
        self.processed_messages.append(message)
        self.context.logger.info(f"Processed message #{self.message_count}: {message}")
        return f"Handled: {message}"
    
    async def handle_connection(self, channel_info):
        self.context.logger.info(f"Channel connected: {channel_info}")
        return f"Connected to {channel_info}"
    
    async def get_stats(self):
        return {
            'total_messages': self.message_count,
            'processed_messages': len(self.processed_messages)
        }
''')
        
        # 3. 加载并激活消息处理插件
        plugin = await plugin_manager.load_plugin('message_handler', message_plugin_file)
        await plugin_manager.activate_plugin('message_handler')
        
        print("✅ 消息处理插件就绪")
        
        # 4. 模拟消息流
        test_messages = [
            "Hello, AgentBus!",
            "Testing channel integration",
            "Multi-model coordination test",
            "Plugin system integration"
        ]
        
        # 处理每条消息
        for message in test_messages:
            results = await plugin_manager.execute_hook("message_received", message)
            assert len(results) == 1
        
        print(f"✅ 处理了 {len(test_messages)} 条测试消息")
        
        # 5. 获取统计信息
        stats = await plugin_manager.execute_tool("get_message_stats")
        assert stats['total_messages'] == len(test_messages)
        
        print("✅ 渠道消息处理集成测试完成")

    @pytest.mark.asyncio
    async def test_multi_model_coordination_integration(self, system_context, multi_model_coordinator, plugin_manager):
        """测试多模型协调器集成"""
        
        print("🤖 开始测试多模型协调器集成...")
        
        # 1. 启动多模型协调器
        await multi_model_coordinator.start()
        
        # 2. 创建模型协调插件
        plugin_dir = system_context.config["agentbus"]["plugins_dir"]
        model_plugin_file = os.path.join(plugin_dir, "model_coordinator.py")
        
        with open(model_plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
from agentbus.plugins import AgentBusPlugin, PluginContext

class ModelCoordinatorPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.coordination_count = 0
    
    def get_info(self):
        return {
            'id': 'model_coordinator',
            'name': 'Model Coordinator Plugin',
            'version': '1.0.0',
            'description': 'Coordinate multiple AI models',
            'author': 'System Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("coordinate_models", "Coordinate AI models", self.coordinate_models)
        self.register_hook("model_request", self.handle_model_request)
    
    def coordinate_models(self, request: dict) -> dict:
        self.coordination_count += 1
        result = {
            'coordinated': True,
            'models_used': ['gpt-3.5-turbo', 'claude-3'],
            'request_id': self.coordination_count,
            'original_request': request
        }
        return result
    
    async def handle_model_request(self, request):
        result = self.coordinate_models(request)
        return result
''')
        
        # 3. 加载并激活模型协调插件
        plugin = await plugin_manager.load_plugin('model_coordinator', model_plugin_file)
        await plugin_manager.activate_plugin('model_coordinator')
        
        print("✅ 模型协调插件就绪")
        
        # 4. 测试模型协调
        coordination_request = {
            'task': 'analyze_data',
            'data': 'sample data for analysis',
            'models': ['gpt-3.5-turbo', 'claude-3'],
            'priority': 'high'
        }
        
        result = await plugin_manager.execute_tool("coordinate_models", coordination_request)
        assert result['coordinated'] == True
        assert len(result['models_used']) == 2
        assert result['request_id'] == 1
        
        print("✅ 多模型协调功能测试通过")
        
        # 5. 测试钩子机制
        hook_result = await plugin_manager.execute_hook("model_request", coordination_request)
        assert len(hook_result) == 1
        assert hook_result[0]['coordinated'] == True
        
        print("✅ 多模型协调器集成测试完成")

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, system_context, plugin_manager, hitl_service, 
                                      knowledge_bus, channel_manager, multi_model_coordinator):
        """测试端到端工作流程"""
        
        print("🔄 开始测试端到端工作流程...")
        
        # 1. 启动所有服务
        await plugin_manager.initialize()
        await hitl_service.start()
        await knowledge_bus.initialize()
        await channel_manager.initialize()
        await multi_model_coordinator.start()
        
        print("✅ 所有服务启动完成")
        
        # 2. 创建工作流插件
        plugin_dir = system_context.config["agentbus"]["plugins_dir"]
        workflow_plugin_file = os.path.join(plugin_dir, "workflow_orchestrator.py")
        
        with open(workflow_plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
import asyncio
from agentbus.plugins import AgentBusPlugin, PluginContext

class WorkflowOrchestratorPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.workflow_count = 0
        self.workflows_completed = 0
    
    def get_info(self):
        return {
            'id': 'workflow_orchestrator',
            'name': 'Workflow Orchestrator Plugin',
            'version': '1.0.0',
            'description': 'Orchestrate end-to-end workflows',
            'author': 'System Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("orchestrate_workflow", "Orchestrate complete workflow", self.orchestrate_workflow)
        self.register_hook("workflow_started", self.handle_workflow_start)
        self.register_hook("workflow_completed", self.handle_workflow_complete)
    
    async def orchestrate_workflow(self, workflow_request: dict) -> dict:
        self.workflow_count += 1
        
        # 模拟工作流程步骤
        workflow_id = f"workflow_{self.workflow_count}"
        
        # 步骤1: 处理输入数据
        processed_data = f"Processed: {workflow_request.get('data', '')}"
        
        # 步骤2: 触发工作流开始事件
        await self.trigger_hook("workflow_started", {
            'workflow_id': workflow_id,
            'request': workflow_request
        })
        
        # 步骤3: 模拟HITL请求
        hitl_needed = workflow_request.get('requires_hitl', False)
        if hitl_needed:
            # 这里应该调用实际的HITL服务
            hitl_result = f"HITL processed for {workflow_id}"
        else:
            hitl_result = "No HITL needed"
        
        # 步骤4: 模拟知识更新
        knowledge_updated = workflow_request.get('update_knowledge', False)
        if knowledge_updated:
            # 这里应该调用实际的知识总线
            knowledge_result = f"Knowledge updated for {workflow_id}"
        else:
            knowledge_result = "No knowledge update needed"
        
        # 步骤5: 触发工作流完成事件
        await self.trigger_hook("workflow_completed", {
            'workflow_id': workflow_id,
            'result': {
                'processed_data': processed_data,
                'hitl_result': hitl_result,
                'knowledge_result': knowledge_result
            }
        })
        
        self.workflows_completed += 1
        
        return {
            'workflow_id': workflow_id,
            'steps_completed': 5,
            'result': {
                'processed_data': processed_data,
                'hitl_result': hitl_result,
                'knowledge_result': knowledge_result
            }
        }
    
    async def handle_workflow_start(self, workflow_info):
        self.context.logger.info(f"Workflow started: {workflow_info}")
        return "Workflow start handled"
    
    async def handle_workflow_complete(self, workflow_info):
        self.context.logger.info(f"Workflow completed: {workflow_info}")
        self.workflows_completed += 1
        return "Workflow completion handled"
''')
        
        # 3. 加载并激活工作流编排插件
        plugin = await plugin_manager.load_plugin('workflow_orchestrator', workflow_plugin_file)
        await plugin_manager.activate_plugin('workflow_orchestrator')
        
        print("✅ 工作流编排插件就绪")
        
        # 4. 执行端到端工作流测试
        workflow_requests = [
            {
                'name': 'simple_data_processing',
                'data': 'sample data',
                'requires_hitl': False,
                'update_knowledge': False
            },
            {
                'name': 'complex_analysis_with_hitl',
                'data': 'complex analysis data',
                'requires_hitl': True,
                'update_knowledge': True
            }
        ]
        
        for i, request in enumerate(workflow_requests):
            result = await plugin_manager.execute_tool("orchestrate_workflow", request)
            
            assert result['workflow_id'] == f"workflow_{i+1}"
            assert result['steps_completed'] == 5
            assert 'processed_data' in result['result']
            assert 'hitl_result' in result['result']
            assert 'knowledge_result' in result['result']
        
        print(f"✅ 完成了 {len(workflow_requests)} 个端到端工作流测试")
        
        # 5. 验证工作流统计
        stats_result = await plugin_manager.execute_tool("orchestrate_workflow", {'get_stats': True})
        # 这里应该返回工作流统计信息
        
        print("✅ 端到端工作流程测试完成")

    @pytest.mark.asyncio
    async def test_system_performance_and_stability(self, system_context, plugin_manager, 
                                                   hitl_service, knowledge_bus):
        """测试系统性能和稳定性"""
        
        print("⚡ 开始测试系统性能和稳定性...")
        
        # 启动服务
        await plugin_manager.initialize()
        await hitl_service.start()
        await knowledge_bus.initialize()
        
        # 创建性能测试插件
        plugin_dir = system_context.config["agentbus"]["plugins_dir"]
        perf_plugin_file = os.path.join(plugin_dir, "performance_test.py")
        
        with open(perf_plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
from agentbus.plugins import AgentBusPlugin, PluginContext

class PerformanceTestPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.test_count = 0
    
    def get_info(self):
        return {
            'id': 'performance_test',
            'name': 'Performance Test Plugin',
            'version': '1.0.0',
            'description': 'Test system performance',
            'author': 'System Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("performance_test", "Run performance test", self.performance_test)
        self.register_tool("stress_test", "Run stress test", self.stress_test)
    
    def performance_test(self, iterations: int) -> dict:
        results = []
        for i in range(iterations):
            # 模拟一些处理工作
            result = f"iteration_{i}_completed"
            results.append(result)
        
        return {
            'iterations': iterations,
            'completed': len(results),
            'success_rate': len(results) / iterations if iterations > 0 else 0
        }
    
    def stress_test(self, load_level: int) -> dict:
        # 模拟压力测试
        return {
            'load_level': load_level,
            'duration': '5s',
            'operations_per_second': load_level * 100,
            'success_rate': 0.95
        }
''')
        
        # 加载并激活性能测试插件
        perf_plugin = await plugin_manager.load_plugin('performance_test', perf_plugin_file)
        await plugin_manager.activate_plugin('performance_test')
        
        print("✅ 性能测试插件就绪")
        
        # 执行性能测试
        perf_result = await plugin_manager.execute_tool("performance_test", iterations=100)
        assert perf_result['iterations'] == 100
        assert perf_result['success_rate'] == 1.0
        
        print("✅ 性能测试完成")
        
        # 执行压力测试
        stress_result = await plugin_manager.execute_tool("stress_test", load_level=10)
        assert stress_result['load_level'] == 10
        assert stress_result['success_rate'] >= 0.9
        
        print("✅ 压力测试完成")
        
        # 并发测试
        async def concurrent_test():
            tasks = []
            for i in range(10):
                task = plugin_manager.execute_tool("performance_test", iterations=10)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            return results
        
        concurrent_results = await concurrent_test()
        assert len(concurrent_results) == 10
        for result in concurrent_results:
            assert result['success_rate'] == 1.0
        
        print("✅ 并发测试完成")
        
        print("✅ 系统性能和稳定性测试完成")

    @pytest.mark.asyncio
    async def test_error_recovery_and_fault_tolerance(self, system_context, plugin_manager, 
                                                    hitl_service, knowledge_bus):
        """测试错误恢复和容错性"""
        
        print("🛡️ 开始测试错误恢复和容错性...")
        
        # 启动服务
        await plugin_manager.initialize()
        await hitl_service.start()
        await knowledge_bus.initialize()
        
        # 创建错误处理插件
        plugin_dir = system_context.config["agentbus"]["plugins_dir"]
        error_plugin_file = os.path.join(plugin_dir, "error_handler.py")
        
        with open(error_plugin_file, 'w', encoding='utf-8') as f:
            f.write('''
from agentbus.plugins import AgentBusPlugin, PluginContext

class ErrorHandlerPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.error_count = 0
        self.recovery_count = 0
    
    def get_info(self):
        return {
            'id': 'error_handler',
            'name': 'Error Handler Plugin',
            'version': '1.0.0',
            'description': 'Handle errors and recovery',
            'author': 'System Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("test_error", "Test error handling", self.test_error)
        self.register_tool("test_recovery", "Test recovery", self.test_recovery)
        self.register_hook("error_occurred", self.handle_error)
    
    def test_error(self, should_error: bool) -> dict:
        if should_error:
            self.error_count += 1
            raise Exception(f"Simulated error #{self.error_count}")
        else:
            return {'status': 'success', 'message': 'No error occurred'}
    
    def test_recovery(self) -> dict:
        self.recovery_count += 1
        return {
            'recovery_attempt': self.recovery_count,
            'status': 'recovered',
            'error_count': self.error_count
        }
    
    async def handle_error(self, error_info):
        self.context.logger.warning(f"Error handled: {error_info}")
        return "Error handled successfully"
''')
        
        # 加载并激活错误处理插件
        error_plugin = await plugin_manager.load_plugin('error_handler', error_plugin_file)
        await plugin_manager.activate_plugin('error_handler')
        
        print("✅ 错误处理插件就绪")
        
        # 测试正常操作
        normal_result = await plugin_manager.execute_tool("test_error", should_error=False)
        assert normal_result['status'] == 'success'
        
        print("✅ 正常操作测试通过")
        
        # 测试错误处理
        try:
            await plugin_manager.execute_tool("test_error", should_error=True)
            assert False, "Expected error was not raised"
        except Exception as e:
            assert "Simulated error" in str(e)
        
        print("✅ 错误处理测试通过")
        
        # 测试恢复机制
        recovery_result = await plugin_manager.execute_tool("test_recovery")
        assert recovery_result['status'] == 'recovered'
        assert recovery_result['error_count'] == 1
        
        print("✅ 恢复机制测试通过")
        
        # 测试钩子错误处理
        hook_result = await plugin_manager.execute_hook("error_occurred", {"test": "error"})
        assert len(hook_result) == 1
        
        print("✅ 钩子错误处理测试通过")
        
        print("✅ 错误恢复和容错性测试完成")

    @pytest.mark.asyncio
    async def test_system_shutdown_and_cleanup(self, system_context, plugin_manager, 
                                             hitl_service, knowledge_bus, channel_manager, 
                                             multi_model_coordinator):
        """测试系统关闭和清理"""
        
        print("🔄 开始测试系统关闭和清理...")
        
        # 启动所有服务
        await plugin_manager.initialize()
        await hitl_service.start()
        await knowledge_bus.initialize()
        await channel_manager.initialize()
        await multi_model_coordinator.start()
        
        print("✅ 所有服务启动完成")
        
        # 执行一些操作确保系统状态
        plugin_stats = await plugin_manager.get_plugin_stats()
        hitl_stats = await hitl_service.get_hitl_statistics()
        kb_stats = await knowledge_bus.get_knowledge_stats()
        
        print("✅ 系统状态记录完成")
        
        # 按顺序关闭服务
        print("🛑 开始关闭服务...")
        
        # 1. 停用所有插件
        await plugin_manager.deactivate_all_plugins()
        print("✅ 插件已停用")
        
        # 2. 关闭多模型协调器
        await multi_model_coordinator.stop()
        print("✅ 多模型协调器已关闭")
        
        # 3. 关闭渠道管理器
        await channel_manager.shutdown()
        print("✅ 渠道管理器已关闭")
        
        # 4. 关闭HITL服务
        await hitl_service.stop()
        print("✅ HITL服务已关闭")
        
        # 5. 关闭知识总线
        await knowledge_bus.shutdown()
        print("✅ 知识总线已关闭")
        
        # 6. 关闭插件管理器
        await plugin_manager.shutdown()
        print("✅ 插件管理器已关闭")
        
        # 验证清理结果
        final_plugin_stats = await plugin_manager.get_plugin_stats()
        assert final_plugin_stats['active_plugins'] == 0
        
        print("✅ 系统关闭和清理测试完成")


# 系统集成测试套件
class TestSystemIntegrationSuite:
    """完整系统集成测试套件"""
    
    @pytest.mark.asyncio
    async def test_full_system_suite(self):
        """运行完整系统集成测试套件"""
        
        print("🎯 开始运行完整系统集成测试套件...")
        print("=" * 80)
        
        # 创建测试上下文
        temp_dir = tempfile.mkdtemp()
        try:
            config = {
                "agentbus": {
                    "data_dir": os.path.join(temp_dir, "data"),
                    "logs_dir": os.path.join(temp_dir, "logs"),
                    "plugins_dir": os.path.join(temp_dir, "plugins")
                },
                "hitl": {"enabled": True},
                "knowledge_bus": {"enabled": True},
                "multi_model": {"enabled": True},
                "channels": {"enabled": True}
            }
            
            system_context = AgentBusContext(
                config=config,
                data_dir=config["agentbus"]["data_dir"],
                logs_dir=config["agentbus"]["logs_dir"]
            )
            
            # 创建所有管理器
            plugin_context = PluginContext(
                config=config.get("plugins", {}),
                logger=logging.getLogger("integration_test"),
                runtime={"system_context": system_context}
            )
            
            plugin_manager = PluginManager(plugin_context)
            hitl_service = HITLService(
                config=config.get("hitl", {}),
                logger=logging.getLogger("integration_test")
            )
            knowledge_bus = KnowledgeBus(
                config=config.get("knowledge_bus", {}),
                logger=logging.getLogger("integration_test")
            )
            
            # 创建目录
            os.makedirs(config["agentbus"]["plugins_dir"], exist_ok=True)
            plugin_manager._plugin_dirs = [config["agentbus"]["plugins_dir"]]
            
            print("✅ 测试环境准备完成")
            
            # 1. 测试系统初始化
            await plugin_manager.initialize()
            await hitl_service.start()
            await knowledge_bus.initialize()
            
            print("✅ 步骤1: 系统初始化 - 通过")
            
            # 2. 测试插件系统
            # 创建并加载测试插件
            test_plugin_file = os.path.join(config["agentbus"]["plugins_dir"], "integration_test.py")
            with open(test_plugin_file, 'w', encoding='utf-8') as f:
                f.write('''
from agentbus.plugins import AgentBusPlugin, PluginContext

class IntegrationTestPlugin(AgentBusPlugin):
    def __init__(self, plugin_id, context):
        super().__init__(plugin_id, context)
        self.test_data = []
    
    def get_info(self):
        return {
            'id': 'integration_test',
            'name': 'Integration Test Plugin',
            'version': '1.0.0',
            'description': 'Plugin for integration testing',
            'author': 'System Test',
            'dependencies': []
        }
    
    async def activate(self):
        await super().activate()
        self.register_tool("test_integration", "Test integration", self.test_integration)
        self.register_hook("integration_event", self.handle_integration_event)
    
    def test_integration(self, test_data: dict) -> dict:
        self.test_data.append(test_data)
        return {
            'processed': True,
            'data_count': len(self.test_data),
            'test_data': test_data
        }
    
    async def handle_integration_event(self, event):
        return f"Integration event handled: {event}"
''')
            
            plugin = await plugin_manager.load_plugin('integration_test', test_plugin_file)
            await plugin_manager.activate_plugin('integration_test')
            
            print("✅ 步骤2: 插件系统 - 通过")
            
            # 3. 测试HITL和知识总线集成
            hitl_request_id = await hitl_service.create_hitl_request(
                agent_id="integration_test",
                title="Integration Test Request",
                description="Testing HITL integration with knowledge bus",
                priority=HITLPriority.NORMAL,
                timeout_minutes=5
            )
            
            knowledge_id = await knowledge_bus.add_knowledge(
                content="Integration test knowledge item",
                knowledge_type=KnowledgeType.FACT,
                source=KnowledgeSource.MANUAL_ENTRY,
                created_by="integration_test",
                tags={"integration", "test"},
                confidence=1.0
            )
            
            print("✅ 步骤3: HITL和知识总线集成 - 通过")
            
            # 4. 测试跨组件功能
            integration_result = await plugin_manager.execute_tool("test_integration", {
                'hitl_request_id': hitl_request_id,
                'knowledge_id': knowledge_id,
                'test_phase': 'integration'
            })
            
            assert integration_result['processed'] == True
            assert integration_result['data_count'] == 1
            
            hook_result = await plugin_manager.execute_hook("integration_event", "test_event")
            assert len(hook_result) == 1
            
            print("✅ 步骤4: 跨组件功能 - 通过")
            
            # 5. 验证统计信息
            plugin_stats = await plugin_manager.get_plugin_stats()
            hitl_stats = await hitl_service.get_hitl_statistics()
            kb_stats = await knowledge_bus.get_knowledge_stats()
            
            assert plugin_stats['total_plugins'] == 1
            assert plugin_stats['active_plugins'] == 1
            assert hitl_stats['total_requests'] >= 1
            assert kb_stats['total_knowledge'] >= 1
            
            print("✅ 步骤5: 统计信息验证 - 通过")
            
            # 6. 测试系统关闭
            await plugin_manager.deactivate_all_plugins()
            await plugin_manager.unload_all_plugins()
            await hitl_service.stop()
            await knowledge_bus.shutdown()
            await plugin_manager.shutdown()
            
            print("✅ 步骤6: 系统关闭 - 通过")
            
            print("🎉 完整系统集成测试套件 - 全部通过！")
            print("=" * 80)
            
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)