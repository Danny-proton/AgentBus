"""
限流系统 - Rate Limiting System

提供多种限流策略，包括令牌桶、滑动窗口、固定窗口等。
防止API滥用和DDoS攻击。
"""

import time
import threading
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import bisect
from ..core.settings import Settings
from ..storage.database import Database
from ..storage.memory import MemoryStorage


class RateLimitStrategy(Enum):
    """限流策略"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    CONCURRENT = "concurrent"


class RateLimitScope(Enum):
    """限流范围"""
    GLOBAL = "global"
    USER = "user"
    IP = "ip"
    ENDPOINT = "endpoint"
    USER_ENDPOINT = "user_endpoint"


@dataclass
class RateLimitRule:
    """限流规则"""
    id: str
    name: str
    strategy: RateLimitStrategy
    scope: RateLimitScope
    limit: int  # 限制数量
    window: int  # 时间窗口（秒）
    burst: Optional[int] = None  # 突发限制（用于令牌桶）
    refill_rate: Optional[float] = None  # 令牌补充速率
    endpoint_patterns: List[str] = None  # 端点模式
    user_patterns: List[str] = None  # 用户模式
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.endpoint_patterns is None:
            self.endpoint_patterns = []
        if self.user_patterns is None:
            self.user_patterns = []
        if self.metadata is None:
            self.metadata = {}
    
    def matches_endpoint(self, endpoint: str) -> bool:
        """检查是否匹配端点"""
        if not self.endpoint_patterns:
            return True
        
        for pattern in self.endpoint_patterns:
            if self._match_pattern(endpoint, pattern):
                return True
        return False
    
    def matches_user(self, user_id: str) -> bool:
        """检查是否匹配用户"""
        if not self.user_patterns:
            return True
        
        for pattern in self.user_patterns:
            if self._match_pattern(user_id, pattern):
                return True
        return False
    
    def _match_pattern(self, value: str, pattern: str) -> bool:
        """简单的模式匹配"""
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return value.startswith(pattern[:-1])
        if pattern.startswith("*"):
            return value.endswith(pattern[1:])
        return value == pattern


class RateLimitExceeded(Exception):
    """限流超限异常"""
    
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class RateLimitStore(ABC):
    """限流存储抽象基类"""
    
    @abstractmethod
    async def increment(self, key: str, window: int) -> int:
        """增加计数"""
        pass
    
    @abstractmethod
    async def get_count(self, key: str, window: int = None) -> int:
        """获取计数"""
        pass
    
    @abstractmethod
    async def reset(self, key: str) -> bool:
        """重置计数"""
        pass


class MemoryRateLimitStore(RateLimitStore):
    """内存限流存储"""
    
    def __init__(self):
        self._counters: Dict[str, deque] = defaultdict(deque)
        self._lock = threading.RLock()
    
    async def increment(self, key: str, window: int) -> int:
        """增加计数"""
        with self._lock:
            now = time.time()
            window_start = now - window
            
            # 清理过期记录
            counter = self._counters[key]
            while counter and counter[0] < window_start:
                counter.popleft()
            
            # 添加当前请求
            counter.append(now)
            
            return len(counter)
    
    async def get_count(self, key: str, window: int = None) -> int:
        """获取计数"""
        with self._lock:
            now = time.time()
            window_start = now - (window or 3600)  # 默认1小时
            
            counter = self._counters[key]
            # 清理过期记录
            while counter and counter[0] < window_start:
                counter.popleft()
            
            return len(counter)
    
    async def reset(self, key: str) -> bool:
        """重置计数"""
        with self._lock:
            self._counters.pop(key, None)
            return True


class DatabaseRateLimitStore(RateLimitStore):
    """数据库限流存储"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def increment(self, key: str, window: int) -> int:
        """增加计数"""
        # 这里应该实现具体的数据库逻辑
        # 简化实现，返回模拟值
        return 1
    
    async def get_count(self, key: str, window: int = None) -> int:
        """获取计数"""
        # 这里应该实现具体的数据库逻辑
        # 简化实现，返回模拟值
        return 0
    
    async def reset(self, key: str) -> bool:
        """重置计数"""
        # 这里应该实现具体的数据库逻辑
        return True


