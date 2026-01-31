"""
AgentBus技能系统测试示例

演示如何使用AgentBus技能系统框架的基本功能。
"""

import asyncio
import logging
import tempfile
from pathlib import Path

from skills import (
    SkillManager, BaseSkill, SkillMetadata, SkillFactory,
    SkillType, SkillContext, SkillStatus,
    SkillLifecycleManager, LifecycleConfig,
    create_skill_metadata, ExampleSkill, ExampleSkillFactory
)


class TestSkill(BaseSkill):
    """测试用技能"""
    
    def __init__(self, metadata: SkillMetadata):
        super().__init__(metadata)
        self.logger = logging.getLogger(f"test_skill.{metadata.name}")
        self.execution_count = 0
    
    async def initialize(self, context: SkillContext) -> None:
        """初始化技能"""
        self.logger.info(f"Initializing test skill: {self.metadata.name}")
        self.context = context
        
        # 创建测试目录
        test_dir = context.get_path("data")
        test_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Test skill initialized with context: {context.workspace_dir}")
    
    async def activate(self) -> None:
        """激活技能"""
        self.logger.info(f"Activating test skill: {self.metadata.name}")
        self.status = SkillStatus.ACTIVE
        self.logger.info(f"Test skill {self.metadata.name} is now active")
    
    async def deactivate(self) -> None:
        """停用技能"""
        self.logger.info(f"Deactivating test skill: {self.metadata.name}")
        self.status = SkillStatus.INACTIVE
        self.logger.info(f"Test skill {self.metadata.name} is now inactive")
    
    async def execute(self, action: str, params: dict) -> any:
        """执行技能操作"""
        self.execution_count += 1
        self.logger.info(f"Executing {action} with params: {params}")
        
        if action == "test":
            return {
                "skill_name": self.metadata.name,
                "execution_count": self.execution_count,
                "message": f"Test skill executed {self.execution_count} times",
                "params": params
            }
        elif action == "status":
            return {
                "name": self.metadata.name,
                "status": self.status.value,
                "execution_count": self.execution_count,
                "initialized": hasattr(self, 'context') and self.context is not None
            }
        elif action == "error":
            raise ValueError("This is a test error")
        else:
            raise ValueError(f"Unknown action: {action}")
    
    def get_capabilities(self) -> list:
        """获取技能能力列表"""
        return ["test", "status", "error"]
    
    def get_commands(self) -> list:
        """获取技能命令列表"""
        return [
            {
                "name": "test",
                "description": "执行测试操作",
                "usage": "test [params]"
            },
            {
                "name": "status",
                "description": "获取技能状态",
                "usage": "status"
            },
            {
                "name": "error",
                "description": "触发测试错误",
                "usage": "error"
            }
        ]


class TestSkillFactory(SkillFactory):
    """测试技能工厂"""
    
    @staticmethod
    def create_skill(metadata: SkillMetadata) -> BaseSkill:
        """创建技能实例"""
        return TestSkill(metadata)
    
    @staticmethod
    def validate_metadata(metadata: SkillMetadata) -> bool:
        """验证技能元数据"""
        return bool(metadata.name and metadata.description)


