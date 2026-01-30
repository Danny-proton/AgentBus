---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 30450220362b9d8203238dea354c61d9c52e2e31a1e39b31f6a9853951c6f6b3005519e2022100954b144daea6c6792bdde841d54976c77f76131053d665e0acab57b9c9c6dc82
    ReservedCode2: 304402201c53c2d83d9ead1cea9ee26a569933b9217d1473e3f2ea1d546e7a4c5c24a57c02202767b2b443b78b0b6d990115f8e0edf3bdc64990973cab6757785e2a4faf44b4
---

# AgentBus 工作空间

## 创建时间
2026-01-29 12:13:32

## 当前会话信息
- 会话 ID: 待初始化
- 主模型: 待配置
- 工作模式: 标准

## 目录结构
- `logs/` - 执行日志和调试信息
- `scripts/` - 运行时生成的脚本文件
- `plans/` - 任务计划文件
- `contexts/` - 上下文和配置文件
- `temp/` - 临时文件（自动清理）
- `memory/` - 工作空间记忆存储
- `knowledge/` - 知识总线存储
- `agent/` - Agent相关配置和状态

## 使用说明
1. 所有Agent生成的脚本文件保存在 `scripts/` 目录
2. 任务计划文件保存在 `plans/` 目录  
3. 上下文文件保存在 `contexts/` 目录
4. 执行日志保存在 `logs/` 目录
5. 临时文件保存在 `temp/` 目录，系统会自动清理

## 与记忆系统集成
- 所有重要文件都会自动记录到记忆系统
- 工作空间操作成为长期记忆的一部分
- 支持智能搜索和检索

## 清理策略
- 临时文件超过 24 小时自动清理
- 每个目录最多保存 1000 个文件
- 重要文件不会被自动清理

---
*此文件由AgentBus工作空间系统自动生成和更新*
