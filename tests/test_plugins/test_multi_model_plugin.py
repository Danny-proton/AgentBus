#!/usr/bin/env python3
"""
多模型协调器插件测试
Multi-Model Coordinator Plugin Tests

测试多模型协调器插件的各项功能，包括：
- 插件激活和停用
- 模型管理工具
- 任务处理工具
- 钩子系统
- 命令系统
- 统计和监控功能
"""

import asyncio
import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from agentbus.plugins import PluginContext, PluginManager
from agentbus.plugins.multi_model_plugin import MultiModelPlugin
from agentbus.services.multi_model_coordinator import (
    ModelConfig, TaskRequest, TaskType, TaskPriority, ModelType
)


class TestMultiModelPlugin:
    """多模型协调器插件测试类"""
    
    @pytest.fixture
    def plugin_context(self):
        """创建测试用的插件上下文"""
        config = {
            'default_models': [],
            'fusion_strategy': 'best',
            'max_concurrent_tasks': 10,
            'enable_monitoring': True
        }
        
        logger = logging.getLogger('test_plugin')
        logger.setLevel(logging.DEBUG)
        
        runtime = {
            'test_mode': True
        }
        
        return PluginContext(
            config=config,
            logger=logger,
            runtime=runtime
        )
    
    @pytest.fixture
    def plugin(self, plugin_context):
        """创建测试用的插件实例"""
        return MultiModelPlugin("test_multi_model_plugin", plugin_context)
    
    @pytest.fixture
    def sample_model_config(self):
        """创建示例模型配置"""
        return ModelConfig(
            model_id="test-gpt-4",
            model_name="Test GPT-4",
            model_type=ModelType.TEXT_GENERATION,
            provider="openai",
            capabilities=[TaskType.TEXT_GENERATION, TaskType.QUESTION_ANSWERING],
            cost_per_token=0.00003,
            quality_score=0.95,
            max_tokens=4096,
            temperature=0.7,
            api_key="test-key"
        )
    
    @pytest.fixture
    def sample_task_request(self):
        """创建示例任务请求"""
        return TaskRequest(
            task_id="test-task-001",
            task_type=TaskType.TEXT_GENERATION,
            content="请写一段关于AI的介绍",
            priority=TaskPriority.NORMAL,
            required_capabilities=[TaskType.TEXT_GENERATION],
            max_cost=0.01
        )
    
    def test_plugin_initialization(self, plugin):
        """测试插件初始化"""
        assert plugin.plugin_id == "test_multi_model_plugin"
        assert plugin.coordinator is not None
        assert plugin.plugin_stats['tasks_submitted'] == 0
        assert plugin.plugin_stats['tasks_completed'] == 0
        assert plugin.plugin_stats['models_registered'] == 0
        assert len(plugin.monitored_tasks) == 0
    
    def test_get_info(self, plugin):
        """测试获取插件信息"""
        info = plugin.get_info()
        
        assert info['id'] == plugin.plugin_id
        assert info['name'] == 'Multi-Model Coordinator Plugin'
        assert info['version'] == '1.0.0'
        assert 'capabilities' in info
        assert 'config_schema' in info
        assert 'multi_model_coordination' in info['capabilities']
    
    @pytest.mark.asyncio
    async def test_plugin_activation(self, plugin):
        """测试插件激活"""
        # 模拟协调器初始化成功
        with patch.object(plugin.coordinator, 'initialize', return_value=True) as mock_init:
            success = await plugin.activate()
            
            assert success is True
            assert plugin.status.value == 'active'
            mock_init.assert_called_once()
            
            # 检查工具是否注册
            tools = plugin.get_tools()
            assert len(tools) > 0
            tool_names = [tool.name for tool in tools]
            assert 'submit_multi_model_task' in tool_names
            assert 'register_model' in tool_names
            assert 'get_task_result' in tool_names
            assert 'list_models' in tool_names
            assert 'get_coordinator_stats' in tool_names
            
            # 检查钩子是否注册
            hooks = plugin.get_hooks()
            assert 'multi_model_task_submitted' in hooks
            assert 'multi_model_task_completed' in hooks
            assert 'model_registered' in hooks
            
            # 检查命令是否注册
            commands = plugin.get_commands()
            command_names = [cmd['command'] for cmd in commands]
            assert '/models' in command_names
            assert '/tasks' in command_names
            assert '/stats' in command_names
            assert '/health' in command_names
    
    @pytest.mark.asyncio
    async def test_plugin_activation_failure(self, plugin):
        """测试插件激活失败"""
        # 模拟协调器初始化失败
        with patch.object(plugin.coordinator, 'initialize', return_value=False):
            with pytest.raises(RuntimeError, match="Failed to initialize"):
                await plugin.activate()
            
            assert plugin.status.value == 'error'
    
    @pytest.mark.asyncio
    async def test_plugin_deactivation(self, plugin):
        """测试插件停用"""
        # 先激活插件
        with patch.object(plugin.coordinator, 'initialize', return_value=True):
            await plugin.activate()
        
        # 模拟监控任务和协调器关闭
        plugin.monitored_tasks['test-task'] = 1234567890
        with patch.object(plugin.coordinator, 'shutdown', return_value=None) as mock_shutdown:
            success = await plugin.deactivate()
            
            assert success is True
            assert plugin.status.value == 'deactivated'
            assert len(plugin.monitored_tasks) == 0
            mock_shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_multi_model_task(self, plugin):
        """测试提交多模型任务"""
        await plugin.activate()
        
        # 模拟协调器提交任务
        test_task_id = "test-task-123"
        with patch.object(plugin.coordinator, 'submit_task', return_value=test_task_id) as mock_submit:
            with patch.object(plugin.coordinator, 'get_available_models', return_value=[]):
                result = await plugin.submit_multi_model_task(
                    task_type="text_generation",
                    content="测试内容",
                    priority="normal"
                )
                
                assert result['success'] is True
                assert result['task_id'] == test_task_id
                assert '任务已成功提交' in result['message']
                
                # 检查统计更新
                assert plugin.plugin_stats['tasks_submitted'] == 1
                
                mock_submit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_multi_model_task_invalid_type(self, plugin):
        """测试提交无效类型任务"""
        await plugin.activate()
        
        result = await plugin.submit_multi_model_task(
            task_type="invalid_type",
            content="测试内容"
        )
        
        assert result['success'] is False
        assert '无效的任务参数' in result['error']
        assert result['task_id'] is None
    
    @pytest.mark.asyncio
    async def test_register_model_tool(self, plugin, sample_model_config):
        """测试注册模型工具"""
        await plugin.activate()
        
        # 模拟协调器注册模型
        with patch.object(plugin.coordinator, 'register_model', return_value=True) as mock_register:
            result = plugin.register_model_tool(
                model_id=sample_model_config.model_id,
                model_name=sample_model_config.model_name,
                model_type=sample_model_config.model_type.value,
                provider=sample_model_config.provider,
                capabilities=[cap.value for cap in sample_model_config.capabilities],
                api_key=sample_model_config.api_key,
                cost_per_token=sample_model_config.cost_per_token,
                quality_score=sample_model_config.quality_score
            )
            
            assert result['success'] is True
            assert result['model_id'] == sample_model_config.model_id
            assert '注册成功' in result['message']
            
            # 检查统计更新
            assert plugin.plugin_stats['models_registered'] == 1
            
            mock_register.assert_called_once()
    
    def test_register_model_tool_invalid_type(self, plugin):
        """测试注册无效类型模型"""
        result = plugin.register_model_tool(
            model_id="test-model",
            model_name="Test Model",
            model_type="invalid_type",
            provider="test",
            capabilities=["text_generation"]
        )
        
        assert result['success'] is False
        assert '无效的模型参数' in result['error']
        assert result['model_id'] == "test-model"
    
    @pytest.mark.asyncio
    async def test_unregister_model_tool(self, plugin):
        """测试注销模型工具"""
        await plugin.activate()
        
        # 模拟协调器注销模型
        with patch.object(plugin.coordinator, 'unregister_model', return_value=True) as mock_unregister:
            result = plugin.unregister_model_tool("test-model")
            
            assert result['success'] is True
            assert result['model_id'] == "test-model"
            assert '注销成功' in result['message']
            
            mock_unregister.assert_called_once_with("test-model")
    
    @pytest.mark.asyncio
    async def test_get_task_result_tool(self, plugin):
        """测试获取任务结果工具"""
        await plugin.activate()
        
        # 模拟任务结果
        from agentbus.services.multi_model_coordinator import TaskResult, TaskStatus
        
        mock_result = TaskResult(
            task_id="test-task",
            status=TaskStatus.COMPLETED,
            final_content="测试结果",
            total_time=1.5,
            total_cost=0.001,
            fusion_method="best"
        )
        
        with patch.object(plugin.coordinator, 'get_task_result', return_value=mock_result):
            result = await plugin.get_task_result_tool("test-task")
            
            assert result['success'] is True
            assert result['task_id'] == "test-task"
            assert result['status'] == "completed"
            assert result['final_content'] == "测试结果"
            assert result['total_time'] == 1.5
            assert result['total_cost'] == 0.001
    
    @pytest.mark.asyncio
    async def test_get_task_result_not_found(self, plugin):
        """测试获取不存在的任务结果"""
        await plugin.activate()
        
        with patch.object(plugin.coordinator, 'get_task_result', return_value=None):
            result = await plugin.get_task_result_tool("non-existent-task")
            
            assert result['success'] is False
            assert '任务不存在' in result['error']
    
    @pytest.mark.asyncio
    async def test_cancel_task_tool(self, plugin):
        """测试取消任务工具"""
        await plugin.activate()
        
        # 添加监控任务
        plugin.monitored_tasks['test-task'] = 1234567890
        
        # 模拟协调器取消任务
        with patch.object(plugin.coordinator, 'cancel_task', return_value=True):
            result = await plugin.cancel_task_tool("test-task")
            
            assert result['success'] is True
            assert result['task_id'] == "test-task"
            assert '取消成功' in result['message']
            assert 'test-task' not in plugin.monitored_tasks
    
    @pytest.mark.asyncio
    async def test_list_models_tool(self, plugin):
        """测试列出模型工具"""
        await plugin.activate()
        
        # 模拟模型列表
        mock_models = [
            ModelConfig(
                model_id="test-model-1",
                model_name="Test Model 1",
                model_type=ModelType.TEXT_GENERATION,
                provider="openai",
                capabilities=[TaskType.TEXT_GENERATION]
            ),
            ModelConfig(
                model_id="test-model-2",
                model_name="Test Model 2",
                model_type=ModelType.CODE_GENERATION,
                provider="anthropic",
                capabilities=[TaskType.CODE_GENERATION]
            )
        ]
        
        with patch.object(plugin.coordinator, 'get_available_models', return_value=mock_models):
            result = plugin.list_models_tool()
            
            assert result['success'] is True
            assert result['total_count'] == 2
            assert len(result['models']) == 2
            assert result['models'][0]['model_id'] == "test-model-1"
            assert result['models'][1]['model_id'] == "test-model-2"
    
    @pytest.mark.asyncio
    async def test_list_models_tool_with_filter(self, plugin):
        """测试带过滤条件的列出模型工具"""
        await plugin.activate()
        
        # 模拟过滤后的模型列表
        mock_models = [
            ModelConfig(
                model_id="test-text-model",
                model_name="Test Text Model",
                model_type=ModelType.TEXT_GENERATION,
                provider="openai",
                capabilities=[TaskType.TEXT_GENERATION]
            )
        ]
        
        with patch.object(plugin.coordinator, 'get_available_models', return_value=mock_models):
            result = plugin.list_models_tool(task_type="text_generation")
            
            assert result['success'] is True
            assert result['filtered_by'] == "text_generation"
            assert result['total_count'] == 1
            assert result['models'][0]['model_type'] == "text_generation"
    
    def test_list_models_tool_invalid_type(self, plugin):
        """测试列出无效类型模型"""
        result = plugin.list_models_tool(task_type="invalid_type")
        
        assert result['success'] is False
        assert '无效的任务类型' in result['error']
        assert result['models'] == []
        assert result['total_count'] == 0
    
    @pytest.mark.asyncio
    async def test_get_coordinator_stats_tool(self, plugin):
        """测试获取协调器统计工具"""
        await plugin.activate()
        
        # 模拟协调器统计
        mock_stats = {
            'active_tasks': 2,
            'total_tasks': 10,
            'completed_tasks': 8,
            'success_rate': 0.8,
            'avg_processing_time': 2.5,
            'avg_cost': 0.001,
            'registered_models': 3,
            'active_models': 3
        }
        
        with patch.object(plugin.coordinator, 'get_coordinator_stats', return_value=mock_stats):
            result = await plugin.get_coordinator_stats_tool()
            
            assert result['success'] is True
            assert 'stats' in result
            assert result['stats']['active_tasks'] == 2
            assert result['stats']['registered_models'] == 3
            assert 'plugin_stats' in result['stats']
    
    def test_get_plugin_stats_tool(self, plugin):
        """测试获取插件统计工具"""
        plugin.plugin_stats['tasks_submitted'] = 5
        plugin.plugin_stats['tasks_completed'] = 4
        plugin.monitored_tasks['task1'] = 123
        
        result = plugin.get_plugin_stats_tool()
        
        assert result['success'] is True
        assert result['plugin_id'] == plugin.plugin_id
        assert result['stats']['tasks_submitted'] == 5
        assert result['stats']['tasks_completed'] == 4
        assert result['monitored_tasks'] == 1
        assert result['registered_tools'] > 0
        assert result['registered_hooks'] > 0
        assert result['registered_commands'] > 0
    
    def test_prepare_prompt_tool(self, plugin):
        """测试准备提示词工具"""
        result = plugin.prepare_prompt_tool(
            task_type="text_generation",
            content="原始内容"
        )
        
        assert result['success'] is True
        assert result['original_content'] == "原始内容"
        assert result['task_type'] == "text_generation"
        assert 'prepared_prompt' in result
    
    def test_recommend_models_tool(self, plugin):
        """测试模型推荐工具"""
        # 模拟可用模型
        mock_models = [
            ModelConfig(
                model_id="high-quality-model",
                model_name="High Quality Model",
                model_type=ModelType.TEXT_GENERATION,
                provider="openai",
                capabilities=[TaskType.TEXT_GENERATION],
                quality_score=0.95,
                cost_per_token=0.00003
            ),
            ModelConfig(
                model_id="low-cost-model",
                model_name="Low Cost Model",
                model_type=ModelType.TEXT_GENERATION,
                provider="local",
                capabilities=[TaskType.TEXT_GENERATION],
                quality_score=0.75,
                cost_per_token=0.0
            )
        ]
        
        with patch.object(plugin.coordinator, 'get_available_models', return_value=mock_models):
            result = plugin.recommend_models_tool(
                task_type="text_generation",
                max_models=2
            )
            
            assert result['success'] is True
            assert result['task_type'] == "text_generation"
            assert len(result['recommended_models']) == 2
            assert result['recommended_models'][0]['model_id'] == "high-quality-model"  # 高质量优先
    
    def test_recommend_models_tool_invalid_type(self, plugin):
        """测试无效类型的模型推荐"""
        result = plugin.recommend_models_tool(task_type="invalid_type")
        
        assert result['success'] is False
        assert '无效的任务类型' in result['error']
        assert result['recommended_models'] == []
    
    @pytest.mark.asyncio
    async def test_hook_handlers(self, plugin):
        """测试钩子处理方法"""
        # 测试任务提交钩子
        task_data = {'task_id': 'test-task', 'task_type': 'text_generation'}
        await plugin.on_task_submitted(task_data)  # 应该不报错
        
        # 测试任务完成钩子
        plugin.monitored_tasks['test-task'] = 1234567890
        await plugin.on_task_completed(task_data)
        assert 'test-task' not in plugin.monitored_tasks
        assert plugin.plugin_stats['tasks_completed'] == 1
        
        # 测试任务失败钩子
        await plugin.on_task_failed(task_data)
        assert plugin.plugin_stats['tasks_failed'] == 1
        
        # 测试模型注册钩子
        model_data = {'model_id': 'test-model', 'model_name': 'Test Model'}
        await plugin.on_model_registered(model_data)  # 应该不报错
        
        await plugin.on_model_unregistered(model_data)  # 应该不报错
    
    @pytest.mark.asyncio
    async def test_command_handlers(self, plugin):
        """测试命令处理方法"""
        await plugin.activate()
        
        # 测试模型命令
        result = await plugin.handle_models_command("")
        assert "📊 模型列表" in result
        
        # 测试任务命令
        with patch.object(plugin, 'get_coordinator_stats_tool') as mock_stats:
            mock_stats.return_value = {
                'success': True,
                'stats': {
                    'active_tasks': 1,
                    'total_tasks': 5,
                    'success_rate': 0.8,
                    'monitored_tasks': 1,
                    'avg_monitor_time': 2.5
                }
            }
            result = await plugin.handle_tasks_command("")
            assert "📋 任务状态" in result
        
        # 测试统计命令
        with patch.object(plugin, 'get_plugin_stats_tool') as mock_plugin_stats:
            with patch.object(plugin, 'get_coordinator_stats_tool') as mock_coord_stats:
                mock_plugin_stats.return_value = {
                    'success': True,
                    'stats': {
                        'tasks_submitted': 5,
                        'tasks_completed': 4,
                        'tasks_failed': 1,
                        'models_registered': 3,
                        'total_processing_time': 10.0,
                        'total_cost': 0.005
                    }
                }
                mock_coord_stats.return_value = {
                    'success': True,
                    'stats': {
                        'active_tasks': 1,
                        'avg_processing_time': 2.5,
                        'avg_cost': 0.001,
                        'active_models': 3
                    }
                }
                result = await plugin.handle_stats_command("")
                assert "📈 统计信息" in result
        
        # 测试健康检查命令
        with patch.object(plugin, 'get_coordinator_stats_tool') as mock_health:
            mock_health.return_value = {
                'success': True,
                'stats': {
                    'active_tasks': 5,
                    'success_rate': 0.9,
                    'registered_models': 3,
                    'active_models': 3
                }
            }
            result = await plugin.handle_health_command("")
            assert "💊 健康检查" in result
            assert "🟢 健康" in result
    
    @pytest.mark.asyncio
    async def test_config_management(self, plugin):
        """测试配置管理"""
        # 测试获取配置
        assert plugin.get_config('enable_monitoring', False) is True
        assert plugin.get_config('non_existent', 'default') == 'default'
        
        # 测试设置配置
        plugin.set_config('test_key', 'test_value')
        assert plugin.get_config('test_key') == 'test_value'
    
    @pytest.mark.asyncio
    async def test_runtime_management(self, plugin):
        """测试运行时变量管理"""
        # 测试获取运行时变量
        assert plugin.get_runtime('test_mode') is True
        assert plugin.get_runtime('non_existent', 'default') == 'default'
        
        # 测试设置运行时变量
        plugin.set_runtime('test_runtime_key', 'test_runtime_value')
        assert plugin.get_runtime('test_runtime_key') == 'test_runtime_value'
    
    @pytest.mark.asyncio
    async def test_plugin_integration(self, plugin):
        """测试插件集成功能"""
        await plugin.activate()
        
        # 注册一个模型
        register_result = plugin.register_model_tool(
            model_id="integration-test-model",
            model_name="Integration Test Model",
            model_type="text_generation",
            provider="test",
            capabilities=["text_generation"]
        )
        assert register_result['success'] is True
        
        # 提交一个任务
        task_result = await plugin.submit_multi_model_task(
            task_type="text_generation",
            content="集成测试内容"
        )
        assert task_result['success'] is True
        
        # 获取插件统计
        stats_result = plugin.get_plugin_stats_tool()
        assert stats_result['success'] is True
        assert stats_result['stats']['models_registered'] >= 1
        assert stats_result['stats']['tasks_submitted'] >= 1
    
    @pytest.mark.asyncio
    async def test_plugin_error_handling(self, plugin):
        """测试插件错误处理"""
        await plugin.activate()
        
        # 测试不存在的工具
        with pytest.raises(ValueError, match="Tool 'non_existent_tool' not found"):
            await plugin.execute_tool('non_existent_tool')
        
        # 测试钩子触发错误
        with patch.object(plugin, 'get_hooks', return_value={'test_event': [MagicMock(handler=lambda x: 1/0)]}):
            await plugin._trigger_hook('test_event', {})
            # 错误应该被记录但不应该抛出异常
    
    @pytest.mark.asyncio
    async def test_plugin_string_representation(self, plugin):
        """测试插件字符串表示"""
        str_repr = str(plugin)
        assert "AgentBusPlugin" in str_repr
        assert plugin.plugin_id in str_repr
        
        repr_str = repr(plugin)
        assert "AgentBusPlugin" in repr_str
        assert plugin.plugin_id in repr_str
        assert "tools=" in repr_str
        assert "hooks=" in repr_str


