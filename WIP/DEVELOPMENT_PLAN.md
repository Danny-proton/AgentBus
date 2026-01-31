# WebExplorer Agent - 开发计划

**分阶段实施方案**

---

## 📅 总体时间规划

| 阶段 | 预计时间 | 交付物 | 依赖 |
|------|---------|--------|------|
| **阶段0: 环境准备** | 0.5天 | 目录结构、Mock Server | 无 |
| **阶段1: AtlasManager** | 1天 | 文件系统管理插件 | 阶段0 |
| **阶段2: BrowserManager** | 1.5天 | 浏览器管理插件 | 阶段0 |
| **阶段3: Skills** | 1天 | 两个LLM技能 | 阶段1,2 |
| **阶段4: Agent核心** | 2天 | WebExplorer Agent | 阶段1,2,3 |
| **阶段5: 集成测试** | 1天 | 端到端测试 | 阶段4 |
| **阶段6: 优化文档** | 0.5天 | 使用文档、示例 | 阶段5 |

**总计**: 约7.5天

---

## 阶段0: 环境准备 (0.5天)

### 目标
- 创建项目目录结构
- 开发Mock测试服务器
- 准备测试数据

### 任务清单

- [ ] **创建目录结构**
  ```bash
  mkdir -p plugins/web_explorer
  mkdir -p skills/web_explorer
  mkdir -p agents/web_explorer
  mkdir -p tests/web_explorer
  ```

- [ ] **开发Mock Server** (`tests/web_explorer/mock_server.py`)
  - [ ] 实现首页(/)
  - [ ] 实现列表页(/products)
  - [ ] 实现详情页(/products/{id})
  - [ ] 实现死胡同页(/deadend)
  - [ ] 实现环路页(/loop-a, /loop-b)
  - [ ] 添加启动脚本

- [ ] **编写测试数据**
  - [ ] 准备测试用的HTML模板
  - [ ] 准备测试用的CSS/JS

### 验收标准
- ✅ Mock Server可以启动并访问
- ✅ 所有测试页面可以正常渲染
- ✅ 页面间的链接关系正确

---

## 阶段1: AtlasManager Plugin (1天)

### 目标
实现文件系统状态管理插件

### 任务清单

- [ ] **基础框架** (`plugins/web_explorer/atlas_manager.py`)
  - [ ] 创建插件类继承AgentBusPlugin
  - [ ] 实现activate/deactivate方法
  - [ ] 定义配置项

- [ ] **功能1: ensure_state**
  - [ ] 实现DOM指纹计算
  - [ ] 实现目录创建逻辑
  - [ ] 实现meta.json写入
  - [ ] 更新全局index.json
  - [ ] 单元测试

- [ ] **功能2: link_state**
  - [ ] 实现软链接创建(跨平台)
  - [ ] 实现Fallback方案(JSON记录)
  - [ ] 单元测试

- [ ] **功能3: manage_todos**
  - [ ] 实现push逻辑(创建任务文件)
  - [ ] 实现pop逻辑(按优先级读取)
  - [ ] 实现任务状态转换
  - [ ] 单元测试

- [ ] **辅助功能**
  - [ ] 实现路径计算(从Root到目标节点)
  - [ ] 实现完整性检查
  - [ ] 实现统计信息收集

### 验收标准
- ✅ 所有功能单元测试通过
- ✅ 可以创建标准的状态节点目录
- ✅ 软链接在Windows/Linux都能工作
- ✅ 任务队列FIFO正确

---

## 阶段2: BrowserManager Plugin (1.5天)

### 目标
实现浏览器操作管理插件

### 任务清单

- [ ] **基础框架** (`plugins/web_explorer/browser_manager.py`)
  - [ ] 创建插件类
  - [ ] 集成automation.browser模块
  - [ ] 实现操作历史缓存

- [ ] **功能1: execute_intent**
  - [ ] 实现意图解析(调用LLM)
  - [ ] 实现元素查找和操作
  - [ ] 实现操作前后截图
  - [ ] 缓存操作步骤
  - [ ] 单元测试

- [ ] **功能2: save_script**
  - [ ] 设计脚本模板
  - [ ] 实现代码生成逻辑
  - [ ] 实现元数据注入
  - [ ] 测试生成的脚本可执行性

- [ ] **功能3: replay_teleport**
  - [ ] 实现脚本加载
  - [ ] 实现顺序执行
  - [ ] 实现失败重试
  - [ ] 实现状态验证
  - [ ] 单元测试

- [ ] **辅助功能**
  - [ ] 实现浏览器状态重置
  - [ ] 实现错误恢复
  - [ ] 实现操作日志记录

### 验收标准
- ✅ 可以执行模糊意图指令
- ✅ 生成的脚本可以独立运行
- ✅ 瞬移功能可以正确恢复状态
- ✅ 所有单元测试通过

---

## 阶段3: Skills Development (1天)

### 目标
实现两个LLM驱动的技能

### 任务清单

- [ ] **PageAnalysis Skill** (`skills/web_explorer/page_analysis.py`)
  - [ ] 创建技能类继承BaseSkill
  - [ ] 设计System Prompt
  - [ ] 实现execute方法
  - [ ] 实现输出验证
  - [ ] 测试不同页面类型

