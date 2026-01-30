"""
消息路由系统
Message Routing System

智能消息路由和分发系统
"""

from typing import Dict, List, Optional, Set, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import asyncio
import json
import uuid
from contextlib import asynccontextmanager

from ..core.logger import get_logger
from ..core.config import settings
from ..adapters.base import Message, MessageType, AdapterType, BaseAdapter
from ..core.session import SessionContext, SessionManager, get_session_manager

logger = get_logger(__name__)


class RoutingStrategy(Enum):
    """路由策略枚举"""
    ROUND_ROBIN = "round_robin"      # 轮询
    WEIGHTED = "weighted"           # 加权
    AFFINITY = "affinity"           # 亲和性
    LOAD_BALANCE = "load_balance"   # 负载均衡
    PRIORITY = "priority"            # 优先级
    FAILOVER = "failover"           # 故障转移


class MessageRoute(Enum):
    """消息路由枚举"""
    DIRECT = "direct"               # 直接路由
    BROADCAST = "broadcast"         # 广播
    FANOUT = "fanout"               # 扇出
    AGGREGATE = "aggregate"         # 聚合
    FILTER = "filter"               # 过滤


@dataclass
class RoutingRule:
    """路由规则"""
    id: str
    name: str
    conditions: Dict[str, Any]      # 路由条件
    targets: List[str]              # 目标适配器/技能
    strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN
    priority: int = 0               # 优先级（数字越大优先级越高）
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def matches(self, message: Message, context: Optional[SessionContext] = None) -> bool:
        """检查消息是否匹配此规则"""
        # 检查消息类型
        if "message_type" in self.conditions:
            if message.message_type.value != self.conditions["message_type"]:
                return False
        
        # 检查平台
        if "platform" in self.conditions:
            if message.platform.value != self.conditions["platform"]:
                return False
        
        # 检查用户ID
        if "user_id" in self.conditions:
            if message.user_id != self.conditions["user_id"]:
                return False
        
        # 检查聊天ID
        if "chat_id" in self.conditions:
            if message.chat_id != self.conditions["chat_id"]:
                return False
        
        # 检查内容关键词
        if "keywords" in self.conditions:
            content = str(message.content).lower()
            keywords = self.conditions["keywords"]
            if not any(keyword.lower() in content for keyword in keywords):
                return False
        
        # 检查会话属性（如果有上下文）
        if context and "session_data" in self.conditions:
            for key, expected_value in self.conditions["session_data"].items():
                if key not in context.data or context.data[key] != expected_value:
                    return False
        
        return True


@dataclass
class RouteTarget:
    """路由目标"""
    id: str
    type: str                       # "adapter", "skill", "gateway"
    name: str
    weight: int = 1                 # 权重
    capacity: int = 100             # 容量
    current_load: int = 0          # 当前负载
    available: bool = True          # 是否可用
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def can_handle(self) -> bool:
        """检查是否可以处理新消息"""
        return self.available and self.current_load < self.capacity
    
    def increment_load(self) -> None:
        """增加负载"""
        self.current_load += 1
    
    def decrement_load(self) -> None:
        """减少负载"""
        self.current_load = max(0, self.current_load - 1)


@dataclass
class RoutedMessage:
    """路由消息"""
    original_message: Message
    route_id: str
    target: RouteTarget
    context: Optional[SessionContext]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "route_id": self.route_id,
            "target": self.target.name,
            "target_type": self.target.type,
            "original_message_id": self.original_message.id,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }


