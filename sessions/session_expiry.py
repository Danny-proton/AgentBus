"""
会话过期处理模块
Session Expiry Management Module

负责会话过期策略、过期检测、自动清理和过期处理
支持多种过期策略、渐进式过期和智能清理
"""

from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
import asyncio
import logging
import json
from pathlib import Path
from collections import defaultdict, deque

from .context_manager import SessionContext, SessionStatus, SessionType, Platform
from .session_storage import SessionStore

logger = logging.getLogger(__name__)


class ExpiryStrategy(Enum):
    """过期策略枚举"""
    TIME_BASED = "time_based"           # 基于时间的过期
    ACTIVITY_BASED = "activity_based"   # 基于活动的过期
    USAGE_BASED = "usage_based"        # 基于使用量的过期
    HYBRID = "hybrid"                   # 混合策略
    CUSTOM = "custom"                   # 自定义策略


class CleanupAction(Enum):
    """清理操作枚举"""
    ARCHIVE = "archive"                 # 归档
    DELETE = "delete"                   # 删除
    MERGE = "merge"                     # 合并
    SUSPEND = "suspend"               # 暂停
    NOTIFY = "notify"                  # 通知
    EXPORT = "export"                  # 导出


class RetentionPolicy(Enum):
    """保留策略枚举"""
    KEEP_ALL = "keep_all"             # 保留所有
    KEEP_RECENT = "keep_recent"       # 保留最近
    KEEP_IMPORTANT = "keep_important"  # 保留重要
    KEEP_BY_SIZE = "keep_by_size"     # 按大小保留


@dataclass
class ExpiryRule:
    """过期规则"""
    rule_id: str
    name: str
    strategy: ExpiryStrategy
    conditions: Dict[str, Any]  # 过期条件
    actions: List[CleanupAction]
    priority: int = 0  # 优先级，数字越大优先级越高
    enabled: bool = True
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


@dataclass
class ExpiryResult:
    """过期处理结果"""
    session_id: str
    rule_id: Optional[str]
    action: CleanupAction
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass
class ExpiryStatistics:
    """过期统计"""
    total_sessions: int = 0
    expired_sessions: int = 0
    archived_sessions: int = 0
    deleted_sessions: int = 0
    suspended_sessions: int = 0
    notified_sessions: int = 0
    exported_sessions: int = 0
    errors: int = 0
    last_cleanup: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.last_cleanup:
            data["last_cleanup"] = self.last_cleanup.isoformat()
        return data


class ExpiryPolicy:
    """过期策略基类"""
    
    def __init__(self, rule: ExpiryRule):
        self.rule = rule
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{rule.rule_id}")
    
    async def check_expiry(self, session: SessionContext) -> bool:
        """检查会话是否过期"""
        raise NotImplementedError
    
    async def get_expiry_time(self, session: SessionContext) -> Optional[datetime]:
        """获取过期时间"""
        raise NotImplementedError


class TimeBasedExpiryPolicy(ExpiryPolicy):
    """基于时间的过期策略"""
    
    async def check_expiry(self, session: SessionContext) -> bool:
        """检查是否过期"""
        expiry_time = await self.get_expiry_time(session)
        return expiry_time and datetime.now() > expiry_time
    
    async def get_expiry_time(self, session: SessionContext) -> Optional[datetime]:
        """获取过期时间"""
        # 从元数据中获取过期时间
        expires_in = session.metadata.get("expires_in")
        if expires_in:
            return session.created_at + timedelta(seconds=expires_in)
        
        # 从条件中获取默认过期时间
        default_hours = self.rule.conditions.get("default_hours", 24)
        return session.created_at + timedelta(hours=default_hours)


