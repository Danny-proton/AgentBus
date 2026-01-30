---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 3046022100b9069855dfa3e54bc8966b72dc7c74934093c3d1122e6f6b0679e88edf9c5626022100fca388d0038a4ee5a11f7e74f2de7b61785bd114f83a96068c23ae74d0ceba8c
    ReservedCode2: 30450221009ffadd4e758baa98d481772be8e6b904f645f3ab8297588025bef400af5c1821022022d80317c7ddac96a60d79ec3b5c33692e665258db37d40dd0871be30cf52b7a
---

# AgentBus 守护进程系统

AgentBus 守护进程是一个跨平台的服务管理系统，支持 Linux (systemd)、macOS (launchd) 和 Windows (Task Scheduler)。

## 特性

- 🚀 **跨平台支持**: Linux (systemd)、macOS (launchd)、Windows (Task Scheduler)
- 🔧 **完整的服务管理**: 安装、卸载、启动、停止、重启
- 📊 **实时监控**: 服务状态监控、健康检查、资源使用监控
- ⚙️ **灵活配置**: 支持配置文件和环境变量配置
- 🛠️ **命令行工具**: 完整的 CLI 管理工具
- 🔍 **诊断工具**: 系统诊断和故障排除
- 📝 **详细日志**: 结构化日志记录

## 安装

```bash
npm install @agentbus/daemon
```

## 快速开始

### 作为库使用

```typescript
import { AgentBusDaemon, AgentBusServiceManager } from '@agentbus/daemon';

// 创建守护进程实例
const daemon = new AgentBusDaemon();

// 初始化
await daemon.initialize();

// 安装服务
await daemon.installService({
  executablePath: '/path/to/your/app',
  arguments: ['--config', '/path/to/config.json'],
  description: 'My Application Service'
});

// 启动守护进程
await daemon.start();
```

### 作为命令行工具使用

```bash
# 安装服务
agentbus-daemon install /usr/local/bin/myapp --args "--config=/etc/myapp.json"

# 启动守护进程
agentbus-daemon start

# 查看状态
agentbus-daemon status

# 停止服务
agentbus-daemon stop

# 健康检查
agentbus-daemon health
```

## 平台支持

| 平台 | 服务管理器 | 状态 | 说明 |
|------|------------|------|------|
| Linux | systemd | ✅ 完全支持 | 推荐使用 |
| macOS | launchd | ✅ 完全支持 | 原生支持 |
| Windows | Task Scheduler | ✅ 完全支持 | 原生支持 |

## 目录结构

```
agentbus/daemon/
├── types.ts           # 类型定义
├── constants.ts       # 常量定义
├── paths.ts          # 路径处理工具
├── service-manager.ts # 跨平台服务管理器
├── systemd.ts        # Linux systemd 实现
├── launchd.ts        # macOS launchd 实现
├── schtasks.ts       # Windows Task Scheduler 实现
├── config.ts         # 配置管理
├── monitor.ts        # 监控和健康检查
├── daemon.ts         # 主守护进程类
├── cli.ts           # 命令行接口
├── utils.ts         # 工具函数
├── index.ts         # 主入口
└── package.json     # 包配置
```

## API 文档

### AgentBusDaemon

主要的守护进程管理类。

```typescript
const daemon = new AgentBusDaemon();

// 初始化
await daemon.initialize();

// 服务管理
await daemon.installService({
  executablePath: string,
  arguments?: string[],
  workingDirectory?: string,
  environment?: Record<string, string>,
  description?: string,
  serviceName?: string
});

await daemon.startService();
await daemon.stopService();
await daemon.restartService();

// 状态查询
const status = await daemon.getDaemonStatus();
const health = await daemon.performHealthCheck();

// 配置管理
await daemon.updateConfig(configUpdates);
const config = daemon.getConfig();
```

### AgentBusServiceManager

跨平台服务管理器。

```typescript
const manager = new AgentBusServiceManager();

// 检查平台支持
const platformInfo = manager.getPlatformInfo();

// 服务操作
await manager.install(args);
await manager.uninstall(args);
await manager.start(args);
await manager.stop(args);
await manager.restart(args);

// 状态查询
const isLoaded = await manager.isLoaded();
const runtime = await manager.readRuntime();
```

### ConfigManager

配置管理器。

```typescript
const configManager = new ConfigManager();

// 加载和保存
await configManager.load();
await configManager.save();

// 配置操作
const config = configManager.getConfig();
configManager.updateConfig(updates);

// 验证
const validation = configManager.validate();
```

### ServiceMonitor

服务监控器。

```typescript
const monitor = new ServiceMonitor(
  manager,
  monitoringConfig,
  (status) => console.log('状态更新:', status),
  (error) => console.error('监控错误:', error)
);

// 启动监控
await monitor.start();
monitor.stop();

// 状态查询
const status = monitor.getStatus();
```

## 配置

### 配置文件

