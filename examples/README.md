# AgentBus 开发示例

本目录包含AgentBus扩展开发的示例代码。

## 📁 示例列表

### 1. 插件开发示例
**文件**: `plugin_example.py`

演示如何创建自定义插件:
- 注册工具函数
- 注册事件Hook
- 处理插件生命周期

**运行**:
```bash
python examples/plugin_example.py
```

### 2. Agent开发示例
**文件**: `agent_example.py`

演示如何创建自定义Agent:
- 管理Agent状态
- 执行自定义任务
- 使用Agent能力

**运行**:
```bash
python examples/agent_example.py
```

### 3. 网页测试Agent示例
**文件**: `web_test_agent_example.py`

演示如何使用浏览器自动化:
- 页面导航
- 表单测试
- 链接验证
- 截图功能

**运行**:
```bash
python examples/web_test_agent_example.py
```

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行示例
```bash
# 插件示例
python -m examples.plugin_example

# Agent示例
python -m examples.agent_example

# 网页测试示例
python -m examples.web_test_agent_example
```

## 📚 相关文档

- [快速扩展指南](../docs/QUICK_EXTENSION_GUIDE.md) - 5分钟快速上手
- [完整开发指南](../docs/EXTENSION_DEVELOPMENT_GUIDE.md) - 深入学习参考

## 💡 开发建议

1. **从插件开始**: 先学习插件开发,理解工具注册和Hook机制
2. **再学Agent**: 掌握Agent的状态管理和任务执行
3. **实战应用**: 结合浏览器自动化开发实际应用

## 🔧 调试技巧

### 启用调试日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 浏览器可视化调试
```python
browser_config = BrowserConfig(
    headless=False,  # 显示浏览器
    slow_mo=1000     # 减慢操作速度
)
```

## 📝 示例说明

### plugin_example.py
- ✅ 工具注册: `process_text`, `calculate_stats`
- ✅ Hook注册: `message.process`, `system.startup`
- ✅ 完整的激活/停用流程

### agent_example.py
- ✅ 任务处理: `process_text`, `analyze_data`, `generate_report`
- ✅ 状态管理: 初始化、启动、暂停、恢复、停止
- ✅ 能力注册: `text_processing`, `data_analysis`

### web_test_agent_example.py
- ✅ 页面导航: 访问URL并获取页面信息
- ✅ 表单测试: 自动填写和提交表单
- ✅ 链接验证: 检查页面链接有效性
- ✅ 截图功能: 保存页面截图

## 🎯 下一步

学习完这些示例后,可以:

1. 修改示例代码,适应你的需求
2. 组合多个功能,创建复杂应用
3. 参考完整文档,了解更多高级特性
