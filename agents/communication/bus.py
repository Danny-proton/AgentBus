"""
AgentBus Communication System
Agent通信系统
"""

from typing import Dict, List, Optional, Any, Callable, AsyncIterator, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import asyncio
import uuid
import json
import asyncio.streams
from collections import defaultdict, deque

from ..core.types import (
    MessageType, Priority, AgentMessage, AgentStatus, AgentState,
    HealthStatus, AlertLevel
)


class CommunicationBus:
    """Agent通信总线"""
    
    def __init__(self, bus_id: str = "default"):
        self.bus_id = bus_id
        self.logger = self._get_logger()
        
        # Agent注册
        self.registered_agents: Dict[str, 'AgentConnection'] = {}
        self.agent_subscriptions: Dict[str, Set[str]] = defaultdict(set)  # agent_id -> message_types
        
        # 消息队列
        self.global_message_queue = asyncio.Queue()
        self.direct_message_queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self.broadcast_queues: Dict[Priority, asyncio.Queue] = {
            Priority.LOW: asyncio.Queue(),
            Priority.NORMAL: asyncio.Queue(),
            Priority.HIGH: asyncio.Queue(),
            Priority.CRITICAL: asyncio.Queue()
        }
        
        # 订阅管理
        self.subscribers: Dict[str, Set[str]] = defaultdict(set)  # message_type -> agent_ids
        self.broadcast_subscribers: Set[str] = set()  # agent_ids for broadcast
        
        # 统计信息
        self.message_stats = {
            "total_messages": 0,
            "direct_messages": 0,
            "broadcast_messages": 0,
            "system_messages": 0,
            "error_messages": 0
        }
        
        # 运行状态
        self.running = False
        self.processing_tasks: List[asyncio.Task] = []
        
        # 消息处理
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        self.error_handlers: List[Callable] = []
        
        # QoS配置
        self.max_queue_size = 10000
        self.message_ttl = 3600  # 1小时
        self.enable_priorities = True
        
        # 负载均衡
        self.round_robin_counters: Dict[str, int] = defaultdict(int)
    
    def _get_logger(self):
        """获取日志记录器"""
        return f"communication.bus.{self.bus_id}"
    
    async def start(self):
        """启动通信总线"""
        if self.running:
            return
        
        self.running = True
        
        # 启动消息处理任务
        self.processing_tasks.extend([
            asyncio.create_task(self._global_message_processor()),
            asyncio.create_task(self._direct_message_processor()),
            asyncio.create_task(self._broadcast_message_processor()),
            asyncio.create_task(self._heartbeat_processor()),
            asyncio.create_task(self._cleanup_processor())
        ])
        
        self.logger.info("Communication bus started")
    
    async def stop(self):
        """停止通信总线"""
        if not self.running:
            return
        
        self.running = False
        
        # 取消所有处理任务
        for task in self.processing_tasks:
            task.cancel()
        
        # 等待任务完成
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        
        self.processing_tasks.clear()
        self.logger.info("Communication bus stopped")
    
    def register_agent(self, agent_id: str, connection: 'AgentConnection') -> bool:
        """注册Agent"""
        try:
            if agent_id in self.registered_agents:
                self.logger.warning(f"Agent {agent_id} already registered")
                return False
            
            self.registered_agents[agent_id] = connection
            self.logger.info(f"Agent {agent_id} registered")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register agent {agent_id}: {e}")
            return False
    
    def unregister_agent(self, agent_id: str):
        """注销Agent"""
        if agent_id in self.registered_agents:
            del self.registered_agents[agent_id]
            
            # 清理订阅
            for message_type in self.agent_subscriptions[agent_id]:
                self.subscribers[message_type].discard(agent_id)
            del self.agent_subscriptions[agent_id]
            
            self.broadcast_subscribers.discard(agent_id)
            
            # 清理消息队列
            self.direct_message_queues.pop(agent_id, None)
            self.round_robin_counters.pop(agent_id, None)
            
            self.logger.info(f"Agent {agent_id} unregistered")
    
    async def send_message(self, message: AgentMessage) -> bool:
        """发送消息"""
        try:
            # 验证消息
            if not self._validate_message(message):
                return False
            
            # 更新统计
            self.message_stats["total_messages"] += 1
            
            # 根据消息类型分发
            if message.message_type == MessageType.DIRECT:
                return await self._send_direct_message(message)
            elif message.message_type == MessageType.BROADCAST:
                return await self._send_broadcast_message(message)
            elif message.message_type == MessageType.HEARTBEAT:
                return await self._send_heartbeat_message(message)
            elif message.message_type == MessageType.SYSTEM:
                return await self._send_system_message(message)
            else:
                # 其他消息类型发送到全局队列
                return await self._send_global_message(message)
                
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False
    
    async def subscribe(self, agent_id: str, message_types: List[MessageType]):
        """订阅消息类型"""
        for message_type in message_types:
            self.subscribers[message_type.value].add(agent_id)
            self.agent_subscriptions[agent_id].add(message_type.value)
        self.logger.info(f"Agent {agent_id} subscribed to {len(message_types)} message types")
    
    async def unsubscribe(self, agent_id: str, message_types: List[MessageType]):
        """取消订阅"""
        for message_type in message_types:
            self.subscribers[message_type.value].discard(agent_id)
            self.agent_subscriptions[agent_id].discard(message_type.value)
        self.logger.info(f"Agent {agent_id} unsubscribed from {len(message_types)} message types")
    
    async def subscribe_broadcast(self, agent_id: str):
        """订阅广播消息"""
        self.broadcast_subscribers.add(agent_id)
        self.logger.info(f"Agent {agent_id} subscribed to broadcast messages")
    
    async def unsubscribe_broadcast(self, agent_id: str):
        """取消订阅广播"""
        self.broadcast_subscribers.discard(agent_id)
        self.logger.info(f"Agent {agent_id} unsubscribed from broadcast messages")
    
    async def create_direct_channel(self, sender_id: str, receiver_id: str) -> 'DirectChannel':
        """创建直接通信通道"""
        if sender_id not in self.registered_agents or receiver_id not in self.registered_agents:
            raise ValueError("Both sender and receiver must be registered agents")
        
        channel = DirectChannel(
            sender_id=sender_id,
            receiver_id=receiver_id,
            bus=self
        )
        
        self.logger.info(f"Direct channel created: {sender_id} -> {receiver_id}")
        return channel
    
    async def create_group_channel(self, agent_ids: List[str], group_name: str = None) -> 'GroupChannel':
        """创建群组通信通道"""
        # 验证所有agent都已注册
        for agent_id in agent_ids:
            if agent_id not in self.registered_agents:
                raise ValueError(f"Agent {agent_id} is not registered")
        
        channel = GroupChannel(
            agent_ids=set(agent_ids),
            group_name=group_name or f"group_{uuid.uuid4().hex[:8]}",
            bus=self
        )
        
        self.logger.info(f"Group channel created: {channel.group_name} with {len(agent_ids)} agents")
        return channel
    
    def add_message_handler(self, message_type: MessageType, handler: Callable):
        """添加消息处理器"""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)
    
    def add_error_handler(self, handler: Callable):
        """添加错误处理器"""
        self.error_handlers.append(handler)
    
    def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取Agent状态"""
        if agent_id not in self.registered_agents:
            return None
        
        connection = self.registered_agents[agent_id]
        return {
            "agent_id": agent_id,
            "connected": connection.connected,
            "last_heartbeat": connection.last_heartbeat.isoformat() if connection.last_heartbeat else None,
            "subscriptions": list(self.agent_subscriptions[agent_id]),
            "queue_size": self.direct_message_queues[agent_id].qsize()
        }
    
    def get_bus_stats(self) -> Dict[str, Any]:
        """获取总线统计信息"""
        return {
            "bus_id": self.bus_id,
            "registered_agents": len(self.registered_agents),
            "message_stats": self.message_stats.copy(),
            "queue_sizes": {
                "global": self.global_message_queue.qsize(),
                "direct": {aid: q.qsize() for aid, q in self.direct_message_queues.items()},
                "broadcast": {p.name: q.qsize() for p, q in self.broadcast_queues.items()}
            },
            "subscriptions": {
                "total_subscriptions": sum(len(subs) for subs in self.subscribers.values()),
                "broadcast_subscribers": len(self.broadcast_subscribers),
                "message_type_subscriptions": {mt: len(subs) for mt, subs in self.subscribers.items()}
            }
        }
    
    # === 私有方法 ===
    
    def _validate_message(self, message: AgentMessage) -> bool:
        """验证消息"""
        if not message.sender_id or not message.receiver_id:
            if message.message_type not in [MessageType.BROADCAST, MessageType.SYSTEM]:
                return False
        
        # 检查过期时间
        if message.is_expired():
            return False
        
        return True
    
    async def _send_direct_message(self, message: AgentMessage) -> bool:
        """发送直接消息"""
        receiver_id = message.receiver_id
        
        if receiver_id not in self.registered_agents:
            return False
        
        # 添加到接收者的队列
        queue = self.direct_message_queues[receiver_id]
        if queue.qsize() >= self.max_queue_size:
            self.logger.warning(f"Queue full for agent {receiver_id}")
            return False
        
        await queue.put(message)
        self.message_stats["direct_messages"] += 1
        
        return True
    
    async def _send_broadcast_message(self, message: AgentMessage) -> bool:
        """发送广播消息"""
        priority_queue = self.broadcast_queues.get(message.priority)
        if not priority_queue:
            return False
        
        if priority_queue.qsize() >= self.max_queue_size:
            self.logger.warning("Broadcast queue full")
            return False
        
        await priority_queue.put(message)
        self.message_stats["broadcast_messages"] += 1
        
        return True
    
    async def _send_heartbeat_message(self, message: AgentMessage) -> bool:
        """发送心跳消息"""
        if message.sender_id in self.registered_agents:
            connection = self.registered_agents[message.sender_id]
            connection.last_heartbeat = datetime.now()
            connection.connected = True
        
        # 心跳消息不进入队列，直接处理
        await self._handle_message(message)
        return True
    
    async def _send_system_message(self, message: AgentMessage) -> bool:
        """发送系统消息"""
        await self.global_message_queue.put(message)
        self.message_stats["system_messages"] += 1
        return True
    
    async def _send_global_message(self, message: AgentMessage) -> bool:
        """发送全局消息"""
        await self.global_message_queue.put(message)
        return True
    
    async def _global_message_processor(self):
        """全局消息处理器"""
        while self.running:
            try:
                message = await asyncio.wait_for(self.global_message_queue.get(), timeout=1.0)
                await self._handle_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Global message processor error: {e}")
                await asyncio.sleep(1)
    
    async def _direct_message_processor(self):
        """直接消息处理器"""
        while self.running:
            try:
                # 检查所有直接消息队列
                for agent_id, queue in list(self.direct_message_queues.items()):
                    if queue.empty():
                        continue
                    
                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=0.1)
                        await self._deliver_direct_message(agent_id, message)
                    except asyncio.TimeoutError:
                        continue
                
                await asyncio.sleep(0.01)  # 短暂休眠
                
            except Exception as e:
                self.logger.error(f"Direct message processor error: {e}")
                await asyncio.sleep(1)
    
    async def _broadcast_message_processor(self):
        """广播消息处理器"""
        while self.running:
            try:
                # 按优先级处理广播消息
                for priority in [Priority.CRITICAL, Priority.HIGH, Priority.NORMAL, Priority.LOW]:
                    queue = self.broadcast_queues[priority]
                    
                    while not queue.empty():
                        try:
                            message = queue.get_nowait()
                            await self._deliver_broadcast_message(message)
                        except asyncio.QueueEmpty:
                            break
                        except Exception as e:
                            self.logger.error(f"Broadcast message delivery error: {e}")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Broadcast message processor error: {e}")
                await asyncio.sleep(1)
    
    async def _deliver_direct_message(self, receiver_id: str, message: AgentMessage):
        """递送直接消息"""
        if receiver_id in self.registered_agents:
            connection = self.registered_agents[receiver_id]
            try:
                await connection.handle_message(message)
            except Exception as e:
                self.logger.error(f"Failed to deliver message to {receiver_id}: {e}")
    
    async def _deliver_broadcast_message(self, message: AgentMessage):
        """递送广播消息"""
        for agent_id in list(self.broadcast_subscribers):
            if agent_id in self.registered_agents:
                connection = self.registered_agents[agent_id]
                try:
                    await connection.handle_message(message)
                except Exception as e:
                    self.logger.error(f"Failed to broadcast message to {agent_id}: {e}")
    
    async def _handle_message(self, message: AgentMessage):
        """处理消息"""
        try:
            # 调用消息处理器
            handlers = self.message_handlers.get(message.message_type, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message)
                    else:
                        handler(message)
                except Exception as e:
                    self.logger.error(f"Message handler error: {e}")
            
            # 调用错误处理器（如果是错误消息）
            if message.message_type == MessageType.ERROR:
                for handler in self.error_handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(message)
                        else:
                            handler(message)
                    except Exception as e:
                        self.logger.error(f"Error handler error: {e}")
        
        except Exception as e:
            self.logger.error(f"Message handling error: {e}")
    
    async def _heartbeat_processor(self):
        """心跳处理器"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # 检查所有连接的心跳
                for agent_id, connection in self.registered_agents.items():
                    if current_time - connection.last_heartbeat > timedelta(seconds=30):
                        connection.connected = False
                        self.logger.warning(f"Agent {agent_id} heartbeat timeout")
                        
                        # 发送心跳超时消息
                        timeout_message = AgentMessage(
                            message_type=MessageType.HEARTBEAT,
                            sender_id="system",
                            receiver_id=agent_id,
                            content={"status": "timeout", "timestamp": current_time.isoformat()}
                        )
                        await self._handle_message(timeout_message)
                
                await asyncio.sleep(10)  # 每10秒检查一次心跳
                
            except Exception as e:
                self.logger.error(f"Heartbeat processor error: {e}")
                await asyncio.sleep(10)
    
    async def _cleanup_processor(self):
        """清理处理器"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # 清理过期消息（这里简化处理）
                # 在实际实现中，需要对每个队列进行清理
                
                await asyncio.sleep(300)  # 每5分钟清理一次
                
            except Exception as e:
                self.logger.error(f"Cleanup processor error: {e}")
                await asyncio.sleep(300)


class AgentConnection:
    """Agent连接"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.connected = False
        self.last_heartbeat = datetime.now()
        self.message_handlers: List[Callable] = []
        self.error_handlers: List[Callable] = []
    
    async def handle_message(self, message: AgentMessage):
        """处理消息"""
        for handler in self.message_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                self.logger.error(f"Message handler error: {e}")
    
    def add_message_handler(self, handler: Callable):
        """添加消息处理器"""
        self.message_handlers.append(handler)
    
    def add_error_handler(self, handler: Callable):
        """添加错误处理器"""
        self.error_handlers.append(handler)


