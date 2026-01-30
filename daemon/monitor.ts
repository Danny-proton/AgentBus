import type { AgentBusServiceRuntime, DaemonStatus, MonitoringConfig } from "./types.js";
import { AgentBusServiceManager } from "./service-manager.js";
import { formatDuration, formatFileSize, getSystemInfo } from "./paths.js";

/**
 * 服务监控器
 */
export class ServiceMonitor {
  private manager: AgentBusServiceManager;
  private config: MonitoringConfig;
  private isMonitoring: boolean = false;
  private intervalId: NodeJS.Timeout | null = null;
  private healthCheckCallback?: (status: DaemonStatus) => void;
  private errorCallback?: (error: Error) => void;

  constructor(
    manager: AgentBusServiceManager,
    config: MonitoringConfig,
    healthCheckCallback?: (status: DaemonStatus) => void,
    errorCallback?: (error: Error) => void
  ) {
    this.manager = manager;
    this.config = config;
    this.healthCheckCallback = healthCheckCallback;
    this.errorCallback = errorCallback;
  }

  /**
   * 启动监控
   */
  async start(): Promise<void> {
    if (this.isMonitoring) {
      console.log("监控已在运行中");
      return;
    }

    console.log(`启动服务监控，间隔: ${this.config.interval}ms`);

    this.isMonitoring = true;

    // 立即执行一次健康检查
    await this.performHealthCheck();

    // 设置定期检查
    this.intervalId = setInterval(async () => {
      if (!this.isMonitoring) return;
      
      try {
        await this.performHealthCheck();
      } catch (error) {
        console.error("健康检查失败:", error);
        this.errorCallback?.(error as Error);
      }
    }, this.config.interval);
  }

