import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import {
  AGENTBUS_SYSTEMD_SERVICE_NAME,
  AGENTBUS_SYSTEMD_USER_UNIT_NAME,
  formatAgentBusServiceDescription,
  AGENTBUS_ENV_VARS
} from "./constants.js";
import type { AgentBusServiceRuntime } from "./types.js";
import { resolveHomeDir, ensureDirExists } from "./paths.js";

const execFileAsync = promisify(execFile);

const toPosixPath = (value: string) => value.replace(/\\/g, "/");

const formatLine = (label: string, value: string) => {
  return `${label}: ${value}`;
};

/**
 * 解析systemd单元文件路径
 */
function resolveSystemdUnitPathForName(
  env: Record<string, string | undefined>,
  name: string,
): string {
  const home = toPosixPath(resolveHomeDir(env));
  return path.posix.join(home, ".config", "systemd", "user", `${name}.service`);
}

/**
 * 解析systemd服务名称
 */
function resolveSystemdServiceName(env: Record<string, string | undefined>): string {
  const override = env[AGENTBUS_ENV_VARS.SYSTEMD_UNIT]?.trim();
  if (override) {
    return override.endsWith(".service") ? override.slice(0, -".service".length) : override;
  }
  return AGENTBUS_SYSTEMD_SERVICE_NAME.replace(".service", "");
}

/**
 * 解析systemd单元文件路径
 */
function resolveSystemdUnitPath(env: Record<string, string | undefined>): string {
  return resolveSystemdUnitPathForName(env, resolveSystemdServiceName(env));
}

/**
 * 构建systemd单元文件内容
 */
export function buildSystemdUnit({
  description,
  programArguments,
  workingDirectory,
  environment,
  serviceName,
}: {
  description: string;
  programArguments: string[];
  workingDirectory?: string;
  environment?: Record<string, string | undefined>;
  serviceName?: string;
}): string {
  const execStart = programArguments.map(arg => `"${arg}"`).join(" ");
  const unit = [
    "[Unit]",
    `Description=${description}`,
    "Documentation=https://agentbus.dev/docs",
    "",
    "[Service]",
    `Type=simple`,
    `ExecStart=${execStart}`,
    ...(workingDirectory ? [`WorkingDirectory=${workingDirectory}`] : []),
    ...(environment ? Object.entries(environment).map(([key, value]) => 
      `Environment="${key}=${value}"`) : []),
    "Restart=always",
    "RestartSec=10",
    "StandardOutput=journal",
    "StandardError=journal",
    "SyslogIdentifier=agentbus",
    "",
    "[Install]",
    "WantedBy=default.target",
    ""
  ].join("\n");
  
  return unit;
}

/**
 * 解析systemd环境变量赋值
 */
export function parseSystemdEnvAssignment(envLine: string): { key: string; value: string } | null {
  const match = envLine.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/);
  if (!match) return null;
  
  const key = match[1];
  let value = match[2];
  
  // 移除引号
  if ((value.startsWith('"') && value.endsWith('"')) || 
      (value.startsWith("'") && value.endsWith("'"))) {
    value = value.slice(1, -1);
  }
  
  return { key, value };
}

/**
 * 解析systemd ExecStart命令
 */
export function parseSystemdExecStart(execStart: string): string[] {
  const args: string[] = [];
  let current = "";
  let inQuotes = false;
  let quoteChar = "";
  
  for (let i = 0; i < execStart.length; i++) {
    const char = execStart[i];
    
    if (!inQuotes && (char === '"' || char === "'")) {
      inQuotes = true;
      quoteChar = char;
    } else if (inQuotes && char === quoteChar) {
      inQuotes = false;
      quoteChar = "";
    } else if (!inQuotes && char === " ") {
      if (current) {
        args.push(current);
        current = "";
      }
    } else {
      current += char;
    }
  }
  
  if (current) {
    args.push(current);
  }
  
  return args;
}

/**
 * 解析键值对输出
 */
export function parseKeyValueOutput(output: string, separator: string = "="): Record<string, string> {
  const result: Record<string, string> = {};
  
  for (const line of output.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    
    const separatorIndex = trimmed.indexOf(separator);
    if (separatorIndex === -1) continue;
    
    const key = trimmed.slice(0, separatorIndex).trim();
    const value = trimmed.slice(separatorIndex + 1).trim();
    
    if (key) {
      result[key.toLowerCase()] = value;
    }
  }
  
  return result;
}

/**
 * 执行systemctl命令
 */
async function execSystemctl(
  args: string[],
): Promise<{ stdout: string; stderr: string; code: number }> {
  try {
    const { stdout, stderr } = await execFileAsync("systemctl", args, {
      encoding: "utf8",
    });
    return {
      stdout: String(stdout ?? ""),
      stderr: String(stderr ?? ""),
      code: 0,
    };
  } catch (error) {
    const e = error as {
      stdout?: unknown;
      stderr?: unknown;
      code?: unknown;
      message?: unknown;
    };
    return {
      stdout: typeof e.stdout === "string" ? e.stdout : "",
      stderr:
        typeof e.stderr === "string" ? e.stderr : typeof e.message === "string" ? e.message : "",
      code: typeof e.code === "number" ? e.code : 1,
    };
  }
}

