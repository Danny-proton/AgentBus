"""
AgentBus告警管理系统

提供智能告警规则管理、多种通知方式和告警抑制功能
"""

import os
import json
import threading
import time
import smtplib
import ssl
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import traceback
from .metrics import MetricsCollector, SystemMetrics, ApplicationMetrics


class AlertLevel(Enum):
    """告警级别枚举"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertStatus(Enum):
    """告警状态枚举"""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class AlertRuleType(Enum):
    """告警规则类型枚举"""
    THRESHOLD = "threshold"        # 阈值告警
    CHANGE_RATE = "change_rate"    # 变化率告警
    STATISTICAL = "statistical"    # 统计告警
    CUSTOM = "custom"             # 自定义告警


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    description: str
    level: AlertLevel
    rule_type: AlertRuleType
    metric_name: str
    condition: str  # 比较条件: >, <, >=, <=, ==, !=
    threshold: float
    evaluation_window: int = 300  # 评估窗口（秒）
    cooldown_period: int = 300    # 冷却期（秒）
    labels: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    
    def evaluate(self, value: float, history: List[float]) -> bool:
        """评估告警条件"""
        if not self.enabled:
            return False
            
        if self.rule_type == AlertRuleType.THRESHOLD:
            return self._evaluate_threshold(value)
        elif self.rule_type == AlertRuleType.CHANGE_RATE:
            return self._evaluate_change_rate(history)
        elif self.rule_type == AlertRuleType.STATISTICAL:
            return self._evaluate_statistical(history)
        else:
            return False
            
    def _evaluate_threshold(self, value: float) -> bool:
        """阈值评估"""
        if self.condition == ">":
            return value > self.threshold
        elif self.condition == "<":
            return value < self.threshold
        elif self.condition == ">=":
            return value >= self.threshold
        elif self.condition == "<=":
            return value <= self.threshold
        elif self.condition == "==":
            return value == self.threshold
        elif self.condition == "!=":
            return value != self.threshold
        return False
        
    def _evaluate_change_rate(self, history: List[float]) -> bool:
        """变化率评估"""
        if len(history) < 2:
            return False
            
        recent_values = history[-min(10, len(history)):]
        if len(recent_values) < 2:
            return False
            
        # 计算变化率
        old_value = recent_values[0]
        new_value = recent_values[-1]
        
        if old_value == 0:
            return False
            
        change_rate = abs((new_value - old_value) / old_value) * 100
        
        return change_rate > self.threshold
        
    def _evaluate_statistical(self, history: List[float]) -> bool:
        """统计评估"""
        if len(history) < 3:
            return False
            
        recent_values = history[-min(30, len(history)):]
        current_value = recent_values[-1]
        
        if self.condition == "outlier":
            # 简单的离群值检测
            mean_val = sum(recent_values) / len(recent_values)
            variance = sum((x - mean_val) ** 2 for x in recent_values) / len(recent_values)
            std_dev = variance ** 0.5
            
            return abs(current_value - mean_val) > (self.threshold * std_dev)
            
        return False


@dataclass
class Alert:
    """告警实例"""
    id: str
    rule_name: str
    level: AlertLevel
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    labels: Dict[str, str] = field(default_factory=dict)
    status: AlertStatus = AlertStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved_at: Optional[str] = None
    count: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class AlertNotification:
    """告警通知"""
    alert: Alert
    channels: List[str]  # 通知渠道: email, webhook, slack, sms等
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert": self.alert.to_dict(),
            "channels": self.channels,
            "timestamp": self.timestamp
        }


class NotificationChannel:
    """通知渠道基类"""
    
    def __init__(self, name: str):
        self.name = name
        
    def send(self, notification: AlertNotification) -> bool:
        """发送通知"""
        raise NotImplementedError
        
    def test(self) -> bool:
        """测试连接"""
        return True


class EmailChannel(NotificationChannel):
    """邮件通知渠道"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str, 
                 from_email: str, to_emails: List[str], use_tls: bool = True):
        super().__init__("email")
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
        self.use_tls = use_tls
        
    def send(self, notification: AlertNotification) -> bool:
        """发送邮件通知"""
        try:
            # 创建邮件内容
            subject = f"[{notification.alert.level.value}] {notification.alert.rule_name}"
            body = f"""
告警详情:
级别: {notification.alert.level.value}
规则: {notification.alert.rule_name}
消息: {notification.alert.message}
指标: {notification.alert.metric_name}
当前值: {notification.alert.metric_value}
阈值: {notification.alert.threshold}
时间: {notification.alert.created_at}
ID: {notification.alert.id}
            """
            
            # 发送邮件
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ", ".join(self.to_emails)
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 连接SMTP服务器
            if self.use_tls:
                context = ssl.create_default_context()
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls(context=context)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.from_email, self.to_emails, text)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Email notification failed: {e}")
            return False
            
    def test(self) -> bool:
        """测试邮件配置"""
        try:
            if self.use_tls:
                context = ssl.create_default_context()
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls(context=context)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                
            server.login(self.username, self.password)
            server.quit()
            return True
        except Exception:
            return False


