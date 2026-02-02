"""
WebExplorer Agent Types - 类型定义
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


class ExplorerState(Enum):
    """Agent状态枚举"""
    IDLE = "idle"                    # 空闲
    LOCATING = "locating"            # 定位当前状态
    ANALYZING = "analyzing"          # 分析页面
    DECIDING = "deciding"            # 决策下一步
    ACTING = "acting"                # 执行动作
    REFLECTING = "reflecting"        # 反思结果
    BACKTRACKING = "backtracking"    # 回溯
    TESTING = "testing"              # 深度测试
    TELEPORTING = "teleporting"      # 瞬移
    COMPLETED = "completed"          # 完成
    ERROR = "error"                  # 错误


@dataclass
class ExplorerConfig:
    """Explorer配置"""
    # 基础配置
    agent_id: str = "web_explorer_001"
    start_url: str = ""
    
    # 探索限制
    max_depth: int = 5               # 最大深度
    max_nodes: int = 100             # 最大节点数
    max_iterations: int = 1000       # 最大迭代次数
    
    # 超时配置
    action_timeout: float = 30.0     # 单个动作超时(秒)
    page_load_timeout: float = 30.0  # 页面加载超时(秒)
    
    # Atlas配置
    atlas_root: str = "project_memory"
    
    # 浏览器配置
    headless: bool = False
    viewport_width: int = 1920
    viewport_height: int = 1080
    
    # LLM配置
    model_provider: str = "openai"
    model_name: str = "gpt-4"
    temperature: float = 0.7
    
    # 调试配置
    debug: bool = False
    save_screenshots: bool = True


@dataclass
class NodeInfo:
    """节点信息"""
    node_id: str
    url: str
    depth: int
    parent_id: Optional[str] = None
    action_from_parent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExplorationResult:
    """探索结果"""
    total_nodes: int = 0
    total_edges: int = 0
    max_depth_reached: int = 0
    atlas_path: str = ""
    errors: list = field(default_factory=list)
