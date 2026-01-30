"""
AgentBus 安全系统测试

测试安全系统的基本功能，包括认证、权限、限流和加密。
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock

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
)


class TestAuthentication:
    """测试认证系统"""
    
    def setup_method(self):
        """设置测试环境"""
        self.mock_settings = Mock()
        self.mock_settings.SECRET_KEY = "test-secret-key"
        self.mock_db = Mock()
        self.mock_memory = Mock()
        
        # 模拟内存存储
        self.mock_memory.get = Mock(return_value=None)
        self.mock_memory.set = Mock()
        self.mock_memory.delete = Mock()
        
        self.auth_manager = AuthenticationManager(
            settings=self.mock_settings,
            db=self.mock_db,
            memory=self.mock_memory
        )
    
    @pytest.mark.asyncio
    async def test_user_registration(self):
        """测试用户注册"""
        # 模拟用户不存在
        self.mock_memory.get.return_value = None
        
        # 注册用户
        user = await self.auth_manager.register_user(
            username="testuser",
            email="test@example.com", 
            password="TestPassword123"
        )
        
        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active == True
        assert AuthProvider.LOCAL in [user.provider]
        
        # 验证密码被哈希
        assert user.hashed_password != "TestPassword123"
    
    @pytest.mark.asyncio
    async def test_password_validation(self):
        """测试密码验证"""
        # 测试弱密码
        with pytest.raises(ValueError, match="密码长度至少8位"):
            await self.auth_manager.register_user(
                "user", "test@example.com", "123"
            )
        
        # 测试缺少大写字母
        with pytest.raises(ValueError, match="密码必须包含至少一个大写字母"):
            await self.auth_manager.register_user(
                "user", "test@example.com", "password123"
            )
        
        # 测试缺少数字
        with pytest.raises(ValueError, match="密码必须包含至少一个数字"):
            await self.auth_manager.register_user(
                "user", "test@example.com", "PasswordOnly"
            )
    
    @pytest.mark.asyncio
    async def test_user_authentication(self):
        """测试用户认证"""
        # 先注册用户
        user = await self.auth_manager.register_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123"
        )
        
        # 模拟用户数据返回
        user_data = user.to_dict()
        user_data['hashed_password'] = user.hashed_password
        self.mock_memory.get.return_value = user_data
        
        # 测试正确密码认证
        token = await self.auth_manager.authenticate_user(
            email="test@example.com",
            password="TestPassword123",
            ip_address="127.0.0.1"
        )
        
        assert token is not None
        assert token.token_type == TokenType.ACCESS
        
        # 测试错误密码认证
        token = await self.auth_manager.authenticate_user(
            email="test@example.com",
            password="WrongPassword",
            ip_address="127.0.0.1"
        )
        
        assert token is None


class TestPermissions:
    """测试权限系统"""
    
    def setup_method(self):
        """设置测试环境"""
        self.mock_settings = Mock()
        self.mock_settings.SECRET_KEY = "test-secret-key"
        self.mock_db = Mock()
        self.mock_memory = Mock()
        
        # 模拟内存存储
        self.mock_memory.get = Mock(return_value=None)
        self.mock_memory.set = Mock()
        self.mock_memory.delete = Mock()
        
        self.perm_manager = PermissionManager(
            settings=self.mock_settings,
            db=self.mock_db,
            memory=self.mock_memory
        )
    
    def test_default_permissions(self):
        """测试默认权限"""
        # 检查默认权限是否存在
        user_read_perm = self.perm_manager.get_permission("user.read")
        assert user_read_perm is not None
        assert user_read_perm.resource == ResourceType.USER
        assert user_read_perm.action == Action.READ
        
        agent_create_perm = self.perm_manager.get_permission("agent.create")
        assert agent_create_perm is not None
        assert agent_create_perm.resource == ResourceType.AGENT
        assert agent_create_perm.action == Action.CREATE
    
    def test_default_roles(self):
        """测试默认角色"""
        # 检查默认角色
        user_role = self.perm_manager.role_manager.get_role("user")
        assert user_role is not None
        assert "agent.read" in user_role.permissions
        assert "message.create" in user_role.permissions
        
        admin_role = self.perm_manager.role_manager.get_role("admin")
        assert admin_role is not None
        assert "user.create" in admin_role.permissions
        assert "user.delete" in admin_role.permissions
    
    def test_permission_checking(self):
        """测试权限检查"""
        user_permissions = ["agent.read", "message.create", "channel.read"]
        
        # 检查存在的权限
        has_agent_read = self.perm_manager.check_permission(
            user_permissions, "agent.read"
        )
        assert has_agent_read == True
        
        # 检查不存在的权限
        has_user_delete = self.perm_manager.check_permission(
            user_permissions, "user.delete"
        )
        assert has_user_delete == False
        
        # 检查资源权限
        can_read_agents = self.perm_manager.check_resource_permission(
            user_permissions, ResourceType.AGENT, Action.READ
        )
        assert can_read_agents == True
        
        can_admin_agents = self.perm_manager.check_resource_permission(
            user_permissions, ResourceType.AGENT, Action.ADMIN
        )
        assert can_admin_agents == False


class TestRateLimiter:
    """测试限流器"""
    
    def setup_method(self):
        """设置测试环境"""
        self.mock_settings = Mock()
        self.rate_limiter = RateLimiter(self.mock_settings)
    
    def test_default_rules(self):
        """测试默认规则"""
        rules = self.rate_limiter.get_all_rules()
        assert len(rules) > 0
        
        # 检查全局API限制规则
        global_rule = None
        for rule in rules:
            if rule.id == "global_api_limit":
                global_rule = rule
                break
        
        assert global_rule is not None
        assert global_rule.strategy == RateLimitStrategy.SLIDING_WINDOW
        assert global_rule.scope == RateLimitScope.GLOBAL
        assert global_rule.limit == 1000
        assert global_rule.window == 3600
    
    @pytest.mark.asyncio
    async def test_rate_limit_check(self):
        """测试限流检查"""
        # 测试API端点
        result = await self.rate_limiter.check_rate_limit(
            endpoint="/api/test",
            user_id="testuser",
            ip_address="127.0.0.1"
        )
        
        assert "allowed" in result
        assert "rules_checked" in result
        assert "results" in result
        assert isinstance(result["results"], list)
    
    @pytest.mark.asyncio
    async def test_token_bucket_algorithm(self):
        """测试令牌桶算法"""
        from agentbus.security.rate_limiter import TokenBucketAlgorithm, MemoryRateLimitStore
        
        store = MemoryRateLimitStore()
        algorithm = TokenBucketAlgorithm(store)
        
        # 创建令牌桶规则
        rule = RateLimitStrategy.TOKEN_BUCKET.value
        from agentbus.security.rate_limiter import RateLimitRule
        test_rule = RateLimitRule(
            id="test_bucket",
            name="测试令牌桶",
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            scope=RateLimitScope.USER,
            limit=10,
            window=60,
            burst=20,
            refill_rate=0.5
        )
        
        # 测试令牌桶限流
        key = "test_user"
        allowed = await algorithm.check_rate_limit(key, test_rule)
        assert isinstance(allowed, bool)


class TestEncryption:
    """测试加密系统"""
    
    def setup_method(self):
        """设置测试环境"""
        self.mock_settings = Mock()
        self.mock_db = Mock()
        self.mock_memory = Mock()
        
        # 模拟内存存储
        self.mock_memory.get = Mock(return_value=None)
        self.mock_memory.set = Mock()
        self.mock_memory.delete = Mock()
        
        self.encryption_manager = EncryptionManager(
            settings=self.mock_settings,
            db=self.mock_db,
            memory=self.mock_memory
        )
    
    @pytest.mark.asyncio
    async def test_symmetric_encryption(self):
        """测试对称加密"""
        test_data = "这是测试数据"
        
        # 加密数据
        secure_data = await self.encryption_manager.encrypt_data(test_data)
        
        assert secure_data is not None
        assert secure_data.encrypted_data != test_data.encode()
        assert secure_data.key_id is not None
        assert secure_data.encryption_algorithm is not None
        
        # 解密数据
        decrypted_data = await self.encryption_manager.decrypt_data(secure_data)
        decrypted_text = decrypted_data.decode('utf-8')
        
        assert decrypted_text == test_data
    
    @pytest.mark.asyncio
    async def test_password_encryption(self):
        """测试密码加密"""
        test_data = "需要密码保护的敏感数据"
        password = "my-secret-password"
        
        # 密码加密
        encrypted_data = await self.encryption_manager.encrypt_with_password(
            test_data, password
        )
        
        assert encrypted_data != test_data.encode()
        assert len(encrypted_data) > len(test_data.encode())
        
        # 密码解密
        decrypted_data = await self.encryption_manager.decrypt_with_password(
            encrypted_data, password
        )
        decrypted_text = decrypted_data.decode('utf-8')
        
        assert decrypted_text == test_data
        
        # 错误密码解密应该失败
        try:
            wrong_decrypted = await self.encryption_manager.decrypt_with_password(
                encrypted_data, "wrong-password"
            )
            assert False, "应该抛出异常"
        except Exception:
            pass  # 期望的异常
    
    def test_crypto_utils(self):
        """测试加密工具"""
        # 测试随机字节生成
        random_bytes = CryptoUtils.generate_random_bytes(32)
        assert len(random_bytes) == 32
        assert isinstance(random_bytes, bytes)
        
        # 测试安全令牌生成
        token = CryptoUtils.generate_token(32)
        assert len(token) > 0
        assert isinstance(token, str)
        
        # 测试哈希计算
        test_data = b"test data"
        hash_result = CryptoUtils.compute_hash(test_data)
        assert len(hash_result) == 32  # SHA256
        assert isinstance(hash_result, bytes)
        
        # 测试Base64编码/解码
        original_data = b"hello world"
        encoded = CryptoUtils.base64_encode(original_data)
        decoded = CryptoUtils.base64_decode(encoded)
        assert decoded == original_data


class TestSecurityIntegration:
    """测试安全系统集成"""
    
    def setup_method(self):
        """设置测试环境"""
        self.mock_settings = Mock()
        self.mock_settings.SECRET_KEY = "integration-test-key"
        self.mock_db = Mock()
        self.mock_memory = Mock()
        
        # 模拟内存存储
        self.mock_memory.get = Mock(return_value=None)
        self.mock_memory.set = Mock()
        self.mock_memory.delete = Mock()
        
        # 初始化各个组件
        self.auth_manager = AuthenticationManager(
            settings=self.mock_settings,
            db=self.mock_db,
            memory=self.mock_memory
        )
        self.perm_manager = PermissionManager(
            settings=self.mock_settings,
            db=self.mock_db,
            memory=self.mock_memory
        )
        self.rate_limiter = RateLimiter(self.mock_settings)
        self.encryption_manager = EncryptionManager(
            settings=self.mock_settings,
            db=self.mock_db,
            memory=self.mock_memory
        )
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """测试完整工作流程"""
        # 1. 用户注册
        user = await self.auth_manager.register_user(
            username="integrationuser",
            email="integration@example.com",
            password="IntegrationTest123"
        )
        assert user is not None
        
        # 2. 用户认证
        user_data = user.to_dict()
        user_data['hashed_password'] = user.hashed_password
        self.mock_memory.get.return_value = user_data
        
        token = await self.auth_manager.authenticate_user(
            email="integration@example.com",
            password="IntegrationTest123"
        )
        assert token is not None
        
        # 3. 权限检查
        # 模拟用户角色分配
        user_role = self.perm_manager.role_manager.get_role("user")
        assert user_role is not None
        
        user_permissions = user_role.permissions
        assert "agent.read" in user_permissions
        
        can_read_agent = self.perm_manager.check_permission(
            user_permissions, "agent.read"
        )
        assert can_read_agent == True
        
        # 4. 限流检查
        rate_limit_result = await self.rate_limiter.check_rate_limit(
            endpoint="/api/agents",
            user_id=user.id
        )
        assert "allowed" in rate_limit_result
        
        # 5. 数据加密
        sensitive_data = "用户敏感信息"
        secure_data = await self.encryption_manager.encrypt_data(sensitive_data)
        assert secure_data is not None
        
        decrypted_data = await self.encryption_manager.decrypt_data(secure_data)
        decrypted_text = decrypted_data.decode('utf-8')
        assert decrypted_text == sensitive_data
        
        print("✓ 完整安全流程测试通过")


def run_tests():
    """运行所有测试"""
    print("AgentBus 安全系统测试")
    print("=" * 50)
    
    # 模拟pytest的异步测试运行
    test_classes = [
        TestAuthentication,
        TestPermissions,
        TestRateLimiter,
        TestEncryption,
        TestSecurityIntegration
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        instance = test_class()
        instance.setup_method()
        
        # 获取测试方法
        test_methods = [method for method in dir(instance) 
                        if method.startswith('test_') and callable(getattr(instance, method))]
        
        for method_name in test_methods:
            total_tests += 1
            method = getattr(instance, method_name)
            
            try:
                # 运行同步测试
                if asyncio.iscoroutinefunction(method):
                    asyncio.run(method())
                else:
                    method()
                
                print(f"  ✓ {method_name}")
                passed_tests += 1
                
            except Exception as e:
                print(f"  ✗ {method_name}: {e}")
    
    print(f"\n测试结果:")
    print(f"总测试数: {total_tests}")
    print(f"通过: {passed_tests}")
    print(f"失败: {total_tests - passed_tests}")
    print(f"成功率: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} 个测试失败")


if __name__ == "__main__":
    run_tests()