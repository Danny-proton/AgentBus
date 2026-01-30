import {
  installLaunchAgent,
  isLaunchAgentLoaded,
  readLaunchAgentProgramArguments,
  readLaunchAgentRuntime,
  restartLaunchAgent,
  stopLaunchAgent,
  uninstallLaunchAgent,
} from "./launchd.js";
import {
  installScheduledTask,
  isScheduledTaskInstalled,
  readScheduledTaskCommand,
  readScheduledTaskRuntime,
  restartScheduledTask,
  stopScheduledTask,
  uninstallScheduledTask,
} from "./schtasks.js";
import type { AgentBusServiceRuntime } from "./types.js";
import {
  installSystemdService,
  isSystemdServiceEnabled,
  readSystemdServiceExecStart,
  readSystemdServiceRuntime,
  restartSystemdService,
  stopSystemdService,
  uninstallSystemdService,
} from "./systemd.js";

export type AgentBusServiceInstallArgs = {
  env: Record<string, string | undefined>;
  stdout: NodeJS.WritableStream;
  programArguments: string[];
  workingDirectory?: string;
  environment?: Record<string, string | undefined>;
  description?: string;
  serviceName?: string;
};

export type AgentBusService = {
  label: string;
  loadedText: string;
  notLoadedText: string;
  install: (args: AgentBusServiceInstallArgs) => Promise<void>;
  uninstall: (args: {
    env: Record<string, string | undefined>;
    stdout: NodeJS.WritableStream;
  }) => Promise<void>;
  stop: (args: {
    env?: Record<string, string | undefined>;
    stdout: NodeJS.WritableStream;
  }) => Promise<void>;
  restart: (args: {
    env?: Record<string, string | undefined>;
    stdout: NodeJS.WritableStream;
  }) => Promise<void>;
  isLoaded: (args: { env?: Record<string, string | undefined> }) => Promise<boolean>;
  readCommand: (env: Record<string, string | undefined>) => Promise<{
    programArguments: string[];
    workingDirectory?: string;
    environment?: Record<string, string>;
    sourcePath?: string;
  } | null>;
  readRuntime: (env: Record<string, string | undefined>) => Promise<AgentBusServiceRuntime>;
};

/**
 * 解析AgentBus服务实例
 * 根据当前操作系统返回相应的服务管理器
 */
export function resolveAgentBusService(): AgentBusService {
  if (process.platform === "darwin") {
    return {
      label: "LaunchAgent",
      loadedText: "已加载",
      notLoadedText: "未加载",
      install: async (args) => {
        await installLaunchAgent(args);
      },
      uninstall: async (args) => {
        await uninstallLaunchAgent(args);
      },
      stop: async (args) => {
        await stopLaunchAgent({
          stdout: args.stdout,
          env: args.env,
        });
      },
      restart: async (args) => {
        await restartLaunchAgent({
          stdout: args.stdout,
          env: args.env,
        });
      },
      isLoaded: async (args) => isLaunchAgentLoaded(args),
      readCommand: readLaunchAgentProgramArguments,
      readRuntime: readLaunchAgentRuntime,
    };
  }

  if (process.platform === "linux") {
    return {
      label: "systemd",
      loadedText: "已启用",
      notLoadedText: "未启用",
      install: async (args) => {
        await installSystemdService(args);
      },
      uninstall: async (args) => {
        await uninstallSystemdService(args);
      },
      stop: async (args) => {
        await stopSystemdService({
          stdout: args.stdout,
          env: args.env,
        });
      },
      restart: async (args) => {
        await restartSystemdService({
          stdout: args.stdout,
          env: args.env,
        });
      },
      isLoaded: async (args) => isSystemdServiceEnabled(args),
      readCommand: readSystemdServiceExecStart,
      readRuntime: async (env) => await readSystemdServiceRuntime(env),
    };
  }

  if (process.platform === "win32") {
    return {
      label: "计划任务",
      loadedText: "已注册",
      notLoadedText: "未注册",
      install: async (args) => {
        await installScheduledTask(args);
      },
      uninstall: async (args) => {
        await uninstallScheduledTask(args);
      },
      stop: async (args) => {
        await stopScheduledTask({
          stdout: args.stdout,
          env: args.env,
        });
      },
      restart: async (args) => {
        await restartScheduledTask({
          stdout: args.stdout,
          env: args.env,
        });
      },
      isLoaded: async (args) => isScheduledTaskInstalled(args),
      readCommand: readScheduledTaskCommand,
      readRuntime: async (env) => await readScheduledTaskRuntime(env),
    };
  }

  throw new Error(`AgentBus守护进程不支持当前操作系统: ${process.platform}`);
}

/**
 * 创建AgentBus服务实例
 */
export function createAgentBusService(): AgentBusService {
  return resolveAgentBusService();
}

/**
 * 服务管理器类
 * 提供高级服务管理功能
 */
export class AgentBusServiceManager {
  private service: AgentBusService;

  constructor(service?: AgentBusService) {
    this.service = service || resolveAgentBusService();
  }

  /**
   * 获取服务标签
   */
  getLabel(): string {
    return this.service.label;
  }

  /**
   * 安装AgentBus服务
   */
  async install(args: AgentBusServiceInstallArgs): Promise<void> {
    console.log(`正在安装${this.service.label}服务...`);
    await this.service.install(args);
    console.log(`${this.service.label}服务安装完成`);
  }

  /**
   * 卸载AgentBus服务
   */
  async uninstall(args: {
    env: Record<string, string | undefined>;
    stdout: NodeJS.WritableStream;
  }): Promise<void> {
    console.log(`正在卸载${this.service.label}服务...`);
    await this.service.uninstall(args);
    console.log(`${this.service.label}服务卸载完成`);
  }

  /**
   * 停止AgentBus服务
   */
  async stop(args: {
    env?: Record<string, string | undefined>;
    stdout: NodeJS.WritableStream;
  }): Promise<void> {
    console.log(`正在停止${this.service.label}服务...`);
    await this.service.stop(args);
    console.log(`${this.service.label}服务已停止`);
  }

  /**
   * 重启AgentBus服务
   */
  async restart(args: {
    env?: Record<string, string | undefined>;
    stdout: NodeJS.WritableStream;
  }): Promise<void> {
    console.log(`正在重启${this.service.label}服务...`);
    await this.service.restart(args);
    console.log(`${this.service.label}服务已重启`);
  }

  /**
   * 检查服务是否已加载
   */
  async isLoaded(args: { env?: Record<string, string | undefined> }): Promise<boolean> {
    return await this.service.isLoaded(args);
  }

  /**
   * 读取服务配置命令
   */
  async readCommand(env: Record<string, string | undefined>) {
    return await this.service.readCommand(env);
  }

  /**
   * 读取服务运行时信息
   */
  async readRuntime(env: Record<string, string | undefined>) {
    return await this.service.readRuntime(env);
  }

  /**
   * 获取服务状态描述
   */
  getStatusText(isLoaded: boolean): string {
    return isLoaded ? this.service.loadedText : this.service.notLoadedText;
  }

  /**
   * 获取当前平台信息
   */
  getPlatformInfo(): {
    platform: string;
    service: string;
  } {
    return {
      platform: process.platform,
      service: this.service.label,
    };
  }
}

/**
 * 默认服务管理器实例
 */
export const defaultServiceManager = new AgentBusServiceManager();