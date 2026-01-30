#!/usr/bin/env python3
"""
会话管理系统测试脚本
Session Management System Test Script

测试AgentBus会话管理系统的核心功能
"""

import asyncio
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sessions import (
    # 导入核心类
    SessionContext, SessionType, SessionStatus, Message, MessageType, Platform,
    
    # 导入管理器和存储
    SessionManager, 
    MemorySessionStore, FileSessionStore, DatabaseSessionStore,
    StorageType,
    
    # 导入便利函数
    initialize_sessions, create_session, get_session, add_message,
    
    # 导入上下文管理
    get_context_manager, session_context
)


async def test_basic_session_operations():
    """测试基本会话操作"""
    print("🔧 测试基本会话操作...")
    
    # 创建内存存储
    store = MemorySessionStore()
    manager = SessionManager(session_store=store)
    await manager.start()
    
    try:
        # 1. 创建会话
        session = await manager.create_session(
            chat_id="test_chat_123",
            user_id="user_456",
            platform=Platform.TELEGRAM,
            session_type=SessionType.PRIVATE,
            ai_model="gpt-3.5-turbo"
        )
        
        print(f"✅ 会话创建成功: {session.session_id}")
        print(f"   聊天ID: {session.chat_id}")
        print(f"   用户ID: {session.user_id}")
        print(f"   平台: {session.platform}")
        print(f"   类型: {session.session_type}")
        
        # 2. 获取会话
        retrieved_session = await manager.get_session(session.session_id)
        assert retrieved_session is not None
        assert retrieved_session.session_id == session.session_id
        print("✅ 会话获取成功")
        
        # 3. 添加消息
        message = Message(
            id="msg_001",
            content="你好，这是一个测试消息",
            user_id="user_456",
            timestamp=datetime.now(),
            message_type=MessageType.TEXT,
            platform=Platform.TELEGRAM,
            chat_id="test_chat_123",
            session_id=session.session_id
        )
        
        success = await manager.add_message_to_session(session.session_id, message)
        assert success
        print("✅ 消息添加成功")
        
        # 4. 获取会话消息
        messages = await manager.get_session_messages(session.session_id, 5)
        assert len(messages) == 1
        print(f"✅ 获取消息成功，共 {len(messages)} 条")
        
        # 5. 会话摘要
        summary = await manager.get_session_summary(session.session_id)
        assert summary is not None
        print(f"✅ 会话摘要: {summary['message_count']} 条消息")
        
    finally:
        await manager.stop()
    
    print("✅ 基本会话操作测试通过\n")


async def test_session_storage_types():
    """测试不同存储类型"""
    print("💾 测试不同存储类型...")
    
    storage_types = [
        ("内存存储", MemorySessionStore()),
        ("文件存储", FileSessionStore("./test_sessions")),
        ("数据库存储", DatabaseSessionStore("./test_agentbus.db"))
    ]
    
    for name, store in storage_types:
        print(f"🔧 测试 {name}...")
        
        manager = SessionManager(session_store=store)
        await manager.start()
        
        try:
            # 创建会话
            session = await manager.create_session(
                chat_id=f"test_chat_{name}",
                user_id="user_test",
                platform=Platform.WEB,
                session_type=SessionType.GROUP
            )
            
            # 验证存储
            retrieved = await manager.get_session(session.session_id)
            assert retrieved is not None
            assert retrieved.session_id == session.session_id
            
            print(f"✅ {name} 测试通过")
            
        except Exception as e:
            print(f"❌ {name} 测试失败: {str(e)}")
            
        finally:
            await manager.stop()
    
    print("✅ 存储类型测试完成\n")


async def test_session_lifecycle():
    """测试会话生命周期管理"""
    print("🔄 测试会话生命周期...")
    
    store = MemorySessionStore()
    manager = SessionManager(session_store=store)
    await manager.start()
    
    try:
        # 创建会话
        session = await manager.create_session(
            chat_id="test_chat_lifecycle",
            user_id="user_lifecycle",
            platform=Platform.DISCORD
        )
        
        # 测试扩展生命周期
        success = await manager.extend_session_lifetime(session.session_id, 3600)
        assert success
        print("✅ 生命周期扩展成功")
        
        # 测试重置历史
        success = await manager.reset_session_history(session.session_id, keep_recent=0)
        assert success
        print("✅ 历史重置成功")
        
        # 测试删除会话
        success = await manager.delete_session(session.session_id)
        assert success
        
        # 验证删除
        retrieved = await manager.get_session(session.session_id)
        assert retrieved is None
        print("✅ 会话删除成功")
        
    finally:
        await manager.stop()
    
    print("✅ 会话生命周期测试通过\n")


