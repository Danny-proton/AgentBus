"""
AgentBus流式响应处理插件测试

测试流式响应处理插件的各项功能，包括：
- 插件激活和停用
- 流创建和管理
- 工具注册和使用
- 钩子事件处理
- 命令执行
- 统计功能
- 兼容性测试
"""

import asyncio
import pytest
import uuid
from datetime import datetime
from typing import Dict, Any, List

from agentbus.plugins.stream_plugin import StreamPlugin, StreamEvent
from agentbus.plugins.core import PluginContext, PluginStatus
from agentbus.services.stream_response import (
    StreamRequest,
    StreamChunk,
    StreamEventType,
    StreamStatus,
)


class MockLogger:
    """模拟日志记录器"""
    
    def __init__(self):
        self.logs = []
    
    def info(self, message: str):
        self.logs.append(("INFO", message))
        print(f"INFO: {message}")
    
    def error(self, message: str):
        self.logs.append(("ERROR", message))
        print(f"ERROR: {message}")
    
    def debug(self, message: str):
        self.logs.append(("DEBUG", message))
        print(f"DEBUG: {message}")
    
    def warning(self, message: str):
        self.logs.append(("WARNING", message))
        print(f"WARNING: {message}")


@pytest.fixture
async def plugin_context():
    """创建插件上下文"""
    mock_logger = MockLogger()
    
    context = PluginContext(
        config={
            "stream_chunk_size": 10,
            "stream_delay_ms": 50,
            "max_concurrent_streams": 100
        },
        logger=mock_logger,
        runtime={
            "test_mode": True
        }
    )
    
    return context


@pytest.fixture
async def stream_plugin(plugin_context):
    """创建流式响应插件实例"""
    plugin = StreamPlugin("stream_plugin_test", plugin_context)
    yield plugin
    
    # 清理
    if plugin.status == PluginStatus.ACTIVE:
        await plugin.deactivate()


@pytest.fixture
async def activated_stream_plugin(stream_plugin):
    """创建已激活的流式响应插件"""
    await stream_plugin.activate()
    return stream_plugin


