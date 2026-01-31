"""
AgentBus 配置管理系统使用示例

这个文件展示了如何在AgentBus应用中使用新的配置管理系统。
"""

import os
import asyncio
from pathlib import Path

# 导入配置管理组件
from config import (
    ConfigManager,
    ProfileManager, 
    EnvLoader,
    SecurityManager,
    get_settings
)


async def example_basic_usage():
    """基本使用示例"""
    print("=== 基本配置使用示例 ===")
    
    # 方式1: 直接获取默认设置
    settings = get_settings()
    print(f"应用名称: {settings.app.name}")
    print(f"调试模式: {settings.app.debug}")
    print(f"日志级别: {settings.logging.level}")
    

async def example_environment_specific():
    """环境特定配置示例"""
    print("\n=== 环境特定配置示例 ===")
    
    # 方式2: 使用配置管理器加载特定环境
    config_manager = ConfigManager()
    
    # 加载开发环境配置
    os.environ["APP_ENV"] = "development"
    settings_dev = await config_manager.load_config()
    print(f"开发环境 - 数据库URL: {settings_dev.database.url}")
    print(f"开发环境 - 调试模式: {settings_dev.app.debug}")
    
    # 加载生产环境配置
    os.environ["APP_ENV"] = "production" 
    settings_prod = await config_manager.load_config()
    print(f"生产环境 - 数据库URL: {settings_prod.database.url}")
    print(f"生产环境 - 调试模式: {settings_prod.app.debug}")


async def example_profile_management():
    """配置文件管理示例"""
    print("\n=== 配置文件管理示例 ===")
    
    profile_manager = ProfileManager()
    
    # 列出可用的配置文件
    profiles = profile_manager.list_profiles()
    print(f"可用配置文件: {profiles}")
    
    # 加载特定配置文件
    base_config = await profile_manager.load_profile("base")
    dev_config = await profile_manager.load_profile("development")
    
    print(f"基础配置 - 应用名称: {base_config['app']['name']}")
    print(f"开发配置 - 应用名称: {dev_config['app']['name']}")


async def example_security_features():
    """安全功能示例"""
    print("\n=== 安全功能示例 ===")
    
    security_manager = SecurityManager()
    
    # 加密敏感数据
    sensitive_data = "my_secret_password"
    encrypted = await security_manager.encrypt_value(sensitive_data)
    print(f"原始数据: {sensitive_data}")
    print(f"加密后: {encrypted}")
    
    # 解密数据
    decrypted = await security_manager.decrypt_value(encrypted)
    print(f"解密后: {decrypted}")
    
    # 验证解密正确性
    assert sensitive_data == decrypted, "加密/解密验证失败"
    print("✓ 加密/解密验证成功")


async def example_env_loading():
    """环境变量加载示例"""
    print("\n=== 环境变量加载示例 ===")
    
    # 设置一些环境变量
    os.environ["AGENTBUS_APP_DEBUG"] = "true"
    os.environ["AGENTBUS_DATABASE_URL"] = "custom_db_url"
    
    env_loader = EnvLoader()
    env_config = await env_loader.load_from_env()
    
    print(f"从环境变量加载的调试模式: {env_config.get('app', {}).get('debug')}")
    print(f"从环境变量加载的数据库URL: {env_config.get('database', {}).get('url')}")
    
    # 清理环境变量
    del os.environ["AGENTBUS_APP_DEBUG"]
    del os.environ["AGENTBUS_DATABASE_URL"]


async def example_complete_workflow():
    """完整工作流程示例"""
    print("\n=== 完整工作流程示例 ===")
    
    # 设置环境
    os.environ["APP_ENV"] = "development"
    
    # 创建配置管理器
    config_manager = ConfigManager()
    
    try:
        # 加载完整配置（基础 + 环境特定 + 环境变量）
        settings = await config_manager.load_config()
        
        print(f"✓ 配置加载成功")
        print(f"  - 应用: {settings.app.name} v{settings.app.version}")
        print(f"  - 环境: {os.getenv('APP_ENV', 'unknown')}")
        print(f"  - 调试: {settings.app.debug}")
        print(f"  - 数据库: {settings.database.url}")
        print(f"  - Redis: {settings.redis.url}")
        
        # 模拟配置热重载
        print("\\n--- 模拟配置变更 ---")
        await config_manager.reload_config()
        print("✓ 配置重载完成")
        
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")


def main():
    """主函数"""
    print("AgentBus 配置管理系统使用示例")
    print("=" * 50)
    
    # 运行所有示例
    asyncio.run(example_basic_usage())
    asyncio.run(example_environment_specific())
    asyncio.run(example_profile_management())
    asyncio.run(example_security_features())
    asyncio.run(example_env_loading())
    asyncio.run(example_complete_workflow())
    
    print("\\n" + "=" * 50)
    print("示例运行完成！")


if __name__ == "__main__":
    main()