/**
 * 检查systemd用户服务是否可用
 */
export async function isSystemdUserServiceAvailable(): Promise<boolean> {
  const res = await execSystemctl(["--user", "status"]);
  if (res.code === 0) return true;
  
  const detail = `${res.stderr} ${res.stdout}`.toLowerCase();
  if (!detail) return false;
  
  return !(
    detail.includes("not found") ||
    detail.includes("failed to connect") ||
    detail.includes("not been booted") ||
    detail.includes("no such file or directory") ||
    detail.includes("not supported")
  );
}

/**
 * 断言systemd可用
 */
async function assertSystemdAvailable() {
  const res = await execSystemctl(["--user", "status"]);
  if (res.code === 0) return;
  
  const detail = res.stderr || res.stdout;
  if (detail.toLowerCase().includes("not found")) {
    throw new Error("systemctl不可用；Linux上需要systemd用户服务");
  }
  throw new Error(`systemctl --user不可用: ${detail || "未知错误"}`.trim());
}

/**
 * 读取systemd服务ExecStart信息
 */
export async function readSystemdServiceExecStart(
  env: Record<string, string | undefined>,
): Promise<{
  programArguments: string[];
  workingDirectory?: string;
  environment?: Record<string, string>;
  sourcePath?: string;
} | null> {
  const unitPath = resolveSystemdUnitPath(env);
  try {
    const content = await fs.readFile(unitPath, "utf8");
    let execStart = "";
    let workingDirectory = "";
    const environment: Record<string, string> = {};
    
    for (const rawLine of content.split("\n")) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) continue;
      
      if (line.startsWith("ExecStart=")) {
        execStart = line.slice("ExecStart=".length).trim();
      } else if (line.startsWith("WorkingDirectory=")) {
        workingDirectory = line.slice("WorkingDirectory=".length).trim();
      } else if (line.startsWith("Environment=")) {
        const raw = line.slice("Environment=".length).trim();
        const parsed = parseSystemdEnvAssignment(raw);
        if (parsed) environment[parsed.key] = parsed.value;
      }
    }
    
    if (!execStart) return null;
    
    const programArguments = parseSystemdExecStart(execStart);
    return {
      programArguments,
      ...(workingDirectory ? { workingDirectory } : {}),
      ...(Object.keys(environment).length > 0 ? { environment } : {}),
      sourcePath: unitPath,
    };
  } catch {
    return null;
  }
}

/**
 * Systemd服务信息类型
 */
export type SystemdServiceInfo = {
  activeState?: string;
  subState?: string;
  mainPid?: number;
  execMainStatus?: number;
  execMainCode?: string;
};

/**
 * 解析systemd show输出
 */
export function parseSystemdShow(output: string): SystemdServiceInfo {
  const entries = parseKeyValueOutput(output, "=");
  const info: SystemdServiceInfo = {};
  
  const activeState = entries.activestate;
  if (activeState) info.activeState = activeState;
  
  const subState = entries.substate;
  if (subState) info.subState = subState;
  
  const mainPidValue = entries.mainpid;
  if (mainPidValue) {
    const pid = Number.parseInt(mainPidValue, 10);
    if (Number.isFinite(pid) && pid > 0) info.mainPid = pid;
  }
  
  const execMainStatusValue = entries.execmainstatus;
  if (execMainStatusValue) {
    const status = Number.parseInt(execMainStatusValue, 10);
    if (Number.isFinite(status)) info.execMainStatus = status;
  }
  
  const execMainCode = entries.execmaincode;
  if (execMainCode) info.execMainCode = execMainCode;
  
  return info;
}

/**
 * 安装systemd服务
 */
export async function installSystemdService({
  env,
  stdout,
  programArguments,
  workingDirectory,
  environment,
  description,
  serviceName,
}: {
  env: Record<string, string | undefined>;
  stdout: NodeJS.WritableStream;
  programArguments: string[];
  workingDirectory?: string;
  environment?: Record<string, string | undefined>;
  description?: string;
  serviceName?: string;
}): Promise<{ unitPath: string }> {
  await assertSystemdAvailable();
  
  const unitPath = resolveSystemdUnitPath(env);
  await ensureDirExists(path.dirname(unitPath));
  
  const serviceDescription =
    description ??
    formatAgentBusServiceDescription({
      profile: env.AGENTBUS_PROFILE,
      version: environment?.AGENTBUS_SERVICE_VERSION ?? env.AGENTBUS_SERVICE_VERSION,
    });
  
  const unit = buildSystemdUnit({
    description: serviceDescription,
    programArguments,
    workingDirectory,
    environment,
    serviceName,
  });
  
  await fs.writeFile(unitPath, unit, "utf8");
  
  const serviceNameResolved = serviceName || resolveSystemdServiceName(env);
  const unitName = `${serviceNameResolved}.service`;
  
  const reload = await execSystemctl(["--user", "daemon-reload"]);
  if (reload.code !== 0) {
    throw new Error(`systemctl daemon-reload失败: ${reload.stderr || reload.stdout}`.trim());
  }
  
  const enable = await execSystemctl(["--user", "enable", unitName]);
  if (enable.code !== 0) {
    throw new Error(`systemctl enable失败: ${enable.stderr || enable.stdout}`.trim());
  }
  
  const restart = await execSystemctl(["--user", "restart", unitName]);
  if (restart.code !== 0) {
    throw new Error(`systemctl restart失败: ${restart.stderr || restart.stdout}`.trim());
  }
  
  stdout.write("\n");
  stdout.write(`${formatLine("已安装systemd服务", unitPath)}\n`);
  return { unitPath };
}

