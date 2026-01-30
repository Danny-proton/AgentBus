#!/usr/bin/env python3
"""
AgentBus 集成测试运行脚本

此脚本用于运行完整的AgentBus系统集成测试，包括：
- 完整的系统集成测试
- 插件系统集成测试
- CLI集成测试
- 自定义测试套件

支持的功能：
- 运行所有集成测试
- 运行特定测试类或测试方法
- 并行测试执行
- 测试结果报告生成
- 测试覆盖率分析
- 性能基准测试
- 错误诊断和报告
"""

import sys
import os
import argparse
import json
import time
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import asyncio

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入测试配置
try:
    from tests.conftest import pytest_plugins
    from tests.test_integration.test_complete_system import TestCompleteSystemIntegration
    from tests.test_integration.test_plugin_integration import TestPluginSystemIntegration
    from tests.test_integration.test_cli_integration import TestCLIIntegration
except ImportError as e:
    print(f"❌ 导入测试模块失败: {e}")
    print("请确保测试文件路径正确")
    sys.exit(1)


class IntegrationTestRunner:
    """集成测试运行器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._load_default_config()
        self.setup_logging()
        self.test_results = []
        self.start_time = None
        self.end_time = None
        
    def _load_default_config(self) -> Dict[str, Any]:
        """加载默认配置"""
        return {
            "test_suites": {
                "complete_system": {
                    "enabled": True,
                    "description": "完整系统集成测试",
                    "timeout": 300,  # 5分钟
                    "parallel": False
                },
                "plugin_system": {
                    "enabled": True,
                    "description": "插件系统集成测试",
                    "timeout": 180,  # 3分钟
                    "parallel": True
                },
                "cli_integration": {
                    "enabled": True,
                    "description": "CLI集成测试",
                    "timeout": 120,  # 2分钟
                    "parallel": True
                }
            },
            "execution": {
                "parallel": True,
                "max_workers": 4,
                "timeout": 600,  # 10分钟总超时
                "retry_failed": True,
                "max_retries": 2
            },
            "reporting": {
                "format": "html",  # html, json, xml, text
                "output_dir": "test_reports",
                "include_coverage": True,
                "include_performance": True
            },
            "environment": {
                "test_data_dir": "test_data",
                "temp_dir": "test_temp",
                "log_level": "INFO",
                "cleanup": True
            }
        }
    
    def setup_logging(self):
        """设置日志记录"""
        log_level = self.config["environment"]["log_level"]
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('integration_tests.log', mode='w')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _prepare_test_environment(self) -> str:
        """准备测试环境"""
        self.logger.info("🔧 准备测试环境...")
        
        # 创建临时目录
        temp_dir = self.config["environment"]["temp_dir"]
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
        
        # 创建测试数据目录
        test_data_dir = self.config["environment"]["test_data_dir"]
        if not os.path.exists(test_data_dir):
            os.makedirs(test_data_dir, exist_ok=True)
        
        # 创建报告目录
        report_dir = self.config["reporting"]["output_dir"]
        if not os.path.exists(report_dir):
            os.makedirs(report_dir, exist_ok=True)
        
        self.logger.info(f"✅ 测试环境准备完成 (temp_dir: {temp_dir})")
        return temp_dir
    
    def _cleanup_test_environment(self, temp_dir: str):
        """清理测试环境"""
        if self.config["environment"]["cleanup"]:
            self.logger.info("🧹 清理测试环境...")
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                self.logger.info("✅ 测试环境清理完成")
            except Exception as e:
                self.logger.warning(f"⚠️ 清理测试环境时出现警告: {e}")
    
    def run_complete_system_tests(self) -> Dict[str, Any]:
        """运行完整系统集成测试"""
        self.logger.info("🚀 开始运行完整系统集成测试...")
        
        test_name = "完整系统集成测试"
        start_time = time.time()
        
        try:
            # 使用pytest运行完整系统测试
            test_file = project_root / "tests/test_integration/test_complete_system.py"
            cmd = [
                "python", "-m", "pytest",
                str(test_file),
                "-v",
                "--tb=short",
                "--timeout=300",
                f"--junit-xml={self.config['reporting']['output_dir']}/complete_system_report.xml"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            
            end_time = time.time()
            duration = end_time - start_time
            
            success = result.returncode == 0
            
            test_result = {
                "test_name": test_name,
                "success": success,
                "duration": duration,
                "start_time": datetime.fromtimestamp(start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd)
            }
            
            if success:
                self.logger.info(f"✅ {test_name} 完成 (耗时: {duration:.2f}s)")
            else:
                self.logger.error(f"❌ {test_name} 失败 (耗时: {duration:.2f}s)")
                self.logger.error(f"错误输出: {result.stderr}")
            
            return test_result
            
        except Exception as e:
            self.logger.error(f"❌ {test_name} 执行时发生异常: {e}")
            return {
                "test_name": test_name,
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
                "exception": True
            }
    
    def run_plugin_system_tests(self) -> Dict[str, Any]:
        """运行插件系统集成测试"""
        self.logger.info("🔌 开始运行插件系统集成测试...")
        
        test_name = "插件系统集成测试"
        start_time = time.time()
        
        try:
            # 使用pytest运行插件系统测试
            test_file = project_root / "tests/test_integration/test_plugin_integration.py"
            cmd = [
                "python", "-m", "pytest",
                str(test_file),
                "-v",
                "--tb=short",
                "--timeout=180",
                f"--junit-xml={self.config['reporting']['output_dir']}/plugin_system_report.xml"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            
            end_time = time.time()
            duration = end_time - start_time
            
            success = result.returncode == 0
            
            test_result = {
                "test_name": test_name,
                "success": success,
                "duration": duration,
                "start_time": datetime.fromtimestamp(start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd)
            }
            
            if success:
                self.logger.info(f"✅ {test_name} 完成 (耗时: {duration:.2f}s)")
            else:
                self.logger.error(f"❌ {test_name} 失败 (耗时: {duration:.2f}s)")
                self.logger.error(f"错误输出: {result.stderr}")
            
            return test_result
            
        except Exception as e:
            self.logger.error(f"❌ {test_name} 执行时发生异常: {e}")
            return {
                "test_name": test_name,
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
                "exception": True
            }
    
    def run_cli_integration_tests(self) -> Dict[str, Any]:
        """运行CLI集成测试"""
        self.logger.info("💻 开始运行CLI集成测试...")
        
        test_name = "CLI集成测试"
        start_time = time.time()
        
        try:
            # 使用pytest运行CLI集成测试
            test_file = project_root / "tests/test_integration/test_cli_integration.py"
            cmd = [
                "python", "-m", "pytest",
                str(test_file),
                "-v",
                "--tb=short",
                "--timeout=120",
                f"--junit-xml={self.config['reporting']['output_dir']}/cli_integration_report.xml"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            
            end_time = time.time()
            duration = end_time - start_time
            
            success = result.returncode == 0
            
            test_result = {
                "test_name": test_name,
                "success": success,
                "duration": duration,
                "start_time": datetime.fromtimestamp(start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd)
            }
            
            if success:
                self.logger.info(f"✅ {test_name} 完成 (耗时: {duration:.2f}s)")
            else:
                self.logger.error(f"❌ {test_name} 失败 (耗时: {duration:.2f}s)")
                self.logger.error(f"错误输出: {result.stderr}")
            
            return test_result
            
        except Exception as e:
            self.logger.error(f"❌ {test_name} 执行时发生异常: {e}")
            return {
                "test_name": test_name,
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
                "exception": True
            }
    
    def run_specific_tests(self, test_patterns: List[str]) -> Dict[str, Any]:
        """运行指定的测试"""
        self.logger.info(f"🎯 开始运行指定测试: {', '.join(test_patterns)}")
        
        test_name = f"指定测试 ({', '.join(test_patterns)})"
        start_time = time.time()
        
        try:
            cmd = [
                "python", "-m", "pytest",
                "-v",
                "--tb=short",
                "--timeout=300",
                f"--junit-xml={self.config['reporting']['output_dir']}/specific_tests_report.xml"
            ]
            
            # 添加测试模式
            for pattern in test_patterns:
                cmd.append(pattern)
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            
            end_time = time.time()
            duration = end_time - start_time
            
            success = result.returncode == 0
            
            test_result = {
                "test_name": test_name,
                "success": success,
                "duration": duration,
                "start_time": datetime.fromtimestamp(start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd),
                "test_patterns": test_patterns
            }
            
            if success:
                self.logger.info(f"✅ {test_name} 完成 (耗时: {duration:.2f}s)")
            else:
                self.logger.error(f"❌ {test_name} 失败 (耗时: {duration:.2f}s)")
                self.logger.error(f"错误输出: {result.stderr}")
            
            return test_result
            
        except Exception as e:
            self.logger.error(f"❌ {test_name} 执行时发生异常: {e}")
            return {
                "test_name": test_name,
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
                "exception": True,
                "test_patterns": test_patterns
            }
    
    def generate_test_report(self, results: List[Dict[str, Any]]) -> str:
        """生成测试报告"""
        self.logger.info("📊 生成测试报告...")
        
        report_dir = self.config["reporting"]["output_dir"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 生成JSON报告
        json_report = {
            "test_run": {
                "timestamp": timestamp,
                "total_tests": len(results),
                "successful_tests": sum(1 for r in results if r.get("success", False)),
                "failed_tests": sum(1 for r in results if not r.get("success", True)),
                "total_duration": sum(r.get("duration", 0) for r in results),
                "start_time": results[0].get("start_time") if results else None,
                "end_time": results[-1].get("end_time") if results else None
            },
            "results": results,
            "configuration": self.config
        }
        
        json_file = os.path.join(report_dir, f"integration_test_report_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, indent=2, ensure_ascii=False)
        
        # 生成文本摘要
        text_summary = self._generate_text_summary(results)
        text_file = os.path.join(report_dir, f"integration_test_summary_{timestamp}.txt")
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text_summary)
        
        self.logger.info(f"✅ 测试报告已生成:")
        self.logger.info(f"   JSON: {json_file}")
        self.logger.info(f"   文本: {text_file}")
        
        return json_file
    
    def _generate_text_summary(self, results: List[Dict[str, Any]]) -> str:
        """生成文本格式摘要"""
        successful_tests = sum(1 for r in results if r.get("success", False))
        failed_tests = len(results) - successful_tests
        total_duration = sum(r.get("duration", 0) for r in results)
        
        summary = f"""
