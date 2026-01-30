import fs from "node:fs/promises";
import path from "node:path";
import type { ServiceConfiguration, MonitoringConfig } from "./types.js";
import {
  AGENTBUS_DEFAULT_CONFIG,
  AGENTBUS_ENV_VARS,
  resolveAgentBusConfigFile,
  resolveAgentBusConfigDir,
  ensureDirExists
} from "./constants.js";

/**
 * AgentBus配置管理器
 */
export class ConfigManager {
  private configPath: string;
  private config: ServiceConfiguration;
  private monitoringConfig: MonitoringConfig;

  constructor(configPath?: string) {
    this.configPath = configPath || resolveAgentBusConfigFile();
    this.config = { ...AGENTBUS_DEFAULT_CONFIG } as ServiceConfiguration;
    this.monitoringConfig = { ...AGENTBUS_DEFAULT_CONFIG.monitoring };
  }

  /**
   * 加载配置
   */
  async load(): Promise<void> {
    try {
      const data = await fs.readFile(this.configPath, "utf8");
      const parsed = JSON.parse(data);
      
      // 合并默认配置和用户配置
      this.config = { ...AGENTBUS_DEFAULT_CONFIG, ...parsed };
      
      // 合并监控配置
      if (parsed.monitoring) {
        this.monitoringConfig = { ...AGENTBUS_DEFAULT_CONFIG.monitoring, ...parsed.monitoring };
        this.config.monitoring = this.monitoringConfig;
      }
      
      // 从环境变量加载配置
      this.loadFromEnvironment();
      
    } catch (error) {
      // 如果配置文件不存在，使用默认配置
      console.warn("配置文件不存在或无法读取，使用默认配置");
      this.loadFromEnvironment();
    }
  }

  /**
   * 从环境变量加载配置
   */
  private loadFromEnvironment(): void {
    const env = process.env;
    
    if (env[AGENTBUS_ENV_VARS.SERVICE_NAME]) {
      this.config.name = env[AGENTBUS_ENV_VARS.SERVICE_NAME];
    }
    
    if (env[AGENTBUS_ENV_VARS.LOG_LEVEL]) {
      this.config.logLevel = env[AGENTBUS_ENV_VARS.LOG_LEVEL] as any;
    }
    
    if (env[AGENTBUS_ENV_VARS.AUTO_RESTART]) {
      this.config.autoRestart = env[AGENTBUS_ENV_VARS.AUTO_RESTART] === "true";
    }
    
    if (env[AGENTBUS_ENV_VARS.MONITORING_ENABLED]) {
      this.monitoringConfig.enabled = env[AGENTBUS_ENV_VARS.MONITORING_ENABLED] === "true";
      this.config.monitoring = this.monitoringConfig;
    }
  }

  /**
   * 保存配置
   */
  async save(): Promise<void> {
    try {
      await ensureDirExists(path.dirname(this.configPath));
      await fs.writeFile(
        this.configPath,
        JSON.stringify(this.config, null, 2),
        "utf8"
      );
    } catch (error) {
      throw new Error(`保存配置失败: ${error}`);
    }
  }

  /**
   * 获取服务配置
   */
  getConfig(): ServiceConfiguration {
    return { ...this.config };
  }

  /**
   * 获取监控配置
   */
  getMonitoringConfig(): MonitoringConfig {
    return { ...this.monitoringConfig };
  }

  /**
   * 更新服务配置
   */
  updateConfig(updates: Partial<ServiceConfiguration>): void {
    this.config = { ...this.config, ...updates };
    
    // 如果更新了监控配置，同时更新monitoringConfig
    if (updates.monitoring) {
      this.monitoringConfig = { ...this.monitoringConfig, ...updates.monitoring };
      this.config.monitoring = this.monitoringConfig;
    }
  }

  /**
   * 更新监控配置
   */
  updateMonitoringConfig(updates: Partial<MonitoringConfig>): void {
    this.monitoringConfig = { ...this.monitoringConfig, ...updates };
    this.config.monitoring = this.monitoringConfig;
  }

  /**
   * 验证配置
   */
  validate(): { isValid: boolean; errors: string[] } {
    const errors: string[] = [];
    
    if (!this.config.name || this.config.name.trim() === "") {
      errors.push("服务名称不能为空");
    }
    
    if (!this.config.executablePath || this.config.executablePath.trim() === "") {
      errors.push("可执行文件路径不能为空");
    }
    
    if (this.config.restartDelay < 0) {
      errors.push("重启延迟不能为负数");
    }
    
    if (this.config.maxRetries < 0) {
      errors.push("最大重试次数不能为负数");
    }
    
    if (this.config.monitoring.enabled) {
      if (this.config.monitoring.interval <= 0) {
        errors.push("监控间隔必须大于0");
      }
      
      if (this.config.monitoring.maxMemoryUsage && this.config.monitoring.maxMemoryUsage <= 0) {
        errors.push("最大内存使用量必须大于0");
      }
      
      if (this.config.monitoring.maxCpuUsage && (this.config.monitoring.maxCpuUsage <= 0 || this.config.monitoring.maxCpuUsage > 100)) {
        errors.push("最大CPU使用率必须在1-100之间");
      }
    }
    
    return {
      isValid: errors.length === 0,
      errors
    };
  }

  /**
   * 创建默认配置文件
   */
  async createDefaultConfig(): Promise<void> {
    const defaultConfig: ServiceConfiguration = {
      ...AGENTBUS_DEFAULT_CONFIG,
      name: "agentbus",
      displayName: "AgentBus Agent Communication Service",
      description: "AgentBus守护进程服务，提供代理之间的通信功能",
      executablePath: "", // 用户需要设置
      arguments: [], // 用户需要设置
      autoRestart: true,
      restartDelay: 5000,
      maxRetries: 3,
      logLevel: "info",
      logFile: "", // 自动生成
      errorFile: "", // 自动生成
      monitoring: {
        enabled: true,
        interval: 30000,
        maxMemoryUsage: 512 * 1024 * 1024, // 512MB
        maxCpuUsage: 80
      }
    };
    
    this.config = defaultConfig;
    this.monitoringConfig = defaultConfig.monitoring;
    await this.save();
  }

  /**
   * 获取配置目录路径
   */
  getConfigDir(): string {
    return resolveAgentBusConfigDir();
  }

  /**
   * 获取配置文件路径
   */
  getConfigPath(): string {
    return this.configPath;
  }

  /**
   * 重置为默认配置
   */
  resetToDefaults(): void {
    this.config = { ...AGENTBUS_DEFAULT_CONFIG } as ServiceConfiguration;
    this.monitoringConfig = { ...AGENTBUS_DEFAULT_CONFIG.monitoring };
    this.config.monitoring = this.monitoringConfig;
  }
}

/**
 * 创建配置管理器实例
 */
export function createConfigManager(configPath?: string): ConfigManager {
  const manager = new ConfigManager(configPath);
  return manager;
}

/**
 * 全局配置管理器实例
 */
let globalConfigManager: ConfigManager | null = null;

/**
 * 获取全局配置管理器
 */
export async function getGlobalConfigManager(): Promise<ConfigManager> {
  if (!globalConfigManager) {
    globalConfigManager = new ConfigManager();
    await globalConfigManager.load();
  }
  return globalConfigManager;
}

/**
 * 重新初始化全局配置管理器
 */
export async function resetGlobalConfigManager(): Promise<void> {
  globalConfigManager = new ConfigManager();
  await globalConfigManager.load();
}