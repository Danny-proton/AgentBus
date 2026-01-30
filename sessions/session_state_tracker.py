"""
会话状态跟踪模块
Session State Tracking Module

负责会话状态的详细跟踪、状态变更记录、状态分析和预测
支持状态机模式、状态变更事件和状态统计
"""

from typing import Dict, List, Optional, Any, Set, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
import asyncio
import logging
import json
from collections import defaultdict, deque
from pathlib import Path

from .context_manager import SessionContext, SessionStatus, SessionType, Platform
from .session_storage import SessionStore

logger = logging.getLogger(__name__)


class StateTransitionType(Enum):
    """状态转换类型"""
    MANUAL = "manual"           # 手动转换
    AUTOMATIC = "automatic"     # 自动转换
    SCHEDULED = "scheduled"     # 定时转换
    EVENT_DRIVEN = "event_driven" # 事件驱动转换
    SYSTEM = "system"          # 系统转换


class EventType(Enum):
    """事件类型枚举"""
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_sent"
    USER_ACTIVITY = "user_activity"
    SYSTEM_NOTIFICATION = "system_notification"
    ERROR_OCCURRED = "error_occurred"
    TIMEOUT = "timeout"
    EXTERNAL_API_CALL = "external_api_call"
    SESSION_MERGE = "session_merge"
    SESSION_SPLIT = "session_split"
    IDLE_DETECTED = "idle_detected"
    STATE_CHANGE = "state_change"


@dataclass
class StateTransition:
    """状态转换记录"""
    transition_id: str
    from_status: Optional[SessionStatus]
    to_status: SessionStatus
    timestamp: datetime
    transition_type: StateTransitionType
    trigger_event: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: Optional[float] = None  # 状态持续时间
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class SessionEvent:
    """会话事件"""
    event_id: str
    event_type: EventType
    session_id: str
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class SessionMetrics:
    """会话指标"""
    session_id: str
    total_messages: int = 0
    user_messages: int = 0
    system_messages: int = 0
    active_duration: float = 0.0  # 活跃持续时间（秒）
    idle_duration: float = 0.0    # 空闲持续时间（秒）
    response_times: List[float] = field(default_factory=list)  # 响应时间列表
    error_count: int = 0
    api_call_count: int = 0
    state_changes: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["last_updated"] = self.last_updated.isoformat()
        return data


class StateMachine:
    """状态机"""
    
    def __init__(self):
        self.transitions: Dict[Tuple[SessionStatus, str], SessionStatus] = {}
        self.transition_handlers: Dict[str, List[Callable]] = {}
    
    def add_transition(
        self,
        from_status: Optional[SessionStatus],
        to_status: SessionStatus,
        event_type: str,
        handler: Optional[Callable] = None
    ) -> None:
        """添加状态转换"""
        key = (from_status, event_type)
        self.transitions[key] = to_status
        
        if handler:
            if event_type not in self.transition_handlers:
                self.transition_handlers[event_type] = []
            self.transition_handlers[event_type].append(handler)
    
    def get_next_state(
        self,
        current_status: SessionStatus,
        event_type: str
    ) -> Optional[SessionStatus]:
        """获取下一个状态"""
        # 尝试精确匹配
        key = (current_status, event_type)
        if key in self.transitions:
            return self.transitions[key]
        
        # 尝试通配符匹配（None表示任意状态）
        key = (None, event_type)
        if key in self.transitions:
            return self.transitions[key]
        
        return None
    
    def add_handler(self, event_type: str, handler: Callable) -> None:
        """添加事件处理器"""
        if event_type not in self.transition_handlers:
            self.transition_handlers[event_type] = []
        self.transition_handlers[event_type].append(handler)


