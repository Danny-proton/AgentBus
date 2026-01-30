"""
用户数据模型 - 为Java用户系统提供数据结构定义
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class UserStatus(Enum):
    """用户状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class SkillLevel(Enum):
    """技能水平枚举"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class UserPreferences(BaseModel):
    """用户偏好设置"""
    language: str = Field(default="zh-CN", description="用户首选语言")
    timezone: str = Field(default="Asia/Shanghai", description="用户时区")
    theme: str = Field(default="light", description="界面主题")
    notifications: bool = Field(default=True, description="是否开启通知")
    auto_save: bool = Field(default=True, description="是否自动保存")
    skill_level: SkillLevel = Field(default=SkillLevel.BEGINNER, description="用户技能水平")
    
    # Java集成特定偏好
    java_version: Optional[str] = Field(default=None, description="Java版本偏好")
    ide_preference: Optional[str] = Field(default=None, description="IDE偏好")
    coding_style: Dict[str, Any] = Field(default_factory=dict, description="编程风格设置")


class UserMemory(BaseModel):
    """用户记忆数据"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(description="用户ID")
    content: str = Field(description="记忆内容")
    memory_type: str = Field(description="记忆类型: conversation, preference, learning_progress")
    importance: int = Field(default=5, ge=1, le=10, description="重要性评分(1-10)")
    tags: List[str] = Field(default_factory=list, description="记忆标签")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class UserSkills(BaseModel):
    """用户技能配置"""
    user_id: str = Field(description="用户ID")
    skill_name: str = Field(description="技能名称")
    skill_level: SkillLevel = Field(description="技能水平")
    experience_points: int = Field(default=0, description="经验值")
    last_practiced: Optional[datetime] = Field(default=None, description="最后练习时间")
    is_enabled: bool = Field(default=True, description="是否启用")
    custom_config: Dict[str, Any] = Field(default_factory=dict, description="自定义配置")


class UserProfile(BaseModel):
    """用户档案"""
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str = Field(description="用户名")
    email: str = Field(description="邮箱")
    full_name: Optional[str] = Field(default=None, description="全名")
    avatar_url: Optional[str] = Field(default=None, description="头像URL")
    status: UserStatus = Field(default=UserStatus.PENDING, description="用户状态")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = Field(default=None, description="最后登录时间")
    preferences: UserPreferences = Field(default_factory=UserPreferences, description="用户偏好")
    skills: List[UserSkills] = Field(default_factory=list, description="用户技能")
    memory_count: int = Field(default=0, description="记忆数量")
    
    class Config:
        use_enum_values = True


class UserContext(BaseModel):
    """用户上下文信息"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(description="用户ID")
    current_context: Dict[str, Any] = Field(default_factory=dict, description="当前上下文")
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list, description="对话历史")
    learning_progress: Dict[str, Any] = Field(default_factory=dict, description="学习进度")
    workspace_state: Dict[str, Any] = Field(default_factory=dict, description="工作空间状态")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class UserIntegration(BaseModel):
    """用户集成配置"""
    integration_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(description="用户ID")
    integration_type: str = Field(description="集成类型: java_ide, version_control, ci_cd")
    integration_name: str = Field(description="集成名称")
    config: Dict[str, Any] = Field(default_factory=dict, description="集成配置")
    credentials: Optional[Dict[str, str]] = Field(default=None, description="凭证信息")
    is_active: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class UserStats(BaseModel):
    """用户统计信息"""
    user_id: str = Field(description="用户ID")
    total_sessions: int = Field(default=0, description="总会话数")
    total_messages: int = Field(default=0, description="总消息数")
    total_skills_practiced: int = Field(default=0, description="练习技能总数")
    learning_hours: float = Field(default=0.0, description="学习小时数")
    achievements: List[str] = Field(default_factory=list, description="成就列表")
    streak_days: int = Field(default=0, description="连续天数")
    last_activity: Optional[datetime] = Field(default=None, description="最后活动时间")


# 用于序列化和反序列化的模型
class UserCreateRequest(BaseModel):
    """创建用户请求"""
    username: str = Field(description="用户名")
    email: str = Field(description="邮箱")
    full_name: Optional[str] = Field(default=None, description="全名")
    preferences: Optional[UserPreferences] = Field(default=None, description="用户偏好")


class UserUpdateRequest(BaseModel):
    """更新用户请求"""
    username: Optional[str] = Field(default=None, description="用户名")
    full_name: Optional[str] = Field(default=None, description="全名")
    avatar_url: Optional[str] = Field(default=None, description="头像URL")
    preferences: Optional[UserPreferences] = Field(default=None, description="用户偏好")


class UserResponse(BaseModel):
    """用户响应模型"""
    success: bool = Field(description="操作是否成功")
    message: Optional[str] = Field(default=None, description="响应消息")
    data: Optional[Union[UserProfile, List[UserProfile]]] = Field(default=None, description="用户数据")


class UserMemoryResponse(BaseModel):
    """用户记忆响应模型"""
    success: bool = Field(description="操作是否成功")
    message: Optional[str] = Field(default=None, description="响应消息")
    data: Optional[Union[UserMemory, List[UserMemory]]] = Field(default=None, description="记忆数据")


class UserPreferencesResponse(BaseModel):
    """用户偏好响应模型"""
    success: bool = Field(description="操作是否成功")
    message: Optional[str] = Field(default=None, description="响应消息")
    data: Optional[UserPreferences] = Field(default=None, description="偏好数据")


class UserIntegrationResponse(BaseModel):
    """用户集成响应模型"""
    success: bool = Field(description="操作是否成功")
    message: Optional[str] = Field(default=None, description="响应消息")
    data: Optional[Union[UserIntegration, List[UserIntegration]]] = Field(default=None, description="集成数据")