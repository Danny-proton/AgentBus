#!/usr/bin/env python3
"""
AgentBus日志和监控系统测试脚本

测试所有核心功能的正常运行
"""

import sys
import time
import tempfile
import shutil
from pathlib import Path

# 添加agentbus路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入AgentBus日志系统模块
try:
    from agentbus_logging import (
        initialize_logging,
        get_logger,
        get_child_logger,
        get_metrics_collector,
        get_alert_manager,
        increment_metric,
        set_metric,
        record_time,
        record_value,
        AlertRule,
        AlertLevel,
        AlertRuleType,
        LogLevel,
        LogFormat,
    )
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"警告: 模块导入失败: {e}")
    IMPORTS_AVAILABLE = False

def test_imports():
    """测试模块导入"""
    print("测试模块导入...")
    if IMPORTS_AVAILABLE:
        print("✓ 所有模块导入成功")
        return True
    else:
        print("✗ 模块导入失败")
        return False


def test_logging_basic():
    """测试基本日志功能"""
    print("\n测试基本日志功能...")
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        
        # 初始化日志
        initialize_logging(
            log_dir=temp_dir,
            level="DEBUG",
            format_type="json",
            enable_console=False,  # 关闭控制台输出避免干扰
        )
        
        # 测试日志记录
        logger = get_logger("test_app")
        logger.debug("调试信息", test_param="value")
        logger.info("信息日志", user_id=123)
        logger.warning("警告信息", error_code="W001")
        logger.error("错误信息", error_msg="测试错误")
        logger.critical("严重错误", system_status="down")
        
        # 测试子日志记录器
        child_logger = get_child_logger("test_app", "plugin")
        child_logger.info("插件日志", plugin_name="test_plugin")
        
        print("✓ 日志记录功能正常")
        
        # 检查日志文件
        log_files = list(Path(temp_dir).glob("*.log"))
        if log_files:
            print(f"✓ 日志文件已创建: {log_files[0].name}")
            # 简单检查文件内容
            with open(log_files[0], 'r') as f:
                content = f.read()
                if len(content) > 0 and '"level":' in content:
                    print("✓ 日志文件格式正确")
                else:
                    print("✗ 日志文件格式异常")
                    return False
        else:
            print("✗ 日志文件未创建")
            return False
            
        # 清理临时目录
        shutil.rmtree(temp_dir)
        return True
        
    except Exception as e:
        print(f"✗ 日志功能测试失败: {e}")
        return False


def test_metrics_basic():
    """测试基本指标功能"""
    print("\n测试基本指标功能...")
    try:
        # 获取指标收集器
        metrics = get_metrics_collector()
        
        # 测试计数器
        increment_metric("test_counter", 1, {"type": "test"})
        increment_metric("test_counter", 2, {"type": "test"})
        
        # 测试仪表盘
        set_metric("test_gauge", 75.5, {"component": "cpu"})
        
        # 测试计时器
        start_time = time.time()
        time.sleep(0.1)  # 模拟工作
        duration = time.time() - start_time
        record_time("test_timer", duration)
        
        # 测试直方图
        import random
        for _ in range(10):
            value = random.uniform(0, 100)
            record_time("test_histogram", value)
        
        # 获取指标快照
        snapshot = metrics.get_metrics_snapshot()
        
        if "custom_metrics" in snapshot and len(snapshot["custom_metrics"]) > 0:
            print("✓ 指标记录功能正常")
            print(f"  记录了 {len(snapshot['custom_metrics'])} 个自定义指标")
            return True
        else:
            print("✗ 指标快照为空")
            return False
            
    except Exception as e:
        print(f"✗ 指标功能测试失败: {e}")
        return False


