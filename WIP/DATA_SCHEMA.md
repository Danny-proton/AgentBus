# WebExplorer Agent - 数据协议规范

**文件系统数据库设计**

---

## 1. 总体设计原则

### 1.1 核心理念

- **目录即节点**: 每个目录代表网站的一个状态
- **软链接即边**: 目录间的软链接代表状态转换
- **文件即数据**: 使用JSON文件存储元数据
- **约定优于配置**: 标准化的目录结构和文件命名

### 1.2 设计目标

- ✅ 人类可读: 可以直接在文件管理器中浏览
- ✅ 版本控制友好: 可以用Git追踪变化
- ✅ 跨平台兼容: Windows/Linux/Mac通用
- ✅ 易于调试: 所有数据都是明文JSON

---

## 2. 目录结构规范

### 2.1 根目录结构

```
project_memory/
├── index.json                 # 全局索引文件
├── config.json                # 项目配置
├── 00_Root/                   # 根节点(起始页面)
├── 01_Login/                  # 示例:登录页面
├── 02_Dashboard/              # 示例:仪表板
├── {hash}/                    # 其他状态节点
└── .atlas/                    # 元数据目录
    ├── graph.json             # 完整状态图
    ├── statistics.json        # 统计信息
    └── logs/                  # 日志文件
```

### 2.2 状态节点目录结构

每个状态节点目录必须包含以下标准结构:

```
{node_id}/
├── meta.json                  # [必需] 节点元数据
├── screenshot.png             # [必需] 页面截图
├── dom.json                   # [可选] DOM树快照
├── links/                     # [必需] 软链接目录
│   ├── action_login -> ../01_Login/
│   ├── action_search -> ../03_Search/
│   └── ...
├── scripts/                   # [必需] 脚本目录
│   ├── nav_login.py           # 导航到此状态的脚本
│   └── ...
├── todos/                     # [必需] 待办任务
│   ├── task_001.json
│   ├── task_002.json
│   └── ...
├── processing/                # [必需] 处理中的任务
│   └── task_001.json
├── completed/                 # [必需] 已完成的任务
│   └── task_001.json
├── test_ideas/                # [可选] 测试想法
│   ├── idea_001.json
│   └── ...
└── reports/                   # [可选] 测试报告
    └── test_report.md
```

---

## 3. JSON Schema定义

### 3.1 index.json (全局索引)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "version": {
      "type": "string",
      "description": "索引格式版本"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time"
    },
    "root_node": {
      "type": "string",
      "description": "根节点ID"
    },
    "nodes": {
      "type": "object",
      "description": "节点ID到路径的映射",
      "patternProperties": {
        "^[a-f0-9]{8,}$": {
          "type": "object",
          "properties": {
            "path": {"type": "string"},
            "url": {"type": "string"},
            "summary": {"type": "string"},
            "created_at": {"type": "string"}
          }
        }
      }
    },
    "statistics": {
      "type": "object",
      "properties": {
        "total_nodes": {"type": "integer"},
        "total_edges": {"type": "integer"},
        "max_depth": {"type": "integer"}
      }
    }
  }
}
```

**示例**:

```json
{
  "version": "1.0",
  "created_at": "2026-01-31T16:00:00Z",
  "updated_at": "2026-01-31T16:30:00Z",
  "root_node": "00_Root",
  "nodes": {
    "00_Root": {
      "path": "project_memory/00_Root",
      "url": "https://example.com",
      "summary": "网站首页",
      "created_at": "2026-01-31T16:00:00Z"
    },
    "01_Login": {
      "path": "project_memory/01_Login",
      "url": "https://example.com/login",
      "summary": "用户登录页面",
      "created_at": "2026-01-31T16:05:00Z"
    }
  },
  "statistics": {
    "total_nodes": 15,
    "total_edges": 23,
    "max_depth": 4
  }
}
```

### 3.2 meta.json (节点元数据)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "url", "created_at"],
  "properties": {
    "id": {
      "type": "string",
      "description": "节点唯一ID(Hash)"
    },
    "url": {
      "type": "string",
      "description": "页面URL"
    },
    "title": {
      "type": "string",
      "description": "页面标题"
    },
    "summary": {
      "type": "string",
      "description": "页面摘要(LLM生成)"
    },
    "dom_fingerprint": {
      "type": "string",
      "description": "DOM指纹Hash"
    },
    "screenshot": {
      "type": "string",
      "description": "截图文件路径"
    },
    "parent_id": {
      "type": "string",
      "description": "父节点ID"
    },
    "source_action": {
      "type": "string",
      "description": "到达此状态的动作描述"
    },
    "depth": {
      "type": "integer",
      "description": "从根节点的深度"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "visited_count": {
      "type": "integer",
      "description": "访问次数"
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "标签列表"
    }
  }
}
```

