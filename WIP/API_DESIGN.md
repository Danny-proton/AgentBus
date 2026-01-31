# WebExplorer Agent - API设计

**组件接口定义**

---

## 1. AtlasManager Plugin API

### 1.1 ensure_state

**功能**: 确保状态节点存在

```python
async def ensure_state(
    self,
    url: str,
    dom_fingerprint: str,
    screenshot_path: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**参数**:
- `url`: 页面URL
- `dom_fingerprint`: DOM指纹字符串
- `screenshot_path`: 截图文件路径
- `metadata`: 可选的额外元数据

**返回**:
```python
{
    "node_id": str,        # 节点ID (Hash)
    "node_path": str,      # 节点目录绝对路径
    "is_new": bool,        # 是否新创建
    "meta_file": str       # meta.json文件路径
}
```

**异常**:
- `FileSystemError`: 文件系统操作失败
- `ValidationError`: 参数验证失败

---

### 1.2 link_state

**功能**: 创建状态间的软链接

```python
async def link_state(
    self,
    source_node_id: str,
    action_name: str,
    target_node_id: str
) -> bool
```

**参数**:
- `source_node_id`: 源节点ID
- `action_name`: 动作名称(用作链接名)
- `target_node_id`: 目标节点ID

**返回**:
- `bool`: 是否创建成功

**异常**:
- `NodeNotFoundError`: 节点不存在
- `LinkExistsError`: 链接已存在

---

### 1.3 manage_todos

**功能**: 管理待办任务

```python
async def manage_todos(
    self,
    node_id: str,
    mode: Literal["push", "pop"],
    tasks: Optional[List[Dict[str, Any]]] = None
) -> Union[List[Dict[str, Any]], bool]
```

**参数**:
- `node_id`: 节点ID
- `mode`: "push"添加任务, "pop"获取任务
- `tasks`: 任务列表(push模式必需)

**返回**:
- push模式: `bool` 是否成功
- pop模式: `List[Dict]` 任务列表

**任务格式**:
```python
{
    "id": str,
    "selector": str,
    "action": str,
    "parameters": dict,
    "priority": int,
    "reason": str,
    "is_destructive": bool
}
```

---

### 1.4 get_path_to_node

**功能**: 获取从根节点到目标节点的路径

```python
async def get_path_to_node(
    self,
    target_node_id: str
) -> List[Dict[str, Any]]
```

**返回**:
```python
[
    {
        "node_id": str,
        "action": str,
        "script_path": str
    },
    ...
]
```

---

## 2. BrowserManager Plugin API

### 2.1 execute_intent

**功能**: 执行模糊意图指令

```python
async def execute_intent(
    self,
    intent: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**参数**:
- `intent`: 模糊指令,如"点击登录按钮"
- `context`: 上下文信息

**返回**:
```python
{
    "success": bool,
    "action_type": str,           # "click" | "type" | "navigate"
    "selector": str,              # 实际使用的选择器
    "screenshot_before": str,     # 操作前截图路径
    "screenshot_after": str,      # 操作后截图路径
    "dom_before": dict,           # 操作前DOM
    "dom_after": dict,            # 操作后DOM
    "error": Optional[str]
}
```

**异常**:
- `IntentParseError`: 意图解析失败
- `ElementNotFoundError`: 元素未找到
- `BrowserError`: 浏览器操作失败

---

### 2.2 save_script

**功能**: 保存操作历史为脚本

```python
async def save_script(
    self,
    script_path: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool
```

**参数**:
- `script_path`: 脚本保存路径
- `metadata`: 脚本元数据

**返回**:
- `bool`: 是否保存成功

**生成的脚本格式**:
```python
"""
脚本名称: {name}
描述: {description}
创建时间: {created_at}
"""

from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # 操作步骤
        await page.goto("https://example.com")
        await page.click("#login-btn")
        # ...
        
        await browser.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

### 2.3 replay_teleport

**功能**: 执行脚本链,瞬移到目标状态

```python
async def replay_teleport(
    self,
    script_paths: List[str]
) -> Dict[str, Any]
```

**参数**:
- `script_paths`: 脚本路径列表,按执行顺序

**返回**:
```python
{
    "success": bool,
    "executed_scripts": List[str],
    "final_url": str,
    "final_screenshot": str,
    "error": Optional[str]
}
```

---

### 2.4 clear_history

**功能**: 清空操作历史缓存

```python
async def clear_history(self) -> None
```

---

## 3. PageAnalysis Skill API

### 3.1 execute

**功能**: 分析页面并生成探索任务

```python
async def execute(
    self,
    action: str,
    parameters: Dict[str, Any]
) -> Dict[str, Any]
```

**参数**:
```python
{
    "screenshot_path": str,
    "dom_tree": dict,
    "url": str
}
```

**返回**:
```python
{
    "summary": str,
    "frontier_tasks": [
        {
            "selector": str,
            "action": str,
            "reason": str,
            "priority": int,
            "is_destructive": bool
        }
    ],
    "test_ideas": [
        {
            "name": str,
            "description": str,
            "type": str
        }
    ]
}
```

---

## 4. TrajectoryLabeling Skill API

### 4.1 execute

**功能**: 判断动作意义并生成标签

```python
async def execute(
    self,
    action: str,
    parameters: Dict[str, Any]
) -> Dict[str, Any]
```

**参数**:
```python
{
    "screenshot_before": str,
    "action_description": str,
    "screenshot_after": str,
    "dom_before": dict,
    "dom_after": dict
}
```

**返回**:
```python
{
    "is_meaningful": bool,
    "semantic_label": str,
    "script_name": str,
    "confidence": float
}
```

---

## 5. WebExplorer Agent API

### 5.1 start_exploration

**功能**: 启动拓荒循环

```python
async def start_exploration(
    self,
    start_url: str,
    max_depth: int = 5,
    max_nodes: int = 100
) -> Dict[str, Any]
```

**参数**:
- `start_url`: 起始URL
- `max_depth`: 最大深度
- `max_nodes`: 最大节点数

**返回**:
```python
{
    "total_nodes": int,
    "total_edges": int,
    "max_depth_reached": int,
    "atlas_path": str
}
```

---

### 5.2 start_testing

**功能**: 启动深测循环

```python
async def start_testing(
    self,
    atlas_path: str
) -> Dict[str, Any]
```

**参数**:
- `atlas_path`: Atlas目录路径

**返回**:
```python
{
    "total_tests": int,
    "passed": int,
    "failed": int,
    "report_path": str
}
```

---

### 5.3 get_status

**功能**: 获取Agent状态

```python
async def get_status(self) -> Dict[str, Any]
```

**返回**:
```python
{
    "state": str,              # 当前状态
    "current_node": str,       # 当前节点ID
    "nodes_explored": int,     # 已探索节点数
    "tasks_pending": int,      # 待处理任务数
    "uptime": float           # 运行时间(秒)
}
```

---

## 6. 错误码定义

```python
class WebExplorerError(Exception):
    """基础错误类"""
    pass

class FileSystemError(WebExplorerError):
    """文件系统错误"""
    code = 1001

class NodeNotFoundError(WebExplorerError):
    """节点不存在"""
    code = 1002

class LinkExistsError(WebExplorerError):
    """链接已存在"""
    code = 1003

class BrowserError(WebExplorerError):
    """浏览器错误"""
    code = 2001

class IntentParseError(WebExplorerError):
    """意图解析失败"""
    code = 2002

class ElementNotFoundError(WebExplorerError):
    """元素未找到"""
    code = 2003

class SkillExecutionError(WebExplorerError):
    """技能执行失败"""
    code = 3001

class LLMError(WebExplorerError):
    """LLM调用失败"""
    code = 3002
```

---

**文档状态**: 初稿完成  
**下一步**: 开始实际开发
