---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 3046022100feae271b190a89f07432e7a379f2558e80c13e6b53395f715377af9e3ecde8f8022100e0acfba84479c5936791a60726c628de156da5bdf9a26ead9311c84908a28ea9
    ReservedCode2: 3044022039a2b0e2ba0b2410be31b5c5dec4d7ab40690a606bc3f6539154db00ac1f7c3e022039ba4ee1f8b54bd31a9372a761317c70171f19ee1886465a91bf2312829548ef
---

# AgentBus日志和监控系统

基于Moltbot日志系统设计的完整日志管理解决方案，为AgentBus提供全面的日志记录、性能监控和告警功能。

## 🚀 功能特性

### 📝 结构化日志记录
- **多格式支持**: JSON、文本、彩色、紧凑格式
- **多输出目标**: 文件、控制台、自定义传输
- **结构化数据**: 线程ID、进程ID、调用栈信息
- **日志级别**: DEBUG、INFO、WARNING、ERROR、CRITICAL

### 📊 性能指标监控
- **系统指标**: CPU、内存、磁盘、网络使用情况
- **应用指标**: 请求统计、响应时间、错误率
- **自定义指标**: 计数器、仪表盘、直方图、计时器
- **历史数据**: 保存1小时内的详细指标数据
- **统计计算**: 平均值、百分位数、最值统计

### 🚨 智能告警系统
- **多级告警**: INFO、WARNING、ERROR、CRITICAL
- **灵活规则**: 阈值、变化率、统计分析
- **多种通知**: 邮件、Webhook、Slack等
- **告警抑制**: 避免重复告警和告警风暴
- **告警历史**: 完整的告警记录和状态跟踪

### 🔄 日志管理
- **自动轮转**: 按大小和时间自动轮转日志文件
- **压缩存储**: 自动压缩历史日志文件
- **定时清理**: 定期清理过期日志文件
- **高性能**: 异步写入，不阻塞主业务逻辑

## 📁 模块结构

```
agentbus/logging/
├── __init__.py           # 模块初始化和便捷接口
├── log_manager.py        # 日志管理器核心
├── metrics.py           # 性能指标系统
├── alerting.py          # 告警管理系统
└── demo_logging_system.py  # 功能演示脚本
```

## 🔧 快速开始

### 1. 基本初始化

```python
from agentbus.logging import initialize_logging

# 初始化日志系统
initialize_logging(
    log_dir="/var/log/agentbus",
    level="INFO",
    format_type="json",
    enable_metrics=True,
    enable_alerting=True,
)
```

### 2. 使用日志记录器

```python
from agentbus.logging import get_logger

# 获取主日志记录器
logger = get_logger("my_app")
logger.info("应用启动", version="1.0.0", port=8080)

# 获取子日志记录器
api_logger = get_child_logger("my_app", "api")
api_logger.debug("API调用", endpoint="/users", method="GET")
```

### 3. 监控指标

```python
from agentbus.logging import increment_metric, set_metric, record_time

# 计数器
increment_metric("requests_total", 1, {"endpoint": "/api/users"})

# 仪表盘
set_metric("active_connections", current_connections)

# 计时器
import time
start = time.time()
# ... 执行代码 ...
duration = time.time() - start
record_time("processing_time", duration)
```

### 4. 配置告警

```python
from agentbus.logging import get_alert_manager, AlertRule, AlertLevel, AlertRuleType
from agentbus.logging import create_email_channel, create_webhook_channel

# 创建告警管理器
alert_manager = get_alert_manager()

# 添加通知渠道
email_channel = create_email_channel(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    username="your-email@gmail.com",
    password="your-password",
    from_email="alerts@agentbus.com",
    to_emails=["admin@company.com"]
)
alert_manager.add_notification_channel(email_channel)

# 添加告警规则
rule = AlertRule(
    name="high_cpu",
    description="CPU使用率过高",
    level=AlertLevel.WARNING,
    rule_type=AlertRuleType.THRESHOLD,
    metric_name="cpu_percent",
    condition=">",
    threshold=80.0,
    evaluation_window=300,
    cooldown_period=600
)
alert_manager.add_rule(rule)

# 手动触发告警
alert_manager.trigger_alert(
    rule_name="high_cpu",
    message="CPU使用率达到85%",
    metric_name="cpu_percent",
    metric_value=85.0
)
```

## 📖 详细文档

### 日志格式

