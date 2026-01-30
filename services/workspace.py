"""
AgentBus Workspace Service
AgentBus工作空间服务 - 与记忆系统融合

工作空间管理与长期记忆系统集成，统一管理项目文件和工作空间操作
"""

import asyncio
import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field

import logging

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceFile:
    """工作空间文件信息"""
    name: str
    path: Path
    file_type: str  # script, plan, context, log, temp
    size: int
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkspaceStats:
    """工作空间统计信息"""
    workspace_path: str
    total_files: int
    total_size_mb: float
    directories: Dict[str, int] = field(default_factory=dict)
    file_types: Dict[str, int] = field(default_factory=dict)
    last_activity: Optional[datetime] = None


class AgentWorkSpace:
    """
    AgentBus工作空间服务
    
    与记忆系统深度集成，将工作空间文件也存储为Markdown格式，
    实现统一的文件管理和记忆系统
    """
    
    def __init__(self, base_path: str = "./workspace"):
        self.base_path = Path(base_path)
        self.storage_path = self.base_path / "workspace_memory"  # 工作空间记忆存储
        self.memory_integration = True  # 与记忆系统集成
        
        # 工作空间目录结构
        self.directories = {
            "logs": "logs",
            "scripts": "scripts", 
            "plans": "plans",
            "contexts": "contexts",
            "temp": "temp",
            "memory": "memory",  # 记忆系统集成
            "knowledge": "knowledge",  # 知识总线
            "agent": "agent"  # Agent相关文件
        }
        
        # 文件类型映射
        self.file_type_mapping = {
            ".sh": "script",
            ".py": "script", 
            ".js": "script",
            ".ts": "script",
            ".md": "context",
            ".txt": "context",
            ".json": "context",
            ".log": "log",
            ".tmp": "temp",
            ".bak": "temp"
        }
        
        # 自动清理配置
        self.auto_cleanup = True
        self.max_temp_age_hours = 24
        self.max_files_per_directory = 1000
        
        logger.info("AgentWorkSpace initialized", base_path=str(self.base_path))
    
    async def initialize(self) -> None:
        """初始化工作空间"""
        # 创建基础目录结构
        await self._create_directory_structure()
        
        # 创建工作空间说明文件
        await self._create_workspace_readme()
        
        # 创建工作空间索引
        await self._create_workspace_index()
        
        logger.info("AgentWorkSpace initialized successfully")
    
    async def _create_directory_structure(self) -> None:
        """创建目录结构"""
        for dir_name, dir_path in self.directories.items():
            full_path = self.base_path / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
        
        # 创建.gitkeep文件确保目录被git跟踪
        for dir_path in self.directories.values():
            gitkeep_path = self.base_path / dir_path / ".gitkeep"
            gitkeep_path.touch(exist_ok=True)
    
    async def _create_workspace_readme(self) -> None:
        """创建工作空间说明文件"""
        readme_content = f"""# AgentBus 工作空间

## 创建时间
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 当前会话信息
- 会话 ID: 待初始化
- 主模型: 待配置
- 工作模式: 标准

## 目录结构
{self._get_directory_description()}

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
- 临时文件超过 {self.max_temp_age_hours} 小时自动清理
- 每个目录最多保存 {self.max_files_per_directory} 个文件
- 重要文件不会被自动清理

---
*此文件由AgentBus工作空间系统自动生成和更新*
"""
        
        readme_path = self.base_path / "README.md"
        await self._write_markdown_file(readme_path, readme_content, {"workspace_info"})
    
    def _get_directory_description(self) -> str:
        """获取目录说明"""
        descriptions = {
            "logs": "执行日志和调试信息",
            "scripts": "运行时生成的脚本文件",
            "plans": "任务计划文件",
            "contexts": "上下文和配置文件", 
            "temp": "临时文件（自动清理）",
            "memory": "工作空间记忆存储",
            "knowledge": "知识总线存储",
            "agent": "Agent相关配置和状态"
        }
        
        result = []
        for dir_name, dir_path in self.directories.items():
            desc = descriptions.get(dir_name, "工作空间目录")
            result.append(f"- `{dir_path}/` - {desc}")
        
        return "\n".join(result)
    
    async def _create_workspace_index(self) -> None:
        """创建工作空间索引"""
        index_content = f"""# AgentBus 工作空间索引

## 统计信息
- 创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 自动清理: {'启用' if self.auto_cleanup else '禁用'}

## 文件统计
"""
        
        stats = await self.get_statistics()
        index_content += f"""
- 总文件数: {stats.total_files}
- 总大小: {stats.total_size_mb:.2f} MB

## 目录分布
"""
        
        for dir_name, count in stats.directories.items():
            index_content += f"- {dir_name}: {count} 文件\n"
        
        index_path = self.base_path / "workspace_index.md"
        await self._write_markdown_file(index_path, index_content, {"workspace_index"})
    
    async def _write_markdown_file(self, file_path: Path, content: str, tags: Set[str] = None) -> None:
        """写入Markdown文件（与记忆系统集成）"""
        if tags is None:
            tags = set()
        
        # 添加工作空间标签
        tags.add("workspace")
        tags.add("system_generated")
        
        # 写入文件
        await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: file_path.write_text(content, encoding='utf-8')
        )
        
        # 如果启用记忆集成，将文件信息存储到记忆系统
        if self.memory_integration:
            await self._store_file_memory(file_path, content, tags)
    
    async def _store_file_memory(self, file_path: Path, content: str, tags: Set[str]) -> None:
        """将文件信息存储到记忆系统"""
        try:
            # 这里应该调用记忆系统的API
            # 为了简化，暂时只记录到日志
            logger.info("Storing file memory", 
                      file=str(file_path), 
                      size=len(content),
                      tags=list(tags))
        except Exception as e:
            logger.error("Failed to store file memory", error=str(e))
    
    async def write_script(self, filename: str, content: str, metadata: Dict[str, Any] = None) -> Path:
        """写入脚本文件"""
        script_path = self.base_path / self.directories["scripts"] / filename
        
        # 确保文件扩展名
        if not filename.endswith(('.sh', '.py', '.js', '.ts')):
            filename += '.py'
            script_path = self.base_path / self.directories["scripts"] / filename
        
        # 写入文件
        await self._write_markdown_file(
            script_path, 
            content, 
            {"script", "generated", "workspace"}
        )
        
        logger.info("Script written", script=str(script_path))
        return script_path
    
    async def write_plan(self, filename: str, content: str, metadata: Dict[str, Any] = None) -> Path:
        """写入计划文件"""
        plan_path = self.base_path / self.directories["plans"] / filename
        
        # 确保文件扩展名
        if not filename.endswith('.md'):
            filename += '.md'
            plan_path = self.base_path / self.directories["plans"] / filename
        
        # 写入文件
        await self._write_markdown_file(
            plan_path,
            content,
            {"plan", "task", "workspace"}
        )
        
        logger.info("Plan written", script=str(plan_path))
        return plan_path
    
    async def write_context(self, filename: str, content: str, metadata: Dict[str, Any] = None) -> Path:
        """写入上下文文件"""
        context_path = self.base_path / self.directories["contexts"] / filename
        
        # 根据内容类型确定扩展名
        if filename.endswith('.json'):
            context_path = self.base_path / self.directories["contexts"] / filename
        else:
            filename += '.md'
            context_path = self.base_path / self.directories["contexts"] / filename
        
        # 写入文件
        await self._write_markdown_file(
            context_path,
            content,
            {"context", "configuration", "workspace"}
        )
        
        logger.info("Context written", script=str(context_path))
        return context_path
    
    async def write_log(self, filename: str, content: str, log_level: str = "INFO") -> Path:
        """写入日志文件"""
        log_path = self.base_path / self.directories["logs"] / filename
        
        # 确保文件扩展名
        if not filename.endswith('.log'):
            filename += '.log'
            log_path = self.base_path / self.directories["logs"] / filename
        
        # 添加日志级别标识
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{log_level}] {content}\n"
        
        # 追加写入文件
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: log_path.write_text(log_entry, encoding='utf-8')
        )
        
        logger.info("Log written", script=str(log_path), level=log_level)
        return log_path
    
    async def list_files(self, directory: str = None, file_type: str = None) -> List[WorkspaceFile]:
        """列出工作空间文件"""
        if directory:
            search_path = self.base_path / self.directories.get(directory, directory)
        else:
            search_path = self.base_path
        
        files = []
        
        # 递归搜索文件
        for file_path in search_path.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                file_info = await self._get_file_info(file_path)
                
                # 按类型过滤
                if file_type and file_info.file_type != file_type:
                    continue
                
                files.append(file_info)
        
        return sorted(files, key=lambda x: x.updated_at, reverse=True)
    
    async def _get_file_info(self, file_path: Path) -> WorkspaceFile:
        """获取文件信息"""
        stat = file_path.stat()
        file_extension = file_path.suffix.lower()
        file_type = self.file_type_mapping.get(file_extension, "unknown")
        
        return WorkspaceFile(
            name=file_path.name,
            path=file_path,
            file_type=file_type,
            size=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime),
            updated_at=datetime.fromtimestamp(stat.st_mtime),
            metadata={
                "extension": file_extension,
                "directory": file_path.parent.name
            }
        )
    
    async def get_statistics(self) -> WorkspaceStats:
        """获取工作空间统计信息"""
        stats = WorkspaceStats(
            workspace_path=str(self.base_path),
            total_files=0,
            total_size_mb=0.0,
            directories={},
            file_types={}
        )
        
        # 遍历所有目录统计
        for dir_name in self.directories.values():
            dir_path = self.base_path / dir_name
            if not dir_path.exists():
                continue
            
            file_count = 0
            dir_size = 0
            
            for file_path in dir_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    file_count += 1
                    dir_size += file_path.stat().st_size
                    
                    # 统计文件类型
                    file_extension = file_path.suffix.lower()
                    file_type = self.file_type_mapping.get(file_extension, "unknown")
                    stats.file_types[file_type] = stats.file_types.get(file_type, 0) + 1
            
            stats.directories[dir_name] = file_count
            stats.total_files += file_count
            stats.total_size_mb += dir_size / (1024 * 1024)  # 转换为MB
        
        return stats
    
    async def cleanup_temp(self, max_age_hours: int = None) -> Dict[str, int]:
        """清理临时文件"""
        if max_age_hours is None:
            max_age_hours = self.max_temp_age_hours
        
        cleanup_stats = {"deleted": 0, "errors": 0}
        temp_dir = self.base_path / self.directories["temp"]
        
        if not temp_dir.exists():
            return cleanup_stats
        
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        for file_path in temp_dir.rglob("*"):
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    cleanup_stats["deleted"] += 1
                except Exception as e:
                    logger.error("Failed to delete temp file", 
                               file=str(file_path), 
                               error=str(e))
                    cleanup_stats["errors"] += 1
        
        logger.info("Temp cleanup completed", **cleanup_stats)
        return cleanup_stats
    
    async def get_path(self, directory: str = None) -> str:
        """获取工作空间路径"""
        if directory:
            return str(self.base_path / self.directories.get(directory, directory))
        return str(self.base_path)
    
    async def export_workspace(self, export_path: str) -> str:
        """导出工作空间"""
        export_path = Path(export_path)
        
        # 创建导出目录
        export_path.mkdir(parents=True, exist_ok=True)
        
        # 复制所有非临时文件
        copied_files = 0
        for dir_name in self.directories.values():
            if dir_name == "temp":
                continue  # 跳过临时目录
            
            src_dir = self.base_path / dir_name
            dst_dir = export_path / dir_name
            
            if src_dir.exists():
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
                copied_files += len(list(src_dir.rglob("*")))
        
        export_info = f"""# AgentBus 工作空间导出

导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
原工作空间: {self.base_path}
导出位置: {export_path}
复制文件数: {copied_files}

## 目录结构
{self._get_directory_description()}

---
*此导出由AgentBus工作空间系统自动生成*
"""
        
        export_readme = export_path / "EXPORT_INFO.md"
        await self._write_markdown_file(export_readme, export_info, {"export", "workspace"})
        
        logger.info("Workspace exported", 
                   export=str(export_path), 
                   files=copied_files)
        
        return str(export_path)


# 全局工作空间实例
_workspace_instance: Optional[AgentWorkSpace] = None


async def init_workspace(base_path: str = "./workspace") -> AgentWorkSpace:
    """初始化工作空间"""
    global _workspace_instance
    _workspace_instance = AgentWorkSpace(base_path)
    await _workspace_instance.initialize()
    return _workspace_instance


def get_workspace() -> Optional[AgentWorkSpace]:
    """获取工作空间实例"""
    return _workspace_instance
