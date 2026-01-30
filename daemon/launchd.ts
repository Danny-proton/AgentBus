import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import {
  AGENTBUS_LAUNCH_AGENT_LABEL,
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
 * 解析LaunchAgent标签
 */
function resolveLaunchAgentLabel(args?: { env?: Record<string, string | undefined> }): string {
  const envLabel = args?.env?.[AGENTBUS_ENV_VARS.LAUNCHD_LABEL]?.trim();
  if (envLabel) return envLabel;
  return AGENTBUS_LAUNCH_AGENT_LABEL;
}

/**
 * 解析LaunchAgent plist文件路径
 */
function resolveLaunchAgentPlistPathForLabel(
  env: Record<string, string | undefined>,
  label: string,
): string {
  const home = toPosixPath(resolveHomeDir(env));
  return path.posix.join(home, "Library", "LaunchAgents", `${label}.plist`);
}

/**
 * 解析LaunchAgent plist文件路径
 */
export function resolveLaunchAgentPlistPath(env: Record<string, string | undefined>): string {
  const label = resolveLaunchAgentLabel({ env });
  return resolveLaunchAgentPlistPathForLabel(env, label);
}

/**
 * 解析日志文件路径
 */
export function resolveAgentBusLogPaths(env: Record<string, string | undefined>): {
  logDir: string;
  stdoutPath: string;
  stderrPath: string;
} {
  const home = resolveHomeDir(env);
  const logDir = path.join(home, "Library", "Logs", "AgentBus");
  return {
    logDir,
    stdoutPath: path.join(logDir, "agentbus.log"),
    stderrPath: path.join(logDir, "agentbus.err.log"),
  };
}

/**
 * 构建LaunchAgent plist内容
 */
export function buildLaunchAgentPlist({
  label = AGENTBUS_LAUNCH_AGENT_LABEL,
  comment,
  programArguments,
  workingDirectory,
  stdoutPath,
  stderrPath,
  environment,
}: {
  label?: string;
  comment?: string;
  programArguments: string[];
  workingDirectory?: string;
  stdoutPath: string;
  stderrPath: string;
  environment?: Record<string, string | undefined>;
}): string {
  const plist = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">',
    "<plist version=\"1.0\">",
    "<dict>",
    `  <key>Label</key>`,
    `  <string>${label}</string>`,
    ...(comment ? [`  <key>Comment</key>`, `  <string>${comment}</string>`] : []),
    `  <key>ProgramArguments</key>`,
    "<array>",
    ...programArguments.map(arg => `    <string>${escapeXml(arg)}</string>`),
    "</array>",
    ...(workingDirectory ? [`  <key>WorkingDirectory</key>`, `  <string>${escapeXml(workingDirectory)}</string>`] : []),
    `  <key>RunAtLoad</key>`,
    `<true/>`,
    `  <key>KeepAlive</key>`,
    `<true/>`,
    `  <key>StandardOutPath</key>`,
    `  <string>${escapeXml(stdoutPath)}</string>`,
    `  <key>StandardErrorPath</key>`,
    `  <string>${escapeXml(stderrPath)}</string>`,
    ...(environment ? [
      `  <key>EnvironmentVariables</key>`,
      "<dict>",
      ...Object.entries(environment).map(([key, value]) => [
        `    <key>${escapeXml(key)}</key>`,
        `    <string>${escapeXml(value || "")}</string>`
      ]).flat(),
      "</dict>"
    ] : []),
    `  <key>ProcessType</key>`,
    `<string>Background</string>`,
    `  <key>SoftResourceLimits</key>`,
    `<dict>`,
    `    <key>NumberOfFiles</key>`,
    `<integer>1024</integer>`,
    `  </dict>`,
    "</dict>",
    "</plist>"
  ].join("\n");
  
  return plist;
}

/**
 * XML转义
 */
function escapeXml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/**
 * 从plist文件读取程序参数
 */
