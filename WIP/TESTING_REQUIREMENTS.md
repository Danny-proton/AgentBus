# WebExplorer Agent - 测试需求文档

**供测试开发人员使用**

---

## 📋 文档信息

| 项目 | 内容 |
|------|------|
| **文档版本** | v1.0 |
| **创建日期** | 2026-01-31 |
| **负责人** | 测试团队 |
| **依赖** | WebExplorer Agent核心组件 |

---

## 1. Mock Server需求

### 1.1 概述

开发一个基于FastAPI的轻量级Web服务,作为WebExplorer Agent的测试靶场。

### 1.2 技术要求

- **框架**: FastAPI
- **模板引擎**: Jinja2
- **端口**: 8080 (可配置)
- **启动方式**: `python tests/web_explorer/mock_server.py`

### 1.3 页面需求

#### 页面A: 首页 (/)

**特征**:
- 包含网站标题和导航
- 包含至少3个链接:
  - 链接到产品列表页 (/products)
  - 链接到登录页 (/login)
  - 链接到关于页 (/about)

**HTML结构示例**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Mock Site - Home</title>
</head>
<body>
    <h1>Welcome to Mock Site</h1>
    <nav>
        <a href="/products" id="products-link">Products</a>
        <a href="/login" id="login-link">Login</a>
        <a href="/about" id="about-link">About</a>
    </nav>
</body>
</html>
```

#### 页面B: 产品列表页 (/products)

**特征**:
- 显示产品列表(至少3个产品)
- 每个产品有链接到详情页
- 包含返回首页的链接

**HTML结构示例**:
```html
<h1>Product List</h1>
<ul>
    <li><a href="/products/1">Product 1</a></li>
    <li><a href="/products/2">Product 2</a></li>
    <li><a href="/products/3">Product 3</a></li>
</ul>
<a href="/">Back to Home</a>
```

#### 页面C: 产品详情页 (/products/{id})

**特征**:
- 显示产品详细信息
- 包含返回列表页的链接
- 包含"添加到购物车"按钮(不需要实际功能)

**深度**: 从首页算起为第3层

#### 页面D: 登录页 (/login)

**特征**:
- 包含登录表单(用户名、密码)
- 包含提交按钮
- 提交后跳转到仪表板页 (/dashboard)

**HTML结构示例**:
```html
<h1>Login</h1>
<form method="POST" action="/login">
    <input type="text" name="username" id="username" placeholder="Username">
    <input type="password" name="password" id="password" placeholder="Password">
    <button type="submit" id="login-btn">Login</button>
</form>
```

#### 页面E: 死胡同页 (/deadend)

**特征**:
- **不包含任何链接**
- 只显示文本内容
- 用于测试Agent的回溯功能

**HTML结构示例**:
```html
<h1>Dead End</h1>
<p>This page has no links. You need to go back.</p>
```

#### 页面F: 环路页A (/loop-a)

**特征**:
- 包含链接到环路页B (/loop-b)
- 用于测试循环检测

#### 页面G: 环路页B (/loop-b)

**特征**:
- 包含链接到环路页A (/loop-a)
- 形成 A -> B -> A 的环路

### 1.4 实现示例

```python
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

app = FastAPI()
templates = Jinja2Templates(directory="tests/web_explorer/templates")

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
        <head><title>Mock Site - Home</title></head>
        <body>
            <h1>Welcome to Mock Site</h1>
            <nav>
                <a href="/products" id="products-link">Products</a>
                <a href="/login" id="login-link">Login</a>
                <a href="/about" id="about-link">About</a>
                <a href="/deadend" id="deadend-link">Dead End</a>
                <a href="/loop-a" id="loop-link">Loop Test</a>
            </nav>
        </body>
    </html>
    """

@app.get("/products", response_class=HTMLResponse)
async def products():
    return """
    <html>
        <head><title>Products</title></head>
        <body>
            <h1>Product List</h1>
            <ul>
                <li><a href="/products/1" id="product-1">Product 1</a></li>
                <li><a href="/products/2" id="product-2">Product 2</a></li>
                <li><a href="/products/3" id="product-3">Product 3</a></li>
            </ul>
            <a href="/" id="home-link">Back to Home</a>
        </body>
    </html>
    """

@app.get("/products/{product_id}", response_class=HTMLResponse)
async def product_detail(product_id: int):
    return f"""
    <html>
        <head><title>Product {product_id}</title></head>
        <body>
            <h1>Product {product_id} Details</h1>
            <p>This is the detail page for product {product_id}</p>
            <button id="add-to-cart">Add to Cart</button>
            <a href="/products" id="back-link">Back to Products</a>
        </body>
    </html>
    """

@app.get("/login", response_class=HTMLResponse)
async def login_form():
    return """
    <html>
        <head><title>Login</title></head>
        <body>
            <h1>Login</h1>
            <form method="POST" action="/login">
                <input type="text" name="username" id="username" placeholder="Username">
                <input type="password" name="password" id="password" placeholder="Password">
                <button type="submit" id="login-btn">Login</button>
            </form>
        </body>
    </html>
    """

@app.post("/login")
async def login_submit(username: str = Form(...), password: str = Form(...)):
    return """
    <html>
        <head><title>Dashboard</title></head>
        <body>
            <h1>Dashboard</h1>
            <p>Welcome! You are logged in.</p>
            <a href="/" id="home-link">Home</a>
        </body>
    </html>
    """

@app.get("/deadend", response_class=HTMLResponse)
async def deadend():
    return """
    <html>
        <head><title>Dead End</title></head>
        <body>
            <h1>Dead End</h1>
            <p>This page has no links. You need to go back.</p>
        </body>
    </html>
    """

@app.get("/loop-a", response_class=HTMLResponse)
async def loop_a():
    return """
    <html>
        <head><title>Loop A</title></head>
        <body>
            <h1>Loop Page A</h1>
            <a href="/loop-b" id="to-b">Go to B</a>
        </body>
    </html>
    """

@app.get("/loop-b", response_class=HTMLResponse)
async def loop_b():
    return """
    <html>
        <head><title>Loop B</title></head>
        <body>
            <h1>Loop Page B</h1>
            <a href="/loop-a" id="to-a">Go to A</a>
        </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