  /**
   * 停止监控
   */
  stop(): void {
    if (!this.isMonitoring) {
      console.log("监控未在运行");
      return;
    }

    console.log("停止服务监控");
    this.isMonitoring = false;

    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  /**
   * 更新监控配置
   */
  updateConfig(config: Partial<MonitoringConfig>): void {
    this.config = { ...this.config, ...config };
    
    // 如果监控间隔改变了，需要重启监控
    if (this.isMonitoring && config.interval) {
      this.stop();
      this.start();
    }
  }

  /**
   * 执行健康检查
   */
  private async performHealthCheck(): Promise<DaemonStatus> {
    try {
      // 获取服务状态
      const runtime = await this.manager.readRuntime(process.env);
      const isLoaded = await this.manager.isLoaded({ env: process.env });
      
      // 构建状态信息
      const status: DaemonStatus = {
        isRunning: runtime.status === "running",
        service: runtime,
        uptime: process.uptime(),
        memoryUsage: process.memoryUsage(),
        cpuUsage: process.cpuUsage()
      };

      // 执行自定义健康检查
      if (this.config.healthCheckUrl) {
        status.healthCheck = await this.performHttpHealthCheck(this.config.healthCheckUrl);
      } else if (this.config.healthCheckCommand) {
        status.healthCheck = await this.performCommandHealthCheck(this.config.healthCheckCommand);
      } else {
        status.healthCheck = true; // 默认健康
      }

      // 检查资源使用情况
      status.resourceCheck = this.checkResourceUsage(status);

      // 执行回调
      this.healthCheckCallback?.(status);

      return status;
    } catch (error) {
      const status: DaemonStatus = {
        isRunning: false,
        service: {
          status: "unknown",
          detail: `健康检查失败: ${error}`
        }
      };
      
      this.healthCheckCallback?.(status);
      throw error;
    }
  }

  /**
   * HTTP健康检查
   */
  private async performHttpHealthCheck(url: string): Promise<boolean> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5秒超时

      const response = await fetch(url, {
        method: "GET",
        signal: controller.signal,
        headers: {
          "User-Agent": "AgentBus-Monitor/1.0"
        }
      });

      clearTimeout(timeoutId);
      return response.ok;
    } catch (error) {
      console.warn("HTTP健康检查失败:", error);
      return false;
    }
  }

  /**
   * 命令健康检查
   */
  private async performCommandHealthCheck(command: string): Promise<boolean> {
    try {
      const { exec } = await import("node:child_process");
      const { promisify } = await import("node:util");
      
      const execAsync = promisify(exec);
      const result = await execAsync(command, { timeout: 5000 }); // 5秒超时
      
      return result.exitCode === 0;
    } catch (error) {
      console.warn("命令健康检查失败:", error);
      return false;
    }
  }

  /**
   * 检查资源使用情况
   */
  private checkResourceUsage(status: DaemonStatus): {
    memory: boolean;
    cpu: boolean;
    overall: boolean;
  } {
    let memoryOk = true;
    let cpuOk = true;

    // 检查内存使用
    if (this.config.maxMemoryUsage && status.memoryUsage) {
      const heapUsed = status.memoryUsage.heapUsed;
      memoryOk = heapUsed <= this.config.maxMemoryUsage;
    }

    // 检查CPU使用（这里简化处理，实际中可能需要更精确的测量）
    if (this.config.maxCpuUsage && status.cpuUsage) {
      // 这里只是一个简单的估算，实际项目中可能需要更复杂的CPU监控
      const cpuUsagePercent = (status.cpuUsage.user + status.cpuUsage.system) / 1000000 * 100;
      cpuOk = cpuUsagePercent <= this.config.maxCpuUsage;
    }

    return {
      memory: memoryOk,
      cpu: cpuOk,
      overall: memoryOk && cpuOk
    };
  }

  /**
   * 获取当前监控状态
   */
  getStatus(): {
    isMonitoring: boolean;
    config: MonitoringConfig;
    interval: number;
  } {
    return {
      isMonitoring: this.isMonitoring,
      config: { ...this.config },
      interval: this.intervalId ? this.config.interval : 0
    };
  }

  /**
   * 生成状态报告
   */
  generateReport(status: DaemonStatus): string {
    const lines: string[] = [];
    
    lines.push("=== AgentBus服务状态报告 ===");
    lines.push(`时间: ${new Date().toISOString()}`);
    lines.push(`平台: ${process.platform} ${process.arch}`);
    lines.push(`系统信息: ${JSON.stringify(getSystemInfo(), null, 2)}`);
    lines.push("");

    // 服务状态
    lines.push("=== 服务状态 ===");
    lines.push(`运行状态: ${status.isRunning ? "运行中" : "未运行"}`);
    lines.push(`服务状态: ${status.service.status || "未知"}`);
    lines.push(`状态详情: ${status.service.detail || "无"}`);
    if (status.service.pid) {
      lines.push(`进程ID: ${status.service.pid}`);
    }
    if (status.service.state) {
      lines.push(`状态: ${status.service.state}`);
    }
    if (status.service.subState) {
      lines.push(`子状态: ${status.service.subState}`);
    }
    lines.push("");

    // 系统资源
    lines.push("=== 系统资源 ===");
    lines.push(`进程运行时间: ${formatDuration((status.uptime || 0) * 1000)}`);
    
    if (status.memoryUsage) {
      lines.push(`内存使用:`);
      lines.push(`  RSS: ${formatFileSize(status.memoryUsage.rss)}`);
      lines.push(`  Heap Total: ${formatFileSize(status.memoryUsage.heapTotal)}`);
      lines.push(`  Heap Used: ${formatFileSize(status.memoryUsage.heapUsed)}`);
      lines.push(`  External: ${formatFileSize(status.memoryUsage.external)}`);
    }

    if (status.cpuUsage) {
      lines.push(`CPU使用: ${JSON.stringify(status.cpuUsage)}`);
    }
    lines.push("");

    // 健康检查
    lines.push("=== 健康检查 ===");
    if (status.healthCheck !== undefined) {
      lines.push(`HTTP/命令检查: ${status.healthCheck ? "通过" : "失败"}`);
    }
    
    if (status.resourceCheck) {
      lines.push(`资源检查:`);
      lines.push(`  内存: ${status.resourceCheck.memory ? "正常" : "超限"}`);
      lines.push(`  CPU: ${status.resourceCheck.cpu ? "正常" : "超限"}`);
      lines.push(`  总体: ${status.resourceCheck.overall ? "健康" : "不健康"}`);
    }
    lines.push("");

    // 监控配置
    lines.push("=== 监控配置 ===");
    lines.push(`监控启用: ${this.config.enabled ? "是" : "否"}`);
    lines.push(`检查间隔: ${this.config.interval}ms`);
    if (this.config.healthCheckUrl) {
      lines.push(`HTTP检查: ${this.config.healthCheckUrl}`);
    }
    if (this.config.healthCheckCommand) {
      lines.push(`命令检查: ${this.config.healthCheckCommand}`);
    }
    if (this.config.maxMemoryUsage) {
      lines.push(`最大内存: ${formatFileSize(this.config.maxMemoryUsage)}`);
    }
    if (this.config.maxCpuUsage) {
      lines.push(`最大CPU: ${this.config.maxCpuUsage}%`);
    }

    return lines.join("\n");
  }
}

