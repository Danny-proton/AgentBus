"""
任务调度CLI命令
Task Scheduler CLI Commands

基于Moltbot的cron CLI系统，提供完整的任务调度管理功能。
"""

import asyncio
import json
import click
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger

from agentbus.scheduler.task_manager import TaskManager, Task, TaskStatus, TaskPriority
from agentbus.scheduler.workflow import Workflow, WorkflowStep, WorkflowStepType
from agentbus.scheduler.cron_handler import CronHandler


class SchedulerCommands:
    """任务调度命令类"""
    
    def __init__(self, task_manager: Optional[TaskManager] = None, 
                 cron_handler: Optional[CronHandler] = None):
        self.task_manager = task_manager or TaskManager()
        self.cron_handler = cron_handler or CronHandler()
    
    async def add_task(self, name: str, command: str, cron_expression: str,
                      description: Optional[str] = None, 
                      priority: str = "normal",
                      timeout: Optional[int] = None,
                      retry_count: int = 0) -> Dict[str, Any]:
        """添加任务"""
        try:
            # 创建任务
            task = Task(
                name=name,
                command=command,
                cron_expression=cron_expression,
                description=description,
                priority=TaskPriority(priority),
                timeout=timeout,
                retry_count=retry_count,
                enabled=True
            )
            
            # 添加任务
            task_id = await self.task_manager.add_task(task)
            
            return {
                "success": True,
                "task_id": task_id,
                "message": f"任务 '{name}' 添加成功",
                "task": {
                    "id": task_id,
                    "name": name,
                    "command": command,
                    "cron": cron_expression,
                    "description": description,
                    "priority": priority
                }
            }
            
        except Exception as e:
            logger.error(f"添加任务失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def list_tasks(self, status_filter: Optional[str] = None,
                        format_type: str = "table") -> Dict[str, Any]:
        """列出任务"""
        try:
            # 获取所有任务
            tasks = await self.task_manager.get_all_tasks()
            
            # 过滤状态
            if status_filter:
                status_enum = TaskStatus(status_filter)
                tasks = [task for task in tasks if task.status == status_enum]
            
            # 格式化任务信息
            task_list = []
            for task in tasks:
                task_info = {
                    "id": task.task_id,
                    "name": task.name,
                    "command": task.command,
                    "cron": task.cron_expression,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "enabled": task.enabled,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                    "run_count": task.run_count,
                    "success_count": task.success_count,
                    "failure_count": task.failure_count,
                    "description": task.description or ""
                }
                task_list.append(task_info)
            
            # 按状态和名称排序
            status_order = {
                'pending': 0, 'running': 1, 'completed': 2, 
                'failed': 3, 'cancelled': 4, 'disabled': 5
            }
            task_list.sort(key=lambda x: (status_order.get(x['status'], 6), x['name']))
            
            return {
                "success": True,
                "total": len(task_list),
                "tasks": task_list,
                "format": format_type
            }
            
        except Exception as e:
            logger.error(f"列出任务失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_task_info(self, task_id: str) -> Dict[str, Any]:
        """获取任务详情"""
        try:
            task = await self.task_manager.get_task(task_id)
            
            if not task:
                return {
                    "success": False,
                    "error": f"任务 '{task_id}' 不存在"
                }
            
            # 获取任务日志
            logs = await self.task_manager.get_task_logs(task_id, limit=50)
            
            # 获取任务统计
            stats = await self.task_manager.get_task_stats(task_id)
            
            return {
                "success": True,
                "task": {
                    "id": task.task_id,
                    "name": task.name,
                    "command": task.command,
                    "cron": task.cron_expression,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "enabled": task.enabled,
                    "created_at": task.created_at.isoformat(),
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                    "last_result": task.last_result,
                    "timeout": task.timeout,
                    "retry_count": task.retry_count,
                    "run_count": task.run_count,
                    "success_count": task.success_count,
                    "failure_count": task.failure_count,
                    "description": task.description or ""
                },
                "statistics": stats,
                "recent_logs": logs[-10:] if logs else []  # 只返回最近10条日志
            }
            
        except Exception as e:
            logger.error(f"获取任务详情失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_task(self, task_id: str, **updates) -> Dict[str, Any]:
        """更新任务"""
        try:
            task = await self.task_manager.get_task(task_id)
            
            if not task:
                return {
                    "success": False,
                    "error": f"任务 '{task_id}' 不存在"
                }
            
            # 更新字段
            for field, value in updates.items():
                if hasattr(task, field):
                    if field == 'priority' and isinstance(value, str):
                        setattr(task, field, TaskPriority(value))
                    else:
                        setattr(task, field, value)
            
            # 保存更新
            success = await self.task_manager.update_task(task)
            
            if success:
                return {
                    "success": True,
                    "task_id": task_id,
                    "message": f"任务 '{task_id}' 更新成功",
                    "updates": list(updates.keys())
                }
            else:
                return {
                    "success": False,
                    "error": f"任务 '{task_id}' 更新失败"
                }
            
        except Exception as e:
            logger.error(f"更新任务失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_task(self, task_id: str) -> Dict[str, Any]:
        """删除任务"""
        try:
            success = await self.task_manager.delete_task(task_id)
            
            if success:
                return {
                    "success": True,
                    "task_id": task_id,
                    "message": f"任务 '{task_id}' 删除成功"
                }
            else:
                return {
                    "success": False,
                    "error": f"任务 '{task_id}' 删除失败，可能不存在"
                }
            
        except Exception as e:
            logger.error(f"删除任务失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def enable_task(self, task_id: str) -> Dict[str, Any]:
        """启用任务"""
        return await self.update_task(task_id, enabled=True)
    
    async def disable_task(self, task_id: str) -> Dict[str, Any]:
        """禁用任务"""
        return await self.update_task(task_id, enabled=False)
    
    async def run_task_now(self, task_id: str) -> Dict[str, Any]:
        """立即执行任务"""
        try:
            # 启动任务执行
            execution_id = await self.task_manager.run_task_now(task_id)
            
            return {
                "success": True,
                "execution_id": execution_id,
                "task_id": task_id,
                "message": f"任务 '{task_id}' 已开始执行",
                "execution_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"立即执行任务失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            task = await self.task_manager.get_task(task_id)
            
            if not task:
                return {
                    "success": False,
                    "error": f"任务 '{task_id}' 不存在"
                }
            
            # 获取当前执行状态
            execution_status = await self.task_manager.get_execution_status(task_id)
            
            return {
                "success": True,
                "task_id": task_id,
                "status": {
                    "task_status": task.status.value,
                    "enabled": task.enabled,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                    "current_execution": execution_status
                },
                "statistics": {
                    "total_runs": task.run_count,
                    "success_rate": (task.success_count / task.run_count * 100) if task.run_count > 0 else 0,
                    "success_count": task.success_count,
                    "failure_count": task.failure_count
                }
            }
            
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def pause_task(self, task_id: str) -> Dict[str, Any]:
        """暂停任务"""
        try:
            success = await self.task_manager.pause_task(task_id)
            
            if success:
                return {
                    "success": True,
                    "task_id": task_id,
                    "message": f"任务 '{task_id}' 已暂停"
                }
            else:
                return {
                    "success": False,
                    "error": f"任务 '{task_id}' 暂停失败"
                }
            
        except Exception as e:
            logger.error(f"暂停任务失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def resume_task(self, task_id: str) -> Dict[str, Any]:
        """恢复任务"""
        try:
            success = await self.task_manager.resume_task(task_id)
            
            if success:
                return {
                    "success": True,
                    "task_id": task_id,
                    "message": f"任务 '{task_id}' 已恢复"
                }
            else:
                return {
                    "success": False,
                    "error": f"任务 '{task_id}' 恢复失败"
                }
            
        except Exception as e:
            logger.error(f"恢复任务失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def cancel_running_task(self, task_id: str) -> Dict[str, Any]:
        """取消正在运行的任务"""
        try:
            success = await self.task_manager.cancel_task(task_id)
            
            if success:
                return {
                    "success": True,
                    "task_id": task_id,
                    "message": f"任务 '{task_id}' 取消成功"
                }
            else:
                return {
                    "success": False,
                    "error": f"任务 '{task_id}' 取消失败，可能未在运行"
                }
            
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_task_logs(self, task_id: str, limit: int = 50) -> Dict[str, Any]:
        """获取任务日志"""
        try:
            logs = await self.task_manager.get_task_logs(task_id, limit)
            
            if logs is None:
                return {
                    "success": False,
                    "error": f"任务 '{task_id}' 不存在"
                }
            
            return {
                "success": True,
                "task_id": task_id,
                "logs": logs,
                "total": len(logs)
            }
            
        except Exception as e:
            logger.error(f"获取任务日志失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def clear_task_logs(self, task_id: str) -> Dict[str, Any]:
        """清除任务日志"""
        try:
            success = await self.task_manager.clear_task_logs(task_id)
            
            if success:
                return {
                    "success": True,
                    "task_id": task_id,
                    "message": f"任务 '{task_id}' 日志已清除"
                }
            else:
                return {
                    "success": False,
                    "error": f"任务 '{task_id}' 日志清除失败"
                }
            
        except Exception as e:
            logger.error(f"清除任务日志失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def export_tasks(self, output_path: Path, format_type: str = "json") -> Dict[str, Any]:
        """导出任务配置"""
        try:
            # 获取所有任务
            tasks = await self.task_manager.get_all_tasks()
            
            # 构建导出数据
            export_data = {
                "version": "1.0",
                "export_time": datetime.now().isoformat(),
                "tasks": []
            }
            
            for task in tasks:
                task_data = {
                    "name": task.name,
                    "command": task.command,
                    "cron_expression": task.cron_expression,
                    "description": task.description,
                    "priority": task.priority.value,
                    "timeout": task.timeout,
                    "retry_count": task.retry_count,
                    "enabled": task.enabled,
                    "created_at": task.created_at.isoformat()
                }
                export_data["tasks"].append(task_data)
            
            # 保存到文件
            if format_type.lower() == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            else:
                return {"success": False, "error": f"不支持的格式: {format_type}"}
            
            return {
                "success": True,
                "output_path": str(output_path),
                "format": format_type,
                "task_count": len(tasks)
            }
            
        except Exception as e:
            logger.error(f"导出任务配置失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def import_tasks(self, config_path: Path, replace_existing: bool = False) -> Dict[str, Any]:
        """导入任务配置"""
        try:
            # 读取配置文件
            if config_path.suffix.lower() == ".json":
                with open(config_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
            else:
                return {"success": False, "error": f"不支持的配置文件格式: {config_path.suffix}"}
            
            imported_count = 0
            errors = []
            
            for task_data in import_data.get("tasks", []):
                try:
                    # 检查任务是否已存在
                    existing_task = await self.task_manager.get_task_by_name(task_data["name"])
                    
                    if existing_task:
                        if replace_existing:
                            # 更新现有任务
                            await self.update_task(existing_task.task_id, **task_data)
                            imported_count += 1
                        else:
                            errors.append(f"任务 '{task_data['name']}' 已存在")
                            continue
                    else:
                        # 创建新任务
                        task = Task(
                            name=task_data["name"],
                            command=task_data["command"],
                            cron_expression=task_data["cron_expression"],
                            description=task_data.get("description"),
                            priority=TaskPriority(task_data.get("priority", "normal")),
                            timeout=task_data.get("timeout"),
                            retry_count=task_data.get("retry_count", 0),
                            enabled=task_data.get("enabled", True)
                        )
                        
                        await self.task_manager.add_task(task)
                        imported_count += 1
                        
                except Exception as e:
                    errors.append(f"导入任务 '{task_data.get('name', 'unknown')}' 失败: {e}")
            
            result = {
                "success": True,
                "imported_count": imported_count,
                "total_count": len(import_data.get("tasks", [])),
                "source_file": str(config_path)
            }
            
            if errors:
                result["errors"] = errors
            
            return result
            
        except Exception as e:
            logger.error(f"导入任务配置失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        try:
            # 获取调度器统计
            stats = await self.task_manager.get_scheduler_stats()
            
            # 获取正在运行的任务
            running_tasks = await self.task_manager.get_tasks_by_status(TaskStatus.RUNNING)
            
            # 获取待执行的任务
            pending_tasks = await self.task_manager.get_tasks_by_status(TaskStatus.PENDING)
            
            return {
                "success": True,
                "scheduler": {
                    "status": "running" if stats.get('active', False) else "stopped",
                    "total_tasks": stats.get('total_tasks', 0),
                    "active_tasks": stats.get('active_tasks', 0),
                    "running_tasks": len(running_tasks),
                    "pending_tasks": len(pending_tasks),
                    "completed_tasks": stats.get('completed_tasks', 0),
                    "failed_tasks": stats.get('failed_tasks', 0)
                },
                "recent_activity": stats.get('recent_activity', []),
                "system_info": {
                    "uptime": stats.get('uptime', 0),
                    "last_restart": stats.get('last_restart'),
                    "memory_usage": stats.get('memory_usage'),
                    "cpu_usage": stats.get('cpu_usage')
                }
            }
            
        except Exception as e:
            logger.error(f"获取调度器状态失败: {e}")
            return {"success": False, "error": str(e)}


def create_scheduler_commands(task_manager: Optional[TaskManager] = None,
                            cron_handler: Optional[CronHandler] = None) -> SchedulerCommands:
    """创建调度命令实例"""
    return SchedulerCommands(task_manager, cron_handler)


# CLI命令组
@click.group()
def scheduler():
    """任务调度命令"""
    pass


@scheduler.command()
@click.argument('name')
@click.argument('command')
@click.argument('cron')
@click.option('--description', '-d', help='任务描述')
@click.option('--priority', '-p', default='normal', 
              type=click.Choice(['low', 'normal', 'high', 'critical']), help='任务优先级')
@click.option('--timeout', '-t', type=int, help='超时时间(秒)')
@click.option('--retry', '-r', default=0, help='重试次数')
@click.pass_context
def add(ctx, name, command, cron, description, priority, timeout, retry):
    """添加定时任务"""
    task_manager = ctx.obj.get('task_manager')
    
    async def _add():
        commands = create_scheduler_commands(task_manager)
        result = await commands.add_task(
            name=name,
            command=command,
            cron_expression=cron,
            description=description,
            priority=priority,
            timeout=timeout,
            retry_count=retry
        )
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
            click.echo(f"   任务ID: {result['task_id']}")
            click.echo(f"   Cron表达式: {cron}")
            click.echo(f"   优先级: {priority}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_add())
    except Exception as e:
        click.echo(f"❌ 添加任务失败: {e}", err=True)


@scheduler.command()
@click.option('--status', 'status_filter', 
              type=click.Choice(['pending', 'running', 'completed', 'failed', 'cancelled', 'disabled']),
              help='按状态过滤')
@click.option('--format', 'output_format', default='table', 
              type=click.Choice(['table', 'json']), help='输出格式')
@click.pass_context
def list(ctx, status_filter, output_format):
    """列出任务"""
    task_manager = ctx.obj.get('task_manager')
    
    async def _list():
        commands = create_scheduler_commands(task_manager)
        result = await commands.list_tasks(status_filter, output_format)
        
        if result['success']:
            if output_format == 'json':
                click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            else:
                click.echo(f"📋 任务列表 (总计: {result['total']})")
                if status_filter:
                    click.echo(f"   状态过滤: {status_filter}")
                click.echo()
                
                for task in result['tasks']:
                    status_icons = {
                        'pending': '⏳',
                        'running': '🔄',
                        'completed': '✅',
                        'failed': '❌',
                        'cancelled': '🚫',
                        'disabled': '⏸️'
                    }
                    
                    icon = status_icons.get(task['status'], '❓')
                    enabled_status = "启用" if task['enabled'] else "禁用"
                    
                    click.echo(f"   {icon} [{task['id']}] {task['name']}")
                    click.echo(f"      命令: {task['command']}")
                    click.echo(f"      状态: {task['status']} ({enabled_status})")
                    click.echo(f"      Cron: {task['cron']}")
                    if task['next_run']:
                        click.echo(f"      下次运行: {task['next_run']}")
                    click.echo()
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_list())
    except Exception as e:
        click.echo(f"❌ 列出任务失败: {e}", err=True)


@scheduler.command()
@click.argument('task_id')
@click.pass_context
def info(ctx, task_id):
    """显示任务详情"""
    task_manager = ctx.obj.get('task_manager')
    
    async def _info():
        commands = create_scheduler_commands(task_manager)
        result = await commands.get_task_info(task_id)
        
        if result['success']:
            task = result['task']
            click.echo(f"📋 任务详情: {task['name']}")
            click.echo(f"   ID: {task['id']}")
            click.echo(f"   命令: {task['command']}")
            click.echo(f"   Cron: {task['cron']}")
            click.echo(f"   状态: {task['status']}")
            click.echo(f"   优先级: {task['priority']}")
            click.echo(f"   启用状态: {'启用' if task['enabled'] else '禁用'}")
            
            if task['description']:
                click.echo(f"   描述: {task['description']}")
            
            if task['last_run']:
                click.echo(f"   最后运行: {task['last_run']}")
            
            if task['next_run']:
                click.echo(f"   下次运行: {task['next_run']}")
            
            # 统计信息
            stats = result['statistics']
            click.echo(f"   统计:")
            click.echo(f"     总执行次数: {task['run_count']}")
            click.echo(f"     成功次数: {task['success_count']}")
            click.echo(f"     失败次数: {task['failure_count']}")
            click.echo(f"     成功率: {stats.get('success_rate', 0):.1f}%")
            
            # 最近日志
            if result['recent_logs']:
                click.echo(f"   最近日志:")
                for log in result['recent_logs']:
                    click.echo(f"     {log['timestamp']}: {log['level']} - {log['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_info())
    except Exception as e:
        click.echo(f"❌ 获取任务详情失败: {e}", err=True)


@scheduler.command()
@click.argument('task_id')
@click.option('--command', help='更新命令')
@click.option('--cron', help='更新Cron表达式')
@click.option('--description', help='更新描述')
@click.option('--priority', type=click.Choice(['low', 'normal', 'high', 'critical']), help='更新优先级')
@click.option('--timeout', type=int, help='更新超时时间')
@click.option('--retry', type=int, help='更新重试次数')
@click.pass_context
def update(ctx, task_id, command, cron, description, priority, timeout, retry):
    """更新任务"""
    task_manager = ctx.obj.get('task_manager')
    
    # 收集更新字段
    updates = {}
    if command:
        updates['command'] = command
    if cron:
        updates['cron_expression'] = cron
    if description:
        updates['description'] = description
    if priority:
        updates['priority'] = priority
    if timeout is not None:
        updates['timeout'] = timeout
    if retry is not None:
        updates['retry_count'] = retry
    
    if not updates:
        click.echo("❌ 请指定要更新的字段", err=True)
        return
    
    async def _update():
        commands = create_scheduler_commands(task_manager)
        result = await commands.update_task(task_id, **updates)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
            click.echo(f"   更新的字段: {', '.join(result['updates'])}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_update())
    except Exception as e:
        click.echo(f"❌ 更新任务失败: {e}", err=True)


@scheduler.command()
@click.argument('task_id')
@click.pass_context
def delete(ctx, task_id):
    """删除任务"""
    task_manager = ctx.obj.get('task_manager')
    
    if not click.confirm(f"⚠️ 确认删除任务 '{task_id}'？此操作不可撤销！"):
        click.echo("操作已取消")
        return
    
    async def _delete():
        commands = create_scheduler_commands(task_manager)
        result = await commands.delete_task(task_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_delete())
    except Exception as e:
        click.echo(f"❌ 删除任务失败: {e}", err=True)


@scheduler.command()
@click.argument('task_id')
@click.pass_context
def enable(ctx, task_id):
    """启用任务"""
    task_manager = ctx.obj.get('task_manager')
    
    async def _enable():
        commands = create_scheduler_commands(task_manager)
        result = await commands.enable_task(task_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_enable())
    except Exception as e:
        click.echo(f"❌ 启用任务失败: {e}", err=True)


@scheduler.command()
@click.argument('task_id')
@click.pass_context
def disable(ctx, task_id):
    """禁用任务"""
    task_manager = ctx.obj.get('task_manager')
    
    async def _disable():
        commands = create_scheduler_commands(task_manager)
        result = await commands.disable_task(task_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_disable())
    except Exception as e:
        click.echo(f"❌ 禁用任务失败: {e}", err=True)


@scheduler.command()
@click.argument('task_id')
@click.pass_context
def run_now(ctx, task_id):
    """立即执行任务"""
    task_manager = ctx.obj.get('task_manager')
    
    async def _run_now():
        commands = create_scheduler_commands(task_manager)
        result = await commands.run_task_now(task_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
            click.echo(f"   执行ID: {result['execution_id']}")
            click.echo(f"   执行时间: {result['execution_time']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_run_now())
    except Exception as e:
        click.echo(f"❌ 立即执行任务失败: {e}", err=True)


@scheduler.command()
@click.argument('task_id')
@click.pass_context
def status(ctx, task_id):
    """查看任务状态"""
    task_manager = ctx.obj.get('task_manager')
    
    async def _status():
        commands = create_scheduler_commands(task_manager)
        result = await commands.get_task_status(task_id)
        
        if result['success']:
            status_info = result['status']
            stats = result['statistics']
            
            click.echo(f"📊 任务状态: {task_id}")
            click.echo(f"   任务状态: {status_info['task_status']}")
            click.echo(f"   启用状态: {'启用' if status_info['enabled'] else '禁用'}")
            
            if status_info['last_run']:
                click.echo(f"   最后运行: {status_info['last_run']}")
            
            if status_info['next_run']:
                click.echo(f"   下次运行: {status_info['next_run']}")
            
            # 当前执行状态
            if status_info['current_execution']:
                exec_info = status_info['current_execution']
                click.echo(f"   当前执行:")
                click.echo(f"     状态: {exec_info.get('status', 'unknown')}")
                click.echo(f"     开始时间: {exec_info.get('start_time', 'unknown')}")
                if exec_info.get('progress'):
                    click.echo(f"     进度: {exec_info['progress']}%")
            
            # 统计信息
            click.echo(f"   统计信息:")
            click.echo(f"     总运行次数: {stats['total_runs']}")
            click.echo(f"     成功次数: {stats['success_count']}")
            click.echo(f"     失败次数: {stats['failure_count']}")
            click.echo(f"     成功率: {stats['success_rate']:.1f}%")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_status())
    except Exception as e:
        click.echo(f"❌ 获取任务状态失败: {e}", err=True)


@scheduler.command()
@click.argument('task_id')
@click.pass_context
def pause(ctx, task_id):
    """暂停任务"""
    task_manager = ctx.obj.get('task_manager')
    
    async def _pause():
        commands = create_scheduler_commands(task_manager)
        result = await commands.pause_task(task_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_pause())
    except Exception as e:
        click.echo(f"❌ 暂停任务失败: {e}", err=True)


@scheduler.command()
@click.argument('task_id')
@click.pass_context
def resume(ctx, task_id):
    """恢复任务"""
    task_manager = ctx.obj.get('task_manager')
    
    async def _resume():
        commands = create_scheduler_commands(task_manager)
        result = await commands.resume_task(task_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_resume())
    except Exception as e:
        click.echo(f"❌ 恢复任务失败: {e}", err=True)


@scheduler.command()
@click.argument('task_id')
@click.pass_context
def cancel(ctx, task_id):
    """取消正在运行的任务"""
    task_manager = ctx.obj.get('task_manager')
    
    if not click.confirm(f"⚠️ 确认取消正在运行的任务 '{task_id}'？"):
        click.echo("操作已取消")
        return
    
    async def _cancel():
        commands = create_scheduler_commands(task_manager)
        result = await commands.cancel_running_task(task_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_cancel())
    except Exception as e:
        click.echo(f"❌ 取消任务失败: {e}", err=True)


@scheduler.command()
@click.argument('task_id')
@click.option('--limit', '-l', default=50, help='日志条数限制')
@click.option('--json-format', 'json_output', is_flag=True, help='JSON格式输出')
@click.pass_context
def logs(ctx, task_id, limit, json_output):
    """获取任务日志"""
    task_manager = ctx.obj.get('task_manager')
    
    async def _logs():
        commands = create_scheduler_commands(task_manager)
        result = await commands.get_task_logs(task_id, limit)
        
        if result['success']:
            if json_output:
                click.echo(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            else:
                click.echo(f"📜 任务日志: {task_id}")
                click.echo(f"   总计: {result['total']} 条")
                click.echo()
                
                for log in result['logs']:
                    click.echo(f"   {log['timestamp']} [{log['level']}] {log['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_logs())
    except Exception as e:
        click.echo(f"❌ 获取任务日志失败: {e}", err=True)


@scheduler.command()
@click.argument('task_id')
@click.pass_context
def clear_logs(ctx, task_id):
    """清除任务日志"""
    task_manager = ctx.obj.get('task_manager')
    
    if not click.confirm(f"⚠️ 确认清除任务 '{task_id}' 的所有日志？此操作不可撤销！"):
        click.echo("操作已取消")
        return
    
    async def _clear_logs():
        commands = create_scheduler_commands(task_manager)
        result = await commands.clear_task_logs(task_id)
        
        if result['success']:
            click.echo(f"✅ {result['message']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_clear_logs())
    except Exception as e:
        click.echo(f"❌ 清除任务日志失败: {e}", err=True)


@scheduler.command()
@click.option('--output', '-o', help='输出文件路径')
@click.option('--format', 'output_format', default='json', type=click.Choice(['json']), help='输出格式')
@click.pass_context
def export(ctx, output, output_format):
    """导出任务配置"""
    task_manager = ctx.obj.get('task_manager')
    
    async def _export():
        commands = create_scheduler_commands(task_manager)
        
        # 设置输出文件路径
        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"tasks_export_{timestamp}.{output_format}"
        
        output_path = Path(output)
        result = await commands.export_tasks(output_path, output_format)
        
        if result['success']:
            click.echo(f"✅ 任务配置导出成功")
            click.echo(f"   文件: {result['output_path']}")
            click.echo(f"   任务数: {result['task_count']}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_export())
    except Exception as e:
        click.echo(f"❌ 导出任务配置失败: {e}", err=True)


@scheduler.command()
@click.argument('config_path', type=click.Path(exists=True))
@click.option('--replace', 'replace_existing', is_flag=True, help='替换已存在的任务')
@click.pass_context
def import_config(ctx, config_path, replace_existing):
    """导入任务配置"""
    task_manager = ctx.obj.get('task_manager')
    
    async def _import():
        commands = create_scheduler_commands(task_manager)
        config_file = Path(config_path)
        result = await commands.import_tasks(configisting)
        
        if result['success']:
            click.e_file, replace_excho(f"✅ 任务配置导入完成")
            click.echo(f"   文件: {result['source_file']}")
            click.echo(f"   导入: {result['imported_count']}/{result['total_count']} 个任务")
            if result.get('errors'):
                click.echo("⚠️ 部分任务导入失败:")
                for error in result['errors']:
                    click.echo(f"   - {error}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_import())
    except Exception as e:
        click.echo(f"❌ 导入任务配置失败: {e}", err=True)


@scheduler.command()
@click.pass_context
def status(ctx):
    """查看调度器状态"""
    task_manager = ctx.obj.get('task_manager')
    
    async def _status():
        commands = create_scheduler_commands(task_manager)
        result = await commands.get_scheduler_status()
        
        if result['success']:
            scheduler_info = result['scheduler']
            system_info = result.get('system_info', {})
            
            click.echo(f"⚙️ 调度器状态")
            click.echo(f"   状态: {'🟢 运行中' if scheduler_info['status'] == 'running' else '🔴 已停止'}")
            click.echo(f"   总任务数: {scheduler_info['total_tasks']}")
            click.echo(f"   活跃任务: {scheduler_info['active_tasks']}")
            click.echo(f"   运行中任务: {scheduler_info['running_tasks']}")
            click.echo(f"   待执行任务: {scheduler_info['pending_tasks']}")
            click.echo(f"   已完成任务: {scheduler_info['completed_tasks']}")
            click.echo(f"   失败任务: {scheduler_info['failed_tasks']}")
            
            if system_info.get('uptime'):
                click.echo(f"   运行时间: {system_info['uptime']:.2f} 秒")
            
            if result.get('recent_activity'):
                click.echo(f"   最近活动:")
                for activity in result['recent_activity'][-5:]:  # 只显示最近5条
                    click.echo(f"     {activity}")
        else:
            click.echo(f"❌ {result['error']}", err=True)
    
    try:
        asyncio.run(_status())
    except Exception as e:
        click.echo(f"❌ 获取调度器状态失败: {e}", err=True)