class RateLimitAlgorithm(ABC):
    """限流算法抽象基类"""
    
    @abstractmethod
    async def check_rate_limit(self, key: str, rule: RateLimitRule) -> bool:
        """检查是否超出限流"""
        pass
    
    @abstractmethod
    async def record_request(self, key: str, rule: RateLimitRule) -> int:
        """记录请求"""
        pass


class FixedWindowAlgorithm(RateLimitAlgorithm):
    """固定窗口算法"""
    
    def __init__(self, store: RateLimitStore):
        self.store = store
    
    async def check_rate_limit(self, key: str, rule: RateLimitRule) -> bool:
        """检查固定窗口限流"""
        count = await self.store.get_count(key, rule.window)
        return count < rule.limit
    
    async def record_request(self, key: str, rule: RateLimitRule) -> int:
        """记录固定窗口请求"""
        count = await self.store.increment(key, rule.window)
        
        if count > rule.limit:
            raise RateLimitExceeded(
                f"Rate limit exceeded for {key}",
                retry_after=rule.window
            )
        
        return count


class SlidingWindowAlgorithm(RateLimitAlgorithm):
    """滑动窗口算法"""
    
    def __init__(self, store: RateLimitStore):
        self.store = store
    
    async def check_rate_limit(self, key: str, rule: RateLimitRule) -> bool:
        """检查滑动窗口限流"""
        count = await self.store.get_count(key, rule.window)
        return count < rule.limit
    
    async def record_request(self, key: str, rule: RateLimitRule) -> int:
        """记录滑动窗口请求"""
        count = await self.store.increment(key, rule.window)
        
        if count > rule.limit:
            raise RateLimitExceeded(
                f"Rate limit exceeded for {key}",
                retry_after=rule.window
            )
        
        return count


class TokenBucketAlgorithm(RateLimitAlgorithm):
    """令牌桶算法"""
    
    def __init__(self, store: RateLimitStore):
        self.store = store
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    async def check_rate_limit(self, key: str, rule: RateLimitRule) -> bool:
        """检查令牌桶限流"""
        with self._lock:
            bucket = self._get_bucket(key, rule)
            
            # 计算当前令牌数
            now = time.time()
            elapsed = now - bucket['last_refill']
            
            # 补充令牌
            tokens_to_add = elapsed * (rule.refill_rate or 1.0)
            bucket['tokens'] = min(
                rule.burst or rule.limit,
                bucket['tokens'] + tokens_to_add
            )
            bucket['last_refill'] = now
            
            # 检查是否有足够的令牌
            return bucket['tokens'] >= 1.0
    
    async def record_request(self, key: str, rule: RateLimitRule) -> float:
        """记录令牌桶请求"""
        with self._lock:
            bucket = self._get_bucket(key, rule)
            
            now = time.time()
            elapsed = now - bucket['last_refill']
            
            # 补充令牌
            tokens_to_add = elapsed * (rule.refill_rate or 1.0)
            bucket['tokens'] = min(
                rule.burst or rule.limit,
                bucket['tokens'] + tokens_to_add
            )
            bucket['last_refill'] = now
            
            # 消耗令牌
            if bucket['tokens'] >= 1.0:
                bucket['tokens'] -= 1.0
                remaining_tokens = bucket['tokens']
                
                # 计算下次补充时间
                if remaining_tokens < 1.0 and rule.refill_rate:
                    time_to_refill = (1.0 - remaining_tokens) / rule.refill_rate
                    raise RateLimitExceeded(
                        f"Rate limit exceeded for {key}",
                        retry_after=int(time_to_refill)
                    )
                
                return remaining_tokens
            else:
                # 计算下次令牌可用时间
                if rule.refill_rate:
                    time_to_refill = (1.0 - bucket['tokens']) / rule.refill_rate
                    raise RateLimitExceeded(
                        f"Rate limit exceeded for {key}",
                        retry_after=int(time_to_refill)
                    )
                else:
                    raise RateLimitExceeded(f"Rate limit exceeded for {key}")
    
    def _get_bucket(self, key: str, rule: RateLimitRule) -> Dict[str, Any]:
        """获取或创建令牌桶"""
        if key not in self._buckets:
            self._buckets[key] = {
                'tokens': rule.burst or rule.limit,
                'last_refill': time.time()
            }
        
        return self._buckets[key]


