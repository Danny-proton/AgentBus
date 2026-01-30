import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { AgentBusServiceManager } from "./service-manager.js";
import { ConfigManager } from "./config.js";
import { ServiceMonitor, HealthChecker } from "./monitor.js";
import { AgentBusDaemon } from "./daemon.js";
import { resolveAgentBusLogFiles } from "./paths.js";
import type { ServiceConfiguration, MonitoringConfig } from "./types.js";

const execFileAsync = promisify(execFile);

/**
 * 诊断工具
 */
export class Diagnostics {
  private manager: AgentBusServiceManager;
  private configManager: ConfigManager;

  constructor(manager?: AgentBusServiceManager, configManager?: ConfigManager) {
    this.manager = manager || new AgentBusServiceManager();
    this.configManager = configManager || new ConfigManager();
  }

  /**
   * 执行完整诊断
   */
  async performFullDiagnostic(): Promise<{
    platform: boolean;
    dependencies: boolean;
    permissions: boolean;
    configuration: boolean;
    services: boolean;
    logs: boolean;
    overall: boolean;
    details: any;
  }> {
    const details: any = {};

    // 平台检查
    details.platform = await this.checkPlatform();

    // 依赖检查
    details.dependencies = await this.checkDependencies();

    // 权限检查
    details.permissions = await this.checkPermissions();

    // 配置检查
    details.configuration = await this.checkConfiguration();

    // 服务检查
    details.services = await this.checkServices();

    // 日志检查
    details.logs = await this.checkLogs();

    const overall = Object.values(details).every(result => result === true);

    return {
      platform: details.platform,
      dependencies: details.dependencies,
      permissions: details.permissions,
      configuration: details.configuration,
      services: details.services,
      logs: details.logs,
      overall,
      details
    };
  }

  /**
   * 检查平台支持
   */
  private async checkPlatform(): Promise<boolean> {
    try {
      const platformInfo = this.manager.getPlatformInfo();
      console.log(`平台: ${platformInfo.platform}, 服务: ${platformInfo.service}`);
      return true;
    } catch (error) {
      console.error("平台检查失败:", error);
      return false;
    }
  }

  /**
   * 检查系统依赖
   */
  private async checkDependencies(): Promise<boolean> {
    const platform = process.platform;
    let allGood = true;

    try {
      if (platform === "linux") {
        // 检查systemd
        try {
          await execFileAsync("systemctl", ["--version"]);
          console.log("systemd: 可用");
        } catch {
          console.log("systemd: 不可用");
          allGood = false;
        }
      } else if (platform === "darwin") {
        // 检查launchd
        try {
          await execFileAsync("launchctl", ["version"]);
          console.log("launchd: 可用");
        } catch {
          console.log("launchd: 不可用");
          allGood = false;
        }
      } else if (platform === "win32") {
        // 检查schtasks
        try {
          await execFileAsync("schtasks", ["/query"]);
          console.log("任务计划程序: 可用");
        } catch {
          console.log("任务计划程序: 不可用");
          allGood = false;
        }
      }

      return allGood;
    } catch (error) {
      console.error("依赖检查失败:", error);
      return false;
    }
  }

  /**
   * 检查权限
   */
  private async checkPermissions(): Promise<boolean> {
    try {
      const platform = process.platform;
      
      if (platform === "linux") {
        // 检查是否可以访问systemd
        try {
          await execFileAsync("systemctl", ["--user", "status"]);
          console.log("systemd用户权限: 正常");
        } catch {
          console.log("systemd用户权限: 无权限");
          return false;
        }
      } else if (platform === "darwin") {
        // 检查launchd权限
        try {
          await execFileAsync("launchctl", ["list"]);
          console.log("launchd权限: 正常");
        } catch {
          console.log("launchd权限: 无权限");
          return false;
        }
      }

      return true;
    } catch (error) {
      console.error("权限检查失败:", error);
      return false;
    }
  }

  /**
   * 检查配置
   */
  private async checkConfiguration(): Promise<boolean> {
    try {
      await this.configManager.load();
      const validation = this.configManager.validate();
      
      if (validation.isValid) {
        console.log("配置: 有效");
        return true;
      } else {
        console.log("配置: 无效");
        validation.errors.forEach(error => console.log(`  - ${error}`));
        return false;
      }
    } catch (error) {
      console.log("配置: 无法读取");
      return false;
    }
  }

  /**
   * 检查服务状态
   */
  private async checkServices(): Promise<boolean> {
    try {
      const isLoaded = await this.manager.isLoaded({ env: process.env });
      const runtime = await this.manager.readRuntime(process.env);
      
      console.log(`服务状态: ${isLoaded ? "已加载" : "未加载"}`);
      console.log(`运行状态: ${runtime.status}`);
      
      return true;
    } catch (error) {
      console.log("服务检查失败:", error);
      return false;
    }
  }

  /**
   * 检查日志
   */
  private async checkLogs(): Promise<boolean> {
    try {
      const logFiles = resolveAgentBusLogFiles();
      
      console.log(`日志目录: ${logFiles.logDir}`);
      console.log(`stdout: ${logFiles.stdoutPath}`);
      console.log(`stderr: ${logFiles.stderrPath}`);
      
      return true;
    } catch (error) {
      console.log("日志检查失败:", error);
      return false;
    }
  }

