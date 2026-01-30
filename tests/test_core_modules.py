"""
核心基础设施模块测试
Core Infrastructure Module Tests
"""

import pytest
import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# 导入要测试的模块
from py_moltbot.core.session import (
    SessionManager, SessionContext, SessionType, SessionStatus,
    MemorySessionStore, get_session_manager, session_context
)
from py_moltbot.core.security import (
    SecurityManager, User, Permission, SecurityToken,
    EncryptionService, JWTService, AuthenticationService
)
from py_moltbot.core.gateway import (
    GatewayServer, GatewayMessage, MessagePriority, ConnectionState
)
from py_moltbot.core.routing import (
    MessageRouter, MessageBus, RoutingRule, RouteTarget, RoutedMessage,
    RoutingStrategy, MessageRoute
)
from py_moltbot.core.app import CoreApplication
from py_moltbot.adapters.base import Message, MessageType, AdapterType


class TestSessionManager:
    """会话管理器测试"""
    
    @pytest.fixture
    def session_manager(self):
        """创建会话管理器"""
        store = MemorySessionStore()
        return SessionManager(store)
    
    @pytest.fixture
    def sample_session_context(self):
        """创建示例会话上下文"""
        return SessionContext(
            session_id="test_session_123",
            chat_id="test_chat_456",
            platform=AdapterType.WEB,
            user_id="test_user_789",
            session_type=SessionType.PRIVATE
        )
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self, session_manager):
        """测试会话生命周期"""
        # 启动管理器
        await session_manager.start()
        assert session_manager._cleanup_task is not None
        
        # 创建会话
        context = await session_manager.create_session(
            chat_id="test_chat",
            user_id="test_user", 
            platform=AdapterType.WEB
        )
        
        assert context.session_id is not None
        assert context.user_id == "test_user"
        assert context.chat_id == "test_chat"
        assert context.platform == AdapterType.WEB
        assert context.session_type == SessionType.PRIVATE
        
        # 获取会话
        retrieved = await session_manager.get_session(context.session_id)
        assert retrieved is not None
        assert retrieved.session_id == context.session_id
        
        # 更新会话
        context.set_data("test_key", "test_value")
        await session_manager.update_session(context)
        
        updated = await session_manager.get_session(context.session_id)
        assert updated.get_data("test_key") == "test_value"
        
        # 删除会话
        await session_manager.delete_session(context.session_id)
        deleted = await session_manager.get_session(context.session_id)
        assert deleted is None
        
        # 停止管理器
        await session_manager.stop()
    
    @pytest.mark.asyncio
    async def test_user_sessions(self, session_manager):
        """测试用户会话管理"""
        await session_manager.start()
        
        # 创建多个会话
        session1 = await session_manager.create_session(
            chat_id="chat1", user_id="user1", platform=AdapterType.WEB
        )
        session2 = await session_manager.create_session(
            chat_id="chat2", user_id="user1", platform=AdapterType.WEB
        )
        session3 = await session_manager.create_session(
            chat_id="chat3", user_id="user2", platform=AdapterType.WEB
        )
        
        # 获取用户会话
        user1_sessions = await session_manager.get_user_sessions("user1")
        assert len(user1_sessions) == 2
        
        # 获取特定聊天会话
        user_chat_session = await session_manager.get_user_session(
            "user1", "chat1", AdapterType.WEB
        )
        assert user_chat_session is not None
        assert user_chat_session.chat_id == "chat1"
        
        # 关闭用户所有会话
        closed_count = await session_manager.close_user_sessions("user1")
        assert closed_count == 2
        
        user1_sessions_after = await session_manager.get_user_sessions("user1")
        assert len(user1_sessions_after) == 0
        
        await session_manager.stop()
    
    @pytest.mark.asyncio
    async def test_session_context_manager(self, session_manager):
        """测试会话上下文管理器"""
        await session_manager.start()
        
        # 使用上下文管理器
        async with session_context(
            session_manager, "test_chat", "test_user", AdapterType.WEB
        ) as context:
            assert context.session_id is not None
            assert context.user_id == "test_user"
            assert context.chat_id == "test_chat"
            
            # 在上下文中设置数据
            context.set_data("test_data", "test_value")
        
        # 检查数据是否被保存
        user_session = await session_manager.get_user_session(
            "test_user", "test_chat", AdapterType.WEB
        )
        assert user_session is not None
        assert user_session.get_data("test_data") == "test_value"
        
        await session_manager.stop()
    
    def test_session_stats(self, session_manager):
        """测试会话统计"""
        # 创建模拟数据
        session_manager.store.sessions["session1"] = SessionContext(
            session_id="session1", chat_id="chat1", platform=AdapterType.WEB,
            user_id="user1", session_type=SessionType.PRIVATE
        )
        session_manager.store.sessions["session2"] = SessionContext(
            session_id="session2", chat_id="chat2", platform=AdapterType.WEB,
            user_id="user2", session_type=SessionType.PRIVATE
        )
        
        stats = session_manager.get_session_stats()
        
        assert stats["total_sessions"] == 2
        assert stats["user_count"] == 2
        assert stats["chat_count"] == 2
        assert stats["platform_stats"]["web"] == 2


