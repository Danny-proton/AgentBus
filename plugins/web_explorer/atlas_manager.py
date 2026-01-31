"""
AtlasManager Plugin - 文件系统状态管理插件

负责管理WebExplorer的状态地图(Atlas):
- 创建和管理状态节点目录
- 创建状态间的软链接
- 管理待办任务队列
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Literal
from datetime import datetime

from plugins.core import AgentBusPlugin, PluginContext


logger = logging.getLogger(__name__)


class AtlasManagerPlugin(AgentBusPlugin):
    """文件系统状态地图管理插件"""
    
    NAME = "atlas_manager"
    VERSION = "1.0.0"
    DESCRIPTION = "管理WebExplorer的文件系统状态地图"
    AUTHOR = "AgentBus Team"
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        
        # 配置
        self.atlas_root = Path("project_memory")
        self.index_file = self.atlas_root / "index.json"
        
        # 内存缓存
        self._index_cache: Optional[Dict[str, Any]] = None
        self._node_counter = 0
    
    def get_info(self) -> Dict[str, Any]:
        """返回插件信息"""
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "description": self.DESCRIPTION,
            "author": self.AUTHOR,
            "status": self.status.value,
            "atlas_root": str(self.atlas_root),
            "total_nodes": len(self._load_index().get("nodes", {}))
        }
    
    async def activate(self) -> bool:
        """激活插件"""
        try:
            # 初始化Atlas根目录
            self.atlas_root.mkdir(parents=True, exist_ok=True)
            
            # 初始化或加载索引
            if not self.index_file.exists():
                self._create_index()
            else:
                self._load_index()
            
            # 注册工具
            self.register_tool(
                name="ensure_state",
                description="确保状态节点存在",
                function=self.ensure_state,
                parameters={
                    "url": {"type": "string", "description": "页面URL"},
                    "dom_fingerprint": {"type": "string", "description": "DOM指纹"},
                    "screenshot_path": {"type": "string", "description": "截图路径"},
                    "metadata": {"type": "object", "description": "额外元数据", "default": None}
                }
            )
            
            self.register_tool(
                name="link_state",
                description="创建状态间的软链接",
                function=self.link_state,
                parameters={
                    "source_node_id": {"type": "string", "description": "源节点ID"},
                    "action_name": {"type": "string", "description": "动作名称"},
                    "target_node_id": {"type": "string", "description": "目标节点ID"}
                }
            )
            
            self.register_tool(
                name="manage_todos",
                description="管理待办任务",
                function=self.manage_todos,
                parameters={
                    "node_id": {"type": "string", "description": "节点ID"},
                    "mode": {"type": "string", "enum": ["push", "pop"], "description": "操作模式"},
                    "tasks": {"type": "array", "description": "任务列表(push模式)", "default": None}
                }
            )
            
            self.register_tool(
                name="get_path_to_node",
                description="获取从根节点到目标节点的路径",
                function=self.get_path_to_node,
                parameters={
                    "target_node_id": {"type": "string", "description": "目标节点ID"}
                }
            )
            
            self.logger.info(f"插件 {self.NAME} 激活成功")
            return True
            
        except Exception as e:
            self.logger.error(f"插件激活失败: {e}", exc_info=True)
            return False
    
    async def deactivate(self) -> bool:
        """停用插件"""
        # 保存索引
        if self._index_cache:
            self._save_index()
        
        self.logger.info(f"插件 {self.NAME} 已停用")
        return True
    
    # ========== 核心功能 ==========
    
    async def ensure_state(
        self,
        url: str,
        dom_fingerprint: str,
        screenshot_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        确保状态节点存在
        
        Args:
            url: 页面URL
            dom_fingerprint: DOM指纹
            screenshot_path: 截图路径
            metadata: 额外元数据
        
        Returns:
            {
                "node_id": str,
                "node_path": str,
                "is_new": bool,
                "meta_file": str
            }
        """
        try:
            # 计算节点ID (Hash)
            node_id = self._calculate_node_id(url, dom_fingerprint)
            
            # 检查节点是否已存在
            index = self._load_index()
            is_new = node_id not in index["nodes"]
            
            if is_new:
                # 创建新节点
                node_path = await self._create_node_directory(
                    node_id, url, dom_fingerprint, screenshot_path, metadata
                )
                
                # 更新索引
                index["nodes"][node_id] = {
                    "path": str(node_path),
                    "url": url,
                    "summary": metadata.get("summary", "") if metadata else "",
                    "created_at": datetime.now().isoformat()
                }
                index["statistics"]["total_nodes"] = len(index["nodes"])
                index["updated_at"] = datetime.now().isoformat()
                
                self._save_index()
                
                self.logger.info(f"创建新节点: {node_id} ({url})")
            else:
                node_path = Path(index["nodes"][node_id]["path"])
                self.logger.debug(f"节点已存在: {node_id}")
            
            meta_file = node_path / "meta.json"
            
            return {
                "node_id": node_id,
                "node_path": str(node_path),
                "is_new": is_new,
                "meta_file": str(meta_file)
            }
            
        except Exception as e:
            self.logger.error(f"ensure_state失败: {e}", exc_info=True)
            raise
    
    async def link_state(
        self,
        source_node_id: str,
        action_name: str,
        target_node_id: str
    ) -> bool:
        """
        创建状态间的软链接
        
        Args:
            source_node_id: 源节点ID
            action_name: 动作名称
            target_node_id: 目标节点ID
        
        Returns:
            是否创建成功
        """
        try:
            index = self._load_index()
            
            # 验证节点存在
            if source_node_id not in index["nodes"]:
                raise ValueError(f"源节点不存在: {source_node_id}")
            if target_node_id not in index["nodes"]:
                raise ValueError(f"目标节点不存在: {target_node_id}")
            
            source_path = Path(index["nodes"][source_node_id]["path"])
            target_path = Path(index["nodes"][target_node_id]["path"])
            
            # 创建links目录
            links_dir = source_path / "links"
            links_dir.mkdir(exist_ok=True)
            
            # 链接名称
            link_name = f"action_{self._sanitize_name(action_name)}"
            link_path = links_dir / link_name
            
            # 如果链接已存在,跳过
            if link_path.exists():
                self.logger.debug(f"链接已存在: {link_path}")
                return True
            
            # 计算相对路径
            relative_target = os.path.relpath(target_path, links_dir)
            
            # 创建软链接
            try:
                link_path.symlink_to(relative_target, target_is_directory=True)
                self.logger.info(f"创建软链接: {link_path} -> {relative_target}")
                
                # 更新统计
                index["statistics"]["total_edges"] = index["statistics"].get("total_edges", 0) + 1
                self._save_index()
                
                return True
                
            except OSError as e:
                # Windows上可能需要管理员权限,使用Fallback方案
                self.logger.warning(f"软链接创建失败,使用JSON记录: {e}")
                await self._create_link_fallback(source_path, link_name, str(relative_target))
                return True
            
        except Exception as e:
            self.logger.error(f"link_state失败: {e}", exc_info=True)
            return False
    
    async def manage_todos(
        self,
        node_id: str,
        mode: Literal["push", "pop"],
        tasks: Optional[List[Dict[str, Any]]] = None
    ) -> Union[List[Dict[str, Any]], bool]:
        """
        管理待办任务
        
        Args:
            node_id: 节点ID
            mode: "push"添加任务, "pop"获取任务
            tasks: 任务列表(push模式必需)
        
        Returns:
            push模式: bool
            pop模式: List[Dict]
        """
        try:
            index = self._load_index()
            
            if node_id not in index["nodes"]:
                raise ValueError(f"节点不存在: {node_id}")
            
            node_path = Path(index["nodes"][node_id]["path"])
            todos_dir = node_path / "todos"
            processing_dir = node_path / "processing"
            
            todos_dir.mkdir(exist_ok=True)
            processing_dir.mkdir(exist_ok=True)
            
            if mode == "push":
                return await self._push_tasks(todos_dir, tasks or [])
            elif mode == "pop":
                return await self._pop_tasks(todos_dir, processing_dir)
            else:
                raise ValueError(f"未知模式: {mode}")
                
        except Exception as e:
            self.logger.error(f"manage_todos失败: {e}", exc_info=True)
            if mode == "push":
                return False
            else:
                return []
    
    async def get_path_to_node(
        self,
        target_node_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取从根节点到目标节点的路径
        
        Args:
            target_node_id: 目标节点ID
        
        Returns:
            路径列表 [{node_id, action, script_path}, ...]
        """
        try:
            index = self._load_index()
            
            if target_node_id not in index["nodes"]:
                raise ValueError(f"节点不存在: {target_node_id}")
            
            # TODO: 实现路径查找算法(BFS或DFS)
            # 这里先返回空列表,后续实现
            self.logger.warning("get_path_to_node功能待实现")
            return []
            
        except Exception as e:
            self.logger.error(f"get_path_to_node失败: {e}", exc_info=True)
            return []
    
    # ========== 辅助方法 ==========
    
    def _calculate_node_id(self, url: str, dom_fingerprint: str) -> str:
        """计算节点ID"""
        # 组合URL和DOM指纹
        combined = f"{url}::{dom_fingerprint}"
        hash_value = hashlib.sha256(combined.encode()).hexdigest()[:16]
        
        # 如果是第一个节点,使用特殊ID
        if self._node_counter == 0:
            return "00_Root"
        
        # 使用计数器生成可读ID
        self._node_counter += 1
        return f"{self._node_counter:02d}_{hash_value[:8]}"
    
    async def _create_node_directory(
        self,
        node_id: str,
        url: str,
        dom_fingerprint: str,
        screenshot_path: str,
        metadata: Optional[Dict[str, Any]]
    ) -> Path:
        """创建节点目录结构"""
        node_path = self.atlas_root / node_id
        node_path.mkdir(parents=True, exist_ok=True)
        
        # 创建标准子目录
        (node_path / "links").mkdir(exist_ok=True)
        (node_path / "scripts").mkdir(exist_ok=True)
        (node_path / "todos").mkdir(exist_ok=True)
        (node_path / "processing").mkdir(exist_ok=True)
        (node_path / "completed").mkdir(exist_ok=True)
        
        # 创建meta.json
        meta = {
            "id": node_id,
            "url": url,
            "dom_fingerprint": dom_fingerprint,
            "screenshot": screenshot_path,
            "created_at": datetime.now().isoformat(),
            "visited_count": 1
        }
        
        if metadata:
            meta.update(metadata)
        
        meta_file = node_path / "meta.json"
        meta_file.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        
        return node_path
    
    def _create_index(self):
        """创建新索引"""
        index = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "root_node": "00_Root",
            "nodes": {},
            "statistics": {
                "total_nodes": 0,
                "total_edges": 0,
                "max_depth": 0
            }
        }
        
        self.index_file.write_text(json.dumps(index, indent=2, ensure_ascii=False))
        self._index_cache = index
        
        self.logger.info("创建新索引文件")
    
    def _load_index(self) -> Dict[str, Any]:
        """加载索引"""
        if self._index_cache is None:
            if self.index_file.exists():
                self._index_cache = json.loads(self.index_file.read_text())
                self._node_counter = len(self._index_cache.get("nodes", {}))
            else:
                self._create_index()
        
        return self._index_cache
    
    def _save_index(self):
        """保存索引"""
        if self._index_cache:
            self._index_cache["updated_at"] = datetime.now().isoformat()
            self.index_file.write_text(
                json.dumps(self._index_cache, indent=2, ensure_ascii=False)
            )
    
    async def _create_link_fallback(self, source_path: Path, link_name: str, target: str):
        """软链接Fallback方案:使用JSON记录"""
        fallback_file = source_path / "links" / "_links.json"
        
        links = {}
        if fallback_file.exists():
            links = json.loads(fallback_file.read_text())
        
        links[link_name] = target
        fallback_file.write_text(json.dumps(links, indent=2))
        
        self.logger.info(f"使用JSON记录链接: {link_name} -> {target}")
    
    async def _push_tasks(self, todos_dir: Path, tasks: List[Dict[str, Any]]) -> bool:
        """推送任务到队列"""
        try:
            for task in tasks:
                task_id = task.get("id", f"task_{datetime.now().timestamp()}")
                task_file = todos_dir / f"{task_id}.json"
                
                task["status"] = "pending"
                task["created_at"] = task.get("created_at", datetime.now().isoformat())
                
                task_file.write_text(json.dumps(task, indent=2, ensure_ascii=False))
            
            self.logger.info(f"推送 {len(tasks)} 个任务")
            return True
            
        except Exception as e:
            self.logger.error(f"推送任务失败: {e}")
            return False
    
    async def _pop_tasks(self, todos_dir: Path, processing_dir: Path) -> List[Dict[str, Any]]:
        """从队列获取任务"""
        try:
            # 获取所有待办任务
            task_files = list(todos_dir.glob("*.json"))
            
            if not task_files:
                return []
            
            # 读取并按优先级排序
            tasks = []
            for task_file in task_files:
                task = json.loads(task_file.read_text())
                task["_file"] = task_file
                tasks.append(task)
            
            # 按优先级排序(降序)
            tasks.sort(key=lambda t: t.get("priority", 0), reverse=True)
            
            # 移动到processing目录
            result_tasks = []
            for task in tasks:
                task_file = task.pop("_file")
                new_path = processing_dir / task_file.name
                task_file.rename(new_path)
                result_tasks.append(task)
            
            self.logger.info(f"获取 {len(result_tasks)} 个任务")
            return result_tasks
            
        except Exception as e:
            self.logger.error(f"获取任务失败: {e}")
            return []
    
    def _sanitize_name(self, name: str) -> str:
        """清理名称,移除非法字符"""
        import re
        # 只保留字母、数字、下划线和连字符
        return re.sub(r'[^\w\-]', '_', name)
