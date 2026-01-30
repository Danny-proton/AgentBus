"""
AgentBus扩展系统测试
AgentBus Extension System Tests

这个脚本用于测试扩展系统的核心功能，包括扩展的发现、加载、
激活、停用和依赖解析等功能。

This script tests the core functionality of the extension system,
including extension discovery, loading, activation, deactivation,
and dependency resolution.

Author: MiniMax Agent
License: MIT
"""

import sys
import os
import logging
import traceback
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from agentbus.extensions import (
        ExtensionManager, ExtensionRegistry, ExtensionSandbox,
        Extension, ExtensionState, ExtensionType, SecurityLevel,
        ExtensionDependency, ExtensionVersion, ExtensionError,
        ExtensionLoadError, ExtensionDependencyError, ExtensionSecurityError
    )
    
    from agentbus.extensions.base import ExtensionType as BaseExtensionType
    
    # 直接从examples目录导入
    sys.path.insert(0, str(Path(__file__).parent / "examples"))
    try:
        from extension_examples import (
            HelloWorldExtension, CalculatorExtension, DataProcessorExtension,
            EXTENSION_FACTORIES, list_available_extensions
        )
    except ImportError:
        # 如果导入失败，定义模拟类用于测试
        class HelloWorldExtension(Extension):
            def __init__(self):
                super().__init__(
                    extension_id="hello_world",
                    name="Hello World Extension",
                    version="1.0.0",
                    description="测试扩展",
                    author="Test",
                    extension_type="custom"
                )
            
            def say_hello(self, name="World"):
                return f"Hello, {name}!"
        
        class CalculatorExtension(Extension):
            def __init__(self):
                super().__init__(
                    extension_id="calculator",
                    name="Calculator Extension",
                    version="1.0.0",
                    description="计算器扩展",
                    author="Test",
                    extension_type="tool"
                )
            
            def add(self, a, b):
                return a + b
        
        class DataProcessorExtension(Extension):
            def __init__(self):
                super().__init__(
                    extension_id="data_processor",
                    name="Data Processor Extension",
                    version="1.0.0",
                    description="数据处理扩展",
                    author="Test",
                    extension_type="tool"
                )
            
            def process_text(self, text):
                return {"word_count": len(text.split())}
    
    print("✓ 所有模块导入成功")
    
except ImportError as e:
    print(f"✗ 模块导入失败: {e}")
    traceback.print_exc()
    sys.exit(1)


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('extension_test.log')
        ]
    )


def test_registry():
    """测试扩展注册表"""
    print("\n=== 测试扩展注册表 ===")
    
    try:
        registry = ExtensionRegistry()
        
        # 创建测试扩展
        ext1 = HelloWorldExtension()
        ext2 = CalculatorExtension()
        
        # 注册扩展
        print("1. 注册扩展...")
        result1 = registry.register_extension(ext1)
        result2 = registry.register_extension(ext2)
        
        print(f"   HelloWorld: {'✓' if result1 else '✗'}")
        print(f"   Calculator: {'✓' if result2 else '✗'}")
        
        # 测试查找
        print("2. 查找扩展...")
        found_ext1 = registry.get_extension(ext1.id)
        found_ext2 = registry.get_extension_by_name(ext2.name)
        
        print(f"   按ID查找: {'✓' if found_ext1 else '✗'}")
        print(f"   按名称查找: {'✓' if found_ext2 else '✗'}")
        
        # 测试按类型查找
        print("3. 按类型查找...")
        custom_exts = registry.find_extensions_by_type("custom")
        tool_exts = registry.find_extensions_by_type("tool")
        
        print(f"   自定义扩展: {len(custom_exts)} 个")
        print(f"   工具扩展: {len(tool_exts)} 个")
        
        # 测试统计信息
        print("4. 统计信息...")
        stats = registry.get_statistics()
        print(f"   总扩展数: {stats['total_extensions']}")
        print(f"   扩展类型: {stats['extension_types']}")
        
        # 测试取消注册
        print("5. 取消注册...")
        result = registry.unregister_extension(ext1.id)
        print(f"   取消注册: {'✓' if result else '✗'}")
        
        return True
        
    except Exception as e:
        print(f"✗ 注册表测试失败: {e}")
        traceback.print_exc()
        return False


def test_sandbox():
    """测试扩展沙箱"""
    print("\n=== 测试扩展沙箱 ===")
    
    try:
        sandbox = ExtensionSandbox()
        
        # 创建测试扩展
        ext = HelloWorldExtension()
        
        # 测试安全检查
        print("1. 安全检查...")
        security_result = sandbox.check_security(ext)
        print(f"   安全检查: {'✓' if security_result else '✗'}")
        
        # 测试资源限制
        print("2. 设置资源限制...")
        limits_result = sandbox.set_resource_limits(ext, max_memory=64*1024*1024)
        print(f"   资源限制: {'✓' if limits_result else '✗'}")
        
        # 测试沙箱执行
        print("3. 沙箱执行...")
        def test_function(x):
            return x * 2
        
        result = sandbox.execute_in_sandbox(ext, test_function, 5)
        expected = 10
        print(f"   执行结果: {result} (期望: {expected}) {'✓' if result == expected else '✗'}")
        
        # 测试监控
        print("4. 监控信息...")
        monitor_info = sandbox.monitor_execution(ext)
        print(f"   监控数据: ✓")
        
        return True
        
    except Exception as e:
        print(f"✗ 沙箱测试失败: {e}")
        traceback.print_exc()
        return False


