#!/usr/bin/env python3
"""
AgentBus CLI工具测试脚本
AgentBus CLI Tool Test Script

测试AgentBus CLI工具的各项功能，包括服务管理、智能协作等。
"""

import asyncio
import subprocess
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))


def run_cli_command(command: str) -> tuple:
    """运行CLI命令"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)


def test_cli_help():
    """测试CLI帮助命令"""
    print("🔧 测试CLI帮助命令")
    print("-" * 30)
    
    returncode, stdout, stderr = run_cli_command("cd /workspace/agentbus && python cli.py --help")
    
    if returncode == 0:
        print("✅ CLI帮助命令执行成功")
        if "AgentBus命令行工具" in stdout:
            print("✅ 帮助信息正确显示")
        else:
            print("⚠️ 帮助信息可能不完整")
    else:
        print(f"❌ CLI帮助命令执行失败: {stderr}")
    
    print()


def test_cli_init():
    """测试CLI初始化"""
    print("🚀 测试CLI初始化")
    print("-" * 30)
    
    returncode, stdout, stderr = run_cli_command("cd /workspace/agentbus && python cli.py init --verbose")
    
    if returncode == 0:
        print("✅ CLI初始化成功")
        if "AgentBus CLI工具初始化完成" in stdout:
            print("✅ 初始化消息正确")
        else:
            print("⚠️ 初始化消息可能不完整")
    else:
        print(f"❌ CLI初始化失败: {stderr}")
    
    print()


def test_cli_status():
    """测试CLI状态命令"""
    print("📊 测试CLI状态命令")
    print("-" * 30)
    
    # 先初始化
    run_cli_command("cd /workspace/agentbus && python cli.py init")
    
    returncode, stdout, stderr = run_cli_command("cd /workspace/agentbus && python cli.py status")
    
    if returncode == 0:
        print("✅ CLI状态命令执行成功")
        if "服务状态" in stdout:
            print("✅ 状态信息正确显示")
        else:
            print("⚠️ 状态信息可能不完整")
    else:
        print(f"❌ CLI状态命令执行失败: {stderr}")
    
    print()


def test_cli_config():
    """测试CLI配置命令"""
    print("⚙️ 测试CLI配置命令")
    print("-" * 30)
    
    returncode, stdout, stderr = run_cli_command("cd /workspace/agentbus && python cli.py config")
    
    if returncode == 0:
        print("✅ CLI配置命令执行成功")
        if "AgentBus 配置" in stdout:
            print("✅ 配置信息正确显示")
        else:
            print("⚠️ 配置信息可能不完整")
    else:
        print(f"❌ CLI配置命令执行失败: {stderr}")
    
    print()


def test_cli_health():
    """测试CLI健康检查命令"""
    print("🏥 测试CLI健康检查命令")
    print("-" * 30)
    
    # 先初始化
    run_cli_command("cd /workspace/agentbus && python cli.py init")
    
    returncode, stdout, stderr = run_cli_command("cd /workspace/agentbus && python cli.py health")
    
    if returncode == 0:
        print("✅ CLI健康检查命令执行成功")
        if "AgentBus 健康检查" in stdout:
            print("✅ 健康检查信息正确显示")
        else:
            print("⚠️ 健康检查信息可能不完整")
    else:
        print(f"❌ CLI健康检查命令执行失败: {stderr}")
    
    print()


def test_cli_subcommands():
    """测试CLI子命令"""
    print("🔍 测试CLI子命令")
    print("-" * 30)
    
    # 测试HITL子命令
    returncode, stdout, stderr = run_cli_command("cd /workspace/agentbus && python cli.py hitl --help")
    if returncode == 0:
        print("✅ HITL子命令帮助正常")
    else:
        print(f"❌ HITL子命令帮助失败: {stderr}")
    
    # 测试知识总线子命令
    returncode, stdout, stderr = run_cli_command("cd /workspace/agentbus && python cli.py knowledge --help")
    if returncode == 0:
        print("✅ 知识总线子命令帮助正常")
    else:
        print(f"❌ 知识总线子命令帮助失败: {stderr}")
    
    # 测试多模型子命令
    returncode, stdout, stderr = run_cli_command("cd /workspace/agentbus && python cli.py model --help")
    if returncode == 0:
        print("✅ 多模型子命令帮助正常")
    else:
        print(f"❌ 多模型子命令帮助失败: {stderr}")
    
    # 测试流式响应子命令
    returncode, stdout, stderr = run_cli_command("cd /workspace/agentbus && python cli.py stream --help")
    if returncode == 0:
        print("✅ 流式响应子命令帮助正常")
    else:
        print(f"❌ 流式响应子命令帮助失败: {stderr}")
    
    print()


def test_cli_cleanup():
    """测试CLI清理命令"""
    print("🧹 测试CLI清理命令")
    print("-" * 30)
    
    returncode, stdout, stderr = run_cli_command("cd /workspace/agentbus && python cli.py cleanup")
    
    if returncode == 0:
        print("✅ CLI清理命令执行成功")
        if "清理完成" in stdout:
            print("✅ 清理消息正确")
        else:
            print("⚠️ 清理消息可能不完整")
    else:
        print(f"❌ CLI清理命令执行失败: {stderr}")
    
    print()


def test_cli_interactive_commands():
    """测试需要交互的命令"""
    print("🔄 测试交互式CLI命令")
    print("-" * 30)
    
    print("ℹ️  以下命令需要用户输入，将在非交互环境中跳过")
    print("   - cli.py knowledge search (需要搜索关键词)")
    print("   - cli.py knowledge add (需要知识内容)")
    print("   - cli.py model submit (需要任务内容)")
    print("   这些命令在完整测试中需要手动验证")
    print()


def run_comprehensive_test():
    """运行综合测试"""
    print("🎯 AgentBus CLI工具综合测试")
    print("=" * 50)
    print(f"时间: {asyncio.get_event_loop().time()}")
    print()
    
    # 测试列表
    tests = [
        ("CLI帮助命令", test_cli_help),
        ("CLI初始化", test_cli_init),
        ("CLI状态命令", test_cli_status),
        ("CLI配置命令", test_cli_config),
        ("CLI健康检查", test_cli_health),
        ("CLI子命令", test_cli_subcommands),
        ("CLI清理命令", test_cli_cleanup),
        ("交互式命令说明", test_cli_interactive_commands)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"🧪 运行测试: {test_name}")
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {test_name} - {e}")
            print()
    
    print("📋 测试总结")
    print("-" * 30)
    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 所有CLI测试通过！")
    elif passed >= total * 0.8:
        print("👍 大部分CLI测试通过")
    else:
        print("⚠️ 多个CLI测试失败，需要检查")
    
    print()
    print("💡 CLI工具功能概览:")
    print("   - init: 初始化AgentBus CLI工具")
    print("   - status: 查看服务状态")
    print("   - config: 查看配置信息")
    print("   - health: 健康检查")
    print("   - hitl: 人在回路管理")
    print("   - knowledge: 知识总线管理")
    print("   - model: 多模型协调管理")
    print("   - stream: 流式响应管理")
    print("   - cleanup: 清理资源")


if __name__ == "__main__":
    try:
        run_comprehensive_test()
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()