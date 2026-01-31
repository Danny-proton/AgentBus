#!/usr/bin/env python3
"""
AgentBus CLI 增强功能演示
Demonstration of Enhanced AgentBus CLI Features

展示新实现的CLI增强功能的使用方法和效果。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from cli.commands.command_parser import AdvancedCommandParser, COMMAND_SCHEMAS
from cli.main import AgentBusCLI


def demo_command_parser():
    """演示高级命令解析功能"""
    print("=" * 60)
    print("🎯 高级命令解析器演示")
    print("=" * 60)
    
    parser = AdvancedCommandParser()
    
    # 注册预定义的命令模式
    for command, schema in COMMAND_SCHEMAS.items():
        parser.register_command(command, schema)
    
    # 演示复杂的命令解析
    test_commands = [
        'config.set database.host localhost --profile=production --encrypt',
        'browser.start --headless --profile=default --proxy=127.0.0.1:8080',
        'scheduler.add daily-backup "python backup.py" "0 2 * * *" --priority=high --timeout=3600',
        'channel.start discord --account=myaccount',
        'plugin.enable github-integration'
    ]
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\n📝 测试命令 {i}: {cmd}")
        try:
            parsed = parser.parse_command_line(cmd)
            print(f"✅ 解析成功:")
            print(f"   命令: {parsed.command}")
            if parsed.subcommand:
                print(f"   子命令: {parsed.subcommand}")
            print(f"   选项: {parsed.options}")
            print(f"   参数: {parsed.arguments}")
            
            # 验证命令
            is_valid, errors = parser.validate_command(parsed)
            if is_valid:
                print(f"   验证: ✅ 有效")
            else:
                print(f"   验证: ❌ 无效")
                for error in errors:
                    print(f"      - {error}")
                    
        except Exception as e:
            print(f"❌ 解析失败: {e}")
    
    # 演示自动补全
    print(f"\n🔧 自动补全演示:")
    partial_commands = ['conf', 'brow', 'sched', 'chan', 'plu']
    for partial in partial_commands:
        suggestions = parser.autocomplete(partial)
        print(f"   '{partial}' -> {suggestions[:3]}...")  # 显示前3个建议


def demo_cli_features():
    """演示CLI增强功能"""
    print("\n" + "=" * 60)
    print("🚀 CLI增强功能演示")
    print("=" * 60)
    
    # 显示功能模块
    features = {
        "🔧 配置管理": [
            "agentbus config profile-create production --base=development",
            "agentbus config set database.host localhost --profile=production",
            "agentbus config export --output=config.json --format=json",
            "agentbus config import config.json --profile=production"
        ],
        "🌐 浏览器管理": [
            "agentbus browser start --headless --profile=default",
            "agentbus browser navigate https://example.com",
            "agentbus browser screenshot --output=screenshot.png",
            "agentbus browser eval \"document.title\""
        ],
        "📡 渠道管理": [
            "agentbus channel add discord --type=discord --name=\"Production Discord\"",
            "agentbus channel connect discord --account=prod_account",
            "agentbus channel test discord",
            "agentbus channel clone discord discord_backup"
        ],
        "⏰ 任务调度": [
            "agentbus scheduler add daily-backup \"python backup.py\" \"0 2 * * *\"",
            "agentbus scheduler enable daily-backup",
            "agentbus scheduler run-now daily-backup",
            "agentbus scheduler status"
        ],
        "🔌 插件管理": [
            "agentbus plugin list --status=active",
            "agentbus plugin enable github-integration",
            "agentbus plugin info github-integration",
            "agentbus plugin export --output=plugins.json"
        ]
    }
    
    for category, commands in features.items():
        print(f"\n{category}:")
        for cmd in commands:
            print(f"   {cmd}")


def demo_error_handling():
    """演示错误处理和用户体验"""
    print("\n" + "=" * 60)
    print("🛡️ 错误处理和用户体验演示")
    print("=" * 60)
    
    error_scenarios = [
        {
            "scenario": "连接不存在的渠道",
            "command": "agentbus channel connect nonexistent-channel",
            "expected_error": "❌ 渠道管理器未初始化",
            "solution": "需要先初始化渠道管理器或检查配置"
        },
        {
            "scenario": "启动未安装的浏览器",
            "command": "agentbus browser start --profile=nonexistent",
            "expected_error": "❌ 启动浏览器失败: [具体错误信息]",
            "solution": "检查浏览器安装或使用默认配置"
        },
        {
            "scenario": "无效的Cron表达式",
            "command": "agentbus scheduler add test \"echo hello\" \"invalid-cron\"",
            "expected_error": "❌ 添加任务失败: [解析错误]",
            "solution": "使用标准的Cron表达式格式"
        },
        {
            "scenario": "配置文件权限问题",
            "command": "agentbus config import /root/private_config.json",
            "expected_error": "❌ 导入配置失败: [权限错误]",
            "solution": "检查文件权限或使用sudo运行"
        }
    ]
    
    for i, scenario in enumerate(error_scenarios, 1):
        print(f"\n📋 场景 {i}: {scenario['scenario']}")
        print(f"   命令: {scenario['command']}")
        print(f"   预期错误: {scenario['expected_error']}")
        print(f"   解决方案: {scenario['solution']}")


def demo_advanced_features():
    """演示高级特性"""
    print("\n" + "=" * 60)
    print("⭐ 高级特性演示")
    print("=" * 60)
    
    advanced_features = [
        {
            "feature": "异步命令执行",
            "description": "所有命令都支持异步执行，提高性能",
            "example": "await commands.start_browser(headless=True)"
        },
        {
            "feature": "智能命令验证",
            "description": "命令参数和选项的实时验证",
            "example": "parser.validate_command(parsed_command)"
        },
        {
            "feature": "多格式输出",
            "description": "支持table、JSON等多种输出格式",
            "example": "agentbus config list --format=json"
        },
        {
            "feature": "批量操作",
            "description": "支持批量启用/禁用渠道、插件等",
            "example": "agentbus channel connect-all"
        },
        {
            "feature": "实时状态监控",
            "description": "组件状态的实时监控和反馈",
            "example": "agentbus status"
        },
        {
            "feature": "配置热重载",
            "description": "配置文件变更的实时检测和应用",
            "example": "配置变更自动生效"
        }
    ]
    
    for feature in advanced_features:
        print(f"\n🎯 {feature['feature']}")
        print(f"   描述: {feature['description']}")
        print(f"   示例: {feature['example']}")


def demo_workflow():
    """演示完整的工作流程"""
    print("\n" + "=" * 60)
    print("🔄 完整工作流程演示")
    print("=" * 60)
    
    workflows = [
        {
            "name": "新项目部署流程",
            "steps": [
                "agentbus health                    # 健康检查",
                "agentbus config profile-create prod --base=dev  # 创建生产环境配置",
                "agentbus config set app.version 1.0.0 --profile=prod",
                "agentbus browser start --headless    # 启动浏览器",
                "agentbus channel add prod-slack --type=slack",
                "agentbus channel connect prod-slack",
                "agentbus scheduler add deploy-check \"python check_deploy.py\" \"*/5 * * * *\"",
                "agentbus scheduler enable deploy-check",
                "agentbus status                    # 确认系统状态"
            ]
        },
        {
            "name": "日常维护流程",
            "steps": [
                "agentbus status                    # 检查系统状态",
                "agentbus channel test all          # 测试所有渠道",
                "agentbus browser restart           # 重启浏览器",
                "agentbus scheduler logs daily-backup --limit=100",
                "agentbus config backup --profile=prod  # 备份配置",
                "agentbus plugin reload github-integration"
            ]
        },
        {
            "name": "故障排查流程",
            "steps": [
                "agentbus health                    # 基础健康检查",
                "agentbus status --output=debug.json  # 输出详细状态",
                "agentbus channel logs discord --limit=200",
                "agentbus scheduler status          # 检查任务状态",
                "agentbus config validate --profile=prod  # 验证配置",
                "agentbus browser info              # 查看浏览器信息"
            ]
        }
    ]
    
    for workflow in workflows:
        print(f"\n📋 {workflow['name']}:")
        for i, step in enumerate(workflow['steps'], 1):
            print(f"   {i:2d}. {step}")


def main():
    """主演示函数"""
    print("🎉 AgentBus CLI 增强功能演示")
    print("基于Moltbot架构的高级命令行界面")
    
    # 执行各个演示
    demo_command_parser()
    demo_cli_features()
    demo_error_handling()
    demo_advanced_features()
    demo_workflow()
    
    print("\n" + "=" * 60)
    print("✅ 演示完成")
    print("=" * 60)
    print("🌟 AgentBus CLI 增强功能已全面实现")
    print("🚀 立即体验: python -m agentbus.cli.main --help")


if __name__ == '__main__':
    main()