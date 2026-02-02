# WebExplorer Agent 测试套件

这是 WebExplorer Agent 的完整测试套件,包含 Mock Server 和各类测试。

## 📁 目录结构

```
tests/web_explorer/
├── mock_server.py           # Mock Web 服务器
├── conftest.py              # pytest 配置和 fixtures
├── test_config.json         # 测试配置
├── test_mock_server.py      # Mock Server 烟雾测试 ✅ 可立即运行
├── test_acceptance.py       # 验收测试
├── test_atlas_manager.py    # AtlasManager 单元测试
├── test_browser_manager.py  # BrowserManager 单元测试
├── test_skills.py           # Skills 单元测试
├── test_agent.py            # Agent 单元测试
└── README.md                # 本文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install pytest pytest-asyncio fastapi uvicorn httpx
```

### 2. 启动 Mock Server

在一个终端窗口中:

```bash
python tests/web_explorer/mock_server.py
```

服务器将在 `http://127.0.0.1:8080` 启动。

### 3. 运行测试

在另一个终端窗口中:

```bash
# 运行所有测试
pytest tests/web_explorer/ -v

# 运行特定测试文件
pytest tests/web_explorer/test_acceptance.py -v

# 运行特定测试
pytest tests/web_explorer/test_acceptance.py::TestGraphCompleteness::test_graph_completeness -v
```

## 📋 Mock Server 页面

Mock Server 提供以下测试页面:

| 路径 | 说明 | 用途 |
|------|------|------|
| `/` | 首页 | 导航入口,包含所有主要链接 |
| `/products` | 产品列表 | 测试列表页面导航 |
| `/products/1-3` | 产品详情 | 测试深度导航(第3层) |
| `/login` | 登录页 | 测试表单提交 |
| `/dashboard` | 仪表板 | 登录后页面 |
| `/about` | 关于页 | 基础信息页 |
| `/deadend` | 死胡同页 | 测试回溯功能(无链接) |
| `/loop-a`, `/loop-b` | 环路页 | 测试循环检测 |
| `/health` | 健康检查 | API 端点 |

## 🧪 测试类型

### 验收测试 (test_acceptance.py)

端到端测试,验证 Agent 的整体功能:

- **建图完整性** - 验证发现所有页面(≥8个节点)
- **链接正确性** - 验证软链接指向正确
- **脚本可执行性** - 验证生成的脚本可独立运行
- **循环检测** - 验证不创建重复节点
- **性能测试** - 验证在60秒内完成探索
- **死胡同处理** - 验证能从无链接页面回溯

### 单元测试

#### AtlasManager (test_atlas_manager.py)

测试状态图管理:
- 状态节点创建 (`ensure_state`)
- 软链接创建 (`link_state`)
- 任务队列管理 (`manage_todos`)
- 索引管理
- 并发安全性

#### BrowserManager (test_browser_manager.py)

测试浏览器操作:
- 意图执行 (`execute_intent`)
- 脚本保存 (`save_script`)
- 页面导航
- 元素交互(点击、填写)
- 截图功能
- 状态检测

#### Skills (test_skills.py)

测试技能系统:
- Skill 注册和执行
- 导航 Skills
- 探索 Skills

#### Agent (test_agent.py)

测试 Agent 核心:
- 初始化和配置
- 探索流程
- 决策制定
- 状态管理
- 错误处理

## ⚙️ 配置

测试配置在 `test_config.json`:

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

## 🔧 开发指南

### 添加新测试

1. 在相应的测试文件中添加测试类或测试方法
2. 使用 `@pytest.mark.asyncio` 装饰异步测试
3. 使用 fixtures 获取共享资源(如 `mock_server`, `test_config`)

示例:

```python
@pytest.mark.asyncio
async def test_my_feature(mock_server, test_config):
    """测试我的功能"""
    # 测试代码
    assert True
```

### 添加新 Fixture

在 `conftest.py` 中添加:

```python
@pytest.fixture
def my_fixture():
    """我的 fixture"""
    # 设置
    yield resource
    # 清理
```

### 添加新 Mock 页面

在 `mock_server.py` 中添加路由:

```python
@app.get("/my-page", response_class=HTMLResponse)
async def my_page():
    return """
    <html>
        <head><title>My Page</title></head>
        <body><h1>My Page</h1></body>
    </html>
    """
```

## 📊 预期测试结果

完整探索后的 Atlas 结构:

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
├── 07_About/             # 关于页
├── 08_Deadend/           # 死胡同
├── 09_Loop_A/            # 环路A
└── 10_Loop_B/            # 环路B
```

## 🐛 故障排除

### Mock Server 无法启动

- 检查端口 8080 是否被占用
- 尝试使用其他端口: `uvicorn.run(app, host="127.0.0.1", port=8081)`

### 测试超时

- 增加 `timeout` 配置
- 检查网络连接
- 确保 Mock Server 正在运行

### 测试被跳过

- 大部分测试使用 `pytest.skip()` 等待实现
- 实现相应组件后移除 `pytest.skip()` 行

### 导入错误

- 确保已安装所有依赖
- 检查 Python 路径配置

## 📝 注意事项

1. **当前状态**: 测试框架已就绪,但大部分测试使用 `pytest.skip()` 等待 WebExplorer Agent 实现
2. **Mock Server**: 完全可用,可独立运行用于手动测试
3. **下一步**: 实现 WebExplorer Agent 核心组件后,逐步取消测试跳过

## 🔗 相关文档

- [TESTING_REQUIREMENTS.md](../../WIP/TESTING_REQUIREMENTS.md) - 详细测试需求
- [PRD_TECHNICAL.md](../../WIP/PRD_TECHNICAL.md) - 技术需求文档
- [API_DESIGN.md](../../WIP/API_DESIGN.md) - API 设计文档

## 📞 支持

如有问题,请查看项目文档或联系开发团队。