class TestSecurityManager:
    """安全管理器测试"""
    
    @pytest.fixture
    def security_manager(self):
        """创建安全管理器"""
        return SecurityManager()
    
    @pytest.fixture
    def test_user_data(self):
        """创建测试用户数据"""
        return {
            "username": "testuser",
            "password": "testpass123",
            "email": "test@example.com"
        }
    
    @pytest.mark.asyncio
    async def test_user_registration(self, security_manager, test_user_data):
        """测试用户注册"""
        # 注册用户
        user = await security_manager.auth.register_user(**test_user_data)
        
        assert user.id is not None
        assert user.username == test_user_data["username"]
        assert user.email == test_user_data["email"]
        assert user.hashed_password is not None
        assert user.hashed_password != test_user_data["password"]  # 应该被哈希
    
    @pytest.mark.asyncio
    async def test_user_authentication(self, security_manager, test_user_data):
        """测试用户认证"""
        # 注册用户
        await security_manager.auth.register_user(**test_user_data)
        
        # 正确密码认证
        authenticated_user = await security_manager.auth.authenticate_user(
            test_user_data["username"], 
            test_user_data["password"]
        )
        assert authenticated_user is not None
        assert authenticated_user.username == test_user_data["username"]
        
        # 错误密码认证
        wrong_user = await security_manager.auth.authenticate_user(
            test_user_data["username"], 
            "wrongpassword"
        )
        assert wrong_user is None
    
    @pytest.mark.asyncio
    async def test_token_management(self, security_manager, test_user_data):
        """测试令牌管理"""
        # 注册用户
        user = await security_manager.auth.register_user(**test_user_data)
        
        # 创建访问令牌
        token = await security_manager.auth.create_access_token(user)
        assert token is not None
        
        # 验证令牌
        security_token = await security_manager.auth.verify_token(token)
        assert security_token is not None
        assert security_token.user_id == user.id
        
        # 撤销令牌
        revoked = await security_manager.auth.revoke_token(token)
        assert revoked is True
        
        # 验证撤销后的令牌
        revoked_token = await security_manager.auth.verify_token(token)
        assert revoked_token is None
    
    @pytest.mark.asyncio
    async def test_permission_system(self, security_manager, test_user_data):
        """测试权限系统"""
        # 注册用户
        user = await security_manager.auth.register_user(
            username=test_user_data["username"],
            password=test_user_data["password"],
            permissions=[Permission.READ, Permission.WRITE]
        )
        
        # 检查权限
        has_read = await security_manager.authorization.check_permission(
            user.id, Permission.READ
        )
        assert has_read is True
        
        has_admin = await security_manager.authorization.check_permission(
            user.id, Permission.ADMIN
        )
        assert has_admin is False
        
        # 更新权限
        updated = await security_manager.auth.update_user_permissions(
            user.id, [Permission.READ, Permission.WRITE, Permission.ADMIN]
        )
        assert updated is True
        
        # 重新检查权限
        has_admin_after = await security_manager.authorization.check_permission(
            user.id, Permission.ADMIN
        )
        assert has_admin_after is True
    
    def test_encryption_service(self):
        """测试加密服务"""
        encryption = EncryptionService()
        
        # 测试加密/解密
        original_data = "test sensitive data"
        encrypted = encryption.encrypt(original_data)
        decrypted = encryption.decrypt(encrypted)
        
        assert encrypted != original_data
        assert decrypted == original_data
        
        # 测试密码哈希
        password = "secure_password_123"
        hashed = encryption.hash_password(password)
        assert hashed != password
        
        # 验证密码
        assert encryption.verify_password(password, hashed) is True
        assert encryption.verify_password("wrong_password", hashed) is False
    
    def test_jwt_service(self):
        """测试JWT服务"""
        jwt_service = JWTService()
        
        # 创建令牌
        token = jwt_service.create_token(
            user_id="test_user",
            permissions=["read", "write"],
            expires_in_hours=1
        )
        assert token is not None
        
        # 验证令牌
        payload = jwt_service.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == "test_user"
        assert payload["permissions"] == ["read", "write"]
    
    @pytest.mark.asyncio
    async def test_secure_context(self, security_manager, test_user_data):
        """测试安全上下文"""
        # 注册用户
        user = await security_manager.auth.register_user(**test_user_data)
        
        # 使用安全上下文
        async with security_manager.secure_context(user.id) as context:
            assert context["user"].id == user.id
            assert "token" in context
            assert "auth_service" in context
            assert "authz_service" in context


