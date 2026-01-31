"""
配置管理CLI命令
Configuration Management CLI Commands

基于Moltbot的配置CLI系统，提供完整的配置管理功能。
"""

import asyncio
import json
import yaml
import click
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
from loguru import logger

from config.config_manager import ConfigManager, ConfigProfile, ConfigFormat
from config.config_types import EnvironmentType, ValidationResult
from cli.commands.command_parser import AdvancedCommandParser, CommandRegistry


class ConfigCommands:
    """配置管理命令类"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    async def get_config(self, key: str, profile: Optional[str] = None, 
                        format_type: str = "table") -> Dict[str, Any]:
        """获取配置值"""
        try:
            # 设置档案
            if profile:
                await self.config_manager.switch_profile(profile)
            
            # 获取配置值
            value = await self.config_manager.get_config(key)
            
            if value is None:
                return {
                    "success": False,
                    "error": f"配置键 '{key}' 不存在"
                }
            
            return {
                "success": True,
                "key": key,
                "value": value,
                "profile": self.config_manager.get_current_profile(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取配置失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def set_config(self, key: str, value: Any, profile: Optional[str] = None,
                        encrypt: bool = False) -> Dict[str, Any]:
        """设置配置值"""
        try:
            # 设置档案
            if profile:
                await self.config_manager.switch_profile(profile)
            
            # 设置配置值
            await self.config_manager.set_config(key, value, encrypt=encrypt)
            
            return {
                "success": True,
                "key": key,
                "value": value,
                "profile": self.config_manager.get_current_profile(),
                "encrypted": encrypt,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"设置配置失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_config(self, key: str, profile: Optional[str] = None) -> Dict[str, Any]:
        """删除配置项"""
        try:
            # 设置档案
            if profile:
                await self.config_manager.switch_profile(profile)
            
            # 删除配置项
            success = await self.config_manager.delete_config(key)
            
            if success:
                return {
                    "success": True,
                    "key": key,
                    "profile": self.config_manager.get_current_profile(),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": f"配置键 '{key}' 不存在"
                }
            
        except Exception as e:
            logger.error(f"删除配置失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_config(self, profile: Optional[str] = None, 
                         format_type: str = "table") -> Dict[str, Any]:
        """列出配置项"""
        try:
            # 设置档案
            if profile:
                await self.config_manager.switch_profile(profile)
            
            # 获取所有配置
            config_data = await self.config_manager.get_all_config()
            
            # 转换为列表格式
            items = []
            for key, value in config_data.items():
                items.append({
                    "key": key,
                    "value": value,
                    "type": type(value).__name__,
                    "encrypted": hasattr(value, '_encrypted') if isinstance(value, dict) else False
                })
            
            # 按键名排序
            items.sort(key=lambda x: x['key'])
            
            return {
                "success": True,
                "profile": self.config_manager.get_current_profile(),
                "total": len(items),
                "items": items,
                "format": format_type
            }
            
        except Exception as e:
            logger.error(f"列出配置失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def create_profile(self, name: str, base_profile: Optional[str] = None) -> Dict[str, Any]:
        """创建配置档案"""
        try:
            success = await self.config_manager.create_profile(name, base_profile)
            
            if success:
                return {
                    "success": True,
                    "profile": name,
                    "base_profile": base_profile,
                    "message": f"配置档案 '{name}' 创建成功"
                }
            else:
                return {
                    "success": False,
                    "error": f"配置档案 '{name}' 创建失败，可能已存在"
                }
            
        except Exception as e:
            logger.error(f"创建配置档案失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def switch_profile(self, name: str) -> Dict[str, Any]:
        """切换配置档案"""
        try:
            success = await self.config_manager.switch_profile(name)
            
            if success:
                return {
                    "success": True,
                    "current_profile": name,
                    "message": f"已切换到配置档案 '{name}'"
                }
            else:
                return {
                    "success": False,
                    "error": f"配置档案 '{name}' 不存在"
                }
            
        except Exception as e:
            logger.error(f"切换配置档案失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_profiles(self) -> Dict[str, Any]:
        """列出所有配置档案"""
        try:
            profiles = await self.config_manager.list_profiles()
            current_profile = self.config_manager.get_current_profile()
            
            profile_list = []
            for name, profile in profiles.items():
                profile_list.append({
                    "name": name,
                    "active": name == current_profile,
                    "base_profile": profile.base_profile,
                    "created_at": profile.created_at.isoformat() if profile.created_at else None,
                    "modified_at": profile.modified_at.isoformat() if profile.modified_at else None,
                    "description": profile.description or ""
                })
            
            # 按名称排序
            profile_list.sort(key=lambda x: x['name'])
            
            return {
                "success": True,
                "profiles": profile_list,
                "current_profile": current_profile,
                "total": len(profile_list)
            }
            
        except Exception as e:
            logger.error(f"列出配置档案失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_profile(self, name: str) -> Dict[str, Any]:
        """删除配置档案"""
        try:
            success = await self.config_manager.delete_profile(name)
            
            if success:
                return {
                    "success": True,
                    "profile": name,
                    "message": f"配置档案 '{name}' 删除成功"
                }
            else:
                return {
                    "success": False,
                    "error": f"配置档案 '{name}' 删除失败"
                }
            
        except Exception as e:
            logger.error(f"删除配置档案失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def export_config(self, output_path: Path, format_type: str = "json",
                           profile: Optional[str] = None) -> Dict[str, Any]:
        """导出配置"""
        try:
            # 设置档案
            if profile:
                await self.config_manager.switch_profile(profile)
            
            # 获取配置数据
            config_data = await self.config_manager.get_all_config()
            
            # 构建导出数据
            export_data = {
                "version": "1.0",
                "export_time": datetime.now().isoformat(),
                "profile": self.config_manager.get_current_profile(),
                "environment": self.config_manager.get_environment(),
                "config": config_data
            }
            
            # 保存到文件
            if format_type.lower() == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            elif format_type.lower() in ["yaml", "yml"]:
                with open(output_path, 'w', encoding='utf-8') as f:
                    yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
            else:
                return {"success": False, "error": f"不支持的格式: {format_type}"}
            
            return {
                "success": True,
                "output_path": str(output_path),
                "format": format_type,
                "profile": self.config_manager.get_current_profile(),
                "config_count": len(config_data)
            }
            
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def import_config(self, config_path: Path, profile: Optional[str] = None,
                          merge: bool = True) -> Dict[str, Any]:
        """导入配置"""
        try:
            # 读取配置文件
            if config_path.suffix.lower() == ".json":
                with open(config_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
            elif config_path.suffix.lower() in [".yaml", ".yml"]:
                with open(config_path, 'r', encoding='utf-8') as f:
                    import_data = yaml.safe_load(f)
            else:
                return {"success": False, "error": f"不支持的配置文件格式: {config_path.suffix}"}
            
            # 设置目标档案
            target_profile = profile or import_data.get('profile', 'default')
            
            # 导入配置
            config_data = import_data.get('config', {})
            imported_count = 0
            
            for key, value in config_data.items():
                try:
                    await self.config_manager.set_config(key, value, profile=target_profile)
                    imported_count += 1
                except Exception as e:
                    logger.warning(f"导入配置项 {key} 失败: {e}")
            
            return {
                "success": True,
                "imported_count": imported_count,
                "total_count": len(config_data),
                "profile": target_profile,
                "source_file": str(config_path)
            }
            
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def validate_config(self, profile: Optional[str] = None) -> Dict[str, Any]:
        """验证配置"""
        try:
            # 设置档案
            if profile:
                await self.config_manager.switch_profile(profile)
            
            # 执行配置验证
            validation_result = await self.config_manager.validate_config()
            
            result = {
                "success": True,
                "profile": self.config_manager.get_current_profile(),
                "valid": validation_result.is_valid,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "timestamp": datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"验证配置失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def reset_config(self, profile: Optional[str] = None) -> Dict[str, Any]:
        """重置配置"""
        try:
            # 设置档案
            target_profile = profile or 'default'
            await self.config_manager.switch_profile(target_profile)
            
            # 重置配置
            success = await self.config_manager.reset_config()
            
            if success:
                return {
                    "success": True,
                    "profile": target_profile,
                    "message": f"配置档案 '{target_profile}' 已重置"
                }
            else:
                return {
                    "success": False,
                    "error": f"配置档案 '{target_profile}' 重置失败"
                }
            
        except Exception as e:
            logger.error(f"重置配置失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def backup_config(self, profile: Optional[str] = None) -> Dict[str, Any]:
        """备份配置"""
        try:
            # 设置档案
            target_profile = profile or self.config_manager.get_current_profile()
            
            # 创建备份
            backup_info = await self.config_manager.create_backup(target_profile)
            
            return {
                "success": True,
                "backup_id": backup_info.backup_id,
                "profile": target_profile,
                "created_at": backup_info.created_at.isoformat(),
                "size": backup_info.size,
                "file_path": str(backup_info.file_path)
            }
            
        except Exception as e:
            logger.error(f"备份配置失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def restore_config(self, backup_id: str) -> Dict[str, Any]:
        """恢复配置"""
        try:
            # 恢复备份
            success = await self.config_manager.restore_backup(backup_id)
            
            if success:
                return {
                    "success": True,
                    "backup_id": backup_id,
                    "message": f"备份 '{backup_id}' 恢复成功"
                }
            else:
                return {
                    "success": False,
                    "error": f"备份 '{backup_id}' 恢复失败"
                }
            
        except Exception as e:
            logger.error(f"恢复配置失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_backups(self) -> Dict[str, Any]:
        """列出备份"""
        try:
            backups = await self.config_manager.list_backups()
            
            backup_list = []
            for backup_info in backups:
                backup_list.append({
                    "backup_id": backup_info.backup_id,
                    "profile": backup_info.profile,
                    "created_at": backup_info.created_at.isoformat(),
                    "size": backup_info.size,
                    "file_path": str(backup_info.file_path)
                })
            
            # 按创建时间倒序
            backup_list.sort(key=lambda x: x['created_at'], reverse=True)
            
            return {
                "success": True,
                "backups": backup_list,
                "total": len(backup_list)
            }
            
        except Exception as e:
            logger.error(f"列出备份失败: {e}")
            return {"success": False, "error": str(e)}


def create_config_commands(config_manager: ConfigManager) -> ConfigCommands:
    """创建配置命令实例"""
    return ConfigCommands(config_manager)


# CLI命令组
@click.group()
def config():
    """配置管理命令"""
    pass


@config.command()
@click.argument('key')
@click.option('--profile', '-p', help='配置档案')
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json']), help='输出格式')
@click.pass_context
def get(ctx, key, profile, output_format):
    """获取配置值"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    async def _get():
        commands = create_config_commands(config_manager)
        result = await commands.get_config(key, profile, output_format)
        
        if result['success']:
            if output_format == 'json':
                click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            else:
                click.echo(f"✅ 配置项: {result['key']}")
                click.echo(f"   值: {result['value']}")
                click.echo(f"   档案: {result['profile']}")
                click.echo(f"   时间: {result['timestamp']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_get())
    except Exception as e:
        click.echo(f"❌ 获取配置失败: {e}", err=True)


@config.command()
@click.argument('key')
@click.argument('value')
@click.option('--profile', '-p', help='配置档案')
@click.option('--encrypt', '-e', is_flag=True, help='加密存储')
@click.pass_context
def set(ctx, key, value, profile, encrypt):
    """设置配置值"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    # 尝试解析JSON值
    try:
        if value.startswith(('{', '[', '"')):
            parsed_value = json.loads(value)
        else:
            parsed_value = value
    except json.JSONDecodeError:
        parsed_value = value
    
    async def _set():
        commands = create_config_commands(config_manager)
        result = await commands.set_config(key, parsed_value, profile, encrypt)
        
        if result['success']:
            click.echo(f"✅ 配置已设置: {result['key']} = {result['value']}")
            click.echo(f"   档案: {result['profile']}")
            if result['encrypted']:
                click.echo("   加密: 已启用")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_set())
    except Exception as e:
        click.echo(f"❌ 设置配置失败: {e}", err=True)


@config.command()
@click.argument('key')
@click.option('--profile', '-p', help='配置档案')
@click.pass_context
def delete(ctx, key, profile):
    """删除配置项"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    async def _delete():
        commands = create_config_commands(config_manager)
        result = await commands.delete_config(key, profile)
        
        if result['success']:
            click.echo(f"✅ 配置项已删除: {result['key']}")
            click.echo(f"   档案: {result['profile']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_delete())
    except Exception as e:
        click.echo(f"❌ 删除配置失败: {e}", err=True)


@config.command()
@click.option('--profile', '-p', help='配置档案')
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json']), help='输出格式')
@click.pass_context
def list(ctx, profile, output_format):
    """列出配置项"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    async def _list():
        commands = create_config_commands(config_manager)
        result = await commands.list_config(profile, output_format)
        
        if result['success']:
            if output_format == 'json':
                click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            else:
                click.echo(f"📋 配置列表 (档案: {result['profile']})")
                click.echo(f"   总计: {result['total']} 项")
                click.echo()
                
                for item in result['items']:
                    # 截断长值
                    value_str = str(item['value'])
                    if len(value_str) > 50:
                        value_str = value_str[:47] + "..."
                    
                    click.echo(f"   {item['key']}: {value_str} ({item['type']})")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_list())
    except Exception as e:
        click.echo(f"❌ 列出配置失败: {e}", err=True)


@config.command()
@click.argument('name')
@click.option('--base', 'base_profile', help='基础档案')
@click.pass_context
def profile_create(ctx, name, base_profile):
    """创建配置档案"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    async def _create():
        commands = create_config_commands(config_manager)
        result = await commands.create_profile(name, base_profile)
        
        if result['success']:
            click.echo(f"✅ 配置档案创建成功: {result['profile']}")
            if result.get('base_profile'):
                click.echo(f"   基础档案: {result['base_profile']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_create())
    except Exception as e:
        click.echo(f"❌ 创建配置档案失败: {e}", err=True)


@config.command()
@click.argument('name')
@click.pass_context
def profile_switch(ctx, name):
    """切换配置档案"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    async def _switch():
        commands = create_config_commands(config_manager)
        result = await commands.switch_profile(name)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_switch())
    except Exception as e:
        click.echo(f"❌ 切换配置档案失败: {e}", err=True)


@config.command()
@click.pass_context
def profile_list(ctx):
    """列出所有配置档案"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    async def _list():
        commands = create_config_commands(config_manager)
        result = await commands.list_profiles()
        
        if result['success']:
            click.echo(f"📋 配置档案列表 (当前: {result['current_profile']})")
            click.echo(f"   总计: {result['total']} 个档案")
            click.echo()
            
            for profile in result['profiles']:
                status = "✅ 激活" if profile['active'] else "📝"
                click.echo(f"   {status} {profile['name']}")
                if profile['description']:
                    click.echo(f"      描述: {profile['description']}")
                if profile['base_profile']:
                    click.echo(f"      基础: {profile['base_profile']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_list())
    except Exception as e:
        click.echo(f"❌ 列出配置档案失败: {e}", err=True)


@config.command()
@click.argument('name')
@click.pass_context
def profile_delete(ctx, name):
    """删除配置档案"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    async def _delete():
        commands = create_config_commands(config_manager)
        result = await commands.delete_profile(name)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_delete())
    except Exception as e:
        click.echo(f"❌ 删除配置档案失败: {e}", err=True)


@config.command()
@click.option('--output', '-o', help='输出文件路径')
@click.option('--format', 'output_format', default='json', type=click.Choice(['json', 'yaml']), help='输出格式')
@click.option('--profile', '-p', help='配置档案')
@click.pass_context
def export(ctx, output, output_format, profile):
    """导出配置"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    async def _export():
        commands = create_config_commands(config_manager)
        
        # 设置输出文件路径
        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            profile_suffix = f"_{profile}" if profile else ""
            output = f"config_export{profile_suffix}_{timestamp}.{output_format}"
        
        output_path = Path(output)
        result = await commands.export_config(output_path, output_format, profile)
        
        if result['success']:
            click.echo(f"✅ 配置导出成功")
            click.echo(f"   文件: {result['output_path']}")
            click.echo(f"   档案: {result['profile']}")
            click.echo(f"   格式: {result['format']}")
            click.echo(f"   配置项: {result['config_count']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_export())
    except Exception as e:
        click.echo(f"❌ 导出配置失败: {e}", err=True)


@config.command()
@click.argument('config_path', type=click.Path(exists=True))
@click.option('--profile', '-p', help='目标档案')
@click.option('--merge/--replace', default=True, help='合并或替换现有配置')
@click.pass_context
def import_config(ctx, config_path, profile, merge):
    """导入配置"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    async def _import():
        commands = create_config_commands(config_manager)
        config_file = Path(config_path)
        result = await commands.import_config(config_file, profile, merge)
        
        if result['success']:
            click.echo(f"✅ 配置导入完成")
            click.echo(f"   文件: {result['source_file']}")
            click.echo(f"   档案: {result['profile']}")
            click.echo(f"   导入: {result['imported_count']}/{result['total_count']} 项")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_import())
    except Exception as e:
        click.echo(f"❌ 导入配置失败: {e}", err=True)


@config.command()
@click.option('--profile', '-p', help='配置档案')
@click.pass_context
def validate(ctx, profile):
    """验证配置"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    async def _validate():
        commands = create_config_commands(config_manager)
        result = await commands.validate_config(profile)
        
        if result['success']:
            click.echo(f"🔍 配置验证结果 (档案: {result['profile']})")
            
            if result['valid']:
                click.echo("✅ 配置有效")
            else:
                click.echo("❌ 配置无效")
            
            if result['errors']:
                click.echo(f"❌ 错误 ({len(result['errors'])}):")
                for error in result['errors']:
                    click.echo(f"   - {error}")
            
            if result['warnings']:
                click.echo(f"⚠️ 警告 ({len(result['warnings'])}):")
                for warning in result['warnings']:
                    click.echo(f"   - {warning}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_validate())
    except Exception as e:
        click.echo(f"❌ 验证配置失败: {e}", err=True)


@config.command()
@click.option('--profile', '-p', help='配置档案')
@click.pass_context
def reset(ctx, profile):
    """重置配置"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    target_profile = profile or 'default'
    
    if not click.confirm(f"⚠️ 确认重置配置档案 '{target_profile}'？这将清除所有配置项！"):
        click.echo("操作已取消")
        return
    
    async def _reset():
        commands = create_config_commands(config_manager)
        result = await commands.reset_config(profile)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_reset())
    except Exception as e:
        click.echo(f"❌ 重置配置失败: {e}", err=True)


@config.command()
@click.option('--profile', '-p', help='配置档案')
@click.pass_context
def backup(ctx, profile):
    """备份配置"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    async def _backup():
        commands = create_config_commands(config_manager)
        result = await commands.backup_config(profile)
        
        if result['success']:
            click.echo(f"✅ 配置备份成功")
            click.echo(f"   备份ID: {result['backup_id']}")
            click.echo(f"   档案: {result['profile']}")
            click.echo(f"   文件: {result['file_path']}")
            click.echo(f"   大小: {result['size']} 字节")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_backup())
    except Exception as e:
        click.echo(f"❌ 备份配置失败: {e}", err=True)


@config.command()
@click.pass_context
def backup_list(ctx):
    """列出备份"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    async def _list():
        commands = create_config_commands(config_manager)
        result = await commands.list_backups()
        
        if result['success']:
            click.echo(f"📦 配置备份列表")
            click.echo(f"   总计: {result['total']} 个备份")
            click.echo()
            
            for backup in result['backups']:
                click.echo(f"   🆔 {backup['backup_id']}")
                click.echo(f"      档案: {backup['profile']}")
                click.echo(f"      时间: {backup['created_at']}")
                click.echo(f"      大小: {backup['size']} 字节")
                click.echo()
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_list())
    except Exception as e:
        click.echo(f"❌ 列出备份失败: {e}", err=True)


@config.command()
@click.argument('backup_id')
@click.pass_context
def backup_restore(ctx, backup_id):
    """恢复配置备份"""
    config_manager = ctx.obj.get('config_manager')
    if not config_manager:
        click.echo("❌ 配置管理器未初始化", err=True)
        return
    
    if not click.confirm(f"⚠️ 确认恢复备份 '{backup_id}'？当前配置将被覆盖！"):
        click.echo("操作已取消")
        return
    
    async def _restore():
        commands = create_config_commands(config_manager)
        result = await commands.restore_config(backup_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_restore())
    except Exception as e:
        click.echo(f"❌ 恢复配置失败: {e}", err=True)