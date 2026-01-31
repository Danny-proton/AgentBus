"""
AgentBus示例技能插件

此插件展示了如何创建自定义技能插件，包括：
- 多种工具定义和使用
- 事件钩子处理
- 命令注册和执行
- 技能状态管理
- 异步任务处理

使用方法：
1. 插件激活后自动注册各种技能工具
2. 通过PluginManager获取工具调用
3. 支持事件钩子监听和处理
"""

import asyncio
import json
import logging
import random
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from plugins.core import AgentBusPlugin, PluginContext, PluginTool, PluginHook


class SkillLevel(Enum):
    """技能等级枚举"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class ExampleSkillPlugin(AgentBusPlugin):
    """
    示例技能插件
    
    展示如何创建各种类型的技能，包括数据处理、计算、文本处理等。
    """
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        self.skill_history = []
        self.active_tasks = {}
        self.skill_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'most_used_skill': None
        }
        
    def get_info(self) -> Dict[str, Any]:
        """返回插件信息"""
        return {
            'id': self.plugin_id,
            'name': 'Example Skill Plugin',
            'version': '1.0.0',
            'description': '示例技能插件，展示各种技能类型和功能',
            'author': 'AgentBus Team',
            'dependencies': [],
            'capabilities': [
                'data_processing',
                'text_manipulation',
                'mathematical_calculations',
                'random_generation',
                'time_operations',
                'async_tasks'
            ]
        }
    
    async def activate(self):
        """激活插件并注册工具和钩子"""
        await super().activate()
        
        # 注册工具
        self.register_tool('calculate', '执行数学计算', self.calculate)
        self.register_tool('generate_random', '生成随机数据', self.generate_random)
        self.register_tool('process_text', '处理文本数据', self.process_text)
        self.register_tool('manage_tasks', '管理异步任务', self.manage_tasks)
        self.register_tool('get_timestamp', '获取时间戳', self.get_timestamp)
        self.register_tool('data_validation', '数据验证', self.data_validation)
        self.register_tool('format_output', '格式化输出', self.format_output)
        self.register_tool('skill_stats', '获取技能统计', self.get_skill_stats)
        self.register_tool('clear_history', '清空历史记录', self.clear_history)
        
        # 注册钩子
        self.register_hook('message_received', self.on_message_received, 5)
        self.register_hook('task_completed', self.on_task_completed, 10)
        self.register_hook('error_occurred', self.on_error_occurred, 1)
        
        # 注册命令
        self.register_command('/calc', self.handle_calc_command, '数学计算命令')
        self.register_command('/random', self.handle_random_command, '生成随机数据命令')
        self.register_command('/text', self.handle_text_command, '文本处理命令')
        self.register_command('/stats', self.handle_stats_command, '显示技能统计')
        self.register_command('/tasks', self.handle_tasks_command, '管理任务命令')
        
        self.context.logger.info(f"Example skill plugin {self.plugin_id} activated")
    
    async def calculate(self, expression: str, precision: int = 2) -> SkillResult:
        """执行数学计算"""
        try:
            self.context.logger.info(f"Calculating: {expression}")
            
            # 安全的数学表达式评估
            # 这里使用简单的字符串处理，实际应用中应该使用更安全的计算库
            safe_operations = ['+', '-', '*', '/', '(', ')', '.']
            
            for char in expression:
                if not (char.isdigit() or char in safe_operations):
                    return SkillResult(
                        success=False,
                        message=f"不支持的操作符: {char}"
                    )
            
            # 执行计算
            result = eval(expression)
            formatted_result = round(result, precision)
            
            # 记录统计
            self.skill_stats['total_executions'] += 1
            self.skill_stats['successful_executions'] += 1
            
            # 添加到历史记录
            self.skill_history.append({
                'type': 'calculation',
                'input': expression,
                'output': formatted_result,
                'timestamp': datetime.now().isoformat()
            })
            
            return SkillResult(
                success=True,
                message=f"计算结果: {formatted_result}",
                data={'result': formatted_result, 'expression': expression}
            )
            
        except Exception as e:
            self.skill_stats['total_executions'] += 1
            self.skill_stats['failed_executions'] += 1
            
            self.context.logger.error(f"Calculation error: {e}")
            return SkillResult(
                success=False,
                message=f"计算错误: {str(e)}"
            )
    
    async def generate_random(self, data_type: str, count: int = 1, 
                           min_val: int = 1, max_val: int = 100) -> SkillResult:
        """生成随机数据"""
        try:
            self.context.logger.info(f"Generating {count} random {data_type} values")
            
            if count <= 0 or count > 1000:
                return SkillResult(
                    success=False,
                    message="数量必须在1-1000之间"
                )
            
            random_data = []
            
            if data_type.lower() == 'number':
                random_data = [random.randint(min_val, max_val) for _ in range(count)]
            elif data_type.lower() == 'float':
                random_data = [random.uniform(min_val, max_val) for _ in range(count)]
            elif data_type.lower() == 'string':
                chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
                random_data = [''.join(random.choices(chars, k=8)) for _ in range(count)]
            elif data_type.lower() == 'boolean':
                random_data = [random.choice([True, False]) for _ in range(count)]
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的数据类型: {data_type}"
                )
            
            # 记录统计
            self.skill_stats['total_executions'] += 1
            self.skill_stats['successful_executions'] += 1
            
            # 添加到历史记录
            self.skill_history.append({
                'type': 'random_generation',
                'input': {'data_type': data_type, 'count': count, 'range': [min_val, max_val]},
                'output': random_data,
                'timestamp': datetime.now().isoformat()
            })
            
            return SkillResult(
                success=True,
                message=f"生成了 {count} 个随机 {data_type} 数据",
                data={'data': random_data, 'type': data_type, 'count': count}
            )
            
        except Exception as e:
            self.skill_stats['total_executions'] += 1
            self.skill_stats['failed_executions'] += 1
            
            self.context.logger.error(f"Random generation error: {e}")
            return SkillResult(
                success=False,
                message=f"随机数据生成错误: {str(e)}"
            )
    
    async def process_text(self, text: str, operation: str) -> SkillResult:
        """处理文本数据"""
        try:
            self.context.logger.info(f"Processing text with operation: {operation}")
            
            if not text:
                return SkillResult(success=False, message="文本不能为空")
            
            result_text = ""
            
            if operation.lower() == 'uppercase':
                result_text = text.upper()
            elif operation.lower() == 'lowercase':
                result_text = text.lower()
            elif operation.lower() == 'title':
                result_text = text.title()
            elif operation.lower() == 'reverse':
                result_text = text[::-1]
            elif operation.lower() == 'words':
                words = text.split()
                result_text = f"共 {len(words)} 个词: {', '.join(words)}"
            elif operation.lower() == 'chars':
                result_text = f"共 {len(text)} 个字符"
            elif operation.lower() == 'palindrome':
                result_text = "是回文" if text.lower() == text.lower()[::-1] else "不是回文"
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {operation}"
                )
            
            # 记录统计
            self.skill_stats['total_executions'] += 1
            self.skill_stats['successful_executions'] += 1
            
            # 添加到历史记录
            self.skill_history.append({
                'type': 'text_processing',
                'input': text,
                'operation': operation,
                'output': result_text,
                'timestamp': datetime.now().isoformat()
            })
            
            return SkillResult(
                success=True,
                message=result_text,
                data={'original_text': text, 'operation': operation, 'processed_text': result_text}
            )
            
        except Exception as e:
            self.skill_stats['total_executions'] += 1
            self.skill_stats['failed_executions'] += 1
            
            self.context.logger.error(f"Text processing error: {e}")
            return SkillResult(
                success=False,
                message=f"文本处理错误: {str(e)}"
            )
    
    async def manage_tasks(self, action: str, task_id: str = None, 
                          task_data: Dict[str, Any] = None) -> SkillResult:
        """管理异步任务"""
        try:
            if action.lower() == 'create':
                if not task_id:
                    return SkillResult(success=False, message="任务ID不能为空")
                
                if task_id in self.active_tasks:
                    return SkillResult(success=False, message=f"任务 {task_id} 已存在")
                
                # 创建异步任务
                task_info = {
                    'id': task_id,
                    'data': task_data or {},
                    'status': 'running',
                    'created_at': datetime.now(),
                    'progress': 0
                }
                
                self.active_tasks[task_id] = task_info
                
                # 启动后台任务
                asyncio.create_task(self._execute_background_task(task_id, task_info))
                
                return SkillResult(
                    success=True,
                    message=f"任务 {task_id} 已创建",
                    data={'task_id': task_id, 'task_info': task_info}
                )
            
            elif action.lower() == 'status':
                if not task_id:
                    return SkillResult(success=False, message="任务ID不能为空")
                
                if task_id not in self.active_tasks:
                    return SkillResult(success=False, message=f"任务 {task_id} 不存在")
                
                task_info = self.active_tasks[task_id]
                return SkillResult(
                    success=True,
                    message=f"任务状态: {task_info['status']}",
                    data={'task_info': task_info}
                )
            
            elif action.lower() == 'cancel':
                if not task_id:
                    return SkillResult(success=False, message="任务ID不能为空")
                
                if task_id not in self.active_tasks:
                    return SkillResult(success=False, message=f"任务 {task_id} 不存在")
                
                del self.active_tasks[task_id]
                
                return SkillResult(
                    success=True,
                    message=f"任务 {task_id} 已取消"
                )
            
            elif action.lower() == 'list':
                task_list = []
                for tid, task_info in self.active_tasks.items():
                    task_list.append({
                        'id': tid,
                        'status': task_info['status'],
                        'progress': task_info['progress'],
                        'created_at': task_info['created_at'].isoformat()
                    })
                
                return SkillResult(
                    success=True,
                    message=f"共有 {len(task_list)} 个活跃任务",
                    data={'tasks': task_list}
                )
            
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}"
                )
                
        except Exception as e:
            self.context.logger.error(f"Task management error: {e}")
            return SkillResult(
                success=False,
                message=f"任务管理错误: {str(e)}"
            )
    
    async def _execute_background_task(self, task_id: str, task_info: Dict[str, Any]):
        """执行后台任务"""
        try:
            steps = task_info['data'].get('steps', 5)
            delay = task_info['data'].get('delay', 1)
            
            for step in range(steps):
                if task_id not in self.active_tasks:
                    break
                
                # 更新进度
                progress = (step + 1) / steps * 100
                self.active_tasks[task_id]['progress'] = progress
                
                self.context.logger.debug(f"Task {task_id} progress: {progress}%")
                
                # 等待一段时间
                await asyncio.sleep(delay)
            
            # 任务完成
            if task_id in self.active_tasks:
                self.active_tasks[task_id]['status'] = 'completed'
                self.active_tasks[task_id]['progress'] = 100
                
                # 触发任务完成事件
                await self.context.runtime.get('event_bus', lambda: None).emit(
                    'task_completed', 
                    {'task_id': task_id, 'task_info': self.active_tasks[task_id]}
                )
                
                self.context.logger.info(f"Task {task_id} completed")
            
        except Exception as e:
            if task_id in self.active_tasks:
                self.active_tasks[task_id]['status'] = 'failed'
                
                self.context.logger.error(f"Task {task_id} failed: {e}")
    
    async def get_timestamp(self, format_type: str = 'iso') -> SkillResult:
        """获取时间戳"""
        try:
            now = datetime.now()
            
            if format_type.lower() == 'iso':
                result = now.isoformat()
            elif format_type.lower() == 'unix':
                result = str(int(now.timestamp()))
            elif format_type.lower() == 'readable':
                result = now.strftime('%Y-%m-%d %H:%M:%S')
            elif format_type.lower() == 'date':
                result = now.strftime('%Y-%m-%d')
            elif format_type.lower() == 'time':
                result = now.strftime('%H:%M:%S')
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的格式类型: {format_type}"
                )
            
            # 记录统计
            self.skill_stats['total_executions'] += 1
            self.skill_stats['successful_executions'] += 1
            
            return SkillResult(
                success=True,
                message=f"当前时间戳: {result}",
                data={'timestamp': result, 'format': format_type}
            )
            
        except Exception as e:
            self.skill_stats['total_executions'] += 1
            self.skill_stats['failed_executions'] += 1
            
            self.context.logger.error(f"Timestamp error: {e}")
            return SkillResult(
                success=False,
                message=f"时间戳获取错误: {str(e)}"
            )
    
    async def data_validation(self, data: Any, validation_type: str) -> SkillResult:
        """数据验证"""
        try:
            if not data:
                return SkillResult(success=False, message="数据不能为空")
            
            is_valid = False
            message = ""
            
            if validation_type.lower() == 'number':
                try:
                    float(data)
                    is_valid = True
                    message = "是有效数字"
                except ValueError:
                    message = "不是有效数字"
            
            elif validation_type.lower() == 'email':
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                is_valid = bool(re.match(email_pattern, str(data)))
                message = "是有效邮箱" if is_valid else "不是有效邮箱"
            
            elif validation_type.lower() == 'url':
                import re
                url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
                is_valid = bool(re.match(url_pattern, str(data)))
                message = "是有效URL" if is_valid else "不是有效URL"
            
            elif validation_type.lower() == 'json':
                try:
                    json.loads(str(data))
                    is_valid = True
                    message = "是有效JSON"
                except json.JSONDecodeError:
                    message = "不是有效JSON"
            
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的验证类型: {validation_type}"
                )
            
            # 记录统计
            self.skill_stats['total_executions'] += 1
            self.skill_stats['successful_executions'] += 1
            
            return SkillResult(
                success=True,
                message=message,
                data={'is_valid': is_valid, 'data': data, 'validation_type': validation_type}
            )
            
        except Exception as e:
            self.skill_stats['total_executions'] += 1
            self.skill_stats['failed_executions'] += 1
            
            self.context.logger.error(f"Data validation error: {e}")
            return SkillResult(
                success=False,
                message=f"数据验证错误: {str(e)}"
            )
    
    async def format_output(self, data: Any, format_type: str) -> SkillResult:
        """格式化输出"""
        try:
            if not data:
                return SkillResult(success=False, message="数据不能为空")
            
            formatted = ""
            
            if format_type.lower() == 'json':
                try:
                    if isinstance(data, str):
                        data = json.loads(data)
                    formatted = json.dumps(data, indent=2, ensure_ascii=False)
                except json.JSONDecodeError as e:
                    return SkillResult(success=False, message=f"JSON格式化错误: {str(e)}")
            
            elif format_type.lower() == 'table':
                if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                    formatted = self._format_as_table(data)
                else:
                    return SkillResult(success=False, message="表格格式需要字典列表数据")
            
            elif format_type.lower() == 'list':
                if isinstance(data, list):
                    formatted = '\n'.join(f"- {item}" for item in data)
                else:
                    return SkillResult(success=False, message="列表格式需要列表数据")
            
            elif format_type.lower() == 'key_value':
                if isinstance(data, dict):
                    formatted = '\n'.join(f"{k}: {v}" for k, v in data.items())
                else:
                    return SkillResult(success=False, message="键值格式需要字典数据")
            
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的格式类型: {format_type}"
                )
            
            # 记录统计
            self.skill_stats['total_executions'] += 1
            self.skill_stats['successful_executions'] += 1
            
            return SkillResult(
                success=True,
                message="格式化完成",
                data={'formatted_output': formatted, 'format_type': format_type}
            )
            
        except Exception as e:
            self.skill_stats['total_executions'] += 1
            self.skill_stats['failed_executions'] += 1
            
            self.context.logger.error(f"Format output error: {e}")
            return SkillResult(
                success=False,
                message=f"格式化输出错误: {str(e)}"
            )
    
    def _format_as_table(self, data: List[Dict[str, Any]]) -> str:
        """将数据格式化为表格"""
        if not data:
            return "空数据"
        
        # 获取所有列名
        columns = set()
        for row in data:
            columns.update(row.keys())
        columns = sorted(columns)
        
        # 计算列宽
        col_widths = {col: len(col) for col in columns}
        for row in data:
            for col in columns:
                col_widths[col] = max(col_widths[col], len(str(row.get(col, ''))))
        
        # 构建表格
        lines = []
        
        # 表头
        header = ' | '.join(col.ljust(col_widths[col]) for col in columns)
        lines.append(header)
        lines.append('-+-'.join('-' * col_widths[col] for col in columns))
        
        # 数据行
        for row in data:
            row_str = ' | '.join(str(row.get(col, '')).ljust(col_widths[col]) for col in columns)
            lines.append(row_str)
        
        return '\n'.join(lines)
    
    async def get_skill_stats(self) -> SkillResult:
        """获取技能统计"""
        try:
            # 计算成功率
            total = self.skill_stats['total_executions']
            success_rate = (self.skill_stats['successful_executions'] / total * 100) if total > 0 else 0
            
            # 获取最常用技能
            skill_usage = {}
            for record in self.skill_history:
                skill_type = record['type']
                skill_usage[skill_type] = skill_usage.get(skill_type, 0) + 1
            
            most_used = max(skill_usage.items(), key=lambda x: x[1]) if skill_usage else None
            self.skill_stats['most_used_skill'] = most_used[0] if most_used else None
            
            stats = {
                **self.skill_stats,
                'success_rate': round(success_rate, 2),
                'history_count': len(self.skill_history),
                'active_tasks': len(self.active_tasks),
                'skill_usage': skill_usage
            }
            
            return SkillResult(
                success=True,
                message="技能统计信息",
                data={'stats': stats}
            )
            
        except Exception as e:
            self.context.logger.error(f"Stats error: {e}")
            return SkillResult(
                success=False,
                message=f"获取统计信息错误: {str(e)}"
            )
    
    async def clear_history(self) -> SkillResult:
        """清空历史记录"""
        try:
            self.skill_history.clear()
            self.skill_stats = {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'most_used_skill': None
            }
            
            return SkillResult(
                success=True,
                message="历史记录已清空"
            )
            
        except Exception as e:
            self.context.logger.error(f"Clear history error: {e}")
            return SkillResult(
                success=False,
                message=f"清空历史记录错误: {str(e)}"
            )
    
    # 事件钩子处理
    async def on_message_received(self, message: str, sender: str):
        """消息接收钩子"""
        try:
            self.context.logger.debug(f"Received message from {sender}: {message[:50]}...")
        except Exception as e:
            self.context.logger.error(f"Error handling message: {e}")
    
    async def on_task_completed(self, task_data: Dict[str, Any]):
        """任务完成钩子"""
        try:
            task_id = task_data.get('task_id')
            self.context.logger.info(f"Task {task_id} completed via hook")
        except Exception as e:
            self.context.logger.error(f"Error handling task completion: {e}")
    
    async def on_error_occurred(self, error_data: Dict[str, Any]):
        """错误发生钩子"""
        try:
            error_msg = error_data.get('message', 'Unknown error')
            self.context.logger.warning(f"Error occurred: {error_msg}")
        except Exception as e:
            self.context.logger.error(f"Error handling error event: {e}")
    
    # 命令处理
    async def handle_calc_command(self, args: str) -> str:
        """处理计算命令"""
        if not args:
            return "用法: /calc <数学表达式>"
        
        result = await self.calculate(args)
        return result.message
    
    async def handle_random_command(self, args: str) -> str:
        """处理随机命令"""
        if not args:
            return "用法: /random <数据类型> [数量] [最小值] [最大值]"
        
        parts = args.split()
        data_type = parts[0]
        count = int(parts[1]) if len(parts) > 1 else 1
        min_val = int(parts[2]) if len(parts) > 2 else 1
        max_val = int(parts[3]) if len(parts) > 3 else 100
        
        result = await self.generate_random(data_type, count, min_val, max_val)
        return result.message
    
    async def handle_text_command(self, args: str) -> str:
        """处理文本命令"""
        if not args:
            return "用法: /text <文本> <操作>"
        
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            return "用法: /text <文本> <操作>"
        
        text, operation = parts
        result = await self.process_text(text, operation)
        return result.message
    
    async def handle_stats_command(self, args: str) -> str:
        """处理统计命令"""
        result = await self.get_skill_stats()
        if result.success:
            stats = result.data['stats']
            return f"""技能统计:
- 总执行次数: {stats['total_executions']}
- 成功次数: {stats['successful_executions']}
- 失败次数: {stats['failed_executions']}
- 成功率: {stats['success_rate']}%
- 历史记录: {stats['history_count']}
- 活跃任务: {stats['active_tasks']}"""
        else:
            return f"获取统计失败: {result.message}"
    
    async def handle_tasks_command(self, args: str) -> str:
        """处理任务命令"""
        result = await self.manage_tasks('list')
        if result.success:
            tasks = result.data['tasks']
            if not tasks:
                return "没有活跃任务"
            
            task_list = []
            for task in tasks:
                task_list.append(f"- {task['id']}: {task['status']} ({task['progress']}%)")
            
            return f"活跃任务:\n" + "\n".join(task_list)
        else:
            return f"获取任务列表失败: {result.message}"