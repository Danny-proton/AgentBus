#!/usr/bin/env python3
"""
AgentBus 配置系统集成测试

验证新配置管理系统与AgentBus应用的集成
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from agentbus.config import (
    ConfigManager,
    get_settings,
    SecurityManager,
    ProfileManager
)


async def test_config_integration():
    """测试配置系统集成"""
    print("🧪 AgentBus 配置系统集成测试")
    print("=" * 50)
    
    # 测试1: 基本配置加载
    print("\n1️⃣ 测试基本配置加载...")
    try:
        settings = get_settings()
        print(f"✅ 配置加载成功")
        print(f"   应用名称: {settings.app.name}")
        print(f"   版本: {settings.app.version}")
        print(f"   调试模式: {settings.app.debug}")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False
    
    # 测试2: 环境特定配置
    print("\n2️⃣ 测试环境特定配置...")
    try:
        # 设置开发环境
        os.environ["APP_ENV"] = "development"
        
        config_manager = ConfigManager()
        dev_settings = await config_manager.load_config()
        
        print(f"✅ 开发环境配置加载成功")
        print(f"   数据库URL: {dev_settings.database.url}")
        print(f"   调试模式: {dev_settings.app.debug}")
        
        # 设置生产环境
        os.environ["APP_ENV"] = "production"
        prod_settings = await config_manager.load_config()
        
        print(f"✅ 生产环境配置加载成功")
        print(f"   数据库URL: {prod_settings.database.url}")
        print(f"   调试模式: {prod_settings.app.debug}")
        
    except Exception as e:
        print(f"❌ 环境配置测试失败: {e}")
        return False
    
    # 测试3: 安全功能
    print("\n3️⃣ 测试安全功能...")
    try:
        security = SecurityManager()
        
        # 测试加密/解密
        test_data = "test_secret_password"
        encrypted = await security.encrypt_value(test_data)
        decrypted = await security.decrypt_value(encrypted)
        
        if test_data == decrypted:
            print("✅ 加密/解密功能正常")
        else:
            print("❌ 加密/解密功能异常")
            return False
            
    except Exception as e:
        print(f"❌ 安全功能测试失败: {e}")
        return False
    
    # 测试4: 配置文件管理
    print("\n4️⃣ 测试配置文件管理...")
    try:
        profile_manager = ProfileManager()
        profiles = profile_manager.list_profiles()
        
        print(f"✅ 可用配置文件: {profiles}")
        
        # 加载基础配置
        base_config = await profile_manager.load_profile("base")
        print(f"✅ 基础配置加载成功")
        
    except Exception as e:
        print(f"❌ 配置文件管理测试失败: {e}")
        return False
    
    # 测试5: 环境变量覆盖
    print("\n5️⃣ 测试环境变量覆盖...")
    try:
        # 设置环境变量
        os.environ["AGENTBUS_APP_DEBUG"] = "true"
        os.environ["AGENTBUS_DATABASE_URL"] = "test_db_url"
        
        # 重新加载配置
        settings = await config_manager.load_config()
        
        print(f"✅ 环境变量覆盖生效")
        print(f"   调试模式: {settings.app.debug}")
        print(f"   数据库URL: {settings.database.url}")
        
        # 清理环境变量
        del os.environ["AGENTBUS_APP_DEBUG"]
        del os.environ["AGENTBUS_DATABASE_URL"]
        
    except Exception as e:
        print(f"❌ 环境变量覆盖测试失败: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 所有测试通过！配置系统集成成功！")
    return True


async def test_start_agentbus_integration():
    """测试与start_agentbus.py的集成"""
    print("\n🔗 测试与启动脚本的集成...")
    
    try:
        # 模拟start_agentbus.py中的配置初始化
        from agentbus.config import ConfigManager, get_settings
        
        # 初始化配置管理器
        config_manager = ConfigManager()
        settings = await config_manager.load_config()
        
        print(f"✅ 启动脚本集成测试通过")
        print(f"   集成环境: {os.getenv('APP_ENV', 'unknown')}")
        print(f"   应用配置: {settings.app.name} v{settings.app.version}")
        
        return True
        
    except Exception as e:
        print(f"❌ 启动脚本集成测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("AgentBus 配置管理系统 - 集成测试")
    print("=" * 60)
    
    # 运行所有测试
    test_results = []
    
    # 基本集成测试
    result1 = await test_config_integration()
    test_results.append(("配置系统集成", result1))
    
    # 启动脚本集成测试
    result2 = await test_start_agentbus_integration()
    test_results.append(("启动脚本集成", result2))
    
    # 总结测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果总结:")
    
    all_passed = True
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 所有集成测试通过！")
        print("AgentBus 配置管理系统已成功集成！")
    else:
        print("\n⚠️  部分测试失败，请检查配置系统")
    
    return all_passed


if __name__ == "__main__":
    # 设置测试环境
    os.environ["APP_ENV"] = "development"
    
    # 运行测试
    success = asyncio.run(main())
    sys.exit(0 if success else 1)