/**
 * 卸载systemd服务
 */
export async function uninstallSystemdService({
  env,
  stdout,
}: {
  env: Record<string, string | undefined>;
  stdout: NodeJS.WritableStream;
}): Promise<void> {
  await assertSystemdAvailable();
  
  const serviceNameResolved = resolveSystemdServiceName(env);
  const unitName = `${serviceNameResolved}.service`;
  
  await execSystemctl(["--user", "disable", "--now", unitName]);
  
  const unitPath = resolveSystemdUnitPath(env);
  try {
    await fs.unlink(unitPath);
    stdout.write(`${formatLine("已移除systemd服务", unitPath)}\n`);
  } catch {
    stdout.write(`在${unitPath}处未找到systemd服务\n`);
  }
}

/**
 * 停止systemd服务
 */
export async function stopSystemdService({
  stdout,
  env,
}: {
  stdout: NodeJS.WritableStream;
  env?: Record<string, string | undefined>;
}): Promise<void> {
  await assertSystemdAvailable();
  
  const serviceNameResolved = resolveSystemdServiceName(env ?? {});
  const unitName = `${serviceNameResolved}.service`;
  
  const res = await execSystemctl(["--user", "stop", unitName]);
  if (res.code !== 0) {
    throw new Error(`systemctl stop失败: ${res.stderr || res.stdout}`.trim());
  }
  
  stdout.write(`${formatLine("已停止systemd服务", unitName)}\n`);
}

/**
 * 重启systemd服务
 */
export async function restartSystemdService({
  stdout,
  env,
}: {
  stdout: NodeJS.WritableStream;
  env?: Record<string, string | undefined>;
}): Promise<void> {
  await assertSystemdAvailable();
  
  const serviceNameResolved = resolveSystemdServiceName(env ?? {});
  const unitName = `${serviceNameResolved}.service`;
  
  const res = await execSystemctl(["--user", "restart", unitName]);
  if (res.code !== 0) {
    throw new Error(`systemctl restart失败: ${res.stderr || res.stdout}`.trim());
  }
  
  stdout.write(`${formatLine("已重启systemd服务", unitName)}\n`);
}

/**
 * 检查systemd服务是否启用
 */
export async function isSystemdServiceEnabled(args: {
  env?: Record<string, string | undefined>;
}): Promise<boolean> {
  await assertSystemdAvailable();
  
  const serviceNameResolved = resolveSystemdServiceName(args.env ?? {});
  const unitName = `${serviceNameResolved}.service`;
  
  const res = await execSystemctl(["--user", "is-enabled", unitName]);
  return res.code === 0;
}

/**
 * 读取systemd服务运行时信息
 */
export async function readSystemdServiceRuntime(
  env: Record<string, string | undefined> = process.env as Record<string, string | undefined>,
): Promise<AgentBusServiceRuntime> {
  try {
    await assertSystemdAvailable();
  } catch (err) {
    return {
      status: "unknown",
      detail: String(err),
    };
  }
  
  const serviceNameResolved = resolveSystemdServiceName(env);
  const unitName = `${serviceNameResolved}.service`;
  
  const res = await execSystemctl([
    "--user",
    "show",
    unitName,
    "--no-page",
    "--property",
    "ActiveState,SubState,MainPID,ExecMainStatus,ExecMainCode",
  ]);
  
  if (res.code !== 0) {
    const detail = (res.stderr || res.stdout).trim();
    const missing = detail.toLowerCase().includes("not found");
    
    return {
      status: missing ? "stopped" : "unknown",
      detail: detail || undefined,
      missingUnit: missing,
    };
  }
  
  const parsed = parseSystemdShow(res.stdout || "");
  const activeState = parsed.activeState?.toLowerCase();
  const status = activeState === "active" ? "running" : activeState ? "stopped" : "unknown";
  
  return {
    status,
    state: parsed.activeState,
    subState: parsed.subState,
    pid: parsed.mainPid,
    lastExitStatus: parsed.execMainStatus,
    lastExitReason: parsed.execMainCode,
  };
}