---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 3044022013fa3e7fc87fec0f71db3ad8082da06544aa76fb995ac2fa0ea2dfd1c36babc6022039aa3a500724081a3267b7574080647aaf6cbbaeec7628a661564132a0ca276f
    ReservedCode2: 304402202ab845b2c89696da34b92581165f758e401fe5a8c265baaf9f2e710fe77aba600220637c48d9e00d35f009281baf9d3089102d20f1e8adcb58cbf29082ce6351dd70
---

# AgentBus CLI 增强功能使用指南

## 概述

AgentBus CLI 增强版是基于Moltbot CLI架构构建的高级命令行界面，提供了完整的系统管理功能。

## 快速开始

### 安装和初始化

```bash
# 进入项目目录
cd /workspace/agentbus

# 运行演示脚本
python cli/demo.py

# 查看帮助信息
python -m agentbus.cli.main --help

# 检查系统健康状态
python -m agentbus.cli.main health
```

## 主要功能模块

### 1. 配置管理 (`config`)

配置管理功能提供了档案管理、配置操作、导入导出等完整功能。

#### 档案管理
```bash
# 创建配置档案
agentbus config profile-create production --base=development

# 列出所有档案
agentbus config profile-list

# 切换档案
agentbus config profile-switch production

# 删除档案
agentbus config profile-delete production
```

#### 配置操作
```bash
# 设置配置值
agentbus config set database.host localhost --profile=production
agentbus config set database.port 3306 --profile=production

# 获取配置值
agentbus config get database.host --profile=production
agentbus config get database.port --format=json

# 列出所有配置
agentbus config list --profile=production

# 删除配置
agentbus config delete database.test_key --profile=production
```

#### 导入导出
```bash
# 导出配置
agentbus config export --output=production_config.json --format=json
agentbus config export --output=production_config.yaml --format=yaml

# 导入配置
agentbus config import production_config.json --profile=production

# 合并或替换配置
agentbus config import new_config.json --profile=production --merge
agentbus config import new_config.json --profile=production --replace
```

#### 配置管理
```bash
# 验证配置
agentbus config validate --profile=production

# 重置配置
agentbus config reset --profile=production

# 备份配置
agentbus config backup --profile=production

# 列出备份
agentbus config backup-list

# 恢复备份
agentbus config backup-restore backup_20231201_120000
```

### 2. 浏览器管理 (`browser`)

浏览器管理提供了浏览器控制、页面操作、元素操作等功能。

#### 浏览器控制
```bash
# 启动浏览器
agentbus browser start --headless --profile=default
agentbus browser start --proxy=127.0.0.1:8080 --timeout=30000

# 停止浏览器
agentbus browser stop

# 重启浏览器
agentbus browser restart --headless

# 查看浏览器状态
agentbus browser status
```

#### 页面操作
```bash
# 导航到URL
agentbus browser navigate https://example.com

# 截取屏幕截图
agentbus browser screenshot --output=screenshot.png
agentbus browser screenshot --output=full_page.png --full-page

# 执行JavaScript脚本
agentbus browser eval "document.title"
agentbus browser eval "document.querySelector('title').textContent"

# 获取页面信息
agentbus browser info --json-format
```

#### 元素操作
```bash
# 查找元素
agentbus browser find "#login-button" --by=css
agentbus browser find "//button[@id='submit']" --by=xpath

# 点击元素
agentbus browser click "#login-button" --by=css

# 填写表单
agentbus browser fill-form username=admin password=secret
```

#### 标签管理
```bash
# 新建标签页
agentbus browser tab-new https://example.com

# 关闭标签页
agentbus browser tab-close 0

# 列出标签页
agentbus browser tabs --json-format

# 查看当前页面信息
agentbus browser info
```

#### 代理设置
```bash
# 设置代理
agentbus browser proxy-set http://proxy.example.com:8080
```

### 3. 渠道管理 (`channel`)

渠道管理提供了渠道配置、连接管理、日志查看等功能。

#### 基础操作
```bash
# 列出渠道
agentbus channel list --status=connected
agentbus channel list --format=json

# 添加渠道
agentbus channel add discord --type=discord --name="Production Discord"

# 删除渠道
agentbus channel remove discord

# 查看渠道详情
agentbus channel info discord
```