export async function readLaunchAgentProgramArgumentsFromFile(
  plistPath: string,
): Promise<{
  programArguments: string[];
  workingDirectory?: string;
  environment?: Record<string, string>;
  sourcePath?: string;
} | null> {
  try {
    const content = await fs.readFile(plistPath, "utf8");
    
    // 简单的plist解析（只提取我们需要的字段）
    let programArguments: string[] = [];
    let workingDirectory = "";
    const environment: Record<string, string> = {};
    
    // 解析ProgramArguments
    const programArgsMatch = content.match(/<key>ProgramArguments<\/key>[\s\S]*?<array>([\s\S]*?)<\/array>/);
    if (programArgsMatch) {
      const argsContent = programArgsMatch[1];
      const stringMatches = argsContent.match(/<string>([\s\S]*?)<\/string>/g);
      if (stringMatches) {
        programArguments = stringMatches.map(match => 
          unescapeXml(match.replace(/<\/?string>/g, ""))
        );
      }
    }
    
    // 解析WorkingDirectory
    const workingDirMatch = content.match(/<key>WorkingDirectory<\/key>[\s\S]*?<string>([\s\S]*?)<\/string>/);
    if (workingDirMatch) {
      workingDirectory = unescapeXml(workingDirMatch[1]);
    }
    
    // 解析EnvironmentVariables
    const envMatch = content.match(/<key>EnvironmentVariables<\/key>[\s\S]*?<dict>([\s\S]*?)<\/dict>/);
    if (envMatch) {
      const envContent = envMatch[1];
      const keyMatches = envContent.match(/<key>([\s\S]*?)<\/key>[\s\S]*?<string>([\s\S]*?)<\/string>/g);
      if (keyMatches) {
        keyMatches.forEach(match => {
          const keyMatch = match.match(/<key>([\s\S]*?)<\/key>/);
          const valueMatch = match.match(/<string>([\s\S]*?)<\/string>/);
          if (keyMatch && valueMatch) {
            environment[unescapeXml(keyMatch[1])] = unescapeXml(valueMatch[1]);
          }
        });
      }
    }
    
    if (programArguments.length === 0) return null;
    
    return {
      programArguments,
      ...(workingDirectory ? { workingDirectory } : {}),
      ...(Object.keys(environment).length > 0 ? { environment } : {}),
      sourcePath: plistPath,
    };
  } catch {
    return null;
  }
}

/**
 * XML反转义
 */
function unescapeXml(text: string): string {
  return text
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, "\"")
    .replace(/&apos;/g, "'");
}

/**
 * 执行launchctl命令
 */