- [ ] **TrajectoryLabeling Skill** (`skills/web_explorer/trajectory_labeling.py`)
  - [ ] 创建技能类
  - [ ] 设计System Prompt
  - [ ] 实现execute方法
  - [ ] 实现输出验证
  - [ ] 测试不同动作类型

- [ ] **Prompt优化**
  - [ ] 测试Prompt稳定性
  - [ ] 添加Few-shot示例
  - [ ] 优化输出格式

### 验收标准
- ✅ PageAnalysis能正确识别可交互元素
- ✅ TrajectoryLabeling能准确判断状态变化
- ✅ 输出JSON格式符合Schema
- ✅ LLM调用失败时有重试机制

---

## 阶段4: WebExplorer Agent (2天)

### 目标
实现核心Agent和状态机

### 任务清单

- [ ] **类型定义** (`agents/web_explorer/types.py`)
  - [ ] 定义ExplorerState枚举
  - [ ] 定义ExplorerConfig
  - [ ] 定义其他数据类型

- [ ] **状态机** (`agents/web_explorer/fsm.py`)
  - [ ] 实现状态转换逻辑
  - [ ] 实现状态验证
  - [ ] 单元测试

- [ ] **Agent核心** (`agents/web_explorer/explorer_agent.py`)
  - [ ] 创建Agent类继承BaseAgent
  - [ ] 实现initialize方法
  - [ ] 实现shutdown方法

- [ ] **拓荒循环**
  - [ ] 实现_locate_current_state
  - [ ] 实现_analyze_page
  - [ ] 实现_decide_next_action
  - [ ] 实现_execute_action
  - [ ] 实现_reflect_on_action
  - [ ] 实现_backtrack
  - [ ] 集成测试

- [ ] **深测循环**
  - [ ] 实现_scan_test_ideas
  - [ ] 实现_teleport_to_state
  - [ ] 实现_execute_test
  - [ ] 实现_generate_report
  - [ ] 集成测试

- [ ] **循环检测**
  - [ ] 实现访问历史记录
  - [ ] 实现循环识别
  - [ ] 实现终止条件

### 验收标准
- ✅ Agent可以完成完整的拓荒循环
- ✅ Agent可以正确回溯
- ✅ Agent可以检测并避免死循环
- ✅ 深测循环可以执行测试用例

---

## 阶段5: 集成测试 (1天)

### 目标
端到端测试和验收

### 任务清单

- [ ] **验收测试** (`tests/web_explorer/test_acceptance.py`)
  - [ ] Case 1: 建图完整性测试
  - [ ] Case 2: 链接正确性测试
  - [ ] Case 3: 脚本可执行性测试
  - [ ] Case 4: 循环检测测试

- [ ] **性能测试**
  - [ ] 测试大规模网站(100+页面)
  - [ ] 测试内存占用
  - [ ] 测试执行速度

- [ ] **边界测试**
  - [ ] 测试网络错误处理
  - [ ] 测试LLM调用失败
  - [ ] 测试文件系统错误

- [ ] **Bug修复**
  - [ ] 修复发现的问题
  - [ ] 回归测试

### 验收标准
- ✅ 所有验收测试通过
- ✅ 无严重性能问题
- ✅ 错误处理健壮

---

## 阶段6: 文档和示例 (0.5天)

### 目标
完善文档和使用示例

### 任务清单

- [ ] **使用文档**
  - [ ] 编写快速开始指南
  - [ ] 编写配置说明
  - [ ] 编写API文档

- [ ] **示例代码**
  - [ ] 基础使用示例
  - [ ] 高级配置示例
  - [ ] 自定义扩展示例

- [ ] **迁移WIP文档**
  - [ ] 将WIP文档移至docs/
  - [ ] 更新README

### 验收标准
- ✅ 文档完整清晰
- ✅ 示例可以运行
- ✅ README更新

---

## 🎯 里程碑

### M1: 插件完成 (第2天结束)
- AtlasManager和BrowserManager两个插件开发完成
- 所有单元测试通过

### M2: 技能完成 (第3天结束)
- PageAnalysis和TrajectoryLabeling技能完成
- Prompt稳定可用

### M3: Agent完成 (第5天结束)
- WebExplorer Agent核心功能完成
- 拓荒循环和深测循环可用

### M4: 项目交付 (第7.5天结束)
- 所有验收测试通过
- 文档完善
- 可以正式使用

---

## 🔧 开发规范

### 代码规范
- 遵循PEP 8
- 使用Type Hints
- 添加Docstring
- 单元测试覆盖率>80%

### Git规范
- 功能分支开发
- Commit message规范
- PR review

### 测试规范
- 单元测试: pytest
- 集成测试: pytest + Mock Server
- 验收测试: 真实场景

---

## 📊 风险管理

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| LLM不稳定 | 高 | 高 | 添加重试和降级方案 |
| 软链接兼容性 | 中 | 中 | 提供JSON Fallback |
| 性能问题 | 中 | 中 | 及早性能测试 |
| 需求变更 | 低 | 高 | 保持WIP文档更新 |

---

## 📝 每日检查清单

### 开发中
- [ ] 代码符合规范
- [ ] 单元测试通过
- [ ] 更新任务清单
- [ ] 提交代码

### 阶段完成时
- [ ] 所有功能实现
- [ ] 所有测试通过
- [ ] 文档更新
- [ ] Code Review

---

**文档状态**: 初稿完成  
**下一步**: 开始阶段0的开发工作
