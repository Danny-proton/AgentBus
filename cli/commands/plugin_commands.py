"""
插件管理CLI命令
Plugin Management CLI Commands
"""

import asyncio
import click
import json
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path
from loguru import logger

from agentbus.plugins.manager import PluginManager, PluginInfo, PluginStatus
from agentbus.plugins.core import PluginContext


class PluginCommands:
    """插件管理命令类"""
    
    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
    
    async def discover_plugins(self) -> List[PluginInfo]:
        """发现所有可用插件"""
        return await self.plugin_manager.discover_plugins()
    
    async def list_plugins(self, format_type: str = "table", status_filter: Optional[str] = None) -> Dict[str, Any]:
        """列出插件"""
        try:
            # 获取插件信息
            plugin_info_list = self.plugin_manager.list_plugin_info()
            
            # 过滤状态
            if status_filter:
                plugin_info_list = [
                    info for info in plugin_info_list 
                    if info.status.value.lower() == status_filter.lower()
                ]
            
            # 构建结果
            result = {
                "total": len(plugin_info_list),
                "plugins": []
            }
            
            for info in plugin_info_list:
                plugin_data = {
                    "id": info.plugin_id,
                    "name": info.name,
                    "version": info.version,
                    "description": info.description,
                    "author": info.author,
                    "status": info.status.value,
                    "dependencies": info.dependencies,
                    "module_path": info.module_path
                }
                
                # 添加错误信息（如果有）
                if info.error_message:
                    plugin_data["error"] = info.error_message
                
                result["plugins"].append(plugin_data)
            
            # 按状态分组统计
            status_counts = {}
            for info in plugin_info_list:
                status = info.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            result["status_summary"] = status_counts
            
            return result
            
        except Exception as e:
            logger.error(f"获取插件列表失败: {e}")
            return {"error": str(e)}
    
    async def enable_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """启用插件"""
        try:
            # 加载插件（如果尚未加载）
            plugin_info = self.plugin_manager.get_plugin_info(plugin_id)
            if not plugin_info:
                # 尝试发现并加载插件
                discovered = await self.discover_plugins()
                found_plugin = None
                for info in discovered:
                    if info.plugin_id == plugin_id:
                        found_plugin = info
                        break
                
                if not found_plugin:
                    return {"success": False, "error": f"插件 {plugin_id} 未找到"}
                
                # 加载插件
                await self.plugin_manager.load_plugin(
                    plugin_id, 
                    found_plugin.module_path, 
                    found_plugin.class_name
                )
            
            # 激活插件
            success = await self.plugin_manager.activate_plugin(plugin_id)
            
            if success:
                return {
                    "success": True, 
                    "message": f"插件 {plugin_id} 已成功启用",
                    "plugin_id": plugin_id
                }
            else:
                return {
                    "success": False, 
                    "error": f"插件 {plugin_id} 启用失败",
                    "plugin_id": plugin_id
                }
                
        except Exception as e:
            logger.error(f"启用插件失败: {e}")
            return {"success": False, "error": f"启用插件时发生异常: {e}"}
    
    async def disable_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """禁用插件"""
        try:
            # 停用插件
            success = await self.plugin_manager.deactivate_plugin(plugin_id)
            
            if success:
                return {
                    "success": True, 
                    "message": f"插件 {plugin_id} 已成功禁用",
                    "plugin_id": plugin_id
                }
            else:
                return {
                    "success": False, 
                    "error": f"插件 {plugin_id} 禁用失败",
                    "plugin_id": plugin_id
                }
                
        except Exception as e:
            logger.error(f"禁用插件失败: {e}")
            return {"success": False, "error": f"禁用插件时发生异常: {e}"}
    
    async def reload_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """重新加载插件"""
        try:
            success = await self.plugin_manager.reload_plugin(plugin_id)
            
            if success:
                return {
                    "success": True, 
                    "message": f"插件 {plugin_id} 已成功重新加载",
                    "plugin_id": plugin_id
                }
            else:
                return {
                    "success": False, 
                    "error": f"插件 {plugin_id} 重新加载失败",
                    "plugin_id": plugin_id
                }
                
        except Exception as e:
            logger.error(f"重新加载插件失败: {e}")
            return {"success": False, "error": f"重新加载插件时发生异常: {e}"}
    
    async def unload_plugin(self, plugin_id: str) -> Dict[str, Any]:
        """卸载插件"""
        try:
            success = await self.plugin_manager.unload_plugin(plugin_id)
            
            if success:
                return {
                    "success": True, 
                    "message": f"插件 {plugin_id} 已成功卸载",
                    "plugin_id": plugin_id
                }
            else:
                return {
                    "success": False, 
                    "error": f"插件 {plugin_id} 卸载失败",
                    "plugin_id": plugin_id
                }
                
        except Exception as e:
            logger.error(f"卸载插件失败: {e}")
            return {"success": False, "error": f"卸载插件时发生异常: {e}"}
    
    async def get_plugin_details(self, plugin_id: str) -> Dict[str, Any]:
        """获取插件详细信息"""
        try:
            plugin = self.plugin_manager.get_plugin(plugin_id)
            plugin_info = self.plugin_manager.get_plugin_info(plugin_id)
            
            if not plugin_info:
                return {"error": f"插件 {plugin_id} 未找到"}
            
            # 获取工具和命令
            tools = []
            commands = []
            hooks = {}
            
            if plugin:
                # 获取插件工具
                plugin_tools = plugin.get_tools()
                for tool in plugin_tools:
                    tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters_schema if hasattr(tool, 'parameters_schema') else {}
                    })
                
                # 获取插件命令
                plugin_commands = plugin.get_commands()
                for cmd in plugin_commands:
                    commands.append({
                        "command": cmd.get('command', ''),
                        "description": cmd.get('description', ''),
                        "async_func": cmd.get('async_func', False)
                    })
                
                # 获取插件钩子
                plugin_hooks = plugin.get_hooks()
                for event, event_hooks in plugin_hooks.items():
                    hooks[event] = []
                    for hook in event_hooks:
                        hooks[event].append({
                            "priority": hook.priority,
                            "async": hook.async_func
                        })
            
            return {
                "plugin_id": plugin_id,
                "info": {
                    "name": plugin_info.name,
                    "version": plugin_info.version,
                    "description": plugin_info.description,
                    "author": plugin_info.author,
                    "status": plugin_info.status.value,
                    "dependencies": plugin_info.dependencies,
                    "module_path": plugin_info.module_path,
                    "class_name": plugin_info.class_name
                },
                "resources": {
                    "tools": tools,
                    "commands": commands,
                    "hooks": hooks
                },
                "statistics": await self.plugin_manager.get_plugin_stats()
            }
            
        except Exception as e:
            logger.error(f"获取插件详情失败: {e}")
            return {"error": f"获取插件详情时发生异常: {e}"}
    
    async def export_config(self, output_path: Path, format_type: str = "json") -> Dict[str, Any]:
        """导出插件配置"""
        try:
            plugin_info_list = self.plugin_manager.list_plugin_info()
            
            config_data = {
                "version": "1.0",
                "export_time": asyncio.get_event_loop().time(),
                "plugins": []
            }
            
            for info in plugin_info_list:
                plugin_config = {
                    "id": info.plugin_id,
                    "name": info.name,
                    "version": info.version,
                    "description": info.description,
                    "author": info.author,
                    "dependencies": info.dependencies,
                    "status": info.status.value,
                    "module_path": info.module_path,
                    "class_name": info.class_name
                }
                config_data["plugins"].append(plugin_config)
            
            # 保存到文件
            if format_type.lower() == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)
            elif format_type.lower() == "yaml":
                with open(output_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            else:
                return {"error": f"不支持的格式: {format_type}"}
            
            return {
                "success": True,
                "message": f"插件配置已导出到 {output_path}",
                "plugin_count": len(plugin_info_list)
            }
            
        except Exception as e:
            logger.error(f"导出插件配置失败: {e}")
            return {"error": f"导出配置时发生异常: {e}"}
    
    async def import_config(self, config_path: Path) -> Dict[str, Any]:
        """导入插件配置"""
        try:
            # 读取配置文件
            if config_path.suffix.lower() == ".json":
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            elif config_path.suffix.lower() in [".yaml", ".yml"]:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
            else:
                return {"error": f"不支持的配置文件格式: {config_path.suffix}"}
            
            imported_count = 0
            errors = []
            
            for plugin_config in config_data.get("plugins", []):
                try:
                    plugin_id = plugin_config.get("id")
                    module_path = plugin_config.get("module_path")
                    class_name = plugin_config.get("class_name")
                    
                    if not all([plugin_id, module_path, class_name]):
                        errors.append(f"插件配置不完整: {plugin_config}")
                        continue
                    
                    # 加载插件
                    await self.plugin_manager.load_plugin(plugin_id, module_path, class_name)
                    
                    # 如果配置中指定要启用，则启用插件
                    if plugin_config.get("status") == "active":
                        await self.plugin_manager.activate_plugin(plugin_id)
                    
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"导入插件 {plugin_config.get('id', 'unknown')} 失败: {e}")
            
            result = {
                "success": True,
                "imported_count": imported_count,
                "total_count": len(config_data.get("plugins", []))
            }
            
            if errors:
                result["errors"] = errors
            
            return result
            
        except Exception as e:
            logger.error(f"导入插件配置失败: {e}")
            return {"error": f"导入配置时发生异常: {e}"}


