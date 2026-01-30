"""
AgentBus日志分析工具集

提供丰富的日志分析、报告生成和可视化工具
"""

import os
import json
import re
import statistics
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd
import numpy as np
from jinja2 import Template

from .log_query import LogQuery, LogQueryEngine, LogAnalysisResult, create_query_engine, analyze_logs, create_visualizer


class LogPatternAnalyzer:
    """日志模式分析器"""
    
    def __init__(self):
        self.patterns = {
            'timestamp': r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
            'ipv4': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'uuid': r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'url': r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w)*)?)?',
            'json': r'\{.*\}',
            'exception': r'(Exception|Error|Traceback)',
            'stack_trace': r'File "[^"]+", line \d+, in',
            'duration': r'\d+\.?\d*\s*(ms|milliseconds?|s|seconds?|m|minutes?)',
            'file_size': r'\d+\.?\d*\s*(KB|MB|GB|TB)',
            'memory_usage': r'\d+\.?\d*\s*(MB|GB|KB)',
            'percentage': r'\d+\.?\d*%'
        }
        
    def analyze_patterns(self, messages: List[str]) -> Dict[str, Any]:
        """分析日志消息中的模式"""
        pattern_counts = {}
        pattern_examples = {}
        
        for pattern_name, pattern_regex in self.patterns.items():
            matches = []
            for message in messages:
                found_matches = re.findall(pattern_regex, message, re.IGNORECASE)
                if found_matches:
                    matches.extend(found_matches)
                    
            if matches:
                pattern_counts[pattern_name] = len(matches)
                pattern_examples[pattern_name] = list(set(matches))[:5]  # 前5个唯一示例
                
        return {
            "pattern_counts": pattern_counts,
            "pattern_examples": pattern_examples,
            "total_patterns_found": sum(pattern_counts.values())
        }


class ErrorAnalyzer:
    """错误分析器"""
    
    def __init__(self):
        self.error_keywords = [
            'exception', 'error', 'failed', 'timeout', 'refused', 'denied',
            'not found', 'invalid', 'corrupt', 'abort', 'crash', 'panic'
        ]
        
    def analyze_errors(self, log_records: List) -> Dict[str, Any]:
        """分析错误日志"""
        errors = []
        error_types = defaultdict(int)
        error_timeline = defaultdict(int)
        error_loggers = defaultdict(int)
        
        for record in log_records:
            if hasattr(record, 'level') and record.level in ['ERROR', 'CRITICAL']:
                # 检查是否为错误日志
                message_lower = record.message.lower()
                for keyword in self.error_keywords:
                    if keyword in message_lower:
                        errors.append({
                            'timestamp': record.timestamp,
                            'level': record.level,
                            'logger': record.logger,
                            'message': record.message[:200] + '...' if len(record.message) > 200 else record.message,
                            'error_type': keyword
                        })
                        error_types[keyword] += 1
                        
                        # 时间线分析
                        try:
                            dt = datetime.fromisoformat(record.timestamp.replace('Z', '+00:00'))
                            hour = dt.hour
                            error_timeline[hour] += 1
                        except:
                            pass
                            
                        error_loggers[record.logger] += 1
                        break
                        
        return {
            "total_errors": len(errors),
            "error_types": dict(error_types),
            "error_timeline": dict(error_timeline),
            "top_error_loggers": dict(sorted(error_loggers.items(), key=lambda x: x[1], reverse=True)[:10]),
            "recent_errors": errors[-10:]  # 最近10个错误
        }


