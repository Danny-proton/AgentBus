#!/usr/bin/env python3
"""
AgentBus日志和监控系统使用示例

展示如何使用日志管理器、指标收集器和告警系统
"""

import sys
import time
import random
import threading
from pathlib import Path

# 添加agentbus路径
sys.path.insert(0, str(Path(__file__).parent.parent))

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
    create_email_channel,
    create_webhook_channel,
)


def demo_logging():
    """演示日志功能"""
    print("=== 日志功能演示 ===")
    
    # 获取主日志记录器
    logger = get_logger("demo")
    logger.info("这是信息日志", user_id=123, action="login")
    
    # 获取子日志记录器
    child_logger = get_child_logger("demo", "plugin")
    child_logger.debug("调试信息", plugin_name="test_plugin", duration=0.5)
    child_logger.warning("警告信息", plugin_name="test_plugin", error_code="W001")
    child_logger.error("错误信息", plugin_name="test_plugin", error_msg="Connection failed")
    
    print("✓ 日志记录完成")


def demo_metrics():
    """演示指标功能"""
    print("\n=== 指标收集演示 ===")
    
    metrics = get_metrics_collector()
    
    # 计数器
    for i in range(10):
        increment_metric("requests_total", 1, {"endpoint": f"/api/{i%3}"})
        time.sleep(0.1)
    
    # 仪表盘
    set_metric("active_connections", random.randint(5, 50))
    set_metric("memory_usage_percent", random.uniform(20, 80))
    
    # 计时器
    for i in range(5):
        duration = random.uniform(0.1, 2.0)
        record_time("response_time", duration, {"method": "GET"})
        time.sleep(0.1)
    
    # 直方图
    for i in range(20):
        value = random.uniform(0, 100)
        record_value("response_size", value)
    
    print("✓ 指标记录完成")
    
    # 导出指标
    metrics_json = metrics.export_metrics("json")
    print(f"指标数据长度: {len(metrics_json)} 字符")
    
    # 保存到文件
    metrics.save_metrics_to_file("/tmp/agentbus_demo_metrics.json")
    print("✓ 指标已保存到文件")


def demo_alerting():
    """演示告警功能"""
    print("\n=== 告警系统演示 ===")
    
    alert_manager = get_alert_manager()
    
    # 添加通知渠道（模拟）
    try:
        # 注意：这里使用模拟的Webhook，实际使用时需要真实的URL
        webhook_channel = create_webhook_channel("https://httpbin.org/post")
        alert_manager.add_notification_channel(webhook_channel)
        print("✓ Webhook通知渠道已添加")
    except Exception as e:
        print(f"Webhook渠道测试失败（预期）: {e}")
    
    # 添加告警规则
    cpu_alert_rule = AlertRule(
        name="high_cpu",
        description="CPU使用率过高",
        level=AlertLevel.WARNING,
        rule_type=AlertRuleType.THRESHOLD,
        metric_name="cpu_usage",
        condition=">",
        threshold=80.0,
        evaluation_window=60,
        cooldown_period=300
    )
    
    memory_alert_rule = AlertRule(
        name="high_memory",
        description="内存使用率过高",
        level=AlertLevel.ERROR,
        rule_type=AlertRuleType.THRESHOLD,
        metric_name="memory_usage_percent",
        condition=">",
        threshold=85.0,
        evaluation_window=60,
        cooldown_period=180
    )
    
    alert_manager.add_rule(cpu_alert_rule)
    alert_manager.add_rule(memory_alert_rule)
    
    print("✓ 告警规则已添加")
    
    # 手动触发告警
    alert_manager.trigger_alert(
        rule_name="high_cpu",
        message="CPU使用率过高，当前值: 85%",
        metric_name="cpu_usage",
        metric_value=85.0,
        labels={"host": "localhost"}
    )
    
    alert_manager.trigger_alert(
        rule_name="high_memory",
        message="内存使用率过高，当前值: 90%",
        metric_name="memory_usage_percent",
        metric_value=90.0,
        labels={"host": "localhost"}
    )
    
    print("✓ 手动告警已触发")
    
    # 获取活跃告警
    active_alerts = alert_manager.get_active_alerts()
    print(f"当前活跃告警数量: {len(active_alerts)}")
    
    # 测试通知渠道
    test_results = alert_manager.test_notification_channels()
    print(f"通知渠道测试结果: {test_results}")
    
    # 保存配置
    alert_manager.save_to_file("/tmp/agentbus_demo_alerts.json")
    print("✓ 告警配置已保存")


def simulate_application_load():
    """模拟应用负载"""
    print("\n=== 模拟应用负载 ===")
    
    logger = get_logger("load_simulator")
    metrics = get_metrics_collector()
    
    def simulate_request():
        """模拟单个请求"""
        start_time = time.time()
        
        # 模拟处理时间
        processing_time = random.uniform(0.1, 1.5)
        time.sleep(processing_time)
        
        # 记录指标
        record_time("request_duration", processing_time)
        increment_metric("requests_total")
        
        # 模拟错误
        if random.random() < 0.1:  # 10% 错误率
            increment_metric("requests_errors")
            logger.error("请求处理失败", error_code="500")
        
        # 模拟高延迟
        if processing_time > 1.0:
            logger.warning("请求响应时间过长", duration=processing_time)
            
        end_time = time.time()
        set_metric("active_connections", random.randint(10, 100))
    
    # 启动多个线程模拟并发请求
    threads = []
    for i in range(20):
        thread = threading.Thread(target=simulate_request)
        threads.append(thread)
        thread.start()
        
    # 等待所有线程完成
    for thread in threads:
        thread.join()
    
    print("✓ 应用负载模拟完成")


def main():
    """主函数"""
    print("AgentBus日志和监控系统演示")
    print("=" * 50)
    
    # 初始化日志系统
    initialize_logging(
        log_dir="/tmp/agentbus/demo",
        level="INFO",
        format_type="colored",
        enable_metrics=True,
        enable_alerting=True,
    )
    
    try:
        # 演示各种功能
        demo_logging()
        demo_metrics()
        demo_alerting()
        
        # 模拟应用负载
        simulate_application_load()
        
        # 显示系统信息
        print("\n=== 系统信息 ===")
        metrics = get_metrics_collector()
        snapshot = metrics.get_metrics_snapshot()
        
        print(f"系统CPU: {snapshot['system']['cpu_percent']:.1f}%")
        print(f"系统内存: {snapshot['system']['memory_percent']:.1f}%")
        print(f"自定义指标数量: {len(snapshot['custom_metrics'])}")
        
        print("\n=== 演示完成 ===")
        print("日志文件位置: /tmp/agentbus/demo/")
        print("指标文件位置: /tmp/agentbus_demo_metrics.json")
        print("告警配置位置: /tmp/agentbus_demo_alerts.json")
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        print("\n正在清理资源...")
        try:
            metrics = get_metrics_collector()
            metrics.stop_collection()
            
            alerts = get_alert_manager()
            alerts.stop_monitoring()
        except Exception as e:
            print(f"清理资源时出现错误: {e}")


if __name__ == "__main__":
    main()