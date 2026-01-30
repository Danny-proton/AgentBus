#!/usr/bin/env python3
"""
流式响应处理测试脚本
Stream Response Processing Test Script

测试流式响应处理的各项功能，包括流创建、管理、SSE等。
"""

import asyncio
import json
import time
from datetime import datetime
from agentbus.services.stream_response import (
    StreamResponseProcessor,
    StreamRequest,
    StreamEventType,
)
from agentbus.core.settings import settings


async def test_stream_response_processor():
    """测试流式响应处理器功能"""
    
    print("🚀 AgentBus 流式响应处理测试")
    print("=" * 50)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 初始化流式响应处理器
    print("📋 步骤 1: 初始化流式响应处理器")
    processor = StreamResponseProcessor()
    await processor.initialize()
    print("✅ 流式响应处理器初始化完成")
    
    # 2. 测试创建WebSocket流
    print("\n📋 步骤 2: 创建WebSocket流")
    websocket_request = StreamRequest(
        stream_id="ws_stream_001",
        content="请写一段关于人工智能的介绍",
        stream_type="text",
        chunk_size=5,
        delay_ms=100,
        metadata={"test": True}
    )
    ws_stream_id = await processor.create_stream(websocket_request, "websocket")
    print(f"✅ WebSocket流已创建: {ws_stream_id}")
    
    # 3. 测试创建HTTP流
    print("\n📋 步骤 3: 创建HTTP流")
    http_request = StreamRequest(
        stream_id="http_stream_001",
        content="def hello_world():",
        stream_type="code",
        chunk_size=3,
        delay_ms=150
    )
    http_stream_id = await processor.create_stream(http_request, "http")
    print(f"✅ HTTP流已创建: {http_stream_id}")
    
    # 4. 开始流式处理
    print("\n📋 步骤 4: 开始流式处理")
    
    # 开始WebSocket流处理
    ws_success = await processor.start_stream_processing(
        ws_stream_id,
        processor.simulate_ai_response
    )
    print(f"✅ WebSocket流处理已开始: {ws_success}")
    
    # 开始HTTP流处理
    http_success = await processor.start_stream_processing(
        http_stream_id,
        processor.simulate_ai_response
    )
    print(f"✅ HTTP流处理已开始: {http_success}")
    
    # 5. 监控流状态
    print("\n📋 步骤 5: 监控流状态")
    monitoring_streams = [ws_stream_id, http_stream_id]
    max_monitor_time = 15  # 最多监控15秒
    start_time = time.time()
    
    while monitoring_streams and (time.time() - start_time) < max_monitor_time:
        completed_streams = []
        
        for stream_id in monitoring_streams:
            status = await processor.get_stream_status(stream_id)
            print(f"   流 {stream_id}: {status.value if status else 'unknown'}")
            
            if status and status.value in ["completed", "error", "cancelled"]:
                completed_streams.append(stream_id)
        
        # 移除已完成的流
        for stream_id in completed_streams:
            monitoring_streams.remove(stream_id)
        
        if monitoring_streams:
            print(f"⏳ 还有 {len(monitoring_streams)} 个流在处理中...")
            await asyncio.sleep(2)
    
    if monitoring_streams:
        print("⚠️  部分流可能仍在处理中")
    
    # 6. 测试流取消
    print("\n📋 步骤 6: 测试流取消")
    
    # 创建一个新的流然后取消
    cancel_request = StreamRequest(
        stream_id="cancel_stream_001",
        content="这是一个会被取消的流",
        stream_type="text",
        chunk_size=2,
        delay_ms=200
    )
    cancel_stream_id = await processor.create_stream(cancel_request, "websocket")
    print(f"✅ 取消测试流已创建: {cancel_stream_id}")
    
    # 开始处理
    await processor.start_stream_processing(cancel_stream_id, processor.simulate_ai_response)
    await asyncio.sleep(1)  # 等待开始处理
    
    # 取消流
    cancel_success = await processor.cancel_stream(cancel_stream_id)
    print(f"✅ 流取消结果: {cancel_success}")
    
    # 7. 测试统计信息
    print("\n📋 步骤 7: 查看流统计信息")
    stats = await processor.get_stream_stats()
    print("✅ 流统计信息:")
    print(f"   活跃流: {stats['active_streams']}")
    print(f"   总流数: {stats['total_streams']}")
    print(f"   处理任务: {stats['processing_tasks']}")
    print("   按状态统计:")
    for status, count in stats['by_status'].items():
        print(f"     - {status}: {count}")
    
    # 8. 测试批量创建
    print("\n📋 步骤 8: 测试批量流创建")
    batch_streams = []
    for i in range(3):
        batch_request = StreamRequest(
            stream_id=f"batch_stream_{i+1:03d}",
            content=f"批量测试流 {i+1}",
            stream_type="text",
            chunk_size=1,
            delay_ms=50
        )
        stream_id = await processor.create_stream(batch_request, "websocket")
        batch_streams.append(stream_id)
    
    print(f"✅ 创建了 {len(batch_streams)} 个批量流")
    
    # 9. 测试SSE队列获取
    print("\n📋 步骤 9: 测试SSE队列获取")
    if batch_streams:
        test_stream_id = batch_streams[0]
        queue = await processor.get_stream_queue(test_stream_id)
        if queue:
            print(f"✅ 成功获取流队列: {test_stream_id}")
        else:
            print(f"❌ 未能获取流队列: {test_stream_id}")
    
    # 10. 清理
    print("\n📋 步骤 10: 清理资源")
    await processor.shutdown()
    print("✅ 流式响应处理器已关闭")
    
    print("\n🎉 流式响应处理测试完成！")
    print("=" * 50)


