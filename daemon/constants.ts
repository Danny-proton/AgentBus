/**
 * AgentBus 守护进程常量定义
 */

// 默认服务名称
export const AGENTBUS_DEFAULT_SERVICE_NAME = "agentbus";
export const AGENTBUS_LEGACY_SERVICE_NAMES = [
  "agentbus",
  "moltbot",
  "gateway",
  "bot"
];

// 默认服务标签和描述
export const AGENTBUS_LAUNCH_AGENT_LABEL = "com.agentbus.service";
export const AGENTBUS_SYSTEMD_SERVICE_NAME = "agentbus.service";
export const AGENTBUS_SCHTASKS_NAME = "AgentBus Service";

export const AGENTBUS_SYSTEMD_UNIT_NAME = "agentbus.service";
export const AGENTBUS_SYSTEMD_USER_UNIT_NAME = "agentbus.service";

// 服务描述格式化
export function formatAgentBusServiceDescription(opts: {
  profile?: string;
  version?: string;
}): string {
  const parts = ["AgentBus Agent Communication Service"];
  if (opts.profile && opts.profile !== "default") {
    parts.push(`Profile: ${opts.profile}`);
  }
  if (opts.version) {
    parts.push(`Version: ${opts.version}`);
  }
  return parts.join(" - ");
}

// 路径配置
export const AGENTBUS_CONFIG_DIRS = {
  linux: ".config/agentbus",
  darwin: "Library/Application Support/AgentBus",
  win32: "AgentBus"
};

export const AGENTBUS_SERVICE_DIRS = {
  linux: {
    user: ".config/systemd/user",
    system: "/etc/systemd/system"
  },
  darwin: {
    user: "Library/LaunchAgents"
  },
  win32: {
    system: "System32\\Tasks\\AgentBus"
  }
};

export const AGENTBUS_LOG_DIRS = {
  linux: {
    user: ".local/share/agentbus/logs",
    system: "/var/log/agentbus"
  },
  darwin: {
    user: "Library/Logs/AgentBus"
  },
  win32: {
    system: "C:\\ProgramData\\AgentBus\\Logs"
  }
};

// 环境变量名称
export const AGENTBUS_ENV_VARS = {
  SERVICE_NAME: "AGENTBUS_SERVICE_NAME",
  SERVICE_VERSION: "AGENTBUS_SERVICE_VERSION",
  CONFIG_DIR: "AGENTBUS_CONFIG_DIR",
  LOG_DIR: "AGENTBUS_LOG_DIR",
  PID_FILE: "AGENTBUS_PID_FILE",
  SYSTEMD_UNIT: "AGENTBUS_SYSTEMD_UNIT",
  LAUNCHD_LABEL: "AGENTBUS_LAUNCHD_LABEL",
  SCHTASKS_NAME: "AGENTBUS_SCHTASKS_NAME",
  PROFILE: "AGENTBUS_PROFILE",
  LOG_LEVEL: "AGENTBUS_LOG_LEVEL",
  AUTO_RESTART: "AGENTBUS_AUTO_RESTART",
  MONITORING_ENABLED: "AGENTBUS_MONITORING_ENABLED"
};

// 默认配置值
export const AGENTBUS_DEFAULT_CONFIG = {
  serviceName: AGENTBUS_DEFAULT_SERVICE_NAME,
  autoRestart: true,
  restartDelay: 5000, // 5 seconds
  maxRetries: 3,
  logLevel: "info" as const,
  monitoring: {
    enabled: true,
    interval: 30000, // 30 seconds
    maxMemoryUsage: 512 * 1024 * 1024, // 512MB
    maxCpuUsage: 80 // 80%
  }
};

// 系统要求
export const SYSTEM_REQUIREMENTS = {
  linux: {
    systemd: {
      minVersion: "215",
      required: true
    }
  },
  darwin: {
    launchd: {
      minVersion: "10.6",
      required: true
    }
  },
  win32: {
    taskScheduler: {
      minVersion: "6.0",
      required: true
    }
  }
};

// 错误消息
export const ERROR_MESSAGES = {
  SYSTEM_NOT_SUPPORTED: "AgentBus守护进程不支持当前操作系统",
  SYSTEMD_NOT_AVAILABLE: "systemd不可用；Linux上需要systemd用户服务",
  LAUNCHCTL_NOT_AVAILABLE: "launchctl不可用；macOS上需要launchd",
  TASK_SCHEDULER_NOT_AVAILABLE: "任务调度器不可用；Windows上需要Task Scheduler",
  PERMISSION_DENIED: "权限不足，无法管理服务",
  SERVICE_INSTALL_FAILED: "服务安装失败",
  SERVICE_UNINSTALL_FAILED: "服务卸载失败",
  SERVICE_START_FAILED: "服务启动失败",
  SERVICE_STOP_FAILED: "服务停止失败",
  SERVICE_RESTART_FAILED: "服务重启失败",
  SERVICE_STATUS_UNKNOWN: "服务状态未知",
  CONFIG_FILE_NOT_FOUND: "配置文件未找到",
  INVALID_CONFIG: "配置文件格式无效",
  LOG_FILE_ERROR: "日志文件错误"
};

// 状态消息
export const STATUS_MESSAGES = {
  SERVICE_INSTALLED: "AgentBus服务已安装",
  SERVICE_UNINSTALLED: "AgentBus服务已卸载",
  SERVICE_STARTED: "AgentBus服务已启动",
  SERVICE_STOPPED: "AgentBus服务已停止",
  SERVICE_RESTARTED: "AgentBus服务已重启",
  SERVICE_STATUS_CHECKED: "AgentBus服务状态已检查",
  MONITORING_STARTED: "服务监控已启动",
  MONITORING_STOPPED: "服务监控已停止",
  HEALTH_CHECK_PASSED: "健康检查通过",
  HEALTH_CHECK_FAILED: "健康检查失败"
};

// 配置文件路径
export function resolveConfigPath(platform: string, homeDir: string): string {
  switch (platform) {
    case "linux":
      return `${homeDir}/.config/agentbus/config.json`;
    case "darwin":
      return `${homeDir}/Library/Application Support/AgentBus/config.json`;
    case "win32":
      return `${homeDir}/AgentBus/config.json`;
    default:
      return `${homeDir}/.agentbus/config.json`;
  }
}

// 日志文件路径
export function resolveLogPaths(platform: string, homeDir: string): {
  stdoutPath: string;
  stderrPath: string;
  logDir: string;
} {
  switch (platform) {
    case "linux":
      return {
        logDir: `${homeDir}/.local/share/agentbus/logs`,
        stdoutPath: `${homeDir}/.local/share/agentbus/logs/agentbus.log`,
        stderrPath: `${homeDir}/.local/share/agentbus/logs/agentbus.err.log`
      };
    case "darwin":
      return {
        logDir: `${homeDir}/Library/Logs/AgentBus`,
        stdoutPath: `${homeDir}/Library/Logs/AgentBus/agentbus.log`,
        stderrPath: `${homeDir}/Library/Logs/AgentBus/agentbus.err.log`
      };
    case "win32":
      return {
        logDir: `${homeDir}/AgentBus/Logs`,
        stdoutPath: `${homeDir}/AgentBus/Logs/agentbus.log`,
        stderrPath: `${homeDir}/AgentBus/Logs/agentbus.err.log`
      };
    default:
      return {
        logDir: `${homeDir}/.agentbus/logs`,
        stdoutPath: `${homeDir}/.agentbus/logs/agentbus.log`,
        stderrPath: `${homeDir}/.agentbus/logs/agentbus.err.log`
      };
  }
}