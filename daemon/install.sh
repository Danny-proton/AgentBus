#!/bin/bash

# AgentBus 守护进程安装和启动脚本

set -e

echo "=== AgentBus 守护进程安装脚本 ==="

# 检查操作系统
OS="$(uname -s)"
case "${OS}" in
    Linux*)     PLATFORM=Linux;;
    Darwin*)    PLATFORM=macOS;;
    CYGWIN*|MINGW*|MSYS*) PLATFORM=Windows;;
    *)          PLATFORM="UNKNOWN:${OS}"
esac

echo "检测到操作系统: ${PLATFORM}"

# 检查Node.js版本
if ! command -v node &> /dev/null; then
    echo "错误: 未找到Node.js，请先安装Node.js 14或更高版本"
    exit 1
fi

NODE_VERSION=$(node -v | sed 's/v//')
REQUIRED_VERSION="14.0.0"

if ! node -e "process.exit(process.version.slice(1).localeCompare('$REQUIRED_VERSION', undefined, {numeric: true}) >= 0 ? 0 : 1)"; then
    echo "错误: Node.js版本过低，需要14.0.0或更高版本，当前版本: $NODE_VERSION"
    exit 1
fi

echo "Node.js版本检查通过: $NODE_VERSION"

# 检查必要的系统工具
case "${PLATFORM}" in
    Linux)
        if ! command -v systemctl &> /dev/null; then
            echo "错误: 未找到systemd，Linux系统需要systemd支持"
            exit 1
        fi
        echo "systemd检查通过"
        ;;
    macOS)
        if ! command -v launchctl &> /dev/null; then
            echo "错误: 未找到launchctl，macOS系统需要launchd支持"
            exit 1
        fi
        echo "launchd检查通过"
        ;;
    Windows)
        if ! command -v schtasks &> /dev/null; then
            echo "错误: 未找到schtasks，Windows系统需要Task Scheduler支持"
            exit 1
        fi
        echo "Task Scheduler检查通过"
        ;;
esac

# 安装依赖
echo "安装Node.js依赖..."
npm install

# 构建项目
echo "构建TypeScript项目..."
npm run build

# 创建配置目录
echo "创建配置目录..."
case "${PLATFORM}" in
    Linux)
        CONFIG_DIR="$HOME/.config/agentbus"
        ;;
    macOS)
        CONFIG_DIR="$HOME/Library/Application Support/AgentBus"
        ;;
    Windows)
        CONFIG_DIR="$HOME/AgentBus"
        ;;
esac

mkdir -p "$CONFIG_DIR"
echo "配置目录: $CONFIG_DIR"

# 复制示例配置
if [ -f "example-config.json" ]; then
    cp example-config.json "$CONFIG_DIR/config.json"
    echo "已复制示例配置文件"
fi

# 创建日志目录
case "${PLATFORM}" in
    Linux)
        LOG_DIR="$HOME/.local/share/agentbus/logs"
        ;;
    macOS)
        LOG_DIR="$HOME/Library/Logs/AgentBus"
        ;;
    Windows)
        LOG_DIR="$HOME/AgentBus/Logs"
        ;;
esac

mkdir -p "$LOG_DIR"
echo "日志目录: $LOG_DIR"

# 运行诊断
echo "运行系统诊断..."
node dist/index.js diagnose

echo ""
echo "=== 安装完成 ==="
echo "配置文件: $CONFIG_DIR/config.json"
echo "日志目录: $LOG_DIR"
echo ""
echo "使用方法:"
echo "  启动守护进程: node dist/index.js daemon start"
echo "  查看状态: node dist/index.js daemon status"
echo "  安装服务: node dist/index.js cli install <可执行文件路径>"
echo "  健康检查: node dist/index.js cli health"
echo "  查看帮助: node dist/index.js cli help"