class ActivityBasedExpiryPolicy(ExpiryPolicy):
    """基于活动的过期策略"""
    
    async def check_expiry(self, session: SessionContext) -> bool:
        """检查是否过期"""
        # 检查空闲时间
        idle_timeout = session.metadata.get("idle_timeout", 3600)  # 默认1小时
        idle_duration = (datetime.now() - session.last_activity).total_seconds()
        
        if idle_duration > idle_timeout:
            return True
        
        # 检查最后活动
        last_activity_hours = self.rule.conditions.get("max_inactive_hours", 24)
        inactive_duration = (datetime.now() - session.last_activity).total_seconds()
        
        return inactive_duration > (last_activity_hours * 3600)
    
    async def get_expiry_time(self, session: SessionContext) -> Optional[datetime]:
        """获取过期时间"""
        idle_timeout = session.metadata.get("idle_timeout", 3600)
        return session.last_activity + timedelta(seconds=idle_timeout)


class UsageBasedExpiryPolicy(ExpiryPolicy):
    """基于使用量的过期策略"""
    
    async def check_expiry(self, session: SessionContext) -> bool:
        """检查是否过期"""
        # 检查消息数量
        max_messages = self.rule.conditions.get("max_messages", 1000)
        if len(session.conversation_history) > max_messages:
            return True
        
        # 检查数据大小
        max_size_mb = self.rule.conditions.get("max_size_mb", 10)
        session_size = self._calculate_session_size(session)
        return session_size > (max_size_mb * 1024 * 1024)
    
    async def get_expiry_time(self, session: SessionContext) -> Optional[datetime]:
        """获取过期时间"""
        # 基于使用量的过期可能没有固定时间
        return None
    
    def _calculate_session_size(self, session: SessionContext) -> int:
        """计算会话大小（字节）"""
        size = 0
        
        # 计算对话历史大小
        for message in session.conversation_history:
            size += len(json.dumps(message, ensure_ascii=False))
        
        # 计算数据大小
        size += len(json.dumps(session.data, ensure_ascii=False))
        
        # 计算元数据大小
        size += len(json.dumps(session.metadata, ensure_ascii=False))
        
        return size


class HybridExpiryPolicy(ExpiryPolicy):
    """混合过期策略"""
    
    async def check_expiry(self, session: SessionContext) -> bool:
        """检查是否过期"""
        # 结合时间和活动检查
        time_policy = TimeBasedExpiryPolicy(self.rule)
        activity_policy = ActivityBasedExpiryPolicy(self.rule)
        
        # 满足任一条件即过期
        return await time_policy.check_expiry(session) or await activity_policy.check_expiry(session)
    
    async def get_expiry_time(self, session: SessionContext) -> Optional[datetime]:
        """获取过期时间"""
        time_policy = TimeBasedExpiryPolicy(self.rule)
        activity_time = await time_policy.get_expiry_time(session)
        
        # 返回较早的时间
        idle_timeout = session.metadata.get("idle_timeout", 3600)
        activity_expiry = session.last_activity + timedelta(seconds=idle_timeout)
        
        if activity_time and activity_expiry:
            return min(activity_time, activity_expiry)
        elif activity_time:
            return activity_time
        else:
            return activity_expiry


class CustomExpiryPolicy(ExpiryPolicy):
    """自定义过期策略"""
    
    def __init__(self, rule: ExpiryRule):
        super().__init__(rule)
        self.custom_checker = rule.conditions.get("custom_checker")
    
    async def check_expiry(self, session: SessionContext) -> bool:
        """检查是否过期"""
        if self.custom_checker:
            try:
                if asyncio.iscoroutinefunction(self.custom_checker):
                    return await self.custom_checker(session)
                else:
                    return self.custom_checker(session)
            except Exception as e:
                self.logger.error("Custom expiry checker failed", 
                                session_id=session.session_id, 
                                error=str(e))
                return False
        
        # 默认返回False（不过期）
        return False
    
    async def get_expiry_time(self, session: SessionContext) -> Optional[datetime]:
        """获取过期时间"""
        # 自定义策略可能返回自定义时间
        return None