def create_plugin_commands(plugin_manager: PluginManager) -> PluginCommands:
    """创建插件命令实例"""
    return PluginCommands(plugin_manager)


# CLI命令组
@click.group()
def plugin():
    """插件管理命令"""
    pass


@plugin.command()
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json']), help='输出格式')
@click.option('--status', 'status_filter', help='按状态过滤 (active, inactive, error, unloaded)')
@click.pass_context
def list(ctx, output_format, status_filter):
    """列出所有插件"""
    plugin_manager = ctx.obj.get('plugin_manager')
    if not plugin_manager:
        click.echo("❌ 插件管理器未初始化", err=True)
        return
    
    async def _list():
        commands = create_plugin_commands(plugin_manager)
        result = await commands.list_plugins(output_format, status_filter)
        
        if "error" in result:
            click.echo(f"❌ {result['error']}", err=True)
            return
        
        if output_format == 'json':
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            click.echo("🔌 插件列表:")
            click.echo(f"   总计: {result['total']} 个插件")
            
            if result.get('status_summary'):
                click.echo("   状态统计:")
                for status, count in result['status_summary'].items():
                    click.echo(f"     {status}: {count}")
            
            click.echo()
            
            for plugin_data in result['plugins']:
                status_icon = {
                    'active': '✅',
                    'inactive': '⏸️',
                    'error': '❌',
                    'unloaded': '📦'
                }.get(plugin_data['status'], '❓')
                
                click.echo(f"   {status_icon} {plugin_data['name']} ({plugin_data['id']})")
                click.echo(f"      版本: {plugin_data['version']}")
                click.echo(f"      作者: {plugin_data['author']}")
                click.echo(f"      描述: {plugin_data['description']}")
                if plugin_data.get('error'):
                    click.echo(f"      错误: {plugin_data['error']}")
                click.echo()
    
    try:
        asyncio.run(_list())
    except Exception as e:
        click.echo(f"❌ 获取插件列表失败: {e}", err=True)