class TestPluginIntegration:
    """插件集成测试类"""
    
    @pytest.mark.asyncio
    async def test_plugin_manager_integration(self):
        """测试插件管理器集成"""
        # 创建插件管理器
        manager = PluginManager()
        
        # 创建插件上下文
        context = PluginContext(
            config={'test_mode': True},
            logger=logging.getLogger('test'),
            runtime={}
        )
        
        # 创建插件实例
        plugin = MultiModelPlugin("integration_test_plugin", context)
        
        # 激活插件
        success = await plugin.activate()
        assert success is True
        
        # 检查插件状态
        assert plugin.status.value == 'active'
        
        # 获取插件信息
        info = plugin.get_info()
        assert info['name'] == 'Multi-Model Coordinator Plugin'
        
        # 停用插件
        success = await plugin.deactivate()
        assert success is True
    
    @pytest.mark.asyncio
    async def test_plugin_with_coordinator_lifecycle(self):
        """测试插件与协调器生命周期"""
        context = PluginContext(
            config={'enable_monitoring': True},
            logger=logging.getLogger('test'),
            runtime={}
        )
        
        plugin = MultiModelPlugin("lifecycle_test_plugin", context)
        
        # 测试激活
        await plugin.activate()
        assert plugin.coordinator.is_running is True
        
        # 执行一些操作
        plugin.register_model_tool(
            model_id="lifecycle-model",
            model_name="Lifecycle Model",
            model_type="text_generation",
            provider="test",
            capabilities=["text_generation"]
        )
        
        # 测试停用
        await plugin.deactivate()
        assert plugin.status.value == 'deactivated'


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v"])