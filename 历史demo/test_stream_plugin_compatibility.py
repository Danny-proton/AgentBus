#!/usr/bin/env python3
"""
流式响应处理插件兼容性测试

测试插件化后的流式响应处理功能是否与原有功能完全兼容。
包括功能测试、性能测试和API兼容性测试。
"""

import asyncio
import time
import sys
from datetime import datetime
from typing import Dict, Any

# 添加agentbus模块路径
sys.path.append('/workspace/agentbus')

from agentbus.services.stream_response import (
    StreamResponseProcessor,
    StreamRequest,
    StreamEventType,
    initialize_stream_plugin,
    create_standalone_stream_processor,
    get_stream_plugin_info,
    stream_factory,
    PluginEventAdapter,
    StreamConfig,
    validate_stream_config,
    create_stream_request_from_dict,
    format_stream_stats
)

from agentbus.plugins.stream_plugin import StreamPlugin
from agentbus.plugins.core import PluginContext
import logging


class CompatibilityTestResult:
    """兼容性测试结果"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.details = []
    
    def add_pass(self, test_name: str, details: str = ""):
        """添加通过的测试"""
        self.passed += 1
        self.details.append(f"✅ {test_name}: {details}")
    
    def add_fail(self, test_name: str, error: str):
        """添加失败的测试"""
        self.failed += 1
        self.errors.append(f"❌ {test_name}: {error}")
        self.details.append(f"❌ {test_name}: {error}")
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("🔍 流式响应处理插件兼容性测试结果")
        print("="*60)
        print(f"✅ 通过: {self.passed}")
        print(f"❌ 失败: {self.failed}")
        print(f"📊 总计: {self.passed + self.failed}")
        
        if self.failed > 0:
            print("\n❌ 失败的测试:")
            for error in self.errors:
                print(f"  {error}")
        
        print("\n📋 详细结果:")
        for detail in self.details:
            print(f"  {detail}")
        
        return self.failed == 0


async def test_plugin_initialization():
    """测试插件初始化"""
    result = CompatibilityTestResult()
    
    try:
        # 测试插件信息获取
        info = get_stream_plugin_info()
        if 'name' in info and info['name'] == 'Stream Response Plugin':
            result.add_pass("插件信息获取", "成功获取插件信息")
        else:
            result.add_fail("插件信息获取", "无法获取正确的插件信息")
        
        # 测试插件初始化
        plugin = await initialize_stream_plugin()
        if plugin and hasattr(plugin, 'stream_processor'):
            result.add_pass("插件初始化", "插件初始化成功")
            await plugin.deactivate()
        else:
            result.add_fail("插件初始化", "插件初始化失败")
        
    except Exception as e:
        result.add_fail("插件初始化", str(e))
    
    return result


async def test_plugin_vs_processor_api():
    """测试插件与传统处理器的API兼容性"""
    result = CompatibilityTestResult()
    
    try:
        # 创建传统处理器
        processor = await create_standalone_stream_processor()
        
        # 创建插件
        plugin = await initialize_stream_plugin()
        
        # 测试相同的流创建接口
        test_content = "API兼容性测试"
        stream_type = "text"
        
        # 使用传统接口
        request = StreamRequest(
            stream_id="test_traditional",
            content=test_content,
            stream_type=stream_type
        )
        
        traditional_stream_id = await processor.create_stream(request, "websocket")
        
        # 使用插件接口
        plugin_stream_id = await plugin.create_stream(request, "websocket")
        
        # 验证返回结果
        if traditional_stream_id and plugin_stream_id:
            result.add_pass("流创建API兼容性", "传统接口和插件接口都能创建流")
        else:
            result.add_fail("流创建API兼容性", "API接口不兼容")
        
        # 测试状态获取接口
        traditional_status = await processor.get_stream_status(traditional_stream_id)
        plugin_status = await plugin.get_stream_status(plugin_stream_id)
        
        if traditional_status == plugin_status:
            result.add_pass("流状态API兼容性", "状态获取接口兼容")
        else:
            result.add_fail("流状态API兼容性", "状态接口不兼容")
        
        # 测试统计接口
        traditional_stats = await processor.get_stream_stats()
        plugin_stats = await plugin.get_stream_stats()
        
        if isinstance(traditional_stats, dict) and isinstance(plugin_stats, dict):
            result.add_pass("统计API兼容性", "统计接口都返回字典")
        else:
            result.add_fail("统计API兼容性", "统计接口不兼容")
        
        # 清理
        await processor.shutdown()
        await plugin.deactivate()
        
    except Exception as e:
        result.add_fail("插件vs处理器API测试", str(e))
    
    return result


async def test_plugin_functionality():
    """测试插件功能完整性"""
    result = CompatibilityTestResult()
    
    try:
        plugin = await initialize_stream_plugin()
        
        # 测试工具注册
        tools = plugin.get_tools()
        if len(tools) >= 7:  # 期望至少7个工具
            result.add_pass("工具注册", f"注册了{len(tools)}个工具")
        else:
            result.add_fail("工具注册", f"工具数量不足，仅有{len(tools)}个")
        
        # 测试钩子注册
        hooks = plugin.get_hooks()
        if len(hooks) >= 6:  # 期望至少6个钩子事件
            result.add_pass("钩子注册", f"注册了{len(hooks)}个钩子事件")
        else:
            result.add_fail("钩子注册", f"钩子事件数量不足，仅有{len(hooks)}个")
        
        # 测试命令注册
        commands = plugin.get_commands()
        if len(commands) >= 3:  # 期望至少3个命令
            result.add_pass("命令注册", f"注册了{len(commands)}个命令")
        else:
            result.add_fail("命令注册", f"命令数量不足，仅有{len(commands)}个")
        
        # 测试使用工具创建流
        create_result = await plugin.create_stream_tool(
            content="工具功能测试",
            stream_type="text",
            chunk_size=5
        )
        
        if create_result['success']:
            result.add_pass("工具功能", "使用工具成功创建流")
            
            # 测试取消流
            cancel_result = await plugin.cancel_stream_tool(create_result['stream_id'])
            if cancel_result['success']:
                result.add_pass("工具功能", "使用工具成功取消流")
            else:
                result.add_fail("工具功能", "取消流失败")
        else:
            result.add_fail("工具功能", "创建流失败")
        
        await plugin.deactivate()
        
    except Exception as e:
        result.add_fail("插件功能测试", str(e))
    
    return result


async def test_backward_compatibility():
    """测试向后兼容性"""
    result = CompatibilityTestResult()
    
    try:
        # 测试工厂函数
        factory_plugin_func = stream_factory(use_plugin_mode=True)
        factory_processor = stream_factory(use_plugin_mode=False)
        
        if callable(factory_plugin_func) and factory_processor:
            result.add_pass("工厂函数", "工厂函数返回正确类型")
        else:
            result.add_fail("工厂函数", "工厂函数返回类型错误")
        
        # 测试配置管理
        config = StreamConfig({"chunk_size": 20, "delay_ms": 100})
        if config.get("chunk_size") == 20 and config.get("delay_ms") == 100:
            result.add_pass("配置管理", "配置管理功能正常")
        else:
            result.add_fail("配置管理", "配置管理功能异常")
        
        # 测试配置验证
        try:
            validate_stream_config({"chunk_size": 10, "delay_ms": 50})
            result.add_pass("配置验证", "有效配置通过验证")
        except:
            result.add_fail("配置验证", "有效配置验证失败")
        
        try:
            validate_stream_config({"chunk_size": -1, "delay_ms": 50})
            result.add_fail("配置验证", "无效配置应该抛出异常")
        except ValueError:
            result.add_pass("配置验证", "无效配置正确抛出异常")
        
        # 测试流请求创建
        request_data = {
            "content": "兼容性测试",
            "stream_type": "text",
            "chunk_size": 15
        }
        
        request = create_stream_request_from_dict(request_data)
        if request.content == "兼容性测试" and request.chunk_size == 15:
            result.add_pass("流请求创建", "从字典创建请求成功")
        else:
            result.add_fail("流请求创建", "从字典创建请求失败")
        
        # 测试统计格式化
        test_stats = {
            "total_streams": 5,
            "active_streams": 2,
            "completed_streams": 3
        }
        
        formatted = format_stream_stats(test_stats)
        if "总流数: 5" in formatted and "活跃流数: 2" in formatted:
            result.add_pass("统计格式化", "统计信息格式化正确")
        else:
            result.add_fail("统计格式化", "统计信息格式化错误")
        
    except Exception as e:
        result.add_fail("向后兼容性测试", str(e))
    
    return result


async def test_performance_comparison():
    """测试性能比较"""
    result = CompatibilityTestResult()
    
    try:
        # 测试传统处理器性能
        processor = await create_standalone_stream_processor()
        
        num_streams = 5
        start_time = time.time()
        
        stream_ids = []
        for i in range(num_streams):
            request = StreamRequest(
                stream_id=f"perf_test_{i}",
                content=f"性能测试流 {i}",
                stream_type="text"
            )
            stream_id = await processor.create_stream(request, "websocket")
            stream_ids.append(stream_id)
        
        traditional_duration = time.time() - start_time
        await processor.shutdown()
        
        # 测试插件性能
        plugin = await initialize_stream_plugin()
        
        start_time = time.time()
        
        plugin_stream_ids = []
        for i in range(num_streams):
            create_result = await plugin.create_stream_tool(
                content=f"插件性能测试流 {i}",
                stream_type="text"
            )
            if create_result['success']:
                plugin_stream_ids.append(create_result['stream_id'])
        
        plugin_duration = time.time() - start_time
        await plugin.deactivate()
        
        # 性能比较
        if traditional_duration < 2.0 and plugin_duration < 2.0:
            result.add_pass("性能比较", f"传统:{traditional_duration:.2f}s, 插件:{plugin_duration:.2f}s")
        else:
            result.add_fail("性能比较", f"性能不满足要求: 传统:{traditional_duration:.2f}s, 插件:{plugin_duration:.2f}s")
        
    except Exception as e:
        result.add_fail("性能比较测试", str(e))
    
    return result


async def test_event_system():
    """测试事件系统"""
    result = CompatibilityTestResult()
    
    try:
        plugin = await initialize_stream_plugin()
        
        # 创建事件适配器
        adapter = PluginEventAdapter(plugin)
        
        # 记录事件触发
        event_log = []
        
        async def test_listener(event_data):
            event_log.append(event_data)
        
        # 添加事件监听器
        adapter.add_listener("stream_created", test_listener)
        
        # 创建一个流来触发事件
        create_result = await plugin.create_stream_tool(
            content="事件测试",
            stream_type="text"
        )
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        if len(event_log) > 0:
            result.add_pass("事件系统", "事件监听器被正确触发")
        else:
            result.add_fail("事件系统", "事件监听器未被触发")
        
        # 清理
        await plugin.deactivate()
        
    except Exception as e:
        result.add_fail("事件系统测试", str(e))
    
    return result


async def test_error_handling():
    """测试错误处理"""
    result = CompatibilityTestResult()
    
    try:
        plugin = await initialize_stream_plugin()
        
        # 测试不存在的流
        fake_stream_id = "non_existent_stream"
        
        status_result = await plugin.get_stream_status_tool(fake_stream_id)
        if not status_result['success'] and 'error' in status_result:
            result.add_pass("错误处理", "正确处理不存在的流")
        else:
            result.add_fail("错误处理", "错误处理不正确")
        
        # 测试取消不存在的流
        cancel_result = await plugin.cancel_stream_tool(fake_stream_id)
        if not cancel_result['success']:
            result.add_pass("错误处理", "正确处理取消不存在流")
        else:
            result.add_fail("错误处理", "取消不存在流应该失败")
        
        # 测试无效参数
        try:
            invalid_result = await plugin.send_stream_chunk_tool(
                stream_id=fake_stream_id,
                content="测试",
                event_type="invalid_type"
            )
            if not invalid_result['success']:
                result.add_pass("错误处理", "正确处理无效事件类型")
            else:
                result.add_fail("错误处理", "无效事件类型应该失败")
        except:
            result.add_pass("错误处理", "无效参数抛出异常")
        
        await plugin.deactivate()
        
    except Exception as e:
        result.add_fail("错误处理测试", str(e))
    
    return result


async def run_all_compatibility_tests():
    """运行所有兼容性测试"""
    print("🚀 开始流式响应处理插件兼容性测试")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 运行所有测试
    tests = [
        ("插件初始化", test_plugin_initialization),
        ("API兼容性", test_plugin_vs_processor_api),
        ("功能完整性", test_plugin_functionality),
        ("向后兼容性", test_backward_compatibility),
        ("性能比较", test_performance_comparison),
        ("事件系统", test_event_system),
        ("错误处理", test_error_handling)
    ]
    
    all_results = CompatibilityTestResult()
    
    for test_name, test_func in tests:
        print(f"\n🔍 运行 {test_name} 测试...")
        try:
            result = await test_func()
            all_results.details.extend(result.details)
            all_results.errors.extend(result.errors)
            all_results.passed += result.passed
            all_results.failed += result.failed
            
            print(f"✅ {test_name} 测试完成")
            
        except Exception as e:
            error_msg = f"{test_name} 测试执行失败: {e}"
            all_results.add_fail(test_name, error_msg)
            print(f"❌ {test_name} 测试失败: {e}")
    
    # 打印最终结果
    success = all_results.print_summary()
    
    if success:
        print("\n🎉 所有兼容性测试通过！插件化重构成功！")
    else:
        print("\n⚠️  部分测试失败，需要进一步检查。")
    
    return success


async def test_real_world_scenario():
    """测试真实场景使用"""
    print("\n🌍 测试真实场景使用...")
    
    try:
        # 模拟真实的使用场景
        plugin = await initialize_stream_plugin({
            "stream_chunk_size": 5,
            "stream_delay_ms": 50
        })
        
        # 创建多个不同类型的流
        scenarios = [
            {"content": "文本分析任务", "stream_type": "text", "handler_type": "websocket"},
            {"content": "代码生成任务", "stream_type": "code", "handler_type": "http"},
            {"content": "实时对话", "stream_type": "chat", "handler_type": "websocket"}
        ]
        
        stream_ids = []
        for i, scenario in enumerate(scenarios):
            result = await plugin.create_stream_tool(**scenario)
            if result['success']:
                stream_ids.append(result['stream_id'])
                print(f"  ✅ 场景 {i+1} 流创建成功: {result['stream_id']}")
            else:
                print(f"  ❌ 场景 {i+1} 流创建失败: {result.get('error', 'Unknown error')}")
        
        # 获取综合统计
        stats_result = await plugin.get_stream_stats_tool()
        if stats_result['success']:
            stats = stats_result['stats']
            print(f"\n📊 综合统计:")
            print(f"  总流数: {stats['total_streams']}")
            print(f"  活跃流数: {stats['active_streams']}")
            print(f"  数据块: {stats['total_chunks_sent']}")
        
        # 测试命令功能
        status_cmd_result = await plugin.handle_stream_status_command("")
        print(f"\n💬 命令执行结果:")
        print(f"  /stream-status: {status_cmd_result[:100]}...")
        
        # 清理
        for stream_id in stream_ids:
            await plugin.cancel_stream_tool(stream_id)
        
        await plugin.deactivate()
        
        print("\n✅ 真实场景测试完成")
        return True
        
    except Exception as e:
        print(f"\n❌ 真实场景测试失败: {e}")
        return False


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        """主测试函数"""
        # 运行兼容性测试
        compatibility_success = await run_all_compatibility_tests()
        
        # 运行真实场景测试
        scenario_success = await test_real_world_scenario()
        
        print("\n" + "="*60)
        print("📋 最终测试摘要")
        print("="*60)
        print(f"🔍 兼容性测试: {'✅ 通过' if compatibility_success else '❌ 失败'}")
        print(f"🌍 真实场景测试: {'✅ 通过' if scenario_success else '❌ 失败'}")
        
        if compatibility_success and scenario_success:
            print("\n🎉 所有测试通过！流式响应处理插件化重构成功！")
            return 0
        else:
            print("\n⚠️  部分测试失败，需要进一步修复。")
            return 1
    
    # 运行测试
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
