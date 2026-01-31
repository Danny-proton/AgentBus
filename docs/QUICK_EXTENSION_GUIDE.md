# AgentBus 扩展开发快速指南

> 简洁版 - 快速了解如何基于AgentBus开发扩展组件

## 🏗️ 核心架构

AgentBus采用三层架构:

```
启动入口 (start_agentbus.py)
    ↓
应用编排 (AgentBusApplication) - 统一管理所有子系统
    ↓
子系统层 - 插件/Agent/技能/Hook/自动化
```

## 🔌 三种扩展方式

### 1. 插件扩展 (最简单)

**用途**: 添加工具函数、注册事件钩子

**步骤**:
```python
# plugins/my_plugin/plugin.py
from plugins.core import AgentBusPlugin

class MyPlugin(AgentBusPlugin):
    NAME = "my_plugin"
    VERSION = "1.0.0"
    
    async def activate(self):
        # 注册工具
        self.register_tool(
            name="my_tool",
            description="我的工具",
            function=self.my_function
        )
        return True
    
    async def my_function(self, param: str):
        return {"result": f"处理: {param}"}
```

### 2. Agent扩展 (中等复杂)

**用途**: 创建自主智能体,执行复杂任务

**步骤**:
```python
# agents/my_agent.py
from agents.core.base import BaseAgent
from agents.core.types import AgentConfig, AgentMetadata

class MyAgent(BaseAgent):
    def __init__(self, config: AgentConfig):
        metadata = AgentMetadata(
            agent_id="my_agent",
            name="My Agent"
        )
        super().__init__(config, metadata)
    
    async def _handle_custom_task(self, task_type: str, params: dict):
        if task_type == "my_task":
            # 执行任务逻辑
            return {"success": True}
```

### 3. 技能扩展 (专业功能)

**用途**: 封装特定领域的能力(如GitHub操作、网页爬取)

**步骤**:
```python
# skills/my_skill.py
from skills.base import BaseSkill

class MySkill(BaseSkill):
    async def execute(self, action: str, parameters: dict):
        if action == "do_something":
            # 执行技能动作
            return {"success": True}
```

## 🌐 网页测试Agent示例

基于自动化系统开发网页测试Agent:

```python
from agents.core.base import BaseAgent
from automation.browser import BrowserAutomation

class WebTestAgent(BaseAgent):
    async def initialize(self):
        # 初始化浏览器
        self.browser = BrowserAutomation()
        await self.browser.start()
        return await super().initialize()
    
    async def _handle_custom_task(self, task_type: str, params: dict):
        if task_type == "test_page":
            # 1. 导航到页面
            await self.browser.navigate_to(params["url"])
            
            # 2. 查找元素
            element = await self.browser.find_element(
                selector=params["selector"]
            )
            
            # 3. 执行操作
            await self.browser.click_element(selector=params["selector"])
            
            # 4. 验证结果
            return {"success": True, "result": "测试通过"}
```

## 🛠️ 关键API

### 浏览器自动化
```python
browser = BrowserAutomation()
await browser.start()
await browser.navigate_to(url)
await browser.find_element(selector="...")
await browser.click_element(selector="...")
await browser.type_text(selector="...", value="...")
await browser.take_screenshot()
```

### Hook系统
```python
# 注册Hook
self.register_hook(
    event="message.process",
    handler=self.on_message,
    priority=10
)
```

### 工具注册
```python
self.register_tool(
    name="tool_name",
    description="工具描述",
    function=self.tool_function,
    parameters={"param1": {"type": "string"}}
)
```

## 📝 最佳实践

1. **插件开发**: 单一职责,完善错误处理
2. **Agent开发**: 正确管理生命周期,使用LLM决策
3. **自动化开发**: 使用显式等待,避免硬编码延迟
4. **测试**: 编写单元测试,使用headless=False调试

## 🚀 快速开始

```python
# 1. 创建Agent
config = AgentConfig(agent_id="test_001")
agent = WebTestAgent(config)

# 2. 初始化并启动
await agent.initialize()
await agent.start()

# 3. 执行任务
result = await agent.execute_task(
    task_type="test_page",
    parameters={"url": "https://example.com", "selector": "#button"}
)

# 4. 停止
await agent.stop()
```

## 📚 核心文件参考

- **插件基类**: `plugins/core.py::AgentBusPlugin`
- **Agent基类**: `agents/core/base.py::BaseAgent`
- **浏览器自动化**: `automation/browser.py::BrowserAutomation`
- **元素查找**: `automation/element_finder.py::ElementFinder`

---

**提示**: 详细文档请参考 `EXTENSION_DEVELOPMENT_GUIDE.md`
