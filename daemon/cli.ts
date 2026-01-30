#!/usr/bin/env node

import { AgentBusDaemon } from "./daemon.js";
import { createConfigManager } from "./config.js";
import { ServiceMonitor } from "./monitor.js";
import { resolveAgentBusLogFiles } from "./paths.js";
import { STATUS_MESSAGES, ERROR_MESSAGES } from "./constants.js";
import type { ServiceConfiguration } from "./types.js";

/**
 * CLI命令处理器
 */
export class AgentBusCLI {
  private daemon: AgentBusDaemon;
  private configManager: any;

  constructor() {
    this.daemon = new AgentBusDaemon();
    this.configManager = createConfigManager();
  }

  /**
   * 执行CLI命令
   */
  async executeCommand(args: string[]): Promise<void> {
    const command = args[0];
    
    try {
      await this.daemon.initialize();

      switch (command) {
        case "start":
          await this.handleStart();
          break;
        case "stop":
          await this.handleStop();
          break;
        case "restart":
          await this.handleRestart();
          break;
        case "status":
          await this.handleStatus();
          break;
        case "install":
          await this.handleInstall(args.slice(1));
          break;
        case "uninstall":
          await this.handleUninstall();
          break;
        case "config":
          await this.handleConfig(args.slice(1));
          break;
        case "health":
          await this.handleHealth();
          break;
        case "logs":
          await this.handleLogs();
          break;
        case "platform":
          await this.handlePlatform();
          break;
        case "help":
        case "--help":
        case "-h":
          this.showHelp();
          break;
        default:
          console.log(`未知命令: ${command}`);
          this.showHelp();
          process.exit(1);
      }
    } catch (error) {
      console.error("执行命令失败:", error);
      process.exit(1);
    }
  }

  /**
   * 启动守护进程
   */
  private async handleStart(): Promise<void> {
    console.log("启动AgentBus守护进程...");
    await this.daemon.start();
    console.log("守护进程已启动");
  }

  /**
   * 停止守护进程
   */
  private async handleStop(): Promise<void> {
    console.log("停止AgentBus守护进程...");
    await this.daemon.stop();
    console.log("守护进程已停止");
  }

  /**
   * 重启守护进程
   */
  private async handleRestart(): Promise<void> {
    console.log("重启AgentBus守护进程...");
    await this.daemon.restart();
    console.log("守护进程已重启");
  }

  /**
   * 查看状态
   */
  private async handleStatus(): Promise<void> {
    const report = await this.daemon.generateStatusReport();
    console.log(report);
  }

  /**
   * 安装服务
   */
  private async handleInstall(args: string[]): Promise<void> {
    const executablePath = args[0];
    if (!executablePath) {
      console.error("请提供可执行文件路径");
      process.exit(1);
    }

    const options = this.parseOptions(args.slice(1));
    
    await this.daemon.installService({
      executablePath,
      arguments: options.args || [],
      workingDirectory: options.workingDirectory,
      environment: options.environment,
      description: options.description,
      serviceName: options.serviceName
    });
  }

  /**
   * 卸载服务
   */
  private async handleUninstall(): Promise<void> {
    await this.daemon.uninstallService();
  }

  /**
   * 配置管理
   */
  private async handleConfig(args: string[]): Promise<void> {
    const subcommand = args[0];

    switch (subcommand) {
      case "show":
        this.showConfig();
        break;
      case "edit":
        await this.editConfig(args.slice(1));
        break;
      case "validate":
        await this.validateConfig();
        break;
      case "reset":
        await this.resetConfig();
        break;
      default:
        console.log("配置子命令: show, edit, validate, reset");
        process.exit(1);
    }
  }

  /**
   * 健康检查
   */
  private async handleHealth(): Promise<void> {
    console.log("执行健康检查...");
    const result = await this.daemon.performHealthCheck();
    
    console.log("\n=== 健康检查结果 ===");
    console.log(`服务状态: ${result.service ? "健康" : "不健康"}`);
    console.log(`系统状态: ${result.system ? "健康" : "不健康"}`);
    console.log(`资源状态: ${result.resources ? "健康" : "不健康"}`);
    console.log(`总体状态: ${result.overall ? "健康" : "不健康"}`);
    
    if (!result.overall) {
      console.log("\n详细信息:");
      console.log(JSON.stringify(result.details, null, 2));
    }
  }

