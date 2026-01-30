/**
 * AgentBus 守护进程服务运行时信息
 */
export type AgentBusServiceRuntime = {
  status?: "running" | "stopped" | "unknown";
  state?: string;
  subState?: string;
  pid?: number;
  lastExitStatus?: number;
  lastExitReason?: string;
  lastRunResult?: string;
  lastRunTime?: string;
  detail?: string;
  cachedLabel?: boolean;
  missingUnit?: boolean;
};

/**
 * AgentBus服务安装参数
 */
export type AgentBusServiceInstallArgs = {
  env: Record<string, string | undefined>;
  stdout: NodeJS.WritableStream;
  programArguments: string[];
  workingDirectory?: string;
  environment?: Record<string, string | undefined>;
  description?: string;
  serviceName?: string;
};

/**
 * AgentBus服务实例
 */
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
 * 服务配置信息
 */
export type ServiceConfiguration = {
  name: string;
  displayName: string;
  description: string;
  executablePath: string;
  arguments: string[];
  workingDirectory?: string;
  environment?: Record<string, string>;
  autoRestart: boolean;
  restartDelay: number; // milliseconds
  maxRetries: number;
  logLevel: "error" | "warn" | "info" | "debug";
  logFile?: string;
  errorFile?: string;
};

/**
 * 守护进程状态
 */
export type DaemonStatus = {
  isRunning: boolean;
  service: AgentBusServiceRuntime;
  uptime?: number;
  memoryUsage?: NodeJS.MemoryUsage;
  cpuUsage?: NodeJS.CpuUsage;
};

/**
 * 监控配置
 */
export type MonitoringConfig = {
  enabled: boolean;
  interval: number; // milliseconds
  healthCheckUrl?: string;
  healthCheckCommand?: string;
  maxMemoryUsage?: number; // bytes
  maxCpuUsage?: number; // percentage
};