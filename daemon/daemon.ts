import { AgentBusServiceManager, AgentBusServiceInstallArgs } from "./service-manager.js";
import { ConfigManager } from "./config.js";
import { ServiceMonitor, HealthChecker } from "./monitor.js";
import { 
  AgentBusServiceRuntime, 
  ServiceConfiguration, 
  DaemonStatus, 
  MonitoringConfig 
} from "./types.js";
import { 
  AGENTBUS_DEFAULT_CONFIG,
  AGENTBUS_ENV_VARS,
  resolveAgentBusLogFiles,
  ERROR_MESSAGES,
  STATUS_MESSAGES
} from "./constants.js";
import { 
  resolveAgentBusLogFiles as resolveLogFiles,
  formatDuration,
  getSystemInfo
} from "./paths.js";

/**
 * AgentBus守护进程主类
 * 提供完整的守护进程管理功能
 */
export class AgentBusDaemon {
  private manager: AgentBusServiceManager;
  private configManager: ConfigManager;
  private config: ServiceConfiguration;
  private monitor: ServiceMonitor | null = null;
  private healthChecker: HealthChecker | null = null;
  private isRunning: boolean = false;
  private status: DaemonStatus | null = null;

  constructor(
    manager?: AgentBusServiceManager,
    configManager?: ConfigManager
  ) {
    this.manager = manager || new AgentBusServiceManager();
    this.configManager = configManager || new ConfigManager();
    this.config = { ...AGENTBUS_DEFAULT_CONFIG } as ServiceConfiguration;
  }

  /**
   * 初始化守护进程
   */
  async initialize(): Promise<void> {
    try {
      console.log("初始化AgentBus守护进程...");
      
      // 加载配置
      await this.configManager.load();
      this.config = this.configManager.getConfig();
      
      // 创建监控器
      if (this.config.monitoring.enabled) {
        this.monitor = new ServiceMonitor(
          this.manager,
          this.config.monitoring,
          (status) => this.onStatusUpdate(status),
          (error) => this.onMonitorError(error)
        );
        this.healthChecker = new HealthChecker(this.manager);
      }
      
      console.log("AgentBus守护进程初始化完成");
    } catch (error) {
      throw new Error(`初始化失败: ${error}`);
    }
  }

  /**
   * 启动守护进程
   */
  async start(): Promise<void> {
    if (this.isRunning) {
      console.log("守护进程已在运行");
      return;
    }

    try {
      console.log("启动AgentBus守护进程...");
      this.isRunning = true;

      // 启动监控
      if (this.monitor) {
        await this.monitor.start();
      }

      // 获取初始状态
      await this.updateStatus();

      console.log("AgentBus守护进程启动完成");
    } catch (error) {
      this.isRunning = false;
      throw new Error(`启动失败: ${error}`);
    }
  }

  /**
   * 停止守护进程
   */
  async stop(): Promise<void> {
    if (!this.isRunning) {
      console.log("守护进程未在运行");
      return;
    }

    try {
      console.log("停止AgentBus守护进程...");
      this.isRunning = false;

      // 停止监控
      if (this.monitor) {
        this.monitor.stop();
      }

      console.log("AgentBus守护进程已停止");
    } catch (error) {
      throw new Error(`停止失败: ${error}`);
    }
  }

  /**
   * 重启守护进程
   */
  async restart(): Promise<void> {
    console.log("重启AgentBus守护进程...");
    await this.stop();
    await this.start();
  }

  /**
   * 安装服务
   */
  async installService(args: {
    executablePath: string;
    arguments?: string[];
    workingDirectory?: string;
    environment?: Record<string, string>;
    description?: string;
    serviceName?: string;
  }): Promise<void> {
    try {
      console.log("安装AgentBus服务...");
      
      // 验证配置
      const installArgs: AgentBusServiceInstallArgs = {
        env: process.env,
        stdout: process.stdout,
        programArguments: [args.executablePath, ...(args.arguments || [])],
        workingDirectory: args.workingDirectory,
        environment: args.environment,
        description: args.description,
        serviceName: args.serviceName
      };

      await this.manager.install(installArgs);
      
      console.log(STATUS_MESSAGES.SERVICE_INSTALLED);
    } catch (error) {
      throw new Error(`${ERROR_MESSAGES.SERVICE_INSTALL_FAILED}: ${error}`);
    }
  }