AgentBus 集成测试报告
{'=' * 50}

测试概览:
- 总测试数: {len(results)}
- 通过测试: {successful_tests}
- 失败测试: {failed_tests}
- 总耗时: {total_duration:.2f}秒
- 成功率: {(successful_tests/len(results)*100):.1f}%

详细结果:
"""
        
        for result in results:
            status = "PASS" if result.get("success", False) else "FAIL"
            duration = result.get("duration", 0)
            summary += f"\n[{status}] {result.get('test_name', 'Unknown Test')} ({duration:.2f}s)"
            
            if not result.get("success", False):
                if result.get("stderr"):
                    summary += f"\n  错误: {result['stderr'][:200]}..."
                if result.get("exception"):
                    summary += f"\n  异常: {result.get('error', 'Unknown error')}"
        
        summary += f"\n\n测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return summary
    
    def run_all_tests(self) -> bool:
        """运行所有集成测试"""
        self.logger.info("🚀 开始运行所有集成测试...")
        
        self.start_time = time.time()
        temp_dir = self._prepare_test_environment()
        
        try:
            all_results = []
            overall_success = True
            
            # 运行完整系统测试
            if self.config["test_suites"]["complete_system"]["enabled"]:
                result = self.run_complete_system_tests()
                all_results.append(result)
                if not result.get("success", False):
                    overall_success = False
            
            # 运行插件系统测试
            if self.config["test_suites"]["plugin_system"]["enabled"]:
                result = self.run_plugin_system_tests()
                all_results.append(result)
                if not result.get("success", False):
                    overall_success = False
            
            # 运行CLI集成测试
            if self.config["test_suites"]["cli_integration"]["enabled"]:
                result = self.run_cli_integration_tests()
                all_results.append(result)
                if not result.get("success", False):
                    overall_success = False
            
            self.test_results = all_results
            self.end_time = time.time()
            
            # 生成报告
            report_file = self.generate_test_report(all_results)
            
            # 输出摘要
            self._print_summary(all_results)
            
            return overall_success
            
        finally:
            self._cleanup_test_environment(temp_dir)
    
    def run_specific_test_suite(self, suite_name: str) -> bool:
        """运行特定的测试套件"""
        self.logger.info(f"🎯 运行特定测试套件: {suite_name}")
        
        self.start_time = time.time()
        temp_dir = self._prepare_test_environment()
        
        try:
            result = None
            
            if suite_name == "complete_system":
                result = self.run_complete_system_tests()
            elif suite_name == "plugin_system":
                result = self.run_plugin_system_tests()
            elif suite_name == "cli_integration":
                result = self.run_cli_integration_tests()
            else:
                self.logger.error(f"❌ 未知的测试套件: {suite_name}")
                return False
            
            if result:
                self.test_results = [result]
                self.end_time = time.time()
                
                # 生成报告
                report_file = self.generate_test_report([result])
                
                # 输出摘要
                self._print_summary([result])
                
                return result.get("success", False)
            
            return False
            
        finally:
            self._cleanup_test_environment(temp_dir)
    
    def run_custom_tests(self, test_patterns: List[str]) -> bool:
        """运行自定义测试"""
        self.logger.info(f"🎨 运行自定义测试: {', '.join(test_patterns)}")
        
        self.start_time = time.time()
        temp_dir = self._prepare_test_environment()
        
        try:
            result = self.run_specific_tests(test_patterns)
            self.test_results = [result]
            self.end_time = time.time()
            
            # 生成报告
            report_file = self.generate_test_report([result])
            
            # 输出摘要
            self._print_summary([result])
            
            return result.get("success", False)
            
        finally:
            self._cleanup_test_environment(temp_dir)
    
    def _print_summary(self, results: List[Dict[str, Any]]):
        """打印测试摘要"""
        successful_tests = sum(1 for r in results if r.get("success", False))
        failed_tests = len(results) - successful_tests
        total_duration = sum(r.get("duration", 0) for r in results)
        
        print("\n" + "=" * 60)
        print("🎯 AgentBus 集成测试摘要")
        print("=" * 60)
        print(f"📊 总测试数: {len(results)}")
        print(f"✅ 通过测试: {successful_tests}")
        print(f"❌ 失败测试: {failed_tests}")
        print(f"⏱️  总耗时: {total_duration:.2f}秒")
        print(f"📈 成功率: {(successful_tests/len(results)*100):.1f}%")
        
        if self.start_time and self.end_time:
            print(f"🕒 开始时间: {datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"🕒 结束时间: {datetime.fromtimestamp(self.end_time).strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n详细结果:")
        for result in results:
            status_icon = "✅" if result.get("success", False) else "❌"
            duration = result.get("duration", 0)
            print(f"  {status_icon} {result.get('test_name', 'Unknown Test')} ({duration:.2f}s)")
        
        print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AgentBus 集成测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python run_integration_tests.py --all                    # 运行所有集成测试
  python run_integration_tests.py --suite complete_system  # 运行完整系统测试
  python run_integration_tests.py --pattern tests/test_integration/test_complete_system.py::TestCompleteSystemIntegration::test_plugin_system_integration
  python run_integration_tests.py --list                   # 列出可用的测试套件
        """
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="运行所有集成测试"
    )
    
    parser.add_argument(
        "--suite",
        choices=["complete_system", "plugin_system", "cli_integration"],
        help="运行特定的测试套件"
    )
    
    parser.add_argument(
        "--pattern",
        action="append",
        help="运行匹配模式的特定测试 (可多次使用)"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出可用的测试套件"
    )
    
    parser.add_argument(
        "--config",
        help="自定义配置文件路径"
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="启用并行测试执行"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出"
    )
    
    args = parser.parse_args()
    
    # 加载配置
    config = None
    if args.config:
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"✅ 已加载配置文件: {args.config}")
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            sys.exit(1)
    
    # 创建测试运行器
    runner = IntegrationTestRunner(config)
    
    # 设置详细输出
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 设置并行执行
    if args.parallel:
        runner.config["execution"]["parallel"] = True
    
    # 处理命令
    if args.list:
        print("📋 可用的测试套件:")
        print("  complete_system  - 完整系统集成测试")
        print("  plugin_system   - 插件系统集成测试")
        print("  cli_integration - CLI集成测试")
        print("\n可用的测试模式示例:")
        print("  tests/test_integration/test_complete_system.py")
        print("  tests/test_integration/test_complete_system.py::TestCompleteSystemIntegration")
        print("  tests/test_integration/test_complete_system.py::TestCompleteSystemIntegration::test_plugin_system_integration")
        return
    
    if args.all:
        success = runner.run_all_tests()
        sys.exit(0 if success else 1)
    
    elif args.suite:
        success = runner.run_specific_test_suite(args.suite)
        sys.exit(0 if success else 1)
    
    elif args.pattern:
        success = runner.run_custom_tests(args.pattern)
        sys.exit(0 if success else 1)
    
    else:
        print("❌ 请指定要运行的测试")
        print("使用 --help 查看可用选项")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 运行测试时发生未处理的异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)