class PerformanceAnalyzer:
    """性能分析器"""
    
    def analyze_performance_logs(self, log_records: List) -> Dict[str, Any]:
        """分析性能日志"""
        performance_logs = []
        response_times = []
        memory_usage = []
        cpu_usage = []
        
        for record in log_records:
            if hasattr(record, 'extra_fields') and record.extra_fields:
                fields = record.extra_fields
                
                # 提取响应时间
                if 'duration' in fields:
                    try:
                        duration = float(fields['duration'])
                        response_times.append(duration)
                        performance_logs.append({
                            'timestamp': record.timestamp,
                            'type': 'response_time',
                            'value': duration,
                            'logger': record.logger
                        })
                    except ValueError:
                        pass
                        
                # 提取内存使用
                if 'memory_usage' in fields:
                    try:
                        memory = float(fields['memory_usage'])
                        memory_usage.append(memory)
                        performance_logs.append({
                            'timestamp': record.timestamp,
                            'type': 'memory',
                            'value': memory,
                            'logger': record.logger
                        })
                    except ValueError:
                        pass
                        
                # 提取CPU使用
                if 'cpu_usage' in fields:
                    try:
                        cpu = float(fields['cpu_usage'])
                        cpu_usage.append(cpu)
                        performance_logs.append({
                            'timestamp': record.timestamp,
                            'type': 'cpu',
                            'value': cpu,
                            'logger': record.logger
                        })
                    except ValueError:
                        pass
                        
        # 统计分析
        analysis = {
            "total_performance_logs": len(performance_logs),
            "response_time_stats": self._calculate_stats(response_times, "response time"),
            "memory_stats": self._calculate_stats(memory_usage, "memory usage"),
            "cpu_stats": self._calculate_stats(cpu_usage, "cpu usage"),
            "performance_logs": performance_logs[-20:]  # 最近20条性能日志
        }
        
        return analysis
        
    def _calculate_stats(self, values: List[float], name: str) -> Dict[str, Any]:
        """计算统计信息"""
        if not values:
            return {f"{name}_stats": "No data available"}
            
        return {
            f"{name}_avg": statistics.mean(values),
            f"{name}_median": statistics.median(values),
            f"{name}_min": min(values),
            f"{name}_max": max(values),
            f"{name}_p95": self._percentile(values, 95),
            f"{name}_p99": self._percentile(values, 99),
            f"{name}_count": len(values)
        }
        
    def _percentile(self, data: List[float], percentile: int) -> float:
        """计算百分位数"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        return sorted_data[index]


class LogVisualizer:
    """日志可视化器"""
    
    def __init__(self, output_dir: str = "logs_analysis"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 设置matplotlib中文支持
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
    def generate_dashboard(self, analysis_result: LogAnalysisResult, 
                         error_analysis: Dict[str, Any],
                         performance_analysis: Dict[str, Any],
                         output_file: str = "dashboard.html") -> str:
        """生成分析报告面板"""
        
        # 创建HTML模板
        template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AgentBus 日志分析报告</title>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { text-align: center; color: #333; }
                .section { margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .metric { display: inline-block; margin: 10px; padding: 15px; background: #f5f5f5; border-radius: 5px; }
                .chart { margin: 20px 0; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                th { background-color: #f2f2f2; }
                .error { color: #d9534f; }
                .warning { color: #f0ad4e; }
                .success { color: #5cb85c; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔍 AgentBus 日志分析报告</h1>
                <p>生成时间: {{ timestamp }}</p>
            </div>
            
            <div class="section">
                <h2>📊 基本统计</h2>
                <div class="metric">
                    <strong>总日志数:</strong> {{ analysis.total_count }}
                </div>
                <div class="metric">
                    <strong>时间范围:</strong> {{ analysis.time_range[0] if analysis.time_range[0] else 'N/A' }} 到 {{ analysis.time_range[1] if analysis.time_range[1] else 'N/A' }}
                </div>
            </div>
            
            <div class="section">
                <h2>📈 日志级别分布</h2>
                <table>
                    <tr><th>级别</th><th>数量</th><th>占比</th></tr>
                    {% for level, count in analysis.level_distribution.items() %}
                    <tr>
                        <td>{{ level }}</td>
                        <td>{{ count }}</td>
                        <td>{{ "%.1f%%"|format((count / analysis.total_count * 100) if analysis.total_count > 0 else 0) }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            
            <div class="section">
                <h2>🏷️ Top 10 日志器</h2>
                <table>
                    <tr><th>日志器</th><th>日志数</th><th>占比</th></tr>
                    {% for logger, count in analysis.logger_distribution.items()[:10] %}
                    <tr>
                        <td>{{ logger }}</td>
                        <td>{{ count }}</td>
                        <td>{{ "%.1f%%"|format((count / analysis.total_count * 100) if analysis.total_count > 0 else 0) }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            
            {% if analysis.error_patterns %}
            <div class="section">
                <h2>❌ 错误模式分析</h2>
                <table>
                    <tr><th>模式</th><th>出现次数</th><th>示例</th></tr>
                    {% for pattern in analysis.error_patterns[:10] %}
                    <tr class="error">
                        <td>{{ pattern.pattern }}</td>
                        <td>{{ pattern.count }}</td>
                        <td>
                            {% for example in pattern.examples[:3] %}
                            <div>{{ example.timestamp }} - {{ example.message[:100] }}...</div>
                            {% endfor %}
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            {% endif %}
            
            {% if performance_analysis %}
            <div class="section">
                <h2>⚡ 性能分析</h2>
                {% if performance_analysis.response_time_stats %}
                <h3>响应时间统计</h3>
                <table>
                    <tr><th>指标</th><th>值</th></tr>
                    {% for key, value in performance_analysis.response_time_stats.items() %}
                    <tr><td>{{ key }}</td><td>{{ "%.3f"|format(value) if value is number else value }}</td></tr>
                    {% endfor %}
                </table>
                {% endif %}
            </div>
            {% endif %}
            
            {% if error_analysis %}
            <div class="section">
                <h2>🚨 错误分析</h2>
                <div class="metric">
                    <strong>总错误数:</strong> {{ error_analysis.total_errors }}
                </div>
                <h3>错误类型分布</h3>
                <table>
                    <tr><th>错误类型</th><th>数量</th></tr>
                    {% for error_type, count in error_analysis.error_types.items() %}
                    <tr class="error"><td>{{ error_type }}</td><td>{{ count }}</td></tr>
                    {% endfor %}
                </table>
            </div>
            {% endif %}
            
            <div class="section">
                <h2>📋 详细分析</h2>
                <p>此报告由 AgentBus 增强日志监控系统自动生成。</p>
                <p>包含 {{ analysis.total_count }} 条日志记录的分析结果。</p>
            </div>
        </body>
        </html>
        """)
        
        # 生成报告
        output_path = self.output_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template.render(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                analysis=analysis_result,
                error_analysis=error_analysis,
                performance_analysis=performance_analysis
            ))
            
        return str(output_path)
        
    def create_charts(self, analysis_result: LogAnalysisResult, 
                     error_analysis: Dict[str, Any],
                     output_prefix: str = "charts") -> List[str]:
        """创建分析图表"""
        chart_files = []
        
        # 1. 日志级别分布饼图
        if analysis_result.level_distribution:
            plt.figure(figsize=(10, 8))
            levels = list(analysis_result.level_distribution.keys())
            counts = list(analysis_result.level_distribution.values())
            
            plt.pie(counts, labels=levels, autopct='%1.1f%%', startangle=90)
            plt.title('日志级别分布')
            plt.axis('equal')
            
            chart_file = self.output_dir / f"{output_prefix}_level_distribution.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            chart_files.append(str(chart_file))
            plt.close()
            
        # 2. 日志器分布条形图
        if analysis_result.logger_distribution:
            plt.figure(figsize=(12, 8))
            top_loggers = dict(list(analysis_result.logger_distribution.items())[:10])
            loggers = list(top_loggers.keys())
            counts = list(top_loggers.values())
            
            plt.barh(loggers, counts)
            plt.title('Top 10 日志器分布')
            plt.xlabel('日志数量')
            plt.tight_layout()
            
            chart_file = self.output_dir / f"{output_prefix}_logger_distribution.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            chart_files.append(str(chart_file))
            plt.close()
            
        # 3. 按小时分布
        if analysis_result.hourly_distribution:
            plt.figure(figsize=(12, 6))
            hours = list(analysis_result.hourly_distribution.keys())
            counts = list(analysis_result.hourly_distribution.values())
            
            plt.plot(hours, counts, marker='o', linewidth=2, markersize=6)
            plt.title('24小时日志分布')
            plt.xlabel('小时')
            plt.ylabel('日志数量')
            plt.xticks(range(24))
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            chart_file = self.output_dir / f"{output_prefix}_hourly_distribution.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            chart_files.append(str(chart_file))
            plt.close()
            
        # 4. 错误分析图表
        if error_analysis.get('error_timeline'):
            plt.figure(figsize=(12, 6))
            hours = list(error_analysis['error_timeline'].keys())
            errors = list(error_analysis['error_timeline'].values())
            
            plt.bar(hours, errors, color='red', alpha=0.7)
            plt.title('24小时错误分布')
            plt.xlabel('小时')
            plt.ylabel('错误数量')
            plt.xticks(range(24))
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            chart_file = self.output_dir / f"{output_prefix}_error_timeline.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            chart_files.append(str(chart_file))
            plt.close()
            
        return chart_files