  /**
   * 卸载服务
   */
  async uninstallService(): Promise<void> {
    try {
      console.log("卸载AgentBus服务...");
      
      await this.manager.uninstall({
        env: process.env,
        stdout: process.stdout
      });
      
      console.log(STATUS_MESSAGES.SERVICE_UNINSTALLED);
    } catch (error) {
      throw new Error(`${ERROR_MESSAGES.SERVICE_UNINSTALL_FAILED}: ${error}`);
    }
  }

  /**
   * 启动服务
   */
  async startService(): Promise<void> {
    try {
      console.log("启动AgentBus服务...");
      
      await this.manager.restart({
        env: process.env,
        stdout: process.stdout
      });
      
      console.log(STATUS_MESSAGES.SERVICE_STARTED);
      await this.updateStatus();
    } catch (error) {
      throw new Error(`${ERROR_MESSAGES.SERVICE_START_FAILED}: ${error}`);
    }
  }

  /**
   * 停止服务
   */
  async stopService(): Promise<void> {
    try {
      console.log("停止AgentBus服务...");
      
      await this.manager.stop({
        env: process.env,
        stdout: process.stdout
      });
      
      console.log(STATUS_MESSAGES.SERVICE_STOPPED);
      await this.updateStatus();
    } catch (error) {
      throw new Error(`${ERROR_MESSAGES.SERVICE_STOP_FAILED}: ${error}`);
    }
  }

  /**
   * 重启服务
   */
  async restartService(): Promise<void> {
    try {
      console.log("重启AgentBus服务...");
      
      await this.manager.restart({
        env: process.env,
        stdout: process.stdout
      });
      
      console.log(STATUS_MESSAGES.SERVICE_RESTARTED);
      await this.updateStatus();
    } catch (error) {
      throw new Error(`${ERROR_MESSAGES.SERVICE_RESTART_FAILED}: ${error}`);
    }
  }

  /**
   * 获取服务状态
   */
  async getServiceStatus(): Promise<AgentBusServiceRuntime> {
    return await this.manager.readRuntime(process.env);
  }

  /**
   * 检查服务是否运行
   */
  async isServiceRunning(): Promise<boolean> {
    const status = await this.getServiceStatus();
    return status.status === "running";
  }

  /**
   * 获取守护进程状态
   */
  async getDaemonStatus(): Promise<DaemonStatus> {
    if (!this.status) {
      await this.updateStatus();
    }
    return this.status!;
  }

  /**
   * 执行健康检查
   */
  async performHealthCheck(): Promise<{
    service: boolean;
    system: boolean;
    resources: boolean;
    overall: boolean;
    details: any;
  }> {
    if (!this.healthChecker) {
      throw new Error("健康检查器未初始化");
    }

    return await this.healthChecker.performFullCheck();
  }

  /**
   * 更新配置
   */
  async updateConfig(updates: Partial<ServiceConfiguration>): Promise<void> {
    this.configManager.updateConfig(updates);
    await this.configManager.save();
    this.config = this.configManager.getConfig();

    // 如果监控配置改变了，重启监控
    if (updates.monitoring && this.monitor) {
      this.monitor.updateConfig(updates.monitoring);
    }
  }

  /**
   * 获取配置
   */
  getConfig(): ServiceConfiguration {
    return { ...this.config };
  }

  /**
   * 验证配置
   */
  validateConfig(): { isValid: boolean; errors: string[] } {
    return this.configManager.validate();
  }

