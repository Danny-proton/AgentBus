"""
Java客户端接口 - 为Java用户提供RESTful API接口
支持Java系统与AgentBus的无缝集成
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uuid

from ..models.user import (
    UserProfile, UserPreferences, UserMemory, UserSkills,
    UserContext, UserIntegration, UserStats,
    UserCreateRequest, UserUpdateRequest,
    UserResponse, UserMemoryResponse, UserPreferencesResponse, UserIntegrationResponse
)
from ..storage import StorageManager
from .user_preferences import UserPreferencesManager

logger = logging.getLogger(__name__)


class JavaClientConfig(BaseModel):
    """Java客户端配置"""
    enabled: bool = Field(default=True, description="是否启用Java客户端")
    cors_origins: List[str] = Field(default=["*"], description="CORS允许的来源")
    max_connections: int = Field(default=1000, description="最大连接数")
    timeout_seconds: int = Field(default=30, description="超时时间")
    storage_type: str = Field(default="memory", description="存储类型")
    health_check_interval: int = Field(default=60, description="健康检查间隔(秒)")


class JavaUserRequest(BaseModel):
    """Java用户请求模型"""
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    full_name: Optional[str] = Field(default=None, description="全名")
    preferences: Optional[Dict[str, Any]] = Field(default=None, description="用户偏好")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="额外元数据")


class JavaUserUpdateRequest(BaseModel):
    """Java用户更新请求"""
    username: Optional[str] = Field(default=None, description="用户名")
    full_name: Optional[str] = Field(default=None, description="全名")
    preferences: Optional[Dict[str, Any]] = Field(default=None, description="用户偏好")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="额外元数据")


class JavaMemoryRequest(BaseModel):
    """Java记忆请求"""
    content: str = Field(..., description="记忆内容")
    memory_type: str = Field(default="conversation", description="记忆类型")
    importance: int = Field(default=5, ge=1, le=10, description="重要性")
    tags: List[str] = Field(default_factory=list, description="标签")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")


class JavaSkillRequest(BaseModel):
    """Java技能请求"""
    skill_name: str = Field(..., description="技能名称")
    skill_level: str = Field(default="beginner", description="技能水平")
    experience_points: int = Field(default=0, description="经验值")
    custom_config: Optional[Dict[str, Any]] = Field(default=None, description="自定义配置")


class JavaContextRequest(BaseModel):
    """Java上下文请求"""
    current_context: Optional[Dict[str, Any]] = Field(default=None, description="当前上下文")
    conversation_history: Optional[List[Dict[str, Any]]] = Field(default=None, description="对话历史")
    learning_progress: Optional[Dict[str, Any]] = Field(default=None, description="学习进度")
    workspace_state: Optional[Dict[str, Any]] = Field(default=None, description="工作空间状态")


class JavaIntegrationRequest(BaseModel):
    """Java集成请求"""
    integration_type: str = Field(..., description="集成类型")
    integration_name: str = Field(..., description="集成名称")
    config: Dict[str, Any] = Field(default_factory=dict, description="配置")
    credentials: Optional[Dict[str, str]] = Field(default=None, description="凭证")


class JavaClientAPI:
    """Java客户端API接口"""
    
    def __init__(self, config: JavaClientConfig, storage_manager: StorageManager):
        self.config = config
        self.storage_manager = storage_manager
        self.app = None
        self.preferences_manager = UserPreferencesManager(storage_manager)
        
    async def initialize(self):
        """初始化API"""
        if not self.config.enabled:
            logger.info("Java client API is disabled")
            return
        
        self.app = FastAPI(
            title="AgentBus Java Client API",
            description="为Java系统提供的RESTful API接口",
            version="1.0.0"
        )
        
        # 添加CORS中间件
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 注册路由
        self._register_routes()
        
        logger.info("Java client API initialized successfully")
    
    def _register_routes(self):
        """注册API路由"""
        
        # 用户管理
        @self.app.post("/java/api/users", response_model=UserResponse)
        async def create_user(request: JavaUserRequest):
            return await self._create_user(request)
        
        @self.app.get("/java/api/users/{user_id}", response_model=UserResponse)
        async def get_user(user_id: str):
            return await self._get_user(user_id)
        
        @self.app.put("/java/api/users/{user_id}", response_model=UserResponse)
        async def update_user(user_id: str, request: JavaUserUpdateRequest):
            return await self._update_user(user_id, request)
        
        @self.app.delete("/java/api/users/{user_id}")
        async def delete_user(user_id: str):
            return await self._delete_user(user_id)
        
        @self.app.get("/java/api/users", response_model=UserResponse)
        async def list_users(limit: int = 100, offset: int = 0):
            return await self._list_users(limit, offset)
        
        # 用户偏好
        @self.app.get("/java/api/users/{user_id}/preferences", response_model=UserPreferencesResponse)
        async def get_user_preferences(user_id: str):
            return await self._get_user_preferences(user_id)
        
        @self.app.put("/java/api/users/{user_id}/preferences", response_model=UserPreferencesResponse)
        async def update_user_preferences(user_id: str, preferences: Dict[str, Any]):
            return await self._update_user_preferences(user_id, preferences)
        
        # 用户记忆
        @self.app.post("/java/api/users/{user_id}/memories", response_model=UserMemoryResponse)
        async def store_user_memory(user_id: str, request: JavaMemoryRequest):
            return await self._store_user_memory(user_id, request)
        
        @self.app.get("/java/api/users/{user_id}/memories", response_model=UserMemoryResponse)
        async def get_user_memories(user_id: str, memory_type: Optional[str] = None):
            return await self._get_user_memories(user_id, memory_type)
        
        @self.app.get("/java/api/users/{user_id}/memories/search", response_model=UserMemoryResponse)
        async def search_user_memories(user_id: str, q: str, limit: int = 10):
            return await self._search_user_memories(user_id, q, limit)
        
        @self.app.delete("/java/api/memories/{memory_id}")
        async def delete_user_memory(memory_id: str):
            return await self._delete_user_memory(memory_id)
        
        # 用户技能
        @self.app.post("/java/api/users/{user_id}/skills")
        async def add_user_skill(user_id: str, request: JavaSkillRequest):
            return await self._add_user_skill(user_id, request)
        
        @self.app.get("/java/api/users/{user_id}/skills")
        async def get_user_skills(user_id: str):
            return await self._get_user_skills(user_id)
        
        @self.app.put("/java/api/users/{user_id}/skills/{skill_id}")
        async def update_user_skill(user_id: str, skill_id: str, skill_data: Dict[str, Any]):
            return await self._update_user_skill(user_id, skill_id, skill_data)
        
        @self.app.delete("/java/api/users/{user_id}/skills/{skill_id}")
        async def delete_user_skill(user_id: str, skill_id: str):
            return await self._delete_user_skill(user_id, skill_id)
        
        # 用户上下文
        @self.app.post("/java/api/users/{user_id}/contexts", response_model=Dict[str, Any])
        async def save_user_context(user_id: str, request: JavaContextRequest):
            return await self._save_user_context(user_id, request)
        
        @self.app.get("/java/api/contexts/{session_id}", response_model=Dict[str, Any])
        async def get_user_context(session_id: str):
            return await self._get_user_context(session_id)
        
        @self.app.get("/java/api/users/{user_id}/contexts", response_model=Dict[str, Any])
        async def get_user_contexts(user_id: str):
            return await self._get_user_contexts(user_id)
        
        # 用户集成
        @self.app.post("/java/api/users/{user_id}/integrations", response_model=UserIntegrationResponse)
        async def add_user_integration(user_id: str, request: JavaIntegrationRequest):
            return await self._add_user_integration(user_id, request)
        
        @self.app.get("/java/api/users/{user_id}/integrations", response_model=UserIntegrationResponse)
        async def get_user_integrations(user_id: str):
            return await self._get_user_integrations(user_id)
        
        @self.app.put("/java/api/integrations/{integration_id}", response_model=UserIntegrationResponse)
        async def update_integration(integration_id: str, config: Dict[str, Any]):
            return await self._update_integration(integration_id, config)
        
        @self.app.delete("/java/api/integrations/{integration_id}")
        async def delete_integration(integration_id: str):
            return await self._delete_integration(integration_id)
        
        # 用户统计
        @self.app.get("/java/api/users/{user_id}/stats", response_model=Dict[str, Any])
        async def get_user_stats(user_id: str):
            return await self._get_user_stats(user_id)
        
        @self.app.put("/java/api/users/{user_id}/stats", response_model=Dict[str, Any])
        async def update_user_stats(user_id: str, stats_data: Dict[str, Any]):
            return await self._update_user_stats(user_id, stats_data)
        
        # 系统健康检查
        @self.app.get("/java/api/health")
        async def health_check():
            return await self._health_check()
        
        # 系统统计
        @self.app.get("/java/api/stats")
        async def system_stats():
            return await self._system_stats()
    
    # 用户管理实现
    async def _create_user(self, request: JavaUserRequest) -> UserResponse:
        """创建用户"""
        try:
            # 创建用户档案
            user = UserProfile(
                username=request.username,
                email=request.email,
                full_name=request.full_name,
                preferences=UserPreferences(**(request.preferences or {}))
            )
            
            # 保存用户
            created_user = await self.storage_manager.user_storage.create_user(user)
            
            return UserResponse(
                success=True,
                message="用户创建成功",
                data=created_user
            )
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return UserResponse(
                success=False,
                message=f"创建用户失败: {str(e)}"
            )
    
    async def _get_user(self, user_id: str) -> UserResponse:
        """获取用户"""
        try:
            user = await self.storage_manager.user_storage.get_user(user_id)
            
            if user:
                return UserResponse(
                    success=True,
                    data=user
                )
            else:
                return UserResponse(
                    success=False,
                    message="用户不存在"
                )
                
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return UserResponse(
                success=False,
                message=f"获取用户失败: {str(e)}"
            )
    
    async def _update_user(self, user_id: str, request: JavaUserUpdateRequest) -> UserResponse:
        """更新用户"""
        try:
            update_data = {}
            
            if request.username:
                update_data['username'] = request.username
            if request.full_name:
                update_data['full_name'] = request.full_name
            if request.preferences:
                update_data['preferences'] = UserPreferences(**request.preferences)
            
            updated_user = await self.storage_manager.user_storage.update_user(user_id, update_data)
            
            if updated_user:
                return UserResponse(
                    success=True,
                    message="用户更新成功",
                    data=updated_user
                )
            else:
                return UserResponse(
                    success=False,
                    message="用户不存在"
                )
                
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            return UserResponse(
                success=False,
                message=f"更新用户失败: {str(e)}"
            )
    
    async def _delete_user(self, user_id: str) -> Dict[str, Any]:
        """删除用户"""
        try:
            success = await self.storage_manager.user_storage.delete_user(user_id)
            
            if success:
                return {"success": True, "message": "用户删除成功"}
            else:
                return {"success": False, "message": "用户不存在"}
                
        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            return {"success": False, "message": f"删除用户失败: {str(e)}"}
    
    async def _list_users(self, limit: int, offset: int) -> UserResponse:
        """列出用户"""
        try:
            users = await self.storage_manager.user_storage.list_users(limit, offset)
            
            return UserResponse(
                success=True,
                data=users
            )
            
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return UserResponse(
                success=False,
                message=f"列出用户失败: {str(e)}"
            )
    
    # 用户偏好实现
    async def _get_user_preferences(self, user_id: str) -> UserPreferencesResponse:
        """获取用户偏好"""
        try:
            preferences = await self.storage_manager.preferences_storage.get_preferences(user_id)
            
            if preferences:
                return UserPreferencesResponse(
                    success=True,
                    data=preferences
                )
            else:
                return UserPreferencesResponse(
                    success=False,
                    message="用户偏好不存在"
                )
                
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return UserPreferencesResponse(
                success=False,
                message=f"获取用户偏好失败: {str(e)}"
            )
    
    async def _update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> UserPreferencesResponse:
        """更新用户偏好"""
        try:
            updated_preferences = await self.storage_manager.preferences_storage.update_preferences(user_id, preferences)
            
            if updated_preferences:
                return UserPreferencesResponse(
                    success=True,
                    message="用户偏好更新成功",
                    data=updated_preferences
                )
            else:
                return UserPreferencesResponse(
                    success=False,
                    message="用户偏好不存在"
                )
                
        except Exception as e:
            logger.error(f"Failed to update user preferences: {e}")
            return UserPreferencesResponse(
                success=False,
                message=f"更新用户偏好失败: {str(e)}"
            )
    
    # 用户记忆实现
    async def _store_user_memory(self, user_id: str, request: JavaMemoryRequest) -> UserMemoryResponse:
        """存储用户记忆"""
        try:
            memory = UserMemory(
                session_id=str(uuid.uuid4()),
                user_id=user_id,
                content=request.content,
                memory_type=request.memory_type,
                importance=request.importance,
                tags=request.tags,
                metadata=request.metadata or {}
            )
            
            memory_id = await self.storage_manager.memory_storage.store_memory(memory)
            
            return UserMemoryResponse(
                success=True,
                message="记忆存储成功",
                data=memory
            )
            
        except Exception as e:
            logger.error(f"Failed to store user memory: {e}")
            return UserMemoryResponse(
                success=False,
                message=f"存储记忆失败: {str(e)}"
            )
    
    async def _get_user_memories(self, user_id: str, memory_type: Optional[str]) -> UserMemoryResponse:
        """获取用户记忆"""
        try:
            memories = await self.storage_manager.memory_storage.get_user_memories(user_id, memory_type)
            
            return UserMemoryResponse(
                success=True,
                data=memories
            )
            
        except Exception as e:
            logger.error(f"Failed to get user memories: {e}")
            return UserMemoryResponse(
                success=False,
                message=f"获取用户记忆失败: {str(e)}"
            )
    
    async def _search_user_memories(self, user_id: str, query: str, limit: int) -> UserMemoryResponse:
        """搜索用户记忆"""
        try:
            memories = await self.storage_manager.memory_storage.search_memories(user_id, query, limit)
            
            return UserMemoryResponse(
                success=True,
                data=memories
            )
            
        except Exception as e:
            logger.error(f"Failed to search user memories: {e}")
            return UserMemoryResponse(
                success=False,
                message=f"搜索用户记忆失败: {str(e)}"
            )
    
    async def _delete_user_memory(self, memory_id: str) -> Dict[str, Any]:
        """删除用户记忆"""
        try:
            success = await self.storage_manager.memory_storage.delete_memory(memory_id)
            
            if success:
                return {"success": True, "message": "记忆删除成功"}
            else:
                return {"success": False, "message": "记忆不存在"}
                
        except Exception as e:
            logger.error(f"Failed to delete user memory: {e}")
            return {"success": False, "message": f"删除记忆失败: {str(e)}"}
    
    # 用户技能实现
    async def _add_user_skill(self, user_id: str, request: JavaSkillRequest) -> Dict[str, Any]:
        """添加用户技能"""
        try:
            skill = UserSkills(
                user_id=user_id,
                skill_name=request.skill_name,
                skill_level=request.skill_level,
                experience_points=request.experience_points,
                custom_config=request.custom_config or {}
            )
            
            skill_id = await self.storage_manager.skills_storage.save_skill(skill)
            
            return {
                "success": True,
                "message": "技能添加成功",
                "skill_id": skill_id
            }
            
        except Exception as e:
            logger.error(f"Failed to add user skill: {e}")
            return {"success": False, "message": f"添加技能失败: {str(e)}"}
    
    async def _get_user_skills(self, user_id: str) -> Dict[str, Any]:
        """获取用户技能"""
        try:
            skills = await self.storage_manager.skills_storage.get_user_skills(user_id)
            
            return {
                "success": True,
                "data": skills
            }
            
        except Exception as e:
            logger.error(f"Failed to get user skills: {e}")
            return {"success": False, "message": f"获取用户技能失败: {str(e)}"}
    
    async def _update_user_skill(self, user_id: str, skill_id: str, skill_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新用户技能"""
        try:
            updated_skill = await self.storage_manager.skills_storage.update_skill(skill_id, skill_data)
            
            if updated_skill:
                return {
                    "success": True,
                    "message": "技能更新成功",
                    "data": updated_skill
                }
            else:
                return {"success": False, "message": "技能不存在"}
                
        except Exception as e:
            logger.error(f"Failed to update user skill: {e}")
            return {"success": False, "message": f"更新技能失败: {str(e)}"}
    
    async def _delete_user_skill(self, user_id: str, skill_id: str) -> Dict[str, Any]:
        """删除用户技能"""
        try:
            success = await self.storage_manager.skills_storage.delete_skill(skill_id)
            
            if success:
                return {"success": True, "message": "技能删除成功"}
            else:
                return {"success": False, "message": "技能不存在"}
                
        except Exception as e:
            logger.error(f"Failed to delete user skill: {e}")
            return {"success": False, "message": f"删除技能失败: {str(e)}"}
    
    # 用户上下文实现
    async def _save_user_context(self, user_id: str, request: JavaContextRequest) -> Dict[str, Any]:
        """保存用户上下文"""
        try:
            context = UserContext(
                user_id=user_id,
                current_context=request.current_context or {},
                conversation_history=request.conversation_history or [],
                learning_progress=request.learning_progress or {},
                workspace_state=request.workspace_state or {}
            )
            
            session_id = await self.storage_manager.context_storage.save_context(context)
            
            return {
                "success": True,
                "message": "上下文保存成功",
                "session_id": session_id,
                "data": context
            }
            
        except Exception as e:
            logger.error(f"Failed to save user context: {e}")
            return {"success": False, "message": f"保存上下文失败: {str(e)}"}
    
    async def _get_user_context(self, session_id: str) -> Dict[str, Any]:
        """获取用户上下文"""
        try:
            context = await self.storage_manager.context_storage.get_context(session_id)
            
            if context:
                return {
                    "success": True,
                    "data": context
                }
            else:
                return {"success": False, "message": "上下文不存在"}
                
        except Exception as e:
            logger.error(f"Failed to get user context: {e}")
            return {"success": False, "message": f"获取上下文失败: {str(e)}"}
    
    async def _get_user_contexts(self, user_id: str) -> Dict[str, Any]:
        """获取用户上下文"""
        try:
            contexts = await self.storage_manager.context_storage.get_user_contexts(user_id)
            
            return {
                "success": True,
                "data": contexts
            }
            
        except Exception as e:
            logger.error(f"Failed to get user contexts: {e}")
            return {"success": False, "message": f"获取用户上下文失败: {str(e)}"}
    
    # 用户集成实现
    async def _add_user_integration(self, user_id: str, request: JavaIntegrationRequest) -> UserIntegrationResponse:
        """添加用户集成"""
        try:
            integration = UserIntegration(
                user_id=user_id,
                integration_type=request.integration_type,
                integration_name=request.integration_name,
                config=request.config,
                credentials=request.credentials
            )
            
            integration_id = await self.storage_manager.integration_storage.save_integration(integration)
            
            return UserIntegrationResponse(
                success=True,
                message="集成添加成功",
                data=integration
            )
            
        except Exception as e:
            logger.error(f"Failed to add user integration: {e}")
            return UserIntegrationResponse(
                success=False,
                message=f"添加集成失败: {str(e)}"
            )
    
    async def _get_user_integrations(self, user_id: str) -> UserIntegrationResponse:
        """获取用户集成"""
        try:
            integrations = await self.storage_manager.integration_storage.get_user_integrations(user_id)
            
            return UserIntegrationResponse(
                success=True,
                data=integrations
            )
            
        except Exception as e:
            logger.error(f"Failed to get user integrations: {e}")
            return UserIntegrationResponse(
                success=False,
                message=f"获取用户集成失败: {str(e)}"
            )
    
    async def _update_integration(self, integration_id: str, config: Dict[str, Any]) -> UserIntegrationResponse:
        """更新集成"""
        try:
            updated_integration = await self.storage_manager.integration_storage.update_integration(integration_id, config)
            
            if updated_integration:
                return UserIntegrationResponse(
                    success=True,
                    message="集成更新成功",
                    data=updated_integration
                )
            else:
                return UserIntegrationResponse(
                    success=False,
                    message="集成不存在"
                )
                
        except Exception as e:
            logger.error(f"Failed to update integration: {e}")
            return UserIntegrationResponse(
                success=False,
                message=f"更新集成失败: {str(e)}"
            )
    
    async def _delete_integration(self, integration_id: str) -> Dict[str, Any]:
        """删除集成"""
        try:
            success = await self.storage_manager.integration_storage.delete_integration(integration_id)
            
            if success:
                return {"success": True, "message": "集成删除成功"}
            else:
                return {"success": False, "message": "集成不存在"}
                
        except Exception as e:
            logger.error(f"Failed to delete integration: {e}")
            return {"success": False, "message": f"删除集成失败: {str(e)}"}
    
    # 用户统计实现
    async def _get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计"""
        try:
            stats = await self.storage_manager.stats_storage.get_stats(user_id)
            
            if stats:
                return {
                    "success": True,
                    "data": stats
                }
            else:
                return {"success": False, "message": "用户统计不存在"}
                
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {"success": False, "message": f"获取用户统计失败: {str(e)}"}
    
    async def _update_user_stats(self, user_id: str, stats_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新用户统计"""
        try:
            updated_stats = await self.storage_manager.stats_storage.update_stats(user_id, stats_data)
            
            if updated_stats:
                return {
                    "success": True,
                    "message": "用户统计更新成功",
                    "data": updated_stats
                }
            else:
                return {"success": False, "message": "更新用户统计失败"}
                
        except Exception as e:
            logger.error(f"Failed to update user stats: {e}")
            return {"success": False, "message": f"更新用户统计失败: {str(e)}"}
    
    # 系统健康检查和统计
    async def _health_check(self) -> Dict[str, Any]:
        """系统健康检查"""
        try:
            health_status = await self.storage_manager.health_check()
            
            return {
                "status": "healthy" if all(health_status.values()) else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "services": health_status
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _system_stats(self) -> Dict[str, Any]:
        """系统统计"""
        try:
            # 获取用户数量
            users = await self.storage_manager.user_storage.list_users(limit=1)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "users_count": len(users),
                "storage_health": await self.storage_manager.health_check()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {"error": str(e)}


class JavaClient:
    """Java客户端主类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = JavaClientConfig(**config)
        self.storage_manager = StorageManager(config)
        self.api = None
        
    async def start(self):
        """启动Java客户端"""
        try:
            # 初始化存储
            await self.storage_manager.initialize()
            
            # 初始化API
            self.api = JavaClientAPI(self.config, self.storage_manager)
            await self.api.initialize()
            
            logger.info("Java client started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Java client: {e}")
            raise
    
    async def stop(self):
        """停止Java客户端"""
        try:
            if self.storage_manager:
                await self.storage_manager.close()
            
            logger.info("Java client stopped successfully")
            
        except Exception as e:
            logger.error(f"Failed to stop Java client: {e}")
    
    def get_app(self) -> Optional[FastAPI]:
        """获取FastAPI应用实例"""
        return self.api.app if self.api else None