class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self, window_size: int = 100, threshold: float = 2.0):
        self.window_size = window_size
        self.threshold = threshold
        
    def detect_log_volume_anomalies(self, hourly_distribution: Dict[int, int]) -> List[Dict[str, Any]]:
        """检测日志量异常"""
        hours = sorted(hourly_distribution.keys())
        volumes = [hourly_distribution[h] for h in hours]
        
        anomalies = []
        
        # 使用滑动窗口检测异常
        for i in range(self.window_size, len(volumes)):
            window = volumes[i-self.window_size:i]
            current_volume = volumes[i]
            
            # 计算窗口统计信息
            mean_volume = statistics.mean(window)
            std_volume = statistics.stdev(window) if len(window) > 1 else 0
            
            # 检测异常
            if std_volume > 0:
                z_score = abs(current_volume - mean_volume) / std_volume
                if z_score > self.threshold:
                    anomalies.append({
                        "hour": hours[i],
                        "volume": current_volume,
                        "expected": mean_volume,
                        "z_score": z_score,
                        "type": "high" if current_volume > mean_volume else "low"
                    })
                    
        return anomalies
        
    def detect_error_rate_anomalies(self, error_data: Dict[int, int]) -> List[Dict[str, Any]]:
        """检测错误率异常"""
        return self.detect_log_volume_anomalies(error_data)
        
    def detect_performance_anomalies(self, performance_data: List[float]) -> List[Dict[str, int]]:
        """检测性能异常"""
        if len(performance_data) < self.window_size:
            return []
            
        anomalies = []
        
        for i in range(self.window_size, len(performance_data)):
            window = performance_data[i-self.window_size:i]
            current_value = performance_data[i]
            
            mean_val = statistics.mean(window)
            std_val = statistics.stdev(window) if len(window) > 1 else 0
            
            if std_val > 0:
                z_score = abs(current_value - mean_val) / std_val
                if z_score > self.threshold:
                    anomalies.append({
                        "index": i,
                        "value": current_value,
                        "expected": mean_val,
                        "z_score": z_score,
                        "type": "high" if current_value > mean_val else "low"
                    })
                    
        return anomalies


