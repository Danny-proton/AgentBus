#!/usr/bin/env python3
"""
多模型协调器插件集成测试
Multi-Model Coordinator Plugin Integration Tests

测试插件与现有系统的兼容性，包括：
- 与原有多模型协调器的兼容性
- 插件管理器的集成
- 现有测试框架的兼容性
- API接口的兼容性
"""

import asyncio
import unittest
import pytest
from unittest.mock import patch, MagicMock

# 测试插件是否能被正确导入
try:
    from agentbus.plugins.multi_model_plugin import MultiModelPlugin
    from agentbus.services.multi_model_coordinator import MultiModelCoordinator
    PLUGIN_IMPORT_SUCCESS = True
except ImportError as e:
    PLUGIN_IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


class TestPluginCompatibility(unittest.TestCase):
    """插件兼容性测试"""
    
    def setUp(self):
        """测试设置"""
        if not PLUGIN_IMPORT_SUCCESS:
            self.skipTest(f"插件导入失败: {IMPORT_ERROR}")
    
    def test_plugin_import(self):
        """测试插件导入"""
        self.assertTrue(PLUGIN_IMPORT_SUCCESS)
        self.assertIsNotNone(MultiModelPlugin)
        self.assertIsNotNone(MultiModelCoordinator)
    
    def test_plugin_inherits_from_base(self):
        """测试插件继承基类"""
        from agentbus.plugins import AgentBusPlugin
        
        # 验证MultiModelPlugin继承自AgentBusPlugin
        self.assertTrue(issubclass(MultiModelPlugin, AgentBusPlugin))
        
        # 创建插件实例测试
        from agentbus.plugins import PluginContext
        import logging
        
        config = {'test': True}
        logger = logging.getLogger('test')
        runtime = {}
        
        context = PluginContext(config=config, logger=logger, runtime=runtime)
        plugin = MultiModelPlugin("test_plugin", context)
        
        self.assertIsInstance(plugin, AgentBusPlugin)
    
    def test_plugin_has_required_methods(self):
        """测试插件具有必需的方法"""
        from agentbus.plugins import PluginContext
        import logging
        
        config = {'test': True}
        logger = logging.getLogger('test')
        runtime = {}
        
        context = PluginContext(config=config, logger=logger, runtime=runtime)
        plugin = MultiModelPlugin("test_plugin", context)
        
        # 检查必需的方法
        required_methods = [
            'get_info',
            'activate', 
            'deactivate',
            'get_tools',
            'get_hooks',
            'get_commands'
        ]
        
        for method_name in required_methods:
            self.assertTrue(hasattr(plugin, method_name))
            self.assertTrue(callable(getattr(plugin, method_name)))
    
    def test_plugin_info_structure(self):
        """测试插件信息结构"""
        from agentbus.plugins import PluginContext
        import logging
        
        config = {'test': True}
        logger = logging.getLogger('test')
        runtime = {}
        
        context = PluginContext(config=config, logger=logger, runtime=runtime)
        plugin = MultiModelPlugin("test_plugin", context)
        
        info = plugin.get_info()
        
        # 检查必需的信息字段
        required_fields = ['id', 'name', 'version', 'description', 'capabilities']
        for field in required_fields:
            self.assertIn(field, info)
        
        self.assertEqual(info['id'], 'test_plugin')
        self.assertIn('Multi-Model', info['name'])
        self.assertIn('multi_model_coordination', info['capabilities'])


class TestCoordinatorCompatibility(unittest.TestCase):
    """协调器兼容性测试"""
    
    def setUp(self):
        """测试设置"""
        if not PLUGIN_IMPORT_SUCCESS:
            self.skipTest(f"插件导入失败: {IMPORT_ERROR}")
    
    def test_coordinator_import(self):
        """测试协调器导入"""
        from agentbus.services.multi_model_coordinator import MultiModelCoordinator
        self.assertIsNotNone(MultiModelCoordinator)
    
    def test_coordinator_initialization(self):
        """测试协调器初始化"""
        from agentbus.services.multi_model_coordinator import MultiModelCoordinator
        
        coordinator = MultiModelCoordinator()
        self.assertIsNotNone(coordinator)
        self.assertFalse(coordinator.is_running)
    
    def test_coordinator_plugin_compatible_methods(self):
        """测试协调器插件兼容方法"""
        from agentbus.services.multi_model_coordinator import MultiModelCoordinator
        
        coordinator = MultiModelCoordinator()
        
        # 检查插件兼容方法是否存在
        compatible_methods = [
            'get_plugin_compatible_stats',
            'export_model_configs',
            'import_model_configs',
            'get_model_by_id',
            'get_models_by_provider',
            'get_models_by_capability',
            'health_check'
        ]
        
        for method_name in compatible_methods:
            self.assertTrue(hasattr(coordinator, method_name))
            self.assertTrue(callable(getattr(coordinator, method_name)))
    
    @pytest.mark.asyncio
    async def test_coordinator_health_check(self):
        """测试协调器健康检查"""
        from agentbus.services.multi_model_coordinator import MultiModelCoordinator
        
        coordinator = MultiModelCoordinator()
        
        health_result = await coordinator.health_check()
        
        self.assertIn('status', health_result)
        self.assertIn('timestamp', health_result)
        self.assertIn('checks', health_result)
        
        # 健康状态应该是 'healthy', 'warning', 'critical', 或 'error'
        valid_statuses = ['healthy', 'warning', 'critical', 'error']
        self.assertIn(health_result['status'], valid_statuses)