class TestGatewayServer:
    """网关服务器测试"""
    
    @pytest.fixture
    def gateway_server(self):
        """创建网关服务器"""
        return GatewayServer()
    
    def test_gateway_message_creation(self):
        """测试网关消息创建"""
        message = GatewayMessage.create("test_type", {"data": "test"})
        
        assert message.id is not None
        assert message.type == "test_type"
        assert message.data == {"data": "test"}
        assert message.priority == MessagePriority.NORMAL
    
    def test_connection_stats(self, gateway_server):
        """测试连接统计"""
        stats = gateway_server.get_connection_stats()
        
        assert "total_connections" in stats
        assert "authenticated_connections" in stats
        assert "state_stats" in stats
        assert "subscription_stats" in stats
        assert "uptime" in stats
    
    @pytest.mark.asyncio
    async def test_message_routing(self, gateway_server):
        """测试消息路由"""
        # 创建测试路由
        route = RoutingRule(
            id="test_route",
            name="Test Route",
            conditions={"message_type": "text"},
            targets=["test_target"],
            priority=10
        )
        
        gateway_server.router.add_rule(route)
        
        # 添加测试目标
        target = RouteTarget(
            id="test_target",
            type="adapter",
            name="Test Adapter",
            weight=1,
            capacity=100
        )
        
        gateway_server.router.add_target(target)
        
        # 注册消息处理器
        handler_called = False
        
        async def test_handler(message, connection):
            nonlocal handler_called
            handler_called = True
        
        gateway_server.router.register_message_handler("test_type", test_handler)
        
        # 创建测试消息
        test_message = GatewayMessage.create(
            "test_type",
            {"content": "test message"}
        )
        
        # 模拟连接
        mock_connection = Mock()
        mock_connection.is_authenticated.return_value = True
        mock_connection.subscriptions = set()
        
        # 路由消息
        await gateway_server.router.route_message(test_message, mock_connection)
        
        # 验证处理器被调用
        assert handler_called is True
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, gateway_server):
        """测试广播消息"""
        # 创建模拟连接
        mock_connections = []
        for i in range(3):
            connection = Mock()
            connection.is_authenticated.return_value = True
            connection.id = f"connection_{i}"
            mock_connections.append(connection)
            gateway_server.connections[connection.id] = connection
        
        # 模拟消息发送
        for connection in mock_connections:
            connection.websocket = Mock()
            connection.websocket.send = AsyncMock()
        
        # 广播消息
        data = {"event": "test", "message": "broadcast test"}
        sent_count = await gateway_server.broadcast_message(data)
        
        # 验证广播结果
        assert sent_count == 3
        for connection in mock_connections:
            connection.websocket.send.assert_called_once()


