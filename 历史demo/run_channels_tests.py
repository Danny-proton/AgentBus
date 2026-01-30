#!/usr/bin/env python3
"""
AgentBus渠道系统测试运行器

运行渠道系统的完整测试套件，包括：
- 基础功能测试
- 渠道管理器测试
- 异步功能测试
"""

import subprocess
import sys
import os

def run_command(command, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"运行: {description}")
    print(f"命令: {command}")
    print('='*60)
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        print("标准输出:")
        print(result.stdout)
        
        if result.stderr:
            print("标准错误:")
            print(result.stderr)
        
        print(f"返回码: {result.returncode}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"命令执行失败: {e}")
        return False

def main():
    """主函数"""
    # 切换到agentbus目录
    agentbus_dir = "/workspace/agentbus"
    os.chdir(agentbus_dir)
    
    print("AgentBus渠道系统测试套件")
    print("="*60)
    
    # 测试结果统计
    results = []
    
    # 1. 运行基础功能测试
    success = run_command(
        "python -m pytest tests/test_channels/test_base.py -v --tb=short",
        "渠道基础功能测试"
    )
    results.append(("基础功能测试", success))
    
    # 2. 运行管理器测试
    success = run_command(
        "python -m pytest tests/test_channels/test_manager.py -v --tb=short",
        "渠道管理器测试"
    )
    results.append(("管理器测试", success))
    
    # 3. 运行集成测试
    success = run_command(
        "python -m pytest tests/test_channels/test_manager.py::TestIntegration -v --tb=short",
        "集成测试"
    )
    results.append(("集成测试", success))
    
    # 4. 运行异步测试
    success = run_command(
        "python -m pytest tests/test_channels/test_manager.py::TestAsyncOperations -v --tb=short",
        "异步操作测试"
    )
    results.append(("异步测试", success))
    
    # 5. 错误处理测试
    success = run_command(
        "python -m pytest tests/test_channels/ -k 'ErrorHandling' -v --tb=short",
        "错误处理测试"
    )
    results.append(("错误处理测试", success))
    
    # 6. 运行所有测试
    success = run_command(
        "python -m pytest tests/test_channels/ --tb=short -q",
        "所有渠道测试"
    )
    results.append(("所有测试", success))
    
    # 显示测试结果摘要
    print("\n" + "="*60)
    print("测试结果摘要")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name:30} {status}")
        if success:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 个测试组通过")
    
    if passed == total:
        print("\n🎉 所有测试都通过了！")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试组失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())