async function execLaunchctl(
  args: string[],
): Promise<{ stdout: string; stderr: string; code: number }> {
  try {
    const { stdout, stderr } = await execFileAsync("launchctl", args, {
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
 * 解析GUI域
 */
function resolveGuiDomain(): string {
  if (typeof process.getuid !== "function") return "gui/501";
  return `gui/${process.getuid()}`;
}

/**
 * Launchctl打印信息类型
 */
export type LaunchctlPrintInfo = {
  state?: string;
  pid?: number;
  lastExitStatus?: number;
  lastExitReason?: string;
};

/**
 * 解析launchctl print输出
 */
export function parseLaunchctlPrint(output: string): LaunchctlPrintInfo {
  const entries = parseKeyValueOutput(output, "=");
  const info: LaunchctlPrintInfo = {};
  
  const state = entries.state;
  if (state) info.state = state;
  
  const pidValue = entries.pid;
  if (pidValue) {
    const pid = Number.parseInt(pidValue, 10);
    if (Number.isFinite(pid)) info.pid = pid;
  }
  
  const exitStatusValue = entries["last exit status"];
  if (exitStatusValue) {
    const status = Number.parseInt(exitStatusValue, 10);
    if (Number.isFinite(status)) info.lastExitStatus = status;
  }
  
  const exitReason = entries["last exit reason"];
  if (exitReason) info.lastExitReason = exitReason;
  
  return info;
}

/**
 * 解析键值对输出
 */
function parseKeyValueOutput(output: string, separator: string = "="): Record<string, string> {
  const result: Record<string, string> = {};
  
  for (const line of output.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    
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
 * 检查LaunchAgent是否已加载
 */
export async function isLaunchAgentLoaded(args: {
  env?: Record<string, string | undefined>;
}): Promise<boolean> {
  const domain = resolveGuiDomain();
  const label = resolveLaunchAgentLabel({ env: args.env });
  const res = await execLaunchctl(["print", `${domain}/${label}`]);
  return res.code === 0;
}

/**
 * 检查LaunchAgent是否已列出
 */
export async function isLaunchAgentListed(args: {
  env?: Record<string, string | undefined>;
}): Promise<boolean> {
  const label = resolveLaunchAgentLabel({ env: args.env });
  const res = await execLaunchctl(["list"]);
  if (res.code !== 0) return false;
  return res.stdout.split(/\r?\n/).some((line) => line.trim().split(/\s+/).at(-1) === label);
}

/**
 * 检查LaunchAgent plist是否存在
 */
export async function launchAgentPlistExists(
  env: Record<string, string | undefined>,
): Promise<boolean> {
  try {
    const plistPath = resolveLaunchAgentPlistPath(env);
    await fs.access(plistPath);
    return true;
  } catch {
    return false;
  }
}

/**
 * 读取LaunchAgent运行时信息
 */
export async function readLaunchAgentRuntime(
  env: Record<string, string | undefined>,
): Promise<AgentBusServiceRuntime> {
  const domain = resolveGuiDomain();
  const label = resolveLaunchAgentLabel({ env });
  const res = await execLaunchctl(["print", `${domain}/${label}`]);
  
  if (res.code !== 0) {
    return {
      status: "unknown",
      detail: (res.stderr || res.stdout).trim() || undefined,
      missingUnit: true,
    };
  }
  
  const parsed = parseLaunchctlPrint(res.stdout || res.stderr || "");
  const plistExists = await launchAgentPlistExists(env);
  const state = parsed.state?.toLowerCase();
  const status = state === "running" || parsed.pid ? "running" : state ? "stopped" : "unknown";
  
  return {
    status,
    state: parsed.state,
    pid: parsed.pid,
    lastExitStatus: parsed.lastExitStatus,
    lastExitReason: parsed.lastExitReason,
    cachedLabel: !plistExists,
  };
}

/**
 * 读取LaunchAgent程序参数
 */
export async function readLaunchAgentProgramArguments(
  env: Record<string, string | undefined>,
): Promise<{
  programArguments: string[];
  workingDirectory?: string;
  environment?: Record<string, string>;
  sourcePath?: string;
} | null> {
  const plistPath = resolveLaunchAgentPlistPath(env);
  return readLaunchAgentProgramArgumentsFromFile(plistPath);
}

/**
 * 修复LaunchAgent引导
 */
export async function repairLaunchAgentBootstrap(args: {
  env?: Record<string, string | undefined>;
}): Promise<{ ok: boolean; detail?: string }> {
  const env = args.env ?? (process.env as Record<string, string | undefined>);
  const domain = resolveGuiDomain();
  const label = resolveLaunchAgentLabel({ env });
  const plistPath = resolveLaunchAgentPlistPath(env);
  
  const boot = await execLaunchctl(["bootstrap", domain, plistPath]);
  if (boot.code !== 0) {
    return { ok: false, detail: (boot.stderr || boot.stdout).trim() || undefined };
  }
  
  const kick = await execLaunchctl(["kickstart", "-k", `${domain}/${label}`]);
  if (kick.code !== 0) {
    return { ok: false, detail: (kick.stderr || kick.stdout).trim() || undefined };
  }
  
  return { ok: true };
}

/**
 * 安装LaunchAgent服务
 */
export async function installLaunchAgent({
  env,
  stdout,
  programArguments,
  workingDirectory,
  environment,
  description,
}: {
  env: Record<string, string | undefined>;
  stdout: NodeJS.WritableStream;
  programArguments: string[];
  workingDirectory?: string;
  environment?: Record<string, string | undefined>;
  description?: string;
}): Promise<{ plistPath: string }> {
  const { logDir, stdoutPath, stderrPath } = resolveAgentBusLogPaths(env);
  await ensureDirExists(logDir);
  
  const domain = resolveGuiDomain();
  const label = resolveLaunchAgentLabel({ env });
  const plistPath = resolveLaunchAgentPlistPathForLabel(env, label);
  
  await ensureDirExists(path.dirname(plistPath));
  
  const serviceDescription =
    description ??
    formatAgentBusServiceDescription({
      profile: env.AGENTBUS_PROFILE,
      version: environment?.AGENTBUS_SERVICE_VERSION ?? env.AGENTBUS_SERVICE_VERSION,
    });
  
  const plist = buildLaunchAgentPlist({
    label,
    comment: serviceDescription,
    programArguments,
    workingDirectory,
    stdoutPath,
    stderrPath,
    environment,
  });
  
  await fs.writeFile(plistPath, plist, "utf8");
  
  await execLaunchctl(["bootout", domain, plistPath]);
  await execLaunchctl(["unload", plistPath]);
  // launchd可以持久化"disabled"状态，即使在bootout + plist移除后；需要在bootstrap之前清除
  await execLaunchctl(["enable", `${domain}/${label}`]);
  
  const boot = await execLaunchctl(["bootstrap", domain, plistPath]);
  if (boot.code !== 0) {
    throw new Error(`launchctl bootstrap失败: ${boot.stderr || boot.stdout}`.trim());
  }
  
  await execLaunchctl(["kickstart", "-k", `${domain}/${label}`]);
  
  stdout.write("\n");
  stdout.write(`${formatLine("已安装LaunchAgent", plistPath)}\n`);
  stdout.write(`${formatLine("日志", stdoutPath)}\n`);
  
  return { plistPath };
}

/**
 * 卸载LaunchAgent服务
 */
export async function uninstallLaunchAgent({
  env,
  stdout,
}: {
  env: Record<string, string | undefined>;
  stdout: NodeJS.WritableStream;
}): Promise<void> {
  const domain = resolveGuiDomain();
  const label = resolveLaunchAgentLabel({ env });
  const plistPath = resolveLaunchAgentPlistPath(env);
  
  await execLaunchctl(["bootout", domain, plistPath]);
  await execLaunchctl(["unload", plistPath]);
  
  try {
    await fs.access(plistPath);
  } catch {
    stdout.write(`在${plistPath}处未找到LaunchAgent\n`);
    return;
  }
  
  const home = resolveHomeDir(env);
  const trashDir = path.join(home, ".Trash");
  const dest = path.join(trashDir, `${label}.plist`);
  
  try {
    await ensureDirExists(trashDir);
    await fs.rename(plistPath, dest);
    stdout.write(`${formatLine("已将LaunchAgent移到废纸篓", dest)}\n`);
  } catch {
    stdout.write(`LaunchAgent仍保留在${plistPath}处（无法移动）\n`);
  }
}

/**
 * 检查launchctl是否未加载
 */
function isLaunchctlNotLoaded(res: { stdout: string; stderr: string; code: number }): boolean {
  const detail = `${res.stderr || res.stdout}`.toLowerCase();
  return (
    detail.includes("no such process") ||
    detail.includes("could not find service") ||
    detail.includes("not found")
  );
}

/**
 * 停止LaunchAgent服务
 */
export async function stopLaunchAgent({
  stdout,
  env,
}: {
  stdout: NodeJS.WritableStream;
  env?: Record<string, string | undefined>;
}): Promise<void> {
  const domain = resolveGuiDomain();
  const label = resolveLaunchAgentLabel({ env });
  const res = await execLaunchctl(["bootout", `${domain}/${label}`]);
  
  if (res.code !== 0 && !isLaunchctlNotLoaded(res)) {
    throw new Error(`launchctl bootout失败: ${res.stderr || res.stdout}`.trim());
  }
  
  stdout.write(`${formatLine("已停止LaunchAgent", `${domain}/${label}`)}\n`);
}

/**
 * 重启LaunchAgent服务
 */
export async function restartLaunchAgent({
  stdout,
  env,
}: {
  stdout: NodeJS.WritableStream;
  env?: Record<string, string | undefined>;
}): Promise<void> {
  const domain = resolveGuiDomain();
  const label = resolveLaunchAgentLabel({ env });
  const res = await execLaunchctl(["kickstart", "-k", `${domain}/${label}`]);
  
  if (res.code !== 0) {
    throw new Error(`launchctl kickstart失败: ${res.stderr || res.stdout}`.trim());
  }
  
  stdout.write(`${formatLine("已重启LaunchAgent", `${domain}/${label}`)}\n`);
}