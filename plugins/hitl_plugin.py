"""
HITL (Human-in-the-Loop) 插件实现

此模块实现了人在回路服务的插件版本，将原来的HITL服务重构为插件模式，
提供HITL审批流程、消息处理等功能通过插件API提供。

主要功能：
- HITL请求创建和管理
- HITL响应处理
- HITL状态管理
- HITL工具注册
- HITL钩子处理
- 消息通道集成
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import asdict
from enum import Enum

from ..plugins import AgentBusPlugin, PluginContext
from ..services.hitl import HITLService, HITLRequest, HITLResponse, HITLStatus, HITLPriority


class HITLPlugin(AgentBusPlugin):
    """
    HITL (Human-in-the-Loop) 插件类
    
    人在回路服务的插件实现，提供HITL相关功能，包括：
    - 创建和管理HITL请求
    - 处理HITL响应
    - HITL状态管理
    - HITL消息处理
    """
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        self.hitl_service = HITLService()
        self._request_handlers: Dict[str, Any] = {}
        
        # 绑定原始服务实例，确保兼容性
        self._original_service = self.hitl_service
    
    def get_info(self) -> Dict[str, Any]:
        """
        返回插件信息
        """
        return {
            'id': self.plugin_id,
            'name': 'HITL Plugin',
            'version': '1.0.0',
            'description': '人在回路 (Human-in-the-Loop) 服务插件，提供HITL审批流程、消息处理等功能',
            'author': 'AgentBus Team',
            'dependencies': [
                'hitl_service',
                'message_channel',
                'communication_map'
            ],
            'capabilities': [
                'hitl_request_management',
                'hitl_response_processing',
                'hitl_status_tracking',
                'hitl_message_handling',
                'hitl_timeout_management'
            ]
        }
    
    async def activate(self):
        """
        激活HITL插件
        """
        # 先调用父类方法
        result = await super().activate()
        if not result:
            return False
        
        # 启动HITL服务
        await self.hitl_service.start()
        
        # 注册HITL工具
        self._register_hitl_tools()
        
        # 注册HITL钩子
        self._register_hitl_hooks()
        
        # 注册HITL命令
        self._register_hitl_commands()
        
        self.context.logger.info(f"HITL plugin {self.plugin_id} activated successfully")
        return True
    
    async def deactivate(self):
        """
        停用HITL插件
        """
        # 先调用父类方法
        result = await super().deactivate()
        if not result:
            return False
        
        # 停止HITL服务
        await self.hitl_service.stop()
        
        self.context.logger.info(f"HITL plugin {self.plugin_id} deactivated")
        return True
    
    def _register_hitl_tools(self):
        """注册HITL工具"""
        
        # 创建HITL请求工具
        self.register_tool(
            name='create_hitl_request',
            description='创建人在回路请求',
            function=self.create_hitl_request_tool
        )
        
        # 提交HITL响应工具
        self.register_tool(
            name='submit_hitl_response',
            description='提交人在回路响应',
            function=self.submit_hitl_response_tool
        )
        
        # 获取HITL请求详情工具
        self.register_tool(
            name='get_hitl_request',
            description='获取HITL请求详情',
            function=self.get_hitl_request_tool
        )
        
        # 列出活跃HITL请求工具
        self.register_tool(
            name='list_active_hitl_requests',
            description='列出所有活跃的HITL请求',
            function=self.list_active_hitl_requests_tool
        )
        
        # 列出用户HITL请求工具
        self.register_tool(
            name='list_user_hitl_requests',
            description='列出指定用户的所有HITL请求',
            function=self.list_user_hitl_requests_tool
        )
        
        # 取消HITL请求工具
        self.register_tool(
            name='cancel_hitl_request',
            description='取消HITL请求',
            function=self.cancel_hitl_request_tool
        )
        
        # 获取HITL统计信息工具
        self.register_tool(
            name='get_hitl_statistics',
            description='获取HITL统计信息',
            function=self.get_hitl_statistics_tool
        )
        
        # 获取HITL服务状态工具
        self.register_tool(
            name='get_hitl_service_status',
            description='获取HITL服务状态',
            function=self.get_hitl_service_status_tool
        )
    
    def _register_hitl_hooks(self):
        """注册HITL钩子"""
        
        # HITL请求创建前钩子
        self.register_hook(
            event='hitl_request_before_create',
            handler=self.on_hitl_request_before_create,
            priority=10
        )
        
        # HITL请求创建后钩子
        self.register_hook(
            event='hitl_request_after_create',
            handler=self.on_hitl_request_after_create,
            priority=10
        )
        
        # HITL响应提交前钩子
        self.register_hook(
            event='hitl_response_before_submit',
            handler=self.on_hitl_response_before_submit,
            priority=10
        )
        
        # HITL响应提交后钩子
        self.register_hook(
            event='hitl_response_after_submit',
            handler=self.on_hitl_response_after_submit,
            priority=10
        )
        
        # HITL请求超时钩子
        self.register_hook(
            event='hitl_request_timeout',
            handler=self.on_hitl_request_timeout,
            priority=5
        )
        
        # HITL请求取消钩子
        self.register_hook(
            event='hitl_request_cancelled',
            handler=self.on_hitl_request_cancelled,
            priority=5
        )
        
        # HITL消息处理钩子
        self.register_hook(
            event='hitl_message_received',
            handler=self.on_hitl_message_received,
            priority=5
        )
    
    def _register_hitl_commands(self):
        """注册HITL命令"""
        
        # HITL状态查看命令
        self.register_command(
            command='/hitl-status',
            handler=self.handle_hitl_status_command,
            description='查看HITL服务状态'
        )
        
        # HITL请求列表命令
        self.register_command(
            command='/hitl-list',
            handler=self.handle_hitl_list_command,
            description='列出HITL请求'
        )
        
        # HITL取消命令
        self.register_command(
            command='/hitl-cancel',
            handler=self.handle_hitl_cancel_command,
            description='取消HITL请求'
        )
    
    # HITL工具实现
    
    async def create_hitl_request_tool(
        self,
        agent_id: str,
        title: str,
        description: str,
        context: Dict[str, Any] = None,
        priority: str = "medium",
        timeout_minutes: int = 30,
        assigned_to: str = None,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """创建HITL请求工具实现"""
        
        try:
            # 转换优先级枚举
            priority_enum = HITLPriority(priority.lower())
        except ValueError:
            raise ValueError(f"Invalid priority: {priority}. Must be one of {[p.value for p in HITLPriority]}")
        
        # 创建请求
        request_id = await self.hitl_service.create_hitl_request(
            agent_id=agent_id,
            title=title,
            description=description,
            context=context or {},
            priority=priority_enum,
            timeout_minutes=timeout_minutes,
            assigned_to=assigned_to,
            tags=set(tags) if tags else None
        )
        
        return {
            'success': True,
            'request_id': request_id,
            'message': f'HITL请求创建成功: {request_id}'
        }
    
    async def submit_hitl_response_tool(
        self,
        request_id: str,
        responder_id: str,
        content: str,
        is_final: bool = True,
        attachments: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """提交HITL响应工具实现"""
        
        success = await self.hitl_service.submit_hitl_response(
            request_id=request_id,
            responder_id=responder_id,
            content=content,
            is_final=is_final,
            attachments=attachments or []
        )
        
        if success:
            return {
                'success': True,
                'message': f'HITL响应提交成功: {request_id}'
            }
        else:
            return {
                'success': False,
                'message': f'HITL请求不存在或已关闭: {request_id}'
            }
    
    async def get_hitl_request_tool(self, request_id: str) -> Dict[str, Any]:
        """获取HITL请求详情工具实现"""
        
        request = await self.hitl_service.get_hitl_request(request_id)
        
        if request:
            return {
                'success': True,
                'request': asdict(request)
            }
        else:
            return {
                'success': False,
                'message': f'HITL请求不存在: {request_id}'
            }
    
    async def list_active_hitl_requests_tool(self) -> Dict[str, Any]:
        """列出活跃HITL请求工具实现"""
        
        requests = await self.hitl_service.list_active_requests()
        
        return {
            'success': True,
            'requests': [asdict(req) for req in requests],
            'count': len(requests)
        }
    
    async def list_user_hitl_requests_tool(self, user_id: str) -> Dict[str, Any]:
        """列出用户HITL请求工具实现"""
        
        requests = await self.hitl_service.list_user_requests(user_id)
        
        return {
            'success': True,
            'requests': [asdict(req) for req in requests],
            'count': len(requests),
            'user_id': user_id
        }
    
    async def cancel_hitl_request_tool(self, request_id: str, reason: str = None) -> Dict[str, Any]:
        """取消HITL请求工具实现"""
        
        success = await self.hitl_service.cancel_hitl_request(
            request_id=request_id,
            reason=reason
        )
        
        if success:
            return {
                'success': True,
                'message': f'HITL请求已取消: {request_id}'
            }
        else:
            return {
                'success': False,
                'message': f'HITL请求不存在或已关闭: {request_id}'
            }
    
    async def get_hitl_statistics_tool(self) -> Dict[str, Any]:
        """获取HITL统计信息工具实现"""
        
        stats = await self.hitl_service.get_hitl_statistics()
        
        return {
            'success': True,
            'statistics': stats
        }
    
    async def get_hitl_service_status_tool(self) -> Dict[str, Any]:
        """获取HITL服务状态工具实现"""
        
        return {
            'success': True,
            'status': 'active',
            'active_requests': len(self.hitl_service.active_requests),
            'total_requests': len(self.hitl_service.request_history),
            'plugin_id': self.plugin_id,
            'plugin_status': self.status.value
        }
    
    # HITL钩子处理实现
    
    async def on_hitl_request_before_create(self, agent_id: str, title: str, description: str, context: Dict[str, Any]):
        """HITL请求创建前钩子"""
        self.context.logger.info(f"HITL请求创建前: agent={agent_id}, title={title}")
        
        # 这里可以添加自定义逻辑，如权限检查、内容验证等
        # 如果需要阻止创建，可以抛出异常
        pass
    
    async def on_hitl_request_after_create(self, request: HITLRequest):
        """HITL请求创建后钩子"""
        self.context.logger.info(f"HITL请求创建后: {request.id} - {request.title}")
        
        # 这里可以添加后续处理逻辑，如发送通知、记录日志等
        # 触发其他相关事件
        await self._trigger_custom_event('hitl_request_created', {
            'request_id': request.id,
            'agent_id': request.agent_id,
            'title': request.title,
            'priority': request.priority.value
        })
    
    async def on_hitl_response_before_submit(self, request_id: str, responder_id: str, content: str):
        """HITL响应提交前钩子"""
        self.context.logger.info(f"HITL响应提交前: request={request_id}, responder={responder_id}")
        
        # 这里可以添加权限检查、内容验证等逻辑
        pass
    
    async def on_hitl_response_after_submit(self, request: HITLRequest, response: HITLResponse):
        """HITL响应提交后钩子"""
        self.context.logger.info(f"HITL响应提交后: {request.id} - {response.content[:100]}")
        
        # 触发响应提交事件
        await self._trigger_custom_event('hitl_response_submitted', {
            'request_id': request.id,
            'responder_id': response.responder_id,
            'content_length': len(response.content),
            'is_final': response.is_final
        })
    
    async def on_hitl_request_timeout(self, request: HITLRequest):
        """HITL请求超时钩子"""
        self.context.logger.warning(f"HITL请求超时: {request.id} - {request.title}")
        
        # 处理超时逻辑，如发送超时通知、重试机制等
        await self._trigger_custom_event('hitl_request_timed_out', {
            'request_id': request.id,
            'title': request.title,
            'timeout_minutes': request.timeout_minutes,
            'original_agent_id': request.agent_id
        })
    
    async def on_hitl_request_cancelled(self, request: HITLRequest, reason: str):
        """HITL请求取消钩子"""
        self.context.logger.info(f"HITL请求取消: {request.id} - 原因: {reason}")
        
        # 处理取消逻辑，如通知相关方、更新状态等
        await self._trigger_custom_event('hitl_request_cancelled', {
            'request_id': request.id,
            'title': request.title,
            'reason': reason,
            'cancelled_at': datetime.now().isoformat()
        })
    
    async def on_hitl_message_received(self, message_data: Dict[str, Any]):
        """HITL消息接收钩子"""
        self.context.logger.debug(f"HITL消息接收: {message_data.get('type', 'unknown')}")
        
        # 处理HITL相关消息
        message_type = message_data.get('type')
        
        if message_type == 'hitl_request':
            await self._handle_hitl_request_message(message_data)
        elif message_type == 'hitl_response':
            await self._handle_hitl_response_message(message_data)
        elif message_type == 'hitl_timeout':
            await self._handle_hitl_timeout_message(message_data)
    
    # HITL命令处理实现
    
    async def handle_hitl_status_command(self, args: str) -> str:
        """处理HITL状态命令"""
        stats = await self.hitl_service.get_hitl_statistics()
        
        status_info = {
            'plugin_id': self.plugin_id,
            'status': self.status.value,
            'statistics': stats,
            'tools': len(self.get_tools()),
            'hooks': sum(len(hooks) for hooks in self.get_hooks().values())
        }
        
        return f"HITL插件状态:\n{json.dumps(status_info, ensure_ascii=False, indent=2)}"
    
    async def handle_hitl_list_command(self, args: str) -> str:
        """处理HITL列表命令"""
        # 解析命令参数
        user_id = args.strip() if args.strip() else None
        
        if user_id:
            requests = await self.hitl_service.list_user_requests(user_id)
            title = f"用户 {user_id} 的HITL请求:"
        else:
            requests = await self.hitl_service.list_active_requests()
            title = "所有活跃的HITL请求:"
        
        if not requests:
            return f"{title}\n暂无请求"
        
        # 格式化输出
        lines = [title, ""]
        for req in requests:
            lines.append(f"ID: {req.id}")
            lines.append(f"标题: {req.title}")
            lines.append(f"状态: {req.status.value}")
            lines.append(f"优先级: {req.priority.value}")
            lines.append(f"创建时间: {req.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("-" * 40)
        
        return "\n".join(lines)
    
    async def handle_hitl_cancel_command(self, args: str) -> str:
        """处理HITL取消命令"""
        if not args.strip():
            return "用法: /hitl-cancel <request_id> [reason]"
        
        parts = args.strip().split(None, 1)
        request_id = parts[0]
        reason = parts[1] if len(parts) > 1 else "用户取消"
        
        success = await self.hitl_service.cancel_hitl_request(request_id, reason)
        
        if success:
            return f"HITL请求 {request_id} 已成功取消"
        else:
            return f"HITL请求 {request_id} 不存在或已关闭"
    
    # 辅助方法
    
    async def _trigger_custom_event(self, event_name: str, data: Dict[str, Any]):
        """触发自定义事件"""
        try:
            # 这里可以触发自定义事件，供其他插件监听
            # 或者与外部系统集成
            self.context.logger.debug(f"触发自定义事件: {event_name}")
        except Exception as e:
            self.context.logger.error(f"触发自定义事件失败: {e}")
    
    async def _handle_hitl_request_message(self, message_data: Dict[str, Any]):
        """处理HITL请求消息"""
        try:
            data = message_data.get('data', {})
            self.context.logger.info(f"收到HITL请求消息: {data.get('request_id')}")
            
            # 这里可以添加自定义处理逻辑
            # 例如：转发到特定渠道、记录日志等
        except Exception as e:
            self.context.logger.error(f"处理HITL请求消息失败: {e}")
    
    async def _handle_hitl_response_message(self, message_data: Dict[str, Any]):
        """处理HITL响应消息"""
        try:
            data = message_data.get('data', {})
            self.context.logger.info(f"收到HITL响应消息: {data.get('request_id')}")
            
            # 这里可以添加自定义处理逻辑
        except Exception as e:
            self.context.logger.error(f"处理HITL响应消息失败: {e}")
    
    async def _handle_hitl_timeout_message(self, message_data: Dict[str, Any]):
        """处理HITL超时消息"""
        try:
            data = message_data.get('data', {})
            self.context.logger.warning(f"收到HITL超时消息: {data.get('request_id')}")
            
            # 这里可以添加自定义处理逻辑
            # 例如：自动重试、通知管理员等
        except Exception as e:
            self.context.logger.error(f"处理HITL超时消息失败: {e}")
    
    # 兼容性方法 - 确保与原有HITL服务完全兼容
    
    def get_hitl_service(self) -> HITLService:
        """获取原始HITL服务实例，确保兼容性"""
        return self._original_service
    
    async def create_hitl_request(
        self,
        agent_id: str,
        title: str,
        description: str,
        context: Dict[str, Any] = None,
        priority: HITLPriority = HITLPriority.MEDIUM,
        timeout_minutes: int = 30,
        assigned_to: str = None,
        tags: Set[str] = None
    ) -> str:
        """兼容性方法：直接调用原始服务方法"""
        return await self._original_service.create_hitl_request(
            agent_id=agent_id,
            title=title,
            description=description,
            context=context,
            priority=priority,
            timeout_minutes=timeout_minutes,
            assigned_to=assigned_to,
            tags=tags
        )
    
    async def submit_hitl_response(
        self,
        request_id: str,
        responder_id: str,
        content: str,
        is_final: bool = True,
        attachments: List[Dict[str, Any]] = None
    ) -> bool:
        """兼容性方法：直接调用原始服务方法"""
        return await self._original_service.submit_hitl_response(
            request_id=request_id,
            responder_id=responder_id,
            content=content,
            is_final=is_final,
            attachments=attachments
        )
    
    async def get_hitl_request(self, request_id: str) -> Optional[HITLRequest]:
        """兼容性方法：直接调用原始服务方法"""
        return await self._original_service.get_hitl_request(request_id)
    
    async def list_active_requests(self) -> List[HITLRequest]:
        """兼容性方法：直接调用原始服务方法"""
        return await self._original_service.list_active_requests()
    
    async def list_user_requests(self, user_id: str) -> List[HITLRequest]:
        """兼容性方法：直接调用原始服务方法"""
        return await self._original_service.list_user_requests(user_id)
    
    async def cancel_hitl_request(self, request_id: str, reason: str = None) -> bool:
        """兼容性方法：直接调用原始服务方法"""
        return await self._original_service.cancel_hitl_request(request_id, reason)
    
    async def get_hitl_statistics(self) -> Dict[str, Any]:
        """兼容性方法：直接调用原始服务方法"""
        return await self._original_service.get_hitl_statistics()
    
    async def start(self):
        """兼容性方法：启动服务"""
        await self._original_service.start()
    
    async def stop(self):
        """兼容性方法：停止服务"""
        await self._original_service.stop()