#### 连接管理
```bash
# 连接渠道
agentbus channel connect discord --account=prod_account

# 断开渠道
agentbus channel disconnect discord --account=prod_account

# 连接所有渠道
agentbus channel connect-all

# 断开所有渠道
agentbus channel disconnect-all
```

#### 高级操作
```bash
# 测试渠道连接
agentbus channel test discord --account=prod_account

# 重启渠道
agentbus channel restart discord

# 获取渠道日志
agentbus channel logs discord --limit=100 --json-format

# 更新渠道配置
agentbus channel update discord --name="Updated Discord" --enabled

# 克隆渠道
agentbus channel clone discord discord_backup --name="Discord Backup"
```

#### 状态和统计
```bash
# 查看渠道状态
agentbus channel status discord

# 查看渠道系统统计
agentbus channel stats
```

### 4. 任务调度 (`scheduler`)

任务调度提供了任务管理、执行控制、状态监控等功能。

#### 任务管理
```bash
# 添加任务
agentbus scheduler add daily-backup "python backup.py" "0 2 * * *" --description="Daily backup"

# 列出任务
agentbus scheduler list --status=running
agentbus scheduler list --format=json

# 查看任务详情
agentbus scheduler info daily-backup
```

#### 任务控制
```bash
# 启用任务
agentbus scheduler enable daily-backup

# 禁用任务
agentbus scheduler disable daily-backup

# 立即执行任务
agentbus scheduler run-now daily-backup

# 暂停任务
agentbus scheduler pause daily-backup

# 恢复任务
agentbus scheduler resume daily-backup

# 取消运行中的任务
agentbus scheduler cancel daily-backup
```

#### 任务更新
```bash
# 更新任务
agentbus scheduler update daily-backup --command="python new_backup.py" --cron="0 3 * * *"
agentbus scheduler update daily-backup --priority=high --timeout=3600

# 删除任务
agentbus scheduler delete daily-backup
```

#### 监控和日志
```bash
# 查看任务状态
agentbus scheduler status daily-backup

# 查看任务日志
agentbus scheduler logs daily-backup --limit=50
agentbus scheduler logs daily-backup --json-format

# 清除任务日志
agentbus scheduler clear-logs daily-backup

# 查看调度器状态
agentbus scheduler status
```

#### 配置管理
```bash
# 导出任务配置
agentbus scheduler export --output=tasks.json

# 导入任务配置
agentbus scheduler import-config tasks.json --replace
```

### 5. 插件管理 (`plugin`)

插件管理提供了插件发现、启用禁用、详情查看等功能。

#### 基础操作
```bash
# 列出插件
agentbus plugin list --status=active --format=json

# 启用插件
agentbus plugin enable github-integration

# 禁用插件
agentbus plugin disable github-integration

# 重新加载插件
agentbus plugin reload github-integration

# 卸载插件
agentbus plugin unload github-integration
```

#### 详细信息
```bash
# 查看插件详情
agentbus plugin info github-integration

# 查看插件统计
agentbus plugin stats
```

#### 配置管理
```bash
# 导出插件配置
agentbus plugin export --output=plugins.json

# 导入插件配置
agentbus plugin import-config plugins.json
```

### 6. 系统管理 (`main`)

系统级命令用于监控和管理整个系统。

#### 系统状态
```bash
# 查看系统状态
agentbus status

# 输出详细状态到文件
agentbus status --output=system_status.json

# 健康检查
agentbus health

# 查看版本信息
agentbus version
```

## 高级功能

### 1. 高级命令解析

支持复杂的命令语法和智能解析：

```bash
# 多级命令
agentbus "config.profile.create production --base=development"

# 混合选项格式
agentbus browser start -h --proxy=127.0.0.1:8080

# 自动类型转换
agentbus config set app.timeout 30000  # 自动识别为数字
agentbus config set app.enabled true   # 自动识别为布尔值
```

### 2. 输出格式控制

支持多种输出格式：

```bash
# 表格格式（默认）
agentbus channel list

# JSON格式
agentbus channel list --format=json

# 控制台友好格式
agentbus config list --format=table
```