**示例**:

```json
{
  "id": "01_Login",
  "url": "https://example.com/login",
  "title": "用户登录 - Example Site",
  "summary": "用户登录页面,包含用户名和密码输入框",
  "dom_fingerprint": "a3f5e9c2d1b4...",
  "screenshot": "screenshot.png",
  "parent_id": "00_Root",
  "source_action": "点击首页的登录按钮",
  "depth": 1,
  "created_at": "2026-01-31T16:05:00Z",
  "visited_count": 3,
  "tags": ["auth", "form"]
}
```

### 3.3 task.json (待办任务)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "selector", "action", "priority"],
  "properties": {
    "id": {
      "type": "string",
      "description": "任务唯一ID"
    },
    "selector": {
      "type": "string",
      "description": "CSS选择器或XPath"
    },
    "action": {
      "type": "string",
      "enum": ["click", "type", "navigate", "scroll"],
      "description": "动作类型"
    },
    "parameters": {
      "type": "object",
      "description": "动作参数(如type动作的文本内容)"
    },
    "priority": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "description": "优先级(1-10,越大越优先)"
    },
    "reason": {
      "type": "string",
      "description": "探索理由"
    },
    "is_destructive": {
      "type": "boolean",
      "description": "是否为破坏性操作"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "status": {
      "type": "string",
      "enum": ["pending", "processing", "completed", "failed"]
    }
  }
}
```

**示例**:

```json
{
  "id": "task_001",
  "selector": "#search-input",
  "action": "type",
  "parameters": {
    "text": "test query"
  },
  "priority": 8,
  "reason": "测试搜索功能",
  "is_destructive": false,
  "created_at": "2026-01-31T16:10:00Z",
  "status": "pending"
}
```

### 3.4 test_idea.json (测试想法)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "name", "type"],
  "properties": {
    "id": {
      "type": "string"
    },
    "name": {
      "type": "string",
      "description": "测试点名称"
    },
    "description": {
      "type": "string",
      "description": "测试描述"
    },
    "type": {
      "type": "string",
      "enum": ["boundary", "injection", "permission", "performance", "accessibility"],
      "description": "测试类型"
    },
    "target_selector": {
      "type": "string",
      "description": "测试目标元素"
    },
    "test_cases": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "input": {"type": "string"},
          "expected": {"type": "string"}
        }
      }
    },
    "priority": {
      "type": "integer"
    },
    "created_at": {
      "type": "string"
    }
  }
}
```

---

## 4. 文件命名规范

### 4.1 节点目录命名

格式: `{序号}_{语义名称}` 或 `{hash}`

- **根节点**: `00_Root`
- **有明确语义**: `01_Login`, `02_Dashboard`, `03_UserProfile`
- **无明确语义**: 使用Hash的前8位,如 `a3f5e9c2`

### 4.2 任务文件命名

格式: `task_{序号}.json`

- 示例: `task_001.json`, `task_002.json`
- 序号补零到3位

### 4.3 脚本文件命名

格式: `{动作}_{目标}.py`

- 示例: `nav_login.py`, `click_search_button.py`
- 使用小写和下划线

---

## 5. 软链接规范