class SessionExpiryManager:
    """会话过期管理器"""
    
    def __init__(
        self,
        session_store: SessionStore,
        archive_dir: Optional[Path] = None,
        auto_cleanup_interval: int = 1800  # 30分钟
    ):
        self.session_store = session_store
        self.archive_dir = archive_dir or Path("archive")
        self.auto_cleanup_interval = auto_cleanup_interval
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 创建归档目录
        self.archive_dir.mkdir(exist_ok=True)
        
        # 过期规则
        self.expiry_rules: Dict[str, ExpiryRule] = {}
        self.policy_cache: Dict[str, ExpiryPolicy] = {}
        
        # 统计信息
        self.statistics = ExpiryStatistics()
        
        # 过期结果记录
        self.expiry_results: deque = deque(maxlen=10000)
        
        # 清理任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # 通知回调
        self.notification_callbacks: List[Callable] = []
    
    async def start(self) -> None:
        """启动过期管理器"""
        self._running = True
        
        # 加载默认规则
        await self._load_default_rules()
        
        # 启动自动清理任务
        self._cleanup_task = asyncio.create_task(self._auto_cleanup_loop())
        
        self.logger.info("Session expiry manager started", 
                        archive_dir=str(self.archive_dir),
                        interval=self.auto_cleanup_interval)
    
    async def stop(self) -> None:
        """停止过期管理器"""
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Session expiry manager stopped")
    
    async def add_expiry_rule(self, rule: ExpiryRule) -> None:
        """添加过期规则"""
        self.expiry_rules[rule.rule_id] = rule
        
        # 创建策略实例
        policy = await self._create_policy(rule)
        self.policy_cache[rule.rule_id] = policy
        
        self.logger.info("Expiry rule added", 
                        rule_id=rule.rule_id,
                        strategy=rule.strategy.value)
    
    async def remove_expiry_rule(self, rule_id: str) -> bool:
        """移除过期规则"""
        if rule_id in self.expiry_rules:
            del self.expiry_rules[rule_id]
            self.policy_cache.pop(rule_id, None)
            
            self.logger.info("Expiry rule removed", rule_id=rule_id)
            return True
        
        return False
    
    async def check_session_expiry(self, session: SessionContext) -> List[str]:
        """检查会话是否过期"""
        expired_rules = []
        
        for rule_id, rule in self.expiry_rules.items():
            if not rule.enabled:
                continue
            
            try:
                policy = self.policy_cache.get(rule_id)
                if policy and await policy.check_expiry(session):
                    expired_rules.append(rule_id)
            
            except Exception as e:
                self.logger.error("Error checking expiry rule", 
                                rule_id=rule_id, 
                                session_id=session.session_id,
                                error=str(e))
        
        return expired_rules
    
    async def process_expired_sessions(self, session_ids: Optional[List[str]] = None) -> List[ExpiryResult]:
        """处理过期会话"""
        results = []
        
        try:
            # 获取要检查的会话
            if session_ids:
                sessions = []
                for session_id in session_ids:
                    session = await self.session_store.get_session(session_id)
                    if session:
                        sessions.append(session)
            else:
                # 获取所有会话
                sessions = await self._get_all_sessions()
            
            for session in sessions:
                # 检查过期规则
                expired_rule_ids = await self.check_session_expiry(session)
                
                if expired_rule_ids:
                    # 按优先级排序
                    sorted_rules = sorted(
                        [self.expiry_rules[rule_id] for rule_id in expired_rule_ids],
                        key=lambda r: r.priority,
                        reverse=True
                    )
                    
                    # 应用最高优先级的规则
                    rule = sorted_rules[0]
                    result = await self._apply_expiry_rule(session, rule)
                    results.append(result)
        
        except Exception as e:
            self.logger.error("Error processing expired sessions", error=str(e))
        
        return results
    
    async def force_expire_session(self, session_id: str, rule_id: str) -> ExpiryResult:
        """强制过期会话"""
        session = await self.session_store.get_session(session_id)
        if not session:
            return ExpiryResult(
                session_id=session_id,
                rule_id=None,
                action=CleanupAction.DELETE,
                timestamp=datetime.now(),
                success=False,
                error_message="Session not found"
            )
        
        rule = self.expiry_rules.get(rule_id)
        if not rule:
            return ExpiryResult(
                session_id=session_id,
                rule_id=rule_id,
                action=CleanupAction.DELETE,
                timestamp=datetime.now(),
                success=False,
                error_message="Rule not found"
            )
        
        return await self._apply_expiry_rule(session, rule)
    
    async def add_notification_callback(self, callback: Callable) -> None:
        """添加通知回调"""
        self.notification_callbacks.append(callback)
    
    async def get_expiry_statistics(self) -> Dict[str, Any]:
        """获取过期统计"""
        return {
            "statistics": self.statistics.to_dict(),
            "rules_count": len(self.expiry_rules),
            "active_rules": sum(1 for rule in self.expiry_rules.values() if rule.enabled),
            "recent_results": [result.to_dict() for result in list(self.expiry_results)[-10:]],
            "archive_dir": str(self.archive_dir)
        }
    
    async def cleanup_expired_sessions(self, dry_run: bool = False) -> List[ExpiryResult]:
        """清理过期会话"""
        try:
            # 检查过期会话
            expired_results = await self.process_expired_sessions()
            
            if dry_run:
                # 干运行模式，只返回结果不执行实际操作
                return expired_results
            
            # 执行清理操作
            executed_results = []
            for result in expired_results:
                executed_result = await self._execute_cleanup_action(result)
                executed_results.append(executed_result)
                
                # 发送通知
                await self._send_notifications(executed_result)
            
            # 更新统计信息
            await self._update_statistics(executed_results)
            
            self.logger.info("Cleanup completed", 
                           processed=len(executed_results),
                           dry_run=dry_run)
            
            return executed_results
        
        except Exception as e:
            self.logger.error("Error during cleanup", error=str(e))
            return []
    
    async def archive_session(self, session: SessionContext) -> bool:
        """归档会话"""
        try:
            # 准备归档数据
            archive_data = {
                "session": session.to_dict(),
                "archived_at": datetime.now().isoformat(),
                "archive_reason": "expiry"
            }
            
            # 生成归档文件名
            archive_filename = f"{session.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            archive_path = self.archive_dir / archive_filename
            
            # 写入归档文件
            with open(archive_path, 'w', encoding='utf-8') as f:
                json.dump(archive_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info("Session archived", 
                           session_id=session.session_id,
                           path=str(archive_path))
            
            return True
        
        except Exception as e:
            self.logger.error("Failed to archive session", 
                            session_id=session.session_id, 
                            error=str(e))
            return False
    
    async def restore_session_from_archive(self, archive_path: Path) -> Optional[SessionContext]:
        """从归档恢复会话"""
        try:
            with open(archive_path, 'r', encoding='utf-8') as f:
                archive_data = json.load(f)
            
            session_data = archive_data.get("session")
            if not session_data:
                raise ValueError("Invalid archive format")
            
            # 创建会话上下文
            session = SessionContext.from_dict(session_data)
            
            # 保存到存储
            await self.session_store.create_session(session)
            
            self.logger.info("Session restored from archive", 
                           session_id=session.session_id,
                           path=str(archive_path))
            
            return session
        
        except Exception as e:
            self.logger.error("Failed to restore session from archive", 
                            path=str(archive_path), 
                            error=str(e))
            return None
    
    async def _auto_cleanup_loop(self) -> None:
        """自动清理循环"""
        while self._running:
            try:
                await asyncio.sleep(self.auto_cleanup_interval)
                
                if not self._running:
                    break
                
                # 执行自动清理
                results = await self.cleanup_expired_sessions()
                
                if results:
                    self.logger.debug("Auto cleanup completed", 
                                   processed=len(results))
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in auto cleanup loop", error=str(e))
                await asyncio.sleep(self.auto_cleanup_interval * 2)
    
    async def _load_default_rules(self) -> None:
        """加载默认规则"""
        # 默认的过期规则
        default_rules = [
            ExpiryRule(
                rule_id="default_time_based",
                name="Default Time Based Expiry",
                strategy=ExpiryStrategy.TIME_BASED,
                conditions={"default_hours": 24},
                actions=[CleanupAction.ARCHIVE],
                priority=1,
                description="Archive sessions after 24 hours of inactivity"
            ),
            ExpiryRule(
                rule_id="long_term_archive",
                name="Long Term Archive",
                strategy=ExpiryStrategy.TIME_BASED,
                conditions={"default_hours": 168},  # 7天
                actions=[CleanupAction.DELETE],
                priority=2,
                description="Delete sessions after 7 days"
            ),
            ExpiryRule(
                rule_id="activity_based",
                name="Activity Based Expiry",
                strategy=ExpiryStrategy.ACTIVITY_BASED,
                conditions={"max_inactive_hours": 2},
                actions=[CleanupAction.SUSPEND],
                priority=3,
                description="Suspend sessions after 2 hours of inactivity"
            )
        ]
        
        for rule in default_rules:
            await self.add_expiry_rule(rule)
    
    async def _create_policy(self, rule: ExpiryRule) -> ExpiryPolicy:
        """创建过期策略"""
        if rule.strategy == ExpiryStrategy.TIME_BASED:
            return TimeBasedExpiryPolicy(rule)
        elif rule.strategy == ExpiryStrategy.ACTIVITY_BASED:
            return ActivityBasedExpiryPolicy(rule)
        elif rule.strategy == ExpiryStrategy.USAGE_BASED:
            return UsageBasedExpiryPolicy(rule)
        elif rule.strategy == ExpiryStrategy.HYBRID:
            return HybridExpiryPolicy(rule)
        elif rule.strategy == ExpiryStrategy.CUSTOM:
            return CustomExpiryPolicy(rule)
        else:
            raise ValueError(f"Unknown expiry strategy: {rule.strategy}")
    
    async def _apply_expiry_rule(self, session: SessionContext, rule: ExpiryRule) -> ExpiryResult:
        """应用过期规则"""
        # 默认使用第一个操作
        action = rule.actions[0] if rule.actions else CleanupAction.ARCHIVE
        
        result = ExpiryResult(
            session_id=session.session_id,
            rule_id=rule.rule_id,
            action=action,
            timestamp=datetime.now(),
            success=False
        )
        
        try:
            # 执行相应的操作
            if action == CleanupAction.ARCHIVE:
                success = await self.archive_session(session)
            elif action == CleanupAction.DELETE:
                success = await self.session_store.delete_session(session.session_id)
            elif action == CleanupAction.SUSPEND:
                session.set_status(SessionStatus.SUSPENDED)
                await self.session_store.update_session(session)
                success = True
            elif action == CleanupAction.NOTIFY:
                success = await self._send_session_notification(session, rule)
            elif action == CleanupAction.EXPORT:
                export_path = await self._export_session(session)
                success = export_path is not None
                if export_path:
                    result.metadata["export_path"] = str(export_path)
            else:
                success = False
                result.error_message = f"Unsupported action: {action}"
            
            result.success = success
            
            if not success and not result.error_message:
                result.error_message = "Operation failed"
        
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            self.logger.error("Failed to apply expiry rule", 
                            session_id=session.session_id,
                            rule_id=rule.rule_id,
                            error=str(e))
        
        # 记录结果
        self.expiry_results.append(result)
        
        return result
    
    async def _execute_cleanup_action(self, result: ExpiryResult) -> ExpiryResult:
        """执行清理操作"""
        if result.success:
            return result
        
        # 重试失败的清理操作
        session = await self.session_store.get_session(result.session_id)
        if session:
            return await self._apply_expiry_rule(session, self.expiry_rules[result.rule_id])
        
        return result
    
    async def _send_session_notification(self, session: SessionContext, rule: ExpiryRule) -> bool:
        """发送会话通知"""
        try:
            notification_data = {
                "session_id": session.session_id,
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "message": f"Session {session.session_id} will expire soon due to rule: {rule.name}",
                "timestamp": datetime.now().isoformat()
            }
            
            # 调用所有通知回调
            for callback in self.notification_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(notification_data)
                    else:
                        callback(notification_data)
                except Exception as e:
                    self.logger.error("Notification callback failed", error=str(e))
            
            return True
        
        except Exception as e:
            self.logger.error("Failed to send session notification", 
                            session_id=session.session_id, 
                            error=str(e))
            return False
    
    async def _send_notifications(self, result: ExpiryResult) -> None:
        """发送通知"""
        for callback in self.notification_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result.to_dict())
                else:
                    callback(result.to_dict())
            except Exception as e:
                self.logger.error("Notification callback failed", error=str(e))
    
    async def _export_session(self, session: SessionContext) -> Optional[Path]:
        """导出会话"""
        try:
            export_data = {
                "session": session.to_dict(),
                "exported_at": datetime.now().isoformat(),
                "export_reason": "expiry"
            }
            
            export_filename = f"{session.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            export_path = self.archive_dir / f"exports/{export_filename}"
            
            # 创建exports目录
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return export_path
        
        except Exception as e:
            self.logger.error("Failed to export session", 
                            session_id=session.session_id, 
                            error=str(e))
            return None
    
    async def _update_statistics(self, results: List[ExpiryResult]) -> None:
        """更新统计信息"""
        for result in results:
            if result.success:
                if result.action == CleanupAction.ARCHIVE:
                    self.statistics.archived_sessions += 1
                elif result.action == CleanupAction.DELETE:
                    self.statistics.deleted_sessions += 1
                elif result.action == CleanupAction.SUSPEND:
                    self.statistics.suspended_sessions += 1
                elif result.action == CleanupAction.NOTIFY:
                    self.statistics.notified_sessions += 1
                elif result.action == CleanupAction.EXPORT:
                    self.statistics.exported_sessions += 1
            else:
                self.statistics.errors += 1
        
        self.statistics.last_cleanup = datetime.now()
    
    async def _get_all_sessions(self) -> List[SessionContext]:
        """获取所有会话"""
        # 这里应该实现获取所有会话的逻辑
        # 由于SessionStore接口限制，我们暂时返回空列表
        # 实际实现时需要扩展SessionStore接口
        return []


# 便捷函数
async def create_expiry_manager(
    session_store: SessionStore,
    archive_dir: Optional[Path] = None,
    **config
) -> SessionExpiryManager:
    """创建会话过期管理器"""
    manager = SessionExpiryManager(session_store, archive_dir, **config)
    await manager.start()
    return manager


# 通知回调示例
async def default_notification_callback(notification_data: Dict[str, Any]) -> None:
    """默认通知回调"""
    logger.info("Session expiry notification", **notification_data)


def create_email_notification_callback(email_config: Dict[str, Any]) -> Callable:
    """创建邮件通知回调"""
    async def email_callback(notification_data: Dict[str, Any]) -> None:
        # 实现邮件发送逻辑
        logger.info("Email notification would be sent", **notification_data)
    
    return email_callback


def create_webhook_notification_callback(webhook_url: str) -> Callable:
    """创建Webhook通知回调"""
    async def webhook_callback(notification_data: Dict[str, Any]) -> None:
        # 实现Webhook发送逻辑
        logger.info("Webhook notification would be sent", url=webhook_url, **notification_data)
    
    return webhook_callback