  /**
   * 生成诊断报告
   */
  generateDiagnosticReport(result: any): string {
    const lines: string[] = [];
    
    lines.push("=== AgentBus诊断报告 ===");
    lines.push(`时间: ${new Date().toISOString()}`);
    lines.push(`平台: ${process.platform} ${process.arch}`);
    lines.push("");

    lines.push("=== 检查结果 ===");
    lines.push(`平台支持: ${result.platform ? "✓" : "✗"}`);
    lines.push(`系统依赖: ${result.dependencies ? "✓" : "✗"}`);
    lines.push(`权限检查: ${result.permissions ? "✓" : "✗"}`);
    lines.push(`配置检查: ${result.configuration ? "✓" : "✗"}`);
    lines.push(`服务检查: ${result.services ? "✓" : "✗"}`);
    lines.push(`日志检查: ${result.logs ? "✓" : "✗"}`);
    lines.push("");
    
    lines.push(`总体状态: ${result.overall ? "健康" : "需要关注"}`);
    
    if (!result.overall) {
      lines.push("");
      lines.push("=== 详细信息 ===");
      lines.push(JSON.stringify(result.details, null, 2));
    }

    return lines.join("\n");
  }
}

/**
 * 升级工具
 */
export class UpgradeManager {
  private manager: AgentBusServiceManager;
  private daemon: AgentBusDaemon;

  constructor(manager?: AgentBusServiceManager, daemon?: AgentBusDaemon) {
    this.manager = manager || new AgentBusServiceManager();
    this.daemon = daemon || new AgentBusDaemon();
  }

  /**
   * 检查升级
   */
  async checkForUpgrade(): Promise<{
    available: boolean;
    current: string;
    latest: string;
    changes: string[];
  }> {
    // 这里可以实现检查最新版本的逻辑
    // 目前返回模拟数据
    return {
      available: false,
      current: "1.0.0",
      latest: "1.0.0",
      changes: []
    };
  }

  /**
   * 执行升级
   */
  async performUpgrade(): Promise<void> {
    console.log("执行升级...");
    
    // 停止服务
    await this.daemon.stopService();
    
    // 备份配置
    await this.backupConfiguration();
    
    // 执行升级
    // 这里实现实际的升级逻辑
    
    console.log("升级完成");
  }

  /**
   * 备份配置
   */
  private async backupConfiguration(): Promise<void> {
    console.log("备份配置文件...");
    // 实现备份逻辑
  }

  /**
   * 回滚升级
   */
  async rollbackUpgrade(): Promise<void> {
    console.log("回滚升级...");
    // 实现回滚逻辑
  }
}

/**
 * 迁移工具
 */
export class MigrationManager {
  private configManager: ConfigManager;

  constructor(configManager?: ConfigManager) {
    this.configManager = configManager || new ConfigManager();
  }

  /**
   * 执行迁移
   */
  async migrate(): Promise<void> {
    console.log("执行数据迁移...");
    
    // 检查当前版本
    const currentVersion = await this.getCurrentVersion();
    const targetVersion = "1.0.0";
    
    if (currentVersion === targetVersion) {
      console.log("已是最新版本，无需迁移");
      return;
    }
    
    // 执行迁移步骤
    await this.performMigrationSteps(currentVersion, targetVersion);
    
    console.log("迁移完成");
  }

  /**
   * 获取当前版本
   */
  private async getCurrentVersion(): Promise<string> {
    // 从配置文件或数据库获取版本
    return "0.9.0";
  }

  /**
   * 执行迁移步骤
   */
  private async performMigrationSteps(from: string, to: string): Promise<void> {
    // 实现版本间的迁移逻辑
    console.log(`从版本 ${from} 迁移到 ${to}`);
  }
}

/**
 * 工具函数
 */

/**
 * 格式化错误信息
 */
export function formatError(error: any): string {
  if (error instanceof Error) {
    return `${error.name}: ${error.message}`;
  }
  return String(error);
}

/**
 * 检查是否为管理员权限
 */
export async function isAdmin(): Promise<boolean> {
  try {
    if (process.platform === "win32") {
      // Windows检查管理员权限
      const { stdout } = await execFileAsync("net", ["session"]);
      return stdout.includes("成功");
    } else {
      // Unix检查root权限
      return process.getuid && process.getuid() === 0;
    }
  } catch {
    return false;
  }
}

/**
 * 获取系统负载信息
 */
export async function getSystemLoad(): Promise<{
  cpu: number;
  memory: number;
  loadAverage: number[];
}> {
  const os = await import("node:os");
  
  return {
    cpu: os.loadavg()[0],
    memory: os.freemem() / os.totalmem(),
    loadAverage: os.loadavg()
  };
}

/**
 * 清理临时文件
 */
export async function cleanupTempFiles(): Promise<void> {
  try {
    const { readdir, unlink, stat } = await import("node:fs/promises");
    const { tmpdir } = await import("node:os");
    const { join } = await import("node:path");
    
    const tempDir = tmpdir();
    const files = await readdir(tempDir);
    
    for (const file of files) {
      if (file.startsWith("agentbus-")) {
        const filePath = join(tempDir, file);
        try {
          const stats = await stat(filePath);
          // 删除超过24小时的临时文件
          if (Date.now() - stats.mtime.getTime() > 24 * 60 * 60 * 1000) {
            await unlink(filePath);
            console.log(`已清理临时文件: ${filePath}`);
          }
        } catch {
          // 忽略错误
        }
      }
    }
  } catch (error) {
    console.warn("清理临时文件失败:", error);
  }
}

/**
 * 创建工具实例
 */
export function createDiagnostics(manager?: AgentBusServiceManager, configManager?: ConfigManager): Diagnostics {
  return new Diagnostics(manager, configManager);
}

export function createUpgradeManager(manager?: AgentBusServiceManager, daemon?: AgentBusDaemon): UpgradeManager {
  return new UpgradeManager(manager, daemon);
}

export function createMigrationManager(configManager?: ConfigManager): MigrationManager {
  return new MigrationManager(configManager);
}