class LeakyBucketAlgorithm(RateLimitAlgorithm):
    """漏桶算法"""
    
    def __init__(self, store: RateLimitStore):
        self.store = store
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    async def check_rate_limit(self, key: str, rule: RateLimitRule) -> bool:
        """检查漏桶限流"""
        with self._lock:
            bucket = self._get_bucket(key, rule)
            
            now = time.time()
            elapsed = now - bucket['last_processed']
            
            # 处理水（请求）
            water_to_process = elapsed * (rule.refill_rate or 1.0)
            bucket['water'] = max(0, bucket['water'] - water_to_process)
            bucket['last_processed'] = now
            
            # 检查是否溢出
            return bucket['water'] < rule.limit
    
    async def record_request(self, key: str, rule: RateLimitRule) -> float:
        """记录漏桶请求"""
        with self._lock:
            bucket = self._get_bucket(key, rule)
            
            now = time.time()
            elapsed = now - bucket['last_processed']
            
            # 处理水（请求）
            water_to_process = elapsed * (rule.refill_rate or 1.0)
            bucket['water'] = max(0, bucket['water'] - water_to_process)
            bucket['last_processed'] = now
            
            # 添加新请求
            bucket['water'] += 1.0
            
            # 检查是否溢出
            if bucket['water'] > rule.limit:
                # 计算水退去时间
                if rule.refill_rate:
                    time_to_empty = bucket['water'] / rule.refill_rate
                    raise RateLimitExceeded(
                        f"Rate limit exceeded for {key}",
                        retry_after=int(time_to_empty)
                    )
                else:
                    raise RateLimitExceeded(f"Rate limit exceeded for {key}")
            
            return bucket['water']
    
    def _get_bucket(self, key: str, rule: RateLimitRule) -> Dict[str, Any]:
        """获取或创建漏桶"""
        if key not in self._buckets:
            self._buckets[key] = {
                'water': 0.0,
                'last_processed': time.time()
            }
        
        return self._buckets[key]


