# WebExplorer Agent

**自主网页遍历和测试Agent**

## 📖 概述

WebExplorer Agent 是一个基于 AgentBus 平台开发的自主网页探索Agent,能够:

- 🗺️ **自动建图**: 遍历未知网站,构建完整的页面状态图
- 💾 **文件系统存储**: 使用文件系统作为状态数据库(Atlas Memory)
- 🔄 **智能回溯**: 遇到死胡同自动回溯
- 🧪 **深度测试**: 基于探索结果生成测试用例
- 🎯 **LLM驱动**: 使用大语言模型进行页面分析和决策

## 🏗️ 架构

### 核心组件

```
WebExplorer Agent
├── AtlasManager Plugin      # 文件系统状态管理
├── BrowserManager Plugin    # 浏览器操作管理
├── PageAnalysis Skill       # 页面分析(LLM)
└── TrajectoryLabeling Skill # 轨迹标注(LLM)
```

### 数据结构

```
project_memory/              # Atlas根目录
├── index.json              # 全局索引
├── 00_Root/                # 根节点
│   ├── meta.json           # 元数据
│   ├── screenshot.png      # 截图
│   ├── links/              # 软链接(状态转换)
│   │   └── action_login -> ../01_Login/
│   ├── scripts/            # 导航脚本
│   │   └── nav_login.py
│   └── todos/              # 待办任务
│       └── task_001.json
└── 01_Login/               # 登录页节点
    └── ...
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install playwright
playwright install chromium
```

### 2. 基础使用

```python
from agents.web_explorer import WebExplorerAgent, ExplorerConfig

# 创建配置
config = ExplorerConfig(
    start_url="http://example.com",
    max_depth=3,
    max_nodes=20
)

# 创建并运行Agent
agent = WebExplorerAgent(config)
await agent.initialize()

result = await agent.start_exploration()
print(f"探索完成,共发现 {result['total_nodes']} 个页面")

await agent.shutdown()
```

### 3. 运行示例

```bash
# 基础探索示例
python examples/web_explorer_usage.py basic

# 自定义配置示例
python examples/web_explorer_usage.py custom

# 监控状态示例
python examples/web_explorer_usage.py monitor

# 分析结果示例
python examples/web_explorer_usage.py analyze
```

## 📋 配置选项

### ExplorerConfig

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `start_url` | str | "" | 起始URL |
| `max_depth` | int | 5 | 最大探索深度 |
| `max_nodes` | int | 100 | 最大节点数 |
| `max_iterations` | int | 1000 | 最大迭代次数 |
| `atlas_root` | str | "project_memory" | Atlas根目录 |
| `headless` | bool | False | 是否无头模式 |
| `model_provider` | str | "openai" | LLM提供商 |
| `model_name` | str | "gpt-4" | 模型名称 |

## 🔄 工作流程

### 拓荒循环 (Exploration Loop)

```
1. LOCATING    - 定位当前状态(计算DOM指纹)
2. ANALYZING   - 分析页面(LLM生成探索任务)
3. DECIDING    - 决策下一步(从任务队列选择)
4. ACTING      - 执行动作(点击/输入/导航)
5. REFLECTING  - 反思结果(LLM判断是否有意义)
6. 循环或回溯
```

### 深测循环 (Testing Loop)

```
1. 扫描测试想法
2. 瞬移到目标状态
3. 执行测试
4. 生成报告
```

## 📊 输出结果

### Atlas结构

探索完成后,会在 `project_memory/` 目录生成:

- **index.json**: 全局索引,包含所有节点信息
- **节点目录**: 每个页面状态一个目录
- **软链接**: 表示状态间的转换关系
- **脚本文件**: 可独立执行的导航脚本

### 示例输出

```json
{
  "total_nodes": 15,
  "total_edges": 18,
  "max_depth_reached": 3,
  "atlas_path": "/path/to/project_memory"
}
```

## 🎯 使用场景

1. **网站测试**: 自动发现所有页面和功能
2. **爬虫开发**: 快速了解网站结构
3. **回归测试**: 生成可重复执行的导航脚本
4. **安全测试**: 发现隐藏页面和功能点

## 🔧 高级功能

### 自定义LLM

```python
config = ExplorerConfig(
    model_provider="anthropic",
    model_name="claude-3-opus",
    temperature=0.5
)
```

### 监控探索进度

```python
# 定期检查状态
status = await agent.get_status()
print(f"当前节点: {status['current_node']}")
print(f"已探索: {status['nodes_explored']}")
```

### 分析Atlas

```python
import json
from pathlib import Path

index = json.loads(Path("project_memory/index.json").read_text())
print(f"总节点数: {index['statistics']['total_nodes']}")
```

## 📚 相关文档

- [技术PRD](../WIP/PRD_TECHNICAL.md) - 详细的技术设计文档
- [数据协议](../WIP/DATA_SCHEMA.md) - 文件系统结构规范
- [API设计](../WIP/API_DESIGN.md) - 组件接口定义
- [测试需求](../WIP/TESTING_REQUIREMENTS.md) - 测试规范

## ⚠️ 注意事项

1. **LLM依赖**: 当前版本的PageAnalysis和TrajectoryLabeling使用模拟数据,需要集成实际的LLM服务
2. **软链接权限**: Windows上创建软链接可能需要管理员权限,已提供JSON Fallback方案
3. **浏览器资源**: 长时间运行可能占用较多内存,建议设置合理的 `max_nodes` 限制
4. **网络超时**: 对于慢速网站,建议增加 `page_load_timeout` 值

## 🐛 已知限制

- [ ] 深测循环功能待完善
- [ ] 回溯逻辑需要实际实现浏览器后退
- [ ] LLM调用需要集成真实服务
- [ ] 循环检测机制待增强

## 🤝 贡献

欢迎提交Issue和Pull Request!

## 📄 许可证

MIT License
