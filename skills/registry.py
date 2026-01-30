"""
AgentBus技能注册和管理系统

提供技能的注册、发现、管理和生命周期控制功能。
"""

import asyncio
import logging
import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, Union
from dataclasses import asdict
import yaml
import json
from datetime import datetime

from .base import (
    BaseSkill, SkillFactory, SkillMetadata, SkillContext, 
    SkillStatus, SkillType, SkillInterface,
    SkillValidationError, SkillLoadError, SkillExecutionError
)


class SkillRegistry:
    """技能注册表，管理所有技能的注册信息"""
    
    def __init__(self):
        self._skills: Dict[str, SkillMetadata] = {}
        self._factories: Dict[str, Type[SkillFactory]] = {}
        self._skill_classes: Dict[str, Type[BaseSkill]] = {}
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
    
    async def register_skill(self, metadata: SkillMetadata, factory: Type[SkillFactory]) -> bool:
        """注册技能"""
        async with self._lock:
            try:
                # 验证元数据
                if not factory.validate_metadata(metadata):
                    raise SkillValidationError(f"Invalid metadata for skill: {metadata.name}")
                
                # 检查依赖
                await self._check_dependencies(metadata)
                
                # 检查冲突
                await self._check_conflicts(metadata)
                
                # 注册技能
                self._skills[metadata.name] = metadata
                self._factories[metadata.name] = factory
                
                self.logger.info(f"Registered skill: {metadata.name} (v{metadata.version})")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to register skill {metadata.name}: {e}")
                raise SkillValidationError(f"Failed to register skill {metadata.name}: {e}")
    
    async def _check_dependencies(self, metadata: SkillMetadata) -> None:
        """检查技能依赖"""
        for dep_name in metadata.dependencies:
            if dep_name not in self._skills:
                # 尝试自动加载依赖
                if not await self._auto_load_dependency(dep_name):
                    raise SkillValidationError(f"Missing dependency: {dep_name} for skill {metadata.name}")
    
    async def _check_conflicts(self, metadata: SkillMetadata) -> None:
        """检查技能冲突"""
        for conflict_name in metadata.conflicts:
            if conflict_name in self._skills:
                raise SkillValidationError(
                    f"Conflict detected: {metadata.name} conflicts with {conflict_name}"
                )
    
    async def _auto_load_dependency(self, skill_name: str) -> bool:
        """自动加载依赖技能"""
        # 这里可以实现自动发现和加载技能的逻辑
        # 目前只是占位符实现
        return False
    
    async def unregister_skill(self, skill_name: str) -> bool:
        """注销技能"""
        async with self._lock:
            if skill_name in self._skills:
                del self._skills[skill_name]
                self._factories.pop(skill_name, None)
                self._skill_classes.pop(skill_name, None)
                self.logger.info(f"Unregistered skill: {skill_name}")
                return True
            return False
    
    def get_skill_metadata(self, skill_name: str) -> Optional[SkillMetadata]:
        """获取技能元数据"""
        return self._skills.get(skill_name)
    
    def list_skills(self) -> List[str]:
        """列出所有技能名称"""
        return list(self._skills.keys())
    
    def get_registered_skills(self) -> Dict[str, SkillMetadata]:
        """获取所有已注册的技能"""
        return self._skills.copy()
    
    async def create_skill_instance(self, skill_name: str) -> Optional[BaseSkill]:
        """创建技能实例"""
        metadata = self._skills.get(skill_name)
        factory = self._factories.get(skill_name)
        
        if not metadata or not factory:
            return None
        
        try:
            skill_instance = factory.create_skill(metadata)
            return skill_instance
        except Exception as e:
            self.logger.error(f"Failed to create skill instance {skill_name}: {e}")
            return None