  /**
   * 查看日志
   */
  private async handleLogs(): Promise<void> {
    const logFiles = resolveAgentBusLogFiles();
    
    console.log("=== AgentBus日志文件 ===");
    console.log(`标准输出: ${logFiles.stdoutPath}`);
    console.log(`错误输出: ${logFiles.stderrPath}`);
    console.log(`日志目录: ${logFiles.logDir}`);
    
    try {
      const { readFile } = await import("node:fs/promises");
      console.log("\n=== 最新日志 (stdout) ===");
      const stdoutContent = await readFile(logFiles.stdoutPath, "utf8");
      console.log(stdoutContent.slice(-2000)); // 显示最后2000字符
    } catch (error) {
      console.log("无法读取日志文件:", error);
    }
  }

  /**
   * 查看平台信息
   */
  private async handlePlatform(): Promise<void> {
    const platformInfo = this.daemon.getPlatformInfo();
    
    console.log("=== 平台信息 ===");
    console.log(`操作系统: ${platformInfo.platform}`);
    console.log(`服务管理器: ${platformInfo.service}`);
    console.log(`支持状态: ${platformInfo.supported ? "支持" : "不支持"}`);
  }

  /**
   * 显示帮助信息
   */
  private showHelp(): void {
    console.log(`
AgentBus守护进程管理工具

用法: agentbus-daemon <命令> [选项]

命令:
  start                    启动守护进程
  stop                     停止守护进程
  restart                  重启守护进程
  status                   查看守护进程状态
  install <可执行文件>      安装服务
  uninstall                卸载服务
  config <子命令>           配置管理
  health                   执行健康检查
  logs                     查看日志
  platform                 查看平台信息
  help                     显示此帮助信息

配置子命令:
  config show              显示当前配置
  config edit [key=value]  编辑配置
  config validate          验证配置
  config reset             重置为默认配置

安装选项:
  --args <参数>            附加参数
  --working-dir <目录>     工作目录
  --env <key=value>        环境变量
  --description <描述>     服务描述
  --name <名称>            服务名称

示例:
  agentbus-daemon start
  agentbus-daemon install /usr/bin/agentbus --args "--config=/etc/agentbus.json"
  agentbus-daemon config edit logLevel=debug
  agentbus-daemon health
  agentbus-daemon status
`);
  }

  /**
   * 显示配置
   */
  private showConfig(): void {
    const config = this.daemon.getConfig();
    console.log("=== 当前配置 ===");
    console.log(JSON.stringify(config, null, 2));
  }

  /**
   * 编辑配置
   */
  private async editConfig(args: string[]): Promise<void> {
    if (args.length === 0) {
      console.log("请提供配置键值对，如: logLevel=debug");
      process.exit(1);
    }

    const updates: any = {};
    
    for (const arg of args) {
      const [key, value] = arg.split("=");
      if (!key || !value) {
        console.log(`无效的配置项: ${arg}`);
        continue;
      }
      
      // 尝试解析值类型
      let parsedValue: any = value;
      if (value === "true") parsedValue = true;
      else if (value === "false") parsedValue = false;
      else if (!isNaN(Number(value))) parsedValue = Number(value);
      
      updates[key] = parsedValue;
    }

    await this.daemon.updateConfig(updates);
    console.log("配置已更新");
  }

  /**
   * 验证配置
   */
  private async validateConfig(): Promise<void> {
    const result = this.daemon.validateConfig();
    
    if (result.isValid) {
      console.log("配置验证通过");
    } else {
      console.log("配置验证失败:");
      result.errors.forEach(error => console.log(`- ${error}`));
      process.exit(1);
    }
  }

  /**
   * 重置配置
   */
  private async resetConfig(): Promise<void> {
    await this.configManager.createDefaultConfig();
    console.log("配置已重置为默认值");
  }

  /**
   * 解析命令行选项
   */
  private parseOptions(args: string[]): any {
    const options: any = {};
    let i = 0;

    while (i < args.length) {
      const arg = args[i];
      
      if (arg === "--args") {
        options.args = args[++i].split(",");
      } else if (arg === "--working-dir") {
        options.workingDirectory = args[++i];
      } else if (arg === "--env") {
        const [key, value] = args[++i].split("=");
        if (!options.environment) options.environment = {};
        options.environment[key] = value;
      } else if (arg === "--description") {
        options.description = args[++i];
      } else if (arg === "--name") {
        options.serviceName = args[++i];
      }
      
      i++;
    }

    return options;
  }
}

/**
 * CLI入口点
 */
export async function main(): Promise<void> {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.log("请提供命令。输入 'agentbus-daemon help' 查看可用命令。");
    process.exit(1);
  }

  const cli = new AgentBusCLI();
  await cli.executeCommand(args);
}

// 如果直接运行此文件，执行CLI
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(error => {
    console.error("CLI执行失败:", error);
    process.exit(1);
  });
}