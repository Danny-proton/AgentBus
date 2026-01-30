---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: "00000000000000000000000000000000"
    PropagateID: "00000000000000000000000000000000"
    ReservedCode1: 30460221009cb4028ee853d0de3f435feb6a16dc52bce224935baea06755a74eaa3a9f2741022100cd8db8aa4aa40486b8ce705083e9a65b030b1ae99060d6450780ae9711bd5ba9
    ReservedCode2: 304402204fd2364ff585b721a6442c6d1124349674eaf7ca48ce58e84eda159138b0df65022032059432eb3ec357120680fd7c8ce375aa59889d10d1485cf68fe23734d22779
---

# AgentBus 工作空间

## 创建时间
2026-01-29 11:53:01

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