class SkillDiscovery:
    """技能发现器"""
    
    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        self.logger = logging.getLogger(__name__)
    
    async def discover_from_directory(self, directory: Path) -> List[SkillMetadata]:
        """从目录发现技能"""
        skills = []
        skill_files = self._find_skill_files(directory)
        
        for skill_file in skill_files:
            try:
                metadata = await self._load_skill_metadata(skill_file)
                if metadata:
                    skills.append(metadata)
                    self.logger.info(f"Discovered skill: {metadata.name} from {skill_file}")
            except Exception as e:
                self.logger.error(f"Failed to load skill metadata from {skill_file}: {e}")
        
        return skills
    
    def _find_skill_files(self, directory: Path) -> List[Path]:
        """查找技能文件"""
        skill_files = []
        patterns = ["skill.yaml", "skill.yml", "skill.json", "*.skill"]
        
        for pattern in patterns:
            skill_files.extend(directory.glob(pattern))
        
        return skill_files
    
    async def _load_skill_metadata(self, skill_file: Path) -> Optional[SkillMetadata]:
        """加载技能元数据文件"""
        try:
            with open(skill_file, 'r', encoding='utf-8') as f:
                if skill_file.suffix.lower() in ['.yml', '.yaml']:
                    data = yaml.safe_load(f)
                elif skill_file.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    return None
            
            if not data or 'name' not in data:
                return None
            
            # 创建技能元数据
            metadata = SkillMetadata(
                name=data['name'],
                description=data.get('description', ''),
                version=data.get('version', '1.0.0'),
                author=data.get('author', ''),
                homepage=data.get('homepage', ''),
                license=data.get('license', ''),
                tags=data.get('tags', []),
                category=SkillType(data.get('category', 'tool')),
                enabled=data.get('enabled', True),
                auto_activate=data.get('auto_activate', True),
                priority=data.get('priority', 0),
                requires=data.get('requires', {}),
                dependencies=data.get('dependencies', []),
                conflicts=data.get('conflicts', []),
                permissions=data.get('permissions', []),
                config_schema=data.get('config_schema', {}),
                install_info=data.get('install_info', {}),
            )
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error loading skill metadata from {skill_file}: {e}")
            return None
    
    async def discover_from_package(self, package_name: str) -> List[SkillMetadata]:
        """从Python包发现技能"""
        skills = []
        try:
            package = importlib.import_module(package_name)
            package_path = Path(package.__file__).parent
            
            # 查找技能类
            for item_name in dir(package):
                item = getattr(package, item_name)
                if (inspect.isclass(item) and 
                    issubclass(item, BaseSkill) and 
                    item != BaseSkill):
                    
                    try:
                        # 创建临时实例获取元数据
                        temp_instance = item.__new__(item)
                        temp_instance.__init__(SkillMetadata(
                            name="temp", description="temp"
                        ))
                        
                        if hasattr(temp_instance, 'metadata'):
                            skills.append(temp_instance.metadata)
                            self.logger.info(f"Discovered skill from package: {temp_instance.metadata.name}")
                    except Exception as e:
                        self.logger.error(f"Error discovering skill from {package_name}.{item_name}: {e}")
        
        except ImportError as e:
            self.logger.error(f"Failed to import package {package_name}: {e}")
        
        return skills
    
    async def scan_standard_locations(self) -> List[SkillMetadata]:
        """扫描标准位置发现技能"""
        all_skills = []
        standard_dirs = [
            Path.home() / ".agentbus" / "skills",
            Path("/usr/local/share/agentbus/skills"),
            Path("/usr/share/agentbus/skills"),
        ]
        
        for skill_dir in standard_dirs:
            if skill_dir.exists():
                skills = await self.discover_from_directory(skill_dir)
                all_skills.extend(skills)
        
        return all_skills