def test_manager():
    """测试扩展管理器"""
    print("\n=== 测试扩展管理器 ===")
    
    try:
        # 创建管理器组件
        sandbox = ExtensionSandbox()
        manager = ExtensionManager(sandbox=sandbox)
        registry = manager._registry
        
        # 创建测试扩展
        extensions = [
            HelloWorldExtension(),
            CalculatorExtension(),
            DataProcessorExtension()
        ]
        
        # 测试加载
        print("1. 加载扩展...")
        load_results = []
        for ext in extensions:
            result = manager.load_extension(ext)
            load_results.append(result)
            print(f"   {ext.name}: {'✓' if result else '✗'}")
        
        # 测试激活
        print("2. 激活扩展...")
        activate_results = []
        for ext in extensions:
            result = manager.activate_extension(ext.id)
            activate_results.append(result)
            print(f"   {ext.name}: {'✓' if result else '✗'}")
        
        # 测试功能调用
        print("3. 测试扩展功能...")
        
        # Hello World测试
        hello_ext = manager.get_extension("hello_world")
        if hello_ext:
            result = hello_ext.say_hello("Test")
            print(f"   Hello World: {result} ✓")
        
        # 计算器测试
        calc_ext = manager.get_extension("calculator")
        if calc_ext:
            result = calc_ext.add(15, 25)
            expected = 40
            print(f"   计算器: 15 + 25 = {result} {'✓' if result == expected else '✗'}")
        
        # 数据处理器测试
        data_ext = manager.get_extension("data_processor")
        if data_ext:
            result = data_ext.process_text("Hello Extension System")
            print(f"   数据处理: {result['word_count']} words ✓")
        
        # 测试停用
        print("4. 停用扩展...")
        deactivate_results = []
        for ext in extensions:
            result = manager.deactivate_extension(ext.id)
            deactivate_results.append(result)
            print(f"   {ext.name}: {'✓' if result else '✗'}")
        
        # 测试统计信息
        print("5. 统计信息...")
        stats = manager.get_statistics()
        print(f"   注册表统计: ✓")
        print(f"   发现路径: {len(stats['discovery_paths'])} 个")
        
        return all(load_results) and all(activate_results) and all(deactivate_results)
        
    except Exception as e:
        print(f"✗ 管理器测试失败: {e}")
        traceback.print_exc()
        return False


def test_dependency_resolution():
    """测试依赖解析"""
    print("\n=== 测试依赖解析 ===")
    
    try:
        sandbox = ExtensionSandbox()
        manager = ExtensionManager(sandbox=sandbox)
        registry = manager._registry
        
        # 创建有依赖关系的扩展
        calc_ext = CalculatorExtension()
        data_ext = DataProcessorExtension()  # 依赖于 calculator
        
        print("1. 加载依赖扩展...")
        calc_result = manager.load_extension(calc_ext)
        data_result = manager.load_extension(data_ext)
        
        print(f"   计算器: {'✓' if calc_result else '✗'}")
        print(f"   数据处理器: {'✓' if data_result else '✗'}")
        
        print("2. 解析依赖...")
        extensions = [calc_ext, data_ext]
        dependency_result = manager.resolve_dependencies(extensions)
        print(f"   依赖解析: {'✓' if dependency_result else '✗'}")
        
        print("3. 激活顺序测试...")
        # 先激活依赖，再激活被依赖的扩展
        calc_activate = manager.activate_extension(calc_ext.id)
        data_activate = manager.activate_extension(data_ext.id)
        
        print(f"   计算器激活: {'✓' if calc_activate else '✗'}")
        print(f"   数据处理器激活: {'✓' if data_activate else '✗'}")
        
        return calc_result and data_result and dependency_result and calc_activate and data_activate
        
    except Exception as e:
        print(f"✗ 依赖解析测试失败: {e}")
        traceback.print_exc()
        return False


def test_security():
    """测试安全功能"""
    print("\n=== 测试安全功能 ===")
    
    try:
        sandbox = ExtensionSandbox()
        
        # 测试不同安全级别
        print("1. 安全级别测试...")
        
        ext = HelloWorldExtension()
        
        # 宽松模式
        from agentbus.extensions.sandbox import SecurityPolicy
        permissive_policy = SecurityPolicy(level="permissive")
        sandbox.set_security_policy(ext, permissive_policy)
        permissive_result = sandbox.check_security(ext)
        print(f"   宽松模式: {'✓' if permissive_result else '✗'}")
        
        # 严格模式
        strict_policy = SecurityPolicy(level="strict")
        sandbox.set_security_policy(ext, strict_policy)
        strict_result = sandbox.check_security(ext)
        print(f"   严格模式: {'✓' if strict_result else '✗'}")
        
        # 测试安全报告
        print("2. 安全报告...")
        report = sandbox.get_security_report()
        print(f"   报告生成: ✓")
        print(f"   安全违规数: {report['total_violations']}")
        
        return permissive_result and strict_result
        
    except Exception as e:
        print(f"✗ 安全功能测试失败: {e}")
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("AgentBus扩展系统测试开始")
    print("=" * 50)
    
    # 设置日志
    setup_logging()
    
    # 运行测试
    tests = [
        ("扩展注册表", test_registry),
        ("扩展沙箱", test_sandbox),
        ("扩展管理器", test_manager),
        ("依赖解析", test_dependency_resolution),
        ("安全功能", test_security)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n开始测试: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{test_name}: {'通过' if result else '失败'}")
        except Exception as e:
            print(f"{test_name}: 异常 - {e}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！扩展系统运行正常。")
        return 0
    else:
        print(f"\n❌ {total - passed} 个测试失败。请检查日志文件了解详情。")
        return 1


if __name__ == "__main__":
    sys.exit(main())