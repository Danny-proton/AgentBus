"""
AgentBus Java集成使用示例
演示如何为Java用户系统提供扩展接口
"""

import asyncio
import logging
from typing import Dict, Any

from agentbus.models.user import UserProfile, UserPreferences, SkillLevel
from agentbus.storage import StorageManager
from agentbus.integrations import JavaClient, UserPreferencesManager
from agentbus.integrations.java_client import JavaUserRequest, JavaMemoryRequest

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """主函数 - 演示Java集成接口的使用"""
    
    # 1. 配置存储管理器
    storage_config = {
        'type': 'memory',  # 或 'database'
        'db_path': 'agentbus.db',  # 如果使用数据库
        'max_memory_size': 10000
    }
    
    storage_manager = StorageManager(storage_config)
    await storage_manager.initialize()
    
    # 2. 创建Java客户端
    java_config = {
        'enabled': True,
        'cors_origins': ['*'],
        'max_connections': 1000,
        'timeout_seconds': 30,
        'storage_type': 'memory'
    }
    
    java_client = JavaClient(java_config)
    await java_client.start()
    
    # 3. 创建用户偏好管理器
    preferences_manager = UserPreferencesManager(storage_manager)
    await preferences_manager.initialize()
    
    # 4. 演示用户管理功能
    await demonstrate_user_management(storage_manager, preferences_manager)
    
    # 5. 演示记忆管理功能
    await demonstrate_memory_management(storage_manager)
    
    # 6. 演示技能管理功能
    await demonstrate_skills_management(storage_manager)
    
    # 7. 演示偏好管理功能
    await demonstrate_preferences_management(preferences_manager)
    
    # 8. 演示集成功能
    await demonstrate_integration_management(storage_manager)
    
    # 清理资源
    await java_client.stop()
    await storage_manager.close()


async def demonstrate_user_management(storage_manager: StorageManager, preferences_manager: UserPreferencesManager):
    """演示用户管理功能"""
    logger.info("=== 演示用户管理功能 ===")
    
    # 创建用户
    user = UserProfile(
        username="java_developer",
        email="java@example.com",
        full_name="Java开发者"
    )
    
    created_user = await storage_manager.user_storage.create_user(user)
    logger.info(f"创建用户成功: {created_user.user_id}")
    
    # 获取用户
    retrieved_user = await storage_manager.user_storage.get_user(created_user.user_id)
    logger.info(f"获取用户成功: {retrieved_user.username}")
    
    # 更新用户
    update_data = {
        'full_name': "Java高级开发者"
    }
    updated_user = await storage_manager.user_storage.update_user(created_user.user_id, update_data)
    logger.info(f"更新用户成功: {updated_user.full_name}")
    
    return created_user


async def demonstrate_memory_management(storage_manager: StorageManager):
    """演示记忆管理功能"""
    logger.info("=== 演示记忆管理功能 ===")
    
    user_id = "demo_user"
    
    # 创建记忆
    memory_data = {
        'content': "用户偏好使用IntelliJ IDEA开发Java应用",
        'memory_type': 'preference',
        'importance': 8,
        'tags': ['java', 'ide', 'preference']
    }
    
    from agentbus.models.user import UserMemory
    memory = UserMemory(
        session_id="session_001",
        user_id=user_id,
        **memory_data
    )
    
    memory_id = await storage_manager.memory_storage.store_memory(memory)
    logger.info(f"存储记忆成功: {memory_id}")
    
    # 获取用户记忆
    user_memories = await storage_manager.memory_storage.get_user_memories(user_id)
    logger.info(f"获取用户记忆: {len(user_memories)} 条")
    
    # 搜索记忆
    search_results = await storage_manager.memory_storage.search_memories(user_id, "IDE", 5)
    logger.info(f"搜索记忆结果: {len(search_results)} 条")
    
    return memory_id


async def demonstrate_skills_management(storage_manager: StorageManager):
    """演示技能管理功能"""
    logger.info("=== 演示技能管理功能 ===")
    
    user_id = "demo_user"
    
    # 添加技能
    from agentbus.models.user import UserSkills
    skill = UserSkills(
        user_id=user_id,
        skill_name="Java编程",
        skill_level=SkillLevel.ADVANCED,
        experience_points=1500
    )
    
    skill_id = await storage_manager.skills_storage.save_skill(skill)
    logger.info(f"添加技能成功: {skill_id}")
    
    # 获取用户技能
    user_skills = await storage_manager.skills_storage.get_user_skills(user_id)
    logger.info(f"用户技能: {len(user_skills)} 个")
    
    return skill_id


