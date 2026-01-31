"""
HITL插件测试模块

测试HITL插件的各项功能，包括：
- 插件激活和停用
- HITL工具注册和使用
- HITL钩子注册和处理
- HITL命令注册和处理
- 与原有HITL服务的兼容性
"""

import asyncio
import pytest
import json
import logging
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any

from plugins import PluginContext, PluginManager
from plugins.hitl_plugin import HITLPlugin
from services.hitl import (
    HITLRequest, HITLResponse, HITLStatus, HITLPriority
)


class TestHITLPlugin:
    """HITL插件测试类"""
    
    @pytest.fixture
    def plugin_context(self):
        """创建测试用的插件上下文"""
        return PluginContext(
            config={
                'hitl_plugin': {
                    'default_timeout': 30,
                    'enable_notifications': True
                }
            },
            logger=logging.getLogger('test_hitl_plugin'),
            runtime={}
        )
    
    @pytest.fixture
    def hitl_plugin(self, plugin_context):
        """创建HITL插件实例"""
        return HITLPlugin('test_hitl_plugin', plugin_context)
    
    @pytest.fixture
    def plugin_manager(self, plugin_context):
        """创建插件管理器"""
        return PluginManager(plugin_context)
    
    def test_plugin_info(self, hitl_plugin):
        """测试插件信息获取"""
        info = hitl_plugin.get_info()
        
        assert info['id'] == 'test_hitl_plugin'
        assert info['name'] == 'HITL Plugin'
        assert info['version'] == '1.0.0'
        assert 'capabilities' in info
        assert 'hitl_request_management' in info['capabilities']
    
    @pytest.mark.asyncio
    async def test_plugin_activation(self, hitl_plugin):
        """测试插件激活"""
        # 模拟服务启动
        with patch.object(hitl_plugin.hitl_service, 'start', new_callable=AsyncMock) as mock_start:
            success = await hitl_plugin.activate()
        
        assert success is True
        assert hitl_plugin.status.value == 'active'
        
        # 验证工具已注册
        tools = hitl_plugin.get_tools()
        tool_names = [tool.name for tool in tools]
        assert 'create_hitl_request' in tool_names
        assert 'submit_hitl_response' in tool_names
        assert 'get_hitl_request' in tool_names
        assert 'list_active_hitl_requests' in tool_names
        assert 'get_hitl_statistics' in tool_names
        
        # 验证钩子已注册
        hooks = hitl_plugin.get_hooks()
        assert 'hitl_request_before_create' in hooks
        assert 'hitl_request_after_create' in hooks
        assert 'hitl_response_before_submit' in hooks
        assert 'hitl_response_after_submit' in hooks
        assert 'hitl_request_timeout' in hooks
        assert 'hitl_request_cancelled' in hooks
        
        # 验证命令已注册
        commands = hitl_plugin.get_commands()
        command_names = [cmd['command'] for cmd in commands]
        assert '/hitl-status' in command_names
        assert '/hitl-list' in command_names
        assert '/hitl-cancel' in command_names
    
    @pytest.mark.asyncio
    async def test_plugin_deactivation(self, hitl_plugin):
        """测试插件停用"""
        # 先激活插件
        await hitl_plugin.activate()
        
        # 模拟服务停止
        with patch.object(hitl_plugin.hitl_service, 'stop', new_callable=AsyncMock) as mock_stop:
            success = await hitl_plugin.deactivate()
        
        assert success is True
        assert hitl_plugin.status.value == 'deactivated'
    
    @pytest.mark.asyncio
    async def test_create_hitl_request_tool(self, hitl_plugin):
        """测试创建HITL请求工具"""
        await hitl_plugin.activate()
        
        # 模拟服务方法
        with patch.object(hitl_plugin.hitl_service, 'create_hitl_request', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = 'test-request-id'
            
            result = await hitl_plugin.create_hitl_request_tool(
                agent_id='test-agent',
                title='测试请求',
                description='这是一个测试请求',
                priority='high',
                timeout_minutes=60
            )
        
        assert result['success'] is True
        assert result['request_id'] == 'test-request-id'
        assert 'HITL请求创建成功' in result['message']
    
    @pytest.mark.asyncio
    async def test_create_hitl_request_tool_invalid_priority(self, hitl_plugin):
        """测试创建HITL请求工具 - 无效优先级"""
        await hitl_plugin.activate()
        
        with pytest.raises(ValueError, match="Invalid priority"):
            await hitl_plugin.create_hitl_request_tool(
                agent_id='test-agent',
                title='测试请求',
                description='这是一个测试请求',
                priority='invalid_priority'
            )
    
    @pytest.mark.asyncio
    async def test_submit_hitl_response_tool(self, hitl_plugin):
        """测试提交HITL响应工具"""
        await hitl_plugin.activate()
        
        # 模拟服务方法
        with patch.object(hitl_plugin.hitl_service, 'submit_hitl_response', new_callable=AsyncMock) as mock_submit:
            mock_submit.return_value = True
            
            result = await hitl_plugin.submit_hitl_response_tool(
                request_id='test-request-id',
                responder_id='test-user',
                content='测试响应内容',
                is_final=True
            )
        
        assert result['success'] is True
        assert 'HITL响应提交成功' in result['message']
    
    @pytest.mark.asyncio
    async def test_submit_hitl_response_tool_failure(self, hitl_plugin):
        """测试提交HITL响应工具 - 失败情况"""
        await hitl_plugin.activate()
        
        # 模拟服务方法返回失败
        with patch.object(hitl_plugin.hitl_service, 'submit_hitl_response', new_callable=AsyncMock) as mock_submit:
            mock_submit.return_value = False
            
            result = await hitl_plugin.submit_hitl_response_tool(
                request_id='invalid-request-id',
                responder_id='test-user',
                content='测试响应内容'
            )
        
        assert result['success'] is False
        assert '不存在或已关闭' in result['message']
    
    @pytest.mark.asyncio
    async def test_get_hitl_request_tool(self, hitl_plugin):
        """测试获取HITL请求详情工具"""
        await hitl_plugin.activate()
        
        # 创建测试请求
        test_request = HITLRequest(
            id='test-request-id',
            agent_id='test-agent',
            title='测试请求',
            description='测试描述',
            context={},
            priority=HITLPriority.MEDIUM,
            created_at=datetime.now()
        )
        
        # 模拟服务方法
        with patch.object(hitl_plugin.hitl_service, 'get_hitl_request', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = test_request
            
            result = await hitl_plugin.get_hitl_request_tool('test-request-id')
        
        assert result['success'] is True
        assert 'request' in result
        assert result['request']['id'] == 'test-request-id'
    
    @pytest.mark.asyncio
    async def test_get_hitl_request_tool_not_found(self, hitl_plugin):
        """测试获取HITL请求详情工具 - 请求不存在"""
        await hitl_plugin.activate()
        
        # 模拟服务方法返回None
        with patch.object(hitl_plugin.hitl_service, 'get_hitl_request', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            result = await hitl_plugin.get_hitl_request_tool('non-existent-id')
        
        assert result['success'] is False
        assert '不存在' in result['message']
    
    @pytest.mark.asyncio
    async def test_list_active_hitl_requests_tool(self, hitl_plugin):
        """测试列出活跃HITL请求工具"""
        await hitl_plugin.activate()
        
        # 创建测试请求列表
        test_requests = [
            HITLRequest(
                id='request-1',
                agent_id='agent-1',
                title='请求1',
                description='描述1',
                context={},
                priority=HITLPriority.MEDIUM,
                created_at=datetime.now()
            ),
            HITLRequest(
                id='request-2',
                agent_id='agent-2',
                title='请求2',
                description='描述2',
                context={},
                priority=HITLPriority.HIGH,
                created_at=datetime.now()
            )
        ]
        
        # 模拟服务方法
        with patch.object(hitl_plugin.hitl_service, 'list_active_requests', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = test_requests
            
            result = await hitl_plugin.list_active_hitl_requests_tool()
        
        assert result['success'] is True
        assert result['count'] == 2
        assert len(result['requests']) == 2
    
    @pytest.mark.asyncio
    async def test_list_user_hitl_requests_tool(self, hitl_plugin):
        """测试列出用户HITL请求工具"""
        await hitl_plugin.activate()
        
        # 创建测试请求列表
        test_requests = [
            HITLRequest(
                id='request-1',
                agent_id='agent-1',
                title='用户请求',
                description='描述',
                context={},
                priority=HITLPriority.MEDIUM,
                created_at=datetime.now(),
                assigned_to='test-user'
            )
        ]
        
        # 模拟服务方法
        with patch.object(hitl_plugin.hitl_service, 'list_user_requests', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = test_requests
            
            result = await hitl_plugin.list_user_hitl_requests_tool('test-user')
        
        assert result['success'] is True
        assert result['user_id'] == 'test-user'
        assert result['count'] == 1
    
    @pytest.mark.asyncio
    async def test_cancel_hitl_request_tool(self, hitl_plugin):
        """测试取消HITL请求工具"""
        await hitl_plugin.activate()
        
        # 模拟服务方法
        with patch.object(hitl_plugin.hitl_service, 'cancel_hitl_request', new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = True
            
            result = await hitl_plugin.cancel_hitl_request_tool(
                'test-request-id',
                '用户取消'
            )
        
        assert result['success'] is True
        assert '已取消' in result['message']
    
    @pytest.mark.asyncio
    async def test_get_hitl_statistics_tool(self, hitl_plugin):
        """测试获取HITL统计信息工具"""
        await hitl_plugin.activate()
        
        # 模拟统计数据
        test_stats = {
            'active_requests': 5,
            'total_requests': 100,
            'completed_requests': 90,
            'timeout_requests': 5,
            'completion_rate': 0.9
        }
        
        # 模拟服务方法
        with patch.object(hitl_plugin.hitl_service, 'get_hitl_statistics', new_callable=AsyncMock) as mock_stats:
            mock_stats.return_value = test_stats
            
            result = await hitl_plugin.get_hitl_statistics_tool()
        
        assert result['success'] is True
        assert result['statistics'] == test_stats
    
    @pytest.mark.asyncio
    async def test_get_hitl_service_status_tool(self, hitl_plugin):
        """测试获取HITL服务状态工具"""
        await hitl_plugin.activate()
        
        result = await hitl_plugin.get_hitl_service_status_tool()
        
        assert result['success'] is True
        assert result['status'] == 'active'
        assert result['plugin_id'] == 'test_hitl_plugin'
        assert 'active_requests' in result
        assert 'total_requests' in result
    
    @pytest.mark.asyncio
    async def test_hitl_hooks(self, hitl_plugin):
        """测试HITL钩子功能"""
        await hitl_plugin.activate()
        
        # 测试HITL请求创建前钩子
        await hitl_plugin.on_hitl_request_before_create(
            agent_id='test-agent',
            title='测试标题',
            description='测试描述',
            context={}
        )
        
        # 测试HITL请求创建后钩子
        test_request = HITLRequest(
            id='test-request-id',
            agent_id='test-agent',
            title='测试请求',
            description='测试描述',
            context={},
            priority=HITLPriority.MEDIUM,
            created_at=datetime.now()
        )
        
        await hitl_plugin.on_hitl_request_after_create(test_request)
        
        # 测试HITL响应提交前钩子
        await hitl_plugin.on_hitl_response_before_submit(
            request_id='test-request-id',
            responder_id='test-user',
            content='测试响应'
        )
        
        # 测试HITL响应提交后钩子
        test_response = HITLResponse(
            request_id='test-request-id',
            responder_id='test-user',
            content='测试响应内容',
            created_at=datetime.now()
        )
        
        await hitl_plugin.on_hitl_response_after_submit(test_request, test_response)
        
        # 测试HITL请求超时钩子
        await hitl_plugin.on_hitl_request_timeout(test_request)
        
        # 测试HITL请求取消钩子
        await hitl_plugin.on_hitl_request_cancelled(test_request, '测试取消原因')
    
    @pytest.mark.asyncio
    async def test_hitl_commands(self, hitl_plugin):
        """测试HITL命令功能"""
        await hitl_plugin.activate()
        
        # 测试HITL状态命令
        status_result = await hitl_plugin.handle_hitl_status_command('')
        assert 'HITL插件状态' in status_result
        
        # 测试HITL列表命令
        list_result = await hitl_plugin.handle_hitl_list_command('')
        assert '所有活跃的HITL请求' in list_result
        
        # 测试用户列表命令
        user_list_result = await hitl_plugin.handle_hitl_list_command('test-user')
        assert '用户 test-user 的HITL请求' in user_list_result
        
        # 测试HITL取消命令 - 先创建请求再取消
        with patch.object(hitl_plugin.hitl_service, 'create_hitl_request', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = 'test-request-id'
            await hitl_plugin.create_hitl_request_tool(
                agent_id='test-agent',
                title='测试请求',
                description='测试描述',
                priority='high'
            )
        
        # 模拟取消成功的场景
        with patch.object(hitl_plugin.hitl_service, 'cancel_hitl_request', new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = True
            cancel_result = await hitl_plugin.handle_hitl_cancel_command('test-request-id')
            assert '已成功取消' in cancel_result
    
    @pytest.mark.asyncio
    async def test_compatibility_methods(self, hitl_plugin):
        """测试兼容性方法"""
        # 测试获取服务实例
        service = hitl_plugin.get_hitl_service()
        assert service is not None
        
        # 测试原始方法调用
        with patch.object(service, 'create_hitl_request', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = 'compat-request-id'
            
            result = await hitl_plugin.create_hitl_request(
                agent_id='test-agent',
                title='兼容性测试',
                description='测试兼容性',
                priority=HITLPriority.LOW
            )
            
            assert result == 'compat-request-id'
        
        with patch.object(service, 'get_hitl_statistics', new_callable=AsyncMock) as mock_stats:
            mock_stats.return_value = {'test': 'stats'}
            
            result = await hitl_plugin.get_hitl_statistics()
            assert result == {'test': 'stats'}
    
    @pytest.mark.asyncio
    async def test_plugin_manager_integration(self, plugin_manager, plugin_context):
        """测试插件管理器集成"""
        import os
        
        # 获取实际的插件文件路径
        current_dir = os.path.dirname(os.path.dirname(__file__))
        plugin_path = os.path.join(current_dir, 'plugins', 'hitl_plugin.py')
        
        # 创建插件实例
        plugin = HITLPlugin('integration_test', plugin_context)
        
        # 先直接注册插件到管理器中（模拟加载过程）
        plugin_manager._plugins['integration_test'] = plugin
        
        # 激活插件
        with patch.object(plugin.hitl_service, 'start', new_callable=AsyncMock):
            success = await plugin_manager.activate_plugin('integration_test')
        
        assert success is True
        
        # 检查插件状态
        status = plugin_manager.get_plugin_status('integration_test')
        assert status.value == 'active'
        
        # 检查工具注册
        tools = plugin_manager.get_tools()
        assert 'create_hitl_request' in tools
        
        # 检查钩子注册
        hooks = plugin_manager.get_hooks()
        assert 'hitl_request_after_create' in hooks
        
        # 检查命令注册
        commands = plugin_manager.get_commands()
        assert '/hitl-status' in commands
    
    @pytest.mark.asyncio
    async def test_error_handling(self, hitl_plugin):
        """测试错误处理"""
        await hitl_plugin.activate()
        
        # 测试不存在的工具
        with pytest.raises(ValueError, match="Tool 'non_existent_tool' not found"):
            await hitl_plugin.execute_tool('non_existent_tool')
        
        # 测试钩子执行中的错误（应该被捕获）
        hooks = hitl_plugin.get_hooks()
        if 'hitl_request_before_create' in hooks:
            # 钩子可能是一个对象或列表，需要安全处理
            for hook_entry in hooks['hitl_request_before_create']:
                # 检查钩子条目的类型
                if hasattr(hook_entry, 'handler'):
                    # 如果是插件钩子对象
                    await hook_entry.handler(
                        agent_id='test-agent',
                        title='测试',
                        description='测试',
                        context={}
                    )
                elif isinstance(hook_entry, tuple) and len(hook_entry) >= 2:
                    # 如果是 (plugin_id, hook) 元组
                    plugin_id, hook = hook_entry
                    await hook(
                        agent_id='test-agent',
                        title='测试',
                        description='测试',
                        context={}
                    )
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, hitl_plugin):
        """测试并发请求处理"""
        await hitl_plugin.activate()
        
        # 模拟多个并发创建请求
        tasks = []
        for i in range(5):
            task = hitl_plugin.create_hitl_request_tool(
                agent_id=f'agent-{i}',
                title=f'请求 {i}',
                description=f'描述 {i}',
                priority='medium'
            )
            tasks.append(task)
        
        # 模拟服务方法
        with patch.object(hitl_plugin.hitl_service, 'create_hitl_request', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = lambda **kwargs: f'request-{id(kwargs)}'
            
            results = await asyncio.gather(*tasks)
        
        # 验证所有请求都成功
        for result in results:
            assert result['success'] is True
            assert 'request-' in result['request_id']