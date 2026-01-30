#!/usr/bin/env python3
"""
AgentBus插件框架测试运行器

此脚本运行插件框架的完整测试套件，验证所有核心功能和管理器功能。
"""

import sys
import subprocess
import os
from pathlib import Path

def run_tests():
    """运行插件框架测试套件"""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print("🚀 开始运行AgentBus插件框架测试套件")
    print("=" * 60)
    
    # 测试配置
    test_commands = [
        {
            "name": "插件核心功能测试",
            "command": [
                "python", "-m", "pytest", 
                "tests/test_plugins/test_plugin_core.py",
                "-v", "--tb=short",
                "--color=yes"
            ],
            "description": "测试PluginContext、AgentBusPlugin、PluginTool、PluginHook等核心组件"
        },
        {
            "name": "插件管理器测试",
            "command": [
                "python", "-m", "pytest",
                "tests/test_plugins/test_plugin_manager.py", 
                "-v", "--tb=short",
                "--color=yes"
            ],
            "description": "测试PluginManager的完整功能，包括插件生命周期管理"
        },
        {
            "name": "插件集成测试",
            "command": [
                "python", "-m", "pytest",
                "tests/test_plugins/",
                "-v", "--tb=short", 
                "--color=yes",
                "-k", "integration"
            ],
            "description": "运行集成测试，验证完整的插件工作流程"
        },
        {
            "name": "插件异步功能测试",
            "command": [
                "python", "-m", "pytest",
                "tests/test_plugins/",
                "-v", "--tb=short",
                "--color=yes", 
                "-k", "async"
            ],
            "description": "专门测试插件的异步功能"
        },
        {
            "name": "插件错误处理测试",
            "command": [
                "python", "-m", "pytest",
                "tests/test_plugins/",
                "-v", "--tb=short",
                "--color=yes",
                "-k", "error"
            ],
            "description": "测试插件系统的错误处理和边界情况"
        },
        {
            "name": "完整测试套件",
            "command": [
                "python", "-m", "pytest",
                "tests/test_plugins/",
                "-v", "--tb=short",
                "--color=yes",
                "--cov=agentbus.plugins",
                "--cov-report=html:htmlcov",
                "--cov-report=term-missing"
            ],
            "description": "运行完整测试套件并生成覆盖率报告"
        }
    ]
    
    total_tests = len(test_commands)
    passed_tests = 0
    
    for i, test_config in enumerate(test_commands, 1):
        print(f"\n📋 测试 {i}/{total_tests}: {test_config['name']}")
        print(f"   描述: {test_config['description']}")
        print(f"   命令: {' '.join(test_config['command'])}")
        print("-" * 60)
        
        try:
            result = subprocess.run(
                test_config['command'],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            if result.returncode == 0:
                print(f"   ✅ 测试通过")
                passed_tests += 1
                # 显示简要结果
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'passed' in line or 'failed' in line or 'error' in line:
                        print(f"   📊 {line.strip()}")
                        break
            else:
                print(f"   ❌ 测试失败")
                print("   🔍 错误信息:")
                error_lines = result.stderr.split('\n')[:5]  # 只显示前5行错误
                for line in error_lines:
                    if line.strip():
                        print(f"      {line}")
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ 测试超时")
        except Exception as e:
            print(f"   🚫 运行错误: {e}")
    
    print("\n" + "=" * 60)
    print(f"🎯 测试总结: {passed_tests}/{total_tests} 测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！插件框架运行正常。")
        return True
    else:
        print("⚠️  部分测试失败，请检查上面的错误信息。")
        return False

def check_dependencies():
    """检查测试依赖"""
    print("🔍 检查测试依赖...")
    
    required_packages = [
        'pytest',
        'pytest-asyncio', 
        'pytest-cov'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  缺少依赖包: {', '.join(missing_packages)}")
        print("请运行以下命令安装:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ 所有依赖已安装")
    return True

def main():
    """主函数"""
    print("AgentBus插件框架测试套件")
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        return 1
    
    print()
    
    # 运行测试
    success = run_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())