class RateLimiter:
    """限流器主类"""
    
    def __init__(self, settings: Settings, db: Database = None, memory: MemoryStorage = None):
        self.settings = settings
        self.db = db
        self.memory = memory
        
        # 选择存储实现
        if db:
            self.store = DatabaseRateLimitStore(db)
        else:
            self.store = MemoryRateLimitStore()
        
        # 初始化算法
        self.algorithms = {
            RateLimitStrategy.FIXED_WINDOW: FixedWindowAlgorithm(self.store),
            RateLimitStrategy.SLIDING_WINDOW: SlidingWindowAlgorithm(self.store),
            RateLimitStrategy.TOKEN_BUCKET: TokenBucketAlgorithm(self.store),
            RateLimitStrategy.LEAKY_BUCKET: LeakyBucketAlgorithm(self.store),
        }
        
        # 限流规则
        self.rules: Dict[str, RateLimitRule] = {}
        self._rules_lock = threading.RLock()
        
        # 加载默认规则
        self._load_default_rules()
    
    def _load_default_rules(self):
        """加载默认限流规则"""
        default_rules = [
            RateLimitRule(
                id="global_api_limit",
                name="全局API限制",
                strategy=RateLimitStrategy.SLIDING_WINDOW,
                scope=RateLimitScope.GLOBAL,
                limit=1000,
                window=3600,  # 1小时
                endpoint_patterns=["/api/*"]
            ),
            RateLimitRule(
                id="user_api_limit",
                name="用户API限制",
                strategy=RateLimitStrategy.SLIDING_WINDOW,
                scope=RateLimitScope.USER,
                limit=100,
                window=3600,  # 1小时
                endpoint_patterns=["/api/*"]
            ),
            RateLimitRule(
                id="ip_api_limit",
                name="IP API限制",
                strategy=RateLimitStrategy.SLIDING_WINDOW,
                scope=RateLimitScope.IP,
                limit=50,
                window=3600,  # 1小时
                endpoint_patterns=["/api/*"]
            ),
            RateLimitRule(
                id="login_attempts",
                name="登录尝试限制",
                strategy=RateLimitStrategy.FIXED_WINDOW,
                scope=RateLimitScope.IP,
                limit=5,
                window=900,  # 15分钟
                endpoint_patterns=["/auth/login"]
            ),
            RateLimitRule(
                id="token_bucket_example",
                name="令牌桶示例",
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                scope=RateLimitScope.USER_ENDPOINT,
                limit=10,
                window=60,  # 1分钟
                burst=20,
                refill_rate=0.5,  # 每秒0.5个令牌
                endpoint_patterns=["/api/heavy-operation"]
            )
        ]
        
        for rule in default_rules:
            self.add_rule(rule)
    
    def add_rule(self, rule: RateLimitRule):
        """添加限流规则"""
        with self._rules_lock:
            self.rules[rule.id] = rule
    
    def remove_rule(self, rule_id: str) -> bool:
        """移除限流规则"""
        with self._rules_lock:
            return self.rules.pop(rule_id, None) is not None
    
    def get_rule(self, rule_id: str) -> Optional[RateLimitRule]:
        """获取限流规则"""
        with self._rules_lock:
            return self.rules.get(rule_id)
    
    def get_rules_for_endpoint(self, endpoint: str) -> List[RateLimitRule]:
        """获取适用于端点的规则"""
        with self._rules_lock:
            return [rule for rule in self.rules.values() if rule.matches_endpoint(endpoint)]
    
    async def check_rate_limit(self, endpoint: str, user_id: str = None, 
                              ip_address: str = None, **kwargs) -> Dict[str, Any]:
        """检查限流"""
        rules = self.get_rules_for_endpoint(endpoint)
        
        if not rules:
            return {"allowed": True, "rules_checked": 0}
        
        results = []
        overall_allowed = True
        
        for rule in rules:
            # 检查用户模式
            if user_id and not rule.matches_user(user_id):
                continue
            
            # 生成限流键
            key = self._generate_key(rule, user_id, ip_address, endpoint, **kwargs)
            
            try:
                # 检查限流
                allowed = await self.algorithms[rule.strategy].check_rate_limit(key, rule)
                
                results.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "strategy": rule.strategy.value,
                    "scope": rule.scope.value,
                    "allowed": allowed,
                    "limit": rule.limit,
                    "window": rule.window
                })
                
                if not allowed:
                    overall_allowed = False
                    
            except Exception as e:
                results.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "strategy": rule.strategy.value,
                    "scope": rule.scope.value,
                    "allowed": False,
                    "error": str(e),
                    "limit": rule.limit,
                    "window": rule.window
                })
                overall_allowed = False
        
        return {
            "allowed": overall_allowed,
            "rules_checked": len(results),
            "results": results
        }
    
    async def record_request(self, endpoint: str, user_id: str = None,
                           ip_address: str = None, **kwargs) -> Dict[str, Any]:
        """记录请求"""
        rules = self.get_rules_for_endpoint(endpoint)
        
        if not rules:
            return {"recorded": True, "rules_applied": 0}
        
        results = []
        overall_success = True
        
        for rule in rules:
            # 检查用户模式
            if user_id and not rule.matches_user(user_id):
                continue
            
            # 生成限流键
            key = self._generate_key(rule, user_id, ip_address, endpoint, **kwargs)
            
            try:
                # 记录请求
                await self.algorithms[rule.strategy].record_request(key, rule)
                
                results.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "strategy": rule.strategy.value,
                    "scope": rule.scope.value,
                    "recorded": True,
                    "limit": rule.limit,
                    "window": rule.window
                })
                
            except RateLimitExceeded as e:
                results.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "strategy": rule.strategy.value,
                    "scope": rule.scope.value,
                    "recorded": False,
                    "rate_limited": True,
                    "retry_after": e.retry_after,
                    "limit": rule.limit,
                    "window": rule.window
                })
                overall_success = False
                
            except Exception as e:
                results.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "strategy": rule.strategy.value,
                    "scope": rule.scope.value,
                    "recorded": False,
                    "error": str(e),
                    "limit": rule.limit,
                    "window": rule.window
                })
                overall_success = False
        
        return {
            "recorded": overall_success,
            "rules_applied": len(results),
            "results": results
        }
    
    def _generate_key(self, rule: RateLimitRule, user_id: str = None,
                     ip_address: str = None, endpoint: str = None, **kwargs) -> str:
        """生成限流键"""
        parts = [rule.scope.value]
        
        if rule.scope in [RateLimitScope.USER, RateLimitScope.USER_ENDPOINT]:
            parts.append(f"user:{user_id or 'anonymous'}")
        
        if rule.scope in [RateLimitScope.IP]:
            parts.append(f"ip:{ip_address or 'unknown'}")
        
        if rule.scope in [RateLimitScope.ENDPOINT, RateLimitScope.USER_ENDPOINT]:
            parts.append(f"endpoint:{endpoint or 'unknown'}")
        
        # 添加额外参数
        for key, value in sorted(kwargs.items()):
            if value is not None:
                parts.append(f"{key}:{value}")
        
        return ":".join(parts)
    
    async def get_rate_limit_status(self, endpoint: str, user_id: str = None,
                                  ip_address: str = None, **kwargs) -> Dict[str, Any]:
        """获取限流状态"""
        rules = self.get_rules_for_endpoint(endpoint)
        
        status = {
            "endpoint": endpoint,
            "user_id": user_id,
            "ip_address": ip_address,
            "rules": []
        }
        
        for rule in rules:
            # 检查用户模式
            if user_id and not rule.matches_user(user_id):
                continue
            
            # 生成限流键
            key = self._generate_key(rule, user_id, ip_address, endpoint, **kwargs)
            
            # 获取当前计数
            try:
                count = await self.store.get_count(key, rule.window)
                
                rule_status = {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "strategy": rule.strategy.value,
                    "scope": rule.scope.value,
                    "current_count": count,
                    "limit": rule.limit,
                    "window": rule.window,
                    "percentage": (count / rule.limit) * 100 if rule.limit > 0 else 0,
                    "remaining": max(0, rule.limit - count),
                    "reset_time": int(time.time()) + rule.window
                }
                
                status["rules"].append(rule_status)
                
            except Exception as e:
                rule_status = {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "strategy": rule.strategy.value,
                    "scope": rule.scope.value,
                    "error": str(e)
                }
                
                status["rules"].append(rule_status)
        
        return status
    
    async def reset_rate_limit(self, endpoint: str, user_id: str = None,
                             ip_address: str = None, **kwargs) -> Dict[str, Any]:
        """重置限流"""
        rules = self.get_rules_for_endpoint(endpoint)
        
        results = []
        total_reset = 0
        
        for rule in rules:
            # 检查用户模式
            if user_id and not rule.matches_user(user_id):
                continue
            
            # 生成限流键
            key = self._generate_key(rule, user_id, ip_address, endpoint, **kwargs)
            
            # 重置限流
            try:
                await self.store.reset(key)
                results.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "reset": True
                })
                total_reset += 1
                
            except Exception as e:
                results.append({
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "reset": False,
                    "error": str(e)
                })
        
        return {
            "reset_count": total_reset,
            "results": results
        }
    
    def get_all_rules(self) -> List[RateLimitRule]:
        """获取所有规则"""
        with self._rules_lock:
            return list(self.rules.values())