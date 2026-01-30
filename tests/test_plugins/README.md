---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 3045022100ade6ba40590af321e8530b9df0bf52c9355d71a112b0e01f0377aec8bf5a3e5f0220364216b749c45544e15764393ab7592e62040984ecdd4ec9c9734db6fcacfca9
    ReservedCode2: 304502204730a459e12e0762c3e71295a549ec73589a049ab3412c5ab098fdeca3e862b20221009986d2710537e03277f82fdcb45058f6d6d605e95fcf970344fa8bf97848e520
---

# AgentBus插件框架测试套件

这个目录包含了AgentBus插件框架的完整测试套件，用于验证插件系统的所有核心功能。

## 📁 测试文件结构

```
tests/test_plugins/
├── __init__.py                    # 测试模块初始化，包含fixtures和配置
├── test_plugin_core.py           # 插件核心功能测试
└── test_plugin_manager.py        # 插件管理器测试
```

## 🧪 测试覆盖范围

### 核心功能测试 (`test_plugin_core.py`)

- **PluginContext**: 插件上下文测试
  - 初始化和验证
  - 类型检查和错误处理

- **AgentBusPlugin**: 插件基类测试
  - 插件生命周期管理
  - 工具、钩子、命令注册
  - 同步和异步功能
  - 配置和运行时变量管理

- **PluginTool**: 插件工具测试
  - 工具创建和验证
  - 函数签名分析
  - 参数验证

- **PluginHook**: 插件钩子测试
  - 钩子创建和验证
  - 异步检测
  - 优先级排序

- **PluginStatus**: 插件状态测试
  - 状态枚举完整性
  - 状态转换验证

### 插件管理器测试 (`test_plugin_manager.py`)

- **插件发现和加载**
  - 插件目录扫描
  - 动态模块导入
  - 插件验证

- **生命周期管理**
  - 插件激活/停用
  - 插件重载
  - 状态管理

- **资源注册**
  - 工具注册表管理
  - 钩子事件调度
  - 命令注册

- **并发操作**
  - 多插件并发加载
  - 异步操作测试

- **错误处理**
  - 加载失败恢复
  - 执行错误处理
  - 边界情况测试

## 🚀 运行测试

### 使用pytest直接运行

```bash
# 运行所有插件测试
pytest tests/test_plugins/ -v

# 运行特定测试文件
pytest tests/test_plugins/test_plugin_core.py -v
pytest tests/test_plugins/test_plugin_manager.py -v

# 运行特定测试类
pytest tests/test_plugins/test_plugin_core.py::TestAgentBusPlugin -v

# 运行特定测试方法
pytest tests/test_plugins/test_plugin_core.py::TestAgentBusPlugin::test_tool_registration -v

# 包含覆盖率报告
pytest tests/test_plugins/ --cov=agentbus.plugins --cov-report=html
```

### 使用测试运行脚本

```bash
# 运行测试套件
python run_plugin_tests.py
```

脚本会：
1. 检查依赖包
2. 运行所有测试套件
3. 生成覆盖率报告
4. 显示详细的测试结果

### 特定测试类别

```bash
# 只运行集成测试
pytest tests/test_plugins/ -k integration

# 只运行异步功能测试
pytest tests/test_plugins/ -k async

# 只运行错误处理测试
pytest tests/test_plugins/ -k error

# 运行快速的单元测试（排除集成测试）
pytest tests/test_plugins/ -m "not integration" -v
```

## 📊 测试类型和标记

### pytest标记

- `@pytest.mark.asyncio`: 异步测试
- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.slow`: 慢速测试
- `@pytest.mark.unit`: 单元测试

### 测试分类

1. **单元测试**: 测试单个组件功能
2. **集成测试**: 测试组件间协作
3. **端到端测试**: 测试完整工作流程
4. **错误处理测试**: 测试异常情况

## 🔧 测试配置

### pytest配置 (`pytest.ini` 或 `pyproject.toml`)

```ini
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--verbose",
    "--tb=short",
    "--strict-markers",
    "--strict-config"
]
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests"
]
```

### 环境配置

测试会自动创建：
- 临时插件目录
- 模拟配置和日志器
- 插件上下文实例
- 测试夹具（fixtures）

## 📝 示例测试

### 基本插件测试

```python
@pytest.mark.asyncio
async def test_plugin_activate_deactivate():
    \"\"\"测试插件激活和停用\"\"\"
    plugin = TestPlugin("test", mock_context)
    
    # 测试激活
    assert plugin.status == PluginStatus.UNLOADED
    result = await plugin.activate()
    assert result == True
    assert plugin.status == PluginStatus.ACTIVE
    
    # 测试停用
    result = await plugin.deactivate()
    assert result == True
    assert plugin.status == PluginStatus.DEACTIVATED
```

### 工具注册测试

```python
def test_tool_registration():
    \"\"\"测试工具注册\"\"\"
    plugin = TestPlugin("test", mock_context)
    
    def sample_tool(x: int, y: str = "default") -> str:
        return f"{y}_{x}"
    
    tool = plugin.register_tool("sample", "Sample tool", sample_tool)
    
    assert len(plugin.get_tools()) == 1
    assert tool.name == "sample"
    assert tool.async_func == False
```

### 钩子优先级测试

```python
@pytest.mark.asyncio
async def test_hook_priority():
    \"\"\"测试钩子优先级\"\"\"
    plugin = TestPlugin("test", mock_context)
    
    # 注册不同优先级的钩子
    plugin.register_hook("event", low_handler, priority=5)
    plugin.register_hook("event", high_handler, priority=10)
    
    hooks = plugin.get_hooks()["event"]
    assert hooks[0].priority == 10  # 高优先级在前
    assert hooks[1].priority == 5
```

## 🎯 最佳实践

### 编写测试

1. **使用描述性测试名称**: 清楚说明测试内容
2. **遵循AAA模式**: Arrange-Act-Assert
3. **使用适当的夹具**: 避免重复代码
4. **测试边界情况**: 包含错误和异常情况
5. **保持测试独立**: 不依赖其他测试结果

### 测试命名约定

- 测试文件: `test_*.py`
- 测试类: `Test*`
- 测试方法: `test_*`

### 断言使用

```python
# ✅ 好的断言
assert plugin.status == PluginStatus.ACTIVE
assert len(tools) == 2
assert "test_tool" in tool_names

# ❌ 避免复杂断言
assert result == expected_complex_object
```

## 🐛 故障排除

### 常见问题

1. **异步测试失败**
   - 确保使用了 `@pytest.mark.asyncio`
   - 检查是否有未等待的协程

2. **导入错误**
   - 确保Python路径包含项目根目录
   - 检查包导入路径

3. **临时文件问题**
   - 测试使用临时目录会自动清理
   - 避免硬编码文件路径

### 调试测试

```bash
# 详细输出
pytest tests/test_plugins/test_plugin_core.py -v -s

# 停止在第一个失败
pytest tests/test_plugins/ -x

# 显示局部变量
pytest tests/test_plugins/ --tb=long -l

# 进入调试器
pytest tests/test_plugins/ --pdb
```

## 📈 性能测试

测试套件包含性能测试来验证：

- 插件加载时间
- 大量插件的内存使用
- 并发操作性能
- 事件调度效率

运行性能测试：

```bash
pytest tests/test_plugins/ -k "performance or slow" --benchmark-only
```

## 🤝 贡献指南

在贡献新功能或修复时：

1. 添加相应的测试
2. 确保所有测试通过
3. 更新文档
4. 遵循现有代码风格

## 📄 许可证

测试套件与主项目使用相同的MIT许可证。