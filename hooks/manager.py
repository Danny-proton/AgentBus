"""
AgentBus Hook Manager

Provides high-level hook lifecycle management, configuration, and orchestration.
"""

import asyncio
import logging
import os
import json
import yaml
from typing import Dict, List, Optional, Any, Set, Callable
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import asdict

from .types import (
    Hook, HookEntry, HookEvent, HookResult, HookEventType,
    HookExecutionContext, HookMetadata, HookSource
)
from .core import hook_engine, get_hook_engine
from .loader import HookLoader
from .config import HookConfig

logger = logging.getLogger(__name__)


class HookManager:
    """High-level manager for hook system operations"""
    
    def __init__(self, config: Optional[HookConfig] = None, workspace_dir: Optional[str] = None):
        self.config = config or HookConfig()
        self.workspace_dir = workspace_dir or os.getcwd()
        self.loader = HookLoader(workspace_dir=self.workspace_dir)
        self._enabled_hooks: Set[str] = set()
        self._disabled_hooks: Set[str] = set()
        self._hook_lifecycles: Dict[str, Dict[str, datetime]] = {}
        self._execution_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000
        
        # Hook state tracking
        self._loaded_hooks: Dict[str, HookEntry] = {}
        self._failed_hooks: Dict[str, str] = {}  # hook_name -> error_message
        self._health_status: Dict[str, bool] = {}  # hook_name -> is_healthy
        
        # Statistics
        self._statistics = {
            'load_time': datetime.now(),
            'total_loads': 0,
            'successful_loads': 0,
            'failed_loads': 0,
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'average_execution_time': 0.0,
            'last_execution': None
        }
    
    async def initialize(self) -> bool:
        """
        Initialize the hook manager and load all hooks
        
        Returns:
            True if initialization successful
        """
        try:
            logger.info("Initializing AgentBus Hook Manager...")
            
            # Load hooks from all sources
            loaded_entries = await self.loader.load_all_hooks(self.config)
            
            # Register loaded hooks
            await self._register_loaded_hooks(loaded_entries)
            
            # Apply configuration
            await self._apply_configuration()
            
            logger.info(f"Hook Manager initialized with {len(loaded_entries)} hooks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Hook Manager: {e}")
            return False
    
    async def _register_loaded_hooks(self, hook_entries: List[HookEntry]) -> None:
        """Register all loaded hook entries"""
        for entry in hook_entries:
            hook_name = entry.hook.name
            
            try:
                # Load the hook handler
                handler = await self.loader.load_hook_handler(entry)
                
                if handler:
                    # Register with hook engine
                    priority = entry.metadata.priority if entry.metadata else 0
                    timeout = entry.metadata.timeout if entry.metadata else None
                    
                    # Register for all events
                    events = entry.metadata.events if entry.metadata else []
                    for event in events:
                        success = hook_engine.registry.register(
                            event_key=event,
                            handler=handler,
                            priority=priority,
                            hook_entry=entry
                        )
                        
                        if success:
                            self._loaded_hooks[hook_name] = entry
                            self._health_status[hook_name] = True
                            logger.debug(f"Registered hook '{hook_name}' for event '{event}'")
                        else:
                            raise Exception("Registration failed")
                    
                    self._statistics['successful_loads'] += 1
                    
                else:
                    raise Exception("Handler loading failed")
                    
            except Exception as e:
                error_msg = f"Failed to register hook '{hook_name}': {e}"
                self._failed_hooks[hook_name] = error_msg
                self._statistics['failed_loads'] += 1
                logger.error(error_msg)
            
            self._statistics['total_loads'] += 1
    
    async def _apply_configuration(self) -> None:
        """Apply hook configuration settings"""
        try:
            # Apply enable/disable settings
            if hasattr(self.config, 'enabled_hooks'):
                for hook_name in self.config.enabled_hooks:
                    await self.enable_hook(hook_name)
            
            if hasattr(self.config, 'disabled_hooks'):
                for hook_name in self.config.disabled_hooks:
                    await self.disable_hook(hook_name)
            
            # Apply priority adjustments
            if hasattr(self.config, 'priority_overrides'):
                for hook_name, priority in self.config.priority_overrides.items():
                    await self.set_hook_priority(hook_name, priority)
            
            logger.debug("Applied hook configuration settings")
            
        except Exception as e:
            logger.error(f"Failed to apply hook configuration: {e}")
    
    async def enable_hook(self, hook_name: str) -> bool:
        """
        Enable a specific hook
        
        Args:
            hook_name: Name of the hook to enable
            
        Returns:
            True if successful
        """
        try:
            self._enabled_hooks.add(hook_name)
            self._disabled_hooks.discard(hook_name)
            self._health_status[hook_name] = True
            
            logger.info(f"Enabled hook '{hook_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable hook '{hook_name}': {e}")
            return False
    
    async def disable_hook(self, hook_name: str) -> bool:
        """
        Disable a specific hook
        
        Args:
            hook_name: Name of the hook to disable
            
        Returns:
            True if successful
        """
        try:
            self._disabled_hooks.add(hook_name)
            self._enabled_hooks.discard(hook_name)
            self._health_status[hook_name] = False
            
            logger.info(f"Disabled hook '{hook_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disable hook '{hook_name}': {e}")
            return False
    
    async def set_hook_priority(self, hook_name: str, priority: int) -> bool:
        """
        Set priority for a specific hook
        
        Args:
            hook_name: Name of the hook
            priority: New priority value
            
        Returns:
            True if successful
        """
        try:
            # This would require access to the hook registry to adjust priorities
            # For now, we'll store this in configuration for the loader to apply
            if not hasattr(self.config, 'priority_overrides'):
                self.config.priority_overrides = {}
            
            self.config.priority_overrides[hook_name] = priority
            logger.info(f"Set priority {priority} for hook '{hook_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set priority for hook '{hook_name}': {e}")
            return False
    
    async def reload_hooks(self) -> bool:
        """
        Reload all hooks from sources
        
        Returns:
            True if reload successful
        """
        try:
            logger.info("Reloading all hooks...")
            
            # Clear existing registrations
            hook_engine.registry.clear()
            
            # Reset state
            self._loaded_hooks.clear()
            self._failed_hooks.clear()
            self._health_status.clear()
            
            # Reinitialize
            return await self.initialize()
            
        except Exception as e:
            logger.error(f"Failed to reload hooks: {e}")
            return False
    
    async def trigger_event(
        self,
        event_type: HookEventType,
        action: str,
        session_key: str,
        context: Optional[HookExecutionContext] = None,
        **kwargs
    ) -> List[HookResult]:
        """
        Trigger event and execute hooks
        
        Args:
            event_type: Type of event
            action: Specific action
            session_key: Session identifier
            context: Execution context
            **kwargs: Additional event data
            
        Returns:
            List of execution results
        """
        start_time = datetime.now()
        
        try:
            event = HookEvent(
                type=event_type,
                action=action,
                session_key=session_key,
                context=context or HookExecutionContext(session_key=session_key),
                data=kwargs
            )
            
            # Execute hooks
            results = await hook_engine.trigger(event)
            
            # Update statistics
            self._update_execution_statistics(results, start_time)
            
            # Log execution
            self._log_execution(event, results, start_time)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to trigger event {event_type.value}:{action}: {e}")
            return []
    
    def _update_execution_statistics(self, results: List[HookResult], start_time: datetime) -> None:
        """Update execution statistics"""
        execution_time = (datetime.now() - start_time).total_seconds()
        
        self._statistics['total_executions'] += 1
        
        if results:
            successful = sum(1 for r in results if r.success)
            failed = len(results) - successful
            
            self._statistics['successful_executions'] += successful
            self._statistics['failed_executions'] += failed
            
            # Update average execution time
            total_time = self._statistics['average_execution_time'] * (self._statistics['total_executions'] - 1)
            self._statistics['average_execution_time'] = (total_time + execution_time) / self._statistics['total_executions']
        
        self._statistics['last_execution'] = start_time
    
    def _log_execution(self, event: HookEvent, results: List[HookResult], start_time: datetime) -> None:
        """Log hook execution details"""
        execution_time = (datetime.now() - start_time).total_seconds()
        successful = sum(1 for r in results if r.success)
        
        logger.info(
            f"Event {event.type.value}:{event.action} executed {len(results)} hooks "
            f"({successful} successful, {len(results) - successful} failed) in {execution_time:.3f}s"
        )
        
        # Add to execution history
        execution_record = {
            'timestamp': start_time.isoformat(),
            'event_type': event.type.value,
            'action': event.action,
            'session_key': event.session_key,
            'hooks_executed': len(results),
            'successful_hooks': successful,
            'failed_hooks': len(results) - successful,
            'execution_time': execution_time,
            'results': [asdict(r) for r in results]
        }
        
        self._execution_history.append(execution_record)
        
        # Trim history if needed
        if len(self._execution_history) > self._max_history_size:
            self._execution_history = self._execution_history[-self._max_history_size:]
    
    def get_hook_status(self, hook_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get status of hooks
        
        Args:
            hook_name: Specific hook name, or None for all
            
        Returns:
            Dictionary with hook status information
        """
        if hook_name:
            return {
                'name': hook_name,
                'loaded': hook_name in self._loaded_hooks,
                'enabled': hook_name not in self._disabled_hooks,
                'healthy': self._health_status.get(hook_name, False),
                'failed': hook_name in self._failed_hooks,
                'error': self._failed_hooks.get(hook_name)
            }
        
        return {
            'total_loaded': len(self._loaded_hooks),
            'total_failed': len(self._failed_hooks),
            'enabled_hooks': len(self._enabled_hooks),
            'disabled_hooks': len(self._disabled_hooks),
            'healthy_hooks': sum(1 for h in self._health_status.values() if h),
            'failed_hooks': list(self._failed_hooks.keys()),
            'loaded_hooks': list(self._loaded_hooks.keys())
        }
    
    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get execution history
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of execution history records
        """
        return self._execution_history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive hook manager statistics"""
        return {
            **self._statistics,
            'engine': get_hook_engine().get_statistics(),
            'status': self.get_hook_status(),
            'uptime': str(datetime.now() - self._statistics['load_time']),
            'memory_usage': self._get_memory_usage()
        }
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        try:
            import psutil
            process = psutil.Process()
            return {
                'rss_mb': process.memory_info().rss / 1024 / 1024,
                'vms_mb': process.memory_info().vms / 1024 / 1024,
                'percent': process.memory_percent()
            }
        except ImportError:
            return {'error': 'psutil not available'}
        except Exception as e:
            return {'error': str(e)}
    
    async def cleanup_expired_history(self, max_age_days: int = 7) -> int:
        """
        Clean up old execution history
        
        Args:
            max_age_days: Maximum age in days for history records
            
        Returns:
            Number of records removed
        """
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        original_count = len(self._execution_history)
        self._execution_history = [
            record for record in self._execution_history
            if datetime.fromisoformat(record['timestamp']) > cutoff_date
        ]
        
        removed_count = original_count - len(self._execution_history)
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old execution history records")
        
        return removed_count
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        
        Returns:
            Dictionary with health check results
        """
        health_status = {
            'overall_health': True,
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        try:
            # Check hook engine health
            engine_stats = get_hook_engine().get_statistics()
            health_status['checks']['hook_engine'] = {
                'healthy': True,
                'details': engine_stats
            }
            
            # Check loader health
            loader_stats = self.loader.get_statistics()
            health_status['checks']['hook_loader'] = {
                'healthy': True,
                'details': loader_stats
            }
            
            # Check hook failures
            if self._failed_hooks:
                health_status['checks']['hook_failures'] = {
                    'healthy': False,
                    'details': self._failed_hooks
                }
                health_status['overall_health'] = False
            
            # Check execution statistics
            failure_rate = 0
            if self._statistics['total_executions'] > 0:
                failure_rate = self._statistics['failed_executions'] / self._statistics['total_executions']
            
            health_status['checks']['execution_rate'] = {
                'healthy': failure_rate < 0.1,  # Less than 10% failure rate
                'failure_rate': failure_rate,
                'details': {
                    'total_executions': self._statistics['total_executions'],
                    'failed_executions': self._statistics['failed_executions']
                }
            }
            
            if failure_rate >= 0.1:
                health_status['overall_health'] = False
            
        except Exception as e:
            health_status['overall_health'] = False
            health_status['error'] = str(e)
            logger.error(f"Health check failed: {e}")
        
        return health_status


# Global hook manager instance
_hook_manager: Optional[HookManager] = None


def get_hook_manager() -> HookManager:
    """Get the global hook manager instance"""
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
    return _hook_manager


async def initialize_hook_manager(
    config: Optional[HookConfig] = None,
    workspace_dir: Optional[str] = None
) -> HookManager:
    """
    Initialize the global hook manager
    
    Args:
        config: Hook configuration
        workspace_dir: Workspace directory
        
    Returns:
        Initialized hook manager
    """
    global _hook_manager
    _hook_manager = HookManager(config, workspace_dir)
    await _hook_manager.initialize()
    return _hook_manager