async def test_skill_system():
    """测试技能系统基本功能"""
    
    print("=== AgentBus技能系统测试 ===\n")
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir) / "workspace"
        config_dir = Path(temp_dir) / "config"
        
        print(f"工作目录: {workspace_dir}")
        print(f"配置目录: {config_dir}\n")
        
        # 1. 创建技能管理器
        print("1. 创建技能管理器...")
        manager = SkillManager(workspace_dir, config_dir)
        print("✓ 技能管理器创建成功\n")
        
        # 2. 创建测试技能元数据
        print("2. 创建测试技能元数据...")
        test_metadata = create_skill_metadata(
            name="test_skill",
            description="测试技能，用于演示技能系统功能",
            version="1.0.0",
            author="Test Author",
            category=SkillType.UTILITY,
            enabled=True,
            auto_activate=True,
            dependencies=[],
            config_schema={
                "test_param": {
                    "type": "string",
                    "required": False,
                    "default": "default_value"
                }
            }
        )
        print(f"✓ 创建技能元数据: {test_metadata.name} v{test_metadata.version}")
        print(f"  描述: {test_metadata.description}")
        print(f"  类别: {test_metadata.category.value}\n")
        
        # 3. 注册技能
        print("3. 注册技能...")
        await manager.registry.register_skill(test_metadata, TestSkillFactory)
        print("✓ 技能注册成功\n")
        
        # 4. 加载技能
        print("4. 加载技能...")
        skill_instance = await manager.load_skill(test_metadata)
        print(f"✓ 技能加载成功: {skill_instance.name}")
        print(f"  状态: {skill_instance.status.value}\n")
        
        # 5. 激活技能
        print("5. 激活技能...")
        success = await manager.activate_skill(skill_instance.name)
        print(f"✓ 技能激活结果: {'成功' if success else '失败'}\n")
        
        # 6. 执行技能操作
        print("6. 执行技能操作...")
        
        # 测试基本操作
        result1 = await manager.execute_skill("test_skill", "test", {"message": "Hello World!"})
        print(f"✓ 测试操作结果: {result1}")
        
        # 获取状态
        result2 = await manager.execute_skill("test_skill", "status", {})
        print(f"✓ 状态查询结果: {result2}")
        
        # 再次执行测试
        result3 = await manager.execute_skill("test_skill", "test", {"counter": 2})
        print(f"✓ 再次执行结果: {result3}\n")
        
        # 7. 测试生命周期管理
        print("7. 测试生命周期管理...")
        lifecycle_config = LifecycleConfig(
            health_check_interval=10,
            auto_restart_enabled=False,
            max_restart_attempts=1
        )
        
        lifecycle_manager = SkillLifecycleManager(manager, lifecycle_config)
        
        # 获取生命周期信息
        lifecycle_info = lifecycle_manager.get_lifecycle_info()
        print(f"✓ 生命周期信息: {lifecycle_info}\n")
        
        # 8. 获取技能信息
        print("8. 获取技能详细信息...")
        skill_info = manager.get_skill_info("test_skill")
        print(f"✓ 技能信息:")
        print(f"  名称: {skill_info['name']}")
        print(f"  状态: {skill_info['status']}")
        print(f"  已加载: {skill_info['is_loaded']}")
        print(f"  已激活: {skill_info['is_active']}")
        print(f"  能力: {skill_info['capabilities']}")
        print(f"  命令: {len(skill_info['commands'])} 个\n")
        
        # 9. 测试错误处理
        print("9. 测试错误处理...")
        try:
            await manager.execute_skill("test_skill", "error", {})
            print("✗ 错误处理测试失败：未抛出预期异常")
        except Exception as e:
            print(f"✓ 错误处理测试成功：捕获到异常 {type(e).__name__}: {e}\n")
        
        # 10. 停用技能
        print("10. 停用技能...")
        await manager.deactivate_skill("test_skill")
        status_after_deactivate = manager.get_skill_status("test_skill")
        print(f"✓ 技能停用后状态: {status_after_deactivate.value if status_after_deactivate else 'None'}\n")
        
        # 11. 卸载技能
        print("11. 卸载技能...")
        await manager.unload_skill("test_skill")
        status_after_unload = manager.get_skill_status("test_skill")
        print(f"✓ 技能卸载后状态: {status_after_unload.value if status_after_unload else 'None'}\n")
        
        # 12. 导出注册表信息
        print("12. 导出注册表信息...")
        registry_export = manager.export_registry()
        print(f"✓ 注册表导出:")
        print(f"  注册技能数量: {len(registry_export['skills'])}")
        print(f"  已加载技能: {len(registry_export['loaded_skills'])}")
        print(f"  技能状态: {registry_export['skill_status']}\n")
        
        print("=== 测试完成 ===")


async def test_skill_discovery():
    """测试技能发现功能"""
    
    print("=== 技能发现测试 ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir) / "workspace"
        config_dir = Path(temp_dir) / "config"
        
        manager = SkillManager(workspace_dir, config_dir)
        
        # 创建测试技能目录
        skills_dir = Path(temp_dir) / "skills"
        skills_dir.mkdir()
        
        # 创建示例技能文件
        example_skill_file = skills_dir / "example_skill.yaml"
        example_content = """
---
name: example_skill
description: 示例技能文件
version: 1.0.0
category: utility
enabled: true
---
        """.strip()
        
        with open(example_skill_file, 'w', encoding='utf-8') as f:
            f.write(example_content)
        
        print(f"创建示例技能文件: {example_skill_file}")
        
        # 发现技能
        discovered_skills = await manager.discover_skills([skills_dir])
        print(f"发现技能数量: {len(discovered_skills)}")
        
        for skill in discovered_skills:
            print(f"  - {skill.name} v{skill.version}: {skill.description}")
        
        print("\n✓ 技能发现测试完成\n")


async def test_example_skill():
    """测试示例技能"""
    
    print("=== 示例技能测试 ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir) / "workspace"
        config_dir = Path(temp_dir) / "config"
        
        # 创建示例技能
        metadata = create_skill_metadata(
            name="example_skill",
            description="示例技能",
            category=SkillType.UTILITY
        )
        
        factory = ExampleSkillFactory()
        skill = factory.create_skill(metadata)
        
        # 创建上下文
        context = SkillContext(
            workspace_dir=workspace_dir,
            config_dir=config_dir,
            data_dir=workspace_dir / "data",
            temp_dir=workspace_dir / "temp"
        )
        
        # 初始化技能
        await skill.initialize(context)
        print(f"✓ 示例技能初始化: {skill.name}")
        
        # 激活技能
        await skill.activate()
        print(f"✓ 示例技能激活: {skill.status.value}")
        
        # 执行操作
        result1 = await skill.execute("hello", {})
        print(f"✓ hello操作: {result1}")
        
        result2 = await skill.execute("status", {})
        print(f"✓ status操作: {result2}")
        
        # 获取能力和命令
        capabilities = skill.get_capabilities()
        commands = skill.get_commands()
        
        print(f"✓ 技能能力: {capabilities}")
        print(f"✓ 技能命令: {commands}")
        
        # 停用技能
        await skill.deactivate()
        print(f"✓ 示例技能停用: {skill.status.value}")
        
        print("\n=== 示例技能测试完成 ===\n")


if __name__ == "__main__":
    print("开始AgentBus技能系统测试...\n")
    
    # 运行测试
    asyncio.run(test_skill_system())
    asyncio.run(test_skill_discovery())
    asyncio.run(test_example_skill())
    
    print("所有测试完成！")