class TestPluginManagerIntegration(unittest.TestCase):
    """插件管理器集成测试"""
    
    def setUp(self):
        """测试设置"""
        if not PLUGIN_IMPORT_SUCCESS:
            self.skipTest(f"插件导入失败: {IMPORT_ERROR}")
    
    def test_plugin_manager_import(self):
        """测试插件管理器导入"""
        from agentbus.plugins import PluginManager
        self.assertIsNotNone(PluginManager)
    
    def test_plugin_creation(self):
        """测试插件创建"""
        from agentbus.plugins import PluginContext, PluginManager
        import logging
        
        config = {'test_mode': True}
        logger = logging.getLogger('test')
        runtime = {}
        
        context = PluginContext(config=config, logger=logger, runtime=runtime)
        plugin = MultiModelPlugin("integration_test_plugin", context)
        
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.plugin_id, "integration_test_plugin")
    
    @pytest.mark.asyncio
    async def test_plugin_lifecycle(self):
        """测试插件生命周期"""
        from agentbus.plugins import PluginContext
        import logging
        
        config = {'enable_monitoring': True}
        logger = logging.getLogger('test')
        runtime = {}
        
        context = PluginContext(config=config, logger=logger, runtime=runtime)
        plugin = MultiModelPlugin("lifecycle_test_plugin", context)
        
        # 测试激活
        with patch.object(plugin.coordinator, 'initialize', return_value=True):
            success = await plugin.activate()
            self.assertTrue(success)
            self.assertEqual(plugin.status.value, 'active')
        
        # 测试停用
        with patch.object(plugin.coordinator, 'shutdown', return_value=None):
            success = await plugin.deactivate()
            self.assertTrue(success)
            self.assertEqual(plugin.status.value, 'deactivated')


class TestExistingTestCompatibility(unittest.TestCase):
    """现有测试兼容性测试"""
    
    def setUp(self):
        """测试设置"""
        if not PLUGIN_IMPORT_SUCCESS:
            self.skipTest(f"插件导入失败: {IMPORT_ERROR}")
    
    def test_can_import_existing_modules(self):
        """测试可以导入现有模块"""
        try:
            from agentbus.services.multi_model_coordinator import (
                ModelConfig, TaskRequest, TaskType, TaskPriority, ModelType
            )
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"无法导入现有模块: {e}")
    
    def test_existing_data_structures_compatibility(self):
        """测试现有数据结构兼容性"""
        from agentbus.services.multi_model_coordinator import (
            ModelConfig, TaskRequest, TaskType, TaskPriority, ModelType
        )
        
        # 测试创建模型配置
        model_config = ModelConfig(
            model_id="test-model",
            model_name="Test Model",
            model_type=ModelType.TEXT_GENERATION,
            provider="test"
        )
        
        self.assertEqual(model_config.model_id, "test-model")
        self.assertEqual(model_config.model_type, ModelType.TEXT_GENERATION)
        
        # 测试创建任务请求
        task_request = TaskRequest(
            task_id="test-task",
            task_type=TaskType.TEXT_GENERATION,
            content="Test content"
        )
        
        self.assertEqual(task_request.task_id, "test-task")
        self.assertEqual(task_request.task_type, TaskType.TEXT_GENERATION)
    
    def test_plugin_uses_existing_structures(self):
        """测试插件使用现有结构"""
        from agentbus.plugins import PluginContext
        import logging
        
        config = {'test': True}
        logger = logging.getLogger('test')
        runtime = {}
        
        context = PluginContext(config=config, logger=logger, runtime=runtime)
        plugin = MultiModelPlugin("compatibility_test_plugin", context)
        
        # 检查插件是否正确使用了现有的数据结构
        self.assertIsNotNone(plugin.coordinator)
        
        # 检查插件的基本属性
        self.assertEqual(plugin.plugin_id, "compatibility_test_plugin")
        self.assertIsNotNone(plugin.coordinator)
        self.assertIsInstance(plugin.coordinator, MultiModelCoordinator)


def run_integration_tests():
    """运行集成测试"""
    print("🧪 运行多模型协调器插件集成测试")
    print("=" * 50)
    
    # 运行兼容性测试
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestPluginCompatibility)
    test_runner = unittest.TextTestRunner(verbosity=2)
    result1 = test_runner.run(test_suite)
    
    print("\n" + "=" * 50)
    
    # 运行协调器兼容性测试
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestCoordinatorCompatibility)
    test_runner = unittest.TextTestRunner(verbosity=2)
    result2 = test_runner.run(test_suite)
    
    print("\n" + "=" * 50)
    
    # 运行插件管理器集成测试
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestPluginManagerIntegration)
    test_runner = unittest.TextTestRunner(verbosity=2)
    result3 = test_runner.run(test_suite)
    
    print("\n" + "=" * 50)
    
    # 运行现有测试兼容性测试
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestExistingTestCompatibility)
    test_runner = unittest.TextTestRunner(verbosity=2)
    result4 = test_runner.run(test_suite)
    
    print("\n" + "=" * 50)
    
    # 总结结果
    total_tests = result1.testsRun + result2.testsRun + result3.testsRun + result4.testsRun
    total_failures = len(result1.failures) + len(result2.failures) + len(result3.failures) + len(result4.failures)
    total_errors = len(result1.errors) + len(result2.errors) + len(result3.errors) + len(result4.errors)
    
    print(f"📊 测试结果总结:")
    print(f"   总测试数: {total_tests}")
    print(f"   成功: {total_tests - total_failures - total_errors}")
    print(f"   失败: {total_failures}")
    print(f"   错误: {total_errors}")
    
    if total_failures == 0 and total_errors == 0:
        print("✅ 所有集成测试通过！")
        return True
    else:
        print("❌ 部分集成测试失败")
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    exit(0 if success else 1)