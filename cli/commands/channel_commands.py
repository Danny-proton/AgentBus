"""
渠道管理CLI命令
Channel Management CLI Commands
"""

import asyncio
import click
import json
import yaml
from typing import Dict, List, Optional, Any
from pathlib import Path
from loguru import logger

from channels.manager import ChannelManager
from channels.base import (
    ChannelConfig, ChannelAccountConfig, MessageType, ChatType
)


class ChannelCommands:
    """渠道管理命令类"""
    
    def __init__(self, channel_manager: ChannelManager):
        self.channel_manager = channel_manager
    
    async def list_channels(self, format_type: str = "table", status_filter: Optional[str] = None) -> Dict[str, Any]:
        """列出渠道"""
        try:
            channel_ids = self.channel_manager.list_channels()
            
            result = {
                "total": len(channel_ids),
                "channels": []
            }
            
            for channel_id in channel_ids:
                config = self.channel_manager.get_channel_config(channel_id)
                if not config:
                    continue
                
                # 检查连接状态
                is_connected = await self.channel_manager.is_channel_connected(channel_id)
                status = "connected" if is_connected else "disconnected"
                
                # 过滤状态
                if status_filter and status != status_filter.lower():
                    continue
                
                channel_data = {
                    "id": channel_id,
                    "name": getattr(config, 'name', channel_id),
                    "type": getattr(config, 'type', 'unknown'),
                    "status": status,
                    "account_count": len(config.accounts) if hasattr(config, 'accounts') else 0,
                    "default_account": getattr(config, 'default_account_id', None)
                }
                
                result["channels"].append(channel_data)
            
            # 统计信息
            connected_count = sum(1 for ch in result["channels"] if ch["status"] == "connected")
            result["statistics"] = {
                "total": len(result["channels"]),
                "connected": connected_count,
                "disconnected": len(result["channels"]) - connected_count
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取渠道列表失败: {e}")
            return {"error": str(e)}
    
    async def add_channel(self, channel_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加渠道"""
        try:
            # 创建渠道配置
            config = ChannelConfig.from_dict(channel_data)
            
            # 注册渠道
            success = await self.channel_manager.register_channel(config)
            
            if success:
                return {
                    "success": True,
                    "message": f"渠道 {config.channel_id} 添加成功",
                    "channel_id": config.channel_id
                }
            else:
                return {
                    "success": False,
                    "error": f"渠道 {channel_data.get('channel_id', 'unknown')} 添加失败"
                }
                
        except Exception as e:
            logger.error(f"添加渠道失败: {e}")
            return {"success": False, "error": f"添加渠道时发生异常: {e}"}
    
    async def remove_channel(self, channel_id: str) -> Dict[str, Any]:
        """删除渠道"""
        try:
            # 注销渠道
            success = await self.channel_manager.unregister_channel(channel_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"渠道 {channel_id} 删除成功",
                    "channel_id": channel_id
                }
            else:
                return {
                    "success": False,
                    "error": f"渠道 {channel_id} 删除失败"
                }
                
        except Exception as e:
            logger.error(f"删除渠道失败: {e}")
            return {"success": False, "error": f"删除渠道时发生异常: {e}"}
    
    async def connect_channel(self, channel_id: str, account_id: Optional[str] = None) -> Dict[str, Any]:
        """连接渠道"""
        try:
            success = await self.channel_manager.connect_channel(channel_id, account_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"渠道 {channel_id} 连接成功",
                    "channel_id": channel_id,
                    "account_id": account_id
                }
            else:
                return {
                    "success": False,
                    "error": f"渠道 {channel_id} 连接失败"
                }
                
        except Exception as e:
            logger.error(f"连接渠道失败: {e}")
            return {"success": False, "error": f"连接渠道时发生异常: {e}"}
    
    async def disconnect_channel(self, channel_id: str, account_id: Optional[str] = None) -> Dict[str, Any]:
        """断开渠道"""
        try:
            success = await self.channel_manager.disconnect_channel(channel_id, account_id)
            
            if success:
                return {
                    "success": True,
                    "message": f"渠道 {channel_id} 断开连接成功",
                    "channel_id": channel_id,
                    "account_id": account_id
                }
            else:
                return {
                    "success": False,
                    "error": f"渠道 {channel_id} 断开连接失败"
                }
                
        except Exception as e:
            logger.error(f"断开渠道失败: {e}")
            return {"success": False, "error": f"断开渠道时发生异常: {e}"}
    
    async def send_message_to_channel(
        self, 
        channel_id: str, 
        content: str, 
        message_type: str = "text",
        account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """向渠道发送消息"""
        try:
            msg_type = MessageType(message_type.lower())
            
            success = await self.channel_manager.send_message(
                channel_id=channel_id,
                content=content,
                message_type=msg_type,
                account_id=account_id
            )
            
            if success:
                return {
                    "success": True,
                    "message": f"消息发送到渠道 {channel_id} 成功",
                    "channel_id": channel_id,
                    "content": content[:50] + "..." if len(content) > 50 else content
                }
            else:
                return {
                    "success": False,
                    "error": f"发送消息到渠道 {channel_id} 失败"
                }
                
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return {"success": False, "error": f"发送消息时发生异常: {e}"}
    
    async def get_channel_status(self, channel_id: str, account_id: Optional[str] = None) -> Dict[str, Any]:
        """获取渠道状态"""
        try:
            status = await self.channel_manager.get_channel_status(channel_id, account_id)
            
            if not status:
                return {"error": f"无法获取渠道 {channel_id} 的状态"}
            
            return {
                "channel_id": channel_id,
                "account_id": account_id,
                "connection_status": status.connection_status.value,
                "state": status.state.value,
                "last_activity": status.last_activity.isoformat() if status.last_activity else None,
                "error_message": status.error_message,
                "metadata": getattr(status, 'metadata', {})
            }
            
        except Exception as e:
            logger.error(f"获取渠道状态失败: {e}")
            return {"error": f"获取渠道状态时发生异常: {e}"}
    
    async def get_channel_details(self, channel_id: str) -> Dict[str, Any]:
        """获取渠道详细信息"""
        try:
            config = self.channel_manager.get_channel_config(channel_id)
            if not config:
                return {"error": f"渠道 {channel_id} 未找到"}
            
            # 获取状态
            status = await self.channel_manager.get_channel_status(channel_id)
            
            # 构建详细信息
            details = {
                "channel_id": channel_id,
                "config": config.to_dict() if hasattr(config, 'to_dict') else {},
                "status": {
                    "connection_status": status.connection_status.value if status else "unknown",
                    "state": status.state.value if status else "unknown",
                    "last_activity": status.last_activity.isoformat() if status and status.last_activity else None,
                    "error_message": status.error_message if status else None
                } if status else None,
                "adapter_info": {
                    "type": type(config).__name__ if config else "unknown",
                    "has_adapter": self.channel_manager.get_channel_adapter(channel_id) is not None
                }
            }
            
            return details
            
        except Exception as e:
            logger.error(f"获取渠道详情失败: {e}")
            return {"error": f"获取渠道详情时发生异常: {e}"}
    
    async def export_config(self, output_path: Path, format_type: str = "json") -> Dict[str, Any]:
        """导出渠道配置"""
        try:
            channel_ids = self.channel_manager.list_channels()
            
            config_data = {
                "version": "1.0",
                "export_time": asyncio.get_event_loop().time(),
                "channels": {}
            }
            
            for channel_id in channel_ids:
                config = self.channel_manager.get_channel_config(channel_id)
                if config and hasattr(config, 'to_dict'):
                    config_data["channels"][channel_id] = config.to_dict()
            
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
                "message": f"渠道配置已导出到 {output_path}",
                "channel_count": len(channel_ids)
            }
            
        except Exception as e:
            logger.error(f"导出渠道配置失败: {e}")
            return {"error": f"导出配置时发生异常: {e}"}
    
    async def import_config(self, config_path: Path) -> Dict[str, Any]:
        """导入渠道配置"""
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
            
            for channel_id, channel_config in config_data.get("channels", {}).items():
                try:
                    # 创建配置对象
                    config = ChannelConfig.from_dict(channel_config)
                    
                    # 注册渠道
                    success = await self.channel_manager.register_channel(config)
                    if success:
                        imported_count += 1
                    else:
                        errors.append(f"注册渠道 {channel_id} 失败")
                        
                except Exception as e:
                    errors.append(f"导入渠道 {channel_id} 失败: {e}")
            
            result = {
                "success": True,
                "imported_count": imported_count,
                "total_count": len(config_data.get("channels", {}))
            }
            
            if errors:
                result["errors"] = errors
            
            return result
            
        except Exception as e:
            logger.error(f"导入渠道配置失败: {e}")
            return {"error": f"导入配置时发生异常: {e}"}
    
    async def connect_all_channels(self) -> Dict[str, Any]:
        """连接所有渠道"""
        try:
            await self.channel_manager.connect_all()
            
            # 获取连接后的状态
            status_info = await self.get_channels_status_summary()
            
            return {
                "success": True,
                "message": "所有渠道连接操作已完成",
                "status": status_info
            }
            
        except Exception as e:
            logger.error(f"连接所有渠道失败: {e}")
            return {"success": False, "error": f"连接所有渠道时发生异常: {e}"}
    
    async def disconnect_all_channels(self) -> Dict[str, Any]:
        """断开所有渠道"""
        try:
            await self.channel_manager.disconnect_all()
            
            return {
                "success": True,
                "message": "所有渠道已断开连接"
            }
            
        except Exception as e:
            logger.error(f"断开所有渠道失败: {e}")
            return {"success": False, "error": f"断开所有渠道时发生异常: {e}"}
    
    async def get_channels_status_summary(self) -> Dict[str, Any]:
        """获取所有渠道状态摘要"""
        try:
            all_status = await self.channel_manager.get_all_status()
            
            summary = {
                "total_channels": len(all_status),
                "connected_channels": 0,
                "disconnected_channels": 0,
                "channels": {}
            }
            
            for channel_id, account_statuses in all_status.items():
                channel_connected = any(
                    status.connection_status.value == "connected" 
                    for status in account_statuses.values()
                )
                
                if channel_connected:
                    summary["connected_channels"] += 1
                else:
                    summary["disconnected_channels"] += 1
                
                summary["channels"][channel_id] = {
                    "connected": channel_connected,
                    "accounts": {
                        acc_id: {
                            "status": status.connection_status.value,
                            "state": status.state.value
                        }
                        for acc_id, status in account_statuses.items()
                    }
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"获取渠道状态摘要失败: {e}")
            return {"error": f"获取状态摘要时发生异常: {e}"}
    
    async def test_channel_connection(self, channel_id: str, account_id: Optional[str] = None) -> Dict[str, Any]:
        """测试渠道连接"""
        try:
            # 首先断开连接
            await self.channel_manager.disconnect_channel(channel_id, account_id)
            
            # 尝试连接
            success = await self.channel_manager.connect_channel(channel_id, account_id)
            
            if success:
                # 等待连接建立
                await asyncio.sleep(2)
                
                # 检查连接状态
                is_connected = await self.channel_manager.is_channel_connected(channel_id, account_id)
                
                if is_connected:
                    return {
                        "success": True,
                        "channel_id": channel_id,
                        "account_id": account_id,
                        "message": f"渠道 {channel_id} 连接测试成功",
                        "connection_time": datetime.now().isoformat()
                    }
                else:
                    # 获取错误信息
                    status = await self.channel_manager.get_channel_status(channel_id, account_id)
                    error_msg = status.error_message if status else "未知错误"
                    
                    return {
                        "success": False,
                        "channel_id": channel_id,
                        "account_id": account_id,
                        "error": f"连接测试失败: {error_msg}",
                        "message": f"渠道 {channel_id} 连接测试失败"
                    }
            else:
                return {
                    "success": False,
                    "channel_id": channel_id,
                    "account_id": account_id,
                    "error": "连接启动失败",
                    "message": f"渠道 {channel_id} 连接测试失败"
                }
                
        except Exception as e:
            logger.error(f"测试渠道连接失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def restart_channel(self, channel_id: str, account_id: Optional[str] = None) -> Dict[str, Any]:
        """重启渠道"""
        try:
            # 断开连接
            await self.channel_manager.disconnect_channel(channel_id, account_id)
            
            # 等待断开完成
            await asyncio.sleep(1)
            
            # 重新连接
            success = await self.channel_manager.connect_channel(channel_id, account_id)
            
            if success:
                # 等待连接建立
                await asyncio.sleep(2)
                
                # 检查连接状态
                is_connected = await self.channel_manager.is_channel_connected(channel_id, account_id)
                
                if is_connected:
                    return {
                        "success": True,
                        "channel_id": channel_id,
                        "account_id": account_id,
                        "message": f"渠道 {channel_id} 重启成功",
                        "restart_time": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "channel_id": channel_id,
                        "account_id": account_id,
                        "error": "重启后连接失败",
                        "message": f"渠道 {channel_id} 重启失败"
                    }
            else:
                return {
                    "success": False,
                    "channel_id": channel_id,
                    "account_id": account_id,
                    "error": "重启启动连接失败",
                    "message": f"渠道 {channel_id} 重启失败"
                }
                
        except Exception as e:
            logger.error(f"重启渠道失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_channel_logs(self, channel_id: str, account_id: Optional[str] = None, 
                             limit: int = 100) -> Dict[str, Any]:
        """获取渠道日志"""
        try:
            # 这里需要根据实际的日志系统实现
            # 目前返回模拟数据
            logs = []
            
            # 模拟日志数据
            for i in range(min(limit, 10)):
                log_entry = {
                    "timestamp": (datetime.now() - timedelta(minutes=i)).isoformat(),
                    "level": "INFO" if i % 3 != 0 else "ERROR",
                    "message": f"模拟日志条目 {i} for channel {channel_id}",
                    "channel_id": channel_id,
                    "account_id": account_id
                }
                logs.append(log_entry)
            
            return {
                "success": True,
                "channel_id": channel_id,
                "account_id": account_id,
                "logs": logs,
                "total": len(logs)
            }
            
        except Exception as e:
            logger.error(f"获取渠道日志失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_channel_config(self, channel_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """更新渠道配置"""
        try:
            # 获取当前配置
            config = self.channel_manager.get_channel_config(channel_id)
            if not config:
                return {
                    "success": False,
                    "error": f"渠道 {channel_id} 未找到"
                }
            
            # 更新配置字段
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            # 重新注册渠道
            success = await self.channel_manager.register_channel(config)
            
            if success:
                return {
                    "success": True,
                    "channel_id": channel_id,
                    "message": f"渠道 {channel_id} 配置更新成功",
                    "updated_fields": list(updates.keys())
                }
            else:
                return {
                    "success": False,
                    "channel_id": channel_id,
                    "error": "配置更新失败",
                    "message": f"渠道 {channel_id} 配置更新失败"
                }
                
        except Exception as e:
            logger.error(f"更新渠道配置失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def clone_channel(self, source_channel_id: str, target_channel_id: str, 
                          target_name: Optional[str] = None) -> Dict[str, Any]:
        """克隆渠道"""
        try:
            # 获取源渠道配置
            source_config = self.channel_manager.get_channel_config(source_channel_id)
            if not source_config:
                return {
                    "success": False,
                    "error": f"源渠道 {source_channel_id} 未找到"
                }
            
            # 创建新配置
            new_config = ChannelConfig(
                channel_id=target_channel_id,
                name=target_name or f"{source_config.name}_clone",
                type=source_config.type,
                accounts=source_config.accounts.copy() if hasattr(source_config, 'accounts') else {},
                settings=source_config.settings.copy() if hasattr(source_config, 'settings') else {},
                enabled=source_config.enabled
            )
            
            # 注册新渠道
            success = await self.channel_manager.register_channel(new_config)
            
            if success:
                return {
                    "success": True,
                    "source_channel_id": source_channel_id,
                    "target_channel_id": target_channel_id,
                    "message": f"渠道 {source_channel_id} 已克隆为 {target_channel_id}",
                    "target_name": new_config.name
                }
            else:
                return {
                    "success": False,
                    "source_channel_id": source_channel_id,
                    "target_channel_id": target_channel_id,
                    "error": "克隆失败",
                    "message": f"渠道 {source_channel_id} 克隆失败"
                }
                
        except Exception as e:
            logger.error(f"克隆渠道失败: {e}")
            return {"success": False, "error": str(e)}


def create_channel_commands(channel_manager: ChannelManager) -> ChannelCommands:
    """创建渠道命令实例"""
    return ChannelCommands(channel_manager)


# CLI命令组
@click.group()
def channel():
    """渠道管理命令"""
    pass


@channel.command()
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json']), help='输出格式')
@click.option('--status', 'status_filter', help='按状态过滤 (connected, disconnected)')
@click.pass_context
def list(ctx, output_format, status_filter):
    """列出所有渠道"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _list():
        commands = create_channel_commands(channel_manager)
        result = await commands.list_channels(output_format, status_filter)
        
        if "error" in result:
            click.echo(f"❌ {result['error']}", err=True)
            return
        
        if output_format == 'json':
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            click.echo("📡 渠道列表:")
            click.echo(f"   总计: {result['total']} 个渠道")
            
            if result.get('statistics'):
                stats = result['statistics']
                click.echo(f"   已连接: {stats['connected']}")
                click.echo(f"   未连接: {stats['disconnected']}")
            
            click.echo()
            
            for channel_data in result['channels']:
                status_icon = "✅" if channel_data['status'] == 'connected' else "❌"
                click.echo(f"   {status_icon} {channel_data['name']} ({channel_data['id']})")
                click.echo(f"      类型: {channel_data['type']}")
                click.echo(f"      状态: {channel_data['status']}")
                click.echo(f"      账户数: {channel_data['account_count']}")
                if channel_data['default_account']:
                    click.echo(f"      默认账户: {channel_data['default_account']}")
                click.echo()
    
    try:
        asyncio.run(_list())
    except Exception as e:
        click.echo(f"❌ 获取渠道列表失败: {e}", err=True)


@channel.command()
@click.argument('channel_id')
@click.option('--name', help='渠道名称')
@click.option('--type', 'channel_type', required=True, help='渠道类型')
@click.option('--default-account', help='默认账户ID')
@click.pass_context
def add(ctx, channel_id, name, channel_type, default_account):
    """添加渠道"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _add():
        commands = create_channel_commands(channel_manager)
        
        channel_data = {
            "channel_id": channel_id,
            "name": name or channel_id,
            "type": channel_type,
            "default_account_id": default_account,
            "accounts": {}
        }
        
        result = await commands.add_channel(channel_data)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_add())
    except Exception as e:
        click.echo(f"❌ 添加渠道失败: {e}", err=True)


@channel.command()
@click.argument('channel_id')
@click.pass_context
def remove(ctx, channel_id):
    """删除渠道"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _remove():
        commands = create_channel_commands(channel_manager)
        result = await commands.remove_channel(channel_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_remove())
    except Exception as e:
        click.echo(f"❌ 删除渠道失败: {e}", err=True)


@channel.command()
@click.argument('channel_id')
@click.option('--account', 'account_id', help='账户ID')
@click.pass_context
def connect(ctx, channel_id, account_id):
    """连接渠道"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _connect():
        commands = create_channel_commands(channel_manager)
        result = await commands.connect_channel(channel_id, account_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_connect())
    except Exception as e:
        click.echo(f"❌ 连接渠道失败: {e}", err=True)


@channel.command()
@click.argument('channel_id')
@click.option('--account', 'account_id', help='账户ID')
@click.pass_context
def disconnect(ctx, channel_id, account_id):
    """断开渠道"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _disconnect():
        commands = create_channel_commands(channel_manager)
        result = await commands.disconnect_channel(channel_id, account_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_disconnect())
    except Exception as e:
        click.echo(f"❌ 断开渠道失败: {e}", err=True)


@channel.command()
@click.argument('channel_id')
@click.option('--account', 'account_id', help='账户ID')
@click.pass_context
def status(ctx, channel_id, account_id):
    """查看渠道状态"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _status():
        commands = create_channel_commands(channel_manager)
        result = await commands.get_channel_status(channel_id, account_id)
        
        if "error" in result:
            click.echo(f"❌ {result['error']}", err=True)
            return
        
        click.echo(f"📡 渠道状态: {channel_id}")
        click.echo(f"   连接状态: {result['connection_status']}")
        click.echo(f"   状态: {result['state']}")
        if result.get('last_activity'):
            click.echo(f"   最后活动: {result['last_activity']}")
        if result.get('error_message'):
            click.echo(f"   错误信息: {result['error_message']}")
    
    try:
        asyncio.run(_status())
    except Exception as e:
        click.echo(f"❌ 获取渠道状态失败: {e}", err=True)


@channel.command()
@click.argument('channel_id')
@click.argument('content')
@click.option('--type', 'message_type', default='text', help='消息类型')
@click.option('--account', 'account_id', help='账户ID')
@click.pass_context
def send(ctx, channel_id, content, message_type, account_id):
    """向渠道发送消息"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _send():
        commands = create_channel_commands(channel_manager)
        result = await commands.send_message_to_channel(
            channel_id, content, message_type, account_id
        )
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_send())
    except Exception as e:
        click.echo(f"❌ 发送消息失败: {e}", err=True)


@channel.command()
@click.argument('channel_id')
@click.pass_context
def info(ctx, channel_id):
    """显示渠道详细信息"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _info():
        commands = create_channel_commands(channel_manager)
        result = await commands.get_channel_details(channel_id)
        
        if "error" in result:
            click.echo(f"❌ {result['error']}", err=True)
            return
        
        details = result
        click.echo(f"📡 渠道详情: {channel_id}")
        
        if details.get('config'):
            config = details['config']
            click.echo("   配置信息:")
            for key, value in config.items():
                click.echo(f"     {key}: {value}")
        
        if details.get('status'):
            status = details['status']
            click.echo("   状态信息:")
            click.echo(f"     连接状态: {status['connection_status']}")
            click.echo(f"     状态: {status['state']}")
            if status.get('last_activity'):
                click.echo(f"     最后活动: {status['last_activity']}")
            if status.get('error_message'):
                click.echo(f"     错误信息: {status['error_message']}")
        
        if details.get('adapter_info'):
            adapter = details['adapter_info']
            click.echo("   适配器信息:")
            click.echo(f"     类型: {adapter['type']}")
            click.echo(f"     有适配器: {adapter['has_adapter']}")
    
    try:
        asyncio.run(_info())
    except Exception as e:
        click.echo(f"❌ 获取渠道详情失败: {e}", err=True)


@channel.command()
@click.pass_context
def connect_all(ctx):
    """连接所有渠道"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _connect_all():
        commands = create_channel_commands(channel_manager)
        result = await commands.connect_all_channels()
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
            if result.get('status'):
                status = result['status']
                click.echo(f"   总渠道数: {status['total_channels']}")
                click.echo(f"   已连接: {status['connected_channels']}")
                click.echo(f"   未连接: {status['disconnected_channels']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_connect_all())
    except Exception as e:
        click.echo(f"❌ 连接所有渠道失败: {e}", err=True)


@channel.command()
@click.pass_context
def disconnect_all(ctx):
    """断开所有渠道"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _disconnect_all():
        commands = create_channel_commands(channel_manager)
        result = await commands.disconnect_all_channels()
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_disconnect_all())
    except Exception as e:
        click.echo(f"❌ 断开所有渠道失败: {e}", err=True)


@channel.command()
@click.option('--output', '-o', help='输出文件路径')
@click.option('--format', 'output_format', default='json', type=click.Choice(['json', 'yaml']), help='输出格式')
@click.pass_context
def export(ctx, output, output_format):
    """导出渠道配置"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _export():
        commands = create_channel_commands(channel_manager)
        
        # 设置输出文件路径
        if not output:
            timestamp = asyncio.get_event_loop().time()
            output = f"channels_config_{timestamp}.{output_format}"
        
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


@channel.command()
@click.argument('config_path', type=click.Path(exists=True))
@click.pass_context
def import_config(ctx, config_path):
    """导入渠道配置"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _import():
        commands = create_channel_commands(channel_manager)
        config_file = Path(config_path)
        result = await commands.import_config(config_file)
        
        if "error" in result:
            click.echo(f"❌ {result['error']}", err=True)
        else:
            click.echo(f"✅ 导入完成: {result['imported_count']}/{result['total_count']} 个渠道")
            if result.get('errors'):
                click.echo("⚠️ 部分渠道导入失败:")
                for error in result['errors']:
                    click.echo(f"   - {error}")
    
    try:
        asyncio.run(_import())
    except Exception as e:
        click.echo(f"❌ 导入配置失败: {e}", err=True)


@channel.command()
@click.pass_context
def stats(ctx):
    """显示渠道系统统计信息"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _stats():
        stats = channel_manager.get_statistics()
        
        click.echo("📊 渠道系统统计:")
        click.echo(f"   总渠道数: {stats['total_channels']}")
        click.echo(f"   活跃适配器: {stats['active_adapters']}")
        click.echo(f"   已连接渠道: {stats['connected_channels']}")
        click.echo(f"   运行状态: {'运行中' if stats['running'] else '已停止'}")
        click.echo(f"   配置文件: {stats['config_path']}")
    
    try:
        asyncio.run(_stats())
    except Exception as e:
        click.echo(f"❌ 获取统计信息失败: {e}", err=True)


@channel.command()
@click.argument('channel_id')
@click.option('--account', 'account_id', help='账户ID')
@click.pass_context
def test(ctx, channel_id, account_id):
    """测试渠道连接"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _test():
        commands = create_channel_commands(channel_manager)
        result = await commands.test_channel_connection(channel_id, account_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
            click.echo(f"   测试时间: {result['connection_time']}")
        else:
            click.echo(f"❌ {result['message']}")
            if result.get('error'):
                click.echo(f"   错误: {result['error']}", err=True)
    
    try:
        asyncio.run(_test())
    except Exception as e:
        click.echo(f"❌ 测试渠道连接失败: {e}", err=True)


@channel.command()
@click.argument('channel_id')
@click.option('--account', 'account_id', help='账户ID')
@click.pass_context
def restart(ctx, channel_id, account_id):
    """重启渠道"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _restart():
        commands = create_channel_commands(channel_manager)
        result = await commands.restart_channel(channel_id, account_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
            click.echo(f"   重启时间: {result['restart_time']}")
        else:
            click.echo(f"❌ {result['message']}")
            if result.get('error'):
                click.echo(f"   错误: {result['error']}", err=True)
    
    try:
        asyncio.run(_restart())
    except Exception as e:
        click.echo(f"❌ 重启渠道失败: {e}", err=True)


@channel.command()
@click.argument('channel_id')
@click.option('--account', 'account_id', help='账户ID')
@click.option('--limit', '-l', default=50, help='日志条数限制')
@click.option('--json-format', 'json_output', is_flag=True, help='JSON格式输出')
@click.pass_context
def logs(ctx, channel_id, account_id, limit, json_output):
    """获取渠道日志"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _logs():
        commands = create_channel_commands(channel_manager)
        result = await commands.get_channel_logs(channel_id, account_id, limit)
        
        if result['success']:
            if json_output:
                click.echo(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                click.echo(f"📜 渠道日志: {channel_id}")
                click.echo(f"   总计: {result['total']} 条")
                click.echo()
                
                for log in result['logs']:
                    icon = "ℹ️" if log['level'] == 'INFO' else "❌" if log['level'] == 'ERROR' else "⚠️"
                    click.echo(f"   {icon} {log['timestamp']} [{log['level']}] {log['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_logs())
    except Exception as e:
        click.echo(f"❌ 获取渠道日志失败: {e}", err=True)


@channel.command()
@click.argument('source_channel_id')
@click.argument('target_channel_id')
@click.option('--name', 'target_name', help='目标渠道名称')
@click.pass_context
def clone(ctx, source_channel_id, target_channel_id, target_name):
    """克隆渠道"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    async def _clone():
        commands = create_channel_commands(channel_manager)
        result = await commands.clone_channel(source_channel_id, target_channel_id, target_name)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
            click.echo(f"   源渠道: {result['source_channel_id']}")
            click.echo(f"   目标渠道: {result['target_channel_id']}")
            click.echo(f"   目标名称: {result['target_name']}")
        else:
            click.echo(f"❌ {result['message']}")
            if result.get('error'):
                click.echo(f"   错误: {result['error']}", err=True)
    
    try:
        asyncio.run(_clone())
    except Exception as e:
        click.echo(f"❌ 克隆渠道失败: {e}", err=True)


@channel.command()
@click.argument('channel_id')
@click.option('--name', help='更新渠道名称')
@click.option('--enabled/--disabled', default=None, help='启用/禁用渠道')
@click.option('--default-account', help='更新默认账户ID')
@click.pass_context
def update(ctx, channel_id, name, enabled, default_account):
    """更新渠道配置"""
    channel_manager = ctx.obj.get('channel_manager')
    if not channel_manager:
        click.echo("❌ 渠道管理器未初始化", err=True)
        return
    
    # 收集更新字段
    updates = {}
    if name:
        updates['name'] = name
    if enabled is not None:
        updates['enabled'] = enabled
    if default_account:
        updates['default_account_id'] = default_account
    
    if not updates:
        click.echo("❌ 请指定要更新的字段", err=True)
        return
    
    async def _update():
        commands = create_channel_commands(channel_manager)
        result = await commands.update_channel_config(channel_id, updates)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
            click.echo(f"   更新的字段: {', '.join(result['updated_fields'])}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_update())
    except Exception as e:
        click.echo(f"❌ 更新渠道配置失败: {e}", err=True)