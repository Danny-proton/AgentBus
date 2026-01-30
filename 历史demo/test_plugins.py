"""
AgentBus插件框架测试脚本

此脚本用于测试插件框架的基本功能，包括：
- 插件管理器初始化
- 插件加载和激活
- 工具和钩子注册
- 事件调度
"""

import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentbus.plugins import PluginManager, PluginContext
from agentbus.plugins.example_plugin import ExamplePlugin


async def test_plugin_framework():
    """测试插件框架"""
    print("🚀 开始测试AgentBus插件框架")
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建插件上下文
    context = PluginContext(
        config={
            'example_plugin': {
                'debug': True,
                'max_messages': 1000
            }
        },
        logger=logging.getLogger('agentbus.test'),
        runtime={
            'test_mode': True,
            'version': '1.0.0'
        }
    )
    
    # 创建插件管理器
    manager = PluginManager(context)
    print("✅ 插件管理器创建成功")
    
    # 测试插件发现
    print("\n📋 测试插件发现...")
    discovered = await manager.discover_plugins()
    print(f"发现 {len(discovered)} 个插件:")
    for plugin_info in discovered:
        print(f"  - {plugin_info.name} ({plugin_info.plugin_id}) v{plugin_info.version}")
    
    # 手动创建示例插件进行测试
    print("\n🔧 手动创建示例插件...")
    try:
        plugin = ExamplePlugin("test_example", context)
        print(f"✅ 插件创建成功: {plugin}")
        
        # 获取插件信息
        info = plugin.get_info()
        print(f"📄 插件信息:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        # 测试工具注册
        print(f"\n🔧 注册的工具数量: {len(plugin.get_tools())}")
        
        # 测试钩子注册
        hooks = plugin.get_hooks()
        print(f"🪝 注册的事件钩子:")
        for event, event_hooks in hooks.items():
            print(f"  {event}: {len(event_hooks)} 个钩子")
        
        # 测试命令注册
        commands = plugin.get_commands()
        print(f"⚡ 注册的命令数量: {len(commands)}")
        
        # 测试插件激活
        print(f"\n⚡ 测试插件激活...")
        success = await plugin.activate()
        print(f"插件激活状态: {'成功' if success else '失败'}")
        
        # 测试工具执行
        print(f"\n🛠️  测试工具执行...")
        
        # 测试计数工具
        count = plugin.count_messages()
        print(f"当前消息计数: {count}")
        
        # 测试回显工具
        echo_result = plugin.echo_message("Hello, AgentBus!")
        print(f"回显结果: {echo_result}")
        
        # 测试异步工具
        async_result = await plugin.async_task(1)
        print(f"异步任务结果: {async_result}")
        
        # 测试钩子执行
        print(f"\n🪝 测试钩子执行...")
        await plugin.on_message_received("测试消息", "test_user")
        print(f"钩子执行后消息计数: {plugin.count_messages()}")
        
        # 测试命令执行
        print(f"\n⚡ 测试命令执行...")
        count_result = await plugin.handle_count_command("")
        print(f"计数命令结果: {count_result}")
        
        status_result = await plugin.handle_status_command("")
        print(f"状态命令结果: {status_result}")
        
    except Exception as e:
        print(f"❌ 插件测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试插件管理器功能
    print(f"\n📊 测试插件管理器统计...")
    stats = await manager.get_plugin_stats()
    print("插件系统统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print(f"\n🎉 AgentBus插件框架测试完成!")


async def test_plugin_lifecycle():
    """测试插件生命周期管理"""
    print(f"\n🔄 测试插件生命周期管理...")
    
    # 设置日志
    logging.basicConfig(level=logging.WARNING)
    
    context = PluginContext(
        config={},
        logger=logging.getLogger('agentbus.lifecycle'),
        runtime={}
    )
    
    manager = PluginManager(context)
    
    # 模拟插件生命周期
    try:
        # 创建插件实例
        plugin = ExamplePlugin("lifecycle_test", context)
        print("✅ 插件创建完成")
        
        # 激活插件
        success = await plugin.activate()
        print(f"⚡ 插件激活: {'成功' if success else '失败'}")
        
        # 停用插件
        success = await plugin.deactivate()
        print(f"🛑 插件停用: {'成功' if success else '失败'}")
        
        print("✅ 插件生命周期测试完成")
        
    except Exception as e:
        print(f"❌ 插件生命周期测试失败: {e}")


if __name__ == "__main__":
    print("AgentBus插件框架测试")
    print("=" * 50)
    
    # 运行基础功能测试
    asyncio.run(test_plugin_framework())
    
    # 运行生命周期测试
    asyncio.run(test_plugin_lifecycle())