```

---

## 2. 验收测试需求

### 2.1 测试框架

- **框架**: pytest
- **异步支持**: pytest-asyncio
- **位置**: `tests/web_explorer/test_acceptance.py`

### 2.2 测试用例

#### Case 1: 建图完整性测试

**测试目标**: 验证Agent能发现所有页面

**步骤**:
1. 启动Mock Server
2. 启动WebExplorer Agent,起始URL为 `http://127.0.0.1:8080/`
3. 等待Agent完成探索
4. 检查 `project_memory/` 目录

**验收标准**:
```python
async def test_graph_completeness():
    """测试建图完整性"""
    # 启动Agent
    agent = WebExplorer(config)
    result = await agent.start_exploration("http://127.0.0.1:8080/")
    
    # 检查节点数量
    assert result["total_nodes"] >= 8  # 至少8个页面
    
    # 检查是否包含关键页面
    index = load_index("project_memory/index.json")
    urls = [node["url"] for node in index["nodes"].values()]
    
    assert "http://127.0.0.1:8080/" in urls
    assert "http://127.0.0.1:8080/products" in urls
    assert "http://127.0.0.1:8080/products/1" in urls
    assert "http://127.0.0.1:8080/login" in urls
    assert "http://127.0.0.1:8080/deadend" in urls
```

#### Case 2: 链接正确性测试

**测试目标**: 验证软链接指向正确

**步骤**:
1. 读取根节点的 `links/` 目录
2. 验证软链接指向的目标节点

**验收标准**:
```python
async def test_link_correctness():
    """测试链接正确性"""
    root_dir = Path("project_memory/00_Root")
    links_dir = root_dir / "links"
    
    # 检查链接存在
    assert (links_dir / "action_products").exists()
    
    # 检查链接指向正确
    target = (links_dir / "action_products").resolve()
    target_meta = json.loads((target / "meta.json").read_text())
    
    assert "products" in target_meta["url"]
```

#### Case 3: 脚本可执行性测试

**测试目标**: 验证生成的脚本可以独立运行

**步骤**:
1. 随机选择一个生成的脚本
2. 在干净的浏览器中执行
3. 验证最终URL正确

**验收标准**:
```python
async def test_script_executable():
    """测试脚本可执行性"""
    # 找到一个脚本
    script_path = Path("project_memory/01_Login/scripts/nav_login.py")
    
    # 执行脚本
    result = subprocess.run(
        ["python", str(script_path)],
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0
    assert "error" not in result.stderr.lower()
```

#### Case 4: 循环检测测试

**测试目标**: 验证Agent能检测并避免死循环

**步骤**:
1. Agent访问环路页面
2. 检查是否创建了重复的节点

**验收标准**:
```python
async def test_loop_detection():
    """测试循环检测"""
    agent = WebExplorer(config)
    await agent.start_exploration("http://127.0.0.1:8080/loop-a")
    
    # 检查节点数量
    index = load_index("project_memory/index.json")
    
    # 应该只有2个节点(loop-a和loop-b),不应该有重复
    loop_nodes = [
        node for node in index["nodes"].values()
        if "loop" in node["url"]
    ]
    
    assert len(loop_nodes) == 2
```

### 2.3 性能测试

