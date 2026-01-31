"""
依赖注入系统
Dependency Injection System
"""

from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncio

from services.hitl import HITLService
from services.communication_map import CommunicationMap
from services.message_channel import MessageChannel
from services.knowledge_bus import KnowledgeBus
from services.multi_model_coordinator import MultiModelCoordinator
from services.stream_response import StreamResponseProcessor
from plugins.manager import PluginManager
from channels.manager import ChannelManager
from core.main_app import get_application
from core.settings import settings


# 全局服务实例
_hitl_service: Optional[HITLService] = None
_communication_map: Optional[CommunicationMap] = None
_message_channel: Optional[MessageChannel] = None
_knowledge_bus: Optional[KnowledgeBus] = None
_multi_model_coordinator: Optional[MultiModelCoordinator] = None
_stream_response_processor: Optional[StreamResponseProcessor] = None

# 全局管理器实例
_plugin_manager: Optional[PluginManager] = None
_channel_manager: Optional[ChannelManager] = None


async def get_hitl_service() -> HITLService:
    """获取HITL服务实例"""
    global _hitl_service
    
    if _hitl_service is None:
        _hitl_service = HITLService()
        await _hitl_service.start()
    
    return _hitl_service


async def get_communication_map() -> CommunicationMap:
    """获取沟通地图实例"""
    global _communication_map
    
    if _communication_map is None:
        _communication_map = CommunicationMap()
        await _communication_map.load()
    
    return _communication_map


async def get_message_channel() -> MessageChannel:
    """获取消息通道实例"""
    global _message_channel
    
    if _message_channel is None:
        _message_channel = MessageChannel()
        await _message_channel.initialize()
    
    return _message_channel


async def get_knowledge_bus() -> KnowledgeBus:
    """获取知识总线实例"""
    global _knowledge_bus
    
    if _knowledge_bus is None:
        _knowledge_bus = KnowledgeBus()
        await _knowledge_bus.initialize()
    
    return _knowledge_bus


async def get_multi_model_coordinator() -> MultiModelCoordinator:
    """获取多模型协调器实例"""
    global _multi_model_coordinator
    
    if _multi_model_coordinator is None:
        _multi_model_coordinator = MultiModelCoordinator()
        await _multi_model_coordinator.initialize()
    
    return _multi_model_coordinator


async def get_stream_response_processor() -> StreamResponseProcessor:
    """获取流式响应处理器实例"""
    global _stream_response_processor
    
    if _stream_response_processor is None:
        _stream_response_processor = StreamResponseProcessor()
        await _stream_response_processor.initialize()
    
    return _stream_response_processor


# 插件和渠道管理器依赖

async def get_plugin_manager() -> PluginManager:
    """获取插件管理器实例"""
    global _plugin_manager
    
    if _plugin_manager is None:
        app = get_application()
        _plugin_manager = app.plugin_manager
        
    if _plugin_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="插件管理器未初始化"
        )
    
    return _plugin_manager


async def get_channel_manager() -> ChannelManager:
    """获取渠道管理器实例"""
    global _channel_manager
    
    if _channel_manager is None:
        app = get_application()
        _channel_manager = app.channel_manager
        
    if _channel_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="渠道管理器未初始化"
        )
    
    return _channel_manager


# 安全依赖
security = HTTPBearer()


from core.auth import verify_api_key


# 可选的认证依赖
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """获取当前用户（可选认证）"""
    # 在实际应用中，这里应该验证JWT token或API密钥
    return "user123"  # 示例用户ID


# 服务健康检查
async def check_services_health():
    """检查所有服务健康状态"""
    health_status = {
        "hitl_service": "healthy",
        "communication_map": "healthy",
        "message_channel": "healthy",
        "knowledge_bus": "healthy",
        "multi_model_coordinator": "healthy",
        "stream_response_processor": "healthy",
        "plugin_manager": "healthy",
        "channel_manager": "healthy"
    }
    
    try:
        # 检查HITL服务
        if _hitl_service:
            await _hitl_service.get_hitl_statistics()
        
        # 检查沟通地图
        if _communication_map:
            await _communication_map.get_contact_stats()
        
        # 检查消息通道
        if _message_channel:
            # 消息通道没有直接的健康检查方法
            pass
        
        # 检查知识总线
        if _knowledge_bus:
            await _knowledge_bus.get_knowledge_stats()
        
        # 检查多模型协调器
        if _multi_model_coordinator:
            await _multi_model_coordinator.get_coordinator_stats()
        
        # 检查流式响应处理器
        if _stream_response_processor:
            await _stream_response_processor.get_stream_stats()
        
        # 检查插件管理器
        if _plugin_manager:
            await _plugin_manager.get_plugin_stats()
        
        # 检查渠道管理器
        if _channel_manager:
            await _channel_manager.health_check()
            
    except Exception as e:
        health_status["error"] = str(e)
        health_status["status"] = "unhealthy"
    
    return health_status


# 应用启动和关闭事件
async def startup_event():
    """应用启动事件"""
    global _hitl_service, _communication_map, _message_channel, _knowledge_bus, _multi_model_coordinator, _stream_response_processor, _plugin_manager, _channel_manager
    
    try:
        # 获取主应用程序实例
        from core.main_app import get_application
        app = get_application()
        
        # 设置服务实例引用
        _hitl_service = app.hitl_service
        _communication_map = app.communication_map
        _message_channel = app.message_channel
        _knowledge_bus = app.knowledge_bus
        _multi_model_coordinator = app.multi_model_coordinator
        _stream_response_processor = app.stream_response_processor
        _plugin_manager = app.plugin_manager
        _channel_manager = app.channel_manager
        
        print("✅ 所有服务实例已设置")
        
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")
        raise


async def shutdown_event():
    """应用关闭事件"""
    global _hitl_service, _communication_map, _message_channel, _knowledge_bus, _multi_model_coordinator, _stream_response_processor, _plugin_manager, _channel_manager
    
    try:
        # 主应用程序关闭时，服务关闭由应用程序管理
        # 这里主要清理全局引用
        
        _hitl_service = None
        _communication_map = None
        _message_channel = None
        _knowledge_bus = None
        _multi_model_coordinator = None
        _stream_response_processor = None
        _plugin_manager = None
        _channel_manager = None
        
        print("✅ 全局服务引用已清理")
        
    except Exception as e:
        print(f"❌ 服务关闭失败: {e}")
