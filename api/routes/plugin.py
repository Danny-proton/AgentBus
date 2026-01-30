"""
插件管理路由
Plugin Management Routes
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any, Optional
import logging

from ...core.dependencies import get_plugin_manager
from ...plugins.manager import PluginManager, PluginInfo

logger = logging.getLogger(__name__)

# 创建插件路由
plugin_router = APIRouter(prefix="/api/v1/plugins", tags=["plugins"])


@plugin_router.get("/")
async def list_plugins(plugin_manager: PluginManager = Depends(get_plugin_manager)):
    """列出所有插件"""
    try:
        plugins = plugin_manager.list_plugin_info()
        return {
            "plugins": [
                {
                    "id": p.plugin_id,
                    "name": p.name,
                    "version": p.version,
                    "description": p.description,
                    "author": p.author,
                    "status": p.status.value,
                    "dependencies": p.dependencies
                }
                for p in plugins
            ]
        }
    except Exception as e:
        logger.error(f"获取插件列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取插件列表失败: {str(e)}"
        )


@plugin_router.get("/{plugin_id}")
async def get_plugin_info(
    plugin_id: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """获取插件详细信息"""
    try:
        plugin_info = plugin_manager.get_plugin_info(plugin_id)
        if not plugin_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"插件 {plugin_id} 不存在"
            )
        
        plugin = plugin_manager.get_plugin(plugin_id)
        tools = plugin.get_tools() if plugin else []
        commands = plugin.get_commands() if plugin else []
        hooks = plugin.get_hooks() if plugin else {}
        
        return {
            "id": plugin_info.plugin_id,
            "name": plugin_info.name,
            "version": plugin_info.version,
            "description": plugin_info.description,
            "author": plugin_info.author,
            "status": plugin_info.status.value,
            "dependencies": plugin_info.dependencies,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
                for tool in tools
            ],
            "commands": [
                {
                    "command": cmd["command"],
                    "description": cmd.get("description", "")
                }
                for cmd in commands
            ],
            "hooks": list(hooks.keys()),
            "error_message": plugin_info.error_message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取插件信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取插件信息失败: {str(e)}"
        )


@plugin_router.post("/load")
async def load_plugin(
    plugin_id: str,
    module_path: str,
    class_name: Optional[str] = None,
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """加载插件"""
    try:
        plugin = await plugin_manager.load_plugin(plugin_id, module_path, class_name)
        return {
            "message": f"插件 {plugin_id} 加载成功",
            "plugin_id": plugin_id,
            "status": plugin.status.value
        }
        
    except Exception as e:
        logger.error(f"加载插件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"加载插件失败: {str(e)}"
        )


@plugin_router.post("/{plugin_id}/activate")
async def activate_plugin(
    plugin_id: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """激活插件"""
    try:
        success = await plugin_manager.activate_plugin(plugin_id)
        if success:
            return {
                "message": f"插件 {plugin_id} 激活成功",
                "plugin_id": plugin_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"插件 {plugin_id} 激活失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"激活插件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"激活插件失败: {str(e)}"
        )


@plugin_router.post("/{plugin_id}/deactivate")
async def deactivate_plugin(
    plugin_id: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """停用插件"""
    try:
        success = await plugin_manager.deactivate_plugin(plugin_id)
        if success:
            return {
                "message": f"插件 {plugin_id} 停用成功",
                "plugin_id": plugin_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"插件 {plugin_id} 停用失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停用插件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"停用插件失败: {str(e)}"
        )


@plugin_router.delete("/{plugin_id}")
async def unload_plugin(
    plugin_id: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """卸载插件"""
    try:
        success = await plugin_manager.unload_plugin(plugin_id)
        if success:
            return {
                "message": f"插件 {plugin_id} 卸载成功",
                "plugin_id": plugin_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"插件 {plugin_id} 卸载失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"卸载插件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"卸载插件失败: {str(e)}"
        )


@plugin_router.post("/{plugin_id}/reload")
async def reload_plugin(
    plugin_id: str,
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """重新加载插件"""
    try:
        success = await plugin_manager.reload_plugin(plugin_id)
        if success:
            return {
                "message": f"插件 {plugin_id} 重新加载成功",
                "plugin_id": plugin_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"插件 {plugin_id} 重新加载失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新加载插件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新加载插件失败: {str(e)}"
        )


@plugin_router.post("/execute_tool/{tool_name}")
async def execute_tool(
    tool_name: str,
    args: Dict[str, Any],
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """执行插件工具"""
    try:
        result = await plugin_manager.execute_tool(tool_name, **args)
        return {
            "tool_name": tool_name,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"执行工具失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行工具失败: {str(e)}"
        )


@plugin_router.get("/tools")
async def list_plugin_tools(
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """列出所有插件工具"""
    try:
        tools = plugin_manager.get_tools()
        return {
            "tools": [
                {
                    "name": name,
                    "owner_plugin_id": owner_id,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
                for name, (owner_id, tool) in tools.items()
            ]
        }
        
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取工具列表失败: {str(e)}"
        )


@plugin_router.get("/commands")
async def list_plugin_commands(
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """列出所有插件命令"""
    try:
        commands = plugin_manager.get_commands()
        return {
            "commands": [
                {
                    "name": name,
                    "owner_plugin_id": info["plugin_id"],
                    "description": info["description"],
                    "async_func": info["async_func"]
                }
                for name, info in commands.items()
            ]
        }
        
    except Exception as e:
        logger.error(f"获取命令列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取命令列表失败: {str(e)}"
        )


@plugin_router.get("/stats")
async def get_plugin_stats(
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """获取插件系统统计信息"""
    try:
        stats = await plugin_manager.get_plugin_stats()
        return stats
        
    except Exception as e:
        logger.error(f"获取插件统计信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取插件统计信息失败: {str(e)}"
        )


@plugin_router.get("/discover")
async def discover_plugins(
    plugin_manager: PluginManager = Depends(get_plugin_manager)
):
    """发现可用插件"""
    try:
        discovered = await plugin_manager.discover_plugins()
        return {
            "discovered_plugins": [
                {
                    "id": p.plugin_id,
                    "name": p.name,
                    "version": p.version,
                    "description": p.description,
                    "author": p.author,
                    "dependencies": p.dependencies,
                    "module_path": p.module_path
                }
                for p in discovered
            ]
        }
        
    except Exception as e:
        logger.error(f"发现插件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发现插件失败: {str(e)}"
        )