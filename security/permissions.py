"""
权限控制系统 - Permission System

基于角色的访问控制(RBAC)实现。
提供细粒度的权限管理功能。
"""

import json
import time
from typing import Dict, List, Set, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from ..core.settings import Settings
from ..storage.database import Database
from ..storage.memory import MemoryStorage


class PermissionLevel(Enum):
    """权限级别"""
    NONE = 0
    READ = 1
    WRITE = 2
    ADMIN = 3
    SUPER_ADMIN = 4


class ResourceType(Enum):
    """资源类型"""
    USER = "user"
    AGENT = "agent"
    CHANNEL = "channel"
    MESSAGE = "message"
    PLUGIN = "plugin"
    CONFIG = "config"
    LOG = "log"
    SYSTEM = "system"


class Action(Enum):
    """操作类型"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class Permission:
    """权限模型"""
    id: str
    name: str
    description: str
    resource: ResourceType
    action: Action
    level: PermissionLevel
    conditions: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.conditions is None:
            self.conditions = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Permission':
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            resource=ResourceType(data['resource']),
            action=Action(data['action']),
            level=PermissionLevel(data['level']),
            conditions=data.get('conditions', {})
        )


@dataclass
class Role:
    """角色模型"""
    id: str
    name: str
    description: str
    permissions: List[str]  # Permission IDs
    is_system: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Role':
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            permissions=data['permissions'],
            is_system=data.get('is_system', False),
            metadata=data.get('metadata', {})
        )


@dataclass
class UserRole:
    """用户角色关联"""
    user_id: str
    role_id: str
    assigned_at: str
    assigned_by: str
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.assigned_at is None:
            from datetime import datetime
            self.assigned_at = datetime.utcnow().isoformat()
    
    def is_expired(self) -> bool:
        """检查角色是否已过期"""
        if not self.expires_at:
            return False
        from datetime import datetime
        return datetime.utcnow() > datetime.fromisoformat(self.expires_at)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserRole':
        return cls(**data)


class PermissionChecker:
    """权限检查器"""
    
    def __init__(self, permission_manager: 'PermissionManager'):
        self.permission_manager = permission_manager
    
    def has_permission(self, user_permissions: List[str], permission_id: str) -> bool:
        """检查用户是否有指定权限"""
        return permission_id in user_permissions
    
    def has_resource_permission(self, user_permissions: List[str], 
                               resource: ResourceType, action: Action) -> bool:
        """检查用户是否有指定资源的操作权限"""
        for perm_id in user_permissions:
            perm = self.permission_manager.get_permission(perm_id)
            if perm and perm.resource == resource and perm.action == action:
                return True
        return False
    
    def has_minimum_level(self, user_permissions: List[str], 
                          resource: ResourceType, action: Action, 
                          min_level: PermissionLevel) -> bool:
        """检查用户是否有最低级别的权限"""
        max_level = PermissionLevel.NONE
        for perm_id in user_permissions:
            perm = self.permission_manager.get_permission(perm_id)
            if perm and perm.resource == resource and perm.action == action:
                if perm.level.value > max_level.value:
                    max_level = perm.level
        
        return max_level.value >= min_level.value
    
    def can_access_resource(self, user_permissions: List[str], 
                           resource: ResourceType, resource_id: str = None) -> bool:
        """检查用户是否可以访问指定资源"""
        # 检查是否有读取权限
        if not self.has_resource_permission(user_permissions, resource, Action.READ):
            return False
        
        # 如果有资源ID，检查资源级权限
        if resource_id:
            for perm_id in user_permissions:
                perm = self.permission_manager.get_permission(perm_id)
                if (perm and perm.resource == resource and 
                    perm.action == Action.READ and 
                    self._check_resource_conditions(perm, resource_id)):
                    return True
            return False
        
        return True
    
    def can_modify_resource(self, user_permissions: List[str], 
                           resource: ResourceType, action: Action, 
                           resource_id: str = None) -> bool:
        """检查用户是否可以修改指定资源"""
        # 检查是否有修改权限
        if not self.has_resource_permission(user_permissions, resource, action):
            return False
        
        # 如果有资源ID，检查资源级权限
        if resource_id:
            for perm_id in user_permissions:
                perm = self.permission_manager.get_permission(perm_id)
                if (perm and perm.resource == resource and perm.action == action and
                    self._check_resource_conditions(perm, resource_id)):
                    return True
            return False
        
        return True
    
    def _check_resource_conditions(self, permission: Permission, resource_id: str) -> bool:
        """检查资源条件"""
        if not permission.conditions:
            return True
        
        # 检查资源ID匹配
        if 'resource_id' in permission.conditions:
            allowed_ids = permission.conditions['resource_id']
            if isinstance(allowed_ids, str):
                allowed_ids = [allowed_ids]
            return resource_id in allowed_ids
        
        # 检查资源前缀匹配
        if 'resource_prefix' in permission.conditions:
            prefix = permission.conditions['resource_prefix']
            return resource_id.startswith(prefix)
        
        # 检查资源标签匹配
        if 'resource_tags' in permission.conditions:
            # 这里应该查询资源的标签，简化实现
            return True
        
        return True


class RoleManager:
    """角色管理器"""
    
    def __init__(self, db: Database, memory: MemoryStorage):
        self.db = db
        self.memory = memory
        self._roles_cache: Dict[str, Role] = {}
        self._user_roles_cache: Dict[str, List[UserRole]] = {}
    
    async def create_role(self, role_id: str, name: str, description: str,
                         permissions: List[str], is_system: bool = False,
                         metadata: Dict[str, Any] = None) -> Role:
        """创建角色"""
        # 检查角色ID是否已存在
        if self.get_role(role_id):
            raise ValueError(f"角色 {role_id} 已存在")
        
        role = Role(
            id=role_id,
            name=name,
            description=description,
            permissions=permissions,
            is_system=is_system,
            metadata=metadata or {}
        )
        
        # 存储角色
        await self._store_role(role)
        
        return role
    
    def get_role(self, role_id: str) -> Optional[Role]:
        """获取角色"""
        # 先检查缓存
        if role_id in self._roles_cache:
            return self._roles_cache[role_id]
        
        # 从内存存储查询
        role_data = self.memory.get(f"role:{role_id}")
        if role_data:
            try:
                role_dict = json.loads(role_data)
                role = Role.from_dict(role_dict)
                # 更新缓存
                self._roles_cache[role_id] = role
                return role
            except (json.JSONDecodeError, TypeError):
                pass
        
        # 从数据库查询
        # 这里应该实现具体的数据库查询逻辑
        
        return None
    
    async def update_role(self, role_id: str, name: str = None, description: str = None,
                         permissions: List[str] = None, metadata: Dict[str, Any] = None) -> Optional[Role]:
        """更新角色"""
        role = self.get_role(role_id)
        if not role:
            return None
        
        if role.is_system:
            raise ValueError("不能修改系统角色")
        
        # 更新字段
        if name is not None:
            role.name = name
        if description is not None:
            role.description = description
        if permissions is not None:
            role.permissions = permissions
        if metadata is not None:
            role.metadata.update(metadata)
        
        # 存储更新后的角色
        await self._store_role(role)
        
        return role
    
    async def delete_role(self, role_id: str) -> bool:
        """删除角色"""
        role = self.get_role(role_id)
        if not role:
            return False
        
        if role.is_system:
            raise ValueError("不能删除系统角色")
        
        # 检查是否有用户使用此角色
        user_roles = await self.get_user_roles_by_role(role_id)
        if user_roles:
            raise ValueError("此角色正在被使用，无法删除")
        
        # 删除角色
        await self._remove_role(role_id)
        
        return True
    
    async def assign_role_to_user(self, user_id: str, role_id: str, 
                                 assigned_by: str, expires_at: str = None,
                                 metadata: Dict[str, Any] = None) -> UserRole:
        """为用户分配角色"""
        role = self.get_role(role_id)
        if not role:
            raise ValueError(f"角色 {role_id} 不存在")
        
        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        # 存储用户角色关联
        await self._store_user_role(user_role)
        
        return user_role
    
    async def revoke_role_from_user(self, user_id: str, role_id: str) -> bool:
        """撤销用户角色"""
        user_role = await self._get_user_role(user_id, role_id)
        if not user_role:
            return False
        
        await self._remove_user_role(user_id, role_id)
        
        return True
    
    async def get_user_roles(self, user_id: str) -> List[UserRole]:
        """获取用户的所有角色"""
        # 先检查缓存
        if user_id in self._user_roles_cache:
            cached_roles = self._user_roles_cache[user_id]
            # 过滤未过期的角色
            active_roles = [ur for ur in cached_roles if not ur.is_expired()]
            return active_roles
        
        # 从内存存储查询
        user_roles = []
        # 这里应该实现具体的查询逻辑
        
        return user_roles
    
    async def get_user_role_ids(self, user_id: str) -> List[str]:
        """获取用户的角色ID列表"""
        user_roles = await self.get_user_roles(user_id)
        return [ur.role_id for ur in user_roles]
    
    async def get_user_permissions(self, user_id: str) -> List[str]:
        """获取用户的所有权限"""
        user_role_ids = await self.get_user_role_ids(user_id)
        all_permissions = []
        
        for role_id in user_role_ids:
            role = self.get_role(role_id)
            if role:
                all_permissions.extend(role.permissions)
        
        # 去重
        return list(set(all_permissions))
    
    async def get_all_roles(self) -> List[Role]:
        """获取所有角色"""
        roles = []
        # 从缓存获取
        roles.extend(self._roles_cache.values())
        
        # 从数据库获取
        # 这里应该实现具体的查询逻辑
        
        return roles
    
    async def _get_user_role(self, user_id: str, role_id: str) -> Optional[UserRole]:
        """获取指定的用户角色关联"""
        # 从内存存储查询
        user_role_data = self.memory.get(f"user_role:{user_id}:{role_id}")
        if user_role_data:
            try:
                return UserRole.from_dict(json.loads(user_role_data))
            except (json.JSONDecodeError, TypeError):
                pass
        
        # 从数据库查询
        # 这里应该实现具体的查询逻辑
        
        return None
    
    async def get_user_roles_by_role(self, role_id: str) -> List[UserRole]:
        """根据角色ID获取所有用户角色关联"""
        user_roles = []
        # 这里应该实现具体的查询逻辑
        
        return user_roles
    
    async def _store_role(self, role: Role):
        """存储角色"""
        # 更新缓存
        self._roles_cache[role.id] = role
        
        # 存储到内存
        role_data = json.dumps(role.to_dict(), default=str)
        self.memory.set(f"role:{role.id}", role_data)
    
    async def _remove_role(self, role_id: str):
        """删除角色"""
        # 从缓存移除
        self._roles_cache.pop(role_id, None)
        
        # 从内存移除
        self.memory.delete(f"role:{role_id}")
        
        # 从数据库删除
        # 这里应该实现具体的删除逻辑
    
    async def _store_user_role(self, user_role: UserRole):
        """存储用户角色关联"""
        # 更新缓存
        if user_role.user_id not in self._user_roles_cache:
            self._user_roles_cache[user_role.user_id] = []
        self._user_roles_cache[user_role.user_id].append(user_role)
        
        # 存储到内存
        user_role_data = json.dumps(asdict(user_role), default=str)
        self.memory.set(f"user_role:{user_role.user_id}:{user_role.role_id}", user_role_data)
    
    async def _remove_user_role(self, user_id: str, role_id: str):
        """删除用户角色关联"""
        # 从缓存移除
        if user_id in self._user_roles_cache:
            self._user_roles_cache[user_id] = [
                ur for ur in self._user_roles_cache[user_id] 
                if ur.role_id != role_id
            ]
        
        # 从内存移除
        self.memory.delete(f"user_role:{user_id}:{role_id}")
        
        # 从数据库删除
        # 这里应该实现具体的删除逻辑


class PermissionManager:
    """权限管理器"""
    
    def __init__(self, settings: Settings, db: Database, memory: MemoryStorage):
        self.settings = settings
        self.db = db
        self.memory = memory
        self.role_manager = RoleManager(db, memory)
        self.permission_checker = PermissionChecker(self)
        
        # 权限缓存
        self._permissions_cache: Dict[str, Permission] = {}
        
        # 初始化默认权限
        self._initialize_default_permissions()
    
    def _initialize_default_permissions(self):
        """初始化默认权限"""
        default_permissions = [
            # 用户管理权限
            Permission("user.read", "查看用户", "查看用户信息", ResourceType.USER, Action.READ, PermissionLevel.READ),
            Permission("user.create", "创建用户", "创建新用户", ResourceType.USER, Action.CREATE, PermissionLevel.ADMIN),
            Permission("user.update", "更新用户", "更新用户信息", ResourceType.USER, Action.UPDATE, PermissionLevel.WRITE),
            Permission("user.delete", "删除用户", "删除用户", ResourceType.USER, Action.DELETE, PermissionLevel.ADMIN),
            
            # 代理管理权限
            Permission("agent.read", "查看代理", "查看代理信息", ResourceType.AGENT, Action.READ, PermissionLevel.READ),
            Permission("agent.create", "创建代理", "创建新代理", ResourceType.AGENT, Action.CREATE, PermissionLevel.WRITE),
            Permission("agent.update", "更新代理", "更新代理信息", ResourceType.AGENT, Action.UPDATE, PermissionLevel.WRITE),
            Permission("agent.delete", "删除代理", "删除代理", ResourceType.AGENT, Action.DELETE, PermissionLevel.ADMIN),
            Permission("agent.execute", "执行代理", "执行代理功能", ResourceType.AGENT, Action.EXECUTE, PermissionLevel.WRITE),
            
            # 通道管理权限
            Permission("channel.read", "查看通道", "查看通道信息", ResourceType.CHANNEL, Action.READ, PermissionLevel.READ),
            Permission("channel.create", "创建通道", "创建新通道", ResourceType.CHANNEL, Action.CREATE, PermissionLevel.WRITE),
            Permission("channel.update", "更新通道", "更新通道信息", ResourceType.CHANNEL, Action.UPDATE, PermissionLevel.WRITE),
            Permission("channel.delete", "删除通道", "删除通道", ResourceType.CHANNEL, Action.DELETE, PermissionLevel.ADMIN),
            
            # 消息管理权限
            Permission("message.read", "查看消息", "查看消息", ResourceType.MESSAGE, Action.READ, PermissionLevel.READ),
            Permission("message.create", "发送消息", "发送消息", ResourceType.MESSAGE, Action.CREATE, PermissionLevel.WRITE),
            Permission("message.update", "更新消息", "更新消息", ResourceType.MESSAGE, Action.UPDATE, PermissionLevel.WRITE),
            Permission("message.delete", "删除消息", "删除消息", ResourceType.MESSAGE, Action.DELETE, PermissionLevel.ADMIN),
            
            # 插件管理权限
            Permission("plugin.read", "查看插件", "查看插件信息", ResourceType.PLUGIN, Action.READ, PermissionLevel.READ),
            Permission("plugin.install", "安装插件", "安装插件", ResourceType.PLUGIN, Action.CREATE, PermissionLevel.ADMIN),
            Permission("plugin.update", "更新插件", "更新插件", ResourceType.PLUGIN, Action.UPDATE, PermissionLevel.ADMIN),
            Permission("plugin.delete", "删除插件", "删除插件", ResourceType.PLUGIN, Action.DELETE, PermissionLevel.SUPER_ADMIN),
            Permission("plugin.execute", "执行插件", "执行插件功能", ResourceType.PLUGIN, Action.EXECUTE, PermissionLevel.WRITE),
            
            # 配置管理权限
            Permission("config.read", "查看配置", "查看系统配置", ResourceType.CONFIG, Action.READ, PermissionLevel.READ),
            Permission("config.update", "更新配置", "更新系统配置", ResourceType.CONFIG, Action.UPDATE, PermissionLevel.ADMIN),
            
            # 日志管理权限
            Permission("log.read", "查看日志", "查看系统日志", ResourceType.LOG, Action.READ, PermissionLevel.READ),
            
            # 系统管理权限
            Permission("system.admin", "系统管理", "系统管理权限", ResourceType.SYSTEM, Action.ADMIN, PermissionLevel.SUPER_ADMIN),
        ]
        
        for permission in default_permissions:
            self._store_permission(permission)
        
        # 初始化默认角色
        self._initialize_default_roles()
    
    def _initialize_default_roles(self):
        """初始化默认角色"""
        # 超级管理员角色
        super_admin_role = Role(
            id="super_admin",
            name="超级管理员",
            description="拥有所有权限",
            permissions=[perm.id for perm in self._permissions_cache.values()],
            is_system=True
        )
        self.role_manager._store_role(super_admin_role)
        
        # 管理员角色
        admin_role = Role(
            id="admin",
            name="管理员",
            description="拥有大部分管理权限",
            permissions=[
                "user.read", "user.create", "user.update",
                "agent.read", "agent.create", "agent.update", "agent.delete", "agent.execute",
                "channel.read", "channel.create", "channel.update", "channel.delete",
                "message.read", "message.create", "message.update", "message.delete",
                "plugin.read", "plugin.install", "plugin.update", "plugin.execute",
                "config.read", "config.update",
                "log.read"
            ],
            is_system=True
        )
        self.role_manager._store_role(admin_role)
        
        # 用户角色
        user_role = Role(
            id="user",
            name="普通用户",
            description="基本用户权限",
            permissions=[
                "agent.read", "agent.execute",
                "channel.read",
                "message.read", "message.create",
                "plugin.read"
            ],
            is_system=True
        )
        self.role_manager._store_role(user_role)
        
        # 只读角色
        readonly_role = Role(
            id="readonly",
            name="只读用户",
            description="只能查看信息",
            permissions=[
                "user.read",
                "agent.read",
                "channel.read",
                "message.read",
                "plugin.read",
                "config.read",
                "log.read"
            ],
            is_system=True
        )
        self.role_manager._store_role(readonly_role)
    
    def get_permission(self, permission_id: str) -> Optional[Permission]:
        """获取权限"""
        # 先检查缓存
        if permission_id in self._permissions_cache:
            return self._permissions_cache[permission_id]
        
        # 从内存存储查询
        perm_data = self.memory.get(f"permission:{permission_id}")
        if perm_data:
            try:
                perm_dict = json.loads(perm_data)
                permission = Permission.from_dict(perm_dict)
                # 更新缓存
                self._permissions_cache[permission_id] = permission
                return permission
            except (json.JSONDecodeError, TypeError):
                pass
        
        # 从数据库查询
        # 这里应该实现具体的数据库查询逻辑
        
        return None
    
    async def create_permission(self, permission_id: str, name: str, description: str,
                              resource: ResourceType, action: Action, level: PermissionLevel,
                              conditions: Dict[str, Any] = None) -> Permission:
        """创建权限"""
        # 检查权限ID是否已存在
        if self.get_permission(permission_id):
            raise ValueError(f"权限 {permission_id} 已存在")
        
        permission = Permission(
            id=permission_id,
            name=name,
            description=description,
            resource=resource,
            action=action,
            level=level,
            conditions=conditions or {}
        )
        
        # 存储权限
        self._store_permission(permission)
        
        return permission
    
    async def update_permission(self, permission_id: str, name: str = None, 
                             description: str = None, level: PermissionLevel = None,
                             conditions: Dict[str, Any] = None) -> Optional[Permission]:
        """更新权限"""
        permission = self.get_permission(permission_id)
        if not permission:
            return None
        
        # 更新字段
        if name is not None:
            permission.name = name
        if description is not None:
            permission.description = description
        if level is not None:
            permission.level = level
        if conditions is not None:
            permission.conditions = conditions
        
        # 存储更新后的权限
        self._store_permission(permission)
        
        return permission
    
    async def delete_permission(self, permission_id: str) -> bool:
        """删除权限"""
        # 检查权限是否被角色使用
        roles = await self.role_manager.get_all_roles()
        for role in roles:
            if permission_id in role.permissions:
                raise ValueError(f"权限 {permission_id} 正在被角色 {role.id} 使用，无法删除")
        
        # 删除权限
        await self._remove_permission(permission_id)
        
        return True
    
    def _store_permission(self, permission: Permission):
        """存储权限"""
        # 更新缓存
        self._permissions_cache[permission.id] = permission
        
        # 存储到内存
        perm_data = json.dumps(permission.to_dict(), default=str)
        self.memory.set(f"permission:{permission.id}", perm_data)
    
    async def _remove_permission(self, permission_id: str):
        """删除权限"""
        # 从缓存移除
        self._permissions_cache.pop(permission_id, None)
        
        # 从内存移除
        self.memory.delete(f"permission:{permission_id}")
        
        # 从数据库删除
        # 这里应该实现具体的删除逻辑
    
    def check_permission(self, user_permissions: List[str], permission_id: str) -> bool:
        """检查权限"""
        return self.permission_checker.has_permission(user_permissions, permission_id)
    
    def check_resource_permission(self, user_permissions: List[str], 
                               resource: ResourceType, action: Action) -> bool:
        """检查资源权限"""
        return self.permission_checker.has_resource_permission(user_permissions, resource, action)
    
    def check_access(self, user_permissions: List[str], resource: ResourceType, 
                   action: Action, resource_id: str = None) -> bool:
        """检查访问权限"""
        if action in [Action.CREATE, Action.READ]:
            return self.permission_checker.can_access_resource(user_permissions, resource, resource_id)
        else:
            return self.permission_checker.can_modify_resource(user_permissions, resource, action, resource_id)
    
    def get_permission_checker(self) -> PermissionChecker:
        """获取权限检查器"""
        return self.permission_checker