class WebhookChannel(NotificationChannel):
    """Webhook通知渠道"""
    
    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None, 
                 timeout: int = 30, retry_count: int = 3):
        super().__init__("webhook")
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
        self.retry_count = retry_count
        
    def send(self, notification: AlertNotification) -> bool:
        """发送Webhook通知"""
        try:
            payload = {
                "alert": notification.alert.to_dict(),
                "timestamp": notification.timestamp,
                "source": "agentbus"
            }
            
            headers = {
                "Content-Type": "application/json",
                **self.headers
            }
            
            response = requests.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return True
            
        except Exception as e:
            print(f"Webhook notification failed: {e}")
            return False


class SlackChannel(NotificationChannel):
    """Slack通知渠道"""
    
    def __init__(self, webhook_url: str, channel: Optional[str] = None, 
                 username: str = "AgentBus Alerts", icon_emoji: str = ":warning:"):
        super().__init__("slack")
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username
        self.icon_emoji = icon_emoji
        
    def send(self, notification: AlertNotification) -> bool:
        """发送Slack通知"""
        try:
            color_map = {
                AlertLevel.INFO: "good",
                AlertLevel.WARNING: "warning", 
                AlertLevel.ERROR: "danger",
                AlertLevel.CRITICAL: "danger"
            }
            
            payload = {
                "username": self.username,
                "icon_emoji": self.icon_emoji,
                "attachments": [{
                    "color": color_map.get(notification.alert.level, "warning"),
                    "title": f"[{notification.alert.level.value}] {notification.alert.rule_name}",
                    "text": notification.alert.message,
                    "fields": [
                        {
                            "title": "指标",
                            "value": notification.alert.metric_name,
                            "short": True
                        },
                        {
                            "title": "当前值",
                            "value": str(notification.alert.metric_value),
                            "short": True
                        },
                        {
                            "title": "阈值",
                            "value": str(notification.alert.threshold),
                            "short": True
                        },
                        {
                            "title": "时间",
                            "value": notification.alert.created_at,
                            "short": True
                        }
                    ],
                    "footer": "AgentBus Alert System",
                    "ts": int(datetime.utcnow().timestamp())
                }]
            }
            
            if self.channel:
                payload["channel"] = self.channel
                
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            return True
            
        except Exception as e:
            print(f"Slack notification failed: {e}")
            return False


