"""
渠道管理路由
Channel Management Routes
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

from core.dependencies import get_channel_manager
from channels.manager import ChannelManager
from channels.base import ChannelConfig

logger = logging.getLogger(__name__)

# 创建渠道路由
channel_router = APIRouter(prefix="/api/v1/channels", tags=["channels"])


@channel_router.get("/")
async def list_channels(
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """列出所有渠道"""
    try:
        channels = channel_manager.list_channels()
        return {
            "channels": channels,
            "count": len(channels)
        }
    except Exception as e:
        logger.error(f"获取渠道列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取渠道列表失败: {str(e)}"
        )


@channel_router.get("/{channel_id}")
async def get_channel_info(
    channel_id: str,
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """获取渠道详细信息"""
    try:
        config = channel_manager.get_channel_config(channel_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"渠道 {channel_id} 不存在"
            )
        
        # 获取连接状态
        status_info = await channel_manager.get_channel_status(channel_id)
        
        return {
            "channel_id": config.channel_id,
            "channel_type": config.channel_type,
            "description": config.description,
            "accounts": list(config.accounts.keys()) if config.accounts else [],
            "default_account_id": config.default_account_id,
            "status": {
                "connection_status": status_info.connection_status.value if status_info else "unknown",
                "state": status_info.state.value if status_info else "unknown",
                "last_error": status_info.last_error if status_info else None
            } if status_info else None,
            "settings": config.settings
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取渠道信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取渠道信息失败: {str(e)}"
        )


@channel_router.get("/{channel_id}/status")
async def get_channel_status(
    channel_id: str,
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """获取渠道状态"""
    try:
        status_info = await channel_manager.get_channel_status(channel_id)
        
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"渠道 {channel_id} 不存在"
            )
        
        return {
            "channel_id": channel_id,
            "connection_status": status_info.connection_status.value,
            "state": status_info.state.value,
            "is_connected": status_info.is_connected,
            "last_error": status_info.last_error,
            "connection_time": status_info.connection_time,
            "statistics": status_info.statistics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取渠道状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取渠道状态失败: {str(e)}"
        )


@channel_router.get("/status/all")
async def get_all_channels_status(
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """获取所有渠道状态"""
    try:
        all_status = await channel_manager.get_all_status()
        
        formatted_status = {}
        for channel_id, channel_status in all_status.items():
            formatted_status[channel_id] = {
                account_id: {
                    "connection_status": status.connection_status.value,
                    "state": status.state.value,
                    "is_connected": status.is_connected,
                    "last_error": status.last_error
                }
                for account_id, status in channel_status.items()
            }
        
        return {
            "channels_status": formatted_status,
            "count": len(formatted_status)
        }
        
    except Exception as e:
        logger.error(f"获取所有渠道状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取所有渠道状态失败: {str(e)}"
        )


@channel_router.post("/{channel_id}/connect")
async def connect_channel(
    channel_id: str,
    account_id: Optional[str] = None,
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """连接渠道"""
    try:
        success = await channel_manager.connect_channel(channel_id, account_id)
        
        if success:
            return {
                "message": f"渠道 {channel_id} 连接成功",
                "channel_id": channel_id,
                "account_id": account_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"渠道 {channel_id} 连接失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"连接渠道失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"连接渠道失败: {str(e)}"
        )


@channel_router.post("/{channel_id}/disconnect")
async def disconnect_channel(
    channel_id: str,
    account_id: Optional[str] = None,
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """断开渠道"""
    try:
        success = await channel_manager.disconnect_channel(channel_id, account_id)
        
        if success:
            return {
                "message": f"渠道 {channel_id} 断开成功",
                "channel_id": channel_id,
                "account_id": account_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"渠道 {channel_id} 断开失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"断开渠道失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"断开渠道失败: {str(e)}"
        )


@channel_router.post("/connect/all")
async def connect_all_channels(
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """连接所有渠道"""
    try:
        await channel_manager.connect_all()
        return {
            "message": "已尝试连接所有渠道",
            "timestamp": "2026-01-29T11:47:03Z"
        }
    except Exception as e:
        logger.error(f"连接所有渠道失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"连接所有渠道失败: {str(e)}"
        )


@channel_router.post("/disconnect/all")
async def disconnect_all_channels(
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """断开所有渠道"""
    try:
        await channel_manager.disconnect_all()
        return {
            "message": "已断开所有渠道",
            "timestamp": "2026-01-29T11:47:03Z"
        }
    except Exception as e:
        logger.error(f"断开所有渠道失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"断开所有渠道失败: {str(e)}"
        )


@channel_router.post("/{channel_id}/send")
async def send_message(
    channel_id: str,
    message_data: Dict[str, Any],
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """发送消息"""
    try:
        content = message_data.get("content")
        message_type = message_data.get("type", "text")
        account_id = message_data.get("account_id")
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="消息内容不能为空"
            )
        
        from ...channels.base import MessageType
        msg_type = MessageType.TEXT if message_type == "text" else MessageType.MEDIA
        
        success = await channel_manager.send_message(
            channel_id=channel_id,
            content=content,
            message_type=msg_type,
            account_id=account_id,
            **message_data.get("metadata", {})
        )
        
        if success:
            return {
                "message": f"消息已发送到渠道 {channel_id}",
                "channel_id": channel_id,
                "content": content,
                "message_type": message_type
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"发送消息失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送消息失败: {str(e)}"
        )


@channel_router.post("/{channel_id}/send_media")
async def send_media_message(
    channel_id: str,
    message_data: Dict[str, Any],
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """发送媒体消息"""
    try:
        content = message_data.get("content", "")
        media_url = message_data.get("media_url")
        account_id = message_data.get("account_id")
        
        if not media_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="媒体URL不能为空"
            )
        
        success = await channel_manager.send_media(
            channel_id=channel_id,
            content=content,
            media_url=media_url,
            account_id=account_id,
            **message_data.get("metadata", {})
        )
        
        if success:
            return {
                "message": f"媒体消息已发送到渠道 {channel_id}",
                "channel_id": channel_id,
                "media_url": media_url
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"发送媒体消息失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送媒体消息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送媒体消息失败: {str(e)}"
        )


@channel_router.get("/types")
async def get_channel_types(
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """获取可用的渠道类型"""
    try:
        registry = channel_manager.registry
        return {
            "channel_types": registry.list_available_channels()
        }
    except Exception as e:
        logger.error(f"获取渠道类型失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取渠道类型失败: {str(e)}"
        )


@channel_router.get("/stats")
async def get_channel_stats(
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """获取渠道统计信息"""
    try:
        stats = channel_manager.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"获取渠道统计信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取渠道统计信息失败: {str(e)}"
        )


@channel_router.get("/health")
async def get_channel_health(
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """获取渠道系统健康状态"""
    try:
        health = await channel_manager.health_check()
        return health
    except Exception as e:
        logger.error(f"获取渠道健康状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取渠道健康状态失败: {str(e)}"
        )


@channel_router.post("/register")
async def register_channel(
    channel_data: Dict[str, Any],
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """注册新渠道"""
    try:
        # 这里应该验证channel_data格式并创建ChannelConfig对象
        # 目前简化处理，实际应该使用ChannelConfig.from_dict()
        channel_id = channel_data.get("channel_id")
        channel_type = channel_data.get("channel_type")
        
        if not channel_id or not channel_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="渠道ID和类型不能为空"
            )
        
        # 创建临时配置对象
        config = ChannelConfig(
            channel_id=channel_id,
            channel_type=channel_type,
            description=channel_data.get("description", ""),
            accounts=channel_data.get("accounts", {}),
            settings=channel_data.get("settings", {})
        )
        
        success = await channel_manager.register_channel(config)
        
        if success:
            return {
                "message": f"渠道 {channel_id} 注册成功",
                "channel_id": channel_id,
                "channel_type": channel_type
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"渠道注册失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册渠道失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册渠道失败: {str(e)}"
        )


@channel_router.delete("/{channel_id}")
async def unregister_channel(
    channel_id: str,
    channel_manager: ChannelManager = Depends(get_channel_manager)
):
    """注销渠道"""
    try:
        success = await channel_manager.unregister_channel(channel_id)
        
        if success:
            return {
                "message": f"渠道 {channel_id} 注销成功",
                "channel_id": channel_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"渠道 {channel_id} 注销失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注销渠道失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注销渠道失败: {str(e)}"
        )