class TestMessageRouter:
    """消息路由器测试"""
    
    @pytest.fixture
    def message_router(self):
        """创建消息路由器"""
        return MessageRouter()
    
    @pytest.fixture
    def sample_message(self):
        """创建示例消息"""
        return Message(
            id="test_msg_123",
            platform=AdapterType.WEB,
            chat_id="test_chat_456",
            user_id="test_user_789",
            content="Hello World",
            message_type=MessageType.TEXT
        )
    
    def test_routing_rule_matching(self, message_router, sample_message):
        """测试路由规则匹配"""
        # 创建匹配规则
        rule = RoutingRule(
            id="match_text",
            name="Match Text Messages",
            conditions={
                "message_type": "text",
                "platform": "web"
            },
            targets=["text_handler"],
            priority=5
        )
        
        message_router.add_rule(rule)
        
        # 测试匹配
        matches = message_router._find_matching_rules(sample_message, None)
        assert len(matches) == 1
        assert matches[0].id == "match_text"
    
    def test_target_management(self, message_router):
        """测试目标管理"""
        # 添加目标
        target = RouteTarget(
            id="test_adapter",
            type="adapter",
            name="Test Adapter",
            weight=2,
            capacity=50
        )
        
        message_router.add_target(target)
        
        # 验证目标存在
        retrieved = message_router._get_target_by_name("Test Adapter")
        assert retrieved is not None
        assert retrieved.id == "test_adapter"
        
        # 测试负载管理
        assert retrieved.can_handle() is True
        retrieved.increment_load()
        assert retrieved.current_load == 1
        retrieved.decrement_load()
        assert retrieved.current_load == 0
    
    @pytest.mark.asyncio
    async def test_message_routing(self, message_router, sample_message):
        """测试消息路由"""
        # 添加规则
        rule = RoutingRule(
            id="route_to_adapter",
            name="Route to Adapter",
            conditions={"platform": "web"},
            targets=["test_adapter"],
            strategy=RoutingStrategy.ROUND_ROBIN
        )
        
        message_router.add_rule(rule)
        
        # 添加目标
        target = RouteTarget(
            id="test_adapter",
            type="adapter",
            name="Test Adapter",
            capacity=10
        )
        
        message_router.add_target(target)
        
        # 路由消息
        routed_messages = await message_router.route_message(sample_message, None)
        
        # 验证路由结果
        assert len(routed_messages) == 1
        assert routed_messages[0].target.id == "test_adapter"
        assert routed_messages[0].route_id == "route_to_adapter"
    
    def test_routing_statistics(self, message_router):
        """测试路由统计"""
        # 添加一些模拟数据
        message_router.stats["messages_routed"] = 10
        message_router.stats["messages_failed"] = 2
        message_router.stats["rules_matched"] = 5
        message_router.stats["targets_used"]["target1"] = 3
        
        stats = message_router.get_routing_stats()
        
        assert stats["total_rules"] == 0  # 没有添加规则
        assert stats["message_stats"]["messages_routed"] == 10
        assert stats["message_stats"]["messages_failed"] == 2


