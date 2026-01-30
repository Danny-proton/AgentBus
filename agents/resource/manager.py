"""
AgentBus Resource Management System
Agent资源管理系统
"""

from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
import asyncio
import uuid
import json
import psutil
from collections import defaultdict, deque

from ..core.types import (
    ResourceType, ResourceQuota, AgentStatus, AgentState, AgentConfig,
    AgentMetrics, SystemMetrics
)


class ResourceManager:
    """资源管理器"""
    
    def __init__(self, manager_id: str = "default"):
        self.manager_id = manager_id
        self.logger = self._get_logger()
        
        # 资源池
        self.resource_pools: Dict[ResourceType, ResourcePool] = {}
        self.agent_allocations: Dict[str, Dict[ResourceType, float]] = defaultdict(dict)
        self.pending_requests: List['ResourceRequest'] = []
        
        # 资源监控
        self.resource_monitors: Dict[ResourceType, 'ResourceMonitor'] = {}
        self.usage_history: Dict[ResourceType, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # 策略配置
        self.allocation_strategies = {
            ResourceType.CPU: FairShareStrategy(),
            ResourceType.MEMORY: FirstFitStrategy(),
            ResourceType.STORAGE: BestFitStrategy(),
            ResourceType.NETWORK: RateLimitingStrategy(),
            ResourceType.GPU: PriorityStrategy(),
            ResourceType.DATABASE_CONNECTIONS: ConnectionPoolStrategy(),
            ResourceType.API_RATE_LIMIT: TokenBucketStrategy(),
            ResourceType.CONCURRENT_TASKS: SlotBasedStrategy()
        }
        
        # 告警和限制
        self.resource_alerts: Dict[ResourceType, 'ResourceAlert'] = {}
        self.global_limits: Dict[ResourceType, float] = {}
        self.per_agent_limits: Dict[str, Dict[ResourceType, float]] = {}
        
        # 运行状态
        self.running = False
        self.management_tasks: List[asyncio.Task] = []
        
        # 统计信息
        self.stats = {
            "total_allocations": 0,
            "total_releases": 0,
            "total_denied": 0,
            "peak_usage": defaultdict(float),
            "average_usage": defaultdict(float),
            "allocation_latency": deque(maxlen=100)
        }
        
        # 初始化默认资源池
        self._initialize_default_pools()
    
    def _get_logger(self):
        """获取日志记录器"""
        return f"resource.manager.{self.manager_id}"
    
    def _initialize_default_pools(self):
        """初始化默认资源池"""
        # CPU资源池
        cpu_count = psutil.cpu_count()
        self.resource_pools[ResourceType.CPU] = ResourcePool(
            resource_type=ResourceType.CPU,
            total_capacity=cpu_count,
            unit="cores"
        )
        
        # 内存资源池
        memory_gb = psutil.virtual_memory().total / (1024**3)
        self.resource_pools[ResourceType.MEMORY] = ResourcePool(
            resource_type=ResourceType.MEMORY,
            total_capacity=memory_gb,
            unit="GB"
        )
        
        # 存储资源池
        storage_gb = psutil.disk_usage('/').total / (1024**3)
        self.resource_pools[ResourceType.STORAGE] = ResourcePool(
            resource_type=ResourceType.STORAGE,
            total_capacity=storage_gb,
            unit="GB"
        )
        
        # GPU资源池（如果可用）
        try:
            import GPUtil
            gpu_count = len(GPUtil.getGPUs())
            if gpu_count > 0:
                self.resource_pools[ResourceType.GPU] = ResourcePool(
                    resource_type=ResourceType.GPU,
                    total_capacity=gpu_count,
                    unit="GPUs"
                )
        except ImportError:
            pass
        
        # 数据库连接池
        self.resource_pools[ResourceType.DATABASE_CONNECTIONS] = ResourcePool(
            resource_type=ResourceType.DATABASE_CONNECTIONS,
            total_capacity=100,
            unit="connections"
        )
        
        # API速率限制
        self.resource_pools[ResourceType.API_RATE_LIMIT] = ResourcePool(
            resource_type=ResourceType.API_RATE_LIMIT,
            total_capacity=1000,
            unit="requests/minute"
        )
        
        # 并发任务限制
        self.resource_pools[ResourceType.CONCURRENT_TASKS] = ResourcePool(
            resource_type=ResourceType.CONCURRENT_TASKS,
            total_capacity=50,
            unit="tasks"
        )
    
    async def start(self):
        """启动资源管理器"""
        if self.running:
            return
        
        self.running = True
        
        # 启动管理任务
        self.management_tasks.extend([
            asyncio.create_task(self._resource_monitoring_loop()),
            asyncio.create_task(self._allocation_processing_loop()),
            asyncio.create_task(self._cleanup_loop())
        ])
        
        self.logger.info("Resource manager started")
    
    async def stop(self):
        """停止资源管理器"""
        if not self.running:
            return
        
        self.running = False
        
        # 取消所有管理任务
        for task in self.management_tasks:
            task.cancel()
        
        if self.management_tasks:
            await asyncio.gather(*self.management_tasks, return_exceptions=True)
        
        self.management_tasks.clear()
        self.logger.info("Resource manager stopped")
    
    def create_resource_pool(self, resource_type: ResourceType, capacity: float, 
                           unit: str = "", reserved: float = 0.0) -> ResourcePool:
        """创建资源池"""
        pool = ResourcePool(
            resource_type=resource_type,
            total_capacity=capacity,
            unit=unit,
            reserved=reserved
        )
        
        self.resource_pools[resource_type] = pool
        self.logger.info(f"Resource pool created: {resource_type.value} ({capacity} {unit})")
        return pool
    
    async def request_resources(self, agent_id: str, requests: Dict[ResourceType, float],
                              priority: int = 0, timeout: float = 30.0) -> 'ResourceAllocation':
        """请求资源"""
        allocation_id = str(uuid.uuid4())
        
        request = ResourceRequest(
            allocation_id=allocation_id,
            agent_id=agent_id,
            requests=requests,
            priority=priority,
            created_at=datetime.now(),
            timeout=timeout
        )
        
        # 添加到待处理队列
        self.pending_requests.append(request)
        
        # 按优先级排序
        self.pending_requests.sort(key=lambda r: r.priority, reverse=True)
        
        self.logger.info(f"Resource request submitted: {agent_id} {requests}")
        return request
    
    async def allocate_resources(self, agent_id: str, requests: Dict[ResourceType, float],
                               config: AgentConfig) -> bool:
        """分配资源"""
        allocation = {}
        allocation_failures = {}
        
        for resource_type, amount in requests.items():
            # 检查资源池
            if resource_type not in self.resource_pools:
                allocation_failures[resource_type] = f"No pool for {resource_type}"
                continue
            
            pool = self.resource_pools[resource_type]
            
            # 检查全局限制
            if resource_type in self.global_limits:
                total_allocated = self._get_total_allocated(resource_type)
                if total_allocated + amount > self.global_limits[resource_type]:
                    allocation_failures[resource_type] = "Global limit exceeded"
                    continue
            
            # 检查每个Agent的限制
            if agent_id in self.per_agent_limits:
                agent_limits = self.per_agent_limits[agent_id]
                if resource_type in agent_limits:
                    if amount > agent_limits[resource_type]:
                        allocation_failures[resource_type] = "Agent limit exceeded"
                        continue
            
            # 应用分配策略
            strategy = self.allocation_strategies.get(resource_type)
            if strategy:
                allocation_result = await strategy.allocate(
                    pool, amount, agent_id, self.agent_allocations
                )
                
                if allocation_result.success:
                    allocation[resource_type] = allocation_result.allocated_amount
                    pool.allocate(allocation_result.allocated_amount)
                else:
                    allocation_failures[resource_type] = allocation_result.reason
            else:
                # 默认策略：直接分配
                if pool.allocate(amount):
                    allocation[resource_type] = amount
                else:
                    allocation_failures[resource_type] = "Insufficient resources"
        
        # 记录分配
        if allocation:
            self.agent_allocations[agent_id].update(allocation)
            self.stats["total_allocations"] += 1
            
            # 更新统计
            for resource_type, amount in allocation.items():
                self._update_resource_stats(resource_type, amount, True)
            
            self.logger.info(f"Resources allocated to {agent_id}: {allocation}")
        
        # 记录失败
        if allocation_failures:
            self.stats["total_denied"] += len(allocation_failures)
            self.logger.warning(f"Resource allocation partially failed for {agent_id}: {allocation_failures}")
        
        return len(allocation_failures) == 0
    
    async def release_resources(self, agent_id: str, resources: Dict[ResourceType, float]):
        """释放资源"""
        released = {}
        
        for resource_type, amount in resources.items():
            if (resource_type in self.agent_allocations[agent_id] and 
                resource_type in self.resource_pools):
                
                pool = self.resource_pools[resource_type]
                current_allocation = self.agent_allocations[agent_id][resource_type]
                
                # 释放较小的数量
                release_amount = min(amount, current_allocation)
                
                if pool.deallocate(release_amount):
                    released[resource_type] = release_amount
                    self.agent_allocations[agent_id][resource_type] -= release_amount
                    
                    # 如果分配为0，删除该资源类型
                    if self.agent_allocations[agent_id][resource_type] <= 0:
                        del self.agent_allocations[agent_id][resource_type]
        
        if released:
            self.stats["total_releases"] += 1
            
            # 更新统计
            for resource_type, amount in released.items():
                self._update_resource_stats(resource_type, amount, False)
            
            self.logger.info(f"Resources released from {agent_id}: {released}")
    
    async def enforce_limits(self, agent_id: str, current_usage: Dict[ResourceType, float]):
        """执行资源限制"""
        violations = []
        
        # 检查每个Agent的限制
        if agent_id in self.per_agent_limits:
            limits = self.per_agent_limits[agent_id]
            
            for resource_type, limit in limits.items():
                if resource_type in current_usage:
                    usage = current_usage[resource_type]
                    if usage > limit:
                        violations.append({
                            "resource_type": resource_type,
                            "limit": limit,
                            "usage": usage,
                            "excess": usage - limit
                        })
        
        # 检查全局限制
        for resource_type, global_limit in self.global_limits.items():
            if resource_type in current_usage:
                usage = current_usage[resource_type]
                if usage > global_limit:
                    violations.append({
                        "resource_type": resource_type,
                        "limit": global_limit,
                        "usage": usage,
                        "excess": usage - global_limit,
                        "scope": "global"
                    })
        
        # 处理违规
        for violation in violations:
            await self._handle_resource_violation(agent_id, violation)
        
        return violations
    
    def set_global_limit(self, resource_type: ResourceType, limit: float):
        """设置全局限制"""
        self.global_limits[resource_type] = limit
        self.logger.info(f"Global limit set for {resource_type.value}: {limit}")
    
    def set_agent_limit(self, agent_id: str, resource_type: ResourceType, limit: float):
        """设置Agent限制"""
        if agent_id not in self.per_agent_limits:
            self.per_agent_limits[agent_id] = {}
        
        self.per_agent_limits[agent_id][resource_type] = limit
        self.logger.info(f"Agent limit set for {agent_id} {resource_type.value}: {limit}")
    
    def get_resource_status(self, resource_type: Optional[ResourceType] = None) -> Dict[str, Any]:
        """获取资源状态"""
        if resource_type:
            if resource_type not in self.resource_pools:
                return {}
            
            pool = self.resource_pools[resource_type]
            total_allocated = self._get_total_allocated(resource_type)
            
            return {
                "resource_type": resource_type.value,
                "total_capacity": pool.total_capacity,
                "reserved": pool.reserved,
                "used": pool.used,
                "available": pool.available,
                "utilization": pool.get_usage_rate() * 100,
                "allocation_count": len([a for a in self.agent_allocations.values() 
                                      if resource_type in a])
            }
        
        # 返回所有资源状态
        status = {}
        for resource_type, pool in self.resource_pools.items():
            status[resource_type.value] = self.get_resource_status(resource_type)
        
        return status
    
    def get_agent_allocations(self, agent_id: str) -> Dict[str, Any]:
        """获取Agent的资源分配"""
        allocations = self.agent_allocations.get(agent_id, {})
        
        allocation_details = {}
        for resource_type, amount in allocations.items():
            pool = self.resource_pools.get(resource_type)
            allocation_details[resource_type.value] = {
                "amount": amount,
                "unit": pool.unit if pool else "",
                "percentage": (amount / pool.total_capacity * 100) if pool else 0
            }
        
        return {
            "agent_id": agent_id,
            "allocations": allocation_details,
            "total_resources": len(allocations)
        }
    
    def get_system_utilization(self) -> Dict[str, Any]:
        """获取系统资源利用率"""
        utilization = {}
        
        for resource_type, pool in self.resource_pools.items():
            utilization[resource_type.value] = {
                "utilization_rate": pool.get_usage_rate(),
                "used": pool.used,
                "available": pool.available,
                "total": pool.total_capacity
            }
        
        # 计算平均利用率
        total_utilization = sum(u["utilization_rate"] for u in utilization.values())
        average_utilization = total_utilization / len(utilization) if utilization else 0
        
        return {
            "resource_utilization": utilization,
            "average_utilization": average_utilization,
            "timestamp": datetime.now().isoformat()
        }
    
    # === 私有方法 ===
    
    def _get_total_allocated(self, resource_type: ResourceType) -> float:
        """获取总分配量"""
        total = 0
        for allocations in self.agent_allocations.values():
            if resource_type in allocations:
                total += allocations[resource_type]
        return total
    
    def _update_resource_stats(self, resource_type: ResourceType, amount: float, allocated: bool):
        """更新资源统计"""
        if allocated:
            # 更新峰值使用
            if amount > self.stats["peak_usage"][resource_type.value]:
                self.stats["peak_usage"][resource_type.value] = amount
        else:
            # 更新平均使用（简化计算）
            if resource_type.value in self.stats["average_usage"]:
                current_avg = self.stats["average_usage"][resource_type.value]
                # 这里可以维护历史平均值
                pass
    
    async def _handle_resource_violation(self, agent_id: str, violation: Dict[str, Any]):
        """处理资源违规"""
        self.logger.warning(f"Resource violation for {agent_id}: {violation}")
        
        # 这里可以触发告警或执行其他处理逻辑
        # 例如：限制Agent操作、暂停Agent等
    
    async def _resource_monitoring_loop(self):
        """资源监控循环"""
        while self.running:
            try:
                # 收集当前资源使用情况
                current_usage = await self._collect_current_usage()
                
                # 检查违规
                for agent_id in self.agent_allocations.keys():
                    await self.enforce_limits(agent_id, current_usage.get(agent_id, {}))
                
                # 更新使用历史
                for resource_type, usage in current_usage.items():
                    self.usage_history[resource_type].append({
                        "timestamp": datetime.now(),
                        "usage": usage
                    })
                
                await asyncio.sleep(30)  # 每30秒监控一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Resource monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _allocation_processing_loop(self):
        """分配处理循环"""
        while self.running:
            try:
                # 处理待处理的分配请求
                if self.pending_requests:
                    request = self.pending_requests.pop(0)
                    
                    # 检查超时
                    if datetime.now() - request.created_at > timedelta(seconds=request.timeout):
                        self.logger.warning(f"Allocation request timed out: {request.allocation_id}")
                        continue
                    
                    # 尝试分配资源
                    success = await self.allocate_resources(
                        request.agent_id, 
                        request.requests, 
                        request.config
                    )
                    
                    if not success:
                        # 分配失败，重新加入队列
                        self.pending_requests.append(request)
                        await asyncio.sleep(1)  # 等待一段时间再重试
                
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Allocation processing loop error: {e}")
                await asyncio.sleep(5)
    
    async def _cleanup_loop(self):
        """清理循环"""
        while self.running:
            try:
                # 清理过期的分配记录
                await self._cleanup_stale_allocations()
                
                # 清理历史数据
                await self._cleanup_history_data()
                
                await asyncio.sleep(3600)  # 每小时清理一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(3600)
    
    async def _collect_current_usage(self) -> Dict[str, Dict[ResourceType, float]]:
        """收集当前资源使用情况"""
        # 简化实现：从Agent分配中获取使用情况
        usage = {}
        for agent_id, allocations in self.agent_allocations.items():
            usage[agent_id] = allocations.copy()
        return usage
    
    async def _cleanup_stale_allocations(self):
        """清理过期的分配记录"""
        # 这里可以添加清理逻辑，例如清理长时间不活跃的Agent的分配
        pass
    
    async def _cleanup_history_data(self):
        """清理历史数据"""
        cutoff_time = datetime.now() - timedelta(days=7)  # 保留7天的历史
        
        for resource_type in self.usage_history:
            # 清理资源使用历史
            while (self.usage_history[resource_type] and 
                   self.usage_history[resource_type][0]["timestamp"] < cutoff_time):
                self.usage_history[resource_type].popleft()


class ResourcePool:
    """资源池"""
    
    def __init__(self, resource_type: ResourceType, total_capacity: float, 
                 unit: str = "", reserved: float = 0.0):
        self.resource_type = resource_type
        self.total_capacity = total_capacity
        self.unit = unit
        self.reserved = reserved
        self.used = 0.0
        self.available = total_capacity - reserved - self.used
    
    def allocate(self, amount: float) -> bool:
        """分配资源"""
        if amount <= self.available:
            self.used += amount
            self.available -= amount
            return True
        return False
    
    def deallocate(self, amount: float) -> bool:
        """释放资源"""
        if amount <= self.used:
            self.used -= amount
            self.available += amount
            return True
        return False
    
    def get_usage_rate(self) -> float:
        """获取使用率"""
        if self.total_capacity == 0:
            return 0.0
        return self.used / self.total_capacity
    
    def get_available_rate(self) -> float:
        """获取可用率"""
        if self.total_capacity == 0:
            return 0.0
        return self.available / self.total_capacity


class AllocationStrategy(ABC):
    """资源分配策略"""
    
    @abstractmethod
    async def allocate(self, pool: ResourcePool, requested_amount: float, 
                      agent_id: str, current_allocations: Dict[str, Dict]) -> 'AllocationResult':
        """分配资源"""
        pass


class FairShareStrategy(AllocationStrategy):
    """公平分配策略"""
    
    async def allocate(self, pool: ResourcePool, requested_amount: float, 
                      agent_id: str, current_allocations: Dict[str, Dict]) -> 'AllocationResult':
        """公平分配"""
        total_agents = len(current_allocations)
        if total_agents == 0:
            fair_share = pool.available
        else:
            fair_share = pool.available / total_agents
        
        allocated_amount = min(requested_amount, fair_share)
        
        if allocated_amount > 0:
            return AllocationResult(True, allocated_amount)
        else:
            return AllocationResult(False, 0, "Insufficient resources for fair share")


class FirstFitStrategy(AllocationStrategy):
    """首次适应策略"""
    
    async def allocate(self, pool: ResourcePool, requested_amount: float, 
                      agent_id: str, current_allocations: Dict[str, Dict]) -> 'AllocationResult':
        """首次适应"""
        allocated_amount = min(requested_amount, pool.available)
        
        if allocated_amount > 0:
            return AllocationResult(True, allocated_amount)
        else:
            return AllocationResult(False, 0, "Insufficient resources")


class BestFitStrategy(AllocationStrategy):
    """最佳适应策略"""
    
    async def allocate(self, pool: ResourcePool, requested_amount: float, 
                      agent_id: str, current_allocations: Dict[str, Dict]) -> 'AllocationResult':
        """最佳适应"""
        allocated_amount = min(requested_amount, pool.available)
        
        if allocated_amount > 0:
            return AllocationResult(True, allocated_amount)
        else:
            return AllocationResult(False, 0, "Insufficient resources")


class PriorityStrategy(AllocationStrategy):
    """优先级策略"""
    
    async def allocate(self, pool: ResourcePool, requested_amount: float, 
                      agent_id: str, current_allocations: Dict[str, Dict]) -> 'AllocationResult':
        """优先级分配"""
        # 简化实现：总是优先分配
        allocated_amount = min(requested_amount, pool.available)
        
        if allocated_amount > 0:
            return AllocationResult(True, allocated_amount)
        else:
            return AllocationResult(False, 0, "Insufficient resources")


class RateLimitingStrategy(AllocationStrategy):
    """速率限制策略"""
    
    async def allocate(self, pool: ResourcePool, requested_amount: float, 
                      agent_id: str, current_allocations: Dict[str, Dict]) -> 'AllocationResult':
        """速率限制分配"""
        # 检查当前速率
        current_usage = current_allocations.get(agent_id, {}).get(self.resource_type, 0)
        
        # 应用速率限制（例如每分钟请求数）
        max_rate = 100  # 每分钟100个请求
        if current_usage + requested_amount > max_rate:
            allocated_amount = max(0, max_rate - current_usage)
        else:
            allocated_amount = requested_amount
        
        if allocated_amount > 0:
            return AllocationResult(True, allocated_amount)
        else:
            return AllocationResult(False, 0, "Rate limit exceeded")


class ConnectionPoolStrategy(AllocationStrategy):
    """连接池策略"""
    
    async def allocate(self, pool: ResourcePool, requested_amount: float, 
                      agent_id: str, current_allocations: Dict[str, Dict]) -> 'AllocationResult':
        """连接池分配"""
        allocated_amount = min(requested_amount, pool.available)
        
        if allocated_amount > 0:
            return AllocationResult(True, allocated_amount)
        else:
            return AllocationResult(False, 0, "No available connections")


class TokenBucketStrategy(AllocationStrategy):
    """令牌桶策略"""
    
    def __init__(self):
        self.tokens = 1000  # 初始令牌数
        self.refill_rate = 10  # 每秒补充令牌数
        self.last_refill = datetime.now()
    
    async def allocate(self, pool: ResourcePool, requested_amount: float, 
                      agent_id: str, current_allocations: Dict[str, Dict]) -> 'AllocationResult':
        """令牌桶分配"""
        # 补充令牌
        now = datetime.now()
        time_passed = (now - self.last_refill).total_seconds()
        self.tokens += time_passed * self.refill_rate
        self.tokens = min(self.tokens, pool.total_capacity)
        self.last_refill = now
        
        # 分配令牌
        allocated_amount = min(requested_amount, self.tokens)
        
        if allocated_amount > 0:
            self.tokens -= allocated_amount
            return AllocationResult(True, allocated_amount)
        else:
            return AllocationResult(False, 0, "No tokens available")


class SlotBasedStrategy(AllocationStrategy):
    """基于槽位的策略"""
    
    async def allocate(self, pool: ResourcePool, requested_amount: float, 
                      agent_id: str, current_allocations: Dict[str, Dict]) -> 'AllocationResult':
        """槽位分配"""
        allocated_amount = min(requested_amount, pool.available)
        
        if allocated_amount > 0:
            return AllocationResult(True, allocated_amount)
        else:
            return AllocationResult(False, 0, "No slots available")


@dataclass
class ResourceRequest:
    """资源请求"""
    allocation_id: str
    agent_id: str
    requests: Dict[ResourceType, float]
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    timeout: float = 30.0
    status: str = "pending"


@dataclass
class AllocationResult:
    """分配结果"""
    success: bool
    allocated_amount: float
    reason: str = ""
    
    def __post_init__(self):
        if self.allocated_amount < 0:
            self.allocated_amount = 0


class ResourceMonitor(ABC):
    """资源监控器"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def collect_metrics(self) -> Dict[str, Any]:
        """收集指标"""
        pass


@dataclass
class ResourceAlert:
    """资源告警"""
    resource_type: ResourceType
    threshold: float
    level: AlertLevel
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False


def create_resource_manager(manager_id: str = "default") -> ResourceManager:
    """创建资源管理器"""
    return ResourceManager(manager_id)


def get_resource_manager(manager_id: str = "default") -> ResourceManager:
    """获取资源管理器（单例）"""
    # 这里可以实现单例模式
    return ResourceManager(manager_id)