默认配置文件位置：
- Linux: `~/.config/agentbus/config.json`
- macOS: `~/Library/Application Support/AgentBus/config.json`
- Windows: `%USERPROFILE%\AgentBus\config.json`

### 配置示例

```json
{
  "name": "agentbus",
  "displayName": "AgentBus Agent Communication Service",
  "description": "AgentBus守护进程服务",
  "executablePath": "/usr/local/bin/agentbus",
  "arguments": ["--config", "/etc/agentbus.json"],
  "workingDirectory": "/var/lib/agentbus",
  "environment": {
    "AGENTBUS_LOG_LEVEL": "info",
    "AGENTBUS_PORT": "8080"
  },
  "autoRestart": true,
  "restartDelay": 5000,
  "maxRetries": 3,
  "logLevel": "info",
  "monitoring": {
    "enabled": true,
    "interval": 30000,
    "healthCheckUrl": "http://localhost:8080/health",
    "maxMemoryUsage": 536870912,
    "maxCpuUsage": 80
  }
}
```

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `AGENTBUS_SERVICE_NAME` | 服务名称 | `agentbus` |
| `AGENTBUS_CONFIG_DIR` | 配置目录 | 平台特定默认路径 |
| `AGENTBUS_LOG_DIR` | 日志目录 | 平台特定默认路径 |
| `AGENTBUS_LOG_LEVEL` | 日志级别 | `info` |
| `AGENTBUS_AUTO_RESTART` | 自动重启 | `true` |
| `AGENTBUS_MONITORING_ENABLED` | 启用监控 | `true` |

## CLI 命令

### 基本命令

```bash
agentbus-daemon start                    # 启动守护进程
agentbus-daemon stop                     # 停止守护进程
agentbus-daemon restart                  # 重启守护进程
agentbus-daemon status                   # 查看状态
agentbus-daemon install <path>           # 安装服务
agentbus-daemon uninstall                # 卸载服务
agentbus-daemon health                   # 健康检查
agentbus-daemon logs                     # 查看日志
agentbus-daemon platform                 # 查看平台信息
```

### 配置管理

```bash
agentbus-daemon config show              # 显示配置
agentbus-daemon config edit key=value   # 编辑配置
agentbus-daemon config validate          # 验证配置
agentbus-daemon config reset             # 重置配置
```

### 安装选项

```bash
agentbus-daemon install /path/to/app \
  --args "--config=/etc/app.json" \
  --working-dir="/var/lib/app" \
  --env="ENV=production" \
  --description="My Application" \
  --name="myapp"
```

## 监控和健康检查

### 内置监控

- **状态监控**: 实时检查服务运行状态
- **资源监控**: 监控内存和CPU使用情况
- **健康检查**: HTTP端点或命令健康检查
- **自动重启**: 服务异常停止时自动重启

### 健康检查配置

```json
{
  "monitoring": {
    "enabled": true,
    "interval": 30000,
    "healthCheckUrl": "http://localhost:8080/health",
    "healthCheckCommand": "curl -f http://localhost:8080/health",
    "maxMemoryUsage": 536870912,
    "maxCpuUsage": 80
  }
}
```

### 监控输出示例

```
=== AgentBus服务状态报告 ===
时间: 2024-01-15T10:30:00.000Z
守护进程运行: 是
平台: linux x64

=== 服务状态 ===
状态: running
运行中: 是
进程ID: 12345
状态: active

=== 系统信息 ===
主机名: server1
CPU核心: 4
总内存: 8GB
运行时间: 2天 5小时

=== 资源使用 ===
内存RSS: 128MB
堆内存: 45MB
运行时间: 2天 5小时

=== 监控状态 ===
监控启用: 是
检查间隔: 30000ms
监控服务: systemd
```

## 故障排除

### 常见问题

1. **权限不足**
   - Linux/macOS: 确保有systemd/launchd访问权限
   - Windows: 以管理员身份运行

2. **服务安装失败**
   - 检查可执行文件路径是否正确
   - 确认配置文件格式正确
   - 查看详细错误日志

3. **服务无法启动**
   - 检查应用程序依赖
   - 验证工作目录权限
   - 查看系统服务日志

### 诊断工具

```bash
# 执行完整诊断
agentbus-daemon diagnose

# 检查特定组件
node -e "
const { createDiagnostics } = require('@agentbus/daemon');
const diagnostics = createDiagnostics();
diagnostics.performFullDiagnostic().then(result => {
  console.log(diagnostics.generateDiagnosticReport(result));
});
"
```

## 开发

### 构建

```bash
npm run build
```

### 开发模式

```bash
npm run dev
```

### 测试

```bash
npm test
```

### 代码检查

```bash
npm run lint
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 路线图

- [ ] 服务依赖管理
- [ ] 滚动更新支持
- [ ] 更丰富的监控指标
- [ ] Web UI 管理界面
- [ ] Docker 容器支持
- [ ] Kubernetes 集成

---

更多信息请访问 [AgentBus 官方文档](https://agentbus.dev/docs)。