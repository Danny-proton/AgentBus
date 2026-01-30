#!/usr/bin/env python3
"""
AgentBus增强日志监控系统演示

展示完整的日志监控功能：分级记录、远程传输、查询分析、存储管理、告警系统等
"""

import asyncio
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
import random

# 导入AgentBus日志系统
from agentbus_logging import (
    # 基础功能
    initialize_enhanced_logging,
    get_enhanced_logger,
    get_enhanced_monitoring_system_instance,
    
    # 高级功能
    LogQuery,
    LogQueryEngine,
    StorageConfig,
    StorageStrategy,
    CompressionType,
    create_storage,
    create_query_engine,
    create_http_transport,
    
    # 分析工具
    quick_log_analysis,
    detect_log_anomalies,
    LogPatternAnalyzer,
    ErrorAnalyzer,
    PerformanceAnalyzer,
    LogReporter,
    
    # 装饰器
    performance_monitor,
    audit_log,
    security_monitor,
    
    # 增强功能
    EnhancedLogLevel,
    MonitoringEventType,
    AlertLevel,
    AlertRule,
    AlertRuleType
)


class EnhancedLoggingDemo:
    """增强日志系统演示"""
    
    def __init__(self):
        self.log_dir = "/tmp/agentbus/logs/demo"
        self.config = self._create_demo_config()
        self.monitoring_system = None
        self.running = False
        
    def _create_demo_config(self) -> dict:
        """创建演示配置"""
        return {
            "logging": {
                "log_dir": self.log_dir,
                "level": "INFO",
                "format_type": "json",
                "max_file_size": 10 * 1024 * 1024,  # 10MB
                "backup_count": 5,
                "retention_days": 7,
                "enable_console": True,
                "enable_file": True,
                "enable_compression": True,
            },
            "remote_transports": [
                {
                    "type": "http",
                    "name": "demo_http",
                    "url": "http://localhost:9999/logs",
                    "options": {
                        "batch_size": 10,
                        "batch_timeout": 5.0,
                        "enable_compression": True
                    }
                }
            ],
            "log_dirs": [self.log_dir],
            "index_path": f"{self.log_dir}/index",
            "storage": {
                "base_path": f"{self.log_dir}/storage",
                "strategy": "json",
                "compression": "gzip",
                "max_file_size": 5 * 1024 * 1024,  # 5MB
                "max_files_per_day": 12,
                "retention_days": 7,
                "enable_indexing": True,
                "enable_partitioning": True,
                "partition_interval": "hour",
            },
            "stream_monitoring": {
                "log_files": [f"{self.log_dir}/demo.log"]
            },
            "centralized_server": {
                "port": 9999,
                "enable_ssl": False,
            },
            "alert_rules": [
                {
                    "name": "high_error_rate",
                    "description": "错误率过高",
                    "level": "WARNING",
                    "rule_type": "threshold",
                    "metric_name": "error_rate",
                    "condition": ">",
                    "threshold": 5.0,
                    "evaluation_window": 60,
                    "cooldown_period": 300
                },
                {
                    "name": "performance_issue",
                    "description": "响应时间过长",
                    "level": "WARNING",
                    "rule_type": "threshold",
                    "metric_name": "response_time",
                    "condition": ">",
                    "threshold": 2.0,
                    "evaluation_window": 300,
                    "cooldown_period": 600
                }
            ]
        }
        
    def initialize(self):
        """初始化演示环境"""
        print("🚀 初始化AgentBus增强日志监控系统...")
        
        # 创建目录
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        
        # 初始化增强日志系统
        self.monitoring_system = initialize_enhanced_logging(self.config)
        
        # 添加事件回调
        self.monitoring_system.add_event_callback(self._handle_monitoring_event)
        
        print("✅ 日志监控系统初始化完成")
        
    def _handle_monitoring_event(self, event):
        """处理监控事件"""
        print(f"📊 监控事件: {event.event_type.value} - {event.source}")
        
    def demo_basic_logging(self):
        """演示基础日志功能"""
        print("\n📝 演示基础日志功能...")
        
        # 获取不同类型的日志记录器
        main_logger = get_enhanced_logger("demo.main")
        api_logger = get_enhanced_logger("demo.api")
        auth_logger = get_enhanced_logger("demo.auth")
        perf_logger = get_enhanced_logger("demo.performance")
        
        # 基础日志
        main_logger.info("应用程序启动", version="1.0.0", environment="demo")
        main_logger.info("系统配置加载完成", config_items=5)
        
        # API日志
        api_logger.info("API请求处理开始", endpoint="/api/users", method="GET")
        api_logger.debug("查询参数", params={"page": 1, "limit": 10})
        api_logger.warning("API响应时间较慢", duration=1.5, threshold=1.0)
        
        # 认证日志
        auth_logger.info("用户登录尝试", user_id="user123", ip="192.168.1.100")
        auth_logger.security("可疑登录尝试", ip="10.0.0.1", attempts=5)
        auth_logger.audit("用户权限变更", user_id="user456", action="grant_admin", by="admin")
        
        # 性能日志
        perf_logger.performance("数据库查询完成", duration=0.8, table="users")
        perf_logger.performance("外部API调用完成", duration=2.3, service="payment")
        
        # 错误日志
        main_logger.error("数据库连接失败", error="Connection timeout", retry_count=3)
        main_logger.critical("系统内存不足", memory_usage="95%", threshold="80%")
        
        print("✅ 基础日志演示完成")
        
    def demo_correlation_tracking(self):
        """演示关联跟踪功能"""
        print("\n🔗 演示关联跟踪功能...")
        
        from agentbus_logging import LogCorrelationTracker, get_enhanced_monitoring_system
        
        monitoring_system = get_enhanced_monitoring_system()
        if not monitoring_system:
            print("❌ 监控系统未初始化")
            return
            
        # 创建关联跟踪器
        tracker = LogCorrelationTracker(monitoring_system)
        
        # 开始关联跟踪
        correlation_id = "req-12345"
        tracker.start_correlation(correlation_id, {
            "user_id": "user123",
            "request_type": "user_search",
            "client": "web"
        })
        
        # 获取带关联ID的日志记录器
        logger = get_enhanced_logger("demo.correlation", correlation_id)
        
        # 模拟处理流程
        logger.info("开始处理用户搜索请求", query="john doe")
        logger.debug("查询数据库", table="users", conditions={"name": "john doe"})
        logger.performance("数据库查询完成", duration=0.5)
        logger.info("格式化搜索结果", result_count=5)
        logger.info("返回搜索结果")
        
        # 结束关联跟踪
        result = tracker.end_correlation(correlation_id, "success")
        print(f"✅ 关联跟踪完成: {result}")
        
    def demo_performance_monitoring(self):
        """演示性能监控装饰器"""
        print("\n⚡ 演示性能监控...")
        
        @performance_monitor("database_query", "req-67890")
        def slow_database_query():
            """模拟慢查询"""
            time.sleep(random.uniform(0.1, 2.0))
            return {"result": "query completed"}
            
        @performance_monitor("api_call")
        def external_api_call():
            """模拟外部API调用"""
            time.sleep(random.uniform(0.5, 3.0))
            return {"status": "success", "data": "api response"}
            
        @audit_log("user_action", "user_profile", "update")
        def update_user_profile(user_id, changes):
            """模拟用户资料更新"""
            print(f"   更新用户 {user_id} 的资料: {changes}")
            time.sleep(0.1)
            return True
            
        @security_monitor("login_attempt")
        def login_attempt(username, ip_address):
            """模拟登录尝试"""
            print(f"   登录尝试: {username} from {ip_address}")
            time.sleep(0.2)
            return True
            
        # 执行装饰器演示
        result1 = slow_database_query()
        result2 = external_api_call()
        
        update_user_profile("user123", {"email": "new@email.com", "name": "John Doe"})
        login_attempt("user123", "192.168.1.100")
        
        print("✅ 性能监控演示完成")
        
    def demo_advanced_search(self):
        """演示高级搜索功能"""
        print("\n🔍 演示高级搜索...")
        
        if not self.monitoring_system or not self.monitoring_system.query_engine:
            print("❌ 查询引擎未初始化")
            return
            
        # 等待一些日志写入
        time.sleep(2)
        
        # 搜索最近的日志
        query = LogQuery(
            start_time=datetime.now() - timedelta(minutes=10),
            end_time=datetime.now(),
            levels=["INFO", "WARNING", "ERROR"],
            limit=10
        )
        
        records = self.monitoring_system.search_logs(query)
        print(f"找到 {len(records)} 条匹配的日志记录")
        
        # 分析搜索结果
        if records:
            from agentbus_logging import analyze_logs
            analysis = analyze_logs(records)
            
            print(f"📊 搜索分析结果:")
            print(f"   总记录数: {analysis.total_count}")
            print(f"   级别分布: {analysis.level_distribution}")
            print(f"   Top日志器: {list(analysis.logger_distribution.keys())[:3]}")
        
        print("✅ 高级搜索演示完成")
        
    def demo_alert_system(self):
        """演示告警系统"""
        print("\n🚨 演示告警系统...")
        
        if not self.monitoring_system:
            print("❌ 监控系统未初始化")
            return
            
        # 手动触发告警
        self.monitoring_system.trigger_custom_alert(
            name="demo_alert",
            message="这是一个演示告警",
            level=AlertLevel.WARNING,
            extra_data={"demo": True, "component": "logging"}
        )
        
        # 触发性能相关告警
        self.monitoring_system.trigger_custom_alert(
            name="performance_alert",
            message="检测到性能问题",
            level=AlertLevel.ERROR,
            extra_data={"response_time": 5.2, "threshold": 2.0}
        )
        
        print("✅ 告警系统演示完成")
        
    def demo_error_analysis(self):
        """演示错误分析"""
        print("\n❌ 演示错误分析...")
        
        # 模拟生成一些错误日志
        error_logger = get_enhanced_logger("demo.error_generator")
        
        for i in range(5):
            error_logger.error("模拟错误", error_code=f"ERR_{i:03d}", 
                             message=f"这是第{i+1}个模拟错误")
            time.sleep(0.1)
            
        # 等待日志写入
        time.sleep(2)
        
        # 执行错误分析
        if self.monitoring_system and self.monitoring_system.query_engine:
            query = LogQuery(
                start_time=datetime.now() - timedelta(minutes=5),
                levels=["ERROR", "CRITICAL"],
                limit=100
            )
            
            records = self.monitoring_system.search_logs(query)
            
            if records:
                from agentbus_logging import ErrorAnalyzer
                analyzer = ErrorAnalyzer()
                error_analysis = analyzer.analyze_errors(records)
                
                print(f"🔍 错误分析结果:")
                print(f"   总错误数: {error_analysis['total_errors']}")
                print(f"   错误类型: {error_analysis['error_types']}")
                
        print("✅ 错误分析演示完成")
        
    def demo_storage_management(self):
        """演示存储管理"""
        print("\n💾 演示存储管理...")
        
        if not self.monitoring_system or not self.monitoring_system.storage:
            print("❌ 存储系统未初始化")
            return
            
        # 获取存储统计
        storage_stats = self.monitoring_system.storage.get_storage_stats()
        
        print(f"📊 存储统计:")
        print(f"   总段数: {storage_stats['total_segments']}")
        print(f"   总记录数: {storage_stats['total_records']}")
        print(f"   总大小: {storage_stats['total_size'] / 1024:.2f} KB")
        
        # 演示数据导出
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        export_file = f"{self.log_dir}/exported_logs.json"
        self.monitoring_system.export_logs(start_time, end_time, export_file, "json")
        
        if Path(export_file).exists():
            print(f"✅ 日志导出完成: {export_file}")
        else:
            print("❌ 日志导出失败")
            
        print("✅ 存储管理演示完成")
        
    def demo_analytics_report(self):
        """演示分析报告生成"""
        print("\n📈 演示分析报告生成...")
        
        # 创建查询引擎
        query_engine = create_query_engine([self.log_dir], f"{self.log_dir}/index")
        
        # 创建报告生成器
        from agentbus_logging import LogReporter
        reporter = LogReporter(query_engine)
        
        # 生成报告
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        try:
            report_result = reporter.generate_comprehensive_report(
                start_time, end_time, f"{self.log_dir}/reports"
            )
            
            print(f"📊 分析报告生成完成:")
            print(f"   JSON报告: {report_result.get('json_report', 'N/A')}")
            print(f"   HTML报告: {report_result.get('html_report', 'N/A')}")
            print(f"   图表文件: {len(report_result.get('chart_files', []))} 个")
            
        except Exception as e:
            print(f"❌ 报告生成失败: {e}")
            
        print("✅ 分析报告演示完成")
        
    def run_demo(self):
        """运行完整演示"""
        print("🎯 AgentBus增强日志监控系统演示")
        print("=" * 50)
        
        try:
            # 初始化
            self.initialize()
            
            # 演示各项功能
            self.demo_basic_logging()
            self.demo_correlation_tracking()
            self.demo_performance_monitoring()
            self.demo_advanced_search()
            self.demo_alert_system()
            self.demo_error_analysis()
            self.demo_storage_management()
            self.demo_analytics_report()
            
            # 显示系统状态
            print("\n📊 系统状态:")
            if self.monitoring_system:
                status = self.monitoring_system.get_system_status()
                print(f"   运行状态: {'运行中' if status['running'] else '已停止'}")
                print(f"   活跃告警: {status.get('active_alerts', 0)}")
                
                for component, enabled in status['components'].items():
                    print(f"   {component}: {'✅' if enabled else '❌'}")
            
            print("\n🎉 演示完成！")
            print(f"📁 查看日志文件: {self.log_dir}")
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ 演示过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            # 清理资源
            if self.monitoring_system:
                self.monitoring_system.stop()
                print("🧹 资源清理完成")


def main():
    """主函数"""
    # 创建并运行演示
    demo = EnhancedLoggingDemo()
    demo.run_demo()


if __name__ == "__main__":
    main()