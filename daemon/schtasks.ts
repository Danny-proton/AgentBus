import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import {
  AGENTBUS_SCHTASKS_NAME,
  formatAgentBusServiceDescription,
  AGENTBUS_ENV_VARS
} from "./constants.js";
import type { AgentBusServiceRuntime } from "./types.js";
import { resolveHomeDir, ensureDirExists } from "./paths.js";

const execFileAsync = promisify(execFile);

const formatLine = (label: string, value: string) => {
  return `${label}: ${value}`;
};

/**
 * 解析Windows任务计划程序任务名称
 */
function resolveScheduledTaskName(env: Record<string, string | undefined>): string {
  const override = env[AGENTBUS_ENV_VARS.SCHTASKS_NAME]?.trim();
  if (override) return override;
  return AGENTBUS_SCHTASKS_NAME;
}

/**
 * 构建XML任务定义
 */
export function buildScheduledTaskXml({
  taskName,
  description,
  programArguments,
  workingDirectory,
  environment,
  logFilePath,
  errorLogPath,
}: {
  taskName: string;
  description: string;
  programArguments: string[];
  workingDirectory?: string;
  environment?: Record<string, string | undefined>;
  logFilePath: string;
  errorLogPath: string;
}): string {
  const execPath = programArguments[0];
  const execArgs = programArguments.slice(1);
  
  const xml = `<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>${escapeXml(description)}</Description>
    <Date>${new Date().toISOString()}</Date>
    <Author>AgentBus</Author>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
    <BootTrigger>
      <Enabled>true</Enabled>
    </BootTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>${escapeXml(execPath)}</Command>
      ${execArgs.length > 0 ? `<Arguments>${escapeXml(execArgs.join(" "))}</Arguments>` : ""}
      ${workingDirectory ? `<WorkingDirectory>${escapeXml(workingDirectory)}</WorkingDirectory>` : ""}
    </Exec>
  </Actions>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <ContextData>
    <LogFile>${escapeXml(logFilePath)}</LogFile>
    <ErrorLog>${escapeXml(errorLogPath)}</ErrorLog>
  </ContextData>
</Task>`;
  
  return xml;
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
 * 执行schtasks命令
 */
async function execSchtasks(
  args: string[],
): Promise<{ stdout: string; stderr: string; code: number }> {
  try {
    const { stdout, stderr } = await execFileAsync("schtasks", args, {
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
 * 解析schtasks查询输出
 */
export function parseScheduledTaskQuery(output: string): {
  taskName?: string;
  status?: string;
  lastRun?: string;
  nextRun?: string;
  lastResult?: string;
  author?: string;
  taskToRun?: string;
} {
  const result: any = {};
  const lines = output.split("\n");
  
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    
    // 解析键值对
    const match = trimmed.match(/^(.+?):\s*(.+)$/);
    if (match) {
      const key = match[1].trim();
      const value = match[2].trim();
      
      switch (key.toLowerCase()) {
        case "taskname":
        case "task name":
          result.taskName = value;
          break;
        case "status":
          result.status = value;
          break;
        case "last run":
          result.lastRun = value;
          break;
        case "next run":
          result.nextRun = value;
          break;
        case "last result":
          result.lastResult = value;
          break;
        case "author":
          result.author = value;
          break;
        case "task to run":
        case "task":
          result.taskToRun = value;
          break;
      }
    }
  }
  
  return result;
}

/**
 * 检查Windows任务计划程序是否可用
 */
export async function isScheduledTaskAvailable(): Promise<boolean> {
  const res = await execSchtasks(["/query"]);
  return res.code === 0;
}

/**
 * 读取已安装的任务信息
 */
export async function readScheduledTaskCommand(
  env: Record<string, string | undefined>,
): Promise<{
  programArguments: string[];
  workingDirectory?: string;
  environment?: Record<string, string>;
  sourcePath?: string;
} | null> {
  try {
    const taskName = resolveScheduledTaskName(env);
    const res = await execSchtasks(["/query", "/tn", taskName, "/v", "/fo", "csv"]);
    
    if (res.code !== 0) return null;
    
    // 解析CSV输出
    const lines = res.stdout.split("\n");
    if (lines.length < 2) return null;
    
    const headers = lines[0].split(",").map(h => h.trim().replace(/"/g, ""));
    const values = lines[1].split(",").map(v => v.trim().replace(/"/g, ""));
    
    const taskInfo: any = {};
    headers.forEach((header, index) => {
      if (values[index]) {
        taskInfo[header.toLowerCase()] = values[index];
      }
    });
    
    const taskToRun = taskInfo["task to run"];
    if (!taskToRun) return null;
    
    // 解析命令和参数
    const parts = parseCommandLine(taskToRun);
    const programArguments = [parts.command, ...parts.args];
    
    return {
      programArguments,
      workingDirectory: taskInfo["start in"],
      environment: {},
      sourcePath: taskName,
    };
  } catch {
    return null;
  }
}

/**
 * 解析命令行字符串
 */
function parseCommandLine(commandLine: string): { command: string; args: string[] } {
  const parts: string[] = [];
  let current = "";
  let inQuotes = false;
  let quoteChar = "";
  
  for (let i = 0; i < commandLine.length; i++) {
    const char = commandLine[i];
    
    if (!inQuotes && char === '"') {
      inQuotes = true;
      quoteChar = char;
    } else if (inQuotes && char === quoteChar) {
      inQuotes = false;
      quoteChar = "";
    } else if (!inQuotes && char === " ") {
      if (current) {
        parts.push(current);
        current = "";
      }
    } else {
      current += char;
    }
  }
  
  if (current) {
    parts.push(current);
  }
  
  const command = parts[0] || "";
  const args = parts.slice(1);
  
  return { command, args };
}

/**
 * 读取任务运行时信息
 */
export async function readScheduledTaskRuntime(
  env: Record<string, string | undefined>,
): Promise<AgentBusServiceRuntime> {
  try {
    const taskName = resolveScheduledTaskName(env);
    const res = await execSchtasks(["/query", "/tn", taskName, "/v", "/fo", "csv"]);
    
    if (res.code !== 0) {
      return {
        status: "unknown",
        detail: (res.stderr || res.stdout).trim() || undefined,
        missingUnit: true,
      };
    }
    
    const parsed = parseScheduledTaskQuery(res.stdout);
    const status = parsed.status?.toLowerCase();
    let serviceStatus: "running" | "stopped" | "unknown" = "unknown";
    
    if (status === "running" || status === "enabled") {
      serviceStatus = "running";
    } else if (status === "disabled" || status === "stopped") {
      serviceStatus = "stopped";
    }
    
    return {
      status: serviceStatus,
      state: parsed.status,
      lastRunTime: parsed.lastRun,
      lastRunResult: parsed.lastResult,
      detail: `Task: ${parsed.taskName || taskName}`,
    };
  } catch (err) {
    return {
      status: "unknown",
      detail: String(err),
    };
  }
}

/**
 * 安装计划任务
 */
export async function installScheduledTask({
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
}): Promise<{ taskName: string }> {
  const taskName = resolveScheduledTaskName(env);
  
  // 创建日志目录
  const home = resolveHomeDir(env);
  const logDir = path.join(home, "AgentBus", "Logs");
  await ensureDirExists(logDir);
  
  const logFilePath = path.join(logDir, "agentbus.log");
  const errorLogPath = path.join(logDir, "agentbus.err.log");
  
  const serviceDescription =
    description ??
    formatAgentBusServiceDescription({
      profile: env.AGENTBUS_PROFILE,
      version: environment?.AGENTBUS_SERVICE_VERSION ?? env.AGENTBUS_SERVICE_VERSION,
    });
  
  // 构建XML任务定义
  const xmlContent = buildScheduledTaskXml({
    taskName,
    description: serviceDescription,
    programArguments,
    workingDirectory,
    environment,
    logFilePath,
    errorLogPath,
  });
  
  // 写入临时XML文件
  const tempXmlPath = path.join(logDir, `${taskName}.xml`);
  await fs.writeFile(tempXmlPath, xmlContent, "utf8");
  
  // 创建任务
  const create = await execSchtasks([
    "/create",
    "/tn", taskName,
    "/xml", tempXmlPath,
    "/f"  // 强制覆盖
  ]);
  
  if (create.code !== 0) {
    throw new Error(`schtasks创建失败: ${create.stderr || create.stdout}`.trim());
  }
  
  // 启动任务
  const start = await execSchtasks([
    "/run",
    "/tn", taskName
  ]);
  
  if (start.code !== 0) {
    throw new Error(`schtasks启动失败: ${start.stderr || start.stdout}`.trim());
  }
  
  stdout.write("\n");
  stdout.write(`${formatLine("已安装计划任务", taskName)}\n`);
  stdout.write(`${formatLine("日志", logFilePath)}\n`);
  
  return { taskName };
}

/**
 * 卸载计划任务
 */
export async function uninstallScheduledTask({
  env,
  stdout,
}: {
  env: Record<string, string | undefined>;
  stdout: NodeJS.WritableStream;
}): Promise<void> {
  const taskName = resolveScheduledTaskName(env);
  
  // 停止并删除任务
  const res = await execSchtasks([
    "/end",
    "/tn", taskName
  ]);
  
  // 忽略停止错误，继续删除
  const deleteRes = await execSchtasks([
    "/delete",
    "/tn", taskName,
    "/f"
  ]);
  
  if (deleteRes.code !== 0) {
    throw new Error(`schtasks删除失败: ${deleteRes.stderr || deleteRes.stdout}`.trim());
  }
  
  stdout.write(`${formatLine("已删除计划任务", taskName)}\n`);
}

/**
 * 停止计划任务
 */
export async function stopScheduledTask({
  stdout,
  env,
}: {
  stdout: NodeJS.WritableStream;
  env?: Record<string, string | undefined>;
}): Promise<void> {
  const taskName = resolveScheduledTaskName(env ?? {});
  
  const res = await execSchtasks([
    "/end",
    "/tn", taskName
  ]);
  
  if (res.code !== 0) {
    throw new Error(`schtasks停止失败: ${res.stderr || res.stdout}`.trim());
  }
  
  stdout.write(`${formatLine("已停止计划任务", taskName)}\n`);
}

/**
 * 重启计划任务
 */
export async function restartScheduledTask({
  stdout,
  env,
}: {
  stdout: NodeJS.WritableStream;
  env?: Record<string, string | undefined>;
}): Promise<void> {
  const taskName = resolveScheduledTaskName(env ?? {});
  
  // 先停止
  await execSchtasks(["/end", "/tn", taskName]);
  
  // 再启动
  const res = await execSchtasks([
    "/run",
    "/tn", taskName
  ]);
  
  if (res.code !== 0) {
    throw new Error(`schtasks重启失败: ${res.stderr || res.stdout}`.trim());
  }
  
  stdout.write(`${formatLine("已重启计划任务", taskName)}\n`);
}

/**
 * 检查计划任务是否已安装
 */
export async function isScheduledTaskInstalled(args: {
  env?: Record<string, string | undefined>;
}): Promise<boolean> {
  const taskName = resolveScheduledTaskName(args.env ?? {});
  const res = await execSchtasks(["/query", "/tn", taskName]);
  return res.code === 0;
}