class LogReporter:
    """日志报告生成器"""
    
    def __init__(self, query_engine: LogQueryEngine):
        self.query_engine = query_engine
        self.pattern_analyzer = LogPatternAnalyzer()
        self.error_analyzer = ErrorAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()
        self.anomaly_detector = AnomalyDetector()
        self.visualizer = LogVisualizer()
        
    def generate_comprehensive_report(self, 
                                    start_time: datetime,
                                    end_time: datetime,
                                    output_dir: str = "reports") -> Dict[str, str]:
        """生成综合分析报告"""
        
        # 1. 查询日志数据
        query = LogQuery(
            start_time=start_time,
            end_time=end_time,
            limit=10000  # 限制查询数量
        )
        
        log_records = self.query_engine.query(query)
        
        if not log_records:
            return {"error": "没有找到匹配的日志记录"}
            
        # 2. 执行各项分析
        print("正在执行日志分析...")
        analysis_result = analyze_logs(log_records)
        print("基本分析完成")
        
        print("正在分析错误模式...")
        error_analysis = self.error_analyzer.analyze_errors(log_records)
        print("错误分析完成")
        
        print("正在分析性能数据...")
        performance_analysis = self.performance_analyzer.analyze_performance_logs(log_records)
        print("性能分析完成")
        
        # 3. 异常检测
        print("正在检测异常...")
        log_anomalies = self.anomaly_detector.detect_log_volume_anomalies(
            analysis_result.hourly_distribution
        )
        error_anomalies = self.anomaly_detector.detect_error_rate_anomalies(
            error_analysis.get('error_timeline', {})
        )
        print("异常检测完成")
        
        # 4. 生成报告
        print("正在生成报告...")
        
        # 生成详细JSON报告
        json_report = {
            "metadata": {
                "report_type": "comprehensive",
                "generated_at": datetime.utcnow().isoformat(),
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "total_records": len(log_records)
            },
            "analysis": asdict(analysis_result),
            "error_analysis": error_analysis,
            "performance_analysis": performance_analysis,
            "anomalies": {
                "log_volume": log_anomalies,
                "error_rate": error_anomalies
            }
        }
        
        # 保存JSON报告
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        json_file = output_path / f"report_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(json_report, f, indent=2, ensure_ascii=False)
            
        # 生成HTML报告
        html_file = self.visualizer.generate_dashboard(
            analysis_result,
            error_analysis,
            performance_analysis,
            f"dashboard_{start_time.strftime('%Y%m%d_%H%M%S')}.html"
        )
        
        # 生成图表
        chart_files = self.visualizer.create_charts(
            analysis_result,
            error_analysis,
            f"charts_{start_time.strftime('%Y%m%d_%H%M%S')}"
        )
        
        return {
            "json_report": str(json_file),
            "html_report": html_file,
            "chart_files": chart_files,
            "summary": {
                "total_records": len(log_records),
                "total_errors": error_analysis.get('total_errors', 0),
                "anomalies_detected": len(log_anomalies) + len(error_anomalies),
                "report_files": [str(json_file), html_file] + chart_files
            }
        }


