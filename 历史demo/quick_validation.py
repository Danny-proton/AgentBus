#!/usr/bin/env python3
"""
快速验证AgentBus扩展系统
Quick validation of AgentBus Extension System
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def quick_validation():
    """快速验证所有组件"""
    print("🔍 AgentBus扩展系统快速验证")
    print("=" * 50)
    
    try:
        # 验证模块导入
        print("1. 验证模块导入...")
        
        from agentbus.extensions import (
            ExtensionManager, ExtensionRegistry, ExtensionSandbox,
            Extension, ExtensionState, SecurityLevel,
            ExtensionError, ExtensionLoadError, ExtensionDependencyError
        )
        print("   ✓ 扩展系统核心模块导入成功")
        
        # 创建基本组件
        print("2. 创建基本组件...")
        registry = ExtensionRegistry()
        sandbox = ExtensionSandbox()
        manager = ExtensionManager(sandbox=sandbox)
        print("   ✓ 组件创建成功")
        
        # 创建测试扩展
        print("3. 创建测试扩展...")
        class TestExtension(Extension):
            def __init__(self):
                super().__init__(
                    extension_id="test",
                    name="Test Extension",
                    version="1.0.0",
                    description="测试扩展",
                    author="System",
                    extension_type="custom"
                )
            
            def test_method(self):
                return "Hello from Test Extension!"
        
        test_ext = TestExtension()
        print("   ✓ 测试扩展创建成功")
        
        # 测试基本功能
        print("4. 测试基本功能...")
        
        # 注册
        if registry.register_extension(test_ext):
            print("   ✓ 扩展注册成功")
        else:
            print("   ✗ 扩展注册失败")
            return False
        
        # 获取
        if registry.get_extension("test"):
            print("   ✓ 扩展获取成功")
        else:
            print("   ✗ 扩展获取失败")
            return False
        
        # 加载
        if manager.load_extension(test_ext):
            print("   ✓ 扩展加载成功")
        else:
            print("   ✗ 扩展加载失败")
            return False
        
        # 激活
        if manager.activate_extension("test"):
            print("   ✓ 扩展激活成功")
        else:
            print("   ✗ 扩展激活失败")
            return False
        
        # 测试扩展功能
        if hasattr(test_ext, 'test_method'):
            result = test_ext.test_method()
            print(f"   ✓ 扩展功能测试: {result}")
        
        # 停用
        if manager.deactivate_extension("test"):
            print("   ✓ 扩展停用成功")
        else:
            print("   ✗ 扩展停用失败")
            return False
        
        print("\n🎉 所有验证通过！扩展系统工作正常。")
        return True
        
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = quick_validation()
    sys.exit(0 if success else 1)