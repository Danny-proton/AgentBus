---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: 5edd6666bd17c4cc9135a4816770ae6d
    PropagateID: 5edd6666bd17c4cc9135a4816770ae6d
    ReservedCode1: 3046022100800a44874428626a0f829f87d7e9ab7f1ff7c3b7807bd098a92ff9aa675cecb0022100ed0960cf15fe3e98548d10906f80ac4c58ea94fb2b3287cfbaf175992fcb94cf
    ReservedCode2: 3046022100ede259660e0a78ecd1eaaf762eb8f8c4510f8a83844ee169224188fc1e863119022100fda2a9a2a2e9b93ed5e90d8970822b22e449a01ff9691014d9721942783b4097
---

# AgentBus Memory System Enhancement

基于Moltbot的Memory系统架构，本项目对现有的AgentBus内存管理功能进行了全面增强和迁移。

## 🚀 新增功能

### 1. 向量数据库支持
- **模块**: `vector_store.py`
- **功能**: 
  - 基于SQLite的向量存储
  - 向量相似性搜索（余弦相似度）
  - 批量向量操作
  - 向量去重和归一化
  - 支持SQLite扩展（sqlite-vicdb, sqlite-vss）

### 2. 混合内存存储
- **模块**: `hybrid_search.py`
- **功能**:
  - 向量搜索 + 关键词搜索融合
  - 多种搜索策略（混合搜索、排名融合）
  - 自适应权重调整
  - 结果去重和重排序
  - 时间衰减评分

### 3. 批量处理功能
- **模块**: `batch_processor.py`
- **功能**:
  - 并发批量处理
  - 进度跟踪和回调
  - 错误处理和重试机制
  - 内存高效的流式处理
  - 支持自定义操作

### 4. 嵌入生成支持
- **模块**: `embedding_manager.py`
- **功能**:
  - 多提供商支持（OpenAI、HuggingFace、本地模型）
  - 自动故障转移
  - 结果缓存优化
  - 批量嵌入生成
  - 速率限制和重试机制

### 5. 内存索引和搜索
- **模块**: `memory_index.py`
- **功能**:
  - 多源内存索引
  - 自动分块和嵌入生成
  - 全文搜索（FTS支持）
  - 元数据过滤
  - 重要性评分和排序
  - 自动清理和优化

## 🏗️ 架构设计

### 核心组件

```
EnhancedMemoryManager (统一接口)
├── VectorStore (向量存储)
├── EmbeddingManager (嵌入生成)
├── HybridSearchEngine (混合搜索)
├── BatchProcessor (批量处理)
├── MemoryIndexer (内存索引)
└── UserMemory (原有系统集成)
```

### 数据流

```
用户输入 → 嵌入生成 → 向量存储 → 内存索引 → 混合搜索 → 结果返回
    ↓
批量处理 → 异步处理 → 缓存优化 → 性能监控
```

## 📋 增强对比

| 功能 | 原系统 | 增强系统 |
|------|--------|----------|
| 存储方式 | 仅SQLite | SQLite + 向量数据库 |
| 搜索能力 | 关键词搜索 | 向量搜索 + 关键词搜索 |
| 嵌入生成 | 不支持 | 多提供商支持 |
| 批处理 | 手动处理 | 自动批量处理 |
| 性能优化 | 基础索引 | 自动优化和清理 |
| 扩展性 | 单一数据源 | 多源混合存储 |
| 智能搜索 | 基础搜索 | AI驱动的混合搜索 |

## 🛠️ 使用示例

### 基本使用

```python
from agentbus.memory import EnhancedMemoryManager, EnhancedMemoryConfig

# 配置增强内存管理器
config = EnhancedMemoryConfig(
    embedding_provider="fake",  # 或 "openai", "huggingface"
    embedding_model="text-embedding-ada-002",
    enable_vector_store=True,
    hybrid_search_weights=(0.7, 0.3)
)

# 初始化管理器
memory_manager = EnhancedMemoryManager(config)
await memory_manager.initialize()

# 存储记忆
memory_id = await memory_manager.store_memory(
    content="Python is a programming language",
    source="technical",
    memory_type="knowledge",
    tags=["python", "programming"]
)

# 混合搜索
results = await memory_manager.search_memories(
    query="Python programming",
    strategy="hybrid",
    limit=10
)
```