# 便捷函数
def quick_log_analysis(log_dirs: List[str], start_time: datetime, end_time: datetime,
                     output_dir: str = "quick_analysis") -> Dict[str, Any]:
    """快速日志分析"""
    query_engine = create_query_engine(log_dirs, "/tmp/logs/index")
    reporter = LogReporter(query_engine)
    return reporter.generate_comprehensive_report(start_time, end_time, output_dir)


def detect_log_anomalies(log_records: List) -> Dict[str, Any]:
    """检测日志异常"""
    analyzer = AnomalyDetector()
    
    # 模拟小时分布数据
    hourly_dist = defaultdict(int)
    for record in log_records:
        try:
            dt = datetime.fromisoformat(record.timestamp.replace('Z', '+00:00'))
            hourly_dist[dt.hour] += 1
        except:
            pass
            
    # 模拟错误数据
    error_dist = defaultdict(int)
    for record in log_records:
        if hasattr(record, 'level') and record.level in ['ERROR', 'CRITICAL']:
            try:
                dt = datetime.fromisoformat(record.timestamp.replace('Z', '+00:00'))
                error_dist[dt.hour] += 1
            except:
                pass
    
    return {
        "log_volume_anomalies": analyzer.detect_log_volume_anomalies(dict(hourly_dist)),
        "error_rate_anomalies": analyzer.detect_error_rate_anomalies(dict(error_dist))
    }