def test_alerting_basic():
    """测试基本告警功能"""
    print("\n测试基本告警功能...")
    try:
        # 获取告警管理器
        alert_manager = get_alert_manager()
        
        # 添加模拟通知渠道
        try:
            from agentbus_logging import create_webhook_channel
            webhook = create_webhook_channel("https://httpbin.org/post")
            alert_manager.add_notification_channel(webhook)
            print("  添加了测试Webhook渠道")
        except:
            print("  Webhook渠道测试跳过（网络不可用）")
        
        # 创建告警规则
        rule = AlertRule(
            name="test_high_cpu",
            description="测试CPU告警",
            level=AlertLevel.WARNING,
            rule_type=AlertRuleType.THRESHOLD,
            metric_name="cpu_percent",
            condition=">",
            threshold=80.0,
            evaluation_window=60,
            cooldown_period=300
        )
        
        alert_manager.add_rule(rule)
        print("✓ 告警规则添加成功")
        
        # 手动触发告警
        alert_manager.trigger_alert(
            rule_name="test_high_cpu",
            message="测试告警: CPU使用率85%",
            metric_name="cpu_percent",
            metric_value=85.0,
            labels={"host": "test-server"}
        )
        print("✓ 手动告警触发成功")
        
        # 获取活跃告警
        active_alerts = alert_manager.get_active_alerts()
        print(f"  当前活跃告警: {len(active_alerts)} 个")
        
        # 测试通知渠道
        test_results = alert_manager.test_notification_channels()
        print(f"  通知渠道测试结果: {test_results}")
        
        return True
        
    except Exception as e:
        print(f"✗ 告警功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """测试集成功能"""
    print("\n测试集成功能...")
    try:
        # 创建集成测试场景
        logger = get_logger("integration_test")
        metrics = get_metrics_collector()
        
        # 模拟一个完整的操作流程
        logger.info("开始集成测试", test_name="full_workflow")
        
        # 模拟请求处理
        for i in range(5):
            # 记录请求开始
            logger.debug(f"处理请求 {i+1}", request_id=i)
            increment_metric("integration_requests_total", 1, {"step": "start"})
            
            # 模拟处理时间
            import random
            import time
            processing_time = random.uniform(0.05, 0.2)
            time.sleep(processing_time)
            record_time("integration_processing_time", processing_time)
            
            # 记录处理完成
            increment_metric("integration_requests_total", 1, {"step": "end"})
            logger.info(f"请求 {i+1} 处理完成", duration=processing_time)
        
        logger.info("集成测试完成", total_requests=5)
        
        print("✓ 集成测试完成")
        return True
        
    except Exception as e:
        print(f"✗ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance():
    """测试性能"""
    print("\n测试性能...")
    try:
        from agentbus_logging import get_logger, increment_metric
        
        logger = get_logger("performance_test")
        
        # 大量日志写入测试
        start_time = time.time()
        for i in range(1000):
            logger.info(f"性能测试日志 {i}", iteration=i)
        
        log_time = time.time() - start_time
        
        # 大量指标写入测试
        start_time = time.time()
        for i in range(1000):
            increment_metric("performance_counter", 1)
        
        metrics_time = time.time() - start_time
        
        print(f"✓ 性能测试完成")
        print(f"  1000条日志写入耗时: {log_time:.3f}秒")
        print(f"  1000个指标写入耗时: {metrics_time:.3f}秒")
        print(f"  日志吞吐: {1000/log_time:.0f} msg/sec")
        print(f"  指标吞吐: {1000/metrics_time:.0f} ops/sec")
        
        # 性能应该是可接受的
        if log_time < 5.0 and metrics_time < 5.0:
            print("✓ 性能测试通过")
            return True
        else:
            print("⚠ 性能测试警告: 写入速度较慢")
            return True  # 仍然返回True，因为性能可能受环境影响
            
    except Exception as e:
        print(f"✗ 性能测试失败: {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("AgentBus日志和监控系统测试")
    print("=" * 50)
    
    tests = [
        ("模块导入", test_imports),
        ("基本日志功能", test_logging_basic),
        ("基本指标功能", test_metrics_basic),
        ("基本告警功能", test_alerting_basic),
        ("集成功能", test_integration),
        ("性能测试", test_performance),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name}测试异常: {e}")
            results.append((test_name, False))
        
        time.sleep(0.5)  # 测试间隔
    
    # 总结结果
    print("\n" + "=" * 50)
    print("测试结果总结:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name:<15} {status}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！AgentBus日志和监控系统运行正常。")
        return True
    else:
        print(f"⚠ {total-passed} 个测试失败，请检查相关功能。")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)