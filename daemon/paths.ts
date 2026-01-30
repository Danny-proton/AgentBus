import path from "node:path";
import os from "node:os";
import {
  resolveConfigPath,
  resolveLogPaths,
  AGENTBUS_CONFIG_DIRS,
  AGENTBUS_SERVICE_DIRS,
  AGENTBUS_LOG_DIRS,
  AGENTBUS_ENV_VARS
} from "./constants.js";

/**
 * 解析用户主目录
 */
export function resolveHomeDir(env: Record<string, string | undefined> = process.env): string {
  const home = env.HOME || env.USERPROFILE || env.HOMEPATH;
  if (!home) {
    throw new Error("无法确定用户主目录");
  }
  return home;
}

/**
 * 解析AgentBus配置目录
 */
export function resolveAgentBusConfigDir(
  env: Record<string, string | undefined> = process.env,
): string {
  const envConfig = env[AGENTBUS_ENV_VARS.CONFIG_DIR];
  if (envConfig) {
    return envConfig;
  }
  
  const home = resolveHomeDir(env);
  const platform = process.platform;
  const configDir = AGENTBUS_CONFIG_DIRS[platform as keyof typeof AGENTBUS_CONFIG_DIRS];
  
  if (typeof configDir === "string") {
    return path.join(home, configDir);
  }
  
  // 默认配置
  return path.join(home, ".config/agentbus");
}

/**
 * 解析AgentBus日志目录
 */
export function resolveAgentBusLogDir(
  env: Record<string, string | undefined> = process.env,
): string {
  const envLogDir = env[AGENTBUS_ENV_VARS.LOG_DIR];
  if (envLogDir) {
    return envLogDir;
  }
  
  const home = resolveHomeDir(env);
  const platform = process.platform;
  const logDirs = AGENTBUS_LOG_DIRS[platform as keyof typeof AGENTBUS_LOG_DIRS];
  
  if (typeof logDirs === "object" && logDirs !== null) {
    // 对于不同平台选择合适的日志目录
    const logDir = (logDirs as any).user || (logDirs as any).system;
    if (logDir) {
      return path.join(home, logDir);
    }
  }
  
  // 默认日志目录
  return path.join(home, ".local/share/agentbus/logs");
}

/**
 * 解析服务状态目录
 */
export function resolveAgentBusStateDir(
  env: Record<string, string | undefined> = process.env,
): string {
  return resolveAgentBusConfigDir(env);
}

/**
 * 解析PID文件路径
 */
export function resolvePidFilePath(
  serviceName: string,
  env: Record<string, string | undefined> = process.env,
): string {
  const envPidFile = env[AGENTBUS_ENV_VARS.PID_FILE];
  if (envPidFile) {
    return envPidFile;
  }
  
  const stateDir = resolveAgentBusStateDir(env);
  return path.join(stateDir, `${serviceName}.pid`);
}

/**
 * 解析配置文件路径
 */
export function resolveAgentBusConfigFile(
  env: Record<string, string | undefined> = process.env,
): string {
  const home = resolveHomeDir(env);
  return resolveConfigPath(process.platform, home);
}

/**
 * 解析日志文件路径
 */
export function resolveAgentBusLogFiles(
  env: Record<string, string | undefined> = process.env,
): {
  stdoutPath: string;
  stderrPath: string;
  logDir: string;
} {
  const home = resolveHomeDir(env);
  return resolveLogPaths(process.platform, home);
}

/**
 * 解析服务配置目录路径
 */
export function resolveServiceConfigDir(
  env: Record<string, string | undefined> = process.env,
): string {
  const configDir = resolveAgentBusConfigDir(env);
  return path.join(configDir, "services");
}

/**
 * 解析系统特定的服务目录
 */
export function resolveSystemServiceDir(
  env: Record<string, string | undefined> = process.env,
  user: boolean = true,
): string {
  const home = resolveHomeDir(env);
  const platform = process.platform;
  const serviceDirs = AGENTBUS_SERVICE_DIRS[platform as keyof typeof AGENTBUS_SERVICE_DIRS];
  
  if (typeof serviceDirs === "object" && serviceDirs !== null) {
    let serviceDir: string | undefined;
    
    if (user) {
      serviceDir = (serviceDirs as any).user;
    } else {
      serviceDir = (serviceDirs as any).system;
    }
    
    if (serviceDir) {
      if (serviceDir.startsWith("/")) {
        // 系统路径
        return serviceDir;
      } else {
        // 用户路径
        return path.join(home, serviceDir);
      }
    }
  }
  
  // 默认路径
  if (platform === "linux") {
    return user 
      ? path.join(home, ".config/systemd/user")
      : "/etc/systemd/system";
  } else if (platform === "darwin") {
    return path.join(home, "Library/LaunchAgents");
  } else if (platform === "win32") {
    return path.join(process.env.PROGRAMFILES || "C:\\Program Files", "AgentBus", "Tasks");
  }
  
  // 通用默认路径
  return path.join(home, ".config/agentbus/services");
}

/**
 * 确保目录存在
 */
export async function ensureDirExists(dirPath: string): Promise<void> {
  const fs = await import("node:fs/promises");
  try {
    await fs.access(dirPath);
  } catch {
    await fs.mkdir(dirPath, { recursive: true });
  }
}

/**
 * 清理旧的日志文件
 */
export async function cleanupOldLogs(
  logDir: string,
  maxAge: number = 7 * 24 * 60 * 60 * 1000, // 7天
): Promise<void> {
  const fs = await import("node:fs/promises");
  const path = await import("node:path");
  
  try {
    const files = await fs.readdir(logDir);
    const now = Date.now();
    
    for (const file of files) {
      const filePath = path.join(logDir, file);
      const stats = await fs.stat(filePath);
      
      if (now - stats.mtime.getTime() > maxAge) {
        await fs.unlink(filePath);
      }
    }
  } catch {
    // 忽略错误
  }
}

/**
 * 获取系统信息
 */
export function getSystemInfo(): {
  platform: string;
  arch: string;
  hostname: string;
  cpus: number;
  totalMemory: number;
  uptime: number;
} {
  return {
    platform: os.platform(),
    arch: os.arch(),
    hostname: os.hostname(),
    cpus: os.cpus().length,
    totalMemory: os.totalmem(),
    uptime: os.uptime()
  };
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  return `${size.toFixed(2)} ${units[unitIndex]}`;
}

/**
 * 格式化时间间隔
 */
export function formatDuration(milliseconds: number): string {
  const seconds = Math.floor(milliseconds / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (days > 0) {
    return `${days}天 ${hours % 24}小时`;
  } else if (hours > 0) {
    return `${hours}小时 ${minutes % 60}分钟`;
  } else if (minutes > 0) {
    return `${minutes}分钟 ${seconds % 60}秒`;
  } else {
    return `${seconds}秒`;
  }
}