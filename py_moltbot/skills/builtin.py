#!/usr/bin/env python3
"""
内置技能模块
Built-in Skills

包含系统内置的基础技能，用于测试和演示
"""

import asyncio
import math
from datetime import datetime
from typing import Dict, List, Optional, Any

from .base import BaseSkill, SkillType, SkillContext, SkillResult, SkillMetadata, SkillRegistry
from .memory import get_memory_store


class CalculatorSkill(BaseSkill):
    """计算器技能"""
    
    def _get_metadata(self):
        return SkillMetadata(
            name="calculator",
            version="1.0.0",
            description="简单计算器技能，支持基本数学运算",
            author="System",
            skill_type=SkillType.COMMAND
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行计算任务"""
        try:
            user_input = context.get_user_input()
            
            # 简单数学表达式解析
            # 这里只支持基本的数学运算
            allowed_chars = set('0123456789+-*/.() ')
            if not all(c in allowed_chars for c in user_input):
                return SkillResult.error("只允许使用数字和运算符 (+-*/.())")
            
            # 防止恶意代码执行
            if any(word in user_input.lower() for word in ['import', 'exec', 'eval', 'compile', '__']):
                return SkillResult.error("检测到可疑内容，不予执行")
            
            # 计算结果
            try:
                result = eval(user_input)
                if not isinstance(result, (int, float)):
                    return SkillResult.error("计算结果不是数字")
                
                # 存储计算记忆
                if hasattr(context, 'data') and 'memory_store' in context.data:
                    memory_store = context.data['memory_store']
                    await memory_store.store_memory(
                        content=f"计算记录：{user_input} = {result}",
                        tags={"calculator", "math"},
                        importance=1,
                        source="calculator_skill"
                    )
                
                return SkillResult.success(
                    f"计算结果：{user_input} = {result}",
                    metadata={"expression": user_input, "result": result}
                )
                
            except ZeroDivisionError:
                return SkillResult.error("除以零错误")
            except SyntaxError:
                return SkillResult.error("语法错误")
            except Exception as e:
                return SkillResult.error(f"计算错误：{str(e)}")
        
        except Exception as e:
            return SkillResult.error(f"处理错误：{str(e)}")


class MemorySearchSkill(BaseSkill):
    """记忆搜索技能"""
    
    def _get_metadata(self):
        return SkillMetadata(
            name="memory_search",
            version="1.0.0",
            description="搜索记忆系统中的内容",
            author="System",
            skill_type=SkillType.COMMAND
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行记忆搜索"""
        try:
            user_input = context.get_user_input()
            
            # 获取记忆存储
            if not hasattr(context, 'data') or 'memory_store' not in context.data:
                return SkillResult.error("记忆系统未初始化")
            
            memory_store = context.data['memory_store']
            
            # 解析搜索查询
            if user_input.startswith('标签:'):
                # 按标签搜索
                tag = user_input[3:].strip()
                memories = await memory_store.get_memories_by_tag(tag)
                
                if not memories:
                    return SkillResult.success(f"未找到标签为 '{tag}' 的记忆")
                
                results = [f"标签 '{tag}' 的记忆："]
                for memory in memories[:5]:  # 最多显示5条
                    results.append(f"- {memory.content[:100]}...")
                
                return SkillResult.success("\n".join(results))
            
            elif user_input.startswith('统计'):
                # 获取统计信息
                stats = await memory_store.get_stats()
                result = f"""
记忆系统统计：
- 总记忆数：{stats['total_memories']}
- 总访问次数：{stats['total_accesses']}
- 总标签数：{stats['total_tags']}
- 存储路径：{stats['storage_path']}
- 最后清理：{stats['last_cleanup']}
"""
                return SkillResult.success(result)
            
            else:
                # 关键词搜索
                keywords = user_input.split()
                from .memory import MemoryQuery
                
                query = MemoryQuery(
                    keywords=keywords,
                    limit=10
                )
                
                memories = await memory_store.query_memories(query)
                
                if not memories:
                    return SkillResult.success(f"未找到包含关键词 '{user_input}' 的记忆")
                
                results = [f"找到 {len(memories)} 条相关记忆："]
                for memory in memories:
                    results.append(f"- {memory.content[:100]}... (重要度: {memory.importance})")
                
                return SkillResult.success("\n".join(results))
        
        except Exception as e:
            return SkillResult.error(f"搜索错误：{str(e)}")


class ReminderSkill(BaseSkill):
    """提醒技能"""
    
    def _get_metadata(self):
        return SkillMetadata(
            name="reminder",
            version="1.0.0",
            description="设置和管理提醒",
            author="System",
            skill_type=SkillType.COMMAND
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行提醒任务"""
        try:
            user_input = context.get_user_input()
            
            # 获取记忆存储
            if not hasattr(context, 'data') or 'memory_store' not in context.data:
                return SkillResult.error("记忆系统未初始化")
            
            memory_store = context.data['memory_store']
            
            if user_input.startswith('添加:'):
                # 添加提醒
                reminder_text = user_input[3:].strip()
                
                await memory_store.store_memory(
                    content=f"提醒：{reminder_text}",
                    tags={"reminder", "todo"},
                    importance=3,
                    source="reminder_skill",
                    metadata={
                        "type": "reminder",
                        "created_by": context.user.username,
                        "platform": context.platform.value
                    }
                )
                
                return SkillResult.success(f"提醒已添加：{reminder_text}")
            
            elif user_input.startswith('列出'):
                # 列出所有提醒
                reminders = await memory_store.get_memories_by_tag("reminder")
                
                if not reminders:
                    return SkillResult.success("暂无提醒")
                
                results = ["当前提醒："]
                for i, reminder in enumerate(reminders[:10], 1):
                    results.append(f"{i}. {reminder.content}")
                
                return SkillResult.success("\n".join(results))
            
            elif user_input.startswith('完成:'):
                # 标记提醒为完成
                try:
                    reminder_id = user_input[3:].strip()
                    success = await memory_store.delete_memory(reminder_id)
                    if success:
                        return SkillResult.success(f"提醒已标记为完成")
                    else:
                        return SkillResult.error("找不到指定的提醒")
                except:
                    return SkillResult.error("无效的提醒ID")
            
            else:
                return SkillResult.error("请使用：添加:内容、列出 或 完成:ID")
        
        except Exception as e:
            return SkillResult.error(f"提醒错误：{str(e)}")


class SystemStatusSkill(BaseSkill):
    """系统状态技能"""
    
    def _get_metadata(self):
        return SkillMetadata(
            name="system_status",
            version="1.0.0",
            description="查看系统状态和统计信息",
            author="System",
            skill_type=SkillType.COMMAND
        )
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行系统状态查询"""
        try:
            from ..skills.manager import get_skill_manager
            
            skill_manager = await get_skill_manager()
            
            if context.get_user_input() == "技能":
                # 显示技能列表
                skills = skill_manager.list_skills()
                stats = skill_manager.get_stats()
                
                result = f"""
技能系统状态：
总技能数：{len(skills)}
运行中的技能：{len(stats['running_skills'])}
活跃调度：{stats['active_schedules']}
总执行次数：{stats['total_executions']}
成功执行：{stats['successful_executions']}
失败执行：{stats['failed_executions']}

技能列表：
"""
                for skill in skills:
                    status_icon = "✅" if skill['is_active'] else "❌"
                    scheduled_icon = "⏰" if skill['scheduled'] else ""
                    result += f"- {status_icon} {skill['name']} ({skill['type']}) {scheduled_icon}\n"
                
                return SkillResult.success(result)
            
            elif context.get_user_input() == "记忆":
                # 显示记忆统计
                if hasattr(context, 'data') and 'memory_store' in context.data:
                    memory_store = context.data['memory_store']
                    stats = await memory_store.get_stats()
                    
                    result = f"""
记忆系统状态：
总记忆数：{stats['total_memories']}
总访问次数：{stats['total_accesses']}
总标签数：{stats['total_tags']}
存储路径：{stats['storage_path']}
清理次数：{stats['cleanup_count']}
"""
                    return SkillResult.success(result)
                else:
                    return SkillResult.error("记忆系统未初始化")
            
            else:
                return SkillResult.error("请输入 '技能' 或 '记忆' 查看相应状态")
        
        except Exception as e:
            return SkillResult.error(f"系统状态错误：{str(e)}")


# 注册技能到系统中
def register_builtin_skills():
    """注册内置技能"""
    from .base import SkillRegistry
    
    # 注册所有内置技能
    SkillRegistry.register("calculator")(CalculatorSkill)
    SkillRegistry.register("memory_search")(MemorySearchSkill)
    SkillRegistry.register("reminder")(ReminderSkill)
    SkillRegistry.register("system_status")(SystemStatusSkill)