#### JSON格式（推荐）
```json
{
  "timestamp": "2024-01-01T12:00:00.123Z",
  "level": "INFO",
  "logger": "my_app",
  "message": "用户登录成功",
  "module": "/app/main.py",
  "function": "login_handler",
  "line": 45,
  "thread_id": 1234,
  "process_id": 5678,
  "extra_fields": {
    "user_id": 12345,
    "ip_address": "192.168.1.1"
  }
}
```

#### 彩色控制台格式
```
12:00:00 INFO     my_app          /app/main.py:login_handler:45 - 用户登录成功 [user_id=12345]
```

### 指标类型

1. **计数器 (COUNTER)**: 递增的数值，用于统计总数
2. **仪表盘 (GAUGE)**: 可上下变化的数值，表示当前状态
3. **直方图 (HISTOGRAM)**: 记录数值分布
4. **计时器 (TIMER)**: 记录时间间隔

### 告警规则类型

1. **阈值告警 (THRESHOLD)**: 基于固定阈值的告警
2. **变化率告警 (CHANGE_RATE)**: 基于数值变化率的告警
3. **统计告警 (STATISTICAL)**: 基于统计特性的告警（如离群值）

### 告警通知渠道

- **邮件通知**: 支持SMTP服务器配置
- **Webhook**: HTTP POST请求通知
- **Slack**: Slack Webhook集成
- **自定义**: 继承`NotificationChannel`类实现

## 🛠️ 配置选项

### 日志配置

```python
configure_logging(
    log_dir="/var/log/agentbus",        # 日志目录
    level="INFO",                      # 日志级别
    format_type="json",                # 日志格式
    max_file_size=100*1024*1024,       # 最大文件大小 (100MB)
    backup_count=10,                   # 备份文件数量
    retention_days=30,                 # 保留天数
    enable_console=True,               # 启用控制台输出
    enable_file=True,                  # 启用文件输出
    enable_compression=True,           # 启用压缩
)
```

### 指标收集配置

```python
metrics_collector = MetricsCollector(
    collection_interval=1.0  # 收集间隔（秒）
)
```

### 告警配置

```python
# 告警抑制规则
alert_manager.add_suppression_rule("cooldown_rule", {
    "type": "cooldown",
    "cooldown_seconds": 300  # 5分钟冷却期
})
```

## 📊 监控指标

### 系统指标
- CPU使用率
- 内存使用率和使用量
- 磁盘使用率
- 网络IO统计
- 进程和线程数量

### 应用指标
- 请求总数和错误数
- 响应时间统计（平均值、P95、P99）
- 活跃连接数
- 排队和处理中的任务数

## 🔍 故障排查

### 常见问题

1. **日志文件权限问题**
   ```bash
   sudo chown -R agentbus:agentbus /var/log/agentbus
   sudo chmod 755 /var/log/agentbus
   ```

2. **邮件发送失败**
   - 检查SMTP服务器配置
   - 验证用户名密码
   - 确认防火墙设置

3. **指标收集异常**
   - 检查psutil库是否正确安装
   - 确认系统权限足够

### 日志级别说明

- **DEBUG**: 详细的调试信息
- **INFO**: 一般信息记录
- **WARNING**: 警告信息，可能影响性能
- **ERROR**: 错误信息，功能可能受影响
- **CRITICAL**: 严重错误，可能导致系统崩溃

## 📈 性能优化

1. **日志级别调优**: 生产环境使用INFO或WARNING级别
2. **文件轮转设置**: 根据磁盘空间合理设置保留天数
3. **指标采样**: 高频指标考虑采样或降频收集
4. **异步处理**: 指标收集和告警检查在后台线程执行

## 🔒 安全考虑

1. **敏感信息过滤**: 日志中避免记录密码、Token等敏感信息
2. **文件权限**: 确保日志文件权限设置合适
3. **网络传输**: Webhook和邮件传输使用加密连接
4. **访问控制**: 限制对日志文件和监控数据的访问

## 🤝 扩展开发

### 自定义日志传输

```python
from agentbus.logging import LogTransport, LogRecord

class DatabaseTransport(LogTransport):
    def __init__(self):
        super().__init__("database")
        # 初始化数据库连接
    
    def write(self, record: LogRecord):
        # 将日志记录写入数据库
        pass
```

### 自定义告警规则

```python
from agentbus.logging import AlertRuleType

class CustomRuleType(AlertRuleType):
    ANOMALY_DETECTION = "anomaly_detection"
```

## 📞 技术支持

如有问题或建议，请通过以下方式联系：
- 查看演示脚本: `demo_logging_system.py`
- 检查日志文件: `/tmp/agentbus/logs/`
- 查看指标数据: 导出的JSON文件

---

*AgentBus日志和监控系统 - 为您的应用提供全方位的监控保障*