# 人在回路 (Human-in-the-Loop) 设计文档

## 核心设计理念

**把人类当作一个强大的工具** - 这是人与 AI 协作的核心范式。

人类可以像其他工具一样被调用，但具有以下独特能力：
- ✅ 提出意见/建议
- ✅ 执行 bash 命令
- ✅ 执行桌面操作（点击、输入等）
- ✅ 执行浏览器操作（导航、点击、提取）
- ✅ 审查代码/内容
- ✅ 批准关键操作

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent (Main)                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                  HumanTool                               ││
│  │  - action="invoke"      调用人类                        ││
│  │  - action="check_result" 检查结果                       ││
│  │  - action="get_summary" 获取总结                       ││
│  │  - action="list_pending" 列出待处理                    ││
│  └─────────────────────────────────────────────────────────┘│
│                            │                                 │
│                            ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              HumanInTheLoopManager                       ││
│  │  - 操作队列管理                                          ││
│  │  - 操作历史记录                                          ││
│  │  - WebSocket 通知                                        ││
│  └─────────────────────────────────────────────────────────┘│
│                            │                                 │
│              ┌─────────────┼─────────────┐                  │
│              ▼             ▼             ▼                  │
│        ┌─────────┐   ┌──────────┐  ┌──────────┐            │
│        │ Desktop │   │ Browser  │  │ 其他    │            │
│        │ Summarizer│  │Summarizer│  │ 组件   │            │
│        └─────────┘   └──────────┘  └──────────┘            │
│                            │                                 │
│                            ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                     Frontend                             ││
│  │  - 接收通知                                              ││
│  │  - 展示请求                                              ││
│  │  - 收集输入                                              ││
│  │  - 执行操作                                              ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## 使用示例

### 1. 基本调用 - 请求人类意见

```python
# Agent 在不确定如何继续时调用人类
await human_tool.execute(
    action="invoke",
    action_type="feedback",
    description="这个设计是否合理？",
    details={
        "current_design": "使用微服务架构...",
        "concerns": ["复杂度较高", "运维成本"]
    },
    context={
        "task": "设计用户认证模块",
        "progress": "已完成初步设计"
    }
)

# 检查结果
result = await human_tool.execute(
    action="check_result",
    operation_id="abc123def456"
)

# 获取总结
summary = await human_tool.execute(action="get_summary")
```

### 2. 调用人类执行 Bash

```python
# Agent 无法执行某些复杂命令时
await human_tool.execute(
    action="invoke",
    action_type="bash",
    description="请手动配置数据库连接",
    details={
        "why_agent_cant": "需要交互式输入密码",
        "target_db": "postgresql://prod-db:5432",
        "required_action": "运行 psql 命令并输入密码"
    }
)
```

### 3. 调用人类执行桌面操作

```python
# Agent 无法自动化 GUI 操作时
await human_tool.execute(
    action="invoke",
    action_type="desktop",
    description="请在 IDE 中打开项目并运行测试",
    details={
        "project_path": "/workspace/my-project",
        "action_sequence": [
            "打开 VS Code",
            "打开项目",
            "点击运行测试按钮",
            "截图测试结果"
        ],
        "expected_outcome": "看到测试通过的绿色标识"
    }
)
```

### 4. 调用人类执行浏览器操作

```python
# Agent 无法访问某些网站或需要人类验证时
await human_tool.execute(
    action="invoke",
    action_type="browser",
    description="请登录管理后台并检查用户列表",
    details={
        "url": "https://admin.example.com",
        "required_action": "登录并导航到用户管理页面",
        "data_to_extract": ["用户总数", "最近活跃用户"],
        "requires_human": "需要验证码"
    }
)
```

### 5. 请求人类审查代码

```python
# Agent 完成了代码编写，请求人类审查
await human_tool.execute(
    action="invoke",
    action_type="review",
    description="请审查这段用户认证代码",
    details={
        "file_path": "/workspace/auth.py",
        "code_snippet": "...",
        "focus_areas": ["安全性", "性能", "可读性"],
        "tests_passed": True
    }
)
```

### 6. 请求人类批准关键操作

```python
# 在执行危险操作前请求批准
await human_tool.execute(
    action="invoke",
    action_type="approve",
    description="确认是否部署到生产环境？",
    details={
        "action": "执行 kubectl apply -f prod-deployment.yaml",
        "impact": "将更新 5 个微服务",
        "risk_level": "high",
        "rollback_plan": "执行 rollback.sh"
    },
    timeout=600  # 给更多时间考虑
)
```

## 操作流程

### Agent 调用人类的完整流程

```python
# 1. Agent 调用人类
operation = await human_tool.execute(
    action="invoke",
    action_type="browser",
    description="请检查登录页面"
)

# 2. 前端接收通知，通知人类
# 3. 人类执行操作...
# 4. 人类提交结果（通过前端或 API）
#    await human_manager.submit_human_input(operation_id, human_input)
# 5. 完成操作（记录结果和总结）
#    await human_manager.complete_operation(
#        operation_id=operation_id,
#        execution_result="登录成功",
#        summary="成功登录，检查了 3 个表单字段",
#        key_findings=["验证码在右下角", "密码最小8位"]
#    )

# 6. Agent 检查结果
result = await human_tool.execute(
    action="check_result",
    operation_id=operation_id
)

# 7. Agent 总结人类的行为，继续工作
#    "人类检查了登录页面，发现验证码在右下角..."
```

## 前端集成

### WebSocket 消息格式