class DirectChannel:
    """直接通信通道"""
    
    def __init__(self, sender_id: str, receiver_id: str, bus: CommunicationBus):
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.bus = bus
        self.message_queue = asyncio.Queue()
        self.running = False
        self.processing_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """启动通道"""
        if self.running:
            return
        
        self.running = True
        self.processing_task = asyncio.create_task(self._message_processor())
    
    async def stop(self):
        """停止通道"""
        if not self.running:
            return
        
        self.running = False
        
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
    
    async def send_message(self, content: Any, priority: Priority = Priority.NORMAL,
                          metadata: Dict[str, Any] = None) -> bool:
        """发送消息"""
        message = AgentMessage(
            message_type=MessageType.DIRECT,
            sender_id=self.sender_id,
            receiver_id=self.receiver_id,
            priority=priority,
            content=content,
            metadata=metadata or {}
        )
        
        return await self.bus.send_message(message)
    
    async def _message_processor(self):
        """消息处理器"""
        while self.running:
            try:
                # 从总线获取消息
                message = await asyncio.wait_for(
                    self.bus.direct_message_queues[self.receiver_id].get(),
                    timeout=1.0
                )
                
                # 验证消息
                if message.sender_id == self.sender_id:
                    await self.message_queue.put(message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                # 记录错误但继续
                pass
    
    async def receive_message(self, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """接收消息"""
        try:
            return await asyncio.wait_for(self.message_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None


class GroupChannel:
    """群组通信通道"""
    
    def __init__(self, agent_ids: Set[str], group_name: str, bus: CommunicationBus):
        self.agent_ids = agent_ids
        self.group_name = group_name
        self.bus = bus
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self.running = False
        self.processing_tasks: List[asyncio.Task] = []
    
    async def start(self):
        """启动通道"""
        if self.running:
            return
        
        self.running = True
        
        # 为每个成员创建消息队列
        for agent_id in self.agent_ids:
            self.message_queues[agent_id] = asyncio.Queue()
            
            # 启动处理器
            task = asyncio.create_task(self._agent_message_processor(agent_id))
            self.processing_tasks.append(task)
    
    async def stop(self):
        """停止通道"""
        if not self.running:
            return
        
        self.running = False
        
        # 取消所有处理器
        for task in self.processing_tasks:
            task.cancel()
        
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)
        
        self.processing_tasks.clear()
        self.message_queues.clear()
    
    async def send_message(self, sender_id: str, content: Any, 
                         priority: Priority = Priority.NORMAL,
                         metadata: Dict[str, Any] = None) -> bool:
        """发送群组消息"""
        if sender_id not in self.agent_ids:
            return False
        
        message = AgentMessage(
            message_type=MessageType.BROADCAST,
            sender_id=sender_id,
            receiver_id=self.group_name,  # 使用群组名作为接收者
            priority=priority,
            content=content,
            metadata={**metadata, "group_name": self.group_name} if metadata else {"group_name": self.group_name}
        )
        
        return await self.bus.send_message(message)
    
    async def _agent_message_processor(self, agent_id: str):
        """成员消息处理器"""
        queue = self.message_queues[agent_id]
        
        while self.running:
            try:
                # 从总线获取消息
                message = await asyncio.wait_for(
                    self.bus.direct_message_queues[agent_id].get(),
                    timeout=1.0
                )
                
                # 检查是否是群组消息
                if message.metadata.get("group_name") == self.group_name:
                    await queue.put(message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                # 记录错误但继续
                pass
    
    async def receive_message(self, agent_id: str, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """接收消息"""
        if agent_id not in self.agent_ids:
            return None
        
        queue = self.message_queues[agent_id]
        
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None
    
    def add_member(self, agent_id: str):
        """添加成员"""
        if agent_id not in self.agent_ids:
            self.agent_ids.add(agent_id)
            self.message_queues[agent_id] = asyncio.Queue()
    
    def remove_member(self, agent_id: str):
        """移除成员"""
        if agent_id in self.agent_ids:
            self.agent_ids.discard(agent_id)
            self.message_queues.pop(agent_id, None)


def create_communication_bus(bus_id: str = "default") -> CommunicationBus:
    """创建通信总线"""
    return CommunicationBus(bus_id)


def get_communication_bus(bus_id: str = "default") -> CommunicationBus:
    """获取通信总线（单例）"""
    # 这里可以实现单例模式
    return CommunicationBus(bus_id)