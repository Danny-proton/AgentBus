#!/usr/bin/env node

/**
 * AgentBus 守护进程主入口
 */

import { AgentBusDaemon } from "./daemon.js";
import { createAgentBusDaemon } from "./daemon.js";
import { AgentBusCLI } from "./cli.js";
import { Diagnostics, createDiagnostics } from "./utils.js";

/**
 * 主函数
 */
async function main(): Promise<void> {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    // 如果没有参数，显示帮助并启动守护进程
    console.log("AgentBus守护进程");
    console.log("用法: agentbus-daemon <command>");
    console.log("输入 'agentbus-daemon help' 查看所有命令");
    return;
  }

  const command = args[0];

  try {
    switch (command) {
      case "daemon":
        await runDaemon(args.slice(1));
        break;
      case "cli":
        await runCLI(args.slice(1));
        break;
      case "diagnose":
        await runDiagnostics(args.slice(1));
        break;
      default:
        // 兼容旧版CLI用法
        const cli = new AgentBusCLI();
        await cli.executeCommand(args);
    }
  } catch (error) {
    console.error("执行失败:", error);
    process.exit(1);
  }
}

/**
 * 运行守护进程模式
 */
async function runDaemon(args: string[]): Promise<void> {
  const daemon = await createAgentBusDaemon();
  
  // 设置信号处理
  daemon.setupSignalHandlers();
  
  // 解析守护进程参数
  const daemonArgs = parseDaemonArgs(args);
  
  if (daemonArgs.action === "start") {
    await daemon.start();
    console.log("AgentBus守护进程已在后台运行...");
    
    // 保持进程运行
    process.on('SIGTERM', async () => {
      console.log("接收到停止信号...");
      await daemon.stop();
      process.exit(0);
    });
    
    process.on('SIGINT', async () => {
      console.log("接收到中断信号...");
      await daemon.stop();
      process.exit(0);
    });
    
    // 防止进程退出
    setInterval(() => {}, 1 << 30);
    
  } else if (daemonArgs.action === "stop") {
    await daemon.stopService();
  } else if (daemonArgs.action === "restart") {
    await daemon.restartService();
  } else if (daemonArgs.action === "status") {
    const status = await daemon.generateStatusReport();
    console.log(status);
  }
}

/**
 * 运行CLI模式
 */
async function runCLI(args: string[]): Promise<void> {
  const cli = new AgentBusCLI();
  await cli.executeCommand(args);
}

/**
 * 运行诊断模式
 */
async function runDiagnostics(args: string[]): Promise<void> {
  const diagnostics = createDiagnostics();
  
  console.log("开始执行诊断...");
  const result = await diagnostics.performFullDiagnostic();
  
  const report = diagnostics.generateDiagnosticReport(result);
  console.log(report);
  
  if (!result.overall) {
    process.exit(1);
  }
}

/**
 * 解析守护进程参数
 */
function parseDaemonArgs(args: string[]): {
  action: string;
  options: any;
} {
  let action = "start"; // 默认启动
  
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    
    if (arg === "start" || arg === "stop" || arg === "restart" || arg === "status") {
      action = arg;
    }
  }
  
  return {
    action,
    options: {}
  };
}

/**
 * 优雅关闭处理
 */
function setupGracefulShutdown(): void {
  const gracefulShutdown = async (signal: string) => {
    console.log(`\n接收到 ${signal} 信号，开始优雅关闭...`);
    
    // 这里可以添加清理逻辑
    // 例如: 关闭数据库连接、保存状态等
    
    process.exit(0);
  };

  process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
  process.on('SIGINT', () => gracefulShutdown('SIGINT'));
  process.on('SIGHUP', () => gracefulShutdown('SIGHUP'));
  
  process.on('uncaughtException', (error) => {
    console.error('未捕获的异常:', error);
    gracefulShutdown('UNCAUGHT_EXCEPTION');
  });
  
  process.on('unhandledRejection', (reason, promise) => {
    console.error('未处理的Promise拒绝:', reason);
    gracefulShutdown('UNHANDLED_REJECTION');
  });
}

// 设置优雅关闭
setupGracefulShutdown();

// 如果直接运行此文件
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(error => {
    console.error("启动失败:", error);
    process.exit(1);
  });
}