### 批量操作

```python
# 批量存储记忆
memories = [
    {"content": f"Technical note {i}", "source": "batch"}
    for i in range(100)
]

batch_result = await memory_manager.batch_store_memories(memories)
print(f"处理了 {batch_result.successful_items} 个记忆")
```

### 高级搜索

```python
from agentbus.memory import SearchStrategy, WeightingScheme

# 自定义搜索
results = await memory_manager.search_memories(
    query="machine learning algorithms",
    source_filter=["technical", "research"],
    memory_type_filter=["knowledge", "concept"],
    tags_filter=["ai", "ml"],
    strategy="hybrid",
    limit=20
)
```

## 🔧 配置选项

### Embedding配置

```python
config = EnhancedMemoryConfig(
    embedding_provider="openai",      # openai, huggingface, local, fake
    embedding_model="text-embedding-ada-002",
    embedding_api_key="your-api-key",
    embedding_base_url="custom-endpoint"
)
```

### 向量存储配置

```python
config = EnhancedMemoryConfig(
    enable_vector_store=True,
    vector_similarity_threshold=0.7,
    max_vector_results=100
)
```

### 搜索配置

```python
config = EnhancedMemoryConfig(
    hybrid_search_weights=(0.7, 0.3),  # (向量权重, 关键词权重)
    enable_query_expansion=True,
    max_search_results=20
)
```

### 批处理配置

```python
config = EnhancedMemoryConfig(
    batch_size=50,
    max_concurrent_batches=3,
    batch_timeout=300.0
)
```

## 📊 性能特性

### 性能优化

- **向量缓存**: 嵌入结果自动缓存
- **批量处理**: 减少API调用开销
- **异步处理**: 非阻塞操作
- **数据库优化**: 自动清理和整理
- **智能索引**: 自动优化查询性能

### 监控指标

```python
stats = await memory_manager.get_memory_stats()
print(f"嵌入生成: {stats['embedding_manager']['requests']}")
print(f"搜索性能: {stats['hybrid_search']['average_processing_time']}s")
print(f"缓存命中率: {stats['embedding_manager']['cache_hit_rate']:.3f}")
```

## 🧪 测试和示例

运行示例脚本查看完整功能演示：

```bash
python agentbus/memory/example_usage.py
```

示例包括：
- 基本内存操作
- 混合搜索演示
- 批量处理操作
- 性能监控
- 高级功能展示

## 📈 升级路径

### 从原系统迁移

1. **向后兼容**: 原有的UserMemory、ConversationHistory等组件保持不变
2. **渐进式升级**: 可以逐步启用新功能
3. **数据迁移**: 支持将现有数据导入到新系统
4. **配置切换**: 通过配置选择使用原系统或增强系统

### 配置示例

```python
# 原系统模式（保持原有功能）
from agentbus.memory import UserMemory
user_memory = UserMemory()

# 增强系统模式（启用所有新功能）
from agentbus.memory import EnhancedMemoryManager
enhanced_memory = EnhancedMemoryManager(EnhancedMemoryConfig())
```

## 🔮 未来扩展

### 计划功能

- **多模态支持**: 图像、音频记忆存储
- **分布式存储**: 支持向量数据库集群
- **实时同步**: 多实例数据同步
- **更智能搜索**: 语义理解和上下文感知
- **自动标签**: AI自动标签生成

### 扩展接口

系统设计支持插件式扩展：
- 自定义嵌入提供商
- 自定义搜索算法
- 自定义评分策略
- 自定义存储后端

## 📚 参考文档

- [Moltbot Memory System](https://github.com/mol泡泡/moltbot) - 原始架构参考
- [Vector Databases](https://github.com/erikbern/ann-benchmarks) - 向量搜索基准
- [Sentence Transformers](https://www.sbert.net/) - 嵌入模型库
- [SQLite Extensions](https://sqlite.org/loadext.html) - 数据库扩展

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个增强的内存系统！

## 📄 许可证

本项目继承AgentBus的许可证条款。