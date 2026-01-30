---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 30460221009bb107a70c908fceb90d9ca67a7169b083d3689e6ca3e5cde92fc33262591ce602210095757f24c25a5a93a5a307e6684d7e269775d7c82610cf51553d74f6abf28c00
    ReservedCode2: 3046022100c1ab710a68f5fab9b44aa7d39ab4ef379aa4624d14fc563238a218f121d5eca5022100cee859592868c05c13513a66c7cd05dd175279819d808d3f35e7a9469ab39dd1
---

# AgentBus 基础设施系统

基于Moltbot的Infrastructure系统，提供完整的基础设施功能模块。

## 系统架构

AgentBus基础设施系统包含以下核心模块：

### 1. 网络管理 (net)
提供安全的网络连接和监控功能。

**主要功能：**
- SSRF (Server Side Request Forgery) 攻击防护
- 网络连接监控和统计
- 网络接口管理
- 连接性测试
- 安全URL验证

**核心类：**
- `SsrFProtection`: SSRF保护机制
- `NetworkManager`: 网络连接管理器
- `NetworkConfig`: 网络配置

**使用示例：**
```python
from agentbus.infrastructure.net import NetworkManager, SsrFProtection

# 创建SSRF保护
ssrf_protection = SsrFProtection()

# 检查URL安全性
is_safe = ssrf_protection.is_safe_url("https://example.com")
if not is_safe:
    raise SecurityError("URL is not safe")

# 创建网络管理器
network_manager = NetworkManager(ssrf_protection)

# 获取网络接口信息
interfaces = await network_manager.get_network_interfaces()

# 测试连接性
connectivity = await network_manager.test_connectivity("8.8.8.8", 53)
```

### 2. 文件系统管理 (filesystem)
提供文件操作、目录管理和存档功能。

**主要功能：**
- 文件和目录操作
- 文件信息获取和统计
- 文件搜索和过滤
- 存档创建和管理（ZIP/TAR）
- 磁盘使用监控

**核心类：**
- `FileSystemManager`: 文件系统管理器
- `ArchiveManager`: 存档管理器
- `ArchiveKind`: 存档类型枚举

**使用示例：**
```python
from agentbus.infrastructure.filesystem import FileSystemManager, ArchiveManager

# 创建文件系统管理器
fs_manager = FileSystemManager()

# 获取文件信息
file_info = await fs_manager.get_file_info("path/to/file.txt")

# 列出目录内容
contents = await fs_manager.list_directory("path/to/dir")

# 搜索文件
files = await fs_manager.search_files("*.py")

# 创建存档
archive_manager = ArchiveManager()
await archive_manager.create_archive(
    source_path="source/dir",
    archive_path="backup.zip",
    kind=ArchiveKind.ZIP
)
```

### 3. 进程管理 (process)
提供进程监控、控制和二进制管理功能。

**主要功能：**
- 进程信息获取和监控
- 进程启动、停止、暂停
- 进程树显示
- 系统资源使用统计
- 二进制文件检测和管理
- 进程性能指标收集

**核心类：**
- `ProcessManager`: 进程管理器
- `BinaryManager`: 二进制管理器
- `ProcessInfo`: 进程信息类
- `ProcessState`: 进程状态枚举

**使用示例：**
```python
from agentbus.infrastructure.process import ProcessManager, BinaryManager

# 创建进程管理器
process_manager = ProcessManager()

# 获取所有进程
processes = await process_manager.list_processes(limit=10)

# 获取进程信息
process_info = await process_manager.get_process_info(pid=1234)

# 创建二进制管理器
binary_manager = BinaryManager()

# 检查必需二进制文件
binary_manager.add_required_binary("python")
status = await binary_manager.check_required_binaries()
```

### 4. 系统监控 (monitoring)
提供诊断事件、性能监控和系统指标功能。

**主要功能：**
- 诊断事件管理和记录
- 系统性能指标收集
- 告警规则和通知
- 健康检查和诊断扫描
- 实时监控和历史数据分析

**核心类：**
- `MonitoringManager`: 监控管理器
- `DiagnosticEvents`: 诊断事件管理器
- `SystemMetrics`: 系统指标类
- `AlertRule`: 告警规则类

**使用示例：**
```python
from agentbus.infrastructure.monitoring import MonitoringManager
from agentbus.infrastructure.monitoring.system_metrics import AlertRule

# 创建监控管理器
monitoring_manager = MonitoringManager()

# 添加自定义告警规则
monitoring_manager.add_alert_rule(AlertRule(
    name="high_cpu",
    metric="cpu_percent",
    operator=">",
    threshold=80.0,
    severity="WARNING",
    duration_seconds=60
))

# 开始监控
await monitoring_manager.start_monitoring(
    metrics_interval=5.0,
    process_monitoring=True,
    network_monitoring=True
)

# 获取当前指标
current_metrics = monitoring_manager.get_current_metrics()

# 发出自定义事件
monitoring_manager.emit_custom_event(
    DiagnosticEventType.SYSTEM_INFO,
    source="my_app",
    message="Application started",
    data={"version": "1.0"}
)
```

### 5. 设备管理 (device)
提供设备身份、配对管理和设备发现功能。

**主要功能：**
- 设备身份和密钥管理
- 设备发现和配对
- 设备状态监控
- 设备信息管理
- 安全通信

