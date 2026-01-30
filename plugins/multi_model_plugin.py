"""
多模型协调器插件
Multi-Model Coordinator Plugin

此插件提供完整的多模型协调功能，包括：
- AI模型的注册和管理
- 智能任务分发和协调
- 多模型结果融合
- 任务队列管理
- 实时统计和监控

插件提供的工具：
- submit_multi_model_task: 提交多模型任务
- register_model: 注册新的AI模型
- get_task_result: 获取任务结果
- list_models: 列出可用模型
- get_coordinator_stats: 获取协调器统计信息

插件钩子：
- multi_model_task_submitted: 任务提交时触发
- multi_model_task_completed: 任务完成时触发
- multi_model_task_failed: 任务失败时触发
- model_registered: 模型注册时触发
- model_unregistered: 模型注销时触发
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from enum import Enum
from dataclasses import asdict

from agentbus.plugins import AgentBusPlugin, PluginContext, PluginTool, PluginHook
from agentbus.services.multi_model_coordinator import (
    MultiModelCoordinator,
    ModelConfig,
    TaskRequest,
    TaskResult,
    TaskType,
    TaskPriority,
    ModelType,
    TaskStatus,
    ModelResult,
)


class MultiModelPlugin(AgentBusPlugin):
    """
    多模型协调器插件
    
    基于多模型协调器服务实现的完整插件，提供：
    - 完整的模型管理和任务协调功能
    - 通过工具接口暴露核心功能
    - 事件钩子系统
    - 实时状态监控
    """
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        
        # 初始化多模型协调器
        self.coordinator = MultiModelCoordinator()
        
        # 插件内部状态
        self.plugin_stats = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'models_registered': 0,
            'total_processing_time': 0.0,
            'total_cost': 0.0
        }
        
        # 任务监控
        self.monitored_tasks: Dict[str, float] = {}
        
        self.context.logger.info(f"MultiModelPlugin {plugin_id} initialized")
    
    def get_info(self) -> Dict[str, Any]:
        """
        返回插件信息
        """
        return {
            'id': self.plugin_id,
            'name': 'Multi-Model Coordinator Plugin',
            'version': '1.0.0',
            'description': '多模型协调器插件，提供AI模型的统一管理和任务协调功能',
            'author': 'AgentBus Team',
            'dependencies': [
                'agentbus.services.multi_model_coordinator'
            ],
            'capabilities': [
                'multi_model_coordination',
                'model_management', 
                'task_processing',
                'result_fusion',
                'real_time_monitoring'
            ],
            'config_schema': {
                'default_models': {
                    'type': 'list',
                    'description': '默认注册的模型列表',
                    'default': []
                },
                'fusion_strategy': {
                    'type': 'string',
                    'description': '默认融合策略',
                    'default': 'best',
                    'options': ['best', 'weighted', 'majority', 'ensemble']
                },
                'max_concurrent_tasks': {
                    'type': 'integer',
                    'description': '最大并发任务数',
                    'default': 10
                },
                'enable_monitoring': {
                    'type': 'boolean',
                    'description': '启用任务监控',
                    'default': True
                }
            }
        }
    
    async def activate(self):
        """
        激活插件
        """
        # 先调用父类方法
        await super().activate()
        
        # 初始化协调器
        success = await self.coordinator.initialize()
        if not success:
            raise RuntimeError("Failed to initialize multi-model coordinator")
        
        # 注册插件工具
        self._register_tools()
        
        # 注册插件钩子
        self._register_hooks()
        
        # 注册插件命令
        self._register_commands()
        
        # 更新统计信息
        self.plugin_stats['models_registered'] = len(self.coordinator.models)
        
        self.context.logger.info(f"MultiModelPlugin {self.plugin_id} activated successfully")
        return True
    
    async def deactivate(self):
        """
        停用插件
        """
        try:
            # 清理监控任务
            self.monitored_tasks.clear()
            
            # 关闭协调器
            await self.coordinator.shutdown()
            
            # 调用父类方法
            await super().deactivate()
            
            self.context.logger.info(f"MultiModelPlugin {self.plugin_id} deactivated")
            return True
            
        except Exception as e:
            self.context.logger.error(f"Failed to deactivate plugin {self.plugin_id}: {e}")
            return False
    
    def _register_tools(self):
        """注册插件工具"""
        
        # 提交多模型任务
        self.register_tool(
            name='submit_multi_model_task',
            description='提交多模型任务进行协调处理',
            function=self.submit_multi_model_task
        )
        
        # 注册模型
        self.register_tool(
            name='register_model',
            description='注册新的AI模型',
            function=self.register_model_tool
        )
        
        # 注销模型
        self.register_tool(
            name='unregister_model',
            description='注销AI模型',
            function=self.unregister_model_tool
        )
        
        # 获取任务结果
        self.register_tool(
            name='get_task_result',
            description='获取任务处理结果',
            function=self.get_task_result_tool
        )
        
        # 取消任务
        self.register_tool(
            name='cancel_task',
            description='取消正在处理的任务',
            function=self.cancel_task_tool
        )
        
        # 列出模型
        self.register_tool(
            name='list_models',
            description='列出所有可用的AI模型',
            function=self.list_models_tool
        )
        
        # 获取协调器统计
        self.register_tool(
            name='get_coordinator_stats',
            description='获取多模型协调器统计信息',
            function=self.get_coordinator_stats_tool
        )
        
        # 获取插件统计
        self.register_tool(
            name='get_plugin_stats',
            description='获取插件统计信息',
            function=self.get_plugin_stats_tool
        )
        
        # 准备提示词
        self.register_tool(
            name='prepare_prompt',
            description='为特定任务类型准备优化的提示词',
            function=self.prepare_prompt_tool
        )
        
        # 模型推荐
        self.register_tool(
            name='recommend_models',
            description='为特定任务推荐最适合的模型',
            function=self.recommend_models_tool
        )
    
    def _register_hooks(self):
        """注册插件钩子"""
        
        # 任务提交钩子
        self.register_hook(
            event='multi_model_task_submitted',
            handler=self.on_task_submitted,
            priority=10
        )
        
        # 任务完成钩子
        self.register_hook(
            event='multi_model_task_completed',
            handler=self.on_task_completed,
            priority=10
        )
        
        # 任务失败钩子
        self.register_hook(
            event='multi_model_task_failed',
            handler=self.on_task_failed,
            priority=10
        )
        
        # 模型注册钩子
        self.register_hook(
            event='model_registered',
            handler=self.on_model_registered,
            priority=5
        )
        
        # 模型注销钩子
        self.register_hook(
            event='model_unregistered',
            handler=self.on_model_unregistered,
            priority=5
        )
        
        # 系统钩子
        self.register_hook(
            event='plugin_activated',
            handler=self.on_plugin_activated,
            priority=1
        )
        
        self.register_hook(
            event='plugin_deactivated',
            handler=self.on_plugin_deactivated,
            priority=1
        )
    
    def _register_commands(self):
        """注册插件命令"""
        
        self.register_command(
            command='/models',
            handler=self.handle_models_command,
            description='显示所有注册的模型信息'
        )
        
        self.register_command(
            command='/tasks',
            handler=self.handle_tasks_command,
            description='显示当前正在处理的任务'
        )
        
        self.register_command(
            command='/stats',
            handler=self.handle_stats_command,
            description='显示插件和协调器统计信息'
        )
        
        self.register_command(
            command='/health',
            handler=self.handle_health_command,
            description='检查多模型协调器健康状态'
        )
    
    # 工具实现方法
    
    async def submit_multi_model_task(self, 
                                    task_type: str,
                                    content: str,
                                    priority: str = "normal",
                                    required_capabilities: List[str] = None,
                                    max_cost: float = None,
                                    max_time: int = None,
                                    preferred_models: List[str] = None,
                                    exclude_models: List[str] = None,
                                    context: Dict[str, Any] = None,
                                    metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        提交多模型任务
        
        Args:
            task_type: 任务类型 (text_generation, code_generation, question_answering等)
            content: 任务内容
            priority: 任务优先级 (low, normal, high, urgent)
            required_capabilities: 必需的能力列表
            max_cost: 最大成本限制
            max_time: 最大处理时间(秒)
            preferred_models: 首选模型列表
            exclude_models: 排除模型列表
            context: 任务上下文
            metadata: 任务元数据
            
        Returns:
            包含任务ID和提交状态的字典
        """
        try:
            # 转换枚举值
            task_enum = TaskType(task_type)
            priority_enum = TaskPriority(priority)
            
            # 创建任务请求
            task_request = TaskRequest(
                task_id=str(uuid.uuid4()),
                task_type=task_enum,
                content=content,
                context=context or {},
                priority=priority_enum,
                required_capabilities=required_capabilities or [],
                max_cost=max_cost,
                max_time=max_time,
                preferred_models=preferred_models or [],
                exclude_models=exclude_models or [],
                metadata=metadata or {}
            )
            
            # 提交任务
            task_id = await self.coordinator.submit_task(task_request)
            
            # 更新插件统计
            self.plugin_stats['tasks_submitted'] += 1
            
            # 添加监控
            if self.get_config('enable_monitoring', True):
                self.monitored_tasks[task_id] = datetime.now().timestamp()
            
            # 触发任务提交钩子
            await self._trigger_hook('multi_model_task_submitted', {
                'task_id': task_id,
                'task_type': task_type,
                'priority': priority,
                'content_length': len(content)
            })
            
            self.context.logger.info(f"Task submitted successfully: {task_id}")
            
            return {
                'success': True,
                'task_id': task_id,
                'message': f'任务已成功提交，任务ID: {task_id}',
                'estimated_models': len(self.coordinator.get_available_models(task_enum))
            }
            
        except ValueError as e:
            self.context.logger.error(f"Invalid task parameters: {e}")
            return {
                'success': False,
                'error': f'无效的任务参数: {str(e)}',
                'task_id': None
            }
        except Exception as e:
            self.context.logger.error(f"Failed to submit task: {e}")
            return {
                'success': False,
                'error': f'任务提交失败: {str(e)}',
                'task_id': None
            }
    
    def register_model_tool(self, 
                           model_id: str,
                           model_name: str,
                           model_type: str,
                           provider: str,
                           capabilities: List[str],
                           api_key: str = None,
                           base_url: str = None,
                           max_tokens: int = 4096,
                           temperature: float = 0.7,
                           cost_per_token: float = 0.0,
                           quality_score: float = 1.0,
                           rate_limit: int = 100) -> Dict[str, Any]:
        """
        注册AI模型
        
        Args:
            model_id: 模型唯一标识符
            model_name: 模型显示名称
            model_type: 模型类型
            provider: 提供者 (openai, anthropic, local等)
            capabilities: 模型能力列表
            api_key: API密钥
            base_url: 基础URL
            max_tokens: 最大token数
            temperature: 温度参数
            cost_per_token: 每token成本
            quality_score: 质量评分
            rate_limit: 速率限制
            
        Returns:
            注册结果
        """
        try:
            # 转换枚举
            model_enum = ModelType(model_type)
            capability_enums = [TaskType(cap) for cap in capabilities]
            
            # 创建模型配置
            model_config = ModelConfig(
                model_id=model_id,
                model_name=model_name,
                model_type=model_enum,
                provider=provider,
                api_key=api_key,
                base_url=base_url,
                max_tokens=max_tokens,
                temperature=temperature,
                rate_limit=rate_limit,
                capabilities=capability_enums,
                cost_per_token=cost_per_token,
                quality_score=quality_score
            )
            
            # 注册模型
            success = self.coordinator.register_model(model_config)
            
            if success:
                self.plugin_stats['models_registered'] += 1
                
                # 触发模型注册钩子
                asyncio.create_task(self._trigger_hook('model_registered', {
                    'model_id': model_id,
                    'model_name': model_name,
                    'provider': provider,
                    'capabilities': capabilities
                }))
                
                self.context.logger.info(f"Model registered successfully: {model_id}")
                
                return {
                    'success': True,
                    'model_id': model_id,
                    'message': f'模型 {model_name} ({model_id}) 注册成功'
                }
            else:
                return {
                    'success': False,
                    'model_id': model_id,
                    'error': '模型注册失败'
                }
                
        except ValueError as e:
            self.context.logger.error(f"Invalid model parameters: {e}")
            return {
                'success': False,
                'error': f'无效的模型参数: {str(e)}',
                'model_id': model_id
            }
        except Exception as e:
            self.context.logger.error(f"Failed to register model: {e}")
            return {
                'success': False,
                'error': f'模型注册失败: {str(e)}',
                'model_id': model_id
            }
    
    def unregister_model_tool(self, model_id: str) -> Dict[str, Any]:
        """
        注销AI模型
        
        Args:
            model_id: 模型标识符
            
        Returns:
            注销结果
        """
        try:
            success = self.coordinator.unregister_model(model_id)
            
            if success:
                self.plugin_stats['models_registered'] = max(0, self.plugin_stats['models_registered'] - 1)
                
                # 触发模型注销钩子
                asyncio.create_task(self._trigger_hook('model_unregistered', {
                    'model_id': model_id
                }))
                
                self.context.logger.info(f"Model unregistered: {model_id}")
                
                return {
                    'success': True,
                    'model_id': model_id,
                    'message': f'模型 {model_id} 注销成功'
                }
            else:
                return {
                    'success': False,
                    'model_id': model_id,
                    'error': '模型不存在或注销失败'
                }
                
        except Exception as e:
            self.context.logger.error(f"Failed to unregister model: {e}")
            return {
                'success': False,
                'error': f'模型注销失败: {str(e)}',
                'model_id': model_id
            }
    
    async def get_task_result_tool(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务结果
        
        Args:
            task_id: 任务标识符
            
        Returns:
            任务结果
        """
        try:
            result = await self.coordinator.get_task_result(task_id)
            
            if result:
                # 转换为可序列化的格式
                result_dict = {
                    'success': True,
                    'task_id': task_id,
                    'status': result.status.value,
                    'final_content': result.final_content,
                    'total_time': result.total_time,
                    'total_cost': result.total_cost,
                    'fusion_method': result.fusion_method,
                    'processing_log': result.processing_log,
                    'metadata': result.metadata
                }
                
                # 添加模型结果详情
                if result.model_results:
                    result_dict['model_results'] = [
                        {
                            'model_id': r.model_id,
                            'confidence': r.confidence,
                            'processing_time': r.processing_time,
                            'cost': r.cost,
                            'quality_score': r.quality_score,
                            'error': r.error
                        }
                        for r in result.model_results
                    ]
                
                return result_dict
            else:
                return {
                    'success': False,
                    'task_id': task_id,
                    'error': '任务不存在或尚未完成'
                }
                
        except Exception as e:
            self.context.logger.error(f"Failed to get task result: {e}")
            return {
                'success': False,
                'error': f'获取任务结果失败: {str(e)}',
                'task_id': task_id
            }
    
    async def cancel_task_tool(self, task_id: str) -> Dict[str, Any]:
        """
        取消任务
        
        Args:
            task_id: 任务标识符
            
        Returns:
            取消结果
        """
        try:
            success = await self.coordinator.cancel_task(task_id)
            
            if success:
                # 从监控列表中移除
                self.monitored_tasks.pop(task_id, None)
                
                self.context.logger.info(f"Task cancelled: {task_id}")
                
                return {
                    'success': True,
                    'task_id': task_id,
                    'message': f'任务 {task_id} 取消成功'
                }
            else:
                return {
                    'success': False,
                    'task_id': task_id,
                    'error': '任务不存在或取消失败'
                }
                
        except Exception as e:
            self.context.logger.error(f"Failed to cancel task: {e}")
            return {
                'success': False,
                'error': f'任务取消失败: {str(e)}',
                'task_id': task_id
            }
    
    def list_models_tool(self, task_type: str = None) -> Dict[str, Any]:
        """
        列出可用模型
        
        Args:
            task_type: 可选的任务类型过滤
            
        Returns:
            模型列表
        """
        try:
            if task_type:
                task_enum = TaskType(task_type)
                models = self.coordinator.get_available_models(task_enum)
            else:
                models = self.coordinator.get_available_models()
            
            model_list = []
            for model in models:
                model_list.append({
                    'model_id': model.model_id,
                    'model_name': model.model_name,
                    'model_type': model.model_type.value,
                    'provider': model.provider,
                    'capabilities': [cap.value for cap in model.capabilities],
                    'max_tokens': model.max_tokens,
                    'temperature': model.temperature,
                    'cost_per_token': model.cost_per_token,
                    'quality_score': model.quality_score,
                    'is_active': model.is_active,
                    'rate_limit': model.rate_limit
                })
            
            return {
                'success': True,
                'models': model_list,
                'total_count': len(model_list),
                'filtered_by': task_type
            }
            
        except ValueError as e:
            return {
                'success': False,
                'error': f'无效的任务类型: {str(e)}',
                'models': [],
                'total_count': 0
            }
        except Exception as e:
            self.context.logger.error(f"Failed to list models: {e}")
            return {
                'success': False,
                'error': f'获取模型列表失败: {str(e)}',
                'models': [],
                'total_count': 0
            }
    
    async def get_coordinator_stats_tool(self) -> Dict[str, Any]:
        """
        获取协调器统计信息
        
        Returns:
            统计信息
        """
        try:
            stats = await self.coordinator.get_coordinator_stats()
            
            # 添加监控的任务信息
            monitored_count = len(self.monitored_tasks)
            avg_monitor_time = 0.0
            if self.monitored_tasks:
                current_time = datetime.now().timestamp()
                monitor_times = [current_time - start_time for start_time in self.monitored_tasks.values()]
                avg_monitor_time = sum(monitor_times) / len(monitor_times)
            
            stats['plugin_stats'] = self.plugin_stats
            stats['monitored_tasks'] = monitored_count
            stats['avg_monitor_time'] = avg_monitor_time
            
            return {
                'success': True,
                'stats': stats
            }
            
        except Exception as e:
            self.context.logger.error(f"Failed to get coordinator stats: {e}")
            return {
                'success': False,
                'error': f'获取统计信息失败: {str(e)}'
            }
    
    def get_plugin_stats_tool(self) -> Dict[str, Any]:
        """
        获取插件统计信息
        
        Returns:
            插件统计信息
        """
        try:
            return {
                'success': True,
                'plugin_id': self.plugin_id,
                'status': self.status.value,
                'stats': self.plugin_stats.copy(),
                'monitored_tasks': len(self.monitored_tasks),
                'registered_tools': len(self.get_tools()),
                'registered_hooks': sum(len(hooks) for hooks in self.get_hooks().values()),
                'registered_commands': len(self.get_commands())
            }
            
        except Exception as e:
            self.context.logger.error(f"Failed to get plugin stats: {e}")
            return {
                'success': False,
                'error': f'获取插件统计失败: {str(e)}'
            }
    
    def prepare_prompt_tool(self, task_type: str, content: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        准备优化的提示词
        
        Args:
            task_type: 任务类型
            content: 原始内容
            context: 上下文信息
            
        Returns:
            优化后的提示词
        """
        try:
            task_enum = TaskType(task_type)
            
            # 创建临时任务请求来使用内置的提示词准备逻辑
            temp_task = TaskRequest(
                task_id="temp",
                task_type=task_enum,
                content=content,
                context=context or {}
            )
            
            # 使用协调器的方法准备提示词
            # 这里我们需要模拟一个模型配置
            from agentbus.services.multi_model_coordinator import ModelConfig, ModelType
            temp_model = ModelConfig(
                model_id="temp",
                model_name="Temp",
                model_type=ModelType.TEXT_GENERATION,
                provider="local"
            )
            
            prepared_prompt = self.coordinator._prepare_prompt(temp_task, temp_model)
            
            return {
                'success': True,
                'original_content': content,
                'prepared_prompt': prepared_prompt,
                'task_type': task_type,
                'optimization_applied': prepared_prompt != content
            }
            
        except Exception as e:
            self.context.logger.error(f"Failed to prepare prompt: {e}")
            return {
                'success': False,
                'error': f'提示词准备失败: {str(e)}'
            }
    
    def recommend_models_tool(self, task_type: str, max_models: int = 5) -> Dict[str, Any]:
        """
        为特定任务推荐模型
        
        Args:
            task_type: 任务类型
            max_models: 最大推荐数量
            
        Returns:
            推荐模型列表
        """
        try:
            task_enum = TaskType(task_type)
            available_models = self.coordinator.get_available_models(task_enum)
            
            # 按质量和成本排序
            recommended = sorted(
                available_models,
                key=lambda m: (m.quality_score, -m.cost_per_token),
                reverse=True
            )[:max_models]
            
            recommendations = []
            for model in recommended:
                recommendations.append({
                    'model_id': model.model_id,
                    'model_name': model.model_name,
                    'provider': model.provider,
                    'quality_score': model.quality_score,
                    'cost_per_token': model.cost_per_token,
                    'max_tokens': model.max_tokens,
                    'estimated_cost': model.cost_per_token * 1000,  # 估算1000 token的成本
                    'capabilities': [cap.value for cap in model.capabilities]
                })
            
            return {
                'success': True,
                'task_type': task_type,
                'recommended_models': recommendations,
                'total_available': len(available_models),
                'recommendation_count': len(recommendations)
            }
            
        except ValueError as e:
            return {
                'success': False,
                'error': f'无效的任务类型: {str(e)}',
                'recommended_models': []
            }
        except Exception as e:
            self.context.logger.error(f"Failed to recommend models: {e}")
            return {
                'success': False,
                'error': f'模型推荐失败: {str(e)}',
                'recommended_models': []
            }
    
    # 钩子处理方法
    
    async def on_task_submitted(self, task_data: Dict[str, Any]):
        """任务提交钩子处理"""
        self.context.logger.debug(f"Task submitted hook: {task_data.get('task_id')}")
        
        # 这里可以添加自定义逻辑，比如：
        # - 记录日志
        # - 发送通知
        # - 更新监控指标
        pass
    
    async def on_task_completed(self, task_data: Dict[str, Any]):
        """任务完成钩子处理"""
        task_id = task_data.get('task_id')
        self.context.logger.debug(f"Task completed hook: {task_id}")
        
        # 更新统计信息
        self.plugin_stats['tasks_completed'] += 1
        
        # 从监控列表中移除
        self.monitored_tasks.pop(task_id, None)
        
        # 这里可以添加自定义逻辑
        pass
    
    async def on_task_failed(self, task_data: Dict[str, Any]):
        """任务失败钩子处理"""
        task_id = task_data.get('task_id')
        self.context.logger.debug(f"Task failed hook: {task_id}")
        
        # 更新统计信息
        self.plugin_stats['tasks_failed'] += 1
        
        # 从监控列表中移除
        self.monitored_tasks.pop(task_id, None)
        
        # 这里可以添加自定义逻辑，比如发送告警
        pass
    
    async def on_model_registered(self, model_data: Dict[str, Any]):
        """模型注册钩子处理"""
        self.context.logger.debug(f"Model registered hook: {model_data.get('model_id')}")
        
        # 这里可以添加自定义逻辑
        pass
    
    async def on_model_unregistered(self, model_data: Dict[str, Any]):
        """模型注销钩子处理"""
        self.context.logger.debug(f"Model unregistered hook: {model_data.get('model_id')}")
        
        # 这里可以添加自定义逻辑
        pass
    
    async def on_plugin_activated(self, plugin_data: Dict[str, Any]):
        """插件激活钩子处理"""
        self.context.logger.info("MultiModelPlugin activated")
        
        # 这里可以添加自定义逻辑
        pass
    
    async def on_plugin_deactivated(self, plugin_data: Dict[str, Any]):
        """插件停用钩子处理"""
        self.context.logger.info("MultiModelPlugin deactivated")
        
        # 这里可以添加自定义逻辑
        pass
    
    # 命令处理方法
    
    async def handle_models_command(self, args: str) -> str:
        """处理模型列表命令"""
        try:
            task_type = args.strip() if args else None
            
            result = self.list_models_tool(task_type)
            
            if result['success']:
                models_info = []
                for model in result['models']:
                    status = "🟢" if model['is_active'] else "🔴"
                    models_info.append(
                        f"{status} {model['model_name']} ({model['model_id']}) - {model['provider']}"
                    )
                
                info_text = f"📊 模型列表 (总计: {result['total_count']})\n"
                if task_type:
                    info_text += f"过滤条件: {task_type}\n"
                info_text += "\n" + "\n".join(models_info)
                
                return info_text
            else:
                return f"❌ 获取模型列表失败: {result['error']}"
                
        except Exception as e:
            return f"❌ 命令执行失败: {str(e)}"
    
    async def handle_tasks_command(self, args: str) -> str:
        """处理任务列表命令"""
        try:
            # 获取协调器统计信息
            stats_result = await self.get_coordinator_stats_tool()
            
            if stats_result['success']:
                stats = stats_result['stats']
                
                tasks_info = f"📋 任务状态\n"
                tasks_info += f"活跃任务: {stats['active_tasks']}\n"
                tasks_info += f"总任务数: {stats['total_tasks']}\n"
                tasks_info += f"成功率: {stats['success_rate']:.1%}\n"
                tasks_info += f"监控任务: {stats['monitored_tasks']}\n"
                
                if stats['monitored_tasks'] > 0:
                    tasks_info += f"平均监控时间: {stats['avg_monitor_time']:.1f}秒\n"
                
                return tasks_info
            else:
                return f"❌ 获取任务状态失败: {stats_result['error']}"
                
        except Exception as e:
            return f"❌ 命令执行失败: {str(e)}"
    
    async def handle_stats_command(self, args: str) -> str:
        """处理统计信息命令"""
        try:
            plugin_stats = self.get_plugin_stats_tool()
            coordinator_stats = await self.get_coordinator_stats_tool()
            
            if plugin_stats['success'] and coordinator_stats['success']:
                stats = plugin_stats['stats']
                coord_stats = coordinator_stats['stats']
                
                stats_info = f"📈 统计信息\n\n"
                stats_info += f"插件统计:\n"
                stats_info += f"  提交任务: {stats['tasks_submitted']}\n"
                stats_info += f"  完成任务: {stats['tasks_completed']}\n"
                stats_info += f"  失败任务: {stats['tasks_failed']}\n"
                stats_info += f"  注册模型: {stats['models_registered']}\n"
                stats_info += f"  总处理时间: {stats['total_processing_time']:.1f}秒\n"
                stats_info += f"  总成本: ${stats['total_cost']:.6f}\n\n"
                
                stats_info += f"协调器统计:\n"
                stats_info += f"  活跃任务: {coord_stats['active_tasks']}\n"
                stats_info += f"  平均处理时间: {coord_stats['avg_processing_time']:.2f}秒\n"
                stats_info += f"  平均成本: ${coord_stats['avg_cost']:.6f}\n"
                stats_info += f"  活跃模型: {coord_stats['active_models']}\n"
                
                return stats_info
            else:
                return f"❌ 获取统计信息失败"
                
        except Exception as e:
            return f"❌ 命令执行失败: {str(e)}"
    
    async def handle_health_command(self, args: str) -> str:
        """处理健康检查命令"""
        try:
            # 检查协调器状态
            coordinator_stats = await self.get_coordinator_stats_tool()
            
            if coordinator_stats['success']:
                stats = coordinator_stats['stats']
                
                # 评估健康状态
                health_score = 100
                issues = []
                
                if stats['active_tasks'] > 20:
                    health_score -= 20
                    issues.append("活跃任务过多")
                
                if stats['success_rate'] < 0.8:
                    health_score -= 30
                    issues.append("任务成功率偏低")
                
                if stats['registered_models'] == 0:
                    health_score -= 50
                    issues.append("没有注册模型")
                
                if health_score >= 80:
                    status = "🟢 健康"
                elif health_score >= 60:
                    status = "🟡 警告"
                else:
                    status = "🔴 不健康"
                
                health_info = f"💊 健康检查\n"
                health_info += f"状态: {status} (分数: {health_score})\n"
                health_info += f"协调器状态: {'正常' if self.coordinator.is_running else '异常'}\n"
                health_info += f"注册模型: {stats['registered_models']}\n"
                health_info += f"活跃模型: {stats['active_models']}\n"
                
                if issues:
                    health_info += f"\n问题:\n" + "\n".join(f"  ⚠️ {issue}" for issue in issues)
                
                return health_info
            else:
                return f"❌ 健康检查失败: {coordinator_stats['error']}"
                
        except Exception as e:
            return f"❌ 命令执行失败: {str(e)}"
    
    async def _trigger_hook(self, event: str, data: Dict[str, Any]):
        """触发钩子"""
        try:
            hooks = self.get_hooks().get(event, [])
            for hook in hooks:
                if hook.async_func:
                    await hook.handler(data)
                else:
                    hook.handler(data)
        except Exception as e:
            self.context.logger.error(f"Failed to trigger hook {event}: {e}")