async def demonstrate_preferences_management(preferences_manager: UserPreferencesManager):
    """演示偏好管理功能"""
    logger.info("=== 演示偏好管理功能 ===")
    
    user_id = "demo_user"
    
    # 设置Java偏好
    java_prefs_success = await preferences_manager.set_java_preferences(
        user_id=user_id,
        java_version="17",
        ide_preference="IntelliJ IDEA",
        coding_style={
            'indent_size': 4,
            'brace_style': 'K&R',
            'import_organization': 'static'
        }
    )
    logger.info(f"设置Java偏好成功: {java_prefs_success}")
    
    # 设置界面偏好
    ui_prefs_success = await preferences_manager.set_ui_preferences(
        user_id=user_id,
        theme="dark",
        language="zh-CN"
    )
    logger.info(f"设置界面偏好成功: {ui_prefs_success}")
    
    # 智能推荐
    suggested_ide = await preferences_manager.suggest_java_ide(user_id)
    suggested_version = await preferences_manager.suggest_java_version(user_id)
    logger.info(f"推荐IDE: {suggested_ide}")
    logger.info(f"推荐Java版本: {suggested_version}")
    
    # 获取偏好
    preferences = await preferences_manager.get_user_preferences(user_id)
    logger.info(f"当前偏好: {preferences.dict() if preferences else None}")
    
    # 导出偏好
    exported_prefs = await preferences_manager.export_user_preferences(user_id)
    logger.info(f"导出偏好成功: {exported_prefs is not None}")


async def demonstrate_integration_management(storage_manager: StorageManager):
    """演示集成管理功能"""
    logger.info("=== 演示集成管理功能 ===")
    
    user_id = "demo_user"
    
    # 添加IDE集成
    from agentbus.models.user import UserIntegration
    integration = UserIntegration(
        user_id=user_id,
        integration_type="java_ide",
        integration_name="IntelliJ IDEA",
        config={
            'project_path': '/workspace/java-projects',
            'auto_save': True,
            'code_style': 'Google Java Style'
        }
    )
    
    integration_id = await storage_manager.integration_storage.save_integration(integration)
    logger.info(f"添加集成成功: {integration_id}")
    
    # 添加版本控制集成
    git_integration = UserIntegration(
        user_id=user_id,
        integration_type="version_control",
        integration_name="GitHub",
        config={
            'repository': 'java-learning-projects',
            'default_branch': 'main'
        },
        credentials={
            'token': 'ghp_xxx...'
        }
    )
    
    git_integration_id = await storage_manager.integration_storage.save_integration(git_integration)
    logger.info(f"添加Git集成成功: {git_integration_id}")
    
    # 获取用户集成
    user_integrations = await storage_manager.integration_storage.get_user_integrations(user_id)
    logger.info(f"用户集成: {len(user_integrations)} 个")
    
    # 更新集成配置
    update_config = {
        'project_path': '/workspace/advanced-java-projects',
        'auto_format': True
    }
    updated_integration = await storage_manager.integration_storage.update_integration(
        integration_id, update_config
    )
    logger.info(f"更新集成成功: {updated_integration.integration_name if updated_integration else None}")


async def demonstrate_java_api_usage():
    """演示Java API使用方式"""
    logger.info("=== 演示Java API使用方式 ===")
    
    # Java客户端请求示例
    java_user_request = JavaUserRequest(
        username="enterprise_java_dev",
        email="enterprise@example.com",
        full_name="企业Java开发者",
        preferences={
            'java_version': '21',
            'ide_preference': 'IntelliJ IDEA Ultimate',
            'theme': 'dark',
            'language': 'zh-CN'
        },
        metadata={
            'department': 'backend',
            'experience_years': 5,
            'specialization': 'microservices'
        }
    )
    
    # Java记忆请求示例
    java_memory_request = JavaMemoryRequest(
        content="用户已完成Spring Boot微服务架构学习",
        memory_type="learning_progress",
        importance=9,
        tags=["spring", "microservices", "learning"],
        metadata={
            "completion_date": "2024-01-15",
            "assessment_score": 95
        }
    )
    
    logger.info("Java API请求示例创建完成")
    
    # 注意：这里只是演示API数据结构
    # 实际的HTTP请求需要通过Java客户端发起
    return java_user_request, java_memory_request


if __name__ == "__main__":
    asyncio.run(main())