@plugin.command()
@click.argument('plugin_id')
@click.pass_context
def enable(ctx, plugin_id):
    """启用插件"""
    plugin_manager = ctx.obj.get('plugin_manager')
    if not plugin_manager:
        click.echo("❌ 插件管理器未初始化", err=True)
        return
    
    async def _enable():
        commands = create_plugin_commands(plugin_manager)
        result = await commands.enable_plugin(plugin_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_enable())
    except Exception as e:
        click.echo(f"❌ 启用插件失败: {e}", err=True)


@plugin.command()
@click.argument('plugin_id')
@click.pass_context
def disable(ctx, plugin_id):
    """禁用插件"""
    plugin_manager = ctx.obj.get('plugin_manager')
    if not plugin_manager:
        click.echo("❌ 插件管理器未初始化", err=True)
        return
    
    async def _disable():
        commands = create_plugin_commands(plugin_manager)
        result = await commands.disable_plugin(plugin_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_disable())
    except Exception as e:
        click.echo(f"❌ 禁用插件失败: {e}", err=True)


@plugin.command()
@click.argument('plugin_id')
@click.pass_context
def reload(ctx, plugin_id):
    """重新加载插件"""
    plugin_manager = ctx.obj.get('plugin_manager')
    if not plugin_manager:
        click.echo("❌ 插件管理器未初始化", err=True)
        return
    
    async def _reload():
        commands = create_plugin_commands(plugin_manager)
        result = await commands.reload_plugin(plugin_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_reload())
    except Exception as e:
        click.echo(f"❌ 重新加载插件失败: {e}", err=True)


@plugin.command()
@click.argument('plugin_id')
@click.pass_context
def unload(ctx, plugin_id):
    """卸载插件"""
    plugin_manager = ctx.obj.get('plugin_manager')
    if not plugin_manager:
        click.echo("❌ 插件管理器未初始化", err=True)
        return
    
    async def _unload():
        commands = create_plugin_commands(plugin_manager)
        result = await commands.unload_plugin(plugin_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_unload())
    except Exception as e:
        click.echo(f"❌ 卸载插件失败: {e}", err=True)


