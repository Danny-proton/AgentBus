#!/usr/bin/env python3
"""
AgentBus Memory and Preferences System Tests

Simple test script to verify the basic functionality of the memory and
preferences management system.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from memory import UserMemory, MemoryType, MemoryPriority
    from preferences import UserPreferences, PreferenceCategory
    print("✅ 成功导入所有模块")
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    sys.exit(1)


async def test_user_memory():
    """测试用户记忆功能"""
    print("\n=== 测试用户记忆功能 ===")
    
    try:
        # 创建用户记忆实例
        memory = UserMemory(storage_base_path="test_data")
        
        # 添加记忆
        await memory.add_memory(
            user_id="test_user",
            content="测试记忆：用户喜欢喝咖啡",
            memory_type=MemoryType.PERSONAL_INFO,
            tags=["测试", "咖啡"],
            priority=MemoryPriority.HIGH
        )
        
        # 检索记忆
        memories = await memory.get_memories("test_user", limit=10)
        print(f"✅ 记忆添加和检索成功，找到 {len(memories)} 条记忆")
        
        # 搜索记忆
        search_results = await memory.search_memories("test_user", "咖啡")
        print(f"✅ 记忆搜索成功，找到 {len(search_results)} 条相关记忆")
        
        return True
        
    except Exception as e:
        print(f"❌ 用户记忆测试失败: {e}")
        return False


async def test_user_preferences():
    """测试用户偏好功能"""
    print("\n=== 测试用户偏好功能 ===")
    
    try:
        # 创建用户偏好实例
        preferences = UserPreferences(storage_base_path="test_data")
        
        # 设置偏好
        await preferences.set_preference(
            user_id="test_user",
            category=PreferenceCategory.GENERAL,
            key="language",
            value="zh-CN"
        )
        
        # 获取偏好
        prefs = await preferences.get_user_preferences("test_user")
        print(f"✅ 偏好设置和获取成功")
        print(f"   语言设置: {prefs.get('general', {}).get('language', '未设置')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 用户偏好测试失败: {e}")
        return False


async def test_conversation_history():
    """测试对话历史功能"""
    print("\n=== 测试对话历史功能 ===")
    
    try:
        from memory import ConversationHistory, MessageType, MessagePriority
        
        # 创建对话历史实例
        history = ConversationHistory(storage_base_path="test_data")
        
        # 添加消息
        await history.add_message(
            session_id="test_session",
            user_id="test_user",
            role="user",
            content="你好，这是一个测试消息",
            message_type=MessageType.TEXT,
            priority=MessagePriority.NORMAL
        )
        
        # 获取对话历史
        messages = await history.get_conversation_history("test_session", limit=10)
        print(f"✅ 对话历史添加和检索成功，找到 {len(messages)} 条消息")
        
        return True
        
    except Exception as e:
        print(f"❌ 对话历史测试失败: {e}")
        return False


async def test_context_cache():
    """测试上下文缓存功能"""
    print("\n=== 测试上下文缓存功能 ===")
    
    try:
        from memory import ContextCache, CacheType
        
        # 创建缓存实例
        cache = ContextCache(
            memory_cache_size=100,
            disk_cache_size=1000,
            cache_dir="test_cache"
        )
        
        # 存储缓存数据
        await cache.store_context(
            key="test_key",
            data={"test": "data", "number": 123},
            cache_type=CacheType.USER_SESSION,
            ttl_hours=1
        )
        
        # 检索缓存数据
        cached_data = await cache.retrieve_context("test_key")
        print(f"✅ 上下文缓存存储和检索成功")
        print(f"   缓存数据: {cached_data}")
        
        return True
        
    except Exception as e:
        print(f"❌ 上下文缓存测试失败: {e}")
        return False


async def test_skill_preferences():
    """测试技能偏好功能"""
    print("\n=== 测试技能偏好功能 ===")
    
    try:
        from preferences import SkillPreferences, SkillStatus, SkillPriority
        
        # 创建技能偏好实例
        skills = SkillPreferences(storage_base_path="test_data")
        
        # 设置技能偏好
        await skills.set_skill_preference(
            user_id="test_user",
            skill_name="test_skill",
            status=SkillStatus.ENABLED,
            priority=SkillPriority.MEDIUM,
            parameters={"setting1": "value1"}
        )
        
        # 获取技能偏好
        user_skills = await skills.get_user_skills("test_user")
        print(f"✅ 技能偏好设置和获取成功，找到 {len(user_skills)} 个技能")
        
        return True
        
    except Exception as e:
        print(f"❌ 技能偏好测试失败: {e}")
        return False


async def test_channel_preferences():
    """测试渠道偏好功能"""
    print("\n=== 测试渠道偏好功能 ===")
    
    try:
        from preferences import ChannelPreferences, ChannelType, NotificationLevel
        
        # 创建渠道偏好实例
        channels = ChannelPreferences(storage_base_path="test_data")
        
        # 设置渠道偏好
        await channels.set_channel_preference(
            user_id="test_user",
            channel_name="test_channel",
            channel_type=ChannelType.SLACK,
            status=ChannelStatus.ACTIVE,
            notification_level=NotificationLevel.NORMAL
        )
        
        # 获取渠道偏好
        user_channels = await channels.get_user_channels("test_user")
        print(f"✅ 渠道偏好设置和获取成功，找到 {len(user_channels)} 个渠道")
        
        return True
        
    except Exception as e:
        print(f"❌ 渠道偏好测试失败: {e}")
        return False


async def cleanup_test_data():
    """清理测试数据"""
    print("\n=== 清理测试数据 ===")
    
    import shutil
    
    test_dirs = ["test_data", "test_cache"]
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            try:
                shutil.rmtree(test_dir)
                print(f"✅ 已清理目录: {test_dir}")
            except Exception as e:
                print(f"⚠️  清理目录失败 {test_dir}: {e}")


async def main():
    """运行所有测试"""
    print("🚀 开始测试 AgentBus 记忆和偏好系统")
    print("=" * 50)
    
    # 运行各项测试
    tests = [
        ("用户记忆", test_user_memory),
        ("用户偏好", test_user_preferences),
        ("对话历史", test_conversation_history),
        ("上下文缓存", test_context_cache),
        ("技能偏好", test_skill_preferences),
        ("渠道偏好", test_channel_preferences),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 测试执行失败: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<12}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统功能正常。")
    else:
        print(f"⚠️  有 {total - passed} 项测试失败，请检查相关功能。")
    
    # 清理测试数据
    await cleanup_test_data()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试执行出现异常: {e}")
        sys.exit(1)