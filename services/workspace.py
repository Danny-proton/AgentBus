"""
Agent WorkSpace 管理器
初始化和管理 Agent 工作空间，包含所有运行时文件
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict


logger = logging.getLogger(__name__)


@dataclass
class WorkspaceFile:
    """工作空间文件"""
    path: str
    name: str
    file_type: str
    created_at: str
    updated_at: str
    size: int
    metadata: Dict[str, Any] = None


class AgentWorkSpace:
    """
    Agent 工作空间
    包含所有运行时文件：logs、agent.md、knowledge bus、临时脚本等
    """
    
    def __init__(self, workspace_path: str, create_if_not_exists: bool = True):
        self.root_path = Path(workspace_path)
        self.create_structure()
        
        # 子目录
        self.logs_dir = self.root_path / "logs"
        self.scripts_dir = self.root_path / "scripts"
        self.plans_dir = self.root_path / "plans"
        self.contexts_dir = self.root_path / "contexts"
        self.temp_dir = self.root_path / "temp"
        
        # 核心文件路径
        self.agent_md_path = self.root_path / "agent.md"
        self.knowledge_bus_path = self.root_path / "knowledge_bus.md"
        self.session_json_path = self.root_path / "session.json"
        
        if create_if_not_exists:
            self.create_structure()
    
    def create_structure(self):
        """创建工作空间目录结构"""
        self.root_path.mkdir(parents=True, exist_ok=True)
        
        # 子目录
        (self.root_path / "logs").mkdir(exist_ok=True)
        (self.root_path / "scripts").mkdir(exist_ok=True)
        (self.root_path / "plans").mkdir(exist_ok=True)
        (self.root_path / "contexts").mkdir(exist_ok=True)
        (self.root_path / "temp").mkdir(exist_ok=True)
        
        # 核心文件
        if not self.agent_md_path.exists():
            self._create_agent_md()
        
        if not self.knowledge_bus_path.exists():
            self._create_empty_knowledge_bus()
        
        if not self.session_json_path.exists():
            self._create_session_json()
        
        logger.info(f"AgentWorkSpace created: {self.root_path}")
    
    def _create_agent_md(self):
        """创建 agent.md 文件"""
        content = f"""# AgentBus 工作空间

## 创建时间
{datetime.now().isoformat()}

## 当前会话信息
- 会话 ID: 待初始化
- 主模型: 待配置
- 工作模式: 标准

## 使用说明

此目录为 AgentBus 的工作空间，包含以下内容：

### 目录结构
- `logs/` - 运行日志
- `scripts/` - 运行时生成的脚本
- `plans/` - 任务计划文件
- `contexts/` - 上下文文件
- `temp/` - 临时文件

### 核心文件
- `agent.md` - 本说明文件
- `knowledge_bus.md` - 知识总线（长期记忆）
- `session.json` - 会话状态

