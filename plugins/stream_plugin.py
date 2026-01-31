"""
AgentBus流式响应处理插件

此模块实现了流式响应处理的插件化版本，将原有的流式响应处理服务
重构为插件模式，提供更好的可扩展性和模块化。

功能包括：
- WebSocket流式处理
- HTTP Server-Sent Events流式处理
- 流式事件管理和钩子
- 流式工具注册
- 统计和监控功能
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable, Union
from enum import Enum

from .core import AgentBusPlugin, PluginContext, PluginTool, PluginHook, PluginResult
from services.stream_response import (
    StreamResponseProcessor,
    StreamRequest,
    StreamChunk,
    StreamEventType,
    StreamStatus,
    StreamHandler,
    WebSocketStreamHandler,
    HTTPStreamHandler,
)


class StreamEvent(Enum):
    """流事件类型枚举"""
    STREAM_CREATED = "stream_created"
    STREAM_STARTED = "stream_started"
    STREAM_COMPLETED = "stream_completed"
    STREAM_CANCELLED = "stream_cancelled"
    STREAM_ERROR = "stream_error"
    CHUNK_SENT = "chunk_sent"
    HEARTBEAT = "heartbeat"


class StreamPlugin(AgentBusPlugin):
    """
    流式响应处理插件
    
    继承AgentBusPlugin基类，提供流式响应处理功能，包括：
    - 流创建和管理
    - WebSocket和HTTP流处理
    - 流事件钩子
    - 流统计和监控
    """
    
    def __init__(self, plugin_id: str, context: PluginContext):
        super().__init__(plugin_id, context)
        
        # 流式响应处理器
        self.stream_processor: Optional[StreamResponseProcessor] = None
        
        # 活跃的流
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        
        # 流事件钩子
        self.stream_event_hooks: Dict[str, List[Callable]] = {}
        
        # 统计数据
        self.stats = {
            "total_streams": 0,
            "active_streams": 0,
            "completed_streams": 0,
            "error_streams": 0,
            "cancelled_streams": 0,
            "total_chunks_sent": 0,
            "total_bytes_sent": 0
        }
        
        self.context.logger.info(f"StreamPlugin {plugin_id} initialized")
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取插件信息
        """
        return {
            'id': self.plugin_id,
            'name': 'Stream Response Plugin',
            'version': '1.0.0',
            'description': '流式响应处理插件，提供WebSocket和HTTP流式处理功能',
            'author': 'AgentBus Team',
            'dependencies': [],
            'capabilities': [
                'websocket_streaming',
                'http_streaming', 
                'stream_management',
                'event_hooks',
                'statistics'
            ]
        }
    
    async def activate(self):
        """
        激活插件
        """
        # 先调用父类方法
        await super().activate()
        
        # 初始化流式响应处理器
        self.stream_processor = StreamResponseProcessor()
        await self.stream_processor.initialize()
        
        # 注册流处理工具
        self._register_stream_tools()
        
        # 注册流事件钩子
        self._register_stream_hooks()
        
        # 注册命令
        self._register_commands()
        
        self.context.logger.info(f"StreamPlugin {self.plugin_id} activated successfully")
    
    async def deactivate(self):
        """
        停用插件
        """
        try:
            # 取消所有活跃流
            for stream_id in list(self.active_streams.keys()):
                await self.cancel_stream(stream_id)
            
            # 关闭流式响应处理器
            if self.stream_processor:
                await self.stream_processor.shutdown()
                self.stream_processor = None
            
            # 调用父类方法
            await super().deactivate()
            
            self.context.logger.info(f"StreamPlugin {self.plugin_id} deactivated")
            
        except Exception as e:
            self.context.logger.error(f"Error deactivating StreamPlugin: {e}")
            self.status = PluginStatus.ERROR
            return False
    
    def _register_stream_tools(self):
        """注册流处理工具"""
        
        # 创建流工具
        self.register_tool(
            name='create_stream',
            description='创建新的流式传输',
            function=self.create_stream_tool
        )
        
        # 取消流工具
        self.register_tool(
            name='cancel_stream',
            description='取消指定的流式传输',
            function=self.cancel_stream_tool
        )
        
        # 获取流状态工具
        self.register_tool(
            name='get_stream_status',
            description='获取流的状态信息',
            function=self.get_stream_status_tool
        )
        
        # 获取流统计工具
        self.register_tool(
            name='get_stream_stats',
            description='获取流处理统计信息',
            function=self.get_stream_stats_tool
        )
        
        # 列出活跃流工具
        self.register_tool(
            name='list_active_streams',
            description='列出所有活跃的流',
            function=self.list_active_streams_tool
        )
        
        # 开始流处理工具
        self.register_tool(
            name='start_stream_processing',
            description='开始流内容处理',
            function=self.start_stream_processing_tool
        )
        
        # 发送流数据块工具
        self.register_tool(
            name='send_stream_chunk',
            description='向流发送数据块',
            function=self.send_stream_chunk_tool
        )
    
    def _register_stream_hooks(self):
        """注册流事件钩子"""
        
        # 流创建钩子
        self.register_hook(
            event=StreamEvent.STREAM_CREATED,
            handler=self.on_stream_created,
            priority=10
        )
        
        # 流开始钩子
        self.register_hook(
            event=StreamEvent.STREAM_STARTED,
            handler=self.on_stream_started,
            priority=10
        )
        
        # 流完成钩子
        self.register_hook(
            event=StreamEvent.STREAM_COMPLETED,
            handler=self.on_stream_completed,
            priority=10
        )
        
        # 流取消钩子
        self.register_hook(
            event=StreamEvent.STREAM_CANCELLED,
            handler=self.on_stream_cancelled,
            priority=10
        )
        
        # 流错误钩子
        self.register_hook(
            event=StreamEvent.STREAM_ERROR,
            handler=self.on_stream_error,
            priority=10
        )
        
        # 数据块发送钩子
        self.register_hook(
            event=StreamEvent.CHUNK_SENT,
            handler=self.on_chunk_sent,
            priority=5
        )
        
        # 心跳钩子
        self.register_hook(
            event=StreamEvent.HEARTBEAT,
            handler=self.on_heartbeat,
            priority=1
        )
    
    def _register_commands(self):
        """注册命令"""
        
        self.register_command(
            command='/stream-status',
            handler=self.handle_stream_status_command,
            description='显示流状态信息'
        )
        
        self.register_command(
            command='/stream-stats',
            handler=self.handle_stream_stats_command,
            description='显示流统计信息'
        )
        
        self.register_command(
            command='/stream-cancel',
            handler=self.handle_stream_cancel_command,
            description='取消指定流'
        )
    
    # 工具实现方法
    
    async def create_stream_tool(
        self,
        content: str,
        stream_type: str = "text",
        handler_type: str = "websocket",
        chunk_size: int = 10,
        delay_ms: int = 50,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建流工具实现"""
        try:
            # 生成流ID
            stream_id = str(uuid.uuid4())
            
            # 创建流请求
            request = StreamRequest(
                stream_id=stream_id,
                content=content,
                stream_type=stream_type,
                chunk_size=chunk_size,
                delay_ms=delay_ms,
                max_tokens=max_tokens,
                temperature=temperature,
                metadata=metadata or {}
            )
            
            # 创建流
            if not self.stream_processor:
                raise Exception("Stream processor not initialized")
            
            created_stream_id = await self.stream_processor.create_stream(request, handler_type)
            
            # 记录流信息
            self.active_streams[created_stream_id] = {
                'request': request,
                'handler_type': handler_type,
                'created_at': datetime.now(),
                'status': 'created'
            }
            
            # 更新统计
            self.stats['total_streams'] += 1
            self.stats['active_streams'] += 1
            
            # 触发流创建钩子
            await self._trigger_hook(StreamEvent.STREAM_CREATED, {
                'stream_id': created_stream_id,
                'request': request,
                'handler_type': handler_type
            })
            
            self.context.logger.info(f"Stream created: {created_stream_id}")
            
            return {
                'success': True,
                'stream_id': created_stream_id,
                'handler_type': handler_type,
                'status': 'created'
            }
            
        except Exception as e:
            self.context.logger.error(f"Failed to create stream: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def cancel_stream_tool(self, stream_id: str) -> Dict[str, Any]:
        """取消流工具实现"""
        try:
            if not self.stream_processor:
                raise Exception("Stream processor not initialized")
            
            # 取消流
            success = await self.stream_processor.cancel_stream(stream_id)
            
            if success:
                # 更新状态
                if stream_id in self.active_streams:
                    self.active_streams[stream_id]['status'] = 'cancelled'
                    del self.active_streams[stream_id]
                
                # 更新统计
                self.stats['active_streams'] -= 1
                self.stats['cancelled_streams'] += 1
                
                # 触发流取消钩子
                await self._trigger_hook(StreamEvent.STREAM_CANCELLED, {
                    'stream_id': stream_id
                })
                
                self.context.logger.info(f"Stream cancelled: {stream_id}")
                
                return {
                    'success': True,
                    'stream_id': stream_id,
                    'status': 'cancelled'
                }
            else:
                return {
                    'success': False,
                    'error': f'Stream not found: {stream_id}'
                }
                
        except Exception as e:
            self.context.logger.error(f"Failed to cancel stream: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_stream_status_tool(self, stream_id: str) -> Dict[str, Any]:
        """获取流状态工具实现"""
        try:
            if not self.stream_processor:
                raise Exception("Stream processor not initialized")
            
            # 获取流状态
            status = await self.stream_processor.get_stream_status(stream_id)
            
            return {
                'success': True,
                'stream_id': stream_id,
                'status': status.value if status else 'unknown'
            }
            
        except Exception as e:
            self.context.logger.error(f"Failed to get stream status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_stream_stats_tool(self) -> Dict[str, Any]:
        """获取流统计工具实现"""
        try:
            if not self.stream_processor:
                raise Exception("Stream processor not initialized")
            
            # 获取处理器统计
            processor_stats = await self.stream_processor.get_stream_stats()
            
            # 合并插件统计
            all_stats = {
                **self.stats,
                'processor_stats': processor_stats
            }
            
            return {
                'success': True,
                'stats': all_stats
            }
            
        except Exception as e:
            self.context.logger.error(f"Failed to get stream stats: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def list_active_streams_tool(self) -> Dict[str, Any]:
        """列出活跃流工具实现"""
        try:
            active_streams_list = []
            
            for stream_id, stream_info in self.active_streams.items():
                active_streams_list.append({
                    'stream_id': stream_id,
                    'handler_type': stream_info['handler_type'],
                    'created_at': stream_info['created_at'].isoformat(),
                    'status': stream_info['status'],
                    'stream_type': stream_info['request'].stream_type
                })
            
            return {
                'success': True,
                'active_streams': active_streams_list,
                'count': len(active_streams_list)
            }
            
        except Exception as e:
            self.context.logger.error(f"Failed to list active streams: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def start_stream_processing_tool(
        self,
        stream_id: str,
        generator_func_name: str = "simulate_ai_response"
    ) -> Dict[str, Any]:
        """开始流处理工具实现"""
        try:
            if not self.stream_processor:
                raise Exception("Stream processor not initialized")
            
            if stream_id not in self.active_streams:
                return {
                    'success': False,
                    'error': f'Stream not found: {stream_id}'
                }
            
            stream_info = self.active_streams[stream_id]
            request = stream_info['request']
            
            # 获取生成器函数
            if generator_func_name == "simulate_ai_response":
                generator_func = self.stream_processor.simulate_ai_response
            else:
                return {
                    'success': False,
                    'error': f'Unknown generator function: {generator_func_name}'
                }
            
            # 开始流处理
            success = await self.stream_processor.start_stream_processing(
                stream_id, generator_func
            )
            
            if success:
                # 更新状态
                self.active_streams[stream_id]['status'] = 'processing'
                
                # 触发流开始钩子
                await self._trigger_hook(StreamEvent.STREAM_STARTED, {
                    'stream_id': stream_id,
                    'request': request
                })
                
                self.context.logger.info(f"Stream processing started: {stream_id}")
                
                return {
                    'success': True,
                    'stream_id': stream_id,
                    'status': 'processing'
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to start stream processing: {stream_id}'
                }
                
        except Exception as e:
            self.context.logger.error(f"Failed to start stream processing: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def send_stream_chunk_tool(
        self,
        stream_id: str,
        content: str,
        event_type: str = "token",
        token_count: int = 0,
        progress: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送流数据块工具实现"""
        try:
            if not self.stream_processor:
                raise Exception("Stream processor not initialized")
            
            # 验证事件类型
            try:
                stream_event_type = StreamEventType(event_type)
            except ValueError:
                return {
                    'success': False,
                    'error': f'Invalid event type: {event_type}'
                }
            
            # 创建数据块
            chunk = StreamChunk(
                stream_id=stream_id,
                event_type=stream_event_type,
                content=content,
                token_count=token_count,
                progress=progress,
                metadata=metadata or {}
            )
            
            # 发送数据块
            success = await self.stream_processor.handlers["websocket"].send_chunk(stream_id, chunk)
            
            if success:
                # 更新统计
                self.stats['total_chunks_sent'] += 1
                self.stats['total_bytes_sent'] += len(content.encode('utf-8'))
                
                # 触发数据块发送钩子
                await self._trigger_hook(StreamEvent.CHUNK_SENT, {
                    'stream_id': stream_id,
                    'chunk': chunk
                })
                
                return {
                    'success': True,
                    'stream_id': stream_id,
                    'chunk_sent': True
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to send chunk to stream: {stream_id}'
                }
                
        except Exception as e:
            self.context.logger.error(f"Failed to send stream chunk: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # 钩子处理方法
    
    async def on_stream_created(self, event_data: Dict[str, Any]):
        """流创建钩子处理"""
        self.context.logger.info(f"Stream created hook: {event_data['stream_id']}")
    
    async def on_stream_started(self, event_data: Dict[str, Any]):
        """流开始钩子处理"""
        self.context.logger.info(f"Stream started hook: {event_data['stream_id']}")
    
    async def on_stream_completed(self, event_data: Dict[str, Any]):
        """流完成钩子处理"""
        stream_id = event_data['stream_id']
        
        # 更新状态和统计
        if stream_id in self.active_streams:
            self.active_streams[stream_id]['status'] = 'completed'
            self.active_streams[stream_id]['completed_at'] = datetime.now()
        
        self.stats['active_streams'] -= 1
        self.stats['completed_streams'] += 1
        
        self.context.logger.info(f"Stream completed hook: {stream_id}")
    
    async def on_stream_cancelled(self, event_data: Dict[str, Any]):
        """流取消钩子处理"""
        self.context.logger.info(f"Stream cancelled hook: {event_data['stream_id']}")
    
    async def on_stream_error(self, event_data: Dict[str, Any]):
        """流错误钩子处理"""
        stream_id = event_data.get('stream_id', 'unknown')
        
        # 更新状态和统计
        if stream_id in self.active_streams:
            self.active_streams[stream_id]['status'] = 'error'
        
        self.stats['active_streams'] -= 1
        self.stats['error_streams'] += 1
        
        self.context.logger.error(f"Stream error hook: {stream_id} - {event_data.get('error', 'Unknown error')}")
    
    async def on_chunk_sent(self, event_data: Dict[str, Any]):
        """数据块发送钩子处理"""
        # 可以在这里添加数据块处理的额外逻辑
        pass
    
    async def on_heartbeat(self, event_data: Dict[str, Any]):
        """心跳钩子处理"""
        # 可以在这里添加心跳处理的额外逻辑
        pass
    
    # 命令处理方法
    
    async def handle_stream_status_command(self, args: str) -> str:
        """处理流状态命令"""
        try:
            # 获取统计信息
            result = await self.get_stream_stats_tool()
            
            if result['success']:
                stats = result['stats']
                status_info = [
                    "📊 流状态统计:",
                    f"  总流数: {stats['total_streams']}",
                    f"  活跃流数: {stats['active_streams']}",
                    f"  已完成: {stats['completed_streams']}",
                    f"  错误: {stats['error_streams']}",
                    f"  已取消: {stats['cancelled_streams']}",
                    f"  发送数据块: {stats['total_chunks_sent']}",
                    f"  发送字节: {stats['total_bytes_sent']}"
                ]
                return "\n".join(status_info)
            else:
                return f"❌ 获取统计失败: {result['error']}"
                
        except Exception as e:
            return f"❌ 处理命令失败: {e}"
    
    async def handle_stream_stats_command(self, args: str) -> str:
        """处理流统计命令"""
        try:
            result = await self.get_stream_stats_tool()
            
            if result['success']:
                stats = result['stats']
                processor_stats = stats.get('processor_stats', {})
                
                stats_info = [
                    "📈 详细统计信息:",
                    "",
                    "插件统计:",
                    f"  总流数: {stats['total_streams']}",
                    f"  活跃流数: {stats['active_streams']}",
                    f"  已完成: {stats['completed_streams']}",
                    f"  错误: {stats['error_streams']}",
                    f"  已取消: {stats['cancelled_streams']}",
                    f"  数据块: {stats['total_chunks_sent']}",
                    f"  字节数: {stats['total_bytes_sent']}",
                    "",
                    "处理器统计:"
                ]
                
                for key, value in processor_stats.items():
                    if isinstance(value, dict):
                        stats_info.append(f"  {key}:")
                        for sub_key, sub_value in value.items():
                            stats_info.append(f"    - {sub_key}: {sub_value}")
                    else:
                        stats_info.append(f"  {key}: {value}")
                
                return "\n".join(stats_info)
            else:
                return f"❌ 获取统计失败: {result['error']}"
                
        except Exception as e:
            return f"❌ 处理命令失败: {e}"
    
    async def handle_stream_cancel_command(self, args: str) -> str:
        """处理流取消命令"""
        try:
            if not args.strip():
                return "❌ 请指定要取消的流ID"
            
            stream_id = args.strip()
            result = await self.cancel_stream_tool(stream_id)
            
            if result['success']:
                return f"✅ 流已取消: {stream_id}"
            else:
                return f"❌ 取消流失败: {result['error']}"
                
        except Exception as e:
            return f"❌ 处理命令失败: {e}"
    
    # 辅助方法
    
    async def _trigger_hook(self, event: StreamEvent, event_data: Dict[str, Any]):
        """触发钩子"""
        try:
            # 转换为字符串事件名
            event_name = event.value
            
            # 获取注册的钩子
            hooks = self.get_hooks().get(event_name, [])
            
            # 按优先级执行钩子
            for hook in hooks:
                try:
                    if hook.async_func:
                        await hook.handler(event_data)
                    else:
                        hook.handler(event_data)
                except Exception as e:
                    self.context.logger.error(f"Hook execution failed for {event_name}: {e}")
                    
        except Exception as e:
            self.context.logger.error(f"Failed to trigger hook {event.value}: {e}")
    
    # 兼容性方法（保持与原有StreamResponseProcessor的接口兼容）
    
    async def create_stream(self, request: StreamRequest, handler_type: str = "websocket") -> str:
        """创建流（兼容性方法）"""
        if not self.stream_processor:
            raise Exception("Stream processor not initialized")
        
        stream_id = await self.stream_processor.create_stream(request, handler_type)
        
        # 记录流信息
        self.active_streams[stream_id] = {
            'request': request,
            'handler_type': handler_type,
            'created_at': datetime.now(),
            'status': 'created'
        }
        
        # 更新统计
        self.stats['total_streams'] += 1
        self.stats['active_streams'] += 1
        
        # 触发钩子
        await self._trigger_hook(StreamEvent.STREAM_CREATED, {
            'stream_id': stream_id,
            'request': request,
            'handler_type': handler_type
        })
        
        return stream_id
    
    async def cancel_stream(self, stream_id: str) -> bool:
        """取消流（兼容性方法）"""
        if not self.stream_processor:
            return False
        
        success = await self.stream_processor.cancel_stream(stream_id)
        
        if success:
            # 更新状态
            if stream_id in self.active_streams:
                self.active_streams[stream_id]['status'] = 'cancelled'
                del self.active_streams[stream_id]
            
            # 更新统计
            self.stats['active_streams'] -= 1
            self.stats['cancelled_streams'] += 1
            
            # 触发钩子
            await self._trigger_hook(StreamEvent.STREAM_CANCELLED, {
                'stream_id': stream_id
            })
        
        return success
    
    async def get_stream_status(self, stream_id: str) -> Optional[StreamStatus]:
        """获取流状态（兼容性方法）"""
        if not self.stream_processor:
            return None
        
        return await self.stream_processor.get_stream_status(stream_id)
    
    async def get_stream_stats(self) -> Dict[str, Any]:
        """获取流统计（兼容性方法）"""
        if not self.stream_processor:
            return {}
        
        processor_stats = await self.stream_processor.get_stream_stats()
        
        return {
            **self.stats,
            'processor_stats': processor_stats
        }
    
    async def list_active_streams(self) -> List[str]:
        """列出活跃流（兼容性方法）"""
        return list(self.active_streams.keys())
    
    async def simulate_ai_response(self, request: StreamRequest) -> AsyncGenerator[str, None]:
        """模拟AI响应（兼容性方法）"""
        if not self.stream_processor:
            return
        
        async for chunk in self.stream_processor.simulate_ai_response(request):
            yield chunk