/**
 * 健康检查器
 */
export class HealthChecker {
  private manager: AgentBusServiceManager;

  constructor(manager: AgentBusServiceManager) {
    this.manager = manager;
  }

  /**
   * 执行完整健康检查
   */
  async performFullCheck(): Promise<{
    service: boolean;
    system: boolean;
    resources: boolean;
    overall: boolean;
    details: any;
  }> {
    const details: any = {};

    // 服务检查
    details.service = await this.checkService();
    
    // 系统检查
    details.system = this.checkSystem();
    
    // 资源检查
    details.resources = this.checkResources();

    const overall = details.service && details.system && details.resources;

    return {
      service: details.service,
      system: details.system,
      resources: details.resources,
      overall,
      details
    };
  }

  /**
   * 检查服务状态
   */
  private async checkService(): Promise<boolean> {
    try {
      const runtime = await this.manager.readRuntime(process.env);
      const isLoaded = await this.manager.isLoaded({ env: process.env });
      
      return runtime.status === "running" && isLoaded;
    } catch (error) {
      console.error("服务检查失败:", error);
      return false;
    }
  }

  /**
   * 检查系统状态
   */
  private checkSystem(): boolean {
    // 检查基本系统状态
    const systemInfo = getSystemInfo();
    
    // 检查内存使用率
    const totalMemory = systemInfo.totalMemory;
    const freeMemory = totalMemory - (process.memoryUsage().rss);
    const memoryUsagePercent = ((totalMemory - freeMemory) / totalMemory) * 100;
    
    return memoryUsagePercent < 90; // 内存使用率小于90%
  }

  /**
   * 检查资源使用
   */
  private checkResources(): boolean {
    const memoryUsage = process.memoryUsage();
    const cpuUsage = process.cpuUsage();
    
    // 检查内存泄漏
    const memoryOk = memoryUsage.heapUsed < 500 * 1024 * 1024; // 500MB
    
    // 检查CPU使用（简化处理）
    const cpuOk = true; // 这里需要更精确的CPU监控
    
    return memoryOk && cpuOk;
  }
}

/**
 * 创建服务监控器
 */
export function createServiceMonitor(
  manager: AgentBusServiceManager,
  config: MonitoringConfig,
  healthCheckCallback?: (status: DaemonStatus) => void,
  errorCallback?: (error: Error) => void
): ServiceMonitor {
  return new ServiceMonitor(manager, config, healthCheckCallback, errorCallback);
}

/**
 * 创建健康检查器
 */
export function createHealthChecker(manager: AgentBusServiceManager): HealthChecker {
  return new HealthChecker(manager);
}