class SkillManager(SkillInterface):
    """技能管理器，提供技能的全生命周期管理"""
    
    def __init__(self, workspace_dir: Path, config_dir: Path):
        self.workspace_dir = Path(workspace_dir)
        self.config_dir = Path(config_dir)
        self.registry = SkillRegistry()
        self.discovery = SkillDiscovery(self.registry)
        self._loaded_skills: Dict[str, BaseSkill] = {}
        self._skill_status: Dict[str, SkillStatus] = {}
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
        
        # 确保目录存在
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    async def discover_skills(self, paths: List[Path]) -> List[SkillMetadata]:
        """发现技能"""
        all_skills = []
        for path in paths:
            if path.is_file():
                # 从单个文件发现
                skills = await self._discover_from_file(path)
                all_skills.extend(skills)
            elif path.is_dir():
                # 从目录发现
                skills = await self.discovery.discover_from_directory(path)
                all_skills.extend(skills)
        
        return all_skills
    
    async def _discover_from_file(self, file_path: Path) -> List[SkillMetadata]:
        """从单个文件发现技能"""
        return await self.discovery._load_skill_metadata(file_path) or []
    
    async def load_skill(self, metadata: SkillMetadata) -> BaseSkill:
        """加载技能"""
        async with self._lock:
            if metadata.name in self._loaded_skills:
                return self._loaded_skills[metadata.name]
            
            try:
                # 更新状态
                self._skill_status[metadata.name] = SkillStatus.LOADING
                
                # 创建技能实例
                skill_instance = await self.registry.create_skill_instance(metadata.name)
                if not skill_instance:
                    raise SkillLoadError(f"Failed to create instance for skill: {metadata.name}")
                
                # 创建执行上下文
                context = self._create_skill_context(metadata.name)
                skill_instance.context = context
                
                # 初始化技能
                await skill_instance.initialize(context)
                
                # 添加到已加载列表
                self._loaded_skills[metadata.name] = skill_instance
                self._skill_status[metadata.name] = SkillStatus.INACTIVE
                
                self.logger.info(f"Loaded skill: {metadata.name}")
                return skill_instance
                
            except Exception as e:
                self._skill_status[metadata.name] = SkillStatus.ERROR
                self.logger.error(f"Failed to load skill {metadata.name}: {e}")
                raise SkillLoadError(f"Failed to load skill {metadata.name}: {e}")
    
    async def unload_skill(self, skill_name: str) -> bool:
        """卸载技能"""
        async with self._lock:
            if skill_name not in self._loaded_skills:
                return False
            
            try:
                skill_instance = self._loaded_skills[skill_name]
                
                # 如果技能激活，先停用
                if skill_instance.is_active:
                    await self.deactivate_skill(skill_name)
                
                # 清理资源
                await skill_instance.cleanup()
                
                # 移除
                del self._loaded_skills[skill_name]
                self._skill_status[skill_name] = SkillStatus.UNLOADED
                
                self.logger.info(f"Unloaded skill: {skill_name}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to unload skill {skill_name}: {e}")
                return False
    
    async def activate_skill(self, skill_name: str) -> bool:
        """激活技能"""
        async with self._lock:
            if skill_name not in self._loaded_skills:
                return False
            
            skill_instance = self._loaded_skills[skill_name]
            
            try:
                # 检查依赖
                await self._check_skill_dependencies(skill_name)
                
                # 激活技能
                await skill_instance.activate()
                skill_instance.status = SkillStatus.ACTIVE
                self._skill_status[skill_name] = SkillStatus.ACTIVE
                
                self.logger.info(f"Activated skill: {skill_name}")
                return True
                
            except Exception as e:
                self._skill_status[skill_name] = SkillStatus.ERROR
                self.logger.error(f"Failed to activate skill {skill_name}: {e}")
                return False
    
    async def deactivate_skill(self, skill_name: str) -> bool:
        """停用技能"""
        async with self._lock:
            if skill_name not in self._loaded_skills:
                return False
            
            skill_instance = self._loaded_skills[skill_name]
            
            try:
                # 停用技能
                await skill_instance.deactivate()
                skill_instance.status = SkillStatus.INACTIVE
                self._skill_status[skill_name] = SkillStatus.INACTIVE
                
                self.logger.info(f"Deactivated skill: {skill_name}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to deactivate skill {skill_name}: {e}")
                return False
    
    async def execute_skill(self, skill_name: str, action: str, params: Dict[str, Any]) -> Any:
        """执行技能"""
        if skill_name not in self._loaded_skills:
            raise SkillExecutionError(f"Skill not loaded: {skill_name}")
        
        skill_instance = self._loaded_skills[skill_name]
        
        if not skill_instance.is_active:
            raise SkillExecutionError(f"Skill not active: {skill_name}")
        
        try:
            # 增加使用计数
            skill_instance.increment_usage()
            
            # 执行技能
            result = await skill_instance.execute(action, params)
            
            self.logger.info(f"Executed skill {skill_name}.{action}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute skill {skill_name}.{action}: {e}")
            raise SkillExecutionError(f"Failed to execute skill {skill_name}.{action}: {e}")
    
    def get_skill_status(self, skill_name: str) -> Optional[SkillStatus]:
        """获取技能状态"""
        return self._skill_status.get(skill_name)
    
    def list_skills(self, status_filter: Optional[Set[SkillStatus]] = None) -> List[str]:
        """列出技能"""
        if not status_filter:
            return list(self._skill_status.keys())
        
        return [
            name for name, status in self._skill_status.items()
            if status in status_filter
        ]
    
    def _create_skill_context(self, skill_name: str) -> SkillContext:
        """创建技能执行上下文"""
        skill_dir = self.workspace_dir / "skills" / skill_name
        config_dir = self.config_dir / "skills" / skill_name
        
        return SkillContext(
            workspace_dir=self.workspace_dir,
            config_dir=config_dir,
            data_dir=skill_dir / "data",
            temp_dir=skill_dir / "temp",
            logger_name=f"skill.{skill_name}",
        )
    
    async def _check_skill_dependencies(self, skill_name: str) -> None:
        """检查技能依赖"""
        metadata = self.registry.get_skill_metadata(skill_name)
        if not metadata:
            return
        
        for dep_name in metadata.dependencies:
            if dep_name not in self._loaded_skills:
                raise SkillExecutionError(f"Missing dependency: {dep_name} for skill {skill_name}")
            
            dep_status = self._skill_status.get(dep_name)
            if dep_status != SkillStatus.ACTIVE:
                raise SkillExecutionError(f"Dependency {dep_name} is not active for skill {skill_name}")
    
    async def load_all_skills(self) -> Dict[str, bool]:
        """加载所有启用的技能"""
        results = {}
        skills = self.registry.get_registered_skills()
        
        for skill_name, metadata in skills.items():
            if metadata.enabled:
                try:
                    await self.load_skill(metadata)
                    results[skill_name] = True
                except Exception as e:
                    self.logger.error(f"Failed to auto-load skill {skill_name}: {e}")
                    results[skill_name] = False
            else:
                results[skill_name] = False
        
        return results
    
    async def activate_auto_skills(self) -> Dict[str, bool]:
        """激活所有自动激活的技能"""
        results = {}
        skills = self.registry.get_registered_skills()
        
        for skill_name, metadata in skills.items():
            if metadata.auto_activate and skill_name in self._loaded_skills:
                try:
                    await self.activate_skill(skill_name)
                    results[skill_name] = True
                except Exception as e:
                    self.logger.error(f"Failed to auto-activate skill {skill_name}: {e}")
                    results[skill_name] = False
            else:
                results[skill_name] = False
        
        return results
    
    def get_skill_info(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """获取技能详细信息"""
        if skill_name not in self._skill_status:
            return None
        
        metadata = self.registry.get_skill_metadata(skill_name)
        skill_instance = self._loaded_skills.get(skill_name)
        
        info = {
            "name": skill_name,
            "status": self._skill_status[skill_name].value,
            "metadata": metadata.to_dict() if metadata else None,
            "capabilities": skill_instance.get_capabilities() if skill_instance else [],
            "commands": skill_instance.get_commands() if skill_instance else [],
            "is_loaded": skill_instance is not None,
            "is_active": skill_instance.is_active if skill_instance else False,
        }
        
        return info
    
    def export_registry(self) -> Dict[str, Any]:
        """导出注册表"""
        return {
            "skills": {
                name: metadata.to_dict()
                for name, metadata in self.registry.get_registered_skills().items()
            },
            "loaded_skills": list(self._loaded_skills.keys()),
            "skill_status": {
                name: status.value for name, status in self._skill_status.items()
            },
        }