**Agent 调用人类时：**
```json
{
  "type": "human_invocation",
  "operation_id": "abc123def456",
  "action_type": "browser",
  "description": "请检查登录页面",
  "request_params": {
    "url": "https://...",
    "action": "login"
  },
  "context": {
    "agent_id": "main_agent",
    "created_at": "2024-01-22T10:00:00"
  }
}
```

**前端通知人类：**
- 弹出通知
- 显示操作详情
- 提供输入框或操作界面
- 收集人类输入

**人类提交结果：**
```python
# 后端 API
POST /api/human/complete
{
  "operation_id": "abc123def456",
  "human_input": "登录页面正常，验证码在右下角...",
  "execution_result": "成功",
  "summary": "检查了登录页面，发现验证码在右下角...",
  "key_findings": [
    "验证码在右下角",
    "密码最小8位",
    "支持记住密码"
  ]
}
```

## 总结组件

### 桌面操作总结（用户实现）

```python
# 用户实现 DesktopActionSummarizer
class MyDesktopSummarizer(DesktopActionSummarizer):
    async def summarize(self, action_result: Dict[str, Any]) -> str:
        # 自定义总结逻辑
        summary = []
        
        if action_result.get("clicked_element"):
            summary.append(f"点击了「{action_result['clicked_element']}」")
        
        if action_result.get("typed_text"):
            summary.append("输入了文本")
        
        if action_result.get("opened_application"):
            summary.append(f"打开了 {action_result['opened_application']}")
        
        if action_result.get("file_operations"):
            ops = action_result["file_operations"]
            summary.append(f"操作了 {len(ops)} 个文件")
        
        return "，".join(summary) if summary else "桌面操作完成"
```

### 浏览器操作总结（用户实现）

```python
# 用户实现 BrowserActionSummarizer
class MyBrowserSummarizer(BrowserActionSummarizer):
    async def summarize(self, action_result: Dict[str, Any]) -> str:
        summary = []
        
        if action_result.get("url"):
            summary.append(f"访问 {action_result['url']}")
        
        if action_result.get("page_title"):
            summary.append(f"页面: {action_result['page_title']}")
        
        if action_result.get("extracted_content"):
            content = action_result["extracted_content"]
            if isinstance(content, dict):
                summary.append(f"提取了 {len(content)} 条数据")
            else:
                summary.append(f"提取了 {len(content)} 字符")
        
        return "，".join(summary) if summary else "浏览器操作完成"
```

## 最佳实践

### 1. 明确调用目的

```python
# ❌ 不好：不明确的调用
await human_tool.execute(
    action="invoke",
    action_type="feedback",
    description="帮我看看"
)

# ✅ 好：明确的调用
await human_tool.execute(
    action="invoke",
    action_type="review",
    description="请审查用户认证模块的安全性",
    details={
        "file": "/workspace/auth.py",
        "focus": ["SQL注入防护", "密码加密", "会话管理"]
    }
)
```

### 2. 提供充分上下文

```python
details={
    "task_background": "实现双因素认证",
    "current_progress": "已完成短信验证码发送",
    "blocked_by": "无法测试实际短信发送",
    "what_human_needs_to_do": "在测试环境验证流程是否正确",
    "expected_result": "收到测试短信并成功验证"
}
```

### 3. 总结人类操作

```python
# 人类操作完成后，Agent 应该总结
human_summary = """
## 人类操作总结

人类执行了以下操作：
1. 打开了登录页面 (https://example.com/login)
2. 点击了"忘记密码"链接
3. 输入了测试邮箱
4. 收到测试邮件

关键发现：
- 忘记密码流程正常
- 邮件发送延迟约 5 秒
- 邮件中的链接有效期为 24 小时

建议：
- 可以继续实现前端表单验证
- 邮件模板可以优化
"""
```

### 4. 记忆人类操作

```python
# 在继续工作前，获取人类操作历史
history = await human_tool.execute(action="get_summary")
# 人类上次检查了登录页面，发现验证码在右下角...
```

## 配置项

```python
# config/settings.py
class HumanLoopConfig(BaseSettings):
    enabled: bool = True
    default_timeout: int = 300  # 默认超时 5 分钟
    max_pending_requests: int = 10  # 最大待处理请求数
    auto_summarize: bool = True  # 自动生成总结
    max_history: int = 100  # 操作历史数量
```

## 与其他模块的集成

### 与 Knowledge Bus 集成

```python
# 将人类操作存储到知识总线
await knowledge_bus.put(
    key=f"human_operation_{operation_id}",
    value=operation.summary,
    category="human_actions"
)
```

### 与 Log Service 集成

```python
# 记录人类操作到日志
await log_service.log(
    action=f"Human operation: {action_type}",
    category=LogCategory.HUMAN,
    agent_id=agent_id,
    details=request_params,
    result=execution_result
)
```

### 与 Agent WorkSpace 集成

```python
# 将人类操作的详细记录保存到工作空间
workspace.write_context(
    f"human_operation_{operation_id}.json",
    json.dumps(operation.to_dict())
)
```

## 常见问题

### Q: Agent 如何知道人类何时完成操作？
A: 通过 `check_result` 轮询，或使用 WebSocket 实时通知。

### Q: 人类操作超时会怎样？
A: 操作保持 pending 状态，Agent 可以取消或继续等待。

### Q: 多个 Agent 同时调用人类怎么办？
A: 使用队列管理，前端按顺序处理。

### Q: 如何区分不同类型的操作？
A: 使用 `action_type` 参数：`feedback`, `bash`, `desktop`, `browser`, `review`, `approve`。

### Q: 人类操作的结果如何传递给 Agent？
A: 通过 `summary` 和 `key_findings` 字段，Agent 可以读取并总结。