class SessionStateTracker:
    """会话状态跟踪器"""
    
    def __init__(
        self,
        session_store: SessionStore,
        history_retention_days: int = 30,
        max_events_per_session: int = 1000,
        enable_prediction: bool = True
    ):
        self.session_store = session_store
        self.history_retention_days = history_retention_days
        self.max_events_per_session = max_events_per_session
        self.enable_prediction = enable_prediction
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 状态跟踪数据
        self.session_states: Dict[str, SessionContext] = {}
        self.session_transitions: Dict[str, List[StateTransition]] = defaultdict(list)
        self.session_events: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_events_per_session))
        self.session_metrics: Dict[str, SessionMetrics] = {}
        
        # 状态机
        self.state_machine = self._create_default_state_machine()
        
        # 预测器
        self.pattern_analyzer = PatternAnalyzer()
        self.state_predictor = StatePredictor() if enable_prediction else None
        
        # 清理任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self) -> None:
        """启动状态跟踪器"""
        self._running = True
        
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self.logger.info("Session state tracker started", 
                        history_retention_days=self.history_retention_days,
                        enable_prediction=self.enable_prediction)
    
    async def stop(self) -> None:
        """停止状态跟踪器"""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Session state tracker stopped")
    
    async def track_session_state_change(
        self,
        session_id: str,
        new_status: SessionStatus,
        transition_type: StateTransitionType = StateTransitionType.AUTOMATIC,
        trigger_event: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """跟踪会话状态变更"""
        try:
            # 获取当前会话
            session = await self.session_store.get_session(session_id)
            if not session:
                self.logger.warning("Session not found for state tracking", session_id=session_id)
                return False
            
            current_status = session.get_status()
            
            # 创建状态转换记录
            transition = await self._create_transition_record(
                session_id, current_status, new_status, transition_type, trigger_event, metadata
            )
            
            # 更新会话状态
            session.set_status(new_status)
            await self.session_store.update_session(session)
            
            # 记录转换
            self.session_transitions[session_id].append(transition)
            
            # 限制转换历史长度
            if len(self.session_transitions[session_id]) > 100:
                self.session_transitions[session_id] = self.session_transitions[session_id][-50:]
            
            # 更新指标
            await self._update_metrics(session_id, "state_change")
            
            # 触发状态变更事件
            await self._emit_event(
                session_id,
                EventType.STATE_CHANGE,
                {
                    "from_status": current_status.value,
                    "to_status": new_status.value,
                    "transition_type": transition_type.value,
                    "trigger_event": trigger_event
                }
            )
            
            # 执行状态转换处理器
            await self._execute_transition_handlers(transition_type.value, session, new_status, metadata)
            
            # 状态预测
            if self.state_predictor:
                await self._predict_next_state(session_id, transition)
            
            self.logger.debug("Session state tracked", 
                           session_id=session_id,
                           from_status=current_status.value,
                           to_status=new_status.value)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to track session state change", 
                            session_id=session_id, 
                            error=str(e))
            return False
    
    async def track_event(
        self,
        session_id: str,
        event_type: EventType,
        data: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> bool:
        """跟踪会话事件"""
        try:
            event = SessionEvent(
                event_id=f"evt_{datetime.now().timestamp()}_{hash(session_id) % 10000}",
                event_type=event_type,
                session_id=session_id,
                timestamp=datetime.now(),
                data=data or {},
                source=source,
                correlation_id=correlation_id
            )
            
            # 添加到事件队列
            self.session_events[session_id].append(event)
            
            # 更新指标
            await self._update_metrics(session_id, event_type.value)
            
            # 检查是否需要状态转换
            await self._check_state_transitions(session_id, event)
            
            # 执行事件处理器
            await self._execute_event_handlers(event)
            
            self.logger.debug("Session event tracked", 
                            session_id=session_id,
                            event_type=event_type.value)
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to track session event", 
                            session_id=session_id, 
                            event_type=event_type.value,
                            error=str(e))
            return False
    
    async def get_session_state_history(
        self,
        session_id: str,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取会话状态历史"""
        try:
            transitions = self.session_transitions.get(session_id, [])
            
            if since:
                transitions = [
                    t for t in transitions 
                    if t.timestamp >= since
                ]
            
            if limit:
                transitions = transitions[-limit:]
            
            return [transition.to_dict() for transition in transitions]
            
        except Exception as e:
            self.logger.error("Failed to get session state history", 
                            session_id=session_id, 
                            error=str(e))
            return []
    
    async def get_session_events(
        self,
        session_id: str,
        event_type: Optional[EventType] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """获取会话事件"""
        try:
            events = list(self.session_events.get(session_id, []))
            
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            if since:
                events = [e for e in events if e.timestamp >= since]
            
            if limit:
                events = events[-limit:]
            
            return [event.to_dict() for event in events]
            
        except Exception as e:
            self.logger.error("Failed to get session events", 
                            session_id=session_id, 
                            error=str(e))
            return []
    
    async def get_session_metrics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话指标"""
        metrics = self.session_metrics.get(session_id)
        return metrics.to_dict() if metrics else None
    
    async def get_state_statistics(
        self,
        time_range: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """获取状态统计信息"""
        try:
            now = datetime.now()
            since = now - (time_range or timedelta(days=7))
            
            # 统计所有转换
            all_transitions = []
            for transitions in self.session_transitions.values():
                all_transitions.extend([
                    t for t in transitions 
                    if t.timestamp >= since
                ])
            
            # 按状态统计
            status_counts = defaultdict(int)
            transition_counts = defaultdict(int)
            
            for transition in all_transitions:
                status_counts[transition.to_status.value] += 1
                transition_key = f"{transition.from_status.value if transition.from_status else 'unknown'}->{transition.to_status.value}"
                transition_counts[transition_key] += 1
            
            # 平均状态持续时间
            avg_durations = {}
            status_durations = defaultdict(list)
            
            for session_id, transitions in self.session_transitions.items():
                for i, transition in enumerate(transitions):
                    if transition.duration_seconds and transition.timestamp >= since:
                        status_durations[transition.to_status.value].append(transition.duration_seconds)
            
            for status, durations in status_durations.items():
                if durations:
                    avg_durations[status] = sum(durations) / len(durations)
            
            return {
                "time_range_days": time_range.days if time_range else 7,
                "total_transitions": len(all_transitions),
                "status_distribution": dict(status_counts),
                "top_transitions": dict(sorted(transition_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                "average_state_durations": avg_durations,
                "unique_sessions": len(self.session_transitions),
                "active_sessions": sum(
                    1 for session_id in self.session_states.keys()
                    if await self._is_session_active(session_id)
                )
            }
            
        except Exception as e:
            self.logger.error("Failed to get state statistics", error=str(e))
            return {}
    
    async def predict_session_lifecycle(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """预测会话生命周期"""
        if not self.state_predictor:
            return None
        
        try:
            # 获取会话历史
            history = await self.get_session_state_history(session_id)
            events = await self.get_session_events(session_id, limit=100)
            
            if not history:
                return None
            
            # 分析模式
            patterns = await self.pattern_analyzer.analyze_patterns(history, events)
            
            # 生成预测
            prediction = await self.state_predictor.predict_lifecycle(
                session_id, history, events, patterns
            )
            
            return prediction
            
        except Exception as e:
            self.logger.error("Failed to predict session lifecycle", 
                            session_id=session_id, 
                            error=str(e))
            return None
    
    async def add_custom_transition_rule(
        self,
        from_status: Optional[SessionStatus],
        to_status: SessionStatus,
        event_type: str,
        condition: Optional[Callable[[SessionContext, Dict[str, Any]], bool]] = None,
        handler: Optional[Callable] = None
    ) -> None:
        """添加自定义状态转换规则"""
        def transition_handler(session: SessionContext, event_data: Dict[str, Any]) -> bool:
            # 检查条件
            if condition and not condition(session, event_data):
                return False
            
            # 执行转换
            return asyncio.create_task(
                self.track_session_state_change(
                    session.session_id,
                    to_status,
                    StateTransitionType.EVENT_DRIVEN,
                    event_type,
                    event_data
                )
            )
        
        self.state_machine.add_transition(from_status, to_status, event_type, transition_handler)
    
    async def _create_transition_record(
        self,
        session_id: str,
        from_status: Optional[SessionStatus],
        to_status: SessionStatus,
        transition_type: StateTransitionType,
        trigger_event: Optional[str],
        metadata: Optional[Dict[str, Any]]
    ) -> StateTransition:
        """创建状态转换记录"""
        # 计算状态持续时间
        duration_seconds = None
        if from_status:
            recent_transitions = self.session_transitions.get(session_id, [])
            if recent_transitions:
                last_to_same_status = next(
                    (t for t in reversed(recent_transitions) 
                     if t.to_status == from_status),
                    None
                )
                if last_to_same_status:
                    duration_seconds = (datetime.now() - last_to_same_status.timestamp).total_seconds()
        
        return StateTransition(
            transition_id=f"tr_{datetime.now().timestamp()}_{hash(session_id) % 10000}",
            from_status=from_status,
            to_status=to_status,
            timestamp=datetime.now(),
            transition_type=transition_type,
            trigger_event=trigger_event,
            metadata=metadata or {},
            duration_seconds=duration_seconds
        )
    
    async def _update_metrics(self, session_id: str, event_type: str) -> None:
        """更新会话指标"""
        if session_id not in self.session_metrics:
            self.session_metrics[session_id] = SessionMetrics(session_id=session_id)
        
        metrics = self.session_metrics[session_id]
        metrics.last_updated = datetime.now()
        
        # 根据事件类型更新指标
        if event_type == "message_received":
            metrics.total_messages += 1
            metrics.user_messages += 1
        elif event_type == "message_sent":
            metrics.total_messages += 1
            metrics.system_messages += 1
        elif event_type == "error_occurred":
            metrics.error_count += 1
        elif event_type == "external_api_call":
            metrics.api_call_count += 1
        elif event_type == "state_change":
            metrics.state_changes += 1
    
    async def _emit_event(
        self,
        session_id: str,
        event_type: EventType,
        data: Dict[str, Any]
    ) -> None:
        """发出事件"""
        await self.track_event(session_id, event_type, data)
    
    async def _check_state_transitions(
        self,
        session_id: str,
        event: SessionEvent
    ) -> None:
        """检查状态转换"""
        try:
            session = await self.session_store.get_session(session_id)
            if not session:
                return
            
            current_status = session.get_status()
            
            # 获取下一个状态
            next_status = self.state_machine.get_next_state(current_status, event.event_type.value)
            
            if next_status and next_status != current_status:
                await self.track_session_state_change(
                    session_id,
                    next_status,
                    StateTransitionType.EVENT_DRIVEN,
                    event.event_type.value,
                    {"triggering_event": event.event_id}
                )
            
        except Exception as e:
            self.logger.error("Failed to check state transitions", 
                            session_id=session_id, 
                            error=str(e))
    
    async def _execute_transition_handlers(
        self,
        event_type: str,
        session: SessionContext,
        new_status: SessionStatus,
        metadata: Optional[Dict[str, Any]]
    ) -> None:
        """执行状态转换处理器"""
        handlers = self.state_machine.transition_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(session, metadata or {})
                else:
                    handler(session, metadata or {})
            except Exception as e:
                self.logger.error("Failed to execute transition handler", 
                                session_id=session.session_id, 
                                error=str(e))
    
    async def _execute_event_handlers(self, event: SessionEvent) -> None:
        """执行事件处理器"""
        # 这里可以添加各种事件处理器
        # 例如：发送通知、更新外部系统、记录日志等
        
        if event.event_type == EventType.ERROR_OCCURRED:
            # 错误事件处理器
            await self._handle_error_event(event)
        elif event.event_type == EventType.IDLE_DETECTED:
            # 空闲检测处理器
            await self._handle_idle_event(event)
    
    async def _handle_error_event(self, event: SessionEvent) -> None:
        """处理错误事件"""
        try:
            # 增加错误计数
            metrics = self.session_metrics.get(event.session_id)
            if metrics:
                metrics.error_count += 1
            
            # 可以在这里添加更多错误处理逻辑
            # 例如：发送错误通知、触发告警等
            
        except Exception as e:
            self.logger.error("Failed to handle error event", error=str(e))
    
    async def _handle_idle_event(self, event: SessionEvent) -> None:
        """处理空闲事件"""
        try:
            # 切换到空闲状态
            await self.track_session_state_change(
                event.session_id,
                SessionStatus.IDLE,
                StateTransitionType.AUTOMATIC,
                "idle_detected",
                event.data
            )
            
        except Exception as e:
            self.logger.error("Failed to handle idle event", error=str(e))
    
    async def _predict_next_state(
        self,
        session_id: str,
        transition: StateTransition
    ) -> None:
        """预测下一个状态"""
        if not self.state_predictor:
            return
        
        try:
            # 更新预测模型
            await self.state_predictor.update_model(session_id, transition)
            
        except Exception as e:
            self.logger.error("Failed to predict next state", 
                            session_id=session_id, 
                            error=str(e))
    
    async def _is_session_active(self, session_id: str) -> bool:
        """检查会话是否活跃"""
        try:
            session = await self.session_store.get_session(session_id)
            return session.is_active() if session else False
        except Exception:
            return False
    
    async def _cleanup_loop(self) -> None:
        """清理循环"""
        while self._running:
            try:
                await asyncio.sleep(3600)  # 每小时清理一次
                
                if not self._running:
                    break
                
                # 清理过期数据
                cutoff_time = datetime.now() - timedelta(days=self.history_retention_days)
                
                # 清理过期转换记录
                for session_id, transitions in self.session_transitions.items():
                    expired = [t for t in transitions if t.timestamp < cutoff_time]
                    if expired:
                        self.session_transitions[session_id] = [
                            t for t in transitions if t.timestamp >= cutoff_time
                        ]
                
                # 清理过期事件
                for session_id, events in self.session_events.items():
                    # deque已经限制了最大长度，这里不需要额外清理
                    pass
                
                # 清理无会话的指标
                active_sessions = set()
                for session_id in self.session_states.keys():
                    if await self._is_session_active(session_id):
                        active_sessions.add(session_id)
                
                # 移除不活跃会话的指标
                inactive_metrics = [
                    sid for sid in self.session_metrics.keys()
                    if sid not in active_sessions
                ]
                
                for sid in inactive_metrics:
                    del self.session_metrics[sid]
                
                self.logger.debug("Cleanup completed", 
                                cleaned_transitions=len([t for trans in self.session_transitions.values() 
                                                       for t in trans if t.timestamp < cutoff_time]),
                                inactive_metrics=len(inactive_metrics))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in cleanup loop", error=str(e))
                await asyncio.sleep(3600 * 2)
    
    def _create_default_state_machine(self) -> StateMachine:
        """创建默认状态机"""
        machine = StateMachine()
        
        # 定义默认转换规则
        machine.add_transition(None, SessionStatus.ACTIVE, "session_created")
        machine.add_transition(SessionStatus.ACTIVE, SessionStatus.IDLE, "idle_detected")
        machine.add_transition(SessionStatus.IDLE, SessionStatus.ACTIVE, "user_activity")
        machine.add_transition(SessionStatus.ACTIVE, SessionStatus.SUSPENDED, "manual_suspend")
        machine.add_transition(SessionStatus.SUSPENDED, SessionStatus.ACTIVE, "manual_resume")
        machine.add_transition(SessionStatus.ACTIVE, SessionStatus.EXPIRED, "timeout")
        machine.add_transition(SessionStatus.IDLE, SessionStatus.EXPIRED, "idle_timeout")
        machine.add_transition(None, SessionStatus.CLOSED, "manual_close")
        
        return machine


class PatternAnalyzer:
    """模式分析器"""
    
    async def analyze_patterns(
        self,
        transitions: List[Dict[str, Any]],
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析模式"""
        patterns = {
            "common_sequences": self._find_common_sequences(transitions),
            "event_patterns": self._analyze_event_patterns(events),
            "timing_patterns": self._analyze_timing_patterns(transitions),
            "status_distribution": self._analyze_status_distribution(transitions)
        }
        
        return patterns
    
    def _find_common_sequences(self, transitions: List[Dict[str, Any]]) -> List[str]:
        """查找常见序列"""
        # 简化的序列分析
        sequences = []
        
        for i in range(len(transitions) - 2):
            from_status = transitions[i].get("to_status", "unknown")
            to_status = transitions[i + 1].get("to_status", "unknown")
            sequences.append(f"{from_status}->{to_status}")
        
        # 统计频率
        from collections import Counter
        sequence_counts = Counter(sequences)
        
        return [seq for seq, count in sequence_counts.most_common(5)]
    
    def _analyze_event_patterns(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """分析事件模式"""
        event_types = [event.get("event_type") for event in events]
        from collections import Counter
        return dict(Counter(event_types))
    
    def _analyze_timing_patterns(self, transitions: List[Dict[str, Any]]) -> Dict[str, float]:
        """分析时间模式"""
        durations = {}
        
        status_durations = defaultdict(list)
        for transition in transitions:
            duration = transition.get("duration_seconds")
            if duration:
                status = transition.get("to_status")
                status_durations[status].append(duration)
        
        for status, duration_list in status_durations.items():
            durations[status] = sum(duration_list) / len(duration_list)
        
        return durations
    
    def _analyze_status_distribution(self, transitions: List[Dict[str, Any]]) -> Dict[str, int]:
        """分析状态分布"""
        statuses = [transition.get("to_status") for transition in transitions]
        from collections import Counter
        return dict(Counter(statuses))


class StatePredictor:
    """状态预测器"""
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
    
    async def predict_lifecycle(
        self,
        session_id: str,
        history: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """预测生命周期"""
        # 简化的预测逻辑
        current_status = history[-1].get("to_status", "active") if history else "active"
        
        predictions = {
            "next_likely_state": await self._predict_next_state(current_status, patterns),
            "estimated_duration": await self._estimate_duration(current_status, patterns),
            "lifecycle_stage": await self._determine_lifecycle_stage(history),
            "confidence": 0.7  # 简化的置信度
        }
        
        return predictions
    
    async def update_model(self, session_id: str, transition: StateTransition) -> None:
        """更新预测模型"""
        # 这里可以实现更复杂的机器学习模型
        pass
    
    async def _predict_next_state(self, current_status: str, patterns: Dict[str, Any]) -> str:
        """预测下一个状态"""
        common_sequences = patterns.get("common_sequences", [])
        
        # 查找以当前状态开始的序列
        for sequence in common_sequences:
            if sequence.startswith(current_status):
                next_state = sequence.split("->")[1]
                return next_state
        
        # 默认预测逻辑
        status_mapping = {
            "active": "idle",
            "idle": "active",
            "suspended": "active",
            "expired": "closed"
        }
        
        return status_mapping.get(current_status, "active")
    
    async def _estimate_duration(self, current_status: str, patterns: Dict[str, Any]) -> float:
        """估计状态持续时间"""
        timing_patterns = patterns.get("timing_patterns", {})
        return timing_patterns.get(current_status, 3600.0)  # 默认1小时
    
    async def _determine_lifecycle_stage(self, history: List[Dict[str, Any]]) -> str:
        """确定生命周期阶段"""
        if not history:
            return "new"
        
        total_transitions = len(history)
        
        if total_transitions < 5:
            return "early"
        elif total_transitions < 20:
            return "mature"
        else:
            return "experienced"


# 便捷函数
async def create_session_state_tracker(
    session_store: SessionStore,
    **config
) -> SessionStateTracker:
    """创建会话状态跟踪器"""
    tracker = SessionStateTracker(session_store, **config)
    await tracker.start()
    return tracker