class TestMessageBus:
    """消息总线测试"""
    
    @pytest.fixture
    def message_bus(self):
        """创建消息总线"""
        return MessageBus()
    
    @pytest.mark.asyncio
    async def test_message_bus_lifecycle(self, message_bus):
        """测试消息总线生命周期"""
        # 启动总线
        await message_bus.start()
        assert message_bus.running is True
        assert len(message_bus._tasks) == 3  # 3个处理任务
        
        # 停止总线
        await message_bus.stop()
        assert message_bus.running is False
    
    @pytest.mark.asyncio
    async def test_message_sending(self, message_bus):
        """测试消息发送"""
        await message_bus.start()
        
        # 创建测试消息
        test_message = Message(
            id="test_msg",
            platform=AdapterType.WEB,
            chat_id="test_chat",
            user_id="test_user",
            content="test content",
            message_type=MessageType.TEXT
        )
        
        # 发送消息
        await message_bus.send_message(test_message)
        
        # 等待处理
        await asyncio.sleep(0.1)
        
        # 接收消息
        routed_msg = await message_bus.receive_message()
        
        # 验证
        assert routed_msg is not None
        assert routed_msg.original_message.id == "test_msg"
        
        await message_bus.stop()
    
    @pytest.mark.asyncio
    async def test_message_processors(self, message_bus):
        """测试消息处理器"""
        await message_bus.start()
        
        processor_called = False
        
        def test_processor(message, context):
            nonlocal processor_called
            processor_called = True
        
        # 添加处理器
        message_bus.add_processor(test_processor)
        
        # 发送消息
        test_message = Message(
            id="test_msg",
            platform=AdapterType.WEB,
            chat_id="test_chat",
            user_id="test_user",
            content="test",
            message_type=MessageType.TEXT
        )
        
        await message_bus.send_message(test_message)
        
        # 等待处理
        await asyncio.sleep(0.1)
        
        # 验证处理器被调用
        assert processor_called is True
        
        await message_bus.stop()


class TestCoreApplication:
    """核心应用程序测试"""
    
    @pytest.fixture
    def core_app(self):
        """创建核心应用程序"""
        return CoreApplication()
    
    @pytest.mark.asyncio
    async def test_application_initialization(self, core_app):
        """测试应用程序初始化"""
        with patch('py_moltbot.core.app.SessionManager') as mock_session, \
             patch('py_moltbot.core.app.SecurityManager') as mock_security, \
             patch('py_moltbot.core.app.MessageBus') as mock_bus, \
             patch('py_moltbot.core.app.GatewayServer') as mock_gateway:
            
            # 设置模拟返回值
            mock_session_instance = AsyncMock()
            mock_session.return_value = mock_session_instance
            
            mock_security_instance = Mock()
            mock_security.return_value = mock_security_instance
            
            mock_bus_instance = AsyncMock()
            mock_bus.return_value = mock_bus_instance
            
            mock_gateway_instance = AsyncMock()
            mock_gateway.return_value = mock_gateway_instance
            
            # 初始化应用
            await core_app.initialize()
            
            # 验证组件被创建
            assert core_app.session_manager is not None
            assert core_app.security_manager is not None
            assert core_app.message_bus is not None
            assert core_app.gateway_server is not None
            
            # 验证方法被调用
            mock_session_instance.start.assert_called_once()
            mock_bus_instance.start.assert_called_once()
            mock_gateway_instance.start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_application_status(self, core_app):
        """测试应用程序状态获取"""
        with patch('py_moltbot.core.app.SessionManager') as mock_session, \
             patch('py_moltbot.core.app.SecurityManager') as mock_security, \
             patch('py_moltbot.core.app.MessageBus') as mock_bus, \
             patch('py_moltbot.core.app.GatewayServer') as mock_gateway:
            
            # 设置模拟实例
            mock_session_instance = Mock()
            mock_session_instance.get_session_stats.return_value = {"total_sessions": 5}
            mock_session.return_value = mock_session_instance
            
            mock_security_instance = Mock()
            mock_security.return_value = mock_security_instance
            
            mock_bus_instance = Mock()
            mock_bus_instance.incoming_queue.qsize.return_value = 2
            mock_bus.return_value = mock_bus_instance
            
            mock_gateway_instance = Mock()
            mock_gateway_instance.connections = {"conn1": Mock(), "conn2": Mock()}
            mock_gateway_instance.get_connection_stats.return_value = {"total_connections": 2}
            mock_gateway.return_value = mock_gateway_instance
            
            # 获取状态
            status = core_app.get_status()
            
            # 验证状态结构
            assert "running" in status
            assert "components" in status
            assert "session_manager" in status["components"]
            assert "message_bus" in status["components"]
            assert "gateway" in status["components"]
            assert "security" in status["components"]


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])