### 5.1 链接命名

格式: `action_{动作描述}`

- 示例: `action_login`, `action_search`, `action_view_details`

### 5.2 链接创建

**Python代码示例**:

```python
import os
from pathlib import Path

def create_state_link(source_dir: Path, action_name: str, target_dir: Path):
    """创建状态链接"""
    links_dir = source_dir / "links"
    links_dir.mkdir(exist_ok=True)
    
    link_name = f"action_{action_name}"
    link_path = links_dir / link_name
    
    # 计算相对路径
    relative_target = os.path.relpath(target_dir, links_dir)
    
    # 创建软链接
    if not link_path.exists():
        link_path.symlink_to(relative_target, target_is_directory=True)
```

### 5.3 跨平台兼容性

**Windows注意事项**:
- 需要管理员权限或开发者模式
- 使用 `os.symlink` 时设置 `target_is_directory=True`

**Fallback方案**:
- 如果软链接创建失败,使用JSON文件记录链接关系
- 文件名: `_links.json`

```json
{
  "action_login": "../01_Login",
  "action_search": "../03_Search"
}
```

---

## 6. DOM指纹计算

### 6.1 指纹算法

```python
import hashlib
import json

def calculate_dom_fingerprint(dom_tree: dict) -> str:
    """
    计算DOM指纹
    
    策略:
    1. 提取关键元素(忽略动态内容)
    2. 标准化排序
    3. 计算SHA256
    """
    # 提取关键特征
    features = {
        "url": dom_tree.get("url", ""),
        "title": dom_tree.get("title", ""),
        "forms": extract_forms(dom_tree),
        "links": extract_links(dom_tree),
        "structure": extract_structure(dom_tree)
    }
    
    # 标准化JSON
    normalized = json.dumps(features, sort_keys=True)
    
    # 计算Hash
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]

def extract_forms(dom_tree: dict) -> list:
    """提取表单特征"""
    # 忽略value,只保留name和type
    pass

def extract_links(dom_tree: dict) -> list:
    """提取链接特征"""
    # 只保留href,忽略文本
    pass

def extract_structure(dom_tree: dict) -> str:
    """提取DOM结构特征"""
    # 只保留标签层次,忽略内容
    pass
```

---

## 7. 数据迁移和版本控制

### 7.1 版本标识

在 `index.json` 中使用 `version` 字段标识数据格式版本。

当前版本: `1.0`

### 7.2 向后兼容

如果数据格式升级,提供迁移脚本:

```python
async def migrate_v1_to_v2(project_dir: Path):
    """从v1迁移到v2"""
    # 读取旧格式
    # 转换数据
    # 写入新格式
    pass
```

---

## 8. 性能优化

### 8.1 索引缓存

- 在内存中缓存 `index.json`
- 仅在节点创建/删除时更新
- 使用文件锁防止并发写入

### 8.2 延迟写入

- 批量创建节点时,最后统一更新索引
- 使用异步IO减少阻塞

---

## 9. 安全考虑

### 9.1 路径注入防护

```python
def sanitize_node_id(node_id: str) -> str:
    """清理节点ID,防止路径遍历"""
    # 移除 ../ 等危险字符
    return re.sub(r'[^\w\-]', '_', node_id)
```

### 9.2 文件大小限制

- 单个JSON文件不超过10MB
- 截图文件不超过5MB
- 超过限制时压缩或分片

---

## 10. 调试和监控

### 10.1 日志记录

在 `.atlas/logs/` 目录下记录:
- `operations.log`: 所有文件操作
- `errors.log`: 错误日志
- `performance.log`: 性能指标

### 10.2 完整性检查

定期运行检查脚本:

```python
async def check_atlas_integrity(project_dir: Path):
    """检查Atlas完整性"""
    # 检查所有节点是否有meta.json
    # 检查软链接是否有效
    # 检查index.json与实际目录是否一致
    pass
```

---

**文档状态**: 初稿完成  
**下一步**: 创建开发计划文档
