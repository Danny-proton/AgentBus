"""
AgentBus Internal Hooks

Built-in hook implementations for the AgentBus system.
"""

import asyncio
import logging
import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from .types import HookEvent, HookResult, HookExecutionContext
from .core import register_hook

logger = logging.getLogger(__name__)


class LoggingHook:
    """Hook for logging events and errors"""
    
    @staticmethod
    async def handle_event(event: HookEvent) -> HookResult:
        """Log hook events for debugging and monitoring"""
        try:
            logger.info(
                f"Event triggered: {event.type.value}:{event.action} "
                f"(session: {event.session_key})"
            )
            
            # Log context details
            if event.context.agent_id:
                logger.debug(f"Agent ID: {event.context.agent_id}")
            if event.context.channel_id:
                logger.debug(f"Channel ID: {event.context.channel_id}")
            if event.context.user_id:
                logger.debug(f"User ID: {event.context.user_id}")
            
            # Log event data
            if event.data:
                logger.debug(f"Event data: {json.dumps(event.data, default=str)}")
            
            return HookResult(
                success=True,
                data={'logged': True}
            )
            
        except Exception as e:
            logger.error(f"Logging hook failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )


class MetricsHook:
    """Hook for collecting metrics and performance data"""
    
    def __init__(self):
        self.metrics_data = {
            'events_processed': 0,
            'hooks_executed': 0,
            'errors_count': 0,
            'total_execution_time': 0.0,
            'average_execution_time': 0.0,
            'events_by_type': {},
            'last_updated': datetime.now()
        }
    
    async def handle_event(self, event: HookEvent) -> HookResult:
        """Collect metrics from events"""
        try:
            # Update basic metrics
            self.metrics_data['events_processed'] += 1
            self.metrics_data['events_by_type'][event.type.value] = \
                self.metrics_data['events_by_type'].get(event.type.value, 0) + 1
            self.metrics_data['last_updated'] = datetime.now()
            
            return HookResult(
                success=True,
                data=self.metrics_data
            )
            
        except Exception as e:
            self.metrics_data['errors_count'] += 1
            logger.error(f"Metrics hook failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collected metrics"""
        return self.metrics_data.copy()


class SessionManagementHook:
    """Hook for managing session lifecycle"""
    
    async def handle_session_start(self, event: HookEvent) -> HookResult:
        """Handle session start events"""
        try:
            context = event.context
            
            # Log session start
            logger.info(f"Session started: {event.session_key}")
            
            # Initialize session data if needed
            if context.workspace_dir:
                session_file = Path(context.workspace_dir) / "sessions" / f"{event.session_key}.json"
                session_file.parent.mkdir(exist_ok=True)
                
                if not session_file.exists():
                    session_data = {
                        'session_key': event.session_key,
                        'start_time': datetime.now().isoformat(),
                        'agent_id': context.agent_id,
                        'channel_id': context.channel_id,
                        'user_id': context.user_id,
                        'events': []
                    }
                    
                    with open(session_file, 'w') as f:
                        json.dump(session_data, f, indent=2)
            
            return HookResult(
                success=True,
                data={'session_initialized': True}
            )
            
        except Exception as e:
            logger.error(f"Session management hook failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )
    
    async def handle_session_end(self, event: HookEvent) -> HookResult:
        """Handle session end events"""
        try:
            context = event.context
            
            # Log session end
            logger.info(f"Session ended: {event.session_key}")
            
            # Update session data if available
            if context.workspace_dir:
                session_file = Path(context.workspace_dir) / "sessions" / f"{event.session_key}.json"
                if session_file.exists():
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)
                    
                    session_data['end_time'] = datetime.now().isoformat()
                    session_data['duration'] = (
                        datetime.now() - datetime.fromisoformat(session_data['start_time'])
                    ).total_seconds()
                    
                    with open(session_file, 'w') as f:
                        json.dump(session_data, f, indent=2)
            
            return HookResult(
                success=True,
                data={'session_finalized': True}
            )
            
        except Exception as e:
            logger.error(f"Session management hook failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )


class ErrorHandlingHook:
    """Hook for centralized error handling and recovery"""
    
    async def handle_error(self, event: HookEvent) -> HookResult:
        """Handle error events"""
        try:
            error_data = event.data.get('error', {})
            error_type = error_data.get('type', 'unknown')
            error_message = error_data.get('message', 'No message')
            
            logger.error(
                f"Error event: {error_type} - {error_message} "
                f"(session: {event.session_key})"
            )
            
            # Attempt recovery actions based on error type
            recovery_actions = self._get_recovery_actions(error_type)
            
            return HookResult(
                success=True,
                data={
                    'error_handled': True,
                    'recovery_actions': recovery_actions
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling hook failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )
    
    def _get_recovery_actions(self, error_type: str) -> List[str]:
        """Get recovery actions based on error type"""
        recovery_map = {
            'connection_error': ['retry', 'fallback'],
            'timeout_error': ['increase_timeout', 'retry'],
            'authentication_error': ['reauthenticate', 'notify_admin'],
            'configuration_error': ['use_defaults', 'notify_admin'],
            'resource_error': ['cleanup', 'retry_with_backoff']
        }
        
        return recovery_map.get(error_type, ['log', 'continue'])


class SecurityHook:
    """Hook for security monitoring and enforcement"""
    
    async def handle_security_event(self, event: HookEvent) -> HookResult:
        """Handle security-related events"""
        try:
            security_data = event.data
            event_type = security_data.get('event_type', 'unknown')
            
            # Log security events
            logger.warning(
                f"Security event: {event_type} "
                f"(session: {event.session_key}, user: {event.context.user_id})"
            )
            
            # Check for suspicious patterns
            suspicious = self._check_suspicious_patterns(event)
            
            return HookResult(
                success=True,
                data={
                    'security_event_logged': True,
                    'suspicious_activity': suspicious
                }
            )
            
        except Exception as e:
            logger.error(f"Security hook failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )
    
    def _check_suspicious_patterns(self, event: HookEvent) -> bool:
        """Check for suspicious activity patterns"""
        # Simple pattern checking - in a real implementation,
        # this would be more sophisticated
        suspicious_patterns = [
            'sql_injection',
            'script_injection', 
            'path_traversal',
            'privilege_escalation'
        ]
        
        event_data_str = str(event.data).lower()
        return any(pattern in event_data_str for pattern in suspicious_patterns)


class HealthMonitoringHook:
    """Hook for system health monitoring"""
    
    def __init__(self):
        self.health_data = {
            'last_check': None,
            'system_status': 'healthy',
            'checks_performed': 0,
            'issues_found': []
        }
    
    async def handle_health_check(self, event: HookEvent) -> HookResult:
        """Perform system health checks"""
        try:
            self.health_data['last_check'] = datetime.now()
            self.health_data['checks_performed'] += 1
            
            # Perform various health checks
            issues = []
            
            # Check memory usage
            import psutil
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 90:
                issues.append(f'High memory usage: {memory_percent}%')
            
            # Check disk usage
            disk_percent = psutil.disk_usage('/').percent
            if disk_percent > 90:
                issues.append(f'High disk usage: {disk_percent}%')
            
            # Check if too many errors recently
            # This would require access to error tracking
            
            self.health_data['issues_found'] = issues
            self.health_data['system_status'] = 'degraded' if issues else 'healthy'
            
            return HookResult(
                success=True,
                data=self.health_data
            )
            
        except Exception as e:
            logger.error(f"Health monitoring hook failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )


class PerformanceOptimizationHook:
    """Hook for performance monitoring and optimization"""
    
    async def handle_performance_event(self, event: HookEvent) -> HookResult:
        """Handle performance-related events"""
        try:
            perf_data = event.data
            operation = perf_data.get('operation', 'unknown')
            duration = perf_data.get('duration', 0)
            
            # Log slow operations
            if duration > 5.0:  # Log operations taking more than 5 seconds
                logger.warning(
                    f"Slow operation detected: {operation} took {duration:.2f}s "
                    f"(session: {event.session_key})"
                )
            
            # Check for optimization opportunities
            optimizations = self._suggest_optimizations(operation, duration)
            
            return HookResult(
                success=True,
                data={
                    'optimizations_suggested': optimizations,
                    'duration': duration
                }
            )
            
        except Exception as e:
            logger.error(f"Performance optimization hook failed: {e}")
            return HookResult(
                success=False,
                error=str(e)
            )
    
    def _suggest_optimizations(self, operation: str, duration: float) -> List[str]:
        """Suggest optimizations based on operation and duration"""
        suggestions = []
        
        if duration > 10.0:
            suggestions.append(f"Consider optimizing {operation} - it took {duration:.2f}s")
        
        if operation == 'database_query':
            suggestions.append('Consider adding database indexes')
        elif operation == 'file_processing':
            suggestions.append('Consider streaming or chunking large files')
        elif operation == 'api_call':
            suggestions.append('Consider caching API responses')
        
        return suggestions


# Initialize built-in hook instances
logging_hook = LoggingHook()
metrics_hook = MetricsHook()
session_management = SessionManagementHook()
error_handler = ErrorHandlingHook()
security_monitor = SecurityHook()
health_monitor = HealthMonitoringHook()
performance_optimizer = PerformanceOptimizationHook()


def register_internal_hooks():
    """Register all internal hooks"""
    try:
        # Logging hooks
        register_hook('*', logging_hook.handle_event, priority=-1000)
        
        # Metrics hooks
        register_hook('*', metrics_hook.handle_event, priority=-900)
        
        # Session management hooks
        register_hook('session:start', session_management.handle_session_start, priority=100)
        register_hook('session:end', session_management.handle_session_end, priority=100)
        
        # Error handling hooks
        register_hook('error', error_handler.handle_error, priority=500)
        
        # Security hooks
        register_hook('security:*', security_monitor.handle_security_event, priority=200)
        
        # Health monitoring hooks
        register_hook('health:check', health_monitor.handle_health_check, priority=-500)
        
        # Performance monitoring hooks
        register_hook('performance:*', performance_optimizer.handle_performance_event, priority=-800)
        
        logger.info("Registered all internal hooks")
        
    except Exception as e:
        logger.error(f"Failed to register internal hooks: {e}")


def get_metrics() -> Dict[str, Any]:
    """Get metrics from built-in hooks"""
    return {
        'logging': {},
        'metrics': metrics_hook.get_metrics(),
        'session_management': {},
        'error_handling': {},
        'security': {},
        'health': health_monitor.health_data,
        'performance': {}
    }


async def cleanup_internal_hooks():
    """Cleanup internal hooks"""
    try:
        # Reset metrics
        global metrics_hook, health_monitor
        metrics_hook = MetricsHook()
        health_monitor = HealthMonitoringHook()
        
        logger.info("Cleaned up internal hooks")
        
    except Exception as e:
        logger.error(f"Failed to cleanup internal hooks: {e}")