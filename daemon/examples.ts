#!/usr/bin/env node

/**
 * AgentBus 守护进程使用示例
 */

import { AgentBusDaemon } from './index.js';
import { createConfigManager } from './config.js';
import { AgentBusCLI } from './cli.js';

async function exampleBasicUsage() {
  console.log('=== 基本使用示例 ===');
  
  // 1. 创建守护进程实例
  const daemon = new AgentBusDaemon();
  
  // 2. 初始化
  await daemon.initialize();
  console.log('守护进程已初始化');
  
  // 3. 安装服务
  await daemon.installService({
    executablePath: '/usr/local/bin/node',
    arguments: ['--version'],
    description: 'Node.js 版本检查服务'
  });
  console.log('服务已安装');
  
  // 4. 启动服务
  await daemon.startService();
  console.log('服务已启动');
  
  // 5. 查看状态
  const status = await daemon.getDaemonStatus();
  console.log('服务状态:', status);
  
  // 6. 健康检查
  const health = await daemon.performHealthCheck();
  console.log('健康检查结果:', health);
  
  // 7. 停止服务
  await daemon.stopService();
  console.log('服务已停止');
}

async function exampleConfigManagement() {
  console.log('\n=== 配置管理示例 ===');
  
  const configManager = createConfigManager();
  
  // 加载配置
  await configManager.load();
  const config = configManager.getConfig();
  console.log('当前配置:', config);
  
  // 更新配置
  await configManager.updateConfig({
    logLevel: 'debug',
    autoRestart: false
  });
  
  // 保存配置
  await configManager.save();
  console.log('配置已更新并保存');
}

async function exampleCLI() {
  console.log('\n=== CLI 使用示例 ===');
  
  const cli = new AgentBusCLI();
  
  // 模拟CLI命令
  const args = ['status'];
  await cli.executeCommand(args);
}

async function exampleMonitoring() {
  console.log('\n=== 监控示例 ===');
  
  const daemon = new AgentBusDaemon();
  await daemon.initialize();
  
  // 启动监控
  await daemon.start();
  console.log('监控已启动');
  
  // 模拟监控一段时间
  setTimeout(async () => {
    const report = await daemon.generateStatusReport();
    console.log('监控报告:');
    console.log(report);
    
    await daemon.stop();
    console.log('监控已停止');
  }, 10000); // 10秒后停止
}

// 主函数
async function main() {
  try {
    console.log('AgentBus 守护进程示例\n');
    
    // 根据命令行参数选择示例
    const args = process.argv.slice(2);
    const example = args[0] || 'basic';
    
    switch (example) {
      case 'basic':
        await exampleBasicUsage();
        break;
      case 'config':
        await exampleConfigManagement();
        break;
      case 'cli':
        await exampleCLI();
        break;
      case 'monitor':
        await exampleMonitoring();
        break;
      case 'all':
        await exampleBasicUsage();
        await exampleConfigManagement();
        await exampleCLI();
        await exampleMonitoring();
        break;
      default:
        console.log('可用示例: basic, config, cli, monitor, all');
        console.log('用法: node examples.js <示例名称>');
    }
    
  } catch (error) {
    console.error('示例执行失败:', error);
    process.exit(1);
  }
}

// 如果直接运行此文件
if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}