**核心类：**
- `DeviceManager`: 设备管理器
- `DeviceIdentityManager`: 设备身份管理器
- `DeviceInfo`: 设备信息类
- `DeviceType`: 设备类型枚举

**使用示例：**
```python
from agentbus.infrastructure.device import DeviceManager, DeviceType

# 创建设备管理器
device_manager = DeviceManager()

# 创建设备身份
device_info = await device_manager.create_device(
    device_name="MyAgent",
    device_type=DeviceType.AGENT,
    capabilities=["monitoring", "communication"]
)

# 搜索附近设备
discovered = await device_manager.discover_devices(timeout=10.0)

# 配对设备
await device_manager.pair_device(device_id)

# 获取设备 device_manager.get_device_statistics()
```

## 综合使用示例统计
stats =

```python
import asyncio
from agentbus.infrastructure import (
    NetworkManager, FileSystemManager, ProcessManager,
    MonitoringManager, DeviceManager
)

async def infrastructure_demo():
    """基础设施系统演示"""
    
    # 创建监控管理器（整合所有功能）
    monitoring_manager = MonitoringManager()
    
    # 开始全面监控
    await monitoring_manager.start_monitoring(
        metrics_interval=5.0,
        process_monitoring=True,
        network_monitoring=True
    )
    
    # 创建设备
    device_manager = DeviceManager()
    device = await device_manager.create_device(
        device_name="AgentBus Demo",
        device_type=DeviceType.SERVER
    )
    
    # 文件系统管理
    fs_manager = FileSystemManager()
    await fs_manager.create_directory("demo_data")
    await fs_manager.write_file("demo_data/info.txt", "Infrastructure demo")
    
    # 等待收集数据
    await asyncio.sleep(10)
    
    # 获取统计信息
    stats = monitoring_manager.get_system_statistics()
    print(f"系统统计: {stats}")
    
    # 停止监控
    await monitoring_manager.stop_monitoring()

# 运行演示
asyncio.run(infrastructure_demo())
```

## 配置和扩展

### 自定义告警规则
```python
from agentbus.infrastructure.monitoring.system_metrics import AlertRule

# 添加自定义告警
monitoring_manager.add_alert_rule(AlertRule(
    name="memory_leak",
    metric="memory_percent",
    operator=">",
    threshold=95.0,
    severity="CRITICAL",
    duration_seconds=120
))
```

### 网络安全配置
```python
from agentbus.infrastructure.net import NetworkConfig, SsrFProtection

# 自定义网络配置
config = NetworkConfig(
    blocked_hostnames={"example.com", "malicious.local"},
    blocked_domains={".internal", ".corp"},
    allowed_public_only=True
)

ssrf_protection = SsrFProtection(config)
```

### 监控事件过滤
```python
from agentbus.infrastructure.monitoring.diagnostic_events import EventFilter, DiagnosticEventType

# 创建事件过滤器
filter_obj = EventFilter(
    event_types=[DiagnosticEventType.SYSTEM_ERROR, DiagnosticEventType.CPU_USAGE_HIGH],
    severities=["WARNING", "ERROR"],
    start_time=datetime.now() - timedelta(hours=1)
)

# 获取过滤后的事件
events = monitoring_manager.get_events(filter_obj=filter_obj)
```

## 最佳实践

### 1. 错误处理
始终使用try-catch包装基础设施调用，并适当记录错误：
```python
try:
    metrics = await monitoring_manager.get_current_metrics()
except Exception as e:
    monitoring_manager.emit_custom_event(
        DiagnosticEventType.SYSTEM_ERROR,
        "my_app",
        f"Failed to get metrics: {str(e)}"
    )
```

### 2. 性能优化
- 合理设置监控间隔（推荐5-30秒）
- 定期清理历史数据
- 使用异步操作避免阻塞

### 3. 安全考虑
- 启用SSRF保护
- 限制文件系统访问权限
- 安全存储设备密钥

### 4. 监控建议
- 设置合理的告警阈值
- 定期执行健康检查
- 监控关键业务指标

## 依赖项

基础设施系统需要以下依赖：
- `psutil`: 系统和进程监控
- `aiohttp`: 异步HTTP操作
- `cryptography`: 加密功能
- `pathlib`: 路径操作
- `asyncio`: 异步编程

## 注意事项

1. **权限要求**: 某些功能可能需要管理员权限
2. **跨平台支持**: 部分功能在不同操作系统上可能有差异
3. **资源消耗**: 监控功能会消耗一定的系统资源
4. **数据持久化**: 历史数据和配置需要定期备份

## 故障排除

### 常见问题

1. **权限错误**
   ```bash
   # Linux/macOS
   sudo chown -R $USER:$USER ~/.agentbus
   
   # Windows
   # 以管理员身份运行
   ```

2. **网络连接失败**
   - 检查防火墙设置
   - 验证网络配置
   - 确认SSRF保护设置

3. **监控数据丢失**
   - 检查磁盘空间
   - 验证日志文件权限
   - 查看错误事件

### 调试模式
启用详细日志记录：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 扩展和自定义

基础设施系统设计为模块化和可扩展的，可以根据需要添加新的监控指标、告警规则和设备类型。

---

更多详细信息和API参考，请参阅各模块的源代码注释和类型定义。