class MessageRouter:
    """消息路由器"""
    
    def __init__(self, session_manager: Optional[SessionManager] = None):
        self.logger = get_logger(self.__class__.__name__)
        self.session_manager = session_manager or get_session_manager()
        
        # 路由规则
        self.rules: Dict[str, RoutingRule] = {}
        
        # 路由目标
        self.targets: Dict[str, RouteTarget] = {}
        
        # 负载均衡状态
        self.round_robin_index: Dict[str, int] = {}
        
        # 消息处理器
        self.message_handlers: Dict[str, Callable] = {}
        
        # 统计信息
        self.stats = {
            "messages_routed": 0,
            "messages_failed": 0,
            "rules_matched": 0,
            "targets_used": {}
        }
    
    def add_rule(self, rule: RoutingRule) -> None:
        """添加路由规则"""
        self.rules[rule.id] = rule
        self.logger.info("Routing rule added", 
                        rule_id=rule.id,
                        rule_name=rule.name,
                        targets=rule.targets)
    
    def remove_rule(self, rule_id: str) -> None:
        """移除路由规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            self.logger.info("Routing rule removed", rule_id=rule_id)
    
    def add_target(self, target: RouteTarget) -> None:
        """添加路由目标"""
        self.targets[target.id] = target
        self.logger.info("Routing target added", 
                        target_id=target.id,
                        target_name=target.name,
                        target_type=target.type)
    
    def remove_target(self, target_id: str) -> None:
        """移除路由目标"""
        if target_id in self.targets:
            del self.targets[target_id]
            self.logger.info("Routing target removed", target_id=target_id)
    
    def register_handler(self, handler_type: str, handler: Callable) -> None:
        """注册消息处理器"""
        self.message_handlers[handler_type] = handler
        self.logger.debug("Message handler registered", handler_type=handler_type)
    
    async def route_message(
        self, 
        message: Message, 
        context: Optional[SessionContext] = None
    ) -> List[RoutedMessage]:
        """路由消息"""
        routed_messages = []
        
        try:
            # 查找匹配的路由规则
            matched_rules = self._find_matching_rules(message, context)
            
            if not matched_rules:
                self.logger.warning("No routing rules matched", 
                                  message_id=message.id,
                                  message_type=message.message_type.value,
                                  platform=message.platform.value)
                return []
            
            # 按优先级排序规则
            matched_rules.sort(key=lambda r: r.priority, reverse=True)
            
            for rule in matched_rules:
                for target_name in rule.targets:
                    target = self._get_target_by_name(target_name)
                    if target and target.can_handle():
                        routed_msg = await self._route_to_target(message, rule, target, context)
                        if routed_msg:
                            routed_messages.append(routed_msg)
                            target.increment_load()
                    
                    # 根据策略决定是否继续路由
                    if rule.strategy == RoutingStrategy.ROUND_ROBIN:
                        break  # 轮询只选择一个目标
                    elif rule.strategy == RoutingStrategy.PRIORITY:
                        break  # 优先级只选择一个目标
            
            # 更新统计
            self.stats["messages_routed"] += len(routed_messages)
            self.stats["rules_matched"] += len(matched_rules)
            
            for routed_msg in routed_messages:
                target_id = routed_msg.target.id
                self.stats["targets_used"][target_id] = \
                    self.stats["targets_used"].get(target_id, 0) + 1
            
            self.logger.info("Message routed", 
                          message_id=message.id,
                          route_count=len(routed_messages),
                          matched_rules=len(matched_rules))
            
        except Exception as e:
            self.logger.error("Message routing failed", 
                            message_id=message.id,
                            error=str(e))
            self.stats["messages_failed"] += 1
        
        return routed_messages
    
    def _find_matching_rules(
        self, 
        message: Message, 
        context: Optional[SessionContext]
    ) -> List[RoutingRule]:
        """查找匹配的路由规则"""
        matched_rules = []
        
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            if rule.matches(message, context):
                matched_rules.append(rule)
        
        return matched_rules
    
    def _get_target_by_name(self, target_name: str) -> Optional[RouteTarget]:
        """根据名称获取目标"""
        # 直接匹配ID
        if target_name in self.targets:
            return self.targets[target_name]
        
        # 按类型和名称匹配
        for target in self.targets.values():
            if target.name == target_name:
                return target
        
        return None
    
    async def _route_to_target(
        self,
        message: Message,
        rule: RoutingRule,
        target: RouteTarget,
        context: Optional[SessionContext]
    ) -> Optional[RoutedMessage]:
        """路由到目标"""
        try:
            # 创建路由消息
            routed_msg = RoutedMessage(
                original_message=message,
                route_id=rule.id,
                target=target,
                context=context,
                metadata={
                    "rule_name": rule.name,
                    "strategy": rule.strategy.value,
                    "routing_timestamp": datetime.now().isoformat()
                }
            )
            
            # 根据目标类型调用处理器
            if target.type == "adapter":
                await self._route_to_adapter(routed_msg)
            elif target.type == "skill":
                await self._route_to_skill(routed_msg)
            elif target.type == "gateway":
                await self._route_to_gateway(routed_msg)
            
            self.logger.debug("Message routed to target", 
                            message_id=message.id,
                            target_name=target.name,
                            target_type=target.type)
            
            return routed_msg
            
        except Exception as e:
            self.logger.error("Failed to route to target", 
                            target_name=target.name,
                            error=str(e))
            return None
    
    async def _route_to_adapter(self, routed_msg: RoutedMessage) -> None:
        """路由到适配器"""
        # 这里可以集成到适配器系统
        # 实际实现中需要调用适配器的消息处理方法
        pass
    
    async def _route_to_skill(self, routed_msg: RoutedMessage) -> None:
        """路由到技能"""
        # 这里可以集成到技能系统
        # 实际实现中需要调用技能的执行方法
        pass
    
    async def _route_to_gateway(self, routed_msg: RoutedMessage) -> None:
        """路由到网关"""
        # 这里可以集成到WebSocket网关
        # 实际实现中需要发送到WebSocket客户端
        pass
    
    async def broadcast_message(
        self, 
        message: Message, 
        targets: List[str],
        exclude_message_id: Optional[str] = None
    ) -> int:
        """广播消息"""
        routed_count = 0
        
        for target_name in targets:
            target = self._get_target_by_name(target_name)
            if target and target.can_handle():
                routed_msg = await self._route_to_target(
                    message, 
                    RoutingRule("broadcast", "broadcast", {}, [target_name]),
                    target,
                    None
                )
                if routed_msg:
                    routed_count += 1
                    target.increment_load()
        
        self.logger.info("Message broadcasted", 
                       message_id=message.id,
                       target_count=routed_count)
        
        return routed_count
    
    async def aggregate_responses(
        self, 
        message: Message, 
        target_names: List[str],
        timeout: float = 5.0
    ) -> List[Any]:
        """聚合响应"""
        # 创建任务列表
        tasks = []
        
        for target_name in target_names:
            target = self._get_target_by_name(target_name)
            if target and target.can_handle():
                # 创建异步任务
                task = asyncio.create_task(
                    self._get_target_response(message, target, timeout)
                )
                tasks.append((target, task))
        
        # 等待所有任务完成或超时
        try:
            responses = await asyncio.wait_for(
                asyncio.gather(*[task for _, task in tasks], return_exceptions=True),
                timeout=timeout
            )
            
            # 处理响应
            valid_responses = []
            for i, response in enumerate(responses):
                target = tasks[i][0]
                if not isinstance(response, Exception):
                    valid_responses.append({
                        "target": target.name,
                        "response": response
                    })
            
            return valid_responses
            
        except asyncio.TimeoutError:
            self.logger.warning("Response aggregation timeout", 
                             message_id=message.id,
                             target_count=len(tasks))
            return []
    
    async def _get_target_response(
        self, 
        message: Message, 
        target: RouteTarget, 
        timeout: float
    ) -> Any:
        """获取目标响应"""
        # 模拟异步响应获取
        await asyncio.sleep(0.1)  # 模拟处理时间
        return f"Response from {target.name}"
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """获取路由统计"""
        active_targets = sum(1 for t in self.targets.values() if t.can_handle())
        total_capacity = sum(t.capacity for t in self.targets.values())
        current_load = sum(t.current_load for t in self.targets.values())
        
        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules.values() if r.enabled),
            "total_targets": len(self.targets),
            "active_targets": active_targets,
            "total_capacity": total_capacity,
            "current_load": current_load,
            "load_percentage": (current_load / total_capacity * 100) if total_capacity > 0 else 0,
            "message_stats": self.stats.copy()
        }
    
    def get_target_stats(self) -> Dict[str, Any]:
        """获取目标统计"""
        target_stats = {}
        
        for target_id, target in self.targets.items():
            target_stats[target_id] = {
                "name": target.name,
                "type": target.type,
                "weight": target.weight,
                "capacity": target.capacity,
                "current_load": target.current_load,
                "load_percentage": (target.current_load / target.capacity * 100) if target.capacity > 0 else 0,
                "available": target.available,
                "usage_count": self.stats["targets_used"].get(target_id, 0)
            }
        
        return target_stats


class MessageBus:
    """消息总线"""
    
    def __init__(self, router: Optional[MessageRouter] = None):
        self.router = router or MessageRouter()
        self.logger = get_logger(self.__class__.__name__)
        
        # 消息队列
        self.incoming_queue = asyncio.Queue()
        self.outgoing_queue = asyncio.Queue()
        
        # 处理器
        self.processors: List[Callable] = []
        
        # 运行状态
        self.running = False
        self._tasks: List[asyncio.Task] = []
    
    async def start(self) -> None:
        """启动消息总线"""
        if self.running:
            return
        
        self.running = True
        
        # 创建处理任务
        self._tasks = [
            asyncio.create_task(self._process_incoming()),
            asyncio.create_task(self._process_outgoing()),
            asyncio.create_task(self._cleanup_old_messages())
        ]
        
        self.logger.info("Message bus started")
    
    async def stop(self) -> None:
        """停止消息总线"""
        if not self.running:
            return
        
        self.running = False
        
        # 取消所有任务
        for task in self._tasks:
            task.cancel()
        
        # 等待任务完成
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self.logger.info("Message bus stopped")
    
    async def send_message(self, message: Message, context: Optional[SessionContext] = None) -> None:
        """发送消息到总线"""
        await self.incoming_queue.put((message, context))
    
    async def receive_message(self) -> Optional[RoutedMessage]:
        """从总线接收消息"""
        try:
            return await asyncio.wait_for(self.outgoing_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None
    
    def add_processor(self, processor: Callable) -> None:
        """添加消息处理器"""
        self.processors.append(processor)
        self.logger.debug("Message processor added")
    
    async def _process_incoming(self) -> None:
        """处理入站消息"""
        while self.running:
            try:
                message, context = await self.incoming_queue.get()
                
                # 调用处理器
                for processor in self.processors:
                    try:
                        if asyncio.iscoroutinefunction(processor):
                            await processor(message, context)
                        else:
                            processor(message, context)
                    except Exception as e:
                        self.logger.error("Message processor error", error=str(e))
                
                # 路由消息
                routed_messages = await self.router.route_message(message, context)
                
                # 将路由的消息放入出站队列
                for routed_msg in routed_messages:
                    await self.outgoing_queue.put(routed_msg)
                
            except Exception as e:
                self.logger.error("Incoming message processing error", error=str(e))
    
    async def _process_outgoing(self) -> None:
        """处理出站消息"""
        while self.running:
            try:
                routed_msg = await self.outgoing_queue.get()
                
                # 这里可以发送到具体的目标
                # 例如WebSocket、适配器等
                
                # 标记处理完成，释放负载
                routed_msg.target.decrement_load()
                
            except Exception as e:
                self.logger.error("Outgoing message processing error", error=str(e))
    
    async def _cleanup_old_messages(self) -> None:
        """清理旧消息"""
        while self.running:
            try:
                await asyncio.sleep(300)  # 5分钟清理一次
                
                # 这里可以实现清理过期消息的逻辑
                # 例如清理超过一定时间的路由消息
                
                self.logger.debug("Message cleanup completed")
                
            except Exception as e:
                self.logger.error("Message cleanup error", error=str(e))
    
    @asynccontextmanager
    async def message_context(self, message: Message, context: Optional[SessionContext] = None):
        """消息上下文管理器"""
        try:
            await self.send_message(message, context)
            yield
        except Exception as e:
            self.logger.error("Message context error", error=str(e))
            raise


# 全局消息总线实例
_message_bus: Optional[MessageBus] = None


def get_message_bus() -> MessageBus:
    """获取全局消息总线"""
    global _message_bus
    if _message_bus is None:
        _message_bus = MessageBus()
    return _message_bus


async def start_message_bus() -> None:
    """启动全局消息总线"""
    bus = get_message_bus()
    await bus.start()


async def stop_message_bus() -> None:
    """停止全局消息总线"""
    global _message_bus
    if _message_bus:
        await _message_bus.stop()
        _message_bus = None


# 便利函数
async def route_message(message: Message, context: Optional[SessionContext] = None) -> List[RoutedMessage]:
    """路由消息便利函数"""
    bus = get_message_bus()
    return await bus.router.route_message(message, context)


async def send_to_message_bus(message: Message, context: Optional[SessionContext] = None) -> None:
    """发送到消息总线便利函数"""
    bus = get_message_bus()
    await bus.send_message(message, context)