class TestStreamPlugin:
    """流式响应插件测试类"""
    
    def test_plugin_initialization(self, stream_plugin):
        """测试插件初始化"""
        assert stream_plugin.plugin_id == "stream_plugin_test"
        assert stream_plugin.status == PluginStatus.UNLOADED
        assert stream_plugin.stream_processor is None
        assert stream_plugin.active_streams == {}
        assert stream_plugin.stream_event_hooks == {}
        assert stream_plugin.stats == {
            "total_streams": 0,
            "active_streams": 0,
            "completed_streams": 0,
            "error_streams": 0,
            "cancelled_streams": 0,
            "total_chunks_sent": 0,
            "total_bytes_sent": 0
        }
    
    def test_plugin_info(self, stream_plugin):
        """测试插件信息"""
        info = stream_plugin.get_info()
        
        assert info['id'] == "stream_plugin_test"
        assert info['name'] == 'Stream Response Plugin'
        assert info['version'] == '1.0.0'
        assert 'capabilities' in info
        assert 'websocket_streaming' in info['capabilities']
        assert 'http_streaming' in info['capabilities']
    
    async def test_plugin_activation(self, stream_plugin):
        """测试插件激活"""
        # 激活插件
        success = await stream_plugin.activate()
        
        assert success is True
        assert stream_plugin.status == PluginStatus.ACTIVE
        assert stream_plugin.stream_processor is not None
        
        # 检查工具注册
        tools = stream_plugin.get_tools()
        tool_names = [tool.name for tool in tools]
        
        expected_tools = [
            'create_stream',
            'cancel_stream',
            'get_stream_status',
            'get_stream_stats',
            'list_active_streams',
            'start_stream_processing',
            'send_stream_chunk'
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Tool {expected_tool} not registered"
        
        # 检查钩子注册
        hooks = stream_plugin.get_hooks()
        expected_events = [
            'stream_created',
            'stream_started',
            'stream_completed',
            'stream_cancelled',
            'stream_error',
            'chunk_sent',
            'heartbeat'
        ]
        
        for expected_event in expected_events:
            assert expected_event in hooks, f"Hook {expected_event} not registered"
        
        # 检查命令注册
        commands = stream_plugin.get_commands()
        command_names = [cmd['command'] for cmd in commands]
        
        expected_commands = [
            '/stream-status',
            '/stream-stats',
            '/stream-cancel'
        ]
        
        for expected_command in expected_commands:
            assert expected_command in command_names, f"Command {expected_command} not registered"
    
    async def test_plugin_deactivation(self, activated_stream_plugin):
        """测试插件停用"""
        plugin = activated_stream_plugin
        
        # 停用插件
        success = await plugin.deactivate()
        
        assert success is True
        assert plugin.status == PluginStatus.DEACTIVATED
        assert plugin.stream_processor is None
    
    async def test_create_stream_tool(self, activated_stream_plugin):
        """测试创建流工具"""
        plugin = activated_stream_plugin
        
        # 创建流
        result = await plugin.create_stream_tool(
            content="测试流内容",
            stream_type="text",
            handler_type="websocket",
            chunk_size=5,
            delay_ms=100
        )
        
        assert result['success'] is True
        assert 'stream_id' in result
        assert result['handler_type'] == 'websocket'
        assert result['status'] == 'created'
        
        stream_id = result['stream_id']
        
        # 检查流是否已记录
        assert stream_id in plugin.active_streams
        
        stream_info = plugin.active_streams[stream_id]
        assert stream_info['handler_type'] == 'websocket'
        assert stream_info['status'] == 'created'
        assert stream_info['request'].content == "测试流内容"
        assert stream_info['request'].stream_type == "text"
        assert stream_info['request'].chunk_size == 5
        assert stream_info['request'].delay_ms == 100
        
        # 检查统计更新
        assert plugin.stats['total_streams'] == 1
        assert plugin.stats['active_streams'] == 1
    
    async def test_cancel_stream_tool(self, activated_stream_plugin):
        """测试取消流工具"""
        plugin = activated_stream_plugin
        
        # 先创建一个流
        create_result = await plugin.create_stream_tool(
            content="测试流",
            stream_type="text"
        )
        assert create_result['success'] is True
        stream_id = create_result['stream_id']
        
        # 取消流
        cancel_result = await plugin.cancel_stream_tool(stream_id)
        
        assert cancel_result['success'] is True
        assert cancel_result['stream_id'] == stream_id
        assert cancel_result['status'] == 'cancelled'
        
        # 检查流已从活跃列表移除
        assert stream_id not in plugin.active_streams
        
        # 检查统计更新
        assert plugin.stats['active_streams'] == 0
        assert plugin.stats['cancelled_streams'] == 1
    
    async def test_get_stream_status_tool(self, activated_stream_plugin):
        """测试获取流状态工具"""
        plugin = activated_stream_plugin
        
        # 创建一个流
        create_result = await plugin.create_stream_tool(
            content="测试流",
            stream_type="text"
        )
        assert create_result['success'] is True
        stream_id = create_result['stream_id']
        
        # 获取流状态
        status_result = await plugin.get_stream_status_tool(stream_id)
        
        assert status_result['success'] is True
        assert status_result['stream_id'] == stream_id
        assert status_result['status'] == 'created'
        
        # 测试不存在的流
        fake_stream_id = str(uuid.uuid4())
        fake_status_result = await plugin.get_stream_status_tool(fake_stream_id)
        
        assert fake_status_result['success'] is False
        assert 'error' in fake_status_result
    
    async def test_get_stream_stats_tool(self, activated_stream_plugin):
        """测试获取流统计工具"""
        plugin = activated_stream_plugin
        
        # 获取初始统计
        stats_result = await plugin.get_stream_stats_tool()
        
        assert stats_result['success'] is True
        assert 'stats' in stats_result
        
        stats = stats_result['stats']
        assert stats['total_streams'] == 0
        assert stats['active_streams'] == 0
        assert stats['completed_streams'] == 0
        assert stats['error_streams'] == 0
        assert stats['cancelled_streams'] == 0
        
        # 创建几个流来测试统计更新
        for i in range(3):
            await plugin.create_stream_tool(
                content=f"测试流 {i}",
                stream_type="text"
            )
        
        # 获取更新后的统计
        updated_stats_result = await plugin.get_stream_stats_tool()
        
        assert updated_stats_result['success'] is True
        updated_stats = updated_stats_result['stats']
        assert updated_stats['total_streams'] == 3
        assert updated_stats['active_streams'] == 3
    
    async def test_list_active_streams_tool(self, activated_stream_plugin):
        """测试列出活跃流工具"""
        plugin = activated_stream_plugin
        
        # 创建几个流
        stream_ids = []
        for i in range(3):
            result = await plugin.create_stream_tool(
                content=f"测试流 {i}",
                stream_type="text"
            )
            assert result['success'] is True
            stream_ids.append(result['stream_id'])
        
        # 列出活跃流
        list_result = await plugin.list_active_streams_tool()
        
        assert list_result['success'] is True
        assert list_result['count'] == 3
        
        active_streams = list_result['active_streams']
        assert len(active_streams) == 3
        
        # 验证流信息
        for stream_info in active_streams:
            assert 'stream_id' in stream_info
            assert 'handler_type' in stream_info
            assert 'created_at' in stream_info
            assert 'status' in stream_info
            assert 'stream_type' in stream_info
    
    async def test_start_stream_processing_tool(self, activated_stream_plugin):
        """测试开始流处理工具"""
        plugin = activated_stream_plugin
        
        # 创建一个流
        create_result = await plugin.create_stream_tool(
            content="测试流处理",
            stream_type="text"
        )
        assert create_result['success'] is True
        stream_id = create_result['stream_id']
        
        # 开始流处理
        process_result = await plugin.start_stream_processing_tool(
            stream_id,
            "simulate_ai_response"
        )
        
        assert process_result['success'] is True
        assert process_result['stream_id'] == stream_id
        assert process_result['status'] == 'processing'
        
        # 检查流状态更新
        assert plugin.active_streams[stream_id]['status'] == 'processing'
        
        # 测试不存在的流
        fake_result = await plugin.start_stream_processing_tool(
            str(uuid.uuid4()),
            "simulate_ai_response"
        )
        
        assert fake_result['success'] is False
        assert 'error' in fake_result
    
    async def test_send_stream_chunk_tool(self, activated_stream_plugin):
        """测试发送流数据块工具"""
        plugin = activated_stream_plugin
        
        # 创建一个流
        create_result = await plugin.create_stream_tool(
            content="测试数据块",
            stream_type="text"
        )
        assert create_result['success'] is True
        stream_id = create_result['stream_id']
        
        # 发送数据块
        chunk_result = await plugin.send_stream_chunk_tool(
            stream_id=stream_id,
            content="测试数据",
            event_type="token",
            token_count=1,
            progress=0.1
        )
        
        assert chunk_result['success'] is True
        assert chunk_result['stream_id'] == stream_id
        assert chunk_result['chunk_sent'] is True
        
        # 检查统计更新
        assert plugin.stats['total_chunks_sent'] == 1
        assert plugin.stats['total_bytes_sent'] == len("测试数据".encode('utf-8'))
        
        # 测试无效的事件类型
        invalid_chunk_result = await plugin.send_stream_chunk_tool(
            stream_id=stream_id,
            content="测试数据",
            event_type="invalid_type"
        )
        
        assert invalid_chunk_result['success'] is False
        assert 'error' in invalid_chunk_result
    
    async def test_hook_events(self, activated_stream_plugin):
        """测试钩子事件"""
        plugin = activated_stream_plugin
        
        # 记录钩子调用
        hook_calls = []
        
        async def custom_hook(event_data):
            hook_calls.append(event_data)
        
        # 注册自定义钩子
        plugin.register_hook(
            event=StreamEvent.STREAM_CREATED.value,
            handler=custom_hook,
            priority=15
        )
        
        # 创建流触发钩子
        result = await plugin.create_stream_tool(
            content="钩子测试",
            stream_type="text"
        )
        assert result['success'] is True
        
        # 检查钩子是否被调用
        assert len(hook_calls) > 0
        
        hook_data = hook_calls[0]
        assert 'stream_id' in hook_data
        assert 'request' in hook_data
        assert 'handler_type' in hook_data
    
    async def test_commands(self, activated_stream_plugin):
        """测试命令处理"""
        plugin = activated_stream_plugin
        
        # 创建一些流
        for i in range(2):
            await plugin.create_stream_tool(
                content=f"命令测试流 {i}",
                stream_type="text"
            )
        
        # 测试流状态命令
        status_result = await plugin.handle_stream_status_command("")
        assert "📊 流状态统计:" in status_result
        assert "总流数: 2" in status_result
        assert "活跃流数: 2" in status_result
        
        # 测试流统计命令
        stats_result = await plugin.handle_stream_stats_command("")
        assert "📈 详细统计信息:" in stats_result
        assert "插件统计:" in stats_result
        assert "处理器统计:" in stats_result
        
        # 测试流取消命令
        stream_id = list(plugin.active_streams.keys())[0]
        cancel_result = await plugin.handle_stream_cancel_command(stream_id)
        assert "✅ 流已取消:" in cancel_result
    
    async def test_error_handling(self, activated_stream_plugin):
        """测试错误处理"""
        plugin = activated_stream_plugin
        
        # 测试取消不存在的流
        fake_stream_id = str(uuid.uuid4())
        cancel_result = await plugin.cancel_stream_tool(fake_stream_id)
        
        assert cancel_result['success'] is False
        assert 'error' in cancel_result
        
        # 测试获取不存在流的状态
        status_result = await plugin.get_stream_status_tool(fake_stream_id)
        
        assert status_result['success'] is False
        assert 'error' in status_result
    
    async def test_compatibility_methods(self, activated_stream_plugin):
        """测试兼容性方法"""
        plugin = activated_stream_plugin
        
        # 创建流请求
        request = StreamRequest(
            stream_id=str(uuid.uuid4()),
            content="兼容性测试",
            stream_type="text",
            chunk_size=5,
            delay_ms=100
        )
        
        # 使用兼容性方法创建流
        stream_id = await plugin.create_stream(request, "websocket")
        
        assert stream_id is not None
        assert stream_id in plugin.active_streams
        
        # 使用兼容性方法获取流状态
        status = await plugin.get_stream_status(stream_id)
        assert status is not None
        
        # 使用兼容性方法获取统计
        stats = await plugin.get_stream_stats()
        assert isinstance(stats, dict)
        assert 'total_streams' in stats
        
        # 使用兼容性方法列出活跃流
        active_streams = await plugin.list_active_streams()
        assert stream_id in active_streams
        
        # 使用兼容性方法取消流
        success = await plugin.cancel_stream(stream_id)
        assert success is True
        assert stream_id not in plugin.active_streams
    
    async def test_multiple_stream_types(self, activated_stream_plugin):
        """测试多种流类型"""
        plugin = activated_stream_plugin
        
        # 测试WebSocket流
        ws_result = await plugin.create_stream_tool(
            content="WebSocket流测试",
            stream_type="text",
            handler_type="websocket"
        )
        assert ws_result['success'] is True
        assert ws_result['handler_type'] == 'websocket'
        
        # 测试HTTP流
        http_result = await plugin.create_stream_tool(
            content="HTTP流测试",
            stream_type="code",
            handler_type="http"
        )
        assert http_result['success'] is True
        assert http_result['handler_type'] == 'http'
        
        # 验证流信息
        ws_stream_id = ws_result['stream_id']
        http_stream_id = http_result['stream_id']
        
        assert plugin.active_streams[ws_stream_id]['handler_type'] == 'websocket'
        assert plugin.active_streams[http_stream_id]['handler_type'] == 'http'
        
        assert plugin.active_streams[ws_stream_id]['request'].stream_type == "text"
        assert plugin.active_streams[http_stream_id]['request'].stream_type == "code"
    
    async def test_stream_metadata(self, activated_stream_plugin):
        """测试流元数据"""
        plugin = activated_stream_plugin
        
        metadata = {
            "user_id": "test_user",
            "session_id": "test_session",
            "priority": "high"
        }
        
        # 创建带元数据的流
        result = await plugin.create_stream_tool(
            content="元数据测试",
            stream_type="text",
            metadata=metadata
        )
        
        assert result['success'] is True
        stream_id = result['stream_id']
        
        # 验证元数据是否保存
        stream_info = plugin.active_streams[stream_id]
        assert stream_info['request'].metadata == metadata
    
    async def test_stream_processing_workflow(self, activated_stream_plugin):
        """测试完整的流处理工作流程"""
        plugin = activated_stream_plugin
        
        # 1. 创建流
        create_result = await plugin.create_stream_tool(
            content="完整工作流程测试",
            stream_type="text",
            chunk_size=3,
            delay_ms=50
        )
        
        assert create_result['success'] is True
        stream_id = create_result['stream_id']
        
        # 2. 验证流状态
        status_result = await plugin.get_stream_status_tool(stream_id)
        assert status_result['success'] is True
        assert status_result['status'] == 'created'
        
        # 3. 开始流处理
        process_result = await plugin.start_stream_processing_tool(
            stream_id,
            "simulate_ai_response"
        )
        assert process_result['success'] is True
        assert process_result['status'] == 'processing'
        
        # 4. 等待处理完成
        await asyncio.sleep(2)  # 等待模拟处理完成
        
        # 5. 验证最终状态
        final_status_result = await plugin.get_stream_status_tool(stream_id)
        assert final_status_result['success'] is True
        # 状态可能是completed、streaming等
        
        # 6. 获取统计信息
        final_stats = await plugin.get_stream_stats_tool()
        assert final_stats['success'] is True
        assert final_stats['stats']['total_streams'] >= 1


# 集成测试
class TestStreamPluginIntegration:
    """流式响应插件集成测试"""
    
    async def test_plugin_lifecycle(self):
        """测试插件完整生命周期"""
        mock_logger = MockLogger()
        
        context = PluginContext(
            config={},
            logger=mock_logger,
            runtime={}
        )
        
        plugin = StreamPlugin("lifecycle_test", context)
        
        # 测试初始状态
        assert plugin.status == PluginStatus.UNLOADED
        
        # 测试激活
        activation_success = await plugin.activate()
        assert activation_success is True
        assert plugin.status == PluginStatus.ACTIVE
        
        # 测试功能使用
        result = await plugin.create_stream_tool(
            content="生命周期测试",
            stream_type="text"
        )
        assert result['success'] is True
        
        # 测试停用
        deactivation_success = await plugin.deactivate()
        assert deactivation_success is True
        assert plugin.status == PluginStatus.DEACTIVATED
        
        # 验证清理
        assert plugin.stream_processor is None
        assert plugin.active_streams == {}
    
    async def test_plugin_with_real_processor(self):
        """测试插件与真实处理器的集成"""
        mock_logger = MockLogger()
        
        context = PluginContext(
            config={
                "stream_chunk_size": 5,
                "stream_delay_ms": 30
            },
            logger=mock_logger,
            runtime={"test_mode": True}
        )
        
        plugin = StreamPlugin("integration_test", context)
        
        # 激活插件
        await plugin.activate()
        
        # 创建多个流
        streams = []
        for i in range(3):
            result = await plugin.create_stream_tool(
                content=f"集成测试流 {i}",
                stream_type="text" if i % 2 == 0 else "code",
                handler_type="websocket" if i % 2 == 0 else "http"
            )
            assert result['success'] is True
            streams.append(result['stream_id'])
        
        # 验证所有流都已创建
        assert len(plugin.active_streams) == 3
        
        # 验证流信息
        for stream_id in streams:
            assert stream_id in plugin.active_streams
            stream_info = plugin.active_streams[stream_id]
            assert stream_info['status'] == 'created'
            assert stream_info['request'] is not None
        
        # 获取统计
        stats_result = await plugin.get_stream_stats_tool()
        assert stats_result['success'] is True
        assert stats_result['stats']['total_streams'] == 3
        assert stats_result['stats']['active_streams'] == 3
        
        # 清理
        await plugin.deactivate()
        
        # 验证清理完成
        assert len(plugin.active_streams) == 0
        assert plugin.stats['active_streams'] == 0


# 性能测试
class TestStreamPluginPerformance:
    """流式响应插件性能测试"""
    
    async def test_concurrent_stream_creation(self, activated_stream_plugin):
        """测试并发流创建性能"""
        plugin = activated_stream_plugin
        
        num_streams = 10
        start_time = datetime.now()
        
        # 并发创建流
        tasks = []
        for i in range(num_streams):
            task = plugin.create_stream_tool(
                content=f"并发测试流 {i}",
                stream_type="text"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 验证结果
        successful_results = [r for r in results if r['success']]
        assert len(successful_results) == num_streams
        
        # 验证性能指标
        assert duration < 5.0  # 应该在5秒内完成
        assert len(plugin.active_streams) == num_streams
        
        print(f"创建 {num_streams} 个流耗时: {duration:.2f}秒")
    
    async def test_rapid_stream_operations(self, activated_stream_plugin):
        """测试快速流操作"""
        plugin = activated_stream_plugin
        
        # 创建流
        create_result = await plugin.create_stream_tool(
            content="快速操作测试",
            stream_type="text"
        )
        assert create_result['success'] is True
        stream_id = create_result['stream_id']
        
        # 快速执行多个操作
        operations = [
            lambda: plugin.get_stream_status_tool(stream_id),
            lambda: plugin.get_stream_stats_tool(),
            lambda: plugin.list_active_streams_tool(),
            lambda: plugin.get_stream_status_tool(stream_id),
            lambda: plugin.get_stream_stats_tool(),
        ]
        
        start_time = datetime.now()
        
        # 并发执行操作
        results = await asyncio.gather(*[op() for op in operations])
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 验证所有操作成功
        for result in results:
            assert result['success'] is True
        
        # 验证性能
        assert duration < 2.0  # 应该在2秒内完成
        
        print(f"快速操作耗时: {duration:.2f}秒")


if __name__ == "__main__":
    # 运行基本测试
    asyncio.run(test_plugin_initialization())
