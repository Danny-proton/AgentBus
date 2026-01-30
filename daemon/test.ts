#!/usr/bin/env node

/**
 * AgentBus 守护进程功能测试
 */

import { AgentBusDaemon } from './daemon.js';
import { AgentBusServiceManager } from './service-manager.js';
import { ConfigManager } from './config.js';
import { createDiagnostics } from './utils.js';

async function testPlatformSupport() {
  console.log('=== 测试平台支持 ===');
  
  const manager = new AgentBusServiceManager();
  const platformInfo = manager.getPlatformInfo();
  
  console.log('平台信息:', platformInfo);
  
  if (platformInfo.supported) {
    console.log('✓ 平台支持正常');
  } else {
    console.log('✗ 平台不支持');
    return false;
  }
  
  return true;
}

async function testConfigManagement() {
  console.log('\n=== 测试配置管理 ===');
  
  try {
    const configManager = new ConfigManager();
    await configManager.load();
    
    const config = configManager.getConfig();
    console.log('配置加载成功:', config.name);
    
    const validation = configManager.validate();
    console.log('配置验证结果:', validation.isValid ? '✓ 通过' : '✗ 失败');
    
    if (!validation.isValid) {
      console.log('验证错误:', validation.errors);
    }
    
    return validation.isValid;
  } catch (error) {
    console.log('✗ 配置管理测试失败:', error);
    return false;
  }
}

async function testServiceManager() {
  console.log('\n=== 测试服务管理器 ===');
  
  try {
    const manager = new AgentBusServiceManager();
    const label = manager.getLabel();
    console.log('服务管理器标签:', label);
    
    // 测试服务状态读取（不需要实际安装服务）
    try {
      const runtime = await manager.readRuntime(process.env);
      console.log('服务状态读取成功:', runtime.status || 'unknown');
    } catch (error) {
      console.log('服务状态读取（预期错误）:', error.message);
    }
    
    return true;
  } catch (error) {
    console.log('✗ 服务管理器测试失败:', error);
    return false;
  }
}

async function testDiagnostics() {
  console.log('\n=== 测试诊断工具 ===');
  
  try {
    const diagnostics = createDiagnostics();
    const result = await diagnostics.performFullDiagnostic();
    
    console.log('诊断结果:');
    console.log(`  平台支持: ${result.platform ? '✓' : '✗'}`);
    console.log(`  系统依赖: ${result.dependencies ? '✓' : '✗'}`);
    console.log(`  权限检查: ${result.permissions ? '✓' : '✗'}`);
    console.log(`  配置检查: ${result.configuration ? '✓' : '✗'}`);
    console.log(`  服务检查: ${result.services ? '✓' : '✗'}`);
    console.log(`  日志检查: ${result.logs ? '✓' : '✗'}`);
    console.log(`  总体状态: ${result.overall ? '健康' : '需要关注'}`);
    
    return true;
  } catch (error) {
    console.log('✗ 诊断工具测试失败:', error);
    return false;
  }
}

async function testDaemonInitialization() {
  console.log('\n=== 测试守护进程初始化 ===');
  
  try {
    const daemon = new AgentBusDaemon();
    await daemon.initialize();
    console.log('✓ 守护进程初始化成功');
    
    const config = daemon.getConfig();
    console.log('配置加载成功:', config.name);
    
    const platformInfo = daemon.getPlatformInfo();
    console.log('平台信息:', platformInfo);
    
    return true;
  } catch (error) {
    console.log('✗ 守护进程初始化失败:', error);
    return false;
  }
}

async function runAllTests() {
  console.log('AgentBus 守护进程功能测试\n');
  
  const tests = [
    { name: '平台支持', test: testPlatformSupport },
    { name: '配置管理', test: testConfigManagement },
    { name: '服务管理器', test: testServiceManager },
    { name: '诊断工具', test: testDiagnostics },
    { name: '守护进程初始化', test: testDaemonInitialization }
  ];
  
  const results = [];
  
  for (const { name, test } of tests) {
    try {
      const result = await test();
      results.push({ name, passed: result });
    } catch (error) {
      console.log(`✗ ${name}测试异常:`, error);
      results.push({ name, passed: false });
    }
  }
  
  // 汇总结果
  console.log('\n=== 测试结果汇总 ===');
  const passed = results.filter(r => r.passed).length;
  const total = results.length;
  
  results.forEach(result => {
    console.log(`${result.passed ? '✓' : '✗'} ${result.name}`);
  });
  
  console.log(`\n通过率: ${passed}/${total} (${Math.round(passed/total*100)}%)`);
  
  if (passed === total) {
    console.log('\n🎉 所有测试通过！');
    process.exit(0);
  } else {
    console.log('\n⚠️  部分测试失败');
    process.exit(1);
  }
}

// 运行测试
if (import.meta.url === `file://${process.argv[1]}`) {
  runAllTests().catch(error => {
    console.error('测试执行失败:', error);
    process.exit(1);
  });
}