## 注意事项
- 所有 Agent 生成的文件默认放在此目录
- 日志文件会记录所有操作
- 知识总线用于跨会话共享信息
"""
        
        self.agent_md_path.write_text(content, encoding='utf-8')
    
    def _create_empty_knowledge_bus(self):
        """创建空的知识总线"""
        content = {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "entries": {}
        }
        
        self.knowledge_bus_path.write_text(
            json.dumps(content, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    
    def _create_session_json(self):
        """创建会话状态文件"""
        content = {
            "created_at": datetime.now().isoformat(),
            "session_id": None,
            "status": "initialized",
            "main_agent": None,
            "models": {},
            "statistics": {
                "total_requests": 0,
                "total_tool_calls": 0,
                "total_errors": 0
            }
        }
        
        self.session_json_path.write_text(
            json.dumps(content, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    
    def get_path(self) -> str:
        """获取工作空间根路径"""
        return str(self.root_path)
    
    def get_logs_path(self) -> str:
        """获取日志目录"""
        return str(self.logs_dir)
    
    def get_scripts_path(self) -> str:
        """获取脚本目录"""
        return str(self.scripts_dir)
    
    def get_plans_path(self) -> str:
        """获取计划目录"""
        return str(self.plans_dir)
    
    def get_contexts_path(self) -> str:
        """获取上下文目录"""
        return str(self.contexts_dir)
    
    def get_temp_path(self) -> str:
        """获取临时目录"""
        return str(self.temp_dir)
    
    def get_agent_md_path(self) -> str:
        """获取 agent.md 路径"""
        return str(self.agent_md_path)
    
    def get_knowledge_bus_path(self) -> str:
        """获取 knowledge_bus.md 路径"""
        return str(self.knowledge_bus_path)
    
    def write_script(self, filename: str, content: str) -> str:
        """
        写入脚本文件
        
        Args:
            filename: 文件名
            content: 脚本内容
        
        Returns:
            str: 完整路径
        """
        script_path = self.scripts_dir / filename
        script_path.write_text(content, encoding='utf-8')
        logger.info(f"Script written: {script_path}")
        return str(script_path)
    
    def write_plan(self, filename: str, content: str) -> str:
        """
        写入计划文件
        
        Args:
            filename: 文件名
            content: 计划内容
        
        Returns:
            str: 完整路径
        """
        plan_path = self.plans_dir / filename
        plan_path.write_text(content, encoding='utf-8')
        logger.info(f"Plan written: {plan_path}")
        return str(plan_path)
    
    def write_context(self, filename: str, content: str) -> str:
        """
        写入上下文文件
        
        Args:
            filename: 文件名
            content: 上下文内容
        
        Returns:
            str: 完整路径
        """
        context_path = self.contexts_dir / filename
        context_path.write_text(content, encoding='utf-8')
        logger.info(f"Context written: {context_path}")
        return str(context_path)
    
    def write_temp(self, filename: str, content: str) -> str:
        """
        写入临时文件
        
        Args:
            filename: 文件名
            content: 内容
        
        Returns:
            str: 完整路径
        """
        temp_path = self.temp_dir / filename
        temp_path.write_text(content, encoding='utf-8')
        return str(temp_path)
    
    def read_file(self, relative_path: str) -> Optional[str]:
        """
        读取工作空间内的文件
        
        Args:
            relative_path: 相对路径
        
        Returns:
            str: 文件内容，不存在返回 None
        """
        file_path = self.root_path / relative_path
        
        if file_path.exists() and file_path.is_file():
            return file_path.read_text(encoding='utf-8')
        
        return None
    
    def list_files(
        self,
        directory: str = ".",
        file_type: Optional[str] = None,
        recursive: bool = False
    ) -> List[WorkspaceFile]:
        """
        列出工作空间文件
        
        Args:
            directory: 目录（相对于工作空间根目录）
            file_type: 文件类型过滤
            recursive: 递归列出
        
        Returns:
            List[WorkspaceFile]: 文件列表
        """
        base_dir = self.root_path / directory
        
        if not base_dir.exists() or not base_dir.is_dir():
            return []
        
        files = []
        
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        for file_path in base_dir.glob(pattern):
            if file_path.is_file():
                stat = file_path.stat()
                
                # 文件类型判断
                ext = file_path.suffix.lower()
                if file_type:
                    if file_type == "script" and ext not in ['.py', '.sh', '.js', '.ts']:
                        continue
                    elif file_type == "plan" and ext != '.md':
                        continue
                    elif file_type == "log" and ext != '.log':
                        continue
                
                files.append(WorkspaceFile(
                    path=str(file_path.relative_to(self.root_path)),
                    name=file_path.name,
                    file_type=ext[1:] if ext else 'file',
                    created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    updated_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    size=stat.st_size
                ))
        
        return sorted(files, key=lambda x: x.updated_at, reverse=True)
    
    def update_session(self, session_data: Dict[str, Any]):
        """更新会话状态"""
        if self.session_json_path.exists():
            try:
                current = json.loads(
                    self.session_json_path.read_text(encoding='utf-8')
                )
                current.update(session_data)
                current["updated_at"] = datetime.now().isoformat()
                
                self.session_json_path.write_text(
                    json.dumps(current, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
            except Exception as e:
                logger.error(f"Failed to update session: {e}")
    
    def get_session(self) -> Dict[str, Any]:
        """获取会话状态"""
        if self.session_json_path.exists():
            try:
                return json.loads(
                    self.session_json_path.read_text(encoding='utf-8')
                )
            except Exception as e:
                logger.error(f"Failed to get session: {e}")
        
        return {}
    
    def cleanup_temp(self, max_age_hours: int = 24):
        """清理临时文件"""
        if not self.temp_dir.exists():
            return
        
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        deleted = []
        for file_path in self.temp_dir.glob("*"):
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff:
                    file_path.unlink()
                    deleted.append(str(file_path))
        
        if deleted:
            logger.info(f"Cleaned up {len(deleted)} temp files")
        
        return deleted
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取工作空间统计"""
        stats = {
            "workspace_path": str(self.root_path),
            "directories": {
                "logs": len(list(self.logs_dir.glob("*"))),
                "scripts": len(list(self.scripts_dir.glob("*"))),
                "plans": len(list(self.plans_dir.glob("*"))),
                "contexts": len(list(self.contexts_dir.glob("*"))),
                "temp": len(list(self.temp_dir.glob("*")))
            },
            "files": {
                "agent_md": self.agent_md_path.exists(),
                "knowledge_bus": self.knowledge_bus_path.exists(),
                "session": self.session_json_path.exists()
            },
            "total_size": 0
        }
        
        # 计算总大小
        for file_path in self.root_path.rglob("*"):
            if file_path.is_file():
                stats["total_size"] += file_path.stat().st_size
        
        stats["total_size_mb"] = round(stats["total_size"] / (1024 * 1024), 2)
        
        return stats


# 全局工作空间实例
_workspace: Optional[AgentWorkSpace] = None


def get_workspace() -> AgentWorkSpace:
    """获取全局工作空间实例"""
    global _workspace
    if _workspace is None:
        raise RuntimeError("AgentWorkSpace not initialized. Call init_workspace first.")
    return _workspace


def init_workspace(workspace_path: str) -> AgentWorkSpace:
    """初始化全局工作空间"""
    global _workspace
    _workspace = AgentWorkSpace(workspace_path)
    return _workspace


def get_workspace_path() -> str:
    """获取当前工作空间路径（从环境变量或默认路径）"""
    import os
    
    # 检查环境变量
    path = os.environ.get("AGENTBUS_WORKSPACE")
    if path:
        return path
    
    # 默认路径
    return "./workspace"