### 3. 批量操作

支持批量处理：

```bash
# 批量连接渠道
agentbus channel connect-all

# 批量启用插件
agentbus plugin enable-all --status=inactive

# 批量重启浏览器
agentbus browser restart-all
```

### 4. 配置驱动

支持基于配置文件的行为定制：

```bash
# 使用配置文件
agentbus --config-dir=/path/to/config main

# 环境变量支持
export AGENTBUS_CONFIG_DIR=/path/to/config
agentbus status
```

## 错误处理

CLI提供了完善的错误处理和用户友好的错误信息：

```bash
# 详细的错误信息
$ agentbus channel connect nonexistent
❌ 渠道管理器未初始化

# 调试信息
$ agentbus --debug plugin enable github-integration
[DEBUG] 正在初始化插件管理器...
[ERROR] 插件加载失败: Plugin not found

# 操作确认
$ agentbus config reset --profile=production
⚠️ 确认重置配置档案 'production'？这将清除所有配置项！
Are you sure? [y/N]: y
✅ 配置已重置
```

## 性能优化

### 1. 异步操作

所有命令都支持异步执行：

```python
# 异步命令执行
async def execute_command():
    result = await commands.start_browser(headless=True)
    return result
```

### 2. 智能缓存

配置和状态信息智能缓存：

```bash
# 状态缓存（减少重复查询）
agentbus status && agentbus status  # 第二次使用缓存
```

### 3. 资源管理

自动资源清理和释放：

```python
# 自动资源清理
@contextmanager
async def browser_context():
    browser = BrowserAutomation()
    try:
        await browser.start()
        yield browser
    finally:
        await browser.stop()
```

## 扩展性

### 1. 自定义命令

可以轻松添加新的命令模块：

```python
# 添加自定义命令
@click.group()
def custom():
    """自定义命令"""
    pass

@custom.command()
def my_command():
    """我的自定义命令"""
    click.echo("自定义命令执行")
```

### 2. 插件系统

支持通过插件扩展CLI功能：

```python
# CLI插件示例
class CLIModule:
    def register_commands(self, cli_group):
        cli_group.add_command(self.custom_command)
```

## 最佳实践

### 1. 命令组织

按照功能模块组织命令：

```bash
# 配置相关
agentbus config ...

# 渠道相关
agentbus channel ...

# 浏览器相关
agentbus browser ...
```

### 2. 错误处理

始终检查命令执行结果：

```bash
# 检查状态码
agentbus health && echo "系统健康" || echo "系统异常"
```

### 3. 日志管理

定期清理日志和备份配置：

```bash
# 定期备份
agentbus config backup && agentbus plugin export

# 清理日志
agentbus scheduler clear-logs old-task
```

## 故障排查

### 1. 常见问题

#### 渠道连接失败
```bash
# 检查配置
agentbus config validate --profile=production

# 测试连接
agentbus channel test discord

# 查看日志
agentbus channel logs discord --limit=100
```

#### 浏览器启动失败
```bash
# 检查浏览器安装
which google-chrome || which chromium-browser

# 使用默认配置
agentbus browser start --profile=default

# 查看详细错误
agentbus --debug browser start
```

#### 任务调度问题
```bash
# 检查调度器状态
agentbus scheduler status

# 查看任务日志
agentbus scheduler logs problematic-task

# 重新启用任务
agentbus scheduler disable problematic-task
agentbus scheduler enable problematic-task
```

### 2. 调试模式

启用详细调试信息：

```bash
# 启用调试模式
agentbus --debug --verbose status

# 调试特定模块
agentbus --debug browser start
```

### 3. 状态输出

输出详细状态用于故障排查：

```bash
# 完整系统状态
agentbus status --output=debug.json

# 特定模块状态
agentbus scheduler status --output=scheduler_debug.json
agentbus channel logs discord --json-format --limit=200
```

## 总结

AgentBus CLI 增强版提供了完整、强大、易用的命令行界面，支持系统配置、渠道管理、浏览器自动化、任务调度和插件管理等所有核心功能。通过合理使用这些命令，可以高效地管理整个AgentBus系统。