class AlertManager:
    """告警管理器"""
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=10000)
        self.notification_channels: Dict[str, NotificationChannel] = {}
        self._lock = threading.Lock()
        self._running = False
        self._evaluation_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[Alert], None]] = []
        self._suppression_rules: Dict[str, Dict[str, Any]] = {}
        
    def start_monitoring(self) -> None:
        """开始监控"""
        with self._lock:
            if not self._running:
                self._running = True
                self._evaluation_thread = threading.Thread(
                    target=self._evaluation_loop,
                    daemon=True,
                    name="AlertEvaluator"
                )
                self._evaluation_thread.start()
                
    def stop_monitoring(self) -> None:
        """停止监控"""
        with self._lock:
            self._running = False
            if self._evaluation_thread:
                self._evaluation_thread.join(timeout=5)
                
    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        with self._lock:
            self.rules[rule.name] = rule
            
    def remove_rule(self, rule_name: str) -> None:
        """删除告警规则"""
        with self._lock:
            self.rules.pop(rule_name, None)
            
    def add_notification_channel(self, channel: NotificationChannel) -> None:
        """添加通知渠道"""
        self.notification_channels[channel.name] = channel
        
    def remove_notification_channel(self, channel_name: str) -> None:
        """删除通知渠道"""
        self.notification_channels.pop(channel_name, None)
        
    def trigger_alert(self, rule_name: str, message: str, metric_name: str, 
                     metric_value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """手动触发告警"""
        with self._lock:
            if rule_name not in self.rules:
                return
                
            rule = self.rules[rule_name]
            alert_id = f"{rule_name}:{metric_name}:{int(time.time())}"
            
            alert = Alert(
                id=alert_id,
                rule_name=rule_name,
                level=rule.level,
                message=message,
                metric_name=metric_name,
                metric_value=metric_value,
                threshold=rule.threshold,
                labels=labels or {}
            )
            
            # 检查是否需要抑制
            if self._should_suppress_alert(alert):
                alert.status = AlertStatus.SUPPRESSED
                self.alert_history.append(alert)
                return
                
            # 发送通知
            self._send_alert_notification(alert)
            
            # 更新活跃告警
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].count += 1
                self.active_alerts[alert_id].updated_at = datetime.utcnow().isoformat()
            else:
                self.active_alerts[alert_id] = alert
                
            self.alert_history.append(alert)
            
            # 触发回调
            for callback in self._callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    print(f"Alert callback failed: {e}")
                    
    def resolve_alert(self, alert_id: str) -> None:
        """解决告警"""
        with self._lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.utcnow().isoformat()
                del self.active_alerts[alert_id]
                
    def add_suppression_rule(self, name: str, rule_config: Dict[str, Any]) -> None:
        """添加告警抑制规则"""
        self._suppression_rules[name] = rule_config
        
    def _should_suppress_alert(self, alert: Alert) -> bool:
        """检查是否应该抑制告警"""
        for rule_name, config in self._suppression_rules.items():
            # 简单的抑制逻辑 - 可以根据需要扩展
            if config.get("type") == "cooldown":
                cooldown_seconds = config.get("cooldown_seconds", 300)
                recent_alerts = [
                    a for a in self.alert_history
                    if (a.rule_name == alert.rule_name and 
                        a.metric_name == alert.metric_name and
                        a.status == AlertStatus.ACTIVE and
                        (datetime.utcnow() - datetime.fromisoformat(a.updated_at)).total_seconds() < cooldown_seconds)
                ]
                if recent_alerts:
                    return True
                    
        return False
        
    def _send_alert_notification(self, alert: Alert) -> None:
        """发送告警通知"""
        # 准备通知渠道列表
        channels = []
        
        # 根据告警级别选择通知渠道
        if alert.level == AlertLevel.CRITICAL:
            channels = list(self.notification_channels.keys())
        elif alert.level == AlertLevel.ERROR:
            channels = [name for name, ch in self.notification_channels.items() 
                       if name in ["email", "slack", "webhook"]]
        elif alert.level == AlertLevel.WARNING:
            channels = [name for name, ch in self.notification_channels.items() 
                       if name in ["slack", "webhook"]]
        else:  # INFO
            channels = [name for name, ch in self.notification_channels.items() 
                       if name == "webhook"]
                       
        # 发送通知
        notification = AlertNotification(alert=alert, channels=channels)
        
        for channel_name in channels:
            channel = self.notification_channels.get(channel_name)
            if channel:
                success = channel.send(notification)
                if not success:
                    print(f"Failed to send notification via {channel_name}")
                    
    def _evaluation_loop(self) -> None:
        """告警评估循环"""
        while self._running:
            try:
                self._evaluate_all_rules()
                time.sleep(30)  # 每30秒评估一次
            except Exception as e:
                print(f"Alert evaluation error: {e}")
                time.sleep(30)
                
    def _evaluate_all_rules(self) -> None:
        """评估所有规则"""
        for rule_name, rule in self.rules.items():
            try:
                # 获取指标历史数据
                history = self._get_metric_history(rule.metric_name, rule.evaluation_window)
                
                if history:
                    current_value = history[-1]
                    
                    # 评估告警条件
                    if rule.evaluate(current_value, history):
                        message = f"指标 {rule.metric_name} 的值 {current_value} 满足告警条件 {rule.condition} {rule.threshold}"
                        self.trigger_alert(rule_name, message, rule.metric_name, current_value)
                    else:
                        # 检查是否需要解决相关告警
                        self._check_alert_resolution(rule_name, rule.metric_name)
                        
            except Exception as e:
                print(f"Rule evaluation failed for {rule_name}: {e}")
                
    def _get_metric_history(self, metric_name: str, window_seconds: int) -> List[float]:
        """获取指标历史数据"""
        # 这里应该从metrics collector获取实际的历史数据
        # 简化实现，返回空列表
        return []
        
    def _check_alert_resolution(self, rule_name: str, metric_name: str) -> None:
        """检查告警是否应该被解决"""
        alert_ids_to_resolve = []
        
        for alert_id, alert in self.active_alerts.items():
            if alert.rule_name == rule_name and alert.metric_name == metric_name:
                if alert.status == AlertStatus.ACTIVE:
                    alert_ids_to_resolve.append(alert_id)
                    
        for alert_id in alert_ids_to_resolve:
            self.resolve_alert(alert_id)
            
    def register_callback(self, callback: Callable[[Alert], None]) -> None:
        """注册告警回调"""
        self._callbacks.append(callback)
        
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        with self._lock:
            return list(self.active_alerts.values())
            
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        return list(self.alert_history)[-limit:]
        
    def test_notification_channels(self) -> Dict[str, bool]:
        """测试所有通知渠道"""
        results = {}
        for name, channel in self.notification_channels.items():
            results[name] = channel.test()
        return results
        
    def export_config(self) -> Dict[str, Any]:
        """导出配置"""
        return {
            "rules": {name: asdict(rule) for name, rule in self.rules.items()},
            "notification_channels": {
                name: {
                    "type": type(channel).__name__,
                    "config": getattr(channel, "__dict__", {})
                }
                for name, channel in self.notification_channels.items()
            },
            "suppression_rules": self._suppression_rules
        }
        
    def save_to_file(self, file_path: str) -> None:
        """保存配置到文件"""
        config = self.export_config()
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)