```python
async def test_performance():
    """测试性能"""
    import time
    
    start_time = time.time()
    
    agent = WebExplorer(config)
    result = await agent.start_exploration("http://127.0.0.1:8080/")
    
    elapsed = time.time() - start_time
    
    # 探索8个页面应该在60秒内完成
    assert elapsed < 60
    
    # 内存占用应该合理(这里需要实际测量)
    # assert memory_usage < 500MB
```

---

## 3. 单元测试需求

### 3.1 AtlasManager Plugin测试

```python
# tests/web_explorer/test_atlas_manager.py

async def test_ensure_state():
    """测试状态节点创建"""
    plugin = AtlasManagerPlugin(...)
    
    result = await plugin.ensure_state(
        url="http://example.com",
        dom_fingerprint="abc123",
        screenshot_path="/path/to/screenshot.png"
    )
    
    assert result["is_new"] == True
    assert Path(result["node_path"]).exists()
    assert Path(result["meta_file"]).exists()

async def test_link_state():
    """测试软链接创建"""
    plugin = AtlasManagerPlugin(...)
    
    success = await plugin.link_state(
        source_node_id="00_Root",
        action_name="login",
        target_node_id="01_Login"
    )
    
    assert success == True
    link_path = Path("project_memory/00_Root/links/action_login")
    assert link_path.exists()
    assert link_path.is_symlink()

async def test_manage_todos():
    """测试任务队列"""
    plugin = AtlasManagerPlugin(...)
    
    # Push任务
    tasks = [
        {"id": "task_001", "selector": "#btn", "priority": 5}
    ]
    await plugin.manage_todos("00_Root", "push", tasks)
    
    # Pop任务
    popped = await plugin.manage_todos("00_Root", "pop")
    
    assert len(popped) == 1
    assert popped[0]["id"] == "task_001"
```

### 3.2 BrowserManager Plugin测试

```python
# tests/web_explorer/test_browser_manager.py

async def test_execute_intent():
    """测试意图执行"""
    plugin = BrowserManagerPlugin(...)
    
    result = await plugin.execute_intent(
        intent="点击登录按钮",
        context={"url": "http://127.0.0.1:8080/"}
    )
    
    assert result["success"] == True
    assert result["action_type"] == "click"
    assert result["selector"] is not None

async def test_save_script():
    """测试脚本保存"""
    plugin = BrowserManagerPlugin(...)
    
    # 先执行一些操作
    await plugin.execute_intent("点击登录")
    
    # 保存脚本
    success = await plugin.save_script(
        script_path="test_script.py",
        metadata={"name": "登录脚本"}
    )
    
    assert success == True
    assert Path("test_script.py").exists()
```

---

## 4. 测试数据

### 4.1 测试配置

```json
{
  "test_config": {
    "mock_server_url": "http://127.0.0.1:8080",
    "max_depth": 5,
    "max_nodes": 20,
    "timeout": 60,
    "headless": true
  }
}
```

### 4.2 预期结果

**完整探索后的Atlas结构**:
```
project_memory/
├── index.json
├── 00_Root/              # 首页
├── 01_Products/          # 产品列表
├── 02_Product_1/         # 产品1详情
├── 03_Product_2/         # 产品2详情
├── 04_Product_3/         # 产品3详情
├── 05_Login/             # 登录页
├── 06_Dashboard/         # 仪表板
├── 07_Deadend/           # 死胡同
├── 08_Loop_A/            # 环路A
└── 09_Loop_B/            # 环路B
```

---

## 5. 测试环境要求

### 5.1 依赖安装

```bash
pip install pytest pytest-asyncio fastapi uvicorn
```

### 5.2 运行测试

```bash
# 启动Mock Server
python tests/web_explorer/mock_server.py &

# 运行单元测试
pytest tests/web_explorer/test_atlas_manager.py -v
pytest tests/web_explorer/test_browser_manager.py -v

# 运行验收测试
pytest tests/web_explorer/test_acceptance.py -v

# 停止Mock Server
pkill -f mock_server.py
```

---

## 6. 交付物清单

- [ ] `tests/web_explorer/mock_server.py` - Mock Web服务器
- [ ] `tests/web_explorer/test_atlas_manager.py` - AtlasManager单元测试
- [ ] `tests/web_explorer/test_browser_manager.py` - BrowserManager单元测试
- [ ] `tests/web_explorer/test_skills.py` - Skills单元测试
- [ ] `tests/web_explorer/test_agent.py` - Agent单元测试
- [ ] `tests/web_explorer/test_acceptance.py` - 验收测试
- [ ] `tests/web_explorer/README.md` - 测试说明文档

---

**文档状态**: 完成  
**负责人**: 测试团队  
**预计工时**: 2-3天
