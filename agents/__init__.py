"""
AgentBus Agent System
完整的Agent系统框架

基于Moltbot架构，提供Agent生命周期管理、通信机制、状态监控、
资源管理和插件系统的完整解决方案。
"""

# 核心组件
from .core.base import (
    AgentCapability, AgentMetadata, AgentConfig, AgentMetrics,
    BaseAgent, AgentFactory, AgentManager, AgentRegistry
)
from .core.types import (
    AgentType, AgentStatus, AgentState, ResourceType,
    MessageType, Priority, PluginType, HealthStatus, AlertLevel,
    LifecycleEvent, LifecycleState, AgentHealth, SystemMetrics, Alert,
    ResourceQuota
)

# 生命周期管理
from .lifecycle.manager import (
    create_lifecycle_manager, get_lifecycle_manager
)

# 通信机制
from .communication.bus import (
    CommunicationBus,
    AgentMessage, BroadcastMessage, DirectMessage,
    create_communication_bus, get_communication_bus
)

# 状态监控
from .monitoring.system import (
    MonitoringSystem,
    create_monitoring_system, get_monitoring_system
)

# 资源管理
from .resource.manager import (
    ResourceManager, ResourcePool,
    create_resource_manager, get_resource_manager
)

# 插件系统
from .plugins.system import (
    PluginSystem,
    PluginManager, PluginInstance,
    create_plugin_system, get_plugin_system
)

# 便利函数
from .core.manager import (
    get_agent_system, initialize_agent_system,
    shutdown_agent_system, create_agent_instance
)

__version__ = "1.0.0"
__all__ = [
    # 核心组件
    "AgentType", "AgentStatus", "AgentState", "ResourceType",
    "AgentCapability", "AgentMetadata", "AgentConfig", "AgentMetrics",
    "BaseAgent", "AgentFactory", "AgentManager", "AgentRegistry",
    
    # 生命周期管理
    "LifecycleManager", "LifecycleEvent", "LifecycleState",
    "create_lifecycle_manager", "get_lifecycle_manager",
    
    # 通信机制
    "CommunicationBus", "MessageType", "Priority",
    "AgentMessage", "BroadcastMessage", "DirectMessage",
    "create_communication_bus", "get_communication_bus",
    
    # 状态监控
    "MonitoringSystem", "HealthStatus", "AlertLevel",
    "AgentHealth", "SystemMetrics", "Alert",
    "create_monitoring_system", "get_monitoring_system",
    
    # 资源管理
    "ResourceManager", "ResourceQuota", "ResourcePool",
    "ResourceUsage", "create_resource_manager", "get_resource_manager",
    
    # 插件系统
    "PluginSystem", "PluginType", "PluginManifest",
    "PluginManager", "PluginInstance",
    "create_plugin_system", "get_plugin_system",
    
    # 便利函数
    "get_agent_system", "initialize_agent_system",
    "shutdown_agent_system", "create_agent_instance"
]