async def test_context_manager():
    """测试上下文管理器"""
    print("🧠 测试上下文管理器...")
    
    context_manager = get_context_manager()
    
    # 创建上下文
    context = await context_manager.create_context(
        session_id="ctx_test_001",
        chat_id="test_chat_ctx",
        user_id="user_ctx",
        platform=Platform.SLACK,
        session_type=SessionType.PRIVATE
    )
    
    assert context is not None
    assert context.session_id == "ctx_test_001"
    print("✅ 上下文创建成功")
    
    # 获取上下文
    retrieved = await context_manager.get_context("ctx_test_001")
    assert retrieved is not None
    assert retrieved.session_id == "ctx_test_001"
    print("✅ 上下文获取成功")
    
    # 更新上下文
    context.set_data("test_key", "test_value")
    await context_manager.update_context(context)
    
    # 验证更新
    updated = await context_manager.get_context("ctx_test_001")
    assert updated.get_data("test_key") == "test_value"
    print("✅ 上下文更新成功")
    
    # 获取统计信息
    stats = await context_manager.get_cache_stats()
    assert "total_contexts" in stats
    print(f"✅ 上下文统计: {stats['total_contexts']} 个上下文")
    
    print("✅ 上下文管理器测试通过\n")


async def test_session_context_decorator():
    """测试会话上下文装饰器"""
    print("🎯 测试会话上下文装饰器...")
    
    store = MemorySessionStore()
    manager = SessionManager(session_store=store)
    await manager.start()
    
    try:
        async def process_with_session():
            async with session_context(
                manager,
                chat_id="decorator_test",
                user_id="user_decorator",
                platform=Platform.WHATSAPP
            ) as session:
                assert session is not None
                assert session.chat_id == "decorator_test"
                
                # 添加一些数据
                session.set_data("decorator_test", "success")
                
                return session.session_id
        
        session_id = await process_with_session()
        assert session_id is not None
        print("✅ 会话上下文装饰器测试成功")
        
    finally:
        await manager.stop()
    
    print("✅ 会话上下文装饰器测试通过\n")


async def test_concurrent_sessions():
    """测试并发会话管理"""
    print("⚡ 测试并发会话管理...")
    
    store = MemorySessionStore()
    manager = SessionManager(session_store=store)
    await manager.start()
    
    try:
        # 创建多个会话
        tasks = []
        for i in range(10):
            task = manager.create_session(
                chat_id=f"concurrent_chat_{i}",
                user_id=f"concurrent_user_{i % 3}",  # 3个用户
                platform=Platform.TELEGRAM
            )
            tasks.append(task)
        
        sessions = await asyncio.gather(*tasks)
        assert len(sessions) == 10
        print(f"✅ 创建了 {len(sessions)} 个并发会话")
        
        # 获取用户的会话
        user_sessions = await manager.get_user_sessions("concurrent_user_0")
        assert len(user_sessions) >= 3  # 至少3个会话
        print(f"✅ 用户0有 {len(user_sessions)} 个会话")
        
        # 清理所有过期会话
        cleaned = await manager.cleanup_all_expired()
        print(f"✅ 清理了 {cleaned} 个过期会话")
        
    finally:
        await manager.stop()
    
    print("✅ 并发会话管理测试通过\n")


async def main():
    """主测试函数"""
    print("🚀 开始会话管理系统测试")
    print("=" * 50)
    
    try:
        await test_basic_session_operations()
        await test_session_storage_types()
        await test_session_lifecycle()
        await test_context_manager()
        await test_session_context_decorator()
        await test_concurrent_sessions()
        
        print("🎉 所有测试通过！")
        print("=" * 50)
        
        # 显示统计信息
        store = MemorySessionStore()
        manager = SessionManager(session_store=store)
        await manager.start()
        
        stats = await manager.get_session_stats()
        print("📊 系统统计:")
        print(f"   存储类型: {stats['storage']['storage_type']}")
        print(f"   总会话数: {stats['storage']['total_sessions']}")
        
        await manager.stop()
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)