async def test_stream_handlers():
    """测试不同类型的流处理器"""
    
    print("\n🔧 测试流处理器功能")
    print("-" * 30)
    
    processor = StreamResponseProcessor()
    await processor.initialize()
    
    # 测试WebSocket处理器
    print("\n📡 测试WebSocket处理器")
    ws_handler = processor.handlers["websocket"]
    
    # 创建测试流
    test_request = StreamRequest(
        stream_id="ws_handler_test",
        content="WebSocket处理器测试",
        stream_type="text"
    )
    
    await ws_handler.start_stream(test_request)
    print("✅ WebSocket流已启动")
    
    # 发送测试数据块
    from agentbus.services.stream_response import StreamChunk
    
    test_chunk = StreamChunk(
        stream_id="ws_handler_test",
        event_type=StreamEventType.TOKEN,
        content="测试数据",
        token_count=1,
        progress=0.1
    )
    
    await ws_handler.send_chunk("ws_handler_test", test_chunk)
    print("✅ WebSocket数据块已发送")
    
    # 发送完成事件
    await ws_handler.complete_stream("ws_handler_test")
    print("✅ WebSocket流已完成")
    
    # 测试HTTP处理器
    print("\n🌐 测试HTTP处理器")
    http_handler = processor.handlers["http"]
    
    await http_handler.start_stream(test_request)
    print("✅ HTTP流已启动")
    
    await http_handler.send_chunk("ws_handler_test", test_chunk)
    print("✅ HTTP数据块已发送")
    
    await http_handler.complete_stream("ws_handler_test")
    print("✅ HTTP流已完成")
    
    await processor.shutdown()


async def test_error_handling():
    """测试错误处理"""
    
    print("\n🚫 测试错误处理")
    print("-" * 30)
    
    processor = StreamResponseProcessor()
    await processor.initialize()
    
    # 测试不存在的流
    non_existent_stream = "non_existent_stream"
    
    # 尝试获取不存在的流状态
    status = await processor.get_stream_status(non_existent_stream)
    print(f"✅ 不存在流状态查询: {status}")
    
    # 尝试取消不存在的流
    cancel_result = await processor.cancel_stream(non_existent_stream)
    print(f"✅ 不存在流取消结果: {cancel_result}")
    
    # 测试无效的处理器类型
    try:
        invalid_request = StreamRequest(
            stream_id="invalid_handler_test",
            content="测试无效处理器",
            stream_type="text"
        )
        await processor.create_stream(invalid_request, "invalid_handler")
        print("❌ 应该抛出异常但没有")
    except ValueError as e:
        print(f"✅ 正确捕获无效处理器异常: {e}")
    
    await processor.shutdown()


async def test_performance_monitoring():
    """测试性能监控"""
    
    print("\n📊 测试性能监控")
    print("-" * 30)
    
    processor = StreamResponseProcessor()
    await processor.initialize()
    
    # 创建多个流进行性能测试
    num_streams = 5
    stream_ids = []
    
    print(f"创建 {num_streams} 个测试流...")
    for i in range(num_streams):
        request = StreamRequest(
            stream_id=f"perf_test_{i+1:03d}",
            content=f"性能测试流 {i+1}",
            stream_type="text",
            chunk_size=2,
            delay_ms=50
        )
        stream_id = await processor.create_stream(request, "websocket")
        stream_ids.append(stream_id)
    
    # 记录开始时间
    start_time = time.time()
    
    # 批量开始流处理
    print("批量开始流处理...")
    for stream_id in stream_ids:
        await processor.start_stream_processing(stream_id, processor.simulate_ai_response)
    
    # 等待所有流完成
    print("等待所有流完成...")
    completed_count = 0
    while completed_count < num_streams:
        completed_count = 0
        for stream_id in stream_ids:
            status = await processor.get_stream_status(stream_id)
            if status and status.value in ["completed", "error", "cancelled"]:
                completed_count += 1
        
        if completed_count < num_streams:
            await asyncio.sleep(1)
    
    # 记录结束时间
    end_time = time.time()
    total_time = end_time - start_time
    
    # 获取最终统计
    stats = await processor.get_stream_stats()
    
    print(f"✅ 性能测试结果:")
    print(f"   流数量: {num_streams}")
    print(f"   总处理时间: {total_time:.2f}秒")
    print(f"   平均每流时间: {total_time/num_streams:.2f}秒")
    print(f"   每秒流数: {num_streams/total_time:.2f}")
    print(f"   最终活跃流: {stats['active_streams']}")
    
    await processor.shutdown()


async def main():
    """主测试函数"""
    try:
        await test_stream_response_processor()
        await test_stream_handlers()
        await test_error_handling()
        await test_performance_monitoring()
        
        print("\n🎯 所有测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())