@plugin.command()
@click.argument('plugin_id')
@click.pass_context
def info(ctx, plugin_id):
    """显示插件详细信息"""
    plugin_manager = ctx.obj.get('plugin_manager')
    if not plugin_manager:
        click.echo("❌ 插件管理器未初始化", err=True)
        return
    
    async def _info():
        commands = create_plugin_commands(plugin_manager)
        result = await commands.get_plugin_details(plugin_id)
        
        if "error" in result:
            click.echo(f"❌ {result['error']}", err=True)
            return
        
        info = result['info']
        click.echo(f"🔌 插件详情: {info['name']}")
        click.echo(f"   ID: {plugin_id}")
        click.echo(f"   版本: {info['version']}")
        click.echo(f"   作者: {info['author']}")
        click.echo(f"   描述: {info['description']}")
        click.echo(f"   状态: {info['status']}")
        click.echo(f"   依赖: {', '.join(info['dependencies']) if info['dependencies'] else '无'}")
        click.echo(f"   模块路径: {info['module_path']}")
        click.echo(f"   类名: {info['class_name']}")
        
        resources = result['resources']
        if resources['tools']:
            click.echo(f"   工具 ({len(resources['tools'])}):")
            for tool in resources['tools']:
                click.echo(f"     - {tool['name']}: {tool['description']}")
        
        if resources['commands']:
            click.echo(f"   命令 ({len(resources['commands'])}):")
            for cmd in resources['commands']:
                click.echo(f"     - {cmd['command']}: {cmd['description']}")
        
        if resources['hooks']:
            click.echo(f"   钩子 ({len(resources['hooks'])}):")
            for event, hooks in resources['hooks'].items():
                click.echo(f"     - {event}: {len(hooks)} 个处理器")
    
    try:
        asyncio.run(_info())
    except Exception as e:
        click.echo(f"❌ 获取插件详情失败: {e}", err=True)


@plugin.command()
@click.option('--output', '-o', help='输出文件路径')
@click.option('--format', 'output_format', default='json', type=click.Choice(['json', 'yaml']), help='输出格式')
@click.pass_context
def export(ctx, output, output_format):
    """导出插件配置"""
    plugin_manager = ctx.obj.get('plugin_manager')
    if not plugin_manager:
        click.echo("❌ 插件管理器未初始化", err=True)
        return
    
    async def _export():
        commands = create_plugin_commands(plugin_manager)
        
        # 设置输出文件路径
        if not output:
            timestamp = asyncio.get_event_loop().time()
            output = f"plugins_config_{timestamp}.{output_format}"
        
        output_path = Path(output)
        result = await commands.export_config(output_path, output_format)
        
        if "error" in result:
            click.echo(f"❌ {result['error']}", err=True)
        else:
            click.echo(f"✅ {result['message']}")
    
    try:
        asyncio.run(_export())
    except Exception as e:
        click.echo(f"❌ 导出配置失败: {e}", err=True)


@plugin.command()
@click.argument('config_path', type=click.Path(exists=True))
@click.pass_context
def import_config(ctx, config_path):
    """导入插件配置"""
    plugin_manager = ctx.obj.get('plugin_manager')
    if not plugin_manager:
        click.echo("❌ 插件管理器未初始化", err=True)
        return
    
    async def _import():
        commands = create_plugin_commands(plugin_manager)
        config_file = Path(config_path)
        result = await commands.import_config(config_file)
        
        if "error" in result:
            click.echo(f"❌ {result['error']}", err=True)
        else:
            click.echo(f"✅ 导入完成: {result['imported_count']}/{result['total_count']} 个插件")
            if result.get('errors'):
                click.echo("⚠️ 部分插件导入失败:")
                for error in result['errors']:
                    click.echo(f"   - {error}")
    
    try:
        asyncio.run(_import())
    except Exception as e:
        click.echo(f"❌ 导入配置失败: {e}", err=True)


@plugin.command()
@click.pass_context
def stats(ctx):
    """显示插件系统统计信息"""
    plugin_manager = ctx.obj.get('plugin_manager')
    if not plugin_manager:
        click.echo("❌ 插件管理器未初始化", err=True)
        return
    
    async def _stats():
        stats = await plugin_manager.get_plugin_stats()
        
        click.echo("📊 插件系统统计:")
        click.echo(f"   总插件数: {stats['total_plugins']}")
        click.echo(f"   活跃插件: {stats['active_plugins']}")
        click.echo(f"   已加载插件: {stats['loaded_plugins']}")
        click.echo(f"   错误插件: {stats['error_plugins']}")
        click.echo(f"   总工具数: {stats['total_tools']}")
        click.echo(f"   总命令数: {stats['total_commands']}")
        click.echo(f"   总钩子数: {stats['total_hooks']}")
        
        if stats.get('plugins_by_status'):
            click.echo("   状态分布:")
            for status, count in stats['plugins_by_status'].items():
                click.echo(f"     {status}: {count}")
    
    try:
        asyncio.run(_stats())
    except Exception as e:
        click.echo(f"❌ 获取统计信息失败: {e}", err=True)