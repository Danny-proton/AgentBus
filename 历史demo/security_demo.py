"""
AgentBus 安全系统演示

展示如何使用AgentBus的安全系统功能，包括认证、授权、限流和加密。
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any

# 导入AgentBus安全模块
from agentbus.security import (
    AuthenticationManager,
    PermissionManager,
    RateLimiter,
    EncryptionManager,
    AuthProvider,
    TokenType,
    PermissionLevel,
    ResourceType,
    Action,
    RateLimitStrategy,
    RateLimitScope,
    CryptoUtils,
    SecureStorage,
)


async def demo_authentication():
    """演示认证功能"""
    print("\n=== 认证系统演示 ===")
    
    # 模拟设置和存储
    class MockSettings:
        SECRET_KEY = "your-secret-key-here"
    
    settings = MockSettings()
    
    # 创建认证管理器
    auth_manager = AuthenticationManager(
        settings=settings,
        db=None,  # 模拟数据库
        memory=None  # 模拟内存存储
    )
    
    # 注册用户
    try:
        user = await auth_manager.register_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123",
            roles=["user"]
        )
        print(f"✓ 用户注册成功: {user.username} ({user.email})")
    except ValueError as e:
        print(f"✗ 用户注册失败: {e}")
    
    # 用户登录
    try:
        token = await auth_manager.authenticate_user(
            email="test@example.com",
            password="TestPassword123",
            ip_address="127.0.0.1",
            user_agent="demo-browser"
        )
        if token:
            print(f"✓ 用户登录成功: {token.token[:20]}...")
            
            # 验证令牌
            verified_token = await auth_manager.verify_token(token.token)
            if verified_token:
                print(f"✓ 令牌验证成功: 用户ID {verified_token.user_id}")
            else:
                print("✗ 令牌验证失败")
        else:
            print("✗ 用户登录失败")
    except Exception as e:
        print(f"✗ 认证过程出错: {e}")


async def demo_permissions():
    """演示权限控制功能"""
    print("\n=== 权限控制系统演示 ===")
    
    # 模拟设置和存储
    class MockSettings:
        SECRET_KEY = "your-secret-key-here"
    
    settings = MockSettings()
    
    # 创建权限管理器
    perm_manager = PermissionManager(
        settings=settings,
        db=None,
        memory=None
    )
    
    # 获取所有权限
    all_permissions = []
    for perm_id in perm_manager._permissions_cache:
        perm = perm_manager.get_permission(perm_id)
        if perm:
            all_permissions.append(perm)
    
    print(f"✓ 系统默认权限数量: {len(all_permissions)}")
    
    # 显示部分权限
    print("\n系统权限示例:")
    for perm in all_permissions[:5]:
        print(f"  - {perm.id}: {perm.description}")
    
    # 获取所有角色
    all_roles = await perm_manager.role_manager.get_all_roles()
    print(f"\n✓ 系统默认角色数量: {len(all_roles)}")
    
    # 显示角色和权限
    print("\n角色权限示例:")
    for role in all_roles:
        print(f"  - {role.name}: {len(role.permissions)} 个权限")
        print(f"    权限示例: {role.permissions[:3]}...")
    
    # 演示权限检查
    user_permissions = ["agent.read", "message.create", "channel.read"]
    
    # 检查基本权限
    has_agent_read = perm_manager.check_permission(user_permissions, "agent.read")
    print(f"\n✓ 用户是否有 agent.read 权限: {has_agent_read}")
    
    # 检查资源权限
    has_channel_admin = perm_manager.check_resource_permission(
        user_permissions, ResourceType.CHANNEL, Action.ADMIN
    )
    print(f"✓ 用户是否有 channel ADMIN 权限: {has_channel_admin}")
    
    # 检查访问权限
    can_read_messages = perm_manager.check_access(
        user_permissions, ResourceType.MESSAGE, Action.READ
    )
    print(f"✓ 用户是否可以读取消息: {can_read_messages}")


async def demo_rate_limiting():
    """演示限流功能"""
    print("\n=== 限流系统演示 ===")
    
    # 模拟设置
    class MockSettings:
        pass
    
    settings = MockSettings()
    
    # 创建限流器
    rate_limiter = RateLimiter(settings)
    
    # 显示默认规则
    all_rules = rate_limiter.get_all_rules()
    print(f"✓ 默认限流规则数量: {len(all_rules)}")
    
    print("\n限流规则示例:")
    for rule in all_rules[:3]:
        print(f"  - {rule.name}:")
        print(f"    策略: {rule.strategy.value}")
        print(f"    范围: {rule.scope.value}")
        print(f"    限制: {rule.limit} 请求 / {rule.window} 秒")
    
    # 模拟API请求限流检查
    endpoint = "/api/messages"
    user_id = "user123"
    ip_address = "192.168.1.100"
    
    print(f"\n模拟API请求: {endpoint}")
    print(f"用户ID: {user_id}, IP: {ip_address}")
    
    # 检查限流
    rate_limit_result = await rate_limiter.check_rate_limit(
        endpoint=endpoint,
        user_id=user_id,
        ip_address=ip_address
    )
    
    print(f"✓ 限流检查结果:")
    print(f"  允许请求: {rate_limit_result['allowed']}")
    print(f"  检查规则数: {rate_limit_result['rules_checked']}")
    
    if rate_limit_result['results']:
        print(f"  规则检查详情:")
        for result in rate_limit_result['results']:
            status = "✓" if result['allowed'] else "✗"
            print(f"    {status} {result['rule_name']}: {result['allowed']}")
    
    # 获取限流状态
    status = await rate_limiter.get_rate_limit_status(
        endpoint=endpoint,
        user_id=user_id,
        ip_address=ip_address
    )
    
    print(f"\n✓ 限流状态:")
    for rule_status in status['rules']:
        print(f"  - {rule_status['rule_name']}:")
        print(f"    当前使用: {rule_status['current_count']}/{rule_status['limit']}")
        print(f"    剩余: {rule_status['remaining']}")
        print(f"    使用率: {rule_status['percentage']:.1f}%")


async def demo_encryption():
    """演示加密功能"""
    print("\n=== 加密系统演示 ===")
    
    # 模拟设置和存储
    class MockSettings:
        pass
    
    settings = MockSettings()
    
    # 创建加密管理器
    encryption_manager = EncryptionManager(
        settings=settings,
        db=None,
        memory=None
    )
    
    # 初始化
    await encryption_manager.initialize()
    print("✓ 加密管理器初始化完成")
    
    # 演示对称加密
    test_data = "这是一段需要加密的敏感数据！"
    print(f"\n原始数据: {test_data}")
    
    # 加密数据
    secure_data = await encryption_manager.encrypt_data(test_data)
    print(f"✓ 数据加密成功:")
    print(f"  数据ID: {secure_data.data_id}")
    print(f"  加密算法: {secure_data.encryption_algorithm}")
    print(f"  使用密钥: {secure_data.key_id}")
    
    # 解密数据
    decrypted_data = await encryption_manager.decrypt_data(secure_data)
    decrypted_text = decrypted_data.decode('utf-8')
    print(f"✓ 数据解密成功: {decrypted_text}")
    print(f"✓ 数据完整性验证: {'通过' if decrypted_text == test_data else '失败'}")
    
    # 演示密码加密
    password = "my-secret-password"
    print(f"\n使用密码加密:")
    print(f"密码: {password}")
    
    password_encrypted = await encryption_manager.encrypt_with_password(test_data, password)
    print(f"✓ 密码加密成功: {len(password_encrypted)} 字节")
    
    password_decrypted = await encryption_manager.decrypt_with_password(password_encrypted, password)
    password_decrypted_text = password_decrypted.decode('utf-8')
    print(f"✓ 密码解密成功: {password_decrypted_text}")
    print(f"✓ 密码加密验证: {'通过' if password_decrypted_text == test_data else '失败'}")
    
    # 演示安全存储
    secure_storage = SecureStorage(encryption_manager)
    storage_key = "demo-secret-data"
    storage_value = "这是存储在安全空间中的机密信息"
    
    print(f"\n安全存储演示:")
    print(f"存储键: {storage_key}")
    print(f"存储值: {storage_value}")
    
    # 存储数据
    stored = await secure_storage.store_secure(storage_key, storage_value, password="storage-password")
    if stored:
        print("✓ 数据安全存储成功")
    else:
        print("✗ 数据安全存储失败")
    
    # 检索数据
    retrieved = await secure_storage.retrieve_secure(storage_key, password="storage-password")
    if retrieved:
        retrieved_text = retrieved.decode('utf-8')
        print(f"✓ 数据检索成功: {retrieved_text}")
        print(f"✓ 存储验证: {'通过' if retrieved_text == storage_value else '失败'}")
    else:
        print("✗ 数据检索失败")
    
    # 演示加密工具
    print(f"\n加密工具演示:")
    
    # 生成随机数据
    random_bytes = CryptoUtils.generate_random_bytes(32)
    print(f"✓ 生成随机字节: {len(random_bytes)} 字节")
    
    # 生成安全令牌
    token = CryptoUtils.generate_token(32)
    print(f"✓ 生成安全令牌: {token[:20]}...")
    
    # 计算哈希
    data_bytes = test_data.encode('utf-8')
    hash_result = CryptoUtils.compute_hash(data_bytes)
    print(f"✓ SHA256哈希: {CryptoUtils.base64_encode(hash_result)}")
    
    # Base64编码/解码
    encoded = CryptoUtils.base64_encode(data_bytes)
    decoded = CryptoUtils.base64_decode(encoded)
    print(f"✓ Base64编码/解码: {'通过' if decoded == data_bytes else '失败'}")


async def demo_security_workflow():
    """演示完整的安全工作流程"""
    print("\n=== 完整安全工作流程演示 ===")
    
    # 模拟一个API访问场景
    class MockSettings:
        SECRET_KEY = "workflow-secret-key"
    
    settings = MockSettings()
    
    # 初始化各个组件
    auth_manager = AuthenticationManager(settings, None, None)
    perm_manager = PermissionManager(settings, None, None)
    rate_limiter = RateLimiter(settings)
    encryption_manager = EncryptionManager(settings, None, None)
    await encryption_manager.initialize()
    
    print("✓ 所有安全组件初始化完成")
    
    # 1. 用户注册和认证
    print("\n1. 用户注册和认证:")
    try:
        user = await auth_manager.register_user(
            username="apideveloper",
            email="dev@example.com",
            password="SecurePassword123",
            roles=["developer"]
        )
        print(f"  ✓ 用户注册: {user.username}")
        
        # 登录获取令牌
        token = await auth_manager.authenticate_user(
            email="dev@example.com",
            password="SecurePassword123"
        )
        if token:
            print(f"  ✓ 用户登录成功")
        else:
            print(f"  ✗ 用户登录失败")
    except Exception as e:
        print(f"  ✗ 认证过程出错: {e}")
    
    # 2. 权限检查
    print("\n2. 权限检查:")
    user_permissions = await perm_manager.role_manager.get_user_permissions(user.id if 'user' in locals() else "unknown")
    if not user_permissions:
        # 如果没有权限，使用默认用户权限
        user_permissions = ["agent.read", "message.create", "channel.read"]
    
    print(f"  用户权限: {user_permissions[:3]}...")
    
    # 检查API访问权限
    can_access_api = perm_manager.check_access(user_permissions, ResourceType.AGENT, Action.READ)
    print(f"  ✓ API访问权限检查: {'通过' if can_access_api else '拒绝'}")
    
    # 3. 限流检查
    print("\n3. 限流检查:")
    api_endpoint = "/api/agents/list"
    
    rate_limit_result = await rate_limiter.check_rate_limit(
        endpoint=api_endpoint,
        user_id=user.id if 'user' in locals() else "unknown",
        ip_address="192.168.1.100"
    )
    
    print(f"  API端点: {api_endpoint}")
    print(f"  ✓ 限流检查: {'通过' if rate_limit_result['allowed'] else '拒绝'}")
    
    # 4. 敏感数据加密
    print("\n4. 敏感数据处理:")
    sensitive_data = {
        "user_info": "用户敏感信息",
        "api_keys": "API密钥数据",
        "config": "系统配置信息"
    }
    
    # 加密敏感数据
    encrypted_data = {}
    for key, value in sensitive_data.items():
        secure_data = await encryption_manager.encrypt_data(value)
        encrypted_data[key] = secure_data
        print(f"  ✓ 加密 {key}: {secure_data.encryption_algorithm}")
    
    # 解密验证
    print(f"  数据解密验证:")
    for key, secure_data in encrypted_data.items():
        decrypted = await encryption_manager.decrypt_data(secure_data)
        original_value = sensitive_data[key]
        decrypted_value = decrypted.decode('utf-8')
        is_valid = decrypted_value == original_value
        print(f"    {key}: {'✓ 通过' if is_valid else '✗ 失败'}")
    
    print("\n✓ 完整安全工作流程演示完成")


async def main():
    """主演示函数"""
    print("AgentBus 安全系统演示")
    print("=" * 50)
    
    try:
        # 演示各个安全功能
        await demo_authentication()
        await demo_permissions()
        await demo_rate_limiting()
        await demo_encryption()
        await demo_security_workflow()
        
        print("\n" + "=" * 50)
        print("✓ 所有演示完成！")
        print("\n安全系统特性:")
        print("• 🔐 完整的认证系统 (JWT, OAuth, API Key)")
        print("• 🛡️  基于角色的权限控制 (RBAC)")
        print("• ⚡ 多种限流策略 (令牌桶, 滑动窗口, 固定窗口)")
        print("• 🔒 数据加密和密钥管理")
        print("• 🏗️  模块化设计，易于扩展")
        print("• 🔄 与Moltbot安全架构兼容")
        
    except Exception as e:
        print(f"\n✗ 演示过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())