  /**
   * 生成状态报告
   */
  async generateStatusReport(): Promise<string> {
    const status = await this.getDaemonStatus();
    const lines: string[] = [];

    lines.push("=== AgentBus守护进程状态报告 ===");
    lines.push(`时间: ${new Date().toISOString()}`);
    lines.push(`守护进程运行: ${this.isRunning ? "是" : "否"}`);
    lines.push(`平台: ${process.platform} ${process.arch}`);
    lines.push("");

    // 服务状态
    lines.push("=== 服务状态 ===");
    lines.push(`状态: ${status.service.status || "未知"}`);
    lines.push(`运行中: ${status.isRunning ? "是" : "否"}`);
    if (status.service.pid) {
      lines.push(`进程ID: ${status.service.pid}`);
    }
    if (status.service.state) {
      lines.push(`状态: ${status.service.state}`);
    }
    lines.push("");

    // 系统信息
    lines.push("=== 系统信息 ===");
    const systemInfo = getSystemInfo();
    lines.push(`主机名: ${systemInfo.hostname}`);
    lines.push(`CPU核心: ${systemInfo.cpus}`);
    lines.push(`总内存: ${Math.round(systemInfo.totalMemory / 1024 / 1024 / 1024)}GB`);
    lines.push(`运行时间: ${formatDuration(systemInfo.uptime * 1000)}`);
    lines.push("");

    // 资源使用
    if (status.memoryUsage) {
      lines.push("=== 资源使用 ===");
      lines.push(`内存RSS: ${Math.round(status.memoryUsage.rss / 1024 / 1024)}MB`);
      lines.push(`堆内存: ${Math.round(status.memoryUsage.heapUsed / 1024 / 1024)}MB`);
      lines.push(`运行时间: ${status.uptime ? formatDuration(status.uptime * 1000) : "未知"}`);
      lines.push("");
    }

    // 监控状态
    if (this.monitor) {
      lines.push("=== 监控状态 ===");
      const monitorStatus = this.monitor.getStatus();
      lines.push(`监控启用: ${monitorStatus.isMonitoring ? "是" : "否"}`);
      lines.push(`检查间隔: ${monitorStatus.config.interval}ms`);
      lines.push(`监控服务: ${this.manager.getLabel()}`);
    }

    return lines.join("\n");
  }

  /**
   * 获取平台信息
   */
  getPlatformInfo(): {
    platform: string;
    service: string;
    supported: boolean;
  } {
    const platformInfo = this.manager.getPlatformInfo();
    return {
      platform: platformInfo.platform,
      service: platformInfo.service,
      supported: true // 如果能创建服务管理器，说明支持
    };
  }

  /**
   * 监听信号处理
   */
  setupSignalHandlers(): void {
    process.on('SIGTERM', async () => {
      console.log("接收到SIGTERM信号，正在停止守护进程...");
      await this.stop();
      process.exit(0);
    });

    process.on('SIGINT', async () => {
      console.log("接收到SIGINT信号，正在停止守护进程...");
      await this.stop();
      process.exit(0);
    });
  }

  /**
   * 更新状态
   */
  private async updateStatus(): Promise<void> {
    try {
      const runtime = await this.manager.readRuntime(process.env);
      const isLoaded = await this.manager.isLoaded({ env: process.env });

      this.status = {
        isRunning: runtime.status === "running",
        service: runtime,
        uptime: process.uptime(),
        memoryUsage: process.memoryUsage(),
        cpuUsage: process.cpuUsage()
      };
    } catch (error) {
      console.error("更新状态失败:", error);
    }
  }

  /**
   * 状态更新回调
   */
  private onStatusUpdate(status: DaemonStatus): void {
    this.status = status;
    
    // 如果启用了自动重启且服务停止了，尝试重启
    if (this.config.autoRestart && !status.isRunning) {
      console.log("检测到服务停止，尝试自动重启...");
      this.restartService().catch(error => {
        console.error("自动重启失败:", error);
      });
    }
  }

  /**
   * 监控错误回调
   */
  private onMonitorError(error: Error): void {
    console.error("监控错误:", error);
  }
}

/**
 * AgentBus守护进程工厂函数
 */
export async function createAgentBusDaemon(): Promise<AgentBusDaemon> {
  const daemon = new AgentBusDaemon();
  await daemon.initialize();
  return daemon;
}

/**
 * 默认守护进程实例
 */
let defaultDaemon: AgentBusDaemon | null = null;

/**
 * 获取默认守护进程实例
 */
export async function getDefaultDaemon(): Promise<AgentBusDaemon> {
  if (!defaultDaemon) {
    defaultDaemon = await createAgentBusDaemon();
  }
  return defaultDaemon;
}