# 全局告警管理器实例
_alert_manager: Optional[AlertManager] = None


def get_alert_manager(metrics_collector: Optional[MetricsCollector] = None) -> AlertManager:
    """获取全局告警管理器"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager(metrics_collector)
    return _alert_manager


# 便捷函数
def create_email_channel(smtp_server: str, smtp_port: int, username: str, password: str,
                        from_email: str, to_emails: List[str]) -> EmailChannel:
    """创建邮件通知渠道"""
    return EmailChannel(smtp_server, smtp_port, username, password, from_email, to_emails)


def create_webhook_channel(url: str, headers: Optional[Dict[str, str]] = None) -> WebhookChannel:
    """创建Webhook通知渠道"""
    return WebhookChannel(url, headers)


def create_slack_channel(webhook_url: str, channel: Optional[str] = None) -> SlackChannel:
    """创建Slack通知渠道"""
    return SlackChannel(webhook_url, channel)


def add_alert_rule(rule: AlertRule) -> None:
    """添加告警规则"""
    get_alert_manager().add_rule(rule)


def trigger_manual_alert(rule_name: str, message: str, metric_name: str, 
                        metric_value: float, labels: Optional[Dict[str, str]] = None) -> None:
    """手动触发告警"""